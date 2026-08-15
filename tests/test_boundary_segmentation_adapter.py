import unittest

from src.boundary_segmentation_adapter import (
    DEFAULT_MAX_DISPLAY_WIDTH,
    segment_notes_for_subtitles_via_boundary_engine,
)
from src.subtitle_segmenter import segment_notes_for_subtitles

# ---------------------------------------------------------------------------
# 1. Basic conversion / contract shape
# ---------------------------------------------------------------------------


class BasicConversionTests(unittest.TestCase):
    def test_returns_a_list_of_dicts(self):
        result = segment_notes_for_subtitles_via_boundary_engine("Hello world.")
        self.assertIsInstance(result, list)
        for entry in result:
            self.assertIsInstance(entry, dict)

    def test_each_entry_has_exactly_the_required_keys(self):
        result = segment_notes_for_subtitles_via_boundary_engine("Hello world, this is a test.")
        self.assertTrue(result)
        for entry in result:
            self.assertEqual(set(entry.keys()), {"text", "source_start_offset", "source_end_offset"})

    def test_default_max_display_width_matches_boundary_segmentation_engine(self):
        from src.boundary_segmentation import DEFAULT_MAX_DISPLAY_WIDTH as ENGINE_DEFAULT

        self.assertEqual(DEFAULT_MAX_DISPLAY_WIDTH, ENGINE_DEFAULT)
        self.assertEqual(DEFAULT_MAX_DISPLAY_WIDTH, 36)


# ---------------------------------------------------------------------------
# 2. Empty / whitespace-only input
# ---------------------------------------------------------------------------


class EmptyInputTests(unittest.TestCase):
    def test_empty_string_returns_empty_list(self):
        self.assertEqual(segment_notes_for_subtitles_via_boundary_engine(""), [])

    def test_none_input_returns_empty_list(self):
        self.assertEqual(segment_notes_for_subtitles_via_boundary_engine(None), [])

    def test_whitespace_only_input_returns_empty_list(self):
        self.assertEqual(segment_notes_for_subtitles_via_boundary_engine("   \n   \n  "), [])


# ---------------------------------------------------------------------------
# 3. Single segment
# ---------------------------------------------------------------------------


