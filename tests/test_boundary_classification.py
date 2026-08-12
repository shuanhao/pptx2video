import unittest
from typing import Optional, Sequence, Tuple

from src.boundary_classification import (
    BoundaryClass,
    ClassifiedBoundary,
    classify_boundaries,
    classify_boundary,
)
from src.boundary_observation import (
    BoundaryCandidate,
    BoundaryFeatures,
    CharacterClass,
    PunctuationSequenceState,
    SpanRef,
    StructuralBoundaryContext,
    observe_boundaries,
)
from src.text_structure import analyze_text_structure


def _observe(text: str) -> Tuple[BoundaryCandidate, ...]:
    return observe_boundaries(analyze_text_structure(text))


def _candidate_at(candidates: Sequence[BoundaryCandidate], position: int) -> Optional[BoundaryCandidate]:
    for c in candidates:
        if c.position == position:
            return c
    return None


def _classify_at(text: str, position: int) -> BoundaryClass:
    candidate = _candidate_at(_observe(text), position)
    assert candidate is not None, f"no boundary candidate at position {position} in {text!r}"
    return classify_boundary(candidate)


def _classify_at_end(text: str) -> BoundaryClass:
    """Classify the boundary immediately after all of `text`. Pads with a
    space (not a word character) so this never accidentally breaks a
    `\\b`-bounded emoticon match at the end of `text` - same rationale as
    the equivalent helper in test_boundary_observation.py.
    """
    padded = text + " "
    return _classify_at(padded, len(text))


def _make_candidate(
    position: int = 1,
    left_char: str = "X",
    right_char: str = "Y",
    contains_sentence_final_punctuation: bool = False,
    punctuation_sequence_state: PunctuationSequenceState = PunctuationSequenceState.NONE,
    containing_spans: Tuple[SpanRef, ...] = (),
    left_adjacent_spans: Tuple[SpanRef, ...] = (),
    right_adjacent_spans: Tuple[SpanRef, ...] = (),
    left_character_class: CharacterClass = CharacterClass.OTHER,
    right_character_class: CharacterClass = CharacterClass.OTHER,
    character_class_transition: bool = False,
) -> BoundaryCandidate:
    """Build a synthetic BoundaryCandidate directly, bypassing Phase 1/2A
    entirely. Used only for evidence combinations that the real pipeline
    cannot produce (see the module contract's testing correction 6) - e.g.
    simultaneous SENTENCE_FINAL-shaped and CLAUSE-shaped evidence at one
    boundary, which never co-occurs in real text because the character
    sets involved are disjoint by construction (see
    src/boundary_classification.py's module docstring).
    """
    context = StructuralBoundaryContext(
        containing_spans=containing_spans,
        left_adjacent_spans=left_adjacent_spans,
        right_adjacent_spans=right_adjacent_spans,
    )
    features = BoundaryFeatures(
        left_character_class=left_character_class,
        right_character_class=right_character_class,
        character_class_transition=character_class_transition,
        punctuation_sequence_state=punctuation_sequence_state,
        contains_sentence_final_punctuation=contains_sentence_final_punctuation,
        structural_context=context,
    )
    return BoundaryCandidate(position=position, left_char=left_char, right_char=right_char, features=features)


# ---------------------------------------------------------------------------
# A. SENTENCE_FINAL
# ---------------------------------------------------------------------------


class SentenceFinalTests(unittest.TestCase):
    def test_cjk_full_stop(self):
        self.assertEqual(_classify_at_end("你好。"), BoundaryClass.SENTENCE_FINAL)

    def test_cjk_question(self):
        self.assertEqual(_classify_at_end("真的嗎？"), BoundaryClass.SENTENCE_FINAL)

    def test_cjk_exclaim(self):
        self.assertEqual(_classify_at_end("太好了！"), BoundaryClass.SENTENCE_FINAL)

    def test_ascii_full_stop(self):
        self.assertEqual(_classify_at_end("Hello."), BoundaryClass.SENTENCE_FINAL)

    def test_ascii_question(self):
        self.assertEqual(_classify_at_end("Really?"), BoundaryClass.SENTENCE_FINAL)

    def test_cjk_interrobang(self):
        self.assertEqual(_classify_at_end("真的？！"), BoundaryClass.SENTENCE_FINAL)

    def test_ascii_interrobang(self):
        self.assertEqual(_classify_at_end("真的?!"), BoundaryClass.SENTENCE_FINAL)

    def test_ellipsis_then_question(self):
        self.assertEqual(_classify_at_end("真的……？"), BoundaryClass.SENTENCE_FINAL)

    def test_ellipsis_then_exclaim(self):
        self.assertEqual(_classify_at_end("真的……！"), BoundaryClass.SENTENCE_FINAL)


