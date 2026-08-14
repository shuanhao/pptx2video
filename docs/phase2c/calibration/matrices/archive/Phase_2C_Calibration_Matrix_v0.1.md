# Phase 2C Calibration Matrix v0.1

**Status:** Draft for numeric calibration  
**Scope:** Phase 2C Boundary Scoring only

## 1. Calibration Baseline v0

These values are a calibration starting point, not frozen production weights.

| Boundary Class | Base |
|---|---:|
| `SENTENCE_FINAL` | +80 |
| `ELLIPSIS` | +65 |
| `CLAUSE` | +35 |
| `OTHER` | 0 |

| Positive Modifier | Value |
|---|---:|
| CJK → Latin | +15 |
| Latin → CJK | +15 |
| Boundary whitespace | +10 |

| Negative Modifier | Value |
|---|---:|
| Technical context | -30 |
| Atomic context | -30 |
| Punctuation sequence `INTERNAL` | -20 |

Numeric semantics:
- signed `float`
- relative boundary preference, not probability
- `score = Base + Bonuses + Penalties`
- no normalization
- no threshold
- no class-specific hard floor
- no hard constraint
- no global / segment-level context
- emoji / emoticon receive no dedicated scoring in v1

## 2. Calibration Method

The most important result is **relative ranking**, not the absolute number.

Each case should be evaluated for:
1. formula correctness
2. feature isolation
3. pairwise ranking
4. counterexamples

Absolute scores should not become regression-test expectations until the numeric model is frozen.

## 3. Layer 1 — Atomic / Base Cases

| ID | Case | Boundary | Expected |
|---|---|---|---|
| C01 | Sentence final | `今天我們介紹 CPU。` at `。` | `SENTENCE_FINAL = 80` |
| C02 | Ellipsis | `這個問題嘛……` at `……` | `ELLIPSIS = 65` |
| C03 | Clause | `首先，我們介紹 CPU` at `，` | `CLAUSE = 35` |
| C04 | Plain other | `中文\|中文` | `OTHER = 0` |
| C05 | Sentence final vs clause | `。` vs `，` | SF > C |
| C06 | Ellipsis vs clause | `……` vs `，` | E > C |
| C07 | Clause vs other | `，` vs plain boundary | C > O |
| C08 | Sentence final vs ellipsis | `。` vs `……` | SF > E |

## 4. Layer 2 — Positive Interaction Cases

| ID | Case | Expected Score / Relation | Purpose |
|---|---|---|---|
| C09 | `中文\|English` | 0 + 15 = **15** | Isolate CJK→Latin |
| C10 | `English\|中文` | 0 + 15 = **15** | v1 directional symmetry |
| C11 | `中文 \| English` | 0 + 15 + 10 = **25** | Whitespace incremental effect |
| C12 | `English \| 中文` | **25** | Symmetry + whitespace |
| C13 | enriched OTHER vs ordinary CLAUSE | 25 vs 35 | CLAUSE > enriched OTHER |
| C14 | CLAUSE + transition + whitespace | 35 + 15 + 10 = **60** | Context can strengthen CLAUSE |
| C15 | enriched CLAUSE vs ELLIPSIS | 60 vs 65 | ELLIPSIS > enriched CLAUSE |
| C16 | enriched CLAUSE vs SENTENCE_FINAL | 60 vs 80 | SF > enriched CLAUSE |

## 5. Layer 3 — Negative / Protection Cases

| ID | Case | Expected Score / Relation | Purpose |
|---|---|---|---|
| C17 | `1,\|000` with technical context | 35 - 30 = **5*** | Technical protection |
| C18 | `1, \|000` with technical context | 35 + 10 - 30 = **15*** | Whitespace must not cancel protection |
| C19 | Atomic expression boundary | 0 - 30 = **-30*** | Atomic penalty |
| C20 | Punctuation sequence INTERNAL | 0 - 20 = **-20** | Internal sequence penalty |
| C21 | INTERNAL vs END ellipsis | -20 vs 65 | END > INTERNAL |
| C22 | technical CLAUSE vs enriched OTHER | 5 vs 25 | Penalty can reverse ordinary class ranking |
| C23 | technical CLAUSE vs SF | 5 vs 80 | SF remains dominant |

`*` Exact class assignment must come from the real Phase 1 → 2A → 2B pipeline; the arithmetic illustrates the intended scoring interaction and must not override classification.

## 6. Layer 4 — Same Class, Different Context

| ID | Variant A | Variant B | Expected |
|---|---|---|---|
| C24 | `中文\|中文` | `中文\|English` | B > A |
| C25 | `中文\|English` | `中文 \| English` | B > A |
| C26 | ordinary CLAUSE | technical-protected CLAUSE | A > B |
| C27 | plain CLAUSE | CLAUSE + language transition | B > A |
| C28 | CLAUSE + transition | CLAUSE + transition + whitespace | B > A |
| C29 | punctuation INTERNAL | punctuation END | END > INTERNAL |

## 7. Layer 5 — Realistic Mixed-Language Cases

