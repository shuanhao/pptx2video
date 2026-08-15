"""Tests for `scripts/phase2d_experiment5_prepare.py` (Phase 2D Experiment
5A - Corpus Sampling & Blinded Evaluation Package).

Scope, matching the round's own boundaries: these tests cover the
sampling/blinding/integrity machinery of Experiment 5A only - deterministic
sampling, strata classification, K selection, integrity checks, width
metadata, blinding, reconstruction, and checksum generation. They do not
test production behavior and do not modify
`tests/test_boundary_segmentation.py`, `tests/test_boundary_segmentation_adapter.py`,
or `tests/test_shadow_mode_comparison.py`.

`scripts/` is not a package (no `__init__.py`, matching the rest of
`scripts/`), so the module under test is loaded by path, mirroring the
existing convention in `tests/test_calibrate_scale.py`.
"""

from __future__ import annotations

import importlib.util
import json
import ntpath
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location(
    "phase2d_experiment5_prepare", ROOT / "scripts" / "phase2d_experiment5_prepare.py"
)
exp5 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(exp5)

REAL_RESULTS_JSON = ROOT / "data" / "phase2d_experiment4" / "phase2d_pareto_results.json"
REAL_CORPUS_DIR = ROOT / "examples" / "notes"


# ---------------------------------------------------------------------------
# Small synthetic fixtures for unit-level tests (no dependency on the real
# 85MB Experiment 4 results file or the real 39-file corpus).
# ---------------------------------------------------------------------------


def _make_record(
    *,
    source_file="examples/notes/fixture.txt",
    paragraph_index=0,
    p_start=0,
    p_end=20,
    k_min=2,
    per_k,
    frontier,
):
    return {
        "source_file": source_file,
        "paragraph_index": paragraph_index,
        "paragraph_start_offset": p_start,
        "paragraph_end_offset": p_end,
        "paragraph_char_length": p_end - p_start,
        "k_min": k_min,
        "k_max": max(int(k) for k in per_k),
        "option_a_selected_k": k_min,
        "option_a_total_score": per_k[str(k_min)]["total_score"],
        "option_a_matches_frozen_algorithm": True,
        "pareto_frontier": frontier,
        "per_k": per_k,
    }


class WidthAndSegmentHelpersTests(unittest.TestCase):
    def test_generate_segments_slices_raw_text(self):
        text = "abcdefghij"
        segs = exp5.generate_segments(text, [0, 3, 7, 10])
        self.assertEqual(segs, ["abc", "defg", "hij"])
        self.assertEqual("".join(segs), text)

    def test_width_stats(self):
        stats = exp5.width_stats([4, 10, 18])
        self.assertEqual(stats["min_segment_width"], 4)
        self.assertEqual(stats["max_segment_width"], 18)
        self.assertAlmostEqual(stats["mean_segment_width"], 32 / 3)


class CorpusTextsPathNormalizationTests(unittest.TestCase):
    """Regression test for a cross-platform path-separator bug: on
    Windows, `os.path.join('examples', 'notes', name)` produces
    'examples\\notes\\<name>', which never matches the frozen Experiment 4
    artifact's POSIX-style `record["source_file"]` values
    ('examples/notes/<name>') - the bug that caused all 7 real-artifact
    E2E tests to fail with "not found among loaded corpus texts" once the
    stale REAL_RESULTS_JSON path was corrected on a Windows checkout. See
    `load_corpus_texts`, whose dict keys `finalize_items` looks up
    directly via `record["source_file"]`.

    `ntpath` (a pure, platform-independent stdlib module implementing
    Windows path-joining semantics) is used only to construct the "what
    the old, buggy code would have produced on Windows" comparison value
    below - it is never used to open a file, so this test is deterministic
    and passes identically on POSIX and Windows."""

    def test_corpus_texts_keys_are_posix_style_regardless_of_platform(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "mcu1_slide_02.txt").write_text("sample content", encoding="utf-8")
            texts = exp5.load_corpus_texts(d, ["mcu1_slide_02.txt"])
        self.assertIn("examples/notes/mcu1_slide_02.txt", texts)
        for key in texts:
            self.assertNotIn("\\", key, f"corpus_texts key must never contain a backslash: {key!r}")

    def test_key_matches_source_file_contract_not_a_windows_style_join(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "mcu1_slide_02.txt").write_text("sample content", encoding="utf-8")
            texts = exp5.load_corpus_texts(d, ["mcu1_slide_02.txt"])
        canonical_key = "examples/notes/mcu1_slide_02.txt"  # matches record["source_file"] in the frozen JSON
        windows_style_key = ntpath.join("examples", "notes", "mcu1_slide_02.txt")  # what the pre-fix os.path.join-based code produced on Windows
        self.assertNotEqual(canonical_key, windows_style_key)  # sanity: these genuinely differ
        self.assertIn(canonical_key, texts)
        self.assertNotIn(windows_style_key, texts)  # the fixed key is never backslash-joined

    def test_finalize_items_can_resolve_a_posix_style_source_file(self):
        # End-to-end within this script: a record whose source_file uses
        # the canonical POSIX contract must resolve against corpus_texts
        # built by load_corpus_texts, exactly as finalize_items does via
        # `corpus_texts.get(record["source_file"])`.
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "mcu1_slide_02.txt").write_text("AB、CD。", encoding="utf-8")
            texts = exp5.load_corpus_texts(d, ["mcu1_slide_02.txt"])
        source_file = "examples/notes/mcu1_slide_02.txt"
        self.assertEqual(texts.get(source_file), "AB、CD。")


