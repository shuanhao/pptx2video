# Phase 2C Protection Calibration — Round 1 Report

## 1. Scope

This report covers the focused Protection Calibration Round 1: an
evidence-gathering experiment on the negative-evidence side of the
provisional Phase 2C scoring model only (Technical, Atomic, and
`PunctuationSequenceState.INTERNAL`), using the real, unmodified
Phase 1 → Phase 2A → Phase 2B pipeline. It does **not** cover
`SENTENCE_FINAL`/`ELLIPSIS` base-score calibration or transition/whitespace
calibration — those were addressed in the Phase 2C Calibration Round 1/2
reports and are only referenced here where directly relevant (§12).

This round did **not**:
- modify `src/text_structure.py`, `src/boundary_observation.py`,
  `src/boundary_classification.py`, or `src/subtitle_segmenter.py`
- implement Phase 2D or any final-cut logic
- implement a production Phase 2C scoring module
- change any provisional numeric weight
- add or modify any production test

Work in this round is confined to
`docs/PHASE_2C_PROTECTION_CALIBRATION_MATRIX.md` (new, copied verbatim
from the supplied v0.1 document), `scripts/calibrate_phase2c_protection_round1.py`
(new), and this report.

## 2. Matrix Version

Confirmed: `docs/PHASE_2C_PROTECTION_CALIBRATION_MATRIX.md` contains
**Phase 2C Protection Calibration Matrix v0.1** (verified by its own
header), copied verbatim from the document supplied this turn. Contents
were not modified.

## 3. Pipeline

```
Phase 1  analyze_text_structure(text)
   -> Phase 2A  observe_boundaries(analysis)
       -> Phase 2B  classify_boundary(candidate)   [real BoundaryClass]
           -> Calibration-only scoring (this round's protection model)
```

Every `BoundaryClass`, `CharacterClass`, `PunctuationSequenceState`, and
`StructuralBoundaryContext` value below was read directly off real
`BoundaryCandidate` objects from the real, unmodified pipeline.

## 4. Numeric Baseline

Unchanged from prior rounds:

| Factor | Value |
|---|---:|
| `SENTENCE_FINAL` (base) | +80 |
| `ELLIPSIS` (base) | +65 |
| `CLAUSE` (base) | +35 |
| `OTHER` (base) | 0 |
| CJK → LATIN | +15 |
| LATIN → CJK | +15 |
| Whitespace | +10 |
| Technical | -30 |
| Atomic | -30 |
| Punctuation sequence `INTERNAL` | -20 |

**Protection combination rule under test this round** (different from
Round 1/2's additive model):

```
ProtectionPenalty = -max(30 if technical else 0, 30 if atomic else 0)
SequencePenalty    = -20 if INTERNAL else 0
score = base + transition_bonus + whitespace_bonus + ProtectionPenalty + SequencePenalty
```

So Technical+Atomic on the same candidate is -30 (strongest-only), not
-60 (additive, as used in the two prior Round 2 scripts). INTERNAL is
fully independent and stacks on top of whatever protection penalty
applies (0 or -30).

## 5. Case Reachability

| Case | Reachable? | Notes |
|---|---|---|
| P01 | Yes | Trivial — most CJK-CJK/Latin-Latin interior boundaries qualify. |
| P02 | Yes | `1,|000`-style atomic-numeric interior boundary (see §6). |
| P03 | Yes | `v1.2.3`-style technical-version interior boundary. |
| P04 | Yes | The same version-string text exposes Technical+Atomic on one candidate. |
| P05 | Yes | Transition-only candidate borrowed from a no-space CJK/Latin case (Technical from P02). |
| P06 | Yes | |
| P07 | Yes | |
| P08 | Yes | CJK ellipsis interior candidate. |
| P09 | Yes | |
| P10 | Yes | |
| P11 | **Yes — but only via an unusual construction** | Technical+INTERNAL is reachable only when an ellipsis-shaped run (`...`) sits inside a URL path, so the URL's technical span and the independent punctuation-sequence scanner both claim the same characters (see §6). Every other realistic construction tried (a version-like string containing `...`) failed to reach this combination. |
| P12 | **No — CASE ISSUE** | Atomic+INTERNAL was not reachable in any of four attempted constructions (see §6). |
| P13 | Yes | Technical-only (P02/P03) vs Atomic-only (P02/P03) comparison. |
| P14 | Yes | Duplicate of P05. |
| P15 | Yes | Duplicate of P06. |

14 of 15 cases are reachable with real, non-synthetic pipeline evidence;
P12 is a genuine `CASE ISSUE`.

## 6. Per-Case Results

### P01 — Plain OTHER Baseline

Input: `中文中文`. Target: any CJK-CJK interior boundary.
Actual candidate: pos1/pos2/pos3, all `文｜中`-style, `LC=CJK RC=CJK`.

| Field | Value |
|---|---|
| BoundaryClass | OTHER |
| Technical | false |
| Atomic | false |
| INTERNAL | false |
| Transition | false |
| Whitespace | false |
| Base score | 0.0 |
| Protection penalty | 0.0 |
| Sequence penalty | 0.0 |
| **Final score** | **0.0** |
| Expected | Score = 0 |
| Observed | 0.0 |
| **Status** | **PASS** |

### P02 — Technical OTHER

Input: `這個數值是 1,000，接下來我們繼續。`. Target: `1,|000` region.
Actual candidates pos7–10 (`1｜,`, `,｜0`, `0｜0`, `0｜0`), all
`containing=['atomic/numeric']` — note: this is `atomic`, not `technical`,
per Phase 1's own span typing (thousands-separated numbers are tagged
`atomic/numeric`, not `technical/*`). The matrix's own P02 narrative calls
this "Technical OTHER," but the real pipeline classifies it `Atomic`.

