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


def _find_boundary_span(text: str, cursor: int, boundary_text: str) -> Optional[Tuple[int, int]]:
    """Find where ``boundary_text`` (one WordBoundary event's ``text``)
    next occurs in ``text`` at or after ``cursor``.

    Tries, in order:
    1. Exact substring search within a bounded lookahead window
       (``_MATCH_SEARCH_WINDOW``) - the fast, expected-common-case path.
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

    idx = text.find(boundary_text, cursor, window_end)
    if idx != -1:
        return idx, idx + len(boundary_text)

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

    for wb in word_boundaries:
        raw_text = str(wb.get("text", ""))
        if not raw_text.strip():
            continue

        span = _find_boundary_span(text, cursor, raw_text)
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
