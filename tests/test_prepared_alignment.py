import unittest
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from unittest.mock import patch

import numpy as np
from scipy.signal import resample_poly

from src.audio_position_locator import SAMPLE_RATE as SR, locate_slide_alignments, locate_slide_start_and_end_times
from src.subtitle_pipeline import generate_srt_from_true_starts, SubtitleTimingError


def noise(seconds, seed=1):
    return np.random.default_rng(seed).normal(0, 2000, int(seconds * SR)).astype(np.float32)


def entry(number, original, tail):
    return {"slide_num": number, "audio_file": f"{number}.wav", "preparation": {
        "source_probe": {"duration_seconds": original},
        "fingerprint": {"settings": {"tail_silence": tail}}}}


def locate(clips, full, entries, **kwargs):
    def load(path):
        return full if Path(path).name == "full.wav" else clips[int(Path(path).stem)]
    with patch("src.audio_position_locator._extract_audio_track"), \
         patch("src.audio_position_locator._load_mono_array", side_effect=load):
        return locate_slide_alignments("video.mp4", [{"slide_num": n} for n in clips],
                                       {"slides": entries}, ".", **kwargs)


class PreparedAnchorTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ffmpeg"), "Requires ffmpeg")
    def test_real_aac_prepared_and_export_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Nonperiodic voiced-like signal, encoded twice as in preparation/export.
            speech = noise(20)
            source = np.concatenate((speech, np.zeros(10 * SR)))
            full = np.concatenate((np.zeros(SR), source))
            for name, samples in (("source", source), ("export", full)):
                with wave.open(str(root / f"{name}.wav"), "wb") as wav:
                    wav.setparams((1, 2, SR, 0, "NONE", "not compressed"))
                    wav.writeframes(samples.astype(np.int16).tobytes())
            for source_name, target in (("source.wav", "1.m4a"), ("export.wav", "video.mp4")):
                subprocess.run(["ffmpeg", "-v", "error", "-i", str(root / source_name),
                                "-ar", "24000", "-c:a", "aac", "-b:a", "64k", str(root / target)],
                               check=True, capture_output=True)
            metadata = entry(1, 20, 10)
            metadata["audio_file"] = "1.m4a"
            records, warnings = locate_slide_alignments(root / "video.mp4", [{"slide_num": 1}],
                                                        {"slides": [metadata]}, root)
            self.assertEqual(warnings, [])
            self.assertEqual(records[1]["status"], "matched")
            self.assertAlmostEqual(records[1]["start_seconds"], 1, delta=.03)
            self.assertAlmostEqual(records[1]["scale"], 1, delta=.001)

    def test_padding_excluded_and_original_silence_trimmed(self):
        speech = noise(24)
        for tail in (1, 4, 8, 10):
            with self.subTest(tail=tail):
                clip = np.concatenate((speech, np.zeros((3 + tail) * SR)))
                full = np.concatenate((np.zeros(2 * SR), clip))
                records, warnings = locate({1: clip}, full, [entry(1, 27, tail)])
                self.assertEqual(warnings, [])
                r = records[1]
                self.assertEqual(r["status"], "matched")
                self.assertAlmostEqual(r["start_seconds"], 2, places=3)
                self.assertAlmostEqual(r["scale"], 1, places=3)
                self.assertLessEqual(r["tail"]["source_start_seconds"] + r["tail"]["duration_seconds"], 24)
                self.assertAlmostEqual(r["end_seconds"], 2 + 27 + tail, places=3)

    def test_shifted_anchor_recovers_stretch_not_padded_endpoint(self):
        original = noise(30)
        clip = np.concatenate((original, np.zeros(10 * SR)))
        full = np.concatenate((np.zeros(SR), resample_poly(original, 1000, 1001), np.zeros(10 * SR)))
        records, _ = locate({1: clip}, full, [entry(1, 30, 10)])
        self.assertEqual(records[1]["status"], "matched")
        self.assertAlmostEqual(records[1]["scale"], 1000 / 1001, delta=.0002)
        self.assertAlmostEqual(records[1]["start_seconds"], 1, delta=.01)

    def test_short_clip_does_not_invent_independent_tail(self):
        clip = np.concatenate((noise(2), np.zeros(10 * SR)))
        records, warnings = locate({1: clip}, clip, [entry(1, 2, 10)])
        self.assertEqual(records[1]["status"], "head_only")
        self.assertEqual(records[1]["scale"], 1)
        self.assertTrue(warnings)

    def test_silence_and_repeated_phrase_are_not_success(self):
        silent = np.zeros(20 * SR)
        records, _ = locate({1: silent}, silent, [entry(1, 10, 10)])
        self.assertEqual(records[1]["status"], "predicted")
        phrase = noise(2)
        clip = np.concatenate((phrase, np.zeros(4 * SR)))
        full = np.concatenate((phrase, np.zeros(SR), phrase, np.zeros(4 * SR)))
        records, _ = locate({1: clip}, full, [entry(1, 2, 4)])
        self.assertEqual(records[1]["status"], "predicted")
        self.assertEqual(records[1]["head"]["reason"], "ambiguous_match")

    def test_rejected_tail_uses_head_and_later_slide_recovers(self):
        first = np.concatenate((noise(24), np.zeros(4 * SR)))
        second = np.concatenate((noise(24, 2), np.zeros(4 * SR)))
        damaged = first.copy()
        damaged[16 * SR:24 * SR] = noise(8, 9)
        full = np.concatenate((np.zeros(SR), damaged, second))
        records, warnings = locate({1: first, 2: second}, full, [entry(1, 24, 4), entry(2, 24, 4)])
        self.assertEqual(records[1]["status"], "head_only")
        self.assertEqual(records[1]["scale"], 1)
        self.assertEqual(records[2]["status"], "matched")
        self.assertAlmostEqual(records[2]["start_seconds"], 29, places=3)
        self.assertTrue(warnings)

    def test_consecutive_failed_heads_do_not_propagate_and_global_once(self):
        clips = {n: np.concatenate((noise(20, n), np.zeros(4 * SR))) for n in (1, 2, 3)}
        full = np.concatenate((np.zeros(49 * SR), clips[3]))
        records, _ = locate(clips, full, [entry(n, 20, 4) for n in clips], global_scale_correction=1.01)
        self.assertEqual([records[n]["status"] for n in clips], ["predicted", "predicted", "matched"])
        self.assertAlmostEqual(records[2]["start_seconds"], 24 * 1.01)
        self.assertAlmostEqual(records[3]["start_seconds"], 49 * 1.01)
        self.assertAlmostEqual(records[3]["scale"], 1.01)

    def test_metadata_mismatch_falls_back(self):
        clip = noise(24)
        records, warnings = locate({1: clip}, clip, [entry(1, 24, 10)])
        self.assertEqual(records[1]["status"], "predicted")
        self.assertIn("metadata mismatch", warnings[0])

    def test_individually_matching_tail_with_impossible_scale_is_rejected(self):
        speech = noise(24)
        clip = np.concatenate((speech, np.zeros(4 * SR)))
        full = np.concatenate((speech[:16 * SR], np.zeros(2 * SR), speech[16 * SR:], np.zeros(4 * SR)))
        records, warnings = locate({1: clip}, full, [entry(1, 24, 4)])
        self.assertEqual(records[1]["status"], "head_only")
        self.assertEqual(records[1]["scale"], 1)
        self.assertEqual(records[1]["reason"], "invalid_scale_or_order")
        self.assertTrue(warnings)

    def test_compatibility_bounds_keep_mapping_and_exclude_predictions(self):
        records = {1: {"status": "matched", "start_seconds": 2., "end_seconds": 36.},
                   2: {"status": "predicted", "start_seconds": 36., "end_seconds": 50.}}
        diagnostics = {}
        with patch("src.audio_position_locator.locate_slide_alignments", return_value=(records, ["review"])):
            bounds, warnings = locate_slide_start_and_end_times("unused", [], {"preparation": {"schema_version": 1, "kind": "prepared"}}, ".", diagnostics=diagnostics)
        self.assertEqual(bounds, {1: (2., 36.)})
        self.assertEqual(diagnostics, records)