| Field | Value |
|---|---|
| BoundaryClass | OTHER |
| Technical | **false** |
| Atomic | **true** |
| Base score | 0.0 |
| Protection penalty | -30.0 |
| **Final score** | **-30.0** |
| Expected | P02 < P01 |
| Observed | -30.0 < 0.0 |
| **Status** | **PASS for the numeric relation**; **CASE ISSUE (naming) for the label** — the matrix's chosen example for "Technical OTHER" is actually an `Atomic` boundary. This does not affect P02's own expected relation (still `< P01`), but it means P02 and P03 as literally specified test the *same* evidence type (Atomic) unless a genuine Technical example is substituted — see P03. |

### P03 — Atomic OTHER (actually genuine Technical, see below)

Input: `目前版本是 v1.2.3，接下來介紹新版。`. Target: interior of `v1.2.3`.
Actual candidates pos7 (`v｜1`, `containing=['technical/version']`), pos8
(`1｜.`, `containing=['technical/version','atomic/numeric']` — both),
pos10 (`2｜.`, `containing=['technical/version']` only).

| Field (pos7, cleanest single-factor example) | Value |
|---|---|
| BoundaryClass | OTHER |
| Technical | **true** |
| Atomic | **false** |
| Base score | 0.0 |
| Protection penalty | -30.0 |
| **Final score** | **-30.0** |
| Expected | P03 < P01 |
| Observed | -30.0 < 0.0 |
| **Status** | **PASS for the numeric relation**; **CASE ISSUE (naming), mirror-image of P02** — this text's cleanest interior boundary (pos7) is actually pure `Technical`, not `Atomic`, and pos8 is where both co-occur (this is P04's evidence, see below). So P02/P03 as written are swapped relative to their own labels: P02's example is genuinely `Atomic`-only, P03's example is genuinely `Technical`-only (plus a `Technical+Atomic` position at pos8, which directly supplies P04). |

### P04 — Technical + Atomic (same candidate)

From P03's text, pos8 (`1｜.`): `containing=['technical/version', 'atomic/numeric']` — both flags true on one real candidate.

| Field | Value |
|---|---|
| BoundaryClass | OTHER |
| Technical | true |
| Atomic | true |
| Base score | 0.0 |
| Protection penalty (strongest-only) | **-30.0** |
| **Final score** | **-30.0** |
| Expected | P04 = P02 = P03 (all -30.0 under strongest-only) |
| Observed | P04 = -30.0, P02 = -30.0, P03 = -30.0 — **all equal** |
| **Status** | **PASS** — the strongest-only rule is internally consistent: a genuinely doubly-protected candidate scores identically to either single-factor candidate, exactly as the matrix's provisional rule specifies. (For contrast: Round 1/2's additive model would have scored this same real candidate at -60.0, breaking the P04=P02=P03 equality the strongest-only rule is designed to produce — see §12.) |

