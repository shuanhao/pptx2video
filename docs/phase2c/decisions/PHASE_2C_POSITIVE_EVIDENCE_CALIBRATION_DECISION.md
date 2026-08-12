# Phase 2C Positive Evidence Calibration Decision

**Status:** Design Decision Ã¢â‚¬â€ documentation only, no code/test/script/matrix changes
**Phase:** Phase 2C Ã¢â‚¬â€ Numeric Calibration (Positive Evidence)
**Purpose:** Lock the Positive Evidence numeric model based on completed Round 1
calibration evidence.

---

## 1. Purpose

`docs/phase2c/calibration/reports/PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_ROUND1_REPORT.md` executed the full
Positive Evidence Calibration Matrix (PE-01Ã¢â‚¬â€œPE-12) against the real, unmodified
pipeline and recorded `KEEP` for all three provisional Positive Evidence values, plus
several structural findings about how those values interact with the locked Base
Classification layer and with each other. This document converts that completed
empirical evidence into formal, locked design decisions, so that Positive Evidence
numeric calibration is closed and future work has one unambiguous reference point Ã¢â‚¬â€
mirroring exactly how `docs/phase2c/decisions/PHASE_2C_NUMERIC_BASELINE_DECISION.md` established the
original provisional baseline and how a Base Classification decision (see Ã‚Â§3, Ã‚Â§9)
was intended to close the base-classification calibration question.

This document does not gather new evidence, does not re-run any calibration, and does
not reinterpret the Round 1 report's findings beyond the single documentation
correction described in Ã‚Â§12.

## 2. Decision Scope

This is a documentation-only round. It creates exactly one new file:
`docs/phase2c/decisions/PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_DECISION.md`. It does not modify, rename,
or delete any existing file; does not implement Phase 2C production scoring; does not
execute another calibration round; does not enter Phase 2D.

In scope: formally locking `CJK Ã¢â€ â€™ LATIN`, `LATIN Ã¢â€ â€™ CJK`, `Whitespace`, transition
symmetry, whitespace non-stacking, and the structural interaction findings from Round 1
(Ã‚Â§6). Out of scope: Base Classification magnitudes (already locked, referenced only as
a fixed input Ã¢â‚¬â€ see Ã‚Â§4, Ã‚Â§9), Protection magnitudes (referenced only as a fixed input Ã¢â‚¬â€
see Ã‚Â§9), any new scoring factor, any threshold/normalization/floor, any Phase 2D
question (Ã‚Â§10).

## 3. Authoritative Inputs

- `docs/PHASE_2C_NUMERIC_BASELINE_DECISION.md` Ã¢â‚¬â€ established the original provisional
  Numeric Baseline v0.1, including the Positive Evidence values this document now
  locks.
- `docs/phase2c/calibration/matrices/PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_MATRIX.md` Ã¢â‚¬â€ designed the PE-01Ã¢â‚¬â€œPE-12
  case groups this decision is based on.
- `docs/phase2c/calibration/reports/PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_ROUND1_REPORT.md` Ã¢â‚¬â€ the **authoritative
  empirical evidence** for every decision in this document. Every numeric claim below
  traces back to a specific section of that report.

**Note on `docs/phase2c/calibration/matrices/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_MATRIX.md`:** this round's
own instructions reference this filename, with the explicit caveat "if absent, do not
create it in this round." Repository inspection confirms it does not exist Ã¢â‚¬â€ only
`docs/phase2c/calibration/reports/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_ROUND1_REPORT.md` exists, which itself
recorded `KEEP` for all three base-classification margins on real-pipeline evidence.
Per the round's own instruction, this document does not create the missing file; Ã‚Â§4
below treats the Round 1 Report's `KEEP` findings, together with
`docs/PHASE_2C_NUMERIC_BASELINE_DECISION.md`'s original adoption, as the basis for
treating the base layer as locked/fixed for this document's purposes. This is the same
factual, non-blocking handling used for this exact discrepancy in
`docs/phase2c/calibration/matrices/PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_MATRIX.md` Ã‚Â§1.

## 4. Locked Base Classification Baseline

Referenced here as a **fixed input only** Ã¢â‚¬â€ not re-decided, not re-opened, not
recalibrated by this document:

| BoundaryClass | Base Score | Status |
|---|---:|---|
| `SENTENCE_FINAL` | +80 | LOCKED |
| `ELLIPSIS` | +65 | LOCKED |
| `CLAUSE` | +35 | LOCKED |
| `OTHER` | 0 | LOCKED |

## 5. Positive Evidence Decisions

### 5.1 CJK Ã¢â€ â€™ LATIN

**Decision: LOCKED at +15.**

Round 1 (Ã‚Â§5 of the Round 1 Report) observed `CJKÃ¢â€ â€™LATIN` scoring exactly `15.0` in
every clean, no-space case tested: PE-01's three independent realistic sentences
(Ã‚Â§4.1), the CJKÃ¢â€ â€™LATIN side of PE-03's three same-sentence symmetry pairs (Ã‚Â§4.3), and
PE-09's two clean product-terminology cases (Ã‚Â§4.8) Ã¢â‚¬â€ multiple independent CLEAN
observations, plus additional incidental confirmations in PE-04-OTHER, PE-08, and
PE-10. No case, clean or contaminated, ever observed `CJKÃ¢â€ â€™LATIN` at a value other than
exactly `15.0`, and no case showed it reversed or disproportionate against the `OTHER`
base (`0`). This document locks `+15` on that basis.

### 5.2 LATIN Ã¢â€ â€™ CJK

**Decision: LOCKED at +15.**

Round 1 (Ã‚Â§6 of the Round 1 Report) found the identical pattern in the reverse
direction: PE-02's three independent cases (Ã‚Â§4.2), the `LATINÃ¢â€ â€™CJK` side of PE-03's
three symmetry pairs (Ã‚Â§4.3), plus incidental confirmations elsewhere Ã¢â‚¬â€ multiple
independent CLEAN observations, all scoring exactly `15.0`, never reversed. This
document locks `+15` on that basis.

### 5.3 Transition Symmetry

**Decision: LOCKED / SUPPORTED.**

This is explicitly **not** justified merely because both provisional values happened
to share the number `+15` Ã¢â‚¬â€ that would be numeric equality, not evidence-supported
symmetry, and this document treats those as two different claims (per Round 1 Ã‚Â§7).

The supporting evidence is PE-03 (Round 1 Report Ã‚Â§4.3, Ã‚Â§7): three independent
sentences, each containing one Latin word sandwiched between CJK text with no spaces
on either side, so that in a **single real pipeline run per sentence**, both the
`CJKÃ¢â€ â€™LATIN` candidate and the `LATINÃ¢â€ â€™CJK` candidate for the same embedded word were
observed together Ã¢â‚¬â€ same sentence, same textual context, same Base Classification
environment, same (absent) protection state, no whitespace on either side. In all
three cases both candidates scored exactly `15.0`, with identical incidental-modifier
profiles (`tech=False`, `atomic=False`, `ws=0.0`, `internal=False` on both sides in
every case). PE-08-01's natural, unengineered three-transition sequence around a
single-letter token (Ã‚Â§4.11 of the Round 1 Report) reproduced the same identical-score
pattern outside of any constructed minimal pair.

This document formally locks `CJK Ã¢â€ â€™ LATIN = LATIN Ã¢â€ â€™ CJK = +15`, with **Transition
symmetry = SUPPORTED**, on the strength of same-context, same-run, real-pipeline
evidence Ã¢â‚¬â€ not on the coincidence of a shared provisional number.

### 5.4 Whitespace

**Decision: LOCKED at +10.**

Round 1 (Ã‚Â§8 of the Round 1 Report) confirmed `Whitespace` scoring exactly `+10` per
candidate across all four character-class combinations tested in PE-05 (CJK+ws+CJK,
CJK+ws+Latin, Latin+ws+CJK, Latin+ws+Latin Ã¢â‚¬â€ Ã‚Â§4.4) and, newly for Round 1, across all
four locked Base Classes in PE-06 (Ã‚Â§4.7), with the following actual observed total
scores:

| Base Classification | Whitespace-attached score |
|---|---:|
| `OTHER` | 10 |
| `CLAUSE` | 45 |
| `ELLIPSIS` | 75 |
| `SENTENCE_FINAL` | 90 |

Every one of these matches the base value plus exactly `10` Ã¢â‚¬â€ `0+10=10`, `35+10=45`,
`65+10=75`, `80+10=90` Ã¢â‚¬â€ confirming Whitespace is structurally compatible with, and
additive on top of, every current Base Classification value. This document locks
`+10` on that basis.

