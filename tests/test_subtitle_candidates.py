import copy
import json
import tempfile
import unittest
import shutil
import subprocess
import sys
import wave
from pathlib import Path
from unittest.mock import patch

from src.subtitle_candidates import SubtitleCandidateRun, candidate_paths
from src.subtitle_pipeline import SubtitleTimingError


class SubtitleCandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plan = [
            {"slide_num": 1, "has_narration": True, "duration_seconds": 14.,
             "captions": [{"text": "one", "start_seconds": 1., "end_seconds": 2.}]},
            {"slide_num": 2, "has_narration": False, "duration_seconds": 5., "captions": []},
            {"slide_num": 3, "has_narration": True, "duration_seconds": 10.,
             "captions": [{"text": "three", "start_seconds": 1., "end_seconds": 2.}]},
        ]
        self.records = {n: {"slide_num": n, "status": status, "reason": "test", "start_seconds": start,
            "scale": 1., "end_seconds": start + duration, "head": None, "tail": None,
            "global_scale_correction": 1.} for n, status, start, duration in
            ((1, "matched", 2., 14.), (2, "silent", 16., 5.), (3, "predicted", 19., 10.))}
        self.payload = {"slides": [{"slide_num": n} for n in (1, 2, 3)], "audio": {"slides": []}}

    def run_object(self, coefficient=1.):
        return SubtitleCandidateRun(self.payload, self.root / "lesson.srt", self.root / "video.mp4", self.root,
                                    global_scale_correction=coefficient)

    def finish(self, run, duration=40., legacy=False):
        def locate(*args, **kwargs):
            self.assertEqual(kwargs["global_scale_correction"], 1.)
            if not legacy:
                kwargs["diagnostics"].update(copy.deepcopy(self.records))
            return {1: (2., 16.)}, ["review slide 3"]
        with patch("src.subtitle_candidates._video_duration", return_value=duration), \
             patch("src.subtitle_candidates.locate_slide_start_and_end_times", side_effect=locate) as locator:
            result = run.finish()
            locator.assert_called_once()
        return result

    def test_names_three_versions_one_plan_one_localization_and_report(self):
        run = self.run_object()
        with patch("src.subtitle_candidates.build_caption_plan", return_value=(self.plan, [])) as builder:
            run.preview()
            preview = run.paths["preview"].read_bytes()
            self.finish(run)
            builder.assert_called_once()
        self.assertIn(b"00:00:20,000 --> 00:00:21,000", preview)  # media padding + blank page
        self.assertEqual(run.paths["preview"].read_bytes(), preview)
        self.assertEqual(run.paths["initial"].read_bytes(), run.paths["captions"].read_bytes())
        self.assertIn("00:00:03,000 --> 00:00:04,000", run.paths["initial"].read_text())
        report = json.loads(run.paths["report"].read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "awaiting_manual_review")
        self.assertEqual(report["summary"]["predicted"], [3])
        self.assertEqual(report["slides"]["3"]["caption_count"], 1)
        for name in ("preview", "initial", "captions"):
            self.assertEqual(report["artifacts"][name]["status"], "ready")
            self.assertEqual(report["artifacts"][name]["run_id"], report["run_id"])
        self.assertEqual(run.paths["report"].name, "lesson_alignment_report.json")

    def test_correction_once_and_raw_records_unchanged(self):
        run = self.run_object(1.1)
        with patch("src.subtitle_candidates.build_caption_plan", return_value=(self.plan, [])):
            self.finish(run)
        self.assertIn("00:00:03,300 --> 00:00:04,400", run.paths["captions"].read_text())
        self.assertIn("00:00:22,000 --> 00:00:23,100", run.paths["captions"].read_text())
        self.assertEqual(run.report["slides"][1]["start_seconds"], 2.)

    def test_invalid_corrected_version_retains_old_file_and_valid_initial(self):
        run = self.run_object(3.)
        run.paths["captions"].write_text("old candidate")
        with patch("src.subtitle_candidates.build_caption_plan", return_value=(self.plan, [])):
            with self.assertRaises(SubtitleTimingError):
                self.finish(run, duration=30.)
        self.assertTrue(run.paths["initial"].exists())
        self.assertEqual(run.paths["captions"].read_text(), "old candidate")
        self.assertEqual(run.report["artifacts"]["captions"]["status"], "failed")
        self.assertEqual(run.report["status"], "partial_failure")

    def test_invalid_initial_does_not_discard_valid_corrected(self):
        self.plan[2]["captions"][0].update(start_seconds=11., end_seconds=12.)
        run = self.run_object(.9)
        with patch("src.subtitle_candidates.build_caption_plan", return_value=(self.plan, [])):
            with self.assertRaises(SubtitleTimingError):
                self.finish(run, duration=30.)
        self.assertFalse(run.paths["initial"].exists())
        self.assertTrue(run.paths["captions"].exists())

    def test_localization_failure_keeps_preview_and_marks_stale_files(self):
        paths = candidate_paths(self.root / "lesson.srt")
        paths["initial"].write_text("old initial")
        paths["captions"].write_text("old corrected")
        run = self.run_object()
        with patch("src.subtitle_candidates.build_caption_plan", return_value=(self.plan, [])):
            run.preview()
        with patch("src.subtitle_candidates._video_duration", return_value=40.), \
             patch("src.subtitle_candidates.locate_slide_start_and_end_times", side_effect=RuntimeError("decode failed")):
            with self.assertRaises(SubtitleTimingError):
                run.finish()
        self.assertEqual(paths["initial"].read_text(), "old initial")
        self.assertEqual(paths["captions"].read_text(), "old corrected")
        self.assertEqual(run.report["artifacts"]["preview"]["status"], "ready")
        self.assertTrue(run.report["artifacts"]["initial"]["existing_before_run"])
        self.assertEqual(run.report["artifacts"]["initial"]["status"], "not_generated")

    def test_source_change_after_preview_prevents_mixed_run(self):
        audio = self.root / "source.mp3"
        audio.write_bytes(b"original")
        self.payload["audio"]["slides"] = [{"slide_num": 1, "audio_file": "source.mp3"}]
        run = self.run_object()
        with patch("src.subtitle_candidates.build_caption_plan", return_value=(self.plan, [])):
            run.preview()
        audio.write_bytes(b"changed")
        with patch("src.subtitle_candidates._video_duration", return_value=40.), \
             patch("src.subtitle_candidates.locate_slide_start_and_end_times") as locate:
            with self.assertRaisesRegex(SubtitleTimingError, "source changed"):
                run.finish()
        locate.assert_not_called()

    def test_original_audio_still_gets_three_candidates_with_legacy_label(self):
        run = self.run_object()
        with patch("src.subtitle_candidates.build_caption_plan", return_value=(self.plan, [])):
            self.finish(run, legacy=True)
        self.assertEqual(run.report["slides"][1]["status"], "legacy_measured")
        self.assertEqual(run.report["slides"][3]["status"], "predicted")

    def test_atomic_commit_failure_keeps_old_candidate(self):
        run = self.run_object()
        run.paths["initial"].write_text("old")
        import os
        replace = os.replace

        def fail_initial(source, target):
            if Path(target) == run.paths["initial"]:
                raise OSError("disk failure")
            return replace(source, target)

        with patch("src.subtitle_candidates.build_caption_plan", return_value=(self.plan, [])), \
             patch("src.subtitle_candidates.os.replace", side_effect=fail_initial):
            with self.assertRaises(SubtitleTimingError):
                self.finish(run)
        self.assertEqual(run.paths["initial"].read_text(), "old")
        self.assertTrue(run.paths["captions"].exists())
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "Requires real media tools")
    def test_rebuild_cli_real_media_and_word_boundaries(self):
        import numpy as np
        rate = 24000
        audio = np.concatenate((np.random.default_rng(4).normal(0, 2000, 2 * rate), np.zeros(rate))).astype(np.int16)
        full = np.concatenate((np.zeros(int(.4 * rate), dtype=np.int16), audio))
        for name, samples in (("audio.wav", audio), ("full.wav", full)):
            with wave.open(str(self.root / name), "wb") as wav:
                wav.setparams((1, 2, rate, 0, "NONE", "not compressed"))
                wav.writeframes(samples.tobytes())
        video = self.root / "video.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(self.root / "full.wav"),
                        "-c:a", "aac", str(video)], check=True, capture_output=True)
        (self.root / "words.json").write_text(json.dumps([
            {"text": "Hello", "offset_seconds": .2, "duration_seconds": .3}]), encoding="utf-8")
        manifest = {"output_dir": str(self.root), "slides": [{"slide_num": 1,
            "audio_file": "audio.wav", "word_boundaries_file": "words.json", "preparation": {
                "source_probe": {"duration_seconds": 2}, "fingerprint": {"settings": {"tail_silence": 1}}}}]}
        (self.root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (self.root / "slides.json").write_text(json.dumps({"slides": [{"slide_num": 1, "notes": "Hello"}]}), encoding="utf-8")
        result = subprocess.run([sys.executable, "scripts/regenerate_srt_from_export.py", "--video", str(video),
            "--manifest", str(self.root / "manifest.json"), "--slides-json", str(self.root / "slides.json"),
            "--output", str(self.root / "lesson.srt"), "--search-window-seconds", "5"],
            capture_output=True, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        paths = candidate_paths(self.root / "lesson.srt")
        self.assertEqual(paths["initial"].read_bytes(), paths["captions"].read_bytes())
        self.assertNotEqual(paths["preview"].read_bytes(), paths["initial"].read_bytes())
        report = json.loads(paths["report"].read_text(encoding="utf-8"))
        self.assertEqual(report["search_window_seconds"], 5)
        self.assertEqual(report["slides"]["1"]["status"], "head_only")
        self.assertAlmostEqual(report["slides"]["1"]["start_seconds"], .4, delta=.03)


if __name__ == "__main__":
    unittest.main()
