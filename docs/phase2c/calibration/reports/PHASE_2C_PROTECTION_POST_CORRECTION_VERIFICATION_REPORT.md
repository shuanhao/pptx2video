# Phase 2C Protection Calibration Ã¢â‚¬â€ Post-Correction Verification

**Status:** Verification Only Ã¢â‚¬â€ no scoring implementation, no weight changes, no
production code changes
**Phase:** Phase 2C Ã¢â‚¬â€ Numeric Calibration (Protection family)
**Purpose:** Re-run the existing Protection Calibration against the corrected Phase
2A/2B pipeline (Phase 2C Upstream Correction, Round B) and determine whether the
Protection Calibration model is behaviorally stable enough to proceed toward numeric
calibration freeze.

---

## 1. Verification Objective

Confirm, using the real, unmodified Phase 1 Ã¢â€ â€™ Phase 2A Ã¢â€ â€™ Phase 2B Ã¢â€ â€™ calibration
pipeline and the existing, unmodified Protection Calibration tooling, that:

1. P11 (Technical + INTERNAL) is now correctly observable as `OTHER`,
   `Technical=True`, `INTERNAL=True`, `Score=-50.0`.
2. No other protection case (P01Ã¢â‚¬â€œP10, P13Ã¢â‚¬â€œP15) drifted as a side effect of the Round B
   correction.
3. P12 (Atomic + INTERNAL) remains an unaffected, independent `CASE ISSUE`.
4. The provisional protection numbers (`Technical=-30`, `Atomic=-30`, `INTERNAL=-20`)
   remain behaviorally supported without any value change.
5. Protection Calibration can be declared ready (or not) to proceed to the next
   Numeric Calibration decision.

This round changes nothing: no scoring implementation, no matrix, no script, no
production code, no existing report.

---

## 2. Code Baseline

```
$ python3 -m pytest tests/ -q
397 passed, 2 warnings, 15 subtests passed in 21.42s

$ python3 -m unittest discover -s tests -v
Ran 397 tests in 19.381s
OK
```

Matches the expected post-Round-B baseline (397) exactly on both runners. No
investigation was required.

---

## 3. Authoritative Documents Identified

Per repository inspection (`docs/`, `scripts/`), the currently authoritative Protection
Calibration artifacts are:

- **Matrix:** `docs/phase2c/calibration/matrices/PHASE_2C_PROTECTION_CALIBRATION_MATRIX.md` (v0.1) Ã¢â‚¬â€ the only
  protection-family matrix in the repository; no v0.2 or later exists.
- **Script:** `scripts/phase2c/calibrate_protection_round1.py` Ã¢â‚¬â€ the only
  protection-family calibration script; implements the matrix's "strongest-only"
  Technical/Atomic combination rule. Not modified this round.
- **Prior report (for drift comparison):**
  `docs/phase2c/calibration/reports/PHASE_2C_PROTECTION_CALIBRATION_ROUND1_REPORT.md` Ã¢â‚¬â€ the pre-correction
  Protection Calibration results this round diffs against.
- **Correction record:**
  `docs/phase2c/decisions/PHASE_2C_ASCII_PERIOD_UPSTREAM_CORRECTION_DECISION.md` Ã¢â‚¬â€ Round A's decision
  document; the fix it specified is what Round B implemented and this round verifies.

None of these four documents were modified.

### 3.1 Numeric baseline discrepancy (flagged, not resolved)