## 6. Structural Interaction Decisions

### 6.1 Whitespace Non-Stacking

**Formally recorded:** Whitespace is a flat, candidate-level `+10` modifier. It does
**not** stack, accumulate, or scale with the number of whitespace characters present.

Evidence: PE-05 (Round 1 Report Ã‚Â§4.4, Ã‚Â§8), specifically PE-05-04, where three separate
space characters in one text produced four separate whitespace-adjacent candidates,
**every one of which scored exactly `10.0`** Ã¢â‚¬â€ no candidate scored `20.0`, `30.0`, or
any multiple. This document formally locks the flat, non-stacking behavior of
Whitespace and does **not** introduce a distance-based or count-based whitespace
modifier of any kind.

### 6.2 Transition + Whitespace

**Formally recorded structural finding:** Transition and Whitespace evidence **cannot
co-occur on a single real `BoundaryCandidate`** under the current candidate model.
Therefore **`+25` is not a calibration target** Ã¢â‚¬â€ it is not merely unobserved in
Round 1's cases, it is unreachable by construction.

Evidence and mechanism (Round 1 Report Ã‚Â§9, Ã‚Â§17 finding 1): PE-07's matched triads
(Ã‚Â§4.5) showed the no-space variant of a given language switch scoring `15.0`
(transition only) and the whitespace variant of the *same underlying switch* scoring
`10.0`+`10.0` split across two separate candidates (whitespace only, no transition on
either) Ã¢â‚¬â€ never a single `25.0` candidate. This is confirmed structural, not merely
empirical: the transition bonus requires `left_character_class` and
`right_character_class` to both be in `{CJK, LATIN}`; the whitespace bonus requires
one of those same two fields to equal `WHITESPACE`. A single character-class field
cannot simultaneously satisfy both conditions, so no real candidate can ever carry
both modifiers at once.

This document does **not** define `Transition + Whitespace = +25` and does **not**
propose an alternative value. This is a structural decision about candidate
architecture, not a numeric calibration decision.

### 6.3 Transition Ãƒâ€” Base Classification

**Formally recorded reachability:**

| Combination | Reachability |
|---|---|
| `OTHER` + Transition | **Reachable** |
| `CLAUSE` + Transition | **Unreachable** |
| `ELLIPSIS` + Transition | **Unreachable** |
| `SENTENCE_FINAL` + Transition | **Unreachable** |

Evidence and mechanism (Round 1 Report Ã‚Â§4.6, Ã‚Â§10, Ã‚Â§17 finding 2): PE-04 placed a Latin
character immediately after a clause comma, an ellipsis run's end, and a
sentence-final mark, with no space in each case. In all three, the resulting candidate
scored exactly its plain base value (`35.0`/`65.0`/`80.0`) with zero transition
contribution Ã¢â‚¬â€ confirmed, not merely predicted. The mechanism is the same
character-class precondition as Ã‚Â§6.2: `CLAUSE`, `ELLIPSIS` (END-state), and
`SENTENCE_FINAL` candidates always have the relevant punctuation mark Ã¢â‚¬â€ character
class `PUNCTUATION` Ã¢â‚¬â€ on one side, and `PUNCTUATION` is never `CJK`/`LATIN`.

The hypothetical arithmetic values that *would* result if this combination were
reachable are explicitly labeled **hypothetical / unreachable under the current
candidate architecture** and are **not** calibration targets:

```
CLAUSE + Transition           = 35 + 15 = 50   (hypothetical, unreachable)
ELLIPSIS + Transition         = 65 + 15 = 80   (hypothetical, unreachable)
SENTENCE_FINAL + Transition   = 80 + 15 = 95   (hypothetical, unreachable)
```

This finding is **not** interpreted as evidence that any Base Classification value is
wrong. It is a statement about which candidates the current architecture can produce,
not about whether `+35`/`+65`/`+80` are the right magnitudes.

### 6.4 Whitespace Ãƒâ€” Base Classification

**Formally recorded reachability:** `OTHER` + Whitespace, `CLAUSE` + Whitespace,
`ELLIPSIS` + Whitespace, and `SENTENCE_FINAL` + Whitespace are **all reachable** Ã¢â‚¬â€
confirmed in Ã‚Â§5.4 above and Round 1 Report Ã‚Â§4.7, Ã‚Â§10.

