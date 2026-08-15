# Phase 2D — Experiment 4: Pareto Simulation (Score vs. K)

**Round type:** OFFLINE EXPERIMENT ONLY. Not Phase 2D Round 2 implementation,
not a Variable-K implementation, not a Phase 2C recalibration, not
production integration, not a threshold/penalty decision.

**Status:** COMPLETE. Simulator built and run against the full real 39-file
corpus. No production, Phase 1-2C, Phase 2D, adapter, or test file was
created, modified, or deleted.

Every claim below is labeled **FACT** (directly observed from the simulator
or from source), **INFERENCE** (a conclusion logically supported by the
observed data), or **HYPOTHESIS** (a possible explanation or future design
idea not established by this experiment). No inference is asserted as fact,
and this experiment does not select or argue for Fixed-K, Variable-K, a
threshold, or a penalty value.

---

## 1. Implementation Status

Complete. `scripts/phase2d_pareto_simulation.py` was written, executed once
against all 39 corpus files, and produced both required output artifacts.
The script is standalone analysis tooling; it is not imported by any
production or test module (verified, section 17).

## 2. Files Created

- `scripts/phase2d_pareto_simulation.py` — the simulator (documented in
  full in its own module docstring).
- `reports/phase2d/phase2d_pareto_results.json` — machine-readable,
  per-paragraph, per-K results (≈85 MB; 4,128 paragraph records).
- `reports/phase2d/phase2d_pareto_summary.txt` — human-readable corpus-level
  aggregate statistics.
- `docs/phase2d/PHASE_2D_EXPERIMENT_4_PARETO_REPORT.md` — this document.

No production module was created under `src/`. No production wiring was
added or modified anywhere.

## 3. Files Modified

None. This round only added the four new files listed in section 2.

## 4. Files Explicitly Verified Unchanged

Checksums taken before and after this round's work, all identical:

| File | MD5 |
|---|---|
| `src/subtitle_segmenter.py` | `9ecdb9741fabaac6fd4ccbaa643a6a58` |
| `src/subtitle_pipeline.py` | `2322747088fb9cfbc1eb3d30c4825e75` |
| `src/subtitle_alignment.py` | `9b14f0d6f68857e8630c9d97aa026e8a` |
| `src/text_structure.py` | `b1a7185f99d46741b30ffbf58208eda5` |
| `src/boundary_observation.py` | `292adeb728ccd6bd7661179459310c7e` |
| `src/boundary_classification.py` | `b8df71e36ac65d7e3abb1d8ce8933334` |
| `src/boundary_scoring.py` | `2a1ded4e11df16d976f5d7fa475204e6` |
| `src/boundary_segmentation.py` | `eb4a3f49f72bb49918f83e66d49dba41` |
| `src/boundary_segmentation_adapter.py` | `0adb935ab35132902189e9b324966495` |
| `tests/test_boundary_segmentation.py` | `f8ab97840e4ed6885f23356ccafb3e77` |
| `tests/test_boundary_segmentation_adapter.py` | `26a3eba51d23296c717487a40299d108` |
| `tests/test_shadow_mode_comparison.py` | `55d1cc45da517189a175f6201766bf7f` |

`examples/notes/*.txt` (the 39-file corpus, user-provided input data, not
produced by this round) was read only, never written.

No `.git` directory exists in this repository (confirmed again this
round); checksums/timestamps are used in place of git-based diffing, per
this task's own instruction and every prior round's precedent.

## 5. Simulator Architecture

`scripts/phase2d_pareto_simulation.py` is a standalone script under
`scripts/`. For each of the 39 files in `examples/notes/`:

1. Runs the real, unmodified Phase 1→2A→2B→2C chain via
   `boundary_segmentation_adapter._weighted_boundaries_for_text()` — no
   score, classification, or evidence logic is reimplemented anywhere.
2. Splits the file into paragraphs via `boundary_segmentation._split_paragraphs`
   (imported, not copied).
3. For each paragraph, computes candidate anchors via
   `boundary_segmentation._internal_positions` (imported), and the
   width-only `K_min` via `boundary_segmentation._greedy_min_k_boundaries`
   (imported) — the exact same function production Phase 2D calls today.
