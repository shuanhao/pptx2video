"""Tests for scripts/apply_subtitle_text.py - writing an AI-preprocessed
speaker-notes text file into a slides.json copy's ``subtitle_text`` field
without needing the caller to hand-escape newlines into valid JSON (see the
script's own module docstring for why that matters).
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "apply_subtitle_text.py"


def _run(args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


class ApplySubtitleTextTests(unittest.TestCase):
    def test_overwrites_subtitle_text_for_matching_slide_and_preserves_others(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            slides_json = tmp_path / "slides.json"
            slides_json.write_text(
                json.dumps({
                    "slides": [
                        {"slide_num": 1, "title": "A", "notes": "早安", "subtitle_text": "早安"},
                        {"slide_num": 2, "title": "B", "notes": "午安", "subtitle_text": "午安"},
                    ]
                }, ensure_ascii=False),
                encoding="utf-8",
            )

            # A real multi-line file, exactly what a chatbot reply pasted
            # into a text editor looks like - actual newlines, not "\n".
            text_file = tmp_path / "note_aichatbot.txt"
            text_file.write_text("早，\n安。\n", encoding="utf-8")

            output = tmp_path / "slides_ai_processed.json"
            result = _run([
                "--slides-json", str(slides_json),
                "--slide", "1",
                "--subtitle-text-file", str(text_file),
                "--output", str(output),
            ])

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            slide_1 = next(s for s in payload["slides"] if s["slide_num"] == 1)
            slide_2 = next(s for s in payload["slides"] if s["slide_num"] == 2)

            # subtitle_text was overwritten with the real newlines intact -
            # a bare copy-paste of a multi-line chatbot reply into a JSON
            # string field (without going through json.dump()) would either
            # produce invalid JSON or silently mangle the newlines; this
            # confirms the round trip preserves them correctly.
            self.assertEqual(slide_1["subtitle_text"], "早，\n安。\n")
            # notes (what was actually sent to edge-tts) is untouched.
            self.assertEqual(slide_1["notes"], "早安")
            # The other slide is completely unaffected.
            self.assertEqual(slide_2["subtitle_text"], "午安")
            self.assertEqual(slide_2["notes"], "午安")

            # The written file must itself be valid, re-parseable JSON -
            # this is the actual bug class this script exists to prevent.
            json.loads(output.read_text(encoding="utf-8"))

    def test_missing_slide_num_fails_loudly_instead_of_silently_doing_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            slides_json = tmp_path / "slides.json"
            slides_json.write_text(
                json.dumps({"slides": [{"slide_num": 1, "title": "A", "notes": "早安"}]}),
                encoding="utf-8",
            )
            text_file = tmp_path / "note.txt"
            text_file.write_text("早安", encoding="utf-8")
            output = tmp_path / "out.json"

            result = _run([
                "--slides-json", str(slides_json),
                "--slide", "99",
                "--subtitle-text-file", str(text_file),
                "--output", str(output),
            ])

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("找不到", result.stderr)
            self.assertFalse(output.exists())

    def test_can_chain_multiple_slides_using_same_path_for_input_and_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            slides_json = tmp_path / "slides.json"
            slides_json.write_text(
                json.dumps({
                    "slides": [
                        {"slide_num": 1, "title": "A", "notes": "早安", "subtitle_text": "早安"},
                        {"slide_num": 2, "title": "B", "notes": "午安", "subtitle_text": "午安"},
                    ]
                }, ensure_ascii=False),
                encoding="utf-8",
            )
            text_file_1 = tmp_path / "note1.txt"
            text_file_1.write_text("早，安。", encoding="utf-8")
            text_file_2 = tmp_path / "note2.txt"
            text_file_2.write_text("午，安。", encoding="utf-8")

            result_1 = _run([
                "--slides-json", str(slides_json),
                "--slide", "1",
                "--subtitle-text-file", str(text_file_1),
                "--output", str(slides_json),
            ])
            self.assertEqual(result_1.returncode, 0, result_1.stderr)

            result_2 = _run([
                "--slides-json", str(slides_json),
                "--slide", "2",
                "--subtitle-text-file", str(text_file_2),
                "--output", str(slides_json),
            ])
            self.assertEqual(result_2.returncode, 0, result_2.stderr)

            payload = json.loads(slides_json.read_text(encoding="utf-8"))
            slide_1 = next(s for s in payload["slides"] if s["slide_num"] == 1)
            slide_2 = next(s for s in payload["slides"] if s["slide_num"] == 2)
            self.assertEqual(slide_1["subtitle_text"], "早，安。")
            self.assertEqual(slide_2["subtitle_text"], "午，安。")


if __name__ == "__main__":
    unittest.main()
