"""Phase 2C of the subtitle segmentation evolution: Boundary Scoring.

This module answers exactly one question: "given an already-observed and
already-classified boundary, what signed relative numeric preference does
the locked Phase 2C numeric model assign to it?" It does not answer "should
a subtitle line break here?" - that judgment (a threshold, a should_cut
decision, candidate selection, ranking, or dynamic programming) is
explicitly out of scope and reserved for Phase 2D, which does not exist yet.

    ClassifiedBoundary (Phase 2B)
        |
        v
    Phase 2C - Boundary Scoring  (this module)
        |
        v
    WeightedBoundary (one signed relative `score` per candidate, plus the
    original `candidate` and `boundary_class` - no should_cut, no
    threshold, no ranking, no DP state)
        |
        v
    Phase 2D - Segmentation Integration  (not implemented yet)

This module is a mechanical implementation of the already-approved Phase 2C
numeric model. It makes no new design decisions - every number, every
interaction rule, and every field this module reads is fixed by, and
traceable to, the documents below. See in particular:

    docs/phase2c/contracts/PHASE_2C_PRODUCTION_SCORING_IMPLEMENTATION_CONTRACT.md
        (the authoritative implementation contract this module follows)
    docs/phase2c/decisions/PHASE_2C_NUMERIC_BASELINE_DECISION.md
    docs/phase2c/calibration/reports/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_ROUND1_REPORT.md
    docs/phase2c/decisions/PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_DECISION.md
    docs/phase2c/calibration/reports/PHASE_2C_PROTECTION_POST_CORRECTION_VERIFICATION_REPORT.md
    docs/phase2c/decisions/PHASE_2C_OVERALL_NUMERIC_RECONCILIATION.md

WHAT THIS MODULE DELIBERATELY DOES NOT DO
--------------------------------------------
- It does not decide whether a boundary is a good or bad place to cut. There
  is no `should_cut`, `threshold`, `ranking`, "preferred"/"discouraged"
  category, and no dynamic programming anywhere in this module - only a
  single signed relative `score` float per boundary.
- It does not run Phase 1, Phase 2A, or Phase 2B itself. `score_boundary()`
  and `score_boundaries()` take an already-computed
  `boundary_classification.ClassifiedBoundary` (or a sequence of them) as
  their only argument, and never call `text_structure.analyze_text_structure()`,
  `boundary_observation.observe_boundaries()`,
  `boundary_classification.classify_boundary()`, or
  `boundary_classification.classify_boundaries()`. Phase 2B's classification
  is read verbatim off `classified.boundary_class` - never recomputed,
  never independently inferred from raw punctuation, and Phase 2B's frozen
  `SENTENCE_FINAL > ELLIPSIS > CLAUSE > OTHER` precedence is never
  duplicated or reordered here.
- It does not re-detect character classes, technical/atomic spans, or
  punctuation-sequence state. Every field this module reads
  (`left_character_class`, `right_character_class`,
  `structural_context.containing_spans`, `punctuation_sequence_state`) was
  already computed by Phase 2A and is read directly off
  `classified.candidate.features` - never recomputed.
- It does not normalize, threshold, floor, clamp, or convert the score to a
  probability. There is no `score >= X -> cut` (or equivalent) decision
  anywhere in this module. The output is a signed relative score only.
- It does not mutate its input. `ClassifiedBoundary`, `BoundaryCandidate`,
  and `BoundaryFeatures` are all frozen dataclasses (defined in
  `boundary_classification.py` / `boundary_observation.py`) and this module
  only ever reads their fields; a `WeightedBoundary` holds the exact same
  `candidate` object its input `ClassifiedBoundary` held (see
  `WeightedBoundary.candidate` - never a copy).
- It is a pure function of its input: deterministic, no I/O, no randomness,
  no hidden/global state. Calling `score_boundary(classified)` twice with an
  equal `classified` always returns an equal result.
- It does not import, call, or otherwise depend on any calibration script
  (`scripts/calibrate_phase2c_*.py`) or calibration matrix at runtime.
  Those are design evidence used to derive and validate the numeric model
  below - not a runtime dependency of production code. This module's
  formula independently reproduces (never imports) the same arithmetic.

LOCKED NUMERIC MODEL (see the implementation contract, section 5, for the
full derivation and evidence trail - not re-litigated here)
-----------------------------------------------------------------------------
    Base Classification:
        SENTENCE_FINAL = +80.0
        ELLIPSIS       = +65.0
        CLAUSE         = +35.0
        OTHER          =   0.0
    Positive Evidence:
        CJK -> LATIN   = +15.0   (symmetric with LATIN -> CJK)
        LATIN -> CJK   = +15.0
        Whitespace     = +10.0   (flat, candidate-level, non-stacking)
    Protection:
        Technical      = -30.0
        Atomic         = -30.0   (Technical + Atomic on one candidate is
                                   strongest-only: -30.0, never -60.0)
        INTERNAL       = -20.0   (fully independent, additive on top of
                                   whatever protection penalty, if any,
                                   already applies: Technical + INTERNAL =
                                   Atomic + INTERNAL = -50.0)

    score = base_classification_score
          + positive_evidence_score
          + protection_score

No value above may be changed by this module. See the implementation
contract's section 13 for which combinations above are confirmed by real
pipeline evidence and which are mechanically defined by this same formula
but not yet empirically observed on any real candidate (e.g.
`CLAUSE + Technical`, `Atomic + INTERNAL`) - this module implements the
identical formula for both categories; it does not special-case, suppress,
or clamp the empirically-unverified combinations merely because no
calibration round has observed them yet.

IMPORTANT: EXACT TRANSITION TRIGGER (see contract section 10)
-----------------------------------------------------------------
`BoundaryFeatures.character_class_transition` is a broad, pre-computed
boolean meaning "the left and right character classes differ" - true for
*any* class change (e.g. CJK -> DIGIT, CJK -> PUNCTUATION,
WHITESPACE -> CJK), not only the specific CJK<->LATIN pair the Positive
Evidence Decision actually calibrated and locked. This module deliberately
does **not** use that field to trigger the +15.0 transition bonus - it
checks the exact `{CJK, LATIN}` character-class pair directly, because that
exact pair check is what every piece of empirical evidence behind the
`+15.0` lock (PE-01, PE-02, PE-03, PE-09) was gathered against.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Sequence, Tuple

from src.boundary_classification import BoundaryClass, ClassifiedBoundary
from src.boundary_observation import BoundaryCandidate, CharacterClass, PunctuationSequenceState

# ---------------------------------------------------------------------------
# Data model (frozen - see docs/phase2c/contracts/PHASE_2C_PRODUCTION_SCORING_IMPLEMENTATION_CONTRACT.md)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WeightedBoundary:
    """Phase 2C's sole output type: a `ClassifiedBoundary` plus one signed
    relative `score`. Carries exactly three fields - `candidate`,
    `boundary_class`, `score` - and nothing else (see the implementation
    contract section 4/14: no `base_classification_score`,
    `positive_evidence_score`, or `protection_score` field, no
    `confidence`/`probability`/`weight`/`category`/`should_cut`/`threshold`/
    `ranking`/DP state). `candidate` is the exact same `BoundaryCandidate`
    object the input `ClassifiedBoundary` held - never a copy (see
    `score_boundary`'s "never a copy" guarantee below).
    """

    candidate: BoundaryCandidate
    boundary_class: BoundaryClass
    score: float


# ---------------------------------------------------------------------------
# Locked numeric model (see module docstring; not to be changed here)
# ---------------------------------------------------------------------------

_BASE_SCORES: Dict[BoundaryClass, float] = {
    BoundaryClass.SENTENCE_FINAL: 80.0,
    BoundaryClass.ELLIPSIS: 65.0,
    BoundaryClass.CLAUSE: 35.0,
    BoundaryClass.OTHER: 0.0,
}

_TRANSITION_BONUS = 15.0
_WHITESPACE_BONUS = 10.0
_PROTECTION_PENALTY = -30.0
_SEQUENCE_PENALTY = -20.0

_PROTECTED_STRUCTURAL_TYPES = frozenset({"technical", "atomic"})


# ---------------------------------------------------------------------------
# Component scoring (each derived solely from already-observed/-classified
# evidence; see module docstring - no re-detection of any kind)
# ---------------------------------------------------------------------------


def _base_classification_score(boundary_class: BoundaryClass) -> float:
    """Read Phase 2B's classification verbatim and map it to its locked
    base score. Fails fast (`KeyError`) rather than silently defaulting if
    `boundary_class` is ever not one of the four frozen `BoundaryClass`
    members - see the implementation contract section 15/17 ("do not
    silently map unknown classes to OTHER").
    """
    return _BASE_SCORES[boundary_class]


def _positive_evidence_score(candidate: BoundaryCandidate) -> float:
    """Transition (+15.0, exact CJK<->LATIN pair only - see module
    docstring's "IMPORTANT: EXACT TRANSITION TRIGGER") plus Whitespace
    (+10.0, flat, at most once per candidate by construction of the Phase
    2A data model - each candidate has exactly one `left_character_class`
    and one `right_character_class`, so no additional non-stacking logic is
    needed here).
    """
    features = candidate.features
    lc = features.left_character_class
    rc = features.right_character_class

    transition_bonus = 0.0
    if (lc == CharacterClass.CJK and rc == CharacterClass.LATIN) or (
        lc == CharacterClass.LATIN and rc == CharacterClass.CJK
    ):
        transition_bonus = _TRANSITION_BONUS

    whitespace_bonus = _WHITESPACE_BONUS if (lc == CharacterClass.WHITESPACE or rc == CharacterClass.WHITESPACE) else 0.0

    return transition_bonus + whitespace_bonus


def _protection_score(candidate: BoundaryCandidate) -> float:
    """Technical/Atomic (-30.0, strongest-only - i.e. a flat penalty applied
    once if either or both are present, never summed to -60.0) plus
    INTERNAL (-20.0, fully independent and additive on top of whatever
    protection penalty, if any, already applies).
    """
    features = candidate.features
    containing_types = {span_ref.type for span_ref in features.structural_context.containing_spans}
    is_protected = bool(containing_types & _PROTECTED_STRUCTURAL_TYPES)
    protection_penalty = _PROTECTION_PENALTY if is_protected else 0.0

    is_internal = features.punctuation_sequence_state == PunctuationSequenceState.INTERNAL
    sequence_penalty = _SEQUENCE_PENALTY if is_internal else 0.0

    return protection_penalty + sequence_penalty


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def score_boundary(classified: ClassifiedBoundary) -> WeightedBoundary:
    """Score exactly one already-classified boundary using the locked Phase
    2C numeric model. Pure function: deterministic, reads `classified` only,
    never mutates it. Does not call `classify_boundary()` or any Phase 2A/2B
    detection function - `classified.boundary_class` and
    `classified.candidate.features` are trusted as already-computed,
    already-correct evidence (see module docstring).

    `weighted.candidate is classified.candidate` always holds - the
    resulting `WeightedBoundary` never copies the original candidate.

    Fails fast (raises `TypeError`) on `None` or any non-`ClassifiedBoundary`
    input, per the implementation contract's "prefer fail-fast behavior for
    programmer errors" - no elaborate validation is performed, and the
    upstream Phase 2A/2B frozen data model is otherwise trusted as-is.
    """
    if not isinstance(classified, ClassifiedBoundary):
        raise TypeError(f"score_boundary() requires a ClassifiedBoundary, got {classified!r}")

    boundary_class = classified.boundary_class
    candidate = classified.candidate

    score = (
        _base_classification_score(boundary_class)
        + _positive_evidence_score(candidate)
        + _protection_score(candidate)
    )

    return WeightedBoundary(candidate=candidate, boundary_class=boundary_class, score=score)


def score_boundaries(classified_boundaries: Sequence[ClassifiedBoundary]) -> Tuple[WeightedBoundary, ...]:
    """Score every item in `classified_boundaries`, preserving order and
    producing exactly one `WeightedBoundary` per input item. Delegates each
    item to `score_boundary()` - no scoring logic is duplicated here. Does
    not mutate `classified_boundaries`. An empty input returns `()`.

    Fails fast (raises `TypeError`) if `classified_boundaries` is `None`
    (iterating `None` already raises `TypeError` naturally; this is not
    additionally guarded to avoid elaborate validation logic beyond what
    the implementation contract calls for).
    """
    return tuple(score_boundary(item) for item in classified_boundaries)
