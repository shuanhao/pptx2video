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
| CJK Ã¢â€ â€™ Latin | +15 |
| Latin Ã¢â€ â€™ CJK | +15 |
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

## 3. Layer 1 Ã¢â‚¬â€ Atomic / Base Cases

| ID | Case | Boundary | Expected |
|---|---|---|---|
| C01 | Sentence final | `Ã¤Â»Å Ã¥Â¤Â©Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â»â€¹Ã§Â´Â¹ CPUÃ£â‚¬â€š` at `Ã£â‚¬â€š` | `SENTENCE_FINAL = 80` |
| C02 | Ellipsis | `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥â€¢ÂÃ©Â¡Å’Ã¥Ëœâ€ºÃ¢â‚¬Â¦Ã¢â‚¬Â¦` at `Ã¢â‚¬Â¦Ã¢â‚¬Â¦` | `ELLIPSIS = 65` |
| C03 | Clause | `Ã©Â¦â€“Ã¥â€¦Ë†Ã¯Â¼Å’Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â»â€¹Ã§Â´Â¹ CPU` at `Ã¯Â¼Å’` | `CLAUSE = 35` |
| C04 | Plain other | `Ã¤Â¸Â­Ã¦â€“â€¡\|Ã¤Â¸Â­Ã¦â€“â€¡` | `OTHER = 0` |
| C05 | Sentence final vs clause | `Ã£â‚¬â€š` vs `Ã¯Â¼Å’` | SF > C |
| C06 | Ellipsis vs clause | `Ã¢â‚¬Â¦Ã¢â‚¬Â¦` vs `Ã¯Â¼Å’` | E > C |
| C07 | Clause vs other | `Ã¯Â¼Å’` vs plain boundary | C > O |
| C08 | Sentence final vs ellipsis | `Ã£â‚¬â€š` vs `Ã¢â‚¬Â¦Ã¢â‚¬Â¦` | SF > E |

## 4. Layer 2 Ã¢â‚¬â€ Positive Interaction Cases

| ID | Case | Expected Score / Relation | Purpose |
|---|---|---|---|
| C09 | `Ã¤Â¸Â­Ã¦â€“â€¡\|English` | 0 + 15 = **15** | Isolate CJKÃ¢â€ â€™Latin |
| C10 | `English\|Ã¤Â¸Â­Ã¦â€“â€¡` | 0 + 15 = **15** | v1 directional symmetry |
| C11 | `Ã¤Â¸Â­Ã¦â€“â€¡ \| English` | 0 + 15 + 10 = **25** | Whitespace incremental effect |
| C12 | `English \| Ã¤Â¸Â­Ã¦â€“â€¡` | **25** | Symmetry + whitespace |
| C13 | enriched OTHER vs ordinary CLAUSE | 25 vs 35 | CLAUSE > enriched OTHER |
| C14 | CLAUSE + transition + whitespace | 35 + 15 + 10 = **60** | Context can strengthen CLAUSE |
| C15 | enriched CLAUSE vs ELLIPSIS | 60 vs 65 | ELLIPSIS > enriched CLAUSE |
| C16 | enriched CLAUSE vs SENTENCE_FINAL | 60 vs 80 | SF > enriched CLAUSE |

## 5. Layer 3 Ã¢â‚¬â€ Negative / Protection Cases

| ID | Case | Expected Score / Relation | Purpose |
|---|---|---|---|
| C17 | `1,\|000` with technical context | 35 - 30 = **5*** | Technical protection |
| C18 | `1, \|000` with technical context | 35 + 10 - 30 = **15*** | Whitespace must not cancel protection |
| C19 | Atomic expression boundary | 0 - 30 = **-30*** | Atomic penalty |
| C20 | Punctuation sequence INTERNAL | 0 - 20 = **-20** | Internal sequence penalty |
| C21 | INTERNAL vs END ellipsis | -20 vs 65 | END > INTERNAL |
| C22 | technical CLAUSE vs enriched OTHER | 5 vs 25 | Penalty can reverse ordinary class ranking |
| C23 | technical CLAUSE vs SF | 5 vs 80 | SF remains dominant |

`*` Exact class assignment must come from the real Phase 1 Ã¢â€ â€™ 2A Ã¢â€ â€™ 2B pipeline; the arithmetic illustrates the intended scoring interaction and must not override classification.

## 6. Layer 4 Ã¢â‚¬â€ Same Class, Different Context

