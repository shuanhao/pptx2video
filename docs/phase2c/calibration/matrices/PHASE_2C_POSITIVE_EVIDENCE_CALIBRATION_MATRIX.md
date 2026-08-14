# Phase 2C Positive Evidence Calibration Matrix

**Status:** Calibration Matrix Design — no calibration experiment executed
**Phase:** Phase 2C — Numeric Calibration (Positive Evidence)
**Purpose:** Design the calibration matrix needed to evaluate whether the current
Positive Evidence magnitudes (`CJK → LATIN +15`, `LATIN → CJK +15`, `Whitespace +10`)
are appropriate on top of the now-locked Base Classification layer, without changing
any value and without running the experiment.

This document is a **design artifact only**. No calibration script was run, no
existing artifact was modified, and no numeric conclusion is drawn here.

---

## 1. Purpose

`docs/PHASE_2C_NUMERIC_BASELINE_DECISION.md` adopted the current Positive Evidence
scores (`CJK → LATIN +15`, `LATIN → CJK +15`, `Whitespace +10`) as a provisional
baseline, not yet the subject of a dedicated calibration round. Base Classification
Dominance was subsequently evaluated in
`docs/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_ROUND1_REPORT.md`, which recorded
`KEEP` for all three base-classification margins (`CLAUSE - OTHER = 35`,
`ELLIPSIS - CLAUSE = 30`, `SENTENCE_FINAL - ELLIPSIS = 15`). This matrix defines the
calibration cases a later execution round will need to evaluate whether Positive
Evidence provides appropriate *relative* preference on top of that now-established
base layer — not to re-litigate the base scores themselves, which are treated as
fixed inputs throughout this document.

**Note on a naming discrepancy in this round's own instructions.** This round's
instructions repeatedly reference `docs/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_DECISION.md`
as an existing, authoritative file that "locks" the base classification values.
Repository inspection confirms **no file by that name exists**. The two real,
existing artifacts covering this ground are `docs/PHASE_2C_NUMERIC_BASELINE_DECISION.md`
(which adopted `SENTENCE_FINAL=+80`/`ELLIPSIS=+65`/`CLAUSE=+35`/`OTHER=0` as the
*provisional* baseline, explicitly not yet calibrated at the time) and
`docs/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_ROUND1_REPORT.md` (which subsequently
recorded `KEEP` for all three margins between those same values, based on real-pipeline
evidence). Numerically, the values this round asks to be treated as "locked" are
identical to the values those two real documents already establish, so this
discrepancy does not block this round's work — the same four numbers
(`+80`/`+65`/`+35`/`0`) are used below exactly as this round's instructions specify.
This note records the naming discrepancy factually, per the established practice of
not silently substituting or fabricating a referenced-but-missing artifact (see
`docs/PHASE_2C_NUMERIC_BASELINE_DECISION.md` §11 for the precedent — the
`CLAUSE=+20`/`ELLIPSIS=+40` prompt-level discrepancy was handled the same way). No
file named `PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_DECISION.md` is created by this
round — this round is scoped to create exactly one file, the matrix named in its own
title.

## 2. Authoritative Baseline

### 2.1 Locked Base Classification

Per `docs/PHASE_2C_NUMERIC_BASELINE_DECISION.md` §4.1 and
`docs/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_ROUND1_REPORT.md` §9 (all three
margins: `KEEP`):

| BoundaryClass | Score | Status |
|---|---:|---|
| `SENTENCE_FINAL` | +80 | LOCKED |
| `ELLIPSIS` | +65 | LOCKED |
| `CLAUSE` | +35 | LOCKED |
| `OTHER` | 0 | LOCKED |

These four values are **fixed inputs** throughout this document. No case in this
matrix is designed to ask whether any of them should change. If a case's observation
later appears to suggest a base-classification value is too weak or too strong, that
observation is recorded as `OUT OF CURRENT SCOPE` (§17) and not acted upon here — the
question is closed for this round.

### 2.2 Provisional Positive Evidence

| Factor | Current Value | Status |
|---|---:|---|
| CJK → LATIN | +15 | PROVISIONAL |
| LATIN → CJK | +15 | PROVISIONAL |
| Whitespace | +10 | PROVISIONAL |

These three values are what this matrix is designed to gather evidence about. No
value above is modified by this document — it only designs cases; it does not execute
them and does not propose a replacement number for anything.

## 3. Calibration Scope

This matrix covers exactly three Positive Evidence factors, applied on top of the
locked base layer:

- **A. CJK → LATIN transition** (+15)
- **B. LATIN → CJK transition** (+15)
- **C. Whitespace** (+10)

And the calibration questions from this round's own objective:

1. Is CJK → LATIN +15 appropriate?
2. Is LATIN → CJK +15 appropriate?
3. Is the symmetry CJK → LATIN = LATIN → CJK appropriate (evidence-supported, not
   merely "same current number")?
4. Is Whitespace +10 appropriate?
5. Does Positive Evidence remain appropriately proportioned when combined with
   different Base Classification values?
6. Does Whitespace interact with Transition evidence in a reasonable way?
7. Are there cases where Positive Evidence becomes disproportionately strong relative
   to Base Classification?

None of these questions is answered in this document. Only the calibration cases
needed to answer them later are designed here.

## 4. Out of Scope

- **Base Classification** (`SENTENCE_FINAL`, `ELLIPSIS`, `CLAUSE`, `OTHER`) — locked,
  per §2.1. Treated as a fixed input; never re-evaluated by any case below.
- **Protection** (`Technical -30`, `Atomic -30`, `INTERNAL -20`) — already the subject
  of the completed Protection Calibration and Post-Correction Verification; not
  recalibrated here. Realistic text may contain Technical/Atomic evidence
  incidentally (especially in the Technical/Product Terminology group, §13); where it
  appears, it is recorded and the case is classified `CONTAMINATED` or `NEEDS DATA`
  as appropriate — never silently subtracted, and the protection value itself is
  never adjusted to compensate.
