"""Phase 2D Experiment 5A - Corpus Sampling & Blinded Evaluation Package.

STANDALONE EXPERIMENT-INFRASTRUCTURE TOOL. NOT part of the production
pipeline, NOT a Phase 2D algorithm change, NOT a human-rating collection or
analysis tool. See `docs/phase2d/PHASE_2D_EXPERIMENT_5_HUMAN_READABILITY_DESIGN.md`
for the full experimental design this script implements the sampling half
of.

WHAT THIS SCRIPT DOES
----------------------------------------------------------------------------
Consumes the already-produced, frozen Experiment 4 artifact
(`reports/phase2d/phase2d_pareto_results.json`) and the original real
corpus (`examples/notes/*.txt`) to deterministically select a stratified
sample of paragraphs, pick one Pareto-frontier alternative segmentation per
sampled item (per the rules in the Experiment 5 design document, section
14), render both the `K_min` segmentation and the chosen alternative from
the *raw* source text, blind the pair (hide which one is `K_min`), and
write a machine-readable evaluation package plus a human-readable preview.

WHAT THIS SCRIPT DELIBERATELY DOES NOT DO
----------------------------------------------------------------------------
- It does not call `boundary_segmentation_adapter._weighted_boundaries_for_text()`,
  `boundary_segmentation.segment_boundaries()`, or any part of the Phase
  1->2C->2D chain. Every score, `K` value, and cut position used here is
  read verbatim from Experiment 4's already-computed
  `phase2d_pareto_results.json` - this script is strictly downstream of
  Experiment 4, never a second computation of it.
- It does not call `subtitle_segmenter.segment_notes_for_subtitles()` or
  any production segmentation function. Production segmentation is not a
  condition in this experiment at all (see the Experiment 5 design
  document's "Design Correction #1": the comparison is `K_min` vs. a
  Pareto alternative, never production vs. Phase 2D).
- It does not apply any new text-normalization rule. Displayed segment
  text is the raw `source_text[start:end]` slice - the same raw-slice
  convention `boundary_segmentation.py` itself uses internally - with no
  whitespace stripping, punctuation stripping, or other cleanup.
- It does not hard-code `MIN_EVALUATION_SEGMENT_WIDTH = 4` (or any other
  value) as a Phase 2D or production rule. It is a local constant of this
  sampling script only, used exclusively to decide which candidates enter
  the *primary* blinded sample; excluded candidates are preserved and
  counted, never silently discarded (see `CandidateMetadata` and
  `sampling_summary.txt`).
- It does not collect human ratings, compute correlation, compute
  agreement, or draw any conclusion about readability, Variable-K, or
  Phase 2D's correctness. That is explicitly out of scope for Experiment
  5A (Experiment 5B).
- It is deterministic given `(results_json, corpus_dir, seed,
  items_per_stratum, min_segment_width, boundary_condition_count)`: running
  it twice with identical inputs produces byte-identical output files
  (aside from the informational, non-deterministic `generated_at`
  timestamp recorded only in `checksums.json`).

ALGORITHM OVERVIEW (see the Experiment 5 design document for the full
rationale; this is the operational summary)
----------------------------------------------------------------------------
1. Load and structurally validate `phase2d_pareto_results.json` and the 39
   corpus files (section "STOP CONDITIONS" below).
2. For every paragraph, compute paragraph-level metadata: frontier size,
   the best-scoring frontier alternative (if any), whether the paragraph's
   full score-vs-K curve is non-monotonic anywhere above `K_min`, and
   width statistics for `K_min`'s segmentation.
3. Stratum A ("Control" - `pareto_frontier` has exactly one point, `K_min`
   itself) paragraphs have no Pareto alternative to compare against by
   construction and therefore do not produce evaluation items - they are
   counted and reported, never forced into a fabricated comparison (this
   is a direct consequence of the Pareto-frontier definition, not an
   improvised STOP-condition workaround: a paragraph with frontier size 1
   has no `K > K_min` frontier point to select at all).
4. For strata B/C/D (gain-size) and G (non-monotonic), the alternative is
   the paragraph's best-scoring qualifying frontier point (highest score,
   ties broken by smallest `K`).
5. For stratum E (`ΔK` targeting), the alternative is `K_min + delta` if
   that value is itself a frontier point; otherwise the smallest frontier
   `K > K_min` is substituted and `alternative_k_substituted=true` is
   recorded (design document section 14, reproduced literally here).
6. For stratum F (frontier shape), the alternative is the paragraph's sole
   non-`K_min` frontier point (frontier size 2) or a seeded-random
   qualifying frontier point (frontier size > 2).
7. For stratum H (material boundary-placement change), the alternative is
   the smallest-`K` qualifying frontier point whose cut-position symmetric
   difference with `K_min` includes at least one position scored >= 35.0
   (`CLAUSE`/`SENTENCE_FINAL`-class evidence, per the design document).
8. Every selection is filtered by the width-quality gate
   (`min_segment_width`, default 4) applied to *both* the `K_min` and the
   alternative segmentation, unless the item is explicitly drawn into the
   separate, clearly-labeled `boundary_condition_candidate` set.
9. Items selected by different stratum procedures for the exact same
   `(source_file, paragraph_index, alternative_k)` triple are merged into
   one item carrying the union of stratum labels (never duplicated).
10. Stable IDs are assigned in sorted `(source_file, paragraph_index,
    alternative_k)` order. Display order (`K_min` first or alternative
    first) is assigned deterministically from a seed derived from the
    sampling seed, independent of the sampling draws themselves.
11. Every item is integrity-checked (offsets valid, `K_min`/alternative
    both exist and are frontier-consistent, reconstructed segments
    concatenate back to the exact paragraph text) before being written.
    Any failure aborts the run with a specific, actionable message - no
    silent repair.
12. Three JSON artifacts are written with progressively less information:
    `sample_manifest.json` (the full hidden mapping and all algorithmic
    metadata - never shown to evaluators), `evaluation_items.json` (the
    complete, non-blinded item records, for internal/researcher use), and
    `evaluation_items_blinded.json` (evaluator-facing only: item id,
    source text, and the two segmentations under neutral labels). A
    post-generation scan asserts the blinded artifact (and the optional
    HTML rendering) contain none of a fixed list of forbidden tokens
    (`k_min`, `score`, `stratum`, `frontier`, ...).
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import itertools
import json
import os
import random
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

DEFAULT_RESULTS_JSON = os.path.join(_REPO_ROOT, "reports", "phase2d", "phase2d_pareto_results.json")
DEFAULT_SUMMARY_TXT = os.path.join(_REPO_ROOT, "reports", "phase2d", "phase2d_pareto_summary.txt")
DEFAULT_CORPUS_DIR = os.path.join(_REPO_ROOT, "examples", "notes")
DEFAULT_OUTPUT_DIR = os.path.join(_REPO_ROOT, "data", "phase2d", "experiment5")
DEFAULT_SEED = 42
DEFAULT_ITEMS_PER_STRATUM = 6
DEFAULT_MIN_SEGMENT_WIDTH = 4
DEFAULT_BOUNDARY_CONDITION_COUNT = 3

#: The "meaningful scored boundary" threshold used only by stratum H
#: (material boundary-placement change), per the design document's
#: CLAUSE/SENTENCE_FINAL-class framing. Local to this sampling script,
#: not a Phase 2C/2D constant.
MATERIAL_BOUNDARY_SCORE_THRESHOLD = 35.0

EXPECTED_CORPUS_FILES = sorted(
    [f"mcu1_slide_{i:02d}.txt" for i in range(1, 22)] + [f"mcu2_slide_{i:02d}.txt" for i in range(1, 19)]
)

#: Evaluator-facing artifacts must never contain any of these tokens
#: (case-insensitive substring match against the serialized JSON/HTML
#: text) - see section 25 of the task and _assert_no_forbidden_tokens().
FORBIDDEN_EVALUATOR_TOKENS = [
    "k_min",
    "alternative_k",
    "phase2d_score",
    "score",
    "delta_score",
    "pareto",
    "frontier",
    "stratum",
    "condition_identity",
    "production",
    "experimental",
    "baseline",
]


class IntegrityError(RuntimeError):
    """Raised when a STOP CONDITION (task section 34) is met. Never caught
    and silently worked around - always propagates to a nonzero exit."""


# ---------------------------------------------------------------------------
# Loading & structural validation
# ---------------------------------------------------------------------------


def load_results(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    for key in ("meta", "aggregate", "paragraphs"):
        if key not in data:
            raise IntegrityError(f"STOP: results JSON missing required top-level key {key!r} in {path}")
    required_paragraph_keys = {
        "source_file",
        "paragraph_index",
        "paragraph_start_offset",
        "paragraph_end_offset",
        "paragraph_char_length",
        "k_min",
        "k_max",
        "pareto_frontier",
        "per_k",
    }
    if data["paragraphs"]:
        missing = required_paragraph_keys - set(data["paragraphs"][0].keys())
        if missing:
            raise IntegrityError(
                f"STOP: results JSON paragraph records missing expected keys {sorted(missing)} - "
                "structure differs from the Experiment 5 design document's assumptions."
            )
    return data


def discover_corpus_files(corpus_dir: str) -> List[str]:
    files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(corpus_dir, "*.txt")))
    if files != EXPECTED_CORPUS_FILES:
        missing = sorted(set(EXPECTED_CORPUS_FILES) - set(files))
        extra = sorted(set(files) - set(EXPECTED_CORPUS_FILES))
        raise IntegrityError(
            "STOP: corpus does not match the expected 39-file set. "
            f"missing={missing} extra={extra}"
        )
    return files


def load_corpus_texts(corpus_dir: str, filenames: Sequence[str]) -> Dict[str, str]:
    texts: Dict[str, str] = {}
    for name in filenames:
        # `record["source_file"]` in the frozen Experiment 4 artifact
        # (phase2d_pareto_results.json) is always POSIX-style
        # ("examples/notes/<name>") - that is the canonical, on-disk data
        # contract this dict's keys must match exactly (see finalize_items
        # below, which looks records up via `corpus_texts.get(source_file)`).
        # os.path.join uses the platform separator, which is "\\" on
        # Windows - joining with it here would silently produce a key
        # ("examples\\notes\\<name>") that never matches the JSON's "/"
        # -separated value, causing every lookup to fail. Join with "/"
        # explicitly so this key is correct on every OS, not just POSIX.
        rel = "/".join(("examples", "notes", name))
        with open(os.path.join(corpus_dir, name), encoding="utf-8") as fh:
            texts[rel] = fh.read()
    return texts


# ---------------------------------------------------------------------------
# Segment text generation (raw slices only - see module docstring)
# ---------------------------------------------------------------------------


def generate_segments(source_text: str, cut_positions: Sequence[int]) -> List[str]:
    return [source_text[a:b] for a, b in zip(cut_positions, cut_positions[1:])]


def width_stats(segment_widths: Sequence[int]) -> Dict[str, float]:
    return {
        "min_segment_width": min(segment_widths),
        "max_segment_width": max(segment_widths),
        "mean_segment_width": sum(segment_widths) / len(segment_widths),
    }


# ---------------------------------------------------------------------------
# Per-paragraph algorithmic metadata (read-only interpretation of
# Experiment 4's own data - no recomputation of any score)
# ---------------------------------------------------------------------------


def _entry(record: Dict[str, Any], k: int) -> Dict[str, Any]:
    e = record["per_k"].get(str(k))
    if e is None or not e.get("feasible"):
        raise IntegrityError(
            f"STOP: per_k[{k}] missing or infeasible for {record['source_file']} "
            f"paragraph {record['paragraph_index']} - cannot select this K."
        )
    return e


def passes_width_filter(record: Dict[str, Any], k_a: int, k_b: int, min_width: int) -> bool:
    wa = _entry(record, k_a)["segment_widths"]
    wb = _entry(record, k_b)["segment_widths"]
    return min(wa) >= min_width and min(wb) >= min_width


def frontier_points_above_k_min(record: Dict[str, Any]) -> List[Tuple[int, float]]:
    k_min = record["k_min"]
    return sorted((k, s) for k, s in record["pareto_frontier"] if k > k_min)


def best_qualifying_alt(record: Dict[str, Any], min_width: int) -> Optional[Tuple[int, float]]:
    k_min = record["k_min"]
    candidates = sorted(frontier_points_above_k_min(record), key=lambda ks: (-ks[1], ks[0]))
    for k, score in candidates:
        if passes_width_filter(record, k_min, k, min_width):
            return k, score
    return None


def best_alt_ignoring_width(record: Dict[str, Any]) -> Optional[Tuple[int, float]]:
    candidates = sorted(frontier_points_above_k_min(record), key=lambda ks: (-ks[1], ks[0]))
    return candidates[0] if candidates else None


def is_non_monotonic(record: Dict[str, Any]) -> bool:
    k_min, k_max = record["k_min"], record["k_max"]
    base = _entry(record, k_min)["total_score"]
    prev = base
    for k in range(k_min + 1, k_max + 1):
        e = record["per_k"].get(str(k))
        if not e or not e.get("feasible"):
            continue
        if e["total_score"] < prev:
            return True
        prev = e["total_score"]
    return False


def material_boundary_change(record: Dict[str, Any], alt_k: int, threshold: float = MATERIAL_BOUNDARY_SCORE_THRESHOLD) -> bool:
    k_min = record["k_min"]
    e_min = _entry(record, k_min)
    e_alt = _entry(record, alt_k)
    cuts_min = set(e_min["internal_cut_positions"])
    cuts_alt = set(e_alt["internal_cut_positions"])
    scores_min = dict(zip(e_min["internal_cut_positions"], e_min["boundary_scores"]))
    scores_alt = dict(zip(e_alt["internal_cut_positions"], e_alt["boundary_scores"]))
    sym_diff = cuts_min ^ cuts_alt
    for p in sym_diff:
        score = scores_min.get(p, scores_alt.get(p))
        if score is not None and abs(score) >= threshold:
            return True
    return False


def select_delta_k_target(record: Dict[str, Any], delta: int, min_width: int) -> Optional[Tuple[int, float, bool]]:
    """Stratum E. `delta` is 1, 2, 3, or 4 (4 means ">= 4" - see caller)."""
    k_min = record["k_min"]
    frontier_map = dict(record["pareto_frontier"])
    target_k = k_min + delta
    substituted = False
    if target_k in frontier_map:
        chosen_k = target_k
    else:
        candidates = sorted(k for k in frontier_map if k > k_min and (delta < 4 or k - k_min >= 4))
        if not candidates:
            return None
        chosen_k = candidates[0]
        substituted = True
    if not passes_width_filter(record, k_min, chosen_k, min_width):
        return None
    return chosen_k, frontier_map[chosen_k], substituted


def _frontier_shape_candidates(record: Dict[str, Any], size_class: str, min_width: int) -> List[int]:
    """Stratum F qualifying alternatives. `size_class` is "2" or "gt2"."""
    frontier = record["pareto_frontier"]
    size = len(frontier)
    if size_class == "2" and size != 2:
        return []
    if size_class == "gt2" and size <= 2:
        return []
    k_min = record["k_min"]
    return sorted(
        k for k, _ in frontier_points_above_k_min(record) if passes_width_filter(record, k_min, k, min_width)
    )


def select_frontier_shape_target(
    record: Dict[str, Any], size_class: str, min_width: int, rng: random.Random
) -> Optional[int]:
    """Stratum F. `size_class` is "2" or "gt2". `rng` must be the shared,
    seeded sampling RNG - deterministic given the caller's fixed processing
    order (see `sample_all`)."""
    candidates = _frontier_shape_candidates(record, size_class, min_width)
    if not candidates:
        return None
    return rng.choice(candidates)


def select_material_change_target(record: Dict[str, Any], min_width: int) -> Optional[int]:
    """Stratum H."""
    k_min = record["k_min"]
    for k, _ in frontier_points_above_k_min(record):
        if not passes_width_filter(record, k_min, k, min_width):
            continue
        if material_boundary_change(record, k):
            return k
    return None


def gain_bucket_label(gain: float) -> str:
    if 10.0 <= gain < 20.0:
        return "B_small_gain"
    if 20.0 <= gain < 70.0:
        return "C_moderate_gain"
    if gain >= 70.0:
        return "D_large_gain"
    return "UNCLASSIFIED_GAIN"  # defensive; not expected given Experiment 4's observed gain floor of 10.0


def delta_k_label(delta_k: int) -> str:
    if delta_k >= 4:
        return "E_delta_k_4plus"
    return f"E_delta_k_{delta_k}"


def frontier_size_label(frontier_size: int) -> str:
    return f"F_frontier_size_{frontier_size}"


# ---------------------------------------------------------------------------
# Candidate item construction
# ---------------------------------------------------------------------------


class CandidateItem:
    """One (paragraph, alternative_k) pairwise-comparison candidate, before
    merging/deduplication and before ID assignment."""

    def __init__(self, record: Dict[str, Any], alt_k: int, alt_score: float, *, substituted: bool = False):
        self.record = record
        self.k_min = record["k_min"]
        self.alt_k = alt_k
        self.alt_score = alt_score
        self.k_min_score = _entry(record, self.k_min)["total_score"]
        self.gain = alt_score - self.k_min_score
        self.delta_k = alt_k - self.k_min
        self.alternative_k_substituted = substituted
        self.key = (record["source_file"], record["paragraph_index"], alt_k)

    def stratum_labels(self, non_monotonic: bool) -> List[str]:
        labels = [gain_bucket_label(self.gain), delta_k_label(self.delta_k), frontier_size_label(len(self.record["pareto_frontier"]))]
        if non_monotonic:
            labels.append("G_non_monotonic")
        if material_boundary_change(self.record, self.alt_k):
            labels.append("H_material_boundary_change")
        return labels


def _sorted_records(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    return sorted(results["paragraphs"], key=lambda r: (r["source_file"], r["paragraph_index"]))


def build_candidate_pools(
    results: Dict[str, Any], min_width: int
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[Tuple[str, int], bool], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Returns:
    - pools: dict of named pools (each a list of paragraph records) used by
      the various stratum sampling procedures.
    - non_monotonic_map: (source_file, paragraph_index) -> bool, computed
      fresh from the results JSON for every paragraph.
    - control_records: stratum-A paragraphs (frontier size 1 - no
      alternative exists; reported, never sampled into items).
    - excluded_records: recoverable paragraphs (frontier size > 1) with no
      frontier point above K_min passing the width filter at all.
    """
    records = _sorted_records(results)
    control_records: List[Dict[str, Any]] = []
    recoverable_records: List[Dict[str, Any]] = []
    excluded_records: List[Dict[str, Any]] = []
    non_monotonic_map: Dict[Tuple[str, int], bool] = {}

    excluded_keys: set = set()
    for r in records:
        key = (r["source_file"], r["paragraph_index"])
        non_monotonic_map[key] = is_non_monotonic(r)
        if len(r["pareto_frontier"]) <= 1:
            control_records.append(r)
            continue
        recoverable_records.append(r)
        if best_qualifying_alt(r, min_width) is None:
            excluded_records.append(r)
            excluded_keys.add(key)

    qualifying_records = [
        r for r in recoverable_records if (r["source_file"], r["paragraph_index"]) not in excluded_keys
    ]

    pools = {
        "recoverable": recoverable_records,
        "qualifying": qualifying_records,
        "non_monotonic": [r for r in recoverable_records if non_monotonic_map[(r["source_file"], r["paragraph_index"])]],
    }
    return pools, non_monotonic_map, control_records, excluded_records


