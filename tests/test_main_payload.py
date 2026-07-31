import json
import tempfile
import unittest
from pathlib import Path

from pydub import AudioSegment

from src.main import build_payload, write_subtitle_output


def _write_silent_mp3(path: Path, duration_ms: int) -> None:
    AudioSegment.silent(duration=duration_ms).export(path, format="mp3")


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

    def test_write_subtitle_output_creates_srt_file_from_word_boundary_manifest(self):
        # As of Phase 4, subtitle generation is driven by real WordBoundary
        # timing data (via subtitle_pipeline.generate_srt_for_deck), not the
        # old equal-duration-split heuristic - so this needs a real audio
        # manifest with a word_boundaries_file, not just "subtitle_text".
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_dir = Path(temp_dir)
            _write_silent_mp3(audio_dir / "slide_001.mp3", 1000)
            (audio_dir / "slide_001.wordboundaries.json").write_text(
                json.dumps([
                    {"text": "Hello", "offset_seconds": 0.0, "duration_seconds": 0.3},
                    {"text": "world", "offset_seconds": 0.3, "duration_seconds": 0.3},
                ]),
                encoding="utf-8",
            )

            payload = {
                "slides": [
                    {"slide_num": 1, "notes": "Hello world"},
                ],
                "audio": {
                    "output_dir": str(audio_dir),
                    "slides": [
                        {
                            "slide_num": 1,
                            "audio_file": "slide_001.mp3",
                            "word_boundaries_file": "slide_001.wordboundaries.json",
                        },
                    ],
                },
            }

            output_path = Path(temp_dir) / "captions.srt"
            result_path, warnings = write_subtitle_output(payload, output_path, audio_dir=audio_dir)

            self.assertEqual(warnings, [])
            self.assertTrue(result_path.exists())
            self.assertIn("Hello world", result_path.read_text(encoding="utf-8"))

    def test_write_subtitle_output_writes_empty_srt_when_no_audio_manifest(self):
        # No "audio" key at all - e.g. the CLI was run without
        # --generate-audio and no manifest.json existed to load. This must
        # not raise; an empty .srt is the expected, supported result.
        payload = {
            "slides": [
                {"slide_num": 1, "notes": "Hello world"},
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "captions.srt"
            result_path, warnings = write_subtitle_output(payload, output_path)

            self.assertEqual(warnings, [])
            self.assertTrue(result_path.exists())
            self.assertEqual(result_path.read_text(encoding="utf-8"), "")


if __name__ == "__main__":
    unittest.main()
