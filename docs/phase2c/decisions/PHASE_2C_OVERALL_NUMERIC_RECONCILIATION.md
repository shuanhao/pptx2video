# Phase 2C Overall Numeric Reconciliation

**Status:** Reconciliation / Final Design Review — documentation only, no code/test/script/matrix/decision changes
**Phase:** Phase 2C — Numeric Calibration (Overall Reconciliation)
**Purpose:** Consolidate every already-locked Phase 2C numeric decision into one coherent
picture and determine whether the resulting scoring model is internally consistent,
hierarchically sound, and ready for production implementation.

---

## 1. Executive Summary

Phase 2C's numeric model consists of three independently calibrated layers — Base
Classification, Positive Evidence, and Protection — plus a small set of interaction
rules governing how they combine. Each layer has already been through its own
dedicated calibration round and is individually locked:

- Base Classification (`SENTENCE_FINAL=+80`, `ELLIPSIS=+65`, `CLAUSE=+35`, `OTHER=0`) —
  provisional baseline per `PHASE_2C_NUMERIC_BASELINE_DECISION.md`, with all three
  pairwise margins independently confirmed `KEEP` by
  `PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_ROUND1_REPORT.md`.
- Positive Evidence (`CJK→LATIN=+15`, `LATIN→CJK=+15`, `Whitespace=+10`) — formally
  `LOCKED` by `PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_DECISION.md`.
- Protection (`Technical=-30`, `Atomic=-30`, `INTERNAL=-20`, strongest-only
  Technical/Atomic + additive INTERNAL) — behaviorally supported per
  `PHASE_2C_NUMERIC_BASELINE_DECISION.md` §9 and `PHASE_2C_PROTECTION_POST_CORRECTION_VERIFICATION.md`.

This reconciliation finds the three layers **consistent with each other** on every
combination that has actually been observed against the real pipeline: Base
Classification dominance holds in all reachable cases, Protection outweighs Positive
Evidence in every case where the two have been jointly observed, and no reachable score
reversal was found.

However, the reconciliation also surfaces a structural gap that no single prior round
was scoped to address: **Positive Evidence and Protection have never been directly
observed co-occurring on the same real candidate.** In every case gathered so far
(Positive Evidence Round 1's PE-09 cases, Protection Round 1's P01–P15), a transition or
whitespace candidate and a technical/atomic-protected candidate always turned out to be
two *different* positions in the text, never the same one. This is different from the
`Transition + Whitespace` case, which was *proven* structurally impossible by inspecting
`calibration_score()`'s field preconditions; `Positive Evidence + Protection`
co-occurrence has only been *not observed*, not proven impossible. This reconciliation
treats that distinction carefully (§8, §9, §13) rather than either assuming safety or
manufacturing new evidence.

Also carried forward and formally reconciled here: Calibration Round 2's `D04` finding
(a whitespace-adjacent CJK/Latin boundary scores lower than the equivalent no-space
transition boundary, `10.0` vs `15.0`) is now understood, in light of the Positive
Evidence Decision's structural findings, as a **candidate-topology** fact (adding a
space removes the transition candidate and replaces it with a whitespace-only one) 
rather than a numeric defect — but it remains a live design input for Phase 2D
candidate selection (§13).

No numeric value is changed, proposed for change, or reopened by this document.

**Overall gate result (§15, §16): READY WITH DOCUMENTATION FOLLOW-UP.** The locked
numeric values are internally consistent everywhere they have been tested; the one
identified gap (Positive Evidence × Protection joint reachability) is a documentation
and evidence-coverage gap, not a contradiction, and does not block moving into
production scoring implementation — but it should be explicitly tracked before or during
that implementation, not silently assumed away.

## 2. Scope and Non-Goals

**In scope:** reading and cross-referencing every completed Phase 2C calibration
artifact; reconstructing the combined scoring model conceptually; evaluating score
hierarchy, dominance, reversal risk, reachability, and the seven numeric-model
properties (§12); producing one new reconciliation document.

**Out of scope / explicitly not performed:**

- No numeric value is changed, increased, decreased, or reproposed.
- No new calibration round was executed; no new pipeline evidence was gathered. This
  document synthesizes only evidence that already exists in the repository's
  documentation.
- No production scoring code, scoring engine, or Phase 2D code was written.
- No existing Matrix, Calibration Report, Calibration Script, or Design Decision was
  modified.
- No git operation of any kind was performed.

This is a reconciliation of *already-locked* decisions, not a fourth Positive Evidence
round or a second Base Classification round.

## 3. Authoritative Inputs

All of the following were read in full or in relevant part before this analysis:

| Document | Role |
|---|---|
| `docs/PHASE_2C_NUMERIC_BASELINE_DECISION.md` | Establishes Numeric Baseline v0.1 (all locked values), the Technical/Atomic strongest-only + INTERNAL-additive interaction rule, and the signed-relative-score strategy. |
| `docs/PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_MATRIX.md` | Designs the PE-01–PE-12 case groups. |
| `docs/PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_ROUND1_REPORT.md` | Executes the PE matrix against the real pipeline; primary empirical source for Positive Evidence findings. |
| `docs/PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_DECISION.md` | Formally locks CJK→LATIN, LATIN→CJK, Whitespace, transition symmetry, whitespace non-stacking, and the structural reachability findings (Transition+Whitespace unreachable, Transition×Base reachability, Whitespace×Base reachability). |
| `docs/PHASE_2C_CALIBRATION_MATRIX.md` | Original (v0.1→v0.2, overwritten in place) general calibration matrix. |
| `docs/PHASE_2C_CALIBRATION_ROUND1_REPORT.md` | Earliest general calibration round; establishes the base/positive numeric values as first used. |
| `docs/PHASE_2C_CALIBRATION_ROUND2_REPORT.md` | Second general calibration round; source of the `D04` transition-vs-whitespace finding and the Group E Technical/Transition ranking check. |
| `docs/PHASE_2C_PROTECTION_CALIBRATION_MATRIX.md` | Designs the P01–P15 protection case set and the strongest-only interaction hypothesis. |
| `docs/PHASE_2C_PROTECTION_CALIBRATION_ROUND1_REPORT.md` | Executes the protection matrix; establishes the full P01–P15 pairwise ranking summary and the primary protection hierarchy. |
| `docs/PHASE_2C_PROTECTION_POST_CORRECTION_VERIFICATION.md` | Re-verifies protection behavior after the Phase 2A ASCII-period upstream fix; confirms `Technical+INTERNAL=-50` on a clean `OTHER`-class candidate; confirms P12 remains a genuine `CASE ISSUE`; issues the "READY FOR NUMERIC CALIBRATION" (Protection-family-scoped) readiness statement. |
| `docs/PHASE_2C_ASCII_PERIOD_UPSTREAM_CORRECTION_DECISION.md` | Referenced by the Post-Correction Verification for the upstream fix context; inspected for protection-value consistency (confirmed consistent, no base-class values restated). |
| `docs/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_MATRIX.md` | Designs the BC-01–BC-12 base classification case set. |
| `docs/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_ROUND1_REPORT.md` | Executes the BC matrix; confirms all three pairwise margins (`35`/`30`/`15`) `KEEP` with zero `CASE ISSUE`. |

**Dedicated Phase 2A / 2B design or decision documents:** repository search (`ls docs/`,
keyword grep for `boundary|observation|classification|2a|2b`) found no file named or
scoped as a standalone "Phase 2A design decision" or "Phase 2B design decision" separate
from the Base Classification calibration documents already listed above. Phase 2A/2B's
design intent is instead recorded inline in `PHASE_2C_NUMERIC_BASELINE_DECISION.md` §8
("Phase Responsibility Boundary") and in the module docstrings of
`src/text_structure.py`, `src/boundary_observation.py`, and
`src/boundary_classification.py` (not modified, read for context only). This is recorded
as a factual discrepancy from what a reader might expect to exist, per this round's own
instruction not to assume a document exists merely because it is plausible — it is
**not** blocking, and no document was created to fill this gap.

**`docs/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_DECISION.md`** — referenced by two
prior rounds' own contracts and confirmed absent in both; re-confirmed absent here via
`ls` (exit code 2). This document treats
`docs/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_ROUND1_REPORT.md`'s own `KEEP` findings,
together with `PHASE_2C_NUMERIC_BASELINE_DECISION.md`'s original adoption, as the basis
for treating the Base Classification layer as locked/fixed for this reconciliation's
purposes — the same non-blocking handling used by the two prior rounds that encountered
this same gap.

## 4. Reconstructed Numeric Model

### 4.1 Base Classification

| BoundaryClass | Score | Status |
|---|---:|---|
| `SENTENCE_FINAL` | +80 | Provisional baseline; all three pairwise margins `KEEP` |
| `ELLIPSIS` | +65 | Provisional baseline; `KEEP` |
| `CLAUSE` | +35 | Provisional baseline; `KEEP` |
| `OTHER` | 0 | Provisional baseline; `KEEP` |

Margins confirmed by `PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_ROUND1_REPORT.md` §9:
`CLAUSE−OTHER=35`, `ELLIPSIS−CLAUSE=30`, `SENTENCE_FINAL−ELLIPSIS=15`.

### 4.2 Positive Evidence

| Evidence | Score | Status |
|---|---:|---|
| `CJK → LATIN` | +15 | LOCKED |
| `LATIN → CJK` | +15 | LOCKED (symmetric with CJK→LATIN, evidence-supported per PE-03) |
| `Whitespace` | +10 | LOCKED (flat, candidate-level, non-stacking) |

### 4.3 Protection

| Evidence | Score | Status |
|---|---:|---|
| `Technical` | -30 | Behaviorally supported |
| `Atomic` | -30 | Behaviorally supported |
| `INTERNAL` | -20 | Behaviorally supported |

**Interaction rule** (recovered exactly, not reinterpreted, from
`PHASE_2C_NUMERIC_BASELINE_DECISION.md` §5 and confirmed by
`PHASE_2C_PROTECTION_CALIBRATION_ROUND1_REPORT.md` P04/P11):

```
Technical + Atomic             → strongest-only: max_penalty(Technical, Atomic) = -30 (not -60)
Technical / Atomic + INTERNAL  → independent additive stacking: e.g. Technical + INTERNAL = -50
```

Note: `scripts/calibrate_phase2c_round1.py` and `scripts/calibrate_phase2c_round2.py`
implement an *additive* Technical+Atomic rule (`-60` when both apply) and are explicitly
recorded as **HISTORICAL**, not authoritative, per
`PHASE_2C_NUMERIC_BASELINE_DECISION.md` §10.3 — they predate the strongest-only decision
and were not written to test that specific interaction. This reconciliation uses the
strongest-only rule throughout, as that is what the Numeric Baseline Decision formally
adopted; it does not modify either historical script.

### 4.4 Numeric Strategy

```
Relative Boundary Score = Base Classification Score
                         + Positive Evidence (where structurally reachable)
                         + Protection Evidence (where structurally reachable)
```

This is a **signed relative score** — not a probability, not a normalized value, not a
cut threshold. Explicitly absent, confirmed still absent by every document reviewed:

- No normalization
- No threshold (`score >= X → cut` / `score <= X → reject`)
- No class-specific hard floor

Numeric possibility (arithmetic sum) is explicitly distinguished throughout this
document from structural reachability (whether the real candidate model can ever produce
a `BoundaryCandidate` exhibiting that combination) and from actual observed real-pipeline
combinations (whether a calibration round has directly witnessed it). Three different
tiers of confidence are used consistently in §9 and elsewhere:

1. **Confirmed reachable** — directly observed against the real pipeline in a completed
   calibration round.
2. **Structurally unreachable** — proven impossible by inspecting the exact field
   preconditions in `calibration_score()` (e.g. `left_character_class`/
   `right_character_class` cannot simultaneously be `{CJK,LATIN}` and `WHITESPACE`).
3. **Not observed / untested** — neither directly confirmed nor structurally proven
   impossible; a genuine gap in the evidence base, not a finding either way.

## 5. Score Hierarchy Review

| Comparison | Values | Margin | Source |
|---|---|---:|---|
| `SENTENCE_FINAL` vs `ELLIPSIS` | 80 vs 65 | 15 | BC-05/BC-06, `KEEP` |
| `ELLIPSIS` vs `CLAUSE` | 65 vs 35 | 30 | BC-03/BC-04, `KEEP` |
| `CLAUSE` vs `OTHER` | 35 vs 0 | 35 | BC-01/BC-02, `KEEP` |
| Base Classification vs Transition | `OTHER=0`→`+15` at most | Transition alone never exceeds `CLAUSE` (35) | PE-01/PE-04-OTHER; Transition only attaches to `OTHER` (§6.3 below) |
| Base Classification vs Whitespace | `+10` flat addend | Whitespace alone never exceeds `CLAUSE` (35); Whitespace-on-`CLAUSE` (45) exceeds plain `CLAUSE` but not `ELLIPSIS` (65) | PE-06, all four classes reachable |
| Protection vs Positive Evidence | `-30`/`-20` vs `+15`/`+10` | Protection magnitude (20–30) exceeds Positive Evidence magnitude (10–15) in every case where a *hypothetical* single candidate carried both | No real candidate observed carrying both simultaneously (§8, §9) — see caveat below |
| Protection vs Base Classification | `-30`/`-20` vs `0`–`80` | Protection can pull an `OTHER` candidate to `-50` (confirmed, P11 post-correction) but has never been observed acting on a `CLAUSE`/`ELLIPSIS`/`SENTENCE_FINAL` candidate | P01–P15 evidence is `OTHER`-class only; see §7, §9 |

The three Base Classification margins (35, 30, 15) are all strictly larger than any
single reachable Positive Evidence addend (10 or 15) and larger than the reachable
Protection magnitudes acting alone on `OTHER` (20 or 30, or 50 combined). This means
that, **on the reachable evidence gathered to date**, Positive Evidence and Protection
are individually "smaller" than a Base Classification margin — the intended relative
hierarchy (Base Classification as the primary signal, Positive Evidence and Protection
as secondary modifiers) holds numerically wherever it has actually been tested.

The narrowest margin, `SENTENCE_FINAL − ELLIPSIS = 15`, is numerically equal to the
`CJK→LATIN`/`LATIN→CJK` Positive Evidence value and smaller than `Whitespace` stacked
twice. This coincidence was already flagged as a design-attention point in
`PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_ROUND1_REPORT.md` §5.3 and §10 (that round's
own evidence did not show the margin failing, but recorded it as "the one most likely to
be judged too thin" and based on only two natural-order cases). This reconciliation does
not add new evidence on this point and does not treat the coincidence itself as a defect
— it is recorded here as a place where the hierarchy has the least numeric headroom, not
as a contradiction.

## 6. Base Classification Dominance

The intended ordering `SENTENCE_FINAL > ELLIPSIS > CLAUSE > OTHER` is confirmed by
`PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_ROUND1_REPORT.md` in isolation (§5) and jointly
in single-paragraph, multi-candidate contexts (§6, BC-09 exercises all four classes in
one realistic paragraph with zero `CASE ISSUE`).

Whether Positive Evidence can reverse this hierarchy on any **real reachable candidate**:

| Combination | Score | Compared to next class up | Reversal? |
|---|---:|---|---|
| `OTHER + Transition` | 15 | still below `CLAUSE` (35) | No |
| `OTHER + Whitespace` | 10 | still below `CLAUSE` (35) | No |
| `CLAUSE + Whitespace` | 45 | above plain `CLAUSE` (35), still below `ELLIPSIS` (65) | No |
| `ELLIPSIS + Whitespace` | 75 | above plain `ELLIPSIS` (65), still below (hypothetical) `SENTENCE_FINAL+Whitespace` | No |
| `SENTENCE_FINAL + Whitespace` | 90 | highest reachable score in the current model | No — this is the ceiling, not a reversal |

No reachable combination causes a lower Base Classification (plus its maximum reachable
Positive Evidence) to exceed a higher Base Classification's own plain score. The closest
approach is `CLAUSE + Whitespace = 45` vs `ELLIPSIS = 65` (still a 20-point gap) and
`ELLIPSIS + Whitespace = 75` vs `SENTENCE_FINAL = 80` (still a 5-point gap, the smallest
margin between an enhanced lower class and the next plain higher class in the entire
model). This 5-point gap is close enough to be worth naming explicitly as a place where
the hierarchy has little headroom, though it is **not** a reversal — `75 < 80` holds.

Unreachable combinations (`CLAUSE + Transition = 50`, `ELLIPSIS + Transition = 80`,
`SENTENCE_FINAL + Transition = 95`) are **not** included in this dominance analysis as
real behavior, per `PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_DECISION.md` §6.3's explicit
"hypothetical / unreachable" labeling. If they were somehow reachable in a future
candidate-model redesign, `ELLIPSIS + Transition = 80` would exactly tie
`SENTENCE_FINAL`'s plain score, and `CLAUSE + Transition = 50` would fall inside the gap
between `CLAUSE` and `ELLIPSIS` — both worth flagging as a **DESIGN QUESTION** for any
future round that revisits candidate-model architecture, not as a current defect (§13).

**Conclusion: Base Classification dominance holds on all reachable evidence.**

## 7. Protection Dominance

Protection's job is to suppress structurally dangerous boundaries (inside technical
identifiers, atomic numeric tokens, or internal punctuation runs) regardless of what
other evidence might otherwise favor a cut there.

