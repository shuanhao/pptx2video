# Phase 2C Positive Evidence Calibration Matrix

**Status:** Calibration Matrix Design Ã¢â‚¬â€ no calibration experiment executed
**Phase:** Phase 2C Ã¢â‚¬â€ Numeric Calibration (Positive Evidence)
**Purpose:** Design the calibration matrix needed to evaluate whether the current
Positive Evidence magnitudes (`CJK Ã¢â€ â€™ LATIN +15`, `LATIN Ã¢â€ â€™ CJK +15`, `Whitespace +10`)
are appropriate on top of the now-locked Base Classification layer, without changing
any value and without running the experiment.

This document is a **design artifact only**. No calibration script was run, no
existing artifact was modified, and no numeric conclusion is drawn here.

---

## 1. Purpose

`docs/phase2c/decisions/PHASE_2C_NUMERIC_BASELINE_DECISION.md` adopted the current Positive Evidence
scores (`CJK Ã¢â€ â€™ LATIN +15`, `LATIN Ã¢â€ â€™ CJK +15`, `Whitespace +10`) as a provisional
baseline, not yet the subject of a dedicated calibration round. Base Classification
Dominance was subsequently evaluated in
`docs/phase2c/calibration/reports/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_ROUND1_REPORT.md`, which recorded
`KEEP` for all three base-classification margins (`CLAUSE - OTHER = 35`,
`ELLIPSIS - CLAUSE = 30`, `SENTENCE_FINAL - ELLIPSIS = 15`). This matrix defines the
calibration cases a later execution round will need to evaluate whether Positive
Evidence provides appropriate *relative* preference on top of that now-established
base layer Ã¢â‚¬â€ not to re-litigate the base scores themselves, which are treated as
fixed inputs throughout this document.

**Note on a naming discrepancy in this round's own instructions.** This round's
instructions repeatedly reference `docs/phase2c/calibration/matrices/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_MATRIX.md`
as an existing, authoritative file that "locks" the base classification values.
Repository inspection confirms **no file by that name exists**. The two real,
existing artifacts covering this ground are `docs/phase2c/decisions/PHASE_2C_NUMERIC_BASELINE_DECISION.md`
(which adopted `SENTENCE_FINAL=+80`/`ELLIPSIS=+65`/`CLAUSE=+35`/`OTHER=0` as the
*provisional* baseline, explicitly not yet calibrated at the time) and
`docs/phase2c/calibration/reports/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_ROUND1_REPORT.md` (which subsequently
recorded `KEEP` for all three margins between those same values, based on real-pipeline
evidence). Numerically, the values this round asks to be treated as "locked" are
identical to the values those two real documents already establish, so this
discrepancy does not block this round's work Ã¢â‚¬â€ the same four numbers
(`+80`/`+65`/`+35`/`0`) are used below exactly as this round's instructions specify.
This note records the naming discrepancy factually, per the established practice of
not silently substituting or fabricating a referenced-but-missing artifact (see
`docs/phase2c/decisions/PHASE_2C_NUMERIC_BASELINE_DECISION.md` Ã‚Â§11 for the precedent Ã¢â‚¬â€ the
`CLAUSE=+20`/`ELLIPSIS=+40` prompt-level discrepancy was handled the same way). No
file named `PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_DECISION.md` is created by this
round Ã¢â‚¬â€ this round is scoped to create exactly one file, the matrix named in its own
title.

## 2. Authoritative Baseline

### 2.1 Locked Base Classification

