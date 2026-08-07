"""Write an AI-preprocessed speaker-notes text file into a copy of
``slides.json``'s ``subtitle_text`` field for one slide, without touching
``notes`` (what was actually sent to edge-tts) or the original .pptx.

Why this exists: an AI chatbot's reply is plain multi-line text - real
newlines, not a JSON string with escaped ``\\n`` sequences. Pasting that
directly into a hand-edited JSON file produces invalid JSON (JSON requires
literal newlines inside a string value to be escaped as ``\\n``), and
getting this wrong is an easy, silent way to end up with a slides.json that
fails to parse - or worse, one that "works" because a JSON-aware editor
quietly reformatted it in a way that also changed something else. This
script does the encoding correctly by construction (it reads the raw text
file and writes it out through Python's own ``json.dump()``, which escapes
newlines/quotes/backslashes correctly), so there's no manual escaping step
to get wrong.

This only overwrites the ``subtitle_text`` field for one slide_num - every
other field, and every other slide, passes through unchanged. See
scripts/verify_notes_preprocessing.py's module docstring for why
``subtitle_text`` (not ``notes``) is the field to use for this, and run it
against the original vs. AI-processed text *before* this script - this
script does not itself check content fidelity, it only performs the write.

Usage (apply to one slide, writing a new file so the original is
untouched):
    python scripts/apply_subtitle_text.py \\
        --slides-json output/slides.json \\
        --slide 1 \\
        --subtitle-text-file note_aichatbot.txt \\
        --output output/slides_ai_processed.json

To process more than one slide, chain invocations - point --slides-json at
the previous step's --output so each call builds on the last:
    python scripts/apply_subtitle_text.py \\
        --slides-json output/slides_ai_processed.json \\
        --slide 2 \\
        --subtitle-text-file note_aichatbot_slide2.txt \\
        --output output/slides_ai_processed.json
(safe to use the same path for --slides-json and --output - the input is
fully read into memory before anything is written)

--subtitle-text-file is read as-is (its exact bytes, decoded as UTF-8) -
whatever line breaks/whitespace/trailing newline the file has is exactly
what ends up in subtitle_text. If you copy-pasted a chatbot reply into a
.txt file yourself, check there isn't a stray trailing blank line or extra
whitespace your editor added, since that becomes part of the deck's actual
subtitle content.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.logging_config import ensure_utf8_console


def main() -> int:
    ensure_utf8_console()

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slides-json", required=True, type=Path, help="現有的 slides.json（或前一步驟已處理過的版本）路徑")
    parser.add_argument("--slide", required=True, type=int, help="要覆寫 subtitle_text 的 slide_num")
    parser.add_argument("--subtitle-text-file", required=True, type=Path, help="AI 處理過的字幕文字檔（純文字，UTF-8，可以直接包含真正的換行）")
    parser.add_argument("--output", required=True, type=Path, help="輸出路徑（可以跟 --slides-json 相同，輸入會先完整讀進記憶體再寫檔）")
    args = parser.parse_args()

    payload = json.loads(args.slides_json.read_text(encoding="utf-8"))
    slides = payload.get("slides", payload) if isinstance(payload, dict) else payload

    matched = [s for s in slides if int(s.get("slide_num", -1)) == args.slide]
    if not matched:
        available = sorted(int(s.get("slide_num", -1)) for s in slides)
        print(f"錯誤：{args.slides_json} 裡找不到 slide_num={args.slide}（現有的 slide_num：{available}）", file=sys.stderr)
        return 1

    new_text = args.subtitle_text_file.read_text(encoding="utf-8")
    for slide in matched:
        slide["subtitle_text"] = new_text

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"已將 {args.subtitle_text_file} 的內容寫入 slide {args.slide} 的 subtitle_text，輸出至 {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