- **No new scoring factor.** Specifically excluded: semantic importance, word
  frequency, word length, emoji weighting, emoticon weighting, capitalization, syntax
  weighting, speaker-intent weighting, sentence-length weighting, paragraph position
  weighting. If a case's observation suggests one of these might matter, it is
  recorded as a `FUTURE DESIGN QUESTION` (§17) and not added to the scoring model.
- **Emoji / emoticon** — no dedicated cases. If present incidentally in a natural
  PPT-note case, excluded from the calibration interpretation rather than given
  special treatment.
- **Threshold / normalization / class-specific hard floor** — none introduced. Phase
  2C remains a signed relative score with no threshold, no normalization, no
  class-specific hard floor.
- Production code, tests, existing calibration scripts/matrices/reports, the Numeric
  Baseline Decision, the Base Classification Calibration Matrix and Round 1 Report,
  Phase 2D, `subtitle_segmenter.py`.

## 5. Calibration Method

A later execution round must:

1. Run each case's input text through the real, unmodified pipeline
   (`analyze_text_structure` → `observe_boundaries` → `classify_boundary` →
   Positive Evidence observation), exactly as every prior calibration script has
   done — no re-parsing, no synthetic `BoundaryClass`/evidence substitution, no
   manually assigning transition or whitespace evidence to a candidate.
2. Locate the real candidate(s) matching each case's "Target boundary" description
   and record the actual observed class, base score, transition modifier, whitespace
   modifier, and any protection modifier that also applies — exactly as the existing
   `dump()`-style calibration output already does.
3. Compare observed values against each case's calibration question and record
   `KEEP` / `INCREASE` / `DECREASE` / `NEED MORE DATA` (§19) — never a fixed numeric
   replacement.
4. Where a target candidate is unreachable, string-final, or otherwise not
   representable by the current pipeline, mark it `CASE ISSUE` (§17) rather than
   forcing a synthetic substitute or modifying the input until it "works."
5. Synthetic fixtures (hand-built `BoundaryCandidate`/`BoundaryFeatures`) may be used
   only for arithmetic sanity checks (e.g. confirming `15 + 10 = 25` computes
   correctly given two known modifiers) — never presented as calibration evidence for
   whether a combination is contextually appropriate.

This document performs none of these steps. It only specifies what a later round
must do.

### 5.1 Existing Evidence Inventory

Per this round's instruction to distinguish previously-observed evidence from newly
designed cases, the following findings are already present in the repository and are
**not** re-derived as new cases below, though several new cases in §7–§16 are
deliberately designed to test whether they replicate under independent text:

| ID | Source | Finding | Status |
|---|---|---|---|
| EE-1 | `docs/PHASE_2C_CALIBRATION_ROUND1_REPORT.md` C09/C10 | No-space CJK→LATIN (`中文｜English`) and LATIN→CJK (`English｜中文`) each produce a clean `OTHER`+transition candidate scoring exactly `15.0` | EXISTING EVIDENCE |
| EE-2 | `docs/PHASE_2C_CALIBRATION_ROUND2_REPORT.md` A04/C03 | Same no-space transition finding, independently reproduced; symmetric CJK→LATIN/LATIN→CJK values confirmed equal in the cases where both were reachable | EXISTING EVIDENCE |
| EE-3 | `docs/PHASE_2C_CALIBRATION_ROUND2_REPORT.md` Group C (C01/C02) | Naturally-written CJK/Latin text almost always has a **space** at the language switch point (standard Chinese typographic convention); when a space is present, the pure transition candidate does not occur — the boundary splits into two whitespace-only candidates instead | EXISTING EVIDENCE |
| EE-4 | `docs/PHASE_2C_CALIBRATION_ROUND2_REPORT.md` Group D (D01–D03) | Whitespace evidence is split across two separate candidates (one on each side of the space character), never combined onto one candidate; multiple consecutive whitespace characters do not stack the bonus — always exactly `+10` per boundary | EXISTING EVIDENCE |
| EE-5 | `docs/PHASE_2C_CALIBRATION_ROUND2_REPORT.md` D04 | The no-space transition candidate (`15.0`) outscores the whitespace-adjacent variant of the same underlying language switch (`10.0`) — adding a space does not "enrich" a transition boundary into a stronger `25`-point candidate, it *replaces* it with a weaker whitespace-only one elsewhere. One of the two most important ranking findings from Round 2. | EXISTING EVIDENCE |
| EE-6 | `docs/PHASE_2C_CALIBRATION_ROUND1_REPORT.md` C14/C27/C28 | `CLAUSE` and language-transition evidence are mutually exclusive on a single real candidate: the `CLAUSE` candidate's left character is always the clause-punctuation mark itself (`CharacterClass.PUNCTUATION`), never `CJK`/`LATIN`, so the transition rule's precondition (both sides being letter-class, one CJK one LATIN) can never fire on a `CLAUSE` candidate. Confirmed at three independent positions across Round 1 (C14, C27, C32 pos13). Whitespace, by contrast, **does** co-occur with `CLAUSE` — C14 observed `CLAUSE`+whitespace = `35+10=45.0` | EXISTING EVIDENCE |
| EE-7 | `docs/PHASE_2C_CALIBRATION_ROUND2_REPORT.md` E01/E02/E04 | Technical/Atomic-protected content (e.g. `1,000`, `v1.2.3`) never coincides with a `CLAUSE` candidate in the cases observed (the actual clause punctuation in those sentences sits outside the protected span); a transition-only candidate (`15.0`) outranks a technical-protected candidate (`-30.0`/`-60.0`) in the intended direction — not flagged as a reversal | EXISTING EVIDENCE |
| EE-8 | `docs/PHASE_2C_CALIBRATION_ROUND2_REPORT.md` §9 finding 4 | Embedded markdown line-wraps inside a case's own source text can incidentally act as whitespace, an artifact of how the case text itself was authored rather than of the pipeline — a caution for how new case text is written, not a pipeline finding | EXISTING EVIDENCE |

EE-6 in particular directly informs §12 below: because the mechanism it documents
(punctuation-anchored candidates cannot carry transition evidence) is structural —
grounded in `CharacterClass` assignment, not particular to the specific sentences
C14/C27/C28 used — the same reasoning predicts that `ELLIPSIS` and `SENTENCE_FINAL`
candidates (which are likewise anchored with a `PUNCTUATION`-class character on one
side) will show the same mutual exclusivity with Transition evidence. §12 designs
cases to test this prediction directly rather than simply asserting it holds by
analogy — a "structural prediction from an existing finding" is not the same as
"already-observed evidence for a different class," and this document does not
conflate the two.