class GainAndDeltaLabelTests(unittest.TestCase):
    def test_gain_bucket_boundaries(self):
        self.assertEqual(exp5.gain_bucket_label(10.0), "B_small_gain")
        self.assertEqual(exp5.gain_bucket_label(19.9), "B_small_gain")
        self.assertEqual(exp5.gain_bucket_label(20.0), "C_moderate_gain")
        self.assertEqual(exp5.gain_bucket_label(69.9), "C_moderate_gain")
        self.assertEqual(exp5.gain_bucket_label(70.0), "D_large_gain")
        self.assertEqual(exp5.gain_bucket_label(500.0), "D_large_gain")

    def test_gain_below_floor_is_unclassified_not_misclassified(self):
        # Experiment 4 never observed a gain below 10.0 in the real corpus,
        # but the label function must not silently mislabel an
        # out-of-range value as a nearby bucket.
        self.assertEqual(exp5.gain_bucket_label(5.0), "UNCLASSIFIED_GAIN")

    def test_delta_k_labels(self):
        self.assertEqual(exp5.delta_k_label(1), "E_delta_k_1")
        self.assertEqual(exp5.delta_k_label(2), "E_delta_k_2")
        self.assertEqual(exp5.delta_k_label(3), "E_delta_k_3")
        self.assertEqual(exp5.delta_k_label(4), "E_delta_k_4plus")
        self.assertEqual(exp5.delta_k_label(9), "E_delta_k_4plus")

    def test_frontier_size_label_is_literal(self):
        self.assertEqual(exp5.frontier_size_label(3), "F_frontier_size_3")
        self.assertEqual(exp5.frontier_size_label(29), "F_frontier_size_29")