4. Runs a new generalized DP (`_paragraph_pareto`, written this round) that
   computes, for every `K` from 1 to `K_max` (the true structural maximum —
   every candidate anchor used as a cut), the maximum achievable total
   Phase 2C score of a width-feasible `K`-segment partition, using the
   *same* feasibility rule, tie-break rule, and per-cut score lookup as the
   frozen `_select_cut_positions` — just evaluated for every `K` instead of
   only `K_min`.
5. Cross-validates: calls the real, frozen `_select_cut_positions()`
   directly at `K = K_min` and asserts its result is byte-identical to this
   script's own DP result at `K = K_min`, for every one of the 4,128
   paragraphs.
6. Aggregates corpus-level statistics and writes the two output files.

Also computed, for reference only (never used to steer the simulation):
production segment counts via the unmodified
`subtitle_segmenter.segment_notes_for_subtitles()`, and current Phase 2D
(Option A) segment counts via the unmodified
`boundary_segmentation.segment_boundaries()`.

## 6. Exact Optimization Performed

For a fixed paragraph with anchors `a0=p_start, a1, ..., a(n-1)=p_end` and
a fixed `K`:

```
maximize   Σ score(cut_i)     over all choices of K-1 internal cut
                                positions c_1 < c_2 < ... < c_(K-1)
                                from {a1, ..., a(n-2)}
subject to  each resulting segment [a_i, a_j] either fits under
            max_display_width=18, or spans exactly two adjacent anchors
            (the same "finest granularity is always acceptable" last-resort
            rule the frozen algorithm already uses)
tie-break   lowest sum of squared segment widths, identical to the frozen
            algorithm
```

`score(cut_i)` is read verbatim from the real `WeightedBoundary.score` map
produced by the unmodified Phase 2C chain — never recomputed, rescaled, or
reinterpreted. Paragraph boundaries are always hard; no segment ever
crosses a paragraph boundary. This is exactly what the task specification
required and exactly what `_select_cut_positions` already computes for one
`K` — this experiment only removes the "stop at `K_min`" restriction.

## 7. K Range Handling

`K_min` = width-only minimum, from the unmodified
`_greedy_min_k_boundaries`. `K_max` = `n - 1` where `n` is the number of
anchors (paragraph start + every internal candidate + paragraph end) — the
true structural maximum, not an arbitrary small cap. Across the corpus,
`K_max` ranged from 2 to 175 (mean anchor count per paragraph ≈ 21, but one
paragraph in `mcu1_slide_20.txt` has 176 anchors). No paragraph's K range
was truncated.

## 8. Pareto Calculation Method

For each paragraph, a layered DP (`dp[k][i]`) is filled for every `k` from
1 to `K_max`, giving `best_score(K)` and its reconstructed partition for
every feasible `K` in one pass (`O(n^2 · K_max)` per paragraph). A point
`(K, score)` is on the Pareto frontier if no other feasible point
`(K2, score2)` exists with `score2 >= score` and `K2 <= K` and at least one
strict inequality (exact definition from the task spec, implemented
literally). Full run over all 4,128 paragraphs completed in 68.0 seconds;
0 integrity mismatches between this script's own `K=K_min` result and the
frozen `_select_cut_positions()`'s result, across all 4,128 paragraphs.

## 9. Real-Content Corpus Used

`examples/notes/*.txt` — the same 39 files (mcu1_slide_01-21,
mcu2_slide_01-18) used by Rounds 3 and 4, read directly, unmodified,
without any reconstruction from JSON. `max_display_width=18`, matching the
authoritative evaluation width established in Round 3.

## 10. Corpus Statistics

- Files: 39. Paragraphs: 4,128 (matches the Round 3 diagnostic baseline
  exactly — a consistency check that this independently-written script
  agrees with the earlier evaluation on basic corpus structure).
- Paragraphs with `K_min > 1`: 2,834 (68.7%).
- `K_min` distribution: 1,294 paragraphs (31.3%) at `K_min=1`; 1,455
  (35.2%) at `K_min=2`; 699 at 3; 307 at 4; a decreasing tail up to
  `K_min=16`. Full histogram in `reports/phase2d/phase2d_pareto_summary.txt`.
- `K_max` distribution: highly right-skewed, from 2 up to 175, reflecting
  paragraph length variance in the corpus.
- Total feasible `(paragraph, K)` points examined: 77,082.
- Production total segments (reference only): 10,372. Current Phase 2D
  (Option A, `K=K_min`) total segments (reference only): 9,985. Both
  numbers match the Round 3 diagnostic baseline exactly.

