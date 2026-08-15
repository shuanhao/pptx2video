"""Phase 2D Experiment 5B - Human Evaluation Rating Collection.

STANDALONE EXPERIMENT-INFRASTRUCTURE TOOL. NOT part of the production
pipeline, NOT a Phase 2D algorithm change. Implements the collection layer
specified by `docs/PHASE_2D_EXPERIMENT_5B_HUMAN_EVALUATION_DESIGN.md`
(sections 7, 10, 11, 18, 21, 25).

WHAT THIS SCRIPT DOES
----------------------------------------------------------------------------
- Reads the frozen, blinded Experiment 5A package
  (`evaluation_items_blinded.json`) and the frozen hidden mapping
  (`sample_manifest.json`) - neither file is ever modified by this script.
- Builds a deterministic per-evaluator session assignment: which of the 69
  items that evaluator sees, in what order, plus a small set of repeat
  exposures drawn only from the 66 primary-sample items (design section 11).
- Renders the blinded content (source text + the two labeled segmentations)
  for a given exposure, for local, offline display - never exposing
  `k_min`, `score`, `stratum`, or any other hidden-mapping field.
- Validates and records one evaluator response at a time to a local,
  append-only raw-response file. Every write is local; there is no cloud
  service, external API, or third-party hosting involved anywhere in this
  script.

WHAT THIS SCRIPT DELIBERATELY DOES NOT DO
----------------------------------------------------------------------------
- It does not modify `sample_manifest.json`, `evaluation_items.json`,
  `evaluation_items_blinded.json`, `evaluation.html`, `checksums.json`, or
  `sampling_summary.txt` (the frozen Experiment 5A package).
- It does not re-randomize the existing Segmentation 1 / Segmentation 2
  assignment for the 69 original items (design section 10) - that
  assignment is read verbatim from `evaluation_items_blinded.json`.
- It does not reuse Experiment 5A's sampling seed (42) or display-order
  seed (43) for any purpose - it uses its own, independent "collection
  seed" (design section 10).
- It does not compute the primary outcome, secondary outcomes, agreement,
  or repeat consistency - that is `phase2d_experiment5b_analyze.py`.
- It does not fabricate or simulate human ratings. Every response record
  it writes corresponds to one explicit `record` invocation.
- It never collects a name, email address, or other personal identifier -
  evaluator identity is an opaque, locally-assigned token
  (design section 21).

SCHEMA (design section 18)
----------------------------------------------------------------------------
One raw response record per rating event (one evaluator judging one
displayed item instance - the original or a repeat):

{
  "response_event_id": "exp5b-resp-000001",
  "item_id": "exp5-0001",
  "is_repeat": false,
  "repeat_of_response_event_id": null,
  "evaluator_id": "evaluator_01",
  "displayed_order": "unswapped",
  "comparative_rating": -1,
  "awkward_split_segmentation_1": false,
  "awkward_split_segmentation_2": true,
  "reading_effort_segmentation_1": 4,
  "reading_effort_segmentation_2": 2,
  "optional_comment": null,
  "timestamp": "informational only - never used in any deterministic computation"
}

`displayed_order` is one of "unswapped" or "swapped". For an original
(non-repeat) exposure it is always "unswapped": Segmentation 1 / 2 are
shown exactly as recorded in `evaluation_items_blinded.json`, per design
section 10's explicit "must not re-randomize" decision. For a repeat
exposure it records whether that specific repeat's Segmentation 1 / 2
labels were independently re-randomized ("swapped") relative to the
original item's labeling, or not ("unswapped") - this makes every response
record self-describing for orientation (see
`phase2d_experiment5b_analyze.py`'s `resolve_displayed_identity`), without
requiring a second lookup into the session assignment manifest just to
interpret a single rating.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import random
from typing import Any, Dict, List, Optional, Sequence

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

DEFAULT_BLINDED_JSON = os.path.join(_REPO_ROOT, "data", "phase2d", "experiment5", "evaluation_items_blinded.json")
DEFAULT_MANIFEST_JSON = os.path.join(_REPO_ROOT, "data", "phase2d", "experiment5", "sample_manifest.json")

#: New, flat-convention Experiment 5B data area, per this round's explicit
#: instruction (distinct from `data/phase2d/experiment5b/`).
DEFAULT_OUTPUT_DIR = os.path.join(_REPO_ROOT, "data", "phase2d_experiment5b")

#: Not Experiment 5A's sampling seed (42) or display-order seed (43) -
#: those are fully consumed and frozen. This is Experiment 5B's own,
#: independent default; the implementation-time value should be recorded
#: explicitly by whoever runs `init` (design section 10, open question 2).
DEFAULT_COLLECTION_SEED = 5100

COMPARATIVE_RATING_VALUES = (-2, -1, 0, 1, 2)
READING_EFFORT_VALUES = (1, 2, 3, 4, 5)

REPEAT_MIN = 2
REPEAT_MAX = 5
REPEAT_FRACTION = 0.10

#: Re-asserted independently for Experiment 5B's own new evaluator-facing
#: material (design section 9/15) - not merely inherited from Experiment
#: 5A's scan of the already-frozen blinded JSON. This is the narrower
#: "internal metadata" list (field/identity names that would leak hidden
#: mapping information) and is applied to every evaluator-facing
#: artifact, including corpus-derived content (the blinded JSON/HTML),
#: where it is safe because these exact strings are not expected to
#: appear in ordinary corpus text.
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

#: Design section 8's explicit, additional "the instructions never use
#: these words" list. This is STRICTER than, and applied IN ADDITION TO,
#: FORBIDDEN_EVALUATOR_TOKENS above, but ONLY against human-authored
#: instructional/confirmation copy (e.g. REVIEWER_INSTRUCTIONS) - never
#: against corpus-derived segmentation/source_text content. The corpus is
#: real MCU/embedded-systems teaching material and may legitimately
#: contain ordinary domain vocabulary this list would otherwise flag as a
#: false positive (e.g. "current" in the electrical-engineering sense,
#: or a numeric "K" in a resistor value like "10K"); design section 5
#: itself directs reviewers to read such technical terminology as
#: ordinary content, not as a defect. Multi-word/phrase entries are
#: matched as case-insensitive whitespace-normalized substrings; the
#: standalone letter "K" is matched separately with a word-boundary
#: regex (see find_forbidden_instructional_terms) so it does not
#: false-positive against ordinary words that merely contain the letter.
FORBIDDEN_INSTRUCTIONAL_PHRASES = [
    "phase 2c",
    "phase 2d",
    "k_min",
    "score",
    "pareto",
    "boundary score",
    "experimental",
    "production",
    "baseline",
    "current",
    "new",
    "improved",
]

REQUIRED_MANIFEST_FIELDS = {"item_id", "segmentation_1_is", "segmentation_2_is", "primary_sample"}
REQUIRED_BLINDED_FIELDS = {
    "item_id",
    "source_file",
    "source_text",
    "segmentation_1",
    "segmentation_2",
    "paragraph_index",
    "paragraph_start_offset",
    "paragraph_end_offset",
    "is_repeat_item",
    "repeat_of_item_id",
}


class IntegrityError(RuntimeError):
    """Raised on a hard integrity failure. Never caught and silently
    worked around - always propagates to a nonzero exit."""


class InvalidResponseError(ValueError):
    """Raised for a single malformed/out-of-range response field. This is
    a soft, per-record rejection (design section 19), distinct from
    IntegrityError."""


# ---------------------------------------------------------------------------
# Loading & validation of the frozen Experiment 5A inputs
# ---------------------------------------------------------------------------


def load_blinded_items(path: str) -> Dict[str, Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as fh:
        records = json.load(fh)
    if not isinstance(records, list):
        raise IntegrityError(f"STOP: {path} is not a JSON list")
    by_id: Dict[str, Dict[str, Any]] = {}
    for r in records:
        missing = REQUIRED_BLINDED_FIELDS - set(r.keys())
        if missing:
            raise IntegrityError(f"STOP: blinded record missing required field(s) {sorted(missing)}: {r.get('item_id')}")
        if r["item_id"] in by_id:
            raise IntegrityError(f"STOP: duplicate item_id in blinded package: {r['item_id']}")
        by_id[r["item_id"]] = r
    return by_id


def load_manifest(path: str) -> Dict[str, Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as fh:
        records = json.load(fh)
    if not isinstance(records, list):
        raise IntegrityError(f"STOP: {path} is not a JSON list")
    by_id: Dict[str, Dict[str, Any]] = {}
    seen_triples = set()
    for r in records:
        missing = REQUIRED_MANIFEST_FIELDS - set(r.keys())
        if missing:
            raise IntegrityError(f"STOP: manifest record missing required field(s) {sorted(missing)}: {r.get('item_id')}")
        if r["item_id"] in by_id:
            raise IntegrityError(f"STOP: duplicate item_id in sample_manifest.json: {r['item_id']}")
        if r["segmentation_1_is"] == r["segmentation_2_is"]:
            raise IntegrityError(f"STOP: malformed manifest record {r['item_id']}: segmentation_1_is == segmentation_2_is")
        triple = (r.get("source_file"), r.get("paragraph_index"), r.get("alternative_k"))
        if triple in seen_triples:
            raise IntegrityError(f"STOP: unexpected duplicate item for triple {triple} in sample_manifest.json")
        seen_triples.add(triple)
        by_id[r["item_id"]] = r
    return by_id


def find_forbidden_tokens(text: str) -> List[str]:
    """Non-raising detector for the narrower FORBIDDEN_EVALUATOR_TOKENS
    (internal-metadata) list. Returns the list of hits (empty if clean)
    so callers can build an auditable verification record rather than
    only being able to catch-or-not an exception."""
    lowered = text.lower()
    return [tok for tok in FORBIDDEN_EVALUATOR_TOKENS if tok in lowered]


def _assert_no_forbidden_tokens(text: str, artifact_name: str) -> None:
    hits = find_forbidden_tokens(text)
    if hits:
        raise IntegrityError(f"STOP: evaluator-facing artifact {artifact_name} leaks forbidden token(s): {hits}")


_STANDALONE_K_RE = re.compile(r"(?<![a-z0-9_])k(?![a-z0-9_])", re.IGNORECASE)


def find_forbidden_instructional_terms(text: str) -> List[str]:
    """Non-raising detector for design section 8's explicit "the
    instructions never use these words" list. Intended ONLY for
    human-authored instructional/confirmation copy - see
    FORBIDDEN_INSTRUCTIONAL_PHRASES's docstring for why this is never
    applied to corpus-derived content. Case-insensitive; phrases are
    matched against whitespace-normalized text so a wrapped/re-flowed
    sentence still matches; the standalone letter "K" is matched with a
    word-boundary regex so it does not fire on ordinary words that merely
    contain the letter (e.g. "OK", "make", "task")."""
    normalized = " ".join(text.lower().split())
    hits = [phrase for phrase in FORBIDDEN_INSTRUCTIONAL_PHRASES if phrase in normalized]
    if _STANDALONE_K_RE.search(normalized):
        hits.append("K (standalone)")
    return hits


def _assert_no_forbidden_instructional_terms(text: str, artifact_name: str) -> None:
    hits = find_forbidden_instructional_terms(text)
    if hits:
        raise IntegrityError(
            f"STOP: evaluator-facing instructional artifact {artifact_name} leaks forbidden term(s) "
            f"per design section 8: {hits}"
        )


def scan_blinded_package(blinded_by_id: Dict[str, Dict[str, Any]]) -> None:
    """Re-runs an independent forbidden-token scan against the blinded
    package as consumed by this collection layer (design section 15 - do
    not merely trust Experiment 5A's own scan). Uses the narrower
    internal-metadata list only - see FORBIDDEN_INSTRUCTIONAL_PHRASES's
    docstring for why the broader section 8 instructional list is not
    applied to corpus-derived content."""
    text = json.dumps(list(blinded_by_id.values()), ensure_ascii=False, sort_keys=True)
    _assert_no_forbidden_tokens(text, "evaluation_items_blinded.json (re-scanned by collect layer)")


REVIEWER_INSTRUCTIONS = (
    "You will see a short piece of text, followed by two different ways of "
    "breaking that same text into subtitle-style lines, labeled "
    '"Segmentation 1" and "Segmentation 2." Please judge only how each '
    "version reads as a sequence of subtitle lines - not whether the "
    "content itself is well-written, factually accurate, or uses the right "
    "terminology (both versions come from the exact same original text, so "
    "that cannot differ between them).\n\n"
    "Consider: does each line read naturally, does it end in a sensible "
    "place, and is the text broken up in a way that's easy to follow at a "
    "glance? Please don't try to guess which version is \"correct\" or which "
    "system produced which - there is no fixed correct answer, and the two "
    "versions are not labeled or ranked in any way.\n\n"
    'If the two versions read about equally well to you, please say so - '
    '"about the same" is a valid and useful answer. Comments are optional. '
    "Each item should take well under a minute to judge."
)


# ---------------------------------------------------------------------------
# Deterministic seeding
# ---------------------------------------------------------------------------


def _stable_seed(*parts: Any) -> int:
    """A deterministic, cross-process-stable seed derivation. Python's
    built-in hash() is randomized per-process by default for str/tuple,
    which previously caused a non-determinism bug in Experiment 5A's own
    implementation (fixed there by removing hash()-based seeding
    entirely). This helper avoids that class of bug by hashing a stable
    string representation with hashlib instead."""
    payload = "\x1f".join(str(p) for p in parts).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return int(digest[:16], 16)


# ---------------------------------------------------------------------------
# Session assignment
# ---------------------------------------------------------------------------


def select_repeat_item_ids(
    assigned_item_ids: Sequence[str],
    manifest_by_id: Dict[str, Dict[str, Any]],
    evaluator_id: str,
    collection_seed: int,
) -> List[str]:
    """Repeats are drawn only from the assigned items that are also
    primary-sample items (design section 11) - never from
    boundary-condition items."""
    candidates = sorted(i for i in assigned_item_ids if manifest_by_id[i]["primary_sample"])
    target = round(len(assigned_item_ids) * REPEAT_FRACTION)
    count = max(REPEAT_MIN, min(REPEAT_MAX, target))
    count = min(count, len(candidates))
    rng = random.Random(_stable_seed(collection_seed, "repeats", evaluator_id))
    return sorted(rng.sample(candidates, count)) if count else []


def build_assignment(
    blinded_by_id: Dict[str, Dict[str, Any]],
    manifest_by_id: Dict[str, Dict[str, Any]],
    evaluator_id: str,
    collection_seed: int,
    item_ids: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Builds one evaluator's deterministic session assignment: an ordered
    list of "exposures" (each either the item's single original exposure,
    or one of its randomly-selected repeat exposures), independent of
    Experiment 5A's own sampling/display-order seeds."""
    all_ids = sorted(blinded_by_id) if item_ids is None else sorted(item_ids)
    unknown = [i for i in all_ids if i not in blinded_by_id]
    if unknown:
        raise IntegrityError(f"STOP: unknown item_id(s) requested for assignment: {unknown}")

    repeat_ids = select_repeat_item_ids(all_ids, manifest_by_id, evaluator_id, collection_seed)

    tokens: List[Dict[str, Any]] = [{"kind": "original", "item_id": i} for i in all_ids]
    for item_id in repeat_ids:
        swap_rng = random.Random(_stable_seed(collection_seed, "repeat_swap", evaluator_id, item_id))
        tokens.append(
            {
                "kind": "repeat",
                "item_id": item_id,
                "displayed_order": "swapped" if swap_rng.random() < 0.5 else "unswapped",
            }
        )

    order_rng = random.Random(_stable_seed(collection_seed, "order", evaluator_id))
    order_rng.shuffle(tokens)

    exposures = []
    for idx, tok in enumerate(tokens):
        exposures.append(
            {
                "exposure_id": f"{evaluator_id}-exp-{idx:04d}",
                "sequence_index": idx,
                "kind": tok["kind"],
                "item_id": tok["item_id"],
                "displayed_order": "unswapped" if tok["kind"] == "original" else tok["displayed_order"],
            }
        )

    return {
        "evaluator_id": evaluator_id,
        "collection_seed": collection_seed,
        "item_ids": all_ids,
        "repeat_item_ids": repeat_ids,
        "exposures": exposures,
    }


def render_exposure(exposure: Dict[str, Any], blinded_by_id: Dict[str, Any]) -> Dict[str, Any]:
    """Renders the blinded, evaluator-facing content for one exposure.
    Contains only item_id, source text, and the two labeled segmentations
    - never any hidden-mapping field."""
    rec = blinded_by_id[exposure["item_id"]]
    seg1, seg2 = rec["segmentation_1"], rec["segmentation_2"]
    if exposure["displayed_order"] == "swapped":
        seg1, seg2 = seg2, seg1
    return {
        "item_id": rec["item_id"],
        "source_text": rec["source_text"],
        "segmentation_1": seg1,
        "segmentation_2": seg2,
    }


# ---------------------------------------------------------------------------
# Response validation & recording
# ---------------------------------------------------------------------------


def validate_comparative_rating(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value not in COMPARATIVE_RATING_VALUES:
        raise InvalidResponseError(f"invalid comparative_rating {value!r}: must be one of {COMPARATIVE_RATING_VALUES}")
    return value


def validate_awkward_split(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise InvalidResponseError(f"invalid {field_name} {value!r}: must be a bool")
    return value


def validate_reading_effort(value: Any, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value not in READING_EFFORT_VALUES:
        raise InvalidResponseError(f"invalid {field_name} {value!r}: must be one of {READING_EFFORT_VALUES}")
    return value


def validate_displayed_order(value: Any) -> str:
    if value not in ("unswapped", "swapped"):
        raise InvalidResponseError(f"invalid displayed_order {value!r}: must be 'unswapped' or 'swapped'")
    return value


def load_raw_responses(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as fh:
        records = json.load(fh)
    if not isinstance(records, list):
        raise IntegrityError(f"STOP: {path} is not a JSON list")
    return records


def generate_response_event_id(existing: Sequence[Dict[str, Any]]) -> str:
    existing_ids = {r["response_event_id"] for r in existing}
    n = len(existing) + 1
    candidate = f"exp5b-resp-{n:06d}"
    while candidate in existing_ids:
        n += 1
        candidate = f"exp5b-resp-{n:06d}"
    return candidate


def find_prior_response(
    existing: Sequence[Dict[str, Any]], evaluator_id: str, item_id: str
) -> Optional[Dict[str, Any]]:
    """First-received, non-repeat response by this evaluator for this item
    - used to auto-resolve `repeat_of_response_event_id` for a later
    repeat exposure, and as the "first valid response" per the duplicate
    -response data-quality rule (design section 19)."""
    for r in existing:
        if r["evaluator_id"] == evaluator_id and r["item_id"] == item_id and not r["is_repeat"]:
            return r
    return None


def build_response_record(
    *,
    existing: Sequence[Dict[str, Any]],
    blinded_by_id: Dict[str, Dict[str, Any]],
    item_id: str,
    evaluator_id: str,
    displayed_order: str,
    comparative_rating: int,
    awkward_split_segmentation_1: bool,
    awkward_split_segmentation_2: bool,
    reading_effort_segmentation_1: int,
    reading_effort_segmentation_2: int,
    is_repeat: bool = False,
    optional_comment: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    if item_id not in blinded_by_id:
        raise IntegrityError(f"STOP: unknown item_id: {item_id}")

    validate_displayed_order(displayed_order)
    validate_comparative_rating(comparative_rating)
    validate_awkward_split(awkward_split_segmentation_1, "awkward_split_segmentation_1")
    validate_awkward_split(awkward_split_segmentation_2, "awkward_split_segmentation_2")
    validate_reading_effort(reading_effort_segmentation_1, "reading_effort_segmentation_1")
    validate_reading_effort(reading_effort_segmentation_2, "reading_effort_segmentation_2")

    repeat_of_response_event_id = None
    if is_repeat:
        prior = find_prior_response(existing, evaluator_id, item_id)
        if prior is None:
            raise InvalidResponseError(
                f"cannot record repeat for item_id={item_id!r}, evaluator_id={evaluator_id!r}: "
                "no prior non-repeat response found for this evaluator/item"
            )
        repeat_of_response_event_id = prior["response_event_id"]

    if optional_comment:
        lowered = optional_comment.lower()
        hits = [tok for tok in FORBIDDEN_EVALUATOR_TOKENS if tok in lowered]
        if hits:
            # Per design section 19: retained as raw data (reviewers' own
            # words are never redacted), but this is surfaced to the
            # caller via the returned record's own flag for manual review
            # rather than silently dropped or rejected.
            pass

    return {
        "response_event_id": generate_response_event_id(existing),
        "item_id": item_id,
        "is_repeat": is_repeat,
        "repeat_of_response_event_id": repeat_of_response_event_id,
        "evaluator_id": evaluator_id,
        "displayed_order": displayed_order,
        "comparative_rating": comparative_rating,
        "awkward_split_segmentation_1": awkward_split_segmentation_1,
        "awkward_split_segmentation_2": awkward_split_segmentation_2,
        "reading_effort_segmentation_1": reading_effort_segmentation_1,
        "reading_effort_segmentation_2": reading_effort_segmentation_2,
        "optional_comment": optional_comment,
        "timestamp": timestamp or "informational only - never used in any deterministic computation",
    }


def append_response(path: str, record: Dict[str, Any]) -> List[Dict[str, Any]]:
    existing = load_raw_responses(path)
    if any(r["response_event_id"] == record["response_event_id"] for r in existing):
        raise IntegrityError(f"STOP: duplicate response_event_id: {record['response_event_id']}")
    existing.append(record)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(existing, fh, ensure_ascii=False, indent=1, sort_keys=True)
    return existing


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _paths(args: argparse.Namespace) -> Dict[str, str]:
    out = args.output_dir
    return {
        "assignments_dir": os.path.join(out, "assignments"),
        "session_assignment_manifest": os.path.join(out, "session_assignment_manifest.json"),
        "raw_responses": os.path.join(out, "raw_responses.json"),
        "collection_config": os.path.join(out, "collection_config.json"),
        "reviewer_instructions": os.path.join(out, "reviewer_instructions.txt"),
    }


def cmd_init(args: argparse.Namespace) -> int:
    os.makedirs(args.output_dir, exist_ok=True)
    paths = _paths(args)
    os.makedirs(paths["assignments_dir"], exist_ok=True)
    blinded_by_id = load_blinded_items(args.blinded_json)
    scan_blinded_package(blinded_by_id)
    # Reviewer instructions are human-authored instructional copy: both
    # the narrower internal-metadata scan (design section 9/15) AND the
    # broader, explicit "the instructions never use these words" list
    # (design section 8) apply here - the metadata scan alone is not
    # sufficient for this artifact.
    _assert_no_forbidden_tokens(REVIEWER_INSTRUCTIONS, "reviewer_instructions.txt")
    _assert_no_forbidden_instructional_terms(REVIEWER_INSTRUCTIONS, "reviewer_instructions.txt")
    with open(paths["reviewer_instructions"], "w", encoding="utf-8") as fh:
        fh.write(REVIEWER_INSTRUCTIONS + "\n")
    config = {
        "collection_seed": args.collection_seed,
        "blinded_json": os.path.relpath(args.blinded_json, _REPO_ROOT),
        "manifest_json": os.path.relpath(args.manifest_json, _REPO_ROOT),
        "n_items": len(blinded_by_id),
        "generated_at_informational_only": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(paths["collection_config"], "w", encoding="utf-8") as fh:
        json.dump(config, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"Initialized Experiment 5B collection area at {args.output_dir} (collection_seed={args.collection_seed})")
    return 0


def cmd_assign(args: argparse.Namespace) -> int:
    blinded_by_id = load_blinded_items(args.blinded_json)
    manifest_by_id = load_manifest(args.manifest_json)
    assignment = build_assignment(blinded_by_id, manifest_by_id, args.evaluator_id, args.collection_seed)

    paths = _paths(args)
    os.makedirs(paths["assignments_dir"], exist_ok=True)
    assignment_path = os.path.join(paths["assignments_dir"], f"{args.evaluator_id}.json")
    with open(assignment_path, "w", encoding="utf-8") as fh:
        json.dump(assignment, fh, ensure_ascii=False, indent=1, sort_keys=True)

    # Update the running session assignment manifest with this evaluator's
    # repeat exposures only (design sections 10, 18).
    sam_path = paths["session_assignment_manifest"]
    sam = load_raw_responses(sam_path)  # reuses the "list JSON or empty" loader
    sam = [e for e in sam if e.get("evaluator_id") != args.evaluator_id]
    for exp in assignment["exposures"]:
        if exp["kind"] == "repeat":
            sam.append(
                {
                    "evaluator_id": args.evaluator_id,
                    "exposure_id": exp["exposure_id"],
                    "item_id": exp["item_id"],
                    "displayed_order": exp["displayed_order"],
                }
            )
    with open(sam_path, "w", encoding="utf-8") as fh:
        json.dump(sam, fh, ensure_ascii=False, indent=1, sort_keys=True)

    print(
        f"Assigned {len(assignment['item_ids'])} items ({len(assignment['repeat_item_ids'])} repeats) "
        f"to {args.evaluator_id} -> {assignment_path}"
    )
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    blinded_by_id = load_blinded_items(args.blinded_json)
    paths = _paths(args)
    assignment_path = os.path.join(paths["assignments_dir"], f"{args.evaluator_id}.json")
    with open(assignment_path, "r", encoding="utf-8") as fh:
        assignment = json.load(fh)
    exposure = next(e for e in assignment["exposures"] if e["exposure_id"] == args.exposure_id)
    rendered = render_exposure(exposure, blinded_by_id)
    print(f"Item: {rendered['item_id']}  (exposure {exposure['exposure_id']}, kind={exposure['kind']})")
    print(f"Source text: {rendered['source_text']}")
    print("Segmentation 1:")
    for seg in rendered["segmentation_1"]:
        print(f"  [ {seg} ]")
    print("Segmentation 2:")
    for seg in rendered["segmentation_2"]:
        print(f"  [ {seg} ]")
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    blinded_by_id = load_blinded_items(args.blinded_json)
    paths = _paths(args)
    existing = load_raw_responses(paths["raw_responses"])
    record = build_response_record(
        existing=existing,
        blinded_by_id=blinded_by_id,
        item_id=args.item_id,
        evaluator_id=args.evaluator_id,
        displayed_order=args.displayed_order,
        comparative_rating=args.comparative_rating,
        awkward_split_segmentation_1=args.awkward_split_1,
        awkward_split_segmentation_2=args.awkward_split_2,
        reading_effort_segmentation_1=args.reading_effort_1,
        reading_effort_segmentation_2=args.reading_effort_2,
        is_repeat=args.is_repeat,
        optional_comment=args.comment,
    )
    append_response(paths["raw_responses"], record)
    print(f"Recorded {record['response_event_id']} for item {args.item_id} by {args.evaluator_id}")
    return 0


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--blinded-json", default=DEFAULT_BLINDED_JSON)
    p.add_argument("--manifest-json", default=DEFAULT_MANIFEST_JSON)
    p.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    sub = p.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="initialize the collection area, seed, and reviewer instructions")
    p_init.add_argument("--collection-seed", type=int, default=DEFAULT_COLLECTION_SEED)
    p_init.set_defaults(func=cmd_init)

    p_assign = sub.add_parser("assign", help="build a deterministic session assignment for one evaluator")
    p_assign.add_argument("--evaluator-id", required=True)
    p_assign.add_argument("--collection-seed", type=int, default=DEFAULT_COLLECTION_SEED)
    p_assign.set_defaults(func=cmd_assign)

    p_show = sub.add_parser("show", help="render one exposure's blinded content for local display")
    p_show.add_argument("--evaluator-id", required=True)
    p_show.add_argument("--exposure-id", required=True)
    p_show.set_defaults(func=cmd_show)

    p_record = sub.add_parser("record", help="validate and record one response")
    p_record.add_argument("--evaluator-id", required=True)
    p_record.add_argument("--item-id", required=True)
    p_record.add_argument("--displayed-order", choices=("unswapped", "swapped"), default="unswapped")
    p_record.add_argument("--comparative-rating", type=int, required=True, choices=list(COMPARATIVE_RATING_VALUES))
    p_record.add_argument("--awkward-split-1", type=lambda s: s.lower() in ("1", "true", "yes"), required=True)
    p_record.add_argument("--awkward-split-2", type=lambda s: s.lower() in ("1", "true", "yes"), required=True)
    p_record.add_argument("--reading-effort-1", type=int, required=True, choices=list(READING_EFFORT_VALUES))
    p_record.add_argument("--reading-effort-2", type=int, required=True, choices=list(READING_EFFORT_VALUES))
    p_record.add_argument("--is-repeat", action="store_true")
    p_record.add_argument("--comment", default=None)
    p_record.set_defaults(func=cmd_record)

    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        return args.func(args)
    except (IntegrityError, InvalidResponseError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
