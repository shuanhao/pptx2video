"""Merge per-slide subtitle alignment (Phase 3) across an entire deck into
one SRT file's worth of text, matching the timeline of the final merged MP4
``ppt_automation.export_video()`` produces.

This is Phase 4 of the SRT subtitle feature (see project discussion). It
ties together:

- ``pptx_parser.extract_notes()`` - the full, ordered slide list (including
  slides with no notes, which still occupy time in the final video).
- The manifest ``tts.generate_audio_files()`` writes - each audio slide's
  mp3 filename and (as of Phase 4's change to that function) its
  ``word_boundaries_file`` sidecar.
- ``subtitle_segmenter.segment_notes_for_subtitles()`` (Phase 2) and
  ``subtitle_alignment.align_segments_with_word_boundaries()`` /
  ``format_srt()`` (Phase 3).

Design decisions (confirmed with the project owner before implementing):

1. Each slide's duration in the final video's timeline is taken to be the
   *actual* length of its embedded audio file (measured directly, via
   pydub - not estimated from WordBoundary data), or ``default_slide_duration``
   for a slide with no narration. This was verified empirically against a
   real PowerPoint "Create a Video" export (see
   ``scripts/verify_slide_timing.py`` and the project discussion) rather
   than assumed - PowerPoint's export timing for audio-driven slides has
   been reported (by other users, elsewhere) to sometimes add several
   seconds of unexplained trailing silence, which would have made this
   approach unsafe; it does not appear to happen for decks built by this
   project's ``ppt_automation.insert_audio()`` (which sets
   ``PlaySettings.PlayOnEntry``/``HideWhileNotPlaying``), where measured
   drift stayed under ~0.2s over a multi-minute deck.
2. No cross-slide extension of the "end time reaches toward the next cue"
   buffer that ``align_segments_with_word_boundaries`` already applies
   *within* a slide (see subtitle_alignment.py's design decision 2). A
   slide's last subtitle line ends at its own last matched word's time;
   subtitles do not carry over the visual cut to the next slide. Kept
   deliberately simple - revisit only if real content shows it looks wrong.
3. All slides' subtitle lines are concatenated in slide order and passed to
   ``format_srt`` once, so numbering is contiguous across the whole deck
   rather than restarting per slide.

Known limitation: a slide whose manifest entry has no
``word_boundaries_file`` (i.e. ``generate_audio_files()`` was called with a
custom ``generator`` that didn't capture timing data) is silently skipped
from the subtitle output - its narration still plays, but with no subtitle
line - and this is called out in the returned ``warnings`` list. This
hasn't been exercised against a real multi-slide deck's full pipeline run
yet (only against ``scripts/verify_slide_timing.py``'s timing measurement,
which doesn't produce subtitles) - like the rest of this feature, it should
be re-checked once real content is run through the whole chain end to end.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pydub import AudioSegment

from src.subtitle_alignment import (
    DEFAULT_TRAILING_GAP_SECONDS,
    align_segments_with_word_boundaries,
    format_srt,
)
from src.subtitle_segmenter import DEFAULT_MAX_DISPLAY_WIDTH, segment_notes_for_subtitles

DEFAULT_SLIDE_DURATION_SECONDS = 5.0  # matches ppt_automation.export_video()'s default


def _measure_audio_duration_seconds(audio_path: Path) -> Optional[float]:
    """Measure an audio file's actual duration via pydub. Returns ``None``
    (rather than raising) if the file is missing or can't be decoded - a
    corrupt/missing audio file shouldn't take down subtitle generation for
    the rest of the deck; the caller falls back to
    ``default_slide_duration`` and this is surfaced via ``warnings``.
    """
    if not audio_path.exists():
        return None
    try:
        return AudioSegment.from_file(audio_path).duration_seconds
    except Exception:
        return None


def generate_srt_for_deck(
    slides: Sequence[Dict[str, Any]],
    manifest: Dict[str, Any],
    audio_dir: Path | str,
    default_slide_duration: float = DEFAULT_SLIDE_DURATION_SECONDS,
    max_display_width: int = DEFAULT_MAX_DISPLAY_WIDTH,
    trailing_gap_seconds: float = DEFAULT_TRAILING_GAP_SECONDS,
) -> Tuple[str, List[str]]:
    """Build one deck-wide SRT file's text, with subtitle timestamps on the
    same timeline as the final merged MP4.

    Args:
        slides: The full, ordered slide list - typically
            ``pptx_parser.extract_notes(pptx_path)``'s return value. Must
            include every slide (with or without notes), so gaps (slides
            with no narration, occupying ``default_slide_duration``) are
            accounted for in the timeline.
        manifest: ``tts.generate_audio_files()``'s return value (or the
            equivalent loaded from ``manifest.json``) - used to find each
            slide's mp3 and word-boundaries sidecar file.
        audio_dir: Directory the manifest's filenames are relative to
            (matches ``manifest["output_dir"]`` in normal use).
        default_slide_duration: Seconds a slide with no narration occupies
            in the final video - must match whatever value was passed to
            ``ppt_automation.export_video()`` for the timeline to line up.
        max_display_width: Passed through to ``segment_notes_for_subtitles``.
        trailing_gap_seconds: Passed through to
            ``align_segments_with_word_boundaries``.

    Returns:
        ``(srt_text, warnings)``: ``srt_text`` is ready to write straight to
        a ``.srt`` file (possibly ``""`` if no slide produced any subtitle
        lines). ``warnings`` collects everything from
        ``align_segments_with_word_boundaries`` (prefixed with which slide
        it came from) plus this function's own notes (missing/corrupt audio
        files, slides with audio but no captured word-boundary data) -
        empty when everything lined up cleanly.
    """
    audio_dir = Path(audio_dir)
    manifest_by_slide = {int(e["slide_num"]): e for e in manifest.get("slides", [])}
    ordered_slides = sorted(slides, key=lambda s: int(s.get("slide_num", 0)))

    cumulative_seconds = 0.0
    all_entries: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for slide in ordered_slides:
        slide_num = int(slide.get("slide_num", 0))
        entry = manifest_by_slide.get(slide_num)

        if entry is None:
            # No narration for this slide - it still occupies time in the
            # final video, but there is nothing to make a subtitle from.
            cumulative_seconds += default_slide_duration
            continue

        audio_path = audio_dir / entry["audio_file"]
        slide_duration = _measure_audio_duration_seconds(audio_path)
        if slide_duration is None:
            warnings.append(
                f"slide {slide_num}: could not measure audio duration for "
                f"{audio_path} (missing or unreadable); assumed "
                f"default_slide_duration ({default_slide_duration}s) instead, "
                "which will desync every slide after this one if wrong."
            )
            slide_duration = default_slide_duration

        word_boundaries_file = entry.get("word_boundaries_file")
        if not word_boundaries_file:
            warnings.append(
                f"slide {slide_num}: has narration but no word_boundaries_file "
                "in the manifest (a custom TTS generator was likely used); "
                "skipped from subtitles - its audio will still play with no "
                "corresponding subtitle line."
            )
            cumulative_seconds += slide_duration
            continue

        word_boundaries_path = audio_dir / word_boundaries_file
        try:
            word_boundaries = json.loads(word_boundaries_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            warnings.append(
                f"slide {slide_num}: could not read word boundaries file "
                f"{word_boundaries_path} ({exc}); skipped from subtitles."
            )
            cumulative_seconds += slide_duration
            continue

        notes_text = str(slide.get("notes") or "")
        segments = segment_notes_for_subtitles(notes_text, max_display_width=max_display_width)

        if segments:
            aligned, slide_warnings = align_segments_with_word_boundaries(
                notes_text, segments, word_boundaries, trailing_gap_seconds=trailing_gap_seconds
            )
            warnings.extend(f"slide {slide_num}: {w}" for w in slide_warnings)

            for aligned_entry in aligned:
                all_entries.append({
                    "text": aligned_entry["text"],
                    "start_seconds": aligned_entry["start_seconds"] + cumulative_seconds,
                    "end_seconds": aligned_entry["end_seconds"] + cumulative_seconds,
                })

        cumulative_seconds += slide_duration

    return format_srt(all_entries), warnings
