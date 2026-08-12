# Phase 2C Calibration Matrix v0.2

**Status:** Design / Calibration Draft
**Supersedes:** Phase 2C Calibration Matrix v0.1
**Scope:** Phase 2C numeric calibration only
**Purpose:** Provide a calibration dataset whose cases are actually observable through the current Phase 1 Ã¢â€ â€™ Phase 2A Ã¢â€ â€™ Phase 2B pipeline.

---

## 1. Purpose of v0.2

Calibration Round 1 demonstrated that several v0.1 cases were based on assumptions that do not match the current candidate topology or upstream representation.

The purpose of v0.2 is therefore **not to change numeric weights yet**.

The purpose is to make every calibration case:

- representable by the current Phase 1 Ã¢â€ â€™ 2A Ã¢â€ â€™ 2B pipeline,
- explicit about the boundary being evaluated,
- explicit about whether the case tests a score, a ranking, or an upstream representation issue,
- free from assumptions about combinations of modifiers that cannot coexist on the same candidate.

The calibration process remains:

```text
Phase 1
    Ã¢â€ â€œ
Phase 2A Boundary Observation
    Ã¢â€ â€œ
Phase 2B Boundary Classification
    Ã¢â€ â€œ
Phase 2C Calibration-only scoring
```

Phase 2C still does not make a final cut decision.

---

# 2. Numeric Baseline Under Evaluation

The following values remain the provisional baseline for Round 2.

They are **not frozen**.

## Base Score

| Boundary Class | Score |
|---|---:|
| `SENTENCE_FINAL` | +80 |
| `ELLIPSIS` | +65 |
| `CLAUSE` | +35 |
| `OTHER` | 0 |

## Positive Modifiers

| Evidence | Score |
|---|---:|
| CJK Ã¢â€ â€™ Latin transition | +15 |
| Latin Ã¢â€ â€™ CJK transition | +15 |
| Boundary whitespace | +10 |

## Negative Modifiers

| Evidence | Score |
|---|---:|
| Technical context | -30 |
| Atomic context | -30 |
| Punctuation sequence `INTERNAL` | -20 |

Formula:

```text
score =
    base_score
    + positive_modifiers
    + negative_modifiers
```

No normalization, threshold, hard floor, hard constraint, segment-length factor, duration factor, line-width factor, neighboring-boundary factor, or Phase 2D decision is included.

---

# 3. Important v0.2 Design Corrections

## 3.1 String-final punctuation is not itself a calibration boundary

The current pipeline does not expose a boundary after the final character of the input.

Therefore this is **not** a valid direct calibration case:

```text
Ã¤Â»Å Ã¥Â¤Â©Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â»â€¹Ã§Â´Â¹ CPUÃ£â‚¬â€š
```

when the intended boundary is after `Ã£â‚¬â€š`.

Instead use an internal sentence-final boundary:

```text
Ã¤Â»Å Ã¥Â¤Â©Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â»â€¹Ã§Â´Â¹ CPUÃ£â‚¬â€šÃ¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Å“â€¹ GPUÃ£â‚¬â€š
```

The intended candidate is:

```text
CPUÃ£â‚¬â€š|Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ 
```

This allows Phase 1 Ã¢â€ â€™ 2A Ã¢â€ â€™ 2B to observe the actual boundary.

String-final behavior remains an architectural consideration for a later stage and is not modified by Phase 2C.

---

## 3.2 `CLAUSE + language transition` is not assumed

A clause boundary normally has punctuation on one side of the boundary.

Therefore v0.2 does not assume that the same candidate can simultaneously be:

```text
CLAUSE
+
CJK Ã¢â€ â€™ Latin transition
+
whitespace
```

Such combinations are removed from the calibration model unless the real pipeline demonstrably exposes them.

---

## 3.3 Whitespace is a boundary-local observation

For:

```text
Ã¤Â¸Â­Ã¦â€“â€¡ | English
```

do not assume a single candidate receives both:

```text
transition + whitespace
```

The current pipeline may expose separate boundary positions.

Therefore v0.2 explicitly tests candidate topology instead of assuming modifier stacking.

---

## 3.4 Technical / atomic context must be evaluated from actual Phase 2B output

Do not assume:

```text
CLAUSE - technical penalty
```

if Phase 2B has already classified the candidate as `OTHER` because the technical / atomic protection changes its classification.