This is an important structural contrast with Ã‚Â§6.3: unlike Transition, Whitespace's
precondition (either side being `WHITESPACE`-class) does not depend on the
punctuation-vs-letter distinction that blocks Transition from attaching to
punctuation-anchored classes. No new numeric factor is inferred from this contrast Ã¢â‚¬â€
it is recorded purely as a structural observation about how the two Positive Evidence
factors differ in their compatibility with the base layer.

## 7. Final Positive Evidence Numeric Model

| Evidence | Score | Status |
|---|---:|---|
| CJK Ã¢â€ â€™ LATIN | +15 | LOCKED |
| LATIN Ã¢â€ â€™ CJK | +15 | LOCKED |
| Whitespace | +10 | LOCKED |

Base layer, referenced as a fixed input (Ã‚Â§4):

| BoundaryClass | Base Score | Status |
|---|---:|---|
| SENTENCE_FINAL | +80 | LOCKED |
| ELLIPSIS | +65 | LOCKED |
| CLAUSE | +35 | LOCKED |
| OTHER | 0 | LOCKED |

Protection, referenced as a fixed input, unchanged and out of scope for this document
(Ã‚Â§9):

| Factor | Value | Status |
|---|---:|---|
| Technical | -30 | LOCKED (behaviorally supported, per `docs/phase2c/decisions/PHASE_2C_NUMERIC_BASELINE_DECISION.md`) |
| Atomic | -30 | LOCKED (behaviorally supported) |
| INTERNAL | -20 | LOCKED (behaviorally supported) |

## 8. Relative Score Examples

Only actual, reachable combinations supported by Round 1 evidence are listed as
examples:

```
OTHER + CJKÃ¢â€ â€™LATIN        = 0 + 15  = 15
OTHER + LATINÃ¢â€ â€™CJK        = 0 + 15  = 15
OTHER + Whitespace       = 0 + 10  = 10
CLAUSE + Whitespace      = 35 + 10 = 45
ELLIPSIS + Whitespace    = 65 + 10 = 75
SENTENCE_FINAL + Whitespace = 80 + 10 = 90
```

The following combinations are **not** examples of the numeric model Ã¢â‚¬â€ they are
unreachable hypotheticals recorded only for completeness in Ã‚Â§6.2/Ã‚Â§6.3, and must not be
read as calibrated relative scores:

```
Transition + Whitespace                (any base class)  = unreachable, not +25
CLAUSE + Transition                    = unreachable, not 50
ELLIPSIS + Transition                  = unreachable, not 80
SENTENCE_FINAL + Transition            = unreachable, not 95
```

## 9. Out-of-Scope Findings

The following observations from the Round 1 Report are recorded here for
completeness, exactly as that report recorded them, and are **not** acted upon by
this document:

- **PE-09-04's version-string span-coverage gap** (`v1.2.3`): Phase 1's
  `atomic/numeric` span covers only the `1.2` portion of the embedded version string,
  leaving the second period uncovered and subject to the bare-ASCII-fallback
  `SENTENCE_FINAL` classification. This is a Base Classification / Phase 1 structural
  detection finding, not a Positive Evidence finding. Phase 1 is not modified by this
  document.
- **PE-08-02's `CI/CD` non-detection**: the hyphen-free, slash-containing token
  produced no `technical`/`atomic` flag anywhere, unlike the hyphenated `GPT-4`
  (PE-09-05) or the digit run `iPhone 15` (PE-09-03). This is a Protection-layer /
  Phase 1 pattern-detection observation. Protection values (`Technical=-30`,
  `Atomic=-30`, `INTERNAL=-20`) are not modified by this document.
- These findings may be useful input to a future, separately-scoped round if either
  the base-classification span-coverage behavior or the protection pattern-detection
  behavior is ever revisited Ã¢â‚¬â€ this document does not schedule or require such a
  round.

## 10. Deferred Phase 2D Questions

This Decision does **not** determine:

- whether a candidate should actually be cut
- subtitle duration
- subtitle line length
- DP optimization
- thresholding
- candidate selection
- tie-breaking
- semantic phrase integrity
- whitespace suppression
- integration into `subtitle_segmenter.py`

Those belong to later phases (Phase 2D and beyond), not to Phase 2C numeric
calibration.