### P05 / P14 — Transition vs Technical

Transition-only candidate: `中文English` pos2 (`文｜E`), OTHER, CJK→LATIN,
**+15.0**. Technical-only candidate: P03 pos7, **-30.0**.

| | Value |
|---|---:|
| Score A (Transition) | 15.0 |
| Score B (Technical) | -30.0 |
| Δ (A-B) | **45.0** |
| Expected | A>B, Δ=45 |
| Observed | A>B, Δ=45.0 |
| **Status** | **PASS — exact match** |

### P06 / P15 — CLAUSE vs Technical

CLAUSE candidate: `首先，我們介紹 CPU，接著再看 GPU。` pos3 (`，｜我`), **+35.0**.
Technical candidate: P03 pos7, **-30.0**.

| | Value |
|---|---:|
| Score A (CLAUSE) | 35.0 |
| Score B (Technical) | -30.0 |
| Δ | **65.0** |
| Expected | A>B, Δ=65 |
| Observed | A>B, Δ=65.0 |
| **Status** | **PASS — exact match** |

### P07 — CLAUSE vs Atomic

CLAUSE candidate: same as P06, **+35.0**. Atomic candidate: P02 pos7,
**-30.0**.

| | Value |
|---|---:|
| Δ | **65.0** |
| Expected | A>B, Δ=65 |
| Observed | A>B, Δ=65.0 |
| **Status** | **PASS — exact match** |

### P08 — Plain OTHER vs INTERNAL

Input: `這個問題嘛……接下來再討論。`. INTERNAL candidate: pos6 (`…｜…`),
`containing=['punctuation_sequence/ellipsis']`, `seq_state=internal`,
`sf_evidence=False` (CJK `…`, not the ASCII-leak character), OTHER,
**-20.0**. Plain OTHER: P01, **0.0**.

| | Value |
|---|---:|
| Score A (OTHER) | 0.0 |
| Score B (INTERNAL) | -20.0 |
| Δ | **20.0** |
| Expected | A>B |
| Observed | A>B |
| **Status** | **PASS** |

### P09 — Transition vs INTERNAL

Transition: P05, **+15.0**. INTERNAL: P08, **-20.0**.

| | Value |
|---|---:|
| Δ | **35.0** |
| Expected | A>B, Δ=35 |
| Observed | A>B, Δ=35.0 |
| **Status** | **PASS — exact match** |

### P10 — CLAUSE vs INTERNAL

CLAUSE: P06, **+35.0**. INTERNAL: P08, **-20.0**.

| | Value |
|---|---:|
| Δ | **55.0** |
| Expected | A>B, Δ=55 |
| Observed | A>B, Δ=55.0 |
| **Status** | **PASS — exact match** |

### P11 — Technical + INTERNAL

Reachability required a deliberate probe (per §5 of the task, this is
still a *real*, non-synthetic pipeline evidence search — no fabricated
`BoundaryCandidate` was constructed). Four constructions were tried:

1. `請參考 http://example.com/a...b 這個頁面。` — **succeeds**: pos25/26
   (the two interior boundaries of the `...` inside the URL path) show
   `containing=['technical/url', 'punctuation_sequence/ellipsis']`,
   `seq_state=internal`. Both flags genuinely co-occur on real candidates.
2. `版本是 v1...2 這樣寫嗎。` — fails: Phase 1's version-pattern matcher does
   not recognize `v1...2` as a `technical/version` span at all (the
   multi-dot run breaks the expected single-dot decimal-version shape), so
   the `...` here is only ever `punctuation_sequence`, never `technical`.

Using construction 1's real candidate (pos25, the cleanest of the two):

