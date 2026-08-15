import unittest
from dataclasses import FrozenInstanceError
from typing import Dict, Optional, Tuple

from src.boundary_classification import BoundaryClass, classify_boundaries
from src.boundary_observation import (
    BoundaryCandidate,
    BoundaryFeatures,
    CharacterClass,
    PunctuationSequenceState,
    StructuralBoundaryContext,
    observe_boundaries,
)
from src.boundary_scoring import WeightedBoundary, score_boundaries
from src.boundary_segmentation import (
    DEFAULT_MAX_DISPLAY_WIDTH,
    SubtitleSegment,
    segment_boundaries,
)
from src.text_structure import analyze_text_structure

# ---------------------------------------------------------------------------
# Real-pipeline fixture helper (Phase 1 -> Phase 2A -> Phase 2B -> Phase 2C,
# unmodified) - used for the one end-to-end structural sanity test (item 13,
# "multiple candidate input"), matching this project's established
# convention of validating against real pipeline output, not only
# hand-built data (see tests/test_boundary_scoring.py).
# ---------------------------------------------------------------------------


def _weighted(text: str) -> Tuple[WeightedBoundary, ...]:
    candidates = observe_boundaries(analyze_text_structure(text))
    classified = classify_boundaries(candidates)
    return score_boundaries(classified)


# ---------------------------------------------------------------------------
# Synthetic fixture helpers (bypass Phase 1/2A/2B/2C entirely)
#
# Used for every test that needs precise, hand-computable control over exact
# positions/scores - this is the decision *layer*'s own test suite, trusting
# Phase 2C's already-tested scores as correct inputs (see design doc section
# 18), not re-testing scoring arithmetic itself. Every fixture text below
# uses plain ASCII letters (display width 1 per character) specifically so
# widths are trivial to hand-verify.
# ---------------------------------------------------------------------------


def _make_weighted(position: int, score: float) -> WeightedBoundary:
    features = BoundaryFeatures(
        left_character_class=CharacterClass.OTHER,
        right_character_class=CharacterClass.OTHER,
        character_class_transition=False,
        punctuation_sequence_state=PunctuationSequenceState.NONE,
        contains_sentence_final_punctuation=False,
        structural_context=StructuralBoundaryContext(
            containing_spans=(), left_adjacent_spans=(), right_adjacent_spans=()
        ),
    )
    candidate = BoundaryCandidate(position=position, left_char="x", right_char="y", features=features)
    return WeightedBoundary(candidate=candidate, boundary_class=BoundaryClass.OTHER, score=score)


def _dense_weighted(text: str, scores: Optional[Dict[int, float]] = None) -> Tuple[WeightedBoundary, ...]:
    """One synthetic WeightedBoundary per internal character gap (position 1
    through len(text)-1), mirroring the real pipeline's density (see
    boundary_observation.observe_boundaries), with score 0.0 everywhere
    except the positions given in `scores`.
    """
    scores = scores or {}
    return tuple(_make_weighted(position=p, score=scores.get(p, 0.0)) for p in range(1, len(text)))


# ---------------------------------------------------------------------------
# 1. API validation
# ---------------------------------------------------------------------------


class ApiValidationTests(unittest.TestCase):
    def test_subtitle_segment_is_frozen_with_exactly_two_fields(self):
        segment = SubtitleSegment(start=0, end=1)
        with self.assertRaises(FrozenInstanceError):
            segment.start = 5  # type: ignore[misc]
        self.assertEqual(set(segment.__dataclass_fields__.keys()), {"start", "end"})

    def test_none_weighted_boundaries_raises_type_error(self):
        with self.assertRaises(TypeError):
            segment_boundaries(None, "abc")

    def test_non_str_source_text_raises_type_error(self):
        with self.assertRaises(TypeError):
            segment_boundaries(_dense_weighted("abc"), 12345)  # type: ignore[arg-type]

    def test_non_weighted_boundary_item_raises_type_error(self):
        with self.assertRaises(TypeError):
            segment_boundaries([object()], "abc")  # type: ignore[list-item]

    def test_non_positive_max_display_width_raises_value_error(self):
        with self.assertRaises(ValueError):
            segment_boundaries(_dense_weighted("abc"), "abc", max_display_width=0)
        with self.assertRaises(ValueError):
            segment_boundaries(_dense_weighted("abc"), "abc", max_display_width=-5)

    def test_default_max_display_width_matches_subtitle_segmenter_convention(self):
        # Mirrors subtitle_segmenter.DEFAULT_MAX_DISPLAY_WIDTH's value (18
        # full-width characters) by design intent - not imported, to avoid
        # coupling this new module to that existing one (see module
        # docstring).
        self.assertEqual(DEFAULT_MAX_DISPLAY_WIDTH, 36)

    def test_does_not_mutate_input_list(self):
        boundaries_list = list(_dense_weighted("abcdefghij", {5: 100.0}))
        original = list(boundaries_list)
        segment_boundaries(boundaries_list, "abcdefghij", max_display_width=6)
        self.assertEqual(boundaries_list, original)