# ---------------------------------------------------------------------------
# B. Terminal attachment
# ---------------------------------------------------------------------------


class TerminalAttachmentTests(unittest.TestCase):
    def test_closing_quote(self):
        self.assertEqual(_classify_at_end("「真的很好！」"), BoundaryClass.SENTENCE_FINAL)

    def test_nested_closing_delimiters(self):
        self.assertEqual(_classify_at_end("《「真的很好！」》"), BoundaryClass.SENTENCE_FINAL)

    def test_closing_quote_with_emoji(self):
        self.assertEqual(_classify_at_end("「真的很好！」😂"), BoundaryClass.SENTENCE_FINAL)

    def test_emoticon_attachment(self):
        self.assertEqual(_classify_at_end("真的很好！XD"), BoundaryClass.SENTENCE_FINAL)


# ---------------------------------------------------------------------------
# C. ELLIPSIS
# ---------------------------------------------------------------------------


class EllipsisTests(unittest.TestCase):
    def test_cjk_ellipsis(self):
        self.assertEqual(_classify_at_end("真的……"), BoundaryClass.ELLIPSIS)

    def test_ascii_ellipsis(self):
        self.assertEqual(_classify_at_end("嗯......"), BoundaryClass.ELLIPSIS)

    def test_ellipsis_then_question_is_sentence_final_not_ellipsis(self):
        self.assertEqual(_classify_at_end("真的……？"), BoundaryClass.SENTENCE_FINAL)

    def test_ellipsis_then_exclaim_is_sentence_final_not_ellipsis(self):
        self.assertEqual(_classify_at_end("真的……！"), BoundaryClass.SENTENCE_FINAL)

    def test_internal_ellipsis_boundary_is_not_ellipsis(self):
        # "……" + "……" is one merged, contiguous punctuation_sequence span
        # (Phase 1 merges adjacent runs of sequence characters) - the
        # boundary strictly between the two halves is INTERNAL, not END.
        text = "……" + "……"
        self.assertEqual(_classify_at(text, 2), BoundaryClass.OTHER)


# ---------------------------------------------------------------------------
# D. CLAUSE
# ---------------------------------------------------------------------------


class ClauseTests(unittest.TestCase):
    def test_cjk_comma(self):
        self.assertEqual(_classify_at("第一，第二", 3), BoundaryClass.CLAUSE)

    def test_cjk_semicolon(self):
        self.assertEqual(_classify_at("第一；第二", 3), BoundaryClass.CLAUSE)

    def test_cjk_enumeration_comma(self):
        self.assertEqual(_classify_at("CPU、GPU", 4), BoundaryClass.CLAUSE)

    def test_ascii_comma(self):
        self.assertEqual(_classify_at("First,we continue", 6), BoundaryClass.CLAUSE)

    def test_ascii_semicolon(self):
        self.assertEqual(_classify_at("First;we continue", 6), BoundaryClass.CLAUSE)


# ---------------------------------------------------------------------------
# E. Technical / atomic protection
# ---------------------------------------------------------------------------