class KSelectionTests(unittest.TestCase):
    """Synthetic paragraph: k_min=2 (score 0.0), frontier points at
    3 (score 20.0), 5 (score 40.0), 7 (score 45.0, but with an extreme
    narrow segment)."""

    def setUp(self):
        self.record = _make_record(
            p_end=30,
            k_min=2,
            frontier=[[2, 0.0], [3, 20.0], [5, 40.0], [7, 45.0]],
            per_k={
                "2": {
                    "feasible": True,
                    "total_score": 0.0,
                    "cut_positions": [0, 15, 30],
                    "internal_cut_positions": [15],
                    "segment_widths": [15, 15],
                    "boundary_scores": [0.0],
                },
                "3": {
                    "feasible": True,
                    "total_score": 20.0,
                    "cut_positions": [0, 10, 20, 30],
                    "internal_cut_positions": [10, 20],
                    "segment_widths": [10, 10, 10],
                    "boundary_scores": [10.0, 10.0],
                },
                "4": {"feasible": False},
                "5": {
                    "feasible": True,
                    "total_score": 40.0,
                    "cut_positions": [0, 6, 12, 18, 24, 30],
                    "internal_cut_positions": [6, 12, 18, 24],
                    "segment_widths": [6, 6, 6, 6, 6],
                    "boundary_scores": [10.0, 10.0, 10.0, 10.0],
                },
                "6": {"feasible": False},
                "7": {
                    "feasible": True,
                    "total_score": 45.0,
                    "cut_positions": [0, 2, 6, 12, 18, 24, 28, 30],
                    "internal_cut_positions": [2, 6, 12, 18, 24, 28],
                    # deliberately includes one extreme-narrow segment (width 2)
                    "segment_widths": [2, 4, 6, 6, 6, 4, 2],
                    "boundary_scores": [5.0, 10.0, 10.0, 10.0, 5.0, 5.0],
                },
            },
        )

    def test_best_qualifying_alt_skips_extreme_narrow_point(self):
        # K=7 has the highest score (45.0) but fails the width>=4 filter
        # (min width 2); K=5 (score 40.0) should be selected instead.
        alt = exp5.best_qualifying_alt(self.record, min_width=4)
        self.assertEqual(alt, (5, 40.0))

    def test_best_alt_ignoring_width_picks_highest_score_regardless(self):
        alt = exp5.best_alt_ignoring_width(self.record)
        self.assertEqual(alt, (7, 45.0))

    def test_select_delta_k_target_exact_frontier_point(self):
        k, score, substituted = exp5.select_delta_k_target(self.record, 1, min_width=4)
        self.assertEqual((k, score), (3, 20.0))
        self.assertFalse(substituted)

    def test_select_delta_k_target_substitutes_when_not_on_frontier(self):
        # K_min+2 = 4 is not a frontier point (and infeasible) - the
        # smallest frontier K > k_min (3) should be substituted.
        k, score, substituted = exp5.select_delta_k_target(self.record, 2, min_width=4)
        self.assertEqual((k, score), (3, 20.0))
        self.assertTrue(substituted)

    def test_select_delta_k_target_none_when_only_option_fails_width(self):
        # K_min+5 = 7 is a frontier point but fails the width filter, and
        # it's the only candidate with delta>=4 (well above the record's
        # frontier), so no >=4 target should be found once 7 is excluded
        # for delta=4's ">=4" search.
        result = exp5.select_delta_k_target(self.record, 4, min_width=4)
        self.assertIsNone(result)

    def test_frontier_shape_candidates_size_2_and_gt2(self):
        # This fixture's frontier has 4 points -> "gt2" class applies, not "2".
        self.assertEqual(exp5._frontier_shape_candidates(self.record, "2", min_width=4), [])
        self.assertEqual(exp5._frontier_shape_candidates(self.record, "gt2", min_width=4), [3, 5])

    def test_material_boundary_change_true_when_symmetric_diff_scores_high(self):
        record = _make_record(
            p_end=20,
            k_min=2,
            frontier=[[2, 0.0], [3, 90.0]],
            per_k={
                "2": {
                    "feasible": True,
                    "total_score": 0.0,
                    "cut_positions": [0, 10, 20],
                    "internal_cut_positions": [10],
                    "segment_widths": [10, 10],
                    "boundary_scores": [0.0],
                },
                "3": {
                    "feasible": True,
                    "total_score": 90.0,
                    "cut_positions": [0, 5, 10, 20],
                    "internal_cut_positions": [5, 10],
                    "segment_widths": [5, 5, 10],
                    # position 5 is new (symmetric diff) and scores 90.0 (>=35)
                    "boundary_scores": [90.0, 0.0],
                },
            },
        )
        self.assertTrue(exp5.material_boundary_change(record, 3))

    def test_material_boundary_change_false_when_only_whitespace_shift(self):
        record = _make_record(
            p_end=20,
            k_min=2,
            frontier=[[2, 0.0], [3, 10.0]],
            per_k={
                "2": {
                    "feasible": True,
                    "total_score": 0.0,
                    "cut_positions": [0, 10, 20],
                    "internal_cut_positions": [10],
                    "segment_widths": [10, 10],
                    "boundary_scores": [0.0],
                },
                "3": {
                    "feasible": True,
                    "total_score": 10.0,
                    "cut_positions": [0, 5, 10, 20],
                    "internal_cut_positions": [5, 10],
                    # new position 5 only scores 10.0 (< 35 threshold)
                    "boundary_scores": [10.0, 0.0],
                    "segment_widths": [5, 5, 10],
                },
            },
        )
        self.assertFalse(exp5.material_boundary_change(record, 3))

    def test_is_non_monotonic_detects_decrease_above_k_min(self):
        record = _make_record(
            p_end=20,
            k_min=2,
            frontier=[[2, 0.0], [3, 20.0]],
            per_k={
                "2": {"feasible": True, "total_score": 0.0, "cut_positions": [0, 10, 20], "internal_cut_positions": [10], "segment_widths": [10, 10], "boundary_scores": [0.0]},
                "3": {"feasible": True, "total_score": 20.0, "cut_positions": [0, 5, 10, 20], "internal_cut_positions": [5, 10], "segment_widths": [5, 5, 10], "boundary_scores": [10.0, 10.0]},
                "4": {"feasible": True, "total_score": 5.0, "cut_positions": [0, 3, 8, 13, 20], "internal_cut_positions": [3, 8, 13], "segment_widths": [3, 5, 5, 7], "boundary_scores": [0.0, 0.0, 5.0]},
            },
        )
        self.assertTrue(exp5.is_non_monotonic(record))

    def test_is_non_monotonic_false_for_monotonic_curve(self):
        alt = self.record
        # constructed fixture's scores 0 -> 20 -> 40 -> 45 are non-decreasing
        self.assertFalse(exp5.is_non_monotonic(alt))


