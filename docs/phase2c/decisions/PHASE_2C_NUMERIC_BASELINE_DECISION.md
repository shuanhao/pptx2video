# Phase 2C Numeric Baseline Decision

**Status:** Baseline Decision Ã¢â‚¬â€ documentation only, no code/test/script/matrix changes
**Phase:** Phase 2C Ã¢â‚¬â€ Numeric Calibration
**Purpose:** Establish one authoritative provisional numeric baseline ("Phase 2C
Numeric Baseline v0.1") from the values the repository already uses consistently,
and audit the repository for consistency before Numeric Calibration begins.

---

## 1. Purpose

Protection Calibration (Technical/Atomic/INTERNAL) is now behaviorally stable (per
`docs/phase2c/calibration/reports/PHASE_2C_PROTECTION_POST_CORRECTION_VERIFICATION_REPORT.md`). Before proceeding to
general Numeric Calibration, this document establishes one unambiguous, named
numeric baseline, and records a full audit of every existing Phase 2C artifact's
numeric values so that any discrepancy is documented rather than silently carried
forward.

## 2. Scope

This is a documentation-only round. It creates exactly one new file:
`docs/phase2c/decisions/PHASE_2C_NUMERIC_BASELINE_DECISION.md`. It does not modify, rename, or delete
any existing file; does not implement Phase 2C production scoring; does not perform
Numeric Calibration; does not touch Phase 2D.

## 3. Historical Context

The numeric values below have been used, without alteration, across every
calibration round performed so far:

- **Phase 2C Numeric Calibration Round 1** (`docs/phase2c/calibration/reports/PHASE_2C_NUMERIC_CALIBRATION_ROUND1_REPORT.md`,
  `scripts/phase2c/calibrate_numeric_round1.py`, against
  `docs/PHASE_2C_CALIBRATION_MATRIX.md` v0.1 content as it existed at that time).
- **Phase 2C Numeric Calibration Round 2** (`docs/phase2c/calibration/reports/PHASE_2C_NUMERIC_CALIBRATION_ROUND2_REPORT.md`,
  `scripts/phase2c/calibrate_numeric_round2.py`, against
  `docs/PHASE_2C_CALIBRATION_MATRIX.md` v0.2 content, which superseded v0.1 in place).
- **Phase 2C Protection Calibration Round 1** (`docs/phase2c/calibration/reports/PHASE_2C_PROTECTION_CALIBRATION_ROUND1_REPORT.md`,
  `scripts/phase2c/calibrate_protection_round1.py`, against
  `docs/phase2c/calibration/matrices/PHASE_2C_PROTECTION_CALIBRATION_MATRIX.md`).
- **Phase 2C Protection Post-Correction Verification**
  (`docs/phase2c/calibration/reports/PHASE_2C_PROTECTION_POST_CORRECTION_VERIFICATION_REPORT.md`), re-running the same
  unmodified protection script after the Phase 2A upstream correction
  (`docs/phase2c/decisions/PHASE_2C_ASCII_PERIOD_UPSTREAM_CORRECTION_DECISION.md`).

Every one of these artifacts independently arrived at, and consistently reused, the
same base/positive/protection values Ã¢â‚¬â€ see Ã‚Â§10 for the full evidence table.

**Note on file naming:** this round's own instructions repeatedly reference
`docs/Phase_2C_Calibration_Matrix_v0.1.md` and `docs/Phase_2C_Calibration_Matrix_v0.2.md`
as if they were two separate, currently-existing files. Repository inspection (Ã‚Â§10)
confirms **no such files exist**. Only one file,
`docs/PHASE_2C_CALIBRATION_MATRIX.md`, exists; its content was v0.1 at the time of
Numeric Calibration Round 1 and was later overwritten in place with v0.2 content
(which the file itself states "Supersedes: Phase 2C Calibration Matrix v0.1") ahead
of Numeric Calibration Round 2. The original v0.1 text is not separately preserved as
a standalone repository file Ã¢â‚¬â€ it exists only as quoted/summarized content inside
`docs/phase2c/calibration/reports/PHASE_2C_NUMERIC_CALIBRATION_ROUND1_REPORT.md`. This is recorded factually here, not
corrected or altered, per this round's explicit prohibition on renaming, recreating,
or reconstructing historical files.

## 4. Current Numeric Baseline

### 4.1 Base Classification Scores

| Factor | Value |
|---|---:|
| `SENTENCE_FINAL` | +80 |
| `ELLIPSIS` | +65 |
| `CLAUSE` | +35 |
| `OTHER` | 0 |

### 4.2 Positive Evidence

| Factor | Value |
|---|---:|
| CJK Ã¢â€ â€™ LATIN | +15 |
| LATIN Ã¢â€ â€™ CJK | +15 |
| Whitespace | +10 |

### 4.3 Protection Evidence

| Factor | Value |
|---|---:|
| Technical | -30 |
| Atomic | -30 |
| INTERNAL | -20 |

## 5. Interaction Rules

| Interaction | Rule |
|---|---|
| Technical + Atomic | Strongest-only: `max_penalty(Technical, Atomic) = -30` (not additive `-60`) |
| Technical / Atomic + INTERNAL | Independent additive stacking: e.g. `Technical + INTERNAL = -50` |

## 6. Score Semantics

Phase 2C scores are **signed relative boundary preferences**. They are not
probabilities, confidence percentages, cut probabilities, or normalized scores.
`SENTENCE_FINAL = +80` means a strong positive boundary preference relative to other
candidates Ã¢â‚¬â€ it does not mean "80% likely to be a cut point." Likewise,
`Technical = -30` means a negative relative boundary preference Ã¢â‚¬â€ it does not mean "30%
probability of not cutting." Scores are only meaningful in comparison to other
scores produced by the same formula; no absolute interpretation is defined or implied.

## 7. Disabled Mechanisms

The following remain explicitly absent from Phase 2C, by design, and this document
does not introduce any of them:

- No class-specific hard floor
- No normalization
- No threshold (no `score >= X Ã¢â€ â€™ cut` / `score < X Ã¢â€ â€™ don't cut` decision)

Phase 2C computes relative scores only. The question of what to do with those scores
belongs to Phase 2D, which does not yet exist.

## 8. Phase Responsibility Boundary

```
Phase 2A: observes structural evidence.
Phase 2B: classifies boundaries.
Phase 2C: assigns / calibrates relative numeric preference.
Phase 2D: integrates scores into segmentation behavior.
```

Phase 2C must not: re-parse raw text; rediscover Technical/Atomic structure
independently of what Phase 1/2A already reports; override Phase 2B's classification;
or decide final subtitle cuts. Every existing calibration script (Round 1, Round 2,
Protection Round 1) already honors this Ã¢â‚¬â€ each reads `BoundaryFeatures` and
`BoundaryClass` verbatim from the real, unmodified pipeline and never re-detects
anything.

## 9. Calibration Evidence Status

The distinction between **behaviorally supported** and **provisional baseline** is
explicit and load-bearing in this document Ã¢â‚¬â€ it is not the same thing as "frozen" or
"fully calibrated," and no value here is declared frozen.

**Behaviorally supported** (validated via the completed Protection Calibration and
Post-Correction Verification, against the real pipeline, with exact-match evidence):

| Factor / Rule | Status | Basis |
|---|---|---|
| `Technical = -30` | Behaviorally supported | Exact-delta match against OTHER, Transition, and CLAUSE; exact symmetry with Atomic; consistent across Protection Calibration Round 1 and Post-Correction Verification |
| `Atomic = -30` | Behaviorally supported | Exact-delta match against OTHER and CLAUSE; exact symmetry with Technical |
| `INTERNAL = -20` | Behaviorally supported | Exact-delta match against OTHER, Transition, and CLAUSE (P08Ã¢â‚¬â€œP10); correctly sits between OTHER and Technical/Atomic in the primary protection hierarchy |
| Technical + Atomic Ã¢â€ â€™ strongest-only | Behaviorally supported | P04: the real, doubly-tagged `v1.2.3` candidate scores `-30.0`, matching either single-factor candidate exactly, as the strongest-only rule requires |
| Technical + INTERNAL Ã¢â€ â€™ additive | Behaviorally supported | P11 (post-correction): real candidate scores exactly `0 - 30 - 20 = -50.0` on a clean, non-leak-contaminated boundary |

**Provisional baseline** (accepted as the current working values because every
calibration artifact uses them consistently and no calibration round to date has
produced evidence against them, but not yet the direct subject of a dedicated,
completed calibration round the way the protection factors above were):

| Factor | Status |
|---|---|
| `SENTENCE_FINAL = +80` | Provisional baseline Ã¢â‚¬â€ accepted as the current provisional baseline; used consistently by every calibration artifact; ranking behavior (`SENTENCE_FINAL > ELLIPSIS > CLAUSE > OTHER`) has held in every pairwise comparison observed so far, but its own magnitude has not been the subject of a dedicated calibration round |
| `ELLIPSIS = +65` | Provisional baseline Ã¢â‚¬â€ same status as `SENTENCE_FINAL` above |
| `CLAUSE = +35` | Provisional baseline Ã¢â‚¬â€ same status; also the factor most affected by the still-open "Base Classification Dominance" question (Ã‚Â§14) |
| `CJK Ã¢â€ â€™ LATIN = +15` | Provisional baseline Ã¢â‚¬â€ direction/sign has held in every observed pairwise comparison (e.g. Transition > Technical, Transition > INTERNAL), but Group C of Calibration Round 2 found that natural Chinese/English text rarely exposes a pure transition-only candidate, so the magnitude itself remains lightly tested |
| `LATIN Ã¢â€ â€™ CJK = +15` | Provisional baseline Ã¢â‚¬â€ same status as CJK Ã¢â€ â€™ LATIN |
| `Whitespace = +10` | Provisional baseline Ã¢â‚¬â€ used consistently, but Calibration Round 2's D04 finding (a whitespace-adjacent candidate scoring higher than a no-space transition candidate, `15.0` vs `10.0`+something) flagged an open interaction question this baseline decision does not resolve |

No statement in this document claims any of `+80`/`+65`/`+35`/`+15`/`+10` is "fully
calibrated." Each is described only as accepted as the current provisional baseline,
or used consistently by the current calibration artifacts.

## 10. Repository Consistency Audit

### 10.1 Inventory

Every file listed in the round's required inspection list was inspected, plus the
repository was searched for the terms `SENTENCE_FINAL`, `ELLIPSIS`, `CLAUSE`, `CJK`,
`LATIN`, `Whitespace`, `Technical`, `Atomic`, `INTERNAL`, and the literal values
`+80`, `+65`, `+35`, `+15`, `+10`, `-30`, `-20` (plus `+20`/`+40` specifically, per
Ã‚Â§11) across `docs/*.md` and `scripts/*.py`, and `src/subtitle_segmenter.py` was
checked for any legacy/overlapping scoring constants (none found Ã¢â‚¬â€ it has no
references to `BoundaryClass`, `CharacterClass`, or any Phase 2C construct).
`docs/CALIBRATION.md` was also inspected and found unrelated (it documents an
unrelated audio/video timing calibration tool, `--global-scale-correction`, not
Phase 2C boundary scoring).

### 10.2 Consistency Table

| File | Factor | Value | Role | Status | Notes |
|---|---|---:|---|---|---|
| `docs/PHASE_2C_CALIBRATION_MATRIX.md` (current content = v0.2) | SENTENCE_FINAL / ELLIPSIS / CLAUSE / OTHER | +80 / +65 / +35 / 0 | Matrix baseline | CONSISTENT | Matches Ã‚Â§4.1 exactly |
| `docs/PHASE_2C_CALIBRATION_MATRIX.md` | INTERNAL | -20 | Matrix baseline | CONSISTENT | Matches Ã‚Â§4.3 |
| `docs/Phase_2C_Calibration_Matrix_v0.1.md` | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | **NOT PRESENT** | No such file exists in the repository; v0.1 content was overwritten in place inside `docs/PHASE_2C_CALIBRATION_MATRIX.md` and is not separately preserved (see Ã‚Â§3) |
| `docs/Phase_2C_Calibration_Matrix_v0.2.md` | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | **NOT PRESENT** | No such file exists; v0.2 content lives in `docs/PHASE_2C_CALIBRATION_MATRIX.md` under its own single filename, not a version-suffixed one |
| `docs/phase2c/calibration/reports/PHASE_2C_NUMERIC_CALIBRATION_ROUND1_REPORT.md` | SENTENCE_FINAL / ELLIPSIS / CLAUSE / CJKÃ¢â€ â€™LATIN / LATINÃ¢â€ â€™CJK / Whitespace | +80 / +65 / +35 / +15 / +15 / +10 | Report's stated baseline (Ã‚Â§ "Numeric Baseline") | CONSISTENT | Matches Ã‚Â§4.1/Ã‚Â§4.2 exactly |
| `docs/phase2c/calibration/reports/PHASE_2C_NUMERIC_CALIBRATION_ROUND2_REPORT.md` | SENTENCE_FINAL / ELLIPSIS / CLAUSE / CJKÃ¢â€ â€™LATIN / LATINÃ¢â€ â€™CJK / Whitespace | +80 / +65 / +35 / +15 / +15 / +10 | Report's stated baseline | CONSISTENT | Matches Ã‚Â§4.1/Ã‚Â§4.2 exactly |
| `docs/phase2c/calibration/matrices/PHASE_2C_PROTECTION_CALIBRATION_MATRIX.md` | SENTENCE_FINAL / ELLIPSIS / CLAUSE / OTHER / Whitespace / Technical / Atomic / INTERNAL | +80 / +65 / +35 / 0 / +10 / -30 / -30 / -20 | Matrix baseline | CONSISTENT | Matches Ã‚Â§4 entirely; also the source of the strongest-only interaction rule (Ã‚Â§5) |
| `docs/phase2c/calibration/reports/PHASE_2C_PROTECTION_CALIBRATION_ROUND1_REPORT.md` | Same set | Same values | Report's observed baseline | CONSISTENT | Matches Ã‚Â§4 entirely |
| `docs/phase2c/calibration/reports/PHASE_2C_PROTECTION_POST_CORRECTION_VERIFICATION_REPORT.md` | Same set | Same values (uses the matrix/script values, not the round-contract's stated 20/40) | Report's observed baseline | CONSISTENT | Explicitly flagged the +20/+40 discrepancy itself as non-authoritative (Ã‚Â§3.1 of that report) rather than adopting it Ã¢â‚¬â€ see Ã‚Â§11 below |
| `docs/phase2c/decisions/PHASE_2C_ASCII_PERIOD_UPSTREAM_CORRECTION_DECISION.md` | Technical / Atomic / INTERNAL | -30 / -30 / -20 | Referenced while discussing the P11 fix | CONSISTENT | No base-class values restated in this document; only protection values, matching Ã‚Â§4.3 |
| `scripts/phase2c/calibrate_numeric_round1.py` | `_BASE_SCORES` (SENTENCE_FINAL/ELLIPSIS/CLAUSE/OTHER), transition (+15/+15), whitespace (+10) | 80.0 / 65.0 / 35.0 / 0.0 / 15 / 15 / 10 | Hardcoded calibration constant | CONSISTENT | Matches Ã‚Â§4.1/Ã‚Â§4.2 exactly |
| `scripts/calibrate_phase2c_round1.py` | Technical / Atomic combination | `-30` and `-30` applied **independently** (additive, can total `-60`) | Hardcoded calibration logic | **HISTORICAL** | Predates the strongest-only decision (Ã‚Â§5); this script implements the additive hypothesis that was later superseded for the protection family Ã¢â‚¬â€ not incorrect for its own round's stated purpose, but not the interaction rule this baseline document adopts. Not modified. |
| `scripts/phase2c/calibrate_numeric_round1.py` | INTERNAL | -20, additive on top of whatever protection penalty applies | Hardcoded calibration logic | CONSISTENT | Matches Ã‚Â§5's "Technical/Atomic + INTERNAL Ã¢â€ â€™ additive" rule (this part was never in dispute) |
| `scripts/phase2c/calibrate_numeric_round2.py` | Same base/positive/INTERNAL values | Same as Round 1 script | Hardcoded calibration constant | CONSISTENT | Matches Ã‚Â§4.1/Ã‚Â§4.2/Ã‚Â§4.3 (INTERNAL) exactly |
| `scripts/calibrate_phase2c_round2.py` | Technical / Atomic combination | Additive (same as Round 1 script) | Hardcoded calibration logic | **HISTORICAL** | Same note as Round 1 script Ã¢â‚¬â€ predates the strongest-only decision, not modified |
| `scripts/phase2c/calibrate_protection_round1.py` | `_BASE_SCORES`, transition, whitespace | 80.0 / 65.0 / 35.0 / 0.0 / 15 / 15 / 10 | Hardcoded calibration constant | CONSISTENT | Matches Ã‚Â§4.1/Ã‚Â§4.2 exactly |
| `scripts/phase2c/calibrate_protection_round1.py` | Technical / Atomic combination | `max(-30, -30) = -30` (strongest-only) | Hardcoded calibration logic | CONSISTENT | This is the script that established and matches Ã‚Â§5's strongest-only rule |
| `scripts/phase2c/calibrate_protection_round1.py` | INTERNAL | -20, additive | Hardcoded calibration logic | CONSISTENT | Matches Ã‚Â§5 |
| `docs/CALIBRATION.md` | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Unrelated subsystem (audio/video timing `--global-scale-correction`) | **NOT APPLICABLE** | No Phase 2C boundary-scoring content of any kind |
| `src/subtitle_segmenter.py` | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Production module, no Phase 2C references | **NOT APPLICABLE** | Confirmed via search: no `BoundaryClass`/`CharacterClass`/Phase 2C construct present |

### 10.3 Summary

Every base classification score, positive-evidence score, and protection score is
**CONSISTENT** across every single artifact that states one Ã¢â‚¬â€ ten out of ten factors,
zero numeric contradictions found anywhere in the repository. The only structural
difference found is the Technical+Atomic **combination rule**: Round 1/Round 2's
general calibration scripts use an additive combination (historical Ã¢â‚¬â€ those rounds
were not designed to test this interaction specifically and were written before the
strongest-only hypothesis existed), while the Protection Calibration script
implements and validates strongest-only, which is what this baseline formally adopts
in Ã‚Â§5. This is recorded as **HISTORICAL**, not **INCONSISTENT**, because it reflects
each script's own stated, documented purpose at the time it was written, not an
unexplained contradiction Ã¢â‚¬â€ see each script's own module docstring, which already
describes this difference explicitly.

## 11. Known Inconsistencies

**The `CLAUSE=+20`/`ELLIPSIS=+40` discrepancy is a prompt-level, external
inconsistency Ã¢â‚¬â€ it was never written into any repository artifact as an adopted
value.** A repository-wide search (Ã‚Â§10.1) confirms the literal strings `+20`/`+40`
(as CLAUSE/ELLIPSIS values) appear nowhere in any `docs/*.md` or `scripts/*.py` file
except inside `docs/phase2c/calibration/reports/PHASE_2C_PROTECTION_POST_CORRECTION_VERIFICATION_REPORT.md`, where they
are explicitly quoted and flagged as a discrepancy to investigate Ã¢â‚¬â€ not adopted,
computed with, or used as a baseline anywhere. This document formally confirms:
`+20`/`+40` are **NOT authoritative repository values**. The repository's actual,
consistently-used values are `CLAUSE=+35`, `ELLIPSIS=+65`, matching Ã‚Â§4.1. No file was
or will be modified to "fix" this, because no file ever contained the erroneous
values in the first place Ã¢â‚¬â€ there is nothing to fix, only something to formally
disclaim.

The Technical+Atomic additive-vs-strongest-only difference between the older
calibration scripts and the Protection Calibration script (Ã‚Â§10.3) is recorded here
for completeness but is not a new finding Ã¢â‚¬â€ it was already the explicit, named
subject of the Protection Calibration round and is already discussed in
`docs/phase2c/calibration/reports/PHASE_2C_PROTECTION_CALIBRATION_ROUND1_REPORT.md` Ã‚Â§12 ("Comparison With
Previous Calibration").

## 12. Decision

**Decision:** Adopt the existing repository-wide Phase 2C numeric values as the
authoritative provisional **Numeric Baseline v0.1**.

**Baseline:**

```
SENTENCE_FINAL = +80
ELLIPSIS       = +65
CLAUSE         = +35
OTHER          = 0
CJK Ã¢â€ â€™ LATIN    = +15
LATIN Ã¢â€ â€™ CJK    = +15
Whitespace     = +10
Technical      = -30
Atomic         = -30
INTERNAL       = -20
```

**Interaction rules:**

```
Technical + Atomic              Ã¢â€ â€™ strongest-only (-30 max, not -60)
Technical / Atomic + INTERNAL   Ã¢â€ â€™ additive (e.g. Technical + INTERNAL = -50)
```

**Scoring model:** Signed relative score. **Base score strategy:** Moderate
Classification Dominance. **Disabled mechanisms:** no class-specific hard floor, no
normalization, no threshold.

This is a **baseline** decision Ã¢â‚¬â€ it names and formally adopts values already in
consistent use, so that future work has one unambiguous reference point. **It is not
a declaration that all values are fully calibrated.** Per Ã‚Â§9, the protection factors
(`Technical`, `Atomic`, `INTERNAL`, and their interaction rules) are behaviorally
supported by completed calibration evidence; the base classification and positive
evidence factors (`SENTENCE_FINAL`, `ELLIPSIS`, `CLAUSE`, `CJKÃ¢â€ â€™LATIN`, `LATINÃ¢â€ â€™CJK`,
`Whitespace`) are accepted as the current provisional baseline pending their own
dedicated calibration round.

## 13. Non-Goals

This decision does **not**:

- Authorize modification of production code, tests, existing calibration scripts,
  existing calibration matrices, or existing calibration reports. Numeric value
  changes require a separate, future Numeric Calibration decision.
- Declare any base classification or positive-evidence value "frozen" or "fully
  calibrated."
- Resolve the Technical+Atomic additive-vs-strongest-only split found in the older
  Round 1/Round 2 scripts versus the Protection Calibration script Ã¢â‚¬â€ those older
  scripts are left exactly as they are (HISTORICAL, Ã‚Â§10.3), and this baseline simply
  states which rule (strongest-only) is authoritative going forward.
- Resolve P12 (Atomic + INTERNAL). It remains `CASE ISSUE` / unreachable in the
  current architecture, per `docs/phase2c/calibration/reports/PHASE_2C_PROTECTION_POST_CORRECTION_VERIFICATION_REPORT.md`
  Ã‚Â§7. No change to Phase 1 is proposed or implied by this document.
- Introduce a threshold, floor, or normalization step.
- Begin Phase 2C production scoring implementation, Numeric Calibration, or Phase 2D.

## 14. Next Phase

After this decision, the next activity is **Phase 2C Numeric Calibration**. It should
investigate, in order:

1. **Base Classification Dominance** Ã¢â‚¬â€ `OTHER`, `CLAUSE`, `ELLIPSIS`, `SENTENCE_FINAL`
   magnitudes and their pairwise margins (not just their ranking direction, which has
   already held in every observed comparison).
2. **Positive Evidence** Ã¢â‚¬â€ `Transition` (`CJKÃ¢â€ â€™LATIN`/`LATINÃ¢â€ â€™CJK`) and `Whitespace`,
   including the open D04-style interaction question (a whitespace-adjacent candidate
   outscoring a no-space transition candidate) flagged in Calibration Round 2.
3. **Cross-factor interactions** beyond what Protection Calibration already covered
   (e.g. base-class-vs-positive-evidence combinations not yet directly tested).

Only after these are understood should final Phase 2C numeric values be considered
for freeze. This document does not perform that calibration.

## 15. Change Control

This decision does **not** authorize modification of:

- production code (`src/*`)
- tests (`tests/*`)
- existing calibration scripts (`scripts/phase2c/calibrate_numeric_round1.py`,
  `scripts/phase2c/calibrate_numeric_round2.py`,
  `scripts/phase2c/calibrate_protection_round1.py`)
- existing calibration matrices (`docs/PHASE_2C_CALIBRATION_MATRIX.md`,
  `docs/phase2c/calibration/matrices/PHASE_2C_PROTECTION_CALIBRATION_MATRIX.md`)
- existing calibration reports (`docs/phase2c/calibration/reports/PHASE_2C_NUMERIC_CALIBRATION_ROUND1_REPORT.md`,
  `docs/phase2c/calibration/reports/PHASE_2C_NUMERIC_CALIBRATION_ROUND2_REPORT.md`,
  `docs/phase2c/calibration/reports/PHASE_2C_PROTECTION_CALIBRATION_ROUND1_REPORT.md`,
  `docs/phase2c/calibration/reports/PHASE_2C_PROTECTION_POST_CORRECTION_VERIFICATION_REPORT.md`,
  `docs/phase2c/decisions/PHASE_2C_ASCII_PERIOD_UPSTREAM_CORRECTION_DECISION.md`)

Any future numeric change (increase, decrease, interaction-rule change, or
introduction of a threshold/floor/normalization) requires a separate, explicitly
scoped Numeric Calibration decision Ã¢â‚¬â€ it is not authorized by this document.

---

## Files

**Created:** `docs/PHASE_2C_NUMERIC_BASELINE_DECISION.md` (this document) Ã¢â‚¬â€ the sole
new file produced this round.

**Confirmed unmodified:** `src/*`, `tests/*`, `scripts/calibrate_phase2c_round1.py`,
`scripts/phase2c/calibrate_numeric_round2.py`,
`scripts/phase2c/calibrate_protection_round1.py`,
`docs/PHASE_2C_CALIBRATION_MATRIX.md`,
`docs/phase2c/calibration/reports/PHASE_2C_NUMERIC_CALIBRATION_ROUND1_REPORT.md`,
`docs/phase2c/calibration/reports/PHASE_2C_NUMERIC_CALIBRATION_ROUND2_REPORT.md`,
`docs/phase2c/calibration/matrices/PHASE_2C_PROTECTION_CALIBRATION_MATRIX.md`,
`docs/phase2c/calibration/reports/PHASE_2C_PROTECTION_CALIBRATION_ROUND1_REPORT.md`,
`docs/phase2c/calibration/reports/PHASE_2C_PROTECTION_POST_CORRECTION_VERIFICATION_REPORT.md`,
`docs/phase2c/decisions/PHASE_2C_ASCII_PERIOD_UPSTREAM_CORRECTION_DECISION.md`, `docs/CALIBRATION.md`,
`README.md`, `pyproject.toml`, and every other existing repository file.

**Test results (health check only, not a requirement of this round):**
```
$ python3 -m pytest tests/ -q
397 passed, 2 warnings, 15 subtests passed in 26.21s
```
No test was run to validate this document's content (there is nothing executable in
it); this was a repository-health sanity check only, and nothing was modified as a
result.
