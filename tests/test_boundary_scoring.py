import dataclasses
import unittest
from typing import Optional, Sequence, Tuple

from src.boundary_classification import BoundaryClass, ClassifiedBoundary, classify_boundary
from src.boundary_observation import (
    BoundaryCandidate,
    BoundaryFeatures,
    CharacterClass,
    PunctuationSequenceState,
    SpanRef,
    StructuralBoundaryContext,
    observe_boundaries,
)
from src.boundary_scoring import WeightedBoundary, score_boundaries, score_boundary
from src.text_structure import analyze_text_structure

# ---------------------------------------------------------------------------
# Real-pipeline fixture helpers (Phase 1 -> Phase 2A -> Phase 2B, unmodified)
# ---------------------------------------------------------------------------


def _observe(text: str) -> Tuple[BoundaryCandidate, ...]:
    return observe_boundaries(analyze_text_structure(text))


def _candidate_at(candidates: Sequence[BoundaryCandidate], position: int) -> Optional[BoundaryCandidate]:
    for c in candidates:
        if c.position == position:
            return c
    return None


def _classified_at(text: str, position: int) -> ClassifiedBoundary:
    """Real-pipeline fixture: run text through Phase 1 -> Phase 2A -> Phase
    2B (unmodified) and return the real ClassifiedBoundary at `position`.
    Used for every test that represents confirmed, real-pipeline evidence.
    """
    candidate = _candidate_at(_observe(text), position)
    assert candidate is not None, f"no boundary candidate at position {position} in {text!r}"
    return ClassifiedBoundary(candidate=candidate, boundary_class=classify_boundary(candidate))


# ---------------------------------------------------------------------------
# Synthetic fixture helper (bypasses Phase 1/2A/2B entirely)
#
# Used ONLY for:
#   (a) combinations the real pipeline cannot currently produce but that the
#       locked formula must still mechanically define (e.g. CLAUSE +
#       Technical, Atomic + INTERNAL) - see
#       docs/phase2c/contracts/PHASE_2C_PRODUCTION_SCORING_IMPLEMENTATION_CONTRACT.md section
#       13's "mechanically defined, empirically unverified" table; and
#   (b) directly proving an internal implementation nuance (e.g. that the
#       broad `character_class_transition` flag alone must NOT trigger the
#       +15.0 transition bonus).
#
# A synthetic fixture is an ARITHMETIC/COMPOSITION test of the locked
# formula, never a claim of real-pipeline calibration evidence - see each
# test's docstring/name for the explicit distinction, mirroring the same
# discipline already used by tests/test_boundary_classification.py's
# `_make_candidate` helper for the equivalent Phase 2B case.
# ---------------------------------------------------------------------------


def _make_classified(
    boundary_class: BoundaryClass,
    position: int = 1,
    left_char: str = "X",
    right_char: str = "Y",
    left_character_class: CharacterClass = CharacterClass.OTHER,
    right_character_class: CharacterClass = CharacterClass.OTHER,
    character_class_transition: bool = False,
    punctuation_sequence_state: PunctuationSequenceState = PunctuationSequenceState.NONE,
    containing_spans: Tuple[SpanRef, ...] = (),
) -> ClassifiedBoundary:
    context = StructuralBoundaryContext(
        containing_spans=containing_spans,
        left_adjacent_spans=(),
        right_adjacent_spans=(),
    )
    features = BoundaryFeatures(
        left_character_class=left_character_class,
        right_character_class=right_character_class,
        character_class_transition=character_class_transition,
        punctuation_sequence_state=punctuation_sequence_state,
        contains_sentence_final_punctuation=False,
        structural_context=context,
    )
    candidate = BoundaryCandidate(position=position, left_char=left_char, right_char=right_char, features=features)
    return ClassifiedBoundary(candidate=candidate, boundary_class=boundary_class)


_TECHNICAL_SPAN = SpanRef(start=0, end=10, type="technical", subtype="identifier")
_ATOMIC_SPAN = SpanRef(start=0, end=10, type="atomic", subtype="numeric")


# ---------------------------------------------------------------------------
# A. Output model
# ---------------------------------------------------------------------------


