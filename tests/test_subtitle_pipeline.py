import json
import tempfile
import unittest
from pathlib import Path

from pydub import AudioSegment

from src.subtitle_pipeline import generate_srt_for_deck, generate_srt_from_true_starts


def _write_silent_mp3(path: Path, duration_ms: int) -> None:
    AudioSegment.silent(duration=duration_ms).export(path, format="mp3")


def _write_word_boundaries(path: Path, events) -> None:
    path.write_text(json.dumps(events), encoding="utf-8")


def _parse_srt_start_seconds(srt_text: str, cue_start_index: int) -> float:
    # cue_start_index should point at (or before) a "HH:MM:SS,mmm -->" line.
    import re
    match = re.search(r"(\d\d):(\d\d):(\d\d),(\d\d\d) -->", srt_text[cue_start_index:])
    # re.search() returns Optional[Match] - assert narrows it to Match for
    # both the type checker (Pylance's "groups is not a known attribute of
    # None" warning) and, more importantly, at runtime: if a test ever
    # passes a cue_start_index that isn't actually pointing at a timestamp
    # line, this fails loudly here with a clear message instead of letting
    # `None.groups()` raise a cryptic AttributeError two lines down.
    assert match is not None, (
        f"No SRT timestamp found at/after index {cue_start_index} in: {srt_text[cue_start_index:cue_start_index + 60]!r}"
    )
    h, m, s, ms = (int(g) for g in match.groups())
    return h * 3600 + m * 60 + s + ms / 1000.0


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