| ID | Variant A | Variant B | Expected |
|---|---|---|---|
| C24 | `Ã¤Â¸Â­Ã¦â€“â€¡\|Ã¤Â¸Â­Ã¦â€“â€¡` | `Ã¤Â¸Â­Ã¦â€“â€¡\|English` | B > A |
| C25 | `Ã¤Â¸Â­Ã¦â€“â€¡\|English` | `Ã¤Â¸Â­Ã¦â€“â€¡ \| English` | B > A |
| C26 | ordinary CLAUSE | technical-protected CLAUSE | A > B |
| C27 | plain CLAUSE | CLAUSE + language transition | B > A |
| C28 | CLAUSE + transition | CLAUSE + transition + whitespace | B > A |
| C29 | punctuation INTERNAL | punctuation END | END > INTERNAL |

## 7. Layer 5 Ã¢â‚¬â€ Realistic Mixed-Language Cases

| ID | Representative Notes | Boundaries / Expected Behavior |
|---|---|---|
| C30 | `Ã¤Â»Å Ã¥Â¤Â©Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¥â€¦Ë†Ã¤Â»â€¹Ã§Â´Â¹ CPU Ã§Å¡â€žÃ¥Å¸ÂºÃ¦Å“Â¬Ã¦Å¾Â¶Ã¦Â§â€¹Ã¯Â¼Å’Ã¦Å½Â¥Ã¨â€˜â€”Ã¥â€ ÂÃ¨ÂªÂªÃ¦ËœÅ½ GPU Ã¨Ë†â€¡ NPU Ã§Å¡â€žÃ¥Â·Â®Ã§â€¢Â°Ã£â‚¬â€š` | final > comma |
| C31 | `Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â½Â¿Ã§â€Â¨ ARM Cortex-A Ã§Â³Â»Ã¥Ë†â€” CPUÃ¯Â¼Å’Ã¤Â¸Â¦Ã¦ÂÂ­Ã©â€¦Â Linux OSÃ£â‚¬â€š` | final > clause; transitions secondary |
| C32 | `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¦Å¾Â¶Ã¦Â§â€¹Ã¤Â¸Â»Ã¨Â¦ÂÃ¥Å’â€¦Ã¥ÂÂ« CPUÃ£â‚¬ÂGPUÃ£â‚¬ÂNPU Ã¤Â¸â€°Ã¥â‚¬â€¹Ã¤Â¸Â»Ã¨Â¦ÂÃ©Ââ€¹Ã§Â®â€”Ã¥â€“Â®Ã¥â€¦Æ’Ã¯Â¼Å’Ã¥â€¦Â¶Ã¤Â¸Â­ CPU Ã¨Â²Â Ã¨Â²Â¬Ã¤Â¸â‚¬Ã¨Ë†Â¬Ã©Ââ€¹Ã§Â®â€”Ã£â‚¬â€š` | final strongest; technical list boundaries lower |
| C33 | `CPU / GPU / NPU Ã¦ËœÂ¯Ã§â€ºÂ®Ã¥â€°ÂÃ¥Â¸Â¸Ã¨Â¦â€¹Ã§Å¡â€ž AI acceleratorÃ£â‚¬â€š` | final strongest; avoid technical-list splits |
| C34 | `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥Å Å¸Ã¨Æ’Â½Ã¥ÂÂ¯Ã¤Â»Â¥Ã¥Å“Â¨ Linux OS Ã¤Â¸Å Ã¥Å¸Â·Ã¨Â¡Å’Ã¯Â¼Å’Windows Ã§â€°Ë†Ã¦Å“Â¬Ã¥â€°â€¡Ã©Å“â‚¬Ã¨Â¦ÂÃ¥ÂÂ¦Ã¥Â¤â€“Ã¨Â¨Â­Ã¥Â®Å¡Ã£â‚¬â€š` | final > clause; transitions secondary |
| C35 | `Ã©Â¦â€“Ã¥â€¦Ë†Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â¾â€ Ã§Å“â€¹ API Ã§Å¡â€žÃ¥Å¸ÂºÃ¦Å“Â¬Ã¦Å¾Â¶Ã¦Â§â€¹Ã¯Â¼Å’Ã§â€žÂ¶Ã¥Â¾Å’Ã¥â€ ÂÃ¨ÂªÂªÃ¦ËœÅ½ SDK Ã§Å¡â€žÃ¤Â½Â¿Ã§â€Â¨Ã¦â€“Â¹Ã¥Â¼ÂÃ£â‚¬â€š` | final > clause |
| C36 | `Ã¤Â¾â€¹Ã¥Â¦â€šÃ¦Ë†â€˜Ã¥â‚¬â€˜Ã¥ÂÂ¯Ã¤Â»Â¥Ã¤Â½Â¿Ã§â€Â¨ Python API Ã¥â€˜Â¼Ã¥ÂÂ«Ã©â‚¬â„¢Ã¥â‚¬â€¹ functionÃ¯Â¼Å’Ã¦Å½Â¥Ã¨â€˜â€”Ã¥â€ ÂÃ¨â„¢â€¢Ã§Ââ€ Ã¥â€ºÅ¾Ã¥â€šÂ³Ã§ÂµÂÃ¦Å¾Å“Ã£â‚¬â€š` | final > clause; technical terms protected |
| C37 | `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥â€¢ÂÃ©Â¡Å’Ã¥Ëœâ€ºÃ¢â‚¬Â¦Ã¢â‚¬Â¦Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Â¨ÂÃ¥Â¾Å’Ã¥â€ ÂÃ¥â€ºÅ¾Ã¤Â¾â€ Ã¨Â¨Å½Ã¨Â«â€“Ã£â‚¬â€š` | final > ellipsis |
| C38 | `Ã¥Â¦â€šÃ¦Å¾Å“Ã¨Â¨Â­Ã¥Â®Å¡Ã¥Â®Å’Ã¦Ë†ÂÃ¯Â¼Å’Ã¥Â°Â±Ã¥ÂÂ¯Ã¤Â»Â¥Ã©â€“â€¹Ã¥Â§â€¹Ã¥Å¸Â·Ã¨Â¡Å’Ã£â‚¬â€š` | final > clause |
| C39 | `Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¦Å“Æ’Ã§Å“â€¹Ã¥Ë†Â°Ã¤Â¸â‚¬Ã¥â‚¬â€¹Ã¥Â¾Ë†Ã©â€¡ÂÃ¨Â¦ÂÃ§Å¡â€žÃ¦Â¦â€šÃ¥Â¿ÂµÃ¯Â¼Å¡CPUÃ£â‚¬ÂGPU Ã¨Ë†â€¡ NPU Ã§Å¡â€žÃ¥Â·Â¥Ã¤Â½Å“Ã¥Ë†â€ Ã¥Â·Â¥Ã£â‚¬â€š` | colon/list must not outrank final |
| C40 | `Ã¦Ââ€ºÃ¥ÂÂ¥Ã¨Â©Â±Ã¨ÂªÂªÃ¯Â¼Å’CPU Ã¨Â²Â Ã¨Â²Â¬Ã¤Â¸â‚¬Ã¨Ë†Â¬Ã©Ââ€¹Ã§Â®â€”Ã¯Â¼Å’Ã¨â‚¬Å’ GPU Ã¦Â¯â€Ã¨Â¼Æ’Ã©ÂÂ©Ã¥ÂË†Ã¥Â¹Â³Ã¨Â¡Å’Ã©Ââ€¹Ã§Â®â€”Ã£â‚¬â€š` | final > clauses |

