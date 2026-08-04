import argparse
import json
import logging
import sys
from pathlib import Path
from typing import NoReturn

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import ppt_automation
from src.audio_position_locator import DEFAULT_GLOBAL_SCALE_CORRECTION, locate_slide_start_and_end_times
from src.exceptions import Pptx2VideoError, PptParseError, TTSGenerationError
from src.logging_config import setup_logging
from src.pptx_parser import extract_notes
from src.subtitle_pipeline import generate_srt_for_deck, generate_srt_from_true_starts
from src.tts import generate_audio_files


def _non_negative_int(value: str) -> int:
    """argparse ``type=`` for options where a negative int would be a silent
    footgun rather than a validation error - see ``--tts-max-retries``: a
    negative value used to make the retry loop never run at all, which
    ``tts.generate_audio_files`` now defends against too, but rejecting it
    here gives the user an immediate, clear error instead of the value being
    quietly clamped somewhere downstream.
    """
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError(f"must be 0 or greater, got {parsed}")
    return parsed


def _parse_slide_selector(value: str) -> set:
    """argparse ``type=`` for ``--slides``: a comma-separated list of slide
    numbers and/or ranges, e.g. ``"6,9"`` or ``"6,8-10,15"``, into a set of
    ints. Added so a single slide (or a handful) can be regenerated - e.g.
    to re-check a specific slide for the dropped-narration issue described
    in CHANGELOG's "未發布" entry - without re-running edge-tts against an
    entire deck, which for a long deck can take well over an hour.

    Kept deliberately simple (no negative numbers, no open-ended ranges) -
    slide numbers are always positive and this is a small CLI convenience,
    not a general expression parser.
    """
    result = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_str, _, end_str = part.partition("-")
            try:
                start, end = int(start_str), int(end_str)
            except ValueError:
                raise argparse.ArgumentTypeError(f"invalid range '{part}' - expected e.g. '8-10'")
            if end < start:
                raise argparse.ArgumentTypeError(f"invalid range '{part}': end before start")
            result.update(range(start, end + 1))
        else:
            try:
                result.add(int(part))
            except ValueError:
                raise argparse.ArgumentTypeError(f"invalid slide number '{part}'")
    if not result:
        raise argparse.ArgumentTypeError("no slide numbers found")
    return result


def build_payload(slides, pptx_path, audio_manifest=None, audio_output_dir=None):
    enriched_slides = []
    for slide in slides:
        notes = slide.get("notes")
        slide_num = int(slide.get("slide_num", 0))
        audio_file = None
        if audio_manifest is not None:
            for entry in audio_manifest.get("slides", []):
                if int(entry.get("slide_num", 0)) == slide_num:
                    audio_file = str((Path(audio_output_dir or "") / entry.get("audio_file", "")).as_posix()) if audio_output_dir else entry.get("audio_file")
                    break

        enriched_slides.append({
            "slide_num": slide_num,
            "title": slide.get("title"),
            "notes": notes,
            "subtitle_text": notes if notes else None,
            "has_notes": bool(notes and str(notes).strip()),
            "audio_file": audio_file,
        })

    payload = {
        "source_pptx": pptx_path,
        "slide_count": len(enriched_slides),
        "slides": enriched_slides,
        "audio": audio_manifest or {},
        "metadata": {
            "generated_by": "pptx2video",
            "audio_output_dir": audio_output_dir,
        },
    }
    return payload


