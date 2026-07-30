"""Manual smoke test for the full Phase 1 -> Phase 2 -> Phase 3 SRT chain:
src.tts.synthesize_with_word_boundaries -> src.subtitle_segmenter.segment_notes_for_subtitles
-> src.subtitle_alignment.align_segments_with_word_boundaries -> src.subtitle_alignment.format_srt.

This is NOT part of the automated test suite (tests/test_subtitle_alignment.py
already covers the alignment logic itself with fabricated WordBoundary data).
This script exists because the alignment matching logic
(``_find_boundary_span`` in src/subtitle_alignment.py) has never been
exercised against *real* edge-tts WordBoundary events - the sandbox this was
developed in cannot reach edge-tts's servers - so it needs to run on a real
machine with real network access, the same way
scripts/smoke_test_word_boundaries.py did for Phase 1.

What to look for when you run this:

1. Does it run without raising, and does the "warnings" section at the end
   stay empty? Any warning printed there means either a WordBoundary event
   couldn't be matched back to the source text, or a subtitle line had no
   matched events at all and its timing was guessed - both worth looking at
   closely, since they mean the alignment logic hit a real-world case its
   design didn't anticipate.
2. Do the printed start/end times for each subtitle line look right relative
   to each other (increasing, no overlaps, no suspiciously huge gaps)?
3. Open smoke_test_alignment_output.mp3 and read along with
   smoke_test_alignment_output.srt (load it into a media player that
   supports external subtitles, e.g. VLC) - does each line appear/disappear
   roughly when it's actually being spoken?
4. Check the .srt file's raw text too - correct sequential numbering,
   correct HH:MM:SS,mmm timestamp format, blank line between cues.

Usage:
    python scripts/smoke_test_alignment.py
    python scripts/smoke_test_alignment.py "自訂的測試文字"
    python scripts/smoke_test_alignment.py --file path/to/notes.txt

scripts/sample_notes_for_smoke_test.txt (from Phase 1) works here too:
    python scripts/smoke_test_alignment.py --file scripts/sample_notes_for_smoke_test.txt
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.subtitle_alignment import align_segments_with_word_boundaries, format_srt
from src.subtitle_segmenter import segment_notes_for_subtitles
from src.tts import synthesize_with_word_boundaries

DEFAULT_TEXT = (
    "這是一段測試文字，用來確認字幕的斷句與時間軸對齊是否正確。\n"
    "第二段，確認換行（段落邊界）前後的字幕時間銜接是否自然。"
)


def _read_text_from_args(argv):
    """Same convention as scripts/smoke_test_word_boundaries.py: --file
    <path> reads the whole file, a plain positional arg is used as-is, no
    args falls back to DEFAULT_TEXT.
    """
    if not argv:
        return DEFAULT_TEXT
    if argv[0] == "--file":
        if len(argv) < 2:
            raise SystemExit("Usage: --file <path>")
        return Path(argv[1]).read_text(encoding="utf-8")
    return argv[0]


def main():
    text = _read_text_from_args(sys.argv[1:])
    output_dir = Path(__file__).resolve().parent
    audio_path = output_dir / "smoke_test_alignment_output.mp3"
    srt_path = output_dir / "smoke_test_alignment_output.srt"

    print(f"Input text:\n{text}\n")

    segments = segment_notes_for_subtitles(text)
    print(f"Phase 2: segmented into {len(segments)} subtitle line(s):")
    for i, seg in enumerate(segments):
        print(f"  [{i}] ({seg['source_start_offset']:3d}-{seg['source_end_offset']:3d}) {seg['text']!r}")
    print()

    print(f"Phase 1: synthesizing via edge-tts -> {audio_path}")
    word_boundaries = synthesize_with_word_boundaries(
        text,
        audio_path,
        voice="zh-TW-YunJheNeural",
    )
    print(f"Got {len(word_boundaries)} WordBoundary event(s).\n")

    aligned, warnings = align_segments_with_word_boundaries(text, segments, word_boundaries)

    print("Phase 3: aligned subtitle lines:")
    for i, entry in enumerate(aligned):
        print(
            f"  [{i}] {entry['start_seconds']:6.2f}s -> {entry['end_seconds']:6.2f}s "
            f"  {entry['text']!r}"
        )
    print()

    srt_text = format_srt(aligned)
    srt_path.write_text(srt_text, encoding="utf-8")
    print(f"Wrote SRT file: {srt_path}\n")
    print("--- SRT content ---")
    print(srt_text)
    print("-------------------\n")

    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("No warnings - every WordBoundary event and every subtitle line matched cleanly.")


if __name__ == "__main__":
    main()
