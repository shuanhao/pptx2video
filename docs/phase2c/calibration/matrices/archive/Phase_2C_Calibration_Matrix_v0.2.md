# Phase 2C Calibration Matrix v0.2

**Status:** Design / Calibration Draft  
**Supersedes:** Phase 2C Calibration Matrix v0.1  
**Scope:** Phase 2C numeric calibration only  
**Purpose:** Provide a calibration dataset whose cases are actually observable through the current Phase 1 → Phase 2A → Phase 2B pipeline.

---

## 1. Purpose of v0.2

Calibration Round 1 demonstrated that several v0.1 cases were based on assumptions that do not match the current candidate topology or upstream representation.

The purpose of v0.2 is therefore **not to change numeric weights yet**.

The purpose is to make every calibration case:

- representable by the current Phase 1 → 2A → 2B pipeline,
- explicit about the boundary being evaluated,
- explicit about whether the case tests a score, a ranking, or an upstream representation issue,
- free from assumptions about combinations of modifiers that cannot coexist on the same candidate.

The calibration process remains:

```text
Phase 1
    ↓
Phase 2A Boundary Observation
    ↓
Phase 2B Boundary Classification
    ↓
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
| CJK → Latin transition | +15 |
| Latin → CJK transition | +15 |
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
今天我們介紹 CPU。
```

when the intended boundary is after `。`.

Instead use an internal sentence-final boundary:

```text
今天我們介紹 CPU。接下來我們看 GPU。
```

The intended candidate is:

```text
CPU。|接下來
```

This allows Phase 1 → 2A → 2B to observe the actual boundary.

String-final behavior remains an architectural consideration for a later stage and is not modified by Phase 2C.

---

## 3.2 `CLAUSE + language transition` is not assumed

A clause boundary normally has punctuation on one side of the boundary.

Therefore v0.2 does not assume that the same candidate can simultaneously be:

```text
CLAUSE
+
CJK → Latin transition
+
whitespace
```

Such combinations are removed from the calibration model unless the real pipeline demonstrably exposes them.

---

## 3.3 Whitespace is a boundary-local observation

For:

```text
中文 | English
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

# 5. Group A — Base Boundary Classes

These cases establish the base hierarchy using boundaries that actually exist inside the input.

## A01 — Sentence Final

Input:

```text
今天我們介紹 CPU。接下來我們看 GPU。
```

Target:

```text
CPU。|接下來
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

## A02 — Ellipsis

Input:

```text
這個問題嘛……接下來我們再討論。
```

Target:

```text
嘛……|接下來
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

## A03 — Clause

Input:

```text
首先，我們介紹 CPU，接著再看 GPU。
```

Target:

```text
首先，|我們
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

## A04 — Plain OTHER

Input:

```text
中文English
```

Target:

```text
中文|English
```

Expected class:

```text
OTHER
```

Expected evidence:

```text
CJK → Latin
```

This case is therefore not a pure `OTHER = 0` case.

A true plain-OTHER case must be selected from an actual pipeline boundary where no positive or negative modifier applies.

If the current pipeline does not expose such a boundary reliably, record:

```text
CASE STATUS = REPRESENTATION ISSUE
```

Do not invent one.

---

# 6. Group B — Base Pairwise Hierarchy

These cases compare base classes.

## B01 — Sentence Final vs Clause

```text
今天我們介紹 CPU。接下來我們看 GPU，
然後再說明 NPU。
```

Compare:

```text
CPU。|接下來
```

against:

```text
GPU，|然後
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

## B02 — Sentence Final vs Ellipsis

Input:

```text
這個問題嘛……我們先暫停一下。接下來繼續。
```

Compare:

```text
嘛……|我們
```

and:

```text
一下。|接下來
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

## B03 — Ellipsis vs Clause

Input:

```text
這個問題嘛……接下來再討論，現在先看 CPU。
```

Compare:

```text
嘛……|接下來
```

and:

```text
討論，|現在
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

# 7. Group C — Language Transition

These cases isolate language-transition evidence.

## C01 — CJK → Latin

Input:

```text
我們使用 Linux。
```

Target:

```text
使用 | Linux
```

Important:

The exact target position must be chosen from the actual Phase 2A candidate output.

If the pipeline does not create the expected transition boundary, record a representation issue rather than changing upstream behavior.

Expected modifier when applicable:

```text
+15
```

---

## C02 — Latin → CJK

Input:

```text
Linux 系統需要重新設定。
```

Target:

```text
Linux | 系統
```

Expected modifier when applicable:

```text
+15
```

Expected symmetry:

```text
CJK → Latin = Latin → CJK
```

---

## C03 — Transition vs ordinary CLAUSE

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

# 8. Group D — Whitespace Topology

Whitespace is tested as a boundary-local observation rather than automatically stacked with language transition.

## D01 — Whitespace before boundary

Input:

```text
中文 English
```

Inspect the actual candidates around:

```text
中文 | English
```

Record which candidate receives whitespace evidence.

---

## D02 — Whitespace after boundary

Use:

```text
中文 English
```

and inspect the boundary on the other side of the whitespace.

Record actual candidate topology.

---

## D03 — Whitespace on both sides

Input:

```text
中文  English
```

Inspect all exposed candidates.

Purpose:

- determine whether whitespace evidence belongs to one candidate or multiple candidates
- do not assume a single candidate receives `+10` twice

---

## D04 — Transition without whitespace vs whitespace variant

Compare:

```text
中文|English
```

with:

```text
中文 | English
```

but compare the **actual candidate positions separately**.

Expected result is not predefined as:

```text
25 > 15
```

until the real pipeline demonstrates that both modifiers can coexist on the same candidate.

This case exists specifically to resolve the topology discovered in Round 1.

---

# 9. Group E — Technical / Atomic Protection

## E01 — Technical numeric expression

Input:

```text
這個值是 1,000，接下來繼續。
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