# ---------------------------------------------------------------------------
# Sampling (deterministic, seeded)
# ---------------------------------------------------------------------------


def _draw(rng: random.Random, population: List[Dict[str, Any]], n: int) -> List[Dict[str, Any]]:
    population = sorted(population, key=lambda r: (r["source_file"], r["paragraph_index"]))
    if n >= len(population):
        return list(population)
    return rng.sample(population, n)


def sample_all(
    results: Dict[str, Any],
    *,
    seed: int,
    items_per_stratum: int,
    min_width: int,
    boundary_condition_count: int,
) -> Tuple[List[CandidateItem], Dict[str, Any]]:
    pools, non_monotonic_map, control_records, excluded_records = build_candidate_pools(results, min_width)
    rng = random.Random(seed)

    merged: Dict[Tuple[str, int, int], CandidateItem] = {}
    boundary_condition_items: Dict[Tuple[str, int, int], CandidateItem] = {}
    draw_log: Dict[str, int] = {}

    def add(item: CandidateItem) -> None:
        existing = merged.get(item.key)
        if existing is None:
            merged[item.key] = item
        # If already present, the merge of stratum labels happens later at
        # finalize time (labels are recomputed from (record, alt_k), so an
        # identical key always yields identical labels - no data loss).
        # Note: `alternative_k_substituted` is a property of *how stratum E
        # reached this triple*, not an inherent property of the triple
        # itself; if the same (paragraph, alt_k) is independently reached
        # by a non-E procedure first, the merged item's substituted flag
        # reflects that first arrival rather than E's substitution history.
        # This does not affect which K/score is used - only this one
        # provenance flag - and is documented here rather than reconciled,
        # to keep the merge rule simple and deterministic.

    # --- Core: best-scoring alternative per qualifying recoverable paragraph,
    # stratified post-hoc into B/C/D by its own gain value. ---
    core_candidates = []
    for r in pools["qualifying"]:
        alt = best_qualifying_alt(r, min_width)
        assert alt is not None
        core_candidates.append((r, alt))
    buckets: Dict[str, List[Tuple[Dict[str, Any], Tuple[int, float]]]] = {"B": [], "C": [], "D": []}
    for r, (k, score) in core_candidates:
        gain = score - _entry(r, r["k_min"])["total_score"]
        label = gain_bucket_label(gain)
        if label.startswith("B"):
            buckets["B"].append((r, (k, score)))
        elif label.startswith("C"):
            buckets["C"].append((r, (k, score)))
        elif label.startswith("D"):
            buckets["D"].append((r, (k, score)))
    for name in ("B", "C", "D"):
        pop = [r for r, _ in buckets[name]]
        chosen = _draw(rng, pop, items_per_stratum)
        chosen_keys = {(r["source_file"], r["paragraph_index"]) for r in chosen}
        count = 0
        for r, (k, score) in buckets[name]:
            if (r["source_file"], r["paragraph_index"]) in chosen_keys:
                add(CandidateItem(r, k, score))
                count += 1
        draw_log[f"core_{name}"] = count

    # --- Stratum E: ΔK targeting ---
    for delta, name in ((1, "E_delta_k_1"), (2, "E_delta_k_2"), (3, "E_delta_k_3"), (4, "E_delta_k_4plus")):
        pop = []
        for r in pools["recoverable"]:
            result = select_delta_k_target(r, delta, min_width)
            if result is not None:
                pop.append(r)
        chosen = _draw(rng, pop, items_per_stratum)
        count = 0
        for r in chosen:
            k, score, substituted = select_delta_k_target(r, delta, min_width)
            add(CandidateItem(r, k, score, substituted=substituted))
            count += 1
        draw_log[name] = count

    # --- Stratum F: frontier shape ---
    for size_class, name in (("2", "F_frontier_size_2"), ("gt2", "F_frontier_size_gt2")):
        pop = [r for r in pools["recoverable"] if _frontier_shape_candidates(r, size_class, min_width)]
        chosen = _draw(rng, pop, items_per_stratum)
        count = 0
        for r in chosen:
            k = select_frontier_shape_target(r, size_class, min_width, rng)
            if k is None:
                continue
            score = dict(r["pareto_frontier"])[k]
            add(CandidateItem(r, k, score))
            count += 1
        draw_log[name] = count

    # --- Stratum G: non-monotonic ---
    chosen = _draw(rng, pools["non_monotonic"], items_per_stratum)
    count = 0
    for r in chosen:
        alt = best_qualifying_alt(r, min_width)
        if alt is None:
            continue
        add(CandidateItem(r, alt[0], alt[1]))
        count += 1
    draw_log["G_non_monotonic"] = count

    # --- Stratum H: material boundary-placement change ---
    pop = []
    for r in pools["recoverable"]:
        if select_material_change_target(r, min_width) is not None:
            pop.append(r)
    chosen = _draw(rng, pop, items_per_stratum)
    count = 0
    for r in chosen:
        k = select_material_change_target(r, min_width)
        score = dict(r["pareto_frontier"])[k]
        add(CandidateItem(r, k, score))
        count += 1
    draw_log["H_material_boundary_change"] = count

    # --- Boundary-condition candidates: recoverable paragraphs with NO
    # width-qualifying alternative at all. Best-score alt used regardless
    # of width; explicitly excluded from the primary sample. ---
    chosen = _draw(rng, excluded_records, boundary_condition_count)
    for r in chosen:
        alt = best_alt_ignoring_width(r)
        if alt is None:
            continue
        item = CandidateItem(r, alt[0], alt[1])
        boundary_condition_items[item.key] = item
    draw_log["boundary_condition"] = len(boundary_condition_items)

    summary = {
        "draw_log": draw_log,
        "n_control_paragraphs": len(control_records),
        "n_recoverable_paragraphs": len(pools["recoverable"]),
        "n_qualifying_paragraphs": len(pools["qualifying"]),
        "n_excluded_extreme_narrow_paragraphs": len(excluded_records),
        "n_non_monotonic_paragraphs": len(pools["non_monotonic"]),
        "n_primary_items_merged": len(merged),
        "n_boundary_condition_items": len(boundary_condition_items),
    }
    all_items = list(merged.values()) + list(boundary_condition_items.values())
    boundary_condition_keys = set(boundary_condition_items.keys())
    for item in all_items:
        item.boundary_condition_candidate = item.key in boundary_condition_keys
        item.primary_sample = not item.boundary_condition_candidate
    return all_items, {"non_monotonic_map": non_monotonic_map, **summary}