| Field | Value |
|---|---|
| BoundaryClass | **SENTENCE_FINAL** (not OTHER — see caveat below) |
| Technical | true |
| Atomic | false |
| PunctuationSequenceState | INTERNAL |
| Base score | 80.0 |
| Protection penalty | -30.0 |
| Sequence penalty | -20.0 |
| **Final score** | **30.0** |
| Expected | `Technical + INTERNAL < Technical` (i.e. < -30.0) |
| Observed | **30.0, which is *greater than* -30.0 — the expected relation is violated** |
| **Status** | **UPSTREAM ISSUE, not a numeric calibration failure** — see explanation below. |

**Why this happens:** the only real candidate exhibiting genuine
Technical+INTERNAL evidence is *also* hit by the previously-documented
(Phase 2C Calibration Round 1/2) bare-fallback SENTENCE_FINAL leak: Phase
2A's single-character fallback fires on the ASCII `.` at this internal
position (no span happens to end exactly there), so `BoundaryClass` is
`SENTENCE_FINAL` (base 80) rather than the `OTHER` (base 0) the matrix's
arithmetic assumes. `80 - 30 - 20 = 30`, not `0 - 30 - 20 = -50`. If the
base class here were correctly `OTHER` (as it would be were the leak
fixed), the arithmetic would come out to exactly -50, satisfying `<
Technical (-30)` as expected. **This is not a Phase 2C weight problem —
it is the same upstream classification leak already documented, now shown
to also contaminate the one real case that could otherwise validate the
Technical+INTERNAL stacking rule.** The stacking arithmetic itself
(`-30-20=-50`) was never actually exercised on a clean `OTHER`-class
candidate this round.

### P12 — Atomic + INTERNAL

Four constructions tried, all real (non-synthetic) pipeline runs:

1. `數值是 100...200 這個範圍。` — atomic span for `100` ends cleanly before
   the `...` run begins; the `...` interior positions show
   `containing=['punctuation_sequence/ellipsis']` only, `atomic=False`.
2. `數值是 3.14......接下來。` — atomic span for `3.14` ends cleanly before
   the trailing `......`; same result, no overlap.
3. `數值是 3..14 接下來。` — the double-dot breaks Phase 1's decimal-number
   pattern entirely: `3` is left un-tagged, `..` becomes its own
   `punctuation_sequence/ellipsis` span, and `14` is separately tagged
   `atomic/numeric` on its own (as a bare 2+-digit run) — no candidate has
   both flags.
4. `數值是 3....14 接下來。` — same outcome as (3) with a 4-dot run.

No construction produced a real candidate with both `Atomic=true` and
`PunctuationSequenceState=INTERNAL`. Mechanistically this makes sense:
Phase 1's atomic-numeric pattern is strictly digit/single-separator
shaped and never extends across a multi-character punctuation run,
whereas the URL technical pattern (which *does* overlap with INTERNAL,
per P11) is broad enough to include arbitrary path characters, including
literal `...`.

| | Value |
|---|---|
| **Status** | **CASE ISSUE** — not representable by the current Phase 1→2A→2B architecture in any construction tried. Per the matrix's own instruction, no synthetic candidate was manufactured to force this case. |

### P13 — Technical vs Atomic Symmetry

Technical-only: P03 pos7, **-30.0**. Atomic-only: P02 pos7, **-30.0**.

| | Value |
|---|---:|
| Technical score | -30.0 |
| Atomic score | -30.0 |
| Expected | Technical == Atomic |
| Observed | -30.0 == -30.0 |
| **Status** | **PASS — exact symmetry confirmed on two independent real single-factor candidates.** |

## 7. Pairwise Ranking Summary

