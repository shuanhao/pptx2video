"""Phase 2D Experiment 4 - Offline Pareto Simulation (score vs. segment count).

STANDALONE ANALYSIS TOOL. NOT part of the production pipeline, NOT imported
by any production module, NOT a new Phase 2D architecture. See
`docs/phase2d/PHASE_2D_EXPERIMENT_4_PARETO_REPORT.md` for the full write-up
of what this script produced and how to interpret it.

WHAT THIS SCRIPT DOES
----------------------------------------------------------------------------
For every non-blank paragraph in the real 39-file `examples/notes/` corpus,
it answers one empirical question:

    "For each feasible exact segment count K (starting at the existing
    Phase 2D width-only minimum K_min, up to the largest K the paragraph's
    candidate anchors structurally allow), what is the highest total
    Phase 2C boundary score achievable by any width-respecting K-segment
    partition of that paragraph?"

This is a direct *generalization* of the exact DP already used in
`src/boundary_segmentation.py::_select_cut_positions` - that function only
ever solves this problem for one fixed K (`target_k = K_min`). This script
reuses that same feasibility rule, the same score/tie-break objective, and
the same underlying helper functions (`_fits`, `_display_width`,
`_greedy_min_k_boundaries`, `_internal_positions`, `_split_paragraphs`) -
all imported directly from `src.boundary_segmentation`, never re-derived -
and sweeps K across its full structurally-possible range instead of
stopping at one value.

WHAT THIS SCRIPT DELIBERATELY DOES NOT DO
----------------------------------------------------------------------------
- It does not modify, wrap, or monkeypatch `src.boundary_segmentation`,
  `src.boundary_segmentation_adapter`, or any Phase 1-2C module. Every
  `WeightedBoundary` consumed here comes from an unmodified call to
  `boundary_segmentation_adapter._weighted_boundaries_for_text()`.
- It does not choose a segment-count penalty, a score threshold, or any
  policy rule for "which K is correct." It reports the empirical
  score-vs-K curve only.
- It does not reinterpret Phase 2C scores as probabilities, confidence
  values, or absolute utilities. A score is only ever compared to another
  score produced by the same formula (see
  `docs/phase2c/decisions/PHASE_2C_NUMERIC_BASELINE_DECISION.md` section 6).
- It does not use production segmentation (`subtitle_segmenter.py`) as an
  optimization target. Production counts are recorded for reference only.
- It does not silently narrow the K range explored. `K_max` is the true
  structural maximum (every candidate anchor used as a cut) for every
  paragraph, not an arbitrary small cap.

ALGORITHM
----------------------------------------------------------------------------
Per paragraph, with `anchors = [p_start] + internal_candidate_positions +
[p_end]` (length `n`):

    K_min  = len(_greedy_min_k_boundaries(anchors, ...)) - 1   (unmodified,
             width-only, exactly what production Phase 2D uses today)
    K_max  = n - 1                                              (every anchor
             used as a cut - the largest number of segments the candidate
             structure can produce)

For every K in [1, K_max], a single layered DP computes the maximum
achievable total score of a K-segment, width-feasible (or, at the finest
granularity, last-resort-feasible - identical rule to the frozen
`_select_cut_positions`) partition, together with the tie-break (lowest
sum of squared segment widths) and the reconstructed cut positions. This
is the same recurrence as `_select_cut_positions`, just filled for every K
instead of one.

INTEGRITY CROSS-CHECK
----------------------------------------------------------------------------
For every paragraph, this script also calls the real, frozen
`_select_cut_positions()` directly at K = K_min and asserts the result
(cut positions) is byte-identical to this script's own DP result at
K = K_min. This is not a design choice; it is a verification step confirming
this script's generalized DP is a faithful superset of the exact algorithm
already running in production-adjacent code, not an independent
reimplementation that could silently drift from it. Any mismatch is
recorded and surfaced (none expected).
"""

from __future__ import annotations

