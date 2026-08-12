# Phase 2C Base Classification Calibration Ã¢â‚¬â€ Round 1 Report

## 1. Executive Summary

All 12 cases designed in `docs/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_MATRIX.md` (BC-01 through BC-12) were executed against the real, unmodified pipeline (`src/text_structure.py` Ã¢â€ â€™ `src/boundary_observation.py` Ã¢â€ â€™ `src/boundary_classification.py`, scored via the existing `scripts/calibrate_phase2c_protection_round1.py` infrastructure, reused unmodified). Every targeted `BoundaryClass` in every case was successfully produced by the real pipeline Ã¢â‚¬â€ **zero `CASE ISSUE` outcomes** across all 12 cases, including the highest-risk case, BC-09, which cleanly produced all four base classes (`OTHER`, `CLAUSE`, `ELLIPSIS`, `SENTENCE_FINAL`) in a single realistic paragraph.

For the three pairwise margins under evaluation:

- **CLAUSE vs OTHER (margin 35)** Ã¢â‚¬â€ `KEEP`
- **ELLIPSIS vs CLAUSE (margin 30)** Ã¢â‚¬â€ `KEEP`
- **SENTENCE_FINAL vs ELLIPSIS (margin 15)** Ã¢â‚¬â€ `KEEP`

No numeric replacement values are proposed anywhere in this report. All three verdicts are supported by real-pipeline evidence showing clean, order-independent separation with no reversal and no incidental modifier materially closing any gap. The narrowest margin (SENTENCE_FINAL vs ELLIPSIS, +15) is flagged in Ã‚Â§10 as warranting continued attention in any future dedicated round, since this round's evidence for it is limited to two natural-order cases.

The only incidental (out-of-scope) evidence observed anywhere in the 12 cases was `INTERNAL` (Ã¢Ë†â€™20.0), appearing at ellipsis-run interior positions in 9 of the 12 cases. No Technical, Atomic, transition, or whitespace evidence appeared incidentally in any case. See Ã‚Â§8.

## 2. Scope and Baseline

This round executes the calibration matrix designed in the prior round and reports findings only. It does not modify `src/*`, `tests/*`, existing `scripts/*`, existing `docs/*` (including the Baseline Decision and the Matrix itself), and does not implement any Phase 2C production scoring module.

Authoritative baseline referenced (from `docs/phase2c/decisions/PHASE_2C_NUMERIC_BASELINE_DECISION.md`, Numeric Baseline v0.1), base classification values only:

| Class | Base score |
|---|---|
| SENTENCE_FINAL | +80.0 |
| ELLIPSIS | +65.0 |
| CLAUSE | +35.0 |
| OTHER | 0.0 |

Margins under evaluation this round: CLAUSE Ã¢Ë†â€™ OTHER = 35, ELLIPSIS Ã¢Ë†â€™ CLAUSE = 30, SENTENCE_FINAL Ã¢Ë†â€™ ELLIPSIS = 15. These are provisional baseline values (not yet the subject of a dedicated calibration round prior to this one) Ã¢â‚¬â€ this round is that dedicated evaluation for base classification dominance specifically, not a re-proof of the already-established ordering SENTENCE_FINAL > ELLIPSIS > CLAUSE > OTHER.

Out-of-scope factors (referenced only when they appear incidentally, never used as grounds to change a base classification value): CJKÃ¢â€ â€™LATIN +15, LATINÃ¢â€ â€™CJK +15, Whitespace +10, Technical Ã¢Ë†â€™30, Atomic Ã¢Ë†â€™30, INTERNAL Ã¢Ë†â€™20.

## 3. Execution Method

- The 12 input texts were extracted programmatically (regex) directly from the `| Input text | \`...\` |` rows of `docs/phase2c/calibration/matrices/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_MATRIX.md`, to guarantee verbatim accuracy against the designed matrix rather than retyping them.
- Execution reused the existing `scripts/calibrate_phase2c_protection_round1.py` module unmodified: `calibration_score()` and `dump()` were imported (`sys.path.insert(0, 'scripts'); import calibrate_phase2c_protection_round1 as cal`) and called once per case (`cal.dump(text, f'BC-{i:02d}')`). No new script file was created, per this round's script policy Ã¢â‚¬â€ the existing infrastructure was sufficient to execute every case without modification.
- All 12 cases' full per-position output was redirected to a temporary file (`/tmp/calibration_base_classification_round1_raw.txt`, not part of the repository) and reviewed in full for every case.

## 4. Case Execution Results

