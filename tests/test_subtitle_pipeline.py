import json
import tempfile
import unittest
from pathlib import Path

from pydub import AudioSegment

from src.subtitle_pipeline import generate_srt_for_deck


def _write_silent_mp3(path: Path, duration_ms: int) -> None:
    AudioSegment.silent(duration=duration_ms).export(path, format="mp3")


def _write_word_boundaries(path: Path, events) -> None:
    path.write_text(json.dumps(events), encoding="utf-8")


class GenerateSrtForDeckTests(unittest.TestCase):
    def test_merges_two_narrated_slides_with_cumulative_offsets(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio_dir = Path(tmp)

            _write_silent_mp3(audio_dir / "slide_001.mp3", 2000)
            _write_word_boundaries(audio_dir / "slide_001.wordboundaries.json", [
                {"text": "早", "offset_seconds": 0.0, "duration_seconds": 0.3},
                {"text": "安", "offset_seconds": 0.3, "duration_seconds": 0.3},
            ])

            _write_silent_mp3(audio_dir / "slide_002.mp3", 1500)
            _write_word_boundaries(audio_dir / "slide_002.wordboundaries.json", [
                {"text": "午", "offset_seconds": 0.0, "duration_seconds": 0.3},
                {"text": "安", "offset_seconds": 0.3, "duration_seconds": 0.3},
            ])

            slides = [
                {"slide_num": 1, "title": "A", "notes": "早安"},
                {"slide_num": 2, "title": "B", "notes": "午安"},
            ]
            manifest = {
                "output_dir": str(audio_dir),
                "slides": [
                    {"slide_num": 1, "audio_file": "slide_001.mp3", "word_boundaries_file": "slide_001.wordboundaries.json"},
                    {"slide_num": 2, "audio_file": "slide_002.mp3", "word_boundaries_file": "slide_002.wordboundaries.json"},
                ],
            }

            srt_text, warnings = generate_srt_for_deck(slides, manifest, audio_dir)

            self.assertEqual(warnings, [])
            self.assertIn("早安", srt_text)
            self.assertIn("午安", srt_text)
            # Slide 2's cue should start at/after ~2.0s (slide 1's measured
            # audio duration), not at 0s.
            self.assertIn("00:00:02,00", srt_text[:srt_text.index("午安")])
            # Sequential numbering across the whole deck, not restarted per slide.
            self.assertTrue(srt_text.startswith("1\n"))
            self.assertIn("\n2\n", srt_text)

    def test_slide_without_notes_advances_timeline_by_default_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio_dir = Path(tmp)

            _write_silent_mp3(audio_dir / "slide_002.mp3", 1000)
            _write_word_boundaries(audio_dir / "slide_002.wordboundaries.json", [
                {"text": "嗨", "offset_seconds": 0.0, "duration_seconds": 0.3},
            ])

            slides = [
                {"slide_num": 1, "title": "Cover", "notes": None},
                {"slide_num": 2, "title": "B", "notes": "嗨"},
            ]
            manifest = {
                "output_dir": str(audio_dir),
                "slides": [
                    {"slide_num": 2, "audio_file": "slide_002.mp3", "word_boundaries_file": "slide_002.wordboundaries.json"},
                ],
            }

            srt_text, warnings = generate_srt_for_deck(
                slides, manifest, audio_dir, default_slide_duration=5.0
            )

            self.assertEqual(warnings, [])
            # Slide 2's cue should start at ~5.0s (slide 1's default duration).
            self.assertIn("00:00:05,00", srt_text)

    def test_narrated_slide_with_no_word_boundaries_file_is_skipped_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio_dir = Path(tmp)
            _write_silent_mp3(audio_dir / "slide_001.mp3", 1000)

            slides = [{"slide_num": 1, "title": "A", "notes": "早安"}]
            manifest = {
                "output_dir": str(audio_dir),
                "slides": [
                    {"slide_num": 1, "audio_file": "slide_001.mp3", "word_boundaries_file": None},
                ],
            }

            srt_text, warnings = generate_srt_for_deck(slides, manifest, audio_dir)

            self.assertEqual(srt_text, "")
            self.assertEqual(len(warnings), 1)
            self.assertIn("no word_boundaries_file", warnings[0])

    def test_missing_audio_file_falls_back_to_default_duration_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio_dir = Path(tmp)
            _write_word_boundaries(audio_dir / "slide_001.wordboundaries.json", [
                {"text": "早", "offset_seconds": 0.0, "duration_seconds": 0.3},
            ])
            # slide_001.mp3 is deliberately not written.

            _write_silent_mp3(audio_dir / "slide_002.mp3", 1000)
            _write_word_boundaries(audio_dir / "slide_002.wordboundaries.json", [
                {"text": "午", "offset_seconds": 0.0, "duration_seconds": 0.3},
            ])

            slides = [
                {"slide_num": 1, "title": "A", "notes": "早"},
                {"slide_num": 2, "title": "B", "notes": "午"},
            ]
            manifest = {
                "output_dir": str(audio_dir),
                "slides": [
                    {"slide_num": 1, "audio_file": "slide_001.mp3", "word_boundaries_file": "slide_001.wordboundaries.json"},
                    {"slide_num": 2, "audio_file": "slide_002.mp3", "word_boundaries_file": "slide_002.wordboundaries.json"},
                ],
            }

            srt_text, warnings = generate_srt_for_deck(
                slides, manifest, audio_dir, default_slide_duration=5.0
            )

            self.assertEqual(len(warnings), 1)
            self.assertIn("could not measure audio duration", warnings[0])
            # Slide 2 should still have advanced by the fallback default (5.0s).
            self.assertIn("00:00:05,00", srt_text)

    def test_corrupt_word_boundaries_file_is_skipped_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio_dir = Path(tmp)
            _write_silent_mp3(audio_dir / "slide_001.mp3", 1000)
            (audio_dir / "slide_001.wordboundaries.json").write_text("not valid json{{{", encoding="utf-8")

            slides = [{"slide_num": 1, "title": "A", "notes": "早安"}]
            manifest = {
                "output_dir": str(audio_dir),
                "slides": [
                    {"slide_num": 1, "audio_file": "slide_001.mp3", "word_boundaries_file": "slide_001.wordboundaries.json"},
                ],
            }

            srt_text, warnings = generate_srt_for_deck(slides, manifest, audio_dir)

            self.assertEqual(srt_text, "")
            self.assertEqual(len(warnings), 1)
            self.assertIn("could not read word boundaries file", warnings[0])

    def test_empty_deck_returns_empty_srt_and_no_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio_dir = Path(tmp)
            manifest = {"output_dir": str(audio_dir), "slides": []}

            srt_text, warnings = generate_srt_for_deck([], manifest, audio_dir)

            self.assertEqual(srt_text, "")
            self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
