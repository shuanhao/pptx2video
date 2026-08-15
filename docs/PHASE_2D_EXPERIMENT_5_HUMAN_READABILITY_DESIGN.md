# Phase 2D — Experiment 5: Human Readability Validation Design

**Round type:** DESIGN-ONLY. This document specifies how Experiment 5
should be performed in a future round. It does not implement Experiment 5,
does not modify production code, does not modify Phase 1-2D or adapter
code, does not modify existing tests, and does not introduce Variable-K
behavior, a threshold, or a penalty.

Every claim is labeled **FACT** (directly observed from Experiment 4's
artifacts or repository source), **INFERENCE** (a conclusion logically
supported by that evidence), or **HYPOTHESIS** (a proposed explanation or
future idea not established by any completed experiment). Proposed
Experiment 5 outcomes are never presented as existing evidence.

---

## 1. Executive Summary

Experiment 4 established, over the real 39-file corpus, that a majority of
paragraphs (56.4%) have a segment count `K` above the current Phase 2D
minimum (`K_min`) at which the DP can select a higher-scoring set of
boundaries, and that this recoverable score is occasionally large. It
explicitly could not and did not establish whether recovering that score
corresponds to a human-perceptible readability improvement, because Phase
2C scores are documented as relative/ordinal evidence, not a readability
utility. Experiment 5 designs — but does not run — a blinded human
evaluation that compares the current `K_min` segmentation against
Pareto-frontier alternatives for a carefully stratified, bias-controlled
sample of real paragraphs, in order to determine whether "higher
achievable Phase 2C score" and "better perceived subtitle segmentation"
are related, unrelated, or related only in some conditions. The design
explicitly allows a "no meaningful correlation found" result and does not
presuppose that Variable-K, a threshold, or any specific policy is
correct.

## 2. Experiment Status

