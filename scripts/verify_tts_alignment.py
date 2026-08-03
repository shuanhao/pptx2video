"""Stage 1 check: is each slide's own .mp3 + .wordboundaries.json internally
consistent, on their own - *before* PowerPoint or any video export enters
the picture at all?

Why this exists: when a real deck's final .srt is still out of sync with its
.mp4 after two rounds of fixes to the true-start/anchor/intra-slide-scale
logic (see CHANGELOG v0.6.1), the project owner asked to stop guessing and
verify each stage of the pipeline independently instead:

    1. edge-tts's own output (.mp3 + .wordboundaries.json) - this script.
    2. PowerPoint's export timing (where each slide's audio really lands in
       the final .mp4) - see scripts/verify_slide_timing.py.
    3. This project's own SRT-composition math (does the generated .srt
       actually match where words are spoken in the real .mp4) - see
       scripts/verify_srt_accuracy.py.

This script only touches stage 1: it never looks at the exported video at
all. It checks, for every narrated slide in the manifest:

- Does the .wordboundaries.json's last event (offset_seconds +
  duration_seconds) line up with the .mp3's own measured duration? A large
  gap here would mean edge-tts's reported WordBoundary timings don't
  actually describe the .mp3 file it also produced - which would make
  *everything* downstream (predictive timeline, true-start anchor,
  intra-slide scaling) unreliable from the very first step, regardless of
  what PowerPoint's export does.
- Are the WordBoundary events themselves monotonically increasing and
  non-overlapping (sanity check - a corrupt/truncated capture could produce
  out-of-order or overlapping events that would silently produce garbled
  subtitles later).

If this script reports everything within a small tolerance (a few tens of
ms - inherent to WordBoundary event granularity, not a bug), stage 1 is
clean and the remaining drift must come from stage 2 and/or 3.

Usage:
    python scripts/verify_tts_alignment.py output/audio/manifest.json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydub import AudioSegment

# A gap beyond this between the last WordBoundary event's end and the
# .mp3's own measured duration is flagged - edge-tts's own trailing
# silence/fade can plausibly account for up to roughly this much on its own.
DRIFT_WARNING_THRESHOLD_SECONDS = 0.3


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("manifest_path", type=Path)
    parser.add_argument("--audio-dir", type=Path, default=None)
    args = parser.parse_args()

    manifest = json.loads(args.manifest_path.read_text(encoding="utf-8"))
    audio_dir = args.audio_dir or Path(manifest.get("output_dir") or args.manifest_path.parent)

    entries = sorted(manifest.get("slides", []), key=lambda e: int(e["slide_num"]))

    print(f"{'slide':>5} {'mp3 duration':>13} {'last WB end':>13} {'gap':>8} {'events':>7}")

    max_abs_gap = 0.0
    worst_slide = None
    problems = []

    for entry in entries:
        slide_num = int(entry["slide_num"])
        audio_file = entry.get("audio_file")
        wb_file = entry.get("word_boundaries_file")

        if not audio_file:
            continue

        audio_path = audio_dir / audio_file
        if not audio_path.exists():
            problems.append(f"slide {slide_num}: audio file not found ({audio_path}); skipped.")
            continue

        try:
            mp3_duration = AudioSegment.from_file(audio_path).duration_seconds
        except Exception as exc:  # noqa: BLE001
            problems.append(f"slide {slide_num}: could not decode {audio_path} ({exc}); skipped.")
            continue

        if not wb_file:
            print(f"{slide_num:>5} {mp3_duration:>12.3f}s   (no word_boundaries_file)")
            continue

        wb_path = audio_dir / wb_file
        try:
            events = json.loads(wb_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"slide {slide_num}: could not read {wb_path} ({exc}); skipped.")
            continue

        if not events:
            print(f"{slide_num:>5} {mp3_duration:>12.3f}s   (no WordBoundary events)")
            continue

        # Monotonicity / overlap sanity check.
        prev_end = 0.0
        for idx, ev in enumerate(events):
            start = ev["offset_seconds"]
            end = start + ev["duration_seconds"]
            if start < prev_end - 0.01:  # small tolerance for float noise
                problems.append(
                    f"slide {slide_num}: WordBoundary event {idx} ({ev.get('text', '')!r}) "
                    f"starts at {start:.3f}s, before the previous event ended "
                    f"at {prev_end:.3f}s - events are not in order."
                )
            prev_end = max(prev_end, end)

        last_end = events[-1]["offset_seconds"] + events[-1]["duration_seconds"]
        gap = mp3_duration - last_end
        max_abs_gap = max(max_abs_gap, abs(gap)) if abs(gap) > abs(max_abs_gap) else max_abs_gap
        if abs(gap) == max_abs_gap:
            worst_slide = slide_num

        flag = "  <-- check this one" if abs(gap) > DRIFT_WARNING_THRESHOLD_SECONDS else ""
        print(f"{slide_num:>5} {mp3_duration:>12.3f}s {last_end:>12.3f}s {gap:>+7.3f}s {len(events):>7}{flag}")

    if problems:
        print("\nProblems:")
        for p in problems:
            print(f"  WARNING: {p}")

    print(f"\nLargest |mp3_duration - last_word_boundary_end| observed: {max_abs_gap:.3f}s"
          + (f" (slide {worst_slide})" if worst_slide is not None else ""))
    if max_abs_gap > DRIFT_WARNING_THRESHOLD_SECONDS:
        print(
            "WARNING: at least one slide's WordBoundary data doesn't line up "
            "with its own .mp3's measured duration by more than "
            f"{DRIFT_WARNING_THRESHOLD_SECONDS}s. This would affect "
            "everything downstream, independent of PowerPoint's export - "
            "worth investigating before looking at stage 2/3."
        )
    else:
        print(
            "Stage 1 (edge-tts's own .mp3 + .wordboundaries.json) looks "
            "internally consistent - the remaining drift is very unlikely "
            "to originate here. Move on to scripts/verify_slide_timing.py "
            "(stage 2) and scripts/verify_srt_accuracy.py (stage 3)."
        )


if __name__ == "__main__":
    main()
