import argparse
import json
import logging
import sys
from pathlib import Path
from typing import NoReturn

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import ppt_automation
from src.exceptions import Pptx2VideoError, PptParseError, TTSGenerationError
from src.logging_config import setup_logging
from src.pptx_parser import extract_notes
from src.subtitle_generator import write_srt
from src.tts import generate_audio_files


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


def write_subtitle_output(payload, output_path, audio_dir=None):
    slides = payload.get("slides", [])
    output_path = Path(output_path)
    return write_srt(slides, output_path, audio_dir=audio_dir)


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
        "--subtitles-output",
        default="output/captions.srt",
        help="Path to write the generated subtitles .srt file",
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
            "PowerPoint's 'Seconds spent on each slide' export field."
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

    logger.debug(f"Loaded {len(slides)} slide(s)")

    if args.strict:
        for slide in slides:
            if slide.get("notes") is None:
                _fail(parser, logger, f"Strict mode: slide {slide['slide_num']} has no notes")

    audio_manifest = None
    if args.generate_audio:
        def _print_audio_progress(current: int, total: int, slide_num: int) -> None:
            logger.info(f"Generating audio {current}/{total} (slide {slide_num})...")

        try:
            audio_manifest = generate_audio_files(
                slides,
                args.audio_output_dir,
                voice=args.voice,
                manifest_path=Path(args.audio_output_dir) / "manifest.json",
                rate=args.rate,
                pitch=args.pitch,
                progress_callback=_print_audio_progress,
            )
        except TTSGenerationError as exc:
            _fail(parser, logger, str(exc))

        logger.debug(json.dumps(audio_manifest, ensure_ascii=False, indent=args.indent))
        logger.info(f"Generated {len(audio_manifest['slides'])} audio file(s) in {args.audio_output_dir}")

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

    subtitle_output_path = Path(args.subtitles_output)
    if subtitle_output_path:
        subtitle_output_path = write_subtitle_output(
            payload,
            subtitle_output_path,
            audio_dir=args.audio_output_dir,
        )
        logger.info(f"Saved subtitles to {subtitle_output_path}")

    # Shared by --insert-audio and --export-video: the PPTX path that
    # downstream steps should operate on. If --insert-audio ran, this is
    # where its output was saved; --export-video reads from the same path
    # so it exports the audio-enriched deck by default.
    pptx_output_path = args.pptx_output or pptx_path

    if args.insert_audio:
        manifest_for_insert = audio_manifest
        if manifest_for_insert is None:
            manifest_path = Path(args.audio_output_dir) / "manifest.json"
            try:
                manifest_for_insert = ppt_automation.load_audio_manifest(manifest_path)
            except FileNotFoundError:
                _fail(
                    parser,
                    logger,
                    "--insert-audio requires an audio manifest. Run with "
                    f"--generate-audio first, or ensure {manifest_path} exists.",
                )

        try:
            insert_result = ppt_automation.insert_audio(
                pptx_path,
                manifest_for_insert,
                args.audio_output_dir,
                output_path=pptx_output_path,
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

    if args.pretty or output_path is None:
        print(json.dumps(payload, ensure_ascii=False, indent=args.indent))


if __name__ == "__main__":
    main()