## 11. Key Score-vs-K Findings

**FACT.** For 1,799 of 4,128 paragraphs (43.6%), `K_min` already achieves
the maximum total score achievable anywhere in the examined `K` range — no
value of `K > K_min` ever produces a higher total score for these
paragraphs. (This is exactly the set of paragraphs whose Pareto frontier
has size 1 and whose step-1 gain is exactly 0 — the three numbers coincide
exactly: 1,799 = 1,799 = 1,799.)

**FACT.** For 2,329 of 4,128 paragraphs (56.4%), at least one `K > K_min`
achieves a strictly higher total score than `K_min` does.

**FACT (worked example).** `examples/notes/mcu1_slide_08.txt`, paragraph
131 (source offsets 2353-2462, text "希望大家記住，MCU 真正的價值不只是運算，
而是整合。它將感知...", `K_min=11`): at `K=11`, the only width-feasible
11-segment partition has segment widths
`[18,18,17,18,18,18,18,18,17,18,18]` (i.e. every segment packed to within
1 unit of the 18-unit ceiling) and a total score of only **10.0** (a single
`+10.0` whitespace-adjacency cut; every other forced cut lands on a
zero-scored `OTHER` position). At `K=12` — one single additional segment —
the same paragraph's optimal partition has widths
`[14,18,18,11,16,16,18,18,18,16,17,16]` and a total score of **285.0**,
selecting six much higher-value candidates (`35.0, 90.0, 35.0, 35.0, 80.0,
10.0`). **INFERENCE:** this demonstrates that `K_min` is not merely "a
little short" of an optimum in some paragraphs — for a paragraph like this
one, `K_min` can be a severely width-starved operating point where nearly
every segment is pinned near the width ceiling, leaving the score-maximizing
DP almost no freedom to respond to evidence at all, even though highly
positive-scored candidates exist a few characters away from where the
width constraint forces a cut.

**FACT.** The step-indexed mean score gain (`K_min → K_min+1 →
K_min+2 → ...`) is front-loaded and generally diminishing: mean gain
15.3 at step 1, 6.5 at step 2, 3.9 at step 3, falling below 1.0 by step 7
and below 0.1 by step ~20. **This is not, however, a strictly
non-increasing or strictly non-negative curve** — several later steps
(e.g. steps 30, 34-38, 42-54) show a *negative* mean gain. **FACT:** the
minimum observed value at those later steps is as low as -30.0.
**INFERENCE:** once a paragraph's supply of non-negative-scored candidates
is exhausted, forcing the DP to produce exactly one more segment than that
can require selecting a negative-scored (protection-penalized) cut it did
not have to select at a smaller `K`, so the achievable score at an exact
`K` can go *down* as `K` increases further past that point. This directly
falsifies any assumption that "more allowed segments can only weakly help
or never hurt" the exact-`K` achievable score — that assumption is true
only up to a hidden, paragraph-specific ceiling; beyond it, it is false.

## 12. Marginal Score-Gain Findings

**FACT.** Across all 72,954 examined `(paragraph, step)` marginal-gain
observations, the histogram is dominated by `Δscore = 0` (64,148
occurrences, 87.9%) and `Δscore = +10` (7,229, 9.9%); all other values
combined account for the remaining ~2.2%. **INFERENCE (corroborating
Round 3):** this closely mirrors the corpus's underlying raw Phase 2C
candidate score composition independently measured in the Round 3
diagnostic report (75.9% zero-scored, 15.9% scored 10.0 among all 87,735
candidates) — the marginal-gain shape is a direct consequence of which
scores exist to be picked up as `K` grows, not an artifact of the DP.

**FACT.** Negative marginal-gain steps are rare: 48 total occurrences (46
at -30.0, 2 at -20.0) across the entire corpus, confined to only 9 of
4,128 paragraphs (0.2%). **INFERENCE:** 48 exactly matches the Round 3
diagnostic's independently-counted total of negative-scored candidates in
the whole corpus (46 at -30 protection score, 2 at -20 INTERNAL score) —
each negative-scored candidate in the corpus corresponds to exactly one
forced negative marginal step somewhere in some paragraph's `K` sweep, when
and only when `K` is pushed far enough that no non-negative candidate
remains available.

**FACT.** The single largest marginal gain observed anywhere in the corpus
is +275.0, at the `mcu1_slide_08` paragraph 131 example above (step
`K=11→12`).

## 13. Pareto-Frontier Findings

**FACT.** Frontier size (number of non-dominated `(K, score)` points per
paragraph): mean 3.12, median 2, min 1, max 29 (in
`mcu2_slide_17.txt`, paragraph 11).

**FACT.** The frontier's maximum `K` (the largest `K` that is ever
non-dominated) has mean 4.54, median 3, maximum observed 39.
**INFERENCE:** even in paragraphs where growing `K` beyond `K_min` does
help, the *useful* trade-off region is concentrated close to `K_min` — a
median of only 3 additional segments beyond `K_min` captures the entire
non-dominated region for a typical paragraph. The very large `K_max`
values present in the corpus (up to 175) are essentially never part of any
non-dominated frontier point; they represent structurally possible but
score-irrelevant over-segmentation.