The calibration case must record the actual class first, then apply the Phase 2C numeric model.

---

## 3.5 ASCII punctuation representation issues are not numeric calibration cases

Examples such as:

```text
3.14
v1.2.3
http://example.com
......
?!
```

may expose upstream sentence-final evidence that is not appropriate.

These are retained only as **upstream observation probes**.

They must not be used to tune:

```text
INTERNAL = -20
```

or any other Phase 2C weight.

---

# 4. Calibration Case Format

Each case should conceptually contain:

```text
Case ID
Input text
Target boundary position
Target boundary representation
Expected / observed BoundaryClass
Relevant features
Calibration purpose
Expected relation
```

Absolute score is calculated from the current baseline after the real pipeline output is known.

The expected relation is more important than the absolute score during calibration.

---

# 5. Group A Ã¢â‚¬â€ Base Boundary Classes

These cases establish the base hierarchy using boundaries that actually exist inside the input.

## A01 Ã¢â‚¬â€ Sentence Final

Input:

```text
Ã¤Â»Å Ã¥Â¤Â©Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â»â€¹Ã§Â´Â¹ CPUÃ£â‚¬â€šÃ¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Å“â€¹ GPUÃ£â‚¬â€š
```

Target:

```text
CPUÃ£â‚¬â€š|Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ 
```

Expected class:

```text
SENTENCE_FINAL
```

Baseline:

```text
+80
```

Purpose:

- verify real sentence-final candidate
- establish the highest normal base class

---

## A02 Ã¢â‚¬â€ Ellipsis

Input:

```text
Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥â€¢ÂÃ©Â¡Å’Ã¥Ëœâ€ºÃ¢â‚¬Â¦Ã¢â‚¬Â¦Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¥â€ ÂÃ¨Â¨Å½Ã¨Â«â€“Ã£â‚¬â€š
```

Target:

```text
Ã¥Ëœâ€ºÃ¢â‚¬Â¦Ã¢â‚¬Â¦|Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ 
```

Expected class:

```text
ELLIPSIS
```

Baseline:

```text
+65
```

Purpose:

- verify ellipsis candidate
- establish ellipsis base score

---

## A03 Ã¢â‚¬â€ Clause

Input:

```text
Ã©Â¦â€“Ã¥â€¦Ë†Ã¯Â¼Å’Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â»â€¹Ã§Â´Â¹ CPUÃ¯Â¼Å’Ã¦Å½Â¥Ã¨â€˜â€”Ã¥â€ ÂÃ§Å“â€¹ GPUÃ£â‚¬â€š
```

Target:

```text
Ã©Â¦â€“Ã¥â€¦Ë†Ã¯Â¼Å’|Ã¦Ë†â€˜Ã¥â‚¬â€˜
```

Expected class:

```text
CLAUSE
```

Baseline:

```text
+35
```

Purpose:

- verify clause base score

---

## A04 Ã¢â‚¬â€ Plain OTHER

Input:

```text
Ã¤Â¸Â­Ã¦â€“â€¡English
```

Target:

```text
Ã¤Â¸Â­Ã¦â€“â€¡|English
```

Expected class:

```text
OTHER
```

Expected evidence:

```text
CJK Ã¢â€ â€™ Latin
```

This case is therefore not a pure `OTHER = 0` case.

A true plain-OTHER case must be selected from an actual pipeline boundary where no positive or negative modifier applies.

If the current pipeline does not expose such a boundary reliably, record:

```text
CASE STATUS = REPRESENTATION ISSUE
```

Do not invent one.

---

# 6. Group B Ã¢â‚¬â€ Base Pairwise Hierarchy

These cases compare base classes.

## B01 Ã¢â‚¬â€ Sentence Final vs Clause

```text
Ã¤Â»Å Ã¥Â¤Â©Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â»â€¹Ã§Â´Â¹ CPUÃ£â‚¬â€šÃ¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Å“â€¹ GPUÃ¯Â¼Å’
Ã§â€žÂ¶Ã¥Â¾Å’Ã¥â€ ÂÃ¨ÂªÂªÃ¦ËœÅ½ NPUÃ£â‚¬â€š
```

Compare:

```text
CPUÃ£â‚¬â€š|Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ 
```

against:

```text
GPUÃ¯Â¼Å’|Ã§â€žÂ¶Ã¥Â¾Å’
```

Expected:

```text
SENTENCE_FINAL > CLAUSE
```

