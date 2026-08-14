# Phase 2C Positive Evidence Calibration — Round 1 Report

## 1. Executive Summary

**Calibration scope:** all 12 case groups (PE-01–PE-12) defined in
`docs/PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_MATRIX.md` were executed against the
real, unmodified pipeline. **Cases attempted:** 40 case-slots (38 distinct real-pipeline
executions; 2 slots — PE-04-OTHER, PE-06-OTHER — cross-referenced from PE-01-01/PE-05-01
per the matrix's own instruction not to re-derive already-covered evidence; 2 additional
slots — PE-07-01c, PE-07-02c — have no independently-constructable input text, per the
matrix's own note, and are resolved analytically from the PE-07-01b/02b data rather than
run separately). **Successfully executed (pipeline ran, real candidates observed):** all
40. **CASE ISSUE:** 5 (PE-04-CLAUSE, PE-04-ELLIPSIS, PE-04-SENTENCE_FINAL, PE-07-01c,
PE-07-02c — all confirmed structurally unreachable, not pipeline failures).
**CONTAMINATED:** 3 (PE-09-03, PE-09-04, PE-09-05). **NEEDS DATA:** 0.
**ANALYSIS ONLY:** 9 (PE-08-01, PE-08-02, PE-10-01, PE-10-02, PE-10-03, PE-11-01,
PE-11-02a, PE-11-02b, PE-11-03). The remainder are CLEAN (19) or INTERACTION (4:
PE-06-CLAUSE, PE-06-ELLIPSIS, PE-06-SENTENCE_FINAL, PE-12).

This section states scope and counts only. The evidence itself is in §4–§14; the
numeric decisions derived from it are in §15, not here.

## 2. Baseline Under Test

| Factor | Value | Status |
|---|---:|---|
| CJK → LATIN | +15 | PROVISIONAL |
| LATIN → CJK | +15 | PROVISIONAL |
| Whitespace | +10 | PROVISIONAL |

| BoundaryClass | Score | Status |
|---|---:|---|
| SENTENCE_FINAL | +80 | LOCKED |
| ELLIPSIS | +65 | LOCKED |
| CLAUSE | +35 | LOCKED |
| OTHER | 0 | LOCKED |

## 3. Execution Method

`scripts/calibrate_phase2c_protection_round1.py` was reused **unmodified**
(`sys.path.insert(0, 'scripts'); import calibrate_phase2c_protection_round1 as cal`),
calling its existing `dump()` function once per case text. This function runs each
input through the real, unmodified pipeline (`analyze_text_structure` →
`observe_boundaries` → `classify_boundary` → `calibration_score()`) and prints, for
every real candidate: position, left/right character, character classes, punctuation
sequence state, sentence-final evidence, containing structural spans, `BoundaryClass`,
base score, transition bonus and label, whitespace bonus, technical/atomic flags,
protection penalty, INTERNAL flag, sequence penalty, and final score — exactly the
fields this round's report requires. No new calibration script was created; a small,
temporary, non-repository driver (`/tmp/run_pe_calibration.py`, listing each case ID
and its exact input text from the matrix and calling `cal.dump()` on each) was written
purely to batch the 38 calls and is **not** part of the repository — see §21.

All 40 case-slots' exact input texts were taken verbatim from
`docs/PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_MATRIX.md` (cross-checked via a
programmatic backtick-span extraction against the matrix file before execution, the
same verbatim-accuracy practice used in the Base Classification Calibration Round 1
execution). No candidate's `BoundaryClass`, transition evidence, or whitespace evidence
was manually assigned anywhere in this round. The one place a code-level fact is cited
without a fresh pipeline run for each of its three instances (§9, §17) is a direct
reading of `calibration_score()`'s own transition/whitespace precondition logic
(`scripts/calibrate_phase2c_protection_round1.py` lines ~78–86) — this is not a
synthetic fixture; it is the real, unmodified scoring function's source, cited to
explain *why* the empirically-observed PE-04/PE-07 results come out the way they do.
No arithmetic sanity check using a hand-built fixture was needed in this round; none
was performed.

## 4. Case-by-Case Results

All scores below are the real, unmodified pipeline's output, captured in
`/tmp/pe_calibration_raw.txt` (temporary, not part of the repository).

### 4.1 PE-01 — CJK → LATIN Individual Evidence

| Case ID | Input | Target boundary | Class | Base | Trans | WS | Protection | Score | Actual Status | Observation |
|---|---|---|---|---:|---:|---:|---:|---:|---|---|
| PE-01-01 | `這個功能使用Python處理資料。` | `用｜P` (pos 6) | OTHER | 0.0 | +15.0 (CJK→LATIN) | 0.0 | 0.0 | 15.0 | CLEAN | Matches predicted; comparison `OTHER` elsewhere = 0.0 |
| PE-01-02 | `我們用Excel做報表，很方便。` | `用｜E` (pos 3) | OTHER | 0.0 | +15.0 (CJK→LATIN) | 0.0 | 0.0 | 15.0 | CLEAN | Independent confirmation |
| PE-01-03 | `系統採用Docker部署服務。` | `用｜D` (pos 4) | OTHER | 0.0 | +15.0 (CJK→LATIN) | 0.0 | 0.0 | 15.0 | CLEAN | Independent confirmation |

Predicted status (matrix): CLEAN for all three. **Actual matches predicted exactly** in
all three cases.

