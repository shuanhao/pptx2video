"""Rebuild a deck's .srt using true-start alignment, from files a previous
run already produced - without re-running --generate-audio, --insert-audio,
or --export-video.

Why this exists: audio_position_locator.locate_slide_start_times() and
subtitle_pipeline.generate_srt_from_true_starts() (added in v0.6.0, see
CHANGELOG) only need three things that survive from a previous full run:
the exported MP4, the audio manifest + its mp3/wordboundaries.json files,
and the slide list (notes text + slide numbers). None of those require
Edge-TTS, PowerPoint COM, or re-exporting video - so if you already have a
deck's output/deck.mp4, output/audio/manifest.json (and the mp3/
wordboundaries.json files it references), and either output/slides.json
(from a previous --output run) or the original .pptx, you can regenerate a
correctly-aligned .srt directly against the existing MP4 without repeating
the (potentially very long - e.g. an hour-plus for a big deck) TTS
generation + PowerPoint automation steps.

Usage:
    python scripts/regenerate_srt_from_export.py \\
        --video output/deck.mp4 \\
        --manifest output/audio/manifest.json \\
        --slides-json output/slides.json \\
        --output output/captions.srt

    # or, if you don't have output/slides.json from a previous --output run:
    python scripts/regenerate_srt_from_export.py \\
        --video output/deck.mp4 \\
        --manifest output/audio/manifest.json \\
        --pptx examples/your_deck.pptx \\
        --output output/captions.srt

Exactly one of --slides-json / --pptx must be given - both mean the same
thing (the full, ordered slide list with notes text), just from different
sources. --slides-json is faster (no need to re-parse the .pptx) and is
what --output writes by default; --pptx is the fallback if you don't have
that file around.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.audio_position_locator import (
    DEFAULT_ANCHOR_SECONDS,
    DEFAULT_GLOBAL_SCALE_CORRECTION,
    DEFAULT_SEARCH_WINDOW_SECONDS,
    locate_slide_start_and_end_times,
)
from src.pptx_parser import extract_notes
from src.subtitle_pipeline import DEFAULT_SLIDE_DURATION_SECONDS, generate_srt_from_true_starts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--video", required=True, type=Path, help="The exported MP4 (ppt_automation.export_video()'s output)")
    parser.add_argument("--manifest", required=True, type=Path, help="Path to manifest.json (from --generate-audio)")
    parser.add_argument(
        "--audio-dir",
        type=Path,
        default=None,
        help="Directory the manifest's audio_file names are relative to. Defaults to manifest.json's own directory, or manifest['output_dir'] if present - usually you don't need to set this explicitly.",
    )
    slide_source = parser.add_mutually_exclusive_group(required=True)
    slide_source.add_argument(
        "--slides-json", type=Path,
        help="Path to a JSON file shaped like main.py's --output (has a top-level 'slides' list with slide_num/notes) - the fastest source, avoids re-parsing the .pptx.",
    )
    slide_source.add_argument(
        "--pptx", type=Path,
        help="Path to the original .pptx, re-parsed for its slide list/notes if --slides-json isn't available.",
    )
    parser.add_argument("--output", required=True, type=Path, help="Where to write the regenerated .srt")
    parser.add_argument(
        "--default-slide-duration", type=float, default=DEFAULT_SLIDE_DURATION_SECONDS,
        help="Must match whatever was used for --export-video's --video-default-duration originally, for silent slides' timeline bookkeeping to line up.",
    )
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
    parser.add_argument(
        "--global-scale-correction", type=float, default=DEFAULT_GLOBAL_SCALE_CORRECTION,
        help=(
            "Multiplier applied to every measured start/end time, to correct a small, deck-wide "
            "proportional bias found in this module's own measurement (NOT in PowerPoint's export - "
            "see audio_position_locator.py's DEFAULT_GLOBAL_SCALE_CORRECTION docstring for the full "
            "story). Defaults to 1.0 (no correction) - this is NOT a universal constant, it must be "
            "calibrated per deck/environment: compare a few of this tool's measured times (widely "
            "spaced across the deck) against real playback times you verify with a media player's "
            "precise 'jump to exact time' feature, then fit real_time / measured_time. One real deck "
            "needed ~1.00121 (i.e. +0.121%); yours may need a different value, or none at all."
        ),
    )
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    audio_dir = args.audio_dir or Path(manifest.get("output_dir") or args.manifest.parent)

    if args.slides_json:
        payload = json.loads(args.slides_json.read_text(encoding="utf-8"))
        slides = payload.get("slides", payload) if isinstance(payload, dict) else payload
    else:
        slides = extract_notes(str(args.pptx))

    print(f"Measuring true per-slide start AND end times in {args.video} ...")
    # locate_slide_start_and_end_times() (not just ...start_times()) so the
    # SRT composition step can measure each slide's own intra-slide stretch
    # ratio directly from its own (start, end) pair, instead of inferring it
    # from the gap to the next slide's start - the latter was found to be
    # biased by whatever gap PowerPoint's export inserts *between* slides,
    # separate from a slide's own narration stretching (see
    # subtitle_pipeline.py's module docstring, design decision 5, and
    # scripts/verify_srt_accuracy.py, which is how this was confirmed on a
    # real deck).
    if args.global_scale_correction != 1.0:
        print(f"Applying global scale correction: x{args.global_scale_correction}")
    bounds, locate_warnings = locate_slide_start_and_end_times(
        args.video, slides, manifest, audio_dir,
        default_slide_duration=args.default_slide_duration,
        search_window_seconds=args.search_window_seconds,
        anchor_seconds=args.anchor_seconds,
        global_scale_correction=args.global_scale_correction,
    )
    for w in locate_warnings:
        print(f"WARNING (locate): {w}")

    start_times = {slide_num: start for slide_num, (start, _end) in bounds.items()}
    end_times = {slide_num: end for slide_num, (_start, end) in bounds.items()}

    srt_text, srt_warnings = generate_srt_from_true_starts(
        slides, manifest, audio_dir, start_times, end_times,
        default_slide_duration=args.default_slide_duration,
    )
    for w in srt_warnings:
        print(f"WARNING (subtitles): {w}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(srt_text, encoding="utf-8")
    print(f"Wrote {args.output} ({len(start_times)} slide(s) with a measured true start time).")


if __name__ == "__main__":
    main()