class TechnicalProtectionTests(unittest.TestCase):
    def test_comma_inside_thousands_separated_number_is_not_clause(self):
        # "1,000" is one atomic/numeric span; the comma sits strictly
        # inside it. This is the one case among these three that actually
        # exercises the protection logic - see the approved plan's note
        # that "3.|14"/"v1.|2.3" already resolve to OTHER purely because
        # "." was never a v1 clause character to begin with.
        self.assertEqual(_classify_at("1,000", 2), BoundaryClass.OTHER)

    def test_decimal_point_is_not_clause_and_not_a_protection_exerciser(self):
        self.assertEqual(_classify_at("3.14", 1), BoundaryClass.OTHER)

    def test_version_string_dot_is_not_clause_and_not_a_protection_exerciser(self):
        self.assertEqual(_classify_at("v1.2.3", 2), BoundaryClass.OTHER)

    def test_synthetic_clause_char_inside_technical_span_is_blocked(self):
        # Direct, controlled exercise of the protection mechanism itself:
        # a clause character whose only containing span is `technical`.
        candidate = _make_candidate(
            left_char="，",
            containing_spans=(SpanRef(start=0, end=10, type="technical", subtype="identifier"),),
        )
        self.assertEqual(classify_boundary(candidate), BoundaryClass.OTHER)

    def test_synthetic_clause_char_inside_atomic_span_is_blocked(self):
        candidate = _make_candidate(
            left_char="；",
            containing_spans=(SpanRef(start=0, end=10, type="atomic", subtype="numeric"),),
        )
        self.assertEqual(classify_boundary(candidate), BoundaryClass.OTHER)

    def test_synthetic_clause_char_inside_paired_delimiter_is_not_blocked(self):
        # Directly proves decision 5: paired_delimiter is NOT a blocking
        # structure - only atomic/technical are.
        candidate = _make_candidate(
            left_char="，",
            containing_spans=(SpanRef(start=0, end=10, type="paired_delimiter", subtype="quotation"),),
        )
        self.assertEqual(classify_boundary(candidate), BoundaryClass.CLAUSE)


# ---------------------------------------------------------------------------
# E2. ASCII "." bare-fallback correction (Phase 2C ASCII Period Upstream
# Correction, Round A/B - see
# docs/phase2c/decisions/PHASE_2C_ASCII_PERIOD_UPSTREAM_CORRECTION_DECISION.md).
#
# These positions previously misclassified as SENTENCE_FINAL because Phase
# 2A's bare fallback leaked `contains_sentence_final_punctuation = True` for
# a "." strictly interior to a technical/atomic/punctuation_sequence span.
# With that upstream evidence corrected, Phase 2B's own classification logic
# is unchanged and now naturally resolves these to OTHER (not SENTENCE_FINAL,
# not CLAUSE - "." is never a clause character; not ELLIPSIS - these
# positions are not at the END of a punctuation_sequence).
# ---------------------------------------------------------------------------


class AsciiPeriodBareFallbackClassificationCorrectionTests(unittest.TestCase):
    def test_ascii_ellipsis_interior_position_is_other_not_sentence_final(self):
        self.assertEqual(_classify_at("......", 3), BoundaryClass.OTHER)

    def test_decimal_interior_period_is_other_not_sentence_final(self):
        self.assertEqual(_classify_at("3.14", 2), BoundaryClass.OTHER)

    def test_version_string_interior_periods_are_other_not_sentence_final(self):
        self.assertEqual(_classify_at("v1.2.3", 3), BoundaryClass.OTHER)
        self.assertEqual(_classify_at("v1.2.3", 5), BoundaryClass.OTHER)

    def test_genuine_bare_ascii_full_stop_still_classifies_sentence_final(self):
        self.assertEqual(_classify_at("Done. Next", 5), BoundaryClass.SENTENCE_FINAL)


# ---------------------------------------------------------------------------
# F. Colon
# ---------------------------------------------------------------------------


class ColonTests(unittest.TestCase):
    def test_ascii_colon(self):
        self.assertEqual(_classify_at("Key:Value", 3), BoundaryClass.OTHER)

    def test_fullwidth_colon(self):
        self.assertEqual(_classify_at("主題：內容", 2), BoundaryClass.OTHER)

    def test_colon_in_time_notation(self):
        self.assertEqual(_classify_at("12:30", 2), BoundaryClass.OTHER)

    def test_colon_in_url_is_not_clause(self):
        text = "見 http://example.com 頁面"
        position = text.index(":") + 1
        self.assertEqual(_classify_at(text, position), BoundaryClass.OTHER)


# ---------------------------------------------------------------------------
# G. Character-class transition
# ---------------------------------------------------------------------------