### 4.2 PE-02 — LATIN → CJK Individual Evidence

| Case ID | Input | Target boundary | Class | Base | Trans | WS | Protection | Score | Actual Status | Observation |
|---|---|---|---|---:|---:|---:|---:|---:|---|---|
| PE-02-01 | `Python可以處理資料。` | `n｜可` (pos 6) | OTHER | 0.0 | +15.0 (LATIN→CJK) | 0.0 | 0.0 | 15.0 | CLEAN | Matches predicted |
| PE-02-02 | `Excel能做報表，很方便。` | `l｜能` (pos 5) | OTHER | 0.0 | +15.0 (LATIN→CJK) | 0.0 | 0.0 | 15.0 | CLEAN | Independent confirmation |
| PE-02-03 | `Docker能部署服務。` | `r｜能` (pos 6) | OTHER | 0.0 | +15.0 (LATIN→CJK) | 0.0 | 0.0 | 15.0 | CLEAN | Independent confirmation |

Predicted status: CLEAN for all three. **Actual matches predicted exactly.**

### 4.3 PE-03 — Transition Symmetry

| Case ID | Input | Target A (CJK→LATIN) | Target B (LATIN→CJK) | A Score | B Score | Actual Status | Observation |
|---|---|---|---|---:|---:|---|---|
| PE-03-01 | `這是Python語言。` | `是｜P` (pos 2) | `n｜語` (pos 8) | 15.0 | 15.0 | CLEAN | Identical score, both from the same sentence, no incidental modifier on either side |
| PE-03-02 | `我們用Docker部署。` | `用｜D` (pos 3) | `r｜部` (pos 9) | 15.0 | 15.0 | CLEAN | Same |
| PE-03-03 | `系統採用API接口。` | `用｜A` (pos 4) | `I｜接` (pos 7) | 15.0 | 15.0 | CLEAN | Same |

Predicted status: CLEAN for all three, with an explicit note that "same numeric value"
and "evidence-supported symmetry" are different claims. **All three cases show A and B
scoring identically (15.0 = 15.0) with zero incidental-modifier asymmetry between the
two directions in the same sentence** — this is the strongest form of symmetry
evidence this matrix could produce (same-sentence, same-context, both directions).
Full analysis in §7.

### 4.4 PE-05 — Whitespace Individual Evidence

| Case ID | Input | Combination | Candidates around the space | Actual Status | Observation |
|---|---|---|---|---|---|
| PE-05-01 | `這個 功能很好用。` | CJK+ws+CJK | pos2 `個｜(sp)`=10.0; pos3 `(sp)｜功`=10.0 | CLEAN | Two candidates, both `OTHER`+`Whitespace`, no transition on either (both sides CJK, not CJK/LATIN pairing) |
| PE-05-02 | `我們使用 Python處理資料。` | CJK+ws+Latin | pos4 `用｜(sp)`=10.0; pos5 `(sp)｜P`=10.0 | CLEAN | No transition evidence on either candidate — confirms EE-3 independently |
| PE-05-03 | `使用Python 處理資料。` | Latin+ws+CJK | pos8 `n｜(sp)`=10.0; pos9 `(sp)｜處`=10.0 | CLEAN | Same finding, reverse direction |
| PE-05-04 | `我們設定 API Key 之後就完成了。` | Latin+ws+Latin | 4 candidate-pairs around the 3 spaces, all exactly 10.0 | CLEAN | Confirms flat, non-stacking `+10` even across 3 separate space characters in one text |

Predicted status: CLEAN for all four. **Actual matches predicted exactly**; PE-05-02/03
additionally reconfirm EE-3 (no pure transition candidate when a space separates the
languages) independently of the Round 2 text that originally found it.

### 4.5 PE-07 — Transition + Whitespace

| Case ID | Input | Finding | Actual Status | Observation |
|---|---|---|---|---|
| PE-07-01a | `我們使用Python分析資料。` | `用｜P`=15.0 (transition only, no ws) | CLEAN | Baseline for the triad |
| PE-07-01b | `我們使用 Python分析資料。` | `用｜(sp)`=10.0, `(sp)｜P`=10.0 (no transition on either) | CLEAN | Whitespace variant of the same underlying switch — no `+25` anywhere |
| PE-07-01c | *(no separate text — see §3, §11)* | n/a | **CASE ISSUE** | Confirmed structurally unreachable: no single real candidate can carry both a transition and a whitespace bonus (see §9/§17 for the code-level reason) |
| PE-07-02a | `Python分析資料很快。` | `n｜分`=15.0 (transition only, no ws) | CLEAN | Baseline for the reverse-direction triad |
| PE-07-02b | `Python 分析資料很快。` | `n｜(sp)`=10.0, `(sp)｜分`=10.0 (no transition on either) | CLEAN | Same finding, reverse direction |
| PE-07-02c | *(no separate text)* | n/a | **CASE ISSUE** | Same structural reason as PE-07-01c |

Predicted status: CLEAN for the a/b pairs; CASE ISSUE (predicted) for the c rows.
**Actual matches predicted exactly** in all six slots. Full analysis in §9.

### 4.6 PE-04 — Transition attached to Base Classification