def write_subtitle_output(payload, output_path, audio_dir=None, default_slide_duration=5.0):
    """Build and write the deck-wide SRT file for ``payload`` (as built by
    ``build_payload``), via ``subtitle_pipeline.generate_srt_for_deck()``.

    Requires ``payload["audio"]`` (the audio manifest, as ``build_payload``
    stores it) to have per-slide ``word_boundaries_file`` entries - i.e.
    this only produces real subtitle lines for slides whose audio was
    generated via ``generate_audio_files()``'s default (word-boundary-
    capturing) path. If ``payload["audio"]`` is empty/missing (no
    ``--generate-audio`` was run this invocation and no manifest was
    loaded), the result is a valid but empty (zero-cue) SRT file rather
    than an error - running without ``--generate-audio`` is a normal,
    supported use of the CLI (e.g. just parsing notes to JSON).

    Returns ``(output_path, warnings)`` - see
    ``generate_srt_for_deck``'s docstring for what ends up in ``warnings``.
    """
    output_path = Path(output_path)
    slides = payload.get("slides", [])
    manifest = payload.get("audio") or {}
    resolved_audio_dir = audio_dir or payload.get("metadata", {}).get("audio_output_dir") or "."

    srt_text, warnings = generate_srt_for_deck(
        slides, manifest, resolved_audio_dir, default_slide_duration=default_slide_duration
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(srt_text, encoding="utf-8")
    return output_path, warnings


def write_subtitle_output_from_export(
    payload, output_path, video_path, audio_dir=None, default_slide_duration=5.0,
    global_scale_correction=DEFAULT_GLOBAL_SCALE_CORRECTION,
):
    """Like ``write_subtitle_output``, but positions each slide's subtitle
    lines using its *measured* real start time in ``video_path`` (an
    already-exported MP4) instead of a predicted cumulative sum - see
    ``src.audio_position_locator`` and
    ``subtitle_pipeline.generate_srt_from_true_starts()`` for why: the
    predictive path was found to drift by several seconds on a real
    long/complex deck, and not as a simple uniform scaling factor either, so
    it isn't trustworthy on its own once a real exported video exists to
    measure against instead.

    Requires ``video_path`` to already exist (i.e. this must be called after
    ``ppt_automation.export_video()`` succeeds) and needs ffmpeg on PATH
    plus the numpy/scipy dependencies - see ``audio_position_locator``'s
    module docstring. Raises whatever ``locate_slide_start_and_end_times``
    raises (e.g. ``RuntimeError`` if the video's audio track can't be
    extracted at all) rather than swallowing it - callers should catch this
    and fall back to ``write_subtitle_output`` if they want the run to still
    produce a (less accurate) SRT rather than fail outright.

    Returns ``(output_path, warnings)`` - ``warnings`` combines
    ``locate_slide_start_and_end_times``'s warnings (prefixed) with
    ``generate_srt_from_true_starts``'s.
    """
    output_path = Path(output_path)
    slides = payload.get("slides", [])
    manifest = payload.get("audio") or {}
    resolved_audio_dir = audio_dir or payload.get("metadata", {}).get("audio_output_dir") or "."

    # build_payload() stores slides without the raw notes text stripped out,
    # but generate_srt_for_deck/generate_srt_from_true_starts both expect
    # the same shape pptx_parser.extract_notes() produces (slide_num, notes)
    # - payload's enriched slides already carry both under those same keys,
    # so no reshaping is needed here.
    #
    # Uses locate_slide_start_and_end_times() (not just ...start_times()) so
    # generate_srt_from_true_starts() can measure each slide's own intra-
    # slide stretch ratio directly (via its own measured end), rather than
    # inferring it from the gap to the next slide's start - the latter was
    # found (via scripts/verify_srt_accuracy.py's word-level ground-truth
    # sampling on a real deck) to be biased by whatever gap PowerPoint's
    # export inserts *between* slides, a separate effect from this slide's
    # own narration stretching. See subtitle_pipeline.py's module docstring,
    # design decision 5.
    bounds, locate_warnings = locate_slide_start_and_end_times(
        video_path, slides, manifest, resolved_audio_dir, default_slide_duration=default_slide_duration,
        global_scale_correction=global_scale_correction,
    )
    start_times = {slide_num: start for slide_num, (start, _end) in bounds.items()}
    end_times = {slide_num: end for slide_num, (_start, end) in bounds.items()}

    srt_text, srt_warnings = generate_srt_from_true_starts(
        slides, manifest, resolved_audio_dir, start_times, end_times,
        default_slide_duration=default_slide_duration,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(srt_text, encoding="utf-8")

    warnings = [f"(true-start locate) {w}" for w in locate_warnings] + srt_warnings
    return output_path, warnings


def _fail(parser: argparse.ArgumentParser, logger: logging.Logger, message: str) -> NoReturn:
    """Log an error (so it's captured in the log file too) and exit via argparse.

    ``parser.error()`` prints the message to stderr and exits with status 2 -
    it never returns, but doesn't itself go through the logger, which is why
    this wrapper logs first.
    """
    logger.error(message)
    parser.error(message)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse a PowerPoint file and optionally generate MP3 audio files from slide notes.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("pptx_path", help="Path to the input .pptx file")
    parser.add_argument(
        "--output",
        "-o",
        help="Path to write the parsed notes JSON output file",
        default="output/slides.json",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON result to stdout",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Number of spaces to use for JSON indentation",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed progress information while processing the file",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail the run if any slide has missing or unreadable content",
    )
    parser.add_argument(
        "--generate-audio",
        action="store_true",
        help="Generate MP3 audio files from slide notes using edge-tts",
    )
    parser.add_argument(
        "--audio-output-dir",
        default="output/audio",
        help="Directory where generated MP3 files should be written",
    )
    parser.add_argument(
        "--slides",
        type=_parse_slide_selector,
        default=None,
        help=(
            "Only (re)generate audio for these slide number(s), e.g. '6,9' or '6,8-10'. "
            "Useful for re-checking/re-generating a specific slide (e.g. to investigate a "
            "POSSIBLE DROPPED NARRATION warning) without re-running edge-tts against the "
            "whole deck. If manifest.json already exists in --audio-output-dir, entries for "
            "slides NOT in this selection are preserved unchanged rather than dropped. "
            "Default: generate every slide with notes."
        ),
    )
    parser.add_argument(
        "--voice",
        default="Microsoft Server Speech Text to Speech Voice (zh-TW, YunJheNeural)",
        help="Edge-TTS voice name to use for audio generation (full style, e.g. Microsoft Server Speech Text to Speech Voice (zh-TW, YunJheNeural))",
    )
    parser.add_argument(
        "--rate",
        default="-10%",
        help="Speech rate for edge-tts (for example -10%% or +5%%)",
    )
    parser.add_argument(
        "--pitch",
        default="+0Hz",
        help="Pitch for edge-tts (use +0Hz to keep the pitch unchanged)",
    )
    parser.add_argument(
        "--tts-max-retries",
        type=_non_negative_int,
        default=3,
        help=(
            "How many times to retry generating a slide's audio after a "
            "transient failure (network blip, service hiccup) before giving "
            "up. Set to 0 to disable retrying entirely. Non-transient "
            "failures (e.g. missing ffmpeg) are never retried."
        ),
    )
    parser.add_argument(
        "--tts-retry-delay",
        type=float,
        default=2.0,
        help="Seconds to wait between TTS retry attempts",
    )
    parser.add_argument(
        "--subtitles-output",
        default="output/captions.srt",
        help=(
            "Path to write the generated subtitles .srt file. Real subtitle "
            "lines require an audio manifest with word-boundary timing data "
            "(from --generate-audio, or an existing manifest.json under "
            "--audio-output-dir) - without one, an empty .srt is written "
            "rather than failing the run."
        ),
    )
    parser.add_argument(
        "--global-scale-correction",
        type=float,
        default=DEFAULT_GLOBAL_SCALE_CORRECTION,
        help=(
            "Multiplier applied to every true-start-measured subtitle time (only used when "
            "--export-video is also given, i.e. the 'measure against the real MP4' subtitle path) - "
            "corrects a small, deck-wide proportional measurement bias found empirically, NOT a "
            "property of PowerPoint's export itself (see src/audio_position_locator.py's "
            "DEFAULT_GLOBAL_SCALE_CORRECTION docstring for the full story and how to derive your own "
            "value). Defaults to 1.0 (no correction) - do not reuse another deck's calibrated value "
            "without re-checking it against your own real playback times."
        ),
    )
    parser.add_argument(
        "--insert-audio",
        action="store_true",
        help=(
            "Insert generated audio into the PPTX, shrunk and tucked into "
            "the top-right corner. Requires Windows with Microsoft "
            "PowerPoint and pywin32 installed. Slides without notes/audio "
            "are left untouched, and slide transition timing is not changed."
        ),
    )
    parser.add_argument(
        "--pptx-output",
        default=None,
        help=(
            "Path to save the PPTX with inserted audio (used with "
            "--insert-audio). Defaults to overwriting the input file."
        ),
    )
    parser.add_argument(
        "--insert-audio-timeout",
        type=float,
        default=1800.0,
        help=(
            "Give up waiting for --insert-audio to finish after this many "
            "seconds (e.g. if PowerPoint is stuck behind a blocking "
            "dialog). Set to 0 to wait indefinitely (the previous, "
            "unbounded behavior). Note this only stops waiting - it cannot "
            "force-close a stuck PowerPoint."
        ),
    )
    parser.add_argument(
        "--export-video",
        action="store_true",
        help=(
            "Export the PPTX to MP4 using PowerPoint's 'Create a Video' "
            "feature. Requires Windows with Microsoft PowerPoint and "
            "pywin32 installed. If --insert-audio was also given, the "
            "deck with inserted audio is exported; otherwise the input "
            "PPTX (or --pptx-output, if given) is exported as-is."
        ),
    )
    parser.add_argument(
        "--video-output",
        default=None,
        help=(
            "Path to write the exported .mp4 (used with --export-video). "
            "Defaults to the PPTX path with its extension changed to .mp4."
        ),
    )
    parser.add_argument(
        "--video-resolution",
        type=int,
        default=720,
        help=(
            "Vertical resolution in pixels, matching PowerPoint's export "
            "presets (e.g. 480, 720 for HD, 1080 for Full HD, 2160 for 4K)"
        ),
    )
    parser.add_argument(
        "--video-fps",
        type=int,
        default=30,
        help="Frames per second for the exported video",
    )
    parser.add_argument(
        "--video-quality",
        type=int,
        default=85,
        help="Encoding quality, 0-100 (PowerPoint's own default is 85)",
    )
    parser.add_argument(
        "--video-default-duration",
        type=float,
        default=5.0,
        help=(
            "Seconds to show a slide that has neither recorded timing nor "
            "auto-playing embedded audio (e.g. a cover slide). Matches "
            "PowerPoint's 'Seconds spent on each slide' export field. Also "
            "used by subtitle generation to predict such a slide's place in "
            "the timeline - keep this in sync with whatever value is "
            "actually used for --export-video, or the subtitles will drift "
            "out of sync with the exported MP4."
        ),
    )
    parser.add_argument(
        "--video-use-recorded-timings",
        action="store_true",
        help=(
            "Use recorded slide timings/narrations instead of "
            "--video-default-duration / embedded-audio-driven timing. "
            "Off by default, matching PowerPoint's 'Don't Use Recorded "
            "Timings and Narrations' option."
        ),
    )
    parser.add_argument(
        "--video-timeout",
        type=float,
        default=3600,
        help=(
            "Give up waiting for PowerPoint to finish exporting after this "
            "many seconds. Increase for longer decks or higher resolutions."
        ),
    )
    parser.add_argument(
        "--log-dir",
        default="logs",
        help=(
            "Directory to write a dated log file into (e.g. logs/2026-07-28.log). "
            "The file always captures full DEBUG-level detail, regardless of --verbose."
        ),
    )
    parser.add_argument(
        "--no-file-log",
        action="store_true",
        help="Disable writing a log file; only print to the console.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    logger = setup_logging(
        verbose=args.verbose,
        log_dir=None if args.no_file_log else args.log_dir,
    )

    pptx_path = args.pptx_path
    output_path = Path(args.output) if args.output else None

    logger.debug(f"Parsing PowerPoint file: {pptx_path}")

    # Every except branch below calls _fail(), which is annotated -> NoReturn
    # and always exits via parser.error() (SystemExit) - so `slides` is
    # guaranteed to be assigned by the time execution reaches past this
    # block. Assigning it inside try and reading it in `else` (rather than
    # right after the try/except) makes that guarantee explicit instead of
    # relying on the reader already knowing what _fail() does.
    try:
        slides = extract_notes(pptx_path)
    except FileNotFoundError as exc:
        _fail(parser, logger, str(exc))
    except ValueError as exc:
        _fail(parser, logger, str(exc))
    except PptParseError as exc:
        _fail(parser, logger, str(exc))
    except Exception as exc:
        _fail(parser, logger, f"Unexpected error while parsing {pptx_path}: {exc}")
    else:
        logger.debug(f"Loaded {len(slides)} slide(s)")

    if args.strict:
        for slide in slides:
            if slide.get("notes") is None:
                _fail(parser, logger, f"Strict mode: slide {slide['slide_num']} has no notes")

    audio_manifest = None
    if args.generate_audio:
        def _print_audio_progress(current: int, total: int, slide_num: int) -> None:
            logger.info(f"Generating audio {current}/{total} (slide {slide_num})...")

        def _print_audio_retry(attempt: int, max_retries: int, slide_num: int, exc: Exception) -> None:
            logger.warning(
                f"Slide {slide_num}: attempt {attempt}/{max_retries + 1} failed "
                f"({exc}); retrying in {args.tts_retry_delay:.0f}s..."
            )

        def _print_narration_gap(slide_num: int, suspect: dict) -> None:
            # Deliberately its own loud, distinct log line - not mixed in
            # with the many small per-segment "interpolated" warnings
            # subtitle generation prints later (see
            # subtitle_alignment.find_suspected_dropped_narration's
            # docstring for why: a real deck showed edge-tts silently skip
            # ~300 characters of a slide's notes, and that got buried among
            # ordinary single-punctuation-mark mismatches until someone
            # went looking by hand). Shows the actual skipped text so
            # there's something concrete to go listen for and verify,
            # rather than just a number.
            preview = suspect["skipped_text"].strip().replace("\n", " ")
            if len(preview) > 120:
                preview = preview[:120] + "..."
            logger.warning(
                f"POSSIBLE DROPPED NARRATION - slide {slide_num}: edge-tts's audio has only "
                f"{suspect['gap_seconds']:.1f}s around {suspect['audio_position_seconds']:.1f}s "
                f"where ~{suspect['expected_seconds']:.0f}s was expected for this much source text. "
                f"Listen to slide_{slide_num:03d}.mp3 around {suspect['audio_position_seconds']:.1f}s "
                f"to confirm. Skipped text: {preview!r}"
            )

        manifest_path = Path(args.audio_output_dir) / "manifest.json"

        # --slides scopes this run to a subset of slides (see its help
        # text) - typically to cheaply re-check/re-generate one slide that
        # threw a POSSIBLE DROPPED NARRATION warning, rather than paying for
        # a full-deck edge-tts run again. generate_audio_files() itself has
        # no concept of "only some slides" - it always writes a fresh
        # manifest.json from whatever slide list it's given - so the
        # narrowing and the manifest-merge-back-in both happen here, not
        # inside tts.py, to keep that function's contract simple (it always
        # fully describes exactly the slides it was asked to generate).
        if args.slides is not None:
            slides_to_generate = [s for s in slides if int(s.get("slide_num", 0)) in args.slides]
            found_slide_nums = {int(s.get("slide_num", 0)) for s in slides_to_generate}
            missing = sorted(args.slides - found_slide_nums)
            if missing:
                _fail(parser, logger, f"--slides referenced slide number(s) not found in the deck: {missing}")

            previous_manifest = None
            if manifest_path.exists():
                try:
                    previous_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    logger.warning(
                        f"--slides was given but existing {manifest_path} could not be read/parsed "
                        f"({exc}) - proceeding without merging; it will be overwritten with only the "
                        "regenerated slide(s)."
                    )
        else:
            slides_to_generate = slides
            previous_manifest = None

        try:
            audio_manifest = generate_audio_files(
                slides_to_generate,
                args.audio_output_dir,
                voice=args.voice,
                manifest_path=manifest_path,
                rate=args.rate,
                pitch=args.pitch,
                progress_callback=_print_audio_progress,
                max_retries=args.tts_max_retries,
                retry_delay_seconds=args.tts_retry_delay,
                on_retry=_print_audio_retry,
                on_narration_gap=_print_narration_gap,
            )
        except TTSGenerationError as exc:
            _fail(parser, logger, str(exc))

        regenerated_count = len(audio_manifest["slides"])

        if previous_manifest is not None:
            # Merge: entries for slides that were just (re)generated replace
            # the old ones; every other slide's entry from the prior run is
            # kept as-is, so a --slides run never silently truncates
            # manifest.json down to just the slides it touched (which would
            # otherwise break --subtitles-output/--insert-audio for every
            # other slide until a full re-run).
            merged_by_slide_num = {
                int(entry.get("slide_num", 0)): entry
                for entry in previous_manifest.get("slides", [])
            }
            for entry in audio_manifest["slides"]:
                merged_by_slide_num[int(entry.get("slide_num", 0))] = entry
            audio_manifest["slides"] = [
                merged_by_slide_num[num] for num in sorted(merged_by_slide_num)
            ]
            manifest_path.write_text(
                json.dumps(audio_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            logger.info(
                f"Regenerated {regenerated_count} audio file(s) for slide(s) {sorted(args.slides)}; "
                f"merged into existing manifest.json ({len(audio_manifest['slides'])} slide(s) total) "
                "so other slides' entries were preserved."
            )
        else:
            logger.debug(json.dumps(audio_manifest, ensure_ascii=False, indent=args.indent))
            logger.info(f"Generated {regenerated_count} audio file(s) in {args.audio_output_dir}")

    # Shared by --insert-audio, --export-video's post-export true-start
    # subtitle path, and (below) the plain predictive subtitle path: all
    # three are fine with either the manifest generated this run or one
    # loaded from a previous run's --generate-audio (e.g. producing
    # subtitles for a deck whose audio was already generated earlier,
    # without paying for another edge-tts run just to re-derive it).
    def _resolve_audio_manifest():
        if audio_manifest is not None:
            return audio_manifest
        manifest_path = Path(args.audio_output_dir) / "manifest.json"
        try:
            return ppt_automation.load_audio_manifest(manifest_path)
        except FileNotFoundError:
            return None

    payload = build_payload(
        slides,
        pptx_path,
        audio_manifest=audio_manifest,
        audio_output_dir=args.audio_output_dir,
    )

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=args.indent),
            encoding="utf-8",
        )
        logger.info(f"Saved JSON to {output_path}")

    subtitle_output_path = Path(args.subtitles_output) if args.subtitles_output else None

    # Subtitle timing has two ways to be placed on the deck-wide timeline -
    # see subtitle_pipeline.py's module docstring:
    #
    # - "Predictive" (write_subtitle_output): sums each slide's own audio
    #   duration to guess its position. Fast, but was found (on a real
    #   ~2h40m/20-slide deck) to drift by several seconds from the actual
    #   exported video, and not as a simple scaling factor either - not
    #   trustworthy for long/complex decks.
    # - "True-start" (write_subtitle_output_from_export): measures each
    #   slide's *real* start time by cross-correlating against the actual
    #   exported MP4's audio track. Accurate, but can only run after
    #   --export-video has produced that file.
    #
    # So: if this run is also exporting a video, subtitle generation is
    # deferred until after that export succeeds (see below) and uses the
    # accurate true-start path; only write the predictive version now, up
    # front, when no video is being exported this run at all (there's
    # nothing yet to measure against).
    #
    # Like the true-start path below, this resolves the audio manifest via
    # _resolve_audio_manifest() rather than only using whatever this
    # invocation's --generate-audio (if any) produced - so running just
    # `--subtitles-output` after audio was already generated in an earlier,
    # separate `--generate-audio` run still produces real subtitle lines
    # from the existing manifest.json, instead of silently writing an empty
    # .srt and requiring --generate-audio to be repeated (and edge-tts
    # called again) purely to re-derive data that's already on disk.
    if subtitle_output_path and not args.export_video:
        manifest_for_subtitles = _resolve_audio_manifest()
        payload_for_subtitles = payload
        if manifest_for_subtitles is not audio_manifest:
            payload_for_subtitles = build_payload(
                slides,
                pptx_path,
                audio_manifest=manifest_for_subtitles,
                audio_output_dir=args.audio_output_dir,
            )

        subtitle_output_path, subtitle_warnings = write_subtitle_output(
            payload_for_subtitles,
            subtitle_output_path,
            audio_dir=args.audio_output_dir,
            default_slide_duration=args.video_default_duration,
        )
        logger.info(f"Saved subtitles to {subtitle_output_path}")
        for warning in subtitle_warnings:
            logger.warning(f"Subtitle generation: {warning}")

    # Shared by --insert-audio and --export-video: the PPTX path that
    # downstream steps should operate on. If --insert-audio ran, this is
    # where its output was saved; --export-video reads from the same path
    # so it exports the audio-enriched deck by default.
    pptx_output_path = args.pptx_output or pptx_path

    if args.insert_audio:
        manifest_for_insert = _resolve_audio_manifest()
        if manifest_for_insert is None:
            manifest_path = Path(args.audio_output_dir) / "manifest.json"
            _fail(
                parser,
                logger,
                "--insert-audio requires an audio manifest. Run with "
                f"--generate-audio first, or ensure {manifest_path} exists.",
            )

        def _print_insert_progress(current: int, total: int, slide_num: int, status: str) -> None:
            logger.info(f"Inserting audio {current}/{total} (slide {slide_num})... {status}")

        try:
            insert_result = ppt_automation.insert_audio(
                pptx_path,
                manifest_for_insert,
                args.audio_output_dir,
                output_path=pptx_output_path,
                progress_callback=_print_insert_progress,
                timeout_seconds=(
                    args.insert_audio_timeout if args.insert_audio_timeout > 0 else None
                ),
            )
        except (Pptx2VideoError, FileNotFoundError) as exc:
            _fail(parser, logger, str(exc))

        logger.debug(json.dumps(insert_result, ensure_ascii=False, indent=args.indent))
        logger.info(
            f"Inserted audio into {len(insert_result['inserted_slides'])} slide(s); "
            f"skipped {len(insert_result['skipped_slides'])}. "
            f"Saved to {insert_result['output_path']}"
        )
        if insert_result["skipped_slides"]:
            for skipped in insert_result["skipped_slides"]:
                logger.warning(
                    f"Skipped slide {skipped['slide_num']}: {skipped['reason']}"
                )

    if args.export_video:
        video_source_pptx = Path(pptx_output_path)
        video_output_path = (
            Path(args.video_output)
            if args.video_output
            else video_source_pptx.with_suffix(".mp4")
        )

        def _print_video_progress(status_name: str) -> None:
            logger.info(f"Exporting video... status: {status_name}")

        try:
            export_result = ppt_automation.export_video(
                video_source_pptx,
                video_output_path,
                resolution_height=args.video_resolution,
                frames_per_second=args.video_fps,
                quality=args.video_quality,
                default_slide_duration=args.video_default_duration,
                use_timings_and_narrations=args.video_use_recorded_timings,
                timeout_seconds=args.video_timeout,
                progress_callback=_print_video_progress,
            )
        except (Pptx2VideoError, FileNotFoundError) as exc:
            _fail(parser, logger, str(exc))

        logger.debug(json.dumps(export_result, ensure_ascii=False, indent=args.indent))
        logger.info(
            f"Exported video to {export_result['output_path']} "
            f"({export_result['elapsed_seconds']:.1f}s)"
        )

        if subtitle_output_path:
            manifest_for_subtitles = _resolve_audio_manifest()
            payload_for_subtitles = payload
            if manifest_for_subtitles is not audio_manifest:
                # audio_manifest was None (no --generate-audio this run) and
                # got resolved from a previous run's manifest.json - rebuild
                # payload's slide list against it so subtitle generation
                # sees the same audio_file/word_boundaries_file info
                # insert_audio would have used.
                payload_for_subtitles = build_payload(
                    slides,
                    pptx_path,
                    audio_manifest=manifest_for_subtitles,
                    audio_output_dir=args.audio_output_dir,
                )

            if manifest_for_subtitles is None:
                logger.warning(
                    "Subtitle generation: no audio manifest available "
                    f"(run with --generate-audio, or ensure "
                    f"{Path(args.audio_output_dir) / 'manifest.json'} exists); "
                    "writing an empty .srt."
                )
                subtitle_output_path, subtitle_warnings = write_subtitle_output(
                    payload_for_subtitles,
                    subtitle_output_path,
                    audio_dir=args.audio_output_dir,
                    default_slide_duration=args.video_default_duration,
                )
            else:
                try:
                    subtitle_output_path, subtitle_warnings = write_subtitle_output_from_export(
                        payload_for_subtitles,
                        subtitle_output_path,
                        export_result["output_path"],
                        audio_dir=args.audio_output_dir,
                        default_slide_duration=args.video_default_duration,
                        global_scale_correction=args.global_scale_correction,
                    )
                except Exception as exc:  # noqa: BLE001 - a working export shouldn't be sunk by subtitle alignment failing
                    logger.warning(
                        f"Subtitle generation: true-start alignment against the "
                        f"exported video failed ({exc}); falling back to the "
                        "predicted timeline, which may drift out of sync for "
                        "long/complex decks."
                    )
                    subtitle_output_path, subtitle_warnings = write_subtitle_output(
                        payload_for_subtitles,
                        subtitle_output_path,
                        audio_dir=args.audio_output_dir,
                        default_slide_duration=args.video_default_duration,
                    )

            logger.info(f"Saved subtitles to {subtitle_output_path}")
            for warning in subtitle_warnings:
                logger.warning(f"Subtitle generation: {warning}")

    if args.pretty or output_path is None:
        print(json.dumps(payload, ensure_ascii=False, indent=args.indent))


if __name__ == "__main__":
    main()