Baseline:

```text
80 > 35
```

---

## B02 Ã¢â‚¬â€ Sentence Final vs Ellipsis

Input:

```text
Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥â€¢ÂÃ©Â¡Å’Ã¥Ëœâ€ºÃ¢â‚¬Â¦Ã¢â‚¬Â¦Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¥â€¦Ë†Ã¦Å¡Â«Ã¥ÂÅ“Ã¤Â¸â‚¬Ã¤Â¸â€¹Ã£â‚¬â€šÃ¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã§Â¹Â¼Ã§ÂºÅ’Ã£â‚¬â€š
```

Compare:

```text
Ã¥Ëœâ€ºÃ¢â‚¬Â¦Ã¢â‚¬Â¦|Ã¦Ë†â€˜Ã¥â‚¬â€˜
```

and:

```text
Ã¤Â¸â‚¬Ã¤Â¸â€¹Ã£â‚¬â€š|Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ 
```

Expected:

```text
SENTENCE_FINAL > ELLIPSIS
```

Baseline:

```text
80 > 65
```

---

## B03 Ã¢â‚¬â€ Ellipsis vs Clause

Input:

```text
Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥â€¢ÂÃ©Â¡Å’Ã¥Ëœâ€ºÃ¢â‚¬Â¦Ã¢â‚¬Â¦Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¥â€ ÂÃ¨Â¨Å½Ã¨Â«â€“Ã¯Â¼Å’Ã§ÂÂ¾Ã¥Å“Â¨Ã¥â€¦Ë†Ã§Å“â€¹ CPUÃ£â‚¬â€š
```

Compare:

```text
Ã¥Ëœâ€ºÃ¢â‚¬Â¦Ã¢â‚¬Â¦|Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ 
```

and:

```text
Ã¨Â¨Å½Ã¨Â«â€“Ã¯Â¼Å’|Ã§ÂÂ¾Ã¥Å“Â¨
```

Expected:

```text
ELLIPSIS > CLAUSE
```

Baseline:

```text
65 > 35
```

---

# 7. Group C Ã¢â‚¬â€ Language Transition

These cases isolate language-transition evidence.

## C01 Ã¢â‚¬â€ CJK Ã¢â€ â€™ Latin

Input:

```text
Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â½Â¿Ã§â€Â¨ LinuxÃ£â‚¬â€š
```

Target:

```text
Ã¤Â½Â¿Ã§â€Â¨ | Linux
```

Important:

The exact target position must be chosen from the actual Phase 2A candidate output.

If the pipeline does not create the expected transition boundary, record a representation issue rather than changing upstream behavior.

Expected modifier when applicable:

```text
+15
```

---

## C02 Ã¢â‚¬â€ Latin Ã¢â€ â€™ CJK

Input:

```text
Linux Ã§Â³Â»Ã§ÂµÂ±Ã©Å“â‚¬Ã¨Â¦ÂÃ©â€¡ÂÃ¦â€“Â°Ã¨Â¨Â­Ã¥Â®Å¡Ã£â‚¬â€š
```

Target:

```text
Linux | Ã§Â³Â»Ã§ÂµÂ±
```

Expected modifier when applicable:

```text
+15
```

Expected symmetry:

```text
CJK Ã¢â€ â€™ Latin = Latin Ã¢â€ â€™ CJK
```

---

## C03 Ã¢â‚¬â€ Transition vs ordinary CLAUSE

Compare an actual language-transition candidate with an actual ordinary clause candidate.

Expected:

```text
ordinary CLAUSE > transition-only OTHER
```

Baseline expectation, when both candidates are represented as intended:

```text
35 > 15
```

Purpose:

- verify moderate classification dominance

---

# 8. Group D Ã¢â‚¬â€ Whitespace Topology

Whitespace is tested as a boundary-local observation rather than automatically stacked with language transition.

## D01 Ã¢â‚¬â€ Whitespace before boundary

Input:

```text
Ã¤Â¸Â­Ã¦â€“â€¡ English
```

Inspect the actual candidates around:

```text
Ã¤Â¸Â­Ã¦â€“â€¡ | English
```

Record which candidate receives whitespace evidence.

---

## D02 Ã¢â‚¬â€ Whitespace after boundary

Use:

```text
Ã¤Â¸Â­Ã¦â€“â€¡ English
```

and inspect the boundary on the other side of the whitespace.

Record actual candidate topology.

