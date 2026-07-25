import tempfile
import unittest
from pathlib import Path

from src.subtitle_generator import build_subtitle_entries, write_srt


class DummyAudioSegment:
    @staticmethod
    def from_file(path):
        class AudioFile:
            duration_seconds = 1.25

        return AudioFile()


class SubtitleGeneratorTests(unittest.TestCase):
    def test_build_subtitle_entries_skips_slides_without_notes(self):
        slides = [
            {"slide_num": 1, "title": "Intro", "subtitle_text": "Hello world"},
            {"slide_num": 2, "title": "Body", "subtitle_text": None},
            {"slide_num": 3, "title": "Outro", "subtitle_text": "Thanks"},
        ]

        entries = build_subtitle_entries(slides)
        self.assertEqual([entry["text"] for entry in entries], ["Hello world", "Thanks"])

    def test_write_srt_creates_expected_file(self):
        slides = [
            {"slide_num": 1, "title": "Intro", "subtitle_text": "Hello world"},
            {"slide_num": 2, "title": "Body", "subtitle_text": "Second line"},
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "captions.srt"
            written = write_srt(slides, output_path, durations=[2.0, 3.0])
            self.assertTrue(written.exists())
            self.assertIn("1", written.read_text(encoding="utf-8"))
            self.assertIn("Hello world", written.read_text(encoding="utf-8"))

    def test_build_subtitle_entries_skips_cover_and_thank_you_slides(self):
        slides = [
            {"slide_num": 1, "title": "Cover Page", "subtitle_text": "Welcome"},
            {"slide_num": 2, "title": "Body", "subtitle_text": "Main content"},
            {"slide_num": 3, "title": "Q&A / Thanks", "subtitle_text": "Thanks"},
        ]

        entries = build_subtitle_entries(slides)
        self.assertEqual([entry["slide_num"] for entry in entries], [2])

    def test_build_subtitle_entries_uses_audio_duration_when_available(self):
        slides = [{"slide_num": 1, "title": "Intro", "subtitle_text": "Hello world"}]

        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "slide_001.mp3"
            audio_path.write_bytes(b"fake")

            import src.subtitle_generator as subtitle_module

            original = subtitle_module.AudioSegment
            subtitle_module.AudioSegment = DummyAudioSegment
            try:
                entries = build_subtitle_entries(slides, audio_dir=temp_dir)
            finally:
                subtitle_module.AudioSegment = original

            self.assertEqual(entries[0]["duration"], 1.25)

    def test_build_subtitle_entries_splits_text_into_sentence_segments(self):
        slides = [{"slide_num": 1, "title": "Intro", "subtitle_text": "First sentence here. Second sentence here! Third sentence here?"}]

        entries = build_subtitle_entries(slides, durations=[6.0])

        self.assertEqual(
            [entry["text"] for entry in entries],
            ["First sentence here.", "Second sentence here!", "Third sentence here?"],
        )
        self.assertEqual([entry["duration"] for entry in entries], [2.0, 2.0, 2.0])


if __name__ == "__main__":
    unittest.main()
