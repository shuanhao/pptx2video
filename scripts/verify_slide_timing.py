"""Report predicted-vs-measured per-slide timing for an exported MP4.

This is now a thin reporting wrapper around
``src.audio_position_locator.locate_slide_start_times()`` - the actual
cross-correlation logic that used to live in this script has moved there so
the real subtitle pipeline (``subtitle_pipeline.generate_srt_from_true_starts()``,
wired up in ``main.py``) and this diagnostic script share one implementation
instead of two copies that could silently drift apart.

Why this exists: multiple independent user reports (e.g. a Microsoft Q&A
thread - see the project discussion this script was originally written in
response to) describe PowerPoint's "Create a Video" export adding
inconsistent extra "dead space" (silence) after a slide's audio finishes,
even when the slide's duration is supposed to be driven entirely by its
embedded audio. This was later confirmed against a real ~2h40m/20-slide
deck, where drift grew to several seconds by the end and did *not* behave
like a simple uniform scaling factor - see the project discussion and
``src/audio_position_locator.py``'s module docstring. As a result, the
pipeline's default behavior (when both ``--subtitles-output`` and
``--export-video`` are given together) is now the accurate, measured
"true-start" path rather than the naive "sum of mp3 durations" prediction -
see ``main.py``. This script remains useful as a standalone diagnostic: to
double check an exported deck's actual drift characteristics, or to verify
the locator's measurements independently of a full CLI run.

Requires numpy and scipy (project dependencies as of the true-start
alignment feature - see pyproject.toml) and ffmpeg/ffprobe on PATH (already
a project prerequisite - see tts.py's FileNotFoundError hint) to extract the
MP4's audio track.

Usage:
    python scripts/verify_slide_timing.py <final.mp4> <manifest.json> <original.pptx> [--default-slide-duration 5.0]

Where:
    final.mp4       - the video exported by ppt_automation.export_video()
    manifest.json   - the manifest written by tts.generate_audio_files()
                       (has each audio slide's mp3 filename + output_dir)
    original.pptx   - the source deck (used only to get the full slide
                       list, including slides with no notes/no audio, so
                       gaps are accounted for in the predicted timeline)

What to look for when you run this:

- A table of predicted vs. measured start time for every slide with audio,
  and the delta between them.
- "Max |delta| observed" at the end. If everything stayed under ~0.5s, the
  naive "sum of mp3 durations" approach is safe to use standalone (no
  export yet). If it grows slide over slide (drift) or jumps
  unpredictably, that confirms why the pipeline's default is now the
  measured true-start path instead.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.audio_position_locator import (
    DEFAULT_ANCHOR_SECONDS,
    DEFAULT_SEARCH_WINDOW_SECONDS,
    SAMPLE_RATE,
    _load_mono_array,
    locate_slide_start_times,
)
from src.pptx_parser import extract_notes
from src.logging_config import ensure_utf8_console

# A delta beyond this is flagged as a likely dead-space/drift symptom rather
# than ordinary correlation noise.
DRIFT_WARNING_THRESHOLD_SECONDS = 0.5


def main():
    # Reconfigure stdout/stderr to UTF-8 before any print() - Windows can
    # otherwise crash printing CJK slide text when stdout/stderr is piped
    # rather than an interactive console (see ensure_utf8_console()'s
    # docstring for the confirmed real-world crash this fixes).
    ensure_utf8_console()

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("video_path", type=Path)
    parser.add_argument("manifest_path", type=Path)
    parser.add_argument("pptx_path", type=Path)
    parser.add_argument("--default-slide-duration", type=float, default=5.0)
    parser.add_argument("--search-window-seconds", type=float, default=DEFAULT_SEARCH_WINDOW_SECONDS)
    parser.add_argument(
        "--anchor-seconds", type=float, default=DEFAULT_ANCHOR_SECONDS,
        help=(
            "Only correlate the first this-many seconds of each slide's own "
            "audio, not the whole clip - avoids a bias from PowerPoint's "
            "export very slightly time-stretching embedded audio, which "
            "otherwise accumulates into a large error on long clips. Usually "
            "no need to change this."
        ),
    )
    args = parser.parse_args()

    manifest = json.loads(args.manifest_path.read_text(encoding="utf-8"))
    audio_dir = Path(manifest.get("output_dir") or args.manifest_path.parent)
    audio_by_slide = {int(e["slide_num"]): e["audio_file"] for e in manifest.get("slides", [])}

    slides = sorted(extract_notes(str(args.pptx_path)), key=lambda s: int(s["slide_num"]))

    print(f"Extracting audio track and measuring per-slide positions in {args.video_path} ...")
    measured_starts, locate_warnings = locate_slide_start_times(
        args.video_path,
        slides,
        manifest,
        audio_dir,
        default_slide_duration=args.default_slide_duration,
        search_window_seconds=args.search_window_seconds,
        anchor_seconds=args.anchor_seconds,
    )
    for warning in locate_warnings:
        print(f"WARNING: {warning}")

    # Re-walk the same predicted timeline locate_slide_start_times() used
    # internally, purely for this script's side-by-side report - the
    # measurements themselves already come back computed.
    predicted_start = 0.0
    max_abs_delta = 0.0
    print(f"\n{'slide':>5} {'predicted':>10} {'measured':>10} {'delta':>8}")

    for slide in slides:
        slide_num = int(slide["slide_num"])
        audio_file = audio_by_slide.get(slide_num)

        if audio_file is None:
            print(f"{slide_num:>5} {predicted_start:>9.2f}s   (no audio - default duration)")
            predicted_start += args.default_slide_duration
            continue

        mp3_path = audio_dir / audio_file
        measured_start = measured_starts.get(slide_num)

        if measured_start is None:
            print(f"{slide_num:>5} {predicted_start:>9.2f}s   (could not measure - see warnings above)")
            continue

        clip_duration = len(_load_mono_array(mp3_path)) / SAMPLE_RATE
        delta = measured_start - predicted_start
        max_abs_delta = max(max_abs_delta, abs(delta))

        flag = "  <-- possible dead-space drift" if abs(delta) > DRIFT_WARNING_THRESHOLD_SECONDS else ""
        print(f"{slide_num:>5} {predicted_start:>9.2f}s {measured_start:>9.2f}s {delta:>+7.2f}s{flag}")

        predicted_start += clip_duration

    print(f"\nMax |delta| observed: {max_abs_delta:.2f}s")
    if max_abs_delta > DRIFT_WARNING_THRESHOLD_SECONDS:
        print(
            "WARNING: predicted and measured slide start times drift apart. "
            "This matches the reported PowerPoint dead-space export issue. "
            "main.py's default behavior when --subtitles-output and "
            "--export-video are used together already accounts for this "
            "(see subtitle_pipeline.generate_srt_from_true_starts())."
        )
    else:
        print(
            "Predicted and measured slide start times stayed closely in "
            "sync for this deck."
        )


if __name__ == "__main__":
    main()
