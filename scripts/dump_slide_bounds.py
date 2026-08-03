"""One-off helper: dump the exact per-slide (start, end) measurements
``locate_slide_start_and_end_times()`` produces against a real video, as a
small JSON file - so they can be shared/re-used without re-uploading the
(often huge, e.g. 2h40m) source video itself.

Why this exists: after two rounds of ground-truth diagnostics
(scripts/verify_tts_alignment.py, scripts/verify_srt_accuracy.py) showed the
true-start + intra-slide-scale fix measuring accurately on a real deck, the
project owner still saw ~1-2s of growing drift by the end when actually
watching the generated .srt against the video - a discrepancy from what the
diagnostics suggested. To pin down whether that's a bug in
``generate_srt_from_true_starts()``'s own SRT-composition math (as opposed
to the measurement step, already validated), this dumps the exact
``(start, end)`` pairs used for that composition, so they can be replayed
against the same manifest/wordboundaries/slides data (all small, text-only
files) on a machine that doesn't have the source video at all - such as
this one - to reproduce the *exact* same generate_srt_from_true_starts()
call and compare its output byte-for-byte against the actually-delivered
.srt.

Usage (same arguments as regenerate_srt_from_export.py):
    python scripts/dump_slide_bounds.py \\
        --video output/deck.mp4 --manifest output/audio/manifest.json \\
        --slides-json output/slides.json --output output/slide_bounds.json
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
from src.subtitle_pipeline import DEFAULT_SLIDE_DURATION_SECONDS


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--audio-dir", type=Path, default=None)
    slide_source = parser.add_mutually_exclusive_group(required=True)
    slide_source.add_argument("--slides-json", type=Path)
    slide_source.add_argument("--pptx", type=Path)
    parser.add_argument("--output", required=True, type=Path, help="Where to write the dumped bounds JSON")
    parser.add_argument("--default-slide-duration", type=float, default=DEFAULT_SLIDE_DURATION_SECONDS)
    parser.add_argument("--search-window-seconds", type=float, default=DEFAULT_SEARCH_WINDOW_SECONDS)
    parser.add_argument("--anchor-seconds", type=float, default=DEFAULT_ANCHOR_SECONDS)
    parser.add_argument(
        "--global-scale-correction", type=float, default=DEFAULT_GLOBAL_SCALE_CORRECTION,
        help=(
            "Multiplier applied to every measured start/end time - see "
            "audio_position_locator.py's DEFAULT_GLOBAL_SCALE_CORRECTION docstring. Defaults to 1.0 "
            "(no correction); calibrate per deck/environment, don't reuse another deck's value blindly."
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

    print(f"Measuring true per-slide start/end times in {args.video} ...")
    if args.global_scale_correction != 1.0:
        print(f"Applying global scale correction: x{args.global_scale_correction}")
    bounds, warnings = locate_slide_start_and_end_times(
        args.video, slides, manifest, audio_dir,
        default_slide_duration=args.default_slide_duration,
        search_window_seconds=args.search_window_seconds,
        anchor_seconds=args.anchor_seconds,
        global_scale_correction=args.global_scale_correction,
    )
    for w in warnings:
        print(f"WARNING: {w}")

    dump = {
        "params": {
            "default_slide_duration": args.default_slide_duration,
            "search_window_seconds": args.search_window_seconds,
            "anchor_seconds": args.anchor_seconds,
            "global_scale_correction": args.global_scale_correction,
        },
        "warnings": warnings,
        # JSON object keys must be strings - slide numbers are stringified,
        # convert back to int when reloading.
        "bounds": {str(k): {"start": v[0], "end": v[1]} for k, v in sorted(bounds.items())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dump, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {args.output} ({len(bounds)} slide(s)).")


if __name__ == "__main__":
    main()