**NOT STARTED.** No human evaluation has been conducted. No evaluation
interface, sampling script, or data file has been built. This document is
the design artifact only. Implementation requires an explicit future
instruction (per this task's own scope boundary).

## 3. Relationship to Experiment 4

Experiment 4 (`docs/phase2d/PHASE_2D_EXPERIMENT_4_PARETO_REPORT.md`,
`scripts/phase2d_pareto_simulation.py`,
`reports/phase2d/phase2d_pareto_results.json`,
`reports/phase2d/phase2d_pareto_summary.txt`) produced, per real-corpus
paragraph, the full achievable-score-vs-K curve and its Pareto frontier,
using the real, unmodified Phase 1→2C evidence chain and a generalized DP
verified byte-identical to the frozen production algorithm at `K=K_min`
(0 mismatches across all 4,128 paragraphs — FACT). Experiment 5 consumes
Experiment 4's output data as its *only* source of candidate segmentations
and scores; it does not recompute, second-guess, or re-derive any Phase
2C score or any Phase 2D segmentation. Where this document needs a number
from Experiment 4, it was re-read directly from
`reports/phase2d/phase2d_pareto_results.json` and
`reports/phase2d/phase2d_pareto_summary.txt` for this document (see
section 6), not copied from the Experiment 4 report's prose.

## 4. Problem Statement

Experiment 4 shows that a different (larger) `K` can, for a majority of
paragraphs, achieve a higher total Phase 2C score than `K_min`. Phase 2C's
own governing documentation
(`docs/phase2c/decisions/PHASE_2C_NUMERIC_BASELINE_DECISION.md`, section
6, quoted in the Round 4 K-Selection Architecture Review) states scores
are "signed relative boundary preferences... not probabilities,
confidence percentages, cut probabilities, or normalized scores," with
"no absolute interpretation... defined or implied." Consequently, a higher
achievable score is evidence of *something* — more of the boundary
evidence Phase 1-2C already collects is being used — but it is not, by
definition, evidence of better human-perceived subtitle quality. Nothing
in the repository currently measures human-perceived quality at all. This
is the gap Experiment 5 is designed to close: **is there any
relationship, and if so what shape, between Phase 2C score recovery /
`K` increase and actual human judgment of subtitle segmentation quality?**

## 5. Research Questions

**Primary question:** For real subtitle text, when Experiment 4 identifies
a segmentation with a higher Phase 2C score and/or a different `K` than
`K_min`, do human evaluators actually perceive that alternative
segmentation as better, worse, or equivalent to the current `K_min`
segmentation?

**Secondary questions** (all to be answered empirically, not assumed):

1. Does a higher Phase 2C score correlate with human preference?
2. Does a small `K` increase (e.g. `K_min+1`) improve perceived
   readability?
3. Does a large `K` increase improve or hurt perceived readability?
4. Are there cases where Phase 2C strongly prefers one segmentation but
   humans prefer the other?
5. Are there cases where two segmentations have similar Phase 2C scores
   but materially different human readability?
6. Does the useful Pareto region Experiment 4 identified (frontier points
   close to `K_min`) correspond to a meaningful human-quality trade-off
   region, or is it not perceptible to readers at all?

No answer to any of these is assumed by this design. The sampling and
analysis plan below is built specifically to be capable of returning
"yes," "no," or "mixed/context-dependent" for each.

## 6. Existing Evidence Baseline

This section was independently re-verified against
`reports/phase2d/phase2d_pareto_results.json` and
`reports/phase2d/phase2d_pareto_summary.txt` for this document (not copied
from the Experiment 4 report's prose).

**FACT — corpus size and paragraph count.** 39 files
(`examples/notes/mcu1_slide_01.txt`...`mcu1_slide_21.txt`,
`mcu2_slide_01.txt`...`mcu2_slide_18.txt`); 4,128 non-blank paragraphs
(`aggregate.n_paragraphs` in the results JSON, matching the Experiment 4
report and the earlier Round 3 diagnostic report exactly).

**FACT — K_min distribution.** 1,294 paragraphs (31.3%) at `K_min=1`;
1,455 (35.2%) at `K_min=2`; a decreasing tail up to `K_min=16`; 2,834
paragraphs (68.7%) have `K_min>1`.

**FACT — K_max characteristics.** `K_max` (structural maximum — every
candidate anchor used as a cut) ranges from 2 to 175 across the corpus,
heavily right-skewed; the single largest value (175) occurs in one
paragraph of `mcu1_slide_20.txt`. `K_max` is frequently far larger than
any point that is ever useful (see Pareto frontier characteristics
below) — it should not itself be read as a plausible operating range.

**FACT — recoverable vs. non-recoverable score.** 2,329 of 4,128
paragraphs (56.4%) have at least one `K>K_min` with a strictly higher
achievable Phase 2C score than `K_min` ("recoverable score" paragraphs).
1,799 (43.6%) have no such `K` — `K_min` already achieves the maximum
achievable score anywhere in the examined range ("control" paragraphs).

**FACT — Pareto frontier characteristics.** Frontier size (count of
non-dominated `(K, score)` points): mean 3.12, median 2, min 1
(exactly the 1,799 control paragraphs), max 29
(`examples/notes/mcu2_slide_17.txt`, paragraph 11). Frontier's maximum
`K` (largest `K` that is ever non-dominated): mean 4.54, median 3, max 39.
**INFERENCE** (already drawn in the Experiment 4 report, re-confirmed
here): the practically relevant trade-off region is concentrated within a
handful of segments above `K_min`, not the full structural range.

**FACT — distribution of achievable score gain, among the 2,329
recoverable paragraphs** (best-frontier-point score minus `K_min` score;
computed fresh for this document from the results JSON): minimum 10.0,
25th percentile 20.0, median 35.0, 75th percentile 70.0, 90th percentile
130.0, maximum 560.0, mean 59.8.

**FACT — distribution of `ΔK` at the best frontier point**, among the
2,329 recoverable paragraphs (computed fresh for this document): `ΔK=1`
in 471 paragraphs, `ΔK=2` in 590, `ΔK=3` in 371, `ΔK=4` in 264, `ΔK=5` in
189, with a long tail out to `ΔK=28`. 81.0% of recoverable paragraphs have
their best frontier point within `ΔK≤5` of `K_min`.

**FACT — representative large-gain case.** `examples/notes/mcu1_slide_08.txt`,
paragraph 131 (offsets 2353-2462, `K_min=11`): the text is "希望大家記住，
MCU 真正的價值不只是運算，而是整合。它將感知、判斷與控制串聯成完整的控制迴路，
讓產品能夠即時反應、穩定運作，並透過軟體持續擴充功能。這也是 Embedded System
能夠實現智慧化的核心基礎。" At `K_min=11`, every segment is packed to within 1
display-width unit of the 18-unit ceiling (widths
`[18,18,17,18,18,18,18,18,17,18,18]`), and the total score is only 10.0.
At `K=12` (`ΔK=1`), widths become
`[14,18,18,11,16,16,18,18,18,16,17,16]` and the score jumps to 285.0.

**FACT — representative moderate-gain case.**
`examples/notes/mcu1_slide_01.txt`, paragraph 3 (offsets 215-245,
`K_min=3`): text "在 Week 1，我們將先回答幾個最基本，也是最重要的問題。" At
`K_min=3`, widths `[17,18,18]`, score 35.0, cuts at offsets `[227,236]`.
At `K=4`, widths `[11,12,12,18]`, score 70.0, cuts at
`[224,230,236]` — a `ΔK=1`, `Δscore=35.0` case.

**FACT — representative small-gain case.**
`examples/notes/mcu1_slide_01.txt`, paragraph 0 (offsets 0-23, `K_min=3`):
text "各位同仁，歡迎參加 MCU 基礎知識培訓計畫。" `K_min=3`: widths
`[10,13,18]`, score 45.0. `K=4`: widths `[10,8,5,18]`, score 55.0 — a
`ΔK=1`, `Δscore=10.0` case (the single most common gain value in the
corpus).

**FACT — representative control (no recoverable score) case.**
`examples/notes/mcu1_slide_02.txt`, paragraph 2 (offsets 58-79,
`K_min=3`): text "在正式開始之前，我想先請大家思考一個問題。" `K_min=3`:
widths `[16,12,14]`, score 35.0. `K=4`: widths `[8,8,12,14]`, score is
still 35.0 — the extra segment produces zero score change; `K_min`
already dominates.

**FACT — important unusual case: degenerate high-K behavior.**
`examples/notes/mcu1_slide_02.txt`, paragraph 29 (offsets around
845-885, `K_min=4`, `K_max=42`): at `K_min=4`, widths `[16,18,17,18]`,
score 10.0. By `K=38`, the DP is forced to select segments of width 1-2
display units each (essentially single-character or single-syllable
"segments"), reaching a score of 155.0; at `K=39` the score *drops* to
125.0 (a negative marginal step), because the DP must now select a
negative-scored candidate to reach the exact target count. **INFERENCE:**
segmentations near `K_max` are combinatorially reachable and can carry a
locally high raw score, but they visibly do not resemble anything a
subtitle segmenter should ever produce (single-character lines). **This
is a direct, concrete illustration of why "higher achievable score" and
"better subtitle" cannot be assumed equivalent, and why Experiment 5's
candidate-selection rules (section 10) must explicitly exclude
degenerate high-`K` alternatives from the human-facing sample even though
they are technically part of the Pareto-eligible search space.**

No claim above should be read as evidence about human readability —
all of section 6 describes only what Experiment 4 already measured
algorithmically.

## 7. Experimental Principles

Experiment 5 maintains a strict separation between two categories that
must never be merged:

- **(A) Algorithmic evidence** — Phase 2C boundary scores, `K`, the
  Pareto frontier, segment boundaries, display width. This is all
  produced once, by Experiment 4's existing artifacts, and is never
  regenerated, recalculated, or reinterpreted by Experiment 5.
- **(B) Human evaluation** — readability, naturalness, linguistic
  boundary quality, subtitle coherence, perceived segmentation quality.
  This is collected fresh, from human evaluators, and is never converted
  back into a Phase 2C score, never used to modify
  `boundary_scoring.py`, and never treated as validating or invalidating
  any specific numeric weight in the existing scoring model.

Additional binding principles for this design (verbatim from the task's
scope, restated as design constraints):

- Do not assume higher Phase 2C score means better readability.
- Do not assume fewer subtitles are better.
- Do not assume more subtitles are better.
- Do not use production (`subtitle_segmenter.py`) segmentation as a human
  ground truth — it is one more candidate segmentation, not an oracle.
- Do not use "looks reasonable to the developer" as evidence — only
  structured, blinded ratings from evaluators who did not build the
  algorithm count as evidence.
- The design must be capable of producing evidence in either direction,
  including "no relationship."

## 8. Corpus and Sampling Strategy

**Source corpus:** the same 39-file `examples/notes/*.txt` real corpus
used by Experiment 4, read directly (not reconstructed from JSON), with
`max_display_width=18`, and paragraph/candidate structure taken verbatim
from `reports/phase2d/phase2d_pareto_results.json`.

**Unit of evaluation:** one paragraph-level comparison (`K_min`
segmentation vs. one alternative-`K` segmentation of the *same*
paragraph, same source text) is one evaluation item. Full-file or
cross-paragraph comparisons are out of scope for the primary experiment
(paragraphs are already the independent unit both Phase 2D and Experiment
4 operate on).

**Population:** 4,128 paragraphs total; 2,329 with a non-trivial
alternative (recoverable-score paragraphs) and 1,799 without (control
paragraphs). Manual evaluation of all 4,128 is explicitly out of scope
(task section 6). A stratified sample is drawn instead (section 9-10).

**Target sample size:** this document specifies the *selection procedure*
(deterministic given a seed), not a final fixed count — the actual count
should be chosen at implementation time to balance evaluator burden
against the statistical plan's needs (section 18). As a starting anchor:
an item budget in the range of 60-120 evaluation items (i.e. roughly
1.5-3% of the 4,128-paragraph population) is enough to populate every
stratum in section 9 with a handful of items each while remaining
completable by a small evaluator panel without excessive fatigue; this
number is a design starting point for the implementation round to
confirm or adjust, not a claim that it yields statistical significance
(see section 18's explicit caveat on power).

## 9. Experimental Strata

Every stratum below is defined **operationally**, using thresholds
derived from Experiment 4's own observed distributions (section 6), not
arbitrary round numbers:

| Stratum | Definition | Operational rule | Approx. population |
|---|---|---|---|
| A — Control | No recoverable score | `pareto_frontier` has exactly 1 point (`K_min` itself) | 1,799 paragraphs |
| B — Small recoverable score | Modest score improvement | best-frontier-point gain in `[10, 20)` (≤ 25th percentile of recoverable-paragraph gains) | ~25% of 2,329 |
| C — Moderate recoverable score | Meaningful, unexceptional improvement | gain in `[20, 70)` (25th-75th percentile) | ~50% of 2,329 |
| D — Large recoverable score | Unusually large improvement | gain `≥ 70` (≥ 75th percentile); a "very large" sub-tag for gain `≥ 130` (≥ 90th percentile) can be reported separately | ~25% / ~10% of 2,329 |
| E — ΔK strata | Cost, in added segments, of reaching the best frontier point | `ΔK=1`, `ΔK=2`, `ΔK=3`, `ΔK≥4` (bucketed; 471/590/371/897 paragraphs respectively among recoverable paragraphs) | as above |
| F — Frontier shape | Richness of the trade-off | frontier size `=1` (stratum A by definition), `=2`, `>2` | 1,799 / to be counted / to be counted from JSON at sampling time |
| G — Non-monotonic | Score-vs-K curve decreases somewhere above `K_min` | at least one `K` in `(K_min, K_max]` with `score(K) < score(K-1)` | 9 paragraphs corpus-wide (FACT, from Experiment 4); every one should be included if feasible, given the small population |
| H — Material boundary-placement change | The alternative segmentation moves a cut across a linguistically meaningful point (e.g. across a clause/sentence-final candidate that scored ≥ 35, not just a whitespace-only shift) | operational filter, applied at candidate-selection time (section 10): require the *symmetric difference* of internal cut positions between `K_min` and the alternative to include at least one position whose Phase 2C score is ≥ 35 (`CLAUSE`/`SENTENCE_FINAL`-class evidence, not just `+10` whitespace-adjacency) | to be counted from JSON at sampling time |

Strata A-D and G are mutually informative about *whether* a relationship
exists at all; E, F, and H are mutually informative about *where/how
strongly* it exists. Every stratum here maps directly to a research
question in section 5 (A/no-recoverable-score tests question 6's
control side; B-D test questions 1-3; E tests question 2/3 jointly; G
tests whether non-monotonic curve shape has any human-perceptible
counterpart; H guards against sampling comparisons that differ only in a
display-width technicality rather than a real linguistic decision).

## 10. Candidate Selection Rules

Given the results JSON, candidate selection for one item is fully
determined by the following procedure (specified precisely enough to
implement later without further design decisions):

1. **Enumerate the population** for a target stratum by filtering
   `paragraphs[]` entries on the operational rule in section 9.
2. **Exclude degenerate alternatives.** For any paragraph being
   considered for strata B-H, the alternative `K` offered to evaluators
   must be chosen from the paragraph's `pareto_frontier`, and must
   additionally satisfy a sanity filter: the resulting segmentation's
   minimum segment display width must be `≥ 4` (an arbitrary-looking but
   evidence-grounded floor — the degenerate case in section 6's "unusual
   case" example has segments of width 1-2, which are visibly not
   candidate subtitle lines by any reasonable standard; 4 is chosen to
   exclude single-character/near-single-character segments while not yet
   imposing any stronger stylistic judgment). Any paragraph whose entire
   frontier (above `K_min`) fails this filter is excluded from the
   sampling population for strata B-H (it may still be reportable as a
   qualitative note, per section 19).
3. **Choose the alternative `K`** for a given item:
   - For stratum E ("ΔK strata"), the alternative is the frontier point
     at exactly `K_min + 1`, `K_min + 2`, or `K_min + 3` (if present on
     the frontier; if the exact `K` is not itself a frontier point,
     select the smallest frontier `K > K_min` instead and record the
     substitution).
   - For strata B/C/D (gain-size strata) and G (non-monotonic), the
     alternative is the frontier point with the maximum score (the
     "best" point), unless that point fails the degeneracy filter in
     step 2, in which case the next-best frontier point is used and the
     substitution is recorded.
   - For stratum F (frontier shape), the alternative is any frontier
     point other than `K_min` itself, chosen by the random draw in step
     4 among the qualifying frontier points.
4. **Randomize within stratum.** Within each stratum's qualifying
   population, candidates are drawn uniformly at random without
   replacement, using a fixed, published seed (see section 21) applied
   to a deterministic ordering of `(source_file, paragraph_index)` pairs
   — this makes the exact sample reproducible by re-running the same
   seed against the same `phase2d_pareto_results.json`.
5. **De-duplicate across strata.** A paragraph may qualify for more than
   one stratum (e.g. large gain and `ΔK=1` simultaneously). The
   implementation should decide once, before drawing, whether
   overlapping strata are allowed to share paragraphs (denser coverage,
   fewer unique paragraphs) or must be disjoint (broader coverage, more
   evaluator burden) — this document recommends allowing overlap for
   strata that are conceptually orthogonal (E and F over B-D) but keeping
   A/B/C/D mutually exclusive by construction (they already partition the
   recoverable population by gain size).
6. **Assign a stable item ID** to every selected `(source_file,
   paragraph_index, alternative_K)` triple before any randomized display
   assembly happens (section 21).

## 11. Comparison Conditions

**Condition A (always present):** the existing Phase 2D `K_min`
segmentation for the paragraph, taken verbatim from
`per_k[str(k_min)].cut_positions` / `.internal_cut_positions` in the
results JSON (equivalently reproducible by calling the frozen
`boundary_segmentation.segment_boundaries()` — both are proven identical
by Experiment 4's own integrity check).

**Condition B (the comparison target):** one Pareto-frontier alternative
with `K > K_min`, selected per section 10 — **not automatically
`K_min + 1`** in every case. The specific frontier point used depends on
which stratum the item belongs to (section 10, step 3).

**Design choice — pairwise, not multi-way.** Each evaluation item
compares exactly two segmentations of one paragraph (`K_min` vs. one
alternative), not three or more simultaneously. Rationale: (a) it
minimizes evaluator fatigue and cognitive load (task section 8's own
requirement), (b) pairwise comparison is the right unit for the primary
research question ("do humans prefer A or B"), and (c) if a paragraph is
sampled into multiple strata with different alternative `K` values, it
simply becomes multiple separate pairwise items (still simpler for an
evaluator than a single ranked multi-way judgment). A future round could
revisit this if position along the whole frontier (not just one point)
turns out to matter, but that is a heavier protocol not justified by
current evidence.

**Not automatically `K_min+1` — justification.** Section 6's "large-gain"
and "moderate-gain" examples both happened to have their best frontier
point at `ΔK=1`, but section 6 also shows 43% of recoverable paragraphs
need `ΔK≥3` to reach their best point (section 6's `mcu1_slide_02`
paragraph 67 example: `ΔK=2`, gain 105.0). Always testing `K_min+1` would
systematically under-sample the paragraphs where the real trade-off only
appears further out on the frontier, biasing the experiment toward small
effects.

## 12. Blinding and Randomization

Evaluators see **only**: the paragraph's source text, rendered as two
labeled segmentations ("Segmentation 1" / "Segmentation 2", not "A" /
"B" / "K_min" / "alternative" / "current" / "experimental"), with
identical typography, font, and line-wrap width for both. Evaluators do
**not** see: Phase 2C scores, `K` values, Pareto frontier information,
which algorithm or experiment produced which segmentation, or any hint
about which one is expected to "win."

- **Left/right (or top/bottom) ordering is randomized per item**, using a
  seed independent from the sampling seed (section 21), so a given
  evaluator cannot learn "Segmentation 1 is always the new one" from
  repeated exposure.
- **The mapping from "Segmentation 1/2" back to "K_min / alternative" is
  stored only in the machine-readable data file** (section 17), never
  shown to the evaluator and never referenced in the evaluation UI's
  visible text or file names.
- If the same evaluator rates multiple items, item order across the
  whole session should also be randomized (not grouped by stratum), so
  that stratum membership cannot be inferred from session position
  either.

## 13. Human Evaluation Dimensions

The task instructs selecting the *smallest useful set*, not every
plausible dimension. Two primary dimensions and one secondary dimension
are proposed:

**Primary 1 — Overall segmentation preference.** What the evaluator
judges: "Considering everything about how this text has been broken into
subtitle lines — where it breaks, whether each line reads naturally, and
whether the breaks fall in sensible places — which version do you
prefer, if either?" This is the dimension that directly answers the
primary research question (section 5) and is the one used for the core
pairwise-preference analysis (section 18).

**Primary 2 — Awkward / mid-phrase splitting.** What the evaluator
judges: "Does either version cut in the middle of a word, a name, a
number, or a short clause that reads awkwardly when interrupted there?"
Rating: for each version independently, "no awkward splits" / "at least
one awkward split." This dimension exists because it is the most
concrete, low-ambiguity signal available (evaluators do not need
linguistic training to notice an interrupted phrase), and it is the
dimension Phase 2D's own known limitations (module docstring: "no
CJK/jieba word-boundary awareness... a long, unpunctuated CJK run will be
cut based on width alone") predicts might diverge between `K_min` and the
alternative in a *specific, checkable* way — this dimension can
corroborate or contradict that predicted mechanism directly. High-quality
example: a cut that falls exactly at a punctuation mark or a natural
clause boundary ("...而是整合。它將感知..." cut after "。"). Low-quality
example: a cut that falls inside a proper noun or a multi-character
technical term (e.g. splitting "門禁系統" — already documented in the
Round 3 diagnostic report as a real corpus occurrence — across two
lines).

**Secondary — Perceived reading burden.** What the evaluator judges, on
a single 1-5 scale per version (not paired): "How easy is this version to
read as a subtitle, on its own, without comparing it to the other
version?" This is intentionally independent-rating rather than
comparative, to catch a scenario the pairwise dimension alone cannot:
both segmentations being judged roughly equally awkward or equally good
in absolute terms even when one is picked as "preferred" relatively.

Dimensions explicitly **not** included, and why: "natural linguistic
segmentation" and "semantic coherence within a subtitle" (task section
10's dimensions 2 and 4) are judged to be largely subsumed by Primary 1
and Primary 2 together for evaluators without linguistics training, and
adding them as separate rated dimensions would increase evaluator burden
without a clear expectation of new signal; "cognitive reading burden" is
kept as the one secondary dimension rather than duplicated across
several near-synonymous labels. This selection can be revisited once
Experiment 5's implementation round pilots the protocol on a handful of
items and observes whether evaluators find the two primary dimensions
sufficient to express their judgment.

## 14. Rating Protocol

**Primary 1 (overall preference)** uses a **5-point comparative scale**,
not independent 1-5 ratings, because the research question is inherently
comparative ("do humans prefer A or B") and a comparative scale avoids a
well-known weakness of independent Likert ratings (different evaluators
anchoring their 1-5 scale differently, making cross-evaluator comparison
unreliable):

```
-2  Segmentation 1 clearly better
-1  Segmentation 1 slightly better
 0  Approximately equivalent / no meaningful difference
+1  Segmentation 2 slightly better
+2  Segmentation 2 clearly better
```

(Sign is with respect to display position, not `K_min`/alternative — the
mapping back to `K_min`/alternative happens only during analysis, using
the stored, hidden randomization key from section 12.)

**Primary 2 (awkward splitting)** uses independent binary flags per
version ("Segmentation 1 has an awkward split: yes/no",
"Segmentation 2 has an awkward split: yes/no"), because the underlying
question ("is there an interruption here") is not inherently comparative
— both, neither, or either version could have the problem.

**Secondary (reading burden)** uses an independent 1-5 Likert rating per
version, collected after the comparative judgment (to avoid anchoring the
comparative judgment on an absolute scale first).

**Optional free-text comment** field per item, for qualitative notes —
not analyzed statistically, used only to help interpret disagreement
cases and counterexamples (section 19).

## 15. Evaluator Requirements

**Qualification:** native or native-level readers of Chinese, since the
corpus is CJK-dominant (Traditional Chinese) with embedded English
technical terms — matching the corpus, not a proxy population. Subtitle
industry professionals are **not** required: the research question is
about general perceived readability of subtitle-style text, not
professional subtitling-standard conformance, and requiring professional
credentials would needlessly shrink the available evaluator pool without
a stated justification for why professional norms specifically are the
right measuring stick at this stage. This can be revisited if Experiment
5's results suggest professional judgment diverges meaningfully from
general-reader judgment.

**Minimum evaluator count:** at least 3 independent evaluators per item,
so that agreement can be measured (section 18) rather than trusting a
single opinion. This is a floor, not a target — more evaluators improve
the reliability of the agreement and correlation statistics but the
design is not blocked on obtaining a large panel; the analysis plan
(section 18) is explicitly scoped to be honest about weak power if the
panel stays small.

**Handling disagreement:** for the comparative scale, use the *median*
of the 3+ ratings as the item's primary summary (robust to one outlier
evaluator); also report the raw spread (e.g. one evaluator says
"Segmentation 1 clearly better" while another says "Segmentation 2
clearly better" on the same item) as a first-class output, not something
averaged away — high-disagreement items are exactly the kind of evidence
section 19's counterexample analysis is looking for, not noise to be
discarded.

**No claim of statistical significance** is made or should be made from
this design at the anchor sample size (section 8) with a 3-evaluator
floor — the resulting cell sizes per stratum (a handful of items × 3
raters) support descriptive and exploratory conclusions (directionality,
qualitative patterns, presence of clear counterexamples) but not a
confirmatory hypothesis test with a stated false-positive rate. Section
18 states this limitation explicitly and does not propose an arbitrary
significance threshold.

## 16. Experimental Controls

- **Repeated items:** include a small number (e.g. 3-5) of duplicate
  items — the same `(paragraph, K_min, alternative)` triple shown twice
  to the same evaluator at different points in the session, with
  independent left/right randomization each time — to measure
  within-evaluator test-retest consistency. Large inconsistency on
  repeats would indicate the rating task itself is noisy/unreliable,
  which must be known before trusting any cross-item comparison.
- **A/B order randomization:** per item and per evaluator, as specified
  in section 12.
- **Balanced presentation:** across the full item set, "Segmentation 1"
  should map to `K_min` approximately as often as it maps to the
  alternative (targeting close to 50/50, verified after randomization,
  not assumed).
- **Identical typography and display width:** both segmentations in an
  item are rendered with the same font, font size, and the same
  `max_display_width=18` wrapping convention already used throughout
  Phase 1-2D, so evaluators are reacting to *where* the cuts are, not to
  incidental rendering differences.
- **Identical source text:** both segmentations of one item always come
  from the exact same paragraph's source text (never a paraphrase or a
  cross-paragraph comparison).
- **No timing differences, no audio:** see section 14 of the task
  (mirrored in section 24 below) — text-only presentation, no TTS
  duration, no synchronized playback.

## 17. Data Schema

Proposed (not implemented) machine-readable schema for one evaluation
item record. PII is limited to an evaluator identifier that must be a
locally-assigned opaque token (e.g. `evaluator_01`), never a name, email,
or other personal identifier:

```json
{
  "item_id": "exp5-0001",
  "source_file": "examples/notes/mcu1_slide_08.txt",
  "paragraph_index": 131,
  "paragraph_start_offset": 2353,
  "paragraph_end_offset": 2462,
  "source_text": "希望大家記住，MCU 真正的價值不只是運算，...",
  "stratum": ["D_large_gain", "E_delta_k_1"],
  "k_min": 11,
  "alternative_k": 12,
  "delta_k": 1,
  "phase2d_score_k_min": 10.0,
  "phase2d_score_alternative": 285.0,
  "delta_phase2d_score": 275.0,
  "segmentation_k_min": ["...", "...", "..."],
  "segmentation_alternative": ["...", "...", "..."],
  "randomized_display_order": "k_min_first | alternative_first",
  "display_order_seed": "<recorded per-item seed or index>",
  "is_repeat_item": false,
  "repeat_of_item_id": null,
  "ratings": [
    {
      "evaluator_id": "evaluator_01",
      "overall_preference": -1,
      "awkward_split_segmentation_1": false,
      "awkward_split_segmentation_2": true,
      "reading_burden_segmentation_1": 4,
      "reading_burden_segmentation_2": 2,
      "confidence": 3,
      "comment": "optional free text"
    }
  ]
}
```

Fields explicitly **excluded** by design: no evaluator name, email, or
other direct identifier; no evaluator demographic data beyond what
section 15 requires to state as a qualification (native/native-level
Chinese reader), and that qualification is recorded once per evaluator
in a separate roster file, not repeated per rating; no timestamp finer
than needed for session-order reconstruction (to avoid incidentally
enabling de-anonymization via timing correlation in a very small panel).

## 18. Statistical / Analytical Plan

- **Pairwise win rate.** Fraction of items where the median comparative
  rating favors the alternative vs. `K_min` vs. "equivalent," reported
  overall and broken down per stratum (sections 9). This is the primary,
  most interpretable output.
- **Mean/median ratings** for the secondary reading-burden dimension, per
  version, per stratum.
- **Evaluator agreement.** Simple pairwise percent agreement (do two
  evaluators pick the same side, ignoring magnitude) and, if the panel is
  large enough to make it meaningful, a chance-corrected agreement
  statistic (e.g. Krippendorff's alpha, appropriate for ordinal
  comparative data with more than 2 raters and possible missing ratings).
  Report both; do not rely on percent agreement alone since it does not
  correct for chance agreement.
- **Score-vs-human correlation.** The central analysis for research
  question 1: compute the **rank correlation** (Spearman's ρ, not a
  Pearson/linear correlation — there is no basis in the existing Phase 2C
  documentation for assuming a linear relationship between score and
  human preference, and Spearman only assumes a monotonic one, which is
  the weaker, more defensible assumption here) between `delta_phase2d_score`
  and the median comparative rating, across all non-control items.
  Separately compute the same correlation between `delta_k` and the
  rating, since Phase 2C score and `K` are related but not identical
  quantities (section 6's examples show the same `ΔK=1` can correspond to
  gains from 10.0 to 275.0).
- **Disagreement cases.** Explicitly list items where the comparative
  rating's sign is opposite the sign implied by `delta_phase2d_score`
  (i.e. Phase 2C prefers the alternative but humans preferred `K_min`, or
  vice versa) — feeds directly into section 19.
- **Interpretation bands — explicitly heuristic, not a formal test.**
  Given the sample-size and evaluator-count caveats in section 15, this
  document proposes *descriptive* interpretation bands for the Spearman
  ρ magnitude (e.g. `|ρ| < 0.2` as "no meaningful correlation," `0.2 ≤
  |ρ| < 0.5` as "weak," `|ρ| ≥ 0.5` as "moderate-to-strong" — commonly
  used descriptive conventions for correlation magnitude, not a
  pre-registered hypothesis-test threshold) to aid *qualitative*
  reporting of the result, paired with the raw win-rate and disagreement
  counts so a reader is not asked to trust a single number. **This
  document does not claim these bands constitute statistical
  significance testing**, and any future report using this plan should
  state the same caveat rather than imply a p-value-backed conclusion
  the sample size cannot support.
- If a future round wants a confirmatory (not exploratory) statistical
  claim, the sample size and evaluator count in this design would need to
  be increased and a pre-registered analysis plan with a stated
  significance threshold and multiple-comparison correction (many strata
  are tested) would need to be written before data collection — explicitly
  out of scope for this design.

## 19. Counterexample Analysis

The experiment is designed to actively surface, not merely tolerate,
disagreement between algorithmic evidence and human judgment. Each case
type below is mapped to where the design already looks for it:

- **(A) Phase 2C strongly prefers the alternative, humans strongly prefer
  `K_min`.** Surfaced by the disagreement-case analysis (section 18) on
  stratum D (large-gain) items — if this occurs, it is the single most
  important finding this experiment could produce, since it would
  directly show that maximizing achievable Phase 2C score can select a
  segmentation that is not the one people prefer.
- **(B) Phase 2C gain is small, but humans strongly prefer the
  alternative.** Surfaced by cross-referencing stratum B (small
  recoverable score) items against strong comparative ratings — would
  suggest the score model under-values something evaluators respond to.
- **(C) Phase 2C gain is large, but humans see no meaningful
  improvement.** Surfaced by stratum D items with a median rating near 0
  ("approximately equivalent") — would suggest large score gains are not
  automatically perceptible or valuable, directly answering research
  question 3 in the negative for those cases.
- **(D) `K` increases substantially, but readability becomes worse.**
  Surfaced by stratum E's `ΔK≥4` bucket combined with a negative-leaning
  comparative rating (alternative rated worse) — the degenerate-high-K
  illustration in section 6 predicts this is plausible, and the
  degeneracy filter (section 10) only excludes the most extreme cases
  (min segment width `<4`), not all large-`ΔK` alternatives, so this
  failure mode remains reachable by the sample.
- **(E) `K` increases by only one, but segmentation becomes materially
  better.** Surfaced by stratum E's `ΔK=1` bucket combined with a
  strongly-positive comparative rating — section 6's `mcu1_slide_08`
  example (`ΔK=1`, `Δscore=275.0`) is exactly the kind of item this
  bucket would include, making it a natural first candidate to test this
  case directly.

Any item meeting one of these patterns should be reported individually
(source file, paragraph index, both segmentations, the rating detail),
not folded only into an aggregate statistic — per the task's framing,
these cases are potentially more valuable than confirming examples.

## 20. Success / Failure Criteria

Experiment 5's success is **not** defined as "Variable-K wins," "Fixed-K
wins," or any other pre-determined policy outcome. Success is defined as
obtaining enough evidence to answer, for each of the following, with
"yes," "no," or "mixed/context-dependent" (all three are valid,
publishable outcomes):

1. Whether Phase 2C score (or `K`) correlates with human segmentation
   preference, and how strongly (section 18).
2. Whether additional `K` generally improves, generally harms, or has
   mixed effects on perceived readability (per stratum, not only in
   aggregate — the effect may differ by gain size or `ΔK`).
3. Whether the Pareto frontier region Experiment 4 identified as "useful"
   algorithmically corresponds to a region humans also find meaningfully
   different from `K_min` (research question 6).
4. Whether the evidence, taken together, is sufficient to justify
   starting a future K-selection *policy* design round (as opposed to
   remaining purely diagnostic).
5. Whether the evidence collected is **insufficient** (too few items,
   too much evaluator disagreement, too narrow a corpus) to answer 1-4 at
   all, in which case the explicit, valid conclusion is that a larger or
   differently-designed follow-up experiment is required before any
   policy decision — not that a policy decision should be made anyway
   despite thin evidence.

"No meaningful correlation found" is an explicitly valid, useful
Experiment 5 outcome — it would mean Phase 2C score is not, on its own, a
usable proxy for subtitle quality, which is itself an important
architectural finding for any future K-selection design.

## 21. Reproducibility

To make Experiment 5 fully reconstructible from this design plus its
future implementation:

- **Corpus version:** the exact 39 files under `examples/notes/`, keyed
  by content — implementation should record the MD5 (or similar)
  checksum of each of the 39 files at the time of sampling, mirroring
  every prior Phase 2D round's checksum-based integrity practice (no
  `.git` exists in this repository — confirmed again this round by
  directory listing; checksums and file listings are used throughout this
  project in place of git-based diffing, and this document follows the
  same convention).
- **Experiment 4 baseline identification:** the exact
  `reports/phase2d/phase2d_pareto_results.json` used as the sampling
  source should be checksummed and the checksum recorded alongside the
  sample, since that file is itself derived from the corpus plus the
  frozen Phase 1-2D chain (already checksum-pinned per Experiment 4's own
  verification, section 4 of that report).
- **Sampling seed:** a single published integer seed, used for both (a)
  the within-stratum random draw (section 10, step 4) and (b) the
  left/right display randomization (section 12) — implementation should
  use two *derived* but distinct seeds (e.g. `seed` and `seed+1`, or two
  named constants) so that re-running the sampling step alone does not
  accidentally also re-randomize already-collected display orders.
- **Sample-selection algorithm:** exactly the procedure in section 10,
  implemented as a script that takes `(results_json_path, seed,
  per_stratum_target_counts)` and deterministically emits the item list —
  no manual/ad hoc item selection.
- **Evaluation-item IDs:** stable, deterministic IDs (e.g.
  `exp5-0001`, assigned in a fixed order such as sorted
  `(source_file, paragraph_index, alternative_k)`), recorded once and
  never reassigned even if the evaluator panel or schedule changes.
- **Evaluator randomization seed:** the per-item, per-evaluator
  left/right order should be derivable from `(item_id, evaluator_id,
  display_order_seed)` deterministically, so a specific evaluator's
  specific session can be reconstructed exactly.
- **Software/version information:** Python version, and checksums of
  `scripts/phase2d_pareto_simulation.py` (already recorded in the
  Experiment 4 report) plus whatever new sampling/analysis scripts a
  future implementation round adds.
- **Phase 2D / Phase 2C baseline identification:** the same 5 file
  checksums already tracked across every round in this series
  (`src/boundary_segmentation.py`, `src/boundary_segmentation_adapter.py`,
  and the three associated test files) should be re-confirmed unchanged
  at the time Experiment 5 is actually run, exactly as every prior round
  in this series has done, so that the segmentations shown to evaluators
  are provably the same ones Experiment 4 characterized.

## 22. Privacy and Data Handling

The corpus (`examples/notes/*.txt`) contains real project slide-note
content. The evaluation workflow must stay local:

- No corpus text should be uploaded to any cloud service (including a
  cloud-hosted survey tool, spreadsheet, or LLM API) as part of this
  design's baseline protocol.
- No external LLM should be used as an "evaluator" in the baseline
  design — the whole point of Experiment 5 is *human* judgment; an LLM
  judge would not answer the research question and would also raise a
  separate, unaddressed data-handling question about sending this
  content to a third-party API.
- A future round *may* consider a web-based human-evaluation platform for
  convenience (e.g. to recruit more evaluators), but if so, it must be
  listed only as a future optional implementation choice with its
  privacy trade-off explicitly stated (i.e. corpus text would leave the
  local environment and be hosted by a third party) — not adopted as
  part of this baseline design.
- The evaluator roster (qualification only, no personal identifiers per
  section 17) and all rating data should be stored locally under
  `data/phase2d/experiment5/` (section 23), not in any shared or
  cloud-synced location, unless a future round explicitly authorizes
  that and documents the trade-off.

## 23. Expected Future Artifacts

This design does not create any of the following. They are specified
here only so a future implementation round has a concrete target:

- `docs/phase2d/PHASE_2D_EXPERIMENT_5_HUMAN_READABILITY_DESIGN.md` — this
  document.
- `scripts/phase2d_experiment5_prepare.py` — future: implements section
  10's candidate-selection procedure and section 17's schema, reading
  `reports/phase2d/phase2d_pareto_results.json` and emitting the blinded
  item set.
- `scripts/phase2d_experiment5_analyze.py` — future: implements section
  18's analysis plan over collected ratings.
- `reports/phase2d/experiment5/` — future: human-readable summary
  reports analogous to `phase2d_pareto_summary.txt`.
- `data/phase2d/experiment5/` — future: the machine-readable item set and
  collected ratings (local only, per section 22).

None of these are created by this round.

## 24. Scope Boundaries

This design round explicitly does **not**:

- Implement Experiment 5 or any of the artifacts in section 23.
- Modify `src/boundary_segmentation.py`,
  `src/boundary_segmentation_adapter.py`, `src/subtitle_segmenter.py`,
  `src/subtitle_pipeline.py`, `src/subtitle_alignment.py`, or any Phase
  1/2A/2B/2C module.
- Modify any existing test file.
- Introduce Variable-K behavior, a segment-count threshold, or a scoring
  penalty of any kind.
- Evaluate SRT/subtitle timing, TTS duration, audio synchronization,
  slide duration, or subtitle persistence time — the primary Experiment 5
  protocol (sections 8-18) evaluates **segmentation quality only**, using
  static text presentation with no timing dimension. If timing is
  potentially important, it is recorded here as a candidate **future,
  separate experiment** (tentatively "Experiment 6"), not folded into
  Experiment 5.
- Use production segmentation as a human-evaluation ground truth (section
  7) — production may optionally appear as a third, still-blinded
  reference condition in a *future* extension, but is not part of this
  baseline two-condition (`K_min` vs. alternative) design.
- Claim statistical significance for any result the anchor sample size
  cannot support (section 15/18).

## 25. Risks and Limitations

- **Sample size limits statistical power.** The anchor sample size
  (section 8) and evaluator floor (section 15) support descriptive and
  exploratory conclusions, not confirmatory hypothesis testing. This is
  stated as a limitation, not remedied by this design.
- **Evaluator pool scarcity/homogeneity.** A small panel of native
  Chinese readers, likely drawn from people accessible to the project
  team, may not represent the full range of the eventual video audience
  (e.g. age, reading-speed, familiarity with the technical subject
  matter). This is a real limitation the analysis plan should state
  explicitly when reporting results, not something this design can
  eliminate procedurally.
- **Residual blinding risk.** Even with labels hidden, an alternative
  segmentation with a much larger `ΔK` may still be visually
  distinguishable purely by having more/shorter lines, which could let a
  sufficiently attentive evaluator guess which one is "the algorithm
  under test" — this cannot be fully eliminated when the two conditions
  differ in segment count by construction; it is mitigated (not solved)
  by never telling evaluators which condition is which and by including
  strata (E, small `ΔK`) where the visual difference is minimal.
- **Degenerate-alternative risk.** Section 10's minimum-segment-width
  filter (`≥4`) reduces but does not formally define away the risk of
  presenting an alternative segmentation that is trivially bad for
  reasons unrelated to the phenomenon under study (e.g. still-awkward but
  above the width-4 floor) — a future implementation round should treat
  this filter as a starting heuristic to be revisited after a small pilot
  batch, not a proven-sufficient rule.
- **Stratum G (non-monotonic) has a very small population (9
  paragraphs corpus-wide)** — any finding from this stratum is
  necessarily anecdotal/illustrative, not statistically generalizable,
  and should be reported as such.
- **Single corpus, single domain.** All 39 files are MCU/embedded-systems
  slide notes from one presentation series; findings may not generalize
  to other subject matter, presentation styles, or speakers. This
  limitation is inherited from Experiment 4 and applies identically here.

## 26. Decision Gates for the Next Phase

These gates describe what a completed Experiment 5 result would imply for
the *next* design round. None of them is triggered by this document —
they are defined now so that whoever runs Experiment 5 later has a clear,
pre-agreed mapping from result to next step, rather than re-litigating it
after seeing the data.

- **Gate A — Strong human correlation with Phase 2C score (or `K`)**
  (e.g. Spearman `|ρ| ≥ 0.5`, win rate clearly favoring the
  higher-scoring alternative, few section-19 disagreement cases).
  *Implication:* proceeding to design a K-selection **policy** round
  (i.e. resuming the Option B/C discussion the Round 4 K-Selection
  Architecture Review deferred) is well-justified by human evidence, not
  merely by algorithmic score recovery.
- **Gate B — Weak or inconsistent correlation** (`0.2 ≤ |ρ| < 0.5`, mixed
  win rates across strata, moderate disagreement-case count).
  *Implication:* a policy round is not yet justified corpus-wide; further
  investigation should focus on *which* strata/conditions show a
  relationship (e.g. only large-gain items, or only small-`ΔK` items)
  before generalizing to a policy.
- **Gate C — Human preference systematically penalizes excessive `K`**
  (large-`ΔK` items rated worse regardless of score gain).
  *Implication:* any future K-selection policy must bound `ΔK` (e.g. stay
  close to the Pareto frontier's low-`K` region) independent of how much
  score is technically recoverable further out — directly informs, but
  does not by itself decide, a future segment-count policy's shape.
- **Gate D — Human preference supports some additional `K` in specific,
  identifiable conditions** (e.g. only for stratum D/large-gain items,
  or only when the alternative resolves a stratum-H material
  boundary-placement change).
  *Implication:* a *conditional*, evidence-scoped policy investigation is
  justified (e.g. "when does the recoverable-score condition predict a
  human-preferred alternative"), rather than a blanket Variable-K change.
- **Gate E — Evidence is insufficient** (too few completed ratings, too
  much evaluator disagreement/inconsistency on repeat items, too narrow a
  sample to draw any of the above conclusions).
  *Implication:* no policy round should start; the next step is a larger
  or better-controlled repeat of Experiment 5 (larger panel, more items,
  or a revised protocol informed by whatever specifically failed), not a
  design decision made despite the gap.

In every gate, **the next step is a design/investigation round, never a
direct implementation of Variable-K, a threshold, or a penalty** — this
document's scope boundary (section 24) applies to the next round's
starting point as much as to this one.

## 27. Open Questions

- What is the final target sample size and per-stratum item count? This
  document proposes an anchor range (60-120 items, section 8) but leaves
  the exact number to the implementation round, informed by realistic
  evaluator availability.
- Should overlapping stratum membership (section 10, step 5) be allowed
  in the final implementation, or should every stratum be sampled from a
  disjoint pool? This document recommends allowing overlap for
  orthogonal strata but does not mandate it.
- Should a pilot batch (a handful of items) be run first to validate that
  the two primary evaluation dimensions (section 13) are sufficient
  before committing to the full sample? This document suggests it would
  be prudent but does not require it.
- Should production (`subtitle_segmenter.py`) segmentation ever be added
  as a third, blinded reference condition, and if so, in this experiment
  or a later one? This document defers that decision (section 24).
- Should Experiment 5's evaluator panel be the same for all items, or
  should items be distributed across a larger panel with partial overlap
  (trading broader coverage for weaker per-item agreement statistics)?
  Not decided here.
- Is a future "Experiment 6" (timing/SRT-inclusive readability) actually
  warranted, and if so, on what trigger? Not decided here; noted only as
  a placeholder in section 24.
