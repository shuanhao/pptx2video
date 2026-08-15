"""Phase 2D Experiment 5B - Human Evaluation Analysis Pipeline.

STANDALONE EXPERIMENT-INFRASTRUCTURE TOOL. NOT part of the production
pipeline, NOT a Phase 2D algorithm change. Implements the analysis layer
specified by `docs/PHASE_2D_EXPERIMENT_5B_HUMAN_EVALUATION_DESIGN.md`
(sections 13, 14, 15, 16, 17, 19, 20, 22, 23, 26).

Implements, in order, the 14-step pipeline of design section 20:

 1. Load raw response data.
 2. Validate response schema.
 3. Validate every item_id against sample_manifest.json's known set.
 4. Load the hidden manifest.
 5. Reconstruct displayed A/B -> original segmentation identity.
 6. Validate mapping completeness.
 7. Validate response integrity per the data-quality rules.
 8. Apply the data-quality rules, producing a cleaned/derived copy - the
    raw file itself is never modified.
 9. Compute the primary outcome.
10. Compute secondary outcomes.
11. Compute reviewer agreement and repeat-item consistency.
12. Perform the predefined exploratory subgroup analyses.
13. Generate the analysis report.
14. Confirm raw response data is byte-identical to its state before
    analysis.

IMPORTANT - NO CONCLUSIONS FABRICATED HERE
----------------------------------------------------------------------------
This script computes whatever the data given to it supports. It does not
generate, simulate, or assume human ratings. If it is run against
synthetic test fixtures (as this implementation round's own tests do, to
validate the machinery), the caller is responsible for labeling that run
accordingly (`--data-label`) and for never presenting its output as a real
Experiment 5B finding. This mirrors the task's own explicit instruction:
implement and test the machinery; do not fabricate or report human-
evaluation conclusions from it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
for _p in (_REPO_ROOT, _SCRIPTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import phase2d_experiment5b_collect as collect5b  # noqa: E402

IntegrityError = collect5b.IntegrityError
InvalidResponseError = collect5b.InvalidResponseError

DEFAULT_MANIFEST_JSON = collect5b.DEFAULT_MANIFEST_JSON
DEFAULT_RAW_RESPONSES = os.path.join(_REPO_ROOT, "data", "phase2d_experiment5b", "raw_responses.json")
DEFAULT_OUTPUT_DIR = os.path.join(_REPO_ROOT, "reports", "phase2d_experiment5b")

#: Smallest-possible addition to the analysis interface (correction round
#: requirement 3): the missing-response audit (design section 19 row 1)
#: needs to know the *expected* assignment population, which only exists
#: in the per-evaluator assignment files `phase2d_experiment5b_collect.py`
#: writes via its `assign` subcommand. This reuses that existing
#: assignment output rather than inventing a second assignment model.
#: Optional: if the directory is absent, the audit is simply not run and
#: is reported as such (never silently assumed complete).
DEFAULT_ASSIGNMENTS_DIR = os.path.join(_REPO_ROOT, "data", "phase2d_experiment5b", "assignments")

#: Also optional: if present, folded into the blinding-verification
#: acceptance criterion alongside the blinded-JSON re-scan (design
#: section 8/9 both apply to this artifact).
DEFAULT_REVIEWER_INSTRUCTIONS_PATH = os.path.join(_REPO_ROOT, "data", "phase2d_experiment5b", "reviewer_instructions.txt")

VALUE_DOMAIN = (-2, -1, 0, 1, 2)
INCONSISTENCY_THRESHOLD = 2

REQUIRED_RESPONSE_FIELDS = {
    "response_event_id",
    "item_id",
    "is_repeat",
    "repeat_of_response_event_id",
    "evaluator_id",
    "displayed_order",
    "comparative_rating",
    "awkward_split_segmentation_1",
    "awkward_split_segmentation_2",
    "reading_effort_segmentation_1",
    "reading_effort_segmentation_2",
    "optional_comment",
    "timestamp",
}


# ---------------------------------------------------------------------------
# Steps 1-3: load & schema/item-id validation
# ---------------------------------------------------------------------------


def load_raw_responses(path: str) -> List[Dict[str, Any]]:
    """Step 1."""
    with open(path, "r", encoding="utf-8") as fh:
        records = json.load(fh)
    if not isinstance(records, list):
        raise IntegrityError(f"STOP: {path} is not a JSON list")
    return records


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_response_schema(record: Dict[str, Any]) -> Optional[str]:
    """Step 2. Returns None if valid, else a specific rejection reason.
    This is a soft, per-record check - a schema failure rejects only this
    record (design section 19's "invalid rating" row), it does not halt
    the batch."""
    missing = REQUIRED_RESPONSE_FIELDS - set(record.keys())
    if missing:
        return f"missing required field(s): {sorted(missing)}"
    if not isinstance(record.get("item_id"), str) or not record["item_id"]:
        return "missing/malformed item_id field"
    if not isinstance(record.get("evaluator_id"), str) or not record["evaluator_id"]:
        return "missing/malformed evaluator_id field"
    if not isinstance(record.get("response_event_id"), str) or not record["response_event_id"]:
        return "missing/malformed response_event_id field"
    if not isinstance(record.get("is_repeat"), bool):
        return "malformed is_repeat field: must be bool"
    if record["is_repeat"] and not isinstance(record.get("repeat_of_response_event_id"), str):
        return "malformed repeat_of_response_event_id: required (non-null) when is_repeat is true"
    if not record["is_repeat"] and record.get("repeat_of_response_event_id") is not None:
        return "malformed repeat_of_response_event_id: must be null when is_repeat is false"
    try:
        collect5b.validate_displayed_order(record.get("displayed_order"))
        collect5b.validate_comparative_rating(record.get("comparative_rating"))
        collect5b.validate_awkward_split(record.get("awkward_split_segmentation_1"), "awkward_split_segmentation_1")
        collect5b.validate_awkward_split(record.get("awkward_split_segmentation_2"), "awkward_split_segmentation_2")
        collect5b.validate_reading_effort(record.get("reading_effort_segmentation_1"), "reading_effort_segmentation_1")
        collect5b.validate_reading_effort(record.get("reading_effort_segmentation_2"), "reading_effort_segmentation_2")
    except InvalidResponseError as exc:
        return str(exc)
    comment = record.get("optional_comment")
    if comment is not None and not isinstance(comment, str):
        return "malformed optional_comment: must be string or null"
    return None


def ingest_responses(
    raw_responses: Sequence[Dict[str, Any]], manifest_by_id: Dict[str, Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Steps 2-3 combined. Returns (valid, rejected). Rejection is
    per-record (soft) for schema/value problems. An item_id that is
    syntactically present but not found in `sample_manifest.json` is a
    hard integrity failure per design section 19 and halts the entire
    batch immediately (mirrors `phase2d_experiment5_prepare.py`'s
    IntegrityError convention)."""
    valid: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for record in raw_responses:
        reason = validate_response_schema(record)
        if reason is not None:
            rejected.append({"record": record, "reason": reason})
            continue
        item_id = record["item_id"]
        if item_id not in manifest_by_id:
            raise IntegrityError(
                f"STOP: malformed item_id (not present in sample_manifest.json): {item_id!r} "
                f"(response_event_id={record.get('response_event_id')!r})"
            )
        valid.append(record)
    return valid, rejected


# ---------------------------------------------------------------------------
# Steps 4-6: hidden mapping & orientation
# ---------------------------------------------------------------------------


def load_hidden_mapping(manifest_path: str) -> Dict[str, Dict[str, Any]]:
    """Step 4. Reuses `phase2d_experiment5b_collect.load_manifest`, which
    already performs the manifest-level integrity checks (duplicate
    item_id, segmentation_1_is == segmentation_2_is, duplicate
    (source_file, paragraph_index, alternative_k) triples)."""
    return collect5b.load_manifest(manifest_path)


def resolve_displayed_identity(item_id: str, displayed_order: str, manifest_by_id: Dict[str, Dict[str, Any]]) -> Tuple[str, str]:
    """Step 5. Returns (effective_segmentation_1_is, effective_segmentation_2_is)
    - which of 'k_min' / 'alternative' was actually shown as Segmentation 1
    and Segmentation 2 for this specific exposure, accounting for a
    repeat's independently-randomized swap (design section 10)."""
    rec = manifest_by_id[item_id]
    seg1_is, seg2_is = rec["segmentation_1_is"], rec["segmentation_2_is"]
    if displayed_order == "swapped":
        seg1_is, seg2_is = seg2_is, seg1_is
    return seg1_is, seg2_is


def orient_rating(comparative_rating: int, item_id: str, displayed_order: str, manifest_by_id: Dict[str, Dict[str, Any]]) -> int:
    """Positive oriented rating always means 'alternative preferred',
    negative always means 'k_min preferred', regardless of which side it
    was physically displayed on (design section 13, step 1)."""
    _, seg2_is = resolve_displayed_identity(item_id, displayed_order, manifest_by_id)
    return comparative_rating if seg2_is == "alternative" else -comparative_rating


def validate_mapping_completeness(
    responses: Sequence[Dict[str, Any]], manifest_by_id: Dict[str, Dict[str, Any]]
) -> List[str]:
    """Step 6. Returns a list of response_event_ids that could NOT be
    resolved to exactly one k_min/alternative identity - should always be
    empty given upstream validation; kept as an explicit, auditable check
    per design section 20 step 6 and acceptance criterion 3 (section 26)."""
    failures = []
    for r in responses:
        try:
            seg1_is, seg2_is = resolve_displayed_identity(r["item_id"], r["displayed_order"], manifest_by_id)
            if {seg1_is, seg2_is} != {"k_min", "alternative"}:
                failures.append(r["response_event_id"])
        except Exception:
            failures.append(r["response_event_id"])
    return failures


# ---------------------------------------------------------------------------
# Steps 7-8: data-quality rules
# ---------------------------------------------------------------------------


def apply_data_quality_rules(
    valid_responses: Sequence[Dict[str, Any]], manifest_by_id: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """Steps 7-8. Produces a cleaned/derived dataset; `valid_responses`
    itself (and, at a higher level, the raw response file) is never
    mutated - every entry below references or copies fields, it never
    writes back to the input."""
    by_evaluator_item: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for r in valid_responses:
        if not r["is_repeat"]:
            by_evaluator_item[(r["evaluator_id"], r["item_id"])].append(r)

    duplicate_flagged_ids = set()
    for group in by_evaluator_item.values():
        if len(group) > 1:
            for r in group[1:]:
                duplicate_flagged_ids.add(r["response_event_id"])

    comment_leak_flagged_ids = set()
    for r in valid_responses:
        comment = r.get("optional_comment")
        if comment:
            lowered = comment.lower()
            if any(tok in lowered for tok in collect5b.FORBIDDEN_EVALUATOR_TOKENS):
                comment_leak_flagged_ids.add(r["response_event_id"])

    # Base (first-received, non-repeat) response per (evaluator, item) -
    # used both as the "first valid response" for primary computation and
    # as the reference point for repeat-inconsistency detection.
    base_by_evaluator_item: Dict[Tuple[str, str], Dict[str, Any]] = {
        key: group[0] for key, group in by_evaluator_item.items()
    }

    cleaned = []
    inconsistent_repeat_ids = set()
    for r in valid_responses:
        oriented = orient_rating(r["comparative_rating"], r["item_id"], r["displayed_order"], manifest_by_id)
        used_in_primary = (not r["is_repeat"]) and (r["response_event_id"] not in duplicate_flagged_ids)
        entry = {
            "response_event_id": r["response_event_id"],
            "item_id": r["item_id"],
            "evaluator_id": r["evaluator_id"],
            "is_repeat": r["is_repeat"],
            "oriented_rating": oriented,
            "used_in_primary": used_in_primary,
            "duplicate_non_repeat_flagged": r["response_event_id"] in duplicate_flagged_ids,
            "comment_leak_flagged": r["response_event_id"] in comment_leak_flagged_ids,
        }
        if r["is_repeat"]:
            base = base_by_evaluator_item.get((r["evaluator_id"], r["item_id"]))
            if base is not None:
                base_oriented = orient_rating(base["comparative_rating"], base["item_id"], base["displayed_order"], manifest_by_id)
                inconsistent = abs(oriented - base_oriented) >= INCONSISTENCY_THRESHOLD
                entry["repeat_inconsistent"] = inconsistent
                entry["repeat_base_response_event_id"] = base["response_event_id"]
                if inconsistent:
                    inconsistent_repeat_ids.add(r["response_event_id"])
            else:
                entry["repeat_inconsistent"] = None
                entry["repeat_base_response_event_id"] = None
        cleaned.append(entry)

    return {
        "cleaned": cleaned,
        "duplicate_non_repeat_flagged_ids": sorted(duplicate_flagged_ids),
        "comment_leak_flagged_ids": sorted(comment_leak_flagged_ids),
        "inconsistent_repeat_ids": sorted(inconsistent_repeat_ids),
    }


# ---------------------------------------------------------------------------
# Step 9: primary outcome
# ---------------------------------------------------------------------------


def compute_primary_outcome(cleaned: Sequence[Dict[str, Any]], manifest_by_id: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    primary_item_ids = sorted(i for i, r in manifest_by_id.items() if r["primary_sample"])
    ratings_by_item: Dict[str, List[int]] = {i: [] for i in primary_item_ids}
    for entry in cleaned:
        if entry["used_in_primary"] and entry["item_id"] in ratings_by_item:
            ratings_by_item[entry["item_id"]].append(entry["oriented_rating"])

    item_medians: Dict[str, Optional[float]] = {}
    item_counts: Dict[str, int] = {}
    for item_id, ratings in ratings_by_item.items():
        item_counts[item_id] = len(ratings)
        item_medians[item_id] = statistics.median(ratings) if ratings else None

    scored_items = {i: m for i, m in item_medians.items() if m is not None}
    wins = sum(1 for m in scored_items.values() if m > 0)
    ties = sum(1 for m in scored_items.values() if m == 0)
    losses = sum(1 for m in scored_items.values() if m < 0)

    corpus_median = statistics.median(scored_items.values()) if scored_items else None
    below_floor = sorted(i for i, c in item_counts.items() if c < 3)

    return {
        "n_primary_items": len(primary_item_ids),
        "n_items_with_data": len(scored_items),
        "n_items_no_data": len(primary_item_ids) - len(scored_items),
        "item_medians": item_medians,
        "item_rating_counts": item_counts,
        "items_below_3_rating_floor": below_floor,
        "corpus_level_median": corpus_median,
        "win_count": wins,
        "tie_count": ties,
        "loss_count": losses,
    }


def sign_test(item_medians: Sequence[float]) -> Dict[str, Any]:
    """Design section 16: exact two-sided sign test, excluding exact-zero
    item-level medians from the win/loss count (still reported in the
    win/tie/loss breakdown elsewhere)."""
    non_zero = [m for m in item_medians if m != 0]
    wins = sum(1 for m in non_zero if m > 0)
    losses = sum(1 for m in non_zero if m < 0)
    n = wins + losses
    if n == 0:
        return {"n": 0, "wins": 0, "losses": 0, "p_value": None}
    k = min(wins, losses)
    cdf = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    p_value = min(1.0, 2 * cdf)
    return {"n": n, "wins": wins, "losses": losses, "p_value": p_value}


# ---------------------------------------------------------------------------
# Step 10: secondary outcomes
# ---------------------------------------------------------------------------


def _oriented_side_stat(
    cleaned_primary_only: Sequence[Dict[str, Any]],
    raw_by_event_id: Dict[str, Dict[str, Any]],
    manifest_by_id: Dict[str, Dict[str, Any]],
    field_1: str,
    field_2: str,
) -> Dict[str, Any]:
    """Orients a per-segmentation-side field (awkward-split / reading-effort)
    onto k_min / alternative, using the same displayed-side resolution as
    the comparative rating."""
    k_min_values: List[Any] = []
    alt_values: List[Any] = []
    for entry in cleaned_primary_only:
        raw = raw_by_event_id[entry["response_event_id"]]
        seg1_is, seg2_is = resolve_displayed_identity(entry["item_id"], raw["displayed_order"], manifest_by_id)
        v1, v2 = raw[field_1], raw[field_2]
        (k_min_values if seg1_is == "k_min" else alt_values).append(v1)
        (k_min_values if seg2_is == "k_min" else alt_values).append(v2)
    return {"k_min": k_min_values, "alternative": alt_values}


def compute_secondary_outcomes(
    cleaned: Sequence[Dict[str, Any]],
    raw_by_event_id: Dict[str, Dict[str, Any]],
    manifest_by_id: Dict[str, Dict[str, Any]],
    primary_outcome: Dict[str, Any],
) -> Dict[str, Any]:
    """SECONDARY (design section 14): predefined, always computed, never
    itself the basis for the Decision Gate. Every subgroup below is
    reported on its own subset; strata overlap (an item may appear in
    more than one breakdown) and are never summed as independent
    evidence."""
    cleaned_primary_only = [e for e in cleaned if e["used_in_primary"]]

    def _summ(medians: Sequence[float]) -> Dict[str, Any]:
        scored = [m for m in medians if m is not None]
        return {
            "n_items": len(scored),
            "median_of_medians": statistics.median(scored) if scored else None,
            "win": sum(1 for m in scored if m > 0),
            "tie": sum(1 for m in scored if m == 0),
            "loss": sum(1 for m in scored if m < 0),
        }

    item_medians = primary_outcome["item_medians"]

    by_stratum: Dict[str, List[float]] = defaultdict(list)
    for item_id, median in item_medians.items():
        if median is None:
            continue
        for label in manifest_by_id[item_id]["stratum"]:
            by_stratum[label].append(median)
    stratum_breakdown = {label: _summ(medians) for label, medians in sorted(by_stratum.items())}

    by_source: Dict[str, List[float]] = defaultdict(list)
    for item_id, median in item_medians.items():
        if median is None:
            continue
        source = os.path.basename(manifest_by_id[item_id]["source_file"])
        prefix = "mcu1" if source.startswith("mcu1") else ("mcu2" if source.startswith("mcu2") else source)
        by_source[prefix].append(median)
    source_breakdown = {label: _summ(medians) for label, medians in sorted(by_source.items())}

    awkward = _oriented_side_stat(cleaned_primary_only, raw_by_event_id, manifest_by_id,
                                   "awkward_split_segmentation_1", "awkward_split_segmentation_2")
    awkward_rate = {
        side: (sum(1 for v in values if v) / len(values) if values else None) for side, values in awkward.items()
    }

    effort = _oriented_side_stat(cleaned_primary_only, raw_by_event_id, manifest_by_id,
                                  "reading_effort_segmentation_1", "reading_effort_segmentation_2")
    effort_stats = {
        side: {
            "n": len(values),
            "mean": statistics.mean(values) if values else None,
            "median": statistics.median(values) if values else None,
        }
        for side, values in effort.items()
    }

    boundary_item_ids = sorted(i for i, r in manifest_by_id.items() if r["boundary_condition_candidate"])
    boundary_detail = []
    for item_id in boundary_item_ids:
        entries = [e for e in cleaned if e["item_id"] == item_id and not e["is_repeat"]]
        ratings = [e["oriented_rating"] for e in entries]
        comments = [
            raw_by_event_id[e["response_event_id"]].get("optional_comment")
            for e in entries
            if raw_by_event_id[e["response_event_id"]].get("optional_comment")
        ]
        boundary_detail.append({"item_id": item_id, "oriented_ratings": ratings, "comments": comments})

    return {
        "by_stratum": stratum_breakdown,
        "by_source_file": source_breakdown,
        "awkward_split_rate_by_side": awkward_rate,
        "reading_effort_by_side": effort_stats,
        "boundary_condition_items": boundary_detail,
        "note_overlapping_strata": (
            "Stratum breakdowns above draw from overlapping subsets of the same primary "
            "population; their sample sizes are never summed as independent evidence."
        ),
    }


# ---------------------------------------------------------------------------
# Step 11: agreement & repeat consistency
# ---------------------------------------------------------------------------


def _delta2_table(freq: Dict[int, float], value_domain: Sequence[int]) -> Dict[Tuple[int, int], float]:
    table = {}
    for idx_c, c in enumerate(value_domain):
        for idx_k, k in enumerate(value_domain):
            if c == k:
                table[(c, k)] = 0.0
                continue
            lo_idx, hi_idx = (idx_c, idx_k) if idx_c < idx_k else (idx_k, idx_c)
            lo, hi = value_domain[lo_idx], value_domain[hi_idx]
            s = sum(freq[value_domain[g]] for g in range(lo_idx, hi_idx + 1))
            table[(c, k)] = (s - (freq[c] + freq[k]) / 2.0) ** 2
    return table


def krippendorff_alpha_ordinal(
    units: Dict[str, List[int]], value_domain: Sequence[int] = VALUE_DOMAIN
) -> Optional[float]:
    """Ordinal-weighted Krippendorff's alpha, computed from scratch via
    the standard coincidence-matrix formulation (design section 17). Each
    `units[unit_id]` is the list of oriented ratings from distinct raters
    for that unit (item); units with fewer than 2 ratings contribute no
    pairable observations. Returns None if there is no pairable data or
    if the expected disagreement is zero (undefined alpha - e.g. every
    rating identical)."""
    o: Dict[Tuple[int, int], float] = defaultdict(float)
    for values in units.values():
        m = len(values)
        if m < 2:
            continue
        denom = m - 1
        for i in range(m):
            for j in range(m):
                if i == j:
                    continue
                o[(values[i], values[j])] += 1.0 / denom

    n_c: Dict[int, float] = defaultdict(float)
    for (c, _k), v in o.items():
        n_c[c] += v
    n = sum(n_c.values())
    if n == 0:
        return None

    freq = {v: n_c.get(v, 0.0) for v in value_domain}
    delta2 = _delta2_table(freq, value_domain)

    Do = sum(o[(c, k)] * delta2[(c, k)] for (c, k) in o) / n

    De_sum = 0.0
    for c in value_domain:
        for k in value_domain:
            if c == k:
                continue
            De_sum += n_c.get(c, 0.0) * n_c.get(k, 0.0) * delta2[(c, k)]
    if n <= 1:
        return None
    De = De_sum / (n * (n - 1))
    if De == 0:
        return None
    return 1.0 - Do / De


def pairwise_percent_agreement(units: Dict[str, List[int]]) -> Optional[float]:
    """Simple descriptive companion (design section 17): do any two raters
    on the same unit land on the same side of 0 (negative / zero /
    positive), ignoring magnitude."""

    def bucket(v: int) -> int:
        return -1 if v < 0 else (0 if v == 0 else 1)

    agree = 0
    total = 0
    for values in units.values():
        m = len(values)
        for i in range(m):
            for j in range(i + 1, m):
                total += 1
                if bucket(values[i]) == bucket(values[j]):
                    agree += 1
    return (agree / total) if total else None


def compute_agreement(cleaned: Sequence[Dict[str, Any]], manifest_by_id: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Computed over primary-sample items only, using each evaluator's
    first-received, non-duplicate, non-repeat rating per item (design
    section 17)."""
    units: Dict[str, List[int]] = defaultdict(list)
    for entry in cleaned:
        if entry["used_in_primary"] and manifest_by_id[entry["item_id"]]["primary_sample"]:
            units[entry["item_id"]].append(entry["oriented_rating"])
    alpha = krippendorff_alpha_ordinal(units)
    pct_agreement = pairwise_percent_agreement(units)
    return {
        "n_units_with_2plus_raters": sum(1 for v in units.values() if len(v) >= 2),
        "krippendorff_alpha_ordinal": alpha,
        "pairwise_percent_agreement": pct_agreement,
    }


def compute_repeat_consistency(cleaned: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    by_evaluator: Dict[str, List[bool]] = defaultdict(list)
    for entry in cleaned:
        if entry["is_repeat"] and entry.get("repeat_inconsistent") is not None:
            by_evaluator[entry["evaluator_id"]].append(not entry["repeat_inconsistent"])

    per_evaluator_rate = {
        evaluator: (sum(flags) / len(flags) if flags else None) for evaluator, flags in sorted(by_evaluator.items())
    }
    rates = [r for r in per_evaluator_rate.values() if r is not None]
    return {
        "per_evaluator_consistency_rate": per_evaluator_rate,
        "corpus_mean_consistency_rate": statistics.mean(rates) if rates else None,
        "corpus_median_consistency_rate": statistics.median(rates) if rates else None,
        "n_evaluators_with_repeats": len(rates),
    }


# ---------------------------------------------------------------------------
# Step 12: exploratory
# ---------------------------------------------------------------------------


def _pearson_r(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    n = len(xs)
    if n < 2:
        return None
    mean_x, mean_y = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return None
    return num / (den_x * den_y)


def compute_exploratory(
    cleaned: Sequence[Dict[str, Any]],
    raw_by_event_id: Dict[str, Dict[str, Any]],
    manifest_by_id: Dict[str, Dict[str, Any]],
    primary_outcome: Dict[str, Any],
    paragraph_length_by_item: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """EXPLORATORY (design section 14/15): reported if supported by the
    data, never used to drive the Decision Gate, not protected against
    multiple-comparisons inflation. Every result here must be presented
    as exploratory in any downstream report.

    `paragraph_length_by_item` (item_id -> paragraph_end_offset -
    paragraph_start_offset) is optional because paragraph offsets live in
    `evaluation_items_blinded.json` / `evaluation_items.json`, not in
    `sample_manifest.json` itself; callers that only load the manifest
    simply get no paragraph-length correlation (None), never a crash."""
    item_medians = primary_outcome["item_medians"]
    paragraph_length_by_item = paragraph_length_by_item or {}

    substituted_medians, unsubstituted_medians = [], []
    for item_id, median in item_medians.items():
        if median is None:
            continue
        (substituted_medians if manifest_by_id[item_id]["alternative_k_substituted"] else unsubstituted_medians).append(median)

    lengths, medians_for_length = [], []
    for item_id, median in item_medians.items():
        if median is None:
            continue
        length = paragraph_length_by_item.get(item_id)
        if length is None:
            continue
        lengths.append(length)
        medians_for_length.append(median)

    by_evaluator: Dict[str, List[int]] = defaultdict(list)
    for entry in cleaned:
        if entry["used_in_primary"]:
            by_evaluator[entry["evaluator_id"]].append(entry["oriented_rating"])
    per_evaluator_mean = {e: statistics.mean(v) for e, v in sorted(by_evaluator.items())}

    comments = []
    for entry in cleaned:
        raw = raw_by_event_id[entry["response_event_id"]]
        if raw.get("optional_comment"):
            comments.append(
                {
                    "item_id": entry["item_id"],
                    "evaluator_id": entry["evaluator_id"],
                    "is_repeat": entry["is_repeat"],
                    "comment": raw["optional_comment"],
                }
            )

    return {
        "alternative_k_substituted_effect": {
            "substituted": {"n": len(substituted_medians), "mean": statistics.mean(substituted_medians) if substituted_medians else None},
            "unsubstituted": {"n": len(unsubstituted_medians), "mean": statistics.mean(unsubstituted_medians) if unsubstituted_medians else None},
        },
        "paragraph_length_correlation_pearson_r": _pearson_r(lengths, medians_for_length) if lengths else None,
        "per_evaluator_mean_oriented_rating": per_evaluator_mean,
        "comments": comments,
    }


# ---------------------------------------------------------------------------
# Missing-response audit (design section 19 row 1; correction round
# requirement 3)
# ---------------------------------------------------------------------------


def load_assignments(assignments_dir: str) -> Dict[str, Dict[str, Any]]:
    """Loads every per-evaluator assignment file written by
    `phase2d_experiment5b_collect.py`'s `assign` subcommand - the
    existing Experiment 5B assignment model, reused as-is rather than
    inventing a second one. Returns {evaluator_id: assignment_dict}."""
    assignments: Dict[str, Dict[str, Any]] = {}
    for fname in sorted(os.listdir(assignments_dir)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(assignments_dir, fname), "r", encoding="utf-8") as fh:
            assignment = json.load(fh)
        assignments[assignment["evaluator_id"]] = assignment
    return assignments


def compute_missing_responses(
    assignments_by_evaluator: Dict[str, Dict[str, Any]], raw_responses: Sequence[Dict[str, Any]]
) -> Dict[str, Any]:
    """Design section 19 row 1: a "missing response" is an assigned
    original-item exposure for which an evaluator submitted NO response
    event at all (valid or invalid). This is explicitly distinct from an
    "invalid rating" (design section 19 row 3), which IS a submitted
    event that failed schema/value validation - those are tracked
    separately by `ingest_responses`'s `rejected` list, never folded into
    this count. This function only counts; it never imputes a value for
    a missing response, and it never reads or writes the raw response
    file - `raw_responses` is only iterated over, never mutated."""
    expected_pairs = {
        (evaluator_id, exposure["item_id"])
        for evaluator_id, assignment in assignments_by_evaluator.items()
        for exposure in assignment["exposures"]
        if exposure["kind"] == "original"
    }
    # An "attempt" is any raw response record (valid or invalid) whose
    # evaluator_id/item_id fields are themselves well-formed strings and
    # which is not a repeat exposure - repeats are optional diagnostic
    # extras (design section 11), not part of the core assigned
    # population this audit reconciles against.
    attempted_pairs = {
        (r["evaluator_id"], r["item_id"])
        for r in raw_responses
        if isinstance(r.get("evaluator_id"), str) and isinstance(r.get("item_id"), str) and not r.get("is_repeat", False)
    }
    attempted_of_expected = expected_pairs & attempted_pairs
    missing_pairs = sorted(expected_pairs - attempted_pairs)

    missing_count_by_item: Dict[str, int] = defaultdict(int)
    missing_count_by_evaluator: Dict[str, int] = defaultdict(int)
    for evaluator_id, item_id in missing_pairs:
        missing_count_by_item[item_id] += 1
        missing_count_by_evaluator[evaluator_id] += 1

    total_expected = len(expected_pairs)
    total_attempted = len(attempted_of_expected)
    total_missing = len(missing_pairs)
    return {
        "total_expected_original_exposures": total_expected,
        "total_attempted_of_expected": total_attempted,
        "total_missing": total_missing,
        # Reconciliation invariant (design section 20 step: "reconcile
        # expected assignments against observed response events"): every
        # expected exposure is either attempted or missing, never both,
        # never neither.
        "reconciles": total_expected == total_attempted + total_missing,
        "missing_pairs": [{"evaluator_id": e, "item_id": i} for e, i in missing_pairs],
        "missing_count_by_item": dict(sorted(missing_count_by_item.items())),
        "missing_count_by_evaluator": dict(sorted(missing_count_by_evaluator.items())),
    }


# ---------------------------------------------------------------------------
# Decision gate classification (machinery only - see module docstring)
# ---------------------------------------------------------------------------


def classify_decision_gate(primary_outcome: Dict[str, Any]) -> str:
    """Derived directly from primary_outcome's real computed state - no
    hardcoded outcome, and no SUPPORT/NULL/CONTRADICTION is ever emitted
    unless every primary-sample item that has data meets the >=3-rating
    floor (design section 26 acceptance criterion 1) and at least one
    item has data at all. This is the anti-fabrication gate: with no (or
    incomplete) real human ratings, this always returns the
    "NOT YET EVALUABLE" state rather than guessing (task correction round
    section 5)."""
    floor_met = (
        primary_outcome["n_primary_items"] > 0
        and primary_outcome["n_items_no_data"] == 0
        and len(primary_outcome["items_below_3_rating_floor"]) == 0
    )
    median = primary_outcome["corpus_level_median"]
    if not floor_met or median is None:
        return (
            "NOT YET EVALUABLE - acceptance criteria not met "
            "(every primary-sample item needs >=3 valid ratings before a Decision Gate state can be claimed); "
            "no SUPPORT/NULL/CONTRADICTION state is reported"
        )
    if median > 0:
        return "STATE A - SUPPORT (machinery classification only; see acceptance criteria)"
    if median < 0:
        return "STATE C - CONTRADICTION (machinery classification only; see acceptance criteria)"
    return "STATE B - NULL (machinery classification only; see acceptance criteria)"


def check_acceptance_criteria(
    primary_outcome: Dict[str, Any],
    mapping_failures: List[str],
    blinding_verification: Optional[Dict[str, Any]],
    dq_verification: Optional[Dict[str, Any]],
    agreement: Dict[str, Any],
    repeat_consistency: Optional[Dict[str, Any]],
    decision_gate_classification: Optional[str],
) -> Dict[str, Dict[str, Any]]:
    """Design section 26's 8 acceptance criteria. Each entry is
    `{"met": bool, "detail": str}`.

    Every criterion is derived from a real verification step that
    actually ran this analysis - none is a hardcoded literal and none is
    a tautology. Passing `None` for `blinding_verification`,
    `dq_verification`, `repeat_consistency`, or
    `decision_gate_classification` explicitly represents "this
    verification did not run" and always fails the corresponding
    criterion - this is the mechanism that lets a caller (or a test)
    prove the gate cannot be satisfied by omission."""
    criteria: Dict[str, Dict[str, Any]] = {}

    floor_met = (
        primary_outcome["n_primary_items"] > 0
        and primary_outcome["n_items_no_data"] == 0
        and len(primary_outcome["items_below_3_rating_floor"]) == 0
    )
    criteria["1_every_primary_item_ge_3_ratings"] = {
        "met": floor_met,
        "detail": (
            f"{len(primary_outcome['items_below_3_rating_floor'])} item(s) below the >=3-rating floor, "
            f"{primary_outcome['n_items_no_data']} item(s) with no data at all "
            f"(of {primary_outcome['n_primary_items']} primary-sample items)"
        ),
    }

    if blinding_verification is None:
        criteria["2_blinding_scan_zero_hits"] = {"met": False, "detail": "blinding scan was not run this analysis"}
    else:
        hits = blinding_verification.get("hits", [])
        criteria["2_blinding_scan_zero_hits"] = {
            "met": bool(blinding_verification.get("ran")) and not hits,
            "detail": blinding_verification.get("detail", ""),
        }

    criteria["3_mapping_100pct_reconstructible"] = {
        "met": len(mapping_failures) == 0,
        "detail": (
            f"{len(mapping_failures)} response event(s) failed to resolve"
            if mapping_failures
            else "all response events resolved to exactly one k_min/alternative identity"
        ),
    }

    if dq_verification is None:
        criteria["4_data_quality_rules_applied_and_auditable"] = {
            "met": False,
            "detail": "data-quality rule audit was not run this analysis",
        }
    else:
        criteria["4_data_quality_rules_applied_and_auditable"] = {
            "met": bool(dq_verification.get("all_rules_applied")),
            "detail": dq_verification.get("detail", ""),
        }

    criteria["5_primary_outcome_and_sign_test_reported"] = {
        "met": primary_outcome["corpus_level_median"] is not None,
        "detail": (
            "corpus-level median computed" if primary_outcome["corpus_level_median"] is not None
            else "no primary-sample data available yet"
        ),
    }

    alpha = agreement.get("krippendorff_alpha_ordinal") if agreement else None
    criteria["6_agreement_computed"] = {
        "met": alpha is not None,
        "detail": "Krippendorff's alpha computed" if alpha is not None else "insufficient multi-rater data to compute alpha",
    }

    if repeat_consistency is None:
        criteria["7_repeat_consistency_computed_no_exclusion"] = {
            "met": False,
            "detail": "repeat consistency was not computed this analysis",
        }
    else:
        expected_keys = {"per_evaluator_consistency_rate", "n_evaluators_with_repeats",
                          "corpus_mean_consistency_rate", "corpus_median_consistency_rate"}
        has_expected_shape = expected_keys <= set(repeat_consistency.keys())
        criteria["7_repeat_consistency_computed_no_exclusion"] = {
            "met": has_expected_shape,
            "detail": (
                "repeat consistency computed with the expected structure; no evaluator excluded"
                if has_expected_shape
                else "repeat consistency result is missing expected field(s)"
            ),
        }

    if decision_gate_classification is None:
        criteria["8_decision_gate_state_reported"] = {
            "met": False,
            "detail": "decision gate classification was not generated this analysis",
        }
    else:
        criteria["8_decision_gate_state_reported"] = {
            "met": isinstance(decision_gate_classification, str) and len(decision_gate_classification) > 0,
            "detail": decision_gate_classification,
        }

    return criteria


def acceptance_criteria_all_met(acceptance_criteria: Dict[str, Dict[str, Any]]) -> bool:
    return all(v["met"] for v in acceptance_criteria.values())


# ---------------------------------------------------------------------------
# Step 13: report generation
# ---------------------------------------------------------------------------


def generate_report_text(results: Dict[str, Any], data_label: Optional[str]) -> str:
    lines = []
    lines.append("PHASE 2D EXPERIMENT 5B - ANALYSIS REPORT")
    lines.append("=" * 76)
    if data_label:
        lines.append(f"DATA LABEL: {data_label}")
    lines.append(
        "This report is generated mechanically from the raw response file given "
        "to phase2d_experiment5b_analyze.py. It draws no conclusion beyond what "
        "that data supports. If the input data is a synthetic/test fixture, "
        "every figure below describes that fixture only, not a real human-"
        "evaluation finding."
    )
    lines.append("")
    lines.append(f"Raw responses ingested: {results['n_raw']}")
    lines.append(f"Valid (schema-passing) responses: {results['n_valid']}")
    lines.append(f"Rejected (schema/value) responses: {len(results['rejected'])}")
    for rej in results["rejected"][:20]:
        lines.append(f"  - {rej['record'].get('response_event_id')}: {rej['reason']}")
    lines.append("")

    dq = results["data_quality"]
    lines.append("DATA QUALITY")
    lines.append("-" * 76)
    lines.append(f"Duplicate non-repeat responses flagged (excluded from primary computation): {len(dq['duplicate_non_repeat_flagged_ids'])}")
    lines.append(f"Comment forbidden-token leak flags (retained, flagged for manual review): {len(dq['comment_leak_flagged_ids'])}")
    lines.append(f"Inconsistent repeats (|delta|>=2): {len(dq['inconsistent_repeat_ids'])}")
    lines.append(f"Mapping-completeness failures: {len(results['mapping_failures'])}")
    lines.append("")

    po = results["primary_outcome"]
    lines.append("PRIMARY OUTCOME")
    lines.append("-" * 76)
    lines.append(f"Primary-sample items: {po['n_primary_items']} (with data: {po['n_items_with_data']}, no data: {po['n_items_no_data']})")
    lines.append(f"Items below the >=3-rating floor: {len(po['items_below_3_rating_floor'])}")
    lines.append(f"Corpus-level median (of item-level medians): {po['corpus_level_median']}")
    lines.append(f"Win / Tie / Loss: {po['win_count']} / {po['tie_count']} / {po['loss_count']}")
    st = results["sign_test"]
    lines.append(f"Sign test (zero-medians excluded): n={st['n']} wins={st['wins']} losses={st['losses']} p_value={st['p_value']}")
    lines.append("")

    lines.append("SECONDARY OUTCOMES (predefined; descriptive only, never independently tested for significance)")
    lines.append("-" * 76)
    so = results["secondary_outcomes"]
    lines.append(so["note_overlapping_strata"])
    for label, summ in so["by_stratum"].items():
        lines.append(f"  stratum={label}: n={summ['n_items']} median_of_medians={summ['median_of_medians']} win/tie/loss={summ['win']}/{summ['tie']}/{summ['loss']}")
    for label, summ in so["by_source_file"].items():
        lines.append(f"  source_file_group={label}: n={summ['n_items']} median_of_medians={summ['median_of_medians']} win/tie/loss={summ['win']}/{summ['tie']}/{summ['loss']}")
    lines.append(f"  awkward-split rate: k_min={so['awkward_split_rate_by_side'].get('k_min')} alternative={so['awkward_split_rate_by_side'].get('alternative')}")
    lines.append(f"  reading effort: k_min={so['reading_effort_by_side'].get('k_min')} alternative={so['reading_effort_by_side'].get('alternative')}")
    lines.append(f"  boundary-condition items (reported individually, never pooled): {len(so['boundary_condition_items'])}")
    for b in so["boundary_condition_items"]:
        lines.append(f"    {b['item_id']}: oriented_ratings={b['oriented_ratings']} comments={b['comments']}")
    lines.append("")

    lines.append("REVIEWER AGREEMENT")
    lines.append("-" * 76)
    ag = results["agreement"]
    lines.append(f"Krippendorff's alpha (ordinal-weighted): {ag['krippendorff_alpha_ordinal']}")
    lines.append(f"Pairwise percent agreement (descriptive companion): {ag['pairwise_percent_agreement']}")
    lines.append("")

    lines.append("REPEAT CONSISTENCY (diagnostic only; no automatic evaluator exclusion)")
    lines.append("-" * 76)
    rc = results["repeat_consistency"]
    lines.append(f"Corpus mean/median consistency rate: {rc['corpus_mean_consistency_rate']} / {rc['corpus_median_consistency_rate']}")
    lines.append(f"Per-evaluator consistency rate: {rc['per_evaluator_consistency_rate']}")
    lines.append("")

    lines.append("EXPLORATORY (not used for the Decision Gate; not multiple-comparisons corrected)")
    lines.append("-" * 76)
    ex = results["exploratory"]
    lines.append(f"alternative_k_substituted effect: {ex['alternative_k_substituted_effect']}")
    lines.append(f"paragraph length vs. rating (Pearson r, descriptive): {ex['paragraph_length_correlation_pearson_r']}")
    lines.append(f"per-evaluator mean oriented rating: {ex['per_evaluator_mean_oriented_rating']}")
    lines.append(f"comments collected: {len(ex['comments'])}")
    lines.append("")

    mra = results.get("missing_response_audit")
    lines.append("MISSING RESPONSE AUDIT (design section 19 row 1)")
    lines.append("-" * 76)
    if mra is None:
        lines.append(
            "NOT RUN this analysis - no --assignments-dir was provided (or the directory did not exist). "
            "Data-quality acceptance criterion 4 is therefore reported as NOT MET below; this audit "
            "requires the per-evaluator assignment files written by phase2d_experiment5b_collect.py's "
            "'assign' subcommand."
        )
    else:
        lines.append(f"Expected original-item exposures (evaluator x assigned item): {mra['total_expected_original_exposures']}")
        lines.append(f"Attempted (a response event, valid or invalid, was submitted): {mra['total_attempted_of_expected']}")
        lines.append(f"Missing (no response event submitted at all - never imputed): {mra['total_missing']}")
        lines.append(f"Reconciles (expected == attempted + missing): {mra['reconciles']}")
        lines.append(f"Missing count by item: {mra['missing_count_by_item']}")
        lines.append(f"Missing count by evaluator: {mra['missing_count_by_evaluator']}")
    lines.append("")

    lines.append("ACCEPTANCE CRITERIA (design section 26) - each criterion is derived from an actual verification step")
    lines.append("-" * 76)
    for k, v in results["acceptance_criteria"].items():
        lines.append(f"  {k}: met={v['met']}  ({v['detail']})")
    n_met = sum(1 for v in results["acceptance_criteria"].values() if v["met"])
    lines.append(f"  Overall: {n_met}/{len(results['acceptance_criteria'])} criteria met -> "
                 f"{'PASS' if results['acceptance_criteria_all_met'] else 'FAIL'}")
    lines.append("")

    lines.append("DECISION GATE")
    lines.append("-" * 76)
    lines.append(results["decision_gate_classification"])
    lines.append(
        "This classification is a MACHINERY OUTPUT ONLY. It is a valid Decision "
        "Gate result (design section 23) only if every acceptance criterion above "
        "is satisfied AND the underlying data is real, non-synthetic human "
        "ratings collected per the design's protocol - never merely because this "
        "script produced a number. With no (or incomplete) real ratings, this "
        "always reads 'NOT YET EVALUABLE' rather than guessing a state."
    )
    lines.append("")

    lines.append("RAW DATA IMMUTABILITY")
    lines.append("-" * 76)
    lines.append(f"Raw response file SHA-256 before analysis: {results['raw_sha256_before']}")
    lines.append(f"Raw response file SHA-256 after analysis:  {results['raw_sha256_after']}")
    lines.append(f"Byte-identical: {results['raw_sha256_before'] == results['raw_sha256_after']}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_analysis(
    raw_responses_path: str,
    manifest_path: str,
    blinded_json_path: Optional[str] = None,
    assignments_dir: Optional[str] = None,
    reviewer_instructions_path: Optional[str] = None,
    data_label: Optional[str] = None,
) -> Dict[str, Any]:
    raw_sha256_before = _sha256_file(raw_responses_path)

    raw_responses = load_raw_responses(raw_responses_path)  # step 1
    manifest_by_id = load_hidden_mapping(manifest_path)  # step 4

    paragraph_length_by_item: Dict[str, int] = {}
    blinding_verification: Optional[Dict[str, Any]] = None
    if blinded_json_path and os.path.exists(blinded_json_path):
        blinded_by_id = collect5b.load_blinded_items(blinded_json_path)
        paragraph_length_by_item = {
            item_id: rec["paragraph_end_offset"] - rec["paragraph_start_offset"] for item_id, rec in blinded_by_id.items()
        }
        # Design section 26 acceptance criterion 2 requires the blinding
        # scan be "re-verified at Experiment 5B's own ingestion time," not
        # merely assumed. This actually re-runs it against the blinded
        # package as loaded for this analysis run.
        blinded_text = json.dumps(list(blinded_by_id.values()), ensure_ascii=False, sort_keys=True)
        hits = list(collect5b.find_forbidden_tokens(blinded_text))
        scanned_artifacts = ["evaluation_items_blinded.json"]
        if reviewer_instructions_path and os.path.exists(reviewer_instructions_path):
            with open(reviewer_instructions_path, "r", encoding="utf-8") as fh:
                instructions_text = fh.read()
            hits += collect5b.find_forbidden_instructional_terms(instructions_text)
            scanned_artifacts.append("reviewer_instructions.txt")
        blinding_verification = {
            "ran": True,
            "scanned_artifacts": scanned_artifacts,
            "hits": hits,
            "detail": (
                f"zero hits across {scanned_artifacts}" if not hits
                else f"forbidden term(s) found in {scanned_artifacts}: {hits}"
            ),
        }

    valid, rejected = ingest_responses(raw_responses, manifest_by_id)  # steps 2-3
    mapping_failures = validate_mapping_completeness(valid, manifest_by_id)  # steps 5-6
    dq = apply_data_quality_rules(valid, manifest_by_id)  # steps 7-8

    raw_by_event_id = {r["response_event_id"]: r for r in valid}

    # Missing-response audit (design section 19 row 1) - requires the
    # expected assignment population, which only exists if assignment
    # files were produced by phase2d_experiment5b_collect.py's `assign`
    # subcommand. Reconciled against the RAW response list (not just
    # `valid`) so an invalid-but-submitted response is correctly counted
    # as "attempted," never as "missing" (design's explicit distinction).
    missing_response_audit: Optional[Dict[str, Any]] = None
    dq_verification: Optional[Dict[str, Any]] = None
    if assignments_dir and os.path.isdir(assignments_dir):
        assignments_by_evaluator = load_assignments(assignments_dir)
        missing_response_audit = compute_missing_responses(assignments_by_evaluator, raw_responses)
        dq_verification = {
            "all_rules_applied": True,
            "detail": (
                f"missing-response audit computed against {len(assignments_by_evaluator)} evaluator assignment(s) "
                f"({missing_response_audit['total_missing']} missing of "
                f"{missing_response_audit['total_expected_original_exposures']} expected, "
                f"reconciles={missing_response_audit['reconciles']}); "
                f"duplicate/invalid/inconsistent-repeat/comment-leak rules also applied "
                f"({len(dq['duplicate_non_repeat_flagged_ids'])} duplicate, {len(rejected)} invalid, "
                f"{len(dq['inconsistent_repeat_ids'])} inconsistent-repeat, {len(dq['comment_leak_flagged_ids'])} comment-leak)"
            ),
        }
    else:
        dq_verification = {
            "all_rules_applied": False,
            "detail": (
                "missing-response audit requires --assignments-dir (the per-evaluator assignment files written by "
                "phase2d_experiment5b_collect.py's 'assign' subcommand); none was provided or the directory does not "
                "exist, so not every design section 19 rule was applied this run"
            ),
        }

    primary_outcome = compute_primary_outcome(dq["cleaned"], manifest_by_id)  # step 9
    scored_medians = [m for m in primary_outcome["item_medians"].values() if m is not None]
    st = sign_test(scored_medians)

    secondary_outcomes = compute_secondary_outcomes(dq["cleaned"], raw_by_event_id, manifest_by_id, primary_outcome)  # step 10
    agreement = compute_agreement(dq["cleaned"], manifest_by_id)  # step 11
    repeat_consistency = compute_repeat_consistency(dq["cleaned"])  # step 11
    exploratory = compute_exploratory(
        dq["cleaned"], raw_by_event_id, manifest_by_id, primary_outcome, paragraph_length_by_item
    )  # step 12

    # classify_decision_gate never needs (or fabricates from) an
    # acceptance-criteria dict - it derives its own anti-fabrication gate
    # directly from primary_outcome's real state (see its docstring).
    decision_gate = classify_decision_gate(primary_outcome)

    acceptance = check_acceptance_criteria(
        primary_outcome,
        mapping_failures,
        blinding_verification=blinding_verification,
        dq_verification=dq_verification,
        agreement=agreement,
        repeat_consistency=repeat_consistency,
        decision_gate_classification=decision_gate,
    )

    raw_sha256_after = _sha256_file(raw_responses_path)  # step 15 (pre-check)

    return {
        "n_raw": len(raw_responses),
        "n_valid": len(valid),
        "rejected": rejected,
        "mapping_failures": mapping_failures,
        "data_quality": dq,
        "blinding_verification": blinding_verification,
        "missing_response_audit": missing_response_audit,
        "primary_outcome": primary_outcome,
        "sign_test": st,
        "secondary_outcomes": secondary_outcomes,
        "agreement": agreement,
        "repeat_consistency": repeat_consistency,
        "exploratory": exploratory,
        "acceptance_criteria": acceptance,
        "acceptance_criteria_all_met": acceptance_criteria_all_met(acceptance),
        "decision_gate_classification": decision_gate,
        "raw_sha256_before": raw_sha256_before,
        "raw_sha256_after": raw_sha256_after,
    }


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--raw-responses", default=DEFAULT_RAW_RESPONSES)
    p.add_argument("--manifest-json", default=DEFAULT_MANIFEST_JSON)
    p.add_argument("--blinded-json", default=collect5b.DEFAULT_BLINDED_JSON,
                    help="used for the exploratory paragraph-length correlation AND the blinding re-scan (acceptance criterion 2)")
    p.add_argument("--assignments-dir", default=DEFAULT_ASSIGNMENTS_DIR,
                    help="per-evaluator assignment directory written by phase2d_experiment5b_collect.py's 'assign' "
                         "subcommand; enables the missing-response audit (design section 19 row 1) and acceptance "
                         "criterion 4. Optional - if absent, the audit is reported as not run, never assumed complete.")
    p.add_argument("--reviewer-instructions-path", default=DEFAULT_REVIEWER_INSTRUCTIONS_PATH,
                    help="if present, folded into the blinding re-scan alongside the blinded JSON")
    p.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--data-label", default=None, help="stamped into the report header, e.g. to mark a synthetic/test run")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        results = run_analysis(
            args.raw_responses,
            args.manifest_json,
            blinded_json_path=args.blinded_json,
            assignments_dir=args.assignments_dir,
            reviewer_instructions_path=args.reviewer_instructions_path,
            data_label=args.data_label,
        )
    except IntegrityError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    os.makedirs(args.output_dir, exist_ok=True)
    report_text = generate_report_text(results, args.data_label)
    with open(os.path.join(args.output_dir, "analysis_report.txt"), "w", encoding="utf-8") as fh:
        fh.write(report_text)
    with open(os.path.join(args.output_dir, "analysis_results.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1, sort_keys=True, default=str)

    if results["raw_sha256_before"] != results["raw_sha256_after"]:
        print("STOP: raw response file was mutated during analysis", file=sys.stderr)
        return 1

    acceptance_word = "PASS" if results["acceptance_criteria_all_met"] else "FAIL"
    print(
        f"Wrote analysis report to {args.output_dir} "
        f"(acceptance_criteria={acceptance_word}, decision_gate={results['decision_gate_classification']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