Per `docs/phase2c/decisions/PHASE_2C_NUMERIC_BASELINE_DECISION.md` Ã‚Â§4.1 and
`docs/phase2c/calibration/reports/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_ROUND1_REPORT.md` Ã‚Â§9 (all three
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
observation is recorded as `OUT OF CURRENT SCOPE` (Ã‚Â§17) and not acted upon here Ã¢â‚¬â€ the
question is closed for this round.

### 2.2 Provisional Positive Evidence

| Factor | Current Value | Status |
|---|---:|---|
| CJK Ã¢â€ â€™ LATIN | +15 | PROVISIONAL |
| LATIN Ã¢â€ â€™ CJK | +15 | PROVISIONAL |
| Whitespace | +10 | PROVISIONAL |

These three values are what this matrix is designed to gather evidence about. No
value above is modified by this document Ã¢â‚¬â€ it only designs cases; it does not execute
them and does not propose a replacement number for anything.

## 3. Calibration Scope

This matrix covers exactly three Positive Evidence factors, applied on top of the
locked base layer:

- **A. CJK Ã¢â€ â€™ LATIN transition** (+15)
- **B. LATIN Ã¢â€ â€™ CJK transition** (+15)
- **C. Whitespace** (+10)

And the calibration questions from this round's own objective:

1. Is CJK Ã¢â€ â€™ LATIN +15 appropriate?
2. Is LATIN Ã¢â€ â€™ CJK +15 appropriate?
3. Is the symmetry CJK Ã¢â€ â€™ LATIN = LATIN Ã¢â€ â€™ CJK appropriate (evidence-supported, not
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

- **Base Classification** (`SENTENCE_FINAL`, `ELLIPSIS`, `CLAUSE`, `OTHER`) Ã¢â‚¬â€ locked,
  per Ã‚Â§2.1. Treated as a fixed input; never re-evaluated by any case below.
- **Protection** (`Technical -30`, `Atomic -30`, `INTERNAL -20`) Ã¢â‚¬â€ already the subject
  of the completed Protection Calibration and Post-Correction Verification; not
  recalibrated here. Realistic text may contain Technical/Atomic evidence
  incidentally (especially in the Technical/Product Terminology group, Ã‚Â§13); where it
  appears, it is recorded and the case is classified `CONTAMINATED` or `NEEDS DATA`
  as appropriate Ã¢â‚¬â€ never silently subtracted, and the protection value itself is
  never adjusted to compensate.
- **No new scoring factor.** Specifically excluded: semantic importance, word
  frequency, word length, emoji weighting, emoticon weighting, capitalization, syntax
  weighting, speaker-intent weighting, sentence-length weighting, paragraph position
  weighting. If a case's observation suggests one of these might matter, it is
  recorded as a `FUTURE DESIGN QUESTION` (Ã‚Â§17) and not added to the scoring model.
- **Emoji / emoticon** Ã¢â‚¬â€ no dedicated cases. If present incidentally in a natural
  PPT-note case, excluded from the calibration interpretation rather than given
  special treatment.
- **Threshold / normalization / class-specific hard floor** Ã¢â‚¬â€ none introduced. Phase
  2C remains a signed relative score with no threshold, no normalization, no
  class-specific hard floor.
- Production code, tests, existing calibration scripts/matrices/reports, the Numeric
  Baseline Decision, the Base Classification Calibration Matrix and Round 1 Report,
  Phase 2D, `subtitle_segmenter.py`.

## 5. Calibration Method

A later execution round must:

1. Run each case's input text through the real, unmodified pipeline
   (`analyze_text_structure` Ã¢â€ â€™ `observe_boundaries` Ã¢â€ â€™ `classify_boundary` Ã¢â€ â€™
   Positive Evidence observation), exactly as every prior calibration script has
   done Ã¢â‚¬â€ no re-parsing, no synthetic `BoundaryClass`/evidence substitution, no
   manually assigning transition or whitespace evidence to a candidate.
2. Locate the real candidate(s) matching each case's "Target boundary" description
   and record the actual observed class, base score, transition modifier, whitespace
   modifier, and any protection modifier that also applies Ã¢â‚¬â€ exactly as the existing
   `dump()`-style calibration output already does.
3. Compare observed values against each case's calibration question and record
   `KEEP` / `INCREASE` / `DECREASE` / `NEED MORE DATA` (Ã‚Â§19) Ã¢â‚¬â€ never a fixed numeric
   replacement.
4. Where a target candidate is unreachable, string-final, or otherwise not
   representable by the current pipeline, mark it `CASE ISSUE` (Ã‚Â§17) rather than
   forcing a synthetic substitute or modifying the input until it "works."
5. Synthetic fixtures (hand-built `BoundaryCandidate`/`BoundaryFeatures`) may be used
   only for arithmetic sanity checks (e.g. confirming `15 + 10 = 25` computes
   correctly given two known modifiers) Ã¢â‚¬â€ never presented as calibration evidence for
   whether a combination is contextually appropriate.

This document performs none of these steps. It only specifies what a later round
must do.

### 5.1 Existing Evidence Inventory

Per this round's instruction to distinguish previously-observed evidence from newly
designed cases, the following findings are already present in the repository and are
**not** re-derived as new cases below, though several new cases in Ã‚Â§7Ã¢â‚¬â€œÃ‚Â§16 are
deliberately designed to test whether they replicate under independent text:

| ID | Source | Finding | Status |
|---|---|---|---|
| EE-1 | `docs/phase2c/calibration/reports/PHASE_2C_NUMERIC_CALIBRATION_ROUND1_REPORT.md` C09/C10 | No-space CJKÃ¢â€ â€™LATIN (`Ã¤Â¸Â­Ã¦â€“â€¡Ã¯Â½Å“English`) and LATINÃ¢â€ â€™CJK (`EnglishÃ¯Â½Å“Ã¤Â¸Â­Ã¦â€“â€¡`) each produce a clean `OTHER`+transition candidate scoring exactly `15.0` | EXISTING EVIDENCE |
| EE-2 | `docs/phase2c/calibration/reports/PHASE_2C_NUMERIC_CALIBRATION_ROUND2_REPORT.md` A04/C03 | Same no-space transition finding, independently reproduced; symmetric CJKÃ¢â€ â€™LATIN/LATINÃ¢â€ â€™CJK values confirmed equal in the cases where both were reachable | EXISTING EVIDENCE |
| EE-3 | `docs/phase2c/calibration/reports/PHASE_2C_NUMERIC_CALIBRATION_ROUND2_REPORT.md` Group C (C01/C02) | Naturally-written CJK/Latin text almost always has a **space** at the language switch point (standard Chinese typographic convention); when a space is present, the pure transition candidate does not occur Ã¢â‚¬â€ the boundary splits into two whitespace-only candidates instead | EXISTING EVIDENCE |
| EE-4 | `docs/phase2c/calibration/reports/PHASE_2C_NUMERIC_CALIBRATION_ROUND2_REPORT.md` Group D (D01Ã¢â‚¬â€œD03) | Whitespace evidence is split across two separate candidates (one on each side of the space character), never combined onto one candidate; multiple consecutive whitespace characters do not stack the bonus Ã¢â‚¬â€ always exactly `+10` per boundary | EXISTING EVIDENCE |
| EE-5 | `docs/phase2c/calibration/reports/PHASE_2C_NUMERIC_CALIBRATION_ROUND2_REPORT.md` D04 | The no-space transition candidate (`15.0`) outscores the whitespace-adjacent variant of the same underlying language switch (`10.0`) Ã¢â‚¬â€ adding a space does not "enrich" a transition boundary into a stronger `25`-point candidate, it *replaces* it with a weaker whitespace-only one elsewhere. One of the two most important ranking findings from Round 2. | EXISTING EVIDENCE |
| EE-6 | `docs/phase2c/calibration/reports/PHASE_2C_NUMERIC_CALIBRATION_ROUND1_REPORT.md` C14/C27/C28 | `CLAUSE` and language-transition evidence are mutually exclusive on a single real candidate: the `CLAUSE` candidate's left character is always the clause-punctuation mark itself (`CharacterClass.PUNCTUATION`), never `CJK`/`LATIN`, so the transition rule's precondition (both sides being letter-class, one CJK one LATIN) can never fire on a `CLAUSE` candidate. Confirmed at three independent positions across Round 1 (C14, C27, C32 pos13). Whitespace, by contrast, **does** co-occur with `CLAUSE` Ã¢â‚¬â€ C14 observed `CLAUSE`+whitespace = `35+10=45.0` | EXISTING EVIDENCE |
| EE-7 | `docs/phase2c/calibration/reports/PHASE_2C_NUMERIC_CALIBRATION_ROUND2_REPORT.md` E01/E02/E04 | Technical/Atomic-protected content (e.g. `1,000`, `v1.2.3`) never coincides with a `CLAUSE` candidate in the cases observed (the actual clause punctuation in those sentences sits outside the protected span); a transition-only candidate (`15.0`) outranks a technical-protected candidate (`-30.0`/`-60.0`) in the intended direction Ã¢â‚¬â€ not flagged as a reversal | EXISTING EVIDENCE |
| EE-8 | `docs/phase2c/calibration/reports/PHASE_2C_NUMERIC_CALIBRATION_ROUND2_REPORT.md` Ã‚Â§9 finding 4 | Embedded markdown line-wraps inside a case's own source text can incidentally act as whitespace, an artifact of how the case text itself was authored rather than of the pipeline Ã¢â‚¬â€ a caution for how new case text is written, not a pipeline finding | EXISTING EVIDENCE |

EE-6 in particular directly informs Ã‚Â§12 below: because the mechanism it documents
(punctuation-anchored candidates cannot carry transition evidence) is structural Ã¢â‚¬â€
grounded in `CharacterClass` assignment, not particular to the specific sentences
C14/C27/C28 used Ã¢â‚¬â€ the same reasoning predicts that `ELLIPSIS` and `SENTENCE_FINAL`
candidates (which are likewise anchored with a `PUNCTUATION`-class character on one
side) will show the same mutual exclusivity with Transition evidence. Ã‚Â§12 designs
cases to test this prediction directly rather than simply asserting it holds by
analogy Ã¢â‚¬â€ a "structural prediction from an existing finding" is not the same as
"already-observed evidence for a different class," and this document does not
conflate the two.

## 6. Evidence Quality Model

Each case in Ã‚Â§7Ã¢â‚¬â€œÃ‚Â§16 is assigned one of six statuses. The full definitions are
authoritative in Ã‚Â§17; this section previews them so the case tables below are
readable without forward-referencing:

- **CLEAN** Ã¢â‚¬â€ the intended positive factor is isolated sufficiently for calibration.
- **INTERACTION** Ã¢â‚¬â€ the case intentionally studies a combination of factors.
- **CONTAMINATED** Ã¢â‚¬â€ an unintended factor materially affects interpretation.
- **CASE ISSUE** Ã¢â‚¬â€ the intended candidate cannot be represented or reached by the
  current pipeline.
- **NEEDS DATA** Ã¢â‚¬â€ evidence is insufficient for a meaningful calibration judgment.
- **ANALYSIS ONLY** Ã¢â‚¬â€ useful diagnostic observation, not sufficient alone to support
  a numeric decision.

No case below is pre-assigned a final status by this design round beyond a
*predicted* status, drawn from the existing evidence in Ã‚Â§5.1 where applicable. Every
predicted status is written as a prediction to be confirmed or refuted by real
execution, never as a foregone conclusion.

## 7. CJK Ã¢â€ â€™ LATIN Calibration (PE-01)

Clean, no-space individual-evidence cases isolating the CJKÃ¢â€ â€™LATIN transition bonus
on an otherwise plain `OTHER` candidate, drawn from realistic PPT-note phrasing about
software tools (a natural place for embedded English terms to appear with no space,
per Chinese technical-writing convention for short tool/product names used as
objects).

Shared fields for all PE-01 cases (not repeated per case): **Expected BoundaryClass**
= `OTHER`; **Base Classification score** = `0.0` (fixed input, per Ã‚Â§2.1); **Expected
positive evidence** = `CJK Ã¢â€ â€™ LATIN`, `+15`; **Evidence requirement** = real pipeline,
no whitespace between the CJK and Latin characters at the target position;
**Clean/interaction criteria** = CLEAN if the target candidate carries no whitespace
or protection modifier alongside the transition; **Interpretation criteria** = per
Ã‚Â§19.

| Case ID | Purpose | Input text | Target boundary | Comparison candidate | Calibration question | Predicted status |
|---|---|---|---|---|---|---|
| PE-01-01 | Tool name embedded directly after a verb, no space (natural short-tool-name convention) | `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥Å Å¸Ã¨Æ’Â½Ã¤Â½Â¿Ã§â€Â¨PythonÃ¨â„¢â€¢Ã§Ââ€ Ã¨Â³â€¡Ã¦â€“â„¢Ã£â‚¬â€š` | `Ã§â€Â¨Ã¯Â½Å“P` (last CJK char of `Ã¤Â½Â¿Ã§â€Â¨`, first Latin char of `Python`) | vs. plain interior `OTHER` elsewhere in the same text (e.g. `Ã©â‚¬â„¢Ã¯Â½Å“Ã¥â‚¬â€¹`, `0.0`) | Does `+15` read as an appropriate increment over plain `OTHER` for this realistic no-space transition? | CLEAN |
| PE-01-02 | Different tool name, different verb, independent sentence | `Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§â€Â¨ExcelÃ¥ÂÅ¡Ã¥Â Â±Ã¨Â¡Â¨Ã¯Â¼Å’Ã¥Â¾Ë†Ã¦â€“Â¹Ã¤Â¾Â¿Ã£â‚¬â€š` | `Ã§â€Â¨Ã¯Â½Å“E` | vs. plain interior `OTHER` in the same text | Same as PE-01-01, independent case | CLEAN |
| PE-01-03 | Third tool name, distinct phrasing (`Ã¦Å½Â¡Ã§â€Â¨` instead of `Ã§â€Â¨`) | `Ã§Â³Â»Ã§ÂµÂ±Ã¦Å½Â¡Ã§â€Â¨DockerÃ©Æ’Â¨Ã§Â½Â²Ã¦Å“ÂÃ¥â€¹â„¢Ã£â‚¬â€š` | `Ã§â€Â¨Ã¯Â½Å“D` | vs. plain interior `OTHER` in the same text | Same as PE-01-01, independent case | CLEAN |

## 8. LATIN Ã¢â€ â€™ CJK Calibration (PE-02)

Mirror of Ã‚Â§7 in the opposite direction Ã¢â‚¬â€ the Latin tool name is immediately followed
by CJK continuation text, no space.

Shared fields: **Expected BoundaryClass** = `OTHER`; **Base Classification score** =
`0.0`; **Expected positive evidence** = `LATIN Ã¢â€ â€™ CJK`, `+15`; **Evidence
requirement** = real pipeline, no whitespace at the target position; other fields as
in Ã‚Â§7.

| Case ID | Purpose | Input text | Target boundary | Comparison candidate | Calibration question | Predicted status |
|---|---|---|---|---|---|---|
| PE-02-01 | Tool name as sentence subject, immediately followed by CJK verb, no space | `PythonÃ¥ÂÂ¯Ã¤Â»Â¥Ã¨â„¢â€¢Ã§Ââ€ Ã¨Â³â€¡Ã¦â€“â„¢Ã£â‚¬â€š` | `nÃ¯Â½Å“Ã¥ÂÂ¯` (last Latin char, first CJK char) | vs. plain interior `OTHER` in the same text | Does `+15` read as an appropriate increment over plain `OTHER` for this realistic no-space transition, in the reverse direction from Ã‚Â§7? | CLEAN |
| PE-02-02 | Different tool name, different continuation verb | `ExcelÃ¨Æ’Â½Ã¥ÂÅ¡Ã¥Â Â±Ã¨Â¡Â¨Ã¯Â¼Å’Ã¥Â¾Ë†Ã¦â€“Â¹Ã¤Â¾Â¿Ã£â‚¬â€š` | `lÃ¯Â½Å“Ã¨Æ’Â½` | vs. plain interior `OTHER` in the same text | Same as PE-02-01, independent case | CLEAN |
| PE-02-03 | Third tool name | `DockerÃ¨Æ’Â½Ã©Æ’Â¨Ã§Â½Â²Ã¦Å“ÂÃ¥â€¹â„¢Ã£â‚¬â€š` | `rÃ¯Â½Å“Ã¨Æ’Â½` | vs. plain interior `OTHER` in the same text | Same as PE-02-01, independent case | CLEAN |

## 9. Transition Symmetry Calibration (PE-03)

Per this round's explicit instruction, symmetry is **not** assumed merely because the
current baseline uses equal values (`+15` = `+15`). These cases place both directions
inside the **same sentence**, in comparable surrounding context (a Latin word
sandwiched between CJK text on both sides, no spaces on either side), so the two
transition candidates can be compared directly from one real-pipeline run rather than
across two separately-constructed texts. This is a stronger symmetry test than Ã‚Â§7/Ã‚Â§8
individually, because both directions share the identical sentence-level context.

Shared fields: **Base Classification score** = `0.0` for both target candidates;
**Expected positive evidence** = `CJK Ã¢â€ â€™ LATIN, +15` for the first target, `LATIN Ã¢â€ â€™
CJK, +15` for the second target; **Evidence requirement** = real pipeline, both
candidates from the same input text, no whitespace on either side of the embedded
Latin word; **Calibration question** (shared) = does the same `+15` contribution
hold for both directions when observed in the same sentence, or does the real
pipeline's evidence (not merely the shared baseline number) support treating them as
genuinely symmetric?

| Case ID | Purpose | Input text | Target A (CJKÃ¢â€ â€™LATIN) | Target B (LATINÃ¢â€ â€™CJK) | Predicted status |
|---|---|---|---|---|---|
| PE-03-01 | Latin word sandwiched between CJK on both sides, no spaces | `Ã©â‚¬â„¢Ã¦ËœÂ¯PythonÃ¨ÂªÅ¾Ã¨Â¨â‚¬Ã£â‚¬â€š` | `Ã¦ËœÂ¯Ã¯Â½Å“P` | `nÃ¯Â½Å“Ã¨ÂªÅ¾` | CLEAN |
| PE-03-02 | Different sandwiched word, different sentence | `Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§â€Â¨DockerÃ©Æ’Â¨Ã§Â½Â²Ã£â‚¬â€š` | `Ã§â€Â¨Ã¯Â½Å“D` | `rÃ¯Â½Å“Ã©Æ’Â¨` | CLEAN |
| PE-03-03 | Acronym sandwiched between CJK on both sides | `Ã§Â³Â»Ã§ÂµÂ±Ã¦Å½Â¡Ã§â€Â¨APIÃ¦Å½Â¥Ã¥ÂÂ£Ã£â‚¬â€š` | `Ã§â€Â¨Ã¯Â½Å“A` | `IÃ¯Â½Å“Ã¦Å½Â¥` | CLEAN |

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
even where a CJK/Latin switch also occurs across the space Ã¢â‚¬â€ these cases are designed
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
| PE-05-01 | CJK + whitespace + CJK | `Ã©â‚¬â„¢Ã¥â‚¬â€¹ Ã¥Å Å¸Ã¨Æ’Â½Ã¥Â¾Ë†Ã¥Â¥Â½Ã§â€Â¨Ã£â‚¬â€š` | both candidates around the inserted space (`Ã¥â‚¬â€¹Ã¯Â½Å“(sp)`, `(sp)Ã¯Â½Å“Ã¥Å Å¸`) | vs. plain CJK-CJK `OTHER` elsewhere in the same text (`0.0`) | CLEAN |
| PE-05-02 | CJK + whitespace + Latin (natural typographic convention) | `Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â½Â¿Ã§â€Â¨ PythonÃ¨â„¢â€¢Ã§Ââ€ Ã¨Â³â€¡Ã¦â€“â„¢Ã£â‚¬â€š` | both candidates around the space between `Ã§â€Â¨` and `Python` | vs. PE-01-01's no-space transition candidate (`15.0`) Ã¢â‚¬â€ cross-referenced, not re-derived | CLEAN, also feeds Ã‚Â§11 |
| PE-05-03 | Latin + whitespace + CJK (natural typographic convention) | `Ã¤Â½Â¿Ã§â€Â¨Python Ã¨â„¢â€¢Ã§Ââ€ Ã¨Â³â€¡Ã¦â€“â„¢Ã£â‚¬â€š` | both candidates around the space between `Python` and `Ã¨â„¢â€¢` | vs. PE-02-01's no-space transition candidate (`15.0`) Ã¢â‚¬â€ cross-referenced | CLEAN, also feeds Ã‚Â§11 |
| PE-05-04 | Latin + whitespace + Latin | `Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¨Â¨Â­Ã¥Â®Å¡ API Key Ã¤Â¹â€¹Ã¥Â¾Å’Ã¥Â°Â±Ã¥Â®Å’Ã¦Ë†ÂÃ¤Âºâ€ Ã£â‚¬â€š` | both candidates around the space between `API` and `Key` | vs. plain Latin-Latin `OTHER` elsewhere in the same text (e.g. within `API` itself, `0.0`) | CLEAN |

## 11. Transition + Whitespace Interaction (PE-07)

Matched triads for both transition directions: transition-only (no space),
whitespace-only (space present, per EE-3/EE-5 no pure transition candidate is
expected), and an explicit attempted "transition + whitespace" case included per this
round's requirement even though EE-5 already predicts it is structurally
unreachable as a single `+25` candidate Ã¢â‚¬â€ the later execution round must confirm
this prediction on independent text rather than rely solely on the Round 2 finding.

| Case ID | Purpose | Input text | Target boundary | Expected/predicted evidence | Predicted status |
|---|---|---|---|---|---|
| PE-07-01a | CJKÃ¢â€ â€™LATIN, transition-only (no space) | `Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â½Â¿Ã§â€Â¨PythonÃ¥Ë†â€ Ã¦Å¾ÂÃ¨Â³â€¡Ã¦â€“â„¢Ã£â‚¬â€š` | `Ã§â€Â¨Ã¯Â½Å“P` | `OTHER`, `+15` transition, no whitespace | CLEAN |
| PE-07-01b | Same underlying phrase, whitespace inserted at the switch point | `Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â½Â¿Ã§â€Â¨ PythonÃ¥Ë†â€ Ã¦Å¾ÂÃ¨Â³â€¡Ã¦â€“â„¢Ã£â‚¬â€š` | both candidates around the inserted space | `OTHER`+`Whitespace(+10)` each side, per EE-3/EE-4; predicted **no** transition evidence on either candidate | CLEAN, tests EE-5's prediction |
| PE-07-01c | Attempted "transition + whitespace" on the same underlying switch | same text as PE-07-01b Ã¢â‚¬â€ no separate text is constructable, since inserting a space is definitionally what produces PE-07-01b instead of PE-07-01a | n/a Ã¢â‚¬â€ this row records the **absence** of a third variant rather than a third input text | Predicted unreachable as a single candidate carrying both `+15` and `+10` simultaneously (`= +25`), per EE-5 | Predicted **CASE ISSUE** (structural: whitespace and no-space transition are mutually exclusive conditions on the same boundary by construction, not merely by current pipeline limitation) |
| PE-07-02a | LATINÃ¢â€ â€™CJK, transition-only (no space) | `PythonÃ¥Ë†â€ Ã¦Å¾ÂÃ¨Â³â€¡Ã¦â€“â„¢Ã¥Â¾Ë†Ã¥Â¿Â«Ã£â‚¬â€š` | `nÃ¯Â½Å“Ã¥Ë†â€ ` | `OTHER`, `+15` transition, no whitespace | CLEAN |
| PE-07-02b | Same underlying phrase, whitespace inserted | `Python Ã¥Ë†â€ Ã¦Å¾ÂÃ¨Â³â€¡Ã¦â€“â„¢Ã¥Â¾Ë†Ã¥Â¿Â«Ã£â‚¬â€š` | both candidates around the inserted space | `OTHER`+`Whitespace(+10)` each side; predicted no transition evidence | CLEAN, tests EE-5's prediction |
| PE-07-02c | Attempted "transition + whitespace" | same construction issue as PE-07-01c, opposite direction | n/a | Predicted unreachable, same reasoning as PE-07-01c | Predicted **CASE ISSUE** |

**Hierarchy question this group feeds (not answered here):** whether the resulting
practical hierarchy Ã¢â‚¬â€ no-space transition (`15`) vs. whitespace-adjacent (`10`) vs.
the arithmetically-implied-but-structurally-unreachable additive combination (`25`)
Ã¢â‚¬â€ is a reasonable outcome for Phase 2D to work with, given that the `25` case never
actually occurs. This round only stages the cases; it does not decide whether that
absence is itself acceptable or whether it points to a future interaction-rule
question for Phase 2D (which is out of scope for Phase 2C calibration).

## 12. Base Classification Ãƒâ€” Positive Evidence (PE-04, PE-06)

Two subgroups: Transition attached to each of the four locked base classes (PE-04),
and Whitespace attached to each of the four locked base classes (PE-06). The purpose
is **not** to recalibrate `SENTENCE_FINAL`/`ELLIPSIS`/`CLAUSE`/`OTHER` Ã¢â‚¬â€ it is to
determine whether the Positive Evidence contribution is appropriately scaled relative
to the locked base hierarchy once actually combined with it. Per Ã‚Â§5.1/EE-6, prior
evidence already predicts that Transition cannot co-occur with `CLAUSE` on a single
real candidate; the same structural reasoning is extended here as a prediction (not
an assumption) for `ELLIPSIS` and `SENTENCE_FINAL`, and each case below is still
designed as a real, executable case rather than skipped, so the later round can
confirm or refute the prediction directly.

### 12.1 PE-04 Ã¢â‚¬â€ Transition attached to Base Classification

| Case ID | Purpose | Input text | Target boundary | Arithmetic if reachable | Calibration question | Predicted status |
|---|---|---|---|---|---|---|
| PE-04-OTHER | `OTHER` + Transition | Cross-referenced from Ã‚Â§7/Ã‚Â§8/Ã‚Â§9 (e.g. PE-01-01) Ã¢â‚¬â€ not a new case | `Ã§â€Â¨Ã¯Â½Å“P` | `0 + 15 = 15` | Is `15` (`OTHER`+Transition) an appropriately modest elevation above plain `OTHER` (`0`), well below `CLAUSE` (`35`)? | CLEAN (reused) |
| PE-04-CLAUSE | `CLAUSE` + Transition (attempted) | `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥Å Å¸Ã¨Æ’Â½Ã¯Â¼Å’PythonÃ¨â„¢â€¢Ã§Ââ€ Ã¨Â³â€¡Ã¦â€“â„¢Ã£â‚¬â€š` | `Ã¯Â¼Å’Ã¯Â½Å“P` (clause comma immediately followed, no space, by the Latin word) | `35 + 15 = 50` if reachable | Does the real pipeline ever produce a candidate that is simultaneously `CLAUSE` and transition-evidenced? | Predicted **CASE ISSUE**, per EE-6 (clause candidate's left character is `PUNCTUATION`, never `CJK`/`LATIN`) Ã¢â‚¬â€ to be confirmed, not assumed |
| PE-04-ELLIPSIS | `ELLIPSIS` + Transition (attempted) | `Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Â¨ÂÃ¥Â¾Å’Ã¨ÂªÂªÃ¦ËœÅ½Ã¢â‚¬Â¦Ã¢â‚¬Â¦PythonÃ§Â¯â€žÃ¤Â¾â€¹Ã¦Å“Æ’Ã¥Â±â€¢Ã§Â¤ÂºÃ£â‚¬â€š` | `Ã¢â‚¬Â¦Ã¯Â½Å“P` (ellipsis run's END-state position immediately followed, no space, by the Latin word) | `65 + 15 = 80` if reachable | Does the real pipeline ever produce a candidate that is simultaneously `ELLIPSIS` (END-state) and transition-evidenced? | Predicted **CASE ISSUE**, by the same structural reasoning as EE-6 (the END-state candidate's left character is the ellipsis mark itself, `PUNCTUATION`) Ã¢â‚¬â€ to be confirmed |
| PE-04-SENTENCE_FINAL | `SENTENCE_FINAL` + Transition (attempted) | `Ã©â‚¬â„¢Ã¦ËœÂ¯Ã©â€¡ÂÃ©Â»Å¾Ã£â‚¬â€šPythonÃ§Â¯â€žÃ¤Â¾â€¹Ã¥Â¦â€šÃ¤Â¸â€¹Ã¯Â¼Å¡` | `Ã£â‚¬â€šÃ¯Â½Å“P` (sentence-final mark immediately followed, no space, by the Latin word) | `80 + 15 = 95` if reachable | Does the real pipeline ever produce a candidate that is simultaneously `SENTENCE_FINAL` and transition-evidenced? | Predicted **CASE ISSUE**, by the same structural reasoning as EE-6 (the SF candidate's left character is the sentence-final mark itself, `PUNCTUATION`) Ã¢â‚¬â€ to be confirmed |

**If all three `CASE ISSUE` predictions are confirmed**, the practical conclusion for
a later round to state (not this one) would be that "Transition attached to
`CLAUSE`/`ELLIPSIS`/`SENTENCE_FINAL`" is not a real-pipeline-representable scenario
at all under the current architecture, and the arithmetic values in the table above
(`50`/`80`/`95`) are never-occurring hypotheticals rather than calibration targets Ã¢â‚¬â€
mirroring exactly how Round 1's C27/C28 treated the equivalent `CLAUSE`+transition
case ("not evaluable"). This document does not draw that conclusion; it stages the
cases needed to reach it.

### 12.2 PE-06 Ã¢â‚¬â€ Whitespace attached to Base Classification

Unlike Transition, EE-6 already shows Whitespace **does** co-occur with `CLAUSE`
(C14: `35+10=45.0`), because the whitespace check does not appear to share the same
CJK/LATIN character-class precondition as the transition check. These cases test
whether that holds independently on new text, and whether it extends to `ELLIPSIS`
and `SENTENCE_FINAL` as well Ã¢â‚¬â€ this is a genuinely open question, not a predicted
`CASE ISSUE` the way Ã‚Â§12.1 is.

| Case ID | Purpose | Input text | Target boundary | Arithmetic if reachable | Calibration question | Predicted status |
|---|---|---|---|---|---|---|
| PE-06-OTHER | `OTHER` + Whitespace | Cross-referenced from Ã‚Â§10 (e.g. PE-05-01) Ã¢â‚¬â€ not a new case | `Ã¥â‚¬â€¹Ã¯Â½Å“(sp)` | `0 + 10 = 10` | Is `10` an appropriately modest elevation above plain `OTHER`? | CLEAN (reused) |
| PE-06-CLAUSE | `CLAUSE` + Whitespace | `Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¯Â¼Å’ Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â»â€¹Ã§Â´Â¹Ã©â€¡ÂÃ©Â»Å¾Ã£â‚¬â€š` (space immediately after the clause comma) | `Ã¯Â¼Å’Ã¯Â½Å“(sp)` | `35 + 10 = 45` | Independent confirmation of EE-6/C14's finding: does `CLAUSE`+Whitespace consistently score `45.0`? Does `+10` read as an appropriate additional increment on top of the much larger `CLAUSE` base? | Predicted CLEAN / reachable, per EE-6 Ã¢â‚¬â€ to be confirmed independently |
| PE-06-ELLIPSIS | `ELLIPSIS` + Whitespace | `Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Â¨ÂÃ¥Â¾Å’Ã¥â€ ÂÃ¨Â«â€¡Ã¢â‚¬Â¦Ã¢â‚¬Â¦ Ã¥Â¥Â½Ã¯Â¼Å’Ã©â€“â€¹Ã¥Â§â€¹Ã¥ÂÂ§Ã£â‚¬â€š` (space immediately after the ellipsis run's END position) | `Ã¢â‚¬Â¦Ã¯Â½Å“(sp)` | `65 + 10 = 75` if reachable | Does an `ELLIPSIS` END-state candidate carry whitespace evidence the same way `CLAUSE` does? | Genuinely open Ã¢â‚¬â€ no existing evidence either way; not predicted `CASE ISSUE` unlike Ã‚Â§12.1's ellipsis row, since whitespace's precondition (unlike transition's) is not known to require non-`PUNCTUATION` character classes |
| PE-06-SENTENCE_FINAL | `SENTENCE_FINAL` + Whitespace | `Ã©â‚¬â„¢Ã¦ËœÂ¯Ã©â€¡ÂÃ©Â»Å¾Ã£â‚¬â€š Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¤Â»â€¹Ã§Â´Â¹Ã§Â¯â€žÃ¤Â¾â€¹Ã£â‚¬â€š` (space immediately after the sentence-final mark) | `Ã£â‚¬â€šÃ¯Â½Å“(sp)` | `80 + 10 = 90` if reachable | Does a `SENTENCE_FINAL` candidate carry whitespace evidence the same way `CLAUSE` does? | Genuinely open, same reasoning as PE-06-ELLIPSIS |

## 13. Technical / Product Terminology (PE-09)

Realistic cases containing product names and acronyms, deliberately split between
text that stays clean (no digits/symbols that would trigger `Technical`/`Atomic`
protection) and text that incidentally contains such spans, so the later round can
distinguish genuine Positive Evidence readings from protection-contaminated ones
without silently discarding the contamination.

| Case ID | Purpose | Input text | Target boundary | Expected class/evidence | Calibration question | Predicted status |
|---|---|---|---|---|---|---|
| PE-09-01 | Clean brand name, no digits/symbols | `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã§Â°Â¡Ã¥Â Â±Ã¤Â½Â¿Ã§â€Â¨PowerPointÃ¨Â£Â½Ã¤Â½Å“Ã£â‚¬â€š` | `Ã§â€Â¨Ã¯Â½Å“P` | `OTHER`, `+15` CJKÃ¢â€ â€™LATIN, no protection | Does a realistic, recognizable product name (not a generic placeholder like "Python"/"Excel") produce the same clean `+15` reading? | CLEAN |
| PE-09-02 | Acronym, no digits/symbols | `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã§Â³Â»Ã§ÂµÂ±Ã¤Â½Â¿Ã§â€Â¨APIÃ¤Â¸Â²Ã¦Å½Â¥Ã¨Â³â€¡Ã¦â€“â„¢Ã£â‚¬â€š` | `Ã§â€Â¨Ã¯Â½Å“A` | `OTHER`, `+15` CJKÃ¢â€ â€™LATIN, no protection | Same question for an acronym rather than a full word | CLEAN |
| PE-09-03 | Product name with embedded version number (digits present) | `Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§â€ºÂ®Ã¥â€°ÂÃ¤Â½Â¿Ã§â€Â¨iPhone 15Ã©â‚¬Â²Ã¨Â¡Å’Ã¦Â¸Â¬Ã¨Â©Â¦Ã£â‚¬â€š` | boundary(ies) around/within `15` and at the CJK/Latin switch points | Predicted: digits trigger `Technical`/`Atomic` protection on the number itself; the `Ã¤Â½Â¿Ã§â€Â¨Ã¯Â½Å“iPhone` switch (with a space, per natural convention) is expected to be whitespace-only per EE-3, not transition | Does the incidental digit/protection evidence materially affect interpretation of the nearby transition/whitespace candidates, or are they cleanly separable positions? | Predicted **CONTAMINATED** for candidates inside/adjacent to `15`; predicted CLEAN for the CJKÃ¢â€ â€`iPhone` switch itself Ã¢â‚¬â€ to be confirmed, not assumed, since the exact span boundaries of the digit protection are a Phase 1/2A matter this round does not re-derive |
| PE-09-04 | Version-string-style product identifier | `Ã§Â³Â»Ã§ÂµÂ±Ã§â€°Ë†Ã¦Å“Â¬Ã¦ËœÂ¯v1.2.3Ã¯Â¼Å’Ã¨Â«â€¹Ã§Â¢ÂºÃ¨ÂªÂÃ£â‚¬â€š` | boundaries within `v1.2.3` and at the clause comma after it | Predicted, per EE-7 (E02): interior positions show `Technical`+`Atomic` interaction (strongest-only per the Numeric Baseline Decision), some via the ASCII-period bare-fallback correction now fixed upstream; the clause comma itself is predicted to sit outside the protected span, per EE-7 | Does this case's clause comma remain a clean, unprotected `CLAUSE` candidate exactly as E01/E02 found, on independently-written text? | Predicted **CONTAMINATED** for the interior version-string positions; predicted CLEAN for the clause comma Ã¢â‚¬â€ cross-checks EE-7 on new text rather than reusing E01/E02's own text |
| PE-09-05 | Acronym embedded with a hyphen (potential atomic/technical trigger) | `Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¦Â¯â€Ã¨Â¼Æ’GPT-4Ã¥â€™Å’Ã¥â€¦Â¶Ã¤Â»â€“Ã¦Â¨Â¡Ã¥Å¾â€¹Ã§Å¡â€žÃ¨Â¡Â¨Ã§ÂÂ¾Ã£â‚¬â€š` | boundaries around `GPT-4` and at its CJK/Latin switch points | Predicted: the hyphenated alphanumeric token may itself be flagged Technical/Atomic per Phase 1's own span rules (not re-derived here); the CJKÃ¢â€ â€™Latin switch into `GPT` is a separate, potentially clean candidate | Is the transition evidence at the language-switch boundary interpretable independently of whatever protection evidence appears inside `GPT-4` itself? | Predicted **CONTAMINATED** or **NEEDS DATA** depending on where Phase 1's actual span boundaries fall Ã¢â‚¬â€ this is exactly the kind of case Ã‚Â§16 (Contaminated vs. Clean) exists to record honestly rather than force into CLEAN |

## 14. Punctuation Interaction (PE-10)

These cases test Transition/Whitespace evidence **near** (not attached to, per Ã‚Â§12's
finding that same-candidate attachment is structurally blocked for punctuation-
anchored classes) clause punctuation, an ellipsis run, and sentence-final
punctuation Ã¢â‚¬â€ i.e., they record the full local candidate neighborhood so a later
round can see whether a nearby high-scoring punctuation-anchored candidate has any
observable effect on an adjacent Positive-Evidence candidate (Phase 2C candidates are
expected, per every prior calibration round, to be computed independently of their
neighbors Ã¢â‚¬â€ these cases are designed to make that independence directly observable
rather than assumed).

| Case ID | Purpose | Input text | Candidates of interest | Calibration question | Predicted status |
|---|---|---|---|---|---|
| PE-10-01 | Transition near clause punctuation | `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥Å Å¸Ã¨Æ’Â½Ã¯Â¼Å’PythonÃ¥ÂÂ¯Ã¤Â»Â¥Ã¨â„¢â€¢Ã§Ââ€ Ã£â‚¬â€š` | (a) the `Ã¯Â¼Å’Ã¯Â½Å“P` position itself (per PE-04-CLAUSE, predicted `CLAUSE` only, no transition); (b) the later `nÃ¯Â½Å“Ã¥ÂÂ¯` position (`LATINÃ¢â€ â€™CJK`, predicted `+15`) | Does the nearby `CLAUSE` candidate (a) have any observable effect on the independently-scored transition candidate (b) a few characters later? | ANALYSIS ONLY (records neighborhood independence, does not itself resolve a KEEP/INCREASE/DECREASE question) |
| PE-10-02 | Transition near an ellipsis run | `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥â€¢ÂÃ©Â¡Å’Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Â¨ÂÃ¥Â¾Å’Ã¨ÂªÂªÃ¦ËœÅ½Ã¢â‚¬Â¦Ã¢â‚¬Â¦PythonÃ§Â¯â€žÃ¤Â¾â€¹Ã¥Â¦â€šÃ¤Â¸â€¹Ã£â‚¬â€š` | (a) the END-state `Ã¢â‚¬Â¦Ã¯Â½Å“P` position (per PE-04-ELLIPSIS, predicted `ELLIPSIS` only, no transition, since `P` directly abuts the mark); (b) the internal `Ã¢â‚¬Â¦Ã¯Â½Å“Ã¢â‚¬Â¦` position (`INTERNAL`, `-20`, incidental) | Same neighborhood-independence question, now against `ELLIPSIS`/`INTERNAL` rather than `CLAUSE` | ANALYSIS ONLY |
| PE-10-03 | Transition near sentence-final punctuation | `Ã©â‚¬â„¢Ã¦ËœÂ¯Ã©â€¡ÂÃ©Â»Å¾Ã£â‚¬â€šPythonÃ§Â¯â€žÃ¤Â¾â€¹Ã¥Â¦â€šÃ¤Â¸â€¹Ã¯Â¼Å¡Ã©â‚¬â„¢Ã¦ËœÂ¯Ã§Â¬Â¬Ã¤ÂºÅ’Ã¥â‚¬â€¹Ã©â€¡ÂÃ©Â»Å¾Ã£â‚¬â€š` | (a) the `Ã£â‚¬â€šÃ¯Â½Å“P` position (per PE-04-SENTENCE_FINAL, predicted `SENTENCE_FINAL` only, no transition); (b) any later transition/whitespace candidate elsewhere in the text | Same neighborhood-independence question, now against `SENTENCE_FINAL` | ANALYSIS ONLY |

## 15. Negative / Non-Useful Whitespace (PE-11)

Cases where whitespace is present for typographic or formatting reasons but should
not automatically be assumed to carry a strong, semantically useful boundary
preference Ã¢â‚¬â€ the goal is not to classify whitespace itself, only to determine whether
its flat `+10` contribution is appropriately calibrated across "useful" and
"not obviously useful" whitespace alike.

| Case ID | Purpose | Input text | Target boundary | Why this whitespace may not be a useful cut signal | Predicted status |
|---|---|---|---|---|---|
| PE-11-01 | Space inside a two-word English product name, itself embedded in a CJK sentence | `Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â½Â¿Ã§â€Â¨ Microsoft Word Ã§Â·Â¨Ã¨Â¼Â¯Ã¦â€“â€¡Ã¤Â»Â¶Ã£â‚¬â€š` | the internal space between `Microsoft` and `Word` (distinct from the CJKÃ¢â€ â€Latin switch spaces on either side of the whole phrase) | A person writing subtitles would essentially never cut in the middle of a proper-noun product name, yet this space is expected to score the same flat `+10` (per EE-4) as any other whitespace boundary | ANALYSIS ONLY |
| PE-11-02 | Space between a number and a CJK measure word (standard typographic convention, not a phrase break) | `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥Å Å¸Ã¨Æ’Â½Ã¥Â°â€¡Ã¦â€“Â¼2026Ã¥Â¹Â´Ã¤Â¸Å Ã§Â·Å¡Ã£â‚¬â€š` vs. a variant with a space: `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥Å Å¸Ã¨Æ’Â½Ã¥Â°â€¡Ã¦â€“Â¼ 2026 Ã¥Â¹Â´Ã¤Â¸Å Ã§Â·Å¡Ã£â‚¬â€š` | the spaces around `2026` | Typographic convention in some style guides inserts a space between digits and CJK text; this is a formatting habit, not a semantic pause, yet it would still score `+10` if present | ANALYSIS ONLY |
| PE-11-03 | Trailing/incidental whitespace from how PPT speaker notes are often authored (line-wrap-adjacent spacing) | `Ã©â‚¬â„¢Ã¦ËœÂ¯Ã§Â¬Â¬Ã¤Â¸â‚¬Ã¨Â¡Å’Ã¥â€ â€¦Ã¥Â®Â¹ Ã©â‚¬â„¢Ã¦ËœÂ¯Ã¦Å½Â¥Ã§ÂºÅ’Ã§Å¡â€žÃ¥â€¦Â§Ã¥Â®Â¹Ã¯Â¼Å’Ã¨ÂªÅ¾Ã¦â€žÂÃ¤Â¸Å Ã¦ËœÂ¯Ã¥ÂÅ’Ã¤Â¸â‚¬Ã¥ÂÂ¥Ã¨Â©Â±Ã£â‚¬â€š` (a single logical sentence authored with an internal space where a line-wrap might occur in the original notes, per EE-8's caution) | the space in the middle of the logically-continuous sentence | This kind of space reflects how the source document was laid out, not an intended subtitle break Ã¢â‚¬â€ EE-8 already flagged this authoring hazard for Round 2; this case exercises it directly rather than only noting it as a caution | ANALYSIS ONLY |

None of the three cases above is expected to produce a `CASE ISSUE` Ã¢â‚¬â€ the whitespace
candidates themselves are expected to be perfectly reachable and to score `10.0`
exactly per EE-4. The open question these cases raise is qualitative (should every
`+10` whitespace boundary be treated as equally useful for segmentation) rather than
mechanical (can the pipeline produce the candidate) Ã¢â‚¬â€ this is recorded as `ANALYSIS
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
| PE-08-01 | Tool-comparison note mixing several embedded tool names, some with spaces (natural convention) and some without | `Ã©â‚¬â„¢Ã¤Â¸â‚¬Ã©Â ÂÃ¦Â¯â€Ã¨Â¼Æ’Ã¥â€¦Â©Ã¥â‚¬â€¹Ã¥Â·Â¥Ã¥â€¦Â·Ã¯Â¼Å¡PythonÃ¥â€™Å’RÃ©Æ’Â½Ã¥ÂÂ¯Ã¤Â»Â¥Ã§â€Â¨Ã¦â€“Â¼Ã¨Â³â€¡Ã¦â€“â„¢Ã¥Ë†â€ Ã¦Å¾ÂÃ¯Â¼Å’Ã¤Â½â€ Ã¦ËœÂ¯Ã¦Ë†â€˜Ã¥â‚¬â€˜teamÃ¦Â¯â€Ã¨Â¼Æ’Ã§â€ Å¸Ã¦â€šâ€°PythonÃ£â‚¬â€š` | multiple CJKÃ¢â€ â€Latin switches, some spaced (`RÃ©Æ’Â½` Ã¢â‚¬â€ actually no space here; deliberately includes both a no-space case `Ã¥â€™Å’R` type switch and a spaced case `Ã¦Ë†â€˜Ã¥â‚¬â€˜team`) plus a `CLAUSE` at the full-width colon/comma | ANALYSIS ONLY |
| PE-08-02 | Roadmap-style note mixing a product name, an acronym, and normal CJK narrative | `Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¨Â¨Ë†Ã§â€¢Â«Ã¤Â¸â€¹Ã¤Â¸â‚¬Ã¦Â­Â¥Ã¥Â°Å½Ã¥â€¦Â¥CI/CDÃ¦ÂµÂÃ§Â¨â€¹Ã¯Â¼Å’Ã¥â€¦Ë†Ã§â€Â¨GitHub ActionsÃ¥ÂÅ¡Ã¦Â¸Â¬Ã¨Â©Â¦Ã¯Â¼Å’Ã¤Â¹â€¹Ã¥Â¾Å’Ã¥â€ ÂÃ¨Â©â€¢Ã¤Â¼Â°Ã¥â€¦Â¶Ã¤Â»â€“Ã¦â€“Â¹Ã¦Â¡Ë†Ã£â‚¬â€š` | transition and whitespace evidence coexisting with `CLAUSE` and plain `OTHER`, plus a likely Technical/Atomic-flagged `CI/CD` token (incidental, to be recorded not removed) | ANALYSIS ONLY |

### 16.2 Integrated Positive-Evidence Candidate Set (PE-12)

The highest-value case in this matrix: one realistic paragraph containing all four
locked base classes (`OTHER`, `CLAUSE`, `ELLIPSIS`, `SENTENCE_FINAL`), with several
candidates also carrying Transition and/or Whitespace evidence, mirroring how
`docs/phase2c/calibration/matrices/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_MATRIX.md`'s BC-09 served as that
matrix's primary integrated case.

| Field | Value |
|---|---|
| Case ID | PE-12 |
| Purpose | Exercise the complete base hierarchy and both Positive Evidence factors together in one coherent, realistic paragraph Ã¢â‚¬â€ the single most direct test of "does Positive Evidence remain appropriately proportioned when combined with different Base Classification values" (calibration question 5, Ã‚Â§3) |
| Input text | `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥Å Å¸Ã¨Æ’Â½Ã©â€šâ€žÃ¥Å“Â¨Ã©â€“â€¹Ã§â„¢Â¼Ã¤Â¸Â­Ã¯Â¼Å’Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â½Â¿Ã§â€Â¨PythonÃ¥â€™Å’DockerÃ¥ÂÅ¡Ã¦Â¸Â¬Ã¨Â©Â¦Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã§Â´Â°Ã§Â¯â‚¬Ã¤Â¹â€¹Ã¥Â¾Å’Ã¦Å“Æ’Ã¥â€¦Â¬Ã¥Â¸Æ’Ã£â‚¬â€šÃ¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¦Å“Æ’Ã¥Â±â€¢Ã§Â¤Âº Demo Ã§Â¯â€žÃ¤Â¾â€¹Ã£â‚¬â€š` |
| Expected candidates (not asserted, only anticipated for design purposes) | `OTHER` (plain CJK-CJK, `0.0`) at multiple positions; `CLAUSE` (`Ã¯Â¼Å’`, `35.0`) after `Ã¤Â¸Â­`; `OTHER`+`CJKÃ¢â€ â€™LATIN` (`Ã§â€Â¨Ã¯Â½Å“P`, `15.0`) and `OTHER`+`LATINÃ¢â€ â€™CJK` (`nÃ¯Â½Å“Ã¥â€™Å’`, `15.0`) and `OTHER`+`CJKÃ¢â€ â€™LATIN` again (`Ã¥â€™Å’Ã¯Â½Å“D`, `15.0`) and `OTHER`+`LATINÃ¢â€ â€™CJK` again (`rÃ¯Â½Å“Ã¥ÂÅ¡`, `15.0`) across `Ã¤Â½Â¿Ã§â€Â¨PythonÃ¥â€™Å’DockerÃ¥ÂÅ¡Ã¦Â¸Â¬Ã¨Â©Â¦`; `INTERNAL` (`-20.0`, incidental) inside the `Ã¢â‚¬Â¦Ã¢â‚¬Â¦` run; `ELLIPSIS` (END-state, `65.0`) after the ellipsis run; `SENTENCE_FINAL` (`80.0`, expected non-string-final since followed by more text) after `Ã¥â€¦Â¬Ã¥Â¸Æ’Ã£â‚¬â€š`; `OTHER`+`Whitespace` (`10.0` each side) around the inserted `Demo` in `Ã¥Â±â€¢Ã§Â¤Âº Demo Ã§Â¯â€žÃ¤Â¾â€¹` |
| Evidence requirement | Real pipeline; full candidate dump recorded, not just the anticipated positions above Ã¢â‚¬â€ per this round's "record the complete candidate set" instruction |
| Clean/interaction criteria | This is explicitly an INTERACTION case, not CLEAN Ã¢â‚¬â€ it deliberately combines multiple factors in one text |
| Interpretation criteria | No single KEEP/INCREASE/DECREASE verdict is forced from this one paragraph (matching how BC-09/BC-12 were treated in the Base Classification round); instead, the later round should report whether the joint picture Ã¢â‚¬â€ four base classes plus two Positive Evidence factors, all in proportion to each other Ã¢â‚¬â€ looks like a coherent, usable signal for a hypothetical Phase 2D consumer, and should flag any surprising interaction (e.g. an unexpected reversal) explicitly rather than silently |
| Status | ANALYSIS ONLY (primary integrated diagnostic case, corroborates but does not replace Ã‚Â§7Ã¢â‚¬â€œÃ‚Â§14's pairwise/matched findings) |

## 17. Case Status Rules

Each case in this matrix is assigned exactly one status from the following six,
matching this round's required definitions:

- **CLEAN** Ã¢â‚¬â€ the intended positive factor is isolated sufficiently for calibration
  (no unintended modifier materially affects the target candidate's interpretation).
- **INTERACTION** Ã¢â‚¬â€ the case intentionally tests a combination of evidence factors
  (e.g. PE-07's whitespace+transition triads, PE-12's full integrated set). An
  INTERACTION case is not a failure state Ã¢â‚¬â€ it is a deliberately designed case type,
  distinct from CLEAN by purpose, not by quality.
- **CONTAMINATED** Ã¢â‚¬â€ an unintended factor (most commonly incidental
  Technical/Atomic protection, per Ã‚Â§13) materially affects interpretation of the
  intended comparison. Recorded explicitly, with the incidental evidence stated in
  full; the case is retained (not discarded) and an explanation of why it does or
  does not still support a conclusion is required.
- **CASE ISSUE** Ã¢â‚¬â€ the intended candidate cannot be represented or reached by the
  current pipeline (e.g. Ã‚Â§12.1's predicted `CLAUSE`/`ELLIPSIS`/`SENTENCE_FINAL` +
  Transition cases, and PE-07's predicted-unreachable "transition + whitespace"
  variant). The input text must not be modified repeatedly to try to force
  reachability.
- **NEEDS DATA** Ã¢â‚¬â€ evidence is insufficient to make a meaningful calibration
  judgment, whether because contamination prevents isolation (and the case cannot be
  meaningfully interpreted even with the contamination recorded) or because too few
  independent cases exist for the specific question asked.
- **ANALYSIS ONLY** Ã¢â‚¬â€ a useful diagnostic observation (most of Ã‚Â§14's neighborhood
  cases, Ã‚Â§15's negative-whitespace cases, Ã‚Â§16's natural/integrated cases), but not by
  itself sufficient to support a numeric KEEP/INCREASE/DECREASE decision. A single
  ANALYSIS ONLY case must never be used, alone, to justify a numeric conclusion.

A CLEAN case and an INTERACTION case are never conflated: this matrix does not mix
"isolate the factor as much as possible" cases with "deliberately combine factors"
cases inside the same case ID. Where both are useful for the same underlying
question (e.g. Ã‚Â§11's transition-only vs. whitespace-only vs. transition+whitespace
triads), they are given separate case IDs (PE-07-01a/b/c) rather than one case
serving both purposes.

Every status shown in the case tables above (Ã‚Â§7Ã¢â‚¬â€œÃ‚Â§16) is a **prediction**, drawn
either from existing evidence (Ã‚Â§5.1) or from structural reasoning extended from that
evidence, explicitly labeled as such. No status is asserted as a final, executed
result Ã¢â‚¬â€ that is the job of the later execution round.

## 18. Required Evidence

Each case in Ã‚Â§7Ã¢â‚¬â€œÃ‚Â§16 defines, either per-case or via an explicitly stated group-level
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
  provisional baseline, e.g. `0+15=15`, `35+10=45` Ã¢â‚¬â€ an arithmetic consequence to be
  checked, never a proposed new value)
- **Base Classification score** (the fixed, locked input from Ã‚Â§2.1)
- **Calibration question**
- **Evidence requirements**
- **Clean / interaction criteria**
- **Interpretation criteria**
- **Predicted status** (Ã‚Â§17)

A later execution round must additionally record, for every actually-executed case
(per the "avoid false isolation" instruction): any Technical, Atomic, INTERNAL,
transition, or whitespace evidence present on the target candidate that was not the
one being intentionally tested, exactly as `docs/phase2c/calibration/reports/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_ROUND1_REPORT.md`
Ã‚Â§8 did for incidental `INTERNAL` evidence in that round. Nothing is silently dropped.

## 19. Calibration Interpretation

A later execution round records exactly one of the following for each numeric
question this matrix feeds (never a specific replacement number):

- **KEEP** Ã¢â‚¬â€ the current value appears appropriately calibrated based on the
  gathered evidence.
- **INCREASE** Ã¢â‚¬â€ the evidence suggests the current value is too weak relative to
  what it is being compared against.
- **DECREASE** Ã¢â‚¬â€ the evidence suggests the current value is too strong relative to
  what it is being compared against.
- **NEED MORE DATA** Ã¢â‚¬â€ the evidence gathered is insufficient to support any of the
  above three verdicts.

**BAD** (not permitted in a later round, illustrating the distinction this document
must preserve): *"Change CJK Ã¢â€ â€™ LATIN from +15 to +20."* *"Whitespace should become
+5."* *"LATIN Ã¢â€ â€™ CJK should become +10."*

**GOOD**: *"CJK Ã¢â€ â€™ LATIN's +15 appears proportionate relative to plain OTHER and well
below CLAUSE, based on PE-01/PE-03/PE-09 Ã¢â€ â€™ KEEP."* *"The Transition+Whitespace
interaction never actually produces an additive +25 candidate (PE-07) Ã¢â€ â€™ this is
recorded as a structural finding, not evaluated as KEEP/INCREASE/DECREASE, since
there is no such candidate to calibrate."*

If a case's observation seems to suggest a base-classification value (not a Positive
Evidence value) is miscalibrated Ã¢â‚¬â€ for example, if PE-06-CLAUSE's `45.0` seems to
crowd too closely against `ELLIPSIS`'s `65.0` Ã¢â‚¬â€ that observation is recorded as **OUT
OF CURRENT SCOPE**, explicitly attributed to the base layer, and not acted upon here.
It belongs to a future, separately-scoped Base Classification round, not to Positive
Evidence Calibration.

## 20. Completion Criteria

This matrix is complete when the following are all true:

1. CJK Ã¢â€ â€™ LATIN is covered by multiple realistic cases. Ã¢Å“â€œ Ã‚Â§7 (PE-01-01Ã¢â‚¬â€œ03), plus
   Ã‚Â§9/Ã‚Â§11/Ã‚Â§13 additional independent occurrences.
2. LATIN Ã¢â€ â€™ CJK is covered by multiple realistic cases. Ã¢Å“â€œ Ã‚Â§8 (PE-02-01Ã¢â‚¬â€œ03), plus
   Ã‚Â§9/Ã‚Â§11/Ã‚Â§13.
3. Transition symmetry has matched cases. Ã¢Å“â€œ Ã‚Â§9 (PE-03-01Ã¢â‚¬â€œ03), same-sentence matched
   pairs.
4. Whitespace has isolated cases. Ã¢Å“â€œ Ã‚Â§10 (PE-05-01Ã¢â‚¬â€œ04), all four character-class
   combinations.
5. Whitespace has realistic non-useful cases. Ã¢Å“â€œ Ã‚Â§15 (PE-11-01Ã¢â‚¬â€œ03).
6. Transition + Whitespace interaction is covered. Ã¢Å“â€œ Ã‚Â§11 (PE-07, matched triads both
   directions).
7. Positive Evidence is tested against all four locked Base Classes. Ã¢Å“â€œ Ã‚Â§12 (PE-04
   for Transition, PE-06 for Whitespace, each against `OTHER`/`CLAUSE`/`ELLIPSIS`/
   `SENTENCE_FINAL`).
8. Punctuation interaction is covered. Ã¢Å“â€œ Ã‚Â§14 (PE-10-01Ã¢â‚¬â€œ03).
9. Technical / product terminology is covered without recalibrating protection. Ã¢Å“â€œ
   Ã‚Â§13 (PE-09-01Ã¢â‚¬â€œ05), explicitly distinguishing clean from contaminated cases and
   never proposing a protection-value change.
10. At least one integrated realistic paragraph contains multiple Base Classes and
    Positive Evidence. Ã¢Å“â€œ Ã‚Â§16.2 (PE-12).
11. Existing evidence is distinguished from new cases. Ã¢Å“â€œ Ã‚Â§5.1 (EE-1Ã¢â‚¬â€œEE-8, each
    tagged EXISTING EVIDENCE and cited by ID wherever a new case tests the same
    ground independently).
12. Cases distinguish CLEAN from INTERACTION. Ã¢Å“â€œ every case table states a predicted
    status per Ã‚Â§17; CLEAN and INTERACTION are never assigned to the same case ID.
13. No numeric value is changed. Ã¢Å“â€œ Ã‚Â§2.1/Ã‚Â§2.2 values are stated as fixed inputs and
    provisional-baseline references only; no replacement value appears anywhere in
    this document.
14. No new scoring factor is introduced. Ã¢Å“â€œ Ã‚Â§4 explicitly excludes every factor named
    in this round's scope restriction.
15. No production code is modified. Ã¢Å“â€œ this document is the sole file created.
16. No existing artifact is modified. Ã¢Å“â€œ confirmed in the final response accompanying
    this document.
17. The matrix is suitable for a later execution round. Ã¢Å“â€œ every case specifies
    input text, target boundary, expected/predicted evidence, and evidence
    requirements sufficient to run against the real, unmodified pipeline using the
    existing `dump()`-style calibration infrastructure, following the same pattern
    already used for Base Classification Calibration Round 1.