# ---------------------------------------------------------------------------
# 2. Empty input
# ---------------------------------------------------------------------------


class EmptyInputTests(unittest.TestCase):
    def test_empty_weighted_boundaries_returns_empty_tuple(self):
        self.assertEqual(segment_boundaries((), "abcdefghij"), ())

    def test_blank_source_text_returns_empty_tuple(self):
        self.assertEqual(segment_boundaries(_dense_weighted("abc"), "   \n  "), ())

    def test_empty_source_text_returns_empty_tuple(self):
        self.assertEqual(segment_boundaries(_dense_weighted("abc"), ""), ())


# ---------------------------------------------------------------------------
# 3. Basic segmentation / cut decision
# ---------------------------------------------------------------------------


class BasicSegmentationTests(unittest.TestCase):
    TEXT = "abcdefghij"  # length 10, ascii - each character has display width 1

    def test_single_dominant_candidate_is_chosen(self):
        # max_display_width=6 forces exactly one cut; the only feasible cut
        # positions are 4..6 (need width(0,a)<=6 and width(a,10)<=6) - among
        # those, position 5 is given a dominant score and must win.
        weighted = _dense_weighted(self.TEXT, {5: 100.0})
        result = segment_boundaries(weighted, self.TEXT, max_display_width=6)
        self.assertEqual(result, (SubtitleSegment(0, 5), SubtitleSegment(5, 10)))

    def test_offset_integrity_reconstructs_source_text(self):
        weighted = _dense_weighted(self.TEXT, {5: 100.0})
        result = segment_boundaries(weighted, self.TEXT, max_display_width=6)
        self.assertEqual(result[0].start, 0)
        self.assertEqual(result[-1].end, len(self.TEXT))
        reconstructed = "".join(self.TEXT[seg.start:seg.end] for seg in result)
        self.assertEqual(reconstructed, self.TEXT)


# ---------------------------------------------------------------------------
# 4. Minimum feasible K
# ---------------------------------------------------------------------------


class MinimumFeasibleKTests(unittest.TestCase):
    TEXT = "abcdefghij"  # length 10

    def test_whole_paragraph_fits_yields_one_segment(self):
        weighted = _dense_weighted(self.TEXT)
        result = segment_boundaries(weighted, self.TEXT, max_display_width=10)
        self.assertEqual(result, (SubtitleSegment(0, 10),))

    def test_segment_count_matches_width_driven_minimum(self):
        # Every score is 0 (no preference signal at all) - segment *count*
        # is determined purely by the width constraint (see design doc
        # section 15), independent of any tie-breaking among equally-good
        # exact cut positions.
        weighted = _dense_weighted(self.TEXT)
        result = segment_boundaries(weighted, self.TEXT, max_display_width=4)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].start, 0)
        self.assertEqual(result[-1].end, len(self.TEXT))
        for a, b in zip(result, result[1:]):
            self.assertEqual(a.end, b.start)


# ---------------------------------------------------------------------------
# 5. Score optimization (multi-cut)
# ---------------------------------------------------------------------------


class ScoreOptimizationTests(unittest.TestCase):
    def test_dp_selects_jointly_optimal_pair_of_cuts_over_single_high_scorer(self):
        text = "abcdefghijklmnop"  # length 16
        # max_display_width=6 forces exactly 3 segments (2 internal cuts).
        # Positions 5 and 11 are jointly width-feasible
        # (widths 5, 6, 5) and together score 100; no other feasible pair
        # of cuts can score higher, since every other position is 0.
        weighted = _dense_weighted(text, {5: 50.0, 11: 50.0})
        result = segment_boundaries(weighted, text, max_display_width=6)
        self.assertEqual(
            result,
            (SubtitleSegment(0, 5), SubtitleSegment(5, 11), SubtitleSegment(11, 16)),
        )

    def test_every_segment_respects_display_width_budget(self):
        text = "abcdefghijklmnop"
        weighted = _dense_weighted(text, {5: 50.0, 11: 50.0})
        result = segment_boundaries(weighted, text, max_display_width=6)
        for seg in result:
            self.assertLessEqual(seg.end - seg.start, 6)