# ---------------------------------------------------------------------------
# Finalization: IDs, display order, integrity checks, item records
# ---------------------------------------------------------------------------


def finalize_items(
    items: List[CandidateItem],
    corpus_texts: Dict[str, str],
    non_monotonic_map: Dict[Tuple[str, int], bool],
    *,
    seed: int,
    max_items: Optional[int],
) -> List[Dict[str, Any]]:
    items = sorted(items, key=lambda it: it.key)
    if max_items is not None and len(items) > max_items:
        items = items[:max_items]

    display_rng = random.Random(seed + 1)
    records: List[Dict[str, Any]] = []
    for idx, item in enumerate(items, start=1):
        item_id = f"exp5-{idx:04d}"
        record = item.record
        source_file = record["source_file"]
        p_start, p_end = record["paragraph_start_offset"], record["paragraph_end_offset"]
        text = corpus_texts.get(source_file)
        if text is None:
            raise IntegrityError(f"STOP: {source_file} not found among loaded corpus texts for item {item_id}")
        if not (0 <= p_start < p_end <= len(text)):
            raise IntegrityError(f"STOP: invalid paragraph offsets ({p_start}, {p_end}) for {item_id}")
        if p_end - p_start != record["paragraph_char_length"]:
            raise IntegrityError(
                f"STOP: paragraph_char_length mismatch for {item_id}: "
                f"expected {record['paragraph_char_length']}, got {p_end - p_start}"
            )

        e_min = _entry(record, item.k_min)
        e_alt = _entry(record, item.alt_k)

        if item.alt_k <= item.k_min:
            raise IntegrityError(f"STOP: alternative_k ({item.alt_k}) is not > k_min ({item.k_min}) for {item_id}")
        # Every selection procedure above (best_qualifying_alt,
        # best_alt_ignoring_width, select_delta_k_target,
        # select_frontier_shape_target, select_material_change_target)
        # draws exclusively from record["pareto_frontier"] - including for
        # boundary_condition_candidate items (those relax the *width*
        # filter, never frontier membership) - so this check always
        # applies, not only to the primary sample.
        frontier_map = dict(record["pareto_frontier"])
        if item.alt_k not in frontier_map:
            raise IntegrityError(f"STOP: alternative_k {item.alt_k} is not a Pareto frontier point for {item_id}")

        cuts_min = e_min["cut_positions"]
        cuts_alt = e_alt["cut_positions"]
        if cuts_min[0] != p_start or cuts_min[-1] != p_end or cuts_alt[0] != p_start or cuts_alt[-1] != p_end:
            raise IntegrityError(f"STOP: cut_positions do not span the full paragraph for {item_id}")

        segs_min = generate_segments(text, cuts_min)
        segs_alt = generate_segments(text, cuts_alt)
        if "".join(segs_min) != text[p_start:p_end] or "".join(segs_min) != "".join(segs_alt):
            raise IntegrityError(f"STOP: reconstructed segments do not match source paragraph exactly for {item_id}")
        if len(segs_min) != item.k_min or len(segs_alt) != item.alt_k:
            raise IntegrityError(f"STOP: segment count does not match K for {item_id}")

        display_order = "k_min_first" if display_rng.random() < 0.5 else "alternative_first"

        min_widths = width_stats(e_min["segment_widths"])
        alt_widths = width_stats(e_alt["segment_widths"])
        contains_extreme_narrow = min_widths["min_segment_width"] < DEFAULT_MIN_SEGMENT_WIDTH or alt_widths["min_segment_width"] < DEFAULT_MIN_SEGMENT_WIDTH

        strata = sorted(set(item.stratum_labels(non_monotonic_map[(source_file, record["paragraph_index"])])))

        records.append(
            {
                "item_id": item_id,
                "source_file": source_file,
                "paragraph_index": record["paragraph_index"],
                "paragraph_start_offset": p_start,
                "paragraph_end_offset": p_end,
                "source_text": text[p_start:p_end],
                "stratum": strata,
                "k_min": item.k_min,
                "alternative_k": item.alt_k,
                "delta_k": item.delta_k,
                "alternative_k_substituted": item.alternative_k_substituted,
                "phase2d_score_k_min": item.k_min_score,
                "phase2d_score_alternative": item.alt_score,
                "delta_phase2d_score": item.gain,
                "frontier_size": len(record["pareto_frontier"]),
                "pareto_frontier": record["pareto_frontier"],
                "segmentation_k_min": segs_min,
                "segmentation_alternative": segs_alt,
                "k_min_width_stats": min_widths,
                "alternative_width_stats": alt_widths,
                "contains_extreme_narrow_segment": contains_extreme_narrow,
                "boundary_condition_candidate": item.boundary_condition_candidate,
                "primary_sample": item.primary_sample,
                "display_order": display_order,
                "is_repeat_item": False,
                "repeat_of_item_id": None,
            }
        )
    return records