| Case ID | Input | Target boundary | Class | Base | Trans | Score | Actual Status | Observation |
|---|---|---|---|---:|---:|---:|---|---|
| PE-04-OTHER | *(cross-referenced from PE-01-01)* | `用｜P` | OTHER | 0.0 | +15.0 | 15.0 | CLEAN (reused) | Not independently re-run — matrix explicitly allows reuse |
| PE-04-CLAUSE | `這個功能，Python處理資料。` | `，｜P` (pos 5) | CLAUSE | 35.0 | **0.0 (None)** | 35.0 | **CASE ISSUE (confirmed)** | Predicted unreachable per EE-6; confirmed: the comma is `LC=punctuation`, `RC=latin` — no transition bonus applies |
| PE-04-ELLIPSIS | `我們稍後說明……Python範例會展示。` | `…｜P` (pos 8, END state) | ELLIPSIS | 65.0 | **0.0 (None)** | 65.0 | **CASE ISSUE (confirmed)** | Predicted unreachable by the same structural reasoning as EE-6; confirmed: `LC=punctuation`, `RC=latin`, no transition bonus |
| PE-04-SENTENCE_FINAL | `這是重點。Python範例如下：` | `。｜P` (pos 5) | SENTENCE_FINAL | 80.0 | **0.0 (None)** | 80.0 | **CASE ISSUE (confirmed)** | Same structural reasoning; confirmed: `LC=punctuation`, `RC=latin`, no transition bonus |

Predicted status: CASE ISSUE for CLAUSE/ELLIPSIS/SENTENCE_FINAL. **All three
predictions are confirmed exactly** — every one of the three candidates scores its
plain base value with zero transition contribution, despite the character immediately
to its right being a Latin letter. Full analysis in §10.

### 4.7 PE-06 — Whitespace attached to Base Classification

| Case ID | Input | Target boundary | Class | Base | WS | Score | Actual Status | Observation |
|---|---|---|---|---:|---:|---:|---|---|
| PE-06-OTHER | *(cross-referenced from PE-05-01)* | `個｜(sp)` | OTHER | 0.0 | +10.0 | 10.0 | CLEAN (reused) | Not independently re-run |
| PE-06-CLAUSE | `接下來， 我們介紹重點。` | `，｜(sp)` (pos 4) | CLAUSE | 35.0 | +10.0 | 45.0 | **INTERACTION (reachable, confirmed)** | Independently reproduces EE-6/C14's `35+10=45.0` finding on new text |
| PE-06-ELLIPSIS | `我們稍後再談…… 好，開始吧。` | `…｜(sp)` (pos 8, END state) | ELLIPSIS | 65.0 | +10.0 | 75.0 | **INTERACTION (reachable, confirmed)** | Resolves the "genuinely open question" from the matrix: **yes**, `ELLIPSIS`+`Whitespace` is reachable |
| PE-06-SENTENCE_FINAL | `這是重點。 接下來介紹範例。` | `。｜(sp)` (pos 5) | SENTENCE_FINAL | 80.0 | +10.0 | 90.0 | **INTERACTION (reachable, confirmed)** | Resolves the same open question for `SENTENCE_FINAL`: **yes**, reachable |

Predicted status: CLEAN (reused) for OTHER; genuinely open (no prediction) for
CLAUSE/ELLIPSIS/SENTENCE_FINAL. **All three open questions are now resolved by direct
evidence**: unlike Transition, Whitespace co-occurs with every one of the four locked
base classes. Full analysis in §10.

### 4.8 PE-09 — Technical / Product Terminology

| Case ID | Input | Transition/Whitespace finding | Incidental protection finding | Actual Status |
|---|---|---|---|---|
| PE-09-01 | `這個簡報使用PowerPoint製作。` | `用｜P`=15.0 (CJK→LATIN); `t｜製`=15.0 (LATIN→CJK) | none (`tech=False`, `atomic=False` throughout) | CLEAN |
| PE-09-02 | `這個系統使用API串接資料。` | `用｜A`=15.0 (CJK→LATIN); `I｜串`=15.0 (LATIN→CJK) | none | CLEAN |
| PE-09-03 | `我們目前使用iPhone 15進行測試。` | `用｜i`=15.0 (CJK→LATIN), clean; whitespace pair around `iPhone 15`=10.0 each, clean | digit run `15` (pos14, `1｜5`): `atomic=True`, `-30.0` | **CONTAMINATED** (for the digit-interior candidate only) — transition and whitespace candidates unaffected |
| PE-09-04 | `系統版本是v1.2.3，請確認。` | `是｜v`=15.0 (CJK→LATIN), clean; clause comma `，｜請`=35.0, clean | interior `1.2` positions (pos7, pos8): `atomic=True`, `-30.0` each; **unexpected additional finding**: pos10 (`.｜3`, the second period) shows `containing=[]` (no covering span at all) and classifies `SENTENCE_FINAL`, `80.0` — see §11/§18 | **CONTAMINATED** for the version-string interior; transition and clause candidates unaffected; the pos10 finding is recorded as **OUT OF CURRENT SCOPE** (§18), not a Positive Evidence question |
| PE-09-05 | `我們比較GPT-4和其他模型的表現。` | `較｜G`=15.0 (CJK→LATIN), clean, sits immediately **before** the technical span begins | `GPT-4` (pos5–8): `tech=True` (`technical/identifier`), `-30.0` at each of 4 interior positions | **CONTAMINATED** for the `GPT-4` interior; transition candidate unaffected (occurs at a position outside the technical span) |