## 6. Evidence Quality Model

Each case in §7–§16 is assigned one of six statuses. The full definitions are
authoritative in §17; this section previews them so the case tables below are
readable without forward-referencing:

- **CLEAN** — the intended positive factor is isolated sufficiently for calibration.
- **INTERACTION** — the case intentionally studies a combination of factors.
- **CONTAMINATED** — an unintended factor materially affects interpretation.
- **CASE ISSUE** — the intended candidate cannot be represented or reached by the
  current pipeline.
- **NEEDS DATA** — evidence is insufficient for a meaningful calibration judgment.
- **ANALYSIS ONLY** — useful diagnostic observation, not sufficient alone to support
  a numeric decision.

No case below is pre-assigned a final status by this design round beyond a
*predicted* status, drawn from the existing evidence in §5.1 where applicable. Every
predicted status is written as a prediction to be confirmed or refuted by real
execution, never as a foregone conclusion.

## 7. CJK → LATIN Calibration (PE-01)

Clean, no-space individual-evidence cases isolating the CJK→LATIN transition bonus
on an otherwise plain `OTHER` candidate, drawn from realistic PPT-note phrasing about
software tools (a natural place for embedded English terms to appear with no space,
per Chinese technical-writing convention for short tool/product names used as
objects).

Shared fields for all PE-01 cases (not repeated per case): **Expected BoundaryClass**
= `OTHER`; **Base Classification score** = `0.0` (fixed input, per §2.1); **Expected
positive evidence** = `CJK → LATIN`, `+15`; **Evidence requirement** = real pipeline,
no whitespace between the CJK and Latin characters at the target position;
**Clean/interaction criteria** = CLEAN if the target candidate carries no whitespace
or protection modifier alongside the transition; **Interpretation criteria** = per
§19.

| Case ID | Purpose | Input text | Target boundary | Comparison candidate | Calibration question | Predicted status |
|---|---|---|---|---|---|---|
| PE-01-01 | Tool name embedded directly after a verb, no space (natural short-tool-name convention) | `這個功能使用Python處理資料。` | `用｜P` (last CJK char of `使用`, first Latin char of `Python`) | vs. plain interior `OTHER` elsewhere in the same text (e.g. `這｜個`, `0.0`) | Does `+15` read as an appropriate increment over plain `OTHER` for this realistic no-space transition? | CLEAN |
| PE-01-02 | Different tool name, different verb, independent sentence | `我們用Excel做報表，很方便。` | `用｜E` | vs. plain interior `OTHER` in the same text | Same as PE-01-01, independent case | CLEAN |
| PE-01-03 | Third tool name, distinct phrasing (`採用` instead of `用`) | `系統採用Docker部署服務。` | `用｜D` | vs. plain interior `OTHER` in the same text | Same as PE-01-01, independent case | CLEAN |

## 8. LATIN → CJK Calibration (PE-02)

Mirror of §7 in the opposite direction — the Latin tool name is immediately followed
by CJK continuation text, no space.

Shared fields: **Expected BoundaryClass** = `OTHER`; **Base Classification score** =
`0.0`; **Expected positive evidence** = `LATIN → CJK`, `+15`; **Evidence
requirement** = real pipeline, no whitespace at the target position; other fields as
in §7.

| Case ID | Purpose | Input text | Target boundary | Comparison candidate | Calibration question | Predicted status |
|---|---|---|---|---|---|---|
| PE-02-01 | Tool name as sentence subject, immediately followed by CJK verb, no space | `Python可以處理資料。` | `n｜可` (last Latin char, first CJK char) | vs. plain interior `OTHER` in the same text | Does `+15` read as an appropriate increment over plain `OTHER` for this realistic no-space transition, in the reverse direction from §7? | CLEAN |
| PE-02-02 | Different tool name, different continuation verb | `Excel能做報表，很方便。` | `l｜能` | vs. plain interior `OTHER` in the same text | Same as PE-02-01, independent case | CLEAN |
| PE-02-03 | Third tool name | `Docker能部署服務。` | `r｜能` | vs. plain interior `OTHER` in the same text | Same as PE-02-01, independent case | CLEAN |

## 9. Transition Symmetry Calibration (PE-03)

Per this round's explicit instruction, symmetry is **not** assumed merely because the
current baseline uses equal values (`+15` = `+15`). These cases place both directions
inside the **same sentence**, in comparable surrounding context (a Latin word
sandwiched between CJK text on both sides, no spaces on either side), so the two
transition candidates can be compared directly from one real-pipeline run rather than
across two separately-constructed texts. This is a stronger symmetry test than §7/§8
individually, because both directions share the identical sentence-level context.

Shared fields: **Base Classification score** = `0.0` for both target candidates;
**Expected positive evidence** = `CJK → LATIN, +15` for the first target, `LATIN →
CJK, +15` for the second target; **Evidence requirement** = real pipeline, both
candidates from the same input text, no whitespace on either side of the embedded
Latin word; **Calibration question** (shared) = does the same `+15` contribution
hold for both directions when observed in the same sentence, or does the real
pipeline's evidence (not merely the shared baseline number) support treating them as
genuinely symmetric?

| Case ID | Purpose | Input text | Target A (CJK→LATIN) | Target B (LATIN→CJK) | Predicted status |
|---|---|---|---|---|---|
| PE-03-01 | Latin word sandwiched between CJK on both sides, no spaces | `這是Python語言。` | `是｜P` | `n｜語` | CLEAN |
| PE-03-02 | Different sandwiched word, different sentence | `我們用Docker部署。` | `用｜D` | `r｜部` | CLEAN |
| PE-03-03 | Acronym sandwiched between CJK on both sides | `系統採用API接口。` | `用｜A` | `I｜接` | CLEAN |