Each case reports position (1-indexed, matching `observe_boundaries`'s candidate positions), left/right characters, `BoundaryClass`, base score, and any incidental modifier. All scores below are the real, unmodified pipeline's output.

### 4.1 BC-01

Text: `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¦Å â€¢Ã¥Â½Â±Ã§â€°â€¡Ã¤Â»â€¹Ã§Â´Â¹Ã§Â³Â»Ã§ÂµÂ±Ã¦Å¾Â¶Ã¦Â§â€¹Ã£â‚¬â€šÃ©Â¦â€“Ã¥â€¦Ë†Ã¯Â¼Å’Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Å“â€¹Ã¦â€¢Â´Ã©Â«â€Ã¨Â¨Â­Ã¨Â¨Ë†Ã£â‚¬â€š` (len=23)

- Target OTHER: many interior CJKÃ¢â‚¬â€œCJK positions score `OTHER`/0.0 (pos 1Ã¢â‚¬â€œ11, 13Ã¢â‚¬â€œ14, 16Ã¢â‚¬â€œ22 excluding the punctuation position). Per the round's BC-01/BC-02 correction (do not aggregate; select one deterministic candidate), the first such candidate by pipeline position order is used: **pos 1** (L=`Ã©â‚¬â„¢`, R=`Ã¥â‚¬â€¹`, `OTHER`, 0.0).
- Target CLAUSE: **pos 15** (L=`Ã¯Â¼Å’`, R=`Ã¦Ë†â€˜`, `CLAUSE`, 35.0).
- Additional, non-targeted candidate present in this text: **pos 12** (L=`Ã£â‚¬â€š`, R=`Ã©Â¦â€“`, `SENTENCE_FINAL`, 80.0, confirmed `sf_evidence=True`, non-string-final). Recorded for completeness; not part of the CLAUSE-vs-OTHER comparison targeted by this case.

Status: `REAL-PIPELINE`. Both targeted classes reachable, clean (no incidental modifier on either targeted candidate).

### 4.2 BC-02

Text: `Ã©Â¦â€“Ã¥â€¦Ë†Ã¯Â¼Å’Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Å“â€¹Ã¦â€¢Â´Ã©Â«â€Ã¨Â¨Â­Ã¨Â¨Ë†Ã£â‚¬â€šÃ©â‚¬â„¢Ã¥â‚¬â€¹Ã¦Å â€¢Ã¥Â½Â±Ã§â€°â€¡Ã¤Â»â€¹Ã§Â´Â¹Ã§Â³Â»Ã§ÂµÂ±Ã¦Å¾Â¶Ã¦Â§â€¹Ã£â‚¬â€š` (len=23) Ã¢â‚¬â€ same sentences as BC-01, opposite order.

- Target OTHER: first deterministic candidate is **pos 1** (L=`Ã©Â¦â€“`, R=`Ã¥â€¦Ë†`, `OTHER`, 0.0).
- Target CLAUSE: **pos 3** (L=`Ã¯Â¼Å’`, R=`Ã¦Ë†â€˜`, `CLAUSE`, 35.0).
- Additional, non-targeted candidate: **pos 11** (L=`Ã£â‚¬â€š`, R=`Ã©â‚¬â„¢`, `SENTENCE_FINAL`, 80.0, non-string-final). Recorded for completeness.

Status: `REAL-PIPELINE`. Both targeted classes reachable, clean.

### 4.3 BC-03

Text: `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥â€¢ÂÃ©Â¡Å’Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Â¨ÂÃ¥Â¾Å’Ã¨ÂªÂªÃ¦ËœÅ½Ã¯Â¼Å’Ã§ÂÂ¾Ã¥Å“Â¨Ã¥â€¦Ë†Ã§Å“â€¹Ã©â€¡ÂÃ©Â»Å¾Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¥Â¥Â½Ã¯Â¼Å’Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã©â€“â€¹Ã¥Â§â€¹Ã£â‚¬â€š` (len=26)

- Target CLAUSE: **pos 11** (L=`Ã¯Â¼Å’`, R=`Ã§ÂÂ¾`, `CLAUSE`, 35.0).
- Target ELLIPSIS: **pos 19** (L=`Ã¢â‚¬Â¦`, R=`Ã¥Â¥Â½`, `ELLIPSIS`, `seq_state=end`, 65.0, confirmed non-string-final).
- Incidental: **pos 18** (`Ã¢â‚¬Â¦`/`Ã¢â‚¬Â¦`, `seq_state=internal`, `class=other`, base 0.0, `internal=True`, `seqpen=-20.0`, `SCORE=-20.0`) Ã¢â‚¬â€ the ellipsis-run interior position, out of scope for base-classification dominance, recorded per instruction not to silently drop it. Does not touch either targeted candidate.
- Additional, non-targeted candidate: a second **CLAUSE** at pos 21 (35.0).

Status: `REAL-PIPELINE`. Both targeted classes reachable, clean (targeted candidates unaffected by the incidental `INTERNAL` position).

### 4.4 BC-04

Text: `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã©Æ’Â¨Ã¥Ë†â€ Ã¦Â¯â€Ã¨Â¼Æ’Ã¨Â¤â€¡Ã©â€ºÅ“Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¥â€¦Ë†Ã¨Â·Â³Ã©ÂÅ½Ã¯Â¼Å’Ã¤Â¹â€¹Ã¥Â¾Å’Ã¥â€ ÂÃ¨Â¨Å½Ã¨Â«â€“Ã£â‚¬â€š` (len=22) Ã¢â‚¬â€ same sentences as BC-03, opposite order.

- Target ELLIPSIS: **pos 10** (L=`Ã¢â‚¬Â¦`, R=`Ã¦Ë†â€˜`, `ELLIPSIS`, `seq_state=end`, 65.0, non-string-final).
- Target CLAUSE: **pos 16** (L=`Ã¯Â¼Å’`, R=`Ã¤Â¹â€¹`, `CLAUSE`, 35.0).
- Incidental: **pos 9** (`internal`, `SCORE=-20.0`), same pattern as BC-03.

Status: `REAL-PIPELINE`. Both targeted classes reachable, clean.

### 4.5 BC-05

Text: `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥â€¢ÂÃ©Â¡Å’Ã§Â¨ÂÃ¥Â¾Å’Ã¥â€ ÂÃ¨Â«â€¡Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã§ÂÂ¾Ã¥Å“Â¨Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Å“â€¹Ã¤Â¸â€¹Ã¤Â¸â‚¬Ã©Â ÂÃ£â‚¬â€šÃ¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¤Â»â€¹Ã§Â´Â¹Ã©â€¡ÂÃ©Â»Å¾Ã£â‚¬â€š` (len=27)

- Target ELLIPSIS: **pos 10** (L=`Ã¢â‚¬Â¦`, R=`Ã§ÂÂ¾`, `ELLIPSIS`, `seq_state=end`, 65.0).
- Target SENTENCE_FINAL: **pos 19** (L=`Ã£â‚¬â€š`, R=`Ã¦Å½Â¥`, `SENTENCE_FINAL`, 80.0, confirmed `sf_evidence=True`, non-string-final Ã¢â‚¬â€ reachable exactly as the matrix designed, since the trailing `Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¤Â»â€¹Ã§Â´Â¹Ã©â€¡ÂÃ©Â»Å¾Ã£â‚¬â€š` sentence gives the first `Ã£â‚¬â€š` trailing content).
- Incidental: **pos 9** (`internal`, `SCORE=-20.0`).

Status: `REAL-PIPELINE`. Both targeted classes reachable, clean.

### 4.6 BC-06

Text: `Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¥â€¦Ë†Ã§Å“â€¹Ã¤Â¸â€¹Ã¤Â¸â‚¬Ã©Â ÂÃ£â‚¬â€šÃ©â‚¬â„¢Ã¥â‚¬â€¹Ã¥â€¢ÂÃ©Â¡Å’Ã§Â¨ÂÃ¥Â¾Å’Ã¥â€ ÂÃ¨Â«â€¡Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¥Â¥Â½Ã¯Â¼Å’Ã©â€“â€¹Ã¥Â§â€¹Ã¥ÂÂ§Ã£â‚¬â€š` (len=24) Ã¢â‚¬â€ same sentences as BC-05, opposite order.

- Target SENTENCE_FINAL: **pos 8** (L=`Ã£â‚¬â€š`, R=`Ã©â‚¬â„¢`, `SENTENCE_FINAL`, 80.0, non-string-final).
- Target ELLIPSIS: **pos 18** (L=`Ã¢â‚¬Â¦`, R=`Ã¥Â¥Â½`, `ELLIPSIS`, `seq_state=end`, 65.0).
- Incidental: **pos 17** (`internal`, `SCORE=-20.0`).
- Additional, non-targeted candidate: **CLAUSE** at pos 20 (35.0).

Status: `REAL-PIPELINE`. Both targeted classes reachable, clean.

### 4.7 BC-07

Text: `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥Å Å¸Ã¨Æ’Â½Ã©â€šâ€žÃ¥Å“Â¨Ã©â€“â€¹Ã§â„¢Â¼Ã¤Â¸Â­Ã¯Â¼Å’Ã§Â´Â°Ã§Â¯â‚¬Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Â¨ÂÃ¥Â¾Å’Ã¨Â£Å“Ã¥â€¦â€¦Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¥â€¦Ë†Ã§Å“â€¹Ã§â€ºÂ®Ã¥â€°ÂÃ§Å¡â€žÃ©â‚¬Â²Ã¥ÂºÂ¦` (len=27) Ã¢â‚¬â€ deliberately no `Ã£â‚¬â€š`/`Ã¯Â¼Â`/`Ã¯Â¼Å¸` anywhere.

- Target CLAUSE: **pos 10** (L=`Ã¯Â¼Å’`, R=`Ã§Â´Â°`, `CLAUSE`, 35.0).
- Target ELLIPSIS: **pos 20** (L=`Ã¢â‚¬Â¦`, R=`Ã¥â€¦Ë†`, `ELLIPSIS`, `seq_state=end`, 65.0).
- Target OTHER: interior CJKÃ¢â‚¬â€œCJK positions throughout (e.g. pos 1, 0.0).
- Incidental: **pos 19** (`internal`, `SCORE=-20.0`).
- No `SENTENCE_FINAL` candidate present anywhere in this text Ã¢â‚¬â€ confirmed, and exactly as designed (the case deliberately contains no sentence-final punctuation), successfully isolating the OTHER/CLAUSE/ELLIPSIS three-way portion of the hierarchy from SENTENCE_FINAL.

Status: `REAL-PIPELINE`. All three targeted classes reachable in one paragraph, clean.

### 4.8 BC-08

Text: `Ã©â‚¬â„¢Ã©Æ’Â¨Ã¥Ë†â€ Ã©â€šÂÃ¨Â¼Â¯Ã¦Â¯â€Ã¨Â¼Æ’Ã¨Â¤â€¡Ã©â€ºÅ“Ã¯Â¼Å’Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Â¨ÂÃ¥Â¾Å’Ã¨ÂªÂªÃ¦ËœÅ½Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã§ÂÂ¾Ã¥Å“Â¨Ã§Å“â€¹Ã¤Â¸â€¹Ã¤Â¸â‚¬Ã¥â‚¬â€¹Ã¥Å Å¸Ã¨Æ’Â½Ã£â‚¬â€šÃ¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¦Å“Æ’Ã¦Å“â€°Ã§Â¯â€žÃ¤Â¾â€¹Ã£â‚¬â€š` (len=35)

- Target CLAUSE: **pos 10** (35.0).
- Target ELLIPSIS: **pos 18** (`seq_state=end`, 65.0).
- Target SENTENCE_FINAL: **pos 27** (80.0, non-string-final).
- Incidental: **pos 17** (`internal`, `SCORE=-20.0`).

Status: `REAL-PIPELINE`. All three targeted classes (CLAUSE, ELLIPSIS, SENTENCE_FINAL Ã¢â‚¬â€ the upper three-way) reachable in one paragraph, clean.

### 4.9 BC-09

Text: `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥Å Å¸Ã¨Æ’Â½Ã©â€šâ€žÃ¥Å“Â¨Ã©â€“â€¹Ã§â„¢Â¼Ã¤Â¸Â­Ã¯Â¼Å’Ã§Â´Â°Ã§Â¯â‚¬Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Â¨ÂÃ¥Â¾Å’Ã¨Â£Å“Ã¥â€¦â€¦Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã§â€ºÂ®Ã¥â€°ÂÃ¥â€¦Ë†Ã§Å“â€¹Ã¦â€¢Â´Ã©Â«â€Ã¤Â»â€¹Ã©ÂÂ¢Ã£â‚¬â€šÃ¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¦Å“Æ’Ã¥Â±â€¢Ã§Â¤ÂºÃ§Â¯â€žÃ¤Â¾â€¹Ã£â‚¬â€š` (len=38)

All four base classes present and clean in a single paragraph:

- **OTHER**: pos 1 (L=`Ã©â‚¬â„¢`, R=`Ã¥â‚¬â€¹`, 0.0), and throughout most interior CJKÃ¢â‚¬â€œCJK positions.
- **CLAUSE**: pos 10 (L=`Ã¯Â¼Å’`, R=`Ã§Â´Â°`, 35.0).
- **ELLIPSIS**: pos 20 (L=`Ã¢â‚¬Â¦`, R=`Ã§â€ºÂ®`, `seq_state=end`, 65.0).
- **SENTENCE_FINAL**: pos 29 (L=`Ã£â‚¬â€š`, R=`Ã¦Å½Â¥`, 80.0, confirmed non-string-final).
- Incidental: pos 19 (`internal`, `SCORE=-20.0`).

Status: `REAL-PIPELINE`. This is the primary case the matrix was built to support: the complete four-class hierarchy, and all three margins simultaneously, are well-formed in one coherent, realistic paragraph, with zero `CASE ISSUE` and zero incidental contamination of any target candidate.

### 4.10 BC-10 (natural, ANALYSIS ONLY)

Text: `Ã©â‚¬â„¢Ã¤Â¸â‚¬Ã©Â ÂÃ¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â»â€¹Ã§Â´Â¹Ã§â€Â¢Ã¥â€œÂÃ¨Â¦ÂÃ¥Å Æ’Ã¯Â¼Å’Ã¥â€¦Ë†Ã¨Â¬â€ºÃ§Å¸Â­Ã¦Å“Å¸Ã§â€ºÂ®Ã¦Â¨â„¢Ã£â‚¬â€šÃ©â€¢Â·Ã¦Å“Å¸Ã¦â€“Â¹Ã¥Ââ€˜Ã©â€šâ€žÃ¥Å“Â¨Ã¨Â¨Å½Ã¨Â«â€“Ã¤Â¸Â­Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã§Â´Â°Ã§Â¯â‚¬Ã¤Â¹â€¹Ã¥Â¾Å’Ã¦Å“Æ’Ã¥â€ ÂÃ¦â€ºÂ´Ã¦â€“Â°Ã£â‚¬â€šÃ©â‚¬â„¢Ã¦ËœÂ¯Ã§â€ºÂ®Ã¥â€°ÂÃ§Å¡â€žÃ©â€¡ÂÃ©Â»Å¾Ã£â‚¬â€š` (len=47)

Full candidate distribution recorded per the case's evidence requirement:

- CLAUSE: pos 12 (35.0)
- SENTENCE_FINAL: pos 19 (80.0, non-string-final)
- Incidental: pos 29 (`internal`, Ã¢Ë†â€™20.0)
- ELLIPSIS: pos 30 (`seq_state=end`, 65.0)
- SENTENCE_FINAL: pos 39 (80.0, non-string-final; second occurrence)
- Everything else: OTHER (0.0)

The final `Ã£â‚¬â€š` at the absolute end of the string (after `Ã©â€¡ÂÃ©Â»Å¾`) produces no candidate at all Ã¢â‚¬â€ this is the known Phase 1/2A string-final representation gap, expected and not a problem here since this trailing mark was never a targeted candidate.

Per this round's instruction, no KEEP/INCREASE/DECREASE verdict is forced from this single natural paragraph. Qualitative observation: the roadmap-style note ("statement Ã¢â€ â€™ clause-qualified statement Ã¢â€ â€™ trailing-off remark Ã¢â€ â€™ statement") produces a score distribution matching the intended ordering at every transition, with no unexpected class assignment anywhere in the text.

Status: `ANALYSIS ONLY`.

### 4.11 BC-11 (natural, ANALYSIS ONLY Ã¢â‚¬â€ must not be used to change CLAUSE or introduce positional weighting)

Text: `Ã¤Â»Å Ã¥Â¤Â©Ã¨Â­Â°Ã§Â¨â€¹Ã¦Å“â€°Ã¤Â¸â€°Ã¥â‚¬â€¹Ã©â€¡ÂÃ©Â»Å¾Ã¯Â¼Å’Ã§Â¬Â¬Ã¤Â¸â‚¬Ã¥â‚¬â€¹Ã¦ËœÂ¯Ã©â‚¬Â²Ã¥ÂºÂ¦Ã¥â€ºÅ¾Ã©Â¡Â§Ã¯Â¼Å’Ã§Â¬Â¬Ã¤ÂºÅ’Ã¥â‚¬â€¹Ã¦ËœÂ¯Ã©Â¢Â¨Ã©Å¡ÂªÃ¨Â¨Å½Ã¨Â«â€“Ã¯Â¼Ë†Ã©â‚¬â„¢Ã©Æ’Â¨Ã¥Ë†â€ Ã¦Â¯â€Ã¨Â¼Æ’Ã©â€¡ÂÃ¨Â¦ÂÃ¯Â¼â€°Ã¯Â¼Å’Ã§Â¬Â¬Ã¤Â¸â€°Ã¥â‚¬â€¹Ã¦â€°ÂÃ¦ËœÂ¯Ã¤Â¸â€¹Ã¤Â¸â‚¬Ã¦Â­Â¥Ã¨Â¦ÂÃ¥Å Æ’Ã£â‚¬â€šÃ¦Å“Æ’Ã¨Â­Â°Ã¥Â¤Â§Ã¦Â¦â€šÃ©â€“â€¹Ã¤Â¸â‚¬Ã¥Â°ÂÃ¦â„¢â€šÃ£â‚¬â€š` (len=57)

Recorded observation only, per the round's explicit instruction that this case not be used to change `CLAUSE`, introduce positional weighting, or create a new classification/scoring factor:

- Three separate CLAUSE candidates, all scoring exactly 35.0: pos 10 (L=`Ã¯Â¼Å’`, R=`Ã§Â¬Â¬`), pos 19 (L=`Ã¯Â¼Å’`, R=`Ã§Â¬Â¬`), pos 37 (L=`Ã¯Â¼Å’`, R=`Ã§Â¬Â¬`, immediately following the parenthetical's closing `Ã¯Â¼â€°`).
- The parenthetical `Ã¯Â¼Ë†Ã©â‚¬â„¢Ã©Æ’Â¨Ã¥Ë†â€ Ã¦Â¯â€Ã¨Â¼Æ’Ã©â€¡ÂÃ¨Â¦ÂÃ¯Â¼â€°` spans pos 28Ã¢â‚¬â€œ35 with `containing=['paired_delimiter/parenthetical']` throughout. This span does not block or otherwise affect the CLAUSE candidate immediately following it at pos 37 Ã¢â‚¬â€ consistent with Phase 2B's existing design, where only `technical`/`atomic` spans (not `paired_delimiter`) suppress base classification.
- SENTENCE_FINAL: pos 48 (80.0, confirmed non-string-final).

Observation (recorded, not acted on): this text confirms the matrix's own anticipated finding Ã¢â‚¬â€ several CLAUSE candidates of equal nominal weight (35.0 each) can coexist in one paragraph regardless of their position within an enumeration or their adjacency to a parenthetical aside. Whether a flat CLAUSE value is appropriate for every one of these positions, or whether some enumerated clause boundaries are more "final" than others, is a question this round does not attempt to resolve Ã¢â‚¬â€ it is left for a future, separately-scoped design round if pursued at all.

Status: `ANALYSIS ONLY`.

### 4.12 BC-12 (natural)

Text: `Ã©â‚¬â„¢Ã¦Â¨Â£Ã¥Â°Â±Ã¨Â¬â€ºÃ¥Â®Å’Ã§Â¬Â¬Ã¤Â¸â‚¬Ã¥â‚¬â€¹Ã©Æ’Â¨Ã¥Ë†â€ Ã¤Âºâ€ Ã£â‚¬â€šÃ¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¯Â¼Å’Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¦ÂÂ¢Ã¤Â¸ÂªÃ¨Â§â€™Ã¥ÂºÂ¦Ã¤Â¾â€ Ã§Å“â€¹Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¥â€¦Â¶Ã¥Â¯Â¦Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥â€¢ÂÃ©Â¡Å’Ã©â€šâ€žÃ¦Å“â€°Ã¥ÂÂ¦Ã¤Â¸â‚¬Ã§Â¨Â®Ã¨Â§Â£Ã¦Â³â€¢Ã¯Â¼Å’Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â¸â€¹Ã¤Â¸â‚¬Ã©Â ÂÃ¦Å“Æ’Ã¨ÂªÂªÃ¦ËœÅ½Ã£â‚¬â€š` (len=49)

- SENTENCE_FINAL: pos 12 (80.0, non-string-final)
- CLAUSE: pos 16 (35.0)
- Incidental: pos 25 (`internal`, Ã¢Ë†â€™20.0)
- ELLIPSIS: pos 26 (`seq_state=end`, 65.0)
- CLAUSE (second occurrence): pos 40 (35.0)
- Everything else: OTHER (0.0)

Incidental textual detail (recorded per this round's "record incidental modifiers, don't silently remove" instruction, though this is not a scoring modifier): the text contains simplified-Chinese characters (`Ã¦ÂÂ¢Ã¤Â¸ÂªÃ¨Â§â€™Ã¥ÂºÂ¦`) mixed into an otherwise traditional-character paragraph, exactly as it appeared verbatim in the matrix (extracted via regex, not retyped). This does not affect classification, since Phase 2A/2B do not distinguish simplified from traditional CJK Ã¢â‚¬â€ both fall under `CharacterClass.CJK`.

Status: `REAL-PIPELINE` for the targeted SENTENCE_FINAL Ã¢â€ â€™ CLAUSE Ã¢â€ â€™ ELLIPSIS transition sequence this "wrap-up / trailing pause / transition" case was designed to exercise.

## 5. Pairwise Margin Analysis

### 5.1 CLAUSE vs OTHER

Evidence: BC-01 (OTHER first, then CLAUSE) and BC-02 (CLAUSE first, then OTHER Ã¢â‚¬â€ independently written, not a mechanical swap).

- BC-01: OTHER = 0.0 (pos 1), CLAUSE = 35.0 (pos 15). Margin observed: 35.
- BC-02: OTHER = 0.0 (pos 1), CLAUSE = 35.0 (pos 3). Margin observed: 35.
- Both cases agree exactly; the margin is identical regardless of which sentence comes first in the paragraph.
- No incidental modifier touches either targeted candidate in either case (both are plain interior CJKÃ¢â‚¬â€œCJK / plain post-comma-CJK positions with `tech=False`, `atomic=False`, `internal=False`, `trans=0.0`, `ws=0.0`).

**Decision: KEEP.** The 35-point margin holds cleanly, with no reversal and no incidental narrowing, and is confirmed order-independent across two independently-written cases.

### 5.2 ELLIPSIS vs CLAUSE

Evidence: BC-03 (CLAUSE first, then ELLIPSIS) and BC-04 (ELLIPSIS first, then CLAUSE).

- BC-03: CLAUSE = 35.0 (pos 11), ELLIPSIS = 65.0 (pos 19, genuine END-state, non-string-final). Margin observed: 30.
- BC-04: ELLIPSIS = 65.0 (pos 10, END-state, non-string-final), CLAUSE = 35.0 (pos 16). Margin observed: 30.
- Both cases agree exactly; order-independent.
- Both cases show an incidental `INTERNAL` (Ã¢Ë†â€™20.0) candidate at the ellipsis run's interior position (BC-03 pos 18, BC-04 pos 9). This is a distinct candidate position from the targeted END-state ELLIPSIS candidate and does not affect either targeted score. Recorded, not treated as contamination.

**Decision: KEEP.** The 30-point margin holds cleanly in both directions; the genuine ELLIPSIS candidate is reliably reachable as a non-string-final END-state position exactly as designed, and the only incidental evidence present (`INTERNAL`) is confined to a separate, non-targeted candidate.

### 5.3 SENTENCE_FINAL vs ELLIPSIS

Evidence: BC-05 (ELLIPSIS first, then SENTENCE_FINAL) and BC-06 (SENTENCE_FINAL first, then ELLIPSIS).

- BC-05: ELLIPSIS = 65.0 (pos 10, END-state), SENTENCE_FINAL = 80.0 (pos 19, confirmed non-string-final). Margin observed: 15.
- BC-06: SENTENCE_FINAL = 80.0 (pos 8, non-string-final), ELLIPSIS = 65.0 (pos 18, END-state). Margin observed: 15.
- Both cases agree exactly; order-independent.
- Both cases show the same incidental `INTERNAL` (Ã¢Ë†â€™20.0) pattern at the ellipsis run's interior position (BC-05 pos 9, BC-06 pos 17), not touching either targeted candidate.
- Both target SENTENCE_FINAL marks were confirmed genuinely reachable (non-string-final) exactly as the matrix's trailing-content design intended Ã¢â‚¬â€ neither case suffered the string-final representation gap.

**Decision: KEEP.** This is the narrowest of the three margins (+15 vs. +35 and +30), and the matrix itself flagged it as the one most likely to be judged too thin. In the evidence actually gathered here, however, the 15-point margin holds cleanly with no reversal and no incidental narrowing, and is confirmed order-independent across the two available cases. This verdict is based on only two natural-order pairs (Ã‚Â§10 notes this as a limitation); it is not a claim that the margin is generously wide, only that nothing in this round's evidence shows it failing to dominate.

## 6. Multi-Candidate Analysis

BC-07 (OTHER/CLAUSE/ELLIPSIS, no SENTENCE_FINAL by design), BC-08 (CLAUSE/ELLIPSIS/SENTENCE_FINAL, the upper three-way), and BC-09 (all four classes) were each executed as single coherent paragraphs rather than constructed minimal pairs.

- BC-07 confirmed the lower three-way ordering (OTHER 0.0 < CLAUSE 35.0 < ELLIPSIS 65.0) holds jointly in one paragraph with no sentence-final mark present anywhere, cleanly isolating that portion of the hierarchy. One incidental `INTERNAL` position, not touching any target.
- BC-08 confirmed the upper three-way ordering (CLAUSE 35.0 < ELLIPSIS 65.0 < SENTENCE_FINAL 80.0) holds jointly, with the SENTENCE_FINAL candidate confirmed non-string-final. One incidental `INTERNAL` position.
- BC-09, the round's highest-value case, confirmed the complete four-class hierarchy and all three margins (35, 30, 15) simultaneously in one realistic paragraph: OTHER (0.0) Ã¢â€ â€™ CLAUSE (35.0) Ã¢â€ â€™ ELLIPSIS (65.0, END-state) Ã¢â€ â€™ SENTENCE_FINAL (80.0, non-string-final), in that textual order, with a single incidental `INTERNAL` position and zero `CASE ISSUE`.

All three margins read as jointly reasonable in this integrated context Ã¢â‚¬â€ no margin is implicated by any unexpected interaction observed in BC-07, BC-08, or BC-09.

## 7. Natural PPT-Note Analysis

BC-10, BC-11, and BC-12 use unengineered, presentation-style paragraphs rather than constructed pairs, and per this round's instruction none of the three is used to force a KEEP/INCREASE/DECREASE verdict.

- **BC-10** (roadmap style: statement Ã¢â€ â€™ clause-qualified statement Ã¢â€ â€™ trailing-off remark Ã¢â€ â€™ statement): produced CLAUSE (35.0) Ã¢â€ â€™ SENTENCE_FINAL (80.0) Ã¢â€ â€™ ELLIPSIS (65.0) Ã¢â€ â€™ SENTENCE_FINAL (80.0) in textual order, matching the intended hierarchy at every transition. The absolute-final `Ã£â‚¬â€š` is string-final and produces no candidate (expected, untargeted).
- **BC-11** (agenda style: enumerated clauses, a parenthetical aside, a concluding statement): produced three CLAUSE candidates, all at the flat value 35.0, including one immediately following a closing parenthetical Ã¢â‚¬â€ confirming that `paired_delimiter/parenthetical` spans do not suppress CLAUSE classification (only `technical`/`atomic` spans do, per Phase 2B's existing frozen design). Recorded as an open observation about flat CLAUSE weighting across enumerated positions; not acted on in this round.
- **BC-12** (transition style: wrap-up Ã¢â€ â€™ pause Ã¢â€ â€™ trailing off Ã¢â€ â€™ transition into new topic): produced SENTENCE_FINAL (80.0) Ã¢â€ â€™ CLAUSE (35.0) Ã¢â€ â€™ ELLIPSIS (65.0) Ã¢â€ â€™ CLAUSE (35.0) in textual order, matching the intended "wrap up / trail off / continue" shape a Phase 2D consumer would need.

Across all three natural cases, the observed score distributions are internally consistent with the intended ordering and show no unexpected class assignments. These three cases corroborate, but do not independently establish, the pairwise and multi-candidate findings in Ã‚Â§5 and Ã‚Â§6.

## 8. Incidental Evidence / Contamination

The only incidental (out-of-scope) evidence observed anywhere across all 12 cases was `INTERNAL` (Ã¢Ë†â€™20.0), which appears at the interior position of every two-character ellipsis run (`Ã¢â‚¬Â¦Ã¢â‚¬Â¦`) in the text. This occurred in 9 of the 12 cases Ã¢â‚¬â€ every case containing an ellipsis: BC-03, BC-04, BC-05, BC-06, BC-07, BC-08, BC-09, BC-10, and BC-12. (BC-01, BC-02, and BC-11 contain no ellipsis and show no `INTERNAL` evidence.)

In every occurrence, the `INTERNAL` candidate is a distinct position from the targeted END-state `ELLIPSIS` candidate (the interior position of the run vs. the position immediately after the run ends) and from any targeted `CLAUSE`/`OTHER`/`SENTENCE_FINAL` candidate. It never coincides with, and never modifies the score of, any of the candidates actually used as evidence in Ã‚Â§5Ã¢â‚¬â€œÃ‚Â§7. It is recorded here in full per this round's explicit instruction not to silently omit incidental modifiers, but none of these occurrences prevent isolation of any targeted comparison Ã¢â‚¬â€ no case required marking `NEEDS DATA` on this basis.

No `Technical`, `Atomic`, transition (`CJKÃ¢â€ â€LATIN`), or whitespace evidence appeared incidentally in any of the 12 cases. All 12 texts are single-language CJK punctuation-only text (confirmed: `tech=False` and `atomic=False` at every position across all 12 dumps; `trans=0.0(None)` at every position; `ws=0.0` at every position), exactly as the matrix's own "Out of Scope" design intended.

## 9. Calibration Decisions

| Margin | Current Margin | Decision | Evidence |
|---|---|---|---|
| CLAUSE vs OTHER | 35 (35.0 Ã¢Ë†â€™ 0.0) | KEEP | BC-01/BC-02: clean, order-independent 35-point separation across two independently-written cases; no incidental modifier touches either target candidate. |
| ELLIPSIS vs CLAUSE | 30 (65.0 Ã¢Ë†â€™ 35.0) | KEEP | BC-03/BC-04: clean, order-independent 30-point separation; genuine non-string-final ELLIPSIS reliably reachable as designed; incidental `INTERNAL` present only at a distinct, non-target ellipsis-interior position. |
| SENTENCE_FINAL vs ELLIPSIS | 15 (80.0 Ã¢Ë†â€™ 65.0) | KEEP | BC-05/BC-06: clean, order-independent 15-point separation; both non-string-final SENTENCE_FINAL candidates confirmed reachable as designed; incidental `INTERNAL` present only at distinct ellipsis-interior positions. Narrowest of the three margins Ã¢â‚¬â€ see Ã‚Â§10 for the limits of this round's evidence on it. |

## 10. Known Limitations

- This round evaluated 12 cases total, drawn entirely from single-language, punctuation-only Traditional/Simplified-mixed Chinese text. No case combines a targeted base-classification comparison with a competing out-of-scope factor acting on the same candidate (e.g., a CLAUSE candidate that is simultaneously adjacent to a Technical/Atomic span, or an OTHER candidate that is also a CJKÃ¢â€ â€Latin transition). Whether the margins hold under such joint conditions is not addressed here.
- Each pairwise margin (Ã‚Â§5.1Ã¢â‚¬â€œÃ‚Â§5.3) is supported by exactly two natural-order cases (forward and reversed). This is sufficient to confirm order-independence and the absence of reversal in the specific sentences used, but is not a large-sample statistical claim about all possible realistic PPT notes.
- The SENTENCE_FINAL vs ELLIPSIS margin (+15) is the narrowest of the three and was explicitly flagged by the matrix design itself as the one most likely to be judged too thin. This round's evidence does not show it failing, but the evidence base for this specific margin is the smallest of the three (two cases, both drawn from short, similarly-structured sentences).
- BC-01/BC-02's `OTHER` candidate was selected via the deterministic "first candidate by pipeline position order" rule specified in this round's contract, since both texts contain many eligible `OTHER` positions. This is a reporting choice for this round only, not a new production selection rule.
- BC-10, BC-11, and BC-12 are `ANALYSIS ONLY` by design and contribute qualitative corroboration, not independent KEEP/INCREASE/DECREASE evidence.
- BC-11's observation about multiple flat-valued CLAUSE candidates in one enumeration is recorded but not evaluated for any potential positional-weighting design change; that would require a separately-scoped round.
- No case in this matrix exercises Latin text, digits, or mixed-script content; the base-classification dominance observed here is specific to CJK punctuation-only structures.

## 11. Recommendation for Next Numeric Calibration Decision

Based on the evidence gathered in this round, the three base-classification margins (CLAUSE Ã¢Ë†â€™ OTHER = 35, ELLIPSIS Ã¢Ë†â€™ CLAUSE = 30, SENTENCE_FINAL Ã¢Ë†â€™ ELLIPSIS = 15) are well-supported by real-pipeline behavior across pairwise, multi-candidate, and natural-paragraph cases, with zero `CASE ISSUE` outcomes and no incidental contamination of any targeted comparison. No change to any of these three values is indicated by this round's evidence.

For any future numeric calibration work, two directions are suggested by what this round deliberately left untested (see Ã‚Â§10), without this report asserting either is necessary:

1. A dedicated round evaluating base-classification margins under joint conditions with the out-of-scope protection factors (Technical/Atomic/INTERNAL/transition/whitespace) acting on the same candidate, rather than merely appearing incidentally elsewhere in the text as observed here.
2. If BC-11's flat-CLAUSE-across-enumeration observation is judged worth pursuing, a separately-scoped design round (not a calibration-execution round) to first decide, as a design question, whether positional or enumeration-aware weighting is in scope for Phase 2C at all Ã¢â‚¬â€ this report takes no position on that question.

Both are optional next steps, not requirements; this round's own conclusion is that the currently adopted base-classification baseline needs no revision on the evidence gathered here.
