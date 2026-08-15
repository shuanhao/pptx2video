"""Phase 2D Production Integration - Step 1: Adapter.

This module answers exactly one question: "what would the accepted Phase 1
-> 2A -> 2B -> 2C -> 2D pipeline produce, expressed in the exact contract
shape the existing production subtitle pipeline already expects?" It is an
orchestration and representation-conversion layer only - it introduces no
new evidence, no new scoring, no new classification, and no new
segmentation algorithm of its own.

    Raw notes text
        |
        v
    text_structure.analyze_text_structure()            (Phase 1, untouched)
        |
        v
    boundary_observation.observe_boundaries()           (Phase 2A, untouched)
        |
        v
    boundary_classification.classify_boundaries()        (Phase 2B, untouched)
        |
        v
    boundary_scoring.score_boundaries()                  (Phase 2C, untouched)
        |
        v
    boundary_segmentation.segment_boundaries()            (Phase 2D, untouched
                                                            - frozen since
                                                            Round 1)
        |
        v
    THIS MODULE - contract conversion only
        |
        v
    [{"text", "source_start_offset", "source_end_offset"}, ...]  - the exact
    same shape `subtitle_segmenter.segment_notes_for_subtitles()` returns,
    consumed as-is by `subtitle_alignment.align_segments_with_word_boundaries()`.

This module is Step 1 of the two-step migration plan in
`docs/phase2d/PHASE_2D_PRODUCTION_INTEGRATION_DESIGN.md` (Option B,
Adapter). It is NOT wired into any production call path - nothing in
`subtitle_pipeline.py` imports or calls this module, and this round of work
does not add any such wiring, feature flag, or runtime selection mechanism
(Step 2, explicitly out of scope here).

WHAT THIS MODULE DELIBERATELY DOES NOT DO
--------------------------------------------
- It does not re-implement, duplicate, or second-guess any part of Phase
  1-2C's evidence gathering, classification, or scoring. Every
  `WeightedBoundary` consumed by `segment_boundaries()` is produced by
  calling the real, unmodified `analyze_text_structure()` ->
  `observe_boundaries()` -> `classify_boundaries()` -> `score_boundaries()`
  chain, exactly once, in that order.
- It does not re-implement, duplicate, or modify Phase 2D's own algorithm.
  `segment_boundaries()` is called as-is, unmodified, with no post-hoc
  correction of its chosen cut positions.
- It does not add any colon-specific compatibility rule. The already-scored,
  already-classified treatment of ":"/"：" (falls to `BoundaryClass.OTHER`
  in `boundary_classification.py`, per the accepted Round 6 "Colon Handling
  Integration Decision") flows through this adapter completely unmodified -
  see "COLON HANDLING" below.
- It does not attempt to compensate for any of Phase 2D's known, documented
  limitations (no CJK/jieba word-boundary awareness, conservative raw-text
  width measurement - see "KNOWN LIMITATIONS PRESERVED, NOT FIXED" below).
- It does not modify `subtitle_segmenter.py`, `subtitle_pipeline.py`,
  `subtitle_alignment.py`, or any Phase 1-2D module. It only *imports* two
  existing private helper functions from `subtitle_segmenter.py`
  (`_display_text_for_span`, `_strip_trailing_punctuation`) - see "DISPLAY
  TEXT CONSTRUCTION" below for why this is a call, not a modification.
- It is a pure function of its input: deterministic, no I/O, no randomness,
  no hidden/global state, no mutation of its argument.

DISPLAY TEXT CONSTRUCTION (resolves design doc's undecided item)
-----------------------------------------------------------------------
The Phase 2D Production Integration Design document (section on the adapter
interface) left the choice between three options open:

    (a) duplicate `subtitle_segmenter.py`'s private display-text helpers
        locally in this module,
    (b) import and call those private helpers directly, unmodified,
    (c) defer, pending a future additive public-export change to
        `subtitle_segmenter.py`.

This module resolves that decision as **(b)**: it imports
`_display_text_for_span` and `_strip_trailing_punctuation` directly from
`src.subtitle_segmenter` and calls them, unmodified, on the exact same
`(source_text, start, end)` triple `subtitle_segmenter.py`'s own
`segment_notes_for_subtitles()` would use for an equivalent span. Rationale:

    - It guarantees byte-for-byte identical display-text semantics to
      production for any given (source_text, start, end) triple - there is
      no risk of this module's own copy of the whitespace-normalization or
      trailing-punctuation-stripping rules silently drifting out of sync
      with `subtitle_segmenter.py`'s if that file is ever revised.
    - It does not require modifying `subtitle_segmenter.py` in any way
      (no export added, no signature changed, no whitespace touched) -
      Python does not enforce module-level privacy, so importing a
      leading-underscore name is a read-only *call*, not a modification of
      the file that defines it.
    - It avoids introducing a second, independently-maintained
      interpretation of display-text semantics (option (a)'s risk) purely
      to avoid an import of a private name.
    - A direct, immediate consequence: whenever this adapter and
      `subtitle_segmenter.segment_notes_for_subtitles()` choose the *same*
      cut offsets for a given input, their `"text"` fields are *provably*
      identical (same function, same arguments) - so every observed
      shadow-mode divergence in this round's comparison harness (see
      `tests/test_shadow_mode_comparison.py`) is attributable entirely to a
      difference in *where* the two systems chose to cut, never to a
      difference in how a chosen span's text is displayed.

    This is a private-function *call*, not a public API change of any kind;
    `subtitle_segmenter.py` itself is not modified by this decision. If a
    future round adds a proper public export to `subtitle_segmenter.py`
    (design doc option (c)), this adapter's two-line import statement is the
    only thing that would need to change.

COLON HANDLING (binding constraint - see Round 6 decision)
----------------------------------------------------------------
This adapter adds no colon-specific logic anywhere. Colon characters
(":"/"：") are classified by the unmodified `boundary_classification.py`
exactly as they already are (falling to `BoundaryClass.OTHER`, per the
approved v1 clause-punctuation taxonomy, which deliberately excludes
colon), and scored by the unmodified `boundary_scoring.py` exactly as any
other `OTHER`-classified boundary would be. The resulting difference from
`subtitle_segmenter.py`'s own colon-splitting behavior (colon is one of its
`_SECONDARY_BREAK_CHARS`) is an accepted, expected, already-investigated
divergence - tracked by the shadow-mode comparison harness under the
`COLON_DRIVEN_DIVERGENCE` category, not compensated for here.

KNOWN LIMITATIONS PRESERVED, NOT FIXED
-------------------------------------------
The following already-documented Phase 1-2D characteristics flow through
this adapter unmodified. None of them are worked around, compensated for,
or silently patched here:

    1. No CJK/jieba word-boundary awareness in Phase 2D - a long
       unpunctuated CJK run can be cut mid-word. Tracked by the shadow
       harness as `WORD_BOUNDARY_DIVERGENCE`.
    2. Phase 2D measures raw `source_text[start:end]` display width, not
       the normalized/stripped display width `subtitle_segmenter.py`
       ultimately shows - conservative (never produces an over-width final
       line) but can cut more eagerly than necessary, most visibly when
       runs of literal whitespace sit between CJK characters. Tracked by
       the shadow harness as `WIDTH_MEASUREMENT_DIVERGENCE`.
    3. Colon-handling divergence - see "COLON HANDLING" above.
    4. Numeric patterns shaped like "16:9"/"1920:1080" are not protected as
       a single atomic unit by either system - this is a pre-existing,
       shared gap (see `text_structure._NUMERIC_RE`/`_TIME_RE`), not
       introduced or worsened by this adapter. In practice, because the
       only candidate boundary inside such a pattern is the colon itself,
       an observed divergence here is captured by the
       `COLON_DRIVEN_DIVERGENCE` category, not a separate category.
    5. No semantic phrase model, no audio timing/subtitle-duration logic,
       no new upstream boundary evidence of any kind - this adapter adds
       none of these, matching Phase 2D's own explicit scope.

A SEPARATE, NEWLY OBSERVED EDGE CASE (documented here, not fixed, not
silently absorbed into the shadow-mode corpus - see the implementation
report for this round)
-----------------------------------------------------------------------------
`segment_boundaries()` (Phase 2D, frozen) returns `()` unconditionally
whenever its `weighted_boundaries` argument is empty - and
`boundary_observation.observe_boundaries()` only ever produces zero
candidates when the *entire* `source_text` passed to it is 0 or 1
characters long (it enumerates one candidate per integer position `1 <=
position < len(source_text)`). Consequently, this adapter returns `[]` for
any input whose total text is 0 or 1 characters long - including a single,
non-whitespace, otherwise-meaningful character (e.g. a slide whose entire
notes/subtitle text is just "A" or "好") - whereas
`subtitle_segmenter.segment_notes_for_subtitles()` still returns one
segment for that same single character. This is a genuine behavioral
difference from production, but it is an extremely narrow edge case (a
real slide's entire narration text being 0-1 characters) that does not fit
any of the four named shadow-mode divergence categories, and fixing it
would require modifying the frozen `boundary_segmentation.py` - out of
scope for this adapter. It is pinned by a dedicated regression test in
`tests/test_boundary_segmentation_adapter.py`
(`ShortInputContractTests.test_single_character_input_returns_empty_list`)
documenting the adapter's actual behavior, and is deliberately excluded
from the automated shadow-mode corpus (which uses realistic subtitle-length
text, per the round's required corpus items) rather than being forced
through the four-category classifier as an unclassified failure. See this
round's implementation report, "New/Unexpected Divergences", for the full
writeup.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.boundary_classification import classify_boundaries
from src.boundary_observation import observe_boundaries
from src.boundary_scoring import score_boundaries
from src.boundary_segmentation import DEFAULT_MAX_DISPLAY_WIDTH, segment_boundaries
from src.subtitle_segmenter import _display_text_for_span, _strip_trailing_punctuation
from src.text_structure import analyze_text_structure

__all__ = ["DEFAULT_MAX_DISPLAY_WIDTH", "segment_notes_for_subtitles_via_boundary_engine"]


def _weighted_boundaries_for_text(source_text: str):
    """Run the real, unmodified Phase 1 -> 2A -> 2B -> 2C chain over
    ``source_text``, exactly once, in order. No step here re-implements,
    re-detects, or second-guesses anything a prior step already computed -
    see module docstring.
    """
    analysis = analyze_text_structure(source_text)
    candidates = observe_boundaries(analysis)
    classified = classify_boundaries(candidates)
    return score_boundaries(classified)


def segment_notes_for_subtitles_via_boundary_engine(
    text: str,
    max_display_width: int = DEFAULT_MAX_DISPLAY_WIDTH,
) -> List[Dict[str, Any]]:
    """Segment one slide's raw notes text into subtitle line candidates,
    using the accepted Phase 1-2D boundary-scoring pipeline instead of
    `subtitle_segmenter.py`'s hand-written punctuation-splitting rules.

    This is a drop-in-*shaped* alternative to
    `subtitle_segmenter.segment_notes_for_subtitles()`: same argument
    shape, same return-value contract
    (``{"text", "source_start_offset", "source_end_offset"}`` dicts, in
    reading order, offsets into the original ``text`` argument). It is not
    wired into any production call path by this round of work - see module
    docstring.

    Args:
        text: The original notes text, exactly as would be passed to
            `subtitle_segmenter.segment_notes_for_subtitles()` - i.e. the
            same string sent to edge-tts, paragraph structure and
            punctuation intact. Mirrors that function's own leniency:
            ``None`` and other falsy non-str values are treated as ``""``.
        max_display_width: Maximum display width per line, passed straight
            through to `boundary_segmentation.segment_boundaries()`
            (full-width/CJK characters count as 2, everything else as 1 -
            identical measurement convention to `subtitle_segmenter.py`,
            though applied to the raw span rather than the normalized
            display text - see module docstring, "KNOWN LIMITATIONS
            PRESERVED, NOT FIXED", item 2).

    Returns:
        A list of ``{"text": str, "source_start_offset": int,
        "source_end_offset": int}`` dicts, in reading order. Empty input
        (or input producing no `WeightedBoundary` candidates at all - see
        module docstring's "A SEPARATE, NEWLY OBSERVED EDGE CASE") returns
        ``[]``. A segment whose display text strips down to nothing is
        skipped, mirroring `subtitle_segmenter.segment_notes_for_subtitles`'s
        own identical skip rule.
    """
    source_text = str(text or "")

    weighted_boundaries = _weighted_boundaries_for_text(source_text)
    segments = segment_boundaries(weighted_boundaries, source_text, max_display_width=max_display_width)

    result: List[Dict[str, Any]] = []
    for segment in segments:
        display_text = _strip_trailing_punctuation(
            _display_text_for_span(source_text, segment.start, segment.end)
        )
        if not display_text:
            continue
        result.append({
            "text": display_text,
            "source_start_offset": segment.start,
            "source_end_offset": segment.end,
        })

    return result