# ---------------------------------------------------------------------------
# Output artifacts
# ---------------------------------------------------------------------------


def build_blinded_record(record: Dict[str, Any]) -> Dict[str, Any]:
    if record["display_order"] == "k_min_first":
        seg_1, seg_2 = record["segmentation_k_min"], record["segmentation_alternative"]
    else:
        seg_1, seg_2 = record["segmentation_alternative"], record["segmentation_k_min"]
    return {
        "item_id": record["item_id"],
        "source_file": record["source_file"],
        "paragraph_index": record["paragraph_index"],
        "paragraph_start_offset": record["paragraph_start_offset"],
        "paragraph_end_offset": record["paragraph_end_offset"],
        "source_text": record["source_text"],
        "segmentation_1": seg_1,
        "segmentation_2": seg_2,
        "is_repeat_item": record["is_repeat_item"],
        "repeat_of_item_id": record["repeat_of_item_id"],
    }


def build_manifest_record(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "item_id": record["item_id"],
        "segmentation_1_is": "k_min" if record["display_order"] == "k_min_first" else "alternative",
        "segmentation_2_is": "alternative" if record["display_order"] == "k_min_first" else "k_min",
        "source_file": record["source_file"],
        "paragraph_index": record["paragraph_index"],
        "k_min": record["k_min"],
        "alternative_k": record["alternative_k"],
        "delta_k": record["delta_k"],
        "alternative_k_substituted": record["alternative_k_substituted"],
        "phase2d_score_k_min": record["phase2d_score_k_min"],
        "phase2d_score_alternative": record["phase2d_score_alternative"],
        "delta_phase2d_score": record["delta_phase2d_score"],
        "frontier_size": record["frontier_size"],
        "pareto_frontier": record["pareto_frontier"],
        "stratum": record["stratum"],
        "contains_extreme_narrow_segment": record["contains_extreme_narrow_segment"],
        "boundary_condition_candidate": record["boundary_condition_candidate"],
        "primary_sample": record["primary_sample"],
    }


