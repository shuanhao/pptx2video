import tempfile
import unittest
from pathlib import Path

from src.exceptions import TTSGenerationError
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


    def test_generate_audio_files_reports_progress(self):
        slides = [
            {"slide_num": 1, "title": "Intro", "notes": "Hello there"},
            {"slide_num": 2, "title": "No notes", "notes": None},
            {"slide_num": 3, "title": "Middle", "notes": "Some content"},
            {"slide_num": 4, "title": "Outro", "notes": "Thanks for watching"},
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            def fake_generator(text, output_path, voice):
                output_path.write_bytes(b"fake-audio")

            progress_calls = []

            def track_progress(current, total, slide_num):
                progress_calls.append((current, total, slide_num))

            generate_audio_files(
                slides,
                output_dir,
                voice="en-US-AriaNeural",
                generator=fake_generator,
                progress_callback=track_progress,
            )

            # Only slides with notes count towards the total (3 of them),
            # and the callback fires once per generated file, in order.
            self.assertEqual(progress_calls, [(1, 3, 1), (2, 3, 3), (3, 3, 4)])

    def test_generate_audio_files_works_without_progress_callback(self):
        slides = [{"slide_num": 1, "title": "Intro", "notes": "Hello there"}]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            def fake_generator(text, output_path, voice):
                output_path.write_bytes(b"fake-audio")

            # Should not raise even though no progress_callback is passed.
            manifest = generate_audio_files(
                slides,
                output_dir,
                voice="en-US-AriaNeural",
                generator=fake_generator,
            )
            self.assertEqual(len(manifest["slides"]), 1)

    def test_generate_audio_files_wraps_generator_failure_with_slide_context(self):
        slides = [
            {"slide_num": 1, "title": "Intro", "notes": "Hello there"},
            {"slide_num": 2, "title": "Boom", "notes": "This one fails"},
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            def flaky_generator(text, output_path, voice):
                if "fails" in text:
                    raise ConnectionError("network is down")
                output_path.write_bytes(b"fake-audio")

            with self.assertRaises(TTSGenerationError) as ctx:
                generate_audio_files(
                    slides,
                    output_dir,
                    voice="en-US-AriaNeural",
                    generator=flaky_generator,
                )

            # The error message should say which slide failed, and the
            # original exception should still be reachable via chaining.
            self.assertIn("slide 2", str(ctx.exception))
            self.assertIsInstance(ctx.exception.__cause__, ConnectionError)

    def test_generate_audio_files_hints_at_ffmpeg_for_file_not_found(self):
        slides = [{"slide_num": 1, "title": "Intro", "notes": "Hello there"}]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            def missing_ffmpeg_generator(text, output_path, voice):
                raise FileNotFoundError("ffmpeg not found")

            with self.assertRaises(TTSGenerationError) as ctx:
                generate_audio_files(
                    slides,
                    output_dir,
                    voice="en-US-AriaNeural",
                    generator=missing_ffmpeg_generator,
                )

            self.assertIn("ffmpeg", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
