"""Phase 2D of the subtitle segmentation evolution: Boundary Segmentation.

This module answers the question Phase 2C deliberately leaves open: "given
every already-scored boundary in a text, which positions should actually be
used to cut it into subtitle segments?" It is the first stage in this
pipeline responsible for a real decision (a chosen set of cut positions),
rather than only evidence or a relative preference number.

    WeightedBoundary[]  (Phase 2C, one signed relative score per boundary)
        |
        v
    Phase 2D - Boundary Segmentation  (this module)
        |
        v
    SubtitleSegment[]  (chosen (start, end) offset spans - no display text,
    no duration, no timing, no production integration)

Full design rationale lives in
`docs/phase2d/PHASE_2D_SCOPE_AND_ARCHITECTURE.md` (read in full before this
module was written) - this docstring summarizes the parts needed to read the
code, not the full design discussion.

WHAT THIS MODULE DELIBERATELY DOES NOT DO
--------------------------------------------
- It does not call `text_structure.analyze_text_structure()`,
  `boundary_observation.observe_boundaries()`,
  `boundary_classification.classify_boundaries()`, or
  `boundary_scoring.score_boundaries()` itself, and it does not recompute or
  second-guess any `WeightedBoundary.score` - every score is read verbatim.
- It does not construct final display text (whitespace normalization,
  trailing-punctuation stripping remain `subtitle_segmenter.py`'s
  responsibility - untouched by this module). Its own width measurement
  operates on the raw `source_text[start:end]` slice, not a normalized
  display version - this makes its width constraint slightly more
  conservative than the final displayed width will be, which is safe (never
  produces an over-width final line) even though it is not byte-for-byte
  the same measurement `subtitle_segmenter.py` uses.
- It does not know anything about Chinese word segmentation (no jieba
  dependency). Phase 1-2C carry no word-boundary evidence, so this module
  has nothing to consume for that; a long, unpunctuated CJK run with no
  character-class transition anywhere in it will be cut based on width
  alone, with no guarantee of landing between two real words. This is a
  known, accepted limitation (design doc section 11/16), not an oversight.
- It does not modify `subtitle_segmenter.py` or integrate with the
  production pipeline in any way. It is a standalone module producing
  offsets only.
- It does not use a fixed score threshold anywhere (`score >= X -> cut`).
  Scores are only ever compared to each other, never to a constant (design
  doc section 9).
- It is a pure function of its input: deterministic, no I/O, no randomness,
  no hidden/global state, no mutation of `weighted_boundaries` or
  `source_text`.

ALGORITHM (see design doc sections 12/15 for the full rationale)
-----------------------------------------------------------------------------
Per paragraph (paragraphs are hard boundaries - `"\\n"` positions in
`source_text`, matching `subtitle_segmenter._split_paragraphs_with_offsets`'s
own convention, deliberately re-implemented independently here rather than
imported, to avoid coupling this new module to that existing one):

1. Frame the paragraph's candidates: every `WeightedBoundary` whose
   `candidate.position` falls strictly inside the paragraph is a candidate
   cut position (`_internal_positions`).
2. Determine the minimum feasible segment count `K` via one greedy
   left-to-right pass that always advances as far as still fits under
   `max_display_width` (`_greedy_min_k_boundaries`) - a pure width question,
   ignoring scores entirely. Left-to-right maximal advance is optimal for
   minimizing segment count over an ordered candidate set (same argument
   `subtitle_segmenter._pack_greedy`'s docstring makes for the analogous
   width-balancing problem).
3. Among all ways to partition the paragraph into exactly `K` width-feasible
   segments, choose the one maximizing the total score of its internal cut
   positions, tie-broken by the lowest sum of squared segment widths
   (`_select_cut_positions`) - a dynamic program directly generalizing
   `subtitle_segmenter._pack_units`'s own fixed-`K` DP, replacing its
   width-balance-only objective with boundary-score maximization.

Fixing `K` from the width constraint *before* optimizing which candidates to
use is what makes a fixed score threshold unnecessary: segment count is
never influenced by score, only segment *placement* is, so there is no way
for the optimization to prefer over-segmenting just to accumulate more small
positive scores (see design doc section 9 for why an un-fixed-`K` objective
would be wrong).

D04 (the CJK<->LATIN transition candidate at `+15.0` versus a nearby
whitespace-adjacent variant of the same conceptual boundary at `+10.0`) is
resolved by this general model with no special-case code: both are ordinary
members of the same candidate pool the DP above already searches over, and
whichever one participates in the higher-total-score, width-feasible
partition is the one selected (design doc section 8).

Last-resort behavior: if even the very next available candidate does not
fit under `max_display_width` from the current segment's start (only
possible when `max_display_width` is smaller than a single character's
display width, or the input's candidate set is sparser than the real
pipeline's - see `feasible()` in `_select_cut_positions`), the pass still
advances to that candidate anyway, deterministically, rather than looping
forever or raising - the same "finest available granularity is always an
acceptable fallback" principle `subtitle_segmenter._hard_split_by_characters`
uses as its own last resort.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from src.boundary_scoring import WeightedBoundary

#: Matches `subtitle_segmenter.DEFAULT_MAX_DISPLAY_WIDTH` (18 full-width
#: characters). Deliberately duplicated rather than imported - see module
#: docstring's "what this module deliberately does not do".
DEFAULT_MAX_DISPLAY_WIDTH = 36


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubtitleSegment:
    """One chosen subtitle segment: an offset span into the `source_text`
    passed to `segment_boundaries()`. Carries exactly `start`/`end` - no
    text, no duration, no score (see module docstring).
    """

    start: int
    end: int


# ---------------------------------------------------------------------------
# Display width (independent re-implementation - see module docstring)
# ---------------------------------------------------------------------------


def _char_width(ch: str) -> int:
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def _display_width(s: str) -> int:
    return sum(_char_width(ch) for ch in s)


def _fits(source_text: str, start: int, end: int, max_width: int) -> bool:
    return _display_width(source_text[start:end]) <= max_width


# ---------------------------------------------------------------------------
# Paragraph splitting (independent re-implementation - see module docstring)
# ---------------------------------------------------------------------------


def _split_paragraphs(source_text: str) -> List[Tuple[int, int]]:
    """Split `source_text` on `"\\n"` into (start, end) offset spans, one per
    non-blank paragraph - mirroring
    `subtitle_segmenter._split_paragraphs_with_offsets`'s own convention
    (blank paragraphs are skipped as segment sources but still separate
    whatever comes before/after them).
    """
    paragraphs: List[Tuple[int, int]] = []
    start = 0
    for i, ch in enumerate(source_text):
        if ch == "\n":
            if source_text[start:i].strip():
                paragraphs.append((start, i))
            start = i + 1
    if source_text[start:].strip():
        paragraphs.append((start, len(source_text)))
    return paragraphs


# ---------------------------------------------------------------------------
# Per-paragraph candidate framing
# ---------------------------------------------------------------------------


def _internal_positions(p_start: int, p_end: int, sorted_positions: Sequence[int]) -> List[int]:
    """Candidate positions strictly inside one paragraph - `p_start`/`p_end`
    themselves are forced structural boundaries, never chosen based on
    score even if a `WeightedBoundary` happens to exist at that exact
    offset (see module docstring's algorithm summary, step 1).
    """
    return [p for p in sorted_positions if p_start < p < p_end]


# ---------------------------------------------------------------------------
# Minimum feasible segment count (width only - see module docstring, step 2)
# ---------------------------------------------------------------------------


def _greedy_min_k_boundaries(anchors: Sequence[int], source_text: str, max_width: int) -> List[int]:
    """`anchors` is `[p_start] + internal_candidate_positions + [p_end]`,
    strictly ascending. Returns the minimum-cardinality subsequence of
    `anchors` (always starting at `anchors[0]` and ending at `anchors[-1]`)
    such that every consecutive pair fits under `max_width` - via a single
    left-to-right pass that always advances as far as still fits, which is
    optimal for minimizing segment count over an ordered candidate set (see
    module docstring).
    """
    boundaries = [anchors[0]]
    n = len(anchors)
    i = 1
    while boundaries[-1] != anchors[-1]:
        current_start = boundaries[-1]
        chosen: Optional[int] = None
        j = i
        while j < n and _fits(source_text, current_start, anchors[j], max_width):
            chosen = anchors[j]
            j += 1
        if chosen is None:
            # Not even the very next anchor fits - deterministic last-resort
            # advance (see module docstring's "last-resort behavior").
            chosen = anchors[i]
            j = i + 1
        boundaries.append(chosen)
        i = j
    return boundaries


# ---------------------------------------------------------------------------
# Score-optimal DP over exactly K segments (see module docstring, step 3)
# ---------------------------------------------------------------------------


def _select_cut_positions(
    p_start: int,
    p_end: int,
    positions: Sequence[int],
    score_map: Dict[int, float],
    source_text: str,
    max_width: int,
) -> List[int]:
    """Return the chosen boundary positions for one paragraph, including
    `p_start` and `p_end`: the minimum feasible segment count `K` (width
    only), then the highest-total-score `K`-segment partition among all
    width-feasible choices, tie-broken by the lowest sum of squared segment
    widths.
    """
    anchors = [p_start] + list(positions) + [p_end]

    greedy_boundaries = _greedy_min_k_boundaries(anchors, source_text, max_width)
    target_k = len(greedy_boundaries) - 1
    if target_k <= 1:
        return greedy_boundaries

    n = len(anchors)

    def feasible(i: int, j: int) -> bool:
        # A segment is feasible if it fits under the width budget, or it is
        # the finest granularity available (adjacent anchors) - the same
        # last-resort allowance `_greedy_min_k_boundaries` relies on, so a
        # valid K-segment path always exists for this DP to find (mirrors
        # `subtitle_segmenter._pack_units`'s own defensive "should be
        # unreachable in practice, but fall back defensively" stance below).
        return j == i + 1 or _fits(source_text, anchors[i], anchors[j], max_width)

    def segment_score(i: int, j: int) -> float:
        if j == n - 1:
            # anchors[-1] is the forced paragraph end, never a scored choice.
            return 0.0
        return score_map.get(anchors[j], 0.0)

    def segment_sq_width(i: int, j: int) -> int:
        width = _display_width(source_text[anchors[i]:anchors[j]])
        return width * width

    # dp[i][k] = (best total score, lowest sum-of-squared-widths achieving
    # that score) partitioning anchors[0:i+1] into exactly k segments ending
    # at anchors[i]. Lexicographic comparison: score first (higher wins),
    # squared-width sum second (lower wins) - see module docstring.
    dp: List[List[Optional[Tuple[float, int]]]] = [[None] * (target_k + 1) for _ in range(n)]
    choice: List[List[Optional[int]]] = [[None] * (target_k + 1) for _ in range(n)]
    dp[0][0] = (0.0, 0)

    for i in range(1, n):
        for k in range(1, target_k + 1):
            best: Optional[Tuple[float, int]] = None
            best_j: Optional[int] = None
            for j in range(k - 1, i):
                prev = dp[j][k - 1]
                if prev is None or not feasible(j, i):
                    continue
                candidate = (prev[0] + segment_score(j, i), prev[1] + segment_sq_width(j, i))
                if best is None or candidate[0] > best[0] or (
                    candidate[0] == best[0] and candidate[1] < best[1]
                ):
                    best = candidate
                    best_j = j
            dp[i][k] = best
            choice[i][k] = best_j

    if dp[n - 1][target_k] is None:
        # Defensive fallback - not expected in practice given `feasible()`
        # always allows the finest granularity; mirrors
        # `subtitle_segmenter._pack_units`'s identical defensive stance.
        return greedy_boundaries

    result: List[int] = []
    i, k = n - 1, target_k
    while k > 0:
        result.append(anchors[i])
        j = choice[i][k]
        assert j is not None
        i, k = j, k - 1
    result.append(anchors[0])
    result.reverse()
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def segment_boundaries(
    weighted_boundaries: Sequence[WeightedBoundary],
    source_text: str,
    max_display_width: int = DEFAULT_MAX_DISPLAY_WIDTH,
) -> Tuple[SubtitleSegment, ...]:
    """Turn a full document's already-scored `weighted_boundaries` into an
    ordered tuple of `SubtitleSegment` offset spans, per the algorithm in
    the module docstring.

    `weighted_boundaries` must be exactly what
    `boundary_scoring.score_boundaries()` (or an equivalent, unmodified
    sequence of `score_boundary()` results) produced for `source_text` -
    this function does not verify that consistency itself, matching the
    "trust the caller's already-computed evidence" convention Phase 2A-2C
    already use for their own inputs. It never calls
    `text_structure.analyze_text_structure()`,
    `boundary_observation.observe_boundaries()`,
    `boundary_classification.classify_boundaries()`, or
    `boundary_scoring.score_boundaries()` itself.

    Pure function: deterministic, does not mutate either argument. Fails
    fast (`TypeError`/`ValueError`) on malformed input rather than
    performing elaborate validation, matching this pipeline's existing
    convention.

    Empty `weighted_boundaries` (or a `source_text` with no non-blank
    paragraphs) returns `()`.
    """
    if not isinstance(source_text, str):
        raise TypeError(f"segment_boundaries() requires source_text to be a str, got {source_text!r}")
    if weighted_boundaries is None:
        raise TypeError("segment_boundaries() requires weighted_boundaries, got None")

    weighted_boundaries = tuple(weighted_boundaries)
    for wb in weighted_boundaries:
        if not isinstance(wb, WeightedBoundary):
            raise TypeError(f"segment_boundaries() requires WeightedBoundary items, got {wb!r}")

    if max_display_width <= 0:
        raise ValueError(f"segment_boundaries() requires a positive max_display_width, got {max_display_width!r}")

    if not weighted_boundaries:
        return ()

    score_map: Dict[int, float] = {wb.candidate.position: wb.score for wb in weighted_boundaries}
    sorted_positions = sorted(score_map.keys())

    segments: List[SubtitleSegment] = []
    for p_start, p_end in _split_paragraphs(source_text):
        positions = _internal_positions(p_start, p_end, sorted_positions)
        boundaries = _select_cut_positions(p_start, p_end, positions, score_map, source_text, max_display_width)
        for a, b in zip(boundaries, boundaries[1:]):
            segments.append(SubtitleSegment(start=a, end=b))

    return tuple(segments)