## 8. Layer 6 Ã¢â‚¬â€ Deliberate Counterexamples

| ID | Counterexample | Current Baseline | Question |
|---|---|---|---|
| X01 | `Ã¥â€”Â¯Ã¢â‚¬Â¦Ã¢â‚¬Â¦` vs `CPUÃ£â‚¬Â \| GPU` | 65 vs 60 | Is ELLIPSIS sufficiently preferred? |
| X02 | ordinary CLAUSE vs `Ã¤Â¸Â­Ã¦â€“â€¡ \| English` | 35 vs 25 | Is CLAUSE sufficiently preferred? |
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
3. CJKÃ¢â€ â€™Latin and LatinÃ¢â€ â€™CJK remain symmetric in v1.
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
        Ã¢â€ â€œ
Run baseline scoring
        Ã¢â€ â€œ
Record actual scores
        Ã¢â€ â€œ
Review pairwise rankings
        Ã¢â€ â€œ
Review counterexamples
        Ã¢â€ â€œ
Adjust numeric model
        Ã¢â€ â€œ
Re-run entire matrix
        Ã¢â€ â€œ
Freeze Numeric Strategy v1
        Ã¢â€ â€œ
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

CJK Ã¢â€ â€™ LATIN    = +15
LATIN Ã¢â€ â€™ CJK    = +15
Whitespace     = +10

Technical      = -30
Atomic         = -30
Internal Seq   = -20
```

**Status:** Calibration Baseline v0. These numbers are intentionally not frozen.