Predicted status: CLEAN for PE-09-01/02; CONTAMINATED or NEEDS DATA for PE-09-03/04/05
depending on where Phase 1's actual span boundaries fall. **Actual: PE-09-01/02 confirmed
CLEAN exactly as predicted; PE-09-03/04/05 confirmed CONTAMINATED, and in every one of
the three the specific transition/whitespace candidate targeted by the case is itself
clean and separable from the contamination** — no case needed to fall back to NEEDS
DATA. Full analysis in §11.

### 4.9 PE-10 — Punctuation Interaction

| Case ID | Input | Punctuation-anchored candidate | Nearby Positive Evidence candidate | Actual Status |
|---|---|---|---|---|
| PE-10-01 | `這個功能，Python可以處理。` | `，｜P`=35.0 (CLAUSE, no transition — same finding as PE-04-CLAUSE) | `n｜可`=15.0 (LATIN→CJK), 6 characters later | ANALYSIS ONLY |
| PE-10-02 | `這個問題我們稍後說明……Python範例如下。` | `…｜P`=65.0 (ELLIPSIS END, no transition — same finding as PE-04-ELLIPSIS) | `n｜範`=15.0 (LATIN→CJK), 6 characters later | ANALYSIS ONLY |
| PE-10-03 | `這是重點。Python範例如下：這是第二個重點。` | `。｜P`=80.0 (SENTENCE_FINAL, no transition — same finding as PE-04-SENTENCE_FINAL) | `n｜範`=15.0 (LATIN→CJK), 6 characters later | ANALYSIS ONLY |

Predicted status: ANALYSIS ONLY for all three. **Confirmed**: in every case, both the
punctuation-anchored candidate and the nearby Positive Evidence candidate score exactly
their independently-expected values — `35.0`/`65.0`/`80.0` for the punctuation-anchored
one, `15.0` for the Positive Evidence one — with no visible interaction between them.
Full analysis in §12.

### 4.10 PE-11 — Negative / Non-Useful Whitespace

| Case ID | Input | Finding | Actual Status |
|---|---|---|---|
| PE-11-01 | `我們使用 Microsoft Word 編輯文件。` | The internal `Microsoft｜Word` space scores `10.0` (pos14/15), mechanically identical to the CJK↔Latin switch spaces around the whole phrase (pos4/5, pos19/20) | ANALYSIS ONLY |
| PE-11-02a | `這個功能將於2026年上線。` (no spaces) | `2026` is one atomic span (3 interior positions, `-30.0` each); no whitespace evidence anywhere | ANALYSIS ONLY |
| PE-11-02b | `這個功能將於 2026 年上線。` (spaces added) | Whitespace candidates (`10.0` each) appear cleanly on either side of the atomic-protected `2026`, never overlapping with the atomic penalty | ANALYSIS ONLY |
| PE-11-03 | `這是第一行内容 這是接續的內容，語意上是同一句話。` | The line-wrap-style internal space scores `10.0` (pos7/8), mechanically identical to any other whitespace boundary; the later clause comma is unaffected (`35.0`) | ANALYSIS ONLY |

Predicted status: ANALYSIS ONLY for all four. **Confirmed** — every whitespace
candidate in this group mechanically scores the flat `+10` exactly as EE-4 predicts,
regardless of whether the whitespace is semantically meaningful. Full analysis in §13.

### 4.11 PE-08 — Mixed CJK / Latin PPT Notes (natural)

| Case ID | Input | Notable findings | Actual Status |
|---|---|---|---|
| PE-08-01 | `這一頁比較兩個工具：Python和R都可以用於資料分析，但是我們team比較熟悉Python。` | Three consecutive transition candidates around the single-letter token `R` (`n｜和`=15.0 LATIN→CJK, `和｜R`=15.0 CJK→LATIN, `R｜都`=15.0 LATIN→CJK); informal loanword `team` embedded with no space (`們｜t`=15.0 CJK→LATIN, `m｜比`=15.0 LATIN→CJK); clause comma unaffected (`，｜但`=35.0) | ANALYSIS ONLY |
| PE-08-02 | `我們計畫下一步導入CI/CD流程，先用GitHub Actions做測試，之後再評估其他方案。` | `CI/CD` produces **no** technical/atomic flag anywhere (`containing=[]` throughout, unlike `GPT-4` in PE-09-05) — see §18; `GitHub Actions` shows a clean transition into `G` (`用｜G`=15.0) and a whitespace pair inside the two-word product name (`b｜(sp)`=10.0, `(sp)｜A`=10.0), plus a clean transition out (`s｜做`=15.0); two clause commas both plain `35.0` | ANALYSIS ONLY |

Predicted status: ANALYSIS ONLY for both. **Confirmed**, with an additional structural
observation (the `CI/CD` non-detection) recorded as OUT OF CURRENT SCOPE in §18.

### 4.12 PE-12 — Integrated Positive-Evidence Candidate Set

Input: `這個功能還在開發中，我們使用Python和Docker做測試……細節之後會公布。接下來會展示 Demo 範例。`
(len=55)

Complete candidate set for all non-zero-modifier positions (all unlisted positions are
plain `OTHER`, `0.0`, exactly as in every prior integrated case):