class GenerateSrtFromTrueStartsTests(unittest.TestCase):
    def test_uses_measured_start_instead_of_predicted_sum(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio_dir = Path(tmp)

            _write_silent_mp3(audio_dir / "slide_001.mp3", 2000)
            _write_word_boundaries(audio_dir / "slide_001.wordboundaries.json", [
                {"text": "早", "offset_seconds": 0.0, "duration_seconds": 0.3},
            ])
            _write_silent_mp3(audio_dir / "slide_002.mp3", 1500)
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

            # Deliberately different from the ~2.0s a predicted-sum approach
            # would produce, to prove the measured value (not the predicted
            # one) drives placement.
            true_starts = {1: 0.0, 2: 7.42}

            srt_text, warnings = generate_srt_from_true_starts(
                slides, manifest, audio_dir, true_starts
            )

            # Slide 2 (the last narrated slide) has no later measured slide
            # to derive its own stretch ratio from, so it falls back to the
            # deck-wide average (here, just slide 1's own ratio) - flagged
            # in the warnings even though, in this test, slide 2's caption
            # sits at offset 0.0 so the scale doesn't visibly move it.
            self.assertEqual(len(warnings), 1)
            self.assertIn("deck-wide average ratio", warnings[0])
            self.assertIn("00:00:07,42", srt_text[srt_text.index("午") - 40:])

    def test_slide_missing_from_true_starts_falls_back_to_predicted_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio_dir = Path(tmp)

            _write_silent_mp3(audio_dir / "slide_001.mp3", 2000)
            _write_word_boundaries(audio_dir / "slide_001.wordboundaries.json", [
                {"text": "早", "offset_seconds": 0.0, "duration_seconds": 0.3},
            ])

            slides = [{"slide_num": 1, "title": "A", "notes": "早"}]
            manifest = {
                "output_dir": str(audio_dir),
                "slides": [
                    {"slide_num": 1, "audio_file": "slide_001.mp3", "word_boundaries_file": "slide_001.wordboundaries.json"},
                ],
            }

            srt_text, warnings = generate_srt_from_true_starts(
                slides, manifest, audio_dir, true_starts_by_slide={}
            )

            self.assertEqual(len(warnings), 1)
            self.assertIn("no measured true start time", warnings[0])
            # Falls back to the predicted position (0.0s, the start of the deck).
            self.assertIn("00:00:00,00", srt_text)

    def test_empty_deck_returns_empty_srt_and_no_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio_dir = Path(tmp)
            manifest = {"output_dir": str(audio_dir), "slides": []}

            srt_text, warnings = generate_srt_from_true_starts([], manifest, audio_dir, {})

            self.assertEqual(srt_text, "")
            self.assertEqual(warnings, [])

    def test_scales_intra_slide_captions_by_measured_stretch_ratio(self):
        # Regression test: correctly placing a slide's *start* isn't enough
        # for a long slide - captions late in that slide's own narration
        # (timed from the original, unstretched mp3) must also be scaled by
        # the slide's real (measured) stretch ratio, or they still drift
        # within the slide even though the slide itself starts on time.
        with tempfile.TemporaryDirectory() as tmp:
            audio_dir = Path(tmp)

            # Slide 1: 10s predicted duration, with a caption near its end
            # (9.5s in) - the part of the slide most exposed to intra-slide
            # drift if scaling isn't applied.
            _write_silent_mp3(audio_dir / "slide_001.mp3", 10000)
            _write_word_boundaries(audio_dir / "slide_001.wordboundaries.json", [
                {"text": "早", "offset_seconds": 9.5, "duration_seconds": 0.3},
            ])
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

            # Slide 1's predicted duration is ~10.0s (whatever pydub actually
            # measures from the mp3 - mp3 encoders can add a few ms of their
            # own padding, hence measuring it directly below rather than
            # assuming an exact 10.0), but its measured real duration in the
            # export (gap between the two measured starts) is 10.05s - a
            # ~0.5% local stretch, deliberately large enough to be
            # unambiguous in the assertion below.
            true_starts = {1: 0.0, 2: 10.05}
            predicted_duration = AudioSegment.from_file(audio_dir / "slide_001.mp3").duration_seconds
            expected_scale = 10.05 / predicted_duration
            expected_caption_start = 9.5 * expected_scale

            srt_text, warnings = generate_srt_from_true_starts(
                slides, manifest, audio_dir, true_starts
            )

            # Slide 2 (the last narrated slide) still gets the "no later
            # slide to derive its own ratio from" warning - its own caption
            # sits at offset 0.0 so this doesn't move anything visible, but
            # the warning itself is still correctly informative.
            self.assertEqual(len(warnings), 1)
            self.assertIn("deck-wide average ratio", warnings[0])
            actual_caption_start = _parse_srt_start_seconds(srt_text, max(0, srt_text.index("早") - 60))
            # Unscaled, the caption at 9.5s would land at ~9.5s - scaling
            # should visibly move it later than that.
            self.assertGreater(actual_caption_start, 9.5)
            self.assertAlmostEqual(actual_caption_start, expected_caption_start, delta=0.01)

    def test_last_measured_slide_uses_deck_wide_average_scale_with_warning(self):
        # The last narrated slide has no *later* measured slide to derive
        # its own stretch ratio from - it should fall back to the deck-wide
        # average of the other slides' measured ratios (not silently assume
        # zero stretch), and say so in the warnings.
        with tempfile.TemporaryDirectory() as tmp:
            audio_dir = Path(tmp)

            _write_silent_mp3(audio_dir / "slide_001.mp3", 10000)
            _write_word_boundaries(audio_dir / "slide_001.wordboundaries.json", [
                {"text": "早", "offset_seconds": 0.0, "duration_seconds": 0.3},
            ])
            _write_silent_mp3(audio_dir / "slide_002.mp3", 10000)
            _write_word_boundaries(audio_dir / "slide_002.wordboundaries.json", [
                {"text": "午", "offset_seconds": 0.0, "duration_seconds": 0.3},
            ])
            _write_silent_mp3(audio_dir / "slide_003.mp3", 10000)
            _write_word_boundaries(audio_dir / "slide_003.wordboundaries.json", [
                {"text": "晚", "offset_seconds": 9.5, "duration_seconds": 0.3},
            ])

            slides = [
                {"slide_num": 1, "title": "A", "notes": "早"},
                {"slide_num": 2, "title": "B", "notes": "午"},
                {"slide_num": 3, "title": "C", "notes": "晚"},
            ]
            manifest = {
                "output_dir": str(audio_dir),
                "slides": [
                    {"slide_num": 1, "audio_file": "slide_001.mp3", "word_boundaries_file": "slide_001.wordboundaries.json"},
                    {"slide_num": 2, "audio_file": "slide_002.mp3", "word_boundaries_file": "slide_002.wordboundaries.json"},
                    {"slide_num": 3, "audio_file": "slide_003.mp3", "word_boundaries_file": "slide_003.wordboundaries.json"},
                ],
            }

            # Slides 1->2 and 2->3 each measure their own stretch ratio from
            # their real (mp3-measured, not assumed-exactly-10.0) predicted
            # gap vs. the measured gap; slide 3 (the last) has no later
            # measured slide of its own, so it falls back to the *average*
            # of those two ratios (mirroring the implementation).
            true_starts = {1: 0.0, 2: 10.1, 3: 20.1}
            d1 = AudioSegment.from_file(audio_dir / "slide_001.mp3").duration_seconds
            d2 = AudioSegment.from_file(audio_dir / "slide_002.mp3").duration_seconds
            scale_1_to_2 = 10.1 / d1  # gap from slide 1's start to slide 2's start
            scale_2_to_3 = (20.1 - 10.1) / d2  # gap from slide 2's start to slide 3's start
            expected_scale = (scale_1_to_2 + scale_2_to_3) / 2
            expected_caption_start = 20.1 + 9.5 * expected_scale

            srt_text, warnings = generate_srt_from_true_starts(
                slides, manifest, audio_dir, true_starts
            )

            self.assertTrue(any("deck-wide average ratio" in w for w in warnings))
            actual_caption_start = _parse_srt_start_seconds(srt_text, max(0, srt_text.index("晚") - 60))
            self.assertAlmostEqual(actual_caption_start, expected_caption_start, delta=0.01)


    def test_direct_end_measurement_is_unaffected_by_inter_slide_gap(self):
        # Regression test for the confound found via
        # scripts/verify_srt_accuracy.py's word-level ground truth sampling
        # on a real deck: inferring a slide's stretch ratio from the gap to
        # the *next* measured slide's start conflates this slide's own
        # stretch with any extra gap PowerPoint's export inserts *between*
        # slides - a different, unrelated effect. A direct measurement of
        # this slide's own end (true_ends_by_slide) should be immune to that
        # gap entirely.
        with tempfile.TemporaryDirectory() as tmp:
            audio_dir = Path(tmp)

            _write_silent_mp3(audio_dir / "slide_001.mp3", 10000)
            _write_word_boundaries(audio_dir / "slide_001.wordboundaries.json", [
                {"text": "早", "offset_seconds": 9.5, "duration_seconds": 0.3},
            ])
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

            d1 = AudioSegment.from_file(audio_dir / "slide_001.mp3").duration_seconds

            # Slide 1 itself has NO real stretch (its own measured end is
            # exactly its own predicted duration later than its start) - but
            # PowerPoint's export inserts an extra 2.0s gap before slide 2
            # starts, unrelated to slide 1's own narration speed.
            true_starts = {1: 0.0, 2: d1 + 2.0}
            true_ends = {1: d1}

            srt_text, warnings = generate_srt_from_true_starts(
                slides, manifest, audio_dir, true_starts, true_ends_by_slide=true_ends
            )

            actual_caption_start = _parse_srt_start_seconds(srt_text, max(0, srt_text.index("早") - 60))
            # With the direct measurement, slide 1's own scale should come
            # out as ~1.0 (no real stretch) - the caption at 9.5s should
            # land at ~9.5s, NOT at 9.5 * ((d1 + 2.0) / d1) (~11.4s), which
            # is what the old next-slide-inferred method would have produced
            # by mistaking the inter-slide gap for this slide's own stretch.
            self.assertAlmostEqual(actual_caption_start, 9.5, delta=0.05)

    def test_omitting_true_ends_falls_back_to_inferred_scale_biased_by_the_gap(self):
        # Same fixture as the previous test, but WITHOUT true_ends_by_slide -
        # demonstrating that this is what the direct measurement is actually
        # fixing: without it, the inter-slide gap gets mistaken for slide 1's
        # own stretch, producing a visibly wrong (too-late) caption time.
        with tempfile.TemporaryDirectory() as tmp:
            audio_dir = Path(tmp)

            _write_silent_mp3(audio_dir / "slide_001.mp3", 10000)
            _write_word_boundaries(audio_dir / "slide_001.wordboundaries.json", [
                {"text": "早", "offset_seconds": 9.5, "duration_seconds": 0.3},
            ])
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

            d1 = AudioSegment.from_file(audio_dir / "slide_001.mp3").duration_seconds
            true_starts = {1: 0.0, 2: d1 + 2.0}

            srt_text, warnings = generate_srt_from_true_starts(
                slides, manifest, audio_dir, true_starts  # no true_ends_by_slide
            )

            actual_caption_start = _parse_srt_start_seconds(srt_text, max(0, srt_text.index("早") - 60))
            # Inferred scale = (d1 + 2.0) / d1 -> caption lands well past
            # 9.5s, unlike the direct-measurement version above.
            self.assertGreater(actual_caption_start, 10.0)


if __name__ == "__main__":
    unittest.main()
