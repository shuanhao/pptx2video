"""Merge per-slide subtitle alignment (Phase 3) across an entire deck into
one SRT file's worth of text, on the timeline of the final merged MP4
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

Two ways to place each slide's aligned lines on the deck-wide timeline are
provided, both built on the same per-slide alignment (``_build_slide_captions``):

- ``generate_srt_for_deck()`` (the original, "predictive" path): each
  slide's position is *predicted* by summing up preceding slides' measured
  audio durations (and ``default_slide_duration`` for silent slides). Fast,
  needs nothing beyond the manifest and audio files, but assumes the
  exported video's timeline is exactly "durations back to back, no gaps" -
  which does not hold for every deck (see next function).
- ``generate_srt_from_true_starts()`` (added after a real ~2h40m/20-slide
  deck showed the predictive path drifting by several seconds by the end,
  and not as a simple uniform scaling factor either - see project
  discussion and ``scripts/verify_slide_timing.py``): each slide's position
  is the *measured* real start time of its audio inside the actual exported
  MP4 (from ``audio_position_locator.locate_slide_start_times()``), not a
  prediction. This is the more accurate option whenever a final MP4 already
  exists to measure against - see ``main.py`` for how the CLI now prefers
  this path when ``--export-video`` is used alongside ``--subtitles-output``,
  falling back to the predictive path only when no video was exported this
  run (or true-start measurement itself fails).

Design decisions (confirmed with the project owner before implementing):

1. Each slide's *predicted* duration is the actual length of its embedded
   audio file (measured directly, via pydub - not estimated from
   WordBoundary data), or ``default_slide_duration`` for a slide with no
   narration. This underlies the predictive path; the true-start path
   doesn't need it for positioning, only as its fallback when a slide's
   measured start time isn't available (see point 4 below).
2. No cross-slide extension of the "end time reaches toward the next cue"
   buffer that ``align_segments_with_word_boundaries`` already applies
   *within* a slide (see subtitle_alignment.py's design decision 2). A
   slide's last subtitle line ends at its own last matched word's time;
   subtitles do not carry over the visual cut to the next slide. Kept
   deliberately simple - revisit only if real content shows it looks wrong.
3. All slides' subtitle lines are concatenated in slide order and passed to
   ``format_srt`` once, so numbering is contiguous across the whole deck
   rather than restarting per slide.
4. In the true-start path, a slide whose real start time couldn't be
   measured (missing/unreadable audio file, or the video's audio track
   couldn't be extracted at all - see ``audio_position_locator``) falls back
   to the *predicted* cumulative position for that slide specifically,
   rather than dropping its subtitles or aborting the whole deck. This is
   flagged in the returned warnings so it can be reviewed - it means that
   one slide's subtitles may still exhibit the drift this whole mechanism
   exists to avoid, but the rest of the deck stays accurate.
5. The true-start path also scales each slide's own *intra-slide* caption
   offsets by that slide's own real stretch ratio - not just its start
   position. Placing a slide's start correctly is not enough on its own for
   a long (multi-minute) slide: PowerPoint's export very slightly time-
   stretches embedded audio (see ``audio_position_locator.py``'s
   ``DEFAULT_ANCHOR_SECONDS`` docstring), so captions late within one
   slide's own narration - timed from the *original*, unstretched
   WordBoundary data - would otherwise drift proportionally within that
   slide even though the slide itself starts in the right place. This was
   found after a real deck still showed ~2s of residual drift by the end
   even with the start-position (anchor) fix alone.
   Preferred source for this ratio is ``true_ends_by_slide`` (from
   ``audio_position_locator.locate_slide_start_and_end_times()``): a
   slide's own measured end minus its own measured start, divided by its
   predicted duration - entirely self-contained, unaffected by any other
   slide. Confirmed via ``scripts/verify_srt_accuracy.py``'s word-level
   ground-truth sampling that this direct measurement is more reliable than
   the fallback used when it isn't available (inferring the ratio from the
   gap to the *next* measured slide's start instead), because the next-
   slide-inferred gap conflates this slide's own stretch with whatever gap
   PowerPoint's export inserts *between* slides - two different things. A
   slide with no ratio of its own at all (direct or inferred - typically
   only the last narrated slide in the deck, when it also has no measured
   end) uses the deck-wide average ratio instead, flagged in the warnings.

Known limitation: a slide whose manifest entry has no
``word_boundaries_file`` (i.e. ``generate_audio_files()`` was called with a
custom ``generator`` that didn't capture timing data) is silently skipped
from the subtitle output - its narration still plays, but with no subtitle
line - and this is called out in the returned ``warnings`` list.
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


def _build_slide_captions(
    slides: Sequence[Dict[str, Any]],
    manifest: Dict[str, Any],
    audio_dir: Path | str,
    default_slide_duration: float,
    max_display_width: int,
    trailing_gap_seconds: float,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Align every narrated slide's subtitle lines against its *own* audio
    (Phase 2 + Phase 3), without deciding where each slide sits on the
    deck-wide timeline - that's left to the caller (either
    ``generate_srt_for_deck``'s predicted cumulative sum, or
    ``generate_srt_from_true_starts``'s measured positions).

    Returns ``(per_slide, warnings)`` where ``per_slide`` is one dict per
    *ordered* input slide (including silent ones, so callers can walk a
    single list to reconstruct the full timeline):
    ``{"slide_num", "has_narration", "duration_seconds", "captions"}`` -
    ``duration_seconds`` is the measured (or default, for silent slides)
    duration used by the predictive path; ``captions`` is a list of
    ``{"text", "start_seconds", "end_seconds"}`` dicts with times *relative
    to this slide's own audio start* (i.e. not yet placed on the deck-wide
    timeline), empty for silent slides or slides skipped due to missing
    data.
    """
    audio_dir = Path(audio_dir)
    manifest_by_slide = {int(e["slide_num"]): e for e in manifest.get("slides", [])}
    ordered_slides = sorted(slides, key=lambda s: int(s.get("slide_num", 0)))

    per_slide: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for slide in ordered_slides:
        slide_num = int(slide.get("slide_num", 0))
        entry = manifest_by_slide.get(slide_num)

        if entry is None:
            # No narration for this slide - it still occupies time in the
            # final video, but there is nothing to make a subtitle from.
            per_slide.append({
                "slide_num": slide_num,
                "has_narration": False,
                "duration_seconds": default_slide_duration,
                "captions": [],
            })
            continue

        audio_path = audio_dir / entry["audio_file"]
        slide_duration = _measure_audio_duration_seconds(audio_path)
        if slide_duration is None:
            warnings.append(
                f"slide {slide_num}: could not measure audio duration for "
                f"{audio_path} (missing or unreadable); assumed "
                f"default_slide_duration ({default_slide_duration}s) instead, "
                "which will desync every slide after this one if wrong "
                "(predictive path only - the true-start path is unaffected)."
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
            per_slide.append({
                "slide_num": slide_num,
                "has_narration": True,
                "duration_seconds": slide_duration,
                "captions": [],
            })
            continue

        word_boundaries_path = audio_dir / word_boundaries_file
        try:
            word_boundaries = json.loads(word_boundaries_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            warnings.append(
                f"slide {slide_num}: could not read word boundaries file "
                f"{word_boundaries_path} ({exc}); skipped from subtitles."
            )
            per_slide.append({
                "slide_num": slide_num,
                "has_narration": True,
                "duration_seconds": slide_duration,
                "captions": [],
            })
            continue

        notes_text = str(slide.get("notes") or "")
        segments = segment_notes_for_subtitles(notes_text, max_display_width=max_display_width)

        captions: List[Dict[str, Any]] = []
        if segments:
            aligned, slide_warnings = align_segments_with_word_boundaries(
                notes_text, segments, word_boundaries, trailing_gap_seconds=trailing_gap_seconds
            )
            warnings.extend(f"slide {slide_num}: {w}" for w in slide_warnings)
            captions = [
                {
                    "text": a["text"],
                    "start_seconds": a["start_seconds"],
                    "end_seconds": a["end_seconds"],
                }
                for a in aligned
            ]

        per_slide.append({
            "slide_num": slide_num,
            "has_narration": True,
            "duration_seconds": slide_duration,
            "captions": captions,
        })

    return per_slide, warnings


def generate_srt_for_deck(
    slides: Sequence[Dict[str, Any]],
    manifest: Dict[str, Any],
    audio_dir: Path | str,
    default_slide_duration: float = DEFAULT_SLIDE_DURATION_SECONDS,
    max_display_width: int = DEFAULT_MAX_DISPLAY_WIDTH,
    trailing_gap_seconds: float = DEFAULT_TRAILING_GAP_SECONDS,
) -> Tuple[str, List[str]]:
    """Build one deck-wide SRT file's text, with each slide's position
    *predicted* by summing up preceding slides' measured audio durations.

    Prefer ``generate_srt_from_true_starts()`` instead whenever a final MP4
    already exists to measure against (see module docstring) - this
    predictive path is for when no export has happened yet (or this run
    isn't exporting video at all), and is not guaranteed to stay in sync
    with the real exported video for long/complex decks.

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
        ``(srt_text, warnings)`` - see module docstring.
    """
    per_slide, warnings = _build_slide_captions(
        slides, manifest, audio_dir, default_slide_duration, max_display_width, trailing_gap_seconds
    )

    cumulative_seconds = 0.0
    all_entries: List[Dict[str, Any]] = []

    for slide in per_slide:
        for caption in slide["captions"]:
            all_entries.append({
                "text": caption["text"],
                "start_seconds": caption["start_seconds"] + cumulative_seconds,
                "end_seconds": caption["end_seconds"] + cumulative_seconds,
            })
        cumulative_seconds += slide["duration_seconds"]

    return format_srt(all_entries), warnings


def generate_srt_from_true_starts(
    slides: Sequence[Dict[str, Any]],
    manifest: Dict[str, Any],
    audio_dir: Path | str,
    true_starts_by_slide: Dict[int, float],
    true_ends_by_slide: Optional[Dict[int, float]] = None,
    default_slide_duration: float = DEFAULT_SLIDE_DURATION_SECONDS,
    max_display_width: int = DEFAULT_MAX_DISPLAY_WIDTH,
    trailing_gap_seconds: float = DEFAULT_TRAILING_GAP_SECONDS,
) -> Tuple[str, List[str]]:
    """Build one deck-wide SRT file's text, with each narrated slide's
    position taken from ``true_starts_by_slide`` - measured real start
    times in an actual exported MP4 (see
    ``audio_position_locator.locate_slide_start_times()`` /
    ``locate_slide_start_and_end_times()``) - instead of predicted from
    summed durations.

    This is the accurate path: it does not assume anything about how
    PowerPoint's export lays out slide timing, because it's built from
    where each slide's audio was actually found in the real output file.

    Args:
        slides, manifest, audio_dir, max_display_width, trailing_gap_seconds:
            Same as ``generate_srt_for_deck``.
        true_starts_by_slide: ``{slide_num: measured_start_seconds}`` from
            ``audio_position_locator.locate_slide_start_times()`` (or the
            starts half of ``locate_slide_start_and_end_times()``). A
            narrated slide missing from this dict falls back to the
            *predicted* cumulative position for that slide only (see module
            docstring, design decision 4) - this is noted in the returned
            warnings.
        true_ends_by_slide: ``{slide_num: measured_end_seconds}`` from
            ``audio_position_locator.locate_slide_start_and_end_times()`` -
            optional, but strongly preferred when available (see design
            decision 5 below). When a slide has both a measured start and
            end, its own real (stretched) duration is known directly, with
            no dependency on any other slide's measurement.
        default_slide_duration: Used only for the fallback predicted
            position of a slide missing from ``true_starts_by_slide``, and
            for silent slides' predicted-timeline bookkeeping while
            computing that fallback.

    Returns:
        ``(srt_text, warnings)`` - see module docstring.
    """
    per_slide, warnings = _build_slide_captions(
        slides, manifest, audio_dir, default_slide_duration, max_display_width, trailing_gap_seconds
    )

    n = len(per_slide)

    # Predicted (fallback) cumulative position for any slide with no
    # measured true start of its own at all.
    predicted_starts = [0.0] * n
    cumulative = 0.0
    for i, slide in enumerate(per_slide):
        predicted_starts[i] = cumulative
        cumulative += slide["duration_seconds"]

    measured_index = [
        i for i, slide in enumerate(per_slide)
        if true_starts_by_slide.get(slide["slide_num"]) is not None
    ]

    # Per-slide intra-slide scale factor. Locating a slide's *start* position
    # (measured_start above) is not the whole fix for a long deck: PowerPoint's
    # export appears to very slightly time-stretch embedded audio (see
    # audio_position_locator.py's DEFAULT_ANCHOR_SECONDS docstring), so a
    # long (multi-minute) slide's own captions - timed from the *original*,
    # unstretched mp3's WordBoundary data - drift proportionally within that
    # slide even once its start is correctly placed. Confirmed against a
    # real report of ~2s residual drift by the end of a 2h40m deck that
    # persisted after the start-position (anchor) fix alone.
    #
    # Two ways to get a slide's own scale, preferred in this order:
    #
    # 1. Direct (``true_ends_by_slide``): this slide's own measured end minus
    #    its own measured start, divided by its predicted (source-mp3)
    #    duration. Entirely self-contained - says nothing about any other
    #    slide, so it can't be biased by whatever gap PowerPoint's export
    #    inserts *between* slides.
    # 2. Inferred (fallback, when no direct measurement is available for a
    #    slide): the gap between this slide's measured start and the *next*
    #    measured slide's start, divided by the predicted gap between them.
    #    Confirmed (via scripts/verify_srt_accuracy.py's word-level ground-
    #    truth sampling on a real deck) to be less reliable than the direct
    #    measurement, because it conflates this slide's own stretch with any
    #    inter-slide gap - kept only as a fallback for when a direct
    #    measurement isn't available (e.g. ``locate_slide_start_times()`` was
    #    used instead of ``locate_slide_start_and_end_times()``).
    direct_scales: Dict[int, float] = {}
    if true_ends_by_slide:
        for i, slide in enumerate(per_slide):
            slide_num = slide["slide_num"]
            start = true_starts_by_slide.get(slide_num)
            end = true_ends_by_slide.get(slide_num)
            predicted_duration = slide["duration_seconds"]
            if start is not None and end is not None and predicted_duration > 1e-6:
                direct_scales[i] = (end - start) / predicted_duration

    inferred_scales: Dict[int, float] = {}
    for pos, i in enumerate(measured_index):
        if pos + 1 >= len(measured_index):
            continue
        j = measured_index[pos + 1]
        predicted_gap = predicted_starts[j] - predicted_starts[i]
        if predicted_gap <= 1e-6:
            continue
        true_gap = (
            true_starts_by_slide[per_slide[j]["slide_num"]]
            - true_starts_by_slide[per_slide[i]["slide_num"]]
        )
        inferred_scales[i] = true_gap / predicted_gap

    # Direct measurement wins wherever both exist for the same slide.
    scales: Dict[int, float] = {**inferred_scales, **direct_scales}

    # Deck-wide average, for a measured slide with no scale of its own at all
    # (typically just the last narrated slide, when true_ends_by_slide isn't
    # available for it either) - better than assuming no stretch at all
    # (scale=1.0), since the ratio is usually consistent across a deck
    # exported from the same PowerPoint run.
    fallback_scale = (sum(scales.values()) / len(scales)) if scales else 1.0

    all_entries: List[Dict[str, Any]] = []

    for i, slide in enumerate(per_slide):
        slide_num = slide["slide_num"]
        measured_start = true_starts_by_slide.get(slide_num)

        if slide["captions"] and measured_start is None:
            warnings.append(
                f"slide {slide_num}: no measured true start time available; "
                "fell back to the predicted position for this slide only "
                "(may still exhibit drift)."
            )

        start_offset = measured_start if measured_start is not None else predicted_starts[i]

        if not slide["captions"]:
            continue

        if measured_start is None:
            scale = 1.0  # predicted-fallback slide - nothing measured to scale from
        elif i in scales:
            scale = scales[i]
        else:
            scale = fallback_scale
            if fallback_scale != 1.0:
                warnings.append(
                    f"slide {slide_num}: no measured end (or later slide) to "
                    "derive this slide's own audio stretch ratio from; used "
                    f"the deck-wide average ratio ({fallback_scale:.5f}) "
                    "instead - captions late in this slide's own narration "
                    "may still show small residual drift."
                )

        for caption in slide["captions"]:
            all_entries.append({
                "text": caption["text"],
                "start_seconds": caption["start_seconds"] * scale + start_offset,
                "end_seconds": caption["end_seconds"] * scale + start_offset,
            })

    return format_srt(all_entries), warnings