---

## D03 Ã¢â‚¬â€ Whitespace on both sides

Input:

```text
Ã¤Â¸Â­Ã¦â€“â€¡  English
```

Inspect all exposed candidates.

Purpose:

- determine whether whitespace evidence belongs to one candidate or multiple candidates
- do not assume a single candidate receives `+10` twice

---

## D04 Ã¢â‚¬â€ Transition without whitespace vs whitespace variant

Compare:

```text
Ã¤Â¸Â­Ã¦â€“â€¡|English
```

with:

```text
Ã¤Â¸Â­Ã¦â€“â€¡ | English
```

but compare the **actual candidate positions separately**.

Expected result is not predefined as:

```text
25 > 15
```

until the real pipeline demonstrates that both modifiers can coexist on the same candidate.

This case exists specifically to resolve the topology discovered in Round 1.

---

# 9. Group E Ã¢â‚¬â€ Technical / Atomic Protection

## E01 Ã¢â‚¬â€ Technical numeric expression

Input:

```text
Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥â‚¬Â¼Ã¦ËœÂ¯ 1,000Ã¯Â¼Å’Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã§Â¹Â¼Ã§ÂºÅ’Ã£â‚¬â€š
```

Inspect candidate(s) inside:

```text
1,000
```

Expected:

- technical context should be observable where applicable
- actual `BoundaryClass` must come from Phase 2B
- Phase 2C must not assume the candidate is `CLAUSE`

Purpose:

- determine the actual Phase 2C penalty path

---

## E02 Ã¢â‚¬â€ Version / atomic expression

Input:

```text
Ã§â€ºÂ®Ã¥â€°ÂÃ¤Â½Â¿Ã§â€Â¨ v1.2.3Ã¯Â¼Å’Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¤Â»â€¹Ã§Â´Â¹Ã¦â€“Â°Ã§â€°Ë†Ã£â‚¬â€š
```

Inspect internal candidates inside:

```text
v1.2.3
```

Expected:

- atomic protection evidence where applicable
- actual class from Phase 2B

---

## E03 Ã¢â‚¬â€ Technical candidate vs ordinary clause

Compare:

```text
technical-protected boundary
```

with:

```text
ordinary clause boundary
```

Expected:

```text
ordinary clause > protected technical boundary
```

The exact score difference is intentionally left open for calibration.

---

## E04 Ã¢â‚¬â€ Technical candidate vs language-transition candidate

Compare a real technical-protected candidate against a real language-transition candidate.

Purpose:

- determine whether `Technical = -30` creates an excessive reversal
- do not change the penalty during this round

---

# 10. Group F Ã¢â‚¬â€ Punctuation Sequence

## F01 Ã¢â‚¬â€ Ellipsis END

Input:

```text
Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥â€¢ÂÃ©Â¡Å’Ã¥Ëœâ€ºÃ¢â‚¬Â¦Ã¢â‚¬Â¦Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¥â€ ÂÃ¨Â¨Å½Ã¨Â«â€“Ã£â‚¬â€š
```

Target:

```text
Ã¢â‚¬Â¦Ã¢â‚¬Â¦|Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ 
```

Expected:

```text
PunctuationSequenceState = END
BoundaryClass = ELLIPSIS
```

Baseline:

```text
+65
```

---

## F02 Ã¢â‚¬â€ Ellipsis INTERNAL

Input:

```text
Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ 
```

Inspect any candidate inside the ellipsis sequence.

Expected:

```text
PunctuationSequenceState = INTERNAL
```

If represented as `OTHER`:

```text
0 - 20 = -20
```

Purpose:

- verify internal sequence suppression

---

## F03 Ã¢â‚¬â€ END vs INTERNAL

Compare an actual END candidate with an actual INTERNAL candidate.

Expected:

```text
END > INTERNAL
```

---

# 11. Group G Ã¢â‚¬â€ Sentence-Final / Ellipsis Composition

These cases ensure punctuation composition is not incorrectly treated as a simple character lookup.

## G01 Ã¢â‚¬â€ Ellipsis followed by question

Input:

```text
Ã§Å“Å¸Ã§Å¡â€žÃ¢â‚¬Â¦Ã¢â‚¬Â¦Ã¯Â¼Å¸Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¨ÂªÂªÃ¦ËœÅ½Ã£â‚¬â€š
```

Target:

```text
Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¯Â¼Å¸|Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ 
```

