import unittest
from typing import List, Optional

from src.boundary_observation import (
    BoundaryCandidate,
    BoundaryFeatures,
    CharacterClass,
    PunctuationSequenceState,
    SpanRef,
    StructuralBoundaryContext,
    classify_character,
    observe_boundaries,
)
from src.text_structure import analyze_text_structure


def _candidate_at(candidates, position) -> Optional[BoundaryCandidate]:
    for c in candidates:
        if c.position == position:
            return c
    return None


def _observe(text: str):
    return observe_boundaries(analyze_text_structure(text))


# ---------------------------------------------------------------------------
# CharacterClass
# ---------------------------------------------------------------------------


class CharacterClassTests(unittest.TestCase):
    def test_whitespace(self):
        for ch in (" ", "\n", "\t", "　"):
            self.assertEqual(classify_character(ch), CharacterClass.WHITESPACE, ch)

    def test_digit(self):
        for ch in ("5", "0", "９"):  # ASCII and fullwidth digit
            self.assertEqual(classify_character(ch), CharacterClass.DIGIT, ch)

    def test_punctuation(self):
        for ch in ("，", ",", "。", ".", "！", "!", "（", ")"):
            self.assertEqual(classify_character(ch), CharacterClass.PUNCTUATION, ch)

    def test_emoji(self):
        for ch in ("😀", "🚀", "🙂"):
            self.assertEqual(classify_character(ch), CharacterClass.EMOJI, ch)

    def test_symbol(self):
        for ch in ("+", "=", "$", "<"):
            self.assertEqual(classify_character(ch), CharacterClass.SYMBOL, ch)

    def test_other(self):
        # Private Use Area character: no Unicode name, not punctuation,
        # not a symbol category - falls through to OTHER.
        self.assertEqual(classify_character(""), CharacterClass.OTHER)

    def test_cjk_han(self):
        for ch in "中文":
            self.assertEqual(classify_character(ch), CharacterClass.CJK, ch)

    def test_cjk_japanese_mixed_kanji_and_kana(self):
        for ch in "日本語":
            self.assertEqual(classify_character(ch), CharacterClass.CJK, ch)

    def test_cjk_hiragana_katakana_explicit(self):
        for ch in ("の", "ア"):  # hiragana, katakana
            self.assertEqual(classify_character(ch), CharacterClass.CJK, ch)

    def test_cjk_korean_hangul(self):
        for ch in "한국어":
            self.assertEqual(classify_character(ch), CharacterClass.CJK, ch)

    def test_latin_ascii(self):
        for ch in "ABC":
            self.assertEqual(classify_character(ch), CharacterClass.LATIN, ch)

    def test_latin_fullwidth(self):
        for ch in "ＡＢＣ":
            self.assertEqual(classify_character(ch), CharacterClass.LATIN, ch)

    def test_latin_fullwidth_lowercase(self):
        for ch in "ａｂｃ":
            self.assertEqual(classify_character(ch), CharacterClass.LATIN, ch)

    def test_cjk_and_latin_do_not_cross_classify(self):
        # A coarse but still meaningful boundary: CJK ideographs must never
        # be classified as LATIN and vice versa.
        self.assertNotEqual(classify_character("中"), CharacterClass.LATIN)
        self.assertNotEqual(classify_character("A"), CharacterClass.CJK)


# ---------------------------------------------------------------------------
# Boundary positions
# ---------------------------------------------------------------------------


class BoundaryPositionTests(unittest.TestCase):
    def test_no_candidates_for_empty_text(self):
        self.assertEqual(_observe(""), ())

    def test_no_candidates_for_single_character(self):
        self.assertEqual(_observe("A"), ())

    def test_first_internal_boundary(self):
        candidates = _observe("ABCDE")
        self.assertEqual(candidates[0].position, 1)

    def test_last_internal_boundary(self):
        text = "ABCDE"
        candidates = _observe(text)
        self.assertEqual(candidates[-1].position, len(text) - 1)

    def test_no_position_zero_candidate(self):
        candidates = _observe("ABCDE")
        self.assertIsNone(_candidate_at(candidates, 0))

    def test_no_position_len_text_candidate(self):
        text = "ABCDE"
        candidates = _observe(text)
        self.assertIsNone(_candidate_at(candidates, len(text)))

    def test_candidate_count_matches_internal_gap_count(self):
        text = "ABCDE"
        candidates = _observe(text)
        self.assertEqual(len(candidates), len(text) - 1)

    def test_left_and_right_char_are_correct(self):
        candidates = _observe("AB")
        candidate = _candidate_at(candidates, 1)
        assert candidate is not None
        self.assertEqual(candidate.left_char, "A")
        self.assertEqual(candidate.right_char, "B")


# ---------------------------------------------------------------------------
# PunctuationSequenceState
# ---------------------------------------------------------------------------