class IntegrityCheckFailureTests(unittest.TestCase):
    def test_finalize_items_raises_on_char_length_mismatch(self):
        record = _make_record(
            p_start=0,
            p_end=20,
            k_min=2,
            frontier=[[2, 0.0], [3, 20.0]],
            per_k={
                "2": {"feasible": True, "total_score": 0.0, "cut_positions": [0, 10, 20], "internal_cut_positions": [10], "segment_widths": [10, 10], "boundary_scores": [0.0]},
                "3": {"feasible": True, "total_score": 20.0, "cut_positions": [0, 5, 10, 20], "internal_cut_positions": [5, 10], "segment_widths": [5, 5, 10], "boundary_scores": [10.0, 10.0]},
            },
        )
        record["paragraph_char_length"] = 999  # deliberately wrong
        item = exp5.CandidateItem(record, 3, 20.0)
        item.boundary_condition_candidate = False
        item.primary_sample = True
        with self.assertRaises(exp5.IntegrityError):
            exp5.finalize_items(
                [item],
                {record["source_file"]: "x" * 20},
                {(record["source_file"], 0): False},
                seed=1,
                max_items=None,
            )

    def test_finalize_items_raises_when_alt_k_not_greater_than_k_min(self):
        record = _make_record(
            p_start=0,
            p_end=20,
            k_min=3,
            frontier=[[3, 0.0]],
            per_k={"3": {"feasible": True, "total_score": 0.0, "cut_positions": [0, 7, 14, 20], "internal_cut_positions": [7, 14], "segment_widths": [7, 7, 6], "boundary_scores": [0.0, 0.0]}},
        )
        item = exp5.CandidateItem(record, 3, 0.0)  # alt_k == k_min, invalid
        item.boundary_condition_candidate = False
        item.primary_sample = True
        with self.assertRaises(exp5.IntegrityError):
            exp5.finalize_items(
                [item],
                {record["source_file"]: "x" * 20},
                {(record["source_file"], 0): False},
                seed=1,
                max_items=None,
            )

    def test_load_results_rejects_missing_top_level_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.json"
            path.write_text(json.dumps({"meta": {}, "paragraphs": []}), encoding="utf-8")
            with self.assertRaises(exp5.IntegrityError):
                exp5.load_results(str(path))

    def test_discover_corpus_files_rejects_wrong_file_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "mcu1_slide_01.txt").write_text("x", encoding="utf-8")
            with self.assertRaises(exp5.IntegrityError):
                exp5.discover_corpus_files(tmp)


class ForbiddenTokenScanTests(unittest.TestCase):
    def test_assert_no_forbidden_tokens_passes_clean_text(self):
        exp5._assert_no_forbidden_tokens('{"item_id": "exp5-0001", "segmentation_1": ["a"]}', "fixture")

    def test_assert_no_forbidden_tokens_catches_leak(self):
        with self.assertRaises(exp5.IntegrityError):
            exp5._assert_no_forbidden_tokens('{"k_min": 3}', "fixture")


# ---------------------------------------------------------------------------
# End-to-end tests against the real Experiment 4 artifact and real corpus
# (both already present in the repository - not regenerated by these
# tests). Skipped gracefully if the Experiment 4 artifact is unavailable in
# a given environment, matching this project's convention of not making
# tests hard-fail on missing optional fixtures.
# ---------------------------------------------------------------------------