## E02 — Version / atomic expression

Input:

```text
目前使用 v1.2.3，接下來介紹新版。
```

Inspect internal candidates inside:

```text
v1.2.3
```

Expected:

- atomic protection evidence where applicable
- actual class from Phase 2B

---

## E03 — Technical candidate vs ordinary clause

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

## E04 — Technical candidate vs language-transition candidate

Compare a real technical-protected candidate against a real language-transition candidate.

Purpose:

- determine whether `Technical = -30` creates an excessive reversal
- do not change the penalty during this round

---

# 10. Group F — Punctuation Sequence

## F01 — Ellipsis END

Input:

```text
這個問題嘛……接下來再討論。
```

Target:

```text
……|接下來
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

## F02 — Ellipsis INTERNAL

Input:

```text
……接下來
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

## F03 — END vs INTERNAL

Compare an actual END candidate with an actual INTERNAL candidate.

Expected:

```text
END > INTERNAL
```

---

# 11. Group G — Sentence-Final / Ellipsis Composition

These cases ensure punctuation composition is not incorrectly treated as a simple character lookup.

## G01 — Ellipsis followed by question

Input:

```text
真的……？接下來我們說明。
```

Target:

```text
……？|接下來
```

Expected:

```text
SENTENCE_FINAL
```

if the existing Phase 1 / 2A / 2B pipeline exposes that result.

Purpose:

- verify sentence-final composition

---

## G02 — Ellipsis followed by exclamation

```text
真的……！接下來我們說明。
```

Expected:

```text
SENTENCE_FINAL
```

---

## G03 — ASCII ellipsis run

```text
真的......接下來我們說明。
```

This is an **upstream observation probe**, not a numeric calibration case.

Record whether Phase 1/2A/2B correctly represents the sequence.

Do not adjust Phase 2C weights based on this case.

---

# 12. Group H — Realistic Mixed-Language Cases

These cases are designed to observe actual score distribution rather than force a predetermined formula.

## H01

```text
今天我們先介紹 CPU 的基本架構，接著再說明 GPU 與 NPU 的差異。
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
我們使用 ARM Cortex-A 系列 CPU，並搭配 Linux OS。
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
這個架構主要包含 CPU、GPU、NPU 三個主要運算單元，其中 CPU 負責一般運算。
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
CPU / GPU / NPU 是目前常見的 AI accelerator。
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
這個功能可以在 Linux OS 上執行，Windows 版本則需要另外設定。
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
首先我們來看 API 的基本架構，然後再說明 SDK 的使用方式。
```

Expected qualitative hierarchy:

```text
sentence final > clause
```

---

## H07

```text
例如我們可以使用 Python API 呼叫這個 function，接著再處理回傳結果。
```

Inspect:

- technical context
- language transitions
- clause
- sentence final

---

## H08

```text
這個問題嘛……我們稍後再回來討論。
```

Expected:

```text
sentence final > ellipsis
```

---

# 13. Group X — Upstream Representation Probes

These cases are intentionally excluded from numeric weight tuning.

## X01 — Decimal

```text
3.14 接下來我們說明。
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

## X02 — Version

```text
v1.2.3-beta 接下來介紹新版。
```

Question:

```text
Does an internal period incorrectly become SENTENCE_FINAL?
```

---

## X03 — URL

```text
請參考 http://example.com 接下來的說明。
```

Question:

```text
Does punctuation inside URL receive inappropriate sentence-final evidence?
```

---

## X04 — ASCII ellipsis

```text
真的......接下來我們說明。
```

Question:

```text
Is the entire ASCII ellipsis run treated as a sequence rather than individual sentence-final punctuation?
```

---

## X05 — Mixed punctuation

```text
真的？！接下來我們說明。
```

Question:

```text
Is the sequence represented consistently as sentence-final evidence?
```

---

## X06 — Punctuation inside paired delimiter

```text
「真的？！」接下來我們說明。
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
CLAUSE + CJK→LATIN + whitespace
```

Reason:

Current candidate topology does not demonstrate that these are simultaneously attached to one candidate.

---

### Removed assumption 2

```text
中文 | English
→ one candidate
→ transition + whitespace
→ +25
```

Reason:

Round 1 demonstrated that the current pipeline may expose separate candidate positions.

---

### Removed assumption 3

```text
technical CLAUSE
→ 35 - 30
```

Reason:

Phase 2B may already classify protected technical candidates as `OTHER`.

The real Phase 2B output must determine the scoring path.

---

### Removed assumption 4

```text
string-final punctuation
→ automatically has a candidate after it
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
        ↓
Calibration Round 2
        ↓
Real Phase 1 → 2A → 2B output
        ↓
Apply unchanged provisional numeric baseline
        ↓
Compare actual ranking
        ↓
Identify genuine numeric calibration issues
        ↓
Numeric Strategy v1
```

No numeric value is frozen by this document.

No production Phase 2C scoring implementation is authorized by this document.
