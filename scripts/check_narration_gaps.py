"""Re-run the "possible dropped narration" heuristic
(``src.subtitle_alignment.find_suspected_dropped_narration``) against audio
that was already generated in a previous ``--generate-audio`` run, without
calling edge-tts again.

Why this exists: the check normally only runs automatically as a side effect
of ``--generate-audio`` (see ``tts.generate_audio_files``'s ``on_narration_gap``
callback and CHANGELOG's "未發布" entry for the real slide-9 case that
motivated it). That's fine going forward, but it means anyone who already has
a ``manifest.json`` + ``slide_XXX.wordboundaries.json`` files from a run made
*before* this check existed has no way to retroactively check that existing
output - the only options would be re-reading the wordboundaries files by
hand, or re-running the entire (potentially hours-long) TTS generation just
to get the check to fire. Both are worse than just re-running the same
already-implemented comparison against files that are already sitting on
disk. This script is that: same function, same defaults, zero network calls.

Usage (checking every narrated slide in a manifest):
    python scripts/check_narration_gaps.py \\
        --manifest output/audio/manifest.json \\
        --slides-json output/slides.json

    # or, if you don't have output/slides.json from a previous --output run:
    python scripts/check_narration_gaps.py \\
        --manifest output/audio/manifest.json \\
        --pptx examples/your_deck.pptx

Usage (checking only specific slides - fast, since it's pure local
comparison against files already on disk regardless of deck size):
    python scripts/check_narration_gaps.py \\
        --manifest output/audio/manifest.json \\
        --slides-json output/slides.json \\
        --slides 6,9

``--slides`` accepts a comma-separated list of slide numbers and/or ranges,
e.g. ``6,9`` or ``6,8-10,15``.

Exit code: 0 if no suspected drops were found (or none of the checked slides
had word-boundary data to check), 1 if at least one was found - so this can
be wired into a script/CI step that fails loudly instead of relying on
someone reading log output.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pptx_parser import extract_notes
from src.subtitle_alignment import (
    DEFAULT_MIN_SUSPECTED_DROP_CHARS,
    DEFAULT_SUSPECTED_DROP_PACE_RATIO,
    find_suspected_dropped_narration,
)


def parse_slide_selector(value: str) -> set:
    """Parse a ``--slides`` value like ``"6,9"`` or ``"6,8-10,15"`` into a
    set of slide numbers. Shared logic with ``src/main.py``'s own
    ``--slides`` flag (see CHANGELOG) - kept as a separate copy here rather
    than imported, since this script is meant to be usable standalone even
    against an older ``src/`` that doesn't have that flag yet.
    """
    result = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_str, _, end_str = part.partition("-")
            start, end = int(start_str), int(end_str)
            if end < start:
                raise argparse.ArgumentTypeError(f"invalid range '{part}': end before start")
            result.update(range(start, end + 1))
        else:
            result.add(int(part))
    if not result:
        raise argparse.ArgumentTypeError("no slide numbers found")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", required=True, type=Path, help="Path to manifest.json (from --generate-audio)")
    parser.add_argument(
        "--audio-dir", type=Path, default=None,
        help="Directory containing slide_XXX.wordboundaries.json files (defaults to manifest.json's own directory / its recorded output_dir)",
    )
    slide_source = parser.add_mutually_exclusive_group(required=True)
    slide_source.add_argument("--slides-json", type=Path, help="output/slides.json from a previous run (has notes text)")
    slide_source.add_argument("--pptx", type=Path, help="Re-extract notes text directly from the .pptx")
    parser.add_argument(
        "--slides", type=str, default=None,
        help="Comma-separated slide numbers/ranges to check, e.g. '6,9' or '6,8-10' (default: every narrated slide in the manifest)",
    )
    parser.add_argument("--min-gap-chars", type=int, default=DEFAULT_MIN_SUSPECTED_DROP_CHARS)
    parser.add_argument("--pace-ratio-threshold", type=float, default=DEFAULT_SUSPECTED_DROP_PACE_RATIO)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    audio_dir = args.audio_dir or Path(manifest.get("output_dir") or args.manifest.parent)

    if args.slides_json:
        payload = json.loads(args.slides_json.read_text(encoding="utf-8"))
        slides = payload.get("slides", payload) if isinstance(payload, dict) else payload
    else:
        slides = extract_notes(str(args.pptx))
    notes_by_slide = {int(s["slide_num"]): s.get("notes") for s in slides if s.get("slide_num") is not None}

    wanted = parse_slide_selector(args.slides) if args.slides else None

    total_checked = 0
    total_skipped_no_wordboundaries = 0
    any_suspects = False

    for entry in manifest.get("slides", []):
        slide_num = int(entry.get("slide_num", 0))
        if wanted is not None and slide_num not in wanted:
            continue

        word_boundaries_file = entry.get("word_boundaries_file")
        if not word_boundaries_file:
            print(f"slide {slide_num}: skipped - no word-boundary data in manifest (custom generator was used, or an older run predating this feature)")
            total_skipped_no_wordboundaries += 1
            continue

        notes = notes_by_slide.get(slide_num)
        if not notes or not str(notes).strip():
            print(f"slide {slide_num}: skipped - no notes text found for this slide in --slides-json/--pptx")
            total_skipped_no_wordboundaries += 1
            continue

        wb_path = audio_dir / word_boundaries_file
        try:
            word_boundaries = json.loads(wb_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"slide {slide_num}: skipped - could not read {wb_path}: {exc}")
            total_skipped_no_wordboundaries += 1
            continue

        total_checked += 1
        suspects = find_suspected_dropped_narration(
            str(notes), word_boundaries,
            min_gap_chars=args.min_gap_chars,
            pace_ratio_threshold=args.pace_ratio_threshold,
        )
        if not suspects:
            print(f"slide {slide_num}: OK ({len(word_boundaries)} word-boundary events, no suspected drops)")
            continue

        any_suspects = True
        for suspect in suspects:
            preview = suspect["skipped_text"].strip().replace("\n", " ")
            if len(preview) > 120:
                preview = preview[:120] + "..."
            print(
                f"slide {slide_num}: POSSIBLE DROPPED NARRATION - audio has only "
                f"{suspect['gap_seconds']:.1f}s around {suspect['audio_position_seconds']:.1f}s "
                f"where ~{suspect['expected_seconds']:.0f}s was expected for this much source text. "
                f"Listen to slide_{slide_num:03d}.mp3 around {suspect['audio_position_seconds']:.1f}s "
                f"to confirm. Skipped text: {preview!r}"
            )

    print()
    print(f"Checked {total_checked} slide(s); {total_skipped_no_wordboundaries} skipped (no data available).")
    if any_suspects:
        print("At least one slide has a suspected dropped-narration gap - see above.")
        return 1
    print("No suspected dropped-narration gaps found in the checked slide(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