**Symmetry interpretation note (to guide, not pre-decide, the later round):** if
PE-03-01 through PE-03-03 all show both targets scoring exactly `15.0` with no
incidental modifier difference between A and B, that is evidence *for* symmetry being
behaviorally supported, not merely numerically coincidental. If any case shows a
material difference between A and B (e.g. one side picking up an incidental
whitespace or protection modifier the other side does not), that is evidence the
"same numeric baseline" and "evidence supports symmetry" statements are not
interchangeable, exactly as this round's instructions caution.

## 10. Whitespace Calibration (PE-05)

Clean, isolated whitespace cases covering all four character-class combinations
around a single space character, distinguishing whitespace evidence from its
absence. Per EE-3/EE-4, a single space is expected to split into two separate
whitespace-only candidates (one on each side), neither carrying transition evidence
even where a CJK/Latin switch also occurs across the space — these cases are designed
to confirm or refute that expectation independently of the specific texts already
used in Round 2.

Shared fields: **Expected BoundaryClass** = `OTHER` for all four; **Base
Classification score** = `0.0`; **Expected positive evidence** = `Whitespace, +10`
per candidate (both candidates around the space, per EE-4); **Evidence requirement**
= real pipeline, exactly one space character at the target position; **Calibration
question** (shared) = does `+10` provide an appropriate, consistently-applied
increment for whitespace-adjacency regardless of which character classes border the
space?

| Case ID | Purpose | Input text | Target boundary | Comparison | Predicted status |
|---|---|---|---|---|---|
| PE-05-01 | CJK + whitespace + CJK | `這個 功能很好用。` | both candidates around the inserted space (`個｜(sp)`, `(sp)｜功`) | vs. plain CJK-CJK `OTHER` elsewhere in the same text (`0.0`) | CLEAN |
| PE-05-02 | CJK + whitespace + Latin (natural typographic convention) | `我們使用 Python處理資料。` | both candidates around the space between `用` and `Python` | vs. PE-01-01's no-space transition candidate (`15.0`) — cross-referenced, not re-derived | CLEAN, also feeds §11 |
| PE-05-03 | Latin + whitespace + CJK (natural typographic convention) | `使用Python 處理資料。` | both candidates around the space between `Python` and `處` | vs. PE-02-01's no-space transition candidate (`15.0`) — cross-referenced | CLEAN, also feeds §11 |
| PE-05-04 | Latin + whitespace + Latin | `我們設定 API Key 之後就完成了。` | both candidates around the space between `API` and `Key` | vs. plain Latin-Latin `OTHER` elsewhere in the same text (e.g. within `API` itself, `0.0`) | CLEAN |

## 11. Transition + Whitespace Interaction (PE-07)

Matched triads for both transition directions: transition-only (no space),
whitespace-only (space present, per EE-3/EE-5 no pure transition candidate is
expected), and an explicit attempted "transition + whitespace" case included per this
round's requirement even though EE-5 already predicts it is structurally
unreachable as a single `+25` candidate — the later execution round must confirm
this prediction on independent text rather than rely solely on the Round 2 finding.

| Case ID | Purpose | Input text | Target boundary | Expected/predicted evidence | Predicted status |
|---|---|---|---|---|---|
| PE-07-01a | CJK→LATIN, transition-only (no space) | `我們使用Python分析資料。` | `用｜P` | `OTHER`, `+15` transition, no whitespace | CLEAN |
| PE-07-01b | Same underlying phrase, whitespace inserted at the switch point | `我們使用 Python分析資料。` | both candidates around the inserted space | `OTHER`+`Whitespace(+10)` each side, per EE-3/EE-4; predicted **no** transition evidence on either candidate | CLEAN, tests EE-5's prediction |
| PE-07-01c | Attempted "transition + whitespace" on the same underlying switch | same text as PE-07-01b — no separate text is constructable, since inserting a space is definitionally what produces PE-07-01b instead of PE-07-01a | n/a — this row records the **absence** of a third variant rather than a third input text | Predicted unreachable as a single candidate carrying both `+15` and `+10` simultaneously (`= +25`), per EE-5 | Predicted **CASE ISSUE** (structural: whitespace and no-space transition are mutually exclusive conditions on the same boundary by construction, not merely by current pipeline limitation) |
| PE-07-02a | LATIN→CJK, transition-only (no space) | `Python分析資料很快。` | `n｜分` | `OTHER`, `+15` transition, no whitespace | CLEAN |
| PE-07-02b | Same underlying phrase, whitespace inserted | `Python 分析資料很快。` | both candidates around the inserted space | `OTHER`+`Whitespace(+10)` each side; predicted no transition evidence | CLEAN, tests EE-5's prediction |
| PE-07-02c | Attempted "transition + whitespace" | same construction issue as PE-07-01c, opposite direction | n/a | Predicted unreachable, same reasoning as PE-07-01c | Predicted **CASE ISSUE** |

**Hierarchy question this group feeds (not answered here):** whether the resulting
practical hierarchy — no-space transition (`15`) vs. whitespace-adjacent (`10`) vs.
the arithmetically-implied-but-structurally-unreachable additive combination (`25`)
— is a reasonable outcome for Phase 2D to work with, given that the `25` case never
actually occurs. This round only stages the cases; it does not decide whether that
absence is itself acceptable or whether it points to a future interaction-rule
question for Phase 2D (which is out of scope for Phase 2C calibration).

## 12. Base Classification × Positive Evidence (PE-04, PE-06)

Two subgroups: Transition attached to each of the four locked base classes (PE-04),
and Whitespace attached to each of the four locked base classes (PE-06). The purpose
is **not** to recalibrate `SENTENCE_FINAL`/`ELLIPSIS`/`CLAUSE`/`OTHER` — it is to
determine whether the Positive Evidence contribution is appropriately scaled relative
to the locked base hierarchy once actually combined with it. Per §5.1/EE-6, prior
evidence already predicts that Transition cannot co-occur with `CLAUSE` on a single
real candidate; the same structural reasoning is extended here as a prediction (not
an assumption) for `ELLIPSIS` and `SENTENCE_FINAL`, and each case below is still
designed as a real, executable case rather than skipped, so the later round can
confirm or refute the prediction directly.

### 12.1 PE-04 — Transition attached to Base Classification