Expected:

```text
SENTENCE_FINAL
```

if the existing Phase 1 / 2A / 2B pipeline exposes that result.

Purpose:

- verify sentence-final composition

---

## G02 Ã¢â‚¬â€ Ellipsis followed by exclamation

```text
Ã§Å“Å¸Ã§Å¡â€žÃ¢â‚¬Â¦Ã¢â‚¬Â¦Ã¯Â¼ÂÃ¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¨ÂªÂªÃ¦ËœÅ½Ã£â‚¬â€š
```

Expected:

```text
SENTENCE_FINAL
```

---

## G03 Ã¢â‚¬â€ ASCII ellipsis run

```text
Ã§Å“Å¸Ã§Å¡â€ž......Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¨ÂªÂªÃ¦ËœÅ½Ã£â‚¬â€š
```

This is an **upstream observation probe**, not a numeric calibration case.

Record whether Phase 1/2A/2B correctly represents the sequence.

Do not adjust Phase 2C weights based on this case.

---

# 12. Group H Ã¢â‚¬â€ Realistic Mixed-Language Cases

These cases are designed to observe actual score distribution rather than force a predetermined formula.

## H01

```text
Ã¤Â»Å Ã¥Â¤Â©Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¥â€¦Ë†Ã¤Â»â€¹Ã§Â´Â¹ CPU Ã§Å¡â€žÃ¥Å¸ÂºÃ¦Å“Â¬Ã¦Å¾Â¶Ã¦Â§â€¹Ã¯Â¼Å’Ã¦Å½Â¥Ã¨â€˜â€”Ã¥â€ ÂÃ¨ÂªÂªÃ¦ËœÅ½ GPU Ã¨Ë†â€¡ NPU Ã§Å¡â€žÃ¥Â·Â®Ã§â€¢Â°Ã£â‚¬â€š
```

Inspect:

- clause boundary
- language transitions
- sentence-final boundary

Expected qualitative hierarchy:

```text
sentence final should be strongest
```

---

## H02

```text
Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â½Â¿Ã§â€Â¨ ARM Cortex-A Ã§Â³Â»Ã¥Ë†â€” CPUÃ¯Â¼Å’Ã¤Â¸Â¦Ã¦ÂÂ­Ã©â€¦Â Linux OSÃ£â‚¬â€š
```

Inspect:

- technical terms
- language transitions
- clause
- sentence final

Expected:

```text
sentence final > ordinary clause
```

---

## H03

```text
Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¦Å¾Â¶Ã¦Â§â€¹Ã¤Â¸Â»Ã¨Â¦ÂÃ¥Å’â€¦Ã¥ÂÂ« CPUÃ£â‚¬ÂGPUÃ£â‚¬ÂNPU Ã¤Â¸â€°Ã¥â‚¬â€¹Ã¤Â¸Â»Ã¨Â¦ÂÃ©Ââ€¹Ã§Â®â€”Ã¥â€“Â®Ã¥â€¦Æ’Ã¯Â¼Å’Ã¥â€¦Â¶Ã¤Â¸Â­ CPU Ã¨Â²Â Ã¨Â²Â¬Ã¤Â¸â‚¬Ã¨Ë†Â¬Ã©Ââ€¹Ã§Â®â€”Ã£â‚¬â€š
```

Inspect:

- list punctuation
- technical contexts
- clause
- sentence final

Purpose:

- observe whether technical-list candidates are appropriately suppressed

---

## H04

```text
CPU / GPU / NPU Ã¦ËœÂ¯Ã§â€ºÂ®Ã¥â€°ÂÃ¥Â¸Â¸Ã¨Â¦â€¹Ã§Å¡â€ž AI acceleratorÃ£â‚¬â€š
```

Inspect:

- list boundaries
- language transitions
- sentence final

Purpose:

- avoid splitting technical enumeration unnecessarily

---

## H05

```text
Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥Å Å¸Ã¨Æ’Â½Ã¥ÂÂ¯Ã¤Â»Â¥Ã¥Å“Â¨ Linux OS Ã¤Â¸Å Ã¥Å¸Â·Ã¨Â¡Å’Ã¯Â¼Å’Windows Ã§â€°Ë†Ã¦Å“Â¬Ã¥â€°â€¡Ã©Å“â‚¬Ã¨Â¦ÂÃ¥ÂÂ¦Ã¥Â¤â€“Ã¨Â¨Â­Ã¥Â®Å¡Ã£â‚¬â€š
```