class OutputModelTests(unittest.TestCase):
    def test_weighted_boundary_exists_and_is_constructible(self):
        classified = _classified_at("這個功能", 1)
        weighted = score_boundary(classified)
        self.assertIsInstance(weighted, WeightedBoundary)

    def test_weighted_boundary_is_frozen(self):
        classified = _classified_at("這個功能", 1)
        weighted = score_boundary(classified)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            weighted.score = 999.0  # type: ignore[misc]

    def test_weighted_boundary_has_exactly_three_fields(self):
        classified = _classified_at("這個功能", 1)
        weighted = score_boundary(classified)
        field_names = set(weighted.__dataclass_fields__.keys())
        self.assertEqual(field_names, {"candidate", "boundary_class", "score"})

    def test_weighted_boundary_field_values(self):
        classified = _classified_at("第一，第二", 3)
        weighted = score_boundary(classified)
        self.assertIs(weighted.candidate, classified.candidate)
        self.assertEqual(weighted.boundary_class, classified.boundary_class)
        self.assertIsInstance(weighted.score, float)


# ---------------------------------------------------------------------------
# B. Base Classification
# ---------------------------------------------------------------------------


class BaseClassificationTests(unittest.TestCase):
    def test_other(self):
        # "這|個" - plain CJK-CJK interior boundary, no incidental evidence.
        classified = _classified_at("這個功能", 1)
        self.assertEqual(classified.boundary_class, BoundaryClass.OTHER)
        self.assertEqual(score_boundary(classified).score, 0.0)

    def test_clause(self):
        # "，|第" - clean clause comma, no incidental evidence.
        classified = _classified_at("第一，第二", 3)
        self.assertEqual(classified.boundary_class, BoundaryClass.CLAUSE)
        self.assertEqual(score_boundary(classified).score, 35.0)

    def test_ellipsis(self):
        # "…|啊" - genuine END-state ellipsis boundary, padded with a CJK
        # character (not whitespace) so this stays a clean, uncontaminated
        # base-classification-only fixture.
        classified = _classified_at("真的……啊", 4)
        self.assertEqual(classified.boundary_class, BoundaryClass.ELLIPSIS)
        self.assertEqual(score_boundary(classified).score, 65.0)

    def test_sentence_final(self):
        # "。|他" - genuine non-string-final sentence-final boundary, padded
        # with a CJK character (not whitespace) for the same reason as above.
        classified = _classified_at("你好。他", 3)
        self.assertEqual(classified.boundary_class, BoundaryClass.SENTENCE_FINAL)
        self.assertEqual(score_boundary(classified).score, 80.0)


# ---------------------------------------------------------------------------
# C. Transition Positive Evidence
# ---------------------------------------------------------------------------


class TransitionPositiveEvidenceTests(unittest.TestCase):
    def test_cjk_to_latin(self):
        # "用|P" in "這個功能使用Python處理資料。"
        classified = _classified_at("這個功能使用Python處理資料。", 6)
        candidate = classified.candidate
        self.assertEqual(candidate.features.left_character_class, CharacterClass.CJK)
        self.assertEqual(candidate.features.right_character_class, CharacterClass.LATIN)
        self.assertEqual(score_boundary(classified).score, 15.0)

    def test_latin_to_cjk(self):
        # "n|可" in "Python可以處理資料。"
        classified = _classified_at("Python可以處理資料。", 6)
        candidate = classified.candidate
        self.assertEqual(candidate.features.left_character_class, CharacterClass.LATIN)
        self.assertEqual(candidate.features.right_character_class, CharacterClass.CJK)
        self.assertEqual(score_boundary(classified).score, 15.0)

    def test_symmetry(self):
        cjk_to_latin = score_boundary(_classified_at("這個功能使用Python處理資料。", 6)).score
        latin_to_cjk = score_boundary(_classified_at("Python可以處理資料。", 6)).score
        self.assertEqual(cjk_to_latin, latin_to_cjk)
        self.assertEqual(cjk_to_latin, 15.0)

    def test_generic_character_class_transition_flag_alone_does_not_trigger_bonus(self):
        # SYNTHETIC ARITHMETIC TEST (not calibration evidence): deliberately
        # set character_class_transition=True on a CJK->DIGIT boundary - a
        # real, broad "class changed" signal Phase 2A already computes -
        # and confirm it does NOT produce the +15.0 transition bonus, which
        # is reserved exclusively for the exact {CJK, LATIN} pair.
        classified = _make_classified(
            boundary_class=BoundaryClass.OTHER,
            left_character_class=CharacterClass.CJK,
            right_character_class=CharacterClass.DIGIT,
            character_class_transition=True,
        )
        self.assertEqual(score_boundary(classified).score, 0.0)

    def test_cjk_to_punctuation_does_not_trigger_bonus(self):
        # SYNTHETIC ARITHMETIC TEST: CJK -> PUNCTUATION is also a
        # character_class_transition=True case that must not receive +15.0.
        classified = _make_classified(
            boundary_class=BoundaryClass.OTHER,
            left_character_class=CharacterClass.CJK,
            right_character_class=CharacterClass.PUNCTUATION,
            character_class_transition=True,
        )
        self.assertEqual(score_boundary(classified).score, 0.0)

    def test_digit_to_cjk_does_not_trigger_bonus(self):
        # SYNTHETIC ARITHMETIC TEST: the reverse-direction non-Latin case.
        classified = _make_classified(
            boundary_class=BoundaryClass.OTHER,
            left_character_class=CharacterClass.DIGIT,
            right_character_class=CharacterClass.CJK,
            character_class_transition=True,
        )
        self.assertEqual(score_boundary(classified).score, 0.0)

    def test_whitespace_to_cjk_does_not_trigger_bonus_but_does_trigger_whitespace(self):
        # SYNTHETIC ARITHMETIC TEST: WHITESPACE -> CJK is a
        # character_class_transition=True case; it must not receive the
        # transition bonus, but it IS a real whitespace boundary and must
        # receive exactly the whitespace bonus (+10.0), not the transition
        # bonus (+15.0) and not both.
        classified = _make_classified(
            boundary_class=BoundaryClass.OTHER,
            left_character_class=CharacterClass.WHITESPACE,
            right_character_class=CharacterClass.CJK,
            character_class_transition=True,
        )
        self.assertEqual(score_boundary(classified).score, 10.0)


