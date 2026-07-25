import tempfile
import unittest
from pathlib import Path

from src.main import build_payload, write_subtitle_output


class MainPayloadTests(unittest.TestCase):
    def test_build_payload_adds_subtitle_and_audio_metadata(self):
        slides = [
            {"slide_num": 1, "title": "Intro", "notes": "Hello world"},
            {"slide_num": 2, "title": "Body", "notes": None},
        ]
        audio_manifest = {
            "voice": "test-voice",
            "rate": "-10%",
            "pitch": "+0Hz",
            "output_dir": "output/audio",
            "slides": [{"slide_num": 1, "title": "Intro", "audio_file": "slide_001.mp3"}],
        }

        payload = build_payload(
            slides,
            "demo.pptx",
            audio_manifest=audio_manifest,
            audio_output_dir="output/audio",
        )

        self.assertEqual(payload["source_pptx"], "demo.pptx")
        self.assertEqual(payload["slide_count"], 2)
        self.assertEqual(payload["slides"][0]["subtitle_text"], "Hello world")
        self.assertTrue(payload["slides"][0]["has_notes"])
        self.assertEqual(payload["slides"][0]["audio_file"], "output/audio/slide_001.mp3")
        self.assertEqual(payload["audio"]["voice"], "test-voice")
        self.assertEqual(payload["audio"]["slides"][0]["slide_num"], 1)

    def test_write_subtitle_output_creates_srt_file(self):
        payload = {
            "slides": [
                {"slide_num": 1, "subtitle_text": "Hello world"},
                {"slide_num": 2, "subtitle_text": "Second line"},
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "captions.srt"
            result = write_subtitle_output(payload, output_path)

            self.assertTrue(result.exists())
            self.assertIn("Hello world", result.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