import glob
import json
import os
import statistics
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from src.boundary_segmentation import (  # noqa: E402
    _display_width,
    _fits,
    _greedy_min_k_boundaries,
    _internal_positions,
    _select_cut_positions,
    _split_paragraphs,
    segment_boundaries,
)
from src.boundary_segmentation_adapter import _weighted_boundaries_for_text  # noqa: E402
from src.subtitle_segmenter import segment_notes_for_subtitles  # noqa: E402

CORPUS_DIR = os.path.join(_REPO_ROOT, "examples", "notes")
MAX_DISPLAY_WIDTH = 18  # authoritative width for this corpus, per task spec

OUTPUT_JSON = os.path.join(_REPO_ROOT, "reports", "phase2d", "phase2d_pareto_results.json")
OUTPUT_SUMMARY = os.path.join(_REPO_ROOT, "reports", "phase2d", "phase2d_pareto_summary.txt")


# ---------------------------------------------------------------------------
# Per-paragraph Pareto DP (generalizes _select_cut_positions across all K)
# ---------------------------------------------------------------------------


def _paragraph_pareto(
    p_start: int,
    p_end: int,
    positions: List[int],
    score_map: Dict[int, float],
    source_text: str,
    max_width: int,
) -> Dict[str, Any]:
    anchors = [p_start] + list(positions) + [p_end]
    n = len(anchors)

    greedy_boundaries = _greedy_min_k_boundaries(anchors, source_text, max_width)
    k_min = len(greedy_boundaries) - 1
    k_max = n - 1  # every anchor used as a cut: the structural maximum

    # Precompute feasibility / segment score / squared width for every
    # (i, j) pair, i < j - identical rule to _select_cut_positions.feasible()
    # and its segment_score()/segment_sq_width() helpers.
    feasible: List[List[bool]] = [[False] * n for _ in range(n)]
    seg_score: List[List[float]] = [[0.0] * n for _ in range(n)]
    seg_sqw: List[List[int]] = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            ok = (j == i + 1) or _fits(source_text, anchors[i], anchors[j], max_width)
            feasible[i][j] = ok
            if ok:
                width = _display_width(source_text[anchors[i] : anchors[j]])
                seg_sqw[i][j] = width * width
                seg_score[i][j] = 0.0 if j == n - 1 else score_map.get(anchors[j], 0.0)

    # dp[k][i] = (best total score, tie-break sum-of-squared-widths) for
    # partitioning anchors[0..i] into exactly k segments ending at anchors[i].
    dp: List[List[Optional[Tuple[float, int]]]] = [[None] * n for _ in range(k_max + 1)]
    choice: List[List[Optional[int]]] = [[None] * n for _ in range(k_max + 1)]
    dp[0][0] = (0.0, 0)

    for k in range(1, k_max + 1):
        dp_k = dp[k]
        choice_k = choice[k]
        dp_prev = dp[k - 1]
        for i in range(k, n):
            best: Optional[Tuple[float, int]] = None
            best_j: Optional[int] = None
            row_feasible = None
            for j in range(k - 1, i):
                prev = dp_prev[j]
                if prev is None or not feasible[j][i]:
                    continue
                cand_score = prev[0] + seg_score[j][i]
                cand_sqw = prev[1] + seg_sqw[j][i]
                if best is None or cand_score > best[0] or (cand_score == best[0] and cand_sqw < best[1]):
                    best = (cand_score, cand_sqw)
                    best_j = j
            dp_k[i] = best
            choice_k[i] = best_j

    per_k: Dict[int, Dict[str, Any]] = {}
    for k in range(1, k_max + 1):
        result = dp[k][n - 1]
        if result is None:
            per_k[k] = {"feasible": False}
            continue
        cuts: List[int] = []
        i, kk = n - 1, k
        while kk > 0:
            cuts.append(anchors[i])
            j = choice[kk][i]
            assert j is not None
            i, kk = j, kk - 1
        cuts.append(anchors[0])
        cuts.reverse()
        internal_cuts = cuts[1:-1]
        widths = [_display_width(source_text[a:b]) for a, b in zip(cuts, cuts[1:])]
        boundary_scores = [score_map.get(p, 0.0) for p in internal_cuts]
        per_k[k] = {
            "feasible": True,
            "total_score": result[0],
            "sum_sq_width": result[1],
            "cut_positions": cuts,
            "internal_cut_positions": internal_cuts,
            "segment_widths": widths,
            "boundary_scores": boundary_scores,
        }

    # Integrity cross-check: the real, frozen _select_cut_positions() at
    # K = K_min must reproduce this DP's own K_min result exactly.
    real_cuts = list(_select_cut_positions(p_start, p_end, positions, score_map, source_text, max_width))
    dp_k_min_cuts = per_k[k_min]["cut_positions"] if per_k.get(k_min, {}).get("feasible") else list(greedy_boundaries)
    option_a_matches_dp = real_cuts == dp_k_min_cuts

    # Pareto frontier: point (K, score) is dominated if another feasible
    # point has score >= it AND K <= it, with at least one strict.
    feasible_points = [(k, per_k[k]["total_score"]) for k in range(1, k_max + 1) if per_k[k]["feasible"]]
    frontier = []
    for k, score in feasible_points:
        dominated = False
        for k2, score2 in feasible_points:
            if (k2, score2) == (k, score):
                continue
            if score2 >= score and k2 <= k and (score2 > score or k2 < k):
                dominated = True
                break
        if not dominated:
            frontier.append((k, score))
    frontier.sort()

    return {
        "k_min": k_min,
        "k_max": k_max,
        "anchors_count": n,
        "per_k": per_k,
        "option_a_selected_k": k_min,
        "option_a_total_score": per_k[k_min]["total_score"] if per_k.get(k_min, {}).get("feasible") else 0.0,
        "option_a_matches_frozen_algorithm": option_a_matches_dp,
        "pareto_frontier": frontier,
    }