class CharacterClassTransitionTests(unittest.TestCase):
    def test_no_space_transition(self):
        # "中文|English"
        self.assertEqual(_classify_at("中文English", 2), BoundaryClass.OTHER)

    def test_boundary_before_space(self):
        # "中文| English" - text is "中文 English", boundary right after "文"
        self.assertEqual(_classify_at("中文 English", 2), BoundaryClass.OTHER)

    def test_boundary_after_space(self):
        # "中文 |English" - same text, boundary right after the space
        self.assertEqual(_classify_at("中文 English", 3), BoundaryClass.OTHER)

    def test_all_internal_boundaries_of_bare_spaced_text_are_other(self):
        # "中文 English" with no pipe marker at all - every internal
        # boundary in this short example should be OTHER.
        text = "中文 English"
        for candidate in _observe(text):
            self.assertEqual(
                classify_boundary(candidate),
                BoundaryClass.OTHER,
                f"position {candidate.position} ({candidate.left_char!r}|{candidate.right_char!r})",
            )

    def test_latin_to_latin_transition(self):
        # "PowerPoint|PPTX"
        self.assertEqual(_classify_at("PowerPointPPTX", 10), BoundaryClass.OTHER)


# ---------------------------------------------------------------------------
# H. Primary classification precedence (behavioral, via synthetic fixtures -
# see testing correction 6: no white-box / control-flow-order tests)
# ---------------------------------------------------------------------------


class PrecedenceTests(unittest.TestCase):
    def test_sentence_final_wins_over_clause_and_ellipsis_shaped_evidence(self):
        candidate = _make_candidate(
            left_char="，",
            contains_sentence_final_punctuation=True,
            punctuation_sequence_state=PunctuationSequenceState.END,
        )
        self.assertEqual(classify_boundary(candidate), BoundaryClass.SENTENCE_FINAL)

    def test_sentence_final_wins_over_clause_shaped_evidence_alone(self):
        candidate = _make_candidate(
            left_char="，",
            contains_sentence_final_punctuation=True,
            punctuation_sequence_state=PunctuationSequenceState.NONE,
        )
        self.assertEqual(classify_boundary(candidate), BoundaryClass.SENTENCE_FINAL)

    def test_ellipsis_wins_over_clause_shaped_evidence(self):
        candidate = _make_candidate(
            left_char="，",
            contains_sentence_final_punctuation=False,
            punctuation_sequence_state=PunctuationSequenceState.END,
        )
        self.assertEqual(classify_boundary(candidate), BoundaryClass.ELLIPSIS)

    def test_real_ellipsis_then_terminal_punctuation_still_prefers_sentence_final(self):
        # Real-pipeline confirmation of the one precedence case that IS
        # naturally constructible (see the approved plan's conflict note).
        self.assertEqual(_classify_at_end("真的……？"), BoundaryClass.SENTENCE_FINAL)


# ---------------------------------------------------------------------------
# I. Determinism
# ---------------------------------------------------------------------------


class DeterminismTests(unittest.TestCase):
    def test_same_candidate_produces_same_class(self):
        candidate = _candidate_at(_observe("真的很好！下一句"), 5)
        assert candidate is not None
        first = classify_boundary(candidate)
        second = classify_boundary(candidate)
        self.assertEqual(first, second)

    def test_same_text_produces_equal_classified_sequence(self):
        text = "「真的很好！」😂 首先，我們繼續……"
        first = classify_boundaries(_observe(text))
        second = classify_boundaries(_observe(text))
        self.assertEqual(first, second)


# ---------------------------------------------------------------------------
# J. Observation preservation
# ---------------------------------------------------------------------------


class PreservationTests(unittest.TestCase):
    def test_classified_boundary_holds_the_exact_same_candidate_object(self):
        candidates = _observe("真的很好！下一句")
        classified = classify_boundaries(candidates)
        for original, result in zip(candidates, classified):
            self.assertIs(result.candidate, original)

    def test_classify_boundary_does_not_mutate_features(self):
        candidate = _candidate_at(_observe("首先，我們繼續"), 2)
        assert candidate is not None
        features_before = candidate.features
        classify_boundary(candidate)
        self.assertIs(candidate.features, features_before)

    def test_classified_boundary_has_no_extra_fields(self):
        candidate = _make_candidate()
        classified = classify_boundary(candidate)
        result = ClassifiedBoundary(candidate=candidate, boundary_class=classified)
        field_names = set(result.__dataclass_fields__.keys())
        self.assertEqual(field_names, {"candidate", "boundary_class"})