# ---------------------------------------------------------------------------
# D. Whitespace
# ---------------------------------------------------------------------------


class WhitespaceTests(unittest.TestCase):
    def test_other_plus_whitespace(self):
        # "個| " in "這個 功能很好用。"
        classified = _classified_at("這個 功能很好用。", 2)
        self.assertEqual(classified.boundary_class, BoundaryClass.OTHER)
        self.assertEqual(score_boundary(classified).score, 10.0)

    def test_clause_plus_whitespace(self):
        # "，| " in "接下來， 我們介紹重點。"
        classified = _classified_at("接下來， 我們介紹重點。", 4)
        self.assertEqual(classified.boundary_class, BoundaryClass.CLAUSE)
        self.assertEqual(score_boundary(classified).score, 45.0)

    def test_ellipsis_plus_whitespace(self):
        # "…| " (END state) in "我們稍後再談…… 好，開始吧。"
        classified = _classified_at("我們稍後再談…… 好，開始吧。", 8)
        self.assertEqual(classified.boundary_class, BoundaryClass.ELLIPSIS)
        self.assertEqual(score_boundary(classified).score, 75.0)

    def test_sentence_final_plus_whitespace(self):
        # "。| " in "這是重點。 接下來介紹範例。"
        classified = _classified_at("這是重點。 接下來介紹範例。", 5)
        self.assertEqual(classified.boundary_class, BoundaryClass.SENTENCE_FINAL)
        self.assertEqual(score_boundary(classified).score, 90.0)

    def test_whitespace_is_non_stacking_around_one_space_character(self):
        # A single space character produces TWO separate boundary
        # candidates (one on each side of it) - each independently scores
        # exactly +10.0 on top of its own base; neither ever scores +20.0.
        text = "這個 功能很好用。"
        left_of_space = score_boundary(_classified_at(text, 2))
        right_of_space = score_boundary(_classified_at(text, 3))
        self.assertEqual(left_of_space.score, 10.0)
        self.assertEqual(right_of_space.score, 10.0)

    def test_whitespace_does_not_stack_across_multiple_space_characters(self):
        # Two separate space characters in one text produce four separate
        # whitespace-adjacent candidates, every one of which scores exactly
        # +10.0 - never +20.0, +30.0, or any multiple, confirming
        # non-stacking across multiple whitespace characters in the source.
        text = "這 個 功能"
        candidates = _observe(text)
        whitespace_adjacent_positions = [1, 2, 3, 4]
        scores = []
        for position in whitespace_adjacent_positions:
            candidate = _candidate_at(candidates, position)
            assert candidate is not None
            classified = ClassifiedBoundary(candidate=candidate, boundary_class=classify_boundary(candidate))
            scores.append(score_boundary(classified).score)
        self.assertEqual(scores, [10.0, 10.0, 10.0, 10.0])


