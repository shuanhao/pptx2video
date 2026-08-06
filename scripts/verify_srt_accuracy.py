"""Stage 3 (ground-truth) check: does the deck's real spoken audio actually
land where the pipeline's math says it should - at *specific words*, not
just at each slide's measured start?

Dense mode (``--slides`` to restrict to specific slide(s), combined with a
high ``--samples-per-slide`` so every WordBoundary event gets sampled, plus
``--csv-output``) exists for one specific follow-up investigation: two real
decks have now shown a *localized* drift that the whole-slide direct_scale
correction can't explain by itself - e.g. one slide's real audio landing
~5s later than predicted at ~18% into that slide's own narration, and a
~12s gap found right at the very end of the deck's last narrated slide.
Both are *extra* delay on top of whatever the deck-wide ~0.12% compression
already accounts for, and both got worse the deeper into their own slide
they were. Three samples per slide (the default) can't distinguish "a
single discrete pause at one specific point" from "the true stretch ratio
gradually changes across the slide" - that needs the full shape of
corrected_delta across a slide's own timeline. Hence: pick one or two
suspect slides, sample every word in them, dump the fractional position
(word_offset / own_duration) and the word's own text alongside each delta,
and load the CSV somewhere it can be plotted/joined against the notes text
to see exactly where any jump happens and what's around it.

Why this exists: after two rounds of fixes (v0.6.1's anchor-based start
measurement, then its per-slide intra-slide scale correction - see
CHANGELOG), a real ~2h40m deck still showed ~2s of residual drift by the
end. Rather than propose a third guess, the project owner asked to verify
each pipeline stage independently:

    1. edge-tts's own .mp3 + .wordboundaries.json - see
       scripts/verify_tts_alignment.py.
    2. Where PowerPoint's export actually places each slide's audio in the
       final .mp4 - see scripts/verify_slide_timing.py (checks each slide's
       *start* only).
    3. Whether specific *words* within a slide's own narration - not just
       the slide's start - really land where the alignment math predicts,
       in the real exported video. This script.

This is the most direct test of all: instead of assuming a model for how
PowerPoint's export behaves (uniform stretch? fixed dead space? something
else?) and checking whether the model's predictions are self-consistent, it
picks real words from partway through and near the end of each slide's own
narration, extracts a short clip of *that exact word* from the slide's
source .mp3, and cross-correlates it directly against the real exported
video's audio track - the same ground-truth technique
audio_position_locator.py uses, just applied to individual words scattered
through each slide instead of only each slide's leading anchor.

For each sampled word this reports THREE things:

- ``naive_delta``: how far off that word's real (measured) position is from
  "this slide's measured start + this word's offset in the source mp3,
  unscaled" - i.e. what a start-only fix (no intra-slide scaling at all)
  would get wrong. This is ground truth about the *video*, not about this
  project's code - it does not change no matter which correction method
  ``generate_srt_from_true_starts()`` used internally, and is a useful
  sanity signal on its own: if it grows roughly linearly with the word's
  offset within its slide, that's a proportional stretch.
- ``implied_local_scale``: the stretch ratio that would make *this specific
  word* line up exactly (``1 + naive_delta / word_offset_within_slide``).
  If these come out consistent within a slide and across the whole deck,
  that's strong direct evidence for the proportional-stretch model.
- ``corrected_delta``: how far off that word's real (measured) position
  still is after applying this slide's own *directly measured* stretch
  ratio (via ``audio_position_locator.locate_slide_start_and_end_times()``
  - the same computation ``generate_srt_from_true_starts()`` now prefers,
  see CHANGELOG's third v0.6.1 fix). This is the number that should shrink
  towards ~0 if that fix is working - unlike ``naive_delta``, this one
  *does* reflect the current correction method, so re-running this script
  after a code change is how you confirm the fix actually helped instead of
  just re-confirming the same underlying ground truth every time.

After sampling, this also prints a **suggested ``--global-scale-correction``
value**, fitted (same least-squares-through-origin regression
``scripts/calibrate_scale.py`` uses) directly from this run's own
cross-correlation samples - see ``_fit_scale``'s docstring. This means you
don't have to manually open the exported MP4 in Audacity and read off real
timestamps by hand just to get a first estimate: this script already has
real, ground-truth-measured word positions scattered across the whole deck
from the same cross-correlation technique. For a quick pass, or a deck
where "close enough" is fine, the suggested value can usually be used
directly with ``--global-scale-correction``. For a deck where getting this
exactly right matters, cross-check it against ``calibrate_scale.py``'s
manually-measured result rather than trusting only this - this script's
samples are all machine-picked and machine-measured, with no independent
human-verified ground truth in the loop.

Usage:
    python scripts/verify_srt_accuracy.py \\
        --video output/deck.mp4 --manifest output/audio/manifest.json \\
        --slides-json output/slides.json [--samples-per-slide 3]

    # Dense mode - every word of slides 8 and 20, dumped to CSV for
    # plotting/correlation against the notes text. --word-search-window-seconds
    # widened past the default 8s because the drift being investigated is
    # already ~12s at the end of slide 20 - the search must comfortably
    # exceed that or it will silently fail to find the real position:
    python scripts/verify_srt_accuracy.py \\
        --video output/deck.mp4 --manifest output/audio/manifest.json \\
        --slides-json output/slides.json \\
        --slides 8,20 --samples-per-slide 9999 \\
        --word-search-window-seconds 20 \\
        --csv-output output/drift_dense.csv
"""

