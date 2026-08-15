# Phase 2D K-Selection Architecture Review

Status of this document: a **design-only** artifact. It modifies no
production code, no Phase 2D implementation, no adapter, no test, and no
Phase 1–2C file. It implements no new algorithm, chooses no numeric
threshold or penalty, and performs no production wiring. Every claim is
labeled **FACT** (directly observed from source code or from the already-
completed real-content diagnostic), **INFERENCE** (a reasoned conclusion
the facts support), or **HYPOTHESIS** (a plausible but unproven
explanation, or a design option not yet evaluated by evidence). Where a
question cannot be answered from the current evidence, this document says
so rather than forcing an answer.

---

## 1. Review Status

**COMPLETE**, as a design review. This document evaluates three
architecture classes for Phase 2D's segment-count (`K`) selection step,
grounds that evaluation in the real-content diagnostic evidence and the
authoritative Phase 2C scoring documentation, and produces a decision
framework — not a decision. No implementation, prototype, threshold, or
penalty value is chosen. The one open engineering question this review
surfaces (whether/how Phase 2C scores should influence `K`) is
explicitly deferred to a future offline simulation, per §19–§20.

---

## 2. Baseline Architecture

**FACT**, quoted directly from `src/boundary_segmentation.py`
(`_select_cut_positions`, unmodified, current form):

```python
anchors = [p_start] + list(positions) + [p_end]
greedy_boundaries = _greedy_min_k_boundaries(anchors, source_text, max_width)
target_k = len(greedy_boundaries) - 1
if target_k <= 1:
    return greedy_boundaries
# ... DP below is combinatorially restricted to exactly `target_k` segments
```

`_greedy_min_k_boundaries` (also unmodified) computes its result purely
from `anchors` (candidate positions) and `max_width`, via `_fits()` — a
pure display-width check on the **raw** source slice. It never receives,
reads, or references `score_map` or any `WeightedBoundary`. Only after
`target_k` is fixed does the score-maximizing DP run
(`dp[i][k]` for `k` in `1..target_k`), and that DP is combinatorially
constrained to produce **exactly** `target_k` segments per paragraph —
never fewer, never more (confirmed again by direct re-reading of the
unmodified source this round, consistent with the diagnostic report).

