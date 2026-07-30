"""Segment raw PowerPoint speaker notes into subtitle-ready lines.

This is Phase 2 of the SRT subtitle feature (see project discussion / phase
plan). It is a pure text-processing module - it does not call edge-tts and
knows nothing about audio timing. Given the *original* notes text for one
slide (the same text that gets sent to edge-tts, with paragraph structure
and punctuation intact - see Phase 1's rationale for sending the
unmodified original text to TTS first), it produces a list of subtitle
line candidates, each carrying:

- ``text``: the line as it should be displayed (unnecessary trailing
  punctuation stripped - see ``_strip_trailing_punctuation`` below).
- ``source_start_offset`` / ``source_end_offset``: the character offsets
  of this line within the *original, unmodified* input text (not the
  stripped display text). These are deliberately offsets into the exact
  string that will also be handed to edge-tts, so Phase 3 (alignment) can
  line these spans up against WordBoundary events without needing a
  second, separately-normalized copy of the text to reconcile against.

Design decisions (confirmed with the project owner before implementing):

1. Max line length is controlled by *display width*, not character count -
   a full-width character (most CJK characters and CJK punctuation) counts
   as 2, everything else (ASCII letters/digits/punctuation) counts as 1.
   Default is 32 (display width), matching the project owner's requested
   "16 個全形字" (16 full-width/CJK characters per line, revised down from
   an initial 20 after checking real Chinese-subtitle conventions - a
   single line of 20 full-width characters reads as too long) - each is
   worth 2 display width, so 16 characters is 32 width. Half-width text
   (ASCII) fits roughly twice as much per line under the same width
   budget, which is intentional (a line of 32 Latin characters and a line
   of 16 CJK characters read as roughly the same amount of content).
2. Trailing punctuation stripping only removes sentence/clause-final marks
   that are purely rhythmic (｡，、；：.,;: - the line break itself already
   conveys the pause). "？"/"！"/"?"/"!" are kept, because they carry
   meaning (a question or an exclamation) that would be lost if silently
   dropped - "去除不必要的句尾標點符號" ("strip *unnecessary* trailing
   punctuation") was read as excluding these.
3. Paragraph boundaries (single ``\\n`` between paragraphs, as produced by
   ``pptx_parser._get_notes_text``) are a hard boundary: a subtitle line
   never spans two paragraphs, even if both are short enough to fit
   together under the width limit. Paragraphs are the speaker's own
   intentional pacing structure; merging across them would erase that.
4. "Unnecessary" whitespace left over from typing/pasting notes into
   PowerPoint is cleaned up in the display text: a space with a CJK
   character on both sides (Chinese doesn't use spaces between words, so
   this is almost always paste/formatting noise) is removed entirely; a
   space anywhere else (between English words, or at a CJK/Latin
   boundary) is collapsed to a single space rather than removed, since it
   may be doing real work there. See ``_normalize_whitespace``.

Within those constraints, this module:

- Splits each paragraph into sentences at primary punctuation (。！？…
  and their ASCII equivalents .!?).
- Greedily merges consecutive short sentences (within the same paragraph)
  into one line as long as the combined display width still fits under
  the limit ("paragraph-aware merging" - short sentences like "好。" or
  "是的。" don't each need their own flashing-by-too-fast subtitle line).
- If a single sentence alone is already too wide, it's broken down further
  at secondary punctuation (，、；：,;:), and those pieces are packed the
  same greedy way. If even a single secondary-punctuation-delimited piece
  is still too wide (a long run of text with no punctuation at all - rare
  in practice for notes, but not impossible), it's force-cut at the width
  limit, preferring the last whitespace boundary within the limit so an
  English word isn't split in half.

Known limitation: trailing-punctuation stripping only looks at the literal
last character(s) of a line. A line ending in a closing quote/bracket
after a stripped mark, e.g. "...。」", won't have the "。" stripped, since
"」" isn't itself a strippable mark and the loop stops there. This is
narrow enough (and safe - it just leaves slightly more punctuation visible
than ideal) that it wasn't worth the added complexity for this phase.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_MAX_DISPLAY_WIDTH = 32  # 16 full-width (CJK) characters, per the project owner's "全形16個字"

# Sentence-ending punctuation: splitting here is the *primary* way this
# module breaks a paragraph into candidate subtitle lines.
_PRIMARY_BREAK_CHARS = "。！？….!?"

# Clause-level punctuation: only used to break a single sentence down
# further when it's already too wide on its own.
_SECONDARY_BREAK_CHARS = "，、；：,;:"

# Trailing marks considered "unnecessary" and stripped from the very end
# of a finished line - deliberately excludes ？！?!  (see module docstring
# point 2).
_STRIP_TRAILING_CHARS = "。，、；：.,;:"


def _char_width(ch: str) -> int:
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def _display_width(s: str) -> int:
    return sum(_char_width(ch) for ch in s)


def _strip_trailing_punctuation(s: str) -> str:
    s = s.strip()
    while s and s[-1] in _STRIP_TRAILING_CHARS:
        s = s[:-1].rstrip()
    return s


_WHITESPACE_RUN_RE = re.compile(r"\s+")


def _is_wide_char(ch: str) -> bool:
    return unicodedata.east_asian_width(ch) in ("W", "F")


def _normalize_whitespace(s: str) -> str:
    """Clean up "unnecessary" whitespace left over from how the notes were
    typed/pasted into PowerPoint (stray double spaces, full-width spaces
    U+3000, spaces sprinkled between individual characters), per the
    project owner's confirmed rule:

    - A run of whitespace with a wide (CJK/full-width) character on *both*
      sides is removed entirely - Chinese text doesn't use spaces between
      words, so a space in that position is almost always paste/formatting
      noise, not intentional content.
    - Any other run of whitespace (between two Latin-script words, or at a
      CJK/Latin boundary) is collapsed to a single ASCII space rather than
      removed - it's still doing a real job there (separating English
      words, or giving a CJK/Latin boundary some breathing room).

    Applied to the *display text* only (see ``_display_text_for_span``,
    the single place this is called from) - never to the raw span used
    for ``source_start_offset``/``source_end_offset``, so this has no
    effect on the character-offset alignment Phase 3 depends on.
    """

    def _replace(match: "re.Match[str]") -> str:
        start, end = match.start(), match.end()
        before = s[start - 1] if start > 0 else ""
        after = s[end] if end < len(s) else ""
        if before and after and _is_wide_char(before) and _is_wide_char(after):
            return ""
        return " "

    return _WHITESPACE_RUN_RE.sub(_replace, s)


def _display_text_for_span(text: str, start: int, end: int) -> str:
    return _normalize_whitespace(text[start:end]).strip()


def _fits(text: str, start: int, end: int, max_width: int) -> bool:
    candidate = _strip_trailing_punctuation(_display_text_for_span(text, start, end))
    return _display_width(candidate) <= max_width


def _split_paragraphs_with_offsets(text: str) -> List[Tuple[int, int]]:
    """Split ``text`` on "\\n" into (start, end) offset spans, one per
    non-blank paragraph. Blank paragraphs (consecutive newlines, or a
    paragraph that's pure whitespace - both of which
    ``pptx_parser._get_notes_text`` can legitimately produce for an
    intentional blank line in the speaker's notes) are skipped: they carry
    no text to build a subtitle line from, but they still count as
    separating whatever comes before and after them.
    """
    paragraphs = []
    start = 0
    for match in re.finditer(r"\n", text):
        end = match.start()
        if text[start:end].strip():
            paragraphs.append((start, end))
        start = match.end()
    if text[start:].strip():
        paragraphs.append((start, len(text)))
    return paragraphs


def _is_numeric_literal_punctuation(text: str, i: int) -> bool:
    """True if ``text[i]`` is "." or "," sitting between two digits, e.g.
    the "." in "3.3V" or the "," in "1,000" - a decimal point / thousands
    separator, not sentence/clause punctuation. Confirmed as a real bug on
    real speaker-notes content: "3.3V" was getting cut into "3" and "3V"
    because "." is otherwise a primary (sentence-ending) break character.
    Both "." and "," are guarded the same way even though only "." has
    been observed causing this in practice, since "," has the identical
    ambiguity (thousands separators) and no reason to treat it
    differently.
    """
    if text[i] not in ".,":
        return False
    return 0 < i < len(text) - 1 and text[i - 1].isdigit() and text[i + 1].isdigit()


def _split_at_chars(text: str, start: int, end: int, break_chars: str) -> List[Tuple[int, int]]:
    """Split ``text[start:end]`` into units, breaking right after each
    *run* of one or more consecutive characters from ``break_chars`` (the
    break characters themselves stay attached to the end of the unit they
    close, so ``text[unit_start:unit_end]`` still includes the
    punctuation - callers that want the punctuation-stripped display text
    apply ``_strip_trailing_punctuation`` separately). A "." or "," between
    two digits is never treated as a break point - see
    ``_is_numeric_literal_punctuation``.

    A whole run of break characters is consumed as a single break point,
    not one break point per character - otherwise a Chinese ellipsis
    ("……", conventionally written as two consecutive "…" characters, both
    of which are individually in ``_PRIMARY_BREAK_CHARS``) would produce
    an extra unit containing nothing but a lone trailing "…", stranding it
    on its own subtitle line with no other content. Confirmed as a real
    bug on real content. The same logic also protects a mixed run like
    "？！" from being split apart into two near-empty pieces.
    """
    units = []
    unit_start = start
    i = start
    while i < end:
        if text[i] in break_chars and not _is_numeric_literal_punctuation(text, i):
            j = i + 1
            while j < end and text[j] in break_chars and not _is_numeric_literal_punctuation(text, j):
                j += 1
            units.append((unit_start, j))
            unit_start = j
            i = j
        else:
            i += 1
    if unit_start < end:
        units.append((unit_start, end))
    return [(s, e) for s, e in units if text[s:e].strip()]


def _pack_greedy(units: List[Tuple[int, int]], text: str, max_width: int) -> List[Tuple[int, int]]:
    """Greedily merge adjacent units (assumed to already each individually
    fit under ``max_width`` on their own - callers are responsible for
    pre-splitting anything that doesn't) into as few lines as possible
    without exceeding ``max_width``. Maximizes each line before starting
    the next, so whatever's left over at the end can be much shorter than
    the lines before it - see ``_pack_units``, which fixes that.
    """
    lines: List[Tuple[int, int]] = []
    current_start = None
    current_end = None

    for u_start, u_end in units:
        if current_start is None:
            current_start, current_end = u_start, u_end
            continue
        if _fits(text, current_start, u_end, max_width):
            current_end = u_end
        else:
            lines.append((current_start, current_end))
            current_start, current_end = u_start, u_end

    if current_start is not None:
        lines.append((current_start, current_end))

    return lines


def _pack_units(units: List[Tuple[int, int]], text: str, max_width: int) -> List[Tuple[int, int]]:
    """Split ``units`` into however many lines they need, balancing the
    lines' widths as evenly as possible instead of greedily maximizing
    each one before moving to the next.

    Pure greedy packing (``_pack_greedy``) can leave an awkward, very
    short trailing line - e.g. on real content, "而是它扮演了整個
    Embedded System 的控制核心" packed greedily as "...的控制" / "核心",
    stranding "核心" ("core", the second half of the compound word
    "控制核心") alone on its own line. The fix (confirmed with the
    project owner): first find the minimum number of lines this content
    needs at all (via one greedy pass at ``max_width``), then redistribute
    across exactly that many lines so they come out close to equal width,
    rather than accepting whatever uneven split greedy happened to
    produce. This never uses more lines than plain greedy would, and
    every line still individually fits under ``max_width`` (often with
    some to spare - that's the trade-off for even distribution).

    Implemented as a dynamic program over exactly ``K`` contiguous groups
    (``K`` = the line count from one greedy pass, which is always the
    minimum possible - packing a fixed-order sequence as full as possible
    left-to-right is optimal for minimizing bin/line count). Among all
    ways to partition the units into exactly ``K`` groups where every
    group individually fits under ``max_width``, this picks the one
    minimizing the *sum of squared widths* - not simply the narrowest
    worst-case line. Minimizing only the worst line (an earlier version
    of this function did exactly that, via binary search) is a weaker
    objective: on real content it once chose a 24/8/26-width three-line
    split over an available 14/18/26 one, because 26 (the earlier split's
    worst line) is smaller than 28 - both, in fact, share the same
    largest final width, but minimizing only the max was blind to the
    stranded 8-width line as long as the max didn't get worse. Squared
    widths penalize any single line being far from the group's average,
    which is what "balanced" actually means here.

    ``_fits``/actual materialized substrings (not a simple sum of unit
    widths) are used throughout for width checks, since a line's real
    display width depends on context - trailing-punctuation stripping and
    whitespace normalization both only apply to whatever ends up as a
    line's actual trailing edge, not to each unit in isolation.
    """
    if not units:
        return []

    greedy_lines = _pack_greedy(units, text, max_width)
    target_line_count = len(greedy_lines)
    if target_line_count <= 1:
        return greedy_lines

    n = len(units)
    # group_width[i][j] = display width of units[i:j] merged into one line
    # (i, j are unit indices, j exclusive), or None if that merged span
    # doesn't fit under max_width at all.
    group_width: List[List[Optional[int]]] = [[None] * (n + 1) for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n + 1):
            width = _display_width(
                _strip_trailing_punctuation(_display_text_for_span(text, units[i][0], units[j - 1][1]))
            )
            group_width[i][j] = width if width <= max_width else None

    UNREACHABLE = float("inf")
    # dp[i][k] = lowest achievable sum of squared line-widths when
    # partitioning units[0:i] into exactly k lines.
    dp = [[UNREACHABLE] * (target_line_count + 1) for _ in range(n + 1)]
    choice: List[List[Optional[int]]] = [[None] * (target_line_count + 1) for _ in range(n + 1)]
    dp[0][0] = 0

    for i in range(1, n + 1):
        for k in range(1, target_line_count + 1):
            for j in range(k - 1, i):
                if dp[j][k - 1] == UNREACHABLE:
                    continue
                width = group_width[j][i]
                if width is None:
                    continue
                cost = dp[j][k - 1] + width * width
                if cost < dp[i][k]:
                    dp[i][k] = cost
                    choice[i][k] = j

    if dp[n][target_line_count] == UNREACHABLE:
        # Should be unreachable in practice (greedy_lines is always a
        # valid K-line partition), but fall back to it defensively rather
        # than raising if some edge case slips through.
        return greedy_lines

    boundaries = []
    i, k = n, target_line_count
    while k > 0:
        j = choice[i][k]
        boundaries.append((j, i))
        i, k = j, k - 1
    boundaries.reverse()

    return [(units[j][0], units[i - 1][1]) for j, i in boundaries]


def _hard_split_by_characters(text: str, start: int, end: int, max_width: int) -> List[Tuple[int, int]]:
    """Force-cut ``text[start:end]`` into chunks of at most ``max_width``
    display width by walking character-by-character. This is the fallback
    of last resort - it has no notion of "word" at all, so on CJK text
    (which has no whitespace between words) it can and will cut a real
    word in half. ``_hard_split`` (below) avoids that for CJK by cutting
    at jieba token boundaries instead; this function only gets used for
    whatever, if anything, is still too wide after that - e.g. a single
    jieba token that's on its own already wider than the limit (a long
    URL, a long English word with no spaces to break at).

    Prefers cutting at the last whitespace seen within the current chunk,
    if there is one, so an English word isn't split mid-word; otherwise
    cuts exactly at the width limit.
    """
    result = []
    seg_start = start
    width = 0
    last_space = None
    i = start

    while i < end:
        ch = text[i]
        ch_width = _char_width(ch)
        if width + ch_width > max_width:
            cut = last_space if last_space is not None and last_space > seg_start else i
            result.append((seg_start, cut))
            seg_start = cut
            while seg_start < end and text[seg_start].isspace():
                seg_start += 1
            width = 0
            last_space = None
            i = seg_start
            continue
        if ch.isspace():
            last_space = i
        width += ch_width
        i += 1

    if seg_start < end:
        result.append((seg_start, end))

    return [(s, e) for s, e in result if text[s:e].strip()]


def _jieba_tokenize(s: str) -> List[str]:
    # Imported lazily (rather than at module load time) purely so that
    # importing src.subtitle_segmenter doesn't pay jieba's dictionary
    # setup cost - which only actually happens on the *first* jieba.cut()
    # call, not on import - for code paths that never hit this function
    # (most notes have enough punctuation that _hard_split is never
    # reached at all; see its docstring for why this exists).
    import logging

    import jieba

    # jieba logs "Building prefix dict...", "Loading model cost ...", etc.
    # at INFO level on first use, straight to stderr via the root logging
    # config - that's noise the rest of this project's console output
    # deliberately avoids (see logging_config.py's console-formatting
    # rationale). Only silence jieba's own logger, not the project's.
    jieba.setLogLevel(logging.WARNING)

    return list(jieba.cut(s))


def _merge_numeric_literal_tokens(tokens: List[str]) -> List[str]:
    """Re-merge jieba tokens that split a single number apart at its
    decimal point / thousands separators, e.g. jieba tokenizes "1,000,000"
    as ``['1', ',', '000', ',', '000']`` (confirmed by direct
    inspection - jieba has no special handling for grouped digits). Left
    alone, ``_pack_units`` can end up closing a line exactly on one of
    those lone "," tokens, and the trailing-punctuation-stripping step
    then silently deletes it, corrupting the number (observed turning
    "1,000,000" into "1000,000" on real content - a worse bug than an
    awkward line break, since it changes the actual number). Merging
    these back into one atomic token before packing means the whole
    number is always kept together on one line, or moves as a whole unit
    to the next one.
    """
    merged: List[str] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.isdigit():
            combined = token
            j = i + 1
            while j + 1 < len(tokens) and tokens[j] in (".", ",") and tokens[j + 1].isdigit():
                combined += tokens[j] + tokens[j + 1]
                j += 2
            merged.append(combined)
            i = j
        else:
            merged.append(token)
            i += 1
    return merged


def _hard_split(text: str, start: int, end: int, max_width: int) -> List[Tuple[int, int]]:
    """Force-split ``text[start:end]`` for the rare case where a single
    punctuation-delimited piece has no punctuation at all to break at
    (e.g. a long run-on clause).

    Chinese has no whitespace between words, so a naive character-count
    cut (see ``_hard_split_by_characters``) can and does land in the
    middle of a real word - confirmed on real speaker-notes text, where
    it split common words like "我們" and "案件" apart. This instead
    tokenizes the span with jieba (a statistical/dictionary Chinese word
    segmenter) and only ever cuts between tokens, never inside one -
    verified against the same real text: 5 of 15 character-level cuts
    landed mid-word, versus 0 of 16 with token-based cuts.

    jieba's own segmentation isn't perfect (a domain-specific term not in
    its dictionary might get split more finely than ideal - use
    ``jieba.load_userdict()``/``jieba.add_word()`` before calling this if
    that matters for a given deck), but it is never *wrong* the way a
    blind character cut can be - splitting between two of its tokens is,
    at worst, a slightly more conservative break than a human would
    choose, not a broken word.

    Falls back to ``_hard_split_by_characters`` only for the rare token
    that is, by itself, still wider than ``max_width`` (e.g. a long URL)
    - jieba can't offer a better cut point for that case since there's no
    internal boundary to use.

    jieba's tokens are also re-merged where they split a single number
    apart (see ``_merge_numeric_literal_tokens``) - otherwise a number
    like "1,000,000" could get corrupted rather than just awkwardly
    broken (also confirmed on real content).
    """
    tokens = _merge_numeric_literal_tokens(_jieba_tokenize(text[start:end]))

    token_units = []
    cursor = start
    for token in tokens:
        token_units.append((cursor, cursor + len(token)))
        cursor += len(token)

    expanded: List[Tuple[int, int]] = []
    for s, e in token_units:
        if text[s:e].strip() == "":
            continue
        if _fits(text, s, e, max_width):
            expanded.append((s, e))
        else:
            expanded.extend(_hard_split_by_characters(text, s, e, max_width))

    return _pack_units(expanded, text, max_width)


def _force_split_sentence(text: str, start: int, end: int, max_width: int) -> List[Tuple[int, int]]:
    """Break down a single sentence that's already too wide on its own,
    first trying secondary (clause-level) punctuation, then falling back
    to a hard character-level cut for any piece that's still too wide,
    then re-packing everything greedily (a sentence broken into several
    short clauses should still end up merged back into as few lines as
    the width limit allows, not one line per clause).
    """
    sub_units = _split_at_chars(text, start, end, _SECONDARY_BREAK_CHARS)
    if not sub_units:
        sub_units = [(start, end)]

    expanded: List[Tuple[int, int]] = []
    for s, e in sub_units:
        if _fits(text, s, e, max_width):
            expanded.append((s, e))
        else:
            expanded.extend(_hard_split(text, s, e, max_width))

    return _pack_units(expanded, text, max_width)


def _segment_paragraph(text: str, p_start: int, p_end: int, max_width: int) -> List[Tuple[int, int]]:
    sentence_units = _split_at_chars(text, p_start, p_end, _PRIMARY_BREAK_CHARS)
    if not sentence_units:
        sentence_units = [(p_start, p_end)]

    lines: List[Tuple[int, int]] = []
    buffer: List[Tuple[int, int]] = []

    def flush_buffer():
        if buffer:
            lines.extend(_pack_units(buffer, text, max_width))
            buffer.clear()

    for u_start, u_end in sentence_units:
        if _fits(text, u_start, u_end, max_width):
            buffer.append((u_start, u_end))
        else:
            # A too-wide sentence breaks the run of mergeable short
            # sentences - it's handled (and possibly split into several
            # lines) on its own, not blended with neighbors.
            flush_buffer()
            lines.extend(_force_split_sentence(text, u_start, u_end, max_width))

    flush_buffer()
    return lines


def segment_notes_for_subtitles(
    text: str,
    max_display_width: int = DEFAULT_MAX_DISPLAY_WIDTH,
) -> List[Dict[str, Any]]:
    """Segment one slide's raw notes text into subtitle line candidates.

    Args:
        text: The original notes text, exactly as extracted by
            ``pptx_parser._get_notes_text`` (paragraphs joined by "\\n",
            punctuation intact) - i.e. the same string Phase 1 sends to
            edge-tts, unmodified. Passing an already-cleaned/re-punctuated
            version would make the returned offsets meaningless for
            Phase 3's alignment purposes.
        max_display_width: Maximum display width per line (full-width
            chars count as 2, everything else as 1).

    Returns:
        A list of ``{"text": str, "source_start_offset": int,
        "source_end_offset": int}`` dicts, in reading order.
        ``source_start_offset``/``source_end_offset`` index into the
        *original* ``text`` argument (Python string indexing, end
        exclusive) and span the line's full content including whatever
        punctuation was originally there - ``text`` is the display
        version with unnecessary trailing punctuation stripped (see
        module docstring). Empty/whitespace-only input returns ``[]``.
    """
    text = str(text or "")
    segments = []

    for p_start, p_end in _split_paragraphs_with_offsets(text):
        for start, end in _segment_paragraph(text, p_start, p_end, max_display_width):
            display_text = _strip_trailing_punctuation(_display_text_for_span(text, start, end))
            if not display_text:
                continue
            segments.append({
                "text": display_text,
                "source_start_offset": start,
                "source_end_offset": end,
            })

    return segments