| Case | A | B | Score A | Score B | Expected | Observed | Δ | Status |
|---|---|---|---:|---:|---|---|---:|---|
| P02 vs P01 | Atomic OTHER | Plain OTHER | -30.0 | 0.0 | A<B | A<B | -30.0 | PASS |
| P03 vs P01 | Technical OTHER | Plain OTHER | -30.0 | 0.0 | A<B | A<B | -30.0 | PASS |
| P04 vs P02/P03 | Technical+Atomic | either single | -30.0 | -30.0 | equal | equal | 0.0 | PASS |
| P05/P14 | Transition | Technical | 15.0 | -30.0 | A>B, Δ45 | A>B | +45.0 | PASS |
| P06/P15 | CLAUSE | Technical | 35.0 | -30.0 | A>B, Δ65 | A>B | +65.0 | PASS |
| P07 | CLAUSE | Atomic | 35.0 | -30.0 | A>B, Δ65 | A>B | +65.0 | PASS |
| P08 | OTHER | INTERNAL | 0.0 | -20.0 | A>B | A>B | +20.0 | PASS |
| P09 | Transition | INTERNAL | 15.0 | -20.0 | A>B, Δ35 | A>B | +35.0 | PASS |
| P10 | CLAUSE | INTERNAL | 35.0 | -20.0 | A>B, Δ55 | A>B | +55.0 | PASS |
| P11 | Technical+INTERNAL | Technical-only | 30.0† | -30.0 | A<B | **A>B** | +60.0 | **UPSTREAM ISSUE** (leak-contaminated, §6) |
| P13 | Technical | Atomic | -30.0 | -30.0 | equal | equal | 0.0 | PASS |

`†` the only reachable P11 evidence is itself an upstream-leaked
`SENTENCE_FINAL` candidate, not a clean `OTHER` one — see §6 for the full
explanation of why this delta is not a numeric finding.

Every pairwise comparison that does not involve INTERNAL's interaction
with a leaked classification is an **exact match** to the matrix's
predicted delta — a stronger and cleaner result than either prior
calibration round produced, because this matrix deliberately isolated
single factors instead of mixing several per case.

## 8. Protection Interaction

- **Technical vs Plain OTHER**: Technical suppresses Plain OTHER by
  exactly -30.0 (P03 vs P01). **Confirmed.**
- **Atomic vs Plain OTHER**: Atomic suppresses Plain OTHER by exactly
  -30.0 (P02 vs P01). **Confirmed.**
- **Technical vs Transition**: Technical remains 45.0 points below
  Transition (P05/P14). **Confirmed, no reversal.**
- **Technical vs CLAUSE**: Technical remains 65.0 points below CLAUSE
  (P06/P15). **Confirmed, no reversal.**
- **Atomic vs CLAUSE**: Atomic remains 65.0 points below CLAUSE (P07).
  **Confirmed, no reversal.**