| ID | Representative Notes | Boundaries / Expected Behavior |
|---|---|---|
| C30 | `今天我們先介紹 CPU 的基本架構，接著再說明 GPU 與 NPU 的差異。` | final > comma |
| C31 | `我們使用 ARM Cortex-A 系列 CPU，並搭配 Linux OS。` | final > clause; transitions secondary |
| C32 | `這個架構主要包含 CPU、GPU、NPU 三個主要運算單元，其中 CPU 負責一般運算。` | final strongest; technical list boundaries lower |
| C33 | `CPU / GPU / NPU 是目前常見的 AI accelerator。` | final strongest; avoid technical-list splits |
| C34 | `這個功能可以在 Linux OS 上執行，Windows 版本則需要另外設定。` | final > clause; transitions secondary |
| C35 | `首先我們來看 API 的基本架構，然後再說明 SDK 的使用方式。` | final > clause |
| C36 | `例如我們可以使用 Python API 呼叫這個 function，接著再處理回傳結果。` | final > clause; technical terms protected |
| C37 | `這個問題嘛……我們稍後再回來討論。` | final > ellipsis |
| C38 | `如果設定完成，就可以開始執行。` | final > clause |
| C39 | `接下來我們會看到一個很重要的概念：CPU、GPU 與 NPU 的工作分工。` | colon/list must not outrank final |
| C40 | `換句話說，CPU 負責一般運算，而 GPU 比較適合平行運算。` | final > clauses |

## 8. Layer 6 — Deliberate Counterexamples

| ID | Counterexample | Current Baseline | Question |
|---|---|---|---|
| X01 | `嗯……` vs `CPU、 \| GPU` | 65 vs 60 | Is ELLIPSIS sufficiently preferred? |
| X02 | ordinary CLAUSE vs `中文 \| English` | 35 vs 25 | Is CLAUSE sufficiently preferred? |
| X03 | technical CLAUSE vs transition + whitespace | 5 vs 25 | Is -30 too strong? |
| X04 | SF with minor negative context vs enriched CLAUSE | case-dependent | Can SF be reduced too much? |
| X05 | long technical expression with multiple candidates | case-dependent | Does protection hold consistently? |
| X06 | notes with frequent mixed-language spaces | case-dependent | Does transition + whitespace create too many candidates? |
| X07 | unusual punctuation runs | case-dependent | Does INTERNAL penalty suppress false boundaries without hurting END? |

## 9. Required Pairwise Invariants

### Strong hierarchy
```text
SENTENCE_FINAL > ELLIPSIS
SENTENCE_FINAL > ordinary CLAUSE
SENTENCE_FINAL > enriched CLAUSE
```

### Moderate hierarchy
```text
ELLIPSIS > ordinary CLAUSE
ELLIPSIS > enriched CLAUSE        # currently expected; calibrate
CLAUSE > ordinary OTHER
CLAUSE > OTHER + transition
CLAUSE > OTHER + transition + whitespace
```

### Intended contextual reversal
```text
OTHER + strong positive context > technically protected CLAUSE
```

### Protection
```text
ordinary CLAUSE > technical CLAUSE
ordinary OTHER > atomic OTHER
terminal sequence > internal sequence
```

## 10. Acceptance Rules

A candidate numeric model should satisfy:

1. Deterministic atomic scores.
2. Single-factor changes produce only the intended score delta.
3. CJK→Latin and Latin→CJK remain symmetric in v1.
4. Technical / atomic penalties remain stronger than whitespace bonus.
5. Ordinary CLAUSE remains above ordinary language-transition-only boundaries.
6. Sentence-final remains the strongest normal local boundary.
7. No modifier accidentally dominates the classification hierarchy without explicit design approval.
8. INTERNAL punctuation remains less preferred than a valid sequence endpoint.
9. No emoji/emoticon-specific scoring appears.
10. No segment length, duration, line balance, or neighboring-boundary information is used.
11. No normalization, threshold, or hard floor is introduced.
12. Absolute values are not frozen until counterexamples and realistic cases are reviewed.

## 11. Calibration Workflow

```text
Calibration Matrix v0.1
        ↓
Run baseline scoring
        ↓
Record actual scores
        ↓
Review pairwise rankings
        ↓
Review counterexamples
        ↓
Adjust numeric model
        ↓
Re-run entire matrix
        ↓
Freeze Numeric Strategy v1
        ↓
Convert frozen cases into regression tests
```

## 12. Out of Scope

- Emoji / emoticon scoring
- Segment length
- Subtitle line-width scoring
- Duration
- Neighboring-boundary interactions
- DP objective
- Final `should_cut` decision
- Hard constraints
- Score normalization
- Score thresholding
- ML / LLM scoring
- Automatic weight learning

## 13. Current Candidate Numeric Model

```text
SENTENCE_FINAL = +80
ELLIPSIS       = +65
CLAUSE         = +35
OTHER          =   0

CJK → LATIN    = +15
LATIN → CJK    = +15
Whitespace     = +10

Technical      = -30
Atomic         = -30
Internal Seq   = -20
```

**Status:** Calibration Baseline v0. These numbers are intentionally not frozen.