# ---------------------------------------------------------------------------
# E. Protection
# ---------------------------------------------------------------------------


class ProtectionTests(unittest.TestCase):
    def test_other_plus_technical(self):
        # "."|"3" (pos 9) in "版本是 v1.2.3 這樣寫。" - technical/version
        # only (not atomic) at this specific position.
        classified = _classified_at("版本是 v1.2.3 這樣寫。", 9)
        self.assertEqual(classified.boundary_class, BoundaryClass.OTHER)
        containing_types = {
            s.type for s in classified.candidate.features.structural_context.containing_spans
        }
        self.assertIn("technical", containing_types)
        self.assertNotIn("atomic", containing_types)
        self.assertEqual(score_boundary(classified).score, -30.0)

    def test_other_plus_atomic(self):
        # "1"|"," (pos 1) in "1,000" - atomic/numeric only.
        classified = _classified_at("1,000", 1)
        self.assertEqual(classified.boundary_class, BoundaryClass.OTHER)
        containing_types = {
            s.type for s in classified.candidate.features.structural_context.containing_spans
        }
        self.assertIn("atomic", containing_types)
        self.assertNotIn("technical", containing_types)
        self.assertEqual(score_boundary(classified).score, -30.0)

    def test_other_plus_internal(self):
        # "…"|"…" (pos 7, INTERNAL) in "我們稍後再談…… 好，開始吧。"
        classified = _classified_at("我們稍後再談…… 好，開始吧。", 7)
        self.assertEqual(classified.boundary_class, BoundaryClass.OTHER)
        self.assertEqual(
            classified.candidate.features.punctuation_sequence_state, PunctuationSequenceState.INTERNAL
        )
        self.assertEqual(score_boundary(classified).score, -20.0)

    def test_technical_plus_atomic_is_strongest_only_not_additive(self):
        # "1"|"." (pos 6) in "版本是 v1.2.3 這樣寫。" - a real candidate
        # genuinely tagged BOTH technical/version and atomic/numeric.
        classified = _classified_at("版本是 v1.2.3 這樣寫。", 6)
        containing_types = {
            s.type for s in classified.candidate.features.structural_context.containing_spans
        }
        self.assertIn("technical", containing_types)
        self.assertIn("atomic", containing_types)
        self.assertEqual(score_boundary(classified).score, -30.0)
        self.assertNotEqual(score_boundary(classified).score, -60.0)

    def test_technical_plus_internal_is_additive(self):
        # Real-pipeline evidence (mirrors
        # PHASE_2C_PROTECTION_POST_CORRECTION_VERIFICATION.md's clean P11
        # case): pos 25 in a URL whose technical/url span and an internal
        # ellipsis run's interior genuinely overlap on one candidate.
        classified = _classified_at("請參考 http://example.com/a...b 這個頁面。", 25)
        containing_types = {
            s.type for s in classified.candidate.features.structural_context.containing_spans
        }
        self.assertIn("technical", containing_types)
        self.assertEqual(
            classified.candidate.features.punctuation_sequence_state, PunctuationSequenceState.INTERNAL
        )
        self.assertEqual(score_boundary(classified).score, -50.0)

    def test_atomic_plus_internal_is_mechanically_additive_synthetic(self):
        # SYNTHETIC ARITHMETIC/COMPOSITION TEST - NOT real-pipeline
        # calibration evidence. Atomic+INTERNAL (P12) remains an unreached
        # CASE ISSUE per
        # docs/phase2c/calibration/reports/PHASE_2C_PROTECTION_CALIBRATION_ROUND1_REPORT.md section 6
        # and docs/phase2c/calibration/reports/PHASE_2C_PROTECTION_POST_CORRECTION_VERIFICATION_REPORT.md
        # section 7 - no real candidate has ever been observed carrying
        # both flags. This test only confirms the locked additive formula
        # produces -50.0 mechanically if the data model is ever asked to
        # represent this combination; it does not claim this combination
        # has been empirically observed.
        classified = _make_classified(
            boundary_class=BoundaryClass.OTHER,
            containing_spans=(_ATOMIC_SPAN,),
            punctuation_sequence_state=PunctuationSequenceState.INTERNAL,
        )
        self.assertEqual(score_boundary(classified).score, -50.0)


# ---------------------------------------------------------------------------
# F. Composition
# ---------------------------------------------------------------------------


