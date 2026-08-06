"""Burn (hardsub) a .srt into a video as a fixed-width black bar with white
text, using ``src.subtitle_burner``.

Why this is a separate tool from ``split_video_by_slides.py``: burning
subtitles is a distinct operation from cutting a video into segments - you
might want to burn subtitles into the full, unsplit ``deck.mp4`` +
``captions.srt``, re-burn a single segment after tweaking the bar's style
without re-cutting anything, or burn any other .mp4/.srt pair this project
had nothing to do with producing. ``split_video_by_slides.py --burn-
subtitles`` calls the same ``src.subtitle_burner.burn_subtitles_into_video()``
function this script calls, so the two never drift out of sync with each
other - this script is not a special case, it's the same logic exposed on
its own.

Usage (burn the full deck):
    python scripts/burn_subtitles.py \\
        --video output/deck.mp4 \\
        --srt output/captions.srt \\
        --output output/deck_burned.mp4

Usage (burn one already-split segment):
    python scripts/burn_subtitles.py \\
        --video output/segments/segment_1.mp4 \\
        --srt output/segments/segment_1.srt \\
        --output output/segments/segment_1_burned.mp4

The default bar size/position/font were tuned by eye against a real
1280x720 exported slide - see src/subtitle_burner.py's module docstring
and docs/SPLIT_VIDEO.md before changing the defaults for a different
resolution, font, or subtitle line-width limit. All of them can be
overridden per-run without editing code.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.logging_config import ensure_utf8_console
from src.subtitle_burner import (
    DEFAULT_BAR_BOTTOM_OFFSET_PX,
    DEFAULT_BAR_HEIGHT_PX,
    DEFAULT_BAR_WIDTH_PX,
    DEFAULT_CRF,
    DEFAULT_FONT_NAME,
    DEFAULT_FONT_SIZE,
    DEFAULT_MARGIN_V,
    burn_subtitles_into_video,
)


def main() -> int:
    # Reconfigure stdout/stderr to UTF-8 before any print() - Windows can
    # otherwise crash printing CJK slide text when stdout/stderr is piped
    # rather than an interactive console (see ensure_utf8_console()'s
    # docstring for the confirmed real-world crash this fixes).
    ensure_utf8_console()

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--video", required=True, type=Path, help="Input .mp4 to burn subtitles into.")
    parser.add_argument("--srt", required=True, type=Path, help="The .srt whose cues get burned in.")
    parser.add_argument("--output", required=True, type=Path, help="Where to write the burned-in .mp4.")
    parser.add_argument("--bar-width", type=int, default=DEFAULT_BAR_WIDTH_PX, help=f"Black bar width in px (default: {DEFAULT_BAR_WIDTH_PX}).")
    parser.add_argument("--bar-height", type=int, default=DEFAULT_BAR_HEIGHT_PX, help=f"Black bar height in px (default: {DEFAULT_BAR_HEIGHT_PX}).")
    parser.add_argument(
        "--bar-bottom-offset", type=int, default=DEFAULT_BAR_BOTTOM_OFFSET_PX,
        help=(
            f"Distance in px from the very bottom of the frame to the bar's TOP edge "
            f"(default: {DEFAULT_BAR_BOTTOM_OFFSET_PX}) - the bar's bottom edge ends up "
            f"(this - --bar-height) px above the frame's bottom edge."
        ),
    )
    parser.add_argument("--font-name", default=DEFAULT_FONT_NAME, help=f"Font family for the burned-in text (default: {DEFAULT_FONT_NAME!r}).")
    parser.add_argument("--font-size", type=int, default=DEFAULT_FONT_SIZE, help=f"Font size in px (default: {DEFAULT_FONT_SIZE}).")
    parser.add_argument(
        "--margin-v", type=int, default=DEFAULT_MARGIN_V,
        help=f"Distance in px from the frame's bottom edge to the text's bottom edge (default: {DEFAULT_MARGIN_V}). Should sit inside the black bar.",
    )
    parser.add_argument("--crf", type=int, default=DEFAULT_CRF, help=f"libx264 quality (lower = better quality, larger file; default: {DEFAULT_CRF}).")
    args = parser.parse_args()

    if not args.video.exists():
        raise SystemExit(f"--video not found: {args.video}")
    if not args.srt.exists():
        raise SystemExit(f"--srt not found: {args.srt}")

    args.output.parent.mkdir(parents=True, exist_ok=True)

    print(f"Burning {args.srt} into {args.video} -> {args.output} ...")
    burn_subtitles_into_video(
        args.video, args.srt, args.output,
        bar_width_px=args.bar_width,
        bar_height_px=args.bar_height,
        bar_bottom_offset_px=args.bar_bottom_offset,
        font_name=args.font_name,
        font_size=args.font_size,
        margin_v=args.margin_v,
        crf=args.crf,
    )
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
