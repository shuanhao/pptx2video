# Phase 2C Numeric Calibration — Round 1 Report

## 1. Scope

This report covers Round 1 of Phase 2C numeric calibration only. It evaluates the
provisional, unfrozen scoring formula in `docs/PHASE_2C_CALIBRATION_MATRIX.md`
section 13 against the real, unmodified Phase 1 → Phase 2A → Phase 2B pipeline,
using the case set in that same document (C01–C40, X01–X07).

This round did **not**:
- modify `src/text_structure.py`, `src/boundary_observation.py`,
  `src/boundary_classification.py`, or `src/subtitle_segmenter.py`
- implement Phase 2D, `should_cut`, segmentation, or DP
- implement a production Phase 2C scoring module (`src/phase2c_scoring.py` was
  not created)
- change any of the provisional numeric weights
- add or modify any production test

All work in this round is confined to one calibration-only script,
`scripts/calibrate_phase2c_round1.py`, and this report.

## 2. Environment

- Repository: `pptx2video` (working copy under `/tmp/work/pptx2video/pptx2video-main`)
- Python: 3.11 (`/tmp/venv`)
- Test runner: `pytest` 
- Pipeline modules used, unmodified: `src/text_structure.py`,
  `src/boundary_observation.py`, `src/boundary_classification.py`
- Calibration matrix: `docs/PHASE_2C_CALIBRATION_MATRIX.md` (copied verbatim from
  the user-supplied `Phase_2C_Calibration_Matrix_v0.1.md`)

## 3. Pipeline Used

```
Phase 1  analyze_text_structure(text)
   -> Phase 2A  observe_boundaries(analysis)
       -> Phase 2B  classify_boundary(candidate)   [real BoundaryClass]
           -> Calibration-only scoring (this round)
```

Every `BoundaryClass`, `CharacterClass`, `PunctuationSequenceState`, and
`StructuralBoundaryContext` value used below was read directly off real
`BoundaryCandidate` objects produced by the real, unmodified pipeline. Nothing
was independently re-detected or inferred from raw text inside the calibration
layer.

The calibration script prints, for every candidate of every case text, the
position, left/right characters, `CharacterClass` on each side,
`PunctuationSequenceState`, `contains_sentence_final_punctuation`, the
`StructuralBoundaryContext.containing_spans`, the real `BoundaryClass`, the
calibration score, and the modifier breakdown. The full raw dump (`scripts/calibrate_phase2c_round1.py`
output) is the evidentiary basis for every claim in this report.

## 4. Numeric Baseline

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

Used exactly as specified; not tuned during this round.

## 5. Case Results (C01–C40)

**A finding that affects most cases below and is stated once here:** several
matrix cases place their key punctuation character as the absolute last
character of the case text (C01, C02, all of C30–C40, and X01's ellipsis
side). `observe_boundaries()` only yields a candidate strictly *between* two
characters that both exist in the string — there is no candidate for "the
boundary after the very last character." Consequently the exact boundary the
matrix intends to score (the SENTENCE_FINAL/ELLIPSIS boundary immediately
after the terminal punctuation) is **never produced** for a case text that
ends in that punctuation. This is confirmed quantitatively in section 8: of
the 550 real (non-probe) candidates across all 40+2×7 case texts, 0 candidates
score the matrix's literal "SENTENCE_FINAL = 80" or "ELLIPSIS = 65" as a
genuine terminal boundary; the only `ellipsis`-classified candidate in the
entire non-probe set is from C37, whose ellipsis is followed by more text.

To separate "the formula is wrong" from "the case text has no trailing
context," three supplementary probes were added to the calibration script
(same texts with one trailing character appended — `C01_ctx_probe`,
`C02_ctx_probe`, `X01b_ctx_probe`, plus `C20_ascii_end_probe` for an ASCII
ellipsis run). These are not new cases and do not reinterpret C01/C02/X01;
they exist purely to show what the real pipeline scores at the boundary the
matrix describes, once that boundary can structurally exist. Results: with
trailing context, `。` scores exactly 80.0 (`SENTENCE_FINAL`, no modifiers)
and `……` scores exactly 65.0 (`ELLIPSIS`, no modifiers) — i.e. the base
scoring formula itself is correct; the gap is a pipeline representation
property of string-final punctuation, not a scoring defect.