# ---------------------------------------------------------------------------
# 6. D04 (resolved generally - no special-case code exists anywhere in
#    src/boundary_segmentation.py for this)
# ---------------------------------------------------------------------------


class D04Tests(unittest.TestCase):
    """Uses the exact score values documented for D04
    (PHASE_2C_OVERALL_NUMERIC_RECONCILIATION.md section 14): a CJK<->LATIN
    transition candidate scores +15.0, a nearby whitespace-adjacent variant
    of the same conceptual boundary scores +10.0. The same two candidates,
    unmodified, are run under two different width budgets to show the
    winner is decided purely by the shared optimization (feasibility +
    score), not a hardcoded "transition beats whitespace" (or vice versa)
    rule - because no such rule exists in the implementation.
    """

    TEXT = "abcdefghij"  # length 10

    def test_higher_scoring_candidate_wins_when_both_feasible(self):
        weighted = _dense_weighted(self.TEXT, {3: 15.0, 5: 10.0})
        result = segment_boundaries(weighted, self.TEXT, max_display_width=7)
        self.assertEqual(result, (SubtitleSegment(0, 3), SubtitleSegment(3, 10)))

    def test_lower_scoring_candidate_wins_when_it_is_the_only_feasible_one(self):
        # Tightening the width budget makes position 3 (score 15.0)
        # infeasible (width(3, 10) = 7 > 6) while position 5 (score 10.0)
        # remains feasible - the same candidate pair, same scores, opposite
        # outcome, driven entirely by width feasibility.
        weighted = _dense_weighted(self.TEXT, {3: 15.0, 5: 10.0})
        result = segment_boundaries(weighted, self.TEXT, max_display_width=6)
        self.assertEqual(result, (SubtitleSegment(0, 5), SubtitleSegment(5, 10)))


# ---------------------------------------------------------------------------
# 7. Competing neighboring candidates
# ---------------------------------------------------------------------------


class CompetingNeighborsTests(unittest.TestCase):
    def test_higher_scoring_neighbor_wins(self):
        text = "abcdefghij"
        weighted = _dense_weighted(text, {5: 30.0, 6: 80.0})
        result = segment_boundaries(weighted, text, max_display_width=7)
        self.assertEqual(result, (SubtitleSegment(0, 6), SubtitleSegment(6, 10)))


# ---------------------------------------------------------------------------
# 8. Deterministic tie-breaking
# ---------------------------------------------------------------------------


class TieBreakingTests(unittest.TestCase):
    def test_equal_scores_broken_by_width_balance(self):
        # Positions 4 and 5 score equally (50.0 each - tied on the primary
        # objective). Cutting at 5 yields widths (5, 5) - sum of squares 50;
        # cutting at 4 yields widths (4, 6) - sum of squares 52. Position 5
        # is the unique width-balance winner.
        text = "abcdefghij"
        weighted = _dense_weighted(text, {4: 50.0, 5: 50.0})
        result = segment_boundaries(weighted, text, max_display_width=7)
        self.assertEqual(result, (SubtitleSegment(0, 5), SubtitleSegment(5, 10)))


# ---------------------------------------------------------------------------
# 9. Paragraph boundaries
# ---------------------------------------------------------------------------


class ParagraphBoundaryTests(unittest.TestCase):
    def test_paragraphs_never_merge_across_hard_boundary(self):
        text = "abcde\nfghij"
        weighted = _dense_weighted(text)  # non-empty input; both paragraphs
        # fit within the budget on their own, so no internal cut is needed.
        result = segment_boundaries(weighted, text, max_display_width=10)
        self.assertEqual(result, (SubtitleSegment(0, 5), SubtitleSegment(6, 11)))

    def test_multiple_paragraphs_aggregate_in_order(self):
        text = "ab\ncdefghij\nkl"
        weighted = _dense_weighted(text)
        result = segment_boundaries(weighted, text, max_display_width=5)
        # Paragraph 2 ("cdefghij", offsets 3-11) needs exactly one internal
        # cut to fit under width 5 (K=2, from the width-only greedy pass).
        # All scores are 0 (tied), so among every width-feasible single-cut
        # position (a in [6, 8]), the tie-break picks the most balanced
        # split: a=7 gives widths (4, 4), sum-of-squares 32 - strictly
        # better than a=6 (3, 5 -> 34) or a=8 (5, 3 -> 34), so it is the
        # unique winner, not merely the greedy pass's own boundary choice.
        self.assertEqual(
            result,
            (
                SubtitleSegment(0, 2),
                SubtitleSegment(3, 7),
                SubtitleSegment(7, 11),
                SubtitleSegment(12, 14),
            ),
        )


