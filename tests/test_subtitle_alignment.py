import unittest

from src.subtitle_alignment import (
    DEFAULT_TRAILING_GAP_SECONDS,
    align_segments_with_word_boundaries,
    format_srt,
    _seconds_to_srt_timestamp,
)
from src.subtitle_segmenter import segment_notes_for_subtitles


def _wb(text, offset_seconds, duration_seconds):
    return {"text": text, "offset_seconds": offset_seconds, "duration_seconds": duration_seconds}


def _seg(text, start, end):
    return {"text": text, "source_start_offset": start, "source_end_offset": end}


class SecondsToSrtTimestampTests(unittest.TestCase):
    def test_formats_zero(self):
        self.assertEqual(_seconds_to_srt_timestamp(0.0), "00:00:00,000")

    def test_formats_sub_second_precision(self):
        self.assertEqual(_seconds_to_srt_timestamp(1.234), "00:00:01,234")

    def test_formats_hours_minutes_seconds(self):
        self.assertEqual(_seconds_to_srt_timestamp(3661.5), "01:01:01,500")

    def test_negative_input_is_clamped_to_zero(self):
        self.assertEqual(_seconds_to_srt_timestamp(-5.0), "00:00:00,000")


class AlignSegmentsWithWordBoundariesTests(unittest.TestCase):
    def test_basic_alignment_matches_offsets_in_order(self):
        text = "早安世界"
        segments = [_seg("早安世界", 0, 4)]
        word_boundaries = [
            _wb("早", 0.0, 0.2),
            _wb("安", 0.2, 0.2),
            _wb("世", 0.4, 0.2),
            _wb("界", 0.6, 0.2),
        ]

        aligned, warnings = align_segments_with_word_boundaries(text, segments, word_boundaries)

        self.assertEqual(warnings, [])
        self.assertEqual(len(aligned), 1)
        self.assertAlmostEqual(aligned[0]["start_seconds"], 0.0)
        # Last segment: no following segment to extend toward, so its end
        # time stays at the raw last-word end (0.6 + 0.2).
        self.assertAlmostEqual(aligned[0]["end_seconds"], 0.8)

    def test_unvoiced_punctuation_between_boundaries_is_skipped_over(self):
        # "，" between the two words has no WordBoundary event of its own -
        # the cursor should still find "世界" right after it.
        text = "早安，世界"
        segments = [_seg("早安，世界", 0, 5)]
        word_boundaries = [
            _wb("早", 0.0, 0.2),
            _wb("安", 0.2, 0.2),
            _wb("世", 0.4, 0.2),
            _wb("界", 0.6, 0.2),
        ]

        aligned, warnings = align_segments_with_word_boundaries(text, segments, word_boundaries)

        self.assertEqual(warnings, [])
        self.assertAlmostEqual(aligned[0]["start_seconds"], 0.0)
        self.assertAlmostEqual(aligned[0]["end_seconds"], 0.8)

    def test_end_time_extends_forward_to_next_segment_start_minus_gap(self):
        text = "第一句。第二句。"
        segments = [_seg("第一句", 0, 3), _seg("第二句", 4, 7)]
        word_boundaries = [
            _wb("第", 0.0, 0.2),
            _wb("一", 0.2, 0.2),
            _wb("句", 0.4, 0.2),
            # noticeable pause before the next sentence begins
            _wb("第", 2.0, 0.2),
            _wb("二", 2.2, 0.2),
            _wb("句", 2.4, 0.2),
        ]

        aligned, warnings = align_segments_with_word_boundaries(
            text, segments, word_boundaries, trailing_gap_seconds=0.15
        )

        self.assertEqual(warnings, [])
        # Raw end of segment 1 would be 0.4 + 0.2 = 0.6, but it should be
        # extended forward to just before segment 2 starts (2.0 - 0.15).
        self.assertAlmostEqual(aligned[0]["end_seconds"], 1.85)
        # Last segment keeps its raw end (2.4 + 0.2).
        self.assertAlmostEqual(aligned[1]["end_seconds"], 2.6)

    def test_end_time_extension_never_shrinks_below_raw_end(self):
        text = "第一句第二句"
        segments = [_seg("第一句", 0, 3), _seg("第二句", 3, 6)]
        # Back-to-back with almost no gap - extending "to just before the
        # next segment, minus 0.15s" would land *before* the raw end here,
        # which must not shrink the interval.
        word_boundaries = [
            _wb("第", 0.0, 0.2),
            _wb("一", 0.2, 0.2),
            _wb("句", 0.4, 0.2),
            _wb("第", 0.62, 0.2),
            _wb("二", 0.82, 0.2),
            _wb("句", 1.02, 0.2),
        ]

        aligned, warnings = align_segments_with_word_boundaries(
            text, segments, word_boundaries, trailing_gap_seconds=0.15
        )

        self.assertEqual(warnings, [])
        # Raw end (0.6) is kept, not shrunk to 0.62 - 0.15 = 0.47.
        self.assertAlmostEqual(aligned[0]["end_seconds"], 0.6)

    def test_unmatched_word_boundary_text_is_skipped_with_a_warning(self):
        text = "早安世界"
        segments = [_seg("早安世界", 0, 4)]
        word_boundaries = [
            _wb("早", 0.0, 0.2),
            _wb("XYZ_NOT_IN_TEXT", 0.2, 0.1),  # can never match
            _wb("安", 0.3, 0.2),
            _wb("世", 0.5, 0.2),
            _wb("界", 0.7, 0.2),
        ]

        aligned, warnings = align_segments_with_word_boundaries(text, segments, word_boundaries)

        self.assertEqual(len(warnings), 1)
        self.assertIn("XYZ_NOT_IN_TEXT", warnings[0])
        # Alignment still completes using the events that did match.
        self.assertAlmostEqual(aligned[0]["start_seconds"], 0.0)
        self.assertAlmostEqual(aligned[0]["end_seconds"], 0.9)

    def test_segment_with_no_matching_boundaries_is_interpolated_with_a_warning(self):
        text = "第一句第二句第三句"
        segments = [
            _seg("第一句", 0, 3),
            _seg("第二句", 3, 6),
            _seg("第三句", 6, 9),
        ]
        # No WordBoundary events at all fall inside segment 2's offset
        # range (3-6) - simulates edge-tts silently dropping that whole
        # span from its boundary events.
        word_boundaries = [
            _wb("第", 0.0, 0.2),
            _wb("一", 0.2, 0.2),
            _wb("句", 0.4, 0.2),
            _wb("第", 3.0, 0.2),  # this text is "第" from segment 3, offset 6
            _wb("三", 3.2, 0.2),
            _wb("句", 3.4, 0.2),
        ]
        # Rig the offsets so the second "第"/"三"/"句" trio is only found
        # starting from character offset 6 onward (segment 3) - the exact
        # substring search would otherwise (incorrectly, for this test)
        # match the first "第" again. Use a cursor-respecting variant by
        # replacing segment 2's characters with something distinguishable.
        text = "第一句　　　第三句"
        segments = [
            _seg("第一句", 0, 3),
            _seg("　　　", 3, 6),
            _seg("第三句", 6, 9),
        ]

        aligned, warnings = align_segments_with_word_boundaries(text, segments, word_boundaries)

        interpolation_warnings = [w for w in warnings if "interpolated" in w]
        self.assertEqual(len(interpolation_warnings), 1)
        self.assertIn("segment 1", interpolation_warnings[0])
        # Interpolated start = segment 1's (already extended) end time;
        # interpolated end = the next matched boundary's start (segment 3's
        # first matched "第" at 3.0s).
        self.assertAlmostEqual(aligned[1]["start_seconds"], aligned[0]["end_seconds"])
        self.assertAlmostEqual(aligned[1]["end_seconds"], 3.0)

    def test_negative_trailing_gap_raises(self):
        with self.assertRaises(ValueError):
            align_segments_with_word_boundaries("x", [], [], trailing_gap_seconds=-0.1)

    def test_default_trailing_gap_constant_is_used_by_default(self):
        text = "第一句第二句"
        segments = [_seg("第一句", 0, 3), _seg("第二句", 3, 6)]
        word_boundaries = [
            _wb("第", 0.0, 0.2),
            _wb("一", 0.2, 0.2),
            _wb("句", 0.4, 0.2),
            _wb("第", 2.0, 0.2),
            _wb("二", 2.2, 0.2),
            _wb("句", 2.4, 0.2),
        ]

        aligned, _ = align_segments_with_word_boundaries(text, segments, word_boundaries)

        self.assertAlmostEqual(aligned[0]["end_seconds"], 2.0 - DEFAULT_TRAILING_GAP_SECONDS)

    def test_end_to_end_with_real_segmenter_output(self):
        # A "\n" paragraph break forces two segments regardless of width
        # (paragraph boundaries are a hard boundary - see subtitle_segmenter's
        # design decision 3), unlike relying on the two sentences alone,
        # which are short enough that _pack_units could legally merge them
        # onto one line.
        text = "今天天氣很好。\n我們出去走走吧！"
        segments = segment_notes_for_subtitles(text)
        self.assertEqual(len(segments), 2)

        # Fabricate one WordBoundary event per character, in order, each
        # 0.2s long with no gaps - a simplified stand-in for real edge-tts
        # output good enough to exercise the alignment logic end-to-end.
        # Punctuation and the paragraph-break newline aren't voiced, so
        # they get no event of their own, same as real edge-tts output.
        word_boundaries = []
        t = 0.0
        for ch in text:
            if ch not in "。！\n":
                word_boundaries.append(_wb(ch, t, 0.2))
                t += 0.2

        aligned, warnings = align_segments_with_word_boundaries(text, segments, word_boundaries)

        self.assertEqual(warnings, [])
        self.assertEqual([a["text"] for a in aligned], [s["text"] for s in segments])
        self.assertLess(aligned[0]["start_seconds"], aligned[0]["end_seconds"])
        self.assertLess(aligned[1]["start_seconds"], aligned[1]["end_seconds"])
        self.assertLessEqual(aligned[0]["end_seconds"], aligned[1]["start_seconds"])


class FormatSrtTests(unittest.TestCase):
    def test_empty_entries_returns_empty_string(self):
        self.assertEqual(format_srt([]), "")

    def test_formats_single_entry(self):
        entries = [{"text": "早安世界", "start_seconds": 0.0, "end_seconds": 1.5}]
        expected = "1\n00:00:00,000 --> 00:00:01,500\n早安世界\n"
        self.assertEqual(format_srt(entries), expected)

    def test_formats_multiple_entries_with_sequential_numbering(self):
        entries = [
            {"text": "第一句", "start_seconds": 0.0, "end_seconds": 1.0},
            {"text": "第二句", "start_seconds": 1.0, "end_seconds": 2.5},
        ]
        expected = (
            "1\n00:00:00,000 --> 00:00:01,000\n第一句\n"
            "\n"
            "2\n00:00:01,000 --> 00:00:02,500\n第二句\n"
        )
        self.assertEqual(format_srt(entries), expected)


if __name__ == "__main__":
    unittest.main()