Confirmed reachable Protection combinations, all on `OTHER`-class candidates (P01–P15,
`PHASE_2C_PROTECTION_CALIBRATION_ROUND1_REPORT.md`):

| Combination | Score | Source |
|---|---:|---|
| `OTHER + Technical` | -30 | P03 |
| `OTHER + Atomic` | -30 | P02 |
| `OTHER + Technical + Atomic` (strongest-only) | -30 | P04 — confirmed equal to either single factor, not `-60` |
| `OTHER + INTERNAL` | -20 | P08 |
| `OTHER + Technical + INTERNAL` | -50 | P11, confirmed on a clean `OTHER`-class candidate in `PHASE_2C_PROTECTION_POST_CORRECTION_VERIFICATION.md` §6 (the original Protection Round 1 P11 evidence was leak-contaminated by an upstream `SENTENCE_FINAL` misclassification and scored `+30.0`, not `-50.0`; the Post-Correction round supersedes it with a clean `-50.0` result) |
| `OTHER + Atomic + INTERNAL` | — | **CASE ISSUE, unreachable** — no real candidate found in four attempted constructions (P12); recorded as an architecture/reachability gap, not evidence against `INTERNAL=-20` |

Every confirmed Protection combination was tested against `OTHER` (base `0`), never
against `CLAUSE`/`ELLIPSIS`/`SENTENCE_FINAL`. The pairwise ranking summary (P05–P10)
confirms Protection sits well below Positive-Evidence-only and Base-Classification-only
candidates in every comparison attempted:

```
Transition (+15) vs Technical (-30):  Δ45, Transition wins — expected, no reversal
CLAUSE (+35) vs Technical (-30):      Δ65, CLAUSE wins — expected, no reversal
CLAUSE (+35) vs Atomic (-30):         Δ65, CLAUSE wins — expected, no reversal
OTHER (0) vs INTERNAL (-20):          Δ20, OTHER wins — expected, no reversal
Transition (+15) vs INTERNAL (-20):   Δ35, Transition wins — expected, no reversal
CLAUSE (+35) vs INTERNAL (-20):       Δ55, CLAUSE wins — expected, no reversal
```

**Important caveat, carried through from §5:** every one of these pairwise comparisons
was performed on **two separate candidates** (one carrying Positive Evidence, a
different one carrying Protection), never on one candidate carrying both. This is
consistent with what Positive Evidence Round 1 separately found: PE-09-03 (`iPhone 15`)
and PE-09-05 (`GPT-4`) each placed a transition or whitespace candidate immediately
adjacent to a technical/atomic span, and in every case the Positive-Evidence-bearing
candidate itself came back `tech=False, atomic=False` — clean, not contaminated — while
the protection-tagged candidate was a distinct position. No case in either round's
evidence shows Protection and Positive Evidence values summed on one candidate.

This means Protection's ability to suppress Positive Evidence specifically (as opposed
to suppressing a plain `OTHER` candidate) is **not yet demonstrated by any real
evidence** — not because it has failed, but because the combination has never been
observed to occur. This is recorded as a genuine gap in §9 and §13, not resolved here.

**Conclusion: Protection dominance holds on all reachable evidence involving `OTHER`
alone. Protection's dominance specifically over co-occurring Positive Evidence on a
single candidate remains untested.**

## 8. Score Reversal Analysis

No reachable score reversal (a structurally weaker Base Classification outscoring a
stronger one) was found anywhere in the evidence base. Specifically inspected:

| Candidate | Score | Would it reverse a stronger class? |
|---|---:|---|
| `SENTENCE_FINAL + Whitespace` | 90 | No — this is the model's ceiling |
| `ELLIPSIS + Whitespace` | 75 | No — still below `SENTENCE_FINAL` (80) |
| `CLAUSE + Whitespace` | 45 | No — still below `ELLIPSIS` (65) |
| `OTHER + Transition` | 15 | No — still below `CLAUSE` (35) |
| `OTHER + Transition + Protection` | N/A | **Not reachable/not observed** — Transition and Protection have never been confirmed on the same candidate (§7); this specific combination cannot be evaluated from real evidence at all, so no reversal claim can be made either way |
| Strongest confirmed Protection combination (`OTHER + Technical + INTERNAL = -50`) | -50 | Not a reversal risk — it only ever lowers an `OTHER`-class candidate further below zero, moving it further from, not closer to, any higher class |