@unittest.skipUnless(REAL_RESULTS_JSON.exists() and REAL_CORPUS_DIR.exists(), "Experiment 4 artifacts not present")
class EndToEndDeterminismTests(unittest.TestCase):
    def setUp(self):
        self.tmpdirs = []

    def tearDown(self):
        for d in self.tmpdirs:
            shutil.rmtree(d, ignore_errors=True)

    def _run(self, **overrides):
        out = tempfile.mkdtemp()
        self.tmpdirs.append(out)
        args = exp5.parse_args(
            [
                "--results-json",
                str(REAL_RESULTS_JSON),
                "--corpus-dir",
                str(REAL_CORPUS_DIR),
                "--output-dir",
                out,
                "--items-per-stratum",
                "2",
                "--max-items",
                "12",
            ]
            + overrides.pop("extra_argv", [])
        )
        for k, v in overrides.items():
            setattr(args, k.replace("-", "_"), v)
        result = exp5.run(args)
        return out, result

    def test_same_seed_produces_byte_identical_output(self):
        out1, _ = self._run(seed=42)
        out2, _ = self._run(seed=42)
        for name in ("sample_manifest.json", "evaluation_items.json", "evaluation_items_blinded.json", "sampling_summary.txt"):
            with open(Path(out1) / name, encoding="utf-8") as f1, open(Path(out2) / name, encoding="utf-8") as f2:
                self.assertEqual(f1.read(), f2.read(), f"{name} differs between two runs with the same seed")

    def test_different_seed_changes_sample_or_order(self):
        out1, _ = self._run(seed=42)
        out2, _ = self._run(seed=1234)
        with open(Path(out1) / "evaluation_items.json", encoding="utf-8") as f1, open(Path(out2) / "evaluation_items.json", encoding="utf-8") as f2:
            self.assertNotEqual(f1.read(), f2.read())

    def test_blinded_artifact_has_no_forbidden_tokens(self):
        out, _ = self._run(seed=42)
        text = (Path(out) / "evaluation_items_blinded.json").read_text(encoding="utf-8").lower()
        for tok in exp5.FORBIDDEN_EVALUATOR_TOKENS:
            self.assertNotIn(tok, text, f"forbidden token {tok!r} leaked into blinded artifact")
        html_path = Path(out) / "evaluation.html"
        if html_path.exists():
            html_text = html_path.read_text(encoding="utf-8").lower()
            for tok in exp5.FORBIDDEN_EVALUATOR_TOKENS:
                self.assertNotIn(tok, html_text, f"forbidden token {tok!r} leaked into evaluation.html")

    def test_reconstruction_matches_source_paragraph_exactly(self):
        out, _ = self._run(seed=42)
        with open(Path(out) / "evaluation_items.json", encoding="utf-8") as f:
            items = json.load(f)
        self.assertGreater(len(items), 0)
        for item in items:
            self.assertEqual("".join(item["segmentation_k_min"]), item["source_text"])
            self.assertEqual("".join(item["segmentation_alternative"]), item["source_text"])

    def test_manifest_and_blinded_are_consistent(self):
        out, _ = self._run(seed=42)
        with open(Path(out) / "sample_manifest.json", encoding="utf-8") as f:
            manifest = {m["item_id"]: m for m in json.load(f)}
        with open(Path(out) / "evaluation_items_blinded.json", encoding="utf-8") as f:
            blinded = {b["item_id"]: b for b in json.load(f)}
        with open(Path(out) / "evaluation_items.json", encoding="utf-8") as f:
            full = {r["item_id"]: r for r in json.load(f)}
        self.assertEqual(set(manifest), set(blinded))
        self.assertEqual(set(manifest), set(full))
        for item_id, m in manifest.items():
            r = full[item_id]
            b = blinded[item_id]
            if m["segmentation_1_is"] == "k_min":
                self.assertEqual(b["segmentation_1"], r["segmentation_k_min"])
                self.assertEqual(b["segmentation_2"], r["segmentation_alternative"])
            else:
                self.assertEqual(b["segmentation_1"], r["segmentation_alternative"])
                self.assertEqual(b["segmentation_2"], r["segmentation_k_min"])

    def test_all_selected_alt_k_are_frontier_points_greater_than_k_min(self):
        out, _ = self._run(seed=42)
        with open(Path(out) / "evaluation_items.json", encoding="utf-8") as f:
            items = json.load(f)
        for item in items:
            frontier_ks = {k for k, _ in item["pareto_frontier"]}
            self.assertIn(item["alternative_k"], frontier_ks)
            self.assertGreater(item["alternative_k"], item["k_min"])

    def test_min_segment_width_filter_is_configurable(self):
        # A very permissive filter (min width 1) should run successfully
        # and admit at least as many primary-sample items as the default
        # (min width 4) filter would for the same seed/config, since fewer
        # candidates get excluded by the width gate.
        out_loose, _ = self._run(seed=42, min_segment_width=1)
        with open(Path(out_loose) / "evaluation_items.json", encoding="utf-8") as f:
            items = json.load(f)
        self.assertGreater(len(items), 0)
        for item in items:
            self.assertGreaterEqual(item["k_min_width_stats"]["min_segment_width"], 1)


if __name__ == "__main__":
    unittest.main()