class SingleSegmentTests(unittest.TestCase):
    def test_short_sentence_produces_one_segment(self):
        text = "This is a short sentence."
        result = segment_notes_for_subtitles_via_boundary_engine(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source_start_offset"], 0)
        self.assertEqual(result[0]["source_end_offset"], len(text))

    def test_short_cjk_sentence_produces_one_segment(self):
        text = "這是一個簡短的句子。"
        result = segment_notes_for_subtitles_via_boundary_engine(text)
        self.assertEqual(len(result), 1)


# ---------------------------------------------------------------------------
# 4. Multiple segments
# ---------------------------------------------------------------------------


class MultipleSegmentsTests(unittest.TestCase):
    def test_long_text_produces_multiple_segments(self):
        text = "這是第一句話。這是第二句話。這是第三句話，內容比較長一點。這是第四句話。"
        result = segment_notes_for_subtitles_via_boundary_engine(text, max_display_width=16)
        self.assertGreater(len(result), 1)

    def test_segments_are_in_reading_order(self):
        text = "這是第一句話。這是第二句話。這是第三句話，內容比較長一點。這是第四句話。"
        result = segment_notes_for_subtitles_via_boundary_engine(text, max_display_width=16)
        starts = [entry["source_start_offset"] for entry in result]
        self.assertEqual(starts, sorted(starts))


# ---------------------------------------------------------------------------
# 5. Offset preservation
# ---------------------------------------------------------------------------


class OffsetPreservationTests(unittest.TestCase):
    def test_offsets_refer_to_original_text_exactly(self):
        text = "第一段話比較短。\n第二段話內容稍微長一些，用來測試分段行為。"
        result = segment_notes_for_subtitles_via_boundary_engine(text, max_display_width=14)
        for entry in result:
            start, end = entry["source_start_offset"], entry["source_end_offset"]
            self.assertTrue(0 <= start < end <= len(text))

    def test_offsets_are_contiguous_within_a_paragraph(self):
        # Each paragraph's segments should tile it exactly (no gaps, no
        # overlaps) - offsets come straight from Phase 2D's own SubtitleSegment
        # spans, which are contiguous by construction.
        text = "第一段話內容稍微長一些用來測試分段行為與偏移量的正確性維持"
        result = segment_notes_for_subtitles_via_boundary_engine(text, max_display_width=14)
        for prev, nxt in zip(result, result[1:]):
            self.assertEqual(prev["source_end_offset"], nxt["source_start_offset"])

    def test_offsets_survive_display_text_stripping(self):
        # The display "text" field may be shorter than text[start:end] (due
        # to whitespace normalization / trailing punctuation stripping), but
        # start/end must always still be raw offsets into the original text,
        # never recomputed from the stripped display text.
        text = "會議時間是 10:30。"
        result = segment_notes_for_subtitles_via_boundary_engine(text)
        self.assertEqual(len(result), 1)
        entry = result[0]
        raw_slice = text[entry["source_start_offset"] : entry["source_end_offset"]]
        self.assertIn(entry["text"], raw_slice)


# ---------------------------------------------------------------------------
# 6. Text extraction / display-text construction
# ---------------------------------------------------------------------------


class TextExtractionTests(unittest.TestCase):
    def test_trailing_rhythmic_punctuation_is_stripped(self):
        text = "這是一句話，"
        result = segment_notes_for_subtitles_via_boundary_engine(text)
        self.assertEqual(len(result), 1)
        self.assertFalse(result[0]["text"].endswith("，"))

    def test_question_and_exclaim_marks_are_kept(self):
        text = "真的嗎？"
        result = segment_notes_for_subtitles_via_boundary_engine(text)
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]["text"].endswith("？"))

    def test_display_text_matches_subtitle_segmenter_private_helpers_directly(self):
        # Whenever the adapter's chosen span exactly matches a span
        # subtitle_segmenter.py would have chosen, the displayed text must
        # be byte-for-byte identical - both go through the exact same
        # private helper functions (see module docstring's "DISPLAY TEXT
        # CONSTRUCTION").
        from src.subtitle_segmenter import _display_text_for_span, _strip_trailing_punctuation

        text = "這是一個重要結論：我們必須繼續。"
        result = segment_notes_for_subtitles_via_boundary_engine(text)
        self.assertEqual(len(result), 1)
        entry = result[0]
        expected = _strip_trailing_punctuation(
            _display_text_for_span(text, entry["source_start_offset"], entry["source_end_offset"])
        )
        self.assertEqual(entry["text"], expected)

    def test_segment_with_empty_display_text_is_skipped(self):
        # A pathological span that strips down to nothing must not appear
        # in the output - mirrors subtitle_segmenter.segment_notes_for_subtitles's
        # own "if not display_text: continue" rule.
        text = "。。。"
        result = segment_notes_for_subtitles_via_boundary_engine(text)
        for entry in result:
            self.assertTrue(entry["text"])


# ---------------------------------------------------------------------------
# 7. Paragraph handling
# ---------------------------------------------------------------------------


class ParagraphHandlingTests(unittest.TestCase):
    def test_paragraphs_never_merge_across_newline(self):
        text = "第一段。\n第二段。"
        result = segment_notes_for_subtitles_via_boundary_engine(text)
        for entry in result:
            self.assertNotIn("\n", text[entry["source_start_offset"] : entry["source_end_offset"]])

    def test_blank_paragraph_is_skipped_but_still_separates(self):
        text = "第一段內容。\n\n第二段內容。"
        result = segment_notes_for_subtitles_via_boundary_engine(text)
        combined = "".join(entry["text"] for entry in result)
        self.assertNotIn("\n", combined)
        self.assertEqual(len(result), 2)

    def test_multiple_paragraphs_all_represented(self):
        text = "第一段話。\n第二段話。\n第三段話。"
        result = segment_notes_for_subtitles_via_boundary_engine(text)
        self.assertEqual(len(result), 3)


# ---------------------------------------------------------------------------
# 8. Width constraint propagation
# ---------------------------------------------------------------------------