**`D04` (Calibration Round 2, `PHASE_2C_CALIBRATION_ROUND2_REPORT.md` §5 Group D,
§7):** the no-space transition candidate (`中文｜English` = `15.0`) outscores the
whitespace-adjacent variant of the *same conceptual boundary* (`中文 ｜ English` = best
real candidate `10.0`). At the time Round 2 was written, this was flagged `NEED MORE
DATA` for both `CJK→LATIN` and `Whitespace` because the interaction was not yet
understood. In light of the Positive Evidence Decision's later, dedicated findings
(§6.2 of that document: Transition and Whitespace are **structurally unreachable on the
same candidate**, confirmed via PE-07's matched triads), `D04` is now understood as a
**candidate-topology** fact, not a single-candidate score reversal: adding a space does
not add to an existing candidate's score, it **replaces** the transition candidate with
a different, weaker whitespace-only candidate at a nearby position. Each candidate's own
score (`15.0` or `10.0`) is computed correctly by the formula; there is no arithmetic
defect. This reconciliation treats `D04` as **explained, not dangerous, but still
practically relevant to Phase 2D** (§13) — the choice of which candidate exists at a
given text position is a Phase 2D candidate-selection concern, not a Phase 2C scoring
defect.

**`E04` (Calibration Round 2, Group E):** confirms Technical protection (`-30` or
`-60` under the old additive script) does not exceed a modest positive-evidence boundary
(`15.0`) in the wrong direction — `15.0 > -30.0`, the intended direction. No reversal.

**Conclusion: no confirmed score reversal exists anywhere in the evidence base.** The
one area where a reversal *cannot be ruled out* because it has never been tested is
Positive Evidence + Protection co-occurring on one candidate (§7, §9) — this is reported
as an untested gap, not as a suspected or confirmed reversal.

## 9. Reachability Matrix

| Combination | Status | Score if reachable | Evidence |
|---|---|---:|---|
| `OTHER` + Transition | **Reachable, confirmed** | 15 | PE-01, PE-04-OTHER |
| `OTHER` + Whitespace | **Reachable, confirmed** | 10 | PE-05, PE-06-OTHER |
| `CLAUSE` + Whitespace | **Reachable, confirmed** | 45 | PE-06-CLAUSE |
| `ELLIPSIS` + Whitespace | **Reachable, confirmed** | 75 | PE-06-ELLIPSIS |
| `SENTENCE_FINAL` + Whitespace | **Reachable, confirmed** | 90 | PE-06-SENTENCE_FINAL |
| `CLAUSE` + Transition | **Structurally unreachable** | hypothetical 50 | PE-04-CLAUSE, confirmed `CASE ISSUE`; mechanism: CLAUSE's left-adjacent character is always `PUNCTUATION`, never `CJK`/`LATIN` |
| `ELLIPSIS` + Transition | **Structurally unreachable** | hypothetical 80 | PE-04-ELLIPSIS, same mechanism |
| `SENTENCE_FINAL` + Transition | **Structurally unreachable** | hypothetical 95 | PE-04-SENTENCE_FINAL, same mechanism |
| Transition + Whitespace (any base class) | **Structurally unreachable** | hypothetical +25 addend | PE-07; proven via `calibration_score()`'s mutually exclusive character-class preconditions |
| `OTHER` + Technical | **Reachable, confirmed** | -30 | P03 |
| `OTHER` + Atomic | **Reachable, confirmed** | -30 | P02 |
| `OTHER` + Technical + Atomic | **Reachable, confirmed** | -30 (strongest-only) | P04 |
| `OTHER` + INTERNAL | **Reachable, confirmed** | -20 | P08 |
| `OTHER` + Technical + INTERNAL | **Reachable, confirmed** | -50 | P11 (post-correction, clean) |
| `OTHER` + Atomic + INTERNAL | **CASE ISSUE — unreachable in all 4 attempted constructions** | hypothetical -50 | P12 |
| `OTHER` + Transition + Technical (or Atomic) | **Not observed / untested** | hypothetical -15 | PE-09-05 (`GPT-4`): transition candidate observed clean (`tech=False`) immediately adjacent to, but outside, the technical span; no code-level proof of impossibility exists (unlike Transition+Whitespace) |
| `OTHER` + Whitespace + Technical (or Atomic) | **Not observed / untested** | hypothetical -20 | PE-09-03 (`iPhone 15`): whitespace candidates observed clean, adjacent to but outside the atomic span |
| `CLAUSE` + Whitespace + INTERNAL | **Not observed / untested** | hypothetical 25 | Not directly tested by PE-06 or any protection case; PE-06-ELLIPSIS's text contains an ellipsis run whose interior `INTERNAL` candidate (if present) was not reported as coinciding with the targeted Whitespace candidate |
| `ELLIPSIS` + Whitespace + INTERNAL | **Not observed / untested** | hypothetical 55 | Same gap as above |
| `CLAUSE`/`ELLIPSIS`/`SENTENCE_FINAL` + Technical (no other modifier) | **Not observed / untested** | hypothetical 5 / 35 / 50 | No case in P01–P15 or PE-01–PE-12 places a Technical/Atomic span directly on a `CLAUSE`/`ELLIPSIS`/`SENTENCE_FINAL`-classified candidate |

This matrix is intentionally scoped to the combinations the round contract named plus
the ones this reconciliation's own analysis surfaced as materially relevant — it is not
an exhaustive combinatorial enumeration.

**The most significant finding of this matrix is the last four rows and the
`Transition/Whitespace + Technical/Atomic` rows above:** the current evidence base has
never directly tested Protection acting on a `CLAUSE`/`ELLIPSIS`/`SENTENCE_FINAL`
candidate, nor Protection co-occurring with Positive Evidence on one candidate. These
are recorded as **NOT OBSERVED / REQUIRES FUTURE DATA**, deliberately distinct from both
"reachable, confirmed" and "structurally unreachable" — the honest status is that nobody
has looked yet, and the two directly-relevant real-world case attempts (PE-09-03,
PE-09-05) both happened to land the Positive-Evidence candidate just outside the
protected span rather than inside it.

## 10. Practical Score Range

**Reachable / observed positive range:** `0` (`OTHER`, plain) to `90`
(`SENTENCE_FINAL + Whitespace`, confirmed PE-06-SENTENCE_FINAL). The strongest realistic
positive candidate observed anywhere in the evidence base is `90`.

**Reachable / observed negative range:** `0` (no protection) to `-50`
(`OTHER + Technical + INTERNAL`, confirmed P11 post-correction). The strongest realistic
protected candidate observed anywhere in the evidence base is `-50`.

**Theoretical arithmetic extrema (NOT reachable, reported only to distinguish from the
above):**

```
Maximum arithmetic sum:  SENTENCE_FINAL + Transition + Whitespace = 80 + 15 + 10 = 105
  — doubly unreachable: Transition cannot attach to SENTENCE_FINAL (§9), and
    Transition + Whitespace cannot co-occur on any candidate regardless of base class (§9).
    105 is not a real number the current model can ever produce.

Minimum arithmetic sum (under the OLD additive Technical+Atomic rule, not the locked
strongest-only rule): OTHER − Technical − Atomic − INTERNAL = 0 − 30 − 30 − 20 = −80
  — not reachable even under the additive rule (P12: Atomic+INTERNAL is itself
    unreachable), and not the locked rule in any case (§4.3): under the locked
    strongest-only rule the arithmetic floor for a fully-protected OTHER candidate is
    −50, which IS the confirmed reachable floor above.
```

The practical range actually exercised by the real pipeline to date is **`-50` to
`+90`**, a span of 140 points. This is the range that should inform any future Phase 2D
work reasoning about relative score magnitudes — not the unreachable arithmetic extrema.

## 11. Interaction Review

| Interaction | Status | Note |
|---|---|---|
| Base + Positive (reachable subset) | **Coherent** | All confirmed combinations (§9) are simple, correct addition; no anomaly |
| Base + Protection (`OTHER` only) | **Coherent** | All confirmed combinations correct; strongest-only and additive-INTERNAL rules both verified exactly (P04, P11) |
| Base + Protection (`CLAUSE`/`ELLIPSIS`/`SENTENCE_FINAL`) | **Needs clarification** | Never directly tested (§9); not a known defect, but genuinely open |
| Positive + Protection (any base) | **Needs clarification** | Never directly observed co-occurring on one candidate (§7, §9); genuinely open, not structurally proven either way |
| INTERNAL stacking | **Coherent** | Additive with Technical, confirmed exactly `-50` (P11); additive with Atomic, unreachable to test (P12, `CASE ISSUE`) |
| Technical / Atomic interaction | **Coherent** | Strongest-only confirmed exactly (P04); historical scripts' additive rule explicitly superseded, not silently reinterpreted |
| Whitespace non-stacking | **Coherent** | Confirmed flat `+10` regardless of whitespace-character count (PE-05-04) |
| Transition symmetry | **Coherent** | `CJK→LATIN = LATIN→CJK = +15`, evidence-supported via same-run, same-context PE-03 pairs, not mere numeric coincidence |
| Transition + Whitespace incompatibility | **Structurally constrained** | Proven impossible by field-level inspection of `calibration_score()`, not merely unobserved |
| Transition × punctuation-anchored classes | **Structurally constrained** | `CLAUSE`/`ELLIPSIS`/`SENTENCE_FINAL` candidates always have a `PUNCTUATION`-class side; Transition requires `{CJK,LATIN}` on both sides |
| Whitespace × all four Base Classes | **Coherent** | All four confirmed reachable (PE-06), consistent with the base value plus exactly `+10` in every case |

No new interaction is invented here. Every row above traces to a specific prior
document's finding.

## 12. Numeric Model Properties

### Property A — Monotonic Positive Evidence

**PASS.** In every confirmed reachable combination (§9), adding valid Positive Evidence
(Transition or Whitespace) only ever adds a non-negative amount to the base score
(`+15` or `+10`); no confirmed case shows Positive Evidence decreasing a score.

### Property B — Monotonic Protection

**PASS.** In every confirmed reachable combination (§9), adding valid Protection
(Technical, Atomic, or INTERNAL) only ever subtracts a non-positive amount from the base
score; no confirmed case shows Protection increasing a score. (The one apparent
counterexample — P11's original leak-contaminated result, `+30.0` instead of the
expected `-50.0` — was an upstream `SENTENCE_FINAL`-misclassification artifact, not a
Protection-arithmetic failure; the corrected, clean evidence confirms `-50.0` exactly,
consistent with monotonic Protection.)

### Property C — Transition Symmetry

**PASS.** `CJK→LATIN = LATIN→CJK = +15`, evidence-supported per
`PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_DECISION.md` §5.3 (same-sentence, same-context,
same-pipeline-run PE-03 evidence, not mere numeric coincidence).

### Property D — Whitespace Flatness

**PASS.** Confirmed flat `+10` per candidate, non-stacking with whitespace-character
count, per PE-05-04 (three space characters, four candidates, every one scoring exactly
`10.0`).

### Property E — Base Classification Dominance

**PASS**, with the qualification noted in §5/§6: the dominance holds on every reachable
combination tested, but the margin narrows to as little as 5 points
(`ELLIPSIS+Whitespace=75` vs `SENTENCE_FINAL=80`) in the closest observed case. This is
recorded as `PASS`, not `CONDITIONAL`, because no actual reversal was found — but the
narrow-margin observation is carried into §13 as a design question, not silently
dropped.

### Property F — No Hidden Threshold

**PASS.** No document reviewed introduces, implies, or requires a `score >= X → cut` or
`score <= X → reject` rule anywhere in Phase 2C. Every calibration round explicitly
disclaims this (`PHASE_2C_NUMERIC_BASELINE_DECISION.md` §7, repeated in the Positive
Evidence Decision §14, repeated in this document's §4.4).

### Property G — Structural Reachability Awareness

**CONDITIONAL.** The model itself (the four scoring components and their formula) does
not rely on any combination the candidate model cannot produce — every locked numeric
decision to date has been careful to label unreachable combinations as hypothetical, not
as calibrated behavior. However, this reconciliation's own analysis (§7, §9) found that
the *evidence base* has not yet established whether Positive Evidence and Protection
*can* jointly occur on one candidate at all — a genuine open question about the
candidate model's reachability space that no single prior round was scoped to answer.
This is `CONDITIONAL` rather than `FAIL` because there is no evidence of a problem, only
an absence of evidence either way.

**Summary: A/B/C/D/F = PASS. E = PASS (narrow-margin caveat noted). G = CONDITIONAL
(untested joint-reachability gap, not a known defect).**

## 13. Risks / Design Questions

Per this round's explicit instruction, none of the following is treated as grounds to
reopen a locked value. Each is recorded using `OBSERVATION`, `POTENTIAL RISK`, `DESIGN
QUESTION`, or `REQUIRES FUTURE CALIBRATION` as appropriate — not as a new numeric
proposal.

1. **REQUIRES FUTURE DATA — Positive Evidence × Protection joint reachability.** No real
   candidate has been observed carrying both a Positive Evidence modifier and a
   Protection modifier simultaneously (§7, §9). Whether this is because the current
   candidate model structurally prevents it (as with Transition+Whitespace) or because
   no calibration round has yet constructed the right text is genuinely unknown. This
   should be investigated by a future, narrowly-scoped calibration round before treating
   the current model's behavior on such candidates as settled either way.

2. **DESIGN QUESTION — Protection acting on `CLAUSE`/`ELLIPSIS`/`SENTENCE_FINAL`.** All
   confirmed Protection evidence (P01–P15) is on `OTHER`-class candidates. It is
   currently unknown whether a `CLAUSE`, `ELLIPSIS`, or `SENTENCE_FINAL` candidate can
   ever also carry a Technical/Atomic/INTERNAL flag, and if so, what the resulting score
   would look like in practice (the hypothetical arithmetic, e.g. `CLAUSE + Technical =
   5`, is presented in §9 purely as arithmetic, not as expected real behavior).

3. **POTENTIAL RISK (hypothetical arithmetic only) — near-collisions if
   Base+Technical/Atomic ever becomes reachable.** Purely as arithmetic, *if* a
   `CLAUSE`+Technical candidate were ever reachable, it would score `5` — visually
   indistinguishable in magnitude from a plain `OTHER` candidate (`0`), collapsing the
   35-point `CLAUSE`/`OTHER` margin to 5. Similarly, `ELLIPSIS`+Technical (`35`) would
   exactly equal plain `CLAUSE` (`35`), and `SENTENCE_FINAL`+Technical (`50`) would sit
   between plain `CLAUSE` (35) and `ELLIPSIS+Whitespace` (75) with no clear
   interpretation. **These are not proposed as real behavior** — item 2 above already
   establishes this combination is untested, not confirmed reachable — but they are
   recorded here per this round's explicit instruction to surface "arithmetic that looks
   dangerous even if currently unreachable," precisely because a future architecture
   change could make them reachable without anyone revisiting this arithmetic.

4. **OBSERVATION — `D04`'s candidate-topology effect remains practically relevant to
   Phase 2D.** Even though `D04` (§8) is explained as a topology fact and not a scoring
   defect, the practical consequence — that inserting a space at a CJK/Latin boundary
   *lowers* the best available score at that text position from `15` to `10` — is
   exactly the kind of fact a future Phase 2D candidate-selection algorithm will need to
   know about. This document does not resolve how Phase 2D should handle it; it is
   flagged so the fact is not lost between now and whenever Phase 2D design begins.

5. **DESIGN QUESTION — the narrowest Base Classification margin (15, `SENTENCE_FINAL` vs
   `ELLIPSIS`) combined with Whitespace produces the tightest observed gap in the whole
   model (`ELLIPSIS+Whitespace=75` vs `SENTENCE_FINAL=80`, a 5-point gap).** No reversal
   was found (§6), but this is the least numeric headroom anywhere in the reachable
   model. Carried forward as a design-attention point, not a defect, consistent with how
   `PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_ROUND1_REPORT.md` §10 already flagged the
   underlying 15-point margin's evidence base as its own smallest.

6. **REQUIRES FUTURE CALIBRATION (deferred, not this round) — semantic usefulness of
   Whitespace.** Already formally deferred by
   `PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_DECISION.md` §10; repeated here only to
   confirm this reconciliation does not resolve it either, and does not treat it as
   grounds to revisit `Whitespace=+10`.

7. **OUT OF CURRENT SCOPE (carried forward, not acted on) — Phase 1 span-coverage and
   pattern-detection gaps.** The `v1.2.3` second-period fallback-to-`SENTENCE_FINAL` leak
   (PE-09-04) and the `CI/CD` non-detection (PE-08-02) remain exactly as recorded in the
   Positive Evidence Decision §9 — Phase 1 / Base Classification structural findings, not
   acted on by any Phase 2C numeric document, including this one.

None of these seven items is treated as contradictory empirical evidence against any
locked value. No locked value is reopened.

## 14. Phase 2D Deferred Items

The following remain explicitly outside Phase 2C and are not addressed, solved, or
implied by this reconciliation:

- Whether a candidate should actually be cut
- Thresholding
- Candidate selection (including how to choose between a transition candidate and a
  whitespace candidate at the same conceptual text position, per `D04`/item 4 above)
- DP optimization
- Subtitle line length
- Subtitle duration
- Semantic phrase integrity
- Whitespace semantic usefulness (deferred per item 6 above)
- Final tie-breaking
- Integration into `subtitle_segmenter.py`

These belong to Phase 2D and beyond. This document only consolidates and reviews the
Phase 2C relative-scoring inputs that Phase 2D will eventually consume.

## 15. Production Readiness Gate

Evaluated against internal consistency, score hierarchy, protection behavior, reachable
interactions, and unresolved contradictions — not merely "are all numbers locked":

| Criterion | Result |
|---|---|
| Internal consistency of locked values across all artifacts | **Met** — zero numeric contradiction found across all layers (confirmed independently in `PHASE_2C_NUMERIC_BASELINE_DECISION.md` §10 and re-confirmed here by cross-reading every document in §3) |
| Score hierarchy preserved on all reachable evidence | **Met** — §5, §6 |
| Protection sufficiently strong where tested | **Met on `OTHER`; untested on other base classes and untested against co-occurring Positive Evidence** — §7 |
| No confirmed reachable score reversal | **Met** — §8 |
| Reachable interactions understood | **Mostly met** — the four "not observed / untested" combinations in §9 are a genuine, named gap, not a contradiction |
| Unresolved contradictions | **None found** |

**Numeric Model Status:** internally consistent and correctly hierarchical everywhere it
has been tested; one evidence-coverage gap (Positive Evidence × Protection joint
reachability, and Protection acting on non-`OTHER` base classes) is open, not
contradictory.

**Documentation Status:** two non-blocking historical discrepancies persist exactly as
previously recorded and are not re-litigated here: (1)
`docs/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_DECISION.md` still does not exist as a
separate file (§3); (2) the Positive Evidence Round 1 Report's "nine independent CLEAN
observations" wording (actually eight, per the Positive Evidence Decision §12) remains
uncorrected in that historical report by design. Neither affects numeric correctness.

Per this round's own instruction not to block implementation unnecessarily for a
historical documentation issue: **neither documentation item blocks the readiness
determination below.** The evidence-coverage gap (§13 item 1) is a numeric-model
question, not a documentation question, and is weighed on its own merits.

**Gate result: READY WITH DOCUMENTATION FOLLOW-UP.**

This is not `NOT READY` because no contradiction, reversal, or inconsistency was found
anywhere in the evidence that does exist. It is not an unqualified `READY` because a
production scoring implementation will inevitably need to decide what happens when
Positive Evidence and Protection (or Protection and a non-`OTHER` base class) co-occur
on a real candidate — a situation the current evidence base cannot yet describe from
observation. The recommended "documentation follow-up" is not a new calibration round
requirement gating implementation start; it is a tracked, explicitly-named gap
(§13 item 1, §9's four "not observed" rows) that implementation work should be aware of
and that a future, narrowly-scoped calibration round should eventually close.

## 16. Final Reconciliation Decision

### A. Are the locked numbers internally consistent?

**Yes.** Every numeric value stated in `PHASE_2C_NUMERIC_BASELINE_DECISION.md`,
`PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_DECISION.md`, and the Protection calibration
documents agrees exactly across every artifact reviewed (§3, §4). No contradiction was
found.

### B. Is Base Classification still dominant?

**Yes, on all reachable evidence.** §5 and §6 confirm the intended ordering holds and
no Positive-Evidence-enhanced lower class exceeds a higher plain class, with the
narrowest observed gap being 5 points (`ELLIPSIS+Whitespace=75` vs `SENTENCE_FINAL=80`)
— narrow, but not reversed.

### C. Is Protection strong enough relative to Positive Evidence?

**Established only indirectly.** Protection (-20 to -30, up to -50 combined) is larger
in magnitude than any single Positive Evidence value (+10 or +15) by a comfortable
margin wherever the two have been compared as *separate* candidates (§7's pairwise
table). But no real candidate has ever been observed carrying both simultaneously, so
whether Protection actually "wins" when directly summed against Positive Evidence on one
candidate has not been empirically demonstrated — only inferred from the fact that
Protection's magnitude is larger. This is reported honestly as an open question (§7,
§13 item 1), not asserted as proven.

### D. Are there any actual reachable score reversals that are problematic?

**No.** §8 found zero confirmed reachable reversals. The `D04` finding is explained as a
candidate-topology fact, not a reversal, and does not indicate a numeric defect.

### E. Are any current decisions contradictory?

**No.** All locked decisions across all three layers agree with each other everywhere
they overlap (§3, §4, §11). The interaction rules (strongest-only Technical/Atomic,
additive INTERNAL, non-stacking Whitespace, symmetric Transition, structural
Transition+Whitespace exclusivity) are all mutually consistent and none conflicts with
another.

### F. Is another calibration round required?

**Not required to proceed with implementation, but recommended before the model is
treated as fully closed.** A narrowly-scoped future round investigating whether Positive
Evidence and Protection can co-occur on one real candidate (and, if so, what score
results) would close the one genuine evidence gap this reconciliation found (§13 item
1). This reconciliation does not schedule or perform that round; it only recommends one
if and when the project wants that gap closed before it becomes practically relevant.

### G. Is Phase 2C ready for production scoring implementation?

**READY WITH DOCUMENTATION FOLLOW-UP.** The locked numeric values, their hierarchy, and
their interaction rules are internally consistent and correctly ordered on every
reachable combination that has actually been tested. Implementation may proceed using
exactly the locked values and rules recorded in §4. The one identified gap — joint
Positive-Evidence/Protection reachability, and Protection's behavior on non-`OTHER` base
classes — should be tracked (e.g., as a code comment or a small follow-up document near
the eventual scoring implementation) rather than silently assumed resolved, so that if a
future candidate-model change or an unusual real-world text ever does produce such a
candidate, its behavior is recognized as previously-unverified rather than
retroactively assumed to have always been intended.

---

## Files

**Created:** `docs/PHASE_2C_OVERALL_NUMERIC_RECONCILIATION.md` (this document) — the
sole new file produced this round.

**Confirmed unmodified:** `src/*`, `tests/*`, `scripts/*`, and every existing file under
`docs/*`, including every calibration matrix, calibration report, protection report, and
design decision listed in §3.

**Test results (health check only, not a requirement of this round):**
```
$ python3 -m pytest tests/ -q
397 passed, 2 warnings, 15 subtests passed
```
No test was run to validate this document's content (there is nothing executable in
it); this was a repository-health sanity check only, and nothing was modified as a
result.