| Case ID | Purpose | Input text | Target boundary | Arithmetic if reachable | Calibration question | Predicted status |
|---|---|---|---|---|---|---|
| PE-04-OTHER | `OTHER` + Transition | Cross-referenced from §7/§8/§9 (e.g. PE-01-01) — not a new case | `用｜P` | `0 + 15 = 15` | Is `15` (`OTHER`+Transition) an appropriately modest elevation above plain `OTHER` (`0`), well below `CLAUSE` (`35`)? | CLEAN (reused) |
| PE-04-CLAUSE | `CLAUSE` + Transition (attempted) | `這個功能，Python處理資料。` | `，｜P` (clause comma immediately followed, no space, by the Latin word) | `35 + 15 = 50` if reachable | Does the real pipeline ever produce a candidate that is simultaneously `CLAUSE` and transition-evidenced? | Predicted **CASE ISSUE**, per EE-6 (clause candidate's left character is `PUNCTUATION`, never `CJK`/`LATIN`) — to be confirmed, not assumed |
| PE-04-ELLIPSIS | `ELLIPSIS` + Transition (attempted) | `我們稍後說明……Python範例會展示。` | `…｜P` (ellipsis run's END-state position immediately followed, no space, by the Latin word) | `65 + 15 = 80` if reachable | Does the real pipeline ever produce a candidate that is simultaneously `ELLIPSIS` (END-state) and transition-evidenced? | Predicted **CASE ISSUE**, by the same structural reasoning as EE-6 (the END-state candidate's left character is the ellipsis mark itself, `PUNCTUATION`) — to be confirmed |
| PE-04-SENTENCE_FINAL | `SENTENCE_FINAL` + Transition (attempted) | `這是重點。Python範例如下：` | `。｜P` (sentence-final mark immediately followed, no space, by the Latin word) | `80 + 15 = 95` if reachable | Does the real pipeline ever produce a candidate that is simultaneously `SENTENCE_FINAL` and transition-evidenced? | Predicted **CASE ISSUE**, by the same structural reasoning as EE-6 (the SF candidate's left character is the sentence-final mark itself, `PUNCTUATION`) — to be confirmed |

**If all three `CASE ISSUE` predictions are confirmed**, the practical conclusion for
a later round to state (not this one) would be that "Transition attached to
`CLAUSE`/`ELLIPSIS`/`SENTENCE_FINAL`" is not a real-pipeline-representable scenario
at all under the current architecture, and the arithmetic values in the table above
(`50`/`80`/`95`) are never-occurring hypotheticals rather than calibration targets —
mirroring exactly how Round 1's C27/C28 treated the equivalent `CLAUSE`+transition
case ("not evaluable"). This document does not draw that conclusion; it stages the
cases needed to reach it.

### 12.2 PE-06 — Whitespace attached to Base Classification

Unlike Transition, EE-6 already shows Whitespace **does** co-occur with `CLAUSE`
(C14: `35+10=45.0`), because the whitespace check does not appear to share the same
CJK/LATIN character-class precondition as the transition check. These cases test
whether that holds independently on new text, and whether it extends to `ELLIPSIS`
and `SENTENCE_FINAL` as well — this is a genuinely open question, not a predicted
`CASE ISSUE` the way §12.1 is.

| Case ID | Purpose | Input text | Target boundary | Arithmetic if reachable | Calibration question | Predicted status |
|---|---|---|---|---|---|---|
| PE-06-OTHER | `OTHER` + Whitespace | Cross-referenced from §10 (e.g. PE-05-01) — not a new case | `個｜(sp)` | `0 + 10 = 10` | Is `10` an appropriately modest elevation above plain `OTHER`? | CLEAN (reused) |
| PE-06-CLAUSE | `CLAUSE` + Whitespace | `接下來， 我們介紹重點。` (space immediately after the clause comma) | `，｜(sp)` | `35 + 10 = 45` | Independent confirmation of EE-6/C14's finding: does `CLAUSE`+Whitespace consistently score `45.0`? Does `+10` read as an appropriate additional increment on top of the much larger `CLAUSE` base? | Predicted CLEAN / reachable, per EE-6 — to be confirmed independently |
| PE-06-ELLIPSIS | `ELLIPSIS` + Whitespace | `我們稍後再談…… 好，開始吧。` (space immediately after the ellipsis run's END position) | `…｜(sp)` | `65 + 10 = 75` if reachable | Does an `ELLIPSIS` END-state candidate carry whitespace evidence the same way `CLAUSE` does? | Genuinely open — no existing evidence either way; not predicted `CASE ISSUE` unlike §12.1's ellipsis row, since whitespace's precondition (unlike transition's) is not known to require non-`PUNCTUATION` character classes |
| PE-06-SENTENCE_FINAL | `SENTENCE_FINAL` + Whitespace | `這是重點。 接下來介紹範例。` (space immediately after the sentence-final mark) | `。｜(sp)` | `80 + 10 = 90` if reachable | Does a `SENTENCE_FINAL` candidate carry whitespace evidence the same way `CLAUSE` does? | Genuinely open, same reasoning as PE-06-ELLIPSIS |

## 13. Technical / Product Terminology (PE-09)

Realistic cases containing product names and acronyms, deliberately split between
text that stays clean (no digits/symbols that would trigger `Technical`/`Atomic`
protection) and text that incidentally contains such spans, so the later round can
distinguish genuine Positive Evidence readings from protection-contaminated ones
without silently discarding the contamination.

| Case ID | Purpose | Input text | Target boundary | Expected class/evidence | Calibration question | Predicted status |
|---|---|---|---|---|---|---|
| PE-09-01 | Clean brand name, no digits/symbols | `這個簡報使用PowerPoint製作。` | `用｜P` | `OTHER`, `+15` CJK→LATIN, no protection | Does a realistic, recognizable product name (not a generic placeholder like "Python"/"Excel") produce the same clean `+15` reading? | CLEAN |
| PE-09-02 | Acronym, no digits/symbols | `這個系統使用API串接資料。` | `用｜A` | `OTHER`, `+15` CJK→LATIN, no protection | Same question for an acronym rather than a full word | CLEAN |
| PE-09-03 | Product name with embedded version number (digits present) | `我們目前使用iPhone 15進行測試。` | boundary(ies) around/within `15` and at the CJK/Latin switch points | Predicted: digits trigger `Technical`/`Atomic` protection on the number itself; the `使用｜iPhone` switch (with a space, per natural convention) is expected to be whitespace-only per EE-3, not transition | Does the incidental digit/protection evidence materially affect interpretation of the nearby transition/whitespace candidates, or are they cleanly separable positions? | Predicted **CONTAMINATED** for candidates inside/adjacent to `15`; predicted CLEAN for the CJK↔`iPhone` switch itself — to be confirmed, not assumed, since the exact span boundaries of the digit protection are a Phase 1/2A matter this round does not re-derive |
| PE-09-04 | Version-string-style product identifier | `系統版本是v1.2.3，請確認。` | boundaries within `v1.2.3` and at the clause comma after it | Predicted, per EE-7 (E02): interior positions show `Technical`+`Atomic` interaction (strongest-only per the Numeric Baseline Decision), some via the ASCII-period bare-fallback correction now fixed upstream; the clause comma itself is predicted to sit outside the protected span, per EE-7 | Does this case's clause comma remain a clean, unprotected `CLAUSE` candidate exactly as E01/E02 found, on independently-written text? | Predicted **CONTAMINATED** for the interior version-string positions; predicted CLEAN for the clause comma — cross-checks EE-7 on new text rather than reusing E01/E02's own text |
| PE-09-05 | Acronym embedded with a hyphen (potential atomic/technical trigger) | `我們比較GPT-4和其他模型的表現。` | boundaries around `GPT-4` and at its CJK/Latin switch points | Predicted: the hyphenated alphanumeric token may itself be flagged Technical/Atomic per Phase 1's own span rules (not re-derived here); the CJK→Latin switch into `GPT` is a separate, potentially clean candidate | Is the transition evidence at the language-switch boundary interpretable independently of whatever protection evidence appears inside `GPT-4` itself? | Predicted **CONTAMINATED** or **NEEDS DATA** depending on where Phase 1's actual span boundaries fall — this is exactly the kind of case §16 (Contaminated vs. Clean) exists to record honestly rather than force into CLEAN |

## 14. Punctuation Interaction (PE-10)

These cases test Transition/Whitespace evidence **near** (not attached to, per §12's
finding that same-candidate attachment is structurally blocked for punctuation-
anchored classes) clause punctuation, an ellipsis run, and sentence-final
punctuation — i.e., they record the full local candidate neighborhood so a later
round can see whether a nearby high-scoring punctuation-anchored candidate has any
observable effect on an adjacent Positive-Evidence candidate (Phase 2C candidates are
expected, per every prior calibration round, to be computed independently of their
neighbors — these cases are designed to make that independence directly observable
rather than assumed).

| Case ID | Purpose | Input text | Candidates of interest | Calibration question | Predicted status |
|---|---|---|---|---|---|
| PE-10-01 | Transition near clause punctuation | `這個功能，Python可以處理。` | (a) the `，｜P` position itself (per PE-04-CLAUSE, predicted `CLAUSE` only, no transition); (b) the later `n｜可` position (`LATIN→CJK`, predicted `+15`) | Does the nearby `CLAUSE` candidate (a) have any observable effect on the independently-scored transition candidate (b) a few characters later? | ANALYSIS ONLY (records neighborhood independence, does not itself resolve a KEEP/INCREASE/DECREASE question) |
| PE-10-02 | Transition near an ellipsis run | `這個問題我們稍後說明……Python範例如下。` | (a) the END-state `…｜P` position (per PE-04-ELLIPSIS, predicted `ELLIPSIS` only, no transition, since `P` directly abuts the mark); (b) the internal `…｜…` position (`INTERNAL`, `-20`, incidental) | Same neighborhood-independence question, now against `ELLIPSIS`/`INTERNAL` rather than `CLAUSE` | ANALYSIS ONLY |
| PE-10-03 | Transition near sentence-final punctuation | `這是重點。Python範例如下：這是第二個重點。` | (a) the `。｜P` position (per PE-04-SENTENCE_FINAL, predicted `SENTENCE_FINAL` only, no transition); (b) any later transition/whitespace candidate elsewhere in the text | Same neighborhood-independence question, now against `SENTENCE_FINAL` | ANALYSIS ONLY |

## 15. Negative / Non-Useful Whitespace (PE-11)

Cases where whitespace is present for typographic or formatting reasons but should
not automatically be assumed to carry a strong, semantically useful boundary
preference — the goal is not to classify whitespace itself, only to determine whether
its flat `+10` contribution is appropriately calibrated across "useful" and
"not obviously useful" whitespace alike.

| Case ID | Purpose | Input text | Target boundary | Why this whitespace may not be a useful cut signal | Predicted status |
|---|---|---|---|---|---|
| PE-11-01 | Space inside a two-word English product name, itself embedded in a CJK sentence | `我們使用 Microsoft Word 編輯文件。` | the internal space between `Microsoft` and `Word` (distinct from the CJK↔Latin switch spaces on either side of the whole phrase) | A person writing subtitles would essentially never cut in the middle of a proper-noun product name, yet this space is expected to score the same flat `+10` (per EE-4) as any other whitespace boundary | ANALYSIS ONLY |
| PE-11-02 | Space between a number and a CJK measure word (standard typographic convention, not a phrase break) | `這個功能將於2026年上線。` vs. a variant with a space: `這個功能將於 2026 年上線。` | the spaces around `2026` | Typographic convention in some style guides inserts a space between digits and CJK text; this is a formatting habit, not a semantic pause, yet it would still score `+10` if present | ANALYSIS ONLY |
| PE-11-03 | Trailing/incidental whitespace from how PPT speaker notes are often authored (line-wrap-adjacent spacing) | `這是第一行内容 這是接續的內容，語意上是同一句話。` (a single logical sentence authored with an internal space where a line-wrap might occur in the original notes, per EE-8's caution) | the space in the middle of the logically-continuous sentence | This kind of space reflects how the source document was laid out, not an intended subtitle break — EE-8 already flagged this authoring hazard for Round 2; this case exercises it directly rather than only noting it as a caution | ANALYSIS ONLY |

None of the three cases above is expected to produce a `CASE ISSUE` — the whitespace
candidates themselves are expected to be perfectly reachable and to score `10.0`
exactly per EE-4. The open question these cases raise is qualitative (should every
`+10` whitespace boundary be treated as equally useful for segmentation) rather than
mechanical (can the pipeline produce the candidate) — this is recorded as `ANALYSIS
ONLY` rather than forced into a KEEP/INCREASE/DECREASE verdict on the numeric value
itself, since that is a Phase 2D consumption question at least as much as a Phase 2C
magnitude question.

## 16. Integrated Positive-Evidence Cases

### 16.1 Mixed CJK / Latin PPT Notes (PE-08)

Natural, unengineered presentation-style paragraphs containing multiple realistic
transition and whitespace occurrences, to see how Positive Evidence behaves across a
whole paragraph rather than a constructed minimal pair. Per this round's instruction,
these are not forced into a pairwise KEEP/INCREASE/DECREASE verdict from a single
paragraph.

| Case ID | Purpose | Input text | What it's expected to exercise | Predicted status |
|---|---|---|---|---|
| PE-08-01 | Tool-comparison note mixing several embedded tool names, some with spaces (natural convention) and some without | `這一頁比較兩個工具：Python和R都可以用於資料分析，但是我們team比較熟悉Python。` | multiple CJK↔Latin switches, some spaced (`R都` — actually no space here; deliberately includes both a no-space case `和R` type switch and a spaced case `我們team`) plus a `CLAUSE` at the full-width colon/comma | ANALYSIS ONLY |
| PE-08-02 | Roadmap-style note mixing a product name, an acronym, and normal CJK narrative | `我們計畫下一步導入CI/CD流程，先用GitHub Actions做測試，之後再評估其他方案。` | transition and whitespace evidence coexisting with `CLAUSE` and plain `OTHER`, plus a likely Technical/Atomic-flagged `CI/CD` token (incidental, to be recorded not removed) | ANALYSIS ONLY |

### 16.2 Integrated Positive-Evidence Candidate Set (PE-12)

The highest-value case in this matrix: one realistic paragraph containing all four
locked base classes (`OTHER`, `CLAUSE`, `ELLIPSIS`, `SENTENCE_FINAL`), with several
candidates also carrying Transition and/or Whitespace evidence, mirroring how
`docs/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_MATRIX.md`'s BC-09 served as that
matrix's primary integrated case.

| Field | Value |
|---|---|
| Case ID | PE-12 |
| Purpose | Exercise the complete base hierarchy and both Positive Evidence factors together in one coherent, realistic paragraph — the single most direct test of "does Positive Evidence remain appropriately proportioned when combined with different Base Classification values" (calibration question 5, §3) |
| Input text | `這個功能還在開發中，我們使用Python和Docker做測試……細節之後會公布。接下來會展示 Demo 範例。` |
| Expected candidates (not asserted, only anticipated for design purposes) | `OTHER` (plain CJK-CJK, `0.0`) at multiple positions; `CLAUSE` (`，`, `35.0`) after `中`; `OTHER`+`CJK→LATIN` (`用｜P`, `15.0`) and `OTHER`+`LATIN→CJK` (`n｜和`, `15.0`) and `OTHER`+`CJK→LATIN` again (`和｜D`, `15.0`) and `OTHER`+`LATIN→CJK` again (`r｜做`, `15.0`) across `使用Python和Docker做測試`; `INTERNAL` (`-20.0`, incidental) inside the `……` run; `ELLIPSIS` (END-state, `65.0`) after the ellipsis run; `SENTENCE_FINAL` (`80.0`, expected non-string-final since followed by more text) after `公布。`; `OTHER`+`Whitespace` (`10.0` each side) around the inserted `Demo` in `展示 Demo 範例` |
| Evidence requirement | Real pipeline; full candidate dump recorded, not just the anticipated positions above — per this round's "record the complete candidate set" instruction |
| Clean/interaction criteria | This is explicitly an INTERACTION case, not CLEAN — it deliberately combines multiple factors in one text |
| Interpretation criteria | No single KEEP/INCREASE/DECREASE verdict is forced from this one paragraph (matching how BC-09/BC-12 were treated in the Base Classification round); instead, the later round should report whether the joint picture — four base classes plus two Positive Evidence factors, all in proportion to each other — looks like a coherent, usable signal for a hypothetical Phase 2D consumer, and should flag any surprising interaction (e.g. an unexpected reversal) explicitly rather than silently |
| Status | ANALYSIS ONLY (primary integrated diagnostic case, corroborates but does not replace §7–§14's pairwise/matched findings) |

## 17. Case Status Rules

Each case in this matrix is assigned exactly one status from the following six,
matching this round's required definitions:

- **CLEAN** — the intended positive factor is isolated sufficiently for calibration
  (no unintended modifier materially affects the target candidate's interpretation).
- **INTERACTION** — the case intentionally tests a combination of evidence factors
  (e.g. PE-07's whitespace+transition triads, PE-12's full integrated set). An
  INTERACTION case is not a failure state — it is a deliberately designed case type,
  distinct from CLEAN by purpose, not by quality.
- **CONTAMINATED** — an unintended factor (most commonly incidental
  Technical/Atomic protection, per §13) materially affects interpretation of the
  intended comparison. Recorded explicitly, with the incidental evidence stated in
  full; the case is retained (not discarded) and an explanation of why it does or
  does not still support a conclusion is required.
- **CASE ISSUE** — the intended candidate cannot be represented or reached by the
  current pipeline (e.g. §12.1's predicted `CLAUSE`/`ELLIPSIS`/`SENTENCE_FINAL` +
  Transition cases, and PE-07's predicted-unreachable "transition + whitespace"
  variant). The input text must not be modified repeatedly to try to force
  reachability.
- **NEEDS DATA** — evidence is insufficient to make a meaningful calibration
  judgment, whether because contamination prevents isolation (and the case cannot be
  meaningfully interpreted even with the contamination recorded) or because too few
  independent cases exist for the specific question asked.
- **ANALYSIS ONLY** — a useful diagnostic observation (most of §14's neighborhood
  cases, §15's negative-whitespace cases, §16's natural/integrated cases), but not by
  itself sufficient to support a numeric KEEP/INCREASE/DECREASE decision. A single
  ANALYSIS ONLY case must never be used, alone, to justify a numeric conclusion.

A CLEAN case and an INTERACTION case are never conflated: this matrix does not mix
"isolate the factor as much as possible" cases with "deliberately combine factors"
cases inside the same case ID. Where both are useful for the same underlying
question (e.g. §11's transition-only vs. whitespace-only vs. transition+whitespace
triads), they are given separate case IDs (PE-07-01a/b/c) rather than one case
serving both purposes.

Every status shown in the case tables above (§7–§16) is a **prediction**, drawn
either from existing evidence (§5.1) or from structural reasoning extended from that
evidence, explicitly labeled as such. No status is asserted as a final, executed
result — that is the job of the later execution round.

## 18. Required Evidence

Each case in §7–§16 defines, either per-case or via an explicitly stated group-level
default that applies uniformly to every case in that group (noted at the top of each
section, per this round's data-model requirement):

- **Case ID**
- **Purpose**
- **Input text**
- **Target boundary**
- **Expected BoundaryClass**
- **Expected positive evidence**
- **Comparison candidate**
- **Current baseline contribution** (the arithmetic value implied by the current
  provisional baseline, e.g. `0+15=15`, `35+10=45` — an arithmetic consequence to be
  checked, never a proposed new value)
- **Base Classification score** (the fixed, locked input from §2.1)
- **Calibration question**
- **Evidence requirements**
- **Clean / interaction criteria**
- **Interpretation criteria**
- **Predicted status** (§17)

A later execution round must additionally record, for every actually-executed case
(per the "avoid false isolation" instruction): any Technical, Atomic, INTERNAL,
transition, or whitespace evidence present on the target candidate that was not the
one being intentionally tested, exactly as `docs/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_ROUND1_REPORT.md`
§8 did for incidental `INTERNAL` evidence in that round. Nothing is silently dropped.

## 19. Calibration Interpretation

A later execution round records exactly one of the following for each numeric
question this matrix feeds (never a specific replacement number):

- **KEEP** — the current value appears appropriately calibrated based on the
  gathered evidence.
- **INCREASE** — the evidence suggests the current value is too weak relative to
  what it is being compared against.
- **DECREASE** — the evidence suggests the current value is too strong relative to
  what it is being compared against.
- **NEED MORE DATA** — the evidence gathered is insufficient to support any of the
  above three verdicts.

**BAD** (not permitted in a later round, illustrating the distinction this document
must preserve): *"Change CJK → LATIN from +15 to +20."* *"Whitespace should become
+5."* *"LATIN → CJK should become +10."*

**GOOD**: *"CJK → LATIN's +15 appears proportionate relative to plain OTHER and well
below CLAUSE, based on PE-01/PE-03/PE-09 → KEEP."* *"The Transition+Whitespace
interaction never actually produces an additive +25 candidate (PE-07) → this is
recorded as a structural finding, not evaluated as KEEP/INCREASE/DECREASE, since
there is no such candidate to calibrate."*

If a case's observation seems to suggest a base-classification value (not a Positive
Evidence value) is miscalibrated — for example, if PE-06-CLAUSE's `45.0` seems to
crowd too closely against `ELLIPSIS`'s `65.0` — that observation is recorded as **OUT
OF CURRENT SCOPE**, explicitly attributed to the base layer, and not acted upon here.
It belongs to a future, separately-scoped Base Classification round, not to Positive
Evidence Calibration.

## 20. Completion Criteria

This matrix is complete when the following are all true:

1. CJK → LATIN is covered by multiple realistic cases. ✓ §7 (PE-01-01–03), plus
   §9/§11/§13 additional independent occurrences.
2. LATIN → CJK is covered by multiple realistic cases. ✓ §8 (PE-02-01–03), plus
   §9/§11/§13.
3. Transition symmetry has matched cases. ✓ §9 (PE-03-01–03), same-sentence matched
   pairs.
4. Whitespace has isolated cases. ✓ §10 (PE-05-01–04), all four character-class
   combinations.
5. Whitespace has realistic non-useful cases. ✓ §15 (PE-11-01–03).
6. Transition + Whitespace interaction is covered. ✓ §11 (PE-07, matched triads both
   directions).
7. Positive Evidence is tested against all four locked Base Classes. ✓ §12 (PE-04
   for Transition, PE-06 for Whitespace, each against `OTHER`/`CLAUSE`/`ELLIPSIS`/
   `SENTENCE_FINAL`).
8. Punctuation interaction is covered. ✓ §14 (PE-10-01–03).
9. Technical / product terminology is covered without recalibrating protection. ✓
   §13 (PE-09-01–05), explicitly distinguishing clean from contaminated cases and
   never proposing a protection-value change.
10. At least one integrated realistic paragraph contains multiple Base Classes and
    Positive Evidence. ✓ §16.2 (PE-12).
11. Existing evidence is distinguished from new cases. ✓ §5.1 (EE-1–EE-8, each
    tagged EXISTING EVIDENCE and cited by ID wherever a new case tests the same
    ground independently).
12. Cases distinguish CLEAN from INTERACTION. ✓ every case table states a predicted
    status per §17; CLEAN and INTERACTION are never assigned to the same case ID.
13. No numeric value is changed. ✓ §2.1/§2.2 values are stated as fixed inputs and
    provisional-baseline references only; no replacement value appears anywhere in
    this document.
14. No new scoring factor is introduced. ✓ §4 explicitly excludes every factor named
    in this round's scope restriction.
15. No production code is modified. ✓ this document is the sole file created.
16. No existing artifact is modified. ✓ confirmed in the final response accompanying
    this document.
17. The matrix is suitable for a later execution round. ✓ every case specifies
    input text, target boundary, expected/predicted evidence, and evidence
    requirements sufficient to run against the real, unmodified pipeline using the
    existing `dump()`-style calibration infrastructure, following the same pattern
    already used for Base Classification Calibration Round 1.
