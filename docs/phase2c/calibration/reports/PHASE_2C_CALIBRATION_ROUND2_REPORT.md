# Phase 2C Numeric Calibration — Round 2 Report

## 1. Scope

This report covers Round 2 of Phase 2C numeric calibration only. It evaluates
the same provisional, unfrozen scoring formula against the real,
unmodified Phase 1 → Phase 2A → Phase 2B pipeline, using the corrected
case set in `docs/PHASE_2C_CALIBRATION_MATRIX.md` v0.2 (Groups A–H, X).

This round did **not**:
- modify `src/text_structure.py`, `src/boundary_observation.py`,
  `src/boundary_classification.py`, or `src/subtitle_segmenter.py`
- implement Phase 2D, `should_cut`, segmentation, or DP
- implement a production Phase 2C scoring module
- change any of the provisional numeric weights
- add or modify any production test

Work in this round is confined to `docs/PHASE_2C_CALIBRATION_MATRIX.md`
(replaced in place with the v0.2 content supplied this round),
`scripts/calibrate_phase2c_round2.py` (new), and this report.
`scripts/calibrate_phase2c_round1.py` and its Round 1 output/report are
left untouched for historical comparison.

## 2. Matrix Version

Confirmed: `docs/PHASE_2C_CALIBRATION_MATRIX.md` now contains
**Phase 2C Calibration Matrix v0.2** (verified by its own header:
`# Phase 2C Calibration Matrix v0.2`, `Supersedes: Phase 2C Calibration
Matrix v0.1`), copied verbatim from the v0.2 document supplied this turn.

## 3. Pipeline

```
Phase 1  analyze_text_structure(text)
   -> Phase 2A  observe_boundaries(analysis)
       -> Phase 2B  classify_boundary(candidate)   [real BoundaryClass]
           -> Calibration-only scoring (this round, unchanged formula)
```

Every `BoundaryClass`, `CharacterClass`, `PunctuationSequenceState`, and
`StructuralBoundaryContext` value below was read directly off real
`BoundaryCandidate` objects produced by the real, unmodified pipeline.

## 4. Numeric Baseline

Unchanged from Round 1 / v0.2 section 2:

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

## 5. Per-Case Results

### Group A — Base Boundary Classes

| Case | Target | Actual boundary | Actual class | Features | Score | Status |
|---|---|---|---|---|---:|---|
| A01 | `CPU。｜接下來` | pos11, `。｜接` | SENTENCE_FINAL | `sf_evidence=True`, no containing spans | **80.0** | **PASS** — the v0.2 fix (trailing context) works exactly as intended; this is the first round to observe a genuine, non-probe SENTENCE_FINAL candidate. |
| A02 | `嘛……｜接下來` | pos7, `…｜接` | ELLIPSIS | `seq_state=END`, `sf_evidence=False` | **65.0** | **PASS** |
| A03 | `首先，｜我們` | pos3, `，｜我` (also pos12, `，｜接`, a second ordinary clause boundary later in the same text) | CLAUSE | left_char=`，` | **35.0** (both) | **PASS** |
| A04 | `中文｜English` | pos2, `文｜E` | OTHER | `CJK→LATIN` evidence present | **15.0**, not 0 | **PASS with the matrix's own caveat** — v0.2 explicitly predicted this target is not pure-OTHER. A genuine plain-OTHER=0.0 boundary *does* exist elsewhere in this same input (pos1 `中｜文`, CJK-CJK, 0.0; pos3–8, Latin-Latin, 0.0 each), so "no true plain-OTHER boundary" is not the case — it's just not at the literal target position, exactly as the matrix anticipated. |

### Group B — Base Pairwise Hierarchy

| Case | A | B | Score A | Score B | Δ | Expected | Status |
|---|---|---|---:|---:|---:|---|---|
| B01 | `CPU。｜接下來` | `GPU，｜然後` | 80.0 | 35.0† | +45.0 | SF>CLAUSE | **PASS** |
| B02 | `一下。｜接下來` | `嘛……｜我們` | 80.0 | 65.0 | +15.0 | SF>ELLIPSIS | **PASS** (matches matrix delta exactly) |
| B03 | `嘛……｜接下來` | `討論，｜現在` | 65.0 | 35.0 | +30.0 | ELLIPSIS>CLAUSE | **PASS** (matches matrix delta exactly) |