**FACT.** 1,799 paragraphs (43.6%) have a frontier of exactly 1 point
(`K_min` itself — no trade-off exists). 2,329 (56.4%) have a frontier of
2 or more points (a genuine trade-off region exists).

## 14. Any Surprising or Unexpected Behavior

- The `mcu1_slide_08` paragraph-131 case (section 11) was the most
  surprising single data point: a 28.5x score jump from a single additional
  segment, caused by `K_min` forcing near-maximal-width packing with
  essentially no freedom to respond to nearby high-value evidence.
- The score-vs-K curve is **not** monotonically non-decreasing at the tail
  of the range for some paragraphs — a finding that would not have been
  visible from a `K_min`-only or `K_min + small constant` experiment design
  (which is part of why the task explicitly required computing the full
  structural `K_max`, not an arbitrary small cap).
- The exact numeric coincidence between "paragraphs with zero step-1 gain"
  (1,799), "paragraphs with frontier size 1" (1,799), and "paragraphs
  where no K anywhere beats K_min" (1,799) held for every single paragraph
  in this corpus: whenever the very first additional segment fails to
  improve the score, no later, larger `K` ever improves it either.
  **HYPOTHESIS, not established by this experiment:** whether this
  "step-1-decides-everything" plateau pattern is a general mathematical
  property of this scoring/width-feasibility structure, or merely an
  empirical regularity of this particular 39-file corpus, is not proven
  here and would need a structural argument (or a counter-example search)
  to resolve.

## 15. Production Comparison (Reference Only)

| Metric | Value |
|---|---|
| Production total segments | 10,372 |
| Current Phase 2D (Option A, `K=K_min`) total segments | 9,985 |
| Delta | -387 |

These numbers are unchanged from the Round 3 diagnostic baseline (this
script recomputed them independently and reproduced them exactly). They
are reported for continuity only. **No parameter, threshold, or K-selection
choice in this experiment was tuned, adjusted, or selected to move this
delta.** The simulator does not use production as an optimization target
anywhere in its code (confirmed by inspection of
`scripts/phase2d_pareto_simulation.py`: `segment_notes_for_subtitles()` is
called exactly once per file, purely to populate a reference-only counter).

## 16. Test Results

`pytest tests/ -q` → **531 passed, 30 subtests passed** (unchanged from
every prior round's baseline; 2 pre-existing deprecation warnings
unrelated to this round).

## 17. Integrity Verification

- Exactly 4 new files created this round (section 2); zero existing files
  modified (section 3); all 12 protected files' checksums confirmed
  unchanged (section 4).
- `grep -rn "phase2d_pareto_simulation" src/ tests/` → no matches (exit
  code 1) — the simulator is not imported by production or test code.
- The simulator's own internal integrity check (real
  `_select_cut_positions()` vs. this script's DP at `K=K_min`) found **0
  mismatches across all 4,128 paragraphs** — the generalized DP is a
  faithful superset of the exact algorithm already running today, not an
  independent reimplementation that could have silently drifted from it.
- `pytest tests/ -q` unchanged at 531 passed / 30 subtests (section 16).
- No `.git` directory exists in this repository; verification used
  checksums, `grep`, and file-listing instead, consistent with every prior
  round.

## 18. Limitations

- The DP's objective is exactly "maximize the sum of per-cut Phase 2C
  scores for exactly `K` segments" — it says nothing about what a "good"
  number of segments is from a viewing/readability standpoint; that
  question is out of scope for Phase 2C's documented score semantics (see
  the K-Selection Architecture Review, section 6) and out of scope for this
  experiment.