Inspect:

- CJK/Latin transitions
- clause
- sentence final

Purpose:

- mixed-language ranking

---

## H06

```text
Ã©Â¦â€“Ã¥â€¦Ë†Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â¾â€ Ã§Å“â€¹ API Ã§Å¡â€žÃ¥Å¸ÂºÃ¦Å“Â¬Ã¦Å¾Â¶Ã¦Â§â€¹Ã¯Â¼Å’Ã§â€žÂ¶Ã¥Â¾Å’Ã¥â€ ÂÃ¨ÂªÂªÃ¦ËœÅ½ SDK Ã§Å¡â€žÃ¤Â½Â¿Ã§â€Â¨Ã¦â€“Â¹Ã¥Â¼ÂÃ£â‚¬â€š
```

Expected qualitative hierarchy:

```text
sentence final > clause
```

---

## H07

```text
Ã¤Â¾â€¹Ã¥Â¦â€šÃ¦Ë†â€˜Ã¥â‚¬â€˜Ã¥ÂÂ¯Ã¤Â»Â¥Ã¤Â½Â¿Ã§â€Â¨ Python API Ã¥â€˜Â¼Ã¥ÂÂ«Ã©â‚¬â„¢Ã¥â‚¬â€¹ functionÃ¯Â¼Å’Ã¦Å½Â¥Ã¨â€˜â€”Ã¥â€ ÂÃ¨â„¢â€¢Ã§Ââ€ Ã¥â€ºÅ¾Ã¥â€šÂ³Ã§ÂµÂÃ¦Å¾Å“Ã£â‚¬â€š
```

Inspect:

- technical context
- language transitions
- clause
- sentence final

---

## H08

```text
Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥â€¢ÂÃ©Â¡Å’Ã¥Ëœâ€ºÃ¢â‚¬Â¦Ã¢â‚¬Â¦Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Â¨ÂÃ¥Â¾Å’Ã¥â€ ÂÃ¥â€ºÅ¾Ã¤Â¾â€ Ã¨Â¨Å½Ã¨Â«â€“Ã£â‚¬â€š
```

Expected:

```text
sentence final > ellipsis
```

---

# 13. Group X Ã¢â‚¬â€ Upstream Representation Probes

These cases are intentionally excluded from numeric weight tuning.

## X01 Ã¢â‚¬â€ Decimal

```text
3.14 Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¨ÂªÂªÃ¦ËœÅ½Ã£â‚¬â€š
```

Inspect:

- `.` inside decimal
- sentence-final evidence
- classification

Question:

```text
Does an internal decimal period incorrectly become SENTENCE_FINAL?
```

---

## X02 Ã¢â‚¬â€ Version

```text
v1.2.3-beta Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¤Â»â€¹Ã§Â´Â¹Ã¦â€“Â°Ã§â€°Ë†Ã£â‚¬â€š
```

Question:

```text
Does an internal period incorrectly become SENTENCE_FINAL?
```

---

## X03 Ã¢â‚¬â€ URL

```text
Ã¨Â«â€¹Ã¥ÂÆ’Ã¨â‚¬Æ’ http://example.com Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã§Å¡â€žÃ¨ÂªÂªÃ¦ËœÅ½Ã£â‚¬â€š
```

Question:

```text
Does punctuation inside URL receive inappropriate sentence-final evidence?
```

---

## X04 Ã¢â‚¬â€ ASCII ellipsis

```text
Ã§Å“Å¸Ã§Å¡â€ž......Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¨ÂªÂªÃ¦ËœÅ½Ã£â‚¬â€š
```

Question:

```text
Is the entire ASCII ellipsis run treated as a sequence rather than individual sentence-final punctuation?
```

---

## X05 Ã¢â‚¬â€ Mixed punctuation

```text
Ã§Å“Å¸Ã§Å¡â€žÃ¯Â¼Å¸Ã¯Â¼ÂÃ¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¨ÂªÂªÃ¦ËœÅ½Ã£â‚¬â€š
```

Question:

```text
Is the sequence represented consistently as sentence-final evidence?
```

---

## X06 Ã¢â‚¬â€ Punctuation inside paired delimiter