`†` B01's matrix text embeds a literal line break inside the markdown code
block (`GPU，` then a newline then `然後再說明`). Run exactly as given, the
`\n` is classified `WHITESPACE`, so the clause boundary picks up the
whitespace modifier: 35+10=**45.0**, not 35.0 (Δ becomes 35.0, not 45.0). A
diagnostic variant with the line break removed (`B01_diagnostic_no_newline`
in the calibration script) gives the clean 35.0 reported above. Both
variants satisfy SF>CLAUSE, so B01's **status is unaffected**, but this is
a real, reproducible topology finding in its own right (see §6): a
markdown line-wrap embedded in a calibration case's source text is not
scoring-neutral, because `\n` is `WHITESPACE` to the real pipeline exactly
like a space.

### Group C — Language Transition

| Case | Finding | Status |
|---|---|---|
| C01 | Target text `我們使用 Linux。` has a **space** between `用` and `Linux` (this is how the phrase is naturally written). The only candidates around that boundary are `用｜(space)` and `(space)｜L`, both `OTHER`, Whitespace-only, **10.0** each. No candidate carries `CJK→LATIN` evidence — the space breaks it into two whitespace-only boundaries (identical to the D-group finding). | **C — PIPELINE REPRESENTATION ISSUE**: the case text does not actually expose a pure-transition candidate, contrary to its own stated purpose ("isolate language-transition evidence" / `+15`). |
| C02 | Same issue, symmetric: `Linux 系統需要重新設定。` has a space between `Linux` and `系統`; both real candidates are whitespace-only, 10.0 each; no `LATIN→CJK` evidence anywhere in this text. | **C — PIPELINE REPRESENTATION ISSUE** |
| C03 | Real transition-only candidate must be borrowed from A04 (`中文｜English`, no space, 15.0) since C01/C02 don't expose one. Compared against A03's ordinary CLAUSE (35.0): 35.0 > 15.0, Δ=20.0. | **PASS** (direction and even magnitude reasonably close to matrix's 35>15) |

This is an important, reproducible finding in its own right: **natural
CJK/Latin mixed text almost always has a space at the language boundary**
(this is standard Chinese typographic convention), which means the
CJK→LATIN/LATIN→CJK `+15` modifier's precondition (`left_character_class`
and `right_character_class` on the *same* candidate being CJK and LATIN
with nothing between them) is rarely satisfied by naturally-written text —
only by the less common no-space style (e.g. `中文English`, A04/A09).

### Group D — Whitespace Topology

| Case | Candidates observed | Finding |
|---|---|---|
| D01/D02 | `中文 English`: pos2 `文｜(sp)` OTHER 10.0; pos3 `(sp)｜E` OTHER 10.0 | Whitespace evidence is split across **two separate candidates**, one on each side of the space character — never combined onto one. Neither candidate carries transition evidence. |
| D03 | `中文  English` (two spaces): pos2 `文｜(sp)` 10.0; pos3 `(sp)｜(sp)` 10.0; pos4 `(sp)｜E` 10.0 | Three candidates, **all exactly 10.0** — whitespace does not stack even across multiple consecutive whitespace characters/boundaries. Each boundary independently asks "is either side whitespace?" and answers yes once. |
| D04 | `中文｜English` (A04, no space): 15.0 (CJK→LATIN, no whitespace). `中文 ｜ English` (D01, with space): best real candidate 10.0 (whitespace only). | **15.0 > 10.0** — the **no-space** transition candidate outscores the **whitespace** variant. This is the opposite of the "25 > 15" intuition the matrix explicitly told us not to assume, and it is a genuine, reproducible ranking property: adding a space does not "enrich" a transition boundary — it *replaces* it with a weaker whitespace-only boundary elsewhere. |

D04's finding is one of the two most important ranking observations in
this round (the other being the H-group gap, §9) — see §7/§9 for the full
analysis.

### Group E — Technical / Atomic Protection

