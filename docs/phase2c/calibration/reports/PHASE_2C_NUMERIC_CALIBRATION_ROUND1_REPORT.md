# Phase 2C Numeric Calibration Ã¢â‚¬â€ Round 1 Report

## 1. Scope

This report covers Round 1 of Phase 2C numeric calibration only. It evaluates the
provisional, unfrozen scoring formula in `docs/PHASE_2C_CALIBRATION_MATRIX.md`
section 13 against the real, unmodified Phase 1 Ã¢â€ â€™ Phase 2A Ã¢â€ â€™ Phase 2B pipeline,
using the case set in that same document (C01Ã¢â‚¬â€œC40, X01Ã¢â‚¬â€œX07).

This round did **not**:
- modify `src/text_structure.py`, `src/boundary_observation.py`,
  `src/boundary_classification.py`, or `src/subtitle_segmenter.py`
- implement Phase 2D, `should_cut`, segmentation, or DP
- implement a production Phase 2C scoring module (`src/phase2c_scoring.py` was
  not created)
- change any of the provisional numeric weights
- add or modify any production test

All work in this round is confined to one calibration-only script,
`scripts/phase2c/calibrate_numeric_round1.py`, and this report.

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
calibration score, and the modifier breakdown. The full raw dump (`scripts/phase2c/calibrate_numeric_round1.py`
output) is the evidentiary basis for every claim in this report.

## 4. Numeric Baseline

| Factor | Value |
|---|---:|
| `SENTENCE_FINAL` (base) | +80 |
| `ELLIPSIS` (base) | +65 |
| `CLAUSE` (base) | +35 |
| `OTHER` (base) | 0 |
| CJK Ã¢â€ â€™ LATIN | +15 |
| LATIN Ã¢â€ â€™ CJK | +15 |
| Whitespace | +10 |
| Technical | -30 |
| Atomic | -30 |
| Punctuation sequence `INTERNAL` | -20 |

Used exactly as specified; not tuned during this round.

## 5. Case Results (C01Ã¢â‚¬â€œC40)

**A finding that affects most cases below and is stated once here:** several
matrix cases place their key punctuation character as the absolute last
character of the case text (C01, C02, all of C30Ã¢â‚¬â€œC40, and X01's ellipsis
side). `observe_boundaries()` only yields a candidate strictly *between* two
characters that both exist in the string Ã¢â‚¬â€ there is no candidate for "the
boundary after the very last character." Consequently the exact boundary the
matrix intends to score (the SENTENCE_FINAL/ELLIPSIS boundary immediately
after the terminal punctuation) is **never produced** for a case text that
ends in that punctuation. This is confirmed quantitatively in section 8: of
the 550 real (non-probe) candidates across all 40+2Ãƒâ€”7 case texts, 0 candidates
score the matrix's literal "SENTENCE_FINAL = 80" or "ELLIPSIS = 65" as a
genuine terminal boundary; the only `ellipsis`-classified candidate in the
entire non-probe set is from C37, whose ellipsis is followed by more text.

To separate "the formula is wrong" from "the case text has no trailing
context," three supplementary probes were added to the calibration script
(same texts with one trailing character appended Ã¢â‚¬â€ `C01_ctx_probe`,
`C02_ctx_probe`, `X01b_ctx_probe`, plus `C20_ascii_end_probe` for an ASCII
ellipsis run). These are not new cases and do not reinterpret C01/C02/X01;
they exist purely to show what the real pipeline scores at the boundary the
matrix describes, once that boundary can structurally exist. Results: with
trailing context, `Ã£â‚¬â€š` scores exactly 80.0 (`SENTENCE_FINAL`, no modifiers)
and `Ã¢â‚¬Â¦Ã¢â‚¬Â¦` scores exactly 65.0 (`ELLIPSIS`, no modifiers) Ã¢â‚¬â€ i.e. the base
scoring formula itself is correct; the gap is a pipeline representation
property of string-final punctuation, not a scoring defect.