class WidthConstraintPropagationTests(unittest.TestCase):
    def test_smaller_max_width_produces_more_segments(self):
        text = "這是第一句話。這是第二句話。這是第三句話，內容比較長一點。這是第四句話。"
        wide = segment_notes_for_subtitles_via_boundary_engine(text, max_display_width=36)
        narrow = segment_notes_for_subtitles_via_boundary_engine(text, max_display_width=10)
        self.assertGreaterEqual(len(narrow), len(wide))

    def test_max_display_width_is_actually_passed_through(self):
        # A width so small it forces heavy last-resort splitting - if
        # max_display_width were silently ignored (e.g. a bug always using
        # the default), this would produce far fewer, wider segments.
        text = "abcdefghijklmnopqrstuvwxyz"
        result = segment_notes_for_subtitles_via_boundary_engine(text, max_display_width=4)
        self.assertGreater(len(result), 1)


# ---------------------------------------------------------------------------
# 9. Contract compatibility with subtitle_segmenter.segment_notes_for_subtitles
# ---------------------------------------------------------------------------


class ContractCompatibilityTests(unittest.TestCase):
    def test_same_key_set_as_production_function(self):
        text = "這是一句用來比較欄位名稱的句子。"
        adapter_result = segment_notes_for_subtitles_via_boundary_engine(text)
        production_result = segment_notes_for_subtitles(text)
        self.assertTrue(adapter_result)
        self.assertTrue(production_result)
        self.assertEqual(set(adapter_result[0].keys()), set(production_result[0].keys()))

    def test_offsets_index_into_the_same_original_string_convention(self):
        text = "第一句話。第二句話。"
        adapter_result = segment_notes_for_subtitles_via_boundary_engine(text)
        for entry in adapter_result:
            self.assertEqual(
                text[entry["source_start_offset"] : entry["source_end_offset"]].strip("\n"),
                text[entry["source_start_offset"] : entry["source_end_offset"]],
            )


# ---------------------------------------------------------------------------
# 10. Deterministic behavior
# ---------------------------------------------------------------------------


class DeterminismTests(unittest.TestCase):
    def test_repeated_calls_are_identical(self):
        text = "這是一段比較長的內容，用來確認多次呼叫得到完全一致的結果，沒有任何隨機性。"
        first = segment_notes_for_subtitles_via_boundary_engine(text, max_display_width=18)
        second = segment_notes_for_subtitles_via_boundary_engine(text, max_display_width=18)
        self.assertEqual(first, second)

    def test_does_not_mutate_input_text_object_identity_irrelevant(self):
        # str is immutable in Python, but confirm the function doesn't raise
        # or behave differently when the same literal text object is reused.
        text = "重複使用同一個字串物件。"
        segment_notes_for_subtitles_via_boundary_engine(text)
        self.assertEqual(text, "重複使用同一個字串物件。")


# ---------------------------------------------------------------------------
# 11. Colon pass-through (binding constraint - Round 6 decision)
# ---------------------------------------------------------------------------


class ColonPassThroughTests(unittest.TestCase):
    def test_ascii_colon_is_not_treated_as_a_forced_break(self):
        # Short enough to fit on one line - if the adapter added any
        # colon-specific splitting rule, this would still be one segment
        # (colon alone, with no width pressure, never forces a split in
        # either system) - this test instead confirms the colon character
        # survives *inside* the single segment's text, untouched.
        text = "Key: Value"
        result = segment_notes_for_subtitles_via_boundary_engine(text)
        self.assertEqual(len(result), 1)
        self.assertIn(":", result[0]["text"])

    def test_fullwidth_colon_is_not_treated_as_a_forced_break(self):
        text = "主題：內容"
        result = segment_notes_for_subtitles_via_boundary_engine(text)
        self.assertEqual(len(result), 1)
        self.assertIn("：", result[0]["text"])

    def test_colon_classification_is_read_verbatim_from_boundary_classification(self):
        # Direct evidence that no colon-specific compatibility logic exists
        # in this adapter: the classification of the colon boundary itself
        # (via the unmodified Phase 2B module) is OTHER, exactly as
        # documented and confirmed by the Round 6 investigation.
        from src.boundary_classification import BoundaryClass, classify_boundaries
        from src.boundary_observation import observe_boundaries
        from src.text_structure import analyze_text_structure

        text = "主題：內容"
        colon_position = text.index("：") + 1
        candidates = observe_boundaries(analyze_text_structure(text))
        classified = {c.candidate.position: c.boundary_class for c in classify_boundaries(candidates)}
        self.assertEqual(classified[colon_position], BoundaryClass.OTHER)

    def test_long_text_with_colon_still_produces_valid_contiguous_segments(self):
        # Colon-adjacent divergence from production is expected (tracked by
        # the shadow harness) - this test only asserts the adapter's own
        # internal contract (contiguous, in-bounds offsets) still holds.
        text = "這是一個非常長的重要結論內容說明：我們接下來必須要繼續往前推進工作"
        result = segment_notes_for_subtitles_via_boundary_engine(text, max_display_width=20)
        self.assertGreater(len(result), 1)
        for prev, nxt in zip(result, result[1:]):
            self.assertEqual(prev["source_end_offset"], nxt["source_start_offset"])