**FACT — the pipeline this baseline sits inside** (unchanged across all
prior rounds, re-confirmed this round via checksum): Phase 1 (`text_structure.py`)
→ Phase 2A (`boundary_observation.py`, one `BoundaryCandidate` per integer
offset `1 ≤ pos < len(text)`) → Phase 2B (`boundary_classification.py`,
`BoundaryClass` ∈ {`SENTENCE_FINAL`, `ELLIPSIS`, `CLAUSE`, `OTHER`}) →
Phase 2C (`boundary_scoring.py`, `WeightedBoundary.score`) → Phase 2D
(`boundary_segmentation.py`, this document's subject) → offsets only, no
display text, no timing. Phase 2D never re-detects or re-scores upstream
evidence (confirmed by source inspection, unchanged).

**FACT — algorithm summary (Option A, the current baseline), formally
characterized:**

1. Split `source_text` into paragraphs on `\n` (hard boundaries, never
   crossed).
2. Per paragraph, compute `K = K_min` — the **minimum** number of
   segments such that every consecutive pair of chosen anchors fits under
   `max_display_width`, using the raw source span's display width. This
   step is a pure combinatorial/geometric computation; it has no access
   to, and makes no use of, Phase 2C evidence.
3. Run a dynamic program that selects the highest-total-score partition
   of the paragraph into **exactly** `K` segments (from step 2), among
   all width-feasible choices, tie-broken by the lowest sum of squared
   segment widths.
4. Return the union of all paragraphs' chosen segments.

This is the correct, non-straw-manned characterization of the current,
accepted, frozen Round 1 design — it is exactly what
`PHASE_2D_SCOPE_AND_ARCHITECTURE.md` specified and what
`PHASE_2D_REAL_CONTENT_DIAGNOSTIC_REPORT.md` measured.

---

## 3. Real-Content Evidence

**FACT**, read from `docs/phase2d/PHASE_2D_REAL_CONTENT_DIAGNOSTIC_REPORT.md`
(the authoritative source for this round; not re-derived from memory) and
not reinterpreted:

| Metric | Value |
|---|---:|
| Corpus | 39 files (`mcu1`: 21, `mcu2`: 18), 87,774 characters, 4,128 paragraphs |
| `max_display_width` | 18 |
| Production segments | 10,372 |
| Phase 2D segments | 9,985 |
| Delta | −387 |
| Files with fewer Phase 2D segments | 36 |
| Files with more Phase 2D segments | 3 |
| Identical files | 0 |
| Total Phase 2C candidates | 87,735 |
| Positive-score candidates | 21,085 (24.03%) |
| Production-only cut positions | 4,753 |
| ...of which positive-scored ("meaningful") | 3,070 |
| ...of which **structurally excluded by fixed-K** | **1,847 (60.2%)** |
| ...of which **K-feasible but not selected by the DP** | **1,223 (39.8%)** |
| Paragraphs where raw width > 18 but stripped width ≤ 18 | 208 / 4,128 (5.0%) — pushes toward **more**, not fewer, Phase 2D segments |
| Adapter-only cut positions between two CJK characters | 2,187 / 3,151 |
| ...confirmed via jieba to split a real token | 1,369 (not established as a direct cause of the −387 count; a positional, not necessarily count, divergence) |

This review treats the 1,847/1,223 distinction as load-bearing throughout
(per the diagnostic report's own explicit instruction): **1,847 positions
could never have been selected regardless of score — this is a structural
property of the architecture. The other 1,223 were K-feasible but simply
outscored by a different combination — this is a normal, expected outcome
of any score-maximizing optimizer and is not, by itself, evidence of an
architectural defect.** Only the first category is direct evidence that
Phase 2C's scoring signal is being structurally prevented from mattering.

---

## 4. Problem Statement

**FACT**, restating the question this review exists to answer, without
alteration: does Phase 2D's current "compute `K` from width alone, then
optimize position within exactly `K`" sequencing correctly express the
intent of the Phase 2C scoring model — or does it structurally discard
information that model was designed to carry? If the latter, what class
of architecture should be considered next?

This review explicitly does **not** ask "how do we make Phase 2D match
production," and does not treat production's 10,372-segment output as a
target. §13 addresses why.

---

## 5. Why Fixed-K Is Structurally Limiting

**FACT**, restated precisely from §2–§3: `target_k` is a pure function of
`(anchors, max_width)`. It has no dependency on `score_map` anywhere in
its computation. Once fixed, no downstream step can revise it — the DP's
state space (`dp[i][k]` for `k` up to `target_k`) is defined only up to
`target_k`; there is no code path by which a very strong candidate (e.g.
`SENTENCE_FINAL`+whitespace, 90.0) could cause `K` to be one larger than
what width alone determined.

**FACT (§3's 1,847 figure), the direct, measured consequence:** on real
content, this structural property is not merely theoretical — it excludes
the majority (60.2%) of positive-scored boundaries production happened to
select but Phase 2D could not, independent of their score magnitude. The
diagnostic report's worked example (`mcu1_slide_02`, position 12, a
`CLAUSE`=35.0 candidate, `forced_k=5 > target_k=4`) demonstrates this is a
hard combinatorial fact about that specific paragraph, not a scoring
artifact.

**INFERENCE.** "Structurally limiting" is the correct characterization
for the 1,847 subset specifically — score has *no path* to influence
whether these positions could ever be chosen. It is **not** the correct
characterization for the other 1,223 (§3) — those were fully visible to
the score-maximizing DP and lost a fair competition to a different
combination; that is the optimizer working as designed, not a structural
limitation. This review does not conflate the two, and any future
proposal must not either.

**Not established here:** whether excluding these 1,847 positions
produces *worse* subtitles than including them would have. §11 and §13
address why this is a separate, harder question that this review does not
answer.

---

## 6. Phase 2C Score Semantics

**FACT, quoted directly, verbatim, from the authoritative, currently-in-
force design decision** (`docs/phase2c/decisions/PHASE_2C_NUMERIC_BASELINE_DECISION.md`
§6, "Score Semantics"):

> "Phase 2C scores are **signed relative boundary preferences**. They are
> not probabilities, confidence percentages, cut probabilities, or
> normalized scores. `SENTENCE_FINAL = +80` means a strong positive
> boundary preference relative to other candidates — it does not mean
> "80% likely to be a cut point." Likewise, `Technical = -30` means a
> negative relative boundary preference — it does not mean "30%
> probability of not cutting." **Scores are only meaningful in comparison
> to other scores produced by the same formula; no absolute interpretation
> is defined or implied.**"

**FACT, corroborated independently by `docs/phase2c/contracts/PHASE_2C_PRODUCTION_SCORING_IMPLEMENTATION_CONTRACT.md`
§5.4 ("Numeric Strategy," LOCKED DESIGN DECISION):** the following are,
and must remain, absent from the implementation: normalization, any
threshold, any hard floor, any probability conversion, sigmoid/softmax,
or "any score-to-cut mapping." The same contract's §21 ("Phase 2D
Boundary") states explicitly: "Phase 2C, including its production
implementation, must not decide, compute, or stub... `should_cut`, any
threshold, candidate selection, candidate ranking, DP (dynamic
programming) optimization... Phase 2C ends at `WeightedBoundary`... Phase
2D... is responsible for consuming that information and turning it into
actual segmentation behavior."

**INFERENCE, directly answering the task's item 10 requirement ("if the
documents do not define a utility interpretation, explicitly state
that").** The authoritative documentation defines Phase 2C scores as an
**ordinal/relative ranking signal within a single, already-fixed
comparison set** ("comparison to other scores produced by the same
formula") — it does **not** define them as an absolute or cardinal
utility with a stable numeric scale that could be meaningfully compared
against a *different kind* of quantity (e.g., "the cost, in some common
unit, of producing one more subtitle segment"). This distinction matters
directly for Options B and C (§8–§9): **any formulation that needs to ask
"is this boundary's score worth the cost of an additional segment?" is
introducing a new interpretation of Phase 2C's numbers that the current,
locked design does not establish or authorize.** This is not a defect in
Phase 2C — the design explicitly, deliberately defers "what to do with
these scores" to Phase 2D (`PHASE_2C_NUMERIC_BASELINE_DECISION.md` §7,
"Phase 2C computes relative scores only. The question of what to do with
those scores belongs to Phase 2D"). But it does mean that step is a
**genuinely new design decision**, not something implicit in the existing
scores waiting to be unlocked by a cleverer algorithm.

**FACT.** Score magnitudes observed on real content (§3 of the diagnostic
report, re-confirmed by this round's reading of the contract) are
`CLAUSE`=35, `SENTENCE_FINAL`=80 (90 with whitespace), `ELLIPSIS`=65 (75
with whitespace), whitespace-only `OTHER`=10, `Technical`/`Atomic`=−30,
`INTERNAL`=−20, `CJK↔LATIN` transition=+15. No document assigns any of
these a meaning beyond "this boundary class/evidence combination ranks
here relative to the others" — e.g., there is no stated basis for
claiing `CLAUSE`(35) is "worth" 3.5× what a whitespace-`OTHER`(10)
boundary is worth in any transferable sense; both statements are only
license to say `CLAUSE` outranks whitespace-`OTHER` when they compete for
the *same* cut position under the *same* `K`.

---

## 7. Option A — Fixed-K

**Formal characterization**, per §2: `K = K_min(width)`; DP maximizes
`Σ score(chosen positions)` subject to exactly `K` segments and per-
segment width feasibility.

**Strengths (FACT/INFERENCE):**

- **Deterministic and simple to reason about.** `K` is decided by one
  pure, side-effect-free geometric pass before any scoring logic runs;
  the DP that follows has a bounded, well-understood state space
  (`O(n·K)` per paragraph).
- **Width-safety is unconditional.** Because `K_min` is computed from
  width feasibility directly, no output segment can ever exceed
  `max_display_width` (re-confirmed, unchanged, by the diagnostic
  report §6, §10, no over-width segment found anywhere in the real
  corpus).
- **Minimizes segment count by construction**, which is a reasonable
  default policy in the absence of any other signal — more segments are
  not "free" (each is a separate subtitle event downstream), so choosing
  the fewest segments the width constraint allows, then making the best
  use of scores within that count, is a coherent, defensible starting
  policy — not an arbitrary one.
- **Correctly does not invent a threshold.** It never asks "is this
  score high enough" — it only ever asks "which subset of the already-
  necessary cuts is best," a comparison Phase 2C's documented relative-
  score semantics (§6) fully supports.

**Weaknesses (FACT/INFERENCE, grounded in §3, §5):**

- **Structurally cannot let a strong boundary create an additional
  segment**, even when width would permit it and the evidence is
  unambiguous (e.g. a `SENTENCE_FINAL`+whitespace=90 candidate one
  character away from the paragraph's computed `K_min` boundary set).
  §3/§5's 1,847-position figure is the direct, measured size of this
  gap on real content.
- **Treats `K_min` as an implicit ceiling of `K`, not just a floor.**
  Nothing in the design intends `K_min` to be a *maximum* — it is
  derived purely as "the fewest segments physically possible" — but the
  current architecture uses it as if it were also the *correct* count,
  with no mechanism to reconsider that assumption using the very
  evidence (Phase 2C scores) the rest of the pipeline exists to produce.
- **What Phase 2C information it structurally discards:** the *presence*
  of a positive-scored candidate outside the chosen `K`-segment
  partition — this is not merely "not selected," per §5's distinction,
  for the 1,847/3,070 subset it is **invisible to the optimizer's
  decision space entirely**, because that decision space excludes any
  partition larger than `K_min`.

This is the accepted, currently-shipping baseline and is **not being
proposed for replacement by this document** — it is being formally
characterized so Options B and C can be compared against it fairly.

---

## 8. Option B — Variable-K

**Formal shape (HYPOTHESIS — a class of architecture, not one specific
algorithm):** `K` is no longer fixed before optimization. The optimizer
may choose any `K ≥ K_min`, up to some natural ceiling (e.g. the number
of available candidate positions), and the objective function itself
decides, as part of the same optimization, whether a `K > K_min`
partition's additional boundary evidence justifies the additional
segment(s).

**Possible formulations, presented without selecting one (per the task's
explicit instruction):**

- **Explicit segment-count penalty.** Maximize
  `Σ score(chosen positions) − penalty × (K − K_min)` over both the
  partition *and* `K` simultaneously. Requires a `penalty` value with a
  defined unit compatible with Phase 2C's score scale — and §6
  establishes that no such unit is currently defined by any locked
  document. Choosing one would be a new, first-of-its-kind Phase 2D
  policy decision, not a mechanical extension of Phase 2C's model.
- **Boundary-value-vs-additional-segment-cost framing.** Conceptually
  similar to the penalty formulation but framed as a direct trade-off
  question ("is this specific candidate's score high enough to be worth
  one more line?") evaluated per-candidate rather than globally. Same
  fundamental requirement: some notion of "worth," which §6 shows is not
  currently defined.
- **Constrained optimization with a evidence-count or evidence-sum
  floor.** E.g., "increase `K` by one only if doing so lets the
  partition include at least one candidate scoring above the *median* (or
  some other data-derived, non-arbitrary) score in that paragraph." This
  avoids inventing an absolute threshold by deriving the comparison from
  the data itself, but still requires deciding *which* data-derived
  statistic is the right one, and that choice is itself a policy
  decision requiring justification this review does not attempt to
  supply.
- **Pareto selection.** Rather than collapsing score and segment-count
  into one scalar objective, treat them as two separate objectives and
  compute the Pareto frontier of `(total score, K)` pairs per paragraph,
  deferring the final single-point choice to a human-reviewable policy
  step rather than an automatic formula. This sidesteps needing a
  numeric trade-off rate at optimization time, at the cost of needing
  one at *some* later point if the system must still emit exactly one
  segmentation per paragraph.

**How width constraints remain hard (INFERENCE, uncontroversial across
all four formulations above):** width feasibility is a **binary**
constraint (a partition either respects `max_display_width` on every
segment or it does not) and would remain exactly that — Option B does
not touch this; only the *count* decision changes from fixed to
optimized-over.

**How paragraph boundaries remain hard:** unaffected in every
formulation above — the paragraph-splitting step (`_split_paragraphs`)
is orthogonal to the `K`-selection question and would be reused
unchanged.

**How determinism would be preserved:** any of the four formulations
above remains a deterministic function of `(candidates, scores, width,
paragraph text)` provided the trade-off rule itself (penalty value,
threshold, or Pareto-selection rule) is itself deterministic and fixed
in advance — determinism is not inherently at risk from moving to
variable-`K`, but it does mean whatever policy is chosen must be fully
specified (no "pick whichever looks better" step), exactly like the
current architecture's tie-break rule (lowest sum-of-squared-widths) is
fully specified today.

**How over-segmentation could be controlled:** this is precisely what
every one of the four formulations above is attempting to do (a penalty,
a worth-threshold, a data-derived floor, or a human-reviewed Pareto
choice) — and precisely why none can be adopted without first deciding
what "the cost of an extra segment" means, since §6 establishes that
concept does not currently exist anywhere in the locked Phase 2C/2D
design.

**What new policy decision is required (the central finding of this
section):** Option B, in **any** of its formulations, requires defining
a **segment-count policy** — a rule for converting "this candidate's
relative score" into "this is or is not worth an additional subtitle
line" — that does not currently exist in any authoritative document.
This is not a numeric-calibration question (adjusting an existing,
already-meaningful value); it is the introduction of an entirely new kind
of decision the pipeline has never made before at any phase.

---

## 9. Option C — Constrained Objective

**Formal shape (HYPOTHESIS, conceptual only, per the task's explicit "do
not implement, do not select numerical penalties" instruction):**

```
maximize:
    Σ selected_boundary_score
    − segmentation_cost(K)
    − optional width_balance_cost
subject to:
    every segment fits under max_display_width
    paragraph boundaries never crossed
    deterministic, pure function of (candidates, scores, width, text)
```

This differs from Option B primarily in **framing, not necessarily in
final mathematical shape**: Option B is presented above as "fix a family
of candidate formulations and pick among them"; Option C is presented as
"treat the whole paragraph's segmentation, including `K` itself, as one
joint optimization from the start," which is a broader framing that could
subsume several of Option B's formulations (e.g. the explicit
segment-count-penalty formulation is one specific instance of Option C's
general shape, with `segmentation_cost(K) = penalty × (K − K_min)`).

**INFERENCE.** The design decisions Option C requires are a superset of
Option B's: it needs (1) the same segment-count policy §8 identifies as
missing, (2) a decision about whether `width_balance_cost` (currently
only a tie-breaker in Option A) should become a first-class term in the
primary objective rather than a secondary tie-break, and (3) a decision
about whether `segmentation_cost` should be a flat per-segment cost, a
convex/increasing cost (discouraging runaway over-segmentation more
strongly as `K` grows), or something else — none of which is specified,
implied, or ruled out by any existing document.

**What this review is explicitly not doing here:** proposing a specific
`segmentation_cost` function, proposing that `width_balance_cost` move
into the primary objective, or asserting Option C is "more principled"
than Option B. They are presented as related but distinct framings so a
future design round can choose deliberately between "extend the existing
two-phase structure with an extra term" (closer to Option B) and
"replace the two-phase structure with one joint optimization" (Option C)
— a genuinely open architectural choice this review surfaces but does not
resolve.

---

## 10. Hard Minimum K vs Fixed K

**FACT.** The current implementation uses `K = K_min` — a **fixed
value**, computed once and never revisited. This is a stronger
constraint than `K ≥ K_min` — a **hard minimum**, which would still
guarantee width-feasibility (no paragraph could ever need fewer than
`K_min` segments, by definition of "minimum feasible") while permitting,
but not requiring, more.

**INFERENCE, on why this distinction is central (directly per the task's
instruction):** `K ≥ K_min` is the correct constraint shape for **any**
of Option B's or Option C's formulations — none of them can ever produce
a `K` below `K_min` without violating width feasibility, so `K_min`
remains a true floor regardless of which architecture is chosen. What
changes across Option A vs. B/C is **only** whether `K_min` is also
treated as a ceiling. The current architecture's `K = K_min` conflates
"the fewest segments physically necessary" with "the number of segments
that should be produced" — §6 already shows nothing in Phase 2C's score
semantics implies these are the same quantity, and §5's 1,847-position
figure shows real, measurable cases where they are not.

**Implications of relaxing to `K ≥ K_min` (INFERENCE):**

- **Complexity:** the DP's state space grows from `O(n·K_min)` per
  paragraph to `O(n·K_max)` for whatever `K_max` the search considers
  (e.g., the number of candidate positions), a real but bounded and
  precomputable cost — not a risk to correctness, only to runtime, and
  subtitle segmentation is an offline, non-realtime operation, so this is
  unlikely to be a binding practical constraint (**HYPOTHESIS** — not
  measured this round).
- **Safety:** width-feasibility remains exactly as strong a guarantee as
  today, since `K ≥ K_min` never permits an infeasible partition; nothing
  about relaxing the ceiling weakens the floor.
- **Determinism:** preserved, provided (per §8) the rule for choosing
  among the now-larger space of feasible `K` values is itself fully
  specified and free of any non-deterministic tie-break.
- **The one genuinely new risk this relaxation introduces:** without a
  well-specified segment-count policy (§8, §11), an unconstrained
  `K ≥ K_min` search could in principle select `K` values far above what
  any reasonable person would consider a good subtitle segmentation
  (e.g., cutting at every candidate with `score > 0`, of which 21,085
  exist across the corpus — §3). This is precisely why §8 frames
  "controlling over-segmentation" as *the* central unresolved policy
  question, not a minor implementation detail.

---

## 11. Segment Count Policy

**FACT/INFERENCE**, restating and formalizing the task's explicit
instruction (§9 of the task) as a first-class finding of this review:
**"boundary strength" (a Phase 2C score) and "segment-count policy" (a
rule for deciding whether that strength justifies an additional subtitle
line) are two conceptually distinct things, and no existing document
defines the second.** `CLAUSE = 35` is evidence that a boundary is more
clause-like than an unclassified `OTHER` boundary; it is not, on its own
or by any documented interpretation, evidence that a clause boundary
"deserves" its own subtitle line whenever width would technically permit
one more segment.

**INFERENCE.** This distinction matters because it changes what a future
design round must produce. It is not sufficient to say "let scores
influence `K`" — that sentence is under-specified until a segment-count
policy answers questions like: does a single `CLAUSE`(35) candidate ever,
by itself, justify one more segment, or only in combination with other
factors (e.g. how much width slack exists, how many other candidates are
competing, how far the paragraph already is from `K_min`)? Is the policy
the same for every `BoundaryClass`, or does `SENTENCE_FINAL` warrant a
different threshold than `CLAUSE`? None of these questions has an answer
in any authoritative document reviewed this round (`PHASE_2C_NUMERIC_BASELINE_DECISION.md`,
`PHASE_2C_PRODUCTION_SCORING_IMPLEMENTATION_CONTRACT.md`,
`PHASE_2D_SCOPE_AND_ARCHITECTURE.md`, `PHASE_2D_PRODUCTION_INTEGRATION_DESIGN.md`).

**Not addressed here, per the task's explicit "do not invent a
threshold" instruction:** this review does not propose an answer to any
of the questions in the preceding paragraph. It records them as the
concrete content of the "segment-count policy" decision that Options B
and C both require and Option A avoids by never asking them.

---

## 12. Protection Score Semantics

**FACT**, from `docs/phase2c/contracts/PHASE_2C_PRODUCTION_SCORING_IMPLEMENTATION_CONTRACT.md`
§11 ("Protection Mapping," LOCKED DESIGN DECISION): `Technical` and
`Atomic` protection (`−30` each, strongest-only, never `−60`) fire when a
candidate position sits inside a `containing_spans` entry of type
`"technical"` or `"atomic"` — i.e., **specific, structurally-identified
spans** Phase 1/2A already detected (per the broader project history in
this repository: technical terms, version strings, and numeric/atomic
literals such as `16:9` or `v1.2.3`). `INTERNAL` (`−20`, additive on top
of Technical/Atomic) fires when `punctuation_sequence_state ==
PunctuationSequenceState.INTERNAL` — i.e., the candidate sits **inside**
a multi-character punctuation run (e.g. the second `.` of an ASCII
ellipsis `...`), not at its boundary.

**FACT.** Both mechanisms are, per the same document's own framing (§6
of `PHASE_2C_NUMERIC_BASELINE_DECISION.md`, "Score Semantics," which
applies uniformly to every term in the additive formula, not only the
positive ones): **relative preferences specific to a structurally-
identified condition at that exact candidate**, not a general-purpose
"discourage splitting" signal. A `Technical`-protected position is
penalized because it sits inside a recognized technical term or numeric
literal that should not be casually split — the penalty is evidence
*about that position*, not a policy lever for controlling how many total
segments a paragraph should have.

**INFERENCE, directly answering the task's explicit warning (§11 of the
task).** A variable-K architecture (Option B/C) that folded protection
scores into a generic "total penalty budget" alongside a new
segment-count cost term would risk conflating two different things:
"this position is a bad place to cut" (protection's actual, documented
meaning) with "cutting anywhere in general has a cost" (the new concept
§8/§11 shows is currently undefined). These should almost certainly
remain **separate** signals in any future architecture — protection
scores continue to suppress specific candidate positions from being
attractive (exactly as they do today, via the additive formula feeding
into the existing score-maximization), while any new segment-count-cost
term (if one is adopted) would need its own, independently justified
definition, not one borrowed from repurposing `−30`/`−20`'s existing,
documented, position-specific meaning. This review does not propose a
mechanism for keeping them separate — only flags that keeping them
separate is a requirement any future design must satisfy, per the
documented semantics of Technical/Atomic/INTERNAL.

---

## 13. Production Behavior vs Phase 2D Objective

**FACT**, restating the task's explicit framing (§12 of the task), which
this review adopts without qualification: production's
`subtitle_segmenter.py` is useful as a **behavioral reference** (it shows
one existing, shipped, presumably-reasonable segmentation of the same
text), a **regression reference** (the shadow-mode harness exists
specifically to detect and classify divergence from it), and a **source
of existing constraints** (e.g. its own width-safety and paragraph-
boundary conventions, which Phase 2D independently re-derives rather than
inherits). It is explicitly **not** treated by this review as the
definition of correct segmentation.

**INFERENCE.** This has a direct consequence for how §3's evidence should
be read: the −387 delta and its 1,847/1,223 breakdown are evidence that
Phase 2C's scoring signal is structurally constrained by Phase 2D's
current architecture — they are **not**, on their own, evidence that
Phase 2D's output is worse than production's. Production's own
segmentation is a hand-written, rule-based, punctuation-driven algorithm
with no access to Phase 1–2C's richer evidence model at all (confirmed
across all prior rounds: `subtitle_segmenter.py` contains no
`BoundaryClass`/`CharacterClass`/Phase 2C reference of any kind). A
future architecture that used Phase 2C's evidence "better" by some
principled measure might diverge from production *more*, not less, and
that would not, by itself, indicate a regression. This review does not
attempt to settle whether production's or a hypothetical future Phase
2D's segmentation is "better" in any absolute sense — that question is
out of scope for a source-level architecture review and would require a
different kind of evidence (e.g., human readability/quality judgment)
than either the code or the real-content corpus can supply directly.

---

## 14. Offline Simulation Architecture

**HYPOTHESIS/design proposal — not implemented this round, per the
task's explicit instruction.** Before any of Options A/B/C can be
compared meaningfully, an offline simulator should exist that:

**Inputs (all already available, no new detection/parsing logic
needed):**

- `source_text` — a single file's raw notes text, unmodified.
- `weighted_boundaries` — the real, unmodified output of
  `boundary_scoring.score_boundaries()` (reachable today via the existing
  `boundary_segmentation_adapter._weighted_boundaries_for_text()` helper,
  which already composes the real, frozen Phase 1→2A→2B→2C chain and
  requires no new code to call).
- `max_display_width` — the same configurable constraint Phase 2D
  already accepts.
- A **pluggable K-selection/optimization strategy** — a function taking
  `(paragraph_span, candidate_positions, score_map, source_text, max_width)`
  and returning a chosen partition. Option A's existing
  `_select_cut_positions()` would be **one** such strategy (reused,
  unmodified, as the baseline/"Experiment 0" implementation — not
  reimplemented); candidate Option B/C strategies would be additional,
  separate functions living **only** in the simulator, never inside
  `src/boundary_segmentation.py` itself, so no frozen file is touched by
  building or running this tool.

**Outputs, per file and aggregated across the corpus:**

- Selected segments (offsets), selected boundary positions, and the
  realized `K` per paragraph and per file.
- Total selected score (sum of `WeightedBoundary.score` over chosen
  cuts) — the direct analogue of the "total score" Option A's DP already
  maximizes, now comparable across strategies with different `K`.
- Width statistics: max/mean segment display width, count of segments
  within some margin of `max_display_width` (a proxy for "how tightly
  packed" a strategy's output is).
- **Protection-violation count**: number of selected cut positions whose
  `WeightedBoundary.score` reflects a `Technical`/`Atomic`/`INTERNAL`
  penalty — i.e., how often a candidate strategy chooses to cut at a
  protected position at all (Option A's DP can already do this today, if
  it is the only way to reach a feasible `K`-segment partition — this
  metric would make that visible and comparable across strategies rather
  than implicit).
- **Paragraph-boundary-violation count**: should always be zero for any
  correct strategy (a structural invariant, not a soft metric) — included
  as a sanity check the simulator itself enforces, not a trade-off
  dimension.
- Comparison against production (`subtitle_segmenter.segment_notes_for_subtitles`,
  unmodified) and against the current Phase 2D adapter output
  (`segment_notes_for_subtitles_via_boundary_engine`, unmodified) — both
  purely as **reference points for the report**, not as an optimization
  target for any candidate strategy (§13).

**Design constraint, explicit and non-negotiable per the task's scope
rules:** this simulator would be new, standalone code living outside
`src/`/`tests/` (e.g. a `scripts/`-style tool, exactly like the user's own
`evaluate_phase2d_real_content.py` or this round's ad hoc diagnostic
script) — it would call the real, frozen Phase 1–2D functions by import,
never reimplement or fork them, and it would not modify
`boundary_segmentation.py`, the adapter, or any test. **This review does
not build this simulator.** It specifies what it would need to do so a
future, explicitly-scoped implementation round has an unambiguous
starting point.

---

## 15. Evaluation Metrics

**Design specification (not computed this round beyond what §3 already
reports from the existing diagnostic).** For each candidate strategy
(Option A baseline plus any Option B/C variants a future round
constructs), the simulator (§14) should report:

1. **Total segment count** (corpus-wide sum) — the same top-line number
   §3 already reports for Options A vs. production.
2. **Per-file segment count delta** vs. production and vs. Option A —
   two separate deltas, not one, since "vs. production" and "vs. current
   Phase 2D" answer different questions (§13).
3. **Per-paragraph `K` distribution** — a histogram of realized `K` per
   paragraph, to see whether a candidate strategy produces a smoothly
   varying distribution or degenerate behavior (e.g. always `K_min`,
   always `K_min+1`, or a long tail of very large `K`).
4. **Boundary agreement with production** — fraction of interior cut
   offsets that match production's exactly (this review's prior rounds
   already compute this; the simulator should compute it per-strategy).
5. **Boundary agreement with current Phase 2D (Option A)** — same
   computation, against Option A's own output, to see how far a
   candidate strategy departs from today's baseline specifically.
6. **Positive Phase 2C boundaries selected** — count of chosen cut
   positions with `score > 0`, per strategy.
7. **Positive Phase 2C boundaries bypassed** — the complement of #6,
   broken down (per §3/§5's discipline) into "structurally excluded by
   `K`" vs. "K-feasible but outscored," **for strategies where that
   distinction still applies** (a variable-`K` strategy may eliminate the
   first category entirely, which would itself be a reportable, expected
   result, not evidence of superiority on its own — see #14 below).
8. **Protection boundaries violated** — as defined in §14's output list.
9. **Maximum display width observed**, and 10. **number of over-width
   segments** — both should remain `0` for every correct strategy; any
   non-zero value here indicates a bug in that strategy's implementation,
   not a legitimate trade-off outcome.
11. **CJK mid-word cut rate** — reusing the existing `jieba.cut()`-based
    check the diagnostic report already applied, so this can be compared
    directly against the §3 baseline figure (1,369/3,151) for any
    candidate strategy.
12. **Determinism** — same input always produces byte-identical output
    across repeated runs; a binary pass/fail check, not a graded metric.
13. **Paragraph-boundary violations** — as in §14, should always be zero;
    a correctness check, not a trade-off metric.
14. **Score utilization** — a new metric this review names but does not
    define numerically: some measure of how much of the corpus's
    positive-scored evidence (21,085 candidates, §3) a strategy is able
    to act on, as opposed to how much of it a strategy is structurally
    prevented from ever considering (the §5 distinction). This is
    conceptually related to, but not the same as, metric #7.
15. **Segment-count distribution** — the corpus-wide distribution of
    per-file or per-paragraph segment counts, to visualize whether a
    candidate strategy's departure from Option A is a small, broad shift
    or a small number of extreme outliers (relevant context for
    interpreting the "+segments" file pattern the diagnostic report's §10
    already found for Option A).

**INFERENCE, restating the task's explicit instruction as a permanent
constraint on how these metrics are used:** "closer to production"
(metrics #2, #4) and "better utilization of Phase 2C evidence" (metrics
#6, #7, #14) are **not the same axis** and must be reported and read
separately. A strategy could score better on one and worse on the other;
neither dominates the other by definition, and no metric in this list is
proposed as a single scalar "winner" criterion.

---

## 16. Experiment Matrix

**Design specification only — not executed this round, per the task's
explicit instruction.**

| # | Experiment | Purpose | What is intentionally left unspecified |
|---|---|---|---|
| 0 | Current fixed-K baseline (Option A, unmodified `_select_cut_positions`) | Establishes the reference point every other experiment is compared against — this is exactly what the real-content diagnostic report already ran; Experiment 0 does not need to be re-run, only re-used as the baseline row in every future comparison table | Nothing — this is the frozen, already-measured baseline |
| 1 | Variable-K, no additional-segment penalty (`K ≥ K_min`, DP free to choose any feasible `K` maximizing total score with zero cost per extra segment) | Establishes the **opposite extreme** from Option A — shows how far segment count would grow if literally every positive-scored candidate were free to trigger a cut, with no offsetting cost at all | The likely (**HYPOTHESIS**, not measured) outcome is substantial over-segmentation, since 21,085 positive-score candidates exist corpus-wide (§3) — this experiment's value is precisely in quantifying how extreme that outcome actually is, not in being a viable design candidate on its own |
| 2 | Variable-K with a symbolic/parameterized segment penalty (`penalty` left as a free variable, swept across a range rather than fixed to one value) | Produces the shape of the score-vs-count trade-off curve as `penalty` varies, without committing to any one value | The specific `penalty` values to sweep, and the unit `penalty` is denominated in — both explicitly deferred, consistent with §6's finding that no such unit currently exists in the locked design |
| 3 | Alternative constrained formulation: `K` may increase only when additional positive evidence exceeds a configurable policy value | Tests a **threshold-shaped** policy (as opposed to Experiment 2's **continuous-cost**-shaped policy) to see whether the two produce meaningfully different corpus-wide behavior, or converge to similar outcomes for some correspondence between the threshold and the penalty rate | The policy value itself, and whether it should be uniform across `BoundaryClass` or vary by class (§11) — both left open |
| 4 | Pareto analysis: total score vs. segment count, per paragraph or per file | Does not produce a single segmentation at all — produces the frontier of non-dominated `(score, K)` pairs, to let a human reviewer see the actual shape of the trade-off before any policy (Experiments 2/3) is chosen | No policy is chosen by this experiment; its output is a diagnostic artifact (a curve or point cloud), not a candidate segmentation strategy |

**INFERENCE.** Experiment 4 (Pareto analysis) is the most information-
rich and least commitment-requiring of the four non-baseline experiments
— it requires no new policy decision to run, only the ability to
enumerate multiple `K`-feasible partitions per paragraph and compute
their scores, and its output (the shape of the trade-off curve) is
exactly the missing input §8/§11 identify as necessary before any
specific penalty or threshold value could be chosen non-arbitrarily. This
review recommends it as the most productive next concrete step (§20),
without asserting the other experiments are unnecessary — they answer
different, also-useful questions once a candidate policy shape exists to
test.

---

## 17. Risks and Failure Modes

**INFERENCE/HYPOTHESIS**, organized by which option(s) each risk applies
to:

- **Over-segmentation runaway (Option B/C, Experiment 1 specifically).**
  With no cost term, a variable-`K` optimizer maximizing raw total score
  has no reason not to cut at every one of the corpus's 21,085
  positive-score candidates — an extreme, almost certainly undesirable
  outcome that Experiment 1 exists specifically to quantify, not to
  propose as a real design.
- **Protection-semantics conflation (Option B/C, §12).** Reusing
  Technical/Atomic/INTERNAL's existing, documented, position-specific
  penalties as if they were a general segment-count-cost signal would
  misrepresent what those scores mean and could produce behavior no
  calibration evidence supports.
- **Score-unit invention without justification (Option B/C, §6, §8).**
  Any penalty, threshold, or cost value introduced without being
  data-derived (e.g., informed by Experiment 4's Pareto curve) or
  otherwise explicitly justified would be an arbitrary policy choice
  dressed up as a calibrated one — precisely what the task instructs
  this review to avoid, and what a future implementation round must also
  avoid.
- **Production-similarity optimization (all options, §13).** Any future
  round that tunes a variable-`K` policy specifically to shrink the
  −387 delta, rather than to express Phase 2C's evidence coherently,
  would be optimizing for the wrong target — the task, this review, and
  the diagnostic report all explicitly reject "match production" as the
  objective.
- **Increased computational complexity (Option B/C, §10).** A larger `K`
  search space is a real, bounded engineering cost, not a correctness
  risk — but should be measured (not assumed) before being dismissed as
  negligible, especially for very long paragraphs.
- **Determinism regression (Option B/C, generic).** Any new
  policy/threshold mechanism must be fully specified with no
  under-determined tie-break, exactly as Option A's existing sum-of-
  squared-widths tie-break is today; an under-specified policy could
  introduce non-determinism where none exists now.
- **Metric conflation (§15).** Treating "closer to production" and
  "better evidence utilization" as one combined score, rather than two
  separate axes, would silently reintroduce the production-similarity
  risk above under a different name.
- **Scope creep toward "fixing" the −387 number specifically (all
  options).** The single most important discipline this review and any
  follow-on work must maintain, per the task's explicit and repeated
  instruction: the real corpus is evidence for an architectural question,
  not a target output. A future round succeeding at "architecturally
  coherent evidence-to-decision translation" and a future round
  succeeding at "segment count closer to 10,372" are not the same success
  criterion, and only the first is in scope for this project's stated
  goal (§4).

---

## 18. Acceptance Criteria for a Future Architecture

**INFERENCE**, synthesized from §7–§17, stated as criteria a future
Option B/C implementation (not designed or chosen here) would need to
satisfy before being considered ready for its own implementation round:

1. Width-feasibility remains an unconditional hard constraint — no
   output segment may ever exceed `max_display_width` (unchanged from
   Option A).
2. Paragraph boundaries remain hard, never-crossed constraints
   (unchanged from Option A).
3. The architecture is fully deterministic — same input always produces
   the same output, with no under-specified tie-break.
4. Any segment-count policy (threshold, penalty, or other mechanism) is
   **explicitly justified**, ideally by reference to an empirically
   observed trade-off curve (Experiment 4) rather than chosen for its own
   sake or to move a specific corpus-wide number.
5. Protection scores (`Technical`/`Atomic`/`INTERNAL`) retain their
   documented, position-specific meaning and are not repurposed as a
   general segment-count-cost signal (§12).
6. The architecture does not require reinterpreting Phase 2C's scores as
   absolute utilities beyond what `PHASE_2C_NUMERIC_BASELINE_DECISION.md`
   §6 actually establishes (relative, same-formula-comparable preferences
   only) — or, if it does require a stronger interpretation, that
   requirement is surfaced as an explicit, separately-reviewed
   **Phase 2C-level** design question, not silently assumed inside
   Phase 2D.
7. Evaluation distinguishes "closer to production" from "better
   utilization of Phase 2C evidence" as separate, non-conflated
   findings (§13, §15).
8. The architecture is evaluated via the offline simulator (§14) against
   the real corpus before being proposed for implementation inside
   `src/boundary_segmentation.py` itself.

---

## 19. Decision Framework

**A. What is proven?**
- Fixed-`K`, as currently implemented, structurally and provably
  excludes a majority (60.2%, 1,847/3,070) of the meaningful, positive-
  scored boundaries production selected but Phase 2D could not — this is
  a demonstrated architectural property, not an inference from
  aggregate numbers (§3, §5).
- Phase 2C's documented score semantics are relative/ordinal, not
  absolute utilities, and no existing document defines a "cost of an
  additional segment" concept commensurable with those scores (§6).
- Protection scores (`Technical`/`Atomic`/`INTERNAL`) have a specific,
  position-level documented meaning distinct from any general
  segment-count-cost concept (§12).
- The −387 net delta is not attributable to fixed-K alone — width
  measurement (§8/§10 of the diagnostic report) and word-boundary
  positional drift both contribute independently, and in the width case,
  in the *opposite* net direction (§3).

**B. What is not proven?**
- That letting Phase 2C scores influence `K` would produce a "better"
  segmentation by any defined standard — no human-quality or downstream-
  impact evidence has been gathered for either Option A's or a
  hypothetical Option B/C's output.
- That any specific penalty, threshold, or cost formulation (Option B's
  four sketched variants, or Option C) is superior to any other — none
  has been implemented, simulated, or measured.
- That the 1,223 "K-feasible but outscored" positions (§3, §5) represent
  a problem at all — this is potentially normal optimizer behavior, not
  necessarily evidence of anything needing to change.

**C. What architectural assumption is now questionable?**
- The assumption, implicit in Option A's `K = K_min`, that "the fewest
  segments width allows" and "the number of segments that should be
  produced" are the same quantity. §5–§6 show this assumption has no
  independent justification in any authoritative document — it is a
  reasonable default, not a proven-correct design principle.

**D. What design decision must be made?**
- Whether Phase 2D should adopt a segment-count policy at all (i.e.,
  whether `K = K_min` should become `K ≥ K_min` with some evidence-aware
  selection rule) — and if so, what that policy's specific
  mechanism/unit/threshold should be (§8, §11).

**E. What information is missing to make that decision?**
- An empirically observed score-vs-segment-count trade-off curve
  (Experiment 4, §16) — without this, any specific policy value chosen
  would be arbitrary, which the task explicitly prohibits.
- Any human-facing quality signal about whether specific real
  divergences (e.g. the `mcu1_slide_02` `CLAUSE`-bypass example, §5) are
  actually worse subtitles, better subtitles, or immaterially different
  — this review's evidence is entirely structural/quantitative, not
  qualitative.
- A resolution to §6's open question — whether Phase 2C's score semantics
  should be extended (a Phase 2C-level decision, not a Phase 2D one) to
  support a utility interpretation, or whether Phase 2D should introduce
  an entirely separate, independently-justified cost concept instead.

**F. What experiment should be performed next?**
- Build the offline simulator (§14) and run **Experiment 4 (Pareto
  analysis)** first, against the same 39-file real corpus, entirely
  outside `src/`/`tests/`, producing the score-vs-`K` trade-off shape per
  paragraph without committing to any policy. This is the lowest-
  commitment, highest-information next step identified by this review.

**This review does not force a decision on D.** Per the task's own
explicit permission, the correct conclusion at this point is:
**architecture decision deferred pending offline simulation (Experiment
4).**

---

## 20. Recommended Next Step

**INFERENCE**, following directly from §19-F: construct the offline
simulator described in §14, as new, standalone tooling outside `src/`
and `tests/` (mirroring the existing `evaluate_phase2d_real_content.py`
and this session's own diagnostic-script precedent), and run Experiment 4
(Pareto analysis, §16) against the real 39-file corpus. This produces the
missing input (§19-E) — an observed trade-off shape — without requiring
any premature commitment to a penalty value, threshold, or utility
reinterpretation of Phase 2C's scores. Only after that evidence exists
should a follow-on design round revisit §19-D (whether and how to adopt
a segment-count policy).

This recommendation is a **next experiment**, not a next implementation.
It does not authorize modifying `boundary_segmentation.py`, the adapter,
or any test, and does not authorize choosing a specific Option B/C
formulation.

---

## 21. Explicit Non-Goals

This review did not, and does not:

- Modify `src/boundary_segmentation.py`, `src/boundary_segmentation_adapter.py`,
  `src/subtitle_segmenter.py`, `src/subtitle_pipeline.py`, `src/subtitle_alignment.py`,
  or any Phase 1–2C source file.
- Modify any existing test file.
- Modify any existing documentation file other than creating this one
  new document.
- Implement, prototype, or run any of Options B/C or the Experiment
  0–4 matrix.
- Choose a specific segment-count penalty, threshold, or policy value.
- Reinterpret Phase 2C scores as absolute utilities beyond what
  `PHASE_2C_NUMERIC_BASELINE_DECISION.md` §6 actually establishes.
- Reinterpret Technical/Atomic/INTERNAL protection scores as a general
  anti-segmentation penalty.
- Treat production's segmentation as the definition of correctness.
- Treat the current Phase 2D implementation as "wrong" merely because it
  diverges from production.
- Add jieba, semantic-phrase logic, colon handling, or any new
  heuristic.
- Perform or design production cutover/wiring.

**Verification performed after writing this document:**

- Exactly one new file was created: `docs/phase2d/PHASE_2D_K_SELECTION_ARCHITECTURE_REVIEW.md`.
- `src/boundary_segmentation.py`, `src/boundary_segmentation_adapter.py`,
  `tests/test_boundary_segmentation.py`,
  `tests/test_boundary_segmentation_adapter.py`, and
  `tests/test_shadow_mode_comparison.py` re-checksummed as unchanged from
  their previously accepted values.
- `pytest tests/ -q` → 531 passed, 30 subtests passed (unchanged from
  baseline).
- `src.boundary_segmentation_adapter` remains unimported by any file
  under `src/` other than its own module (confirmed by direct grep).
- This repository has no `.git` directory; checksums and a recent-file-
  modification-time scan were used in place of a git diff, consistent
  with every prior round's approach.