class ExplicitMappingTests(unittest.TestCase):
    def test_fallback_uses_own_scale_not_next_slide_gap(self):
        slides = [{"slide_num": n, "duration_seconds": 20, "captions": [
            {"text": "line", "start_seconds": 1., "end_seconds": 2.}]} for n in (1, 2)]
        records = {n: {"status": "head_only", "reason": "weak_tail", "start_seconds": start,
                       "scale": 1., "video_duration_seconds": 100} for n, start in ((1, 3), (2, 40))}
        with patch("src.subtitle_pipeline._build_slide_captions", return_value=(slides, [])):
            srt, warnings = generate_srt_from_true_starts([], {}, ".", {}, alignment_records=records)
        self.assertIn("00:00:04,000 --> 00:00:05,000", srt)
        self.assertEqual(len(warnings), 2)

    def test_invalid_candidate_rejected_before_serializing(self):
        for start, end in ((2, 1), (1, 1), (-1, 1), (1, 101), (float("nan"), 2)):
            slide = {"slide_num": 1, "captions": [{"text": "bad", "start_seconds": start, "end_seconds": end}]}
            record = {1: {"status": "matched", "start_seconds": 0, "scale": 1, "video_duration_seconds": 100}}
            with self.subTest(start=start), patch("src.subtitle_pipeline._build_slide_captions", return_value=([slide], [])):
                with self.assertRaises(SubtitleTimingError):
                    generate_srt_from_true_starts([], {}, ".", {}, alignment_records=record)

    def test_cross_page_overlap_rejected(self):
        slides = [{"slide_num": n, "captions": [{"text": "bad", "start_seconds": 0, "end_seconds": 3}]} for n in (1, 2)]
        records = {n: {"status": "predicted", "reason": "weak_match", "start_seconds": n,
                       "scale": 1, "video_duration_seconds": 100} for n in (1, 2)}
        with patch("src.subtitle_pipeline._build_slide_captions", return_value=(slides, [])):
            with self.assertRaises(SubtitleTimingError):
                generate_srt_from_true_starts([], {}, ".", {}, alignment_records=records)


if __name__ == "__main__":
    unittest.main()