import argparse
import csv
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.audio_position_locator import (
    DEFAULT_ANCHOR_SECONDS,
    SAMPLE_RATE,
    _extract_audio_track,
    _load_mono_array,
    find_best_offset_seconds,
    locate_slide_start_and_end_times,
)
from src.pptx_parser import extract_notes
from src.logging_config import ensure_utf8_console

DEFAULT_SAMPLES_PER_SLIDE = 3
DEFAULT_WORD_SEARCH_WINDOW_SECONDS = 8.0
# Extra context around the sampled word, so the correlation template isn't
# a single, possibly-very-short WordBoundary event (which can be under
# 100ms for a single character and too weak a signal to correlate reliably
# on its own).
CLIP_LEAD_IN_SECONDS = 0.2
MIN_CLIP_SECONDS = 1.5


def _pick_sample_indices(n_events: int, samples_per_slide: int):
    if n_events <= samples_per_slide:
        return list(range(n_events))
    # Evenly spaced, always including the first and last event.
    return sorted({round(i * (n_events - 1) / (samples_per_slide - 1)) for i in range(samples_per_slide)})


def _fit_scale(measured: list, observed: list) -> float:
    """Least-squares fit of ``observed ~= k * measured``, forced through the
    origin - the exact same regression ``scripts/calibrate_scale.py`` uses
    (deliberately duplicated, not imported, so this script stays usable
    standalone - see that script's own copy for the derivation). Closed-form
    solution for a single coefficient with no intercept: ``k = sum(m*o) /
    sum(m*m)``.

    Added so this script can suggest a ``--global-scale-correction`` value
    directly from its own cross-correlation samples - every ``(measured,
    observed)`` pair this needs (``corrected_predicted_word_position``,
    ``measured_word_position``) is something this script already computes
    per sampled word while verifying accuracy, in the course of normal
    operation. That means a deck-wide correction coefficient can now be
    derived *without* ``scripts/calibrate_scale.py``'s manual step (opening
    the exported MP4 in Audacity and reading off real timestamps by hand for
    a handful of slides) - this script already has real, ground-truth
    measured positions for many words scattered across the whole deck, from
    the same cross-correlation technique, just automated instead of
    ear/eye-verified. See ``main()``'s use of this after the sampling loop
    for why this is *not* a strictly-better replacement for
    ``calibrate_scale.py`` in every case (fewer/noisier samples on a short
    deck, and no independent human-verified ground truth to sanity-check
    against) - it's a fast first estimate, not a replacement for manual
    calibration on a deck where getting this right really matters.
    """
    numerator = sum(m * o for m, o in zip(measured, observed))
    denominator = sum(m * m for m in measured)
    if denominator == 0:
        raise ValueError("all measured word positions are zero - can't fit a scale correction from this data")
    return numerator / denominator


