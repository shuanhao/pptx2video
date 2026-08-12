# Phase 2C Protection Calibration Matrix v0.1

**Status:** Focused Calibration Specification
**Phase:** Phase 2C Ã¢â‚¬â€ Numeric Calibration
**Purpose:** Calibrate Technical / Atomic protection and Punctuation Sequence INTERNAL suppression

## 1. Purpose

This document defines a focused calibration set for the negative evidence used by Phase 2C.

The experiment determines whether the provisional protection/suppression values produce the desired relative boundary preference.

Primary qualitative target:

```text
CLAUSE
   >
Transition
   >
OTHER
   >
INTERNAL
   >
Technical / Atomic
```

The final ordering of `INTERNAL` versus `Technical / Atomic` remains an empirical question.

## 2. Scope

Covers:
- Plain `OTHER`
- Technical protection
- Atomic protection
- Technical + Atomic interaction
- `PunctuationSequenceState.INTERNAL`
- Technical + INTERNAL
- Atomic + INTERNAL
- Technical vs Atomic symmetry
- Protection relative to Transition
- Protection relative to CLAUSE

Does not cover:
- `SENTENCE_FINAL` calibration
- `ELLIPSIS` base score calibration
- Transition / Whitespace calibration
- Phase 2D
- final segmentation decisions

## 3. Provisional Numeric Baseline

| BoundaryClass | Score |
|---|---:|
| `SENTENCE_FINAL` | +80 |
| `ELLIPSIS` | +65 |
| `CLAUSE` | +35 |
| `OTHER` | 0 |

| Evidence | Score |
|---|---:|
| CJK Ã¢â€ â€™ Latin | +15 |
| Latin Ã¢â€ â€™ CJK | +15 |
| Whitespace | +10 |
| Technical | -30 |
| Atomic | -30 |
| Punctuation Sequence `INTERNAL` | -20 |

**No value may be changed during this experiment.**

## 4. Protection Model Under Evaluation

### 4.1 Technical / Atomic

Technical and Atomic are treated as a protection family rather than automatically additive penalties.

Provisional rule:

```text
ProtectionPenalty = strongest(Technical, Atomic)
```

Therefore:

```text
Technical          = -30
Atomic             = -30
Technical + Atomic = -30
```

Do not calculate `-30 + -30 = -60`.

This rule is itself subject to calibration evidence.

### 4.2 INTERNAL

`PunctuationSequenceState.INTERNAL` is conceptually different from Technical / Atomic protection.

Provisional rule:

```text
SequenceSuppression =
    -20 when INTERNAL
     0 otherwise
```

INTERNAL may combine with Technical or Atomic if the real pipeline exposes both on the same candidate:

```text
Technical + INTERNAL = -50
Atomic + INTERNAL    = -50
```

Do not manufacture such candidates.

## 5. Phase Responsibility Boundary

### Phase 2B

Determines the structural boundary class. Technical / Atomic structure may prevent `CLAUSE` classification.

### Phase 2C

Determines relative boundary preference using the actual `BoundaryFeatures` and `BoundaryClass`. It must not re-parse raw text to rediscover Technical / Atomic structure.

### Phase 2D

Not part of this experiment. Do not choose final subtitle cuts.

## 6. Case Status Rules

Each case receives exactly one status:

- **PASS** Ã¢â‚¬â€ reachable and intended relationship holds.
- **CALIBRATION REVIEW** Ã¢â‚¬â€ reachable but provisional numeric model produces a questionable ranking.
- **UPSTREAM ISSUE** Ã¢â‚¬â€ problem originates in Phase 1 / 2A / 2B.
- **CASE ISSUE** Ã¢â‚¬â€ intended candidate/evidence combination is not representable by the current pipeline.

Do not turn CASE ISSUE or UPSTREAM ISSUE into numeric failures.

## 7. Calibration Cases

### P01 Ã¢â‚¬â€ Plain OTHER Baseline

Find a genuine candidate with:

```text
BoundaryClass = OTHER
Technical = false
Atomic = false
INTERNAL = false
Transition = false
Whitespace = false
```

Expected:

```text
Score = 0
```

Do not create a synthetic candidate merely to obtain this baseline. If none exists, mark `CASE ISSUE`.

### P02 Ã¢â‚¬â€ Technical OTHER

Use a realistic technical expression such as:

```text
Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¦â€¢Â¸Ã¥â‚¬Â¼Ã¦ËœÂ¯ 1,000Ã¯Â¼Å’Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Â¹Â¼Ã§ÂºÅ’Ã£â‚¬â€š
```

Inspect the actual candidate around the internal technical boundary, such as `1,|000`.

If represented:

```text
BoundaryClass = OTHER
Technical = true
Score = -30
```

Expected:

```text
P02 < P01
```

### P03 Ã¢â‚¬â€ Atomic OTHER

Use a realistic atomic expression such as:

```text
Ã§â€ºÂ®Ã¥â€°ÂÃ§â€°Ë†Ã¦Å“Â¬Ã¦ËœÂ¯ v1.2.3Ã¯Â¼Å’Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¤Â»â€¹Ã§Â´Â¹Ã¦â€“Â°Ã§â€°Ë†Ã£â‚¬â€š
```

If represented:

```text
BoundaryClass = OTHER
Atomic = true
Score = -30
```

Expected:

```text
P03 < P01
```

### P04 Ã¢â‚¬â€ Technical + Atomic

Use an expression such as `v1.2.3` only if the real pipeline reports both Technical and Atomic on the same candidate.

Expected:

```text
Technical + Atomic
= strongest(-30, -30)
= -30
```