| ID | Case | Real result | Category |
|---|---|---|---|
| C01 | `Ã£â‚¬â€š` at string end | No SF candidate observable (see above). Probe confirms 80.0 exactly once trailing context exists. | C (root); resolved via probe |
| C02 | `Ã¢â‚¬Â¦Ã¢â‚¬Â¦` at string end | No ELLIPSIS candidate observable; interior position (between the two `Ã¢â‚¬Â¦`) = OTHER, -20.0 (correct INTERNAL behavior). Probe confirms 65.0 exactly. | C (root); resolved via probe |
| C03 | `Ã¯Â¼Å’` clause | pos3 `Ã¯Â¼Å’Ã¯Â½Å“Ã¦Ë†â€˜`: CLAUSE, 35.0 | **A Ã¢â‚¬â€ PASS** |
| C04 | `Ã¤Â¸Â­Ã¦â€“â€¡Ã¯Â½Å“Ã¤Â¸Â­Ã¦â€“â€¡` | all boundaries OTHER, 0.0 | **A Ã¢â‚¬â€ PASS** |
| C05 | SF vs clause | 80.0 (probe) vs 35.0 (C03), ÃŽâ€=45, SF>C | **A Ã¢â‚¬â€ PASS** (via probe) |
| C06 | Ellipsis vs clause | 65.0 (probe) vs 35.0 (C03), ÃŽâ€=30, E>C | **A Ã¢â‚¬â€ PASS** (via probe) |
| C07 | Clause vs other | 35.0 (C03) vs 0.0 (C04), ÃŽâ€=35, C>O | **A Ã¢â‚¬â€ PASS** |
| C08 | SF vs Ellipsis | 80.0 (probe) vs 65.0 (probe), ÃŽâ€=15, SF>E | **A Ã¢â‚¬â€ PASS** (via probe) |
| C09 | `Ã¤Â¸Â­Ã¦â€“â€¡Ã¯Â½Å“English` | pos2: OTHER, 15.0 (CJKÃ¢â€ â€™LATIN) | **A Ã¢â‚¬â€ PASS** |
| C10 | `EnglishÃ¯Â½Å“Ã¤Â¸Â­Ã¦â€“â€¡` | pos7: OTHER, 15.0 (LATINÃ¢â€ â€™CJK) | **A Ã¢â‚¬â€ PASS** |
| C11 | `Ã¤Â¸Â­Ã¦â€“â€¡ Ã¯Â½Å“ English` | TWO candidates, 10.0 + 10.0 Ã¢â‚¬â€ **no candidate reaches 25** | **B Ã¢â‚¬â€ CALIBRATION OBSERVATION** |
| C12 | `English Ã¯Â½Å“ Ã¤Â¸Â­Ã¦â€“â€¡` | Same as C11 (symmetric): 10.0 + 10.0 | **B Ã¢â‚¬â€ CALIBRATION OBSERVATION** |
| C13 | enriched OTHER (25) vs CLAUSE (35) | best real "enriched OTHER" = 15.0 (C09, no-space transition); CLAUSE = 35.0 (C03). Ranking C>enriched-OTHER still holds (35>15) but "25" itself never occurs. | **B Ã¢â‚¬â€ CALIBRATION OBSERVATION** |
| C14 | CLAUSE+transition+whitespace (60) | pos3 of `Ã©Â¦â€“Ã¥â€¦Ë†Ã¯Â¼Å’ English`: CLAUSE, 45.0 (35+10 whitespace only Ã¢â‚¬â€ **no transition bonus**, because the clause character's `CharacterClass` is `PUNCTUATION`, never `CJK`/`LATIN`, so the transition rule's precondition can never fire on a CLAUSE candidate) | **C Ã¢â‚¬â€ PIPELINE REPRESENTATION ISSUE** |
| C15 | enriched CLAUSE (60) vs ELLIPSIS (65) | real enriched-CLAUSE max = 45.0 (C14) vs ELLIPSIS 65.0 (probe). E>enriched-C still holds (65>45) but built on the unreachable "60" premise. | **B Ã¢â‚¬â€ CALIBRATION OBSERVATION** (built on C14's issue) |
| C16 | enriched CLAUSE (60) vs SF (80) | 45.0 vs 80.0 (probe). SF>enriched-C holds (80>45) but built on the unreachable "60" premise. | **B Ã¢â‚¬â€ CALIBRATION OBSERVATION** (built on C14's issue) |
| C17 | `1,Ã¯Â½Å“000` technical, expected 5* | comma boundary: real class = **OTHER**, not CLAUSE (Phase 2B's own `_is_clause()` already falls through to OTHER when technical/atomic-protected). Score = -30.0 (0-30), not 5. Matrix's own footnote anticipates this. | **B Ã¢â‚¬â€ CALIBRATION OBSERVATION** (matrix-flagged) |
| C18 | `1, Ã¯Â½Å“000` technical, expected 15* | The space breaks Phase 1's thousands-separator match into **two disjoint atomic spans** (`1` and `000`); the comma is not inside either. Real: comma boundary = CLAUSE, 45.0 (35+10, **no** technical penalty at all Ã¢â‚¬â€ a third, different structural surprise from C17). | **C Ã¢â‚¬â€ PIPELINE REPRESENTATION ISSUE** |
| C19 | atomic boundary, expected -30* | `3.14`: pos1 (`3Ã¯Â½Å“.`) = OTHER, -30.0 (matches); pos2 (`.Ã¯Â½Å“1`) = **SENTENCE_FINAL, 50.0** (bare-fallback leak on the decimal point Ã¢â‚¬â€ see Ã‚Â§9); pos3 (`1Ã¯Â½Å“4`) = OTHER, -30.0 (matches). 2/3 positions match; the decimal point itself leaks SF. | **B Ã¢â‚¬â€ CALIBRATION OBSERVATION** (major finding, Ã‚Â§9) |
| C20 | INTERNAL, expected -20 | CJK ellipsis interior (C02/X01b/X07b): OTHER, -20.0 Ã¢â‚¬â€ **matches**. ASCII `.` runs (`Ã¥â€”Â¯......`, `......`) and interrobang runs (`Ã§Å“Å¸Ã§Å¡â€žÃ¯Â¼Å¸Ã¯Â¼Â`): all interior positions = **SENTENCE_FINAL, 60.0** (80-20), not -20.0. | **A for CJK; B for ASCII/interrobang runs** (major finding, Ã‚Â§9) |
| C21 | INTERNAL vs END | CJK: -20.0 vs 65.0 (probe) Ã¢â‚¬â€ END>INTERNAL holds cleanly. ASCII: INTERNAL=60.0 (leak) vs END=65.0 (`C20_ascii_end_probe`) Ã¢â‚¬â€ END still nominally > INTERNAL (65>60) but by a much smaller, essentially meaningless margin, because INTERNAL itself is wrongly positive. | **A for CJK; B for ASCII** |
| C22 | technical CLAUSE (5) vs enriched OTHER (25) | Real "technical CLAUSE" doesn't exist (see C17: it's OTHER, -30.0). Best real enriched-OTHER = 15.0 (C09). 15 > -30 Ã¢â‚¬â€ same qualitative direction as intended, but neither side matches its assumed class or value. | **B Ã¢â‚¬â€ CALIBRATION OBSERVATION** |
| C23 | technical CLAUSE (5) vs SF (80) | -30.0 (C17) vs 80.0 (probe). SF remains dominant (80 > -30, ÃŽâ€=110 vs matrix's assumed ÃŽâ€=75) | **A Ã¢â‚¬â€ PASS** (ranking holds; premise differs, see C17) |
| C24 | `Ã¤Â¸Â­Ã¦â€“â€¡\|Ã¤Â¸Â­Ã¦â€“â€¡` (0) vs `Ã¤Â¸Â­Ã¦â€“â€¡\|English` (15) | 0.0 (C04) vs 15.0 (C09), ÃŽâ€=15, B>A | **A Ã¢â‚¬â€ PASS** |
| C25 | `Ã¤Â¸Â­Ã¦â€“â€¡\|English` (15) vs `Ã¤Â¸Â­Ã¦â€“â€¡ \| English` (25) | 15.0 (C09) vs best 10.0 (C11) Ã¢â‚¬â€ **B < A, relation inverted** | **B Ã¢â‚¬â€ CALIBRATION OBSERVATION (ranking reversal)**, see Ã‚Â§9 |
| C26 | ordinary CLAUSE vs technical-protected CLAUSE | 35.0 (`Ã§Â¬Â¬Ã¤Â¸â‚¬Ã¯Â¼Å’Ã§Â¬Â¬Ã¤ÂºÅ’`) vs -30.0 (C17, actually OTHER). A>B holds (ÃŽâ€=65) but B is not really "CLAUSE". | **A Ã¢â‚¬â€ PASS** (ranking); note on B's real class |
| C27 | plain CLAUSE vs CLAUSE+transition | "CLAUSE+transition" is never observed anywhere in any dump (mutual exclusivity Ã¢â‚¬â€ see C14). Confirmed again at C32 pos13 (`Ã£â‚¬ÂÃ¯Â½Å“G`): class=CLAUSE, 35.0, **no** transition bonus despite `G` being LATIN. | **C Ã¢â‚¬â€ PIPELINE REPRESENTATION ISSUE** (not evaluable) |
| C28 | CLAUSE+transition vs +whitespace | Both variants require the unreachable "CLAUSE+transition" base. | **C Ã¢â‚¬â€ PIPELINE REPRESENTATION ISSUE** (not evaluable) |
| C29 | INTERNAL vs END | CJK: -20.0 vs 65.0(probe) Ã¢â‚¬â€ clean PASS. ASCII: 60.0 vs 65.0(`C20_ascii_end_probe`) Ã¢â‚¬â€ technically END>INTERNAL but the margin is trivial and INTERNAL is wrongly positive. | **A for CJK; B for ASCII** |
| C30Ã¢â‚¬â€œC36, C38Ã¢â‚¬â€œC40 | realistic sentences | See Ã‚Â§10. All of these terminate in `Ã£â‚¬â€š` as the last character, so (per the note above) their nominal "final" boundary is never produced as a candidate; every comma/`Ã£â‚¬Â` boundary present classifies CLAUSE=35.0 exactly as expected, all plain CJK-CJK/Latin-Latin boundaries = OTHER 0.0, transition/whitespace boundaries score 0/10/15 as expected. | **A for interior structure; C for the "final" boundary itself** |
| C37 | `Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã£â‚¬â€š` | pos7: ELLIPSIS, 65.0 (only non-probe ELLIPSIS in the whole dataset, because this is the one case whose ellipsis is *not* string-final) Ã¢â‚¬â€ matches exactly. Trailing `Ã£â‚¬â€š` again produces no SF candidate (string-final). | **A for the ellipsis; C for the trailing SF** |

## 6. Pairwise Ranking Summary

| Case | A | B | Score A | Score B | ÃŽâ€ (A-B) | Expected | Observed | Result |
|---|---|---|---:|---:|---:|---|---|---|
| C05 | SF | Clause | 80.0* | 35.0 | +45.0 | A>B | A>B | PASS* |
| C06 | Ellipsis | Clause | 65.0* | 35.0 | +30.0 | A>B | A>B | PASS* |
| C07 | Clause | Other | 35.0 | 0.0 | +35.0 | A>B | A>B | PASS |
| C08 | SF | Ellipsis | 80.0* | 65.0* | +15.0 | A>B | A>B | PASS* |
| C13 | Clause | enriched OTHER | 35.0 | 15.0Ã¢â‚¬Â  | +20.0 | A>B | A>B | PASSÃ¢â‚¬Â  |
| C15 | Ellipsis | enriched CLAUSE | 65.0* | 45.0Ã¢â‚¬Â  | +20.0 | B>A in matrix labels (E>enriched-C) i.e. A(here=Ellipsis)>B | A>B | PASSÃ¢â‚¬Â  (magnitude differs) |
| C16 | SF | enriched CLAUSE | 80.0* | 45.0Ã¢â‚¬Â  | +35.0 | A>B | A>B | PASSÃ¢â‚¬Â  (magnitude differs) |
| C21 (CJK) | END | INTERNAL | 65.0* | -20.0 | +85.0 | A>B | A>B | PASS* |
| C21 (ASCII) | END | INTERNAL | 65.0Ã¢â‚¬Â¡ | 60.0Ã¢â‚¬Â  | +5.0 | A>B | A>B (barely) | REVIEWÃ¢â‚¬Â  |
| C22 | enriched OTHER | technical CLAUSE | 15.0Ã¢â‚¬Â  | -30.0Ã¢â‚¬Â  | +45.0 | A>B | A>B | PASSÃ¢â‚¬Â  (both premises differ) |
| C23 | SF | technical CLAUSE | 80.0* | -30.0Ã¢â‚¬Â  | +110.0 | A>B | A>B | PASSÃ¢â‚¬Â  (premise differs) |
| C24 | `Ã¤Â¸Â­Ã¦â€“â€¡Ã¯Â½Å“English` | `Ã¤Â¸Â­Ã¦â€“â€¡Ã¯Â½Å“Ã¤Â¸Â­Ã¦â€“â€¡` | 15.0 | 0.0 | +15.0 | A>B | A>B | PASS |
| C25 | `Ã¤Â¸Â­Ã¦â€“â€¡ \| English` | `Ã¤Â¸Â­Ã¦â€“â€¡Ã¯Â½Å“English` | 10.0Ã¢â‚¬Â  | 15.0 | **-5.0** | A>B | **A<B** | **REVIEW** (real reversal) |
| C26 | ordinary CLAUSE | technical CLAUSE | 35.0 | -30.0Ã¢â‚¬Â  | +65.0 | A>B | A>B | PASS (premise differs) |
| C27 | plain CLAUSE | CLAUSE+transition | 35.0 | not observable | n/a | B>A | n/a | **N/E** (not evaluable) |
| C28 | CLAUSE+transition | +whitespace | not observable | not observable | n/a | B>A | n/a | **N/E** (not evaluable) |
| C29 (CJK) | END | INTERNAL | 65.0* | -20.0 | +85.0 | A>B | A>B | PASS* |
| C29 (ASCII) | END | INTERNAL | 65.0Ã¢â‚¬Â¡ | 60.0Ã¢â‚¬Â  | +5.0 | A>B | A>B (barely) | REVIEWÃ¢â‚¬Â  |

`*` value obtained via a trailing-context probe (see Ã‚Â§5), because the literal
matrix text is string-final and cannot produce the candidate directly.
`Ã¢â‚¬Â ` value differs from the matrix's assumed value/class because of a
representation issue documented in Ã‚Â§5/Ã‚Â§9 (real class or real reachable score
differs from the matrix's illustrative arithmetic).
`Ã¢â‚¬Â¡` value from `C20_ascii_end_probe`.

**Strong hierarchy (matrix Ã‚Â§9):** SF > ELLIPSIS, SF > ordinary CLAUSE, SF >
enriched CLAUSE Ã¢â‚¬â€ all hold on real (probe-supplemented) data.
**Moderate hierarchy:** ELLIPSIS > CLAUSE variants Ã¢â‚¬â€ holds. CLAUSE > ordinary
OTHER Ã¢â‚¬â€ holds (C07). CLAUSE > OTHER+transition Ã¢â‚¬â€ holds (C13, by 20 not 10).
CLAUSE > OTHER+transition+whitespace Ã¢â‚¬â€ cannot be tested as stated because
"OTHER+transition+whitespace" (25) is itself unreachable (C11/C12); best real
substitute (10.0) is still < CLAUSE (35.0), so the *intent* of the rule holds.
**Contextual reversal (OTHER+strong positive context > technically protected
CLAUSE):** holds numerically (15 > -30) but neither side is the class the
matrix assumed.
**Protection:** ordinary CLAUSE > technical CLAUSE Ã¢â‚¬â€ holds, but "technical
CLAUSE" doesn't exist as a real class (it's OTHER). Ordinary OTHER > atomic
OTHER Ã¢â‚¬â€ holds (0 > -30). Terminal > internal sequence Ã¢â‚¬â€ holds for CJK, holds
only nominally (and by a thin, near-meaningless margin) for ASCII/interrobang
runs because internal is wrongly elevated by the SF leak.

## 7. Counterexample Analysis (X01Ã¢â‚¬â€œX07)

### X01 Ã¢â‚¬â€ `Ã¥â€”Â¯Ã¢â‚¬Â¦Ã¢â‚¬Â¦` (ellipsis) vs `CPUÃ£â‚¬Â Ã¯Â½Å“ GPU` (clause+whitespace)
1. **Interpretation:** `Ã¥â€”Â¯Ã¢â‚¬Â¦Ã¢â‚¬Â¦` is string-final, so its ELLIPSIS candidate is not
   directly observable; `X01b_ctx_probe` (`Ã¥â€”Â¯Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¥Â¥Â½`) supplies it.
2. **Boundary A evidence:** ellipsis END, `PunctuationSequenceState=END`,
   `contains_sentence_final_punctuation=False`.
3. **Boundary A score:** 65.0 (probe).
4. **Boundary B evidence:** `Ã£â‚¬ÂÃ¯Â½Å“(space)` in `CPUÃ£â‚¬Â GPU`, left_char=`Ã£â‚¬Â`,
   `left_character_class=PUNCTUATION` (not CJK), `Whitespace` modifier only.
5. **Boundary B score:** 45.0 (35 CLAUSE + 10 whitespace; **not 60** Ã¢â‚¬â€ the
   matrix's "60" for this side assumes a transition bonus that the real
   pipeline never grants a CLAUSE candidate, per the C14/C27 finding).
6. **Actual ranking:** A(65.0) > B(45.0).
7. **Intended ranking:** ELLIPSIS(65) > "CLAUSE+transition+whitespace"(60) Ã¢â‚¬â€ same direction.
8. **Score difference:** matrix ÃŽâ€=5; real ÃŽâ€=20.
9. **Reasonableness:** the *direction* the question asks about ("is ELLIPSIS
   sufficiently preferred?") is answered yes, and by a wider margin than the
   matrix assumed Ã¢â‚¬â€ but only because B's assumed value (60) is itself
   unreachable; B's real ceiling is 45.
10. **Numeric adjustment:** not evaluated this round (rule 15); flagged that
    B's premise, not the ELLIPSIS/CLAUSE weights, is what drives the gap.

### X02 Ã¢â‚¬â€ ordinary CLAUSE (35) vs `Ã¤Â¸Â­Ã¦â€“â€¡ Ã¯Â½Å“ English` (25)
1. **Interpretation:** directly representable; both sides are real cases (C03/C26-style clause, C11).
2. **Boundary A evidence:** `Ã¯Â¼Å’Ã¯Â½Å“Ã¦Ë†â€˜` in `Ã©Â¦â€“Ã¥â€¦Ë†Ã¯Â¼Å’Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â»â€¹Ã§Â´Â¹ CPU`, CLAUSE.
3. **Boundary A score:** 35.0.
4. **Boundary B evidence:** best of the two `Ã¤Â¸Â­Ã¦â€“â€¡ Ã¯Â½Å“ English` candidates (whitespace-only, no transition co-occurrence Ã¢â‚¬â€ see C11/C25).
5. **Boundary B score:** 10.0 (not 25).
6. **Actual ranking:** A(35.0) > B(10.0).
7. **Intended ranking:** CLAUSE(35) > enriched-OTHER(25) Ã¢â‚¬â€ same direction, larger margin.
8. **Score difference:** matrix ÃŽâ€=10; real ÃŽâ€=25.
9. **Reasonableness:** direction preserved; the question ("is CLAUSE sufficiently preferred?") is answered even more strongly yes than the matrix assumed, again because B's assumed 25 never actually occurs (C11 finding).
10. **Numeric adjustment:** none indicated; the C11 representation issue is the actual driver.

### X03 Ã¢â‚¬â€ technical CLAUSE (5) vs transition+whitespace (25)
1. **Interpretation:** `1,000` Ã¢â‚¬â€ comma is OTHER (Atomic), not CLAUSE (C17 finding); "transition+whitespace" (25) is also unreachable (C11 finding). Both sides of this counterexample rest on unreachable/mis-assumed classes.
2. **Boundary A evidence:** `1,Ã¯Â½Å“000` comma boundary, `containing_spans=[atomic/numeric]`, real class=OTHER.
3. **Boundary A score:** -30.0 (not 5).
4. **Boundary B evidence:** best real transition+whitespace candidate (C11-style), whitespace-only.
5. **Boundary B score:** 10.0 (not 25).
6. **Actual ranking:** B(10.0) > A(-30.0).
7. **Intended ranking:** A(5) < B(25), i.e. B>A Ã¢â‚¬â€ same direction.
8. **Score difference:** matrix ÃŽâ€=20; real ÃŽâ€=40.
9. **Reasonableness:** direction holds; question "is -30 too strong?" cannot be cleanly answered from this pairing because A is not really a penalized CLAUSE at all Ã¢â‚¬â€ it is an ordinary atomic-penalized OTHER position, so this counterexample doesn't actually probe what it was designed to probe.
10. **Numeric adjustment:** not evaluable as specified; would need a case where a clause character is technical-protected *and* still classified CLAUSE, which the current Phase 2B rules make impossible by design (Ã‚Â§9 "technical-protected-CLAUSE-is-actually-OTHER").

### X04 Ã¢â‚¬â€ SF with minor negative context vs enriched CLAUSE (case-dependent, no concrete text given)
No representative text was specified in the matrix. A minimal literal reading
("sentence-final immediately after a technical/atomic span," e.g. `v1.0Ã£â‚¬â€š`)
was not separately probed this round because it overlaps substantially with
X05's evidence (technical-context SF at 50.0/20.0, sections below). Recorded
as:
- **Category: D Ã¢â‚¬â€ CASE SPECIFICATION ISSUE** (no concrete boundary text to
  evaluate against; the matrix itself labels it "case-dependent").
- Partial evidence from X05: SF immediately after technical/atomic content
  scores 20.0Ã¢â‚¬â€œ50.0 (80 base minus one or two 30-point penalties), still well
  above ordinary CLAUSE (35) and comfortably above OTHER Ã¢â‚¬â€ i.e. even "minor
  negative context" versions of SF observed so far remain fairly strong, not
  reduced to reversal.

### X05 Ã¢â‚¬â€ long technical expression, multiple candidates
1. **Interpretation:** `Ã¨Â¦â€¹ v1.2.3-beta Ã§â€°Ë†Ã¦Å“Â¬Ã¨ÂªÂªÃ¦ËœÅ½ http://example.com/path Ã©Â ÂÃ©ÂÂ¢Ã£â‚¬â€š` exercises version, numeric, and URL technical/atomic spans together.
2. **Boundary evidence (representative):**
   - `vÃ¯Â½Å“1`: OTHER, `technical/version`, -30.0
   - `1Ã¯Â½Å“.`: OTHER, `technical/version`+`atomic/numeric`, -60.0
   - `.Ã¯Â½Å“2`: **SENTENCE_FINAL**, same double containment, **+20.0** (80-30-30) Ã¢â‚¬â€ bare-fallback SF leak on a decimal point nested inside both a version span and a numeric span
   - `.Ã¯Â½Å“3`: **SENTENCE_FINAL**, `technical/version` only, **+50.0** (80-30)
   - interior of the URL (`http://...`): all OTHER, -30.0 each (18 boundaries)
   - `.Ã¯Â½Å“c` in `example.com`: **SENTENCE_FINAL**, `technical/url`, **+50.0** (80-30) Ã¢â‚¬â€ same leak inside a URL domain separator
3. **Actual ranking:** the SF-leak boundaries (20.0/50.0/50.0) score *higher* than every ordinary interior technical boundary (-30.0) and higher than ordinary CLAUSE (35.0 elsewhere in the corpus).
4. **Intended/expected behavior (matrix):** "Does protection hold consistently?"
5. **Assessment:** protection does **not** hold consistently for these three
   positions Ã¢â‚¬â€ a boundary strictly inside a version string or a URL domain
   scores as if it were a genuine, unpenalized-relative-to-CLAUSE sentence
   ending, which is the opposite of the intended effect of technical
   protection. All three are internal punctuation positions that happen to be
   "." immediately followed by a digit or letter with no span ending exactly
   there, so Phase 2A's bare single-character fallback fires.
6. **Numeric adjustment:** not evaluated this round; this is a classification/representation issue (Phase 2A's bare-fallback SF character set), not a Phase 2C weight issue Ã¢â‚¬â€ changing weights would not fix it, since the problem is the boundary being labeled `SENTENCE_FINAL` at all.

### X06 Ã¢â‚¬â€ notes with frequent mixed-language spaces
1. **Interpretation:** `Ã¤Â¸Â­Ã¦â€“â€¡ English Ã¤Â¸Â­Ã¦â€“â€¡ English Ã¤Â¸Â­Ã¦â€“â€¡` Ã¢â‚¬â€ five language transitions, each mediated by whitespace.
2. **Boundary evidence:** every transition point produces **two** OTHER,
   10.0 (whitespace-only) candidates, exactly as in C11/C12/C25 Ã¢â‚¬â€ never a
   single combined 25.0 candidate.
3. **Actual candidate count:** 8 non-zero-scoring boundaries (all 10.0), 0
   candidates at 15.0 or 25.0.
4. **Intended ranking:** "does transition+whitespace create too many
   candidates?"
5. **Assessment:** yes Ã¢â‚¬â€ each language switch produces two boundaries at a
   modest, identical score (10.0) rather than one clearly-preferred boundary,
   so this scoring layer alone does not distinguish "the space between two
   words" from "the space that is also a language switch." That distinction
   is present in C09/C10 (15.0, no space) but disappears once whitespace is
   introduced.
6. **Numeric adjustment:** not evaluated; flagged as a design question for
   Phase 2D (how multiple adjacent low-margin candidates around one semantic
   switch point should be resolved) rather than a Phase 2C weight change.

### X07 Ã¢â‚¬â€ unusual punctuation runs
1. **Interpretation:** two sub-cases: `Ã§Å“Å¸Ã§Å¡â€žÃ¯Â¼Å¸Ã¯Â¼Â` (interrobang run) and
   `Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¢â‚¬Â¦`/`Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¢â‚¬Â¦` (merged ellipsis run).
2. **Boundary A evidence (X07a, interrobang interior):** `Ã¯Â¼Å¸Ã¯Â½Å“Ã¯Â¼Â`,
   `PunctuationSequenceState=INTERNAL`, `contains_sentence_final_punctuation=True`
   (bare fallback fires on `Ã¯Â¼Å¸`).
3. **Boundary A score:** 60.0 (**SENTENCE_FINAL**, 80-20), not the -20 a
   plain INTERNAL position would suggest.
4. **Boundary B evidence (X07b, merged ellipsis run `Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¢â‚¬Â¦`):** all 3
   interior positions, `INTERNAL`, `contains_sentence_final_punctuation=False`
   (CJK `Ã¢â‚¬Â¦` is not in the bare-fallback SF set).
5. **Boundary B score:** -20.0 each (OTHER), matches C20's assumption exactly.
6. **Actual ranking / behavior:** ASCII/interrobang-composed internal runs
   leak SENTENCE_FINAL (60.0); CJK-`Ã¢â‚¬Â¦`-composed internal runs do not (-20.0).
7. **Intended/expected:** "does INTERNAL penalty suppress false boundaries
   without hurting END?" Ã¢â‚¬â€ for CJK runs, yes; for ASCII `.`/`Ã¯Â¼Å¸`/`Ã¯Â¼Â`
   composed runs, no Ã¢â‚¬â€ the internal penalty is not just insufficiently
   suppressive, it is overridden entirely by a positive SENTENCE_FINAL base.
8. **Score difference:** CJK vs ASCII internal, same structural role: -20.0
   vs +60.0, a swing of 80 points from a single upstream evidence field.
9. **Reasonableness:** this is the most severe individual finding in this
   round Ã¢â‚¬â€ an INTERNAL punctuation-sequence position (which every acceptance
   rule treats as something that should be suppressed) can score higher than
   an ordinary CLAUSE boundary (35.0) whenever the sequence is composed of
   ASCII `.`, `Ã¯Â¼Å¸`, or `Ã¯Â¼Â` characters.
10. **Numeric adjustment:** would not fix this Ã¢â‚¬â€ even Internal Seq = -80 or
    lower would only be masking a classification issue (the position is
    being labeled SENTENCE_FINAL when it should not be eligible for that
    label at all inside a sequence). This is a Phase 2A/2B design question,
    out of this round's scope to change.

## 8. Score Distribution

Computed over all 550 real (non-probe) boundary candidates dumped across
C01Ã¢â‚¬â€œC40 and X01Ã¢â‚¬â€œX07 (probe-only supplementary candidates excluded to keep
this distribution matched to the literal matrix case set):

- **Minimum:** -60.0 (X05, position doubly inside `technical/version` +
  `atomic/numeric`)
- **Maximum:** 65.0 (C37, the one non-string-final ellipsis end)
- **Mean:** Ã¢â€°Ë†2.56
- **Median:** 0.0

Distribution by real `BoundaryClass`:

| BoundaryClass | Count | Note |
|---|---:|---|
| `other` | 517 | includes every plain/whitespace/transition/technical/atomic-penalized position |
| `clause` | 17 | all exactly 35.0 or 45.0 (with whitespace) Ã¢â‚¬â€ never technical-protected in this set (protected clause chars fall to `other`) |
| `sentence_final` | 15 | **all 15 are bare-fallback leaks** at internal/technical/atomic positions (Ã‚Â§5, Ã‚Â§9) Ã¢â‚¬â€ zero are genuine terminal endings, because every case text with a genuine terminal sentence-final character places it as the string's last character, which produces no candidate |
| `ellipsis` | 1 | C37 only Ã¢â‚¬â€ the sole case whose ellipsis is not string-final |

The maximum observed score (65.0, not 80.0) and the fact that 100% of
`sentence_final`-classified candidates are leak artifacts are themselves
calibration findings, not just descriptive statistics: they mean this
round's real dataset never exercises the base `SENTENCE_FINAL=80` value in
its intended (genuine terminal boundary) role at all Ã¢â‚¬â€ only the
trailing-context probes did.

## 9. Important Observations

### Pipeline behavior
1. **String-final punctuation produces no boundary candidate.**
   `observe_boundaries()` only yields candidates strictly between two
   existing characters, so a sentence-final or ellipsis character at the very
   end of an input string never gets scored as the terminal boundary the
   matrix describes. This affects C01, C02, all of C30Ã¢â‚¬â€œC40's "final"
   boundary, and X01's ellipsis side. Confirmed innocuous (not a scoring
   defect) via three trailing-context probes that reproduce the exact
   expected 80.0/65.0 once a following character exists.
2. **Bare-fallback SENTENCE_FINAL leak.** Any internal punctuation-sequence
   position, or any position strictly inside a technical/atomic span, where
   no Phase 1 span happens to *end* exactly there, falls through to Phase
   2A's bare single-character check. Because that bare set includes ASCII
   `.`, `Ã¯Â¼Å¸`, `Ã¯Â¼Â` (an already-approved Phase 2A design decision, not
   something this round can or should change), such positions register
   `contains_sentence_final_punctuation=True` and classify SENTENCE_FINAL Ã¢â‚¬â€
   even though they are internal to an ellipsis run, a version string, a
   decimal number, or a URL. Observed at C19, C20/C21 (ASCII), X05 (3
   positions), X07a. CJK `Ã¢â‚¬Â¦` does not trigger this (it is intentionally
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
   the comma is not protected at all (C18) Ã¢â‚¬â€ a materially different
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
   2A/2B evidence) is arithmetically correct in every candidate inspected Ã¢â‚¬â€
   every discrepancy above traces back to which `BoundaryClass`/features the
   real pipeline assigns, not to the arithmetic applied on top of them.
8. No case exercised two positive modifiers simultaneously except CJK/Latin
   transition and whitespace individually stacking on separate positions Ã¢â‚¬â€
   the formula's "no modifier accidentally dominates" acceptance rule (rule
   7) was not stressed by any *reachable* multi-modifier combination this
   round, because CLAUSE+transition and transition+whitespace-on-one-
   candidate are both unreachable.

### Ranking behavior
9. **C25 is a genuine, reproducible ranking reversal**, not an artifact of
   an unreachable premise: `Ã¤Â¸Â­Ã¦â€“â€¡Ã¯Â½Å“English` (no space, 15.0) actually
   outranks the best real candidate from `Ã¤Â¸Â­Ã¦â€“â€¡ Ã¯Â½Å“ English` (with space,
   10.0), inverting the matrix's expected "adding whitespace should
   increase the score" intuition. This happens because adding the space
   removes the transition bonus from the boundary entirely (it moves to a
   different, whitespace-only candidate) rather than adding to it.
10. **X07/C20's ASCII-vs-CJK asymmetry is the most severe finding**: an
    INTERNAL position inside an ASCII ellipsis or interrobang run can score
    60.0 Ã¢â‚¬â€ higher than ordinary CLAUSE (35.0) Ã¢â‚¬â€ while the structurally
    identical CJK case scores -20.0 exactly as intended. A single upstream
    evidence field (the bare fallback's ASCII character set) produces an
    80-point swing between two cases the matrix treats as equivalent.

## 10. Realistic Case Review (C30Ã¢â‚¬â€œC40)

Across all 11 cases:
- **High-scoring candidates** are, without exception, ordinary CLAUSE
  boundaries at 35.0 (C30, C31, C32Ãƒâ€”2, C34, C35, C36, C38, C40Ãƒâ€”2) or 45.0
  where whitespace happens to coincide with the clause boundary (X01-style;
  not observed in C30Ã¢â‚¬â€œC40 directly, all CLAUSE hits here are 35.0 exactly
  since none of these particular commas sit next to whitespace). No
  candidate in C30Ã¢â‚¬â€œC40 scored above 35.0 anywhere Ã¢â‚¬â€ the sentences never
  produced their nominal terminal SENTENCE_FINAL candidate (see Ã‚Â§5/Ã‚Â§9,
  finding 1), so the "final > comma" claim in each row's "expected behavior"
  column could not be directly demonstrated from these dumps alone; it is
  independently supported by the trailing-context probes in Ã‚Â§5, which show
  a genuine SF boundary (80.0) does outscore every CLAUSE boundary observed
  here (35.0/45.0) once it can exist as a candidate.
- **Low-scoring candidates**: none were negative in C30Ã¢â‚¬â€œC40 specifically
  (no technical/atomic spans were matched inside these particular sentences,
  even where the matrix's notes call out "technical terms protected," e.g.
  C31's `ARM Cortex-A`, C33's `AI accelerator`, C36's `Python API`/`function`
  Ã¢â‚¬â€ none of these were recognized as `technical`/`atomic` spans by Phase 1
  in this text; only genuinely numeric/version/URL patterns are, per X05).
  This means C31/C33/C34/C36's "technical terms protected" expectation is
  **not actually exercised** by these sentences Ã¢â‚¬â€ Phase 1 does not treat
  bare identifiers like `ARM`, `Cortex-A`, `AI accelerator`, or `function`
  as technical/atomic spans, so there is nothing here for the -30 penalty to
  apply to. This is a case-specification observation, not a scoring defect:
  the intended "technical protection" behavior is real (demonstrated by
  X05's URL/version content) but these particular realistic sentences don't
  contain the kind of technical span Phase 1 actually recognizes.
- **Technical-context penalization**: not exercised in C30Ã¢â‚¬â€œC40 (see above);
  confirmed working correctly (if leak-prone, see Ã‚Â§9 finding 2) in X05.
- **CJK/Latin transition bonus**: fires as the flat +15 exactly where
  expected (e.g. C30 pos2 `Ã§Â´Â¹Ã¯Â½Å“ ` region is whitespace-mediated so scores
  10.0, not 15.0 Ã¢â‚¬â€ nearly every CJK/Latin boundary in C30Ã¢â‚¬â€œC40 is
  whitespace-adjacent, so the "pure" +15 transition bonus in isolation is
  rare in this realistic set; most transitions here score 10.0 via
  whitespace instead, consistent with finding 4 in Ã‚Â§9).
- **Whitespace incremental effect**: consistently and only +10, applied
  uniformly, no compounding observed Ã¢â‚¬â€ consistent with the formula.
- **Sentence-final dominance**: cannot be directly confirmed from C30Ã¢â‚¬â€œC40's
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
  strong cut point) Ã¢â‚¬â€ the Phase 2C score alone cannot supply that signal for
  a string-final period, only for a period followed by more text.

## 11. Scope Compliance

- `src/subtitle_segmenter.py`: **untouched** (verified: file mtime and
  content unchanged from before this round).
- Phase 2D: **not implemented.**
- `src/text_structure.py`: **untouched** this round.
- `src/boundary_observation.py`: **untouched** this round.
- `src/boundary_classification.py`: **untouched** this round.
- No production scoring module implemented Ã¢â‚¬â€ `src/phase2c_scoring.py` does
  not exist; the only new/changed file is the calibration-only
  `scripts/phase2c/calibrate_numeric_round1.py` (not imported by anything under
  `src/`, verified via `grep -rn "phase2c\|calibrate_phase2c" src/` Ã¢â€ â€™ no
  matches) plus this report and the calibration matrix copy under `docs/`.
- No numeric weight changed Ã¢â‚¬â€ the values in Ã‚Â§4 are exactly the matrix's
  Ã‚Â§13 values.
- No tests modified to hide regressions Ã¢â‚¬â€ no test file was touched.

## 12. Test Results

Command: `python -m pytest tests/ -q` (run from repository root, using the
project's `/tmp/venv` interpreter)

Result: **389 passed, 2 warnings, 15 subtests passed** Ã¢â‚¬â€ identical to the
pre-round baseline. No regression.

(Run both before and after the calibration script changes in this round;
identical result both times, as expected since no production file was
touched.)

---

## Summary of case categories

- **A Ã¢â‚¬â€ PASS:** C03, C04, C05*, C06*, C07, C08*, C09, C10, C21(CJK), C23,
  C24, C26, C29(CJK), plus the interior structure of C30Ã¢â‚¬â€œC36/C38Ã¢â‚¬â€œC40.
- **B Ã¢â‚¬â€ CALIBRATION OBSERVATION:** C11, C12, C13, C15, C16, C17, C19, C20
  (ASCII/interrobang), C21(ASCII), C22, C25 (ranking reversal), C29(ASCII),
  X01, X02, X03, X05, X06, X07.
- **C Ã¢â‚¬â€ PIPELINE REPRESENTATION ISSUE:** C01 (root case), C02 (root case),
  C14, C18, C27, C28, the "final" boundary of C30Ã¢â‚¬â€œC40, X01's ellipsis side
  (root case).
- **D Ã¢â‚¬â€ CASE SPECIFICATION ISSUE:** X04 (no concrete text provided in the
  matrix).

`*` resolved via a supplementary trailing-context probe rather than the
literal case text.

## Numeric sensitivity observations

Ranked by how much a single upstream evidence bit changes the outcome,
holding the formula fixed:
1. **`contains_sentence_final_punctuation` (bare-fallback ASCII leak):**
   swings a candidate from -20 (or -30) to +50/+60 Ã¢â‚¬â€ an 80Ã¢â‚¬â€œ110 point range
   from one boolean, entirely outside the numeric model's control.
2. **Whether whitespace intervenes between a CJK/Latin transition:**
   changes 15 Ã¢â€ â€™ 10 and splits one candidate into two (C25's reversal).
3. **Whether a clause character falls inside a technical/atomic span:**
   changes CLAUSE(35) Ã¢â€ â€™ OTHER(-30), a 65-point swing, not the "35Ã¢â€ â€™5" the
   matrix's illustrative arithmetic assumed.
4. **Technical vs Atomic stacking (X05):** two -30 penalties can co-occur
   in the same containing_spans set, reaching -60 Ã¢â‚¬â€ the model has no cap on
   how many negative modifiers stack.
5. Ordinary modifier stacking (Whitespace alone, CJK/Latin alone) behaves
   exactly as specified Ã¢â‚¬â€ no surprises.

## Numeric Calibration Recommendations (Round 1 Ã¢â‚¬â€ no changes made)

| Factor | Recommendation | Basis |
|---|---|---|
| `SENTENCE_FINAL` base (+80) | **NEED MORE DATA** | Never exercised in its genuine terminal-boundary role by any of the 40+7 literal case texts; only probes exercised it. Round 2 should include case texts with trailing context so the base value can be judged in-situ. |
| `ELLIPSIS` base (+65) | **KEEP** | Confirmed exactly correct at C37 (genuine, non-string-final) and at all three probes. |
| `CLAUSE` base (+35) | **KEEP** | Confirmed exactly correct at every ordinary (non-technical) clause boundary observed (17 candidates, C03/C26/C30Ã¢â‚¬â€œC40/X01). |
| `OTHER` base (0) | **KEEP** | Baseline, consistent everywhere. |
| CJK Ã¢â€ â€™ LATIN (+15) | **KEEP** | Matches C09 exactly; symmetric with LATINÃ¢â€ â€™CJK (C10) as required by acceptance rule 3. |
| LATIN Ã¢â€ â€™ CJK (+15) | **KEEP** | Same as above. |
| Whitespace (+10) | **NEED MORE DATA** | Arithmetically consistent everywhere it applies, but its *interaction* with the transition bonus (splitting one 25-point candidate into two 10-point ones, and reversing C25's expected ranking) is a structural, not numeric, question Ã¢â‚¬â€ before changing this value, Round 2 should determine whether Phase 2D should instead look at adjacent-candidate pairs rather than single candidates. |
| Technical (-30) | **NEED MORE DATA** | Correct in isolation (X05 interior, C17), but co-occurs with the SF leak (finding 2) in a way no weight change can fix; also interacts unpredictably with span-splitting (C18). |
| Atomic (-30) | **NEED MORE DATA** | Same caveats as Technical; additionally stacks with Technical to -60 (X05) with no observed upper bound on stacking. |
| Punctuation sequence `INTERNAL` (-20) | **NEED MORE DATA** | Correct for CJK ellipsis runs; completely overridden by the SF leak for ASCII/interrobang runs, where INTERNAL candidates score +60 instead of -20. No value of this single weight can compensate for a candidate that is misclassified as SENTENCE_FINAL in the first place Ã¢â‚¬â€ this is a classification-layer question, not a Round 1 weight-tuning question. |

No value was changed in this round, per the task's explicit instruction.

---

**Round 1 status:** Complete per the stated completion criteria Ã¢â‚¬â€ all
applicable C01Ã¢â‚¬â€œC40 cases evaluated (including via supplementary
trailing-context probes where the literal text could not produce the
relevant candidate), X01Ã¢â‚¬â€œX07 explicitly analyzed, real Phase 1Ã¢â€ â€™2AÃ¢â€ â€™2B output
used throughout, pairwise rankings recorded with deltas, questionable
rankings and representation/specification issues separated from clean
passes, no production behavior changed, full regression suite unchanged
(389 passed) before and after. Stopping here per instruction, pending the
next design decision.
