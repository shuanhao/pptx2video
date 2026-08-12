"""Phase 2A of the subtitle segmentation evolution: Boundary Observation Layer.

This module answers exactly one question: "what objective, structural facts
surround this one specific character gap in the text?" It does not answer
"should a subtitle line break here?" - that judgment (a score, a weight, a
should_cut decision) is explicitly out of scope and reserved for later
phases.

    Raw Text + Phase 1 TextAnalysisResult
        |
        v
    Phase 2A - Boundary Observation Layer  (this module)
        |
        v
    BoundaryCandidate[] (one per internal character gap, each carrying
    purely observational BoundaryFeatures - no score, no weight, no
    should_cut, no boundary category)
        |
        v
    Phase 2B - Boundary Classification       (not implemented yet)
        |
        v
    Phase 2C - Weight / Scoring              (not implemented yet)
        |
        v
    Phase 2D - Segmentation Integration      (not implemented yet)

WHAT THIS MODULE DELIBERATELY DOES NOT DO
--------------------------------------------
- It does not decide whether a boundary is a good or bad place to cut. There
  is no score, weight, priority, confidence, "preferred"/"acceptable"/
  "discouraged"/"forbidden" category, and no dynamic programming anywhere in
  this module.
- It does not run Phase 1 itself. ``observe_boundaries()`` takes an
  already-computed ``text_structure.TextAnalysisResult`` as its only
  argument and never calls ``text_structure.analyze_text_structure()`` -
  Phase 1 runs exactly once, by whatever assembles the pipeline, and this
  module is a pure, second consumer of that one result.
- It does not modify Phase 1's spans, re-detect paired delimiters, re-detect
  emoji/emoticons, or build a second, independent punctuation taxonomy. Every
  structural fact this module reports is read directly off the ``Span``
  objects (and their ``children``) that Phase 1 already produced - see
  "Reused vs. new logic" below for exactly which parts are reused and which
  are genuinely new.
- It does not depend on ``src/subtitle_segmenter.py`` (or any other part of
  the existing subtitle pipeline) and nothing in the existing pipeline calls
  into this module - same one-directional-independence discipline Phase 1
  established for itself, extended one layer further down the pipeline.
- It is a pure function of its input: deterministic, no I/O, no randomness,
  no hidden state. Calling ``observe_boundaries(analysis)`` twice with an
  equal ``analysis`` always returns an equal result.

REUSED VS. NEW LOGIC
------------------------
Reused directly from Phase 1's output (no re-implementation):
    - Paired-delimiter matching: read via ``Span.structural_type ==
      "paired_delimiter"`` and ``Span.children`` - never re-matched.
    - Emoji/emoticon detection: read via ``Span.structural_type == "atomic"``
      with ``Span.subtype in ("emoji", "emoticon")`` - never re-matched.
    - Punctuation-sequence detection and run composition: read via
      ``Span.structural_type == "punctuation_sequence"`` and the span's own
      ``text`` - never re-matched. ``PunctuationSequenceState`` and the
      punctuation-composition part of ``contains_sentence_final_punctuation``
      are both derived solely from these spans.

Genuinely new in this module (not a duplication of anything Phase 1 has,
because Phase 1 was never asked to answer these questions):
    - ``CharacterClass``: a general, per-character classifier (CJK / Latin /
      digit / whitespace / punctuation / emoji / symbol / other). Phase 1
      has no equivalent - its detectors only ever answer "does a *pattern*
      start here," never "what kind of character is this one codepoint, in
      isolation." Per an explicit project decision, this also does not
      import Phase 1's private emoji character-block constant
      (``text_structure._EMOJI_CHAR_CLASS``): ``CharacterClass.EMOJI`` is
      intentionally a separate, coarser, independently-declared concern from
      Phase 1's curated emoji detector, and the two are not required to
      agree on every codepoint (see ``_EMOJI_CODEPOINT_RANGES`` below).
    - The single-bare-terminal-character check at the base case of the
      terminal-ending chain (see ``_walk_terminal_chain``): unavoidable
      because Phase 1's own ``_detect_punctuation_sequences`` deliberately
      never emits a span for a lone, single occurrence of ``。``/``！``/
      ``？``/``.``/``!``/``?`` (its documented "run length 1 doesn't qualify
      unless it's the single ellipsis character" rule) - so there is no span
      to look up for that specific, narrow case, and a direct character
      comparison against a small, Phase-2A-owned constant
      (``_SENTENCE_FINAL_CHARS``) is the only way to observe it.

OFFSET / DETERMINISM CONTRACT
---------------------------------
``observe_boundaries(analysis)`` returns exactly one ``BoundaryCandidate``
for every integer ``position`` with ``1 <= position < len(analysis.source_text)``,
in ascending order - never a candidate at position ``0`` or
``len(source_text)`` (there is no character gap there to describe). Every
field on every returned object is derived solely from ``analysis`` (and the
``source_text`` it carries) - no hidden state, no accumulated scoring, no
global correction pass.

TERMINAL-ENDING CHAIN (sentence-final evidence)
----------------------------------------------------
``BoundaryFeatures.contains_sentence_final_punctuation`` answers: "does the
legal terminal-ending chain immediately preceding this boundary contain
explicit sentence-final punctuation (``。！？.!?``)?" This is evidence only -
it carries no boundary-strength judgment, and ellipsis characters
(``…``/``.``) are never counted as sentence-final punctuation on their own
(they still participate as ordinary members of a punctuation_sequence span,
but that alone does not make the span "sentence-final" - see
``_sequence_contains_sentence_final``).

The chain never scans arbitrary raw text backwards. It only ever follows two
kinds of *transparent* structural attachment, both read directly from Phase 1
spans, and both strictly shrink the position being examined (so the walk is
guaranteed to terminate):

    1. An ``atomic``/``emoji`` or ``atomic``/``emoticon`` span ending exactly
       at the position being examined is transparent - the walk continues
       just before it (``span.start``).
    2. A ``paired_delimiter`` span (any span whose ``structural_type`` is in
       ``text_structure.STRUCTURAL_CONTAINER_TYPES``) ending exactly at the
       position being examined is transparent - the walk continues *inside*
       it, at the position just before its own closing character
       (``span.end - 1``).

Critically, once the walk descends into a paired_delimiter, every subsequent
lookup is scoped to that specific span's own ``children`` - never a generic,
depth-unrestricted re-scan of every span in the analysis. This mirrors Phase
1's own "containment is geometric; children is structural" principle: a span
that merely happens to end at the same computed offset without being the
span Phase 1's own nesting resolution actually placed inside this specific
delimiter (e.g. a span that lost the widest-first sibling contest and became
an independent top-level span, per Phase 1's documented behavior) must never
be picked up by this walk. Consulting ``.children`` directly makes that
impossible; a generic position-keyed re-scan could not offer the same
guarantee. The *first* lookup (at the real, externally-given boundary
``position`` itself) is the only exception - it searches every span in the
analysis at any depth, which is legitimate there because ``position`` is a
real fact about the document, not an offset this module invented.

The walk terminates (returns its answer) the moment it reaches:
    - a ``punctuation_sequence`` span - the answer is whether that span's
      own text contains any explicit sentence-final character (see
      ``_sequence_contains_sentence_final`` - this is a composition check,
      not a check of the span's ``subtype``, since e.g. an
      ``ellipsis_question`` sequence like "……？" does contain "？" and must
      be reported ``True``);
    - any other, non-transparent structural span (e.g. ``technical``,
      or an ``atomic`` span that isn't emoji/emoticon) - ordinary
      structured content, so the answer is ``False``;
    - or no span at all ending at the position being examined - the answer
      is whether the single literal character immediately before that
      position is one of ``_SENTENCE_FINAL_CHARS``.

KNOWN LIMITATIONS (accepted for this version, not bugs)
-----------------------------------------------------------
- If ordinary, non-transparent content (e.g. a stray space) sits directly
  between the last piece of terminal punctuation and a closing delimiter
  (e.g. "「你好！！ 」" with a trailing space before "」"), the chain stops at
  that ordinary content and reports ``False`` - it does not look further
  back past it. This is a direct consequence of "ordinary content
  terminates the chain" and is intentional, not an oversight.
- ``CharacterClass.CJK`` is a coarse bucket covering Han, Hiragana,
  Katakana, and Hangul together (as specified), identified via a Unicode
  *character name* substring check (``"CJK"``, ``"HIRAGANA"``,
  ``"KATAKANA"``, ``"HANGUL"``) rather than a full Unicode Script property
  classifier - this is a deliberately coarse, stdlib-only heuristic, not a
  complete script classification system, and does not add any new
  dependency. ``CharacterClass.LATIN`` is identified the same way (Unicode
  name containing ``"LATIN"``), which naturally also covers fullwidth Latin
  forms (e.g. "Ａ"/"ａ", whose Unicode names are "FULLWIDTH LATIN CAPITAL
  LETTER A" / "FULLWIDTH LATIN SMALL LETTER A").
- ``CharacterClass.EMOJI`` uses a small, independently-declared set of
  common Unicode emoji code-point ranges (stdlib-only - no third-party
  ``emoji``/``regex`` package). It does not attempt to recognize
  multi-codepoint grapheme clusters (ZWJ sequences, skin-tone modifiers) as
  a single unit - each codepoint is classified independently, same
  accepted gap as Phase 1's own emoji detector, though the two are not
  guaranteed to agree on every codepoint (see "Reused vs. new logic" above).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple

from src.text_structure import STRUCTURAL_CONTAINER_TYPES, Span, TextAnalysisResult

# ---------------------------------------------------------------------------
# Data model (frozen - see Phase 2A design decision record)
# ---------------------------------------------------------------------------


class CharacterClass(str, Enum):
    WHITESPACE = "whitespace"
    CJK = "cjk"
    LATIN = "latin"
    DIGIT = "digit"
    PUNCTUATION = "punctuation"
    EMOJI = "emoji"
    SYMBOL = "symbol"
    OTHER = "other"


@dataclass(frozen=True)
class SpanRef:
    start: int
    end: int
    type: str
    subtype: Optional[str]


@dataclass(frozen=True)
class StructuralBoundaryContext:
    containing_spans: Tuple[SpanRef, ...]
    left_adjacent_spans: Tuple[SpanRef, ...]
    right_adjacent_spans: Tuple[SpanRef, ...]


class PunctuationSequenceState(str, Enum):
    NONE = "none"
    INTERNAL = "internal"
    END = "end"


@dataclass(frozen=True)
class BoundaryFeatures:
    left_character_class: CharacterClass
    right_character_class: CharacterClass
    character_class_transition: bool
    punctuation_sequence_state: PunctuationSequenceState
    contains_sentence_final_punctuation: bool
    structural_context: StructuralBoundaryContext


@dataclass(frozen=True)
class BoundaryCandidate:
    position: int
    left_char: str
    right_char: str
    features: BoundaryFeatures


# ---------------------------------------------------------------------------
# CharacterClass classification
# ---------------------------------------------------------------------------
# Intentionally coarse and stdlib-only (see module docstring's "Known
# limitations"). Declared entirely independently of text_structure.py's own,
# differently-scoped character sets (e.g. its emoji block list, its narrow
# adjacency-punctuation list) - see the module docstring's "Reused vs. new
# logic" for why this independence is deliberate, not an oversight.

#: A small, Phase-2A-owned set of common Unicode emoji code-point ranges.
#: Deliberately not imported from text_structure.py - see module docstring.
_EMOJI_CODEPOINT_RANGES: Tuple[Tuple[int, int], ...] = (
    (0x1F300, 0x1F5FF),  # Misc Symbols and Pictographs
    (0x1F600, 0x1F64F),  # Emoticons block
    (0x1F680, 0x1F6FF),  # Transport and Map Symbols
    (0x1F900, 0x1F9FF),  # Supplemental Symbols and Pictographs
    (0x2600, 0x26FF),  # Misc Symbols
    (0x2700, 0x27BF),  # Dingbats
)

#: Unicode character-*name* substrings used to coarsely recognize the CJK
#: writing systems this project cares about (Han, Hiragana, Katakana,
#: Hangul) without building a full Unicode Script property classifier - see
#: module docstring's "Known limitations".
_CJK_NAME_MARKERS: Tuple[str, ...] = ("CJK", "HIRAGANA", "KATAKANA", "HANGUL")

#: Unicode general categories (see unicodedata.category) treated as SYMBOL
#: once EMOJI/PUNCTUATION have already been ruled out.
_SYMBOL_CATEGORIES = frozenset({"Sm", "Sc", "Sk", "So"})


def _is_emoji_char(ch: str) -> bool:
    codepoint = ord(ch)
    return any(lo <= codepoint <= hi for lo, hi in _EMOJI_CODEPOINT_RANGES)


def _unicode_name(ch: str) -> str:
    try:
        return unicodedata.name(ch)
    except ValueError:
        return ""


def classify_character(ch: str) -> CharacterClass:
    """Classify a single character into one of the eight coarse
    ``CharacterClass`` buckets. See the module docstring's "Known
    limitations" for the precise, deliberately coarse rules used for CJK/
    Latin/emoji. Classification order matters (each check only applies once
    every earlier one has been ruled out):

    whitespace -> digit -> emoji -> punctuation -> cjk -> latin -> symbol
    -> other
    """
    if ch.isspace():
        return CharacterClass.WHITESPACE
    if ch.isdigit():
        return CharacterClass.DIGIT
    if _is_emoji_char(ch):
        return CharacterClass.EMOJI
    if unicodedata.category(ch).startswith("P"):
        return CharacterClass.PUNCTUATION

    name = _unicode_name(ch)
    if any(marker in name for marker in _CJK_NAME_MARKERS):
        return CharacterClass.CJK
    if "LATIN" in name:
        return CharacterClass.LATIN

    if unicodedata.category(ch) in _SYMBOL_CATEGORIES:
        return CharacterClass.SYMBOL
    return CharacterClass.OTHER


# ---------------------------------------------------------------------------
# Span flattening (generic tree walk over Phase 1's public `children` field -
# not a reuse or duplication of any Phase 1 detection/nesting logic)
# ---------------------------------------------------------------------------


def _flatten_spans(spans: Sequence[Span]) -> List[Span]:
    flat: List[Span] = []
    for span in spans:
        flat.append(span)
        flat.extend(_flatten_spans(span.children))
    return flat


def _to_span_ref(span: Span) -> SpanRef:
    return SpanRef(start=span.start, end=span.end, type=span.structural_type, subtype=span.subtype)


# ---------------------------------------------------------------------------
# StructuralBoundaryContext
# ---------------------------------------------------------------------------


def _structural_context_at(position: int, flat_spans: Sequence[Span]) -> StructuralBoundaryContext:
    containing = [s for s in flat_spans if s.start < position < s.end]
    containing.sort(key=lambda s: (s.start, -s.end, s.structural_type, s.subtype))

    left_adjacent = [s for s in flat_spans if s.end == position]
    left_adjacent.sort(key=lambda s: (s.start, s.end, s.structural_type, s.subtype))

    right_adjacent = [s for s in flat_spans if s.start == position]
    right_adjacent.sort(key=lambda s: (s.start, s.end, s.structural_type, s.subtype))

    return StructuralBoundaryContext(
        containing_spans=tuple(_to_span_ref(s) for s in containing),
        left_adjacent_spans=tuple(_to_span_ref(s) for s in left_adjacent),
        right_adjacent_spans=tuple(_to_span_ref(s) for s in right_adjacent),
    )


# ---------------------------------------------------------------------------
# PunctuationSequenceState
# ---------------------------------------------------------------------------


def _punctuation_sequence_state_at(position: int, flat_spans: Sequence[Span]) -> PunctuationSequenceState:
    for span in flat_spans:
        if span.structural_type != "punctuation_sequence":
            continue
        if span.end == position:
            return PunctuationSequenceState.END
        if span.start < position < span.end:
            return PunctuationSequenceState.INTERNAL
    return PunctuationSequenceState.NONE


# ---------------------------------------------------------------------------
# Sentence-final evidence (terminal-ending chain)
# ---------------------------------------------------------------------------

#: Explicit sentence-final punctuation characters used for the BARE,
#: single-literal-character fallback (no structural span covers this
#: position at all). Includes ASCII "." alongside "!"/"?" and their CJK
#: counterparts, per the approved Phase 2A decision that ASCII punctuation
#: is supported on equal footing with CJK punctuation. This is a
#: Phase-2A-owned constant, independent of text_structure.py's own,
#: differently-scoped `_ADJACENCY_PUNCTUATION_CHARS` (which includes clause
#: marks like ，、；： that are not sentence-final evidence here).
_SENTENCE_FINAL_CHARS_BARE = "。！？.!?"

#: Explicit sentence-final punctuation characters used when inspecting the
#: COMPOSITION of an actual punctuation_sequence span (2+ characters, or a
#: lone "…"). Deliberately EXCLUDES ASCII "." - unlike the bare-character
#: case above, "." is also text_structure.py's own ellipsis-run character
#: (see its `_ELLIPSIS_CHARS = "…."`), so any run of 2+ "."s is always
#: classified by Phase 1 as an ellipsis-family sequence, never as multiple
#: separate sentence-ending periods. Presence-checking "." inside such a
#: run would make a pure ellipsis run (e.g. "......") register as
#: sentence-final purely because it's built out of ASCII dots - which
#: directly contradicts the required "......" -> False example. "…" itself
#: is excluded for the same reason it's excluded from the bare set: an
#: ellipsis, alone, is never sentence-final evidence.
_SENTENCE_FINAL_CHARS_IN_SEQUENCE = "。！？!?"

_TERMINAL_ATTACHMENT_SUBTYPES = frozenset({"emoji", "emoticon"})


def _sequence_contains_sentence_final(span: Span) -> bool:
    """Whether a punctuation_sequence span's own text contains any explicit
    sentence-final character - a composition check, not a check of the
    span's `subtype` (an "ellipsis_question" sequence like "……？" does
    contain "？" and must be reported True; see module docstring). Uses
    `_SENTENCE_FINAL_CHARS_IN_SEQUENCE` (excludes ASCII ".") - see that
    constant's docstring for why a pure "." run must not match here.
    """
    return any(ch in _SENTENCE_FINAL_CHARS_IN_SEQUENCE for ch in span.text)


def _walk_terminal_chain(cur: int, siblings: Sequence[Span], source_text: str) -> bool:
    match = next((s for s in siblings if s.end == cur), None)

    if match is None:
        # Base case: no structural span *ends* exactly here. That alone is
        # NOT sufficient to conclude the character immediately before `cur`
        # is genuinely unspanned - it may still be strictly *interior* to a
        # technical/atomic/punctuation_sequence span (e.g. the first "." in
        # "3.14", or any non-final "." in an ASCII ellipsis run like
        # "......" - see Phase 2C ASCII Period Upstream Correction Decision,
        # Round A/B). Only when no span in `siblings` covers that character
        # at all does the bare, single-literal-character check apply - see
        # module docstring's "no span to look up" justification, which is
        # specifically about a mark with no span of any kind. Any span
        # covering the character - regardless of type - means this is
        # ordinary structured content, exactly like the explicit
        # non-transparent-span branch below; the walk must not
        # independently re-decide the question by looking at the bare
        # character in that case.
        if any(s.start <= cur - 1 < s.end for s in siblings):
            return False
        ch = source_text[cur - 1] if cur > 0 else ""
        return ch in _SENTENCE_FINAL_CHARS_BARE

    if match.structural_type == "punctuation_sequence":
        return _sequence_contains_sentence_final(match)

    if match.structural_type == "atomic" and match.subtype in _TERMINAL_ATTACHMENT_SUBTYPES:
        # Transparent attachment (emoji/emoticon) - keep looking within the
        # same sibling scope for whatever precedes it.
        return _walk_terminal_chain(match.start, siblings, source_text)

    if match.structural_type in STRUCTURAL_CONTAINER_TYPES:
        # Transparent closing delimiter - descend INTO this specific span's
        # own children only (never a generic, depth-unrestricted re-scan;
        # see module docstring for why that distinction matters).
        return _walk_terminal_chain(match.end - 1, match.children, source_text)

    # Any other structural content (e.g. technical/other atomic subtypes) is
    # ordinary content - the chain stops here.
    return False


def _contains_sentence_final_punctuation(position: int, flat_spans: Sequence[Span], source_text: str) -> bool:
    # The first hop is the only place a depth-unrestricted lookup is
    # legitimate: `position` is a real, externally-given boundary, not an
    # offset this module computed - see module docstring.
    return _walk_terminal_chain(position, flat_spans, source_text)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def observe_boundaries(analysis: TextAnalysisResult) -> Tuple[BoundaryCandidate, ...]:
    """Observe every internal character-gap boundary in ``analysis``.

    Consumes an already-computed Phase 1 ``TextAnalysisResult`` - never
    calls ``text_structure.analyze_text_structure()`` itself (see module
    docstring). Returns one ``BoundaryCandidate`` per integer position with
    ``1 <= position < len(analysis.source_text)``, in ascending order. This
    is a pure function: deterministic, no I/O, no randomness, no hidden
    state, no segmentation decision of any kind.
    """
    source_text = analysis.source_text
    flat_spans = _flatten_spans(analysis.spans)

    candidates: List[BoundaryCandidate] = []
    for position in range(1, len(source_text)):
        left_char = source_text[position - 1]
        right_char = source_text[position]
        left_class = classify_character(left_char)
        right_class = classify_character(right_char)

        features = BoundaryFeatures(
            left_character_class=left_class,
            right_character_class=right_class,
            character_class_transition=left_class != right_class,
            punctuation_sequence_state=_punctuation_sequence_state_at(position, flat_spans),
            contains_sentence_final_punctuation=_contains_sentence_final_punctuation(
                position, flat_spans, source_text
            ),
            structural_context=_structural_context_at(position, flat_spans),
        )
        candidates.append(
            BoundaryCandidate(position=position, left_char=left_char, right_char=right_char, features=features)
        )

    return tuple(candidates)