Expected:

```text
P04 = P02 = P03
```

If the combination is not observable, mark `CASE ISSUE`.

### P05 Ã¢â‚¬â€ Transition vs Technical

Compare real candidates:

```text
Transition = +15
Technical  = -30
```

Expected:

```text
Transition > Technical
```

Expected delta: `45`.

### P06 Ã¢â‚¬â€ CLAUSE vs Technical

Compare:

```text
CLAUSE    = +35
Technical = -30
```

Expected:

```text
CLAUSE > Technical
```

Expected delta: `65`.

### P07 Ã¢â‚¬â€ CLAUSE vs Atomic

Compare:

```text
CLAUSE = +35
Atomic = -30
```

Expected:

```text
CLAUSE > Atomic
```

Expected delta: `65`.

### P08 Ã¢â‚¬â€ Plain OTHER vs INTERNAL

Identify a genuine candidate with:

```text
PunctuationSequenceState = INTERNAL
```

Expected:

```text
OTHER    = 0
INTERNAL = -20
```

Expected:

```text
OTHER > INTERNAL
```

### P09 Ã¢â‚¬â€ Transition vs INTERNAL

Expected:

```text
Transition = +15
INTERNAL   = -20
Transition > INTERNAL
```

Expected delta: `35`.

### P10 Ã¢â‚¬â€ CLAUSE vs INTERNAL

Expected:

```text
CLAUSE   = +35
INTERNAL = -20
CLAUSE > INTERNAL
```

Expected delta: `55`.

### P11 Ã¢â‚¬â€ Technical + INTERNAL

Only if the real pipeline exposes both on the same candidate.

Expected:

```text
0 - 30 - 20 = -50
```

Expected:

```text
Technical + INTERNAL < Technical
```

Otherwise `CASE ISSUE`.

### P12 Ã¢â‚¬â€ Atomic + INTERNAL

Only if the real pipeline exposes both on the same candidate.

Expected:

```text
0 - 30 - 20 = -50
```

Expected:

```text
Atomic + INTERNAL < Atomic
```

Otherwise `CASE ISSUE`.

### P13 Ã¢â‚¬â€ Technical vs Atomic Symmetry

Compare real Technical-only and Atomic-only candidates.

Current hypothesis:

```text
Technical = Atomic = -30
```

Expected:

```text
Technical == Atomic
```

This is a factor-model symmetry check, not a requirement that the raw text be identical.

### P14 Ã¢â‚¬â€ Transition vs Technical Reversal Test

Expected:

```text
Transition (+15) > Technical (-30)
```

### P15 Ã¢â‚¬â€ CLAUSE vs Technical Reversal Test

Expected:

```text
CLAUSE (+35) > Technical (-30)
```

## 8. Primary Calibration Hierarchy

Evaluate:

```text
CLAUSE
   >
Transition
   >
OTHER
   >
INTERNAL
   >
Technical / Atomic
```

Do not freeze the final position of INTERNAL versus Technical / Atomic until the evidence supports it.

## 9. Numeric Interpretation

Scores are signed relative boundary preferences, not probabilities.

Focus on:
- intended ordering
- margin size
- suppression strength
- unexpected reversals
- stacking behavior

## 10. Experiment Restrictions

Do not:
- modify `subtitle_segmenter.py`
- modify Phase 1
- modify Phase 2A
- modify Phase 2B
- implement production Phase 2C
- implement Phase 2D
- change provisional weights
- add thresholds, normalization, hard floors, or special-case scoring
- add raw-text Technical / Atomic parsing to Phase 2C
- modify tests merely to make calibration pass
- commit changes

## 11. Required Output

For every reachable case record:

```text
Case ID
Input
Target boundary
Actual candidate position
BoundaryClass
Technical evidence
Atomic evidence
PunctuationSequenceState
Transition evidence
Whitespace evidence
Base score
Protection penalty
Sequence penalty
Final provisional score
Expected relation
Observed relation
Status
```

For unreachable cases explicitly record `CASE ISSUE`.

For upstream problems explicitly record `UPSTREAM ISSUE`.

## 12. Required Summary

The calibration report must contain:

1. Reachability for P01Ã¢â‚¬â€œP15.
2. Score table for all reachable candidates.
3. Pairwise ranking: expected, observed, delta, status.
4. Protection interaction analysis:
   - Technical vs Plain OTHER
   - Atomic vs Plain OTHER
   - Technical vs Transition
   - Technical vs CLAUSE
   - Atomic vs CLAUSE
   - INTERNAL vs Plain OTHER
   - INTERNAL vs Transition
   - INTERNAL vs CLAUSE
   - Technical + INTERNAL
   - Atomic + INTERNAL
   - Technical + Atomic
5. Numeric recommendations for:
   - Technical -30
   - Atomic -30
   - INTERNAL -20

Each recommendation must be one of:

```text
KEEP
INCREASE
DECREASE
NEED MORE DATA
UPSTREAM ISSUE
NOT CALIBRATABLE YET
```

Do not change the values during the experiment.

## 13. Completion Criteria

Complete only when:
- P01Ã¢â‚¬â€œP15 are evaluated or explicitly marked unreachable
- actual Phase 1 Ã¢â€ â€™ 2A Ã¢â€ â€™ 2B output is used
- no production module is modified
- no provisional weight is changed
- Technical / Atomic interaction is analyzed
- INTERNAL interaction is analyzed
- pairwise rankings are reported
- upstream and case-design issues are separated from numeric issues
- full existing regression remains passing
- a complete calibration report is produced

The result will be used as input to the Phase 2C Numeric Strategy v1 design decision.
