"""Tests for `scripts/phase2d_experiment5b_analyze.py` (Phase 2D
Experiment 5B - Human Evaluation Analysis Pipeline).

Scope: these tests cover the analysis machinery only, using small,
explicitly-synthetic fixtures with hand-verifiable expected statistics.
They never use real human ratings (none exist yet) and never modify
`data/phase2d/experiment5/` or any Phase 2D production/test file. Any
result computed by these tests describes the synthetic fixture only, per
this round's explicit "no fabricated human-evaluation conclusions"
instruction.

`scripts/` is not a package, so the module under test is loaded by path.
The analyze module itself imports `phase2d_experiment5b_collect` via a
sys.path insertion of its own directory (see the module's docstring); to
guarantee both modules see the *same* IntegrityError/InvalidResponseError
classes, this test file accesses the collect module exclusively via
`analyze5b.collect5b` rather than importing it a second, separate way.
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location(
    "phase2d_experiment5b_analyze", ROOT / "scripts" / "phase2d_experiment5b_analyze.py"
)
analyze5b = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(analyze5b)

collect5b = analyze5b.collect5b


# ---------------------------------------------------------------------------
# Synthetic fixture: 4 primary items + 1 boundary-condition item, hand
# chosen so every downstream statistic is independently verifiable.
# ---------------------------------------------------------------------------


def _manifest_record(item_id, *, primary_sample, seg1_is, seg2_is, stratum, alt_substituted=False):
    return {
        "item_id": item_id,
        "source_file": "examples/notes/mcu1_slide_01.txt" if "1" in item_id or "5" in item_id else "examples/notes/mcu2_slide_01.txt",
        "paragraph_index": int(item_id[-1]),
        "alternative_k": 3,
        "k_min": 2,
        "primary_sample": primary_sample,
        "boundary_condition_candidate": not primary_sample,
        "segmentation_1_is": seg1_is,
        "segmentation_2_is": seg2_is,
        "stratum": stratum,
        "alternative_k_substituted": alt_substituted,
        "contains_extreme_narrow_segment": False,
        "delta_k": 1,
        "delta_phase2d_score": 10.0,
        "frontier_size": 2,
        "pareto_frontier": [[2, 5.0], [3, 15.0]],
        "phase2d_score_alternative": 15.0,
        "phase2d_score_k_min": 5.0,
    }


def _fixture_manifest():
    return {
        "item1": _manifest_record("item1", primary_sample=True, seg1_is="k_min", seg2_is="alternative", stratum=["B_small_gain"]),
        "item2": _manifest_record("item2", primary_sample=True, seg1_is="alternative", seg2_is="k_min", stratum=["C_moderate_gain"]),
        "item3": _manifest_record("item3", primary_sample=True, seg1_is="k_min", seg2_is="alternative",
                                   stratum=["B_small_gain", "H_material_boundary_change"]),
        "item4": _manifest_record("item4", primary_sample=True, seg1_is="k_min", seg2_is="alternative", stratum=["D_large_gain"]),
        "item5": _manifest_record("item5", primary_sample=False, seg1_is="alternative", seg2_is="k_min", stratum=["boundary"]),
    }


def _resp(event_id, item_id, evaluator_id, rating, *, is_repeat=False, repeat_of=None, displayed_order="unswapped",
          awk1=False, awk2=False, eff1=3, eff2=3, comment=None):
    return {
        "response_event_id": event_id,
        "item_id": item_id,
        "is_repeat": is_repeat,
        "repeat_of_response_event_id": repeat_of,
        "evaluator_id": evaluator_id,
        "displayed_order": displayed_order,
        "comparative_rating": rating,
        "awkward_split_segmentation_1": awk1,
        "awkward_split_segmentation_2": awk2,
        "reading_effort_segmentation_1": eff1,
        "reading_effort_segmentation_2": eff2,
        "optional_comment": comment,
        "timestamp": "informational only",
    }


def _fixture_responses():
    """
    item1 (seg1=k_min, seg2=alternative): raw 2,1,1 -> oriented 2,1,1 -> median 1 (WIN)
    item2 (seg1=alternative, seg2=k_min): raw 0,0,1 -> oriented 0,0,-1 -> median 0 (TIE)
    item3 (seg1=k_min, seg2=alternative): raw -2,-1,-1 -> oriented -2,-1,-1 -> median -1 (LOSS)
    item4 (seg1=k_min, seg2=alternative): raw 1,1 (only 2 raters, below floor) -> oriented 1,1 -> median 1
    item5 (boundary, seg1=alternative, seg2=k_min): raw -2 (1 rater) -> oriented +2

    corpus-level median of [1, 0, -1, 1] = 0.5; win=2 tie=1 loss=1.
    sign test excludes item2's 0 -> wins=2 losses=1 n=3 p=1.0.

    Plus: a duplicate non-repeat response for item1/e1 (flagged, excluded);
    a consistent repeat (e1 repeats item1); an inconsistent repeat
    (e2 repeats item3); a repeat with a swapped displayed_order
    (e3 repeats item2, tests swap-aware orientation); a comment containing
    a forbidden token (flagged, retained).
    """
    return [
        _resp("r001", "item1", "e1", 2, awk1=False, awk2=True, eff1=4, eff2=2),
        _resp("r002", "item1", "e2", 1),
        _resp("r003", "item1", "e3", 1),
        _resp("r004", "item2", "e1", 0),
        _resp("r005", "item2", "e2", 0),
        _resp("r006", "item2", "e3", 1),
        _resp("r007", "item3", "e1", -2),
        _resp("r008", "item3", "e2", -1),
        _resp("r009", "item3", "e3", -1),
        _resp("r010", "item4", "e1", 1),
        _resp("r011", "item4", "e2", 1),
        _resp("r012", "item5", "e1", -2, comment="looked fine to me"),
        # duplicate non-repeat: e1 rates item1 a second time
        _resp("r013", "item1", "e1", -2),
        # consistent repeat: e1 repeats item1 (base oriented=2, repeat raw=1 -> oriented=1, diff=1)
        _resp("r014", "item1", "e1", 1, is_repeat=True, repeat_of="r001"),
        # inconsistent repeat: e2 repeats item3 (base oriented=-1, repeat raw=2 -> oriented=2, diff=3)
        _resp("r015", "item3", "e2", 2, is_repeat=True, repeat_of="r008"),
        # swapped repeat: e3 repeats item2 (base oriented=-1); swapped displayed_order flips
        # effective seg2_is to 'alternative', so oriented=+raw=+1; diff=|1-(-1)|=2 -> inconsistent
        _resp("r016", "item2", "e3", 1, is_repeat=True, repeat_of="r006", displayed_order="swapped"),
        # comment forbidden-token leak (retained, flagged)
        _resp("r017", "item4", "e1", 0, comment="the score felt about the same"),
    ]


class SchemaValidationTests(unittest.TestCase):
    def test_valid_record_passes(self):
        r = _resp("r001", "item1", "e1", 1)
        self.assertIsNone(analyze5b.validate_response_schema(r))

    def test_missing_field_rejected(self):
        r = _resp("r001", "item1", "e1", 1)
        del r["evaluator_id"]
        self.assertIsNotNone(analyze5b.validate_response_schema(r))

    def test_invalid_comparative_rating_rejected(self):
        r = _resp("r001", "item1", "e1", 5)
        self.assertIsNotNone(analyze5b.validate_response_schema(r))

    def test_invalid_reading_effort_rejected(self):
        r = _resp("r001", "item1", "e1", 1, eff1=9)
        self.assertIsNotNone(analyze5b.validate_response_schema(r))

    def test_invalid_awkward_split_type_rejected(self):
        r = _resp("r001", "item1", "e1", 1)
        r["awkward_split_segmentation_1"] = "yes"
        self.assertIsNotNone(analyze5b.validate_response_schema(r))

    def test_is_repeat_without_repeat_of_rejected(self):
        r = _resp("r001", "item1", "e1", 1, is_repeat=True, repeat_of=None)
        self.assertIsNotNone(analyze5b.validate_response_schema(r))

    def test_non_repeat_with_repeat_of_set_rejected(self):
        r = _resp("r001", "item1", "e1", 1, is_repeat=False)
        r["repeat_of_response_event_id"] = "r000"
        self.assertIsNotNone(analyze5b.validate_response_schema(r))

    def test_malformed_displayed_order_rejected(self):
        r = _resp("r001", "item1", "e1", 1, displayed_order="sideways")
        self.assertIsNotNone(analyze5b.validate_response_schema(r))


class IngestResponsesTests(unittest.TestCase):
    def test_unknown_item_id_raises_hard_integrity_error(self):
        manifest = _fixture_manifest()
        responses = [_resp("r001", "does-not-exist", "e1", 1)]
        with self.assertRaises(analyze5b.IntegrityError):
            analyze5b.ingest_responses(responses, manifest)

    def test_malformed_record_soft_rejected_not_halting(self):
        manifest = _fixture_manifest()
        responses = [_resp("r001", "item1", "e1", 1), _resp("r002", "item1", "e2", 5)]  # 5 is out of range
        valid, rejected = analyze5b.ingest_responses(responses, manifest)
        self.assertEqual(len(valid), 1)
        self.assertEqual(len(rejected), 1)
        self.assertIn("comparative_rating", rejected[0]["reason"])

    def test_all_valid_pass_through(self):
        manifest = _fixture_manifest()
        responses = _fixture_responses()
        valid, rejected = analyze5b.ingest_responses(responses, manifest)
        self.assertEqual(len(valid), len(responses))
        self.assertEqual(rejected, [])


class OrientationTests(unittest.TestCase):
    def test_resolve_displayed_identity_unswapped(self):
        manifest = _fixture_manifest()
        seg1, seg2 = analyze5b.resolve_displayed_identity("item1", "unswapped", manifest)
        self.assertEqual((seg1, seg2), ("k_min", "alternative"))

    def test_resolve_displayed_identity_swapped(self):
        manifest = _fixture_manifest()
        seg1, seg2 = analyze5b.resolve_displayed_identity("item1", "swapped", manifest)
        self.assertEqual((seg1, seg2), ("alternative", "k_min"))

    def test_orient_rating_seg2_alternative_no_flip(self):
        manifest = _fixture_manifest()
        self.assertEqual(analyze5b.orient_rating(2, "item1", "unswapped", manifest), 2)

    def test_orient_rating_seg2_k_min_flips_sign(self):
        manifest = _fixture_manifest()
        self.assertEqual(analyze5b.orient_rating(2, "item2", "unswapped", manifest), -2)

    def test_orient_rating_swap_changes_sign(self):
        manifest = _fixture_manifest()
        unswapped = analyze5b.orient_rating(1, "item2", "unswapped", manifest)
        swapped = analyze5b.orient_rating(1, "item2", "swapped", manifest)
        self.assertEqual(unswapped, -swapped)

    def test_validate_mapping_completeness_all_resolve(self):
        manifest = _fixture_manifest()
        responses = _fixture_responses()
        self.assertEqual(analyze5b.validate_mapping_completeness(responses, manifest), [])

    def test_validate_mapping_completeness_detects_malformed_identity(self):
        manifest = _fixture_manifest()
        manifest["item1"]["segmentation_1_is"] = "weird"
        manifest["item1"]["segmentation_2_is"] = "also_weird"
        responses = [_resp("r001", "item1", "e1", 1)]
        failures = analyze5b.validate_mapping_completeness(responses, manifest)
        self.assertEqual(failures, ["r001"])


class DataQualityTests(unittest.TestCase):
    def setUp(self):
        self.manifest = _fixture_manifest()
        self.responses = _fixture_responses()
        self.valid, _ = analyze5b.ingest_responses(self.responses, self.manifest)
        self.dq = analyze5b.apply_data_quality_rules(self.valid, self.manifest)

    def test_duplicate_non_repeat_flagged(self):
        self.assertIn("r013", self.dq["duplicate_non_repeat_flagged_ids"])

    def test_duplicate_excluded_from_primary(self):
        entry = next(e for e in self.dq["cleaned"] if e["response_event_id"] == "r013")
        self.assertFalse(entry["used_in_primary"])
        entry_first = next(e for e in self.dq["cleaned"] if e["response_event_id"] == "r001")
        self.assertTrue(entry_first["used_in_primary"])

    def test_consistent_repeat_not_flagged(self):
        entry = next(e for e in self.dq["cleaned"] if e["response_event_id"] == "r014")
        self.assertFalse(entry["repeat_inconsistent"])

    def test_inconsistent_repeat_flagged(self):
        self.assertIn("r015", self.dq["inconsistent_repeat_ids"])

    def test_swapped_repeat_inconsistent_flagged(self):
        self.assertIn("r016", self.dq["inconsistent_repeat_ids"])

    def test_comment_leak_flagged(self):
        self.assertIn("r017", self.dq["comment_leak_flagged_ids"])
        # data is retained, not redacted
        entry = next(e for e in self.valid if e["response_event_id"] == "r017")
        self.assertEqual(entry["optional_comment"], "the score felt about the same")


class PrimaryOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.manifest = _fixture_manifest()
        valid, _ = analyze5b.ingest_responses(_fixture_responses(), self.manifest)
        self.dq = analyze5b.apply_data_quality_rules(valid, self.manifest)
        self.po = analyze5b.compute_primary_outcome(self.dq["cleaned"], self.manifest)

    def test_item_medians(self):
        self.assertEqual(self.po["item_medians"]["item1"], 1)
        self.assertEqual(self.po["item_medians"]["item2"], 0)
        self.assertEqual(self.po["item_medians"]["item3"], -1)
        self.assertEqual(self.po["item_medians"]["item4"], 1)

    def test_boundary_condition_excluded_from_primary(self):
        self.assertNotIn("item5", self.po["item_medians"])
        self.assertEqual(self.po["n_primary_items"], 4)

    def test_corpus_level_median(self):
        self.assertEqual(self.po["corpus_level_median"], 0.5)

    def test_win_tie_loss(self):
        self.assertEqual(self.po["win_count"], 2)
        self.assertEqual(self.po["tie_count"], 1)
        self.assertEqual(self.po["loss_count"], 1)

    def test_below_floor(self):
        self.assertEqual(self.po["items_below_3_rating_floor"], ["item4"])

    def test_duplicate_did_not_alter_item1_median(self):
        # r013 (duplicate, rating -2) must not have pulled item1's median down.
        self.assertEqual(self.po["item_medians"]["item1"], 1)


class SignTestTests(unittest.TestCase):
    def test_matches_hand_calculation(self):
        result = analyze5b.sign_test([1, 0, -1, 1])
        self.assertEqual(result["n"], 3)
        self.assertEqual(result["wins"], 2)
        self.assertEqual(result["losses"], 1)
        self.assertAlmostEqual(result["p_value"], 1.0)

    def test_empty_input(self):
        result = analyze5b.sign_test([])
        self.assertEqual(result["n"], 0)
        self.assertIsNone(result["p_value"])

    def test_all_zero_excluded(self):
        result = analyze5b.sign_test([0, 0, 0])
        self.assertEqual(result["n"], 0)
        self.assertIsNone(result["p_value"])

    def test_unanimous_wins_low_p_value(self):
        result = analyze5b.sign_test([1, 1, 1, 1, 1, 1, 1, 1])
        self.assertEqual(result["wins"], 8)
        self.assertLess(result["p_value"], 0.01)


class SecondaryOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.manifest = _fixture_manifest()
        valid, _ = analyze5b.ingest_responses(_fixture_responses(), self.manifest)
        self.dq = analyze5b.apply_data_quality_rules(valid, self.manifest)
        self.raw_by_event_id = {r["response_event_id"]: r for r in valid}
        self.po = analyze5b.compute_primary_outcome(self.dq["cleaned"], self.manifest)
        self.so = analyze5b.compute_secondary_outcomes(self.dq["cleaned"], self.raw_by_event_id, self.manifest, self.po)

    def test_stratum_breakdown_b_small_gain(self):
        # item1 (median 1) + item3 (median -1) -> median_of_medians 0
        summ = self.so["by_stratum"]["B_small_gain"]
        self.assertEqual(summ["n_items"], 2)
        self.assertEqual(summ["median_of_medians"], 0)
        self.assertEqual((summ["win"], summ["tie"], summ["loss"]), (1, 0, 1))

    def test_stratum_breakdown_h_material_change(self):
        summ = self.so["by_stratum"]["H_material_boundary_change"]
        self.assertEqual(summ["n_items"], 1)
        self.assertEqual(summ["median_of_medians"], -1)

    def test_boundary_condition_reported_individually(self):
        detail = self.so["boundary_condition_items"]
        self.assertEqual(len(detail), 1)
        self.assertEqual(detail[0]["item_id"], "item5")
        self.assertEqual(detail[0]["oriented_ratings"], [2])
        self.assertIn("looked fine to me", detail[0]["comments"])

    def test_overlapping_strata_note_present(self):
        self.assertIn("overlapping", self.so["note_overlapping_strata"])

    def test_awkward_split_rate_uses_orientation(self):
        # item1 e1: awk1=False (k_min side), awk2=True (alternative side)
        rate = self.so["awkward_split_rate_by_side"]
        self.assertIsNotNone(rate["k_min"])
        self.assertIsNotNone(rate["alternative"])


class AgreementTests(unittest.TestCase):
    def test_perfect_agreement_alpha_is_one(self):
        units = {"u1": [1, 1, 1], "u2": [-1, -1, -1], "u3": [0, 0, 0]}
        alpha = analyze5b.krippendorff_alpha_ordinal(units)
        self.assertAlmostEqual(alpha, 1.0)

    def test_no_variance_alpha_is_none(self):
        units = {"u1": [1, 1], "u2": [1, 1]}
        alpha = analyze5b.krippendorff_alpha_ordinal(units)
        self.assertIsNone(alpha)

    def test_single_rater_units_contribute_nothing(self):
        units = {"u1": [1], "u2": [2]}
        alpha = analyze5b.krippendorff_alpha_ordinal(units)
        self.assertIsNone(alpha)

    def test_pairwise_percent_agreement_disagree(self):
        pct = analyze5b.pairwise_percent_agreement({"u1": [1, -1]})
        self.assertEqual(pct, 0.0)

    def test_pairwise_percent_agreement_agree(self):
        pct = analyze5b.pairwise_percent_agreement({"u1": [1, 2]})
        self.assertEqual(pct, 1.0)

    def test_pairwise_percent_agreement_no_data(self):
        self.assertIsNone(analyze5b.pairwise_percent_agreement({}))

    def test_compute_agreement_on_fixture_runs(self):
        manifest = _fixture_manifest()
        valid, _ = analyze5b.ingest_responses(_fixture_responses(), manifest)
        dq = analyze5b.apply_data_quality_rules(valid, manifest)
        agreement = analyze5b.compute_agreement(dq["cleaned"], manifest)
        self.assertIsInstance(agreement["krippendorff_alpha_ordinal"], float)
        self.assertGreaterEqual(agreement["n_units_with_2plus_raters"], 3)


class RepeatConsistencyTests(unittest.TestCase):
    def test_corpus_and_per_evaluator_rates(self):
        manifest = _fixture_manifest()
        valid, _ = analyze5b.ingest_responses(_fixture_responses(), manifest)
        dq = analyze5b.apply_data_quality_rules(valid, manifest)
        rc = analyze5b.compute_repeat_consistency(dq["cleaned"])
        # e1: 1 repeat, consistent -> rate 1.0
        self.assertEqual(rc["per_evaluator_consistency_rate"]["e1"], 1.0)
        # e2: 1 repeat, inconsistent -> rate 0.0
        self.assertEqual(rc["per_evaluator_consistency_rate"]["e2"], 0.0)
        # e3: 1 repeat, inconsistent (swap case) -> rate 0.0
        self.assertEqual(rc["per_evaluator_consistency_rate"]["e3"], 0.0)
        self.assertEqual(rc["n_evaluators_with_repeats"], 3)


class MissingResponseDerivationTests(unittest.TestCase):
    """Design section 19 row 1 ('missing response'): analyze.py does not
    itself track assignment-vs-response (it only sees actual raw
    responses), but the assignment produced by the collect layer plus the
    raw responses received is sufficient to derive missing items - this
    test demonstrates that derivation is possible and correct."""

    def test_missing_items_derivable_from_assignment_and_responses(self):
        blinded = {
            iid: {
                "item_id": iid, "source_file": "x.txt", "source_text": "t", "segmentation_1": ["t"],
                "segmentation_2": ["t"], "paragraph_index": 0, "paragraph_start_offset": 0,
                "paragraph_end_offset": 1, "is_repeat_item": False, "repeat_of_item_id": None,
            }
            for iid in ["item1", "item2", "item3", "item4"]
        }
        manifest = _fixture_manifest()
        assignment = collect5b.build_assignment(blinded, manifest, "e1", 5100, item_ids=list(blinded.keys()))
        responded_item_ids = {"item1", "item2"}
        assigned_original_ids = {e["item_id"] for e in assignment["exposures"] if e["kind"] == "original"}
        missing = assigned_original_ids - responded_item_ids
        self.assertEqual(missing, {"item3", "item4"})


class EndToEndAnalysisTests(unittest.TestCase):
    def _write_fixture(self, tmpdir):
        manifest_path = Path(tmpdir) / "manifest.json"
        manifest_path.write_text(json.dumps(list(_fixture_manifest().values())), encoding="utf-8")
        raw_path = Path(tmpdir) / "raw_responses.json"
        raw_path.write_text(json.dumps(_fixture_responses(), ensure_ascii=False, indent=1), encoding="utf-8")
        return str(manifest_path), str(raw_path)

    def test_run_analysis_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            manifest_path, raw_path = self._write_fixture(d)
            results = analyze5b.run_analysis(raw_path, manifest_path, data_label="SYNTHETIC TEST FIXTURE")
        self.assertEqual(results["primary_outcome"]["corpus_level_median"], 0.5)
        self.assertEqual(results["sign_test"]["wins"], 2)
        self.assertEqual(results["raw_sha256_before"], results["raw_sha256_after"])

    def test_raw_file_byte_identical_on_disk_after_cli_run(self):
        with tempfile.TemporaryDirectory() as d:
            manifest_path, raw_path = self._write_fixture(d)
            before_bytes = Path(raw_path).read_bytes()
            out_dir = str(Path(d) / "out")
            rc = analyze5b.main(["--raw-responses", raw_path, "--manifest-json", manifest_path,
                                  "--output-dir", out_dir, "--data-label", "SYNTHETIC"])
            self.assertEqual(rc, 0)
            after_bytes = Path(raw_path).read_bytes()
            self.assertEqual(before_bytes, after_bytes)
            self.assertTrue((Path(out_dir) / "analysis_report.txt").exists())
            self.assertTrue((Path(out_dir) / "analysis_results.json").exists())

    def test_deterministic_across_repeated_runs(self):
        with tempfile.TemporaryDirectory() as d:
            manifest_path, raw_path = self._write_fixture(d)
            r1 = analyze5b.run_analysis(raw_path, manifest_path)
            r2 = analyze5b.run_analysis(raw_path, manifest_path)
        self.assertEqual(r1["primary_outcome"], r2["primary_outcome"])
        self.assertEqual(r1["sign_test"], r2["sign_test"])
        self.assertEqual(r1["agreement"], r2["agreement"])

    def test_unknown_item_id_in_raw_file_halts_with_integrity_error(self):
        with tempfile.TemporaryDirectory() as d:
            manifest_path, raw_path = self._write_fixture(d)
            responses = _fixture_responses() + [_resp("rbad", "does-not-exist", "e1", 1)]
            Path(raw_path).write_text(json.dumps(responses, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(analyze5b.IntegrityError):
                analyze5b.run_analysis(raw_path, manifest_path)

    def test_decision_gate_not_yet_evaluable_when_floor_not_met(self):
        # O. Decision Gate state criterion reflects actual state: the
        # shared fixture has item4 below the >=3-rating floor, so no
        # SUPPORT/NULL/CONTRADICTION may be fabricated even though the
        # raw corpus median (0.5) is positive.
        with tempfile.TemporaryDirectory() as d:
            manifest_path, raw_path = self._write_fixture(d)
            results = analyze5b.run_analysis(raw_path, manifest_path)
        self.assertIn("NOT YET EVALUABLE", results["decision_gate_classification"])
        self.assertNotIn("STATE A", results["decision_gate_classification"])
        self.assertNotIn("STATE B", results["decision_gate_classification"])
        self.assertNotIn("STATE C", results["decision_gate_classification"])
        self.assertFalse(results["acceptance_criteria"]["1_every_primary_item_ge_3_ratings"]["met"])
        # criterion 8 only checks that a classification string WAS generated
        # (it was - "NOT YET EVALUABLE..." - so this criterion passes even
        # though the overall gate below is still closed by criterion 1).
        self.assertTrue(results["acceptance_criteria"]["8_decision_gate_state_reported"]["met"])
        self.assertFalse(results["acceptance_criteria_all_met"])

    def test_decision_gate_reaches_state_when_floor_genuinely_met(self):
        # O (positive path). A fully floor-compliant fixture (every
        # primary item has >=3 ratings) must reach a real STATE A/B/C
        # classification, proving the gate isn't just permanently closed.
        manifest = _fixture_manifest()
        responses = [
            _resp("r001", "item1", "e1", 2), _resp("r002", "item1", "e2", 1), _resp("r003", "item1", "e3", 1),
            _resp("r004", "item2", "e1", 0), _resp("r005", "item2", "e2", 0), _resp("r006", "item2", "e3", 1),
            _resp("r007", "item3", "e1", -2), _resp("r008", "item3", "e2", -1), _resp("r009", "item3", "e3", -1),
            _resp("r010", "item4", "e1", 1), _resp("r011", "item4", "e2", 1), _resp("r012", "item4", "e3", 1),
        ]
        with tempfile.TemporaryDirectory() as d:
            manifest_path = Path(d) / "manifest.json"
            manifest_path.write_text(json.dumps(list(manifest.values())), encoding="utf-8")
            raw_path = Path(d) / "raw_responses.json"
            raw_path.write_text(json.dumps(responses, ensure_ascii=False), encoding="utf-8")
            results = analyze5b.run_analysis(str(raw_path), str(manifest_path))
        self.assertTrue(results["acceptance_criteria"]["1_every_primary_item_ge_3_ratings"]["met"])
        self.assertIn("STATE A", results["decision_gate_classification"])
        self.assertNotIn("NOT YET EVALUABLE", results["decision_gate_classification"])

    def test_report_text_labels_synthetic_data(self):
        with tempfile.TemporaryDirectory() as d:
            manifest_path, raw_path = self._write_fixture(d)
            results = analyze5b.run_analysis(raw_path, manifest_path, data_label="SYNTHETIC TEST FIXTURE")
        report = analyze5b.generate_report_text(results, "SYNTHETIC TEST FIXTURE")
        self.assertIn("SYNTHETIC TEST FIXTURE", report)
        self.assertIn("MACHINERY OUTPUT ONLY", report)

    def test_report_includes_missing_response_audit_section_when_absent(self):
        with tempfile.TemporaryDirectory() as d:
            manifest_path, raw_path = self._write_fixture(d)
            results = analyze5b.run_analysis(raw_path, manifest_path)
        report = analyze5b.generate_report_text(results, None)
        self.assertIn("MISSING RESPONSE AUDIT", report)
        self.assertIn("NOT RUN", report)

    def test_run_analysis_without_assignments_dir_fails_dq_criterion(self):
        # G. data-quality acceptance criterion fails when the required
        # missing-response audit is absent.
        with tempfile.TemporaryDirectory() as d:
            manifest_path, raw_path = self._write_fixture(d)
            results = analyze5b.run_analysis(raw_path, manifest_path, assignments_dir=None)
        self.assertIsNone(results["missing_response_audit"])
        self.assertFalse(results["acceptance_criteria"]["4_data_quality_rules_applied_and_auditable"]["met"])

    def test_run_analysis_with_assignments_dir_computes_missing_response_audit(self):
        blinded = {
            iid: {
                "item_id": iid, "source_file": "x.txt", "source_text": "t", "segmentation_1": ["t"],
                "segmentation_2": ["t"], "paragraph_index": 0, "paragraph_start_offset": 0,
                "paragraph_end_offset": 1, "is_repeat_item": False, "repeat_of_item_id": None,
            }
            for iid in ["item1", "item2", "item3", "item4"]
        }
        manifest = _fixture_manifest()
        assignment = collect5b.build_assignment(blinded, manifest, "e1", 5100, item_ids=list(blinded.keys()))
        with tempfile.TemporaryDirectory() as d:
            manifest_path = Path(d) / "manifest.json"
            manifest_path.write_text(json.dumps(list(manifest.values())), encoding="utf-8")
            raw_path = Path(d) / "raw_responses.json"
            # e1 only responds to item1 and item2 (of the 4 assigned originals)
            raw_path.write_text(json.dumps([_resp("r001", "item1", "e1", 1), _resp("r002", "item2", "e1", 0)]), encoding="utf-8")
            assignments_dir = Path(d) / "assignments"
            assignments_dir.mkdir()
            (assignments_dir / "e1.json").write_text(json.dumps(assignment), encoding="utf-8")

            results = analyze5b.run_analysis(str(raw_path), str(manifest_path), assignments_dir=str(assignments_dir))

        mra = results["missing_response_audit"]
        self.assertIsNotNone(mra)
        self.assertEqual(mra["total_expected_original_exposures"], 4)
        self.assertEqual(mra["total_attempted_of_expected"], 2)
        self.assertEqual(mra["total_missing"], 2)
        self.assertTrue(mra["reconciles"])
        self.assertTrue(results["acceptance_criteria"]["4_data_quality_rules_applied_and_auditable"]["met"])


class AcceptanceCriteriaTests(unittest.TestCase):
    """Design section 26's 8 acceptance criteria, corrected to be real,
    non-hardcoded checks (correction round discrepancy B)."""

    def _base_kwargs(self):
        manifest = _fixture_manifest()
        valid, _ = analyze5b.ingest_responses(_fixture_responses(), manifest)
        dq = analyze5b.apply_data_quality_rules(valid, manifest)
        po = analyze5b.compute_primary_outcome(dq["cleaned"], manifest)
        agreement = analyze5b.compute_agreement(dq["cleaned"], manifest)
        rc = analyze5b.compute_repeat_consistency(dq["cleaned"])
        decision_gate = analyze5b.classify_decision_gate(po)
        blinding_ok = {"ran": True, "hits": [], "detail": "zero hits"}
        dq_ok = {"all_rules_applied": True, "detail": "audit computed"}
        return dict(
            primary_outcome=po, mapping_failures=[], blinding_verification=blinding_ok,
            dq_verification=dq_ok, agreement=agreement, repeat_consistency=rc,
            decision_gate_classification=decision_gate,
        )

    def test_floor_not_met_when_item_below_3_ratings(self):
        kwargs = self._base_kwargs()
        acceptance = analyze5b.check_acceptance_criteria(**kwargs)
        self.assertFalse(acceptance["1_every_primary_item_ge_3_ratings"]["met"])  # item4 has only 2

    # F. Blinding acceptance criterion fails when the scan actually finds hits.
    def test_blinding_criterion_fails_when_scan_finds_hits(self):
        kwargs = self._base_kwargs()
        kwargs["blinding_verification"] = {"ran": True, "hits": ["score"], "detail": "forbidden token found"}
        acceptance = analyze5b.check_acceptance_criteria(**kwargs)
        self.assertFalse(acceptance["2_blinding_scan_zero_hits"]["met"])

    # F (continued). Fails when the scan simply never ran (None sentinel).
    def test_blinding_criterion_fails_when_scan_not_run(self):
        kwargs = self._base_kwargs()
        kwargs["blinding_verification"] = None
        acceptance = analyze5b.check_acceptance_criteria(**kwargs)
        self.assertFalse(acceptance["2_blinding_scan_zero_hits"]["met"])
        self.assertIn("not run", acceptance["2_blinding_scan_zero_hits"]["detail"])

    def test_blinding_criterion_passes_when_scan_ran_clean(self):
        kwargs = self._base_kwargs()
        acceptance = analyze5b.check_acceptance_criteria(**kwargs)
        self.assertTrue(acceptance["2_blinding_scan_zero_hits"]["met"])

    # G. Data-quality acceptance criterion fails when the required audit is absent.
    def test_data_quality_criterion_fails_when_audit_absent(self):
        kwargs = self._base_kwargs()
        kwargs["dq_verification"] = None
        acceptance = analyze5b.check_acceptance_criteria(**kwargs)
        self.assertFalse(acceptance["4_data_quality_rules_applied_and_auditable"]["met"])

    def test_data_quality_criterion_fails_when_audit_reports_incomplete(self):
        kwargs = self._base_kwargs()
        kwargs["dq_verification"] = {"all_rules_applied": False, "detail": "missing-response audit not run"}
        acceptance = analyze5b.check_acceptance_criteria(**kwargs)
        self.assertFalse(acceptance["4_data_quality_rules_applied_and_auditable"]["met"])

    def test_data_quality_criterion_passes_when_audit_complete(self):
        kwargs = self._base_kwargs()
        acceptance = analyze5b.check_acceptance_criteria(**kwargs)
        self.assertTrue(acceptance["4_data_quality_rules_applied_and_auditable"]["met"])

    # H. Repeat-consistency criterion fails when not computed.
    def test_repeat_consistency_criterion_fails_when_not_computed(self):
        kwargs = self._base_kwargs()
        kwargs["repeat_consistency"] = None
        acceptance = analyze5b.check_acceptance_criteria(**kwargs)
        self.assertFalse(acceptance["7_repeat_consistency_computed_no_exclusion"]["met"])

    def test_repeat_consistency_criterion_fails_on_malformed_shape(self):
        kwargs = self._base_kwargs()
        kwargs["repeat_consistency"] = {"n_evaluators_with_repeats": 3}  # missing expected keys
        acceptance = analyze5b.check_acceptance_criteria(**kwargs)
        self.assertFalse(acceptance["7_repeat_consistency_computed_no_exclusion"]["met"])

    # I. Repeat-consistency criterion passes when actually computed with the expected shape.
    def test_repeat_consistency_criterion_passes_when_actually_computed(self):
        kwargs = self._base_kwargs()
        acceptance = analyze5b.check_acceptance_criteria(**kwargs)
        self.assertTrue(acceptance["7_repeat_consistency_computed_no_exclusion"]["met"])

    # O. Decision Gate state criterion reflects actual state generation.
    def test_decision_gate_criterion_fails_when_state_not_generated(self):
        kwargs = self._base_kwargs()
        kwargs["decision_gate_classification"] = None
        acceptance = analyze5b.check_acceptance_criteria(**kwargs)
        self.assertFalse(acceptance["8_decision_gate_state_reported"]["met"])

    def test_decision_gate_criterion_passes_when_state_generated(self):
        kwargs = self._base_kwargs()
        acceptance = analyze5b.check_acceptance_criteria(**kwargs)
        self.assertTrue(acceptance["8_decision_gate_state_reported"]["met"])

    # N. Acceptance criteria cannot be satisfied by hardcoded True: every
    # verification input set to its "not verified" sentinel must fail its
    # own criterion, and the overall gate must report FAIL, not PASS.
    def test_all_omitted_verifications_fail_their_own_criteria_not_pass(self):
        po = analyze5b.compute_primary_outcome([], _fixture_manifest())  # no data at all
        acceptance = analyze5b.check_acceptance_criteria(
            primary_outcome=po,
            mapping_failures=[],
            blinding_verification=None,
            dq_verification=None,
            agreement={"krippendorff_alpha_ordinal": None, "pairwise_percent_agreement": None, "n_units_with_2plus_raters": 0},
            repeat_consistency=None,
            decision_gate_classification=None,
        )
        self.assertFalse(acceptance["2_blinding_scan_zero_hits"]["met"])
        self.assertFalse(acceptance["4_data_quality_rules_applied_and_auditable"]["met"])
        self.assertFalse(acceptance["6_agreement_computed"]["met"])
        self.assertFalse(acceptance["7_repeat_consistency_computed_no_exclusion"]["met"])
        self.assertFalse(acceptance["8_decision_gate_state_reported"]["met"])
        self.assertFalse(analyze5b.acceptance_criteria_all_met(acceptance))

    def test_acceptance_criteria_all_met_helper(self):
        kwargs = self._base_kwargs()
        acceptance = analyze5b.check_acceptance_criteria(**kwargs)
        # item4 is below the floor in this fixture, so overall must be False
        # even though most individual criteria pass - proving the helper
        # doesn't just default to True.
        self.assertFalse(analyze5b.acceptance_criteria_all_met(acceptance))
        self.assertFalse(acceptance["1_every_primary_item_ge_3_ratings"]["met"])


class MissingResponseAuditTests(unittest.TestCase):
    """Design section 19 row 1 + correction round requirement 3."""

    def _assignment(self, evaluator_id, item_ids, blinded=None):
        blinded = blinded or {
            iid: {
                "item_id": iid, "source_file": "x.txt", "source_text": "t", "segmentation_1": ["t"],
                "segmentation_2": ["t"], "paragraph_index": 0, "paragraph_start_offset": 0,
                "paragraph_end_offset": 1, "is_repeat_item": False, "repeat_of_item_id": None,
            }
            for iid in item_ids
        }
        manifest = _fixture_manifest()
        return collect5b.build_assignment(blinded, manifest, evaluator_id, 5100, item_ids=item_ids)

    # J. Missing-response per-item audit.
    def test_missing_count_by_item(self):
        a1 = self._assignment("e1", ["item1", "item2"])
        a2 = self._assignment("e2", ["item1", "item2"])
        raw = [_resp("r001", "item1", "e1", 1)]  # only e1/item1 responded
        result = analyze5b.compute_missing_responses({"e1": a1, "e2": a2}, raw)
        self.assertEqual(result["missing_count_by_item"]["item1"], 1)  # e2 missing
        self.assertEqual(result["missing_count_by_item"]["item2"], 2)  # both missing

    # K. Missing-response per-evaluator audit.
    def test_missing_count_by_evaluator(self):
        a1 = self._assignment("e1", ["item1", "item2"])
        a2 = self._assignment("e2", ["item1", "item2"])
        raw = [_resp("r001", "item1", "e1", 1), _resp("r002", "item2", "e1", 1)]  # e1 complete, e2 all missing
        result = analyze5b.compute_missing_responses({"e1": a1, "e2": a2}, raw)
        self.assertEqual(result["missing_count_by_evaluator"].get("e1", 0), 0)
        self.assertEqual(result["missing_count_by_evaluator"]["e2"], 2)

    # L. Missing response is not imputed - the missing pair simply never
    # appears in any rating aggregation; no value is fabricated for it.
    def test_missing_response_not_imputed(self):
        a1 = self._assignment("e1", ["item1", "item2"])
        raw = [_resp("r001", "item1", "e1", 1)]  # item2 missing entirely
        result = analyze5b.compute_missing_responses({"e1": a1}, raw)
        missing_item_ids = {p["item_id"] for p in result["missing_pairs"]}
        self.assertIn("item2", missing_item_ids)
        # And downstream: item2 must not appear with a fabricated rating in
        # the cleaned/primary computation from this same raw data.
        manifest = _fixture_manifest()
        valid, _ = analyze5b.ingest_responses(raw, manifest)
        dq = analyze5b.apply_data_quality_rules(valid, manifest)
        po = analyze5b.compute_primary_outcome(dq["cleaned"], manifest)
        self.assertIsNone(po["item_medians"]["item2"])  # no data, not a fabricated 0

    # An invalid-but-submitted response is "attempted," never "missing."
    def test_invalid_response_counts_as_attempted_not_missing(self):
        a1 = self._assignment("e1", ["item1", "item2"])
        raw = [
            _resp("r001", "item1", "e1", 1),
            _resp("r002", "item2", "e1", 99),  # out-of-range: invalid, but an attempt was made
        ]
        result = analyze5b.compute_missing_responses({"e1": a1}, raw)
        self.assertEqual(result["total_missing"], 0)
        self.assertEqual(result["total_attempted_of_expected"], 2)

    # M. Assignment/response reconciliation invariant.
    def test_reconciliation_invariant_holds(self):
        a1 = self._assignment("e1", ["item1", "item2", "item3"])
        a2 = self._assignment("e2", ["item1", "item2", "item3"])
        raw = [_resp("r001", "item1", "e1", 1), _resp("r002", "item2", "e2", -1)]
        result = analyze5b.compute_missing_responses({"e1": a1, "e2": a2}, raw)
        self.assertTrue(result["reconciles"])
        self.assertEqual(
            result["total_expected_original_exposures"],
            result["total_attempted_of_expected"] + result["total_missing"],
        )

    def test_repeats_excluded_from_expected_and_attempted(self):
        a1 = self._assignment("e1", ["item1", "item2", "item3", "item4"])  # will include repeats
        # A repeat-flagged response for a repeat item must not count as an
        # "attempt" against the original exposure's expected count.
        repeat_item_id = a1["repeat_item_ids"][0] if a1["repeat_item_ids"] else "item1"
        raw = [_resp("r001", repeat_item_id, "e1", 1, is_repeat=True, repeat_of="r000")]
        result = analyze5b.compute_missing_responses({"e1": a1}, raw)
        # The repeat response must not satisfy the original exposure.
        self.assertIn(repeat_item_id, {p["item_id"] for p in result["missing_pairs"] if p["evaluator_id"] == "e1"})

    def test_load_assignments_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            a1 = self._assignment("e1", ["item1", "item2"])
            (Path(d) / "e1.json").write_text(json.dumps(a1), encoding="utf-8")
            loaded = analyze5b.load_assignments(d)
        self.assertEqual(set(loaded.keys()), {"e1"})
        self.assertEqual(loaded["e1"]["evaluator_id"], "e1")


class RawImmutabilityWithNewPipelineTests(unittest.TestCase):
    """P. Raw-response immutability remains intact after the correction
    round's additions (blinding re-scan, missing-response audit)."""

    def test_raw_response_file_untouched_with_full_pipeline(self):
        manifest = _fixture_manifest()
        blinded_by_id = {
            iid: {
                "item_id": iid, "source_file": "x.txt", "source_text": "t", "segmentation_1": ["t"],
                "segmentation_2": ["t"], "paragraph_index": 0, "paragraph_start_offset": 0,
                "paragraph_end_offset": 10, "is_repeat_item": False, "repeat_of_item_id": None,
            }
            for iid in manifest
        }
        with tempfile.TemporaryDirectory() as d:
            manifest_path = Path(d) / "manifest.json"
            manifest_path.write_text(json.dumps(list(manifest.values())), encoding="utf-8")
            blinded_path = Path(d) / "blinded.json"
            blinded_path.write_text(json.dumps(list(blinded_by_id.values())), encoding="utf-8")
            raw_path = Path(d) / "raw_responses.json"
            raw_path.write_text(json.dumps(_fixture_responses(), ensure_ascii=False), encoding="utf-8")
            assignments_dir = Path(d) / "assignments"
            assignments_dir.mkdir()
            assignment = collect5b.build_assignment(blinded_by_id, manifest, "e1", 5100, item_ids=list(manifest.keys()))
            (assignments_dir / "e1.json").write_text(json.dumps(assignment), encoding="utf-8")

            before = raw_path.read_bytes()
            results = analyze5b.run_analysis(
                str(raw_path), str(manifest_path), blinded_json_path=str(blinded_path),
                assignments_dir=str(assignments_dir),
            )
            after = raw_path.read_bytes()

        self.assertEqual(before, after)
        self.assertEqual(results["raw_sha256_before"], results["raw_sha256_after"])
        self.assertIsNotNone(results["blinding_verification"])
        self.assertTrue(results["blinding_verification"]["ran"])
        self.assertIsNotNone(results["missing_response_audit"])


if __name__ == "__main__":
    unittest.main()