- `K_max` (structural maximum) is often far larger than any point on the
  Pareto frontier (section 13); the raw `K_max` distribution reported in
  section 10 should not be read as "how large K should ever practically
  be" — it is reported because the task required the true structural
  maximum to be examined, not because large `K` values are informative on
  their own.
- This experiment examines paragraphs independently, exactly as the
  existing Phase 2D and this simulator's DP both do; it says nothing about
  cross-paragraph effects (e.g. total video length, subtitle pacing across
  a whole slide) — those are outside the scope of both the existing
  algorithm and this experiment.
- The corpus remains the same 39-file real corpus used in Round 3; the
  representativeness caveats already on record in
  `PHASE_2D_REAL_CONTENT_SHADOW_EVALUATION.md` and
  `PHASE_2D_REAL_CONTENT_DIAGNOSTIC_REPORT.md` still apply and are not
  re-litigated here.

## 19. What Is Proven

- **FACT:** A generalized DP sweeping `K` from `K_min` to the true
  structural `K_max`, using the same feasibility/tie-break rules as the
  frozen production algorithm, reproduces the frozen algorithm's own
  `K_min` result exactly, for all 4,128 real-corpus paragraphs (0
  mismatches).
- **FACT:** In a majority of paragraphs (56.4%), a strictly higher total
  Phase 2C score is achievable at some `K > K_min` than at `K_min` itself
  — i.e. `K_min` does not, in the majority of paragraphs, already sit at
  the score-maximizing point of the full structural K range.
- **FACT:** In the remaining paragraphs (43.6%), `K_min` already achieves
  the maximum achievable score anywhere in the range — more segments would
  never help.
- **FACT:** The achievable-score-vs-K relationship is not monotonic in
  general; it can decrease at large `K` once a paragraph's supply of
  non-negative-scored candidates is exhausted.
- **FACT:** The useful (non-dominated) trade-off region is typically small
  and close to `K_min` (median frontier max `K` of 3 additional segments),
  even though the structurally possible range can be enormous (up to 175).

## 20. What Remains Unknown

- Whether the 56.4%-of-paragraphs "recoverable score above `K_min`"
  finding should be acted on at all — Phase 2C scores are documented as
  relative/ordinal (K-Selection Architecture Review, section 6), so this
  experiment cannot and does not say whether recovering that score is
  "worth" an additional subtitle segment from a viewer's perspective.
- Whether the "step-1 decides everything" plateau pattern (section 14)
  generalizes beyond this corpus.
- Any segment-count policy — this experiment produces the trade-off
  curve; it does not, and by design was not asked to, produce or imply a
  rule for selecting a point on it.
- Whether a Pareto-informed variable-K design would actually improve
  perceived subtitle quality; that is a human-judgment question this
  experiment does not touch.

## 21. Recommended Next Design Question

The K-Selection Architecture Review (Round 4) identified that adopting any
form of variable-K requires a new segment-count policy decision that no
existing document currently supplies, and deferred that decision pending
this experiment's evidence. This experiment now shows concretely: (a) the
"recoverable score" opportunity is real and majority-prevalent (56.4% of
paragraphs), (b) it is occasionally dramatic in specific cases (the
28.5x mcu1_slide_08 example), but (c) the useful range is typically small
and concentrated just above `K_min` rather than open-ended.

The next design question this raises — **not answered here** — is: given
that Phase 2C scores carry no defined utility unit comparable to "the cost
of one more subtitle segment," what non-score-derived signal (human
readability judgment on a sample of these specific recoverable-score
paragraphs, a project-owner policy preference, or some other externally
supplied criterion) should be used to decide, for the 56.4% of paragraphs
where recoverable score exists, whether recovering it is worth adding a
segment? This is a policy question, not an algorithmic one, and answering
it does not require, and should not be preceded by, any implementation
change to Phase 2D.

---

**Explicit non-conclusions (per task scope):** This experiment does not
conclude that Variable-K is better than Fixed-K, that Fixed-K is better
than Variable-K, that any penalty or threshold value is correct, or that
`K` should "normally" be `K_min + 1` or any other fixed increment. It
reports the empirical score-vs-K shape observed in the real corpus and
nothing more.