def main():
    # Reconfigure stdout/stderr to UTF-8 before any print() - Windows can
    # otherwise crash printing CJK slide text when stdout/stderr is piped
    # rather than an interactive console (see ensure_utf8_console()'s
    # docstring for the confirmed real-world crash this fixes).
    ensure_utf8_console()

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--audio-dir", type=Path, default=None)
    slide_source = parser.add_mutually_exclusive_group(required=True)
    slide_source.add_argument("--slides-json", type=Path)
    slide_source.add_argument("--pptx", type=Path)
    parser.add_argument("--samples-per-slide", type=int, default=DEFAULT_SAMPLES_PER_SLIDE,
                         help="How many words to sample per slide. Set this >= the slide's own WordBoundary "
                              "event count (e.g. 9999) together with --slides to sample EVERY word in specific "
                              "slide(s) - dense mode, for mapping out exactly where a local drift starts.")
    parser.add_argument("--slides", type=str, default=None,
                         help="Comma-separated slide numbers to restrict sampling to (e.g. '8,20'). Default: "
                              "every narrated slide in the deck. Combine with a high --samples-per-slide for "
                              "dense mode on a specific suspect slide.")
    parser.add_argument("--anchor-seconds", type=float, default=DEFAULT_ANCHOR_SECONDS)
    parser.add_argument("--word-search-window-seconds", type=float, default=DEFAULT_WORD_SEARCH_WINDOW_SECONDS,
                         help="How far around the naive (unscaled) prediction to search for each sampled word - "
                              "must comfortably exceed the residual drift you're investigating (e.g. the ~12s "
                              "reported at the end of the deck) or the search simply won't find the real "
                              "position. Widen this for dense mode on the suspect slides.")
    parser.add_argument("--csv-output", type=Path, default=None,
                         help="Write every sampled row to this CSV path (slide_num, text, word_offset, "
                              "fraction_within_slide, naive_delta, implied_local_scale, corrected_delta) - "
                              "for offline plotting or joining against the notes text. In addition to, not "
                              "instead of, the console table.")
    args = parser.parse_args()

    wanted_slides = None
    if args.slides:
        wanted_slides = {int(s.strip()) for s in args.slides.split(",") if s.strip()}

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    audio_dir = args.audio_dir or Path(manifest.get("output_dir") or args.manifest.parent)
    manifest_by_slide = {int(e["slide_num"]): e for e in manifest.get("slides", [])}

    if args.slides_json:
        payload = json.loads(args.slides_json.read_text(encoding="utf-8"))
        slides = payload.get("slides", payload) if isinstance(payload, dict) else payload
    else:
        slides = extract_notes(str(args.pptx))
    slides = sorted(slides, key=lambda s: int(s["slide_num"]))

    print("Step 1/2: measuring each slide's start AND end (locate_slide_start_and_end_times) ...")
    bounds, locate_warnings = locate_slide_start_and_end_times(
        args.video, slides, manifest, audio_dir, anchor_seconds=args.anchor_seconds
    )
    for w in locate_warnings:
        print(f"WARNING: {w}")

    print("Step 2/2: extracting the full video audio track once for word-level sampling ...")
    with tempfile.TemporaryDirectory() as tmp:
        full_wav = Path(tmp) / "full.wav"
        _extract_audio_track(args.video, full_wav)
        full_track = _load_mono_array(full_wav)

        print(
            f"\n{'slide':>5} {'word':>10} {'offset':>8} {'frac':>6} {'naive_delta':>12} "
            f"{'implied_scale':>14} {'corrected_delta':>16}"
        )

        rows = []
        for slide in slides:
            slide_num = int(slide["slide_num"])
            if wanted_slides is not None and slide_num not in wanted_slides:
                continue
            entry = manifest_by_slide.get(slide_num)
            slide_bounds = bounds.get(slide_num)
            if entry is None or slide_bounds is None:
                continue
            slide_start, slide_end = slide_bounds

            wb_file = entry.get("word_boundaries_file")
            if not wb_file:
                continue
            wb_path = audio_dir / wb_file
            try:
                events = json.loads(wb_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not events:
                continue

            audio_path = audio_dir / entry["audio_file"]
            try:
                own_clip = _load_mono_array(audio_path)
            except Exception:
                continue
            own_duration = len(own_clip) / SAMPLE_RATE

            # This slide's own directly-measured stretch ratio - the same
            # computation generate_srt_from_true_starts() now prefers (see
            # subtitle_pipeline.py's module docstring, design decision 5).
            direct_scale = (slide_end - slide_start) / own_duration if own_duration > 1e-6 else 1.0

            for idx in _pick_sample_indices(len(events), args.samples_per_slide):
                ev = events[idx]
                word_offset = ev["offset_seconds"]
                if word_offset < 0.05:
                    continue  # too close to the slide's own start - the anchor already covers this; not informative

                clip_start_offset = max(0.0, word_offset - CLIP_LEAD_IN_SECONDS)
                clip_end_offset = min(
                    own_duration,
                    max(clip_start_offset + MIN_CLIP_SECONDS, word_offset + ev["duration_seconds"] + CLIP_LEAD_IN_SECONDS),
                )
                start_sample = int(clip_start_offset * SAMPLE_RATE)
                end_sample = int(clip_end_offset * SAMPLE_RATE)
                query_clip = own_clip[start_sample:end_sample]
                if len(query_clip) < int(0.5 * SAMPLE_RATE):
                    continue  # not enough signal to correlate meaningfully

                naive_predicted_clip_start = slide_start + clip_start_offset
                measured_clip_start = find_best_offset_seconds(
                    full_track, query_clip, naive_predicted_clip_start,
                    search_window_seconds=args.word_search_window_seconds,
                )
                measured_word_position = measured_clip_start + (word_offset - clip_start_offset)
                naive_predicted_word_position = slide_start + word_offset
                naive_delta = measured_word_position - naive_predicted_word_position
                implied_scale = 1.0 + (naive_delta / word_offset)

                corrected_predicted_word_position = slide_start + word_offset * direct_scale
                corrected_delta = measured_word_position - corrected_predicted_word_position
                fraction = word_offset / own_duration if own_duration > 1e-6 else 0.0

                rows.append((
                    slide_num, ev.get("text", ""), word_offset, fraction, naive_delta, implied_scale,
                    corrected_delta, corrected_predicted_word_position, measured_word_position,
                ))
                print(
                    f"{slide_num:>5} {ev.get('text', '')[:10]:>10} {word_offset:>7.2f}s {fraction:>5.1%} "
                    f"{naive_delta:>+11.3f}s {implied_scale:>14.5f} {corrected_delta:>+15.3f}s"
                )

    if args.csv_output:
        args.csv_output.parent.mkdir(parents=True, exist_ok=True)
        with args.csv_output.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "slide_num", "text", "word_offset_seconds", "fraction_within_slide",
                "naive_delta_seconds", "implied_local_scale", "corrected_delta_seconds",
                "corrected_predicted_word_position_seconds", "measured_word_position_seconds",
            ])
            for r in rows:
                writer.writerow(r)
        print(f"\nWrote {len(rows)} row(s) to {args.csv_output}")

    if not rows:
        print("\nNo samples could be measured (no narrated slides with word boundaries, or all too close to slide start).")
        return

    deltas = [r[4] for r in rows]
    scales = [r[5] for r in rows]
    corrected_deltas = [r[6] for r in rows]
    print(f"\nSampled {len(rows)} words across the deck.")
    print(f"naive_delta range: {min(deltas):+.3f}s .. {max(deltas):+.3f}s")
    print(f"implied_local_scale range: {min(scales):.5f} .. {max(scales):.5f}")
    print(f"corrected_delta range (after this slide's own directly-measured scale): "
          f"{min(corrected_deltas):+.3f}s .. {max(corrected_deltas):+.3f}s")
    print(
        "\nHow to read this:\n"
        "- naive_delta / implied_local_scale describe the raw video, independent of this project's\n"
        "  code - they will look the same every time you run this against the same .mp4, no matter\n"
        "  what fix was applied. If naive_delta grows roughly in proportion to each word's offset\n"
        "  within its own slide and implied_local_scale clusters tightly across the deck, that\n"
        "  confirms the proportional intra-slide stretch model.\n"
        "- corrected_delta is what actually reflects the current fix (this slide's own directly\n"
        "  measured start/end, see locate_slide_start_and_end_times). This is the number to watch\n"
        "  after a code change - if it's now consistently small (a few tens of ms, similar to the\n"
        "  correlation technique's own noise floor) across the whole deck, the intra-slide scaling\n"
        "  fix is working. If it's still large - especially if it's large in a way naive_delta\n"
        "  wasn't (e.g. it doesn't shrink relative to naive_delta at all), something is still wrong\n"
        "  with how the scale is being computed or applied, not just with which slide it's measured\n"
        "  from."
    )

    # Auto-suggested --global-scale-correction, derived entirely from this
    # run's own cross-correlation samples - no Audacity/manual timestamp
    # reading required (see _fit_scale's docstring for why this pairing of
    # values is valid). Needs at least a couple of samples spread across
    # real elapsed playback time to mean anything; a single slide or a very
    # short deck won't give the regression much to work with.
    measured_positions = [r[7] for r in rows]
    observed_positions = [r[8] for r in rows]
    try:
        suggested_k = _fit_scale(measured_positions, observed_positions)
    except ValueError as exc:
        print(f"\nCould not derive a suggested --global-scale-correction: {exc}")
        return

    residuals = [k_row[8] - k_row[7] * suggested_k for k_row in rows]
    rms = (sum(r * r for r in residuals) / len(residuals)) ** 0.5
    max_abs = max(abs(r) for r in residuals)
    print(
        f"\nSuggested --global-scale-correction (fitted from the {len(rows)} sample(s) above, "
        f"no manual measurement needed): {suggested_k:.5f}\n"
        f"Residual after applying it: RMS {rms:.3f}s, max {max_abs:.3f}s across the sampled words.\n"
        "This is a fast estimate from whatever this run happened to sample - more samples (raise "
        "--samples-per-slide) and a longer deck (more elapsed time for any proportional drift to "
        "show up in) make it more reliable. For a deck where getting this exactly right matters, "
        "cross-check against scripts/calibrate_scale.py's manually-measured result rather than "
        "trusting this alone; for a quick pass or a short deck, this number is usually good enough "
        "to use directly with --global-scale-correction."
    )


if __name__ == "__main__":
    main()
