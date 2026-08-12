# Phase 2C Base Classification Calibration Matrix

**Status:** Calibration Matrix Design Ã¢â‚¬â€ no calibration experiment executed
**Phase:** Phase 2C Ã¢â‚¬â€ Numeric Calibration (Base Classification Dominance)
**Purpose:** Design the calibration matrix needed to evaluate whether the current
base classification magnitudes and margins are appropriate, without changing any
value and without running the experiment.

This document is a **design artifact only**. No calibration script was run, no
existing artifact was modified, and no conclusion about any margin is drawn here.

---

## 1. Purpose

`docs/phase2c/decisions/PHASE_2C_NUMERIC_BASELINE_DECISION.md` adopted the current base classification
scores as a provisional baseline, explicitly not yet calibrated. This matrix defines
the calibration cases a later execution round will need to evaluate the *magnitudes*
and *margins* between `OTHER`, `CLAUSE`, `ELLIPSIS`, and `SENTENCE_FINAL` Ã¢â‚¬â€ not their
ordering, which prior rounds have already observed to hold. The ordering
`SENTENCE_FINAL > ELLIPSIS > CLAUSE > OTHER` is treated as given; the open question is
whether `+80`/`+65`/`+35`/`0` and the margins `45`/`30`/`15`/`35` between them are
*appropriately dominant* Ã¢â‚¬â€ too strong, too weak, or reasonable Ã¢â‚¬â€ against realistic
PowerPoint speaker-note text.

## 2. Authoritative Baseline

Per `docs/phase2c/decisions/PHASE_2C_NUMERIC_BASELINE_DECISION.md` Ã‚Â§4.1, unchanged in this round:

| Factor | Value |
|---|---:|
| `SENTENCE_FINAL` | +80 |
| `ELLIPSIS` | +65 |
| `CLAUSE` | +35 |
| `OTHER` | 0 |

No value above is modified by this document. This matrix only designs cases; it does
not execute them and does not propose a replacement number for anything.

## 3. Calibration Scope

- Base classification magnitudes: `SENTENCE_FINAL`, `ELLIPSIS`, `CLAUSE`, `OTHER`.
- The three adjacent margins: `CLAUSE - OTHER = 35`, `ELLIPSIS - CLAUSE = 30`,
  `SENTENCE_FINAL - ELLIPSIS = 15`.
- Whether these margins are reasonable when the competing candidates come from
  realistic, multi-sentence PowerPoint speaker-note text (not hand-built strings
  whose sole purpose is to contain a specific punctuation mark).
- Multi-candidate competition: what a single realistic paragraph's whole set of
  candidate scores looks like when `OTHER`/`CLAUSE`/`ELLIPSIS`/`SENTENCE_FINAL` all
  appear together.

## 4. Out of Scope

- **Positive evidence** (`CJK Ã¢â€ â€™ LATIN +15`, `LATIN Ã¢â€ â€™ CJK +15`, `Whitespace +10`) Ã¢â‚¬â€
  frozen for this round per `docs/phase2c/decisions/PHASE_2C_NUMERIC_BASELINE_DECISION.md` Ã‚Â§4.2. Cases
  below are deliberately written in single-language (CJK) text wherever possible to
  avoid conflating a base-classification finding with an incidental transition/
  whitespace bonus; where a transition or whitespace bonus appears anyway (it
  sometimes will, since realistic PPT notes are not hermetically single-factor), it
  is noted as an incidental contribution, not treated as evidence for or against any
  base-classification margin.
- **Protection** (`Technical -30`, `Atomic -30`, `INTERNAL -20`) Ã¢â‚¬â€ already the
  subject of the completed Protection Calibration and Post-Correction Verification;
  frozen for this round. Cases below avoid technical/atomic/punctuation-sequence
  content by design; if it appears incidentally, it is flagged the same way as
  positive evidence above.
- **Emoji / emoticon** Ã¢â‚¬â€ no dedicated cases; if present incidentally in a candidate
  source text, excluded from the calibration case rather than given special
  treatment. No new emoji-specific scoring factor is proposed.
- Production code, tests, existing calibration scripts/matrices/reports, the Numeric
  Baseline Decision itself, Phase 2D, thresholds, floors, normalization.

## 5. Score Margin Questions

| Comparison | Current scores | Current margin | Calibration question |
|---|---:|---:|---|
| CLAUSE vs OTHER | +35 vs 0 | 35 | Is +35 sufficient dominance for CLAUSE over OTHER? |
| ELLIPSIS vs CLAUSE | +65 vs +35 | 30 | Is +30 sufficient dominance for ELLIPSIS over CLAUSE? |
| SENTENCE_FINAL vs ELLIPSIS | +80 vs +65 | 15 | Is +15 sufficient dominance for SENTENCE_FINAL over ELLIPSIS? |

These are the three questions every case group below is designed to feed evidence
into. No case is designed to re-litigate the ordering itself.

## 6. Calibration Method

A later execution round must:

1. Run each case's input text through the real, unmodified pipeline
   (`analyze_text_structure` Ã¢â€ â€™ `observe_boundaries` Ã¢â€ â€™ `classify_boundary`), exactly
   as every prior calibration script has done Ã¢â‚¬â€ no re-parsing, no synthetic
   `BoundaryClass` substitution.
2. Locate the real candidate(s) matching each case's "Target boundary" description.
3. Record the actual observed class, score, and any incidental modifiers (transition,
   whitespace, protection) that also apply to that candidate, exactly as the
   Protection Calibration script's `dump()`-style output already does.
4. Compare the observed margin against the "Current margin" column and record
   `KEEP` / `INCREASE` / `DECREASE` / `NEED MORE DATA` per the status criteria in
   each case Ã¢â‚¬â€ never a fixed numeric replacement.
5. Where a case's target class turns out to be unreachable, string-final (no
   candidate produced Ã¢â‚¬â€ the known Phase 2A "no candidate after the final character"
   representation gap, documented since Calibration Round 1), or otherwise not
   representable, mark it `CASE ISSUE` rather than forcing a synthetic substitute.