# ---------------------------------------------------------------------------
# 10. Display-width constraint (covered further by ScoreOptimizationTests
#     and MinimumFeasibleKTests above; this adds an explicit direct check)
# ---------------------------------------------------------------------------


class DisplayWidthConstraintTests(unittest.TestCase):
    def test_no_segment_exceeds_budget_when_a_feasible_solution_exists(self):
        text = "abcdefghij"
        weighted = _dense_weighted(text)
        result = segment_boundaries(weighted, text, max_display_width=4)
        for seg in result:
            self.assertLessEqual(seg.end - seg.start, 4)


# ---------------------------------------------------------------------------
# 11. Offset integrity (see also BasicSegmentationTests above)
# ---------------------------------------------------------------------------


class OffsetIntegrityTests(unittest.TestCase):
    def test_segments_are_contiguous_and_non_overlapping(self):
        text = "abcdefghijklmnop"
        weighted = _dense_weighted(text, {5: 50.0, 11: 50.0})
        result = segment_boundaries(weighted, text, max_display_width=6)
        self.assertEqual(result[0].start, 0)
        self.assertEqual(result[-1].end, len(text))
        for a, b in zip(result, result[1:]):
            self.assertEqual(a.end, b.start)


# ---------------------------------------------------------------------------
# 12. No-valid-cut input
# ---------------------------------------------------------------------------


class NoValidCutTests(unittest.TestCase):
    def test_short_paragraph_produces_exactly_one_segment(self):
        text = "abc"
        weighted = _dense_weighted(text)
        result = segment_boundaries(weighted, text, max_display_width=10)
        self.assertEqual(result, (SubtitleSegment(0, 3),))


# ---------------------------------------------------------------------------
# 13. Last-resort splitting
# ---------------------------------------------------------------------------


class LastResortSplittingTests(unittest.TestCase):
    def test_forced_advance_when_no_candidate_fits_within_budget(self):
        # A deliberately sparse candidate set (only position 8 provided) -
        # the real pipeline is always dense (see
        # boundary_observation.observe_boundaries), so this scenario only
        # arises from a synthetic/malformed input, but the fallback must
        # still behave deterministically rather than looping or raising.
        # With max_display_width=3, no candidate exists that lets segment
        # (0, 8) fit - the pass still advances to position 8, producing a
        # segment that exceeds the nominal budget, rather than failing.
        text = "abcdefghij"
        weighted = (_make_weighted(position=8, score=0.0),)
        result = segment_boundaries(weighted, text, max_display_width=3)
        self.assertEqual(result, (SubtitleSegment(0, 8), SubtitleSegment(8, 10)))


# ---------------------------------------------------------------------------
# 14. Multiple candidate input (real pipeline, structural sanity)
# ---------------------------------------------------------------------------


class RealPipelineStructuralSanityTests(unittest.TestCase):
    def test_real_pipeline_output_produces_valid_contiguous_segmentation(self):
        text = "這是重點。接下來介紹範例，謝謝大家。"
        weighted = _weighted(text)
        result = segment_boundaries(weighted, text, max_display_width=12)
        self.assertGreaterEqual(len(result), 1)
        self.assertEqual(result[0].start, 0)
        self.assertEqual(result[-1].end, len(text))
        for a, b in zip(result, result[1:]):
            self.assertEqual(a.end, b.start)
        for seg in result:
            reconstructed_width = sum(
                2 if __import__("unicodedata").east_asian_width(ch) in ("W", "F") else 1
                for ch in text[seg.start:seg.end]
            )
            self.assertLessEqual(reconstructed_width, 12)


# ---------------------------------------------------------------------------
# 15. Deterministic repeated execution
# ---------------------------------------------------------------------------


class DeterminismTests(unittest.TestCase):
    def test_repeated_calls_with_equal_input_return_equal_results(self):
        text = "abcdefghij"
        first_call = segment_boundaries(_dense_weighted(text, {5: 100.0}), text, max_display_width=6)
        second_call = segment_boundaries(_dense_weighted(text, {5: 100.0}), text, max_display_width=6)
        self.assertEqual(first_call, second_call)


if __name__ == "__main__":
    unittest.main()