This round's own instructions (Ã‚Â§2 of the round contract) state the current base
scores as `CLAUSE=+20`, `ELLIPSIS=+40`. The authoritative matrix
(`docs/PHASE_2C_PROTECTION_CALIBRATION_MATRIX.md`, Ã‚Â§3) and the existing, unmodified
calibration script (`scripts/phase2c/calibrate_protection_round1.py`,
`_BASE_SCORES`) both use `CLAUSE=+35`, `ELLIPSIS=+65` Ã¢â‚¬â€ identical to every prior
round (Calibration Round 1, Round 2, and Protection Round 1). This document does not
silently adopt either number set as correct: since the round's own rules require
using the existing matrix/script exactly as-is and forbid changing any weight, the
verification below uses the values the actual matrix and script implement
(`CLAUSE=35`, `ELLIPSIS=65`), not the round contract's restated `20`/`40`. This
discrepancy does not affect Protection Calibration's own scope (the matrix explicitly
excludes `ELLIPSIS`/`CLAUSE` base-score calibration Ã¢â‚¬â€ see its Ã‚Â§2 "Does not cover"),
but it is flagged here as something that must be reconciled before it can silently
propagate into a future Numeric Calibration round Ã¢â‚¬â€ see Ã‚Â§11.

---

## 4. Calibration Script Used

```
$ python3 scripts/phase2c/calibrate_protection_round1.py > /tmp/calibration_protection_postcorrection_verification_raw.txt
```

Run exactly as-is, unmodified, with its existing case list (P01_a, P01_b, P02,
P03_P04, P05_transition_only, P06_P15_clause_only, P08_P09_P10_internal,
P11_probe_url_ellipsis, P11_probe_version_ellipsis, P12_probe_number_ellipsis,
P12_probe_decimal_then_ellipsis_touching, P12_probe_malformed_decimal_double_dot,
P12_probe_malformed_decimal_quad_dot). Output format preserved verbatim (raw
per-candidate dump); nothing edited by hand.

---

## 5. P01Ã¢â‚¬â€œP15 Result Table

Candidate positions below are the same real-pipeline candidates the prior
(pre-correction) Protection Calibration Round 1 report identified and used Ã¢â‚¬â€ verified
unchanged in this round's raw output except where explicitly marked.

| Case | Class | Technical | Atomic | Punc State | Base | Protection | Sequence | Final | Status |
|---|---|---|---|---|---|---|---|---|---|
| P01 (`Ã¤Â¸Â­Ã¦â€“â€¡Ã¤Â¸Â­Ã¦â€“â€¡`, pos1Ã¢â‚¬â€œ3) | OTHER | No | No | none | 0.0 | 0.0 | 0.0 | **0.0** | PASS |
| P02 (`1,\|000` region, pos7) | OTHER | No | Yes | none | 0.0 | -30.0 | 0.0 | **-30.0** | PASS (relation); label CASE ISSUE carried over unchanged (see Ã‚Â§5.1) |
| P03 (`v\|1.2.3`, pos7) | OTHER | Yes | No | none | 0.0 | -30.0 | 0.0 | **-30.0** | PASS (relation); label CASE ISSUE carried over unchanged, mirrors P02 |
| P04 (`1\|.` in `v1.2.3`, pos8) | OTHER | Yes | Yes | none | 0.0 | -30.0 (strongest-only) | 0.0 | **-30.0** | PASS |
| P05/P14 (`Ã¦â€“â€¡\|E`, pos2) | OTHER | No | No | none | 0.0 (+15.0 transition CJKÃ¢â€ â€™LATIN) | 0.0 | 0.0 | **15.0** | PASS |
| P06/P15 (`Ã¯Â¼Å’\|Ã¦Ë†â€˜`, pos3) | CLAUSE | No | No | none | 35.0 | 0.0 | 0.0 | **35.0** | PASS |
| P07 (CLAUSE vs Atomic, pairwise) | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | **ÃŽâ€=65.0** | PASS |
| P08 (`Ã¢â‚¬Â¦\|Ã¢â‚¬Â¦`, pos6) | OTHER | No | No | INTERNAL | 0.0 | 0.0 | -20.0 | **-20.0** | PASS |
| P09 (Transition vs INTERNAL, pairwise) | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | **ÃŽâ€=35.0** | PASS |
| P10 (CLAUSE vs INTERNAL, pairwise) | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | **ÃŽâ€=55.0** | PASS |
| **P11** (`.\|.` internal to URL path, pos25/26) | **OTHER** | **Yes** | No | **INTERNAL** | 0.0 | -30.0 | -20.0 | **-50.0** | **PASS Ã¢â‚¬â€ corrected** (was `UPSTREAM ISSUE`, leaked `SENTENCE_FINAL`, score `+30.0`, pre-correction) |
| P12 (Atomic+INTERNAL) | N/A Ã¢â‚¬â€ unreachable | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | **CASE ISSUE Ã¢â‚¬â€ unchanged** |
| P13 (Technical vs Atomic, pairwise) | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | Ã¢â‚¬â€ | equal (-30.0 = -30.0) | PASS |

