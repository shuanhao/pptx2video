"""Tests for `scripts/phase2d_experiment5b_collect.py` (Phase 2D
Experiment 5B - Human Evaluation Rating Collection).

Scope: these tests cover the collection layer's own machinery only -
loading/validating the frozen Experiment 5A inputs, deterministic session
assignment, repeat selection, response validation, and append-only raw
response storage. They use small synthetic fixtures, never the real
69-item Experiment 5A package or real human ratings, and they never
modify `data/phase2d/experiment5/` (the frozen Experiment 5A package) or
any Phase 2D production/test file.

`scripts/` is not a package (no `__init__.py`), so the module under test
is loaded by path, mirroring `tests/test_phase2d_experiment5_prepare.py`.
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location(
    "phase2d_experiment5b_collect", ROOT / "scripts" / "phase2d_experiment5b_collect.py"
)
collect5b = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(collect5b)


# ---------------------------------------------------------------------------
# Synthetic fixtures
# ---------------------------------------------------------------------------


def _blinded_record(item_id, source_file="examples/notes/fixture1.txt", paragraph_index=0, is_repeat_item=False):
    return {
        "item_id": item_id,
        "source_file": source_file,
        "source_text": "AB、CD。",
        "segmentation_1": ["AB、", "CD。"],
        "segmentation_2": ["AB", "、CD。"],
        "paragraph_index": paragraph_index,
        "paragraph_start_offset": 0,
        "paragraph_end_offset": 6,
        "is_repeat_item": is_repeat_item,
        "repeat_of_item_id": None,
    }


def _manifest_record(item_id, primary_sample=True, source_file="examples/notes/fixture1.txt", paragraph_index=0,
                      seg1_is="k_min", seg2_is="alternative"):
    return {
        "item_id": item_id,
        "source_file": source_file,
        "paragraph_index": paragraph_index,
        "alternative_k": 3,
        "k_min": 2,
        "primary_sample": primary_sample,
        "boundary_condition_candidate": not primary_sample,
        "segmentation_1_is": seg1_is,
        "segmentation_2_is": seg2_is,
        "stratum": ["B_small_gain"],
        "alternative_k_substituted": False,
        "contains_extreme_narrow_segment": False,
        "delta_k": 1,
        "delta_phase2d_score": 10.0,
        "frontier_size": 2,
        "pareto_frontier": [[2, 5.0], [3, 15.0]],
        "phase2d_score_alternative": 15.0,
        "phase2d_score_k_min": 5.0,
    }


def _make_package(n_items=10, n_boundary=0):
    blinded = {}
    manifest = {}
    for i in range(1, n_items + 1):
        item_id = f"fx-{i:04d}"
        primary = i > n_boundary
        blinded[item_id] = _blinded_record(item_id, paragraph_index=i)
        manifest[item_id] = _manifest_record(item_id, primary_sample=primary, paragraph_index=i)
    return blinded, manifest


class LoadingTests(unittest.TestCase):
    def test_load_blinded_items_roundtrip(self):
        blinded, _ = _make_package(5)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "blinded.json"
            path.write_text(json.dumps(list(blinded.values())), encoding="utf-8")
            loaded = collect5b.load_blinded_items(str(path))
        self.assertEqual(set(loaded.keys()), set(blinded.keys()))

    def test_load_blinded_items_missing_field_raises(self):
        rec = _blinded_record("fx-0001")
        del rec["source_text"]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "blinded.json"
            path.write_text(json.dumps([rec]), encoding="utf-8")
            with self.assertRaises(collect5b.IntegrityError):
                collect5b.load_blinded_items(str(path))

    def test_load_blinded_items_duplicate_item_id_raises(self):
        rec = _blinded_record("fx-0001")
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "blinded.json"
            path.write_text(json.dumps([rec, rec]), encoding="utf-8")
            with self.assertRaises(collect5b.IntegrityError):
                collect5b.load_blinded_items(str(path))

    def test_load_manifest_roundtrip(self):
        _, manifest = _make_package(5)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "manifest.json"
            path.write_text(json.dumps(list(manifest.values())), encoding="utf-8")
            loaded = collect5b.load_manifest(str(path))
        self.assertEqual(set(loaded.keys()), set(manifest.keys()))

    def test_load_manifest_malformed_same_identity_raises(self):
        """A malformed hidden mapping: segmentation_1_is == segmentation_2_is
        for the same item is structurally invalid and must be rejected."""
        rec = _manifest_record("fx-0001", seg1_is="k_min", seg2_is="k_min")
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "manifest.json"
            path.write_text(json.dumps([rec]), encoding="utf-8")
            with self.assertRaises(collect5b.IntegrityError):
                collect5b.load_manifest(str(path))

    def test_load_manifest_duplicate_triple_raises(self):
        rec1 = _manifest_record("fx-0001", source_file="a.txt", paragraph_index=1)
        rec2 = _manifest_record("fx-0002", source_file="a.txt", paragraph_index=1)
        rec1["alternative_k"] = rec2["alternative_k"] = 3
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "manifest.json"
            path.write_text(json.dumps([rec1, rec2]), encoding="utf-8")
            with self.assertRaises(collect5b.IntegrityError):
                collect5b.load_manifest(str(path))

    def test_load_manifest_duplicate_item_id_raises(self):
        rec = _manifest_record("fx-0001")
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "manifest.json"
            path.write_text(json.dumps([rec, rec]), encoding="utf-8")
            with self.assertRaises(collect5b.IntegrityError):
                collect5b.load_manifest(str(path))


class ForbiddenTokenScanTests(unittest.TestCase):
    def test_clean_text_passes(self):
        collect5b._assert_no_forbidden_tokens("hello world", "unit-test")

    def test_forbidden_token_detected(self):
        with self.assertRaises(collect5b.IntegrityError):
            collect5b._assert_no_forbidden_tokens("the k_min segmentation", "unit-test")

    def test_reviewer_instructions_pass_scan(self):
        collect5b._assert_no_forbidden_tokens(collect5b.REVIEWER_INSTRUCTIONS, "reviewer_instructions.txt")

    def test_scan_blinded_package_passes_for_clean_fixture(self):
        blinded, _ = _make_package(5)
        collect5b.scan_blinded_package(blinded)

    def test_scan_blinded_package_detects_leak(self):
        blinded, _ = _make_package(2)
        blinded["fx-0001"]["source_text"] += " pareto"
        with self.assertRaises(collect5b.IntegrityError):
            collect5b.scan_blinded_package(blinded)


class ForbiddenInstructionalTermsTests(unittest.TestCase):
    """Design section 8's explicit, broader 'the instructions never use
    these words' list, applied to human-authored instructional/UI copy
    (correction round discrepancy A)."""

    # E. Clean evaluator-facing instructions pass both scans.
    def test_reviewer_instructions_pass_extended_scan(self):
        self.assertEqual(collect5b.find_forbidden_instructional_terms(collect5b.REVIEWER_INSTRUCTIONS), [])
        collect5b._assert_no_forbidden_instructional_terms(collect5b.REVIEWER_INSTRUCTIONS, "reviewer_instructions.txt")

    def test_reviewer_instructions_no_longer_contain_new(self):
        # Regression guard for the exact leak found in pre-commit verification.
        self.assertNotIn("new", collect5b.REVIEWER_INSTRUCTIONS.lower().split())
        hits = collect5b.find_forbidden_instructional_terms(collect5b.REVIEWER_INSTRUCTIONS)
        self.assertNotIn("new", hits)

    # A. Every design section 8 forbidden evaluator-facing term is detected.
    def test_every_mandatory_forbidden_term_is_detected(self):
        mandatory_terms = [
            "Phase 2C",
            "Phase 2D",
            "K",
            "K_min",
            "score",
            "Pareto",
            "boundary score",
            "experimental",
            "production",
            "baseline",
            "current",
            "new",
            "improved",
        ]
        for term in mandatory_terms:
            with self.subTest(term=term):
                text = f"This sentence intentionally contains the forbidden term {term} for testing."
                hits = collect5b.find_forbidden_instructional_terms(text)
                self.assertTrue(hits, f"expected {term!r} to be detected, got no hits in: {text!r}")
                with self.assertRaises(collect5b.IntegrityError):
                    collect5b._assert_no_forbidden_instructional_terms(text, "unit-test")

    # B. Case-insensitive detection.
    def test_case_insensitive_detection(self):
        for text in ("PHASE 2C", "phase 2c", "Phase 2C", "PaReTo", "SCORE", "Improved", "BASELINE"):
            with self.subTest(text=text):
                self.assertTrue(collect5b.find_forbidden_instructional_terms(text))

    # C. Standalone "K" detection, with false-positive avoidance.
    def test_standalone_k_detected(self):
        for text in ("the K value", "K=5", "a K of 3", "(K)"):
            with self.subTest(text=text):
                hits = collect5b.find_forbidden_instructional_terms(text)
                self.assertIn("K (standalone)", hits)

    def test_standalone_k_no_false_positive_on_ordinary_words(self):
        for text in ("MCU controls the device", "make sure this works", "OK, that works",
                     "task list", "everything looks fine", "keep it simple"):
            with self.subTest(text=text):
                self.assertEqual(collect5b.find_forbidden_instructional_terms(text), [])

    # D. Phrase detection (multi-word terms), including across a
    # whitespace-normalized (e.g. wrapped) sentence.
    def test_phrase_detection_boundary_score(self):
        self.assertIn("boundary score", collect5b.find_forbidden_instructional_terms("the boundary score is high"))

    def test_phrase_detection_phase_2c_2d(self):
        self.assertTrue(collect5b.find_forbidden_instructional_terms("as used in Phase 2C"))
        self.assertTrue(collect5b.find_forbidden_instructional_terms("as used in Phase 2D"))

    def test_phrase_detection_across_wrapped_whitespace(self):
        wrapped = "this is a\nboundary   score\tvalue"
        self.assertIn("boundary score", collect5b.find_forbidden_instructional_terms(wrapped))

    def test_clean_sentence_has_no_hits(self):
        clean = "Please judge how naturally each line reads and whether it breaks in a sensible place."
        self.assertEqual(collect5b.find_forbidden_instructional_terms(clean), [])

    def test_narrower_metadata_scan_does_not_catch_broader_terms(self):
        # Demonstrates the original bug: the narrower FORBIDDEN_EVALUATOR_TOKENS
        # list alone cannot catch "new"/"current"/"improved"/standalone "K"/
        # "Phase 2C"/"Phase 2D" - only the extended instructional scan does.
        text = "the new, improved, current version, Phase 2C, with a K"
        self.assertEqual(collect5b.find_forbidden_tokens(text), [])
        self.assertTrue(collect5b.find_forbidden_instructional_terms(text))

    def test_cmd_init_scans_instructions_with_extended_list(self):
        # cmd_init must call the extended scan, not merely the narrower one.
        import inspect

        source = inspect.getsource(collect5b.cmd_init)
        self.assertIn("_assert_no_forbidden_instructional_terms", source)


class StableSeedTests(unittest.TestCase):
    def test_deterministic_across_calls(self):
        a = collect5b._stable_seed(42, "repeats", "evaluator_01")
        b = collect5b._stable_seed(42, "repeats", "evaluator_01")
        self.assertEqual(a, b)

    def test_differs_by_evaluator(self):
        a = collect5b._stable_seed(42, "repeats", "evaluator_01")
        b = collect5b._stable_seed(42, "repeats", "evaluator_02")
        self.assertNotEqual(a, b)

    def test_no_python_hash_dependency(self):
        # A regression guard for the Experiment 5A non-determinism bug:
        # _stable_seed must not rely on Python's randomized hash().
        import random as _random

        seed = collect5b._stable_seed(1, "x", "y")
        self.assertIsInstance(seed, int)
        # Must be reproducible in a fresh RNG regardless of PYTHONHASHSEED.
        r1 = _random.Random(seed).random()
        r2 = _random.Random(collect5b._stable_seed(1, "x", "y")).random()
        self.assertEqual(r1, r2)


class RepeatSelectionTests(unittest.TestCase):
    def test_repeats_drawn_only_from_primary_items(self):
        blinded, manifest = _make_package(20, n_boundary=3)
        assigned = sorted(blinded.keys())
        repeats = collect5b.select_repeat_item_ids(assigned, manifest, "evaluator_01", 5100)
        boundary_ids = {i for i, r in manifest.items() if not r["primary_sample"]}
        self.assertTrue(all(i not in boundary_ids for i in repeats))

    def test_repeat_count_floor(self):
        # Very small assignment: 10% would round to <2; floor of 2 applies
        # (bounded by available primary candidates).
        blinded, manifest = _make_package(5, n_boundary=0)
        assigned = sorted(blinded.keys())
        repeats = collect5b.select_repeat_item_ids(assigned, manifest, "evaluator_01", 5100)
        self.assertEqual(len(repeats), 2)

    def test_repeat_count_cap(self):
        blinded, manifest = _make_package(69, n_boundary=3)
        assigned = sorted(blinded.keys())
        repeats = collect5b.select_repeat_item_ids(assigned, manifest, "evaluator_01", 5100)
        self.assertEqual(len(repeats), 5)

    def test_repeat_selection_deterministic(self):
        blinded, manifest = _make_package(30, n_boundary=2)
        assigned = sorted(blinded.keys())
        r1 = collect5b.select_repeat_item_ids(assigned, manifest, "evaluator_07", 5100)
        r2 = collect5b.select_repeat_item_ids(assigned, manifest, "evaluator_07", 5100)
        self.assertEqual(r1, r2)

    def test_repeat_selection_differs_by_evaluator(self):
        blinded, manifest = _make_package(30, n_boundary=2)
        assigned = sorted(blinded.keys())
        r1 = collect5b.select_repeat_item_ids(assigned, manifest, "evaluator_01", 5100)
        r2 = collect5b.select_repeat_item_ids(assigned, manifest, "evaluator_02", 5100)
        self.assertNotEqual(r1, r2)


class AssignmentTests(unittest.TestCase):
    def test_build_assignment_covers_all_items(self):
        blinded, manifest = _make_package(15, n_boundary=1)
        assignment = collect5b.build_assignment(blinded, manifest, "evaluator_01", 5100)
        exposed_originals = {e["item_id"] for e in assignment["exposures"] if e["kind"] == "original"}
        self.assertEqual(exposed_originals, set(blinded.keys()))

    def test_build_assignment_unknown_item_id_raises(self):
        blinded, manifest = _make_package(5)
        with self.assertRaises(collect5b.IntegrityError):
            collect5b.build_assignment(blinded, manifest, "evaluator_01", 5100, item_ids=["does-not-exist"])

    def test_build_assignment_deterministic(self):
        blinded, manifest = _make_package(20, n_boundary=1)
        a1 = collect5b.build_assignment(blinded, manifest, "evaluator_01", 5100)
        a2 = collect5b.build_assignment(blinded, manifest, "evaluator_01", 5100)
        self.assertEqual(a1, a2)

    def test_build_assignment_differs_by_seed(self):
        blinded, manifest = _make_package(20, n_boundary=1)
        a1 = collect5b.build_assignment(blinded, manifest, "evaluator_01", 5100)
        a2 = collect5b.build_assignment(blinded, manifest, "evaluator_01", 9999)
        order1 = [e["exposure_id"] for e in a1["exposures"]]
        order2 = [e["exposure_id"] for e in a2["exposures"]]
        self.assertNotEqual([a1["exposures"][i]["item_id"] for i in range(len(order1))],
                             [a2["exposures"][i]["item_id"] for i in range(len(order2))])

    def test_original_exposures_never_swapped(self):
        blinded, manifest = _make_package(15, n_boundary=1)
        assignment = collect5b.build_assignment(blinded, manifest, "evaluator_01", 5100)
        for e in assignment["exposures"]:
            if e["kind"] == "original":
                self.assertEqual(e["displayed_order"], "unswapped")

    def test_render_exposure_swap_flips_segmentations(self):
        blinded, manifest = _make_package(5)
        item_id = "fx-0001"
        unswapped = {"item_id": item_id, "displayed_order": "unswapped"}
        swapped = {"item_id": item_id, "displayed_order": "swapped"}
        r1 = collect5b.render_exposure(unswapped, blinded)
        r2 = collect5b.render_exposure(swapped, blinded)
        self.assertEqual(r1["segmentation_1"], r2["segmentation_2"])
        self.assertEqual(r1["segmentation_2"], r2["segmentation_1"])


class ValidationTests(unittest.TestCase):
    def test_comparative_rating_valid_values(self):
        for v in (-2, -1, 0, 1, 2):
            self.assertEqual(collect5b.validate_comparative_rating(v), v)

    def test_comparative_rating_out_of_range(self):
        with self.assertRaises(collect5b.InvalidResponseError):
            collect5b.validate_comparative_rating(3)

    def test_comparative_rating_rejects_bool(self):
        with self.assertRaises(collect5b.InvalidResponseError):
            collect5b.validate_comparative_rating(True)

    def test_comparative_rating_rejects_float(self):
        with self.assertRaises(collect5b.InvalidResponseError):
            collect5b.validate_comparative_rating(1.0)

    def test_awkward_split_requires_bool(self):
        self.assertTrue(collect5b.validate_awkward_split(True, "field"))
        with self.assertRaises(collect5b.InvalidResponseError):
            collect5b.validate_awkward_split("yes", "field")

    def test_reading_effort_valid_range(self):
        for v in (1, 2, 3, 4, 5):
            self.assertEqual(collect5b.validate_reading_effort(v, "field"), v)

    def test_reading_effort_out_of_range(self):
        with self.assertRaises(collect5b.InvalidResponseError):
            collect5b.validate_reading_effort(6, "field")
        with self.assertRaises(collect5b.InvalidResponseError):
            collect5b.validate_reading_effort(0, "field")

    def test_displayed_order_valid(self):
        self.assertEqual(collect5b.validate_displayed_order("swapped"), "swapped")
        with self.assertRaises(collect5b.InvalidResponseError):
            collect5b.validate_displayed_order("sideways")


class ResponseRecordingTests(unittest.TestCase):
    def test_build_response_record_unknown_item_raises(self):
        blinded, _ = _make_package(5)
        with self.assertRaises(collect5b.IntegrityError):
            collect5b.build_response_record(
                existing=[], blinded_by_id=blinded, item_id="does-not-exist", evaluator_id="evaluator_01",
                displayed_order="unswapped", comparative_rating=1,
                awkward_split_segmentation_1=False, awkward_split_segmentation_2=False,
                reading_effort_segmentation_1=3, reading_effort_segmentation_2=3,
            )

    def test_build_response_record_schema(self):
        blinded, _ = _make_package(5)
        record = collect5b.build_response_record(
            existing=[], blinded_by_id=blinded, item_id="fx-0001", evaluator_id="evaluator_01",
            displayed_order="unswapped", comparative_rating=-1,
            awkward_split_segmentation_1=False, awkward_split_segmentation_2=True,
            reading_effort_segmentation_1=4, reading_effort_segmentation_2=2,
            optional_comment="fine",
        )
        expected_keys = {
            "response_event_id", "item_id", "is_repeat", "repeat_of_response_event_id", "evaluator_id",
            "displayed_order", "comparative_rating", "awkward_split_segmentation_1", "awkward_split_segmentation_2",
            "reading_effort_segmentation_1", "reading_effort_segmentation_2", "optional_comment", "timestamp",
        }
        self.assertEqual(set(record.keys()), expected_keys)
        self.assertEqual(record["response_event_id"], "exp5b-resp-000001")
        self.assertFalse(record["is_repeat"])
        self.assertIsNone(record["repeat_of_response_event_id"])

    def test_repeat_without_prior_response_raises(self):
        blinded, _ = _make_package(5)
        with self.assertRaises(collect5b.InvalidResponseError):
            collect5b.build_response_record(
                existing=[], blinded_by_id=blinded, item_id="fx-0001", evaluator_id="evaluator_01",
                displayed_order="unswapped", comparative_rating=1,
                awkward_split_segmentation_1=False, awkward_split_segmentation_2=False,
                reading_effort_segmentation_1=3, reading_effort_segmentation_2=3,
                is_repeat=True,
            )

    def test_repeat_resolves_repeat_of_response_event_id(self):
        blinded, _ = _make_package(5)
        first = collect5b.build_response_record(
            existing=[], blinded_by_id=blinded, item_id="fx-0001", evaluator_id="evaluator_01",
            displayed_order="unswapped", comparative_rating=1,
            awkward_split_segmentation_1=False, awkward_split_segmentation_2=False,
            reading_effort_segmentation_1=3, reading_effort_segmentation_2=3,
        )
        repeat = collect5b.build_response_record(
            existing=[first], blinded_by_id=blinded, item_id="fx-0001", evaluator_id="evaluator_01",
            displayed_order="swapped", comparative_rating=0,
            awkward_split_segmentation_1=False, awkward_split_segmentation_2=False,
            reading_effort_segmentation_1=3, reading_effort_segmentation_2=3,
            is_repeat=True,
        )
        self.assertEqual(repeat["repeat_of_response_event_id"], first["response_event_id"])
        self.assertTrue(repeat["is_repeat"])

    def test_generate_response_event_id_sequential_and_unique(self):
        existing = [{"response_event_id": "exp5b-resp-000001"}]
        self.assertEqual(collect5b.generate_response_event_id(existing), "exp5b-resp-000002")
        self.assertEqual(collect5b.generate_response_event_id([]), "exp5b-resp-000001")


class AppendResponseTests(unittest.TestCase):
    def test_append_response_creates_and_preserves_prior_records(self):
        blinded, _ = _make_package(5)
        with tempfile.TemporaryDirectory() as d:
            path = str(Path(d) / "raw_responses.json")
            r1 = collect5b.build_response_record(
                existing=[], blinded_by_id=blinded, item_id="fx-0001", evaluator_id="evaluator_01",
                displayed_order="unswapped", comparative_rating=1,
                awkward_split_segmentation_1=False, awkward_split_segmentation_2=False,
                reading_effort_segmentation_1=3, reading_effort_segmentation_2=3,
            )
            collect5b.append_response(path, r1)
            existing_after_1 = collect5b.load_raw_responses(path)
            self.assertEqual(len(existing_after_1), 1)

            r2 = collect5b.build_response_record(
                existing=existing_after_1, blinded_by_id=blinded, item_id="fx-0002", evaluator_id="evaluator_01",
                displayed_order="unswapped", comparative_rating=-2,
                awkward_split_segmentation_1=True, awkward_split_segmentation_2=False,
                reading_effort_segmentation_1=2, reading_effort_segmentation_2=5,
            )
            collect5b.append_response(path, r2)
            final = collect5b.load_raw_responses(path)
            self.assertEqual(len(final), 2)
            # First record must be byte-for-byte preserved (raw-data
            # immutability across successive append calls).
            self.assertEqual(final[0], r1)
            self.assertEqual(final[1], r2)

    def test_append_response_rejects_duplicate_event_id(self):
        blinded, _ = _make_package(5)
        with tempfile.TemporaryDirectory() as d:
            path = str(Path(d) / "raw_responses.json")
            r1 = collect5b.build_response_record(
                existing=[], blinded_by_id=blinded, item_id="fx-0001", evaluator_id="evaluator_01",
                displayed_order="unswapped", comparative_rating=1,
                awkward_split_segmentation_1=False, awkward_split_segmentation_2=False,
                reading_effort_segmentation_1=3, reading_effort_segmentation_2=3,
            )
            collect5b.append_response(path, r1)
            with self.assertRaises(collect5b.IntegrityError):
                collect5b.append_response(path, r1)

    def test_load_raw_responses_missing_file_returns_empty(self):
        self.assertEqual(collect5b.load_raw_responses("/nonexistent/path/raw.json"), [])


#: The frozen Experiment 5A package is known to live at two different
#: paths depending on environment: the actual repository convention,
#: `data/phase2d_experiment5/` (flat), and this sandbox's own layout,
#: `data/phase2d/experiment5/` (nested) - both hold byte-identical
#: content (established and accepted in an earlier synchronization
#: round; not a data discrepancy, purely a directory-naming one). This
#: never moves, copies, renames, or regenerates anything - it only picks
#: whichever of the two already-existing paths to read from, so the
#: smoke test below actually runs (rather than skips) in whichever
#: environment it is executed in, flat convention checked first per the
#: task's explicit "use the actual repository convention" instruction.
REAL_EXP5A_DIR_CANDIDATES = [
    ROOT / "data" / "phase2d_experiment5",
    ROOT / "data" / "phase2d" / "experiment5",
]
REAL_EXP5A_DIR = next((p for p in REAL_EXP5A_DIR_CANDIDATES if p.exists()), None)


class RealArtifactSmokeTest(unittest.TestCase):
    """Optional end-to-end smoke test against the real, frozen Experiment
    5A package - skipped only if the artifacts are not present under
    EITHER known path (see REAL_EXP5A_DIR_CANDIDATES above), matching the
    pattern in tests/test_phase2d_experiment5_prepare.py."""

    @unittest.skipUnless(
        REAL_EXP5A_DIR is not None
        and (REAL_EXP5A_DIR / "evaluation_items_blinded.json").exists()
        and (REAL_EXP5A_DIR / "sample_manifest.json").exists(),
        "real Experiment 5A package not present under data/phase2d_experiment5/ or data/phase2d/experiment5/",
    )
    def test_assignment_against_real_package_is_deterministic_and_complete(self):
        blinded = collect5b.load_blinded_items(str(REAL_EXP5A_DIR / "evaluation_items_blinded.json"))
        manifest = collect5b.load_manifest(str(REAL_EXP5A_DIR / "sample_manifest.json"))
        self.assertEqual(len(blinded), 69)
        self.assertEqual(len(manifest), 69)
        collect5b.scan_blinded_package(blinded)

        a1 = collect5b.build_assignment(blinded, manifest, "evaluator_01", 5100)
        a2 = collect5b.build_assignment(blinded, manifest, "evaluator_01", 5100)
        self.assertEqual(a1, a2)
        self.assertEqual(len(a1["item_ids"]), 69)
        self.assertEqual(len(a1["repeat_item_ids"]), 5)  # round(0.10*69)=7, capped at 5
        boundary_ids = {i for i, r in manifest.items() if not r["primary_sample"]}
        self.assertTrue(all(i not in boundary_ids for i in a1["repeat_item_ids"]))


if __name__ == "__main__":
    unittest.main()