class CompositionConfirmedReachableTests(unittest.TestCase):
    """Confirmed-reachable Base + Positive Evidence combinations, all via
    real Phase 1 -> Phase 2A -> Phase 2B pipeline fixtures."""

    def test_other_plus_transition(self):
        classified = _classified_at("這個功能使用Python處理資料。", 6)
        self.assertEqual(score_boundary(classified).score, 15.0)

    def test_other_plus_whitespace(self):
        classified = _classified_at("這個 功能很好用。", 2)
        self.assertEqual(score_boundary(classified).score, 10.0)

    def test_clause_plus_whitespace(self):
        classified = _classified_at("接下來， 我們介紹重點。", 4)
        self.assertEqual(score_boundary(classified).score, 45.0)

    def test_ellipsis_plus_whitespace(self):
        classified = _classified_at("我們稍後再談…… 好，開始吧。", 8)
        self.assertEqual(score_boundary(classified).score, 75.0)

    def test_sentence_final_plus_whitespace(self):
        classified = _classified_at("這是重點。 接下來介紹範例。", 5)
        self.assertEqual(score_boundary(classified).score, 90.0)


class CompositionFormulaDerivedUnverifiedTests(unittest.TestCase):
    """Formula-derived, empirically-UNVERIFIED combinations - see
    docs/phase2c/contracts/PHASE_2C_PRODUCTION_SCORING_IMPLEMENTATION_CONTRACT.md section 13's
    "mechanically defined, empirically unverified" table. Every fixture here
    is SYNTHETIC (bypasses Phase 1/2A/2B). These tests verify the locked
    formula's arithmetic only - they are explicitly NOT calibration
    evidence and must never be read as confirming these combinations occur
    in real text.
    """

    def test_other_plus_transition_plus_technical_is_minus_fifteen(self):
        # 0 (OTHER) + 15 (CJK->LATIN) - 30 (Technical) = -15
        classified = _make_classified(
            boundary_class=BoundaryClass.OTHER,
            left_character_class=CharacterClass.CJK,
            right_character_class=CharacterClass.LATIN,
            containing_spans=(_TECHNICAL_SPAN,),
        )
        self.assertEqual(score_boundary(classified).score, -15.0)

    def test_other_plus_whitespace_plus_technical_is_minus_twenty(self):
        # 0 (OTHER) + 10 (Whitespace) - 30 (Technical) = -20
        classified = _make_classified(
            boundary_class=BoundaryClass.OTHER,
            left_character_class=CharacterClass.WHITESPACE,
            right_character_class=CharacterClass.CJK,
            containing_spans=(_TECHNICAL_SPAN,),
        )
        self.assertEqual(score_boundary(classified).score, -20.0)

    def test_clause_plus_technical_is_five(self):
        # 35 (CLAUSE) - 30 (Technical) = 5
        classified = _make_classified(
            boundary_class=BoundaryClass.CLAUSE,
            containing_spans=(_TECHNICAL_SPAN,),
        )
        self.assertEqual(score_boundary(classified).score, 5.0)

    def test_ellipsis_plus_technical_is_thirty_five(self):
        # 65 (ELLIPSIS) - 30 (Technical) = 35
        classified = _make_classified(
            boundary_class=BoundaryClass.ELLIPSIS,
            containing_spans=(_TECHNICAL_SPAN,),
        )
        self.assertEqual(score_boundary(classified).score, 35.0)

    def test_sentence_final_plus_technical_is_fifty(self):
        # 80 (SENTENCE_FINAL) - 30 (Technical) = 50
        classified = _make_classified(
            boundary_class=BoundaryClass.SENTENCE_FINAL,
            containing_spans=(_TECHNICAL_SPAN,),
        )
        self.assertEqual(score_boundary(classified).score, 50.0)


# ---------------------------------------------------------------------------
# G. Determinism
# ---------------------------------------------------------------------------


class DeterminismTests(unittest.TestCase):
    def test_same_classified_boundary_produces_same_score(self):
        classified = _classified_at("這個功能使用Python處理資料。", 6)
        first = score_boundary(classified)
        second = score_boundary(classified)
        self.assertEqual(first, second)
        self.assertEqual(first.score, second.score)

    def test_same_text_produces_equal_weighted_sequence(self):
        text = "「真的很好！」😂 首先，我們繼續……"
        classified_boundaries = tuple(
            ClassifiedBoundary(candidate=c, boundary_class=classify_boundary(c)) for c in _observe(text)
        )
        first = score_boundaries(classified_boundaries)
        second = score_boundaries(classified_boundaries)
        self.assertEqual(first, second)