class PunctuationSequenceStateTests(unittest.TestCase):
    def test_none_when_unrelated_to_any_sequence(self):
        candidates = _observe("ABCDE")
        candidate = _candidate_at(candidates, 2)
        assert candidate is not None
        self.assertEqual(candidate.features.punctuation_sequence_state, PunctuationSequenceState.NONE)

    def test_internal_boundary_inside_ellipsis_run(self):
        text = "很好……嗎"
        # "……" occupies positions [2, 4); the boundary strictly between the
        # two "…" characters (position 3) is INTERNAL.
        candidates = _observe(text)
        candidate = _candidate_at(candidates, 3)
        assert candidate is not None
        self.assertEqual(candidate.features.punctuation_sequence_state, PunctuationSequenceState.INTERNAL)

    def test_end_boundary_immediately_after_sequence(self):
        text = "很好……嗎"
        # position 4 is exactly where the "……" sequence ends.
        candidates = _observe(text)
        candidate = _candidate_at(candidates, 4)
        assert candidate is not None
        self.assertEqual(candidate.features.punctuation_sequence_state, PunctuationSequenceState.END)

    def test_end_boundary_after_interrobang_sequence(self):
        text = "很好？！嗎"
        candidates = _observe(text)
        candidate = _candidate_at(candidates, 4)
        assert candidate is not None
        self.assertEqual(candidate.features.punctuation_sequence_state, PunctuationSequenceState.END)

    def test_internal_boundary_inside_ascii_ellipsis_run(self):
        text = "ok......go"
        # "......" occupies positions [2, 8); pick a strictly-internal gap.
        candidates = _observe(text)
        candidate = _candidate_at(candidates, 5)
        assert candidate is not None
        self.assertEqual(candidate.features.punctuation_sequence_state, PunctuationSequenceState.INTERNAL)


# ---------------------------------------------------------------------------
# StructuralBoundaryContext
# ---------------------------------------------------------------------------


class StructuralRelationTests(unittest.TestCase):
    def test_containing_span(self):
        text = "（MT8395）"
        candidates = _observe(text)
        # Position 2 sits strictly inside the parenthetical.
        candidate = _candidate_at(candidates, 2)
        assert candidate is not None
        types = {(s.type, s.subtype) for s in candidate.features.structural_context.containing_spans}
        self.assertIn(("paired_delimiter", "parenthetical"), types)

    def test_left_adjacent_span(self):
        text = "（MT8395）之後"
        candidates = _observe(text)
        close_position = text.index("）") + 1
        candidate = _candidate_at(candidates, close_position)
        assert candidate is not None
        types = {(s.type, s.subtype) for s in candidate.features.structural_context.left_adjacent_spans}
        self.assertIn(("paired_delimiter", "parenthetical"), types)
        # A span ending exactly at the boundary is left-adjacent, not containing.
        containing_types = {
            (s.type, s.subtype) for s in candidate.features.structural_context.containing_spans
        }
        self.assertNotIn(("paired_delimiter", "parenthetical"), containing_types)

    def test_right_adjacent_span(self):
        text = "之前（MT8395）"
        candidates = _observe(text)
        open_position = text.index("（")
        candidate = _candidate_at(candidates, open_position)
        assert candidate is not None
        types = {(s.type, s.subtype) for s in candidate.features.structural_context.right_adjacent_spans}
        self.assertIn(("paired_delimiter", "parenthetical"), types)
        containing_types = {
            (s.type, s.subtype) for s in candidate.features.structural_context.containing_spans
        }
        self.assertNotIn(("paired_delimiter", "parenthetical"), containing_types)

    def test_nested_containing_spans_ordered_outer_to_inner(self):
        text = "《「很好！」》"
        candidates = _observe(text)
        # Position just before "！" is inside both the outer title_mark and
        # the inner quotation.
        bang_position = text.index("！")
        candidate = _candidate_at(candidates, bang_position)
        assert candidate is not None
        containing = candidate.features.structural_context.containing_spans
        subtypes_in_order = [s.subtype for s in containing if s.type == "paired_delimiter"]
        self.assertEqual(subtypes_in_order, ["title_mark", "quotation"])

    def test_exact_span_boundary_is_not_containing(self):
        text = "（MT8395）"
        candidates = _observe(text)
        start_position = text.index("（")
        end_position = text.index("）") + 1
        for position in (start_position, end_position):
            candidate = _candidate_at(candidates, position)
            if candidate is None:
                continue  # position 0 / len(text) never produce a candidate
            containing_types = {
                (s.type, s.subtype) for s in candidate.features.structural_context.containing_spans
            }
            self.assertNotIn(("paired_delimiter", "parenthetical"), containing_types)


# ---------------------------------------------------------------------------
# Sentence-final evidence
# ---------------------------------------------------------------------------