```text
Ã£â‚¬Å’Ã§Å“Å¸Ã§Å¡â€žÃ¯Â¼Å¸Ã¯Â¼ÂÃ£â‚¬ÂÃ¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¨ÂªÂªÃ¦ËœÅ½Ã£â‚¬â€š
```

Question:

```text
Does the terminal punctuation inside the paired delimiter remain associated with the delimiter's structural context?
```

---

# 14. Removed v0.1 Assumptions

The following v0.1 assumptions are explicitly removed.

### Removed assumption 1

```text
CLAUSE + CJKÃ¢â€ â€™LATIN + whitespace
```

Reason:

Current candidate topology does not demonstrate that these are simultaneously attached to one candidate.

---

### Removed assumption 2

```text
Ã¤Â¸Â­Ã¦â€“â€¡ | English
Ã¢â€ â€™ one candidate
Ã¢â€ â€™ transition + whitespace
Ã¢â€ â€™ +25
```

Reason:

Round 1 demonstrated that the current pipeline may expose separate candidate positions.

---

### Removed assumption 3

```text
technical CLAUSE
Ã¢â€ â€™ 35 - 30
```

Reason:

Phase 2B may already classify protected technical candidates as `OTHER`.

The real Phase 2B output must determine the scoring path.

---

### Removed assumption 4

```text
string-final punctuation
Ã¢â€ â€™ automatically has a candidate after it
```

Reason:

Current candidate generation does not expose the final end-of-input boundary.

---

# 15. Calibration Objectives for v0.2

The Round 2 experiment should answer:

### Objective 1

Does the base hierarchy remain valid?

```text
SENTENCE_FINAL > ELLIPSIS > CLAUSE
```

### Objective 2

Does language transition provide a meaningful but moderate bonus?

```text
transition > plain OTHER
transition < ordinary CLAUSE
```

### Objective 3

What is the actual topology of whitespace candidates?

This is intentionally an empirical question.

### Objective 4

Does technical / atomic protection need an additional Phase 2C penalty after Phase 2B classification?

This must be answered from actual pipeline output.

### Objective 5

Does `INTERNAL = -20` behave correctly when the upstream punctuation representation is valid?

ASCII punctuation anomalies are excluded from this question.

### Objective 6

Do realistic mixed-language notes produce reasonable local ranking?

No final segmentation decision is made.

---

# 16. Calibration Decision Rules

During Round 2:

### KEEP

Use when the current numeric value produces the intended relationship and there is no evidence of instability.

### NEED MORE DATA

Use when the case is representable but the available cases are insufficient to justify changing the value.

### ADJUST

Use only when multiple valid cases demonstrate a consistent undesirable ranking.

### UPSTREAM ISSUE

Use when the result is caused by Phase 1 / 2A / 2B representation rather than numeric scoring.

### CASE ISSUE

Use when the calibration case itself does not correspond to a valid candidate topology.

---

# 17. Round 2 Must Not Do

Do not:

- modify `subtitle_segmenter.py`
- implement Phase 2D
- change Phase 1
- change Phase 2A
- change Phase 2B
- implement production Phase 2C scoring
- change the provisional weights before observing all cases
- introduce special-case scoring
- add normalization
- add thresholding
- add hard floors
- add segment-length factors
- add duration factors
- add line-width factors
- add emoji/emoticon scoring

---

# 18. Current Matrix Status

```text
Phase 2C Calibration Matrix v0.2

Base classes                     READY
Base pairwise hierarchy          READY
Language transition              READY
Whitespace topology              READY FOR OBSERVATION
Technical / atomic               READY FOR OBSERVATION
Punctuation sequence             READY
Sentence-final composition       READY
Realistic mixed-language         READY
Upstream representation probes   SEPARATED
```

The matrix is now designed to answer the actual calibration questions without assuming candidate combinations that the current pipeline does not expose.

---

# 19. Next Step

The next execution step is:

```text
Calibration Matrix v0.2
        Ã¢â€ â€œ
Calibration Round 2
        Ã¢â€ â€œ
Real Phase 1 Ã¢â€ â€™ 2A Ã¢â€ â€™ 2B output
        Ã¢â€ â€œ
Apply unchanged provisional numeric baseline
        Ã¢â€ â€œ
Compare actual ranking
        Ã¢â€ â€œ
Identify genuine numeric calibration issues
        Ã¢â€ â€œ
Numeric Strategy v1
```

No numeric value is frozen by this document.

No production Phase 2C scoring implementation is authorized by this document.