# ---------------------------------------------------------------------------
# H. Immutability
# ---------------------------------------------------------------------------


class ImmutabilityTests(unittest.TestCase):
    def test_candidate_identity_is_preserved(self):
        classified = _classified_at("這個功能使用Python處理資料。", 6)
        weighted = score_boundary(classified)
        self.assertIs(weighted.candidate, classified.candidate)

    def test_classified_boundary_is_unchanged_after_scoring(self):
        classified = _classified_at("這個功能使用Python處理資料。", 6)
        boundary_class_before = classified.boundary_class
        candidate_before = classified.candidate
        features_before = classified.candidate.features
        score_boundary(classified)
        self.assertEqual(classified.boundary_class, boundary_class_before)
        self.assertIs(classified.candidate, candidate_before)
        self.assertIs(classified.candidate.features, features_before)

    def test_input_candidate_features_object_is_not_mutated(self):
        classified = _classified_at("第一，第二", 3)
        features_before = classified.candidate.features
        score_boundary(classified)
        self.assertIs(classified.candidate.features, features_before)


# ---------------------------------------------------------------------------
# I. Collection API
# ---------------------------------------------------------------------------


class CollectionApiTests(unittest.TestCase):
    def test_empty_collection_returns_empty_tuple(self):
        self.assertEqual(score_boundaries(()), ())

    def test_preserves_input_order_and_one_to_one_correspondence(self):
        text = "首先，我們繼續……然後結束。"
        classified_boundaries = tuple(
            ClassifiedBoundary(candidate=c, boundary_class=classify_boundary(c)) for c in _observe(text)
        )
        weighted_boundaries = score_boundaries(classified_boundaries)
        self.assertEqual(len(weighted_boundaries), len(classified_boundaries))
        for classified, weighted in zip(classified_boundaries, weighted_boundaries):
            self.assertIs(weighted.candidate, classified.candidate)
            self.assertEqual(weighted.boundary_class, classified.boundary_class)

    def test_matches_individual_score_boundary_calls(self):
        text = "首先，我們繼續……然後結束。"
        classified_boundaries = tuple(
            ClassifiedBoundary(candidate=c, boundary_class=classify_boundary(c)) for c in _observe(text)
        )
        via_collection = score_boundaries(classified_boundaries)
        via_individual = tuple(score_boundary(c) for c in classified_boundaries)
        self.assertEqual(via_collection, via_individual)

    def test_does_not_mutate_input_collection(self):
        text = "首先，我們繼續。"
        classified_boundaries = tuple(
            ClassifiedBoundary(candidate=c, boundary_class=classify_boundary(c)) for c in _observe(text)
        )
        snapshot = tuple(classified_boundaries)
        score_boundaries(classified_boundaries)
        self.assertEqual(classified_boundaries, snapshot)


# ---------------------------------------------------------------------------
# J. Error handling
# ---------------------------------------------------------------------------


class ErrorHandlingTests(unittest.TestCase):
    def test_none_raises_type_error(self):
        with self.assertRaises(TypeError):
            score_boundary(None)  # type: ignore[arg-type]

    def test_malformed_input_raises_type_error(self):
        with self.assertRaises(TypeError):
            score_boundary("not a ClassifiedBoundary")  # type: ignore[arg-type]

    def test_none_collection_raises_type_error(self):
        with self.assertRaises(TypeError):
            score_boundaries(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# K. Public-API-only surface (score_boundary does not call classify_boundary)
# ---------------------------------------------------------------------------


class ScorerDoesNotReclassifyTests(unittest.TestCase):
    def test_score_reflects_the_supplied_boundary_class_even_if_inconsistent_with_features(self):
        # SYNTHETIC ARITHMETIC TEST: proves the scorer trusts
        # `classified.boundary_class` as given and never independently
        # re-derives it from the candidate's features (i.e. it never calls
        # classify_boundary() internally) - the base score here must come
        # from the explicitly supplied SENTENCE_FINAL, not from whatever a
        # real classification of these (deliberately minimal/inconsistent)
        # features would produce.
        classified = _make_classified(
            boundary_class=BoundaryClass.SENTENCE_FINAL,
            left_char="X",
            right_char="Y",
        )
        self.assertEqual(score_boundary(classified).score, 80.0)


if __name__ == "__main__":
    unittest.main()