| ID | Case | Real result | Category |
|---|---|---|---|
| C01 | `。` at string end | No SF candidate observable (see above). Probe confirms 80.0 exactly once trailing context exists. | C (root); resolved via probe |
| C02 | `……` at string end | No ELLIPSIS candidate observable; interior position (between the two `…`) = OTHER, -20.0 (correct INTERNAL behavior). Probe confirms 65.0 exactly. | C (root); resolved via probe |
| C03 | `，` clause | pos3 `，｜我`: CLAUSE, 35.0 | **A — PASS** |
| C04 | `中文｜中文` | all boundaries OTHER, 0.0 | **A — PASS** |
| C05 | SF vs clause | 80.0 (probe) vs 35.0 (C03), Δ=45, SF>C | **A — PASS** (via probe) |
| C06 | Ellipsis vs clause | 65.0 (probe) vs 35.0 (C03), Δ=30, E>C | **A — PASS** (via probe) |
| C07 | Clause vs other | 35.0 (C03) vs 0.0 (C04), Δ=35, C>O | **A — PASS** |
| C08 | SF vs Ellipsis | 80.0 (probe) vs 65.0 (probe), Δ=15, SF>E | **A — PASS** (via probe) |
| C09 | `中文｜English` | pos2: OTHER, 15.0 (CJK→LATIN) | **A — PASS** |
| C10 | `English｜中文` | pos7: OTHER, 15.0 (LATIN→CJK) | **A — PASS** |
| C11 | `中文 ｜ English` | TWO candidates, 10.0 + 10.0 — **no candidate reaches 25** | **B — CALIBRATION OBSERVATION** |
| C12 | `English ｜ 中文` | Same as C11 (symmetric): 10.0 + 10.0 | **B — CALIBRATION OBSERVATION** |
| C13 | enriched OTHER (25) vs CLAUSE (35) | best real "enriched OTHER" = 15.0 (C09, no-space transition); CLAUSE = 35.0 (C03). Ranking C>enriched-OTHER still holds (35>15) but "25" itself never occurs. | **B — CALIBRATION OBSERVATION** |
| C14 | CLAUSE+transition+whitespace (60) | pos3 of `首先， English`: CLAUSE, 45.0 (35+10 whitespace only — **no transition bonus**, because the clause character's `CharacterClass` is `PUNCTUATION`, never `CJK`/`LATIN`, so the transition rule's precondition can never fire on a CLAUSE candidate) | **C — PIPELINE REPRESENTATION ISSUE** |
| C15 | enriched CLAUSE (60) vs ELLIPSIS (65) | real enriched-CLAUSE max = 45.0 (C14) vs ELLIPSIS 65.0 (probe). E>enriched-C still holds (65>45) but built on the unreachable "60" premise. | **B — CALIBRATION OBSERVATION** (built on C14's issue) |
| C16 | enriched CLAUSE (60) vs SF (80) | 45.0 vs 80.0 (probe). SF>enriched-C holds (80>45) but built on the unreachable "60" premise. | **B — CALIBRATION OBSERVATION** (built on C14's issue) |
| C17 | `1,｜000` technical, expected 5* | comma boundary: real class = **OTHER**, not CLAUSE (Phase 2B's own `_is_clause()` already falls through to OTHER when technical/atomic-protected). Score = -30.0 (0-30), not 5. Matrix's own footnote anticipates this. | **B — CALIBRATION OBSERVATION** (matrix-flagged) |
| C18 | `1, ｜000` technical, expected 15* | The space breaks Phase 1's thousands-separator match into **two disjoint atomic spans** (`1` and `000`); the comma is not inside either. Real: comma boundary = CLAUSE, 45.0 (35+10, **no** technical penalty at all — a third, different structural surprise from C17). | **C — PIPELINE REPRESENTATION ISSUE** |
| C19 | atomic boundary, expected -30* | `3.14`: pos1 (`3｜.`) = OTHER, -30.0 (matches); pos2 (`.｜1`) = **SENTENCE_FINAL, 50.0** (bare-fallback leak on the decimal point — see §9); pos3 (`1｜4`) = OTHER, -30.0 (matches). 2/3 positions match; the decimal point itself leaks SF. | **B — CALIBRATION OBSERVATION** (major finding, §9) |
| C20 | INTERNAL, expected -20 | CJK ellipsis interior (C02/X01b/X07b): OTHER, -20.0 — **matches**. ASCII `.` runs (`嗯......`, `......`) and interrobang runs (`真的？！`): all interior positions = **SENTENCE_FINAL, 60.0** (80-20), not -20.0. | **A for CJK; B for ASCII/interrobang runs** (major finding, §9) |
| C21 | INTERNAL vs END | CJK: -20.0 vs 65.0 (probe) — END>INTERNAL holds cleanly. ASCII: INTERNAL=60.0 (leak) vs END=65.0 (`C20_ascii_end_probe`) — END still nominally > INTERNAL (65>60) but by a much smaller, essentially meaningless margin, because INTERNAL itself is wrongly positive. | **A for CJK; B for ASCII** |
| C22 | technical CLAUSE (5) vs enriched OTHER (25) | Real "technical CLAUSE" doesn't exist (see C17: it's OTHER, -30.0). Best real enriched-OTHER = 15.0 (C09). 15 > -30 — same qualitative direction as intended, but neither side matches its assumed class or value. | **B — CALIBRATION OBSERVATION** |
| C23 | technical CLAUSE (5) vs SF (80) | -30.0 (C17) vs 80.0 (probe). SF remains dominant (80 > -30, Δ=110 vs matrix's assumed Δ=75) | **A — PASS** (ranking holds; premise differs, see C17) |
| C24 | `中文\|中文` (0) vs `中文\|English` (15) | 0.0 (C04) vs 15.0 (C09), Δ=15, B>A | **A — PASS** |
| C25 | `中文\|English` (15) vs `中文 \| English` (25) | 15.0 (C09) vs best 10.0 (C11) — **B < A, relation inverted** | **B — CALIBRATION OBSERVATION (ranking reversal)**, see §9 |
| C26 | ordinary CLAUSE vs technical-protected CLAUSE | 35.0 (`第一，第二`) vs -30.0 (C17, actually OTHER). A>B holds (Δ=65) but B is not really "CLAUSE". | **A — PASS** (ranking); note on B's real class |
| C27 | plain CLAUSE vs CLAUSE+transition | "CLAUSE+transition" is never observed anywhere in any dump (mutual exclusivity — see C14). Confirmed again at C32 pos13 (`、｜G`): class=CLAUSE, 35.0, **no** transition bonus despite `G` being LATIN. | **C — PIPELINE REPRESENTATION ISSUE** (not evaluable) |
| C28 | CLAUSE+transition vs +whitespace | Both variants require the unreachable "CLAUSE+transition" base. | **C — PIPELINE REPRESENTATION ISSUE** (not evaluable) |
| C29 | INTERNAL vs END | CJK: -20.0 vs 65.0(probe) — clean PASS. ASCII: 60.0 vs 65.0(`C20_ascii_end_probe`) — technically END>INTERNAL but the margin is trivial and INTERNAL is wrongly positive. | **A for CJK; B for ASCII** |
| C30–C36, C38–C40 | realistic sentences | See §10. All of these terminate in `。` as the last character, so (per the note above) their nominal "final" boundary is never produced as a candidate; every comma/`、` boundary present classifies CLAUSE=35.0 exactly as expected, all plain CJK-CJK/Latin-Latin boundaries = OTHER 0.0, transition/whitespace boundaries score 0/10/15 as expected. | **A for interior structure; C for the "final" boundary itself** |
| C37 | `……我們……。` | pos7: ELLIPSIS, 65.0 (only non-probe ELLIPSIS in the whole dataset, because this is the one case whose ellipsis is *not* string-final) — matches exactly. Trailing `。` again produces no SF candidate (string-final). | **A for the ellipsis; C for the trailing SF** |

## 6. Pairwise Ranking Summary

| Case | A | B | Score A | Score B | Δ (A-B) | Expected | Observed | Result |
|---|---|---|---:|---:|---:|---|---|---|
| C05 | SF | Clause | 80.0* | 35.0 | +45.0 | A>B | A>B | PASS* |
| C06 | Ellipsis | Clause | 65.0* | 35.0 | +30.0 | A>B | A>B | PASS* |
| C07 | Clause | Other | 35.0 | 0.0 | +35.0 | A>B | A>B | PASS |
| C08 | SF | Ellipsis | 80.0* | 65.0* | +15.0 | A>B | A>B | PASS* |
| C13 | Clause | enriched OTHER | 35.0 | 15.0† | +20.0 | A>B | A>B | PASS† |
| C15 | Ellipsis | enriched CLAUSE | 65.0* | 45.0† | +20.0 | B>A in matrix labels (E>enriched-C) i.e. A(here=Ellipsis)>B | A>B | PASS† (magnitude differs) |
| C16 | SF | enriched CLAUSE | 80.0* | 45.0† | +35.0 | A>B | A>B | PASS† (magnitude differs) |
| C21 (CJK) | END | INTERNAL | 65.0* | -20.0 | +85.0 | A>B | A>B | PASS* |
| C21 (ASCII) | END | INTERNAL | 65.0‡ | 60.0† | +5.0 | A>B | A>B (barely) | REVIEW† |
| C22 | enriched OTHER | technical CLAUSE | 15.0† | -30.0† | +45.0 | A>B | A>B | PASS† (both premises differ) |
| C23 | SF | technical CLAUSE | 80.0* | -30.0† | +110.0 | A>B | A>B | PASS† (premise differs) |
| C24 | `中文｜English` | `中文｜中文` | 15.0 | 0.0 | +15.0 | A>B | A>B | PASS |
| C25 | `中文 \| English` | `中文｜English` | 10.0† | 15.0 | **-5.0** | A>B | **A<B** | **REVIEW** (real reversal) |
| C26 | ordinary CLAUSE | technical CLAUSE | 35.0 | -30.0† | +65.0 | A>B | A>B | PASS (premise differs) |
| C27 | plain CLAUSE | CLAUSE+transition | 35.0 | not observable | n/a | B>A | n/a | **N/E** (not evaluable) |
| C28 | CLAUSE+transition | +whitespace | not observable | not observable | n/a | B>A | n/a | **N/E** (not evaluable) |
| C29 (CJK) | END | INTERNAL | 65.0* | -20.0 | +85.0 | A>B | A>B | PASS* |
| C29 (ASCII) | END | INTERNAL | 65.0‡ | 60.0† | +5.0 | A>B | A>B (barely) | REVIEW† |

`*` value obtained via a trailing-context probe (see §5), because the literal
matrix text is string-final and cannot produce the candidate directly.
`†` value differs from the matrix's assumed value/class because of a
representation issue documented in §5/§9 (real class or real reachable score
differs from the matrix's illustrative arithmetic).
`‡` value from `C20_ascii_end_probe`.

**Strong hierarchy (matrix §9):** SF > ELLIPSIS, SF > ordinary CLAUSE, SF >
enriched CLAUSE — all hold on real (probe-supplemented) data.
**Moderate hierarchy:** ELLIPSIS > CLAUSE variants — holds. CLAUSE > ordinary
OTHER — holds (C07). CLAUSE > OTHER+transition — holds (C13, by 20 not 10).
CLAUSE > OTHER+transition+whitespace — cannot be tested as stated because
"OTHER+transition+whitespace" (25) is itself unreachable (C11/C12); best real
substitute (10.0) is still < CLAUSE (35.0), so the *intent* of the rule holds.
**Contextual reversal (OTHER+strong positive context > technically protected
CLAUSE):** holds numerically (15 > -30) but neither side is the class the
matrix assumed.
**Protection:** ordinary CLAUSE > technical CLAUSE — holds, but "technical
CLAUSE" doesn't exist as a real class (it's OTHER). Ordinary OTHER > atomic
OTHER — holds (0 > -30). Terminal > internal sequence — holds for CJK, holds
only nominally (and by a thin, near-meaningless margin) for ASCII/interrobang
runs because internal is wrongly elevated by the SF leak.

## 7. Counterexample Analysis (X01–X07)

### X01 — `嗯……` (ellipsis) vs `CPU、 ｜ GPU` (clause+whitespace)
1. **Interpretation:** `嗯……` is string-final, so its ELLIPSIS candidate is not
   directly observable; `X01b_ctx_probe` (`嗯……好`) supplies it.
2. **Boundary A evidence:** ellipsis END, `PunctuationSequenceState=END`,
   `contains_sentence_final_punctuation=False`.
3. **Boundary A score:** 65.0 (probe).
4. **Boundary B evidence:** `、｜(space)` in `CPU、 GPU`, left_char=`、`,
   `left_character_class=PUNCTUATION` (not CJK), `Whitespace` modifier only.
5. **Boundary B score:** 45.0 (35 CLAUSE + 10 whitespace; **not 60** — the
   matrix's "60" for this side assumes a transition bonus that the real
   pipeline never grants a CLAUSE candidate, per the C14/C27 finding).
6. **Actual ranking:** A(65.0) > B(45.0).
7. **Intended ranking:** ELLIPSIS(65) > "CLAUSE+transition+whitespace"(60) — same direction.
8. **Score difference:** matrix Δ=5; real Δ=20.
9. **Reasonableness:** the *direction* the question asks about ("is ELLIPSIS
   sufficiently preferred?") is answered yes, and by a wider margin than the
   matrix assumed — but only because B's assumed value (60) is itself
   unreachable; B's real ceiling is 45.
10. **Numeric adjustment:** not evaluated this round (rule 15); flagged that
    B's premise, not the ELLIPSIS/CLAUSE weights, is what drives the gap.

### X02 — ordinary CLAUSE (35) vs `中文 ｜ English` (25)
1. **Interpretation:** directly representable; both sides are real cases (C03/C26-style clause, C11).
2. **Boundary A evidence:** `，｜我` in `首先，我們介紹 CPU`, CLAUSE.
3. **Boundary A score:** 35.0.
4. **Boundary B evidence:** best of the two `中文 ｜ English` candidates (whitespace-only, no transition co-occurrence — see C11/C25).
5. **Boundary B score:** 10.0 (not 25).
6. **Actual ranking:** A(35.0) > B(10.0).
7. **Intended ranking:** CLAUSE(35) > enriched-OTHER(25) — same direction, larger margin.
8. **Score difference:** matrix Δ=10; real Δ=25.
9. **Reasonableness:** direction preserved; the question ("is CLAUSE sufficiently preferred?") is answered even more strongly yes than the matrix assumed, again because B's assumed 25 never actually occurs (C11 finding).
10. **Numeric adjustment:** none indicated; the C11 representation issue is the actual driver.

### X03 — technical CLAUSE (5) vs transition+whitespace (25)
1. **Interpretation:** `1,000` — comma is OTHER (Atomic), not CLAUSE (C17 finding); "transition+whitespace" (25) is also unreachable (C11 finding). Both sides of this counterexample rest on unreachable/mis-assumed classes.
2. **Boundary A evidence:** `1,｜000` comma boundary, `containing_spans=[atomic/numeric]`, real class=OTHER.
3. **Boundary A score:** -30.0 (not 5).
4. **Boundary B evidence:** best real transition+whitespace candidate (C11-style), whitespace-only.
5. **Boundary B score:** 10.0 (not 25).
6. **Actual ranking:** B(10.0) > A(-30.0).
7. **Intended ranking:** A(5) < B(25), i.e. B>A — same direction.
8. **Score difference:** matrix Δ=20; real Δ=40.
9. **Reasonableness:** direction holds; question "is -30 too strong?" cannot be cleanly answered from this pairing because A is not really a penalized CLAUSE at all — it is an ordinary atomic-penalized OTHER position, so this counterexample doesn't actually probe what it was designed to probe.
10. **Numeric adjustment:** not evaluable as specified; would need a case where a clause character is technical-protected *and* still classified CLAUSE, which the current Phase 2B rules make impossible by design (§9 "technical-protected-CLAUSE-is-actually-OTHER").

### X04 — SF with minor negative context vs enriched CLAUSE (case-dependent, no concrete text given)
No representative text was specified in the matrix. A minimal literal reading
("sentence-final immediately after a technical/atomic span," e.g. `v1.0。`)
was not separately probed this round because it overlaps substantially with
X05's evidence (technical-context SF at 50.0/20.0, sections below). Recorded
as:
- **Category: D — CASE SPECIFICATION ISSUE** (no concrete boundary text to
  evaluate against; the matrix itself labels it "case-dependent").
- Partial evidence from X05: SF immediately after technical/atomic content
  scores 20.0–50.0 (80 base minus one or two 30-point penalties), still well
  above ordinary CLAUSE (35) and comfortably above OTHER — i.e. even "minor
  negative context" versions of SF observed so far remain fairly strong, not
  reduced to reversal.

### X05 — long technical expression, multiple candidates
1. **Interpretation:** `見 v1.2.3-beta 版本說明 http://example.com/path 頁面。` exercises version, numeric, and URL technical/atomic spans together.
2. **Boundary evidence (representative):**
   - `v｜1`: OTHER, `technical/version`, -30.0
   - `1｜.`: OTHER, `technical/version`+`atomic/numeric`, -60.0
   - `.｜2`: **SENTENCE_FINAL**, same double containment, **+20.0** (80-30-30) — bare-fallback SF leak on a decimal point nested inside both a version span and a numeric span
   - `.｜3`: **SENTENCE_FINAL**, `technical/version` only, **+50.0** (80-30)
   - interior of the URL (`http://...`): all OTHER, -30.0 each (18 boundaries)
   - `.｜c` in `example.com`: **SENTENCE_FINAL**, `technical/url`, **+50.0** (80-30) — same leak inside a URL domain separator
3. **Actual ranking:** the SF-leak boundaries (20.0/50.0/50.0) score *higher* than every ordinary interior technical boundary (-30.0) and higher than ordinary CLAUSE (35.0 elsewhere in the corpus).
4. **Intended/expected behavior (matrix):** "Does protection hold consistently?"
5. **Assessment:** protection does **not** hold consistently for these three
   positions — a boundary strictly inside a version string or a URL domain
   scores as if it were a genuine, unpenalized-relative-to-CLAUSE sentence
   ending, which is the opposite of the intended effect of technical
   protection. All three are internal punctuation positions that happen to be
   "." immediately followed by a digit or letter with no span ending exactly
   there, so Phase 2A's bare single-character fallback fires.
6. **Numeric adjustment:** not evaluated this round; this is a classification/representation issue (Phase 2A's bare-fallback SF character set), not a Phase 2C weight issue — changing weights would not fix it, since the problem is the boundary being labeled `SENTENCE_FINAL` at all.

### X06 — notes with frequent mixed-language spaces
1. **Interpretation:** `中文 English 中文 English 中文` — five language transitions, each mediated by whitespace.
2. **Boundary evidence:** every transition point produces **two** OTHER,
   10.0 (whitespace-only) candidates, exactly as in C11/C12/C25 — never a
   single combined 25.0 candidate.
3. **Actual candidate count:** 8 non-zero-scoring boundaries (all 10.0), 0
   candidates at 15.0 or 25.0.
4. **Intended ranking:** "does transition+whitespace create too many
   candidates?"
5. **Assessment:** yes — each language switch produces two boundaries at a
   modest, identical score (10.0) rather than one clearly-preferred boundary,
   so this scoring layer alone does not distinguish "the space between two
   words" from "the space that is also a language switch." That distinction
   is present in C09/C10 (15.0, no space) but disappears once whitespace is
   introduced.
6. **Numeric adjustment:** not evaluated; flagged as a design question for
   Phase 2D (how multiple adjacent low-margin candidates around one semantic
   switch point should be resolved) rather than a Phase 2C weight change.

### X07 — unusual punctuation runs
1. **Interpretation:** two sub-cases: `真的？！` (interrobang run) and
   `……………`/`…………` (merged ellipsis run).
2. **Boundary A evidence (X07a, interrobang interior):** `？｜！`,
   `PunctuationSequenceState=INTERNAL`, `contains_sentence_final_punctuation=True`
   (bare fallback fires on `？`).
3. **Boundary A score:** 60.0 (**SENTENCE_FINAL**, 80-20), not the -20 a
   plain INTERNAL position would suggest.
4. **Boundary B evidence (X07b, merged ellipsis run `…………`):** all 3
   interior positions, `INTERNAL`, `contains_sentence_final_punctuation=False`
   (CJK `…` is not in the bare-fallback SF set).
5. **Boundary B score:** -20.0 each (OTHER), matches C20's assumption exactly.
6. **Actual ranking / behavior:** ASCII/interrobang-composed internal runs
   leak SENTENCE_FINAL (60.0); CJK-`…`-composed internal runs do not (-20.0).
7. **Intended/expected:** "does INTERNAL penalty suppress false boundaries
   without hurting END?" — for CJK runs, yes; for ASCII `.`/`？`/`！`
   composed runs, no — the internal penalty is not just insufficiently
   suppressive, it is overridden entirely by a positive SENTENCE_FINAL base.
8. **Score difference:** CJK vs ASCII internal, same structural role: -20.0
   vs +60.0, a swing of 80 points from a single upstream evidence field.
9. **Reasonableness:** this is the most severe individual finding in this
   round — an INTERNAL punctuation-sequence position (which every acceptance
   rule treats as something that should be suppressed) can score higher than
   an ordinary CLAUSE boundary (35.0) whenever the sequence is composed of
   ASCII `.`, `？`, or `！` characters.
10. **Numeric adjustment:** would not fix this — even Internal Seq = -80 or
    lower would only be masking a classification issue (the position is
    being labeled SENTENCE_FINAL when it should not be eligible for that
    label at all inside a sequence). This is a Phase 2A/2B design question,
    out of this round's scope to change.

## 8. Score Distribution

Computed over all 550 real (non-probe) boundary candidates dumped across
C01–C40 and X01–X07 (probe-only supplementary candidates excluded to keep
this distribution matched to the literal matrix case set):

- **Minimum:** -60.0 (X05, position doubly inside `technical/version` +
  `atomic/numeric`)
- **Maximum:** 65.0 (C37, the one non-string-final ellipsis end)
- **Mean:** ≈2.56
- **Median:** 0.0

Distribution by real `BoundaryClass`:

| BoundaryClass | Count | Note |
|---|---:|---|
| `other` | 517 | includes every plain/whitespace/transition/technical/atomic-penalized position |
| `clause` | 17 | all exactly 35.0 or 45.0 (with whitespace) — never technical-protected in this set (protected clause chars fall to `other`) |
| `sentence_final` | 15 | **all 15 are bare-fallback leaks** at internal/technical/atomic positions (§5, §9) — zero are genuine terminal endings, because every case text with a genuine terminal sentence-final character places it as the string's last character, which produces no candidate |
| `ellipsis` | 1 | C37 only — the sole case whose ellipsis is not string-final |

The maximum observed score (65.0, not 80.0) and the fact that 100% of
`sentence_final`-classified candidates are leak artifacts are themselves
calibration findings, not just descriptive statistics: they mean this
round's real dataset never exercises the base `SENTENCE_FINAL=80` value in
its intended (genuine terminal boundary) role at all — only the
trailing-context probes did.

## 9. Important Observations

### Pipeline behavior
1. **String-final punctuation produces no boundary candidate.**
   `observe_boundaries()` only yields candidates strictly between two
   existing characters, so a sentence-final or ellipsis character at the very
   end of an input string never gets scored as the terminal boundary the
   matrix describes. This affects C01, C02, all of C30–C40's "final"
   boundary, and X01's ellipsis side. Confirmed innocuous (not a scoring
   defect) via three trailing-context probes that reproduce the exact
   expected 80.0/65.0 once a following character exists.
2. **Bare-fallback SENTENCE_FINAL leak.** Any internal punctuation-sequence
   position, or any position strictly inside a technical/atomic span, where
   no Phase 1 span happens to *end* exactly there, falls through to Phase
   2A's bare single-character check. Because that bare set includes ASCII
   `.`, `？`, `！` (an already-approved Phase 2A design decision, not
   something this round can or should change), such positions register
   `contains_sentence_final_punctuation=True` and classify SENTENCE_FINAL —
   even though they are internal to an ellipsis run, a version string, a
   decimal number, or a URL. Observed at C19, C20/C21 (ASCII), X05 (3
   positions), X07a. CJK `…` does not trigger this (it is intentionally
   excluded from the in-sequence SF composition set), so CJK ellipsis runs
   behave exactly as the matrix expects.
3. **CLAUSE and language-transition are mutually exclusive at a single
   candidate.** A clause-triggering character's `CharacterClass` is always
   `PUNCTUATION`, never `CJK`/`LATIN`, so the transition modifier's
   precondition can never be true on a CLAUSE-classified candidate. "Enriched
   CLAUSE" (C14/C27/C28/X01's B side) cannot be represented as a single real
   candidate under the current Phase 2A/2B design.
4. **Whitespace splits a transition into two weaker candidates instead of
   compounding it.** When whitespace separates a CJK token from a Latin
   token, the transition bonus and the whitespace bonus land on two adjacent
   but distinct candidates (10.0 + 10.0), never combined onto one (25.0).
   Affects C11/C12/C13/C25/X02/X06.
5. **Technical span boundaries are sensitive to exact character adjacency.**
   `1,000` (no space) is one atomic span containing the comma (C17); `1,
   000` (space after the comma) is parsed as two separate atomic spans, and
   the comma is not protected at all (C18) — a materially different
   structural interpretation from a single extra space, not anticipated by
   the matrix's shared "35+10-30=15" framing for both.
6. **Technical-protected CLAUSE is actually OTHER, not a discounted CLAUSE.**
   Confirmed exactly as the matrix's own C17/C18/C19 footnote anticipated:
   Phase 2B's `_is_clause()` already returns `False` under technical/atomic
   protection, so the real class is OTHER (base 0), not CLAUSE (base 35).
   Every matrix case built on "CLAUSE base minus technical/atomic penalty"
   (C17, C18, C22, C23, C26, X03) actually starts from OTHER's base instead.

### Scoring behavior
7. The formula itself (base + modifiers, evaluated purely from real Phase
   2A/2B evidence) is arithmetically correct in every candidate inspected —
   every discrepancy above traces back to which `BoundaryClass`/features the
   real pipeline assigns, not to the arithmetic applied on top of them.
8. No case exercised two positive modifiers simultaneously except CJK/Latin
   transition and whitespace individually stacking on separate positions —
   the formula's "no modifier accidentally dominates" acceptance rule (rule
   7) was not stressed by any *reachable* multi-modifier combination this
   round, because CLAUSE+transition and transition+whitespace-on-one-
   candidate are both unreachable.

### Ranking behavior
9. **C25 is a genuine, reproducible ranking reversal**, not an artifact of
   an unreachable premise: `中文｜English` (no space, 15.0) actually
   outranks the best real candidate from `中文 ｜ English` (with space,
   10.0), inverting the matrix's expected "adding whitespace should
   increase the score" intuition. This happens because adding the space
   removes the transition bonus from the boundary entirely (it moves to a
   different, whitespace-only candidate) rather than adding to it.
10. **X07/C20's ASCII-vs-CJK asymmetry is the most severe finding**: an
    INTERNAL position inside an ASCII ellipsis or interrobang run can score
    60.0 — higher than ordinary CLAUSE (35.0) — while the structurally
    identical CJK case scores -20.0 exactly as intended. A single upstream
    evidence field (the bare fallback's ASCII character set) produces an
    80-point swing between two cases the matrix treats as equivalent.

## 10. Realistic Case Review (C30–C40)

Across all 11 cases:
- **High-scoring candidates** are, without exception, ordinary CLAUSE
  boundaries at 35.0 (C30, C31, C32×2, C34, C35, C36, C38, C40×2) or 45.0
  where whitespace happens to coincide with the clause boundary (X01-style;
  not observed in C30–C40 directly, all CLAUSE hits here are 35.0 exactly
  since none of these particular commas sit next to whitespace). No
  candidate in C30–C40 scored above 35.0 anywhere — the sentences never
  produced their nominal terminal SENTENCE_FINAL candidate (see §5/§9,
  finding 1), so the "final > comma" claim in each row's "expected behavior"
  column could not be directly demonstrated from these dumps alone; it is
  independently supported by the trailing-context probes in §5, which show
  a genuine SF boundary (80.0) does outscore every CLAUSE boundary observed
  here (35.0/45.0) once it can exist as a candidate.
- **Low-scoring candidates**: none were negative in C30–C40 specifically
  (no technical/atomic spans were matched inside these particular sentences,
  even where the matrix's notes call out "technical terms protected," e.g.
  C31's `ARM Cortex-A`, C33's `AI accelerator`, C36's `Python API`/`function`
  — none of these were recognized as `technical`/`atomic` spans by Phase 1
  in this text; only genuinely numeric/version/URL patterns are, per X05).
  This means C31/C33/C34/C36's "technical terms protected" expectation is
  **not actually exercised** by these sentences — Phase 1 does not treat
  bare identifiers like `ARM`, `Cortex-A`, `AI accelerator`, or `function`
  as technical/atomic spans, so there is nothing here for the -30 penalty to
  apply to. This is a case-specification observation, not a scoring defect:
  the intended "technical protection" behavior is real (demonstrated by
  X05's URL/version content) but these particular realistic sentences don't
  contain the kind of technical span Phase 1 actually recognizes.
- **Technical-context penalization**: not exercised in C30–C40 (see above);
  confirmed working correctly (if leak-prone, see §9 finding 2) in X05.
- **CJK/Latin transition bonus**: fires as the flat +15 exactly where
  expected (e.g. C30 pos2 `紹｜ ` region is whitespace-mediated so scores
  10.0, not 15.0 — nearly every CJK/Latin boundary in C30–C40 is
  whitespace-adjacent, so the "pure" +15 transition bonus in isolation is
  rare in this realistic set; most transitions here score 10.0 via
  whitespace instead, consistent with finding 4 in §9).
- **Whitespace incremental effect**: consistently and only +10, applied
  uniformly, no compounding observed — consistent with the formula.
- **Sentence-final dominance**: cannot be directly confirmed from C30–C40's
  own candidates (no SF candidate is produced, see above); confirmed via
  probe instead.
- **Overall plausibility**: within the boundaries that *are* produced, the
  relative ordering (CLAUSE > transition-only > whitespace-only > plain
  CJK-CJK/Latin-Latin) is sensible and matches the moderate-hierarchy
  invariants. The main open question these realistic cases raise is
  practical rather than numeric: because genuine terminal SF boundaries
  never appear as candidates for a single self-contained sentence, any
  Phase 2D consumer that processes one slide's text in isolation would need
  a separate mechanism (e.g. treating "end of input" itself as an implicit
  strong cut point) — the Phase 2C score alone cannot supply that signal for
  a string-final period, only for a period followed by more text.

## 11. Scope Compliance

- `src/subtitle_segmenter.py`: **untouched** (verified: file mtime and
  content unchanged from before this round).
- Phase 2D: **not implemented.**
- `src/text_structure.py`: **untouched** this round.
- `src/boundary_observation.py`: **untouched** this round.
- `src/boundary_classification.py`: **untouched** this round.
- No production scoring module implemented — `src/phase2c_scoring.py` does
  not exist; the only new/changed file is the calibration-only
  `scripts/calibrate_phase2c_round1.py` (not imported by anything under
  `src/`, verified via `grep -rn "phase2c\|calibrate_phase2c" src/` → no
  matches) plus this report and the calibration matrix copy under `docs/`.
- No numeric weight changed — the values in §4 are exactly the matrix's
  §13 values.
- No tests modified to hide regressions — no test file was touched.

## 12. Test Results

Command: `python -m pytest tests/ -q` (run from repository root, using the
project's `/tmp/venv` interpreter)

Result: **389 passed, 2 warnings, 15 subtests passed** — identical to the
pre-round baseline. No regression.

(Run both before and after the calibration script changes in this round;
identical result both times, as expected since no production file was
touched.)

---

## Summary of case categories

- **A — PASS:** C03, C04, C05*, C06*, C07, C08*, C09, C10, C21(CJK), C23,
  C24, C26, C29(CJK), plus the interior structure of C30–C36/C38–C40.
- **B — CALIBRATION OBSERVATION:** C11, C12, C13, C15, C16, C17, C19, C20
  (ASCII/interrobang), C21(ASCII), C22, C25 (ranking reversal), C29(ASCII),
  X01, X02, X03, X05, X06, X07.
- **C — PIPELINE REPRESENTATION ISSUE:** C01 (root case), C02 (root case),
  C14, C18, C27, C28, the "final" boundary of C30–C40, X01's ellipsis side
  (root case).
- **D — CASE SPECIFICATION ISSUE:** X04 (no concrete text provided in the
  matrix).

`*` resolved via a supplementary trailing-context probe rather than the
literal case text.

## Numeric sensitivity observations

Ranked by how much a single upstream evidence bit changes the outcome,
holding the formula fixed:
1. **`contains_sentence_final_punctuation` (bare-fallback ASCII leak):**
   swings a candidate from -20 (or -30) to +50/+60 — an 80–110 point range
   from one boolean, entirely outside the numeric model's control.
2. **Whether whitespace intervenes between a CJK/Latin transition:**
   changes 15 → 10 and splits one candidate into two (C25's reversal).
3. **Whether a clause character falls inside a technical/atomic span:**
   changes CLAUSE(35) → OTHER(-30), a 65-point swing, not the "35→5" the
   matrix's illustrative arithmetic assumed.
4. **Technical vs Atomic stacking (X05):** two -30 penalties can co-occur
   in the same containing_spans set, reaching -60 — the model has no cap on
   how many negative modifiers stack.
5. Ordinary modifier stacking (Whitespace alone, CJK/Latin alone) behaves
   exactly as specified — no surprises.

## Numeric Calibration Recommendations (Round 1 — no changes made)

| Factor | Recommendation | Basis |
|---|---|---|
| `SENTENCE_FINAL` base (+80) | **NEED MORE DATA** | Never exercised in its genuine terminal-boundary role by any of the 40+7 literal case texts; only probes exercised it. Round 2 should include case texts with trailing context so the base value can be judged in-situ. |
| `ELLIPSIS` base (+65) | **KEEP** | Confirmed exactly correct at C37 (genuine, non-string-final) and at all three probes. |
| `CLAUSE` base (+35) | **KEEP** | Confirmed exactly correct at every ordinary (non-technical) clause boundary observed (17 candidates, C03/C26/C30–C40/X01). |
| `OTHER` base (0) | **KEEP** | Baseline, consistent everywhere. |
| CJK → LATIN (+15) | **KEEP** | Matches C09 exactly; symmetric with LATIN→CJK (C10) as required by acceptance rule 3. |
| LATIN → CJK (+15) | **KEEP** | Same as above. |
| Whitespace (+10) | **NEED MORE DATA** | Arithmetically consistent everywhere it applies, but its *interaction* with the transition bonus (splitting one 25-point candidate into two 10-point ones, and reversing C25's expected ranking) is a structural, not numeric, question — before changing this value, Round 2 should determine whether Phase 2D should instead look at adjacent-candidate pairs rather than single candidates. |
| Technical (-30) | **NEED MORE DATA** | Correct in isolation (X05 interior, C17), but co-occurs with the SF leak (finding 2) in a way no weight change can fix; also interacts unpredictably with span-splitting (C18). |
| Atomic (-30) | **NEED MORE DATA** | Same caveats as Technical; additionally stacks with Technical to -60 (X05) with no observed upper bound on stacking. |
| Punctuation sequence `INTERNAL` (-20) | **NEED MORE DATA** | Correct for CJK ellipsis runs; completely overridden by the SF leak for ASCII/interrobang runs, where INTERNAL candidates score +60 instead of -20. No value of this single weight can compensate for a candidate that is misclassified as SENTENCE_FINAL in the first place — this is a classification-layer question, not a Round 1 weight-tuning question. |

No value was changed in this round, per the task's explicit instruction.

---

**Round 1 status:** Complete per the stated completion criteria — all
applicable C01–C40 cases evaluated (including via supplementary
trailing-context probes where the literal text could not produce the
relevant candidate), X01–X07 explicitly analyzed, real Phase 1→2A→2B output
used throughout, pairwise rankings recorded with deltas, questionable
rankings and representation/specification issues separated from clean
passes, no production behavior changed, full regression suite unchanged
(389 passed) before and after. Stopping here per instruction, pending the
next design decision.
