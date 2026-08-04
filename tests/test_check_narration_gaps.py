"""Tests for scripts/check_narration_gaps.py - the standalone,
no-network-call re-check of already-generated audio for the
dropped-narration heuristic (see CHANGELOG's "未發布" entry and
src/subtitle_alignment.py's find_suspected_dropped_narration docstring for
the real slide-9 case this exists to catch retroactively).
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location(
    "check_narration_gaps", ROOT / "scripts" / "check_narration_gaps.py"
)
check_narration_gaps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_narration_gaps)


class ParseSlideSelectorTests(unittest.TestCase):
    def test_single_numbers(self):
        self.assertEqual(check_narration_gaps.parse_slide_selector("6,9"), {6, 9})

    def test_range(self):
        self.assertEqual(check_narration_gaps.parse_slide_selector("6,8-10"), {6, 8, 9, 10})

    def test_rejects_empty(self):
        with self.assertRaises(Exception):
            check_narration_gaps.parse_slide_selector("")

    def test_rejects_backwards_range(self):
        with self.assertRaises(Exception):
            check_narration_gaps.parse_slide_selector("10-8")


class CheckNarrationGapsEndToEndTests(unittest.TestCase):
    """Builds a manifest.json + wordboundaries.json + slides.json on disk
    shaped like real --generate-audio output (an older run, predating this
    feature, so the manifest entries deliberately do NOT have
    narration_gap_warnings already populated) and runs the script against
    them as a subprocess, the same way a user would from the command line.
    """

    def _write_fixture(self, tmp_path, notes, word_boundaries, slide_num=1):
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()
        wb_path = audio_dir / f"slide_{slide_num:03d}.wordboundaries.json"
        wb_path.write_text(json.dumps(word_boundaries, ensure_ascii=False), encoding="utf-8")

        manifest = {
            "output_dir": str(audio_dir),
            "slides": [{
                "slide_num": slide_num,
                "title": "Slide",
                "audio_file": f"slide_{slide_num:03d}.mp3",
                "word_boundaries_file": wb_path.name,
                # Deliberately no "narration_gap_warnings" key - simulating
                # a manifest.json written before this feature existed.
            }],
        }
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

        slides = [{"slide_num": slide_num, "notes": notes}]
        slides_json_path = tmp_path / "slides.json"
        slides_json_path.write_text(json.dumps(slides, ensure_ascii=False), encoding="utf-8")

        return manifest_path, slides_json_path

    def _run(self, args):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_narration_gaps.py")] + args,
            capture_output=True, text=True,
        )

    def test_detects_real_shaped_drop_and_exits_1(self):
        # Same gap shape as the real slide-9 case: two matched events with a
        # large chunk of un-vocalized text between them and almost no
        # elapsed audio time to cover it.
        notes = "第一段話。" + ("因此中間這一大段完全沒有被念出來的文字內容需要超過十五個字才會被判定為疑似漏講" ) + "今天大家先建立概念即可。"
        word_boundaries = [
            {"text": "第一段話", "offset_seconds": 0.0, "duration_seconds": 1.0},
            {"text": "今天", "offset_seconds": 1.05, "duration_seconds": 0.3},
            {"text": "大家先建立概念即可", "offset_seconds": 1.4, "duration_seconds": 2.5},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            manifest_path, slides_json_path = self._write_fixture(tmp_path, notes, word_boundaries)

            result = self._run([
                "--manifest", str(manifest_path),
                "--slides-json", str(slides_json_path),
            ])

            self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)
            self.assertIn("POSSIBLE DROPPED NARRATION", result.stdout)
            self.assertIn("slide 1", result.stdout)

    def test_steady_pace_reports_ok_and_exits_0(self):
        notes = "第一段話。第二段話。第三段話。"
        word_boundaries = [
            {"text": "第一段話", "offset_seconds": 0.0, "duration_seconds": 1.0},
            {"text": "第二段話", "offset_seconds": 1.2, "duration_seconds": 1.0},
            {"text": "第三段話", "offset_seconds": 2.4, "duration_seconds": 1.0},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            manifest_path, slides_json_path = self._write_fixture(tmp_path, notes, word_boundaries)

            result = self._run([
                "--manifest", str(manifest_path),
                "--slides-json", str(slides_json_path),
            ])

            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertNotIn("POSSIBLE DROPPED NARRATION", result.stdout)
            self.assertIn("OK", result.stdout)

    def test_slides_filter_skips_unselected_slides(self):
        notes = "第一段話。第二段話。"
        word_boundaries = [
            {"text": "第一段話", "offset_seconds": 0.0, "duration_seconds": 1.0},
            {"text": "第二段話", "offset_seconds": 1.2, "duration_seconds": 1.0},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            manifest_path, slides_json_path = self._write_fixture(tmp_path, notes, word_boundaries, slide_num=5)

            result = self._run([
                "--manifest", str(manifest_path),
                "--slides-json", str(slides_json_path),
                "--slides", "9",
            ])

            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("Checked 0 slide(s)", result.stdout)


if __name__ == "__main__":
    unittest.main()
