"""Manual smoke test for src.tts.synthesize_with_word_boundaries().

This is NOT part of the automated test suite (tests/test_tts_word_boundaries.py
already covers the function's logic with fake edge-tts responses). This
script exists because that logic has never been exercised against a real
edge-tts network call - the sandbox this project was developed in cannot
reach edge-tts's servers (SSL/network restrictions), so this needs to run
on a real machine with real network access.

What to look for when you run this:

1. Does it run at all without raising (confirms your installed edge-tts
   version is compatible - either >=7.2.0 using boundary="WordBoundary"
   directly, or an older version falling back correctly)?
2. Print your installed edge-tts version (this script does it for you) -
   worth checking against what actually got exercised.
3. Look at the printed word boundary events: what's the granularity? Is it
   one event per Chinese character, per word/phrase, or something else?
   This directly affects how Phase 2 (segmentation) and Phase 3 (alignment)
   should be designed.
4. Do the offset_seconds/duration_seconds values look sane (increasing,
   roughly matching how long the text takes to speak, no huge gaps or
   overlaps)?
5. Open test_output.mp3 and listen - does it sound normal (this confirms
   the audio-writing path wasn't broken by the streaming rewrite)?

Usage:
    python scripts/smoke_test_word_boundaries.py
    python scripts/smoke_test_word_boundaries.py "自訂的測試文字"
    python scripts/smoke_test_word_boundaries.py --file path/to/notes.txt

scripts/sample_notes_for_smoke_test.txt is a fixed, more elaborate sample
(multiple paragraphs, mixed Chinese/English/numbers, a wide range of
punctuation: ，。？！；：「」（）——、"") kept alongside this script
specifically so re-runs after future changes (segmentation logic changes,
an edge-tts library upgrade, etc.) can be compared against the same input
instead of a freshly-improvised one each time:

    python scripts/smoke_test_word_boundaries.py --file scripts/sample_notes_for_smoke_test.txt
"""

import sys
from pathlib import Path

import edge_tts

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tts import synthesize_with_word_boundaries
from src.logging_config import ensure_utf8_console

DEFAULT_TEXT = (
    "這是一段測試文字，用來確認word boundary的顆粒度。\n"
    "第二段，確認換行是否會影響時間戳記的連續性。"
)


def _read_text_from_args(argv):
    """Returns the text to synthesize: --file <path> reads the whole file
    (so multi-paragraph text with real newlines can be passed without
    fighting shell quoting), a plain positional arg is used as-is, and no
    args at all falls back to DEFAULT_TEXT.
    """
    if not argv:
        return DEFAULT_TEXT
    if argv[0] == "--file":
        if len(argv) < 2:
            raise SystemExit("Usage: --file <path>")
        return Path(argv[1]).read_text(encoding="utf-8")
    return argv[0]


def main():
    # Reconfigure stdout/stderr to UTF-8 before any print() - Windows can
    # otherwise crash printing CJK slide text when stdout/stderr is piped
    # rather than an interactive console (see ensure_utf8_console()'s
    # docstring for the confirmed real-world crash this fixes).
    ensure_utf8_console()

    text = _read_text_from_args(sys.argv[1:])
    output_path = Path(__file__).resolve().parent / "smoke_test_output.mp3"

    print(f"edge-tts version: {getattr(edge_tts, '__version__', 'unknown')}")
    print(f"Input text:\n{text}\n")
    print(f"Output audio: {output_path}\n")

    events = synthesize_with_word_boundaries(
        text,
        output_path,
        voice="zh-TW-YunJheNeural",
    )

    print(f"Got {len(events)} WordBoundary event(s):\n")
    for e in events:
        print(
            f"  [{e['offset_seconds']:6.2f}s +{e['duration_seconds']:5.2f}s] "
            f"{e['text']!r}"
        )

    if not events:
        print("\nWARNING: no WordBoundary events were returned at all - "
              "check the edge-tts version / boundary support.")


if __name__ == "__main__":
    main()