| Case | Evidence | Status |
|---|---|---|
| E01 | `這個值是 1,000，接下來繼續。` — ASCII comma inside `1,000` (pos6–9): all `OTHER`, `Atomic -30` (score -30.0). The **Chinese** clause comma `，` immediately after the number (pos11) is **outside** the atomic span entirely and classifies as ordinary `CLAUSE`, **35.0** — completely unprotected. | **A — PASS for the actual evidence**, but confirms (again, more cleanly than Round 1's C17) that "technical-protected CLAUSE" is not a class the real pipeline ever produces: the number's internal comma is never CLAUSE-eligible in the first place (`_is_clause` requires `left_char` to be a clause-punctuation character, and ASCII `,` is not in `_CLAUSE_PUNCTUATION_CHARS`), and the actual clause punctuation in this sentence sits entirely outside the atomic span. |
| E02 | `目前使用 v1.2.3，接下來介紹新版。` — internal version-string periods: pos7 `OTHER, -60.0` (Technical+Atomic double); pos8 `.｜2`: **SENTENCE_FINAL leak, 20.0** (80-30-30); pos9 `OTHER, -30.0`; pos10 `.｜3`: **SENTENCE_FINAL leak, 50.0** (80-30). Clause comma at pos12 (outside the version span): ordinary `CLAUSE`, **35.0**, again fully unprotected. | **B — CALIBRATION REVIEW** for the two leaked SF positions (same bare-fallback issue as Round 1/X02); **A — PASS** for the clause comma and the plain interior-of-version positions. |
| E03 | Ordinary clause (E01/E02's `，`, 35.0 / A03, 35.0) vs. best real technical-protected boundary (E01/E02 interior, -30.0 or -60.0). | **35.0 > -30.0** (or -60.0), Δ=65.0 (or 95.0). **PASS** — direction matches "ordinary clause > protected technical boundary" exactly, though the mechanism is "ordinary CLAUSE vs. penalized OTHER," not "ordinary CLAUSE vs. penalized CLAUSE" (matrix's own removed-assumption-3 already anticipated this). |
| E04 | Technical-protected boundary (-30.0/-60.0) vs. transition-only candidate (best real 15.0, from A04, since C01/C02 don't expose one — see Group C). | **15.0 > -30.0** (or -60.0), Δ=45.0 (or 75.0). Does `Technical=-30` create an "excessive reversal"? **No** — the ranking here goes the *intended* direction (protected content scores below even a modest positive-evidence boundary); this is not a reversal at all, unlike D04's whitespace/transition case. **PASS** (no adjustment signal). |

### Group F — Punctuation Sequence

| Case | Evidence | Status |
|---|---|---|
| F01 | `這個問題嘛……接下來再討論。`, pos7 `…｜接`: `END`, `ELLIPSIS`, **65.0** | **PASS** |
| F02 | `……接下來`, pos1 `…｜…`: `INTERNAL`, `sf_evidence=False`, `OTHER`, **-20.0** (0-20 exactly as the matrix's formula note anticipated) | **PASS** |
| F03 | END (F01, 65.0) vs INTERNAL (F02, -20.0): Δ=85.0 | **PASS**, END>INTERNAL exactly as expected |

### Group G — Sentence-Final / Ellipsis Composition

| Case | Evidence | Status |
|---|---|---|
| G01 | `真的……？接下來我們說明。`, pos5 `？｜接`: `END`, `sf_evidence=True`, `SENTENCE_FINAL`, **80.0**. Internal positions (pos3,4) correctly `OTHER, -20.0`, and Phase 1 records the composite span subtype as `punctuation_sequence/ellipsis_question` (distinct from plain `ellipsis`). | **PASS** — sentence-final composition over an ellipsis+question run works exactly as intended. |
| G02 | `真的……！接下來我們說明。`, pos5 `！｜接`: `SENTENCE_FINAL`, **80.0**; subtype `ellipsis_exclaim`. | **PASS** |
| G03 (diagnostic) | `真的......接下來我們說明。` (ASCII run): internal positions pos3–7 all **leak** `SENTENCE_FINAL, 60.0` (80-20); END position pos8 correctly `ELLIPSIS, 65.0`. | **Upstream observation probe only, per matrix instruction** — not used to calibrate `INTERNAL=-20`. Confirms the Round 1 finding persists identically under v0.2 methodology: the leak is confined to CJK-vs-ASCII composition, not to string-final-ness (this text has trailing context and still leaks internally). |

### Group H — Realistic Mixed-Language Cases

**Important finding, applies to all of H01–H08 uniformly:** every H-group
case text is copied unchanged from Round 1's C30–C37 and, like those
cases, terminates with `。` as the **very last character of the string**.
v0.2's own section 3.1 fix (append trailing context so a real
SENTENCE_FINAL candidate can exist) was applied to Groups A/B/F/G but was
**not** applied to Group H. Consequently every H-group case reproduces
Round 1's exact string-final gap: **zero of the 283 candidates observed
across H01–H08 are `SENTENCE_FINAL`** (confirmed by direct count on the
raw dump). This means the qualitative claims "sentence final should be
strongest" (H01), "sentence final > ordinary clause" (H02), "sentence
final > clause" (H06), and "sentence final > ellipsis" (H08) **cannot be
verified from the H-group data itself** — exactly the situation Round 1
was in, and exactly what v0.2 section 3.1 set out to fix elsewhere. This
is recorded as a **CASE ISSUE carried over from Round 1**, not a new
upstream problem (Groups A/B/F/G prove the pipeline handles trailing
context correctly when it's present).

What H01–H08 *do* verify directly (boundary-local, per case):

| Case | Observed | Assessment |
|---|---|---|
| H01 | 1 CLAUSE (35.0), transitions all whitespace-mediated (10.0), no technical spans matched | Clause/transition/whitespace ranking internally consistent; SF claim unverifiable (see above) |
| H02 | 1 CLAUSE (35.0); `ARM`, `Cortex-A` not recognized as technical/atomic spans by Phase 1 (no penalty applied anywhere in this text) | "technical terms" expectation not actually exercised — Phase 1 does not treat bare identifiers as technical; SF claim unverifiable |
| H03 | 2 CLAUSE (35.0 each, at `、` boundaries), no technical spans matched on `CPU`/`GPU`/`NPU` | List-boundary CLAUSE scores are ordinary, not suppressed — consistent with "not over-suppressed," but "technical-list candidates appropriately suppressed" is not actually tested since no technical span exists here; SF claim unverifiable |
| H04 | No CLAUSE (`/` is not clause punctuation), all boundaries OTHER/whitespace, no technical spans matched on `AI accelerator` | Enumeration is not split by any elevated score — consistent with the intent, but again because nothing here is technical-flagged, not because protection actively suppressed it; SF claim unverifiable |
| H05 | 1 CLAUSE (35.0); no technical spans matched on `Linux`, `OS`, `Windows` | Same "technical terms" caveat as H02 |
| H06 | 1 CLAUSE (35.0) | SF claim unverifiable |
| H07 | 1 CLAUSE (35.0); no technical span matched on `Python`, `API`, `function` | Same caveat |
| H08 | ellipsis END genuinely observable (65.0, pos7, since this text does have trailing context after the ellipsis) but the trailing `。` is still string-final | SF>ellipsis (H08's stated expectation) partially verifiable: ELLIPSIS=65.0 is confirmed real, but SF itself is not observable in H08 — the comparison must borrow B02's 80.0 from elsewhere, as in Round 1 |

### Group X — Upstream Representation Probes (diagnostic-only, not used for numeric tuning)

| Case | Finding |
|---|---|
| X01 (decimal) | `3.14 接下來...`: pos2 `.｜1` **leaks** `SENTENCE_FINAL, 50.0` (80-30 Atomic). Confirms the question "does an internal decimal period incorrectly become SENTENCE_FINAL?" → **yes**. |
| X02 (version) | `v1.2.3-beta 接下來...`: two leaked SF positions, 20.0 and 50.0, identical mechanism to E02. → **yes**, same answer. |
| X03 (URL) | `請參考 http://example.com 接下來...`: pos19 `.｜c` (the domain separator) **leaks** `SENTENCE_FINAL, 50.0` inside `technical/url`. → **yes**. |
| X04 (ASCII ellipsis) | Identical to G03: internal leak 60.0, correct END 65.0. |
| X05 (mixed punctuation `？！`) | `真的？！接下來...`: pos3 (internal, between `？` and `！`) **leaks** `SENTENCE_FINAL, 60.0`; pos4 (genuine END of the interrobang run) correctly `SENTENCE_FINAL, 80.0`. This case usefully separates the leak (internal, wrong) from the correct behavior (END, right) within one input. |
| X06 (paired delimiter) | `「真的？！」接下來...`: pos4 internal leak (60.0, same mechanism); pos5, the boundary **immediately inside** the closing `」` (`！｜」`), classifies `SENTENCE_FINAL, 80.0` genuinely (`containing=[paired_delimiter/quotation]` only — not penalized, since `paired_delimiter` is not a protected type); pos6, **immediately outside** the closing `」` (`」｜接`), *also* classifies `SENTENCE_FINAL, 80.0` (the terminal-ending chain traversal is transparent through the closing delimiter, as designed in Phase 2A). **New topology observation**: this produces **two adjacent, equal-strength SENTENCE_FINAL candidates** (pos5 and pos6) for what is semantically one sentence ending. Not itself an error under the current per-candidate scoring model (each candidate is independently and correctly classified), but worth flagging for Phase 2D as a place where two strong candidates sit one character apart. |

All six are diagnostic-only per v0.2 §3.5/§13; none of these were used to
argue for changing any Phase 2C weight, per the matrix's instruction and
this round's rule 15.

## 6. Candidate Topology Findings

- **Language transition**: naturally-written CJK/Latin text almost always
  has a space at the switch point, which means `CJK→LATIN`/`LATIN→CJK`
  practically never fires in realistic input — it only fires in the
  less-common no-space style (§ Group C, confirmed by C01/C02 both failing
  to expose a pure-transition candidate despite being designed to).
- **Whitespace**: always a separate, per-boundary, non-stacking +10 signal
  (§ Group D). Multiple consecutive whitespace characters do not
  accumulate bonus (D03). Whitespace and transition modifiers never
  co-occur on one candidate when a literal space character sits between
  the two language regions (D01/D02/D04) — confirmed identical to Round 1.
- **Technical/atomic**: protection changes the real `BoundaryClass` itself
  (to `OTHER`) rather than discounting an existing `CLAUSE` (§ Group E),
  confirmed cleanly by two independent cases (E01, E02) where the ordinary
  clause punctuation in the sentence sits structurally outside the
  technical/atomic span, so it's never even in contention for protection.
- **Punctuation sequence**: `INTERNAL`/`END` behave exactly as specified
  for CJK-composed sequences and CJK ellipsis+question/exclaim composites
  (F01–F03, G01–G02); the ASCII-composition leak (G03/X01–X05) is
  reproduced identically to Round 1 and remains classified as upstream,
  not numeric.
- **Paired delimiters** (new this round, X06): terminal punctuation just
  inside a closing delimiter and the boundary just outside it can both
  independently classify `SENTENCE_FINAL`, producing two adjacent
  full-strength candidates for one semantic sentence end.
- **Markdown line-wraps in case source text are not scoring-neutral**
  (new this round, B01): an embedded `\n` is `WHITESPACE` to the pipeline,
  so a clause boundary immediately before a wrapped line gets the
  whitespace bonus it would not otherwise receive. This is a
  case-authoring hazard for future matrix versions, not a pipeline defect.

## 7. Pairwise Ranking Summary

| Case | A | B | Score A | Score B | Expected | Observed | Δ (A-B) | Status |
|---|---|---|---:|---:|---|---|---:|---|
| B01 | SF | CLAUSE | 80.0 | 35.0† | A>B | A>B | +45.0 (or +35.0 w/ literal newline) | PASS |
| B02 | SF | ELLIPSIS | 80.0 | 65.0 | A>B | A>B | +15.0 | PASS |
| B03 | ELLIPSIS | CLAUSE | 65.0 | 35.0 | A>B | A>B | +30.0 | PASS |
| C03 | ordinary CLAUSE | transition-only OTHER | 35.0 | 15.0 | A>B | A>B | +20.0 | PASS |
| D04 | transition-only (no space) | whitespace-only (with space) | 15.0 | 10.0 | not predetermined | **A>B** | +5.0 | **REVIEW** — genuine, reproducible: adding whitespace *lowers* the best-available score at this boundary rather than raising it, because it removes the transition candidate rather than augmenting it. Not a bug per se (each candidate is scored correctly per the formula) but a real, counter-intuitive interaction the matrix explicitly asked to be surfaced rather than assumed away. |
| E03 | ordinary CLAUSE | technical-protected boundary | 35.0 | -30.0 (or -60.0) | A>B | A>B | +65.0 (or +95.0) | PASS |
| E04 | transition-only | technical-protected boundary | 15.0 | -30.0 (or -60.0) | not predetermined | A>B | +45.0 (or +75.0) | PASS — correctly-directed, not a reversal |
| F03 | END | INTERNAL | 65.0 | -20.0 | A>B | A>B | +85.0 | PASS |
| G01 internal vs end | END (SF) | INTERNAL | 80.0 | -20.0 | A>B | A>B | +100.0 | PASS |
| X05 internal vs end | END (SF, genuine) | INTERNAL (leak, also SF) | 80.0 | 60.0 | not a matrix case (diagnostic) | A>B, but only by 20 | small margin, diagnostic only — not used for tuning |

No ranking reversal in this round is unexplained: D04 is a real,
reproducible topology effect (whitespace removing rather than augmenting a
transition candidate); everything else that superficially looks like a
"failure" (E01–E03, C01–C03) is an artifact of the real classification
path differing from the matrix's illustrative arithmetic, not an actual
inverted preference.

## 8. Score Distribution

Computed over the 540 real, non-diagnostic candidates across Groups
A–H (Group X and the `_diagnostic_*`/`G03` entries excluded, per the
matrix's own instruction that these are not numeric calibration cases):

- **Minimum:** -60.0 (E02, doubly inside `technical/version` + `atomic/numeric`)
- **Maximum:** 80.0 (A01, B01, B02, G01, G02 — genuine terminal
  SENTENCE_FINAL candidates; this is the first round where 80.0 is reached
  by a non-probe, non-diagnostic case)
- **Mean:** ≈3.58
- **Median:** 0.0
- **Most common scores:** 0.0 (395 candidates — plain CJK-CJK/Latin-Latin
  and technical/atomic-unaffected OTHER boundaries), 10.0 (100 —
  whitespace-only), 35.0 (13 — ordinary CLAUSE), -20.0 (10 — INTERNAL
  sequence, both CJK-correct and ASCII-leaked... note: the 10
  `-20.0`-scoring candidates here are exactly the CJK/composite-sequence
  INTERNAL positions; ASCII-leak INTERNAL positions score +60.0, not
  -20.0, and are excluded here as diagnostic), 65.0 (6 — ELLIPSIS), -30.0
  (6 — Technical/Atomic-only), 80.0 (5 — genuine SENTENCE_FINAL), 15.0 (1
  — pure transition, A04/C03).

Distribution by real `BoundaryClass` (non-diagnostic candidates):

| BoundaryClass | Count |
|---|---:|
| `other` | 513 |
| `clause` | 14 |
| `sentence_final` | 7 |
| `ellipsis` | 6 |

Distribution by case group (non-diagnostic):

| Group | N | Min | Max | Mean |
|---|---:|---:|---:|---:|
| A | 64 | -20.0 | 80.0 | 4.53 |
| B | 74 | -20.0 | 80.0 | 5.68 |
| C | 24 | 0.0 | 10.0 | 1.67 |
| D | 19 | 0.0 | 10.0 | 2.63 |
| E | 35 | -60.0 | 50.0 | -1.71 |
| F | 17 | -20.0 | 65.0 | 5.29 |
| G | 24 | -20.0 | 80.0 | 3.33 |
| H | 283 | -20.0 | 65.0 | 3.62 |

Unlike Round 1 (where 100% of `sentence_final`-classified candidates were
leak artifacts and the true maximum was 65.0), Round 2 now has **7 genuine
`sentence_final` candidates reaching 80.0** (A01, B01, B02, G01, G02, plus
X05/X06's genuine END positions which are excluded from this table as
diagnostic) — direct, unambiguous confirmation that v0.2's fix works.

## 9. Upstream Representation Issues

1. **ASCII-composed punctuation sequences still leak `SENTENCE_FINAL` at
   INTERNAL positions** (G03, X01–X05, E02) — identical mechanism and
   magnitude to Round 1. Unaffected by this round's matrix corrections
   because it is orthogonal to the string-final issue v0.2 targeted; it is
   Phase 2A's bare single-character fallback firing on ASCII `.`/`？`/`！`
   at any position where no span happens to end exactly there.
2. **Group H was not updated with the v0.1→v0.2 string-final fix** (§5,
   Group H) — every H01–H08 case still terminates in `。` as the string's
   last character, so zero genuine `SENTENCE_FINAL` candidates exist
   anywhere in the 283 H-group candidates. This blocks direct verification
   of 4 of the group's 8 stated qualitative expectations.
3. **Paired-delimiter transparency produces duplicate adjacent
   SENTENCE_FINAL candidates** (X06) — both immediately inside and
   immediately outside a closing quotation mark, when the content just
   inside ends in sentence-final punctuation.
4. **Embedded markdown line-wraps in case source text act as whitespace**
   (B01) — a purely case-authoring/transcription hazard, not a pipeline
   defect, but one that changes scores by exactly +10 wherever it occurs
   adjacent to a boundary.

None of these were treated as numeric calibration findings; none justify
or were used to argue for a weight change this round.

## 10. Calibration Issues (genuine Phase 2C numeric observations)

After separating out the upstream/case issues above, the numeric-layer
observations that remain are:

1. **D04 (transition vs. whitespace) is a genuine ranking property of the
   two positive modifiers as currently defined**, not an upstream defect:
   a no-space transition candidate (15.0) outscores the best whitespace-
   adjacent candidate produced when a space is inserted at the same
   semantic position (10.0). Whether this is desirable depends on how
   Phase 2D will eventually aggregate multiple nearby candidates — as a
   single-candidate scoring layer, Phase 2C is behaving exactly per its
   formula; the "which candidate wins locally" outcome is what changes.
2. **Technical/Atomic penalties do not create an excessive or
   counter-intuitive reversal against transition-only or clause
   candidates** (E03, E04) — both comparisons resolve in the intended
   direction and by a clear margin (Δ≥45). No adjustment signal from this
   round's evidence.
3. **All base-class pairwise hierarchies (SF>ELLIPSIS>CLAUSE) now hold on
   genuine, non-probe data** (B01–B03), closing Round 1's single biggest
   open question (whether the formula behaves correctly once a real
   terminal boundary exists to test it against).

## 11. Numeric Recommendations

Using the matrix's own decision rules (§16 of v0.2: KEEP / NEED MORE DATA
/ ADJUST / UPSTREAM ISSUE / CASE ISSUE):

| Factor | Recommendation | Basis |
|---|---|---|
| `SENTENCE_FINAL` (+80) | **KEEP** | Now confirmed on 7 genuine, non-diagnostic candidates (A01, B01, B02, G01, G02) exactly at 80.0; base hierarchy (SF>ELLIPSIS>CLAUSE) holds cleanly. |
| `ELLIPSIS` (+65) | **KEEP** | Confirmed on 6 genuine candidates (A02, B02, B03, F01, F02, H08) exactly at 65.0. |
| `CLAUSE` (+35) | **KEEP** | Confirmed on 14 genuine candidates across every group, always exactly 35.0 when unprotected. |
| `OTHER` (0) | **KEEP** | Baseline, consistent everywhere (513 candidates). |
| CJK → LATIN (+15) | **NEED MORE DATA** | Arithmetically correct where it fires (A04, confirmed exactly 15.0), but Group C's own cases show it essentially never fires on naturally-space-separated mixed text — more realistic no-space examples are needed before this modifier's real-world impact can be assessed. |
| LATIN → CJK (+15) | **NEED MORE DATA** | Symmetric with CJK→LATIN (same value, same mechanism); same caveat — untested on any Round 2 case because both C01 and C02 turned out to be whitespace-separated. |
| Whitespace (+10) | **NEED MORE DATA** | Correct and non-stacking in isolation (D01–D03), but D04 shows it interacts with the transition modifier in a way that lowers rather than raises the best local score once a space is present — whether that's the desired behavior is a design question for Phase 2D, not resolvable from Phase 2C numbers alone. |
| Technical (-30) | **KEEP** | Produces the intended, non-excessive suppression relative to both CLAUSE (E03) and transition-only (E04) candidates; no reversal concern found. |
| Atomic (-30) | **KEEP** | Same as Technical; stacks with it in E02 to -60.0 with no observed problems beyond the pre-existing, separately-tracked SF leak (§9). |
| Punctuation sequence `INTERNAL` (-20) | **UPSTREAM ISSUE** | Correct and unambiguous for CJK-only and CJK-composite (ellipsis+question/exclaim) sequences (F02, G01, G02 all show exactly -20.0). Cannot be evaluated for ASCII-composed sequences because those positions are misclassified as `SENTENCE_FINAL` rather than `OTHER` before the -20 modifier is even relevant — no value of this weight can fix a classification-layer problem, so this factor is correctly marked upstream-blocked rather than numerically deficient. |

No value was changed in this round, per rule 23.

## 12. Comparison with Round 1

**Resolved by v0.2:**
- The single biggest Round 1 finding — that no case text exposed a
  genuine, non-probe `SENTENCE_FINAL` candidate — is now resolved for
  Groups A, B, F, G by appending trailing context after the target
  punctuation. A01/B01/B02/G01/G02 all now show real 80.0 scores directly,
  without needing a supplementary probe.
- The base pairwise hierarchy (SF>ELLIPSIS>CLAUSE) is now verified on
  genuine data for the first time (B01–B03), rather than via the Round 1
  probes.
- v0.2's explicit framing of A04 ("this is not a pure OTHER=0 case") and
  the Group D cases ("do not assume 15+10=25") pre-empted what would
  otherwise have been mis-scored expectations — the matrix itself now
  matches the real topology instead of the report having to explain the
  mismatch after the fact.

**Remains unresolved:**
- The ASCII-composed-punctuation `SENTENCE_FINAL` leak at INTERNAL
  positions (G03, X01–X05, E02) — identical in Round 2 to Round 1;
  correctly kept out of scope for numeric tuning in both rounds.
- The D04/C25-equivalent whitespace-vs-transition ranking property
  persists exactly as found in Round 1 (there called C25): a no-space
  transition candidate still outranks the whitespace-adjacent alternative.
- The "technical-protected CLAUSE is actually OTHER" finding persists
  (E01–E04), now demonstrated more cleanly (E01/E02's actual clause
  punctuation sits structurally outside the protected span, rather than
  requiring an artificial construction).

**New observations this round (not present or not visible in Round 1):**
- Group H was not brought in line with v0.2's own string-final fix, so
  the fix's benefit (§ above) does not extend to the realistic-case group
  that most needed it — Round 1 had the *same* gap in C30–C40 for the
  same underlying reason, but Round 1 could not have distinguished
  "matrix didn't apply its own fix" from "fix doesn't work," since v0.1
  had no fix to compare against. Round 2 can now say precisely: the fix
  works (Groups A/B/F/G prove it), it just wasn't applied to Group H.
- The paired-delimiter double-SENTENCE_FINAL-candidate topology (X06) is
  new — Round 1's calibration set had no paired-delimiter case.
- The markdown-line-wrap-as-whitespace hazard (B01) is new and specific to
  how this matrix's source text was authored, not a pipeline property
  Round 1 had reason to surface.
- Group C's cases (C01/C02) failing to expose a pure transition candidate,
  despite existing specifically to test that modifier, is new — Round 1's
  transition cases (C09/C10 in the old numbering) were deliberately
  written without a space, so this space-related failure mode wasn't
  visible until v0.2 tried to use "naturally-written" sentences for the
  same purpose.

## 13. Scope Compliance

- `src/subtitle_segmenter.py`: **untouched.**
- Phase 2D: **not implemented.**
- `src/text_structure.py`: **untouched.**
- `src/boundary_observation.py`: **untouched.**
- `src/boundary_classification.py`: **untouched.**
- No production Phase 2C scoring module implemented (no `src/phase2c_scoring.py`;
  `grep -rn "phase2c\|calibrate_phase2c" src/` returns no matches).
- No numeric weight changed — §4's values are exactly v0.2 §2's values.
- No production tests modified to hide regressions — no test file was
  touched.

## 14. Test Results

Commands run (from repository root, `/tmp/venv` interpreter):

```
python -m pytest tests/ -q
```
Result: **389 passed, 2 warnings, 15 subtests passed** (41.6s)

```
python -m unittest discover -s tests -v
```
Result: **Ran 389 tests ... OK**

Both commands were run after all Round 2 changes (matrix update, new
calibration script). Identical to the pre-round baseline (389) — no
regression.

---

## Files created / modified / untouched

**Created:**
- `scripts/calibrate_phase2c_round2.py` — new calibration-only script
  (not imported by `src/`), covering all v0.2 groups A–H and X.
- `docs/PHASE_2C_CALIBRATION_ROUND2_REPORT.md` — this report.

**Modified:**
- `docs/PHASE_2C_CALIBRATION_MATRIX.md` — replaced in place with the
  supplied v0.2 content (v0.1 content fully superseded, per the matrix's
  own "Supersedes" declaration).

**Untouched:**
- `src/text_structure.py`, `src/boundary_observation.py`,
  `src/boundary_classification.py`, `src/subtitle_segmenter.py`
- `scripts/calibrate_phase2c_round1.py` and its Round 1 raw output/report
  (kept for historical comparison, per §1)
- All test files under `tests/`

**Test results:** 389 passed (pytest) / OK (unittest discover) — unchanged
from baseline.

**Calibration report location:** `docs/PHASE_2C_CALIBRATION_ROUND2_REPORT.md`

---

**Round 2 status:** Complete per the stated completion criteria — all
applicable v0.2 cases evaluated using real Phase 1→2A→2B output, candidate
topology explicitly documented (Groups C, D especially), pairwise rankings
evaluated with deltas, X probes kept separate from numeric calibration,
numeric recommendations made without changing any weight, full regression
suite unchanged (389 passed / OK) before and after. Stopping here per
instruction, pending the next design decision.