def _assert_no_forbidden_tokens(text: str, artifact_name: str) -> None:
    lowered = text.lower()
    hits = [tok for tok in FORBIDDEN_EVALUATOR_TOKENS if tok in lowered]
    if hits:
        raise IntegrityError(f"STOP: evaluator-facing artifact {artifact_name} leaks forbidden token(s): {hits}")


def render_html(blinded_records: List[Dict[str, Any]]) -> str:
    parts = [
        "<!DOCTYPE html><html lang='zh-Hant'><head><meta charset='utf-8'>",
        "<title>Phase 2D Experiment 5 - Blinded Evaluation Package</title>",
        "<style>",
        "body{font-family:sans-serif;max-width:760px;margin:2em auto;line-height:1.6;}",
        ".item{border-top:2px solid #333;padding:1.5em 0;}",
        ".source{background:#f4f4f4;padding:0.8em;margin-bottom:1em;white-space:pre-wrap;}",
        ".segblock{margin-bottom:1em;}",
        ".seg{border:1px solid #888;padding:0.5em 0.8em;margin:0.3em 0;white-space:pre-wrap;font-family:monospace;}",
        ".label{font-weight:bold;margin-top:1em;}",
        "</style></head><body>",
        "<h1>Phase 2D Experiment 5 - Blinded Evaluation Preview</h1>",
        "<p>Each item below shows one paragraph, segmented two different ways. "
        "There is no algorithmic information shown here; the two versions are unlabeled beyond "
        "\"Segmentation 1\" / \"Segmentation 2\".</p>",
    ]
    for r in blinded_records:
        parts.append(f"<div class='item' id='{r['item_id']}'>")
        parts.append(f"<div class='label'>Item {r['item_id']}</div>")
        parts.append(f"<div class='source'>{r['source_text']}</div>")
        parts.append("<div class='segblock'><div class='label'>Segmentation 1</div>")
        for seg in r["segmentation_1"]:
            parts.append(f"<div class='seg'>{seg}</div>")
        parts.append("</div>")
        parts.append("<div class='segblock'><div class='label'>Segmentation 2</div>")
        for seg in r["segmentation_2"]:
            parts.append(f"<div class='seg'>{seg}</div>")
        parts.append("</div></div>")
    parts.append("</body></html>")
    return "\n".join(parts)