# ---------------------------------------------------------------------------
# Corpus driver
# ---------------------------------------------------------------------------


def _run() -> Dict[str, Any]:
    files = sorted(glob.glob(os.path.join(CORPUS_DIR, "*.txt")))
    if not files:
        raise SystemExit(f"STOP CONDITION: no corpus files found under {CORPUS_DIR}")

    paragraph_records: List[Dict[str, Any]] = []
    mismatches: List[Dict[str, Any]] = []

    production_total = 0
    phase2d_total = 0

    t0 = time.time()
    for fp in files:
        rel = os.path.relpath(fp, _REPO_ROOT)
        source_text = open(fp, encoding="utf-8").read()

        weighted_boundaries = _weighted_boundaries_for_text(source_text)
        score_map = {wb.candidate.position: wb.score for wb in weighted_boundaries}
        sorted_positions = sorted(score_map.keys())

        # Reference-only counts (NOT an optimization target - see module
        # docstring and the Experiment 4 report's "Production Comparison"
        # section).
        production_segments = segment_notes_for_subtitles(source_text, max_display_width=MAX_DISPLAY_WIDTH)
        phase2d_segments = segment_boundaries(weighted_boundaries, source_text, max_display_width=MAX_DISPLAY_WIDTH)
        production_total += len(production_segments)
        phase2d_total += len(phase2d_segments)

        paragraphs = _split_paragraphs(source_text)
        for p_idx, (p_start, p_end) in enumerate(paragraphs):
            positions = _internal_positions(p_start, p_end, sorted_positions)
            pareto = _paragraph_pareto(p_start, p_end, positions, score_map, source_text, MAX_DISPLAY_WIDTH)
            record = {
                "source_file": rel,
                "paragraph_index": p_idx,
                "paragraph_start_offset": p_start,
                "paragraph_end_offset": p_end,
                "paragraph_char_length": p_end - p_start,
                **pareto,
            }
            paragraph_records.append(record)
            if not pareto["option_a_matches_frozen_algorithm"]:
                mismatches.append({"source_file": rel, "paragraph_index": p_idx})

    elapsed = time.time() - t0

    return {
        "files": files,
        "paragraph_records": paragraph_records,
        "mismatches": mismatches,
        "production_total_segments": production_total,
        "phase2d_total_segments": phase2d_total,
        "elapsed_seconds": elapsed,
    }


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _median(xs: List[float]) -> Optional[float]:
    return statistics.median(xs) if xs else None