class SentenceFinalEvidenceTests(unittest.TestCase):
    def _evidence_at_end(self, text: str) -> bool:
        """Evidence for the boundary immediately after all of `text`."""
        # Pad with a space (not a word character) so this never accidentally
        # breaks a `\b`-bounded emoticon match (e.g. "XD") at the end of `text`.
        padded = text + " "
        candidates = _observe(padded)
        candidate = _candidate_at(candidates, len(text))
        assert candidate is not None
        return candidate.features.contains_sentence_final_punctuation

    def test_direct_full_stop(self):
        self.assertTrue(self._evidence_at_end("很好。"))

    def test_direct_ascii_full_stop(self):
        # A single, un-spanned ASCII "." (no run, so no punctuation_sequence
        # span) is still explicit sentence-final evidence at the bare
        # fallback layer - contrast with test_ellipsis_ascii_is_not_sentence_final,
        # where 2+ dots form an ellipsis-family sequence instead.
        self.assertTrue(self._evidence_at_end("Done."))

    def test_direct_exclaim(self):
        self.assertTrue(self._evidence_at_end("很好！"))

    def test_direct_question(self):
        self.assertTrue(self._evidence_at_end("很好？"))

    def test_interrobang_cjk(self):
        self.assertTrue(self._evidence_at_end("很好？！"))

    def test_interrobang_ascii(self):
        self.assertTrue(self._evidence_at_end("ok?!"))

    def test_repeated_exclaim_ascii(self):
        self.assertTrue(self._evidence_at_end("ok!!!"))

    def test_repeated_question_ascii(self):
        self.assertTrue(self._evidence_at_end("ok???"))

    def test_ellipsis_cjk_is_not_sentence_final(self):
        self.assertFalse(self._evidence_at_end("很好……"))

    def test_ellipsis_ascii_is_not_sentence_final(self):
        self.assertFalse(self._evidence_at_end("ok......"))

    def test_ellipsis_then_question_is_sentence_final(self):
        self.assertTrue(self._evidence_at_end("很好……？"))

    def test_ellipsis_then_exclaim_is_sentence_final(self):
        self.assertTrue(self._evidence_at_end("很好……！"))

    def test_ellipsis_then_interrobang_is_sentence_final(self):
        self.assertTrue(self._evidence_at_end("很好……？！"))

    def test_comma_is_not_sentence_final(self):
        self.assertFalse(self._evidence_at_end("很好，"))

    def test_closing_quote_after_sentence_final_punctuation(self):
        self.assertTrue(self._evidence_at_end("「很好！」"))

    def test_closing_quote_without_sentence_final_punctuation(self):
        self.assertFalse(self._evidence_at_end("「很好」"))

    def test_nested_closing_delimiters(self):
        self.assertTrue(self._evidence_at_end("《「很好！」》"))

    def test_emoji_attachment_after_sentence_final_punctuation(self):
        self.assertTrue(self._evidence_at_end("很好！😂"))

    def test_emoticon_attachment_after_sentence_final_punctuation(self):
        self.assertTrue(self._evidence_at_end("很好！XD"))

    def test_closing_quote_with_emoji_attachment_inside(self):
        self.assertTrue(self._evidence_at_end("「很好！😂」"))

    def test_composition_not_last_character_when_punctuation_reordered(self):
        # The punctuation_sequence span is "？……" - it CONTAINS "？" and must
        # be reported True even though the literal last character before the
        # boundary is "…", not "？". This is what distinguishes "inspect the
        # sequence's composition" from "check only the last character".
        self.assertTrue(self._evidence_at_end("「你好？……」"))

    def test_ordinary_text_terminates_the_chain(self):
        self.assertFalse(self._evidence_at_end("這是很好的一天"))

    def test_whitespace_between_punctuation_and_closing_delimiter_breaks_the_chain(self):
        # A space directly before the closing delimiter is ordinary content;
        # the chain must not look past it to the "！！" further back.
        self.assertFalse(self._evidence_at_end("「你好！！ 」"))


# ---------------------------------------------------------------------------
# Determinism / no hidden state
# ---------------------------------------------------------------------------


class DeterminismTests(unittest.TestCase):
    def test_same_input_produces_equal_output(self):
        text = "《「很好！😂」》這是測試 3.14 ok?! ......"
        analysis = analyze_text_structure(text)
        first = observe_boundaries(analysis)
        second = observe_boundaries(analysis)
        self.assertEqual(first, second)

    def test_no_candidate_carries_score_weight_or_should_cut_fields(self):
        text = "很好！下一句"
        candidates = _observe(text)
        for candidate in candidates:
            field_names = set(candidate.features.__dataclass_fields__.keys())
            self.assertTrue(field_names.issubset({
                "left_character_class",
                "right_character_class",
                "character_class_transition",
                "punctuation_sequence_state",
                "contains_sentence_final_punctuation",
                "structural_context",
            }))
