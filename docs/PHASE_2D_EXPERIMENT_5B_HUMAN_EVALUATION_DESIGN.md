# Phase 2D — Experiment 5B: Human Evaluation / Rating Collection & Analysis Design

**Round type:** DESIGN-ONLY. This document specifies how Experiment 5B —
rating collection against the existing, frozen Experiment 5A blinded
package, and the subsequent analysis of those ratings — should be
performed in a future, separately authorized implementation round. It
does not implement Experiment 5B, does not collect human ratings, does
not generate new evaluation data, and does not modify any production
file, Phase 2D file, adapter file, test file, or existing Experiment
4/5A artifact.

Every claim in this document is labeled **FACT** (directly observed from
the actual Experiment 4/5A artifacts or repository source), **DECISION**
(a design choice made in this document, with its rationale), **INFERENCE**
(a conclusion logically supported by existing evidence), or **OPEN
QUESTION** (left for the implementation round or a human decision-maker).
Where this task's instructions differ from the existing
`PHASE_2D_EXPERIMENT_5_HUMAN_READABILITY_DESIGN.md`, the difference is
identified explicitly in section 3 rather than silently reconciled.

---

## 1. Design Status

**NOT STARTED (implementation).** This document is the design artifact
only. No rating-collection tool, analysis script, or data file exists for
Experiment 5B. No human evaluation has been performed. Implementation
requires a separate, explicit future authorization, per this task's own
scope boundary.

## 2. Experiment Objective

Experiment 4 established that, for a majority of real-corpus paragraphs,
a segment count `K` above the current width-only minimum (`K_min`) can
achieve a strictly higher total Phase 2C boundary score. Experiment 5A
converted a stratified, bias-controlled sample of that finding into a
blinded pairwise comparison package (`K_min` segmentation vs. one
Pareto-frontier alternative, per paragraph). Neither experiment
established, or was designed to establish, whether recovering that score
corresponds to a human-perceived readability improvement.

Experiment 5B's objective is exactly one question:

> For the paragraphs in the Experiment 5A package, do human reviewers
> perceive the higher-`K` alternative segmentation as more readable, less
> readable, or about the same as the current `K_min` segmentation — and
> under what conditions (if any) does that differ?

Experiment 5B is explicitly **not** designed to prove that Variable-K is
correct, to select a threshold or penalty, or to decide a production
K-selection policy. It is designed to produce the human evidence a later,
separate architecture decision would need.

## 3. Relationship to Phase 2D / Experiment 4 / Experiment 5A

**FACT.** The conceptual position of this experiment in the project is:

```
Phase 1 -> Phase 2 (2A/2B/2C/2D) -> Design -> Implementation ->
Adapter + Shadow Mode -> Real-content validation -> Experiment 4 ->
Experiment 5A -> Experiment 5B (this document) -> Decision Gate ->
K-selection Architecture Decision -> Controlled Integration OR
documented rejection/deferral -> Phase 2D COMPLETE
```

Experiment 5B is a validation activity inside Phase 2D, not a new project
phase. This document does not introduce "Phase 2E," "Phase 5," or any
numbering outside the existing Phase 1-2D structure.

**FACT — frozen inputs re-confirmed by direct inspection for this
document** (not from memory; see section 4 for the full inventory):
`data/phase2d/experiment5/sample_manifest.json`,
`evaluation_items.json`, `evaluation_items_blinded.json`,
`evaluation.html`, `sampling_summary.txt`, and `checksums.json` all exist
in this workspace with the schemas described in section 5 and section 18
below. Per the handover established at the start of this task, the
equivalent files exist in the local Windows repository under
`data/phase2d_experiment5/` (flat naming) with identical content — the
path difference is a known, accepted environment difference, not a
content discrepancy, and is not investigated further here.

**Discrepancy log — differences between this task's instructions and the
existing `docs/phase2d/PHASE_2D_EXPERIMENT_5_HUMAN_READABILITY_DESIGN.md`**
(read in full for this document), classified per the required FACT /
DECISION / INFERENCE / OPEN QUESTION discipline:

1. **FACT.** The original design document (section 8) proposed an
   "anchor" sample-size range of 60-120 items without committing to an
   exact count. Experiment 5A's implementation produced exactly 69 items
   (66 primary, 3 boundary-condition) — inside that range. No
   discrepancy; the original design's flexibility was resolved by the
   implementation round, and this document treats 69 as fixed (section
   12).
2. **DECISION, made during the Experiment 5A implementation, not
   explicit in the original design document.** Stratum A ("Control")
   paragraphs — those where `pareto_frontier` has exactly one point
   (`K_min` itself) — produce no evaluation items at all, because no
   `K > K_min` frontier point exists to compare against. They are
   reported as a count (1,799 paragraphs) only. The original design
   document's stratum table did not specify a selection procedure for
   stratum A, leaving this to the implementation round. Experiment 5B
   inherits this decision unchanged: there is nothing to evaluate for
   these paragraphs.
3. **DECISION, unchanged.** Production segmentation
   (`subtitle_segmenter.py`) is not a condition anywhere in Experiment
   5A or 5B. The original design document (section 24) explicitly
   deferred adding it as a possible future third condition; this
   document does not revisit that deferral and treats it as still out
   of scope.
4. **INFERENCE — a genuine tightening, flagged rather than silently
   applied.** The original design document's Decision Gates (section 26)
   included "Gate E — evidence insufficient -> a larger or
   better-controlled repeat of Experiment 5" as a legitimate next step.
   This task's instructions (sections 10, 30, 31 of the task prompt) are
   materially stricter: they define a bounded three-state outcome
   (SUPPORT / NULL / CONTRADICTION, section 23 below) and an explicit
   Stop Condition (section 24 below) that forbids creating a further
   experiment merely because a subgroup looks interesting or evidence
   feels open-endedly "insufficient." This document adopts the stricter,
   current framework as authoritative for Experiment 5B. This is a
   deliberate narrowing relative to the original design document, made
   explicit here rather than silently substituted.
5. **DECISION, resolving an item the Experiment 5A round left open.**
   Repeat items for test-retest consistency were explicitly left as "a
   documented TODO for Experiment 5B" by the Experiment 5A implementation
   report (confirmed by inspection: every item in
   `evaluation_items_blinded.json` currently has
   `is_repeat_item: false` and `repeat_of_item_id: null`). This document
   makes that decision now: yes, include repeats, diagnostic use only,
   no automatic evaluator exclusion (section 11).
