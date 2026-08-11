"""Phase 2B of the subtitle segmentation evolution: Boundary Classification.

This module answers exactly one question: "what *type* of structural
boundary is this?" It does not answer "should the subtitle be cut here?" -
that judgment (a score, a weight, a should_cut decision) is explicitly out
of scope and reserved for later phases.

    BoundaryCandidate (Phase 2A)
        |
        v
    Phase 2B - Boundary Classification  (this module)
        |
        v
    ClassifiedBoundary (one BoundaryClass per candidate)
        |
        v
    Phase 2C - Weight / Scoring          (not implemented yet)
        |
        v
    Phase 2D - Segmentation Integration  (not implemented yet)

WHAT THIS MODULE DELIBERATELY DOES NOT DO
--------------------------------------------
- It does not score, weight, prioritize, or judge boundaries. There is no
  `score`/`weight`/`priority`/`confidence`/`should_cut`/`cut` field
  anywhere in this module, and `ClassifiedBoundary` carries nothing beyond
  the original `BoundaryCandidate` plus a single `BoundaryClass` label.
- It does not re-run Phase 1 or Phase 2A, and does not re-detect paired
  delimiters, punctuation sequences, emoji, emoticons, or technical/atomic
  spans. Every classification decision below is computed purely from
  fields Phase 2A already produced on the `BoundaryCandidate` it is given
  (`BoundaryFeatures`, `StructuralBoundaryContext`) - this module never
  imports `text_structure.py` or calls `analyze_text_structure()`.
- It does not perform multi-label classification. Each `BoundaryCandidate`
  receives at most one `BoundaryClass` (see `classify_boundary`).
- It does not mutate its input. `BoundaryCandidate`/`BoundaryFeatures` are
  frozen dataclasses and this module only ever reads their fields; a
  `ClassifiedBoundary` holds the exact same `candidate` object it was
  given (see `ClassifiedBoundary.candidate` - never a copy).
- It is a pure function of its input: deterministic, no I/O, no
  randomness, no hidden/global state, no dependency on execution order,
  external services, current time, or environment encoding.

THE FOUR BOUNDARY CLASSES (frozen taxonomy - do not extend)
-----------------------------------------------------------------
    SENTENCE_FINAL - the boundary is a valid terminal-ending boundary
        whose terminal punctuation evidence contains explicit
        sentence-final punctuation. Read directly off Phase 2A's
        `BoundaryFeatures.contains_sentence_final_punctuation` - this
        module never re-implements the terminal-ending chain traversal
        that field already encodes (paired-delimiter/emoji/emoticon
        transparency, nested closing delimiters, etc. all already live in
        `boundary_observation.py` and are reused as-is here).
    ELLIPSIS - the boundary is at the END of an ellipsis-only punctuation
        sequence (see `_is_ellipsis` for the precise, evidence-only way
        this is derived from Phase 2A fields without re-detecting
        anything).
    CLAUSE - the boundary immediately follows one of a small, fixed set
        of clause-level punctuation characters (see
        `_CLAUSE_PUNCTUATION_CHARS`), and that character is not part of a
        Phase 1-recognized atomic/technical structure (see
        `_is_technical_or_atomic_protected`).
    OTHER - none of the above apply. This is a deliberately neutral
        "insufficient evidence for a more specific primary boundary type"
        result - it does NOT mean forbidden, invalid, do-not-cut, or zero
        score. Colon (":"/"："), character-class transitions, and plain
        whitespace boundaries all fall here in this v1, simply because no
        rule in this module claims them - not because they are explicitly
        excluded by name.

CLASSIFICATION PRECEDENCE (frozen - do not reorder)
---------------------------------------------------------
    SENTENCE_FINAL > ELLIPSIS > CLAUSE > OTHER

Checked in exactly this order, first match wins. This is what makes e.g.
"真的……？" (an ellipsis run immediately followed by "？") resolve to
SENTENCE_FINAL rather than ELLIPSIS - `contains_sentence_final_punctuation`
is already True for that boundary (Phase 2A's own composition check on the
punctuation_sequence span), and SENTENCE_FINAL is checked first.

ELLIPSIS: HOW IT IS DERIVED WITHOUT RE-DETECTING ANYTHING (see decision 9)
-------------------------------------------------------------------------------
`_is_ellipsis` uses:

    punctuation_sequence_state == END  and  not contains_sentence_final_punctuation

This is an *evidence combination*, not a re-detection of ellipsis
composition. It relies on a specific, documented property of Phase 1's
frozen punctuation-sequence character universe (see
`text_structure._SEQUENCE_CHARS` = ellipsis chars "…." union question
chars "?？" union exclaim chars "!！"): those are the *only* characters
that can ever appear inside a `punctuation_sequence` span. Consequently, a
sequence whose composition contains none of the sentence-final characters
(`。！？!?` - see `contains_sentence_final_punctuation`'s own composition
check in `boundary_observation.py`) can only be composed of ellipsis
characters (`…`/`.`), since question/exclaim characters are themselves
always sentence-final. This module depends on that upstream invariant
holding; it does not re-scan the sequence's characters itself to verify
it. If Phase 1's punctuation-sequence character universe ever changes
(e.g. a new character family is added), this equivalence - and this
module's ELLIPSIS rule - would need to be re-examined.

TECHNICAL / ATOMIC PROTECTION (see `_is_technical_or_atomic_protected`)
-----------------------------------------------------------------------------
Only Phase 1 `atomic`/`technical` spans block a clause character from
being classified as CLAUSE - checked via strict containment
(`span.start < position < span.end`) over
`BoundaryFeatures.structural_context.containing_spans`, which Phase 2A
already computed across every nesting depth. `paired_delimiter` and
`punctuation_sequence` are deliberately NOT in the blocking set: a comma
inside a quotation or parenthetical is still ordinary clause punctuation,
not technical/atomic content - only technical/atomic content (a number
with thousands separators, a version string, a URL, ...) suppresses
CLAUSE, falling back to OTHER. Sentence-final punctuation immediately
following technical/atomic content (e.g. "版本 1.0。") is never suppressed
by this protection, because SENTENCE_FINAL is evaluated before CLAUSE ever
runs, and `contains_sentence_final_punctuation` does not consult
containing-span type information at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Sequence, Tuple

from src.boundary_observation import BoundaryCandidate, PunctuationSequenceState

# ---------------------------------------------------------------------------
# Data model (frozen - see Phase 2B design decision record)
# ---------------------------------------------------------------------------


class BoundaryClass(str, Enum):
    SENTENCE_FINAL = "sentence_final"
    ELLIPSIS = "ellipsis"
    CLAUSE = "clause"
    OTHER = "other"


@dataclass(frozen=True)
class ClassifiedBoundary:
    candidate: BoundaryCandidate
    boundary_class: BoundaryClass


# ---------------------------------------------------------------------------
# Classification rules
# ---------------------------------------------------------------------------

#: The v1 clause-level punctuation taxonomy (approved decision 4). Colon
#: (":"/"：") is deliberately excluded - see module docstring.
_CLAUSE_PUNCTUATION_CHARS = "，,、；;"

#: Only these Phase 1 structural_type values block CLAUSE (approved
#: decision 5). `paired_delimiter` and `punctuation_sequence` are
#: deliberately excluded - see module docstring.
_PROTECTED_STRUCTURAL_TYPES: FrozenSet[str] = frozenset({"atomic", "technical"})


def _is_sentence_final(candidate: BoundaryCandidate) -> bool:
    """SENTENCE_FINAL evidence is read verbatim from Phase 2A - see module
    docstring. This is the sole source of truth; no independent
    terminal-ending traversal is performed here.
    """
    return candidate.features.contains_sentence_final_punctuation


def _is_ellipsis(candidate: BoundaryCandidate) -> bool:
    """See module docstring's "ELLIPSIS: how it is derived without
    re-detecting anything" for why this specific combination of Phase 2A
    fields is equivalent to "boundary is at the end of an ellipsis-only
    punctuation sequence."
    """
    return (
        candidate.features.punctuation_sequence_state == PunctuationSequenceState.END
        and not candidate.features.contains_sentence_final_punctuation
    )


def _is_technical_or_atomic_protected(candidate: BoundaryCandidate) -> bool:
    return any(
        span_ref.type in _PROTECTED_STRUCTURAL_TYPES
        for span_ref in candidate.features.structural_context.containing_spans
    )


def _is_clause(candidate: BoundaryCandidate) -> bool:
    if candidate.left_char not in _CLAUSE_PUNCTUATION_CHARS:
        return False
    return not _is_technical_or_atomic_protected(candidate)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_boundary(candidate: BoundaryCandidate) -> BoundaryClass:
    """Classify a single Phase 2A ``BoundaryCandidate`` into exactly one
    ``BoundaryClass``, per the frozen precedence
    SENTENCE_FINAL > ELLIPSIS > CLAUSE > OTHER (see module docstring). Pure
    function: deterministic, reads ``candidate`` only, never mutates it.
    """
    if _is_sentence_final(candidate):
        return BoundaryClass.SENTENCE_FINAL
    if _is_ellipsis(candidate):
        return BoundaryClass.ELLIPSIS
    if _is_clause(candidate):
        return BoundaryClass.CLAUSE
    return BoundaryClass.OTHER


def classify_boundaries(candidates: Sequence[BoundaryCandidate]) -> Tuple[ClassifiedBoundary, ...]:
    """Classify every candidate in ``candidates``, preserving order. Each
    resulting ``ClassifiedBoundary.candidate`` is the exact same object
    passed in - never a copy - per the module docstring's "does not
    mutate its input" guarantee.
    """
    return tuple(
        ClassifiedBoundary(candidate=candidate, boundary_class=classify_boundary(candidate))
        for candidate in candidates
    )