### 5.1 P02/P03 labeling note (carried over, unaffected by this round)

As documented in the original Protection Calibration Round 1 report: the matrix's
P02 narrative example (`1,000`) is actually `atomic/numeric` per Phase 1's real span
typing, and P03's example (`v1.2.3`) contains a position (pos7) that is purely
`technical/version` Ã¢â‚¬â€ the two labels are effectively swapped relative to the matrix's
own descriptions. This is a pre-existing, unrelated labeling/naming issue in the
matrix's narrative text, not a numeric defect, and is untouched by the Round B
correction. It is repeated here only for completeness, not as a new finding.

---

## 6. P11 Detailed Verification

Probe: `"Ã¨Â«â€¹Ã¥ÂÆ’Ã¨â‚¬Æ’ http://example.com/a...b Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã©Â ÂÃ©ÂÂ¢Ã£â‚¬â€š"` (`P11_probe_url_ellipsis`).

Actual raw output for the two candidates inside the literal `...` path segment:

```
pos=25  L='.' R='.'  LC=punctuation RC=punctuation  seq_state=internal
        sf_evidence=False
        containing=['technical/url', 'punctuation_sequence/ellipsis']
        class=other
        base=0.0  trans=0.0(None)  ws=0.0
        tech=True  atomic=False  protection=-30.0
        internal=True  seqpen=-20.0
        SCORE=-50.0

pos=26  L='.' R='.'  LC=punctuation RC=punctuation  seq_state=internal
        sf_evidence=False
        containing=['technical/url', 'punctuation_sequence/ellipsis']
        class=other
        base=0.0  trans=0.0(None)  ws=0.0
        tech=True  atomic=False  protection=-30.0
        internal=True  seqpen=-20.0
        SCORE=-50.0
```

Confirmed exactly as required:

| Field | Value |
|---|---|
| `BoundaryClass` | `OTHER` |
| `Technical` | `True` |
| `INTERNAL` (`punctuation_sequence_state`) | `internal` |
| `contains_sentence_final_punctuation` (sentence-final evidence) | `False` |
| Final Score | `-50.0` (`0.0` base `- 30.0` protection `- 20.0` sequence) |

