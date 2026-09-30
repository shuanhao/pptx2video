import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.audio_preparation import (
    AudioPreparationOptions, prepare_audio_manifest, probe_audio,
    validate_preparation_options,
)
from src.exceptions import AudioPreparationError


class PreparationValidationTests(unittest.TestCase):
    def test_disabled_does_not_check_tools_or_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("src.audio_preparation.shutil.which", side_effect=AssertionError):
                result = prepare_audio_manifest({"slides": []}, root / "source", root / "out",
                                                AudioPreparationOptions())
            self.assertEqual(result["converted"], [])
            self.assertFalse((root / "out").exists())

    def test_invalid_settings(self):
        for seconds in (-1, .5, 11, float("nan"), float("inf"), True):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                validate_preparation_options(AudioPreparationOptions(tail_silence=seconds))
        for options in (AudioPreparationOptions(format="wav"),
                        AudioPreparationOptions(4, "wav", "64k"),
                        AudioPreparationOptions(4, "mp3")):
            with self.assertRaises(ValueError):
                validate_preparation_options(options)
        for kwargs in ({"force": True}, {"explicit_options": ["format"]}):
            with self.assertRaises(ValueError):
                validate_preparation_options(AudioPreparationOptions(), **kwargs)
        self.assertTrue(validate_preparation_options(AudioPreparationOptions(1.5)))

    def test_overlapping_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for source, output in ((root, root), (root, root / "out"), (root / "src", root)):
                with self.assertRaises(ValueError):
                    validate_preparation_options(AudioPreparationOptions(4), source, output)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "Requires real ffmpeg/ffprobe")
class PreparationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.output = self.root / "原始 audio", self.root / "prepared"
        self.source.mkdir()
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                        "sine=frequency=440:sample_rate=24000:duration=1.25",
                        "-ac", "1", "-c:a", "libmp3lame", "-b:a", "48k",
                        str(self.source / "slide_001.mp3")], check=True, capture_output=True)
        (self.source / "slide_001.wordboundaries.json").write_text(
            '[{"text":"測試","offset_seconds":0,"duration_seconds":1}]', encoding="utf-8")
        self.manifest = {"voice": "test", "output_dir": str(self.source), "slides": [
            {"slide_num": 1, "audio_file": "slide_001.mp3",
             "word_boundaries_file": "slide_001.wordboundaries.json", "notes": "測試"}]}
        (self.source / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def prepare(self, options=None, **kwargs):
        return prepare_audio_manifest(self.manifest, self.source, self.output,
                                      options or AudioPreparationOptions(4), **kwargs)

    def test_formats_durations_and_originals_preserved(self):
        original = {p.name: p.read_bytes() for p in self.source.iterdir()}
        for fmt in ("m4a", "wav"):
            for seconds in (1, 1.5, 4, 8, 10):
                with self.subTest(format=fmt, seconds=seconds):
                    result = self.prepare(AudioPreparationOptions(seconds, fmt))
                    entry = result["manifest"]["slides"][0]
                    info = probe_audio(self.output / entry["audio_file"])
                    self.assertEqual(info["codec"], "aac" if fmt == "m4a" else "pcm_s16le")
                    self.assertEqual(info["sample_rate"], 24000)
                    self.assertEqual(info["channels"], 1)
                    self.assertAlmostEqual(info["duration_seconds"], 1.25 + seconds, delta=.09)
                    self.assertEqual((self.output / entry["word_boundaries_file"]).read_bytes(),
                                     original["slide_001.wordboundaries.json"])
        self.assertEqual(original, {p.name: p.read_bytes() for p in self.source.iterdir()})

    def test_cache_changes_force_and_corruption(self):
        first = self.prepare()
        old_path = self.output / first["manifest"]["slides"][0]["audio_file"]
        old_bytes = old_path.read_bytes()
        with patch("src.audio_preparation.prepare_audio_file", side_effect=AssertionError):
            self.assertEqual(self.prepare()["reused"], [1])
        self.assertEqual(self.prepare(force=True)["converted"], [1])
        self.assertEqual(old_path.read_bytes(), old_bytes)
        (self.source / "slide_001.wordboundaries.json").write_text("[]")
        self.assertEqual(self.prepare()["converted"], [1])
        changed = self.prepare(AudioPreparationOptions(8))
        self.assertEqual(changed["converted"], [1])
        (self.output / changed["manifest"]["slides"][0]["audio_file"]).write_bytes(b"corrupt")
        self.assertEqual(self.prepare(AudioPreparationOptions(8))["converted"], [1])
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                        "sine=frequency=880:sample_rate=24000:duration=1.25",
                        "-ac", "1", "-c:a", "libmp3lame", "-b:a", "48k",
                        str(self.source / "slide_001.mp3")], check=True, capture_output=True)
        self.assertEqual(self.prepare(AudioPreparationOptions(8))["converted"], [1])

    def test_wav_preserves_decoded_narration_and_appends_silence(self):
        result = self.prepare(AudioPreparationOptions(4, "wav"))
        target = self.output / result["manifest"]["slides"][0]["audio_file"]

        def pcm(path):
            return subprocess.run(["ffmpeg", "-v", "error", "-i", str(path),
                                   "-f", "s16le", "-c:a", "pcm_s16le", "pipe:1"],
                                  check=True, capture_output=True).stdout

        original, prepared = pcm(self.source / "slide_001.mp3"), pcm(target)
        self.assertEqual(prepared[:len(original)], original)
        self.assertEqual(prepared[len(original):], bytes(4 * 24000 * 2))

    def test_failed_batch_keeps_previous_manifest_and_files(self):
        first = self.prepare()
        committed = (self.output / "manifest.json").read_bytes()
        entry = first["manifest"]["slides"][0]
        original = (self.output / entry["audio_file"]).read_bytes()
        second = copy.deepcopy(self.manifest["slides"][0])
        second["slide_num"] = 2
        self.manifest["slides"].append(second)
        from src.audio_preparation import prepare_audio_file
        calls = []

        def fail_second(*args):
            calls.append(args)
            if len(calls) == 2:
                raise AudioPreparationError("simulated encoder failure")
            return prepare_audio_file(*args)

        with patch("src.audio_preparation.prepare_audio_file", side_effect=fail_second):
            with self.assertRaisesRegex(AudioPreparationError, "Slide 2"):
                self.prepare(force=True)
        self.assertEqual((self.output / "manifest.json").read_bytes(), committed)
        self.assertEqual((self.output / entry["audio_file"]).read_bytes(), original)

    def test_missing_boundary_and_source_guard(self):
        self.manifest["slides"][0]["word_boundaries_file"] = None
        result = self.prepare()
        self.assertIsNone(result["manifest"]["slides"][0]["word_boundaries_file"])
        with self.assertRaises(ValueError):
            prepare_audio_manifest(result["manifest"], self.output, self.root / "other", AudioPreparationOptions(4))
        self.manifest["slides"][0]["audio_file"] = "../escape.mp3"
        with self.assertRaises(ValueError):
            self.prepare()

    def test_tool_and_publication_failures(self):
        with patch("src.audio_preparation.shutil.which", return_value=None):
            with self.assertRaisesRegex(AudioPreparationError, "Required tool"):
                self.prepare()
        first = self.prepare()
        committed = (self.output / "manifest.json").read_bytes()
        import os
        replace = os.replace

        def fail_manifest(source, target):
            if Path(target).name == "manifest.json":
                raise OSError("simulated publish failure")
            return replace(source, target)

        with patch("src.audio_preparation.os.replace", side_effect=fail_manifest):
            with self.assertRaisesRegex(AudioPreparationError, "Cannot publish"):
                self.prepare(force=True)
        self.assertEqual((self.output / "manifest.json").read_bytes(), committed)
        self.assertTrue((self.output / first["manifest"]["slides"][0]["audio_file"]).exists())


if __name__ == "__main__":
    unittest.main()