def render_preview_text(blinded_records: List[Dict[str, Any]], n: int = 10) -> str:
    lines = ["PHASE 2D EXPERIMENT 5A - BLINDED PREVIEW (first {} items)".format(min(n, len(blinded_records))), "=" * 76]
    for r in blinded_records[:n]:
        lines.append("")
        lines.append(f"Item: {r['item_id']}  ({r['source_file']}, paragraph {r['paragraph_index']})")
        lines.append(f"Source text: {r['source_text']}")
        lines.append("Segmentation 1:")
        for seg in r["segmentation_1"]:
            lines.append(f"  [ {seg} ]")
        lines.append("Segmentation 2:")
        for seg in r["segmentation_2"]:
            lines.append(f"  [ {seg} ]")
    return "\n".join(lines) + "\n"


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_checksums(
    corpus_dir: str, corpus_files: Sequence[str], results_json_path: str, summary_txt_path: str, config: Dict[str, Any]
) -> Dict[str, Any]:
    corpus_checksums = {
        os.path.join("examples", "notes", name): _sha256_file(os.path.join(corpus_dir, name)) for name in corpus_files
    }
    payload: Dict[str, Any] = {
        "corpus_files_sha256": corpus_checksums,
        "results_json_sha256": _sha256_file(results_json_path),
        "results_json_path": os.path.relpath(results_json_path, _REPO_ROOT),
    }
    if os.path.exists(summary_txt_path):
        payload["summary_txt_sha256"] = _sha256_file(summary_txt_path)
        payload["summary_txt_consumed"] = False
    payload["preparation_script_sha256"] = _sha256_file(os.path.abspath(__file__))
    payload["python_version"] = sys.version
    payload["config"] = config
    payload["generated_at_informational_only"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    payload["generated_at_note"] = "informational only - never used to derive any deterministic ID or selection"
    return payload


def write_sampling_summary(
    path: str,
    sample_meta: Dict[str, Any],
    records: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> None:
    lines = []
    lines.append("PHASE 2D EXPERIMENT 5A - SAMPLING SUMMARY")
    lines.append("=" * 76)
    lines.append("This round produces sampling + a blinded evaluation package ONLY.")
    lines.append("No human ratings were collected. No conclusions about readability,")
    lines.append("correlation, or K-selection policy are drawn here.")
    lines.append("")
    lines.append("Configuration:")
    for k, v in config.items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append(f"Control paragraphs (no Pareto alternative, not sampled into items): {sample_meta['n_control_paragraphs']}")
    lines.append(f"Recoverable paragraphs (frontier size > 1): {sample_meta['n_recoverable_paragraphs']}")
    lines.append(f"  Qualifying (>=1 alt passes width filter): {sample_meta['n_qualifying_paragraphs']}")
    lines.append(f"  Excluded by extreme-narrow-segment filter (no alt passes): {sample_meta['n_excluded_extreme_narrow_paragraphs']}")
    lines.append(f"Non-monotonic paragraphs (score decreases somewhere above K_min): {sample_meta['n_non_monotonic_paragraphs']}")
    lines.append("")
    lines.append("Draw log (candidates drawn per stratum-targeting procedure; items may overlap/merge):")
    for k, v in sample_meta["draw_log"].items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append(f"Total evaluation items after merge: {len(records)}")
    primary = [r for r in records if r["primary_sample"]]
    boundary = [r for r in records if r["boundary_condition_candidate"]]
    lines.append(f"  Primary-sample items: {len(primary)}")
    lines.append(f"  Boundary-condition items (excluded from primary sample): {len(boundary)}")
    from collections import Counter

    stratum_counts = Counter(s for r in records for s in r["stratum"])
    lines.append("")
    lines.append("Stratum label counts (an item may carry multiple labels):")
    for s, c in sorted(stratum_counts.items()):
        lines.append(f"  {s}: {c}")
    overlap = sum(1 for r in records if len(r["stratum"]) > 1)
    lines.append("")
    lines.append(f"Items carrying more than one stratum label: {overlap}")
    lines.append(f"Items with alternative_k_substituted=true (target ΔK not itself a frontier point): {sum(1 for r in records if r['alternative_k_substituted'])}")
    lines.append(f"Items with contains_extreme_narrow_segment=true: {sum(1 for r in records if r['contains_extreme_narrow_segment'])}")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# CLI / orchestration
# ---------------------------------------------------------------------------


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--results-json", default=DEFAULT_RESULTS_JSON)
    p.add_argument("--corpus-dir", default=DEFAULT_CORPUS_DIR)
    p.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--items-per-stratum", type=int, default=DEFAULT_ITEMS_PER_STRATUM)
    p.add_argument("--min-segment-width", type=int, default=DEFAULT_MIN_SEGMENT_WIDTH)
    p.add_argument("--boundary-condition-count", type=int, default=DEFAULT_BOUNDARY_CONDITION_COUNT)
    p.add_argument("--max-items", type=int, default=None)
    p.add_argument("--no-html", action="store_true", help="skip writing evaluation.html")
    return p.parse_args(argv)


def run(args: argparse.Namespace) -> Dict[str, Any]:
    results = load_results(args.results_json)
    corpus_files = discover_corpus_files(args.corpus_dir)
    corpus_texts = load_corpus_texts(args.corpus_dir, corpus_files)

    items, sample_meta = sample_all(
        results,
        seed=args.seed,
        items_per_stratum=args.items_per_stratum,
        min_width=args.min_segment_width,
        boundary_condition_count=args.boundary_condition_count,
    )
    records = finalize_items(
        items, corpus_texts, sample_meta["non_monotonic_map"], seed=args.seed, max_items=args.max_items
    )

    os.makedirs(args.output_dir, exist_ok=True)

    manifest = [build_manifest_record(r) for r in records]
    blinded = [build_blinded_record(r) for r in records]

    manifest_path = os.path.join(args.output_dir, "sample_manifest.json")
    items_path = os.path.join(args.output_dir, "evaluation_items.json")
    blinded_path = os.path.join(args.output_dir, "evaluation_items_blinded.json")
    summary_path = os.path.join(args.output_dir, "sampling_summary.txt")
    checksums_path = os.path.join(args.output_dir, "checksums.json")
    html_path = os.path.join(args.output_dir, "evaluation.html")
    preview_path = os.path.join(args.output_dir, "preview_blinded.txt")

    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1, sort_keys=True)
    with open(items_path, "w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False, indent=1, sort_keys=True)
    with open(blinded_path, "w", encoding="utf-8") as fh:
        json.dump(blinded, fh, ensure_ascii=False, indent=1, sort_keys=True)

    blinded_text = json.dumps(blinded, ensure_ascii=False, sort_keys=True)
    _assert_no_forbidden_tokens(blinded_text, "evaluation_items_blinded.json")

    html_text = None
    if not args.no_html:
        html_text = render_html(blinded)
        _assert_no_forbidden_tokens(html_text, "evaluation.html")
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(html_text)

    preview_text = render_preview_text(blinded, n=10)
    _assert_no_forbidden_tokens(preview_text, "preview_blinded.txt")
    with open(preview_path, "w", encoding="utf-8") as fh:
        fh.write(preview_text)

    config = {
        "seed": args.seed,
        "items_per_stratum": args.items_per_stratum,
        "min_segment_width": args.min_segment_width,
        "boundary_condition_count": args.boundary_condition_count,
        "max_items": args.max_items,
        "results_json": os.path.relpath(args.results_json, _REPO_ROOT),
        "corpus_dir": os.path.relpath(args.corpus_dir, _REPO_ROOT),
    }
    write_sampling_summary(summary_path, sample_meta, records, config)
    checksums = build_checksums(args.corpus_dir, corpus_files, args.results_json, DEFAULT_SUMMARY_TXT, config)
    with open(checksums_path, "w", encoding="utf-8") as fh:
        json.dump(checksums, fh, ensure_ascii=False, indent=1, sort_keys=True)

    return {
        "n_items": len(records),
        "n_primary": sum(1 for r in records if r["primary_sample"]),
        "n_boundary_condition": sum(1 for r in records if r["boundary_condition_candidate"]),
        "sample_meta": sample_meta,
        "output_dir": args.output_dir,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        result = run(args)
    except IntegrityError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Wrote {result['n_items']} evaluation items ({result['n_primary']} primary, {result['n_boundary_condition']} boundary-condition) to {result['output_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