This is real pipeline evidence (`analyze_text_structure` Ã¢â€ â€™ `observe_boundaries` Ã¢â€ â€™
`classify_boundary` Ã¢â€ â€™ the calibration script's own scoring function), not a synthetic
candidate. Both positions inside the run report identically, as expected for a
multi-character internal run.

For reference, position 19 (`.|c` inside `example.com`, previously also leaked as
`SENTENCE_FINAL`) is likewise now `OTHER` with `Technical=True` and no `INTERNAL`
evidence (`seq_state=none`, since it is not inside any `punctuation_sequence` span) Ã¢â‚¬â€
consistent, not part of the P11 target combination itself, but further confirmation
the correction applied uniformly within this one probe text.

---

## 7. P12 Reachability Verification

All four existing reachability probes in the script were re-run unmodified:

- `P12_probe_number_ellipsis` (`Ã¦â€¢Â¸Ã¥â‚¬Â¼Ã¦ËœÂ¯ 100...200 Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã§Â¯â€žÃ¥Å“ÂÃ£â‚¬â€š`)
- `P12_probe_decimal_then_ellipsis_touching` (`Ã¦â€¢Â¸Ã¥â‚¬Â¼Ã¦ËœÂ¯ 3.14......Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã£â‚¬â€š`)
- `P12_probe_malformed_decimal_double_dot` (`Ã¦â€¢Â¸Ã¥â‚¬Â¼Ã¦ËœÂ¯ 3..14 Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã£â‚¬â€š`)
- `P12_probe_malformed_decimal_quad_dot` (`Ã¦â€¢Â¸Ã¥â‚¬Â¼Ã¦ËœÂ¯ 3....14 Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã£â‚¬â€š`)

In every one of the four constructions, every candidate's `containing` list shows
either `['atomic/numeric']` alone or `['punctuation_sequence/ellipsis']` alone Ã¢â‚¬â€
**never both together**. Example (`P12_probe_number_ellipsis`):

```
pos=6  containing=['atomic/numeric']              (end of the '100' digit run)
pos=7  containing=[]                               (the '0|.' boundary - genuinely uncovered)
pos=8  containing=['punctuation_sequence/ellipsis'] internal=True  seqpen=-20.0
pos=9  containing=['punctuation_sequence/ellipsis'] internal=True  seqpen=-20.0
pos=10 containing=[]  class=ellipsis                (end of the '...' run)
pos=11 containing=['atomic/numeric']              (start of the '200' digit run)
```

**P12 remains `CASE ISSUE Ã¢â‚¬â€ unchanged.`** The structural reason is exactly as
previously documented and is unaffected by the Round B correction: Phase 1's
`_NUMERIC_RE` (atomic/numeric detector) and the punctuation-sequence run detector
partition the source text at the digit/non-digit character-class boundary Ã¢â‚¬â€ an
`atomic/numeric` span and a `punctuation_sequence` span are always adjacent
(`atomic.end == punctuation_sequence.start` or vice versa), never overlapping, in
every construction tested, including the two malformed-decimal probes specifically
designed to stress this boundary. The Round B correction only changed how
`contains_sentence_final_punctuation` is computed for characters already covered by
an existing span Ã¢â‚¬â€ it does not and cannot change which spans Phase 1 produces or
where they are positioned, so it was never expected to affect P12's reachability, and
it did not.

---

## 8. Drift Analysis

Full output diff of this round's raw dump against the last pre-correction Protection
Calibration raw dump (captured after Round C, before Round B's fix) shows **exactly
seven** changed blocks, all involving positions where the character immediately to
the left is an ASCII `.` interior to a `technical`, `atomic`, or `punctuation_sequence`
span Ã¢â‚¬â€ precisely the class of leak Round A/B identified and targeted. No other line
in the entire 258-line output differs.

| Case | Classification |
|---|---|
| P01 | **UNCHANGED** |
| P02 | **UNCHANGED** |
| P03 | **UNCHANGED** |
| P04 | **UNCHANGED** |
| P05/P14 | **UNCHANGED** |
| P06/P15 | **UNCHANGED** |
| P07 (pairwise, derived from P06/P02) | **UNCHANGED** |
| P08 | **UNCHANGED** |
| P09 (pairwise, derived from P05/P08) | **UNCHANGED** |
| P10 (pairwise, derived from P06/P08) | **UNCHANGED** |
| **P11** | **EXPECTED CHANGE** Ã¢â‚¬â€ `SENTENCE_FINAL`/`+30.0` (leaked) Ã¢â€ â€™ `OTHER`/`-50.0` (corrected); this was the entire purpose of Round B |
| P12 | **NOT APPLICABLE / CASE ISSUE unchanged** Ã¢â‚¬â€ remained unreachable before and after; no candidate exists to have drifted |
| P13 (pairwise, derived from P02/P03) | **UNCHANGED** |

Additional leaked positions corrected in this same raw output, outside the twelve
positions the report's named P-cases directly cite (all within the P03_P04 sentence
and the four P11/P12 diagnostic probe texts Ã¢â‚¬â€ `pos=9`/`pos=11` in `P03_P04`,
`pos=19` in `P11_probe_url_ellipsis`, and internal ellipsis-run positions in
`P11_probe_version_ellipsis`/`P12_probe_decimal_then_ellipsis_touching`/
`P12_probe_malformed_decimal_double_dot`/`P12_probe_malformed_decimal_quad_dot`):
all of these are further leak-fix instances of the same single root cause, not new
or unrelated drift, and none of them is the specific real candidate any P-numbered
case's reported result relies on (confirmed by cross-referencing every position
against Ã‚Â§5 above and the prior report's own candidate citations).

**Conclusion: the only case-level status that changed is P11, exactly as the Round B
correction intended.** No unexpected regression was found anywhere in P01Ã¢â‚¬â€œP10 or
P13Ã¢â‚¬â€œP15.

---

## 9. Protection Numeric Assessment

Values remain exactly as provisioned Ã¢â‚¬â€ **no change made or proposed in this round**:

| Rule | Status | Basis |
|---|---|---|
| `Technical = -30` | **Supported** | P02 (technical-adjacent, mislabeled but numerically valid), P03 (clean technical-only, `-30.0` exact), P04 (technical+atomic strongest-only, `-30.0` exact, matches P02/P03), P05/P14 (Transition beats Technical by exactly `45.0`), P06/P15 (CLAUSE beats Technical by exactly `65.0`), P11 (Technical+INTERNAL now cleanly observable at `-50.0` exact, on real, non-leaked evidence), P13 (Technical == Atomic exactly, symmetry holds) |
| `Atomic = -30` | **Supported** | P02 (clean atomic-only, `-30.0` exact), P07 (CLAUSE beats Atomic by exactly `65.0`), P13 (symmetry with Technical holds exactly) |
| `INTERNAL = -20` | **Supported** for its independent effect (P08 `-20.0` exact; P09 ÃŽâ€35 exact; P10 ÃŽâ€55 exact) and now **additionally supported** for its Technical-combined effect (P11: `-30.0 - 20.0 = -50.0` exact, confirming additive stacking with the protection penalty as the matrix's Ã‚Â§4.2 specifies). **Blocked by unreachable case** specifically for its Atomic-combined effect (P12 remains `CASE ISSUE` Ã¢â‚¬â€ no real candidate exists to test `Atomic + INTERNAL` directly; this is an architecture/reachability gap, not evidence against the `-20` value itself) |

No value was changed, increased, decreased, or otherwise tuned during this round.

---

## 10. Numeric Calibration Readiness Decision

Evaluated against the six stated criteria:

| # | Criterion | Result |
|---|---|---|
| A | P11 is now correctly observable | **Met** Ã¢â‚¬â€ Ã‚Â§6 |
| B | P11 produces `OTHER + Technical + INTERNAL = 0 - 30 - 20 = -50` | **Met** Ã¢â‚¬â€ exact, Ã‚Â§6 |
| C | No unexpected regression in P01Ã¢â‚¬â€œP10 or P13Ã¢â‚¬â€œP15 | **Met** Ã¢â‚¬â€ Ã‚Â§8, full-output diff confirms zero unrelated drift |
| D | P12 remains explicitly documented as an independent reachability/architecture issue | **Met** Ã¢â‚¬â€ Ã‚Â§7 |
| E | No numeric weight changes were required | **Met** Ã¢â‚¬â€ none made |
| F | Evidence is based on real pipeline behavior wherever the matrix requires it | **Met** Ã¢â‚¬â€ no synthetic candidates used for P11 or P12; both driven by the real Phase 1Ã¢â€ â€™2AÃ¢â€ â€™2BÃ¢â€ â€™calibration pipeline |

**All six criteria hold.**

### READY FOR NUMERIC CALIBRATION

Protection Calibration (Technical/Atomic/INTERNAL) is behaviorally stable: every
reachable case (P01Ã¢â‚¬â€œP11, P13Ã¢â‚¬â€œP15) passes exactly against its expected relation, the
Round B correction changed only the one case it was designed to change, and the one
remaining unreachable case (P12) is a well-understood, independently-documented
architecture gap rather than an open numeric question.

This readiness statement is scoped specifically to the **Protection family**
(Technical/Atomic/INTERNAL), matching this matrix's own stated scope. It does **not**
by itself certify `SENTENCE_FINAL`/`ELLIPSIS`/`CLAUSE`/`Transition`/`Whitespace`
calibration (out of this matrix's scope Ã¢â‚¬â€ see Ã‚Â§3.1's flagged discrepancy for why that
matters for whichever numeric baseline a future round adopts).

---

## 11. Remaining Issues

1. **Numeric baseline discrepancy (new finding, this round Ã¢â‚¬â€ see Ã‚Â§3.1).** This
   round's own instructions state `CLAUSE=+20`/`ELLIPSIS=+40`, while every existing
   matrix, script, and prior report uses `CLAUSE=+35`/`ELLIPSIS=+65`. This was not
   resolved or silently chosen either way in this document; it must be explicitly
   reconciled (which number set is actually authoritative) before a Numeric
   Calibration round begins, since that round will need one unambiguous baseline.
2. **P02/P03 label swap (carried over, unrelated to this round).** The matrix's
   narrative descriptions for P02 ("Technical OTHER") and P03 ("Atomic OTHER") do not
   match which evidence type the real pipeline actually assigns to each example text
   Ã¢â‚¬â€ see Ã‚Â§5.1. Does not affect either case's own numeric PASS status.
3. **P12 remains unreachable.** `Atomic + INTERNAL` has no real-pipeline
   representation given Phase 1's current numeric/punctuation-sequence detector
   boundaries. This is an architecture question for a future round (would require
   either a new Phase 1 detector shape or accepting the combination as permanently
   untestable), not something this round attempted or should attempt to resolve.
4. **Residual, explicitly out-of-scope Phase 1 gaps** (`1.000.000`, bare
   `example.com`) noted in the Round A/B documents remain unaddressed, as intended Ã¢â‚¬â€
   not part of Protection Calibration's scope.

---

## 12. Exact Next Recommended Step

Before starting a Numeric Calibration round: resolve the Ã‚Â§3.1/Ã‚Â§11.1 baseline
discrepancy (confirm whether `CLAUSE=35`/`ELLIPSIS=65` or `CLAUSE=20`/`ELLIPSIS=40`
is the number set to carry forward Ã¢â‚¬â€ or whether this represents an intentional,
not-yet-documented revision that needs its own matrix update). Once that is settled,
Protection Calibration itself is ready to be treated as a stable input to a "Phase 2C
Numeric Strategy v1" design decision, per criteria AÃ¢â‚¬â€œF in Ã‚Â§10.

---

## Files

**Created:** `docs/PHASE_2C_PROTECTION_POST_CORRECTION_VERIFICATION.md` (this
document) Ã¢â‚¬â€ the sole new file produced this round.

**Confirmed unmodified:** `src/text_structure.py`, `src/boundary_observation.py`,
`src/boundary_classification.py`, `src/subtitle_segmenter.py`, every file under
`tests/`, `scripts/phase2c/calibrate_protection_round1.py`,
`scripts/phase2c/calibrate_numeric_round1.py`, `scripts/phase2c/calibrate_numeric_round2.py`,
`docs/PHASE_2C_CALIBRATION_MATRIX.md`, `docs/phase2c/calibration/reports/PHASE_2C_NUMERIC_CALIBRATION_ROUND1_REPORT.md`,
`docs/phase2c/calibration/reports/PHASE_2C_NUMERIC_CALIBRATION_ROUND2_REPORT.md`,
`docs/phase2c/calibration/matrices/PHASE_2C_PROTECTION_CALIBRATION_MATRIX.md`,
`docs/phase2c/calibration/reports/PHASE_2C_PROTECTION_CALIBRATION_ROUND1_REPORT.md`,
`docs/phase2c/decisions/PHASE_2C_ASCII_PERIOD_UPSTREAM_CORRECTION_DECISION.md`.

**Test results:** `pytest tests/ -q` Ã¢â€ â€™ 397 passed, 2 warnings, 15 subtests passed
(21.42s). `python -m unittest discover -s tests -v` Ã¢â€ â€™ Ran 397 tests, OK (19.381s). No
regressions; nothing modified to produce this result.