6. **FACT, reconsidered per this task's explicit instruction rather than
   carried over unexamined.** The original design document's proposed
   rating protocol (its section 14) already specified a 5-point
   comparative "overall preference" scale, independent binary "awkward
   split" flags, and an independent 1-5 "reading burden" rating, without
   formally designating exactly one of them as *the* primary outcome.
   Section 13 of this document re-derives the rating method from first
   principles (per this task's section 15 instruction) and confirms
   substantially the same structure, while formally designating "overall
   preference" as the single primary outcome and the other two as
   secondary — a sharper designation than the original document made.
7. **OPEN QUESTION, carried forward unresolved.** The original design
   document's own open questions (its section 27) about final sample
   size and overlapping-stratum policy were resolved by Experiment 5A's
   implementation. Two were not: whether production segmentation should
   ever become a third reference condition, and whether a
   timing/SRT-inclusive follow-on experiment is warranted. Both remain
   explicitly out of scope for Experiment 5B (section 25) and, per the
   Stop Condition (section 24), would require their own separate
   architecture-level justification if ever revisited — they are not
   automatically part of a "5C."

## 4. Frozen Inputs

All items below were inspected directly in this workspace for this
document (schemas quoted are read from the actual files, not
reconstructed from memory or from the design document's prose).

| Artifact | Status in this workspace | Role for Experiment 5B |
|---|---|---|
| `docs/phase2d/PHASE_2D_EXPERIMENT_5_HUMAN_READABILITY_DESIGN.md` | present, read in full | conceptual source; see discrepancy log (section 3) |
| `docs/phase2d/PHASE_2D_EXPERIMENT_4_PARETO_REPORT.md` | present, read in full | source of Experiment 4's findings restated in section 2 |
| `data/phase2d/experiment5/sample_manifest.json` | present, 69 records, schema confirmed (section 18) | the hidden mapping — authoritative source of `K_min`/alternative identity, never shown to evaluators |
| `data/phase2d/experiment5/evaluation_items.json` | present, 69 records, schema confirmed | full, non-blinded item records (internal/analysis use) |
| `data/phase2d/experiment5/evaluation_items_blinded.json` | present, 69 records, schema confirmed | the evaluator-facing data source |
| `data/phase2d/experiment5/evaluation.html` | present, rendered static preview confirmed (section 5) | reference rendering; Experiment 5B's future evaluator-facing interface must preserve its blinding properties, whether it reuses this file directly or builds a new renderer from the same blinded JSON |
| `data/phase2d/experiment5/sampling_summary.txt` | present | source of the stratum/exclusion counts cited throughout this document |
| `data/phase2d/experiment5/checksums.json` | present | source corpus/results-JSON checksums; reused for Experiment 5B's own reproducibility record (section 21) |
| `scripts/phase2d_experiment5_prepare.py` | present | defines the exact stratum/selection semantics this document relies on; not modified, not rerun |
| `tests/test_phase2d_experiment5_prepare.py` | present | out of scope for this design; not modified |

**FACT.** Per the local Windows repository handover, the equivalent
Experiment 4 raw JSON (`phase2d_pareto_results.json`,
SHA-256 `07f6fd6e7bd36133d9ff33c8349210d121e8d4bab8a108c4223a124266cb8cd7`)
and `scripts/evaluate_phase2d_real_content.py` / its shadow-evaluation
outputs exist in the local repository but not in this workspace under
those exact filenames. This document does not need their content
directly — the Experiment 4 findings it relies on are already
summarized, checksummed, and cited in
`docs/phase2d/PHASE_2D_EXPERIMENT_4_PARETO_REPORT.md` and in
`sample_manifest.json`'s per-item fields — and this limitation is stated
here rather than worked around.

## 5. Evaluation Unit

**FACT, confirmed by direct inspection of `evaluation_items_blinded.json`
and `evaluation.html`.** One evaluation item is one paragraph rendered as
two segmentations. Concretely, per item:

- The original source paragraph **is shown** (`source_text` field;
  rendered as a `<div class='source'>` block above both segmentations in
  `evaluation.html`).
- **Both** segmentation options are shown (`segmentation_1`,
  `segmentation_2` — ordered lists of raw text spans).
- Each segment **is visually separated** (one bordered `<div class='seg'>`
  box per segment, confirmed in the rendered HTML).
- Segments **are not explicitly numbered** — reading order (top to
  bottom within each segmentation block) is the only ordering cue. This
  document decides (**DECISION**) that this is sufficient: subtitle
  reading order is inherently sequential and unambiguous without an
  added index, and adding numbering risks implying a false significance
  to segment count that the blinding design otherwise carefully avoids
  (section 9). This document does not propose modifying
  `evaluation.html`.
- Each segment box **is** the subtitle "line break" unit — there is no
  additional line-break marking inside a segment.
- Punctuation **is preserved exactly** as in the source text (raw
  `source_text[start:end]` slices, per `boundary_segmentation.py`'s own
  raw-slice convention, carried through unmodified by
  `phase2d_experiment5_prepare.py`).
- Whitespace **is not normalized** — leading/trailing spaces from the
  raw slice remain exactly as extracted (e.g. item `exp5-0001`'s
  `Segmentation 2` includes a segment `" Embedded"` with a leading
  space, confirmed by direct inspection).
- **No audio is provided.** Experiment 5B is text-only, matching the
  original design document's explicit exclusion of TTS/timing/audio
  from the primary protocol (its section 24, restated as an out-of-scope
  item in section 25 below).
- **No visual timing is shown.**
- The evaluation is **purely text-based.**

This document does not propose adding any field to the evaluation unit
that is not already present in the frozen `evaluation_items_blinded.json`
schema (`item_id`, `source_file`, `paragraph_index`,
`paragraph_start_offset`, `paragraph_end_offset`, `source_text`,
`segmentation_1`, `segmentation_2`, `is_repeat_item`,
`repeat_of_item_id`) — Experiment 5B's rating-collection layer consumes
this schema as-is.

## 6. Human Readability Definition

**DECISION.** "Subtitle segmentation readability" is defined
operationally, for this experiment, as: *how easily and naturally a
reader can process the text given how it has been divided into
sequential lines* — independent of whether the underlying content itself
is well-written, factually correct, or grammatically sound. The
operational definition draws on, but narrows, the fuller descriptive list
in this task's instructions:

Included in scope (things a reviewer should be judging):
- natural phrase/clause grouping vs. mid-phrase interruption,
- excessive fragmentation (too many very short lines for the content),
- overly long or dense lines relative to the others shown,
- awkward boundary placement (a cut that lands somewhere a natural pause
  would not fall),
- punctuation placement relative to the cut (e.g. a line ending
  mid-clause vs. at a natural punctuation boundary),
- semantic continuity within a single line (does one line hold together
  as a coherent unit),
- visual scanning effort (how easy the sequence of lines is to read
  through at a glance).

Explicitly **excluded** from readability judgment, and stated as such in
the reviewer instructions (section 8):
- factual correctness of the underlying content,
- semantic correctness of what the paragraph is claiming,
- grammar correctness of the source wording,
- technical correctness of any terminology used.

**INFERENCE.** Because both segmentations of a given item are built from
the *identical* source paragraph (only the cut positions differ — see
section 5), any perceived difference in factual/semantic/grammatical
quality between "Segmentation 1" and "Segmentation 2" is definitionally
impossible; the *only* thing that can differ between them is
segmentation. The reviewer instructions therefore do not need to work
hard to redirect attention away from content quality — the comparison
structure itself already isolates segmentation as the only variable.

**DECISION.** Consistent with the original design document's own
"smallest useful set" principle, this broader operational definition
informs what reviewers are told to *consider*, but the *rated dimensions*
themselves remain minimal (section 13) — asking reviewers to score every
sub-dimension listed above independently would increase burden without a
clear expectation of additional signal beyond a well-designed overall
judgment plus one concrete, low-ambiguity secondary flag.

## 7. Rating Method

**DECISION, re-derived from first principles per this task's instruction,
not adopted merely because it is the original design document's
proposal.**

Three candidate methods were evaluated:

- **(A) Pure pairwise forced choice** ("which is easier to read — no
  ties allowed"). Rejected as the sole method: forcing a choice on
  genuinely equivalent pairs would fabricate a signal that does not
  exist, which is a direct risk given Experiment 4's own evidence that a
  majority of the sampled paragraphs have only a small score gain — many
  items are plausibly close to indistinguishable in practice, and a
  method that cannot record "no meaningful difference" would corrupt the
  primary outcome with noise disguised as signal.
- **(B) Independent quality ratings** (rate each segmentation on its own
  scale, without a direct comparison). Rejected as the sole method: it
  does not directly answer the comparative research question (section
  2), and independent Likert ratings are well known to suffer from
  inconsistent anchoring across reviewers (one reviewer's "4" is
  another's "3"), which would weaken exactly the corpus-level preference
  signal Experiment 5B needs. It is, however, useful as a *secondary*
  signal (see below) for a case (A) and pairwise methods structurally
  cannot resolve on their own: two segmentations that are both good, or
  both poor, and therefore rated as "about the same" by a pairwise
  method without indicating which.
- **(C) Combined design: pairwise comparative rating with an explicit
  equivalence point, plus a small independent secondary layer.**
  Selected.

**Selected primary rating instrument — 5-point comparative scale:**

```
-2  Segmentation 1 clearly easier to read
-1  Segmentation 1 somewhat easier to read
 0  About the same / no meaningful difference
+1  Segmentation 2 somewhat easier to read
+2  Segmentation 2 clearly easier to read
```

The sign is with respect to the *displayed* position ("Segmentation 1" /
"Segmentation 2"), never `K_min`/alternative directly — the mapping back
to `K_min`/alternative identity happens only during analysis, via
`sample_manifest.json`'s `segmentation_1_is` / `segmentation_2_is`
fields (already present, confirmed in section 4).

**Secondary rating instruments** (collected on the same item, after the
comparative judgment, to avoid anchoring the comparative judgment on an
absolute scale first):

- **Awkward-split flag**, independent per displayed version (not
  comparative): "Does this version cut in the middle of a word, name,
  number, or short phrase that reads awkwardly when interrupted there?"
  — yes/no per version. This directly operationalizes one concrete
  mechanism Phase 2D's own documentation already predicts
  (`boundary_segmentation.py`'s module docstring: no CJK/jieba
  word-boundary awareness), giving Experiment 5B a mechanism-specific
  signal distinct from the holistic comparative judgment.
- **Independent reading-effort rating**, 1-5, per version (not
  comparative): "How easy is this version to read as a subtitle, on its
  own?" This resolves the "both good" / "both poor" ambiguity a
  comparative-only design cannot: two items can both register "0, about
  the same" on the comparative scale while one pair is rated 4-and-4
  (both good) and another is rated 2-and-2 (both poor) on this
  independent scale.

**Ties/equivalence:** explicitly representable (`0` on the comparative
scale) and never discarded — a `0` rating is a legitimate, informative
data point (see section 13, primary outcome definition), not a
non-response.

**Forced choice:** not used. A reviewer is never required to declare a
preference where none exists; doing so would be scientifically
dishonest given this experiment's explicit purpose (section 2) of
testing whether a preference exists at all.

## 8. Reviewer Instructions

**DECISION.** Draft instructions (final wording to be confirmed at
implementation time, but the structure and constraints below are fixed
by this design):

> You will see a short piece of text, followed by two different ways of
> breaking that same text into subtitle-style lines, labeled
> "Segmentation 1" and "Segmentation 2." Please judge only how each
> version reads as a sequence of subtitle lines — not whether the
> content itself is well-written, factually accurate, or uses the right
> terminology (both versions come from the exact same original text, so
> that cannot differ between them).
>
> Consider: does each line read naturally, does it end in a sensible
> place, and is the text broken up in a way that's easy to follow at a
> glance? Please don't try to guess which version is "correct" or which
> system produced which — there is no fixed correct answer, and the two
> versions are not labeled as new/old or better/worse in any way.
>
> If the two versions read about equally well to you, please say so —
> "about the same" is a valid and useful answer. Comments are optional.
> Each item should take well under a minute to judge.

Explicit constraints on the instructions (mandatory, not stylistic
preferences):

- Punctuation is part of the text as originally written and should be
  read as-is, not treated as an error.
- Technical terminology (English terms embedded in Chinese text, product
  names, numbers) should be read as ordinary content, not flagged as a
  readability problem in itself — only *where a line breaks relative to*
  such a term is in scope (covered by the awkward-split flag, section 7).
- Comments are explicitly optional.
- Expected time per item is stated (sets expectations, discourages
  either rushing or over-deliberating).
- The instructions **never** use the words: Phase 2C, Phase 2D, K,
  K_min, score, Pareto, boundary score, experimental, production,
  baseline, current, new, improved — mirroring, and extending to
  free-text instructional copy, the forbidden-token list Experiment 5A
  already enforces mechanically on the data artifacts (section 9).

## 9. Blinding Design

**FACT, reused unchanged from Experiment 5A.** The evaluator-facing
artifact (`evaluation_items_blinded.json` / `evaluation.html`) already
excludes every one of: `k_min`, `alternative_k`, `phase2d_score_*`,
`delta_phase2d_score`, `pareto_frontier`, `stratum`,
`boundary_condition_candidate`, `primary_sample`, and any condition-name
field — confirmed by Experiment 5A's own automated forbidden-token scan,
which this document does not need to repeat since the underlying file is
frozen and unchanged.

**DECISION, extending the same principle to Experiment 5B's own new
material.** The forbidden-token list from Experiment 5A
(`k_min`, `alternative_k`, `phase2d_score`, `score`, `delta_score`,
`pareto`, `frontier`, `stratum`, `condition_identity`, `production`,
`experimental`, `baseline`) applies identically to every new
evaluator-facing artifact Experiment 5B produces (reviewer instructions
text, any rating-collection UI, any confirmation/thank-you messaging).
The future implementation round must re-run an equivalent automated scan
against its own new evaluator-facing text, not just trust that reusing
the existing blinded JSON is sufficient — new instructional copy is a new
surface where a leak could be introduced.

**DECISION.** Item IDs (`exp5-0001` etc.) **may** remain visible to
evaluators (they already are, in `evaluation.html`) — an opaque sequence
number carries no information about `K`, score, or stratum, and is
necessary for evaluators to reference a specific item in an optional
comment.

## 10. Randomization Design

**FACT.** The original 69 items' `Segmentation 1` / `Segmentation 2`
assignment is already fixed and frozen by Experiment 5A
(`display_order` in `evaluation_items.json`, derived deterministically
from `seed + 1` where `seed = 42`, per `phase2d_experiment5_prepare.py`).
**DECISION:** Experiment 5B must not re-randomize or otherwise alter this
existing assignment for the 69 original items — doing so would mean two
different "runs" of the same item could show `K_min` on different sides
without a recorded reason, breaking reproducibility (section 21).

**DECISION — a new, distinct randomization domain for Experiment 5B's
own layer**, separate from Experiment 5A's sampling seed (`42`) and
display-order seed (`43`), both of which are already fully consumed and
must not be reused for a different purpose:

- A **collection seed** (a new integer, to be fixed and published by the
  implementation round, not invented in this design) governs: (a) which
  subset of the 69 items each evaluator is assigned, if not every
  evaluator rates all items, and (b) the selection and re-randomization
  described for repeat items (section 11).
- Evaluator IDs are opaque, locally-assigned tokens (section 21).
- The **hidden mapping** for the original 69 items remains exactly
  `sample_manifest.json`, unchanged and unmodified: `item_id ->
  segmentation_1_is / segmentation_2_is -> k_min / alternative_k /
  phase2d_score_* / stratum / ...`. No new hidden-mapping file is needed
  for the base 69 items.
- For **repeat items** (section 11), a new, small "session assignment
  manifest" (not created in this document — a specified future artifact,
  section 25) records, per repeat exposure: a distinct
  `response_event_id`, the `item_id` it repeats, the evaluator it was
  shown to, and its own independently randomized `displayed_order` — so
  that `displayed A/B -> original segmentation identity` remains
  reconstructible without ambiguity for every single exposure, original
  or repeat, via `sample_manifest.json` (item identity) plus the session
  assignment manifest (which side was shown, to whom, when).

## 11. Repeat / Consistency Design

**DECISION.** Experiment 5B includes repeat items, for diagnostic
purposes only:

- **Selection:** repeats are drawn only from the 66 **primary-sample**
  items (not the 3 boundary-condition items, to avoid conflating two
  different sources of noise in one diagnostic signal).
- **Percentage/count:** approximately 10% of each evaluator's assigned
  item set, rounded to a whole number, with a floor of 2 and a cap of 5
  repeats per evaluator regardless of how many items they are assigned —
  matching the original design document's proposed range (3-5) while
  scaling sensibly for an evaluator assigned a small subset.
- **Content:** identical to the original — the exact same
  `source_text`, `segmentation_1` content, and `segmentation_2` content
  as the item being repeated (no re-derivation, no new sampling from
  Experiment 4/5A).
- **Display order:** independently re-randomized for the repeat exposure
  (a fresh draw from the collection-seed-derived randomization, section
  10) — a repeat is a new exposure event, not a replay of the exact same
  screen state, so a naive "remembered the layout, not the content" bias
  is not conflated with "gave a different content judgment."
- **What counts as inconsistency:** the repeat's comparative-preference
  rating (section 7) differs from the original rating by **2 or more
  scale points** (e.g. original `+2`, repeat `0` or worse) after
  orienting both to the same displayed reference frame. A one-point
  difference (e.g. `+2` vs `+1`) is not flagged — ordinary rating noise
  at adjacent scale points is expected and not treated as inconsistency.
- **Reporting:** a per-evaluator consistency rate (fraction of that
  evaluator's repeats not flagged inconsistent) is reported as a
  secondary/diagnostic statistic (section 14), and a corpus-level
  distribution of consistency rates is reported alongside the primary
  outcome, never merged into it.
- **Exclusion:** **no automatic evaluator exclusion rule.** Per this
  task's explicit instruction, diagnostic use is preferred. If a
  future implementation round observes a small number of evaluators with
  persistently poor consistency (e.g. more than half of their repeats
  flagged), that is reported as a named, auditable qualitative note for
  human review — not an automated deletion rule applied silently during
  analysis.

## 12. Sample Size and Reviewer Allocation

**DECISION.** All 69 existing items are evaluated — no new corpus is
created, per this task's explicit instruction and consistent with
"do not create a new corpus unless absolutely necessary" (nothing here
necessitates one).

**DECISION — analysis population split**, consistent with Experiment 5A's
own `primary_sample` flag:
- **Primary analysis population:** the 66 items with
  `primary_sample: true`. The single primary outcome (section 13) is
  computed over this population only.
- **Boundary-condition items (3):** evaluated using the identical
  interface and instructions (so evaluators are not aware anything is
  different about them), but their ratings are reported and discussed
  **separately**, as qualitative/diagnostic evidence about degenerate
  extreme-narrow-segment cases (section 14) — never pooled into the
  primary statistic. This mirrors Experiment 5A's own framing of these
  items as illustrative boundary conditions, not primary evidence.

**DECISION — reviewers per item.** A floor of **at least 3 independent
evaluators per primary-sample item** is required, matching the original
design document's own floor and for the same reason: it is the minimum
that supports a meaningful item-level median and an agreement statistic
(section 17) rather than trusting a single opinion. This is a floor, not
a target; a larger panel improves precision but is not required to
proceed.

**INFERENCE / explicit statistical honesty statement.** A formal
statistical power analysis is **not appropriate** for this experiment and
is not attempted: the 69-item sample is a stratified convenience sample
from one 39-file, single-domain corpus (not a random sample from a
defined population of "all possible subtitle paragraphs"), and the
reviewer panel size is not fixed by this design (it depends on
implementation-time recruitment). Any effect-size or confidence-interval
figures the future analysis reports (section 16) should therefore be
read as descriptive/exploratory characterizations of *this specific
sample*, not as generalizable, power-justified estimates of a population
parameter.

## 13. Primary Outcome

**DECISION — exactly one primary outcome, as required.**

Three candidate formulations were considered:

- *(a) Win-rate excluding ties*: proportion of non-tied comparisons where
  the alternative is preferred. Rejected as the sole primary metric: it
  discards every "about the same" rating, which for this corpus (a
  majority of sampled paragraphs have small algorithmic score gains, per
  Experiment 4) is expected to be a large and informative fraction of the
  data — discarding it would materially bias the answer to "does the
  alternative improve readability" toward whichever side happens to win
  among the *minority* of items with a clear preference.
- *(b) Mean of the -2..+2 comparative scale*, oriented toward the
  alternative. Rejected as the primary aggregation statistic (though
  reported as a descriptive companion figure): treating a 5-point ordinal
  scale's numeric labels as an interval scale for a mean is a common
  simplification but is not the most defensible choice for a
  statistically honest design (task section 35).
- *(c) Median oriented comparative-preference score, with win/tie/loss
  proportions reported alongside it.* **Selected.**

**Primary outcome, defined precisely:**

1. For each primary-sample item, orient every valid comparative rating
   (section 7) so that positive values always mean "alternative
   preferred," using `sample_manifest.json`'s
   `segmentation_1_is`/`segmentation_2_is` fields (flip sign if
   `segmentation_1_is == "alternative"`).
2. Compute the **item-level median** oriented rating across that item's
   `>=3` ratings (ties in the median broken toward 0, i.e. toward "no
   preference," the conservative direction).
3. The **primary outcome** is the **corpus-level median of the 66
   item-level medians**, reported together with the induced
   **win/tie/loss proportions** (fraction of items whose item-level
   median is `>0`, `=0`, `<0` respectively) as an inseparable companion
   breakdown — always reported together, never one without the other.

This directly answers the research question (section 2): a corpus-level
median reliably greater than 0, with a win proportion clearly exceeding
the tie/loss proportions, is evidence of a readability preference for the
higher-`K` alternative; a median at or near 0 with a large tie proportion
is evidence of no meaningful preference; a corpus-level median reliably
less than 0 is evidence the alternative is *less* preferred despite its
higher algorithmic score.

Ties (`0` ratings, and items whose item-level median lands on `0`) are
never discarded, excluded, or treated as missing.

## 14. Secondary Outcomes

Classified explicitly, per this task's requirement:

**SECONDARY** (predefined, always computed and reported alongside the
primary outcome, but not the basis for the Decision Gate on their own):
- tie rate (already part of the primary outcome's companion breakdown,
  restated here for completeness),
- awkward-split flag rate, per displayed version and oriented to
  `K_min`/alternative,
- independent reading-effort rating, per version, oriented,
- effect by `ΔK` bucket (`E_delta_k_1/2/3/4plus` — reusing Experiment
  5A's own stratum labels, section 20 of `sample_manifest.json`'s
  `stratum` field),
- effect by frontier size (`F_frontier_size_*`),
- effect by material boundary-placement change
  (`H_material_boundary_change` present/absent),
- effect by non-monotonic paragraph status (`G_non_monotonic`),
- effect by source file (corpus-level grouping, e.g. mcu1 vs. mcu2),
- boundary-condition item behavior (the 3 excluded items, reported
  qualitatively — ratings, flags, and any comments, discussed
  individually given the population is too small for any aggregate
  statistic to be meaningful),
- reviewer agreement (section 17),
- repeat-item consistency (section 11).

**EXPLORATORY** (reported if the data supports it, explicitly not used
to drive the Decision Gate, and not protected against multiple-testing
inflation — see section 16):
- interactions between strata (e.g. does the `ΔK` effect differ for
  `H_material_boundary_change` items specifically),
- qualitative review of free-text comments,
- per-evaluator individual variation beyond the repeat-consistency
  statistic (e.g. does one evaluator systematically rate more positively
  than others),
- any observed relationship between `alternative_k_substituted` (cases
  where Experiment 5A's `ΔK`-targeting fell back to a substituted
  frontier point) and rating pattern,
- paragraph length (`paragraph_end_offset - paragraph_start_offset`) as
  a continuous moderator.

**Explicit note on overlapping strata (mandatory per this task's
instructions).** Every item's `stratum` field in `sample_manifest.json`
is a list, and 69/69 items already carry more than one label (confirmed,
`sampling_summary.txt`). A "by-`ΔK`" breakdown and a "by-frontier-size"
breakdown therefore draw from **overlapping**, not independent, subsets
of the same 66-item population — an item counted in the
`E_delta_k_1` breakdown may also be counted in the `H_material_boundary_
change` breakdown. **DECISION:** every subgroup breakdown is reported
and interpreted independently, on its own subset, and no subgroup
breakdown's sample size is ever summed across strata as if it represented
additional independent evidence. This is stated explicitly here to
prevent a future analysis from silently treating overlapping-stratum
counts as if they added up to more than 66/69 independent observations.

## 15. Exploratory Analysis

(Combines with section 14's EXPLORATORY list above; this section states
the ground rules for how exploratory findings may be used.)

**DECISION.** Exploratory findings may be reported, described, and used
to motivate an **explicit, separately justified** future investigation
(per the Stop Condition, section 24) — but they may never, on their own,
be used to: (a) alter the primary outcome's computation after the fact,
(b) justify skipping the Decision Gate, or (c) be presented with the same
evidentiary weight as the primary outcome in the final Experiment 5B
report. Any exploratory finding presented in that report must be
explicitly labeled exploratory in the report text itself, not just in
this design document.

## 16. Statistical Analysis

**DECISION — descriptive statistics (always reported):** item-level and
corpus-level medians (section 13), win/tie/loss proportions, awkward-split
and reading-effort rating distributions, per-stratum breakdowns (section
14), interquartile range of the oriented comparative rating.

**DECISION — inferential statistic for the primary outcome only:** a
**sign test** against the null hypothesis "no systematic preference"
(median oriented rating = 0), applied once, at the corpus level, to the
66 item-level medians. A sign test is selected because: it requires the
minimum assumptions appropriate for ordinal preference data (no
interval-scale assumption, unlike a t-test or a raw mean-based test), it
handles ties naturally (a well-established convention: `0`s are either
excluded from the sign test's own count or treated as ties per the
standard sign-test tie-handling convention — this document specifies
excluding exact `0` item-level medians from the sign test's win/loss
count, while still reporting them in the win/tie/loss breakdown), and it
is simple enough to be auditable by a non-statistician reviewer of a
future analysis report (task section 35's "prefer the simplest method").
A Wilcoxon signed-rank test is noted as an **optional, exploratory**
supplementary check if the magnitude information in the -2..+2 scale is
judged useful — but it is not the primary inferential method, given the
caveat about treating ordinal labels as ranks being a stronger assumption
than the sign test requires.

**DECISION — no per-subgroup inferential test.** Given 66 primary items
distributed across multiple overlapping strata (section 14), most
individual strata (e.g. `E_delta_k_2` with 7 items, `G_non_monotonic`
with 6 items) are far too small for an inferential test to be meaningful,
and running one test per stratum would invite exactly the kind of
multiple-comparisons inflation this task's instructions warn against.
**Every subgroup breakdown in section 14 is descriptive only** — reported
as counts, proportions, and medians, never accompanied by a p-value or a
significance claim.

**DECISION — mixed-effects modeling.** A mixed-effects logistic/ordinal
model (accounting for reviewer and item random effects simultaneously)
is **not used for the primary analysis**: with a reviewer panel size not
yet fixed by this design (section 12) and only 66 primary items, such a
model is likely to be under-identified or to produce falsely precise
estimates. It is listed as an **optional exploratory technique**, usable
only if the eventual implementation reaches a reviewer panel and
per-item rating count sufficient to support it (a rough, non-binding
heuristic: at least 5 ratings per item and at least 8 distinct
evaluators) — and even then, its output is exploratory, never a
replacement for the sign test as the primary inferential result.

**No causal claim.** Every statistical result in this section describes
association/preference in the sampled and rated data, never a causal
claim about what "causes" readability differences.

## 17. Inter-Rater Agreement

**DECISION.** Given that (a) the comparative rating is ordinal, (b) the
number of raters per item is not guaranteed to be uniform across items
(some items may receive exactly 3 ratings, others more, depending on
evaluator assignment), and (c) not every evaluator is guaranteed to rate
every item, **Krippendorff's alpha** (ordinal-weighted) is selected as
the primary chance-corrected agreement statistic — it is the one
standard agreement measure designed to handle a variable number of
raters per unit and missing data without requiring a fully crossed design.

A simple **pairwise percent agreement** (do any two raters on the same
item land on the same side of 0, ignoring magnitude) is reported as a
companion, easily-auditable descriptive figure alongside the alpha value
— not as a replacement for it, since raw percent agreement does not
correct for chance.

**Explicitly not used:** Cohen's kappa (requires exactly 2 raters, not
guaranteed here) and Fleiss' kappa (requires every item to be rated by
the same fixed number of raters, which this design's flexible assignment
does not guarantee). **OPEN QUESTION for the implementation round:** if
the eventual reviewer-assignment scheme happens to produce a fixed,
uniform number of raters per item, Fleiss' kappa becomes an available
option too and may be reported as an additional descriptive figure — this
is not precluded, just not assumed.

## 18. Data Model

Four layers, matching this task's required structure and Experiment 5A's
existing precedent:

**Evaluator-facing data** (reused unchanged from Experiment 5A; no new
file created by this document): `evaluation_items_blinded.json` /
`evaluation.html`, containing no hidden metadata (verified by Experiment
5A's own forbidden-token scan). Experiment 5B's implementation may build
a new rendering surface from the same blinded JSON if a different
interface is desired, subject to the blinding requirements in section 9.

**Raw response data** (new; specified here, not created by this
document). One record per rating event (an "event" is one evaluator
judging one displayed item instance — the original or a repeat):

```json
{
  "response_event_id": "exp5b-resp-000001",
  "item_id": "exp5-0001",
  "is_repeat": false,
  "repeat_of_response_event_id": null,
  "evaluator_id": "evaluator_01",
  "displayed_order": "as recorded in evaluation_items_blinded.json for originals; independently drawn for repeats (section 10)",
  "comparative_rating": -1,
  "awkward_split_segmentation_1": false,
  "awkward_split_segmentation_2": true,
  "reading_effort_segmentation_1": 4,
  "reading_effort_segmentation_2": 2,
  "optional_comment": null,
  "timestamp": "informational only - never used in any deterministic computation, see section 21"
}
```

**Hidden analysis mapping:** `sample_manifest.json` (existing, frozen,
unmodified) for the base 69 items, plus a new, small **session
assignment manifest** (specified, not created) recording, for repeat
exposures only, the link `response_event_id -> item_id ->
repeat_of_response_event_id` plus the repeat's own
`displayed_order` — everything needed to reconstruct `displayed A/B ->
original segmentation identity` for every event, original or repeat,
without ambiguity, per this task's explicit requirement.

**Derived analysis data** (new; specified, not created): validated,
schema-checked, hidden-mapping-joined response records; item-level
medians; corpus-level primary outcome; secondary/exploratory breakdowns;
agreement statistics; repeat-consistency statistics. All computed fresh
from raw response data plus the hidden mapping — **raw response data is
never mutated, only read**, matching this task's explicit "no raw
response mutation" requirement (restated as an invariant in section 20).

**Files that may safely be exposed to evaluators:** only the existing
blinded artifact (`evaluation_items_blinded.json` / `evaluation.html`)
and the reviewer instructions text (section 8). **Never exposed:**
`sample_manifest.json`, the session assignment manifest, or any derived
analysis data — all three contain `K_min`/alternative identity, scores,
or stratum information.

## 19. Data-Quality Rules

Every rule below is explicit and auditable; none silently discards or
repairs data.

| Condition | Handling |
|---|---|
| Missing response (evaluator skipped an assigned item) | Excluded from that item's rating count only; reported as a non-response count per item and per evaluator; never imputed. |
| Duplicate response (same evaluator rates the same *non-repeat* item twice, not an intentional repeat) | First-received response kept for the primary computation; the duplicate is retained in raw data but flagged and reported as an anomaly (possible logging/UI issue) — never silently merged or averaged. |
| Invalid rating (out-of-range value, malformed field) | Rejected at ingestion with a specific, logged reason (item/evaluator/field); not coerced, clamped, or silently dropped. |
| Abandoned evaluation session | Every individually completed item-level rating already collected remains a valid data point; only the specific items the evaluator never reached are "missing" (see row 1) — nothing is retroactively deleted because a session ended early. |
| Inconsistent repeat response | Not excluded (section 11); flagged and reported as a diagnostic statistic. |
| Malformed `item_id` (not present in `sample_manifest.json`) | Hard integrity failure at ingestion — halts processing of that response batch and reports the exact offending `item_id`, mirroring `phase2d_experiment5_prepare.py`'s own `IntegrityError` convention. |
| Missing hidden mapping (an `item_id` in raw responses has no `sample_manifest.json` entry) | Hard integrity failure, halts analysis, reports the exact `item_id` — never silently skipped. |
| Accidental exposure of blinded metadata (any evaluator-facing artifact or raw-response free-text field contains a forbidden token, e.g. a comment that somehow includes "K_min") | Hard integrity failure for the artifact-level scan (section 9); for a *comment field* containing such a string verbatim from a reviewer (unlikely but possible, e.g. a reviewer guesses and writes it in a comment), the comment is retained as raw data (reviewers' own words are not blinding-scanned or redacted) but flagged for manual review, since it may indicate the reviewer somehow inferred internal information. |
| Unexpected duplicate item (two different `item_id`s reference the identical `(source_file, paragraph_index, alternative_k)` triple) | Should not occur given Experiment 5A's own deduplication; if detected, flagged as a hard integrity failure requiring investigation before analysis proceeds — never silently merged. |

## 20. Analysis Pipeline

Future implementation sequence (specified, not built):

1. Load raw response data.
2. Validate response schema (every field present and well-typed).
3. Validate every `item_id` against `sample_manifest.json`'s known set.
4. Load the hidden manifest (`sample_manifest.json` + the session
   assignment manifest for repeats).
5. Reconstruct `displayed A/B -> original segmentation identity` for
   every response event.
6. Validate mapping completeness (every response event resolves to
   exactly one `K_min`/alternative identity).
7. Validate response integrity per the data-quality rules (section 19).
8. Apply the data-quality rules, producing a cleaned, oriented dataset —
   **the raw file itself is never modified; a separate cleaned/derived
   copy is produced.**
9. Compute the primary outcome (section 13).
10. Compute secondary outcomes (section 14).
11. Compute reviewer agreement (section 17) and repeat-item consistency
    (section 11).
12. Perform the predefined exploratory subgroup analyses (sections 14-15),
    explicitly labeled as such in all outputs.
13. Generate the analysis report (structure informed by, but not
    identical to, this design document — the report presents results,
    this document specifies method).
14. Confirm raw response data is byte-identical to its state before
    analysis (an explicit post-hoc integrity check, mirroring every prior
    Phase 2D round's checksum-based verification habit).

## 21. Privacy / Evaluator Identity

**DECISION, consistent with the original design document.** Evaluator
identity is limited to an opaque, locally-assigned token (e.g.
`evaluator_01`). No name, email, or other direct personal identifier is
collected anywhere in the raw response schema (section 18). The single
qualification criterion (native or native-level Chinese reader, per the
original design document's evaluator-requirements reasoning, unchanged
here) is recorded once per evaluator in a separate roster, not repeated
per response. Timestamps, if recorded at all, are informational only —
used at most for session-order reconstruction during data-quality review
(section 19), never as an input to any deterministic ID, selection, or
statistical computation. All processing remains local; no evaluator data
or corpus text is sent to a cloud service or external API (restating and
extending Experiment 5A's own privacy stance).

## 22. Result Interpretation

Defined **before** implementation, per this task's requirement.

- **Positive:** the primary outcome's corpus-level median is reliably
  greater than 0 (supported by the sign test, section 16) with a win
  proportion clearly exceeding the loss proportion → interpreted as
  credible evidence that, for this sample, the higher-`K` alternative is
  perceived as more readable.
- **Null:** the corpus-level median is at or near 0, and/or the sign test
  does not indicate a reliable departure from 0, and/or the tie
  proportion dominates → interpreted as no meaningful readability
  preference detected in this sample.
- **Negative:** the corpus-level median is reliably less than 0 → higher-`K`
  alternatives are, on the whole, perceived as *less* readable despite
  their higher algorithmic score.
- **Local improvement, global decline (or the reverse):** if a specific
  secondary breakdown (e.g. `D_large_gain` or `H_material_boundary_change`)
  shows a positive-leaning pattern while the overall corpus-level result
  is null or negative (or vice versa) → interpreted as evidence that any
  relationship between score/`K` and readability, if real, is
  condition-dependent, not global — reported explicitly as such, and
  treated as descriptive characterization, not as grounds for a separate
  conclusion outside the primary outcome's own state (section 23).
- **Strong reviewer disagreement** (e.g. Krippendorff's alpha low, or a
  cluster of items with near-even split between `+2` and `-2` ratings
  across reviewers) → interpreted as evidence that readability preference
  for those items is itself contested/ambiguous among readers, not as a
  data-quality failure to be fixed by exclusion (section 11).
- **Different results by `ΔK`:** reported descriptively (section 14); if
  small `ΔK` (e.g. `E_delta_k_1`) shows a different pattern than large
  `ΔK`, this is evidence relevant to a *future* K-selection policy
  question (how far from `K_min` a change should be allowed to go) but is
  not, by itself, translated into a specific numeric bound by this
  experiment.
- **Different results by paragraph length:** reported descriptively
  (exploratory, section 14/15); not causally interpreted.
- **Different results for boundary-condition items:** reported
  individually and qualitatively (section 12); if reviewers rate these
  items negatively for the alternative (plausible, given they contain an
  extreme-narrow segment by construction), that is treated as
  corroborating, not surprising, evidence — consistent with, not
  contradicting, whatever the primary-sample result shows.

**Binding constraint, repeated from the task instructions:** none of the
above interpretations is, by itself, converted into a production
K-selection policy, a threshold, or a penalty value. That conversion is
explicitly reserved for the separate, subsequent K-selection Architecture
Decision (section 23).

## 23. Decision Gate

Experiment 5B's future implementation must terminate in exactly one of
three evidence states, matching this task's required framework:

**STATE A — SUPPORT.** The primary outcome is Positive (section 22), with
evidence credible enough (sign test result, reasonable agreement, no
overriding local/global contradiction) to support the conclusion that
additional segmentation can improve readability under defined conditions.
*Possible next step:* proceed to the K-selection Architecture Decision,
using Experiment 5B's evidence (including which conditions, per section
14's secondary breakdowns, showed the effect) as an input to a controlled
implementation design.

**STATE B — NULL.** The primary outcome is Null (section 22). *Possible
next step:* document the finding, proceed to the architecture decision
with this evidence, and retain or revise the current Fixed-K strategy
accordingly. **Do not automatically create another experiment** — a null
result is a complete, valid answer to Experiment 5B's research question,
not a reason to keep looking until a positive result appears.

**STATE C — CONTRADICTION.** The primary outcome is Negative (section
22): higher-`K` alternatives systematically read worse despite their
higher Phase 2C score. *Possible next step:* an Architecture Review of
the relationship between Phase 2C's scoring model and human readability
(a design-level review, not automatically another rating-collection
experiment) — since this state would mean the algorithmic objective
(maximize selected boundary score) and the human objective (readable
segmentation) are, at least in part, misaligned, which is itself the
single most important possible finding this experiment could produce.
**Do not automatically create Experiment 5C** to re-test this — the
review that follows is an architecture-level activity, per the Stop
Condition (section 24), not another data-collection round unless that
review itself identifies a specific, justified need for one.

## 24. Stop Conditions

**Experiment 5B is not a gateway to an automatically expanding research
program.** After Experiment 5B reaches one of the three states in section
23, no additional experiment (5C, 5D, or otherwise) may be created merely
because: a subgroup result looks interesting, an edge case exists, more
data would be nice to have, a different statistic could be tried, another
sampling method could be explored, or another score formulation could be
tested.

A new experiment may be justified **only** if all four of the following
hold, and the justification is written down explicitly at the time:

1. it identifies a concrete, specific, unresolved question;
2. it demonstrates that Experiment 5B's existing evidence genuinely
   cannot answer that question (not merely "could answer it more
   precisely with more data");
3. it demonstrates that answering the question could materially change
   the production K-selection decision (not merely add academic
   interest); and
4. it defines its own explicit exit condition before it begins, per the
   same discipline this document applies to Experiment 5B itself.

Absent all four, the project proceeds directly from Experiment 5B's
Decision Gate (section 23) to the K-selection Architecture Decision and,
from there, to Controlled Integration or a documented rejection/deferral
— **not** to a further experiment.

## 25. Implementation Scope for Experiment 5B

Explicitly **not built by this document** — specified here only so a
future, separately authorized implementation round has a concrete,
unambiguous target:

- A local, static, no-cloud rating-collection mechanism consuming
  `evaluation_items_blinded.json` (reusing `evaluation.html` directly, or
  building an equivalent local renderer from the same blinded JSON) and
  producing raw response records matching the schema in section 18.
  Candidate lightweight approaches (implementation detail, not decided
  here): a simple local form/spreadsheet workflow, or a minimal local
  script-driven collection tool — no cloud survey platform, no external
  LLM evaluator, no third-party hosting, per this document's privacy
  constraints (section 21) and consistent with the original design
  document's own baseline stance.
- `scripts/phase2d_experiment5b_collect.py` (or an equivalent) —
  candidate name, matching the existing flat `scripts/` naming
  convention (`phase2d_experiment5_prepare.py`).
- `scripts/phase2d_experiment5b_analyze.py` (or an equivalent) —
  implements the analysis pipeline (section 20).
- `data/phase2d_experiment5b/` (candidate path, matching the local
  Windows repository's now-established flat `data/phase2d_experimentN/`
  naming convention) — raw response data, the session assignment
  manifest, and derived analysis data.
- `reports/phase2d_experiment5b/` (candidate path) — the human-readable
  analysis report.

**Explicitly out of scope for Experiment 5B** (restated, mandatory):
production K-selection algorithm, score threshold, penalty value, any
new Phase 2C scoring rule, any semantic phrase model, production
integration architecture, TTS/audio, subtitle timing/SRT generation, and
production segmentation as a rated condition.

## 26. Acceptance Criteria

A future Experiment 5B implementation's results are considered usable
input to the Decision Gate (section 23) only if:

1. every primary-sample item received `>=3` valid ratings from
   independent evaluators;
2. the evaluator-facing artifact (whatever renders
   `evaluation_items_blinded.json`) passes a forbidden-token scan with
   zero hits, re-verified at Experiment 5B's own ingestion time, not
   merely inherited from Experiment 5A;
3. `displayed A/B -> original segmentation identity` is reconstructible
   without ambiguity for 100% of collected response events;
4. every data-quality rule in section 19 was applied and its outcome
   (counts of excluded/flagged responses, by category) is reported,
   auditable, and reconciles to the total number of response events
   collected;
5. the primary outcome (section 13) and its win/tie/loss companion
   breakdown are computed exactly as specified, with the sign test
   (section 16) reported alongside it;
6. inter-rater agreement (section 17) is computed and reported;
7. repeat-item consistency (section 11) is computed and reported,
   diagnostically, with no evaluator silently excluded;
8. the report explicitly states which of the three Decision Gate states
   (section 23) the result falls into, and does not proceed to propose a
   production K-selection policy directly.

## 27. Open Questions

Left for the implementation round or a human decision-maker, not decided
by this document:

- Exact reviewer panel size and recruitment mechanism (beyond the
  floor of `>=3` raters per item, section 12).
- Exact collection seed value (to be fixed and published at
  implementation time, section 10).
- Whether a lightweight local web UI or a simpler spreadsheet/manual
  workflow is preferred for rating collection (section 25) — a tooling
  choice, not a design-methodology choice, and therefore deliberately
  left open here.
- Whether Krippendorff's alpha tooling/library availability in the local
  implementation environment needs to be confirmed before implementation
  begins, or substituted with a from-scratch implementation.
- Whether the final Experiment 5B analysis report should include the raw
  per-item rating table as an appendix or only aggregate/derived
  statistics in the main body.
- Whether, if STATE C (Contradiction, section 23) occurs, the
  "Architecture Review of the relationship between Phase 2C scoring and
  readability" it triggers should be scoped as a design-only document
  (matching every prior Phase 2D architecture-review round) — likely yes,
  by precedent, but not formally pre-committed here since it depends on
  what that review actually finds.

None of these open questions block finalizing this design; they are
implementation-time decisions or decisions properly reserved for a human
reviewer of this document.

## 28. Final Design Decision

This document finalizes the design for Phase 2D Experiment 5B: rating
collection against the existing, frozen 69-item Experiment 5A blinded
package (66 primary + 3 boundary-condition items), using a blinded,
randomized, 5-point comparative "overall preference" scale as the single
primary rating instrument (with awkward-split and reading-effort ratings
as secondary instruments), a `>=3`-evaluator floor per primary item,
diagnostic-only repeat items, a single, precisely defined primary outcome
(the corpus-level median of item-level oriented preference medians, with
its win/tie/loss companion breakdown, tested via a one-time sign test),
a three-state Decision Gate (SUPPORT / NULL / CONTRADICTION), and an
explicit Stop Condition preventing automatic escalation into a further
experiment. No implementation, human evaluation, or new evaluation data
was produced by this design round. The next authorized step is a
separate implementation task for Experiment 5B, to be explicitly
authorized after this design is reviewed.