def _mean(xs: List[float]) -> Optional[float]:
    return statistics.mean(xs) if xs else None


def _aggregate(run: Dict[str, Any]) -> Dict[str, Any]:
    records = run["paragraph_records"]

    n_files = len(run["files"])
    n_paragraphs = len(records)
    n_k_gt_1 = sum(1 for r in records if r["k_min"] > 1)

    k_min_hist: Dict[int, int] = {}
    k_max_hist: Dict[int, int] = {}
    for r in records:
        k_min_hist[r["k_min"]] = k_min_hist.get(r["k_min"], 0) + 1
        k_max_hist[r["k_max"]] = k_max_hist.get(r["k_max"], 0) + 1

    total_feasible_points = sum(
        1 for r in records for k in range(1, r["k_max"] + 1) if r["per_k"][k]["feasible"]
    )

    # Score distribution: at Option A (K_min), and across all feasible points.
    option_a_scores = [r["option_a_total_score"] for r in records]
    all_feasible_scores = [
        r["per_k"][k]["total_score"] for r in records for k in range(1, r["k_max"] + 1) if r["per_k"][k]["feasible"]
    ]

    # Step-indexed marginal gain: step i = K_min+i-1 -> K_min+i.
    step_gains: Dict[int, List[float]] = {}
    all_marginal_gains: List[float] = []
    n_step1_positive = 0
    n_step1_zero = 0
    n_step1_examined = 0
    n_no_gain_anywhere = 0
    max_single_gain = float("-inf")
    max_single_gain_loc = None
    max_observed_k = 0

    for r in records:
        k_min = r["k_min"]
        k_max = r["k_max"]
        max_observed_k = max(max_observed_k, k_max)
        base_score = r["per_k"][k_min]["total_score"] if r["per_k"][k_min]["feasible"] else 0.0
        best_score_anywhere = base_score
        prev_score = base_score
        step = 0
        for k in range(k_min + 1, k_max + 1):
            entry = r["per_k"][k]
            if not entry["feasible"]:
                continue
            step += 1
            gain = entry["total_score"] - prev_score
            step_gains.setdefault(step, []).append(gain)
            all_marginal_gains.append(gain)
            if step == 1:
                n_step1_examined += 1
                if gain > 0:
                    n_step1_positive += 1
                elif gain == 0:
                    n_step1_zero += 1
            if gain > max_single_gain:
                max_single_gain = gain
                max_single_gain_loc = {
                    "source_file": r["source_file"],
                    "paragraph_index": r["paragraph_index"],
                    "K": k,
                    "gain": gain,
                }
            best_score_anywhere = max(best_score_anywhere, entry["total_score"])
            prev_score = entry["total_score"]
        if best_score_anywhere <= base_score:
            n_no_gain_anywhere += 1

    step_summary = {
        step: {
            "n": len(gains),
            "mean": _mean(gains),
            "median": _median(gains),
            "min": min(gains) if gains else None,
            "max": max(gains) if gains else None,
        }
        for step, gains in sorted(step_gains.items())
    }

    marginal_gain_hist: Dict[str, int] = {}
    for g in all_marginal_gains:
        key = f"{g:g}"
        marginal_gain_hist[key] = marginal_gain_hist.get(key, 0) + 1

    # Pareto frontier stats.
    frontier_sizes = [len(r["pareto_frontier"]) for r in records]
    frontier_max_k = [max((k for k, _ in r["pareto_frontier"]), default=r["k_min"]) for r in records]

    # Protection-penalty presence among Option-A selected cuts.
    n_option_a_cuts_with_negative_score = 0
    n_option_a_cuts_total = 0
    for r in records:
        entry = r["per_k"][r["k_min"]]
        if not entry["feasible"]:
            continue
        for s in entry["boundary_scores"]:
            n_option_a_cuts_total += 1
            if s < 0:
                n_option_a_cuts_with_negative_score += 1

    return {
        "n_files": n_files,
        "n_paragraphs": n_paragraphs,
        "n_paragraphs_k_min_gt_1": n_k_gt_1,
        "k_min_distribution": dict(sorted(k_min_hist.items())),
        "k_max_distribution": dict(sorted(k_max_hist.items())),
        "total_feasible_paragraph_k_points": total_feasible_points,
        "option_a_score_distribution": {
            "n": len(option_a_scores),
            "mean": _mean(option_a_scores),
            "median": _median(option_a_scores),
            "min": min(option_a_scores) if option_a_scores else None,
            "max": max(option_a_scores) if option_a_scores else None,
        },
        "all_feasible_points_score_distribution": {
            "n": len(all_feasible_scores),
            "mean": _mean(all_feasible_scores),
            "median": _median(all_feasible_scores),
            "min": min(all_feasible_scores) if all_feasible_scores else None,
            "max": max(all_feasible_scores) if all_feasible_scores else None,
        },
        "step_gain_summary": step_summary,
        "marginal_gain_histogram": dict(sorted(marginal_gain_hist.items(), key=lambda kv: float(kv[0]))),
        "n_paragraphs_step1_examined": n_step1_examined,
        "n_paragraphs_score_increases_at_k_min_plus_1": n_step1_positive,
        "n_paragraphs_score_unchanged_at_k_min_plus_1": n_step1_zero,
        "n_paragraphs_no_gain_anywhere_above_k_min": n_no_gain_anywhere,
        "max_observed_k": max_observed_k,
        "max_single_step_gain": None if max_single_gain == float("-inf") else max_single_gain,
        "max_single_step_gain_location": max_single_gain_loc,
        "pareto_frontier_size_distribution": {
            "n": len(frontier_sizes),
            "mean": _mean(frontier_sizes),
            "median": _median(frontier_sizes),
            "min": min(frontier_sizes) if frontier_sizes else None,
            "max": max(frontier_sizes) if frontier_sizes else None,
        },
        "pareto_frontier_max_k_distribution": {
            "mean": _mean(frontier_max_k),
            "median": _median(frontier_max_k),
            "max": max(frontier_max_k) if frontier_max_k else None,
        },
        "option_a_selected_cuts_total": n_option_a_cuts_total,
        "option_a_selected_cuts_with_negative_score": n_option_a_cuts_with_negative_score,
        "production_total_segments_reference_only": run["production_total_segments"],
        "phase2d_total_segments_reference_only": run["phase2d_total_segments"],
        "integrity_mismatches": run["mismatches"],
        "elapsed_seconds": run["elapsed_seconds"],
    }


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------