In particular, the **semantic usefulness of whitespace** Ã¢â‚¬â€ the qualitative
observation from PE-11 (Round 1 Report Ã‚Â§13) that some whitespace positions (e.g. the
internal space in `Microsoft Word`, line-wrap-like spaces, or other phrase/product-
name-internal spaces) are mechanically indistinguishable from meaningful whitespace
boundaries even though a person would rarely choose to cut there Ã¢â‚¬â€ is explicitly
**deferred**, not resolved, by this document. Round 1's mechanical evidence (Ã‚Â§5.4, Ã‚Â§6.1
above) is strong and is the basis for locking `+10`; the deferred question is whether
and how a *later* phase (most plausibly Phase 2D, which is responsible for turning
relative scores into actual cut decisions) should treat semantically weak whitespace
positions differently from strong ones. This document does not decrease or increase
`+10` on the basis of that deferred question Ã¢â‚¬â€ per Round 1's own explicit instruction,
"some whitespace positions are poor subtitle boundaries" is not converted into "`+10`
is wrong."

## 11. Decision Summary

**Formally LOCKED (numeric decisions):**

- PE-01 `CJK Ã¢â€ â€™ LATIN` = `+15`
- PE-02 `LATIN Ã¢â€ â€™ CJK` = `+15`
- PE-03 Transition symmetry (`CJK Ã¢â€ â€™ LATIN = LATIN Ã¢â€ â€™ CJK = +15`) Ã¢â‚¬â€ SUPPORTED
- PE-04 `Whitespace` = `+10`
- PE-05 Whitespace non-stacking (flat, candidate-level, not distance/count-based)

**Formally recorded as LOCKED STRUCTURAL FINDINGS (architectural facts, not numeric
decisions):**

- PE-06 Transition + Whitespace is unreachable on a single real candidate; `+25` is
  not a calibration target
- PE-07 Transition cannot combine with `CLAUSE`/`ELLIPSIS`/`SENTENCE_FINAL` on a
  single real candidate
- PE-08 Whitespace can combine with all four locked Base Classes
  (`OTHER`/`CLAUSE`/`ELLIPSIS`/`SENTENCE_FINAL`)

**Remains DEFERRED (not locked, not resolved):**

- Semantic usefulness of whitespace (Ã‚Â§10) Ã¢â‚¬â€ a Phase 2D question

## 12. Calibration Evidence Quality

Per the Round 1 Report's own confidence assessment (Ã‚Â§19), evidence for `CJKÃ¢â€ â€™LATIN`,
`LATINÃ¢â€ â€™CJK`, and their symmetry is **Strong**: multiple independent, clean, real-
pipeline, same-context observations, zero contradicting evidence, zero reversal.
Evidence for Whitespace's mechanical behavior (flat, non-stacking, reachable against
all four base classes) is likewise **Strong**, confirmed across eight independent
cases with exact arithmetic matches in every reachable combination. Evidence for
Whitespace's overall numeric appropriateness, once semantic usefulness is considered,
remains **Moderate** Ã¢â‚¬â€ the mechanical case is strong, but the qualitative question in
Ã‚Â§10 was deliberately left unresolved, per instruction, rather than folded into the
numeric decision.

**Documentation correction (this document only):** the Round 1 Report's Ã‚Â§5 states
"Across nine independent CLEAN observations..." for `CJKÃ¢â€ â€™LATIN`. The explicitly listed
independent CLEAN cases in that same paragraph are PE-01 (3 cases) + PE-03 (3 cases,
the `CJKÃ¢â€ â€™LATIN` side of each symmetry pair) + PE-09 (2 cases) = 8, not 9. This is a
counting discrepancy in the Round 1 Report's own wording. Per this round's explicit
instruction, `docs/phase2c/calibration/reports/PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_ROUND1_REPORT.md` is **not**
modified to fix this Ã¢â‚¬â€ it is left exactly as it was produced, consistent with this
project's established practice of not silently rewriting historical documents (see
`docs/phase2c/decisions/PHASE_2C_NUMERIC_BASELINE_DECISION.md` Ã‚Â§11 for the precedent). This document
instead avoids repeating the disputed "nine" figure and uses "multiple independent
CLEAN observations, plus additional incidental observations" throughout Ã‚Â§5.1Ã¢â‚¬â€œÃ‚Â§5.2,
which is accurate regardless of whether the correct count is 8 or 9 and does not
depend on resolving the discrepancy. The underlying **decision is unaffected**: whether
the correct count is 8 or 9, the evidence is multiple independent, clean, unreversed,
uncontradicted observations, which is what supports the `LOCKED` status in Ã‚Â§5.1/Ã‚Â§5.2.

