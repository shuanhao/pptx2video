import tempfile
import unittest
from pathlib import Path

from src.tts import generate_audio_files


class TtsGeneratorTests(unittest.TestCase):
    def test_generate_audio_files_skips_slides_without_notes(self):
        slides = [
            {"slide_num": 1, "title": "Intro", "notes": "Hello there"},
            {"slide_num": 2, "title": "No notes", "notes": None},
            {"slide_num": 3, "title": "Outro", "notes": "Thanks for watching"},
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            def fake_generator(text, output_path, voice):
                output_path.write_bytes(b"fake-audio")

            manifest = generate_audio_files(
                slides,
                output_dir,
                voice="en-US-AriaNeural",
                generator=fake_generator,
            )

            self.assertEqual(
                [entry["audio_file"] for entry in manifest["slides"]],
                ["slide_001.mp3", "slide_003.mp3"],
            )
            self.assertTrue((output_dir / "slide_001.mp3").exists())
            self.assertTrue((output_dir / "slide_003.mp3").exists())
            self.assertFalse((output_dir / "slide_002.mp3").exists())


if __name__ == "__main__":
    unittest.main()