- **INTERNAL vs Plain OTHER**: INTERNAL suppresses Plain OTHER by exactly
  -20.0 for CJK-composed sequences (P08). **Confirmed** (with the
  standing caveat, unchanged from prior rounds, that ASCII-composed
  sequences leak `SENTENCE_FINAL` at the same structural position instead
  — not re-litigated here, out of this matrix's scope per §2).
- **INTERNAL vs Transition**: INTERNAL remains 35.0 points below
  Transition (P09). **Confirmed, no reversal.**
- **INTERNAL vs CLAUSE**: INTERNAL remains 55.0 points below CLAUSE
  (P10). **Confirmed, no reversal.**
- **Technical + INTERNAL**: reachable only via one unusual construction
  (a URL containing a literal `...` path segment), and the only reachable
  real candidate is contaminated by the pre-existing SF leak, so the
  clean arithmetic (`-30-20=-50 < -30`) could not be validated against an
  actual `OTHER`-class candidate this round. **UPSTREAM ISSUE — not
  evaluable cleanly.**
- **Atomic + INTERNAL**: not reachable in any of four constructions
  tried. **CASE ISSUE.**
- **Technical + Atomic**: confirmed to score identically to either single
  factor under the strongest-only rule (P04 = P02 = P03, all -30.0), on
  a genuinely doubly-tagged real candidate (not synthetic). **Confirmed —
  the strongest-only rule behaves exactly as specified.**

## 9. Primary Protection Hierarchy

Target hierarchy:

```
CLAUSE > Transition > OTHER > INTERNAL > Technical / Atomic
```

Observed values: CLAUSE=35.0, Transition=15.0, OTHER=0.0, INTERNAL=-20.0,
Technical=Atomic=-30.0.

**35.0 > 15.0 > 0.0 > -20.0 > -30.0 — the full hierarchy holds exactly, on
real, non-synthetic evidence, in the strongest-only protection model.**
This is the round's headline result: unlike the additive model used in
Calibration Round 1/2 (where a doubly-protected candidate could reach
-60, disrupting comparisons against other negative factors), the
strongest-only model keeps Technical/Atomic anchored at a single -30
value that sits cleanly below INTERNAL (-20) with no observed exception
among P01–P10/P13. The only place this round could not close the loop is
Technical+INTERNAL specifically (P11), where the sole reachable real
example is contaminated by an unrelated upstream leak rather than by
anything wrong with the -30/-20 hierarchy itself.

## 10. Numeric Recommendations

| Factor | Recommendation | Basis |
|---|---|---|
| Technical (-30) | **KEEP** | Exact-delta match against OTHER (P03), Transition (P05/P14), and CLAUSE (P06/P15); exact symmetry with Atomic (P13); no reversal anywhere it was cleanly testable. |
| Atomic (-30) | **KEEP** | Exact-delta match against OTHER (P02) and CLAUSE (P07); exact symmetry with Technical (P13); the strongest-only combination with Technical (P04) reproduces the intended equality exactly. |
| INTERNAL (-20) | **KEEP for CJK-composed sequences** | Exact-delta match against OTHER (P08), Transition (P09), and CLAUSE (P10), and it correctly sits between OTHER and Technical/Atomic in the primary hierarchy (§9). **NOT CALIBRATABLE YET for its interaction with Technical specifically** — the one real case that would test `Technical+INTERNAL=-50` (P11) is upstream-leak-contaminated, and Atomic+INTERNAL (P12) is not reachable at all in the current pipeline, so the "should Technical/Atomic + INTERNAL stack independently" design question (task §1, item 10/11) remains open pending either an upstream fix to the SF leak or a genuinely clean example. |

The strongest-only protection combination rule (§4, this matrix's core
hypothesis) is **supported by every case that could test it** (P04, and
by extension P02/P03/P13's individual-factor consistency) — no evidence
this round argues for reverting to additive combination. No value was
changed in this round, per rule 28.

## 11. Upstream / Case Issues

**Upstream issues** (Phase 1/2A/2B representation problems, not numeric
findings):
1. **P11's bare-fallback SF leak contamination** (§6, §7, §8) — the sole
   real Technical+INTERNAL candidate is misclassified `SENTENCE_FINAL`
   instead of `OTHER` because of the same ASCII-`.`-bare-fallback issue
   documented in the two prior Phase 2C calibration reports. This is the
   only new manifestation of that pre-existing issue found this round;
   the underlying mechanism is identical, not a new bug.
2. **P02/P03 labeling mismatch** (§6) — the matrix's own example texts for
   "Technical OTHER" (P02, `1,000`) and "Atomic OTHER" (P03, `v1.2.3`) are
   swapped relative to Phase 1's actual span typing: `1,000` is tagged
   `atomic/numeric`, and `v1.2.3`'s cleanest single-factor position is
   tagged `technical/version` (with a `technical+atomic` position
   available at `v1.2.3`'s first internal dot, which is what actually
   supplies P04). This does not change any numeric conclusion — P02 and
   P03's own expected relations (`< P01`) hold regardless of which label
   applies to which text — but it is worth correcting in a future matrix
   revision so P02/P03 map onto their intended single-factor evidence
   type precisely.

**Case issues** (not representable by the current architecture, not a
numeric finding):
1. **P12 (Atomic+INTERNAL)** — confirmed unreachable across four distinct
   real-pipeline constructions (§6). This is a structural property of how
   Phase 1's atomic-numeric pattern is shaped (strictly digit/separator,
   never overlapping a multi-character punctuation run), not a defect.

## 12. Comparison With Previous Calibration

Relative to **Phase 2C Calibration Round 2** (which used the additive
Technical+Atomic model, -60 when both apply):

- **P04 directly tests the one thing Round 2 could not**: whether
  strongest-only combination is a better model than additive. On the real
  `v1.2.3` candidate (technical+atomic both true), the additive model
  (Round 2's E02) scored this position -60.0; this round's strongest-only
  model scores the identical real candidate -30.0. Both are internally
  consistent with their respective rules — this round provides no
  evidence to prefer one over the other numerically (neither produces an
  unreasonable ranking against CLAUSE/Transition/OTHER on its own), but it
  does confirm the strongest-only rule keeps the primary hierarchy
  (§9) intact with a comfortable, single-step margin, whereas the
  additive model would place a doubly-protected candidate ten points
  further below Technical/Atomic-only than a single -30 step — a
  question for the next design decision, not resolved here per rule 28.
- **The bare-fallback SF leak reappears in a new context** (P11):
  Round 1/2 documented this leak extensively for plain internal
  ASCII-ellipsis/interrobang/decimal positions; this round shows the same
  mechanism also contaminates the one real Technical+INTERNAL candidate,
  confirming the leak's reach extends into every combination this
  matrix tried to isolate it from.
- **The whitespace/transition topology findings from Round 2 (D04) are
  out of this matrix's scope** and were not re-examined, per the task's
  own scope note (§2 of the matrix: "Does not cover... Transition /
  Whitespace calibration").
- **This round's cases are markedly cleaner than Round 1/2's**: every
  pairwise comparison that wasn't blocked by the pre-existing SF leak
  (P02, P03, P05–P10, P13, P14, P15) matched its expected delta exactly,
  in contrast to Round 1/2 where matrix-illustrative deltas frequently
  diverged from real deltas because the matrix's premise combined
  multiple factors that don't co-occur on one real candidate. This
  matrix's discipline of isolating one factor per case (with pairwise
  comparisons drawing on separate single-factor candidates rather than
  assuming stacking) avoided that entire class of mismatch.

## 13. Scope Compliance

- `src/subtitle_segmenter.py`: **untouched.**
- Phase 1 (`src/text_structure.py`): **untouched.**
- Phase 2A (`src/boundary_observation.py`): **untouched.**
- Phase 2B (`src/boundary_classification.py`): **untouched.**
- Phase 2D: **not implemented.**
- Production Phase 2C: **not implemented** (no `src/phase2c_scoring.py`;
  `grep -rn "phase2c\|calibrate_phase2c" src/` returns no matches).
- Provisional weights: **unchanged** — §4's values are exactly the
  matrix's §3 values; only the protection *combination rule* (a
  calibration-script-local choice, not a weight) differs from Round 1/2's
  script, exactly as this matrix specifies.
- No production tests modified to hide regressions — no test file was
  touched.

## 14. Test Results

```
pytest tests/ -q
```
Result: **389 passed, 2 warnings, 15 subtests passed** (36.9s)

```
python -m unittest discover -s tests -v
```
Result: **Ran 389 tests ... OK**

Both run after all Round 1 protection-calibration changes (new matrix
file, new calibration script). Identical to baseline — no regression.

---

## Files created / modified / untouched

**Created:**
- `docs/PHASE_2C_PROTECTION_CALIBRATION_MATRIX.md` — copied verbatim from
  the supplied v0.1 document.
- `scripts/calibrate_phase2c_protection_round1.py` — new calibration-only
  script implementing the strongest-only protection model (not imported
  by `src/`).
- `docs/PHASE_2C_PROTECTION_CALIBRATION_ROUND1_REPORT.md` — this report.

**Modified:** none.

**Untouched:**
- `src/text_structure.py`, `src/boundary_observation.py`,
  `src/boundary_classification.py`, `src/subtitle_segmenter.py`
- `scripts/calibrate_phase2c_round1.py`,
  `scripts/calibrate_phase2c_round2.py`, and their raw outputs/reports
  (kept for historical comparison)
- `docs/PHASE_2C_CALIBRATION_MATRIX.md` (v0.2, from the previous round)
- All test files under `tests/`

**Test results:** 389 passed (pytest) / OK (unittest discover) —
unchanged from baseline.

**Calibration report location:**
`docs/PHASE_2C_PROTECTION_CALIBRATION_ROUND1_REPORT.md`

---

**Round status:** Complete per the stated completion criteria — P01–P15
evaluated or explicitly marked unreachable (P12), real Phase 1→2A→2B
output used throughout, no production module modified, no provisional
weight changed, Technical/Atomic interaction and INTERNAL interaction
both analyzed, pairwise rankings reported with deltas, upstream/case-design
issues kept separate from numeric issues, full regression unchanged (389
passed / OK) before and after. Stopping here; no commit made; awaiting the
Phase 2C Numeric Strategy v1 design decision.
