"""Locate each slide's *real* narration start time inside an already-exported
MP4, via audio cross-correlation - not prediction.

Why this exists: ``subtitle_pipeline.generate_srt_for_deck()`` (the
"predictive" path) places each slide's subtitle lines by summing up each
slide's own mp3 duration (measured via pydub) plus ``default_slide_duration``
for silent slides. That assumes the final exported video's timeline is
exactly "slide durations, back to back, no gaps" - which does not hold in
practice: PowerPoint's "Create a Video" export can add uneven amounts of
extra time per slide (verified against a real ~2h40m/20-slide deck - see the
project discussion this module was written in response to - drift grew from
under half a second in the first few slides to several seconds by the end,
and did *not* behave like a simple/uniform scaling factor either, ruling out
a "just multiply everything by a constant" fix). For any deck long/complex
enough for that drift to be noticeable, the predictive timeline is not
trustworthy on its own.

This module is the "measure the truth after the fact" alternative: given the
*actual* exported MP4, it finds where each slide's own (already-known) mp3
audio really starts playing in that file, using FFT-based cross-correlation
(the same technique ``scripts/verify_slide_timing.py`` used to diagnose the
drift in the first place - this module is that script's core measurement
logic, extracted so both the diagnostic script and the real subtitle
pipeline can share one implementation instead of two copies drifting apart).

Consequence for the pipeline: this can only run *after*
``ppt_automation.export_video()`` has produced the final MP4 - it needs that
file to exist. See ``subtitle_pipeline.generate_srt_from_true_starts()`` and
``main.py`` for how the CLI now defers final subtitle generation until after
video export when both are requested together, instead of the old "subtitles
written right after --generate-audio" order.

Extra dependencies: unlike the rest of the pipeline, this module needs
``numpy`` and ``scipy`` (for the FFT-based cross-correlation) and ``ffmpeg``
on PATH (to extract the MP4's audio track - already a project prerequisite
for subtitle generation in general, see tts.py's ffmpeg hint). These are
real, required dependencies now (not optional/diagnostic-only) for anyone
using ``--subtitles-output`` together with ``--export-video`` - see
pyproject.toml/requirements.txt.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from pydub import AudioSegment
from scipy.signal import correlate

# Downsampled rate used for cross-correlation - plenty for locating a speech
# onset to well under 100ms precision, and keeps the FFT-based correlation
# fast even for multi-hour decks.
SAMPLE_RATE = 8000

# Multiplier applied to every measured absolute time this module returns, to
# correct a small but very real proportional bias found empirically on a
# real ~2h40m deck (see CHANGELOG's fourth v0.6.1 entry): comparing this
# module's measured slide-start times against the project owner's own
# precise, independently-verified real playback times (VLC "jump to exact
# time", cross-checked against 20 data points spanning the full deck) showed
# this module's own measured times run consistently ~0.12% "early" relative
# to true elapsed video time, growing smoothly with elapsed time (not with
# slide count, and not concentrated at any one slide) - residuals after
# fitting a single multiplicative correction were under 0.55s across the
# entire 2h40m deck (RMS ~0.27s), a dramatically better fit than any
# per-slide or per-count model tried. Deliberately ruled out as *not* the
# cause: the exported MP4's own audio/video sync (the project owner
# confirmed picture and voice agree with each other when watching without
# subtitles, and ffprobe showed the container's audio- and video-stream
# durations agreeing to within 0.02s), and resampling in this module's own
# ffmpeg/pydub extraction path (verified with a controlled 1000-second test
# signal round-tripped through both paths - both preserved duration exactly).
# The precise root cause within ``find_best_offset_seconds``'s correlation
# itself has not been pinned down; this constant is an empirically-derived,
# environment-specific calibration, not a universal constant - a value
# measured on one machine/PowerPoint build/deck is not guaranteed to transfer
# to another. It defaults to 1.0 (no correction) precisely because of that:
# every caller must opt in with its own measured value (see
# ``DEFAULT_GLOBAL_SCALE_CORRECTION``'s docstring reference in
# ``locate_slide_start_times``/``locate_slide_start_and_end_times`` for how
# to derive it for a new deck/environment) rather than silently applying
# someone else's number.
DEFAULT_GLOBAL_SCALE_CORRECTION = 1.0

# How far around the naive (summed-durations) prediction to search for the
# real match - generous relative to the multi-second drift this module
# exists to correct, while still bounding the search (and ruling out false
# matches against a completely different slide's audio far away in the
# track).
DEFAULT_SEARCH_WINDOW_SECONDS = 30.0

# How much of the *start* of each slide's own audio to use as the
# correlation template, instead of the whole clip.
#
# This matters more than it sounds like it should: correlating the *entire*
# clip (which can be several minutes long) against the exported video's
# audio track assumes the embedded audio plays back at exactly the same
# speed as the source mp3. Evidence from a real deck (see project
# discussion / CHANGELOG) points to PowerPoint's export very slightly
# time-stretching embedded audio - on the order of ~0.1% - which is
# imperceptible over a few seconds but, over a multi-hundred-second clip
# used whole as the correlation template, accumulates into a phase drift of
# hundreds of milliseconds to multiple seconds by the end of the clip. That
# drift biases where the whole-clip correlation's peak lands, systematically
# and substantially - confirmed empirically (see tests/test_audio_position_
# locator.py's stretch-bias test): a 120s clip stretched by 0.1% gave a
# ~0.2s error when correlated whole, versus ~0.005s when only its first 8s
# were used. Anchoring on a short leading window keeps the accumulated
# stretch error negligible regardless of how long the full slide's audio is,
# since only the anchor's own (short) duration is exposed to it.
DEFAULT_ANCHOR_SECONDS = 8.0


def _extract_audio_track(video_path: Path, out_wav: Path) -> None:
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(video_path),
                "-ar", str(SAMPLE_RATE), "-ac", "1", "-vn",
                str(out_wav),
            ],
            check=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "ffmpeg was not found on PATH - it is required to extract the "
            "exported video's audio track for true-start subtitle "
            "alignment. Install ffmpeg and ensure it's on PATH."
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
        raise RuntimeError(
            f"ffmpeg failed to extract audio from {video_path}: {stderr[-500:]}"
        ) from exc


def _load_mono_array(audio_path: Path) -> np.ndarray:
    audio = AudioSegment.from_file(audio_path).set_frame_rate(SAMPLE_RATE).set_channels(1)
    return np.array(audio.get_array_of_samples()).astype(np.float32)


def _normalize(x: np.ndarray) -> np.ndarray:
    std = x.std()
    return (x - x.mean()) / std if std > 1e-6 else x - x.mean()


def find_best_offset_seconds(
    full_track: np.ndarray,
    clip: np.ndarray,
    predicted_start_seconds: float,
    sample_rate: int = SAMPLE_RATE,
    search_window_seconds: float = DEFAULT_SEARCH_WINDOW_SECONDS,
) -> float:
    """Cross-correlate ``clip`` against a window of ``full_track`` centered
    on ``predicted_start_seconds`` (+/- ``search_window_seconds``),
    returning the real start time (seconds) that best matches.

    Uses FFT-based correlation (``scipy.signal.correlate(..., method="fft")``)
    rather than ``numpy.correlate``'s direct method, which is O(n*m) and far
    too slow for anything beyond a few seconds of audio at this sample rate.
    Both signals are mean/std-normalized first so the match is driven by
    waveform shape, not loudness.
    """
    center = int(predicted_start_seconds * sample_rate)
    window = int(search_window_seconds * sample_rate)
    lo = max(0, center - window)
    hi = min(len(full_track), center + window + len(clip))
    segment = full_track[lo:hi]

    if len(segment) < len(clip) or len(clip) == 0:
        return predicted_start_seconds  # not enough data to search - give up gracefully

    correlation = correlate(_normalize(segment), _normalize(clip), mode="valid", method="fft")
    best_index = int(np.argmax(correlation))
    return (lo + best_index) / sample_rate


def locate_slide_start_times(
    video_path: Path | str,
    slides: Sequence[Dict[str, Any]],
    manifest: Dict[str, Any],
    audio_dir: Path | str,
    default_slide_duration: float = 5.0,
    search_window_seconds: float = DEFAULT_SEARCH_WINDOW_SECONDS,
    anchor_seconds: float = DEFAULT_ANCHOR_SECONDS,
    global_scale_correction: float = DEFAULT_GLOBAL_SCALE_CORRECTION,
) -> Tuple[Dict[int, float], List[str]]:
    """Measure each narrated slide's *real* start time in ``video_path``.

    Args:
        video_path: The MP4 produced by ``ppt_automation.export_video()``.
        slides: The full, ordered slide list (e.g.
            ``pptx_parser.extract_notes()``'s return value) - used to walk
            every slide in order, including ones with no narration, so the
            naive/predicted starting point handed to each correlation search
            still accounts for the gaps they occupy.
        manifest: The audio manifest (``tts.generate_audio_files()``'s
            return value, or the equivalent loaded ``manifest.json``).
        audio_dir: Directory the manifest's audio filenames are relative to.
        default_slide_duration: Seconds a slide with no narration occupies -
            must match whatever was actually used for ``export_video()``,
            same as the predictive path's parameter of the same name.
        search_window_seconds: How far around the naive prediction to search
            for each slide's real audio - see ``find_best_offset_seconds``.
        anchor_seconds: Only the first this-many seconds of each slide's own
            audio is used as the correlation template (see
            ``DEFAULT_ANCHOR_SECONDS`` for why the whole clip is not used).
            A slide whose audio is shorter than this uses the whole clip.
        global_scale_correction: Multiplier applied to every returned
            measured time (see ``DEFAULT_GLOBAL_SCALE_CORRECTION``'s
            docstring for why this exists and how it was derived). Leave at
            1.0 unless you've independently confirmed *your* deck/export
            environment shows the same kind of proportional drift - to
            derive your own value, compare a handful of this function's
            measured times (widely spaced across the deck) against real
            playback times you verify precisely (e.g. a media player's
            "jump to exact time" feature, not eyeballing a running clock or
            a progress bar) and fit ``real_time / measured_time``.

    Returns:
        ``(start_times_by_slide, warnings)``: ``start_times_by_slide`` maps
        slide number -> measured real start time (seconds) in the video, for
        every slide that has narration *and* whose audio file could be
        loaded. A slide missing from this dict (silent slide, or its audio
        file was unreadable) has no measured position - callers should fall
        back to the predictive estimate for it and treat that as noted in
        ``warnings``.

    Raises:
        RuntimeError: if the video's audio track can't be extracted at all
            (missing ffmpeg, corrupt/unreadable video) - this is a hard
            failure since no per-slide measurement is possible without it,
            unlike per-slide audio problems which are only ever skipped.
    """
    video_path = Path(video_path)
    audio_dir = Path(audio_dir)
    manifest_by_slide = {int(e["slide_num"]): e for e in manifest.get("slides", [])}
    ordered_slides = sorted(slides, key=lambda s: int(s.get("slide_num", 0)))

    warnings: List[str] = []
    start_times: Dict[int, float] = {}

    with tempfile.TemporaryDirectory() as tmp:
        full_wav = Path(tmp) / "full.wav"
        _extract_audio_track(video_path, full_wav)
        full_track = _load_mono_array(full_wav)

        predicted_start = 0.0
        for slide in ordered_slides:
            slide_num = int(slide.get("slide_num", 0))
            entry = manifest_by_slide.get(slide_num)

            if entry is None:
                predicted_start += default_slide_duration
                continue

            audio_path = audio_dir / entry["audio_file"]
            if not audio_path.exists():
                warnings.append(
                    f"slide {slide_num}: audio file not found ({audio_path}); "
                    "could not measure its true start time, falling back to "
                    "the predicted position for it."
                )
                # Advance by the best guess available (default_slide_duration)
                # rather than leaving predicted_start stuck - later slides'
                # search windows should still be centered reasonably close,
                # not off by this slide's entire (unknown) duration.
                predicted_start += default_slide_duration
                continue

            try:
                clip = _load_mono_array(audio_path)
            except Exception as exc:  # noqa: BLE001 - one bad file shouldn't abort the deck
                warnings.append(
                    f"slide {slide_num}: could not decode {audio_path} ({exc}); "
                    "falling back to the predicted position for it."
                )
                predicted_start += default_slide_duration
                continue

            clip_duration = len(clip) / SAMPLE_RATE
            # See DEFAULT_ANCHOR_SECONDS: only correlate a short leading
            # window of the clip, not the whole thing, so a small embedded-
            # audio time-stretch (observed empirically - see module
            # docstring) doesn't bias the located start.
            anchor_samples = int(anchor_seconds * SAMPLE_RATE)
            anchor_clip = clip[:anchor_samples] if anchor_samples < len(clip) else clip
            measured_start = find_best_offset_seconds(
                full_track, anchor_clip, predicted_start, search_window_seconds=search_window_seconds
            )
            start_times[slide_num] = measured_start * global_scale_correction
            predicted_start += clip_duration

    return start_times, warnings


def locate_slide_start_and_end_times(
    video_path: Path | str,
    slides: Sequence[Dict[str, Any]],
    manifest: Dict[str, Any],
    audio_dir: Path | str,
    default_slide_duration: float = 5.0,
    search_window_seconds: float = DEFAULT_SEARCH_WINDOW_SECONDS,
    anchor_seconds: float = DEFAULT_ANCHOR_SECONDS,
    global_scale_correction: float = DEFAULT_GLOBAL_SCALE_CORRECTION,
) -> Tuple[Dict[int, Tuple[float, float]], List[str]]:
    """Measure each narrated slide's real start *and* end time in
    ``video_path``, independently of one another and of any other slide.

    IMPORTANT UPDATE (see ``DEFAULT_GLOBAL_SCALE_CORRECTION``'s docstring):
    the ~0.9988-0.9989 per-slide ratio mentioned below turned out to be
    mostly - possibly entirely - this same module's own ~0.12% global
    measurement bias, not a real per-slide audio stretch. Once a deck's
    ``global_scale_correction`` is calibrated and applied, a slide's own
    (measured_end - measured_start) / predicted_duration ratio should come
    out close to 1.0 (confirmed: 0.9988709... * 1.0012092... = 1.0000788,
    i.e. the two "corrections" cancel to within 0.008% on real data) -
    consistent with PowerPoint's export *not* actually changing embedded
    audio's playback speed at all. The per-slide direct-scale machinery
    below is left in place (it's harmless and still theoretically correct
    if some deck genuinely does have real per-slide stretch), but do not
    assume its ~0.9988 output on an *uncorrected* deck means "PowerPoint
    speeds up audio by 0.12%" - that reflects a fixable measurement bias,
    not a property of the exported video, as this note's history shows.

    Why this exists (in addition to ``locate_slide_start_times``): knowing
    where a slide *starts* is not enough to know how much its own audio was
    stretched by PowerPoint's export (see ``DEFAULT_ANCHOR_SECONDS``) -
    ``subtitle_pipeline.generate_srt_from_true_starts()`` originally derived
    a slide's real duration (and thus its own stretch ratio) from the gap
    between *its* measured start and the *next* slide's measured start. That
    conflates two different things that can both contribute to that gap:
    this slide's own audio playing back slightly faster/slower than its
    source mp3, and any extra time PowerPoint's export inserts *between*
    slides (a separate effect, unrelated to this slide's own narration
    speed). Confirmed against a real deck (see project discussion / this
    module's regression tests): the per-word ground-truth stretch ratio,
    measured directly within a slide via
    ``scripts/verify_srt_accuracy.py``, was consistent across an entire
    20-slide deck (~0.9988-0.9989) - but the *next-slide-inferred* ratio
    that ``generate_srt_from_true_starts()`` was actually using is
    systematically less reliable, because it's contaminated by whatever
    inter-slide gap PowerPoint's export adds.

    This function instead measures each slide's own end directly - via a
    second, independent correlation search using a *trailing* anchor (the
    last ``anchor_seconds`` of that slide's own audio) centered on the naive
    prediction ``measured_start + this slide's own predicted duration`` -
    exactly mirroring how the *start* is measured via the leading anchor.
    The resulting ``(start, end)`` pair for a slide is entirely self-
    contained: it says nothing about where the next slide begins, so it
    cannot be biased by an inter-slide gap the way the next-slide-inferred
    approach was.

    A slide whose own audio is shorter than ``2 * anchor_seconds`` (so the
    leading and trailing anchors would mostly or entirely overlap) falls
    back to ``measured_start + clip_duration`` for its end - there isn't
    enough independent signal in a short clip for two separate anchors to
    be meaningful, but a short clip is also far less exposed to
    accumulated stretch error in the first place (see
    ``DEFAULT_ANCHOR_SECONDS``), so this is a reasonable simplification.

    Args:
        Same as ``locate_slide_start_times`` (including
        ``global_scale_correction``, applied to both the returned start and
        end of every slide).

    Returns:
        ``(bounds_by_slide, warnings)``: ``bounds_by_slide`` maps slide
        number -> ``(measured_start_seconds, measured_end_seconds)``, for
        every slide that has narration *and* whose audio file could be
        loaded - same coverage as ``locate_slide_start_times``'s returned
        dict. A slide missing from this dict should fall back the same way
        callers already do for ``locate_slide_start_times``.

    Raises:
        RuntimeError: same as ``locate_slide_start_times``.
    """
    video_path = Path(video_path)
    audio_dir = Path(audio_dir)
    manifest_by_slide = {int(e["slide_num"]): e for e in manifest.get("slides", [])}
    ordered_slides = sorted(slides, key=lambda s: int(s.get("slide_num", 0)))

    warnings: List[str] = []
    bounds: Dict[int, Tuple[float, float]] = {}

    with tempfile.TemporaryDirectory() as tmp:
        full_wav = Path(tmp) / "full.wav"
        _extract_audio_track(video_path, full_wav)
        full_track = _load_mono_array(full_wav)

        predicted_start = 0.0
        for slide in ordered_slides:
            slide_num = int(slide.get("slide_num", 0))
            entry = manifest_by_slide.get(slide_num)

            if entry is None:
                predicted_start += default_slide_duration
                continue

            audio_path = audio_dir / entry["audio_file"]
            if not audio_path.exists():
                warnings.append(
                    f"slide {slide_num}: audio file not found ({audio_path}); "
                    "could not measure its true start/end time, falling back "
                    "to the predicted position for it."
                )
                predicted_start += default_slide_duration
                continue

            try:
                clip = _load_mono_array(audio_path)
            except Exception as exc:  # noqa: BLE001 - one bad file shouldn't abort the deck
                warnings.append(
                    f"slide {slide_num}: could not decode {audio_path} ({exc}); "
                    "falling back to the predicted position for it."
                )
                predicted_start += default_slide_duration
                continue

            clip_duration = len(clip) / SAMPLE_RATE
            anchor_samples = int(anchor_seconds * SAMPLE_RATE)

            leading_clip = clip[:anchor_samples] if anchor_samples < len(clip) else clip
            measured_start = find_best_offset_seconds(
                full_track, leading_clip, predicted_start, search_window_seconds=search_window_seconds
            )

            if anchor_samples < len(clip) and len(clip) >= 2 * anchor_samples:
                trailing_clip = clip[-anchor_samples:]
                # Naive prediction for where the trailing anchor's own start
                # falls: this slide's measured start plus its predicted
                # (unstretched) duration, minus the trailing anchor's own
                # length.
                naive_trailing_start = measured_start + clip_duration - anchor_seconds
                measured_trailing_start = find_best_offset_seconds(
                    full_track, trailing_clip, naive_trailing_start, search_window_seconds=search_window_seconds
                )
                measured_end = measured_trailing_start + anchor_seconds
            else:
                # Too short for two independent anchors - fall back to the
                # single (leading, or whole-clip) measurement plus the
                # predicted duration.
                measured_end = measured_start + clip_duration

            bounds[slide_num] = (
                measured_start * global_scale_correction,
                measured_end * global_scale_correction,
            )
            predicted_start += clip_duration

    return bounds, warnings