| Position | L｜R | Class | Base | Trans | WS | Protection | Score |
|---:|---|---|---:|---:|---:|---:|---:|
| 10 | ，｜我 | CLAUSE | 35.0 | 0.0 | 0.0 | 0.0 | 35.0 |
| 14 | 用｜P | OTHER | 0.0 | +15.0 (CJK→LATIN) | 0.0 | 0.0 | 15.0 |
| 20 | n｜和 | OTHER | 0.0 | +15.0 (LATIN→CJK) | 0.0 | 0.0 | 15.0 |
| 21 | 和｜D | OTHER | 0.0 | +15.0 (CJK→LATIN) | 0.0 | 0.0 | 15.0 |
| 27 | r｜做 | OTHER | 0.0 | +15.0 (LATIN→CJK) | 0.0 | 0.0 | 15.0 |
| 31 | …｜… | OTHER | 0.0 | 0.0 | 0.0 | INTERNAL −20.0 | −20.0 |
| 32 | …｜細 | ELLIPSIS | 65.0 | 0.0 | 0.0 | 0.0 | 65.0 |
| 40 | 。｜接 | SENTENCE_FINAL | 80.0 | 0.0 | 0.0 | 0.0 | 80.0 |
| 46 | 示｜(sp) | OTHER | 0.0 | 0.0 | +10.0 | 0.0 | 10.0 |
| 47 | (sp)｜D | OTHER | 0.0 | 0.0 | +10.0 | 0.0 | 10.0 |
| 51 | o｜(sp) | OTHER | 0.0 | 0.0 | +10.0 | 0.0 | 10.0 |
| 52 | (sp)｜範 | OTHER | 0.0 | 0.0 | +10.0 | 0.0 | 10.0 |

**Actual status: INTERACTION** (as predicted — this case is intentionally a combination
case, not CLEAN). All four locked base classes are present exactly once each (`CLAUSE`
35.0, `ELLIPSIS` 65.0, `SENTENCE_FINAL` 80.0 non-string-final, and the pervasive `OTHER`
0.0 baseline), two independent `CJK↔LATIN` transition pairs appear cleanly (around
`Python` and `Docker`), and one whitespace-mediated pair appears cleanly (around
`Demo`), with a single incidental `INTERNAL` (`-20.0`) at the expected ellipsis-run
interior position. No score reversal, no impossible candidate combination, and no
protection dominance were observed anywhere in this text. Full analysis in §14.

## 5. CJK → LATIN Results

PE-01 (§4.1) produced exactly `15.0` on the intended `OTHER`+`CJK→LATIN` candidate in
all three independent, realistic no-space cases, with zero incidental modifiers in any
of them. PE-03 (§4.3) reproduced the same `15.0` reading three more times as the "A"
side of its symmetry pairs. PE-09-01/02 (§4.8) reproduced it twice more with
recognizable real-world product/acronym names. PE-08's natural paragraphs (§4.11)
reproduced it four more times incidentally in unengineered text. Across nine
independent CLEAN observations and four more incidental ones, `+15` for `CJK→LATIN`
was never contradicted, never reversed, and never observed at any value other than
exactly `15.0`.

## 6. LATIN → CJK Results

PE-02 (§4.2) produced exactly `15.0` on the intended `OTHER`+`LATIN→CJK` candidate in
all three independent cases. PE-03 reproduced it as the "B" side of its symmetry pairs
(three more). PE-04-OTHER/PE-09/PE-10/PE-08 collectively surface several more
incidental `LATIN→CJK` observations, all exactly `15.0`. As with CJK→LATIN, this value
was never contradicted or observed at a different magnitude anywhere in this round's
evidence.

## 7. Transition Symmetry

**Numeric equality** (both factors currently defined as `+15`) is a fact about the
provisional baseline, not evidence. **Evidence-supported symmetry** is a separate,
stronger claim this round specifically tested for in PE-03: three independent
sentences, each containing one Latin word sandwiched between CJK text with no spaces
on either side, so both the `CJK→LATIN` candidate and the `LATIN→CJK` candidate for the
same embedded word are observed from the same real-pipeline run. In all three cases
(§4.3), both candidates scored exactly `15.0`, with no incidental modifier present on
either side that would differentiate them (identical `tech=False`, `atomic=False`,
`ws=0.0`, `internal=False` on both). PE-08-01's `R`-sandwich (§4.11) additionally shows
`LATIN→CJK` then `CJK→LATIN` then `LATIN→CJK` all scoring `15.0` back-to-back around a
single-letter token, in unengineered natural text.

This constitutes real, same-context, real-pipeline evidence that the two directions
behave identically under the current scoring formula — not merely that they happen to
share a baseline number. No case in this round exposed any asymmetry between the two
directions. See §16 for the formal Symmetry Decision.

## 8. Whitespace Results

PE-05 (§4.4) confirms, across all four character-class combinations
(CJK+ws+CJK, CJK+ws+Latin, Latin+ws+CJK, Latin+ws+Latin), that a single whitespace
character produces exactly two `OTHER`+`Whitespace` candidates (one on each side),
each scoring exactly `10.0`, with the bonus never stacking even across three separate
spaces in one text (PE-05-04). PE-06 (§4.7) additionally confirms Whitespace is the
only Positive Evidence factor that **does** combine with all four locked base classes
on a single real candidate: `CLAUSE`+Whitespace = `45.0`, `ELLIPSIS`+Whitespace =
`75.0`, `SENTENCE_FINAL`+Whitespace = `90.0`, in addition to the already-known
`OTHER`+Whitespace = `10.0`. This is a genuinely new, round-1 finding — the matrix
explicitly left the `ELLIPSIS`/`SENTENCE_FINAL` cases as "genuinely open questions,"
and both are now answered: yes, reachable, and the arithmetic (`base+10`) holds exactly
in every case observed.