6. Synthetic fixtures (a hand-built `BoundaryCandidate`/`BoundaryFeatures`) may be
   used only for arithmetic sanity checks (e.g. "does `65-35=30` compute correctly
   given these two classes") Ã¢â‚¬â€ never presented as calibration evidence for whether a
   margin is contextually appropriate. This mirrors the restriction already
   documented in the Protection Calibration Matrix.

This document performs none of these six steps. It only specifies what a later round
must do.

## 7. Pairwise Cases

Each pairwise group below covers one adjacent margin in one textual direction; a
sibling group in the opposite direction is provided for the same margin per Ã‚Â§5's "both
directions where meaningful" requirement Ã¢â‚¬â€ mirrored, independently-written realistic
text, not a mechanical reversal of the same candidate.

### 7.1 OTHER vs CLAUSE

#### BC-01 Ã¢â‚¬â€ OTHER vs CLAUSE

| Field | Value |
|---|---|
| Case ID | BC-01 |
| Purpose | Observe a plain `OTHER` interior boundary and an ordinary `CLAUSE` boundary in one short, realistic multi-sentence note, in that textual order (plain sentence first, clause-punctuated sentence second) |
| Input text | `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¦Å â€¢Ã¥Â½Â±Ã§â€°â€¡Ã¤Â»â€¹Ã§Â´Â¹Ã§Â³Â»Ã§ÂµÂ±Ã¦Å¾Â¶Ã¦Â§â€¹Ã£â‚¬â€šÃ©Â¦â€“Ã¥â€¦Ë†Ã¯Â¼Å’Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Å“â€¹Ã¦â€¢Â´Ã©Â«â€Ã¨Â¨Â­Ã¨Â¨Ë†Ã£â‚¬â€š` |
| Target boundary | (a) any interior CJK-CJK boundary within `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¦Å â€¢Ã¥Â½Â±Ã§â€°â€¡Ã¤Â»â€¹Ã§Â´Â¹Ã§Â³Â»Ã§ÂµÂ±Ã¦Å¾Â¶Ã¦Â§â€¹` that carries no other evidence Ã¢â‚¬â€ expected `OTHER`; (b) the `Ã¯Â¼Å’` boundary immediately after `Ã©Â¦â€“Ã¥â€¦Ë†` Ã¢â‚¬â€ expected `CLAUSE` |
| Expected candidate class | (a) `OTHER`; (b) `CLAUSE` |
| Comparison candidate | (a) vs (b), within the same text |
| Current baseline score | 0.0 vs 35.0 |
| Current margin | 35 |
| Calibration question | Is CLAUSE's +35 sufficient dominance over a genuinely plain OTHER boundary drawn from realistic text, not a hand-picked minimal-pair string? |
| Evidence requirement | Real pipeline; both candidates must come from the same input text |
| Expected observation | Not asserted here Ã¢â‚¬â€ a later round records the actual scores and whether the +35 margin reads as proportionate given the sentences' actual content |
| Status criteria | `KEEP` if the margin holds with no reversal and no incidental modifier materially closes the gap; `INCREASE`/`DECREASE` if the realistic margin feels disproportionate either way; `NEED MORE DATA` if the note's first sentence produces no clean OTHER candidate (e.g. it is entirely consumed by incidental evidence) |

#### BC-02 Ã¢â‚¬â€ CLAUSE vs OTHER (reverse textual order)

| Field | Value |
|---|---|
| Case ID | BC-02 |
| Purpose | Same margin as BC-01, opposite textual order (clause-punctuated sentence first, plain sentence second), independently written Ã¢â‚¬â€ not a mechanical swap of BC-01's own candidates Ã¢â‚¬â€ to check whether paragraph position changes anything (it should not, since neither Phase 2A nor this scoring formula consult `context_flags`, but this has not been directly demonstrated for base classification the way it was for Protection) |
| Input text | `Ã©Â¦â€“Ã¥â€¦Ë†Ã¯Â¼Å’Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Å“â€¹Ã¦â€¢Â´Ã©Â«â€Ã¨Â¨Â­Ã¨Â¨Ë†Ã£â‚¬â€šÃ©â‚¬â„¢Ã¥â‚¬â€¹Ã¦Å â€¢Ã¥Â½Â±Ã§â€°â€¡Ã¤Â»â€¹Ã§Â´Â¹Ã§Â³Â»Ã§ÂµÂ±Ã¦Å¾Â¶Ã¦Â§â€¹Ã£â‚¬â€š` |
| Target boundary | (a) the `Ã¯Â¼Å’` boundary immediately after `Ã©Â¦â€“Ã¥â€¦Ë†` Ã¢â‚¬â€ expected `CLAUSE`; (b) any interior CJK-CJK boundary within `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¦Å â€¢Ã¥Â½Â±Ã§â€°â€¡Ã¤Â»â€¹Ã§Â´Â¹Ã§Â³Â»Ã§ÂµÂ±Ã¦Å¾Â¶Ã¦Â§â€¹` Ã¢â‚¬â€ expected `OTHER` |
| Expected candidate class | (a) `CLAUSE`; (b) `OTHER` |
| Comparison candidate | (a) vs (b), within the same text |
| Current baseline score | 35.0 vs 0.0 |
| Current margin | 35 |
| Calibration question | Does the CLAUSE-over-OTHER margin hold identically regardless of which sentence comes first in the paragraph? |
| Evidence requirement | Real pipeline |
| Expected observation | Not asserted Ã¢â‚¬â€ a later round confirms whether BC-01 and BC-02 produce identical per-class scores (they are expected to, since the scoring formula is a pure function of each candidate's own local features, not paragraph position Ã¢â‚¬â€ but this is a fact to verify, not assume) |
| Status criteria | `KEEP` if BC-01/BC-02 agree exactly; `NEED MORE DATA` if they unexpectedly diverge (would itself be a notable finding, not merely a margin question) |

### 7.2 CLAUSE vs ELLIPSIS

#### BC-03 Ã¢â‚¬â€ CLAUSE vs ELLIPSIS

| Field | Value |
|---|---|
| Case ID | BC-03 |
| Purpose | Observe an ordinary CLAUSE boundary and a genuine ELLIPSIS (END-of-sequence, with trailing content so it is a real candidate) in one realistic note |
| Input text | `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥â€¢ÂÃ©Â¡Å’Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Â¨ÂÃ¥Â¾Å’Ã¨ÂªÂªÃ¦ËœÅ½Ã¯Â¼Å’Ã§ÂÂ¾Ã¥Å“Â¨Ã¥â€¦Ë†Ã§Å“â€¹Ã©â€¡ÂÃ©Â»Å¾Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¥Â¥Â½Ã¯Â¼Å’Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã©â€“â€¹Ã¥Â§â€¹Ã£â‚¬â€š` |
| Target boundary | (a) the `Ã¯Â¼Å’` after `Ã¨ÂªÂªÃ¦ËœÅ½` Ã¢â‚¬â€ expected `CLAUSE`; (b) the boundary at the end of `Ã¢â‚¬Â¦Ã¢â‚¬Â¦` (before `Ã¥Â¥Â½`) Ã¢â‚¬â€ expected `ELLIPSIS`, *provided* the ellipsis run has trailing content, which it does here (`Ã¥Â¥Â½Ã¯Â¼Å’Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã©â€“â€¹Ã¥Â§â€¹Ã£â‚¬â€š` follows) |
| Expected candidate class | (a) `CLAUSE`; (b) `ELLIPSIS` |
| Comparison candidate | (a) vs (b) |
| Current baseline score | 35.0 vs 65.0 |
| Current margin | 30 |
| Calibration question | Is ELLIPSIS's +30 margin over CLAUSE sufficient dominance in realistic usage, where an ellipsis often signals a more significant pause/trailing-off than a clause comma? |
| Evidence requirement | Real pipeline; the ellipsis run must not be string-final (per the known Phase 2A representation gap Ã¢â‚¬â€ a trailing sentence is included specifically to avoid this) |
| Expected observation | Not asserted |
| Status criteria | `KEEP`/`INCREASE`/`DECREASE` per how the realistic margin reads; `NEED MORE DATA` if the ellipsis run is unexpectedly reclassified (e.g. absorbed into a different composition) or if `INTERNAL`-state interior positions are mistakenly used instead of the genuine END candidate |

#### BC-04 Ã¢â‚¬â€ ELLIPSIS vs CLAUSE (reverse textual order)

| Field | Value |
|---|---|
| Case ID | BC-04 |
| Purpose | Same margin as BC-03, opposite order (ellipsis sentence first, clause sentence second), independently written |
| Input text | `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã©Æ’Â¨Ã¥Ë†â€ Ã¦Â¯â€Ã¨Â¼Æ’Ã¨Â¤â€¡Ã©â€ºÅ“Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¥â€¦Ë†Ã¨Â·Â³Ã©ÂÅ½Ã¯Â¼Å’Ã¤Â¹â€¹Ã¥Â¾Å’Ã¥â€ ÂÃ¨Â¨Å½Ã¨Â«â€“Ã£â‚¬â€š` |
| Target boundary | (a) end of `Ã¢â‚¬Â¦Ã¢â‚¬Â¦` (before `Ã¦Ë†â€˜`) Ã¢â‚¬â€ expected `ELLIPSIS`; (b) the `Ã¯Â¼Å’` after `Ã¨Â·Â³Ã©ÂÅ½` Ã¢â‚¬â€ expected `CLAUSE` |
| Expected candidate class | (a) `ELLIPSIS`; (b) `CLAUSE` |
| Comparison candidate | (a) vs (b) |
| Current baseline score | 65.0 vs 35.0 |
| Current margin | 30 |
| Calibration question | Same as BC-03, opposite order Ã¢â‚¬â€ does the margin hold regardless of which class's candidate appears first? |
| Evidence requirement | Real pipeline |
| Expected observation | Not asserted |
| Status criteria | Same as BC-03; additionally compare BC-03/BC-04 for order-independence per BC-02's rationale |

### 7.3 ELLIPSIS vs SENTENCE_FINAL

#### BC-05 Ã¢â‚¬â€ ELLIPSIS vs SENTENCE_FINAL

| Field | Value |
|---|---|
| Case ID | BC-05 |
| Purpose | Observe a genuine ELLIPSIS candidate and a genuine SENTENCE_FINAL candidate (non-string-final, per the known representation gap) in one realistic note |
| Input text | `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥â€¢ÂÃ©Â¡Å’Ã§Â¨ÂÃ¥Â¾Å’Ã¥â€ ÂÃ¨Â«â€¡Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã§ÂÂ¾Ã¥Å“Â¨Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Å“â€¹Ã¤Â¸â€¹Ã¤Â¸â‚¬Ã©Â ÂÃ£â‚¬â€šÃ¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¤Â»â€¹Ã§Â´Â¹Ã©â€¡ÂÃ©Â»Å¾Ã£â‚¬â€š` |
| Target boundary | (a) end of `Ã¢â‚¬Â¦Ã¢â‚¬Â¦` (before `Ã§ÂÂ¾`) Ã¢â‚¬â€ expected `ELLIPSIS`; (b) the `Ã£â‚¬â€š` after `Ã¤Â¸â€¹Ã¤Â¸â‚¬Ã©Â Â` (before `Ã¦Å½Â¥`) Ã¢â‚¬â€ expected `SENTENCE_FINAL`, since it has trailing content (`Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¤Â»â€¹Ã§Â´Â¹Ã©â€¡ÂÃ©Â»Å¾Ã£â‚¬â€š`) |
| Expected candidate class | (a) `ELLIPSIS`; (b) `SENTENCE_FINAL` |
| Comparison candidate | (a) vs (b) |
| Current baseline score | 65.0 vs 80.0 |
| Current margin | 15 |
| Calibration question | Is SENTENCE_FINAL's +15 margin over ELLIPSIS sufficient Ã¢â‚¬â€ this is the narrowest of the three adjacent margins, and the one most likely to be judged "too thin" if realistic text shows ELLIPSIS behaving like a near-terminal boundary in practice |
| Evidence requirement | Real pipeline; the final `Ã£â‚¬â€š` in the text (after `Ã©â€¡ÂÃ©Â»Å¾`) is deliberately included only to give the *first* `Ã£â‚¬â€š` trailing content Ã¢â‚¬â€ it is not itself a target candidate for this case (it would itself be string-final relative to the whole input and thus unobservable, per the representation gap) |
| Expected observation | Not asserted |
| Status criteria | `KEEP` if the narrow +15 margin still reads as clearly dominant in context; `INCREASE` if realistic text suggests ELLIPSIS too closely rivals SENTENCE_FINAL as a cut signal; `NEED MORE DATA` if the target `Ã£â‚¬â€š` is unexpectedly unreachable or leak-contaminated |

#### BC-06 Ã¢â‚¬â€ SENTENCE_FINAL vs ELLIPSIS (reverse textual order)

| Field | Value |
|---|---|
| Case ID | BC-06 |
| Purpose | Same margin as BC-05, opposite order (a genuine sentence-final sentence first, an ellipsis-trailing sentence second, with one more sentence appended so the ellipsis has trailing content) |
| Input text | `Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¥â€¦Ë†Ã§Å“â€¹Ã¤Â¸â€¹Ã¤Â¸â‚¬Ã©Â ÂÃ£â‚¬â€šÃ©â‚¬â„¢Ã¥â‚¬â€¹Ã¥â€¢ÂÃ©Â¡Å’Ã§Â¨ÂÃ¥Â¾Å’Ã¥â€ ÂÃ¨Â«â€¡Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¥Â¥Â½Ã¯Â¼Å’Ã©â€“â€¹Ã¥Â§â€¹Ã¥ÂÂ§Ã£â‚¬â€š` |
| Target boundary | (a) the `Ã£â‚¬â€š` after `Ã¤Â¸â€¹Ã¤Â¸â‚¬Ã©Â Â` (before `Ã©â‚¬â„¢`) Ã¢â‚¬â€ expected `SENTENCE_FINAL`; (b) end of `Ã¢â‚¬Â¦Ã¢â‚¬Â¦` (before `Ã¥Â¥Â½`) Ã¢â‚¬â€ expected `ELLIPSIS` |
| Expected candidate class | (a) `SENTENCE_FINAL`; (b) `ELLIPSIS` |
| Comparison candidate | (a) vs (b) |
| Current baseline score | 80.0 vs 65.0 |
| Current margin | 15 |
| Calibration question | Same as BC-05, opposite order |
| Evidence requirement | Real pipeline |
| Expected observation | Not asserted |
| Status criteria | Same as BC-05; compare against BC-05 for order-independence |

## 8. Multi-Candidate Cases

These cases put three or four base classes into competition within one realistic
paragraph, to observe the *whole* relative ordering and the shape of the margins
together, not just one pairwise delta at a time. Per the known Phase 2A
representation gap (a terminal punctuation mark at the very end of the analyzed
string produces no candidate), every SENTENCE_FINAL-seeking case below deliberately
appends one more short sentence after its target `Ã£â‚¬â€š` so that boundary is not
string-final.

#### BC-07 Ã¢â‚¬â€ OTHER + CLAUSE + ELLIPSIS

| Field | Value |
|---|---|
| Case ID | BC-07 |
| Purpose | Three-way competition without a sentence-final mark (deliberately no `Ã£â‚¬â€š`/`Ã¯Â¼Â`/`Ã¯Â¼Å¸` anywhere), to isolate the OTHER/CLAUSE/ELLIPSIS portion of the hierarchy |
| Input text | `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥Å Å¸Ã¨Æ’Â½Ã©â€šâ€žÃ¥Å“Â¨Ã©â€“â€¹Ã§â„¢Â¼Ã¤Â¸Â­Ã¯Â¼Å’Ã§Â´Â°Ã§Â¯â‚¬Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Â¨ÂÃ¥Â¾Å’Ã¨Â£Å“Ã¥â€¦â€¦Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¥â€¦Ë†Ã§Å“â€¹Ã§â€ºÂ®Ã¥â€°ÂÃ§Å¡â€žÃ©â‚¬Â²Ã¥ÂºÂ¦` |
| Target boundary | (a) plain CJK-CJK interior boundary in `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥Å Å¸Ã¨Æ’Â½Ã©â€šâ€žÃ¥Å“Â¨Ã©â€“â€¹Ã§â„¢Â¼Ã¤Â¸Â­` Ã¢â‚¬â€ expected `OTHER`; (b) the `Ã¯Â¼Å’` after `Ã©â€“â€¹Ã§â„¢Â¼Ã¤Â¸Â­` Ã¢â‚¬â€ expected `CLAUSE`; (c) end of `Ã¢â‚¬Â¦Ã¢â‚¬Â¦` (before `Ã¥â€¦Ë†`) Ã¢â‚¬â€ expected `ELLIPSIS` |
| Expected candidate class | (a) `OTHER`, (b) `CLAUSE`, (c) `ELLIPSIS` |
| Comparison candidate | All three, pairwise and as a set |
| Current baseline score | 0.0 / 35.0 / 65.0 |
| Current margin | 35 (CLAUSE-OTHER), 30 (ELLIPSIS-CLAUSE) |
| Calibration question | Does the full three-way ordering and both margins hold together in one coherent, realistic paragraph (not three separately-constructed minimal pairs)? |
| Evidence requirement | Real pipeline; record every candidate's score in this text, not just the three targeted ones, so unexpected interactions are visible |
| Expected observation | Not asserted |
| Status criteria | `KEEP`/`INCREASE`/`DECREASE` per whether the joint ordering and margins feel proportionate; `NEED MORE DATA` if any target class fails to appear as expected |

#### BC-08 Ã¢â‚¬â€ CLAUSE + ELLIPSIS + SENTENCE_FINAL

| Field | Value |
|---|---|
| Case ID | BC-08 |
| Purpose | Three-way competition covering the upper half of the hierarchy, with a genuine non-string-final SENTENCE_FINAL candidate |
| Input text | `Ã©â‚¬â„¢Ã©Æ’Â¨Ã¥Ë†â€ Ã©â€šÂÃ¨Â¼Â¯Ã¦Â¯â€Ã¨Â¼Æ’Ã¨Â¤â€¡Ã©â€ºÅ“Ã¯Â¼Å’Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Â¨ÂÃ¥Â¾Å’Ã¨ÂªÂªÃ¦ËœÅ½Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã§ÂÂ¾Ã¥Å“Â¨Ã§Å“â€¹Ã¤Â¸â€¹Ã¤Â¸â‚¬Ã¥â‚¬â€¹Ã¥Å Å¸Ã¨Æ’Â½Ã£â‚¬â€šÃ¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¦Å“Æ’Ã¦Å“â€°Ã§Â¯â€žÃ¤Â¾â€¹Ã£â‚¬â€š` |
| Target boundary | (a) the `Ã¯Â¼Å’` after `Ã¨Â¤â€¡Ã©â€ºÅ“` Ã¢â‚¬â€ expected `CLAUSE`; (b) end of `Ã¢â‚¬Â¦Ã¢â‚¬Â¦` (before `Ã§ÂÂ¾`) Ã¢â‚¬â€ expected `ELLIPSIS`; (c) the `Ã£â‚¬â€š` after `Ã¥Å Å¸Ã¨Æ’Â½` (before `Ã¦Å½Â¥`) Ã¢â‚¬â€ expected `SENTENCE_FINAL` |
| Expected candidate class | (a) `CLAUSE`, (b) `ELLIPSIS`, (c) `SENTENCE_FINAL` |
| Comparison candidate | All three, pairwise and as a set |
| Current baseline score | 35.0 / 65.0 / 80.0 |
| Current margin | 30 (ELLIPSIS-CLAUSE), 15 (SF-ELLIPSIS) |
| Calibration question | Does the full three-way ordering and both upper margins hold together in one paragraph? |
| Evidence requirement | Real pipeline |
| Expected observation | Not asserted |
| Status criteria | Same pattern as BC-07 |

#### BC-09 Ã¢â‚¬â€ OTHER + CLAUSE + ELLIPSIS + SENTENCE_FINAL

| Field | Value |
|---|---|
| Case ID | BC-09 |
| Purpose | All four base classes in one realistic paragraph Ã¢â‚¬â€ the most complete single-text picture of the whole hierarchy and all three margins together |
| Input text | `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥Å Å¸Ã¨Æ’Â½Ã©â€šâ€žÃ¥Å“Â¨Ã©â€“â€¹Ã§â„¢Â¼Ã¤Â¸Â­Ã¯Â¼Å’Ã§Â´Â°Ã§Â¯â‚¬Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã§Â¨ÂÃ¥Â¾Å’Ã¨Â£Å“Ã¥â€¦â€¦Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã§â€ºÂ®Ã¥â€°ÂÃ¥â€¦Ë†Ã§Å“â€¹Ã¦â€¢Â´Ã©Â«â€Ã¤Â»â€¹Ã©ÂÂ¢Ã£â‚¬â€šÃ¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¦Å“Æ’Ã¥Â±â€¢Ã§Â¤ÂºÃ§Â¯â€žÃ¤Â¾â€¹Ã£â‚¬â€š` |
| Target boundary | (a) plain CJK-CJK interior boundary in `Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥Å Å¸Ã¨Æ’Â½Ã©â€šâ€žÃ¥Å“Â¨Ã©â€“â€¹Ã§â„¢Â¼Ã¤Â¸Â­` Ã¢â‚¬â€ expected `OTHER`; (b) the `Ã¯Â¼Å’` after `Ã©â€“â€¹Ã§â„¢Â¼Ã¤Â¸Â­` Ã¢â‚¬â€ expected `CLAUSE`; (c) end of `Ã¢â‚¬Â¦Ã¢â‚¬Â¦` (before `Ã§â€ºÂ®`) Ã¢â‚¬â€ expected `ELLIPSIS`; (d) the `Ã£â‚¬â€š` after `Ã¤Â»â€¹Ã©ÂÂ¢` (before `Ã¦Å½Â¥`) Ã¢â‚¬â€ expected `SENTENCE_FINAL` |
| Expected candidate class | (a) `OTHER`, (b) `CLAUSE`, (c) `ELLIPSIS`, (d) `SENTENCE_FINAL` |
| Comparison candidate | All four, pairwise and as a set |
| Current baseline score | 0.0 / 35.0 / 65.0 / 80.0 |
| Current margin | 35 / 30 / 15 |
| Calibration question | Is the complete four-class hierarchy, with all three margins, simultaneously well-formed in one coherent realistic paragraph Ã¢â‚¬â€ the single most direct test of "moderate classification dominance" as a whole design? |
| Evidence requirement | Real pipeline; this is the primary case this whole matrix is built to support Ã¢â‚¬â€ record the complete candidate dump for this text, not just the four targeted positions |
| Expected observation | Not asserted |
| Status criteria | `KEEP` only if all three margins independently read as reasonable in this joint context; otherwise flag exactly which margin(s) are implicated, using the same per-margin criteria as BC-01Ã¢â‚¬â€œBC-08 |

## 9. Natural PPT Note Cases

Three additional, topically-varied realistic speaker-note paragraphs, each mixing
multiple punctuation patterns naturally (not engineered as a minimal pair), to avoid
overfitting the calibration evidence to one sentence pattern or topic (per the round's
explicit "do not overfit" instruction). Each still avoids technical/atomic content and
CJK/Latin mixing by design (Ã‚Â§4), though incidental instances are tolerated and must be
noted, not silently excluded from the score reading.

#### BC-10 Ã¢â‚¬â€ Natural PPT-note mixed set: product roadmap

| Field | Value |
|---|---|
| Case ID | BC-10 |
| Purpose | A roadmap-style note: statement, clause-qualified statement, a trailing-off remark, a following statement |
| Input text | `Ã©â‚¬â„¢Ã¤Â¸â‚¬Ã©Â ÂÃ¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â»â€¹Ã§Â´Â¹Ã§â€Â¢Ã¥â€œÂÃ¨Â¦ÂÃ¥Å Æ’Ã¯Â¼Å’Ã¥â€¦Ë†Ã¨Â¬â€ºÃ§Å¸Â­Ã¦Å“Å¸Ã§â€ºÂ®Ã¦Â¨â„¢Ã£â‚¬â€šÃ©â€¢Â·Ã¦Å“Å¸Ã¦â€“Â¹Ã¥Ââ€˜Ã©â€šâ€žÃ¥Å“Â¨Ã¨Â¨Å½Ã¨Â«â€“Ã¤Â¸Â­Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã§Â´Â°Ã§Â¯â‚¬Ã¤Â¹â€¹Ã¥Â¾Å’Ã¦Å“Æ’Ã¥â€ ÂÃ¦â€ºÂ´Ã¦â€“Â°Ã£â‚¬â€šÃ©â‚¬â„¢Ã¦ËœÂ¯Ã§â€ºÂ®Ã¥â€°ÂÃ§Å¡â€žÃ©â€¡ÂÃ©Â»Å¾Ã£â‚¬â€š` |
| Target boundary | Whatever `OTHER`/`CLAUSE`/`ELLIPSIS`/`SENTENCE_FINAL` candidates the real pipeline actually produces in this text Ã¢â‚¬â€ not pre-selected positions, since this case's purpose is to see what a natural paragraph yields rather than to engineer a specific boundary |
| Expected candidate class | Not pre-asserted Ã¢â‚¬â€ recorded from real output |
| Comparison candidate | All candidates produced, ranked by score |
| Current baseline score | N/A Ã¢â‚¬â€ to be recorded |
| Current margin | N/A Ã¢â‚¬â€ to be recorded |
| Calibration question | Does the natural distribution of scores in an unengineered paragraph match the intended hierarchy and feel proportionate to how a person would actually want this text segmented for subtitles? |
| Evidence requirement | Real pipeline; full candidate dump |
| Expected observation | Not asserted |
| Status criteria | `ANALYSIS ONLY` Ã¢â‚¬â€ this case is diagnostic/exploratory by design, not a strict pairwise PASS/FAIL; a later round should summarize qualitative fit rather than force a KEEP/INCREASE/DECREASE verdict on a single natural paragraph alone (those verdicts belong to the pairwise/multi-candidate cases above, which this case corroborates) |

#### BC-11 Ã¢â‚¬â€ Natural PPT-note mixed set: meeting agenda

| Field | Value |
|---|---|
| Case ID | BC-11 |
| Purpose | An agenda-style note: enumerated clauses, a parenthetical aside, a concluding statement |
| Input text | `Ã¤Â»Å Ã¥Â¤Â©Ã¨Â­Â°Ã§Â¨â€¹Ã¦Å“â€°Ã¤Â¸â€°Ã¥â‚¬â€¹Ã©â€¡ÂÃ©Â»Å¾Ã¯Â¼Å’Ã§Â¬Â¬Ã¤Â¸â‚¬Ã¥â‚¬â€¹Ã¦ËœÂ¯Ã©â‚¬Â²Ã¥ÂºÂ¦Ã¥â€ºÅ¾Ã©Â¡Â§Ã¯Â¼Å’Ã§Â¬Â¬Ã¤ÂºÅ’Ã¥â‚¬â€¹Ã¦ËœÂ¯Ã©Â¢Â¨Ã©Å¡ÂªÃ¨Â¨Å½Ã¨Â«â€“Ã¯Â¼Ë†Ã©â‚¬â„¢Ã©Æ’Â¨Ã¥Ë†â€ Ã¦Â¯â€Ã¨Â¼Æ’Ã©â€¡ÂÃ¨Â¦ÂÃ¯Â¼â€°Ã¯Â¼Å’Ã§Â¬Â¬Ã¤Â¸â€°Ã¥â‚¬â€¹Ã¦â€°ÂÃ¦ËœÂ¯Ã¤Â¸â€¹Ã¤Â¸â‚¬Ã¦Â­Â¥Ã¨Â¦ÂÃ¥Å Æ’Ã£â‚¬â€šÃ¦Å“Æ’Ã¨Â­Â°Ã¥Â¤Â§Ã¦Â¦â€šÃ©â€“â€¹Ã¤Â¸â‚¬Ã¥Â°ÂÃ¦â„¢â€šÃ£â‚¬â€š` |
| Target boundary | Real pipeline output Ã¢â‚¬â€ includes multiple CLAUSE candidates (enumeration commas), a parenthetical (`Ã¯Â¼Ë†Ã¢â‚¬Â¦Ã¯Â¼â€°`, which is a transparent `paired_delimiter`, not itself scored specially by base classification), and a SENTENCE_FINAL candidate at the first `Ã£â‚¬â€š` (non-string-final, since a second sentence follows) |
| Expected candidate class | Not pre-asserted |
| Comparison candidate | All candidates produced |
| Current baseline score | N/A Ã¢â‚¬â€ to be recorded |
| Current margin | N/A Ã¢â‚¬â€ to be recorded |
| Calibration question | With several CLAUSE candidates of equal nominal weight (35.0 each) in one paragraph, does a single flat CLAUSE value feel appropriate for every one of them, or does realistic enumeration suggest some clause boundaries are more "final" than others (a question for future consideration, not something this matrix proposes resolving now)? |
| Evidence requirement | Real pipeline; full candidate dump |
| Expected observation | Not asserted |
| Status criteria | `ANALYSIS ONLY` |

#### BC-12 Ã¢â‚¬â€ Natural PPT-note mixed set: explanatory transition

| Field | Value |
|---|---|
| Case ID | BC-12 |
| Purpose | A presentation-style transition note: wrap-up of one topic, a trailing pause, transition into the next topic |
| Input text | `Ã©â‚¬â„¢Ã¦Â¨Â£Ã¥Â°Â±Ã¨Â¬â€ºÃ¥Â®Å’Ã§Â¬Â¬Ã¤Â¸â‚¬Ã¥â‚¬â€¹Ã©Æ’Â¨Ã¥Ë†â€ Ã¤Âºâ€ Ã£â‚¬â€šÃ¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¯Â¼Å’Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¦ÂÂ¢Ã¤Â¸ÂªÃ¨Â§â€™Ã¥ÂºÂ¦Ã¤Â¾â€ Ã§Å“â€¹Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¥â€¦Â¶Ã¥Â¯Â¦Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥â€¢ÂÃ©Â¡Å’Ã©â€šâ€žÃ¦Å“â€°Ã¥ÂÂ¦Ã¤Â¸â‚¬Ã§Â¨Â®Ã¨Â§Â£Ã¦Â³â€¢Ã¯Â¼Å’Ã¦Ë†â€˜Ã¥â‚¬â€˜Ã¤Â¸â€¹Ã¤Â¸â‚¬Ã©Â ÂÃ¦Å“Æ’Ã¨ÂªÂªÃ¦ËœÅ½Ã£â‚¬â€š` |
| Target boundary | Real pipeline output Ã¢â‚¬â€ a SENTENCE_FINAL candidate at the first `Ã£â‚¬â€š` (non-string-final), a CLAUSE candidate after `Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ `, an ELLIPSIS candidate at the end of `Ã¢â‚¬Â¦Ã¢â‚¬Â¦`, and ordinary OTHER candidates throughout |
| Expected candidate class | Not pre-asserted |
| Comparison candidate | All candidates produced |
| Current baseline score | N/A Ã¢â‚¬â€ to be recorded |
| Current margin | N/A Ã¢â‚¬â€ to be recorded |
| Calibration question | Does a natural "wrap up / transition / trail off / continue" pattern Ã¢â‚¬â€ arguably the single most common speaker-note shape for slide-to-slide transitions Ã¢â‚¬â€ produce a score distribution that a Phase 2D consumer could sensibly use, given only the current four base values? |
| Evidence requirement | Real pipeline; full candidate dump |
| Expected observation | Not asserted |
| Status criteria | `ANALYSIS ONLY` |

## 10. Case Status Rules

Each case, once executed by a later round, must receive exactly one status:

- **REAL-PIPELINE** Ã¢â‚¬â€ evaluated using genuine, real `analyze_text_structure` Ã¢â€ â€™
  `observe_boundaries` Ã¢â€ â€™ `classify_boundary` output, and the target candidate(s) were
  produced as expected.
- **CASE ISSUE** Ã¢â‚¬â€ the target class/boundary is not representable by the current
  pipeline as written (e.g. string-final gap, unexpected span absorption, a targeted
  class not actually produced by this specific text). Must not be silently patched
  into a different case; record the mechanism, same discipline as every prior
  calibration round.
- **NEEDS DATA** Ã¢â‚¬â€ reachable in principle but the specific case as designed did not
  yield a clean, single-factor reading (e.g. an unremovable incidental modifier
  contaminates the comparison) Ã¢â‚¬â€ a revised case or additional probe is needed before
  a KEEP/INCREASE/DECREASE judgment can be made.
- **ANALYSIS ONLY** Ã¢â‚¬â€ diagnostic/exploratory cases (Ã‚Â§9's natural-note set) not
  designed to produce a strict pairwise verdict on their own; used to corroborate or
  contextualize the pairwise/multi-candidate findings.

No case may be marked with a PASS-style status merely because plugging the baseline
numbers into arithmetic produces the expected ordering Ã¢â‚¬â€ every case requires actual
real-pipeline evidence, per Ã‚Â§6 and Ã‚Â§9 of the round's governing instructions.

## 11. Required Evidence

For every case, a later execution round must record, at minimum, the same fields the
Protection Calibration script's dump format already provides for each candidate:
position, left/right character, `left_character_class`/`right_character_class`,
`punctuation_sequence_state`, `contains_sentence_final_punctuation`,
`structural_context.containing_spans`, the resulting `BoundaryClass`, and the final
score with its full modifier breakdown (base + any incidental transition/whitespace/
protection/sequence contribution). This is necessary even for a "pure" base-
classification case, because Ã‚Â§4's out-of-scope factors can appear incidentally and
must be visible, not silently assumed absent.

## 12. Calibration Interpretation

A later execution round must evaluate each of the three margins (Ã‚Â§5) as exactly one
of:

```
KEEP
INCREASE
DECREASE
NEED MORE DATA
```

No fixed numeric replacement value may be proposed at that stage either Ã¢â‚¬â€ e.g. the
correct shape of a finding is "CLAUSE's +35 margin over OTHER reads as too strong in
realistic enumeration-style notes (BC-11), where several ordinary commas end up tied
at the same score a genuinely important CLAUSE boundary would also receive, blurring
a distinction Phase 2D might want to preserve Ã¢â€ â€™ INCREASE... [or DECREASE / KEEP]",
never "so change +35 to +25." Any actual numeric adjustment is reserved for a
subsequent, separately-scoped Numeric Strategy design decision Ã¢â‚¬â€ this matrix and its
eventual execution only produce the KEEP/INCREASE/DECREASE/NEED MORE DATA judgment
and the qualitative reasoning behind it.

## 13. Completion Criteria

This matrix is complete because:

1. All three pairwise dominance relationships are covered (Ã‚Â§7.1Ã¢â‚¬â€œÃ‚Â§7.3).
2. Both textual directions are represented for each pairwise margin (BC-01/BC-02,
   BC-03/BC-04, BC-05/BC-06).
3. Multi-candidate competition is represented at three-way (BC-07, BC-08) and
   four-way (BC-09) scope.
4. Natural, unengineered PPT-note cases are represented (BC-10, BC-11, BC-12),
   spanning three different topical patterns (roadmap, agenda, transition) to avoid
   overfitting to one sentence shape.
5. Existing evidence is distinguished from new cases (Ã‚Â§14 below) rather than silently
   merged.
6. No production code was modified.
7. No existing calibration artifact (matrix, script, report, or the Numeric Baseline
   Decision) was modified.
8. The current baseline values (`+80`/`+65`/`+35`/`0`, and the out-of-scope
   `+15`/`+15`/`+10`/`-30`/`-30`/`-20`) remain unchanged throughout this document.
9. No threshold, floor, or normalization mechanism is introduced or implied anywhere
   in this matrix.
10. Every case defines the full data model (Ã‚Â§10 of the round's instructions: Case ID,
    Purpose, Input text, Target boundary, Expected candidate class, Comparison
    candidate, Current baseline score, Current margin, Calibration question, Evidence
    requirement, Expected observation, Status criteria) without hard-coding a
    conclusion, making the matrix directly executable by a later round without
    further design work.

## 14. Existing Evidence Reuse

The following prior findings are **existing evidence**, already collected against the
real pipeline in earlier rounds, and are reused here only as *context* for why the
ordering itself is not re-tested Ã¢â‚¬â€ they are not re-run, re-verified, or modified by
this matrix, and none of the new BC-01Ã¢â‚¬â€œBC-12 cases duplicates their exact text:

| Existing evidence | Source | Relevance |
|---|---|---|
| C05: SF (80.0, via trailing-context probe) vs CLAUSE (35.0), ÃŽâ€45.0, PASS | `docs/phase2c/calibration/reports/PHASE_2C_NUMERIC_CALIBRATION_ROUND1_REPORT.md` Ã‚Â§6 | Ordering SF>CLAUSE already observed; margin not the focus there |
| C06: ELLIPSIS (65.0, via probe) vs CLAUSE (35.0), ÃŽâ€30.0, PASS | Same | Ordering ELLIPSIS>CLAUSE already observed |
| C07: CLAUSE (35.0) vs OTHER (0.0), ÃŽâ€35.0, PASS | Same | Directly the CLAUSE-OTHER margin, but from one specific minimal-pair text (`Ã§Â¬Â¬Ã¤Â¸â‚¬Ã¯Â¼Å’Ã§Â¬Â¬Ã¤ÂºÅ’`-style), not a natural multi-sentence note Ã¢â‚¬â€ BC-01/BC-02 deliberately use natural note text instead |
| C08: SF (80.0, via probe) vs ELLIPSIS (65.0, via probe), ÃŽâ€15.0, PASS | Same | The narrowest margin, already observed to hold direction-wise but only via trailing-context probes on otherwise string-final matrix text, not natural prose |
| B01: SF (80.0) vs CLAUSE (35.0 or 45.0 with an embedded newline), Round 2 | `docs/phase2c/calibration/reports/PHASE_2C_NUMERIC_CALIBRATION_ROUND2_REPORT.md` Ã‚Â§6 | Reconfirms C05's finding, adds the newline-as-whitespace interaction (out of scope here) |
| B02: SF (80.0) vs ELLIPSIS (65.0), ÃŽâ€15.0, PASS | Same | Reconfirms C08 |
| C03 (Group C): ordinary CLAUSE (35.0) vs transition-only OTHER (15.0, borrowed from A04 since C01/C02 didn't expose a pure transition candidate), ÃŽâ€20.0 | Same | Not a base-classification margin (CLAUSE vs a positive-evidence-boosted OTHER, not plain OTHER) Ã¢â‚¬â€ out of this matrix's scope, cited only as a reminder that natural CJK/Latin text often fails to expose "pure" single-factor candidates, which is exactly why BC-01Ã¢â‚¬â€œBC-12 are written in single-language CJK text wherever possible |
| C30Ã¢â‚¬â€œC40 realistic-sentence review: genuine SF candidates never appeared for any single self-contained sentence (string-final gap); only CLAUSE (35.0/45.0) and lower-scoring candidates were directly observed | `docs/phase2c/calibration/reports/PHASE_2C_NUMERIC_CALIBRATION_ROUND1_REPORT.md` Ã‚Â§10 | Directly motivates every SENTENCE_FINAL-targeting case in this matrix (BC-05, BC-06, BC-08, BC-09, BC-10, BC-12) deliberately appending a following sentence so the target `Ã£â‚¬â€š` is not string-final |
| `docs/phase2c/decisions/PHASE_2C_NUMERIC_BASELINE_DECISION.md` Ã‚Â§9 | Baseline decision | Already classifies `SENTENCE_FINAL`/`ELLIPSIS`/`CLAUSE`/transition/whitespace as "provisional baseline," not "behaviorally supported" Ã¢â‚¬â€ this matrix is the mechanism by which that status could change for the base classes |

**New calibration cases** (this matrix): BC-01 through BC-12, all using freshly
written realistic text not appearing verbatim in any prior round's case list.

## 15. Anticipated Difficulty / Reachability Notes

Recorded here for the benefit of whichever round executes this matrix, per the known,
already-documented pipeline behaviors from prior rounds:

- **String-final gap (affects BC-05, BC-06, BC-08, BC-09, BC-10, BC-12):** every
  SENTENCE_FINAL-targeting case appends a trailing sentence specifically to avoid the
  known "no candidate after the final character" gap. If an execution round finds a
  target `Ã£â‚¬â€š` is still unreachable for some other reason, it must be marked `CASE
  ISSUE`, not silently patched.
- **Natural CJK/Latin spacing (informs the CJK-only design choice):** Calibration
  Round 2's Group C found that natural Chinese/English text almost always inserts a
  space at a language boundary, which fragments a would-be `+15` transition candidate
  into two `+10` whitespace candidates instead. Since positive evidence is out of
  scope this round, all BC-01Ã¢â‚¬â€œBC-12 texts are written in single-language CJK to
  sidestep this entirely Ã¢â‚¬â€ but BC-11's parenthetical and any incidental Latin
  abbreviation, if it creeps into a later revision, should be watched for the same
  effect.
- **Multiple CLAUSE candidates at equal score (BC-11):** an enumeration-style
  sentence produces several CLAUSE candidates, all nominally 35.0 Ã¢â‚¬â€ this is expected
  pipeline behavior (per Phase 2B's flat, non-positional CLAUSE rule), not a defect,
  but it is flagged in BC-11's own calibration question as worth surfacing.
- **BC-09's four-way case is the highest-value but highest-risk case in this matrix**
  Ã¢â‚¬â€ it depends on a single paragraph cleanly producing all four target classes
  without any of them being absorbed, leak-contaminated, or string-final. If it does
  not work as written, a later round should not force it; it should report exactly
  which class failed to materialize as a `CASE ISSUE` and fall back on the pairwise
  (Ã‚Â§7) and three-way (BC-07/BC-08) cases for evidence instead.
- **Parenthetical content (BC-11):** `Ã¯Â¼Ë†Ã©â‚¬â„¢Ã©Æ’Â¨Ã¥Ë†â€ Ã¦Â¯â€Ã¨Â¼Æ’Ã©â€¡ÂÃ¨Â¦ÂÃ¯Â¼â€°` uses a `paired_delimiter`
  span. Base classification does not treat `paired_delimiter` specially (only
  `technical`/`atomic` block CLAUSE, per the frozen Phase 2B design), so this is not
  expected to interfere with the target CLAUSE/SENTENCE_FINAL candidates outside it,
  but it is called out since a later round should confirm this rather than assume it.