## 13. Consequences

After this Decision, **Positive Evidence numeric calibration is closed.** The
following values are now fixed:

```
CJK Ã¢â€ â€™ LATIN    = +15
LATIN Ã¢â€ â€™ CJK    = +15
Whitespace     = +10
```

Future work must not casually change these values. Any future change to any of the
three requires a new, explicitly-scoped calibration and design decision Ã¢â‚¬â€ it is not
authorized as an implementation preference, a refactor side-effect, or an
unstated assumption in a later phase. The structural findings in Ã‚Â§6 (Transition +
Whitespace unreachable, Transition incompatible with punctuation-anchored classes,
Whitespace compatible with all base classes) are not numeric decisions and do not
themselves lock any future architecture Ã¢â‚¬â€ they may still validly inform later design
discussions (for example, if a future round considers redesigning the candidate model
itself, these findings describe the *current* model's behavior, not a requirement that
the future model preserve it).

## 14. Non-Goals

This document does **not**:

- Authorize modification of production code, tests, existing calibration scripts,
  existing calibration matrices, or existing calibration reports.
- Recalibrate or reopen Base Classification (`SENTENCE_FINAL`/`ELLIPSIS`/`CLAUSE`/
  `OTHER`) Ã¢â‚¬â€ those remain locked exactly as referenced in Ã‚Â§4, on the basis of
  `docs/phase2c/decisions/PHASE_2C_NUMERIC_BASELINE_DECISION.md` and
  `docs/phase2c/calibration/reports/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_ROUND1_REPORT.md`'s own findings.
- Recalibrate or reopen Protection (`Technical`/`Atomic`/`INTERNAL`) Ã¢â‚¬â€ those remain
  locked exactly as referenced in Ã‚Â§7/Ã‚Â§9.
- Introduce any new scoring factor, threshold, normalization step, or class-specific
  hard floor. Phase 2C's numeric strategy remains a **signed relative score**: no
  normalization, no threshold (no `score >= X Ã¢â€ â€™ cut` decision), no class-specific hard
  floor. Positive Evidence remains additive evidence contributing to that relative
  score Ã¢â‚¬â€ it is not itself a segmentation decision.
- Resolve the semantic-usefulness-of-whitespace question (Ã‚Â§10) Ã¢â‚¬â€ explicitly deferred.
- Resolve the two out-of-scope findings in Ã‚Â§9 (`v1.2.3` span coverage, `CI/CD`
  non-detection) Ã¢â‚¬â€ explicitly out of scope.
- Begin Phase 2C production scoring implementation, or Phase 2D integration.

## 15. Next Phase

Phase 2C Positive Evidence numeric calibration is complete. Phase 2C now has locked:

- **Base Classification** (`docs/phase2c/decisions/PHASE_2C_NUMERIC_BASELINE_DECISION.md`,
  `docs/phase2c/calibration/reports/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_ROUND1_REPORT.md`)
- **Positive Evidence** (this document)
- **Protection calibration inputs** (`docs/phase2c/calibration/reports/PHASE_2C_PROTECTION_CALIBRATION_ROUND1_REPORT.md`,
  `docs/phase2c/calibration/reports/PHASE_2C_PROTECTION_POST_CORRECTION_VERIFICATION_REPORT.md`)
- **Numeric strategy** (signed relative score, no threshold/normalization/floor,
  strongest-only Technical+Atomic combination, additive INTERNAL stacking Ã¢â‚¬â€ per
  `docs/phase2c/decisions/PHASE_2C_NUMERIC_BASELINE_DECISION.md` Ã‚Â§5)

The next work should be a **Phase 2C overall reconciliation / final scoring-model
review** Ã¢â‚¬â€ consolidating all locked inputs (base, positive evidence, protection,
interaction rules, and the structural findings recorded in Ã‚Â§6 of this document) into
one coherent picture Ã¢â‚¬â€ before any production scoring implementation or Phase 2D
integration begins. This document does not perform that reconciliation and does not
implement that next phase.
