"""Align Phase 2 subtitle-line candidates against Phase 1's edge-tts
per-word timing data, and format the result as SRT text.

This is Phase 3 of the SRT subtitle feature (see project discussion / phase
plan). It is a pure data-transformation module - no file I/O, no decisions
about where output goes on disk or how it wires into the CLI/manifest (that
is Phase 4's job). Given:

- ``text``: the *original* notes text for one slide (the same string
  ``segment_notes_for_subtitles`` was given, and the same string
  ``synthesize_with_word_boundaries``/``_stream_edge_tts_audio_with_word_boundaries``
  sent to edge-tts) - unmodified, so all three modules agree on what
  character offset N means.
- ``segments``: Phase 2's output (``segment_notes_for_subtitles(text)``) -
  a list of ``{"text", "source_start_offset", "source_end_offset"}`` dicts.
- ``word_boundaries``: Phase 1's output
  (``synthesize_with_word_boundaries(text, ...)``) - a list of
  ``{"text", "offset_seconds", "duration_seconds"}`` dicts, one per
  ``WordBoundary`` event edge-tts emitted, in text order.

...this produces a list of ``{"text", "start_seconds", "end_seconds",
"source_start_offset", "source_end_offset"}`` dicts, one per Phase 2
segment, ready to hand to ``format_srt``.

The central problem this module solves: edge-tts's ``WordBoundary`` events
carry *audio* timing (``offset``/``duration``) and the literal text of
whatever it decided to voice as one "word", but - confirmed by reading
edge-tts's own source (``Communicate.__parse_metadata`` in
``communicate.py``, which builds each event as
``{"type", "offset", "duration", "text"}``) - they carry no character
offset into the original input text at all. So the two building blocks
(Phase 2's offset-based segments, Phase 1's offset-less timing events)
can't be joined directly; this module reconstructs the missing offsets by
walking a cursor through ``text`` in the same order edge-tts emitted the
events (edge-tts does not reorder text), matching each boundary event's
``text`` against the next occurrence at or after the cursor.

Design decisions (confirmed with the project owner before implementing):

1. Matching strategy is lenient and best-effort, not strict. edge-tts may
   skip emitting boundary events for characters it doesn't voice
   (whitespace, some punctuation), so an exact substring search from the
   cursor is tried first; if that fails, a case-insensitive/whitespace-
   normalized search is tried as a fallback. If a boundary event still
   can't be located, it is skipped (not matched to any offset) rather than
   raising - one stray unmatched event should not blow up alignment for an
   entire slide. Every skip is recorded in the returned ``warnings`` list
   (plain strings) so callers can surface them (e.g. via the project's
   logger in Phase 4) without this module taking a dependency on
   ``logging_config``.
2. A segment's end time extends forward to just before the next segment's
   start time (minus ``trailing_gap_seconds``, default 0.15s), rather than
   cutting off tight at the last matched word's audio end. This covers the
   natural pause between sentences so the subtitle doesn't disappear then
   reappear during a brief silence - standard practice in subtitle timing.
   The very last segment (no following segment to extend toward) keeps its
   raw last-word end time, since there's no information here about how
   much silence follows it. If the raw gap between a segment's last word
   and the next segment's first word is already smaller than
   ``trailing_gap_seconds`` (or negative/overlapping), the raw end time is
   kept as-is rather than shrinking it or producing an inverted interval.
3. Scope: this module produces timing data and SRT-formatted text only. It
   does not decide *where* an SRT file is written, whether one is produced
   per slide or for the whole deck, or how any of this wires into
   ``main.py``/``manifest.json`` - all Phase 4 concerns.

Known limitation: if a Phase 2 segment has no matched ``WordBoundary``
events overlapping its offset range at all (e.g. every event in that span
failed to match), its timing is interpolated from whatever surrounding
information is available (the previous segment's computed end time, and
the next successfully-matched boundary event after it) rather than left
undefined - see ``_interpolate_missing_segment``. This keeps the pipeline
from breaking on one bad segment, but an interpolated segment's timing is
a guess, not a measurement; it is called out in ``warnings`` so it can be
reviewed. This has not yet been exercised against real edge-tts output
(the sandbox this was written in cannot reach edge-tts's servers - see
``scripts/smoke_test_alignment.py`` for the real-network verification
tool), so this fallback path may need adjustment once real mismatches are
observed, the same way Phase 2's edge cases were found and fixed against
real content.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

DEFAULT_TRAILING_GAP_SECONDS = 0.15

# How far past the cursor to look, on the first (exact) match attempt,
# before falling back to an unbounded search. edge-tts emits boundary
# events in text order with only small gaps between them (skipped
# whitespace/punctuation), so a match should normally be found within a
# few dozen characters of the cursor; this window just keeps the common
# case fast without ruling out a legitimate faraway match if the first,
# bounded attempt fails (see ``_find_boundary_span``).
_MATCH_SEARCH_WINDOW = 200


# How many of the immediately-following WordBoundary events' texts to use
# for disambiguating which occurrence of a *repeated* boundary_text is the
# right one (see _pick_best_candidate). Found necessary by a real case: a
# slide whose notes said "...第三。SRAM 斷電後資料立即消失。Flash 則可以永
# 久保存。第四。SRAM 的讀寫速度非常快。Flash 的讀取速度雖然也很快..." - edge-tts
# silently dropped everything from "SRAM 斷電後" through "...非常快。" (a real
# content-loss bug, the same failure mode find_suspected_dropped_narration
# exists to catch - see that function's docstring), so the *actual* audio
# jumped straight from "第三" to the *second* "Flash 的讀取速度...". But
# because "Flash" (and shortly after, "的") also occur earlier in the
# skipped text, picking the first occurrence at-or-after the cursor (the
# old, unconditional behavior) locked onto the *first* "Flash" - the one
# inside the dropped span - instead of the one that was actually spoken.
# That misattribution didn't just get one word wrong: every event after it
# inherited a wrong cursor position, fragmenting what should have been one
# large, obviously-anomalous gap into several small ones, each too small on
# its own to look suspicious. 3 is enough to disambiguate that real case
# (the very next event, "的", was itself ambiguous - "Flash" appears twice
# nearby and each is followed by "的" - but the event after that, "讀取" vs.
# "讀寫", was not) while staying cheap - most boundary_text values are not
# ambiguous at all (see _find_boundary_span), so this only adds work in the
# rare case there's more than one candidate to choose between.
_DISAMBIGUATION_LOOKAHEAD = 3


def _find_all_occurrences(text: str, cursor: int, window_end: int, boundary_text: str) -> List[int]:
    """All non-overlapping start indices of ``boundary_text`` in
    ``text[cursor:window_end]`` (searched with respect to the full string's
    offsets, not the slice's). Empty if none.
    """
    occurrences: List[int] = []
    search_from = cursor
    while True:
        idx = text.find(boundary_text, search_from, window_end)
        if idx == -1:
            break
        occurrences.append(idx)
        search_from = idx + 1  # allow overlapping matches, e.g. boundary_text "aa" in "aaa"
    return occurrences


# When two (or more) candidates' downstream continuations are within this
# many characters of each other, treat their continuation quality as
# "roughly tied" and let proximity to the cursor break the tie instead
# (see _pick_best_candidate). Sized to comfortably cover the kind of
# single-character punctuation noise that a genuine nearby match can
# accumulate (e.g. "：\n" vs "，" before the next word, or a 1-2 character
# reshuffle), while staying well below the length of any real dropped
# clause - the shortest confirmed real drop seen so far skipped well over
# ten characters of source text, let alone the ~20-30 seen in the cases
# that motivated this module. There's no exact value derived from first
# principles here; this just needs to sit clearly between "a couple of
# characters of punctuation" and "a real skipped sentence fragment".
_CONTINUATION_TIE_THRESHOLD = 10


def _pick_best_candidate(
    text: str,
    cursor: int,
    candidates: List[int],
    match_len: int,
    upcoming_texts: Sequence[str],
) -> int:
    """When ``boundary_text`` occurs more than once shortly after the
    cursor, pick the occurrence that lets the *next few* WordBoundary
    events also be found close by, instead of always the earliest one (see
    ``_DISAMBIGUATION_LOOKAHEAD``'s docstring for the real case this fixes).

    For each candidate, a "continuation cost" is computed: greedily locate
    ``upcoming_texts`` one after another starting right after that
    candidate, summing how many characters were skipped to find each one
    (unbounded - a legitimate continuation can be arbitrarily far if
    nothing closer fits). The candidate whose continuation reads most
    fluently (lowest cost) is preferred - this is what correctly resolves
    the original real case this feature exists for: a slide whose notes
    said "...第三。SRAM 斷電後資料立即消失。Flash 則可以永久保存。第四。
    SRAM 的讀寫速度非常快。Flash 的讀取速度雖然也很快..." where edge-tts
    silently dropped everything from "SRAM 斷電後" through "...非常快。",
    so the actual audio jumped straight from "第三" to the *second*
    "Flash"; picking the first "Flash" (inside the dropped span) would
    have looked fine locally but fails badly a few words later, while the
    second "Flash" reads perfectly - a large, unambiguous continuation-cost
    gap.

    Continuation cost alone isn't always enough, though: when *both*
    "Flash" and its dropped-span twin are close together in a genuinely
    ambiguous way, or when the source text itself contains two
    near-duplicate phrases (e.g. a slide whose notes said "...分成四個階
    段：Input，也就是輸入。" summarizing, then "...第一個階段，Input，也
    就是輸入。" introducing detail moments later), the continuation costs
    of the two candidates can come out only a character or two apart - one
    fewer skipped character of punctuation before the next word is not
    meaningful evidence, and picking the farther candidate on that basis
    alone jumps the cursor forward and silently discards everything in
    between as if it had been matched (confirmed for real: it did exactly
    this, cascading into a flood of "Could not locate" warnings for
    everything downstream). So candidates are compared lexicographically:
    continuation cost is the primary key, but any candidates whose cost is
    within ``_CONTINUATION_TIE_THRESHOLD`` of the best are treated as tied,
    and among those the one nearest the cursor wins. This resolves both
    real cases correctly - the ~2-character continuation-cost gaps in the
    duplicate-phrase cases fall within the tie threshold (so proximity
    decides, correctly picking the near candidate), while the "Flash" case's
    continuation-cost gap (tens of characters, the length of the dropped
    span) does not (so continuation quality decides, correctly picking the
    far candidate).

    A candidate for which some upcoming text can't be found at all
    afterward is not competitive - only considered if no candidate manages
    to place all of them (falls back to the first candidate then,
    preserving the old behavior rather than guessing).
    """
    scored: List[Tuple[int, int, int]] = []  # (continuation_cost, distance, index)

    for index, candidate in enumerate(candidates):
        pos = candidate + match_len
        continuation_cost = 0
        placed_all = True
        for upcoming in upcoming_texts:
            idx = text.find(upcoming, pos)
            if idx == -1:
                placed_all = False
                break
            continuation_cost += idx - pos
            pos = idx + len(upcoming)

        if not placed_all:
            continue
        scored.append((continuation_cost, candidate - cursor, index))

    if not scored:
        return candidates[0]

    best_cost = min(cost for cost, _distance, _index in scored)
    tied = [entry for entry in scored if entry[0] <= best_cost + _CONTINUATION_TIE_THRESHOLD]
    _cost, _distance, best_index = min(tied, key=lambda entry: entry[1])
    return candidates[best_index]


def _find_boundary_span(
    text: str, cursor: int, boundary_text: str, upcoming_texts: Sequence[str] = ()
) -> Optional[Tuple[int, int]]:
    """Find where ``boundary_text`` (one WordBoundary event's ``text``)
    next occurs in ``text`` at or after ``cursor``.

    Tries, in order:
    1. Exact substring search within a bounded lookahead window
       (``_MATCH_SEARCH_WINDOW``) - the fast, expected-common-case path.
       If more than one occurrence exists in that window, ``upcoming_texts``
       (the next few WordBoundary events' texts, if given) are used to
       disambiguate which one is actually right - see
       ``_pick_best_candidate``. With zero or one occurrence, or no
       ``upcoming_texts`` to disambiguate with, the first (only) one is
       used, same as before this disambiguation existed.
    2. Exact substring search with no bound - a legitimate match that's
       simply farther from the cursor than expected (e.g. several
       consecutive unmatched events before it).
    3. Case-insensitive search within the bounded window - covers the
       (unconfirmed, defensive) possibility of edge-tts normalizing case
       for some voices/locales.

    Returns ``(start, end)`` (end exclusive, ``end - start ==
    len(boundary_text)``) or ``None`` if nothing was found.
    """
    if not boundary_text:
        return None

    window_end = min(len(text), cursor + _MATCH_SEARCH_WINDOW)

    candidates = _find_all_occurrences(text, cursor, window_end, boundary_text)
    if candidates:
        if len(candidates) == 1 or not upcoming_texts:
            start = candidates[0]
        else:
            start = _pick_best_candidate(text, cursor, candidates, len(boundary_text), upcoming_texts)
        return start, start + len(boundary_text)

    idx = text.find(boundary_text, cursor)
    if idx != -1:
        return idx, idx + len(boundary_text)

    lowered_window = text[cursor:window_end].lower()
    idx = lowered_window.find(boundary_text.lower())
    if idx != -1:
        start = cursor + idx
        return start, start + len(boundary_text)

    return None


def _match_word_boundaries(
    text: str, word_boundaries: Sequence[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Walk ``word_boundaries`` in order, locating each event's matching
    span in ``text`` and attaching ``source_start_offset``/
    ``source_end_offset`` to it. Events that can't be located are dropped
    (not included in the returned list) with a note added to ``warnings``.
    """
    matched: List[Dict[str, Any]] = []
    warnings: List[str] = []
    cursor = 0

    # Precompute the non-empty texts once, in order, so each event can look
    # ahead at the next few upcoming ones for disambiguation (see
    # _DISAMBIGUATION_LOOKAHEAD) without re-filtering word_boundaries on
    # every iteration.
    non_empty_texts = [str(wb.get("text", "")) for wb in word_boundaries if str(wb.get("text", "")).strip()]

    lookahead_index = 0
    for wb in word_boundaries:
        raw_text = str(wb.get("text", ""))
        if not raw_text.strip():
            continue

        upcoming_texts = non_empty_texts[lookahead_index + 1 : lookahead_index + 1 + _DISAMBIGUATION_LOOKAHEAD]
        lookahead_index += 1

        span = _find_boundary_span(text, cursor, raw_text, upcoming_texts)
        if span is None:
            warnings.append(
                f"Could not locate WordBoundary text {raw_text!r} in the "
                f"source text at or after position {cursor}; it was "
                "skipped for alignment purposes."
            )
            continue

        start, end = span
        matched.append({
            "source_start_offset": start,
            "source_end_offset": end,
            "offset_seconds": wb["offset_seconds"],
            "duration_seconds": wb["duration_seconds"],
        })
        cursor = end

    return matched, warnings


def _interpolate_missing_segment(
    segment: Dict[str, Any],
    aligned_so_far: List[Dict[str, Any]],
    matched: List[Dict[str, Any]],
) -> Tuple[float, float]:
    """Best-effort timing guess for a segment with no matched WordBoundary
    events at all inside its offset range (see module docstring's "Known
    limitation").

    Start time: the previous already-aligned segment's end time, or 0.0 if
    this is the first segment.
    End time: the offset of the next matched WordBoundary event that
    starts at or after this segment's end offset (i.e. the first bit of
    speech known to come after this segment), or the same as the guessed
    start time if there is none (nothing after it to anchor to either).
    """
    start_seconds = aligned_so_far[-1]["end_seconds"] if aligned_so_far else 0.0

    seg_end_off = segment["source_end_offset"]
    next_matched = next(
        (m for m in matched if m["source_start_offset"] >= seg_end_off), None
    )
    end_seconds = next_matched["offset_seconds"] if next_matched is not None else start_seconds

    if end_seconds < start_seconds:
        end_seconds = start_seconds

    return start_seconds, end_seconds


def align_segments_with_word_boundaries(
    text: str,
    segments: Sequence[Dict[str, Any]],
    word_boundaries: Sequence[Dict[str, Any]],
    trailing_gap_seconds: float = DEFAULT_TRAILING_GAP_SECONDS,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Compute a start/end time (in seconds) for each Phase 2 segment,
    using Phase 1's WordBoundary timing data.

    Args:
        text: The original notes text - the same string both
            ``segment_notes_for_subtitles`` and
            ``synthesize_with_word_boundaries`` were called with.
        segments: ``segment_notes_for_subtitles(text)``'s return value.
        word_boundaries: ``synthesize_with_word_boundaries(text, ...)``'s
            return value.
        trailing_gap_seconds: How much of a buffer to leave before the
            next segment's start time when extending a segment's end time
            forward (see module docstring, decision 2). Must be >= 0.

    Returns:
        A tuple ``(aligned_segments, warnings)``:

        - ``aligned_segments``: one ``{"text", "start_seconds",
          "end_seconds", "source_start_offset", "source_end_offset"}``
          dict per input segment, in the same order, ready for
          ``format_srt``.
        - ``warnings``: plain-string notes about anything that didn't
          match cleanly (an unmatched WordBoundary event, or a segment
          whose timing had to be interpolated). Empty when everything
          matched cleanly. Callers decide what to do with these (print,
          log, ignore) - this module has no logging dependency of its
          own.
    """
    if trailing_gap_seconds < 0:
        raise ValueError(f"trailing_gap_seconds must be >= 0, got {trailing_gap_seconds!r}")

    matched, warnings = _match_word_boundaries(text, word_boundaries)

    aligned: List[Dict[str, Any]] = []
    for index, segment in enumerate(segments):
        seg_start_off = segment["source_start_offset"]
        seg_end_off = segment["source_end_offset"]

        overlapping = [
            m for m in matched
            if m["source_start_offset"] < seg_end_off and m["source_end_offset"] > seg_start_off
        ]

        if overlapping:
            start_seconds = min(m["offset_seconds"] for m in overlapping)
            end_seconds = max(m["offset_seconds"] + m["duration_seconds"] for m in overlapping)
        else:
            start_seconds, end_seconds = _interpolate_missing_segment(segment, aligned, matched)
            warnings.append(
                f"No WordBoundary events matched segment {index} "
                f"({segment['text']!r}); its timing was interpolated "
                "rather than measured."
            )

        aligned.append({
            "text": segment["text"],
            "start_seconds": start_seconds,
            "end_seconds": end_seconds,
            "source_start_offset": seg_start_off,
            "source_end_offset": seg_end_off,
        })

    for index in range(len(aligned) - 1):
        next_start = aligned[index + 1]["start_seconds"]
        extended_end = next_start - trailing_gap_seconds
        if extended_end > aligned[index]["end_seconds"]:
            aligned[index]["end_seconds"] = extended_end

    return aligned, warnings


# Defaults for find_suspected_dropped_narration() - see its docstring for
# how these were chosen (against the real slide_009 case that motivated
# this function).
DEFAULT_MIN_SUSPECTED_DROP_CHARS = 15
DEFAULT_SUSPECTED_DROP_PACE_RATIO = 0.3


def find_suspected_dropped_narration(
    text: str,
    word_boundaries: Sequence[Dict[str, Any]],
    min_gap_chars: int = DEFAULT_MIN_SUSPECTED_DROP_CHARS,
    pace_ratio_threshold: float = DEFAULT_SUSPECTED_DROP_PACE_RATIO,
) -> List[Dict[str, Any]]:
    """Detect stretches of ``text`` that edge-tts likely never voiced at
    all, as opposed to ordinary unmatched punctuation/whitespace.

    Why this exists: a real deck showed edge-tts silently skip an entire
    ~300-character stretch of a slide's notes (two full bullet points'
    worth of content) while synthesizing its mp3 - not a crash, not an
    error, just a WordBoundary stream that jumps straight from one word to
    another with several sentences' worth of source text in between and
    only a few seconds of audio to show for it. The existing per-segment
    "No WordBoundary events matched" warning (see
    ``align_segments_with_word_boundaries``) only surfaces this
    indirectly, one small Phase-2 segment at a time, mixed in with
    ordinary single-character punctuation mismatches (e.g. a lone closing
    quote mark edge-tts doesn't voice) - nothing about it flags "this is
    unusually large" or shows what text was actually lost. Confirmed
    against a real deck: the project owner listened to the exact audio
    position this function would have flagged and confirmed the narration
    genuinely jumped straight over that text.

    Method: re-run the same word-boundary-to-source-text matching
    ``align_segments_with_word_boundaries`` uses internally
    (``_match_word_boundaries``), then walk the *matched* events in order
    and look at the gap between each consecutive pair - both in source
    *characters* (how much text sits between them, unmatched) and in
    *audio seconds* (how much time the recording actually spent between
    them). Ordinary skipped punctuation/whitespace produces small,
    unremarkable gaps in both dimensions. A dropped chunk of real content
    produces a gap that's large in characters but suspiciously small in
    seconds, because the audio simply doesn't contain it - compared
    against this slide's *own* overall narration pace (characters spoken
    per second, measured from its own matched events, so it's not thrown
    off by a different slide's voice/rate settings), a gap is flagged when
    the actual audio time is less than ``pace_ratio_threshold`` (default
    30%) of what that much source text should have taken to speak at this
    slide's own pace. ``min_gap_chars`` (default 15) filters out the
    ordinary small gaps (a skipped punctuation mark, a line break) that
    would otherwise trigger on nearly every slide and bury real findings
    in noise.

    This is deliberately a heuristic, not a guarantee: a slide with too
    few matched events (fewer than 2) can't establish its own pace at all
    and is skipped entirely (returns ``[]``); a genuinely unusual but real
    pause (e.g. a long dramatic silence written into the notes) could in
    theory trip this too, though it hasn't been observed in practice, and
    reviewing the flagged ``skipped_text`` immediately tells a human which
    case it is.

    Args:
        text: The original notes text - same string passed to
            ``synthesize_with_word_boundaries``/``align_segments_with_word_boundaries``.
        word_boundaries: The raw WordBoundary events from
            ``synthesize_with_word_boundaries`` (the same input
            ``align_segments_with_word_boundaries`` takes).
        min_gap_chars: Minimum unmatched source-character span for a gap
            to be considered at all - smaller gaps are ordinary and not
            reported.
        pace_ratio_threshold: A gap is flagged when its actual audio
            duration is less than this fraction of what the slide's own
            measured narration pace would predict for that many
            characters.

    Returns:
        A list of dicts, one per suspected drop, each with
        ``source_start_offset``/``source_end_offset`` (the unmatched
        span's bounds in ``text``), ``skipped_text`` (the actual substring
        - shown directly so a human doesn't have to go hunting for it, see
        the real slide_009 investigation this was built from), ``gap_seconds``
        (how much audio time actually elapsed), ``expected_seconds`` (how
        much this slide's own pace predicts that much text should have
        taken), and ``audio_position_seconds`` (where in the mp3 to listen
        to check by ear). Empty if nothing suspicious was found.
    """
    matched, _ = _match_word_boundaries(text, word_boundaries)
    if len(matched) < 2:
        return []

    total_chars = matched[-1]["source_end_offset"] - matched[0]["source_start_offset"]
    total_seconds = (
        matched[-1]["offset_seconds"] + matched[-1]["duration_seconds"] - matched[0]["offset_seconds"]
    )
    if total_chars <= 0 or total_seconds <= 0:
        return []
    overall_pace_chars_per_second = total_chars / total_seconds

    suspects: List[Dict[str, Any]] = []
    for prev, nxt in zip(matched, matched[1:]):
        gap_chars = nxt["source_start_offset"] - prev["source_end_offset"]
        if gap_chars < min_gap_chars:
            continue

        gap_seconds = nxt["offset_seconds"] - (prev["offset_seconds"] + prev["duration_seconds"])
        expected_seconds = gap_chars / overall_pace_chars_per_second

        if gap_seconds < expected_seconds * pace_ratio_threshold:
            suspects.append({
                "source_start_offset": prev["source_end_offset"],
                "source_end_offset": nxt["source_start_offset"],
                "skipped_text": text[prev["source_end_offset"]:nxt["source_start_offset"]],
                "gap_seconds": max(gap_seconds, 0.0),
                "expected_seconds": expected_seconds,
                "audio_position_seconds": prev["offset_seconds"] + prev["duration_seconds"],
            })

    return suspects


def _seconds_to_srt_timestamp(seconds: float) -> str:
    """Format a seconds value as an SRT timestamp: ``HH:MM:SS,mmm``.

    Negative input (should not happen from this module's own output, but
    guarded defensively since this is also usable standalone) is clamped
    to zero rather than producing a malformed/negative timestamp.
    """
    if seconds < 0:
        seconds = 0.0
    total_ms = round(seconds * 1000)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, ms = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def format_srt(entries: Sequence[Dict[str, Any]]) -> str:
    """Format aligned segments (``align_segments_with_word_boundaries``'s
    ``aligned_segments`` return value, or anything shaped like it - only
    ``text``/``start_seconds``/``end_seconds`` are read) as standard SRT
    text: 1-based sequential index, ``HH:MM:SS,mmm --> HH:MM:SS,mmm``
    timestamp line, the subtitle text, then a blank line separating cues.

    Returns "" for an empty ``entries`` sequence.
    """
    if not entries:
        return ""

    lines: List[str] = []
    for index, entry in enumerate(entries, start=1):
        start = _seconds_to_srt_timestamp(entry["start_seconds"])
        end = _seconds_to_srt_timestamp(entry["end_seconds"])
        lines.append(str(index))
        lines.append(f"{start} --> {end}")
        lines.append(str(entry["text"]))
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"