## 9. Transition + Whitespace

PE-07 (§4.5) confirms, in both directions (CJK→LATIN and LATIN→CJK), that the
no-space variant of a given language switch scores `15.0` (transition only) and the
whitespace variant of the *same underlying switch* scores `10.0`+`10.0` split across
two candidates (whitespace only, no transition on either) — never a single `25.0`
candidate. This independently reproduces EE-5 (D04) on new text.

**A single candidate cannot carry both Transition and Whitespace evidence.** This is
not merely an empirical absence in the specific texts tried — reading
`calibration_score()`'s own logic confirms it is a structural property of the current
scoring formula: `transition_bonus` requires `left_character_class` and
`right_character_class` to be `{CJK, LATIN}` in one order or the other, while
`whitespace_bonus` requires one of those same two fields to equal `WHITESPACE`. Since
a single character class field cannot simultaneously be `CJK`/`LATIN` and
`WHITESPACE`, no real candidate can ever satisfy both preconditions at once. `+25` is
therefore not merely unobserved in this round's cases — it is unreachable by
construction under the current formula. This is recorded as a **structural finding**
(§17), not converted into a numeric decision — per this round's explicit instruction,
the absence of `+25` does not by itself justify any KEEP/INCREASE/DECREASE verdict on
either `+15` or `+10` individually.

## 10. Base × Positive Evidence

**Reachable:** `OTHER`+Transition (`15.0`), `OTHER`+Whitespace (`10.0`),
`CLAUSE`+Whitespace (`45.0`), `ELLIPSIS`+Whitespace (`75.0`),
`SENTENCE_FINAL`+Whitespace (`90.0`) — all confirmed by direct real-pipeline
observation in §4.6/§4.7.