# ---------------------------------------------------------------------------
# 12. Numeric-literal behavior (documented shared gap, not adapter-introduced)
# ---------------------------------------------------------------------------


class NumericLiteralBehaviorTests(unittest.TestCase):
    def test_time_notation_is_protected_when_it_fits_on_one_line(self):
        text = "會議時間是 10:30。"
        result = segment_notes_for_subtitles_via_boundary_engine(text)
        self.assertEqual(len(result), 1)
        self.assertIn("10:30", result[0]["text"])

    def test_ratio_notation_is_not_specially_protected(self):
        # "16:9" is not protected as an atomic unit by Phase 1-2C (shared,
        # pre-existing, documented gap - see module docstring). This test
        # pins the adapter's actual behavior (it fits on one line here, so
        # no split occurs), not a claim that protection exists.
        text = "比例為 16:9。"
        result = segment_notes_for_subtitles_via_boundary_engine(text)
        self.assertEqual(len(result), 1)
        self.assertIn("16:9", result[0]["text"])


# ---------------------------------------------------------------------------
# 13. Malformed / edge-case input handling
# ---------------------------------------------------------------------------


class MalformedInputHandlingTests(unittest.TestCase):
    def test_integer_input_is_stringified_like_production(self):
        # Mirrors subtitle_segmenter.segment_notes_for_subtitles's own
        # `text = str(text or "")` leniency exactly.
        result = segment_notes_for_subtitles_via_boundary_engine(12345)  # type: ignore[arg-type]
        self.assertIsInstance(result, list)

    def test_zero_is_treated_as_falsy_like_production(self):
        result = segment_notes_for_subtitles_via_boundary_engine(0)  # type: ignore[arg-type]
        self.assertEqual(result, [])

    def test_non_positive_max_display_width_raises(self):
        with self.assertRaises(ValueError):
            segment_notes_for_subtitles_via_boundary_engine("Hello.", max_display_width=0)
        with self.assertRaises(ValueError):
            segment_notes_for_subtitles_via_boundary_engine("Hello.", max_display_width=-1)


# ---------------------------------------------------------------------------
# 14. Short-input contract (newly observed edge case - documented, not fixed)
# ---------------------------------------------------------------------------


class ShortInputContractTests(unittest.TestCase):
    """Pins the adapter's actual, documented behavior for total input text
    of 0 or 1 characters - see module docstring's "A SEPARATE, NEWLY
    OBSERVED EDGE CASE". This is NOT an assertion that the adapter matches
    production here (it does not - see this round's implementation
    report); it only pins the adapter's own real behavior so any future
    change to it is a deliberate, visible decision.
    """

    def test_single_ascii_character_returns_empty_list(self):
        self.assertEqual(segment_notes_for_subtitles_via_boundary_engine("A"), [])

    def test_single_cjk_character_returns_empty_list(self):
        self.assertEqual(segment_notes_for_subtitles_via_boundary_engine("好"), [])

    def test_two_character_input_is_not_affected(self):
        # Confirms the gap is specific to 0-1 character total input, not a
        # general short-input problem.
        result = segment_notes_for_subtitles_via_boundary_engine("AB")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "AB")

    def test_single_character_paragraph_within_a_longer_document_is_not_lost(self):
        # A single-character *paragraph* is fine as long as the overall
        # document has >= 2 characters (candidates are computed globally,
        # not per-paragraph) - only a totally empty/near-empty whole
        # document triggers the gap. See module docstring.
        text = "A\nBCDEFGHIJKL"
        result = segment_notes_for_subtitles_via_boundary_engine(text)
        combined = "".join(entry["text"] for entry in result)
        self.assertIn("A", combined)


if __name__ == "__main__":
    unittest.main()