def _write_json(run: Dict[str, Any], agg: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    payload = {
        "meta": {
            "corpus_dir": os.path.relpath(CORPUS_DIR, _REPO_ROOT),
            "max_display_width": MAX_DISPLAY_WIDTH,
            "n_files": agg["n_files"],
            "n_paragraphs": agg["n_paragraphs"],
        },
        "aggregate": agg,
        "paragraphs": [
            {
                "source_file": r["source_file"],
                "paragraph_index": r["paragraph_index"],
                "paragraph_start_offset": r["paragraph_start_offset"],
                "paragraph_end_offset": r["paragraph_end_offset"],
                "paragraph_char_length": r["paragraph_char_length"],
                "k_min": r["k_min"],
                "k_max": r["k_max"],
                "option_a_selected_k": r["option_a_selected_k"],
                "option_a_total_score": r["option_a_total_score"],
                "option_a_matches_frozen_algorithm": r["option_a_matches_frozen_algorithm"],
                "pareto_frontier": r["pareto_frontier"],
                "per_k": r["per_k"],
            }
            for r in run["paragraph_records"]
        ],
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)


def _write_summary(agg: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(OUTPUT_SUMMARY), exist_ok=True)
    lines: List[str] = []
    lines.append("PHASE 2D EXPERIMENT 4 - PARETO SIMULATION - CORPUS SUMMARY")
    lines.append("=" * 76)
    lines.append(f"Files: {agg['n_files']}")
    lines.append(f"Paragraphs: {agg['n_paragraphs']}")
    lines.append(f"Paragraphs with K_min > 1: {agg['n_paragraphs_k_min_gt_1']}")
    lines.append(f"Total feasible (paragraph, K) points: {agg['total_feasible_paragraph_k_points']}")
    lines.append(f"Max observed K (any paragraph): {agg['max_observed_k']}")
    lines.append("")
    lines.append("K_min distribution (K_min -> paragraph count):")
    for k, c in agg["k_min_distribution"].items():
        lines.append(f"  {k}: {c}")
    lines.append("")
    lines.append("K_max distribution (K_max -> paragraph count):")
    for k, c in agg["k_max_distribution"].items():
        lines.append(f"  {k}: {c}")
    lines.append("")
    lines.append("Option-A (current Phase 2D, K=K_min) total-score distribution:")
    lines.append(f"  {agg['option_a_score_distribution']}")
    lines.append("")
    lines.append("All feasible (paragraph, K) points - total-score distribution:")
    lines.append(f"  {agg['all_feasible_points_score_distribution']}")
    lines.append("")
    lines.append("Step-indexed score gain (step i = (K_min+i-1) -> (K_min+i)):")
    for step, s in agg["step_gain_summary"].items():
        lines.append(f"  step {step}: n={s['n']} mean={s['mean']:.3f} median={s['median']:.3f} min={s['min']:.3f} max={s['max']:.3f}")
    lines.append("")
    lines.append(f"Paragraphs where step-1 (K_min -> K_min+1) was examined: {agg['n_paragraphs_step1_examined']}")
    lines.append(f"  score increases: {agg['n_paragraphs_score_increases_at_k_min_plus_1']}")
    lines.append(f"  score unchanged: {agg['n_paragraphs_score_unchanged_at_k_min_plus_1']}")
    lines.append(f"Paragraphs where NO K above K_min ever beats K_min's score: {agg['n_paragraphs_no_gain_anywhere_above_k_min']}")
    lines.append("")
    lines.append(f"Max single-step marginal gain observed: {agg['max_single_step_gain']}")
    lines.append(f"  at: {agg['max_single_step_gain_location']}")
    lines.append("")
    lines.append("Marginal gain histogram (Δscore(K) value -> occurrence count):")
    for val, c in agg["marginal_gain_histogram"].items():
        lines.append(f"  {val}: {c}")
    lines.append("")
    lines.append("Pareto frontier size distribution (per paragraph):")
    lines.append(f"  {agg['pareto_frontier_size_distribution']}")
    lines.append("Pareto frontier max-K distribution (per paragraph):")
    lines.append(f"  {agg['pareto_frontier_max_k_distribution']}")
    lines.append("")
    lines.append(f"Option-A selected cuts total: {agg['option_a_selected_cuts_total']}")
    lines.append(f"Option-A selected cuts carrying a negative (protection) score: {agg['option_a_selected_cuts_with_negative_score']}")
    lines.append("")
    lines.append("Reference only (NOT an optimization target):")
    lines.append(f"  Production total segments: {agg['production_total_segments_reference_only']}")
    lines.append(f"  Current Phase 2D (Option A) total segments: {agg['phase2d_total_segments_reference_only']}")
    lines.append("")
    lines.append(f"Integrity cross-check mismatches (Option-A DP vs frozen _select_cut_positions): {len(agg['integrity_mismatches'])}")
    if agg["integrity_mismatches"]:
        lines.append(f"  {agg['integrity_mismatches']}")
    lines.append(f"Elapsed: {agg['elapsed_seconds']:.1f}s")
    with open(OUTPUT_SUMMARY, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main() -> None:
    run = _run()
    agg = _aggregate(run)
    _write_json(run, agg)
    _write_summary(agg)
    print(f"Wrote {OUTPUT_JSON}")
    print(f"Wrote {OUTPUT_SUMMARY}")
    print(f"Integrity mismatches: {len(agg['integrity_mismatches'])}")
    print(f"Elapsed: {agg['elapsed_seconds']:.1f}s")


if __name__ == "__main__":
    main()
