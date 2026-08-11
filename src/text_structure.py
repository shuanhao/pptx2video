"""Phase 1 of the subtitle segmentation evolution: Text Structure Span Detection.

This module answers exactly one question about a piece of raw text: "what
recognizable *structural* patterns appear in it, and where?" It does not
answer "where should this text be split for subtitles?" - that is a
different question, deliberately left to later phases.

    Raw Text
        |
        v
    Phase 1 - Text Structure Span Detection  (this module)
        |
        v
    Structural Spans + Context Facts
        |
        v
    Phase 2 - Boundary Feature Analysis            (not implemented yet)
        |
        v
    Phase 3 - Candidate Boundary Engine             (not implemented yet)
        |
        v
    Phase 4 - Weighted Segmentation / DP            (not implemented yet)
        |
        v
    Subtitle Segments -> existing subtitle_alignment.py -> Edge-TTS WordBoundary

WHAT A "STRUCTURAL SPAN" IS
----------------------------
A ``Span`` is a claim of the form: "the characters ``source_text[start:end]``
have a recognizable *structural* identity" - e.g. "this is a pair of
matching brackets", "this is a run of ellipsis/question/exclamation marks",
"this looks like a version number", "this looks like a snake_case
identifier". Spans are produced purely from *character-level format
patterns* (regular expressions, bracket matching, curated fixed lists) -
never from a dictionary of words, a language model, or any notion of what a
piece of text "means".

IMPORTANT INVARIANT - READ BEFORE USING THIS MODULE ELSEWHERE
----------------------------------------------------------------
    A structural span is not necessarily a semantic unit.

For example, in "MediaTek Genio 1200 開發", the atomic detector recognizes
"1200" as a numeric span purely because it has the *shape* of a number -
this says nothing about whether "1200" is a meaningful, independently
citable unit in this sentence (it plainly isn't; it's the last word of a
product model name, "MediaTek Genio 1200"). Similarly, a
``technical``/``identifier`` span is a claim about character *format*
("this token is shaped like MT8395"), never a claim about whether that
token is an important term, a term that must not be split, or a term with
any particular semantic weight. Any code consuming this module's output
that treats a Span's mere existence as "this text is meaningful" or "this
text must not be split apart" is making an assumption this module does not
support and does not intend to support.

WHAT THIS MODULE DELIBERATELY DOES NOT DO
--------------------------------------------
- It does not produce boundaries. There is no ``TextBoundary`` type, no
  ``candidate_boundaries``, no "can/cannot split here" judgment anywhere in
  this module. A Span describes a region of text; it never describes a
  cut point, a preference for or against cutting at some position, or any
  kind of score/weight/priority for such a decision. That is explicitly
  out of scope for Phase 1 and is reserved for Phase 2 (Boundary Feature
  Analysis) and beyond.
- It does not make a segmentation decision. This module has no opinion on
  how a slide's notes should be broken into subtitle lines. It does not
  call, import, or otherwise depend on ``src.subtitle_segmenter``,
  ``src.subtitle_pipeline``, or ``src.subtitle_alignment``, and nothing in
  the existing subtitle segmentation pipeline calls into this module
  either (as of this Phase, ``analyze_text_structure()`` is not wired into
  any production code path - see the module-level test suite for how to
  exercise it independently).
- It does not depend on Edge-TTS, audio, timing, ffmpeg, or PowerPoint.
  This module analyzes a plain Python ``str`` and returns a plain,
  in-memory data structure - no I/O, no network, no external process, no
  randomness. Calling ``analyze_text_structure(text)`` twice with the same
  ``text`` always returns an equal result.
- It does not classify "modifier" semantics. Earlier design iterations of
  this Phase considered attaching a ``role`` (e.g. "modifier") to spans
  like emoji/emoticons/parentheticals - that idea was deliberately dropped
  before implementation. This module only ever records *structural
  geometry facts* about a span's position relative to the surrounding text
  (see ``context_flags`` below) - never an interpretation of what that
  position *means* (e.g. "this is probably expressing an emotion"). Facts
  are preserved for later phases to interpret; this module does not
  interpret them itself.
- It does not build a technical/company/product/modifier dictionary, does
  not use jieba (or any other NLP tool) to *guess* whether a word is a
  technical term, does not use a large language model, embeddings, or any
  statistical language model. Every detector here is a small, deterministic,
  explainable pattern (a regex, a fixed lookup table, or a bracket-matching
  scan) that a reader can fully understand by reading the source.

OFFSET INTEGRITY CONTRACT (hard invariant)
---------------------------------------------
Every ``Span`` in a ``TextAnalysisResult`` (including every span nested
inside another span's ``children``, at any depth) satisfies:

    span.text == source_text[span.start:span.end]
    0 <= span.start < span.end <= len(source_text)

``Span`` itself cannot self-validate this (it has no reference back to the
source string it came from - see the ``Span``/``TextAnalysisResult`` design
notes below for why). Instead:

- Every ``Span`` produced by this module's own detectors is built exclusively
  through the internal ``_make_span()`` factory, which always derives
  ``text`` from ``source_text[start:end]`` itself - callers of the
  detectors never get a chance to pass in a mismatched ``text``.
- ``TextAnalysisResult.__post_init__`` independently re-verifies this
  invariant for *every* span it holds (recursively, including nested
  children) the moment the result object is constructed, and raises
  ``ValueError`` immediately if it ever finds a mismatch - so even a future
  code path that somehow bypasses ``_make_span()`` cannot silently produce
  a ``TextAnalysisResult`` with drifted offsets.

STRUCTURAL CONTAINMENT vs. GEOMETRIC CONTAINMENT
-----------------------------------------------------
    Containment is geometric; children is structural.

Many spans happen to geometrically overlap or contain one another purely as
an artifact of four independent detectors each scanning the same raw text
(e.g. the digits inside a technical/identifier token, such as "8395" inside
"MT8395", are also independently recognized by the atomic detector as their
own numeric span). That kind of containment does not, by itself, mean one
span belongs in the other's ``children`` - it only means two detectors both
produced a true, independent observation about overlapping character
ranges.

``children`` is reserved for genuine *structural* nesting: a region of text
whose boundaries are explicitly marked by an enclosing structure. Only a
``paired_delimiter`` span (something with an explicit opening and closing
character) is a *structural container* in this module (see
``STRUCTURAL_CONTAINER_TYPES``) - it is the only structural_type that can
ever appear as the *outer* span of a ``children`` relationship. A
``technical``, ``atomic``, or ``punctuation_sequence`` span is always a
leaf: even when it geometrically contains another span, that other span
never becomes its ``children``.

When a paired_delimiter's interior contains multiple, mutually-overlapping
detector observations (e.g. "(MT8395)" contains both the identifier
"MT8395" and, separately, the number "8395" inside it), only the single
widest of those mutually-overlapping observations becomes an actual
structural child; anything it already covers is not also counted as a
second child. The narrower observation is not discarded - it still exists,
correctly, as an independent, top-level entry in
``TextAnalysisResult.spans`` (see ``_resolve_overlaps_and_nesting`` for the
exact algorithm). This is also why a top-level span can, in rare cases, be
geometrically located entirely inside another top-level span's range -
"top-level" in this module's output means "not a structural child of
anything", not "does not geometrically overlap anything else".

A hard invariant follows directly from this: **the direct children of any
one span never overlap one another** - for any two direct children A and B
of the same span, either ``A.end <= B.start`` or ``B.end <= A.start``
always holds. This is a distinct guarantee from offset integrity and is
verified independently by this module's own test suite.

KNOWN LIMITATIONS (accepted for this version, not bugs)
-----------------------------------------------------------
- Complex Unicode emoji grapheme clusters (ZWJ sequences such as the
  "family" emoji made of four joined people, or a person emoji combined
  with a skin-tone modifier) are matched as several separate ``atomic``/
  ``emoji`` spans (and the ZWJ joiner itself, and skin-tone modifiers, may
  either be silently skipped or separately reported), not as one combined
  span. Python's standard library has no built-in notion of a Unicode
  "extended grapheme cluster", and per this Phase's explicit scope this
  module does not add the third-party ``regex`` package (which supports
  ``\\X`` grapheme-cluster matching) to work around that. This is a
  deliberately accepted gap, not an oversight.
- Emoticon detection (``atomic``/``emoticon``) only recognizes a small,
  fixed, case-sensitive list of common patterns (see ``_EMOTICON_DEFS``).
  Variants in other letter case (e.g. "xd" instead of "XD"), or any
  kaomoji/emoticon not on that list, are not recognized.
- ``technical``/``version`` only recognizes the strict ``vX.Y[.Z]`` prefix
  convention (e.g. "v0.10.0"). A "Name X.Y[.Z]" shape (e.g.
  "Python 3.13.2", "USB 3.2", "HDMI 2.1") is instead reported under
  ``technical``/``identifier`` - see that detector's docstring for why this
  is a deliberate choice, not an oversight.
- ``technical`` detection never attempts to recognize multi-word technical
  concepts that require knowing a specific brand/product/company name (e.g.
  "MediaTek Genio 1200", "Power Management IC", "display engine"). Per the
  approved Phase 1 scope, only sub-parts of such phrases that already have
  an unambiguous *character format* (e.g. the "1200" in "MediaTek Genio
  1200", recognized as ``atomic``/``numeric``) are reported; the rest of
  the phrase is simply not covered by any span. This is the single most
  important accepted scope boundary of this Phase - see the module
  docstring's "structural span is not necessarily a semantic unit" note.
- ``context_flags``' geometric classification is paragraph-relative (a
  "paragraph" is a run of text between ``\\n`` characters, matching how
  ``src/pptx_parser.py`` already represents notes) and only considers
  whether *meaningful* (non-whitespace, non-punctuation) content exists
  before/after a span within its own paragraph. It has no notion of
  sentence boundaries below the paragraph level (e.g. it does not treat a
  "。" in the middle of a paragraph as starting a new "sentence" for this
  purpose) - see ``_compute_context_flags`` for the precise, deliberately
  simple rule used.
- ASCII straight double quote (``"``) is supported as a paired
  ``quotation`` delimiter, but through a dedicated matcher
  (``_detect_ascii_double_quote_spans``) entirely separate from the
  stack-based bracket matcher used for every other delimiter pair, because
  ``"`` is simultaneously its own opener and closer - see that function's
  docstring. Pairing uses simple left-to-right parity plus a "digit
  immediately before the quote" exclusion for inch/measurement notation
  (e.g. ``5"``, ``4"``). This is a format-only heuristic, not a
  grammar-aware quotation parser: a digit-adjacent quote that happens to
  genuinely be an opening quotation with no space before it (e.g. a quote
  starting immediately after a bare year, ``2024"like this"``) is also
  excluded, and unusual interleavings of genuine quotations with inch marks
  are not guaranteed to pair correctly. These are accepted, documented
  limitations, not defects.
- ASCII straight apostrophe (``'``) is never treated as a paired delimiter
  under any circumstance, and this module does not attempt to. Unlike
  ``"``, which reliably signals "quotation" even though it is
  self-paired, ``'`` is used constantly as a plain apostrophe inside
  ordinary words ("It's", "don't", "John's", "Users'", "rock'n'roll") -
  applying the same parity-pairing strategy used for ``"`` would misfire
  on nearly every contraction and possessive in English text. Recognizing
  genuine single-quote quotations while excluding apostrophes would require
  language-aware disambiguation, which is out of scope for Phase 1.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any, Dict, FrozenSet, List, Mapping, Optional, Pattern, Sequence, Tuple

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

#: The four mutually-exclusive structural identities a Span can have. Every
#: Span has exactly one of these as its ``structural_type``. "modifier" is
#: deliberately NOT one of these - see the module docstring.
STRUCTURAL_TYPES: FrozenSet[str] = frozenset(
    {"paired_delimiter", "punctuation_sequence", "atomic", "technical"}
)

#: The subset of STRUCTURAL_TYPES that may act as a *structural container*
#: (i.e. may own ``children``). See the module docstring's "Structural
#: containment vs. geometric containment" section: containment alone never
#: implies a ``children`` relationship - only a span whose structural_type
#: is in this set can ever be the outer span of one. Today this is exactly
#: ``paired_delimiter`` (something with an explicit opening/closing
#: character); ``technical``/``atomic``/``punctuation_sequence`` spans are
#: always leaves, even when they geometrically contain another span.
STRUCTURAL_CONTAINER_TYPES: FrozenSet[str] = frozenset({"paired_delimiter"})

#: The full set of geometric position facts ``context_flags`` can contain.
#: Exactly one of {"standalone", "sentence_final", "internal"} is always
#: present; "punctuation_adjacency" is independent and may or may not
#: co-occur with any of the other three. See ``_compute_context_flags``.
CONTEXT_FLAGS: FrozenSet[str] = frozenset(
    {"standalone", "sentence_final", "internal", "punctuation_adjacency"}
)


@dataclass(frozen=True)
class Span:
    """A single structural observation about ``source_text[start:end]``.

    Fields are intentionally minimal - see the module docstring and the
    Phase 1 design discussion for what was deliberately left out (no
    ``score``/``weight``/``priority``/``confidence``/``protected``/
    ``role``; no ``parent_id``).

    ``text`` is included as a plain, directly-readable field (rather than
    only being derivable via ``source_text[start:end]``) for convenience in
    tests, debugging, and downstream code - its consistency with
    ``start``/``end`` is guaranteed by construction discipline (see
    ``_make_span``) and independently re-verified for every Span in a
    ``TextAnalysisResult`` at construction time (see
    ``TextAnalysisResult.__post_init__``), not merely assumed.
    """

    start: int
    end: int
    structural_type: str
    subtype: str
    text: str
    source: str
    context_flags: FrozenSet[str] = frozenset()
    attributes: Mapping[str, Any] = field(default_factory=dict)
    children: Tuple["Span", ...] = ()


@dataclass(frozen=True)
class TextAnalysisResult:
    """The complete output of :func:`analyze_text_structure` for one text.

    ``spans`` holds only *top-level* spans - a span fully contained inside
    another appears solely inside that other span's ``children``, never
    also duplicated at the top level (see ``_resolve_overlaps_and_nesting``).
    """

    source_text: str
    spans: Tuple[Span, ...]
    diagnostics: Tuple[str, ...]

    def __post_init__(self) -> None:
        for span in _iter_all_spans(self.spans):
            if not (0 <= span.start < span.end <= len(self.source_text)):
                raise ValueError(
                    f"invalid span offsets: start={span.start!r}, end={span.end!r} "
                    f"for source_text of length {len(self.source_text)}"
                )
            expected_text = self.source_text[span.start : span.end]
            if span.text != expected_text:
                raise ValueError(
                    f"span text/offset mismatch at [{span.start}, {span.end}): "
                    f"span.text={span.text!r} but source_text slice={expected_text!r}"
                )


def _iter_all_spans(spans: Sequence[Span]):
    """Yield every span in ``spans``, recursively including all nested
    ``children`` at every depth. Used for offset-integrity validation and by
    tests; not part of the public API.
    """
    for span in spans:
        yield span
        yield from _iter_all_spans(span.children)


def _make_span(
    source_text: str,
    start: int,
    end: int,
    *,
    structural_type: str,
    subtype: str,
    source: str,
    context_flags: FrozenSet[str] = frozenset(),
    attributes: Optional[Mapping[str, Any]] = None,
    children: Tuple[Span, ...] = (),
) -> Span:
    """The *only* place a :class:`Span` is constructed in this module.

    Always derives ``text`` from ``source_text[start:end]`` itself, rather
    than accepting caller-supplied text - this is what makes
    ``span.text == source_text[span.start:span.end]`` structurally
    impossible to violate from within this module (see the module
    docstring's "Offset integrity contract" section).
    """
    return Span(
        start=start,
        end=end,
        structural_type=structural_type,
        subtype=subtype,
        text=source_text[start:end],
        source=source,
        context_flags=context_flags,
        attributes=MappingProxyType(dict(attributes or {})),
        children=children,
    )


# ---------------------------------------------------------------------------
# Detector 1: paired_delimiter
# ---------------------------------------------------------------------------
# (opening, closing, subtype) - subtype groups delimiters by conventional
# usage, not by every distinct glyph, so downstream code doesn't need to
# know all eleven individual characters to ask "is this a quotation-style
# delimiter?".
_PAIRED_DELIMITERS: Tuple[Tuple[str, str, str], ...] = (
    ("「", "」", "quotation"),  # 「」
    ("『", "』", "quotation"),  # 『』
    ("《", "》", "title_mark"),  # 《》
    ("〈", "〉", "title_mark"),  # 〈〉
    ("（", "）", "parenthetical"),  # （）
    ("(", ")", "parenthetical"),
    ("【", "】", "bracket"),  # 【】
    ("[", "]", "bracket"),
    ("〔", "〕", "bracket"),  # 〔〕
    ("“", "”", "quotation"),  # " "
    ("‘", "’", "quotation"),  # ' '
)
_OPEN_TO_PAIR_INDEX: Dict[str, int] = {
    open_ch: i for i, (open_ch, _close_ch, _subtype) in enumerate(_PAIRED_DELIMITERS)
}
_CLOSE_TO_PAIR_INDEX: Dict[str, int] = {
    close_ch: i for i, (_open_ch, close_ch, _subtype) in enumerate(_PAIRED_DELIMITERS)
}


def _detect_paired_delimiters(text: str) -> Tuple[List[Span], List[str]]:
    """Bracket-match every supported delimiter pair via a single left-to-right
    scan with a stack, producing one *flat* span per successfully matched
    pair (nesting between spans - e.g. a parenthetical fully inside a
    quotation - is deliberately NOT resolved here; that is the job of the
    shared, cross-detector ``_resolve_overlaps_and_nesting`` step below, so
    that same-family and cross-family nesting are both handled by exactly
    one piece of logic instead of two).

    Unmatched delimiters (an opening delimiter with no matching close by
    end of text, or a closing delimiter that doesn't match the innermost
    currently-open delimiter) never raise - they are recorded as plain
    diagnostic strings and otherwise ignored, so a single stray bracket in
    real speaker notes cannot crash analysis of the rest of the text.
    """
    diagnostics: List[str] = []
    spans: List[Span] = []
    stack: List[Tuple[int, int]] = []  # (pair_index, start_offset)

    for i, ch in enumerate(text):
        if ch in _CLOSE_TO_PAIR_INDEX:
            pair_idx = _CLOSE_TO_PAIR_INDEX[ch]
            if stack and stack[-1][0] == pair_idx:
                _, start = stack.pop()
                open_ch, close_ch, subtype = _PAIRED_DELIMITERS[pair_idx]
                spans.append(
                    _make_span(
                        text,
                        start,
                        i + 1,
                        structural_type="paired_delimiter",
                        subtype=subtype,
                        source="paired_delimiter_detector",
                        attributes={"opening": open_ch, "closing": close_ch},
                    )
                )
            else:
                diagnostics.append(f"unmatched closing delimiter {ch!r} at offset {i}")
        elif ch in _OPEN_TO_PAIR_INDEX:
            stack.append((_OPEN_TO_PAIR_INDEX[ch], i))

    for pair_idx, start in stack:
        open_ch = _PAIRED_DELIMITERS[pair_idx][0]
        diagnostics.append(f"unmatched opening delimiter {open_ch!r} at offset {start}")

    return spans, diagnostics


# ---------------------------------------------------------------------------
# Detector 1b: ASCII double-quote paired spans (C-3)
# ---------------------------------------------------------------------------
# ASCII straight double quote (") cannot be added to _PAIRED_DELIMITERS: that
# table's stack-based scan (_detect_paired_delimiters) distinguishes "is this
# an opener?" from "is this a closer?" purely by which distinct character it
# is, via two separate dicts. ASCII '"' is simultaneously its own opener and
# closer, so it needs its own, simpler, separate strategy - see the function
# docstring below and the module docstring's "Known limitations".
#
# ASCII straight apostrophe (') is deliberately NOT handled here or anywhere
# else in this module - see the module docstring's "Known limitations" for
# why (it would misfire on ordinary contractions/possessives).


def _is_inch_mark_quote(text: str, pos: int) -> bool:
    """True if the ``"`` at ``pos`` is immediately preceded by a digit with
    no space (the ``5"``/``4"`` inch/measurement-notation shape). This is a
    pure character-adjacency format check - not a semantic understanding of
    "this means inches" - used to exclude such quotes from ASCII
    quote-pairing entirely, so they never become spurious paired_delimiter
    boundaries (see ``_detect_ascii_double_quote_spans``).
    """
    return pos > 0 and text[pos - 1].isdigit()


def _detect_ascii_double_quote_spans(text: str) -> Tuple[List[Span], List[str]]:
    """Detect ASCII straight double-quote (``"``) paired ``quotation``
    spans, using a strategy independent of the stack-based bracket matcher
    used for every other delimiter pair:

    1. Exclude inch/measurement-shaped quotes (see ``_is_inch_mark_quote``)
       from candidacy entirely - they are left completely inert, exactly as
       before this detector existed. This deliberately does not attempt to
       resolve every ambiguous case (e.g. a digit-adjacent ``"`` that is
       genuinely an opening quotation with no space before it is also
       excluded) - see the module docstring's "Known limitations".
    2. Pair what remains by simple left-to-right parity: the 1st remaining
       ``"`` opens, the 2nd closes, the 3rd opens, the 4th closes, and so
       on. There is no stack here (there is nothing to push/pop against,
       since opener and closer are the same character), and no
       grammar-aware or semantic disambiguation of which quote "really"
       opens or closes a quotation is attempted.
    3. A leftover, unpaired trailing ``"`` never raises and never produces a
       span - it is recorded as a diagnostic string, mirroring how every
       other unmatched delimiter in this module is handled.
    """
    diagnostics: List[str] = []
    spans: List[Span] = []

    candidate_positions = [
        i for i, ch in enumerate(text) if ch == '"' and not _is_inch_mark_quote(text, i)
    ]

    paired_count = len(candidate_positions) - (len(candidate_positions) % 2)
    for k in range(0, paired_count, 2):
        open_pos = candidate_positions[k]
        close_pos = candidate_positions[k + 1]
        spans.append(
            _make_span(
                text,
                open_pos,
                close_pos + 1,
                structural_type="paired_delimiter",
                subtype="quotation",
                source="ascii_double_quote_detector",
                attributes={"opening": '"', "closing": '"'},
            )
        )

    if len(candidate_positions) % 2 == 1:
        diagnostics.append(
            f"unmatched ASCII double quote at offset {candidate_positions[-1]}"
        )

    return spans, diagnostics


# ---------------------------------------------------------------------------
# Detector 2: punctuation_sequence
# ---------------------------------------------------------------------------
# Only the ellipsis/question/exclamation family - NOT comma/semicolon/colon,
# which are deliberately out of scope for this detector (they are ordinary,
# singular punctuation in this module's model, not "sequences").
_ELLIPSIS_CHARS = "…."  # … and ASCII "."
_QUESTION_CHARS = "?？"  # ? and ？
_EXCLAIM_CHARS = "!！"  # ! and ！
_SEQUENCE_CHARS = _ELLIPSIS_CHARS + _QUESTION_CHARS + _EXCLAIM_CHARS
_SEQUENCE_RUN_RE = re.compile(f"[{re.escape(_SEQUENCE_CHARS)}]+")


def _classify_punctuation_run(run: str) -> str:
    has_ellipsis = any(ch in _ELLIPSIS_CHARS for ch in run)
    has_question = any(ch in _QUESTION_CHARS for ch in run)
    has_exclaim = any(ch in _EXCLAIM_CHARS for ch in run)

    if has_ellipsis and has_question and has_exclaim:
        return "ellipsis_interrobang"
    if has_ellipsis and has_question:
        return "ellipsis_question"
    if has_ellipsis and has_exclaim:
        return "ellipsis_exclaim"
    if has_question and has_exclaim:
        return "interrobang"
    if has_ellipsis:
        return "ellipsis"
    if has_question:
        return "repeated_question"
    return "repeated_exclaim"


def _detect_punctuation_sequences(text: str) -> List[Span]:
    """Find every maximal run of consecutive ellipsis/question/exclamation
    characters and report it as a single ``punctuation_sequence`` span - a
    run like "……？" is one span, never two adjacent unrelated spans (see the
    module's design discussion for why this matters: reporting each
    character separately would misrepresent one visually/structurally
    connected mark as several independent ones).

    A run of length 1 does not qualify UNLESS it is the single Unicode
    ellipsis character "…" (U+2026) - that one character already visually
    represents multiple dots, so it is treated as a "sequence" on its own,
    unlike a single "." or a single "！"/"？", which are just ordinary
    punctuation and out of this detector's scope (see ``_ADJACENCY_PUNCTUATION_CHARS``
    and ``_compute_context_flags`` for how lone punctuation marks are still
    accounted for elsewhere, via ``punctuation_adjacency``, without needing
    a span of their own here).

    This function only identifies *what* a punctuation run is (its
    composition) - it never judges whether the run is a good or bad place
    to break subtitle text; that question belongs to a later phase.
    """
    spans: List[Span] = []
    for match in _SEQUENCE_RUN_RE.finditer(text):
        run = match.group(0)
        if len(run) < 2 and run != "…":
            continue
        subtype = _classify_punctuation_run(run)
        spans.append(
            _make_span(
                text,
                match.start(),
                match.end(),
                structural_type="punctuation_sequence",
                subtype=subtype,
                source="punctuation_sequence_detector",
                attributes={"chars": run},
            )
        )
    return spans


# ---------------------------------------------------------------------------
# Detector 3: atomic
# ---------------------------------------------------------------------------
# Format-only patterns, tried in priority order at every position (see
# ``_scan_with_priority_matchers`` below) so a longer/more specific format
# (e.g. "4K@60Hz" as one measurement) always wins over a shorter, more
# generic one (e.g. two separate numeric matches) it would otherwise
# fragment into - this is the "same structural type internal overlap ->
# minimal maximal-munch rule" approved for this Phase, deliberately scoped
# to *within* one detector family only (see module docstring).

_DATE_RE = re.compile(r"\d{4}[-/]\d{2}[-/]\d{2}")
_TIME_RE = re.compile(r"\d{1,2}:\d{2}(?::\d{2})?")

_MEASUREMENT_UNIT_RE = (
    r"(?:°C|°F|MHz|GHz|kHz|Hz|mm|cm|km|kg|ms|min|V|A|W|K|g|m|h|s)"
)
_MEASUREMENT_RE = re.compile(
    rf"\d+(?:\.\d+)?{_MEASUREMENT_UNIT_RE}(?:@\d+(?:\.\d+)?{_MEASUREMENT_UNIT_RE})?"
)

_ABBREVIATIONS: Tuple[str, ...] = ("e.g.", "i.e.", "etc.", "U.S.", "U.K.", "Dr.", "Mr.")
_ABBREVIATION_RE = re.compile(
    "|".join(re.escape(a) for a in sorted(_ABBREVIATIONS, key=len, reverse=True))
)

# Thousands-separated (1,000 / 1,000.25), plain decimal (3.14), or
# percentage (10%) - all reported under the single "numeric" subtype (see
# module docstring: Phase 1 keeps to the 7 approved atomic subtypes and does
# not invent a separate "percentage"/"decimal" subtype).
_NUMERIC_RE = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?%?|\d+(?:\.\d+)?%?")

# Emoji: a curated set of common single-codepoint Unicode emoji blocks, with
# an optional trailing Variation Selector-16 (U+FE0F, e.g. the "️" in
# "❤️"). See the module docstring's "Known limitations" for what
# this deliberately does not cover (multi-codepoint ZWJ sequences, skin
# tone modifiers rendered as part of one visual glyph, etc.).
_EMOJI_CHAR_CLASS = (
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F900-\U0001F9FF"
    "☀-⛿"
    "✀-➿"
)
_EMOJI_RE = re.compile(f"[{_EMOJI_CHAR_CLASS}]️?")

# Emoticon: a fixed, closed list (see module docstring - no attempt to
# generalize to arbitrary kaomoji). ``needs_word_boundary`` is True for the
# purely-alphabetic entries ("XD", "orz"), which would otherwise risk
# matching as a false positive inside an unrelated longer word (e.g. "XD"
# inside "SIXDIGIT"); the symbol-only entries don't need this since they
# already contain characters no ordinary word would.
_EMOTICON_DEFS: Tuple[Tuple[str, bool], ...] = (
    ("^_^", False),
    ("T_T", False),
    (">_<", False),
    ("XD", True),
    ("@@", False),
    ("orz", True),
)


def _build_emoticon_pattern() -> Pattern[str]:
    parts = []
    for literal, needs_boundary in sorted(_EMOTICON_DEFS, key=lambda d: -len(d[0])):
        escaped = re.escape(literal)
        parts.append(rf"\b{escaped}\b" if needs_boundary else escaped)
    return re.compile("|".join(parts))


_EMOTICON_RE = _build_emoticon_pattern()

_ATOMIC_PATTERNS: Tuple[Tuple[str, Pattern[str]], ...] = (
    ("date", _DATE_RE),
    ("time", _TIME_RE),
    ("measurement", _MEASUREMENT_RE),
    ("abbreviation", _ABBREVIATION_RE),
    ("emoji", _EMOJI_RE),
    ("emoticon", _EMOTICON_RE),
    ("numeric", _NUMERIC_RE),
)


def _scan_with_priority_matchers(
    text: str,
    matchers: Sequence[Tuple[str, "_Matcher"]],
    structural_type: str,
    source: str,
) -> List[Span]:
    """Shared left-to-right scanning strategy for both the atomic and
    technical detectors: at every position, try each ``(subtype, matcher)``
    pair in the given priority order and take the first one that matches
    starting exactly there; advance past the match and repeat. Positions
    that no matcher recognizes are simply skipped (they carry no
    structural span at all - most of any real text falls in this
    category).

    This constructs each detector's own output as an inherently
    non-overlapping sequence by never re-visiting an already-consumed
    position, which is what implements the "same structural type internal
    overlap -> minimal maximal-munch rule" without needing a separate
    post-hoc overlap-resolution pass within a single detector family.
    """
    spans: List[Span] = []
    i = 0
    n = len(text)
    while i < n:
        for subtype, matcher in matchers:
            end = matcher(text, i)
            if end is not None and end > i:
                spans.append(
                    _make_span(
                        text, i, end, structural_type=structural_type, subtype=subtype, source=source
                    )
                )
                i = end
                break
        else:
            i += 1
    return spans


def _regex_matcher(pattern: Pattern[str]):
    def matcher(text: str, pos: int) -> Optional[int]:
        m = pattern.match(text, pos)
        return m.end() if m else None

    return matcher


def _detect_atomic_spans(text: str) -> List[Span]:
    """Format-only detection of numeric/date/time/measurement/abbreviation/
    emoji/emoticon tokens. See the module docstring: this never claims a
    matched token is semantically meaningful, only that it has a
    recognizable structural shape.
    """
    matchers = [(subtype, _regex_matcher(pattern)) for subtype, pattern in _ATOMIC_PATTERNS]
    return _scan_with_priority_matchers(text, matchers, structural_type="atomic", source="atomic_detector")


# ---------------------------------------------------------------------------
# Detector 4: technical
# ---------------------------------------------------------------------------
_URL_RE = re.compile(r"https?://\S+")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")

_UNIX_PATH_RE_SRC = r"(?:[\w.-]+/)+[\w.-]+\.[A-Za-z0-9]+"
_WINDOWS_PATH_RE_SRC = r"[A-Za-z]:\\(?:[^\\\s]+\\)*[^\\\s]+"
_PATH_RE = re.compile(f"(?:{_WINDOWS_PATH_RE_SRC})|(?:{_UNIX_PATH_RE_SRC})")

_FUNCTION_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\(\)")
_COMMAND_RE = re.compile(r"(?:--[A-Za-z][\w-]*)|(?:\bpython -m [\w.]+)")

# "version" is deliberately restricted to the unambiguous "vX.Y[.Z]" prefix
# convention only (e.g. "v0.10.0") - see the module docstring's "Known
# limitations" for why "Python 3.13.2"/"USB 3.2"/"HDMI 2.1" land under
# ``identifier`` instead, not here.
_VERSION_RE = re.compile(r"\bv\d+(?:\.\d+){1,2}\b")

# "NamedToken X.Y[.Z]" shape - covers "Python 3.13.2", "USB 3.2", "HDMI 2.1"
# uniformly via *character shape* (capitalized word + a dotted version-like
# number) rather than a lookup of which specific names are "real" products
# or standards - see module docstring.
_NAMED_VERSION_PAIR_RE = re.compile(r"\b[A-Z][A-Za-z]*\s\d+(?:\.\d+)+\b")

# Bare single-token identifiers like "MT8395"/"S805X3-B"/"Cortex-A78":
# matched as a hyphen-tolerant token, then kept only if it contains at
# least one uppercase letter AND at least one digit - this is a *format*
# filter (not a dictionary lookup) that happens to also correctly exclude
# plain capitalized English words with no digit in them, e.g. "MediaTek"
# and "Genio" (see the module docstring's Case F discussion).
_IDENTIFIER_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9-]*")

# snake_case identifiers like "global_scale_correction"/"subtitle_text" -
# lowercase only for v1 (see module docstring's Known limitations for
# SCREAMING_SNAKE_CASE not being covered).
_VARIABLE_RE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")


def _match_identifier_token(text: str, pos: int) -> Optional[int]:
    m = _IDENTIFIER_TOKEN_RE.match(text, pos)
    if not m:
        return None
    token = m.group(0)
    if any(c.isupper() for c in token) and any(c.isdigit() for c in token):
        return m.end()
    return None


_TECHNICAL_MATCHERS_DEFS: Tuple[Tuple[str, Any], ...] = (
    ("email", _regex_matcher(_EMAIL_RE)),
    ("url", _regex_matcher(_URL_RE)),
    ("path", _regex_matcher(_PATH_RE)),
    ("function", _regex_matcher(_FUNCTION_RE)),
    ("command", _regex_matcher(_COMMAND_RE)),
    ("version", _regex_matcher(_VERSION_RE)),
    ("identifier", _regex_matcher(_NAMED_VERSION_PAIR_RE)),
    ("identifier", _match_identifier_token),
    ("variable", _regex_matcher(_VARIABLE_RE)),
)


def _detect_technical_spans(text: str) -> List[Span]:
    """Format-only detection of version/identifier/function/variable/command/
    path/url/email tokens. Deliberately does NOT attempt to recognize
    multi-word technical concepts that require brand/product knowledge -
    see the module docstring's Case F discussion and "Known limitations".
    """
    return _scan_with_priority_matchers(
        text, _TECHNICAL_MATCHERS_DEFS, structural_type="technical", source="technical_detector"
    )


# ---------------------------------------------------------------------------
# Overlap / nesting resolution (cross-detector)
# ---------------------------------------------------------------------------


def _is_strict_container(outer: Span, inner: Span) -> bool:
    return (
        outer.start <= inner.start
        and inner.end <= outer.end
        and (outer.start, outer.end) != (inner.start, inner.end)
    )


def _resolve_overlaps_and_nesting(candidates: List[Span]) -> Tuple[List[Span], List[str]]:
    """Merge the flat candidate spans produced by all four detectors into a
    tree (top-level spans + nested ``children``), following the approved
    Phase 1 overlap policy:

    - Exact overlap (two spans with identical ``[start, end)`` from
      different detectors): both are kept, as siblings, with no attempt to
      decide which one is "more important" - this is what lets a single
      region of text carry more than one independent structural
      observation at once. (Unchanged by the C-2 correction below.)
    - Partial overlap (neither contains the other, neither is identical,
      but their ranges intersect): both spans are kept, unresolved, exactly
      where their own containment relationships with *other* spans place
      them; a diagnostic string is recorded describing the overlap. No
      span is ever dropped because of a partial overlap, and no priority/
      score/winner is computed. (Unchanged by the C-2 correction below.)
    - Containment (one span's range fully contains another's, and they are
      not identical): see "structural nesting" below - containment alone
      no longer automatically produces a ``children`` relationship.

    STRUCTURAL NESTING (the C-2 correction)
    ----------------------------------------
    Containment is geometric; children is structural (see the module
    docstring). Only a span whose ``structural_type`` is in
    ``STRUCTURAL_CONTAINER_TYPES`` (today: ``paired_delimiter`` alone) may
    ever be the *outer* span of a ``children`` relationship. Concretely:

    1. For each candidate span, find its *innermost eligible* container -
       the narrowest span, among those with a structural-container type,
       that strictly contains it. A span with no such container (e.g. a
       bare "MT8395" with nothing enclosing it, or a "8395" whose only
       geometric container is a non-container ``technical`` span) has no
       candidate parent at all and is top-level.
    2. Multiple candidates can propose the *same* eligible container as
       their innermost one (e.g. both "MT8395" and "8395" inside
       "(MT8395)" - the atomic detector's "8395" and the technical
       detector's "MT8395" both geometrically sit inside the same
       parenthetical, and "technical" is not itself an eligible container,
       so both "look past" it to the same delimiter). Within that shared
       group, only a mutually non-overlapping subset becomes actual
       children: candidates are considered widest-first, and a candidate is
       accepted as a structural child only if it does not overlap any
       already-accepted sibling. A candidate that loses this contest (e.g.
       "8395", losing to the wider "MT8395") is not silently dropped and
       is not force-nested somewhere else - it becomes a genuine top-level
       span in its own right (see the module docstring for why a top-level
       span can therefore end up geometrically inside another top-level
       span's range). This greedy, width-based selection uses no score,
       weight, priority, or confidence value - only each candidate's own
       ``end - start``, exactly like the "maximal munch" rule already used
       within a single detector's own scan.
    3. This directly guarantees the children non-overlap invariant: the
       accepted set for any one container is, by construction, mutually
       non-overlapping.

    This function is intentionally the *only* place any nesting is
    resolved - individual detectors (``_detect_paired_delimiters`` in
    particular) deliberately return flat lists rather than pre-nesting
    same-family matches themselves, so that same-family and cross-family
    nesting are both handled by this one piece of logic instead of several
    separately-maintained ones.
    """
    diagnostics: List[str] = []
    n = len(candidates)

    for i in range(n):
        for j in range(i + 1, n):
            a, b = candidates[i], candidates[j]
            if (a.start, a.end) == (b.start, b.end):
                continue  # exact overlap: allowed to coexist, nothing to report
            if _is_strict_container(a, b) or _is_strict_container(b, a):
                continue  # containment: handled structurally below
            if max(a.start, b.start) < min(a.end, b.end):
                diagnostics.append(
                    f"partial overlap between {a.structural_type}/{a.subtype} "
                    f"[{a.start},{a.end}) and {b.structural_type}/{b.subtype} "
                    f"[{b.start},{b.end}); both spans are kept as-is, no resolution attempted"
                )

    # Step 1: for each span, find its innermost *eligible* (structural
    # container) geometric container, if any. Non-container spans (technical/
    # atomic/punctuation_sequence) are never considered as containers here,
    # regardless of what they themselves geometrically contain.
    eligible_container_indices = [
        j for j in range(n) if candidates[j].structural_type in STRUCTURAL_CONTAINER_TYPES
    ]
    proposed_parent: Dict[int, int] = {}
    for i in range(n):
        containers = [
            j
            for j in eligible_container_indices
            if j != i and _is_strict_container(candidates[j], candidates[i])
        ]
        if containers:
            proposed_parent[i] = min(
                containers, key=lambda j: candidates[j].end - candidates[j].start
            )

    # Step 2: group spans by their proposed parent, then keep only a
    # mutually non-overlapping subset per group (widest span wins; anything
    # it already covers does not also become a sibling child).
    groups: Dict[int, List[int]] = {}
    for i, parent_idx in proposed_parent.items():
        groups.setdefault(parent_idx, []).append(i)

    accepted_parent_of: Dict[int, int] = {}
    for parent_idx, member_indices in groups.items():
        ordered = sorted(
            member_indices,
            key=lambda idx: (-(candidates[idx].end - candidates[idx].start), candidates[idx].start),
        )
        accepted: List[int] = []
        for idx in ordered:
            cand = candidates[idx]
            overlaps_accepted = any(
                max(cand.start, candidates[a].start) < min(cand.end, candidates[a].end)
                for a in accepted
            )
            if not overlaps_accepted:
                accepted.append(idx)
                accepted_parent_of[idx] = parent_idx

    children_of: Dict[int, List[int]] = {i: [] for i in range(n)}
    top_level_indices: List[int] = []
    for i in range(n):
        if i in accepted_parent_of:
            children_of[accepted_parent_of[i]].append(i)
        else:
            top_level_indices.append(i)

    def _build(i: int) -> Span:
        nested = [_build(ci) for ci in sorted(children_of[i], key=lambda k: candidates[k].start)]
        all_children = tuple(sorted((*candidates[i].children, *nested), key=lambda s: s.start))
        return replace(candidates[i], children=all_children)

    top_level = [_build(i) for i in sorted(top_level_indices, key=lambda k: candidates[k].start)]
    return top_level, diagnostics


# ---------------------------------------------------------------------------
# Context annotation
# ---------------------------------------------------------------------------
# Deliberately independent from ``_ADJACENCY_PUNCTUATION_CHARS`` in
# src/subtitle_segmenter.py, even though the two sets overlap in spirit -
# this module must not import from subtitle_segmenter (see module
# docstring's architectural-independence requirement), so a small amount of
# duplication here is intentional, not an oversight.
_ADJACENCY_PUNCTUATION_CHARS = "。！？…，、；：.!?,;:"


def _paragraph_bounds(text: str, pos: int) -> Tuple[int, int]:
    """Return the ``(start, end)`` offsets of the "\\n"-delimited paragraph
    containing ``pos`` (end exclusive, never including the newline itself).
    """
    start = text.rfind("\n", 0, pos)
    start = 0 if start == -1 else start + 1
    end = text.find("\n", pos)
    end = len(text) if end == -1 else end
    return start, end


def _strip_trailing_punctuation_and_space(s: str) -> str:
    s = s.rstrip()
    while s and s[-1] in _ADJACENCY_PUNCTUATION_CHARS:
        s = s[:-1].rstrip()
    return s


def _strip_leading_punctuation_and_space(s: str) -> str:
    s = s.lstrip()
    while s and s[0] in _ADJACENCY_PUNCTUATION_CHARS:
        s = s[1:].lstrip()
    return s


def _compute_context_flags(span: Span, source_text: str) -> FrozenSet[str]:
    """Compute the geometric position facts for ``span`` within its own
    paragraph of ``source_text``. See module docstring's "Known
    limitations" for the precise (deliberately simple) rule:

    - Whether anything *meaningful* (non-whitespace, non-punctuation)
      follows the span in its paragraph is the primary factor: if
      something meaningful follows, the span is "internal" (there is more
      content coming after it), regardless of what precedes it.
    - Otherwise (nothing meaningful follows), the span is "sentence_final"
      if something meaningful precedes it, or "standalone" if it is the
      entire (non-whitespace, non-punctuation) content of its paragraph.
    - "punctuation_adjacency" is independent of the above and is set
      whenever the single nearest non-whitespace character immediately
      before or after the span (not skipping over punctuation, unlike the
      other three facts above) is itself a punctuation mark - so it can
      co-occur with any of "internal"/"sentence_final"/"standalone".

    Exactly one of {"internal", "sentence_final", "standalone"} is always
    present; this is a natural consequence of the if/elif/else below, not
    an externally-imposed priority ranking over otherwise-independent facts
    (there is no "which fact matters more" scoring here - the three
    conditions are mutually exclusive by their own definitions).
    """
    p_start, p_end = _paragraph_bounds(source_text, span.start)
    raw_before = source_text[p_start : span.start]
    raw_after = source_text[span.end : p_end] if span.end <= p_end else ""

    meaningful_before = _strip_trailing_punctuation_and_space(raw_before)
    meaningful_after = _strip_leading_punctuation_and_space(raw_after)

    flags = set()
    if meaningful_after:
        flags.add("internal")
    elif meaningful_before:
        flags.add("sentence_final")
    else:
        flags.add("standalone")

    before_ws_stripped = raw_before.rstrip()
    after_ws_stripped = raw_after.lstrip()
    before_char = before_ws_stripped[-1] if before_ws_stripped else ""
    after_char = after_ws_stripped[0] if after_ws_stripped else ""
    # NOTE: `before_char`/`after_char` are "" when there is no character at
    # all on that side (span sits at the very start/end of its paragraph).
    # `"" in _ADJACENCY_PUNCTUATION_CHARS` is `True` in Python (an empty
    # string is trivially a substring of everything), so each side is
    # guarded with an explicit truthiness check first - an absent character
    # is never treated as punctuation. (This was previously a confirmed bug:
    # see Phase 1 Behavioral Verification, Finding C-1.)
    if (before_char and before_char in _ADJACENCY_PUNCTUATION_CHARS) or (
        after_char and after_char in _ADJACENCY_PUNCTUATION_CHARS
    ):
        flags.add("punctuation_adjacency")

    return frozenset(flags)


def _annotate_context(spans: Sequence[Span], source_text: str) -> List[Span]:
    """Recursively attach ``context_flags`` to every span (top-level and
    nested), computed purely from each span's own absolute position in
    ``source_text`` - not from its parent, and not from any other span in
    the result (see ``_compute_context_flags``).
    """

    def _walk(span: Span) -> Span:
        flags = _compute_context_flags(span, source_text)
        new_children = tuple(_walk(child) for child in span.children)
        return replace(span, context_flags=flags, children=new_children)

    return [_walk(span) for span in spans]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_text_structure(text: str) -> TextAnalysisResult:
    """Analyze ``text`` and return every structural span found in it.

    This is the single public entry point of this module. It is a pure
    function: deterministic (the same ``text`` always yields an equal
    result), no I/O, no network, no randomness, no hidden global state, and
    no dependency on any other part of this project (see module docstring).

    Args:
        text: Arbitrary text to analyze - e.g. a slide's raw speaker notes.
            ``None`` and non-``str`` falsy values are treated as ``""``.

    Returns:
        A :class:`TextAnalysisResult` whose ``spans`` are top-level (with
        nested containment expressed via each span's own ``children``) and
        whose ``diagnostics`` records anything notable that isn't itself a
        span (unmatched delimiters, unresolved partial overlaps).

    This function does not decide where subtitle lines should break, does
    not produce boundaries of any kind, and is not called by any part of
    the existing subtitle generation pipeline - see module docstring.
    """
    source_text = str(text or "")

    paired_spans, paired_diagnostics = _detect_paired_delimiters(source_text)
    ascii_quote_spans, ascii_quote_diagnostics = _detect_ascii_double_quote_spans(source_text)
    punctuation_spans = _detect_punctuation_sequences(source_text)
    atomic_spans = _detect_atomic_spans(source_text)
    technical_spans = _detect_technical_spans(source_text)

    all_candidates: List[Span] = [
        *paired_spans,
        *ascii_quote_spans,
        *punctuation_spans,
        *atomic_spans,
        *technical_spans,
    ]

    top_level, overlap_diagnostics = _resolve_overlaps_and_nesting(all_candidates)
    annotated = _annotate_context(top_level, source_text)

    diagnostics = (
        tuple(paired_diagnostics) + tuple(ascii_quote_diagnostics) + tuple(overlap_diagnostics)
    )

    return TextAnalysisResult(
        source_text=source_text,
        spans=tuple(annotated),
        diagnostics=diagnostics,
    )