**Unreachable (confirmed CASE ISSUE):** `CLAUSE`+Transition, `ELLIPSIS`+Transition,
`SENTENCE_FINAL`+Transition. All three were predicted unreachable in the matrix (per
EE-6's structural reasoning) and all three are now **confirmed**, not merely assumed:
PE-04-CLAUSE/ELLIPSIS/SENTENCE_FINAL (§4.6) each placed a Latin character immediately
after the relevant punctuation mark with no space, and in every case the resulting
candidate scored exactly its plain base value (`35.0`/`65.0`/`80.0`) with `trans=0.0
(None)` — the transition bonus never fires. The reason, confirmed by source
inspection (§9): `CLAUSE`, `ELLIPSIS` (END-state), and `SENTENCE_FINAL` candidates all
have the relevant punctuation mark as one side's character, and `PUNCTUATION` is never
one of the two classes (`CJK`, `LATIN`) the transition bonus checks for — this makes
the "attached transition" scenario for these three classes unreachable by the same
structural mechanism as the Transition+Whitespace finding in §9, not by coincidence.

This means the arithmetic values `50` (`35+15`), `80` (`65+15`), and `95` (`80+15`)
that would result *if* this combination were reachable are, like PE-07's `+25`,
never-occurring hypotheticals under the current architecture — not calibration targets.

## 11. Technical / Product Terminology

PE-09-01/PE-09-02 (§4.8) confirm that ordinary product names and acronyms without
digits or special characters produce clean `+15` transitions with zero incidental
protection evidence — `PowerPoint`/`API` did not trigger any technical/atomic span.

PE-09-03 (`iPhone 15`), PE-09-04 (`v1.2.3`), and PE-09-05 (`GPT-4`) all did trigger
incidental protection (`atomic` for the two numeric cases, `technical` for the
hyphenated identifier), confirming the matrix's CONTAMINATED prediction. In every one
of the three, however, the actually-targeted Positive Evidence candidate (the
transition into the product term, or the surrounding whitespace) sits at a position
the pipeline does **not** flag as protected, and is therefore separable and usable as
clean evidence in its own right, exactly as the matrix's own "a clean candidate
elsewhere in the same input may still be used, clearly distinguished" instruction
anticipated.

**Unplanned finding, recorded factually, not acted on (see §18):** PE-09-04's version
string `v1.2.3`, embedded in running text, shows Phase 1's `atomic/numeric` span
covering only the `1.2` portion — not the full three-segment `1.2.3`. The second
period (between `2` and `3`) is not covered by any structural span at all, and the
bare-ASCII-period fallback (correctly, per the Round B fix, since Round B's fix only
suppresses the fallback for characters that genuinely *are* covered by some span)
applies to it, producing a `SENTENCE_FINAL`, `80.0` candidate in the middle of the
version string. This is a Phase 1/Base-Classification-layer observation about
structural span coverage of multi-segment version identifiers — it is unrelated to
Transition or Whitespace, is not evidence for changing any Positive Evidence value,
and is not investigated further in this round.

No protection value was recalibrated anywhere in this section.

## 12. Punctuation Interaction

PE-10-01/02/03 (§4.9) each placed a `CLAUSE`/`ELLIPSIS`/`SENTENCE_FINAL` candidate a
few characters away from an independent Positive Evidence candidate in the same text.
In every case, both candidates scored exactly their independently-expected values —
neither one's score shifted, dropped, or elevated due to the other's proximity or
magnitude. This confirms, directly and observably (not merely by architectural
assumption), that Phase 2C candidates are scored independently of their neighbors, for
every pairing this round tested. No segmentation behavior is inferred from this —
per this round's explicit instruction, these observations describe only the scoring
layer's independence, not what a hypothetical Phase 2D consumer would do with it.

## 13. Non-Useful Whitespace

**Mechanical evidence** (§4.10): in all four PE-11 cases, whitespace scores exactly
`+10` per candidate, with no distinction in the pipeline's output between "obviously
useful" whitespace (e.g. the CJK↔Latin switch spaces) and "not obviously useful"
whitespace (e.g. the internal space in `Microsoft Word`, or a typographic space around
a digit run). The mechanism does not know or care about semantic usefulness — it only
checks character class.

**Semantic usefulness** is a separate, qualitative observation this round records but
does not convert into a numeric finding: a person writing subtitles would essentially
never choose to cut a proper-noun product name in half, yet the pipeline assigns that
position the same score as any other whitespace boundary. This is recorded as an
`ANALYSIS ONLY` observation per §15's explicit instruction not to collapse "some
whitespace positions are poor subtitle boundaries" into "`+10` is wrong" — the former
is a Phase 2D consumption question (how a future segmentation step should treat ties
or near-ties among same-scoring candidates), not a Phase 2C magnitude question this
round's evidence can resolve.

## 14. Integrated Case

PE-12 (§4.12) is treated strictly as a diagnostic, integrated observation, not as
independent evidence for any single numeric decision, per this round's explicit
instruction. It corroborates, without adding new claims beyond, what §5–§10 already
established from cleaner pairwise/matched cases: both transition directions and
whitespace all appear at their expected values, all four base classes coexist without
interference, and the one incidental `INTERNAL` evidence present is confined to its
own distinct, non-target candidate exactly as in every prior calibration round. No
reversal, no unexpected interaction, no protection dominance, and no impossible
candidate combination were found anywhere in this text.

## 15. Numeric Calibration Decisions

| Factor | Current Value | Decision | Evidence |
|---|---:|---|---|
| CJK → LATIN | +15 | **KEEP** | Nine independent CLEAN real-pipeline observations (PE-01 ×3, PE-03 ×3 same-sentence, PE-09 ×2, plus incidental PE-08 occurrences), all scoring exactly `15.0` with zero incidental contamination; never reversed or found disproportionate against `OTHER` (0) in any observed context |
| LATIN → CJK | +15 | **KEEP** | Same evidentiary strength and pattern as CJK→LATIN (PE-02 ×3, PE-03 ×3, plus incidental occurrences), all exactly `15.0` |
| Whitespace | +10 | **KEEP** | Mechanically consistent, non-stacking `+10` across all four PE-05 character-class combinations and all four PE-06 base-class attachments (`OTHER`/`CLAUSE`/`ELLIPSIS`/`SENTENCE_FINAL`), confirmed arithmetically exact (`base+10`) in every reachable combination; the PE-11 semantic-usefulness observation (§13) is recorded but, per this round's explicit instruction, is not by itself sufficient grounds for INCREASE or DECREASE — it is a Phase 2D consumption question, not a magnitude question this round's mechanical evidence contradicts |

No replacement numeric value is proposed anywhere in this document, for any factor.

## 16. Symmetry Decision

- **CJK → LATIN:** KEEP
- **LATIN → CJK:** KEEP
- **Symmetry: SUPPORTED** — not merely because both factors currently share the value
  `+15`, but because PE-03's three same-sentence, same-context matched pairs (§4.3, §7)
  and PE-08-01's natural back-to-back three-transition sequence (§4.11) show both
  directions producing identical scores (`15.0` = `15.0`) with identical incidental-
  modifier profiles (none) in every case observed. No asymmetry was found anywhere in
  this round's evidence.

## 17. Structural Findings

1. **Transition + Whitespace cannot co-occur on a single real candidate.** Confirmed
   both empirically (PE-07, §9) and by direct inspection of
   `calibration_score()`'s precondition logic: the transition check requires
   `{CJK, LATIN}` on both sides; the whitespace check requires `WHITESPACE` on at
   least one side; these are mutually exclusive character-class conditions. `+25`
   (`15+10`) is therefore structurally unreachable, not merely unobserved.
2. **Transition cannot co-occur with `CLAUSE`, `ELLIPSIS` (END-state), or
   `SENTENCE_FINAL` on a single real candidate**, confirmed empirically (PE-04, §10)
   for all three classes independently. The mechanism is the same character-class
   precondition as finding 1: these three classes' candidates always have the relevant
   punctuation mark (class `PUNCTUATION`) on one side, and `PUNCTUATION` is never
   `CJK`/`LATIN`.
3. **Whitespace, unlike Transition, does co-occur with every one of the four locked
   base classes**, confirmed empirically (PE-06, §10) for `CLAUSE` (`45.0`), `ELLIPSIS`
   (`75.0`), and `SENTENCE_FINAL` (`90.0`), in addition to the already-known `OTHER`
   (`10.0`). This asymmetry between how Transition and Whitespace interact with the
   base layer is itself worth naming explicitly for any future round designing further
   cross-factor cases.
4. Neither finding 1 nor finding 2 is converted into a numeric decision in this round,
   per explicit instruction (§8, §12 of the round contract).

## 18. Out-of-Scope Findings

- **PE-09-04's version-string span-coverage gap** (§11): Phase 1's `atomic/numeric`
  span for `v1.2.3` embedded in running text covers only `1.2`, leaving the second
  period uncovered and subject to the bare-ASCII-fallback `SENTENCE_FINAL`
  classification. This belongs to Base Classification / Phase 1 structural detection,
  not Positive Evidence. Not acted on.
- **PE-08-02's `CI/CD` non-detection** (§4.11): unlike `GPT-4` (PE-09-05), the
  hyphen-free, slash-containing token `CI/CD` produced no `technical`/`atomic` flag
  anywhere in its span. This is a Protection-layer / Phase 1 pattern-detection
  observation, not a Positive Evidence finding. Not acted on; Protection values remain
  unchanged.
- **PE-11's semantic-usefulness observation** (§13): whether some whitespace positions
  are poor subtitle boundaries is, per this round's own framing, a **FUTURE DESIGN
  QUESTION** that borders on paragraph-position/phrase-integrity weighting — explicitly
  excluded from this round's scope (§4 of the round contract) and not incorporated into
  any scoring recommendation here.
- No case in this round produced any observation suggesting a locked Base
  Classification value (`SENTENCE_FINAL`/`ELLIPSIS`/`CLAUSE`/`OTHER`) itself needs
  reconsideration; the version-string finding above is about span *coverage*, not
  about whether `SENTENCE_FINAL=+80` is the wrong magnitude.

## 19. Calibration Confidence

**Strong** for CJK→LATIN and LATIN→CJK individually and for their symmetry: multiple
independent, clean, real-pipeline, same-context observations, zero contradicting
evidence, zero reversal, high repeatability (identical results across nine and more
independent texts per direction).

**Strong** for Whitespace's mechanical behavior (flat, non-stacking `+10`, reachable
against all four base classes): confirmed across eight independent cases (PE-05 ×4,
PE-06 ×4) with exact arithmetic matches in every reachable combination.

