"""Derive a deck/environment-specific ``--global-scale-correction`` value
from a handful of user-supplied real playback observations, instead of the
fully manual process (dump raw measured times, paste both columns into a
spreadsheet, fit a regression by hand) used to derive the very first value
of this constant (see CHANGELOG's fourth v0.6.1 entry and
``audio_position_locator.DEFAULT_GLOBAL_SCALE_CORRECTION``'s docstring).

Why this exists: that first value (k=1.00121) was validated on exactly one
deck, on exactly one machine, with exactly one PowerPoint installation. It
is explicitly documented as *not* a universal constant - whether the same
~0.12% bias shows up on other machines/PowerPoint versions/decks is still
an open question (see TODO.md). Regardless of the answer, anyone who needs
their own value should not have to repeat the original ad-hoc process by
hand. This script is that repeatable process:

    1. Run the project's normal pipeline once with the default
       ``--global-scale-correction 1.0`` (i.e. don't pass the flag at all)
       to get an *uncorrected* output/deck.mp4 and output/audio/manifest.json.
    2. Pick a handful of slides spread across the deck (the start and end
       slides plus 2-4 more in between is plenty - see "How many
       observations" below) and, in a real media player, precisely seek to
       the exact moment each picked slide's narration begins. Use a
       player's "jump to exact time" / frame-accurate seek feature - do NOT
       eyeball a running clock or a progress bar; sub-second precision
       here is the whole point.
    3. Record those real times against their slide numbers in a small JSON
       file (see ``--observations`` below).
    4. Run this script. It re-measures those same slides' *uncorrected*
       start times (the same computation ``locate_slide_start_times()``
       does internally), fits a single multiplicative constant
       ``k = real_time / measured_time`` by least squares (forced through
       the origin, matching how the original 1.00121 value was derived -
       see the module docstring reference above), and reports the
       suggested value plus how well it actually fits your observations.

How many observations: the original 1.00121 value was fit against 20 points
spanning a 2h40m deck and got a dramatically better fit (RMS 0.27s) than an
additive/per-slide-count alternative (RMS 0.44s) - direct evidence that,
for that deck, a *single* proportional constant explains the drift far
better than any per-slide model would. Since the model has exactly one
free parameter, it does not need 20 points to estimate well; 5-8 slides
spread across the full length of the deck (not clustered near the start)
is enough to get a reliable fit and, just as importantly, to see whether
the residual pattern still looks like a single proportional constant at
all (see "Residual too large" below) rather than something this simple
model can't capture.

Usage:
    python scripts/calibrate_scale.py \\
        --video output/deck.mp4 \\
        --manifest output/audio/manifest.json \\
        --slides-json output/slides.json \\
        --observations my_observations.json

    # or, if you don't have output/slides.json from a previous --output run:
    python scripts/calibrate_scale.py \\
        --video output/deck.mp4 \\
        --manifest output/audio/manifest.json \\
        --pptx examples/your_deck.pptx \\
        --observations my_observations.json

``my_observations.json`` maps slide number (as a string or int - either is
accepted) to the real, precisely-measured playback time in seconds, e.g.:

    {
        "2": 14.30,
        "6": 612.10,
        "11": 1340.85,
        "17": 2508.02,
        "21": 3021.44
    }

Output: prints the suggested ``--global-scale-correction`` value plus RMS
and max residual (in seconds, *after* applying the suggested correction) so
you can judge fit quality yourself, and (with ``--report``) writes a JSON
file with the same numbers plus the raw per-slide measured/observed/
residual rows, for a permanent record of how a given value was derived (the
same way ``dump_slide_bounds.py`` records its own params/output).

Residual too large: if the reported RMS/max residual is much worse than a
per-observation sanity check like "well under a second" for your deck's
length, that's a signal the single-proportional-constant model may not fit
this deck as cleanly as it fit the original one - e.g. because there's a
genuinely localized drift somewhere (a long silence, a very quiet slide
that measured poorly) rather than a smooth deck-wide bias. In that case,
look at the per-slide residuals in ``--report``'s output before trusting
the suggested value; a large residual concentrated on one or two slides
points at a measurement problem on those specific slides (see
``verify_srt_accuracy.py``'s dense per-word mode for digging into a single
suspect slide), not at the correction model itself.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.audio_position_locator import (
    DEFAULT_ANCHOR_SECONDS,
    DEFAULT_SEARCH_WINDOW_SECONDS,
    locate_slide_start_times,
)
from src.pptx_parser import extract_notes
from src.subtitle_pipeline import DEFAULT_SLIDE_DURATION_SECONDS


def _fit_scale(measured: list, observed: list) -> float:
    """Least-squares fit of ``observed ~= k * measured``, forced through
    the origin - the same regression form used to derive the original
    1.00121 value (see module docstring). Closed-form solution for a single
    coefficient with no intercept: k = sum(m*o) / sum(m*m).
    """
    numerator = sum(m * o for m, o in zip(measured, observed))
    denominator = sum(m * m for m in measured)
    if denominator == 0:
        raise ValueError("all measured times are zero - can't fit a scale correction from this data")
    return numerator / denominator


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--video", required=True, type=Path, help="The exported MP4 (ppt_automation.export_video()'s output)")
    parser.add_argument("--manifest", required=True, type=Path, help="Path to manifest.json (from --generate-audio)")
    parser.add_argument("--audio-dir", type=Path, default=None)
    slide_source = parser.add_mutually_exclusive_group(required=True)
    slide_source.add_argument("--slides-json", type=Path)
    slide_source.add_argument("--pptx", type=Path)
    parser.add_argument(
        "--observations", required=True, type=Path,
        help="JSON file mapping slide number -> real, precisely-measured playback time in seconds (see module docstring)",
    )
    parser.add_argument("--default-slide-duration", type=float, default=DEFAULT_SLIDE_DURATION_SECONDS)
    parser.add_argument("--search-window-seconds", type=float, default=DEFAULT_SEARCH_WINDOW_SECONDS)
    parser.add_argument("--anchor-seconds", type=float, default=DEFAULT_ANCHOR_SECONDS)
    parser.add_argument("--report", type=Path, default=None, help="Optional path to write a JSON report of the fit (per-slide rows + suggested value)")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    audio_dir = args.audio_dir or Path(manifest.get("output_dir") or args.manifest.parent)

    if args.slides_json:
        payload = json.loads(args.slides_json.read_text(encoding="utf-8"))
        slides = payload.get("slides", payload) if isinstance(payload, dict) else payload
    else:
        slides = extract_notes(str(args.pptx))

    raw_observations = json.loads(args.observations.read_text(encoding="utf-8"))
    observed_by_slide = {int(k): float(v) for k, v in raw_observations.items()}
    if not observed_by_slide:
        print("No observations found in --observations file - nothing to fit.")
        sys.exit(1)

    print(f"Measuring uncorrected (global_scale_correction=1.0) slide start times in {args.video} ...")
    # Always measured with global_scale_correction=1.0 - we are deriving that
    # very value, not applying an existing one. This also means this script
    # walks the whole deck (needed so each slide's search window is centered
    # near the right place, same as dump_slide_bounds.py), even though only
    # the slides mentioned in --observations end up being used for the fit.
    measured_starts, warnings = locate_slide_start_times(
        args.video, slides, manifest, audio_dir,
        default_slide_duration=args.default_slide_duration,
        search_window_seconds=args.search_window_seconds,
        anchor_seconds=args.anchor_seconds,
        global_scale_correction=1.0,
    )
    for w in warnings:
        print(f"WARNING: {w}")

    rows = []
    missing = []
    for slide_num, observed in sorted(observed_by_slide.items()):
        measured = measured_starts.get(slide_num)
        if measured is None:
            missing.append(slide_num)
            continue
        rows.append({"slide_num": slide_num, "measured": measured, "observed": observed})

    if missing:
        print(
            f"WARNING: no measurement available for slide(s) {missing} (silent slide, or its audio "
            "could not be loaded) - excluded from the fit. Check --observations against the deck's "
            "actual narrated slides."
        )
    if len(rows) < 2:
        print(
            f"Only {len(rows)} usable observation(s) after excluding missing slides - need at least "
            "2 spread across the deck to fit a meaningful correction. Add more entries to --observations."
        )
        sys.exit(1)

    measured_list = [r["measured"] for r in rows]
    observed_list = [r["observed"] for r in rows]
    k = _fit_scale(measured_list, observed_list)

    residuals = []
    for r in rows:
        corrected = r["measured"] * k
        residual = corrected - r["observed"]
        r["corrected"] = corrected
        r["residual"] = residual
        residuals.append(residual)

    rms = (sum(r * r for r in residuals) / len(residuals)) ** 0.5
    max_abs = max(abs(r) for r in residuals)

    print()
    print(f"Fitted from {len(rows)} observation(s) spanning slides {rows[0]['slide_num']}-{rows[-1]['slide_num']}:")
    print(f"{'slide':>6}  {'measured':>10}  {'observed':>10}  {'corrected':>10}  {'residual':>9}")
    for r in rows:
        print(
            f"{r['slide_num']:>6}  {r['measured']:>10.3f}  {r['observed']:>10.3f}  "
            f"{r['corrected']:>10.3f}  {r['residual']:>+9.3f}"
        )
    print()
    print(f"Suggested --global-scale-correction: {k:.6f}")
    print(f"RMS residual after correction: {rms:.3f}s   Max residual: {max_abs:.3f}s")
    if rms > 1.0 or max_abs > 2.0:
        print(
            "\nNOTE: this residual is noticeably larger than what the original calibration achieved "
            "(RMS 0.27s / max 0.53s over a 2h40m deck). A single proportional constant may not be "
            "cleanly explaining this deck's drift - check the per-slide residuals above for one or "
            "two outliers before trusting the suggested value; see this script's module docstring "
            "('Residual too large')."
        )

    if args.report:
        report = {
            "params": {
                "default_slide_duration": args.default_slide_duration,
                "search_window_seconds": args.search_window_seconds,
                "anchor_seconds": args.anchor_seconds,
            },
            "warnings": warnings,
            "missing_slides": missing,
            "rows": rows,
            "suggested_global_scale_correction": k,
            "rms_residual_seconds": rms,
            "max_residual_seconds": max_abs,
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWrote {args.report}")


if __name__ == "__main__":
    main()