**Moderate** for Whitespace's overall numeric appropriateness once semantic usefulness
is considered: the mechanical evidence is strong, but this round deliberately did not
(and was instructed not to) resolve the qualitative question raised in §13, so
"appropriately calibrated" here means "mechanically consistent and unreversed," not
"semantically optimal for every context."

**Not assessed / out of scope** for whether the *absence* of the `CLAUSE`/`ELLIPSIS`/
`SENTENCE_FINAL`+Transition combination, or the absence of `+25`, represents a design
gap Phase 2D should care about — this round confirms the structural facts (§17) but
takes no position on their downstream desirability, per instruction.

## 20. Conclusion

Round 1 establishes, with real-pipeline evidence rather than assumption: (1) both
`CJK→LATIN` and `LATIN→CJK` transitions consistently and reliably score exactly `+15`
in every clean context tested, with no observed asymmetry between the two directions;
(2) `Whitespace` consistently and reliably scores exactly `+10`, non-stacking, and —
newly established this round — combines additively with every one of the four locked
base classes, not just `OTHER`; (3) Transition, by contrast, structurally cannot
combine with `CLAUSE`, `ELLIPSIS`, or `SENTENCE_FINAL` on a single candidate, and
cannot combine with Whitespace on a single candidate either — both are architectural
facts of the current scoring formula, not numeric findings; (4) incidental Technical/
Atomic protection appears in realistic technical terminology but never contaminates
the specific transition/whitespace candidate a case targets, in every instance
observed.

What remains unresolved: whether Whitespace's flat `+10` is the right *design* for
positions a human would never choose as a subtitle break (§13, an explicitly
out-of-scope qualitative question this round); whether the structural unreachability
of `CLAUSE`/`ELLIPSIS`/`SENTENCE_FINAL`+Transition and of Transition+Whitespace matters
for a future Phase 2D consumer (§17, explicitly not decided here); and the two
out-of-scope Phase 1/Protection observations in §18, neither of which this round is
positioned to resolve. No numeric value was changed, and per §15, none of the evidence
gathered points toward a needed change — all three factors are recommended `KEEP`.

## 21. Files Changed

**Created:** `docs/PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_ROUND1_REPORT.md` (this
document) — the sole new repository file.

**Temporary, non-repository helper** (not part of the repository, reported per §22 of
the round contract): `/tmp/run_pe_calibration.py` — a batch driver that imports the
existing, unmodified `scripts/calibrate_phase2c_protection_round1.py` and calls its
`dump()` function once per matrix case; and `/tmp/pe_calibration_raw.txt`, the captured
raw output. Neither file exists inside the repository working tree, and neither should
be assumed to belong there.

**Confirmed unmodified** (checksummed before and after this round's work):
`src/text_structure.py`, `src/boundary_observation.py`,
`src/boundary_classification.py`, `src/subtitle_segmenter.py`,
`scripts/calibrate_phase2c_protection_round1.py`, `scripts/calibrate_phase2c_round1.py`,
`scripts/calibrate_phase2c_round2.py`,
`docs/PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_MATRIX.md`,
`docs/PHASE_2C_NUMERIC_BASELINE_DECISION.md`,
`docs/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_MATRIX.md`,
`docs/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_ROUND1_REPORT.md`, and every other
existing repository file. No test file was modified. No production code was modified.

**Note:** `docs/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_DECISION.md`, referenced by
this round's own instructions as an existing file, was confirmed (again) not to exist
in the repository — same discrepancy already recorded in
`docs/PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_MATRIX.md` §1. Not created here, since
this round's file-creation scope is limited to the report named in §22 of the round
contract.
