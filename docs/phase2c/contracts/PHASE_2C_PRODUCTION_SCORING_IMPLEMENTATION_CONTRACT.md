# Phase 2C Production Scoring Implementation Contract

**Status:** Design-to-implementation contract Ã¢â‚¬â€ documentation only, no code/test/script/matrix/decision changes
**Phase:** Phase 2C Ã¢â‚¬â€ Production Scoring (pre-implementation contract)
**Purpose:** Translate the already-locked Phase 2C numeric model into one strict,
implementation-ready specification, without writing the scoring engine itself.

---

## 1. Purpose

Every Phase 2C numeric question has already been decided: Base Classification
(`PHASE_2C_NUMERIC_BASELINE_DECISION.md`, `PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_ROUND1_REPORT.md`),
Positive Evidence (`PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_DECISION.md`), Protection
(`PHASE_2C_NUMERIC_BASELINE_DECISION.md` Ã‚Â§9, `PHASE_2C_PROTECTION_POST_CORRECTION_VERIFICATION.md`),
and the overall model's coherence (`PHASE_2C_OVERALL_NUMERIC_RECONCILIATION.md`) have all
been reviewed and locked. This document does not revisit any of those numbers. Its sole
job is to state, precisely enough that an implementer cannot silently improvise, how
those already-approved numbers become a production scoring function over the existing
Phase 2A/2B data model.

This document is a **contract**, not code. It defines what must be true of the eventual
implementation; it does not write that implementation.

## 2. Scope

**In scope:** one new file, `docs/phase2c/contracts/PHASE_2C_PRODUCTION_SCORING_IMPLEMENTATION_CONTRACT.md`,
specifying the input/output contract, score composition, data model, public API,
error-handling, test, and acceptance requirements for a future Phase 2C scoring module.

**Out of scope, explicitly not performed by this round:**

- No production scoring code, scoring engine, or module file is created.
- No test file is created.
- No calibration script or calibration matrix is created.
- No Phase 2D code is created.
- No numeric value is changed, increased, decreased, or reproposed.
- No locked decision (Numeric Baseline, Base Classification, Positive Evidence,
  Protection, or Overall Reconciliation) is reopened.
- No existing file Ã¢â‚¬â€ `src/*`, `tests/*`, `scripts/*`, any existing Matrix, Calibration
  Report, Design Decision, or `PHASE_2C_OVERALL_NUMERIC_RECONCILIATION.md` Ã¢â‚¬â€ is modified.
- No git operation of any kind is performed.

## 3. Authoritative Design Inputs

Read in full or in relevant part before drafting this contract:

| Document | What this contract takes from it |
|---|---|
| `docs/phase2c/decisions/PHASE_2C_NUMERIC_BASELINE_DECISION.md` | The full locked numeric baseline; the Technical/Atomic strongest-only + INTERNAL-additive interaction rule (Ã‚Â§5); the signed-relative-score strategy and disabled mechanisms (Ã‚Â§7); the Phase Responsibility Boundary (Ã‚Â§8). |
| `docs/phase2c/calibration/matrices/PHASE_2C_BASE_CLASSIFICATION_CALIBRATION_MATRIX.md` / `..._ROUND1_REPORT.md` | Confirms the three Base Classification margins (35/30/15) as `KEEP`, with zero `CASE ISSUE`. |
| `docs/phase2c/calibration/matrices/PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_MATRIX.md` / `..._ROUND1_REPORT.md` | The PE-01Ã¢â‚¬â€œPE-12 evidence base for Positive Evidence and its structural reachability findings. |
| `docs/phase2c/decisions/PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_DECISION.md` | The formal LOCK of `CJKÃ¢â€ â€™LATIN=+15`, `LATINÃ¢â€ â€™CJK=+15`, `Whitespace=+10`, whitespace non-stacking, and the Transition+Whitespace / TransitionÃƒâ€”Base-Class structural reachability findings. |
| `docs/phase2c/calibration/matrices/PHASE_2C_PROTECTION_CALIBRATION_MATRIX.md` / `..._ROUND1_REPORT.md` | The P01Ã¢â‚¬â€œP15 evidence base for Protection; the strongest-only Technical/Atomic hypothesis and its confirmation. |
| `docs/phase2c/calibration/reports/PHASE_2C_PROTECTION_POST_CORRECTION_VERIFICATION_REPORT.md` | Confirms `Technical+INTERNAL=-50` on a clean `OTHER`-class candidate; confirms `Atomic+INTERNAL` (P12) remains an unreachable `CASE ISSUE`. |
| `docs/phase2c/decisions/PHASE_2C_OVERALL_NUMERIC_RECONCILIATION.md` | Confirms cross-layer consistency; explicitly names the untested Positive-EvidenceÃƒâ€”Protection and ProtectionÃƒâ€”non-`OTHER`-class combinations this contract must still mechanically define without claiming empirical support for them. |

**Source code inspected (read-only, for data-model compatibility only Ã¢â‚¬â€ not modified and
not re-implemented):**

- `src/boundary_observation.py` Ã¢â‚¬â€ defines `CharacterClass`, `SpanRef`,
  `StructuralBoundaryContext`, `PunctuationSequenceState`, `BoundaryFeatures`,
  `BoundaryCandidate`, and `observe_boundaries()`.
- `src/boundary_classification.py` Ã¢â‚¬â€ defines `BoundaryClass`, `ClassifiedBoundary`,
  `classify_boundary()`, and `classify_boundaries()`.
- `tests/test_boundary_observation.py`, `tests/test_boundary_classification.py` Ã¢â‚¬â€
  inspected only to confirm existing test-file naming convention
  (`tests/test_<module>.py`), not modified.
- `scripts/calibrate_phase2c_protection_round1.py` Ã¢â‚¬â€ inspected as the most
  numerically-faithful existing implementation of the locked formula (its
  `calibration_score()` function implements exactly the strongest-only Technical/Atomic
  rule this contract also requires). This script is **evidence of correct arithmetic**,
  not an architectural precedent Ã¢â‚¬â€ see Ã‚Â§20 for why it must not be imported by production
  code, and Ã‚Â§6 for a genuine input-shape question this contract does **not** resolve by
  copying the script's own choice.

No document was found describing this contract's file as already existing; this is
confirmed the first attempt at this exact document.

## 4. Phase 2C Responsibility Boundary

Reproduced verbatim in spirit from `PHASE_2C_NUMERIC_BASELINE_DECISION.md` Ã‚Â§8, extended
one layer:

```
Phase 2A: observes structural evidence.      -> BoundaryCandidate
Phase 2B: classifies boundaries.              -> ClassifiedBoundary (BoundaryClass)
Phase 2C: assigns/calibrates relative numeric preference.  -> WeightedBoundary (this contract)
Phase 2D: integrates scores into segmentation behavior.     -> not designed here
```

Phase 2C must not: re-parse raw text; call `analyze_text_structure()`; rediscover
Technical/Atomic/punctuation-sequence structure independently of what Phase 1/2A already
report; override or recompute Phase 2B's classification logic; decide `should_cut`,
candidate selection, ranking, or final subtitle cuts. Phase 2C's sole output is a signed
relative score attached to each already-observed, already-classified boundary.

## 5. Locked Numeric Model

### 5.1 Base Classification

| BoundaryClass | Score | Status |
|---|---:|---|
| `SENTENCE_FINAL` | +80 | LOCKED (provisional baseline, `KEEP`) |
| `ELLIPSIS` | +65 | LOCKED (provisional baseline, `KEEP`) |
| `CLAUSE` | +35 | LOCKED (provisional baseline, `KEEP`) |
| `OTHER` | 0 | LOCKED (provisional baseline, `KEEP`) |

### 5.2 Positive Evidence

| Evidence | Score | Status |
|---|---:|---|
| `CJK Ã¢â€ â€™ LATIN` | +15 | LOCKED, symmetric with `LATIN Ã¢â€ â€™ CJK` |
| `LATIN Ã¢â€ â€™ CJK` | +15 | LOCKED, symmetric with `CJK Ã¢â€ â€™ LATIN` |
| `Whitespace` | +10 | LOCKED, flat, candidate-level, non-stacking |

### 5.3 Protection

| Evidence | Score | Status |
|---|---:|---|
| `Technical` | -30 | LOCKED (behaviorally supported) |
| `Atomic` | -30 | LOCKED (behaviorally supported) |
| `INTERNAL` | -20 | LOCKED (behaviorally supported) |

**Interaction rule (LOCKED, reproduced exactly, not reinterpreted):**

```
Technical + Atomic              -> strongest-only: max_penalty(Technical, Atomic) = -30, NOT -60
Technical + INTERNAL            -> additive: -30 + -20 = -50
Atomic + INTERNAL               -> additive: -30 + -20 = -50 (mechanically defined;
                                    no real candidate has exhibited this combination Ã¢â‚¬â€
                                    Atomic+INTERNAL, P12, remains a CASE ISSUE per
                                    PHASE_2C_PROTECTION_CALIBRATION_ROUND1_REPORT.md Ã‚Â§6
                                    and PHASE_2C_PROTECTION_POST_CORRECTION_VERIFICATION.md Ã‚Â§7 Ã¢â‚¬â€
                                    the -50 value is what the locked additive rule
                                    produces IF this combination is ever reachable, not a
                                    confirmed observation)
```

No numeric value in Ã‚Â§5.1Ã¢â‚¬â€œÃ‚Â§5.3 may be changed by this contract or by its eventual
implementation.

### 5.4 Numeric Strategy

**LOCKED DESIGN DECISION:** the scoring model is a **signed relative score**. The
following are, and must remain, absent from the implementation:

- No normalization
- No threshold (`score >= X -> cut` / `score <= X -> reject`)
- No hard floor (class-specific or otherwise)
- No probability conversion
- No sigmoid / softmax
- No score-to-cut mapping

The Phase 2C scorer produces evidence only. It does not decide `should_cut`,
`selected_boundary`, final segmentation, or subtitle grouping Ã¢â‚¬â€ those remain entirely
Phase 2D's responsibility (Ã‚Â§21).

## 6. Input Contract

**LOCKED DESIGN DECISION:** the scorer consumes exactly the fields Phase 2A and Phase 2B
already compute. It performs no independent detection of any kind (Ã‚Â§8Ã¢â‚¬â€œÃ‚Â§11 define this
precisely per component). It does not call `analyze_text_structure()`. It does not
reconstruct punctuation-sequence state, terminal-ending chains, technical/atomic span
detection, or boundary classification.

**OPEN DESIGN QUESTION Ã¢â‚¬â€ input object shape (must be resolved before coding, not chosen
here):**

The authoritative documents describe the scorer's input at two different levels of
specificity that do not, on their own, resolve to one unambiguous function signature:

- `PHASE_2C_PRODUCTION_SCORING_IMPLEMENTATION_CONTRACT.md`'s own governing round
  instructions (Ã‚Â§7 "Score Composition") state: "The scorer consumes an already-observed
  **and classified** candidate." Read literally and by direct analogy with the existing
  pipeline discipline Ã¢â‚¬â€ Phase 2A consumes Phase 1's already-computed
  `TextAnalysisResult` rather than raw text, and Phase 2B consumes Phase 2A's
  already-computed `BoundaryCandidate` Ã¢â‚¬â€ the natural, symmetric reading is that Phase 2C
  should consume Phase 2B's already-computed output object, `ClassifiedBoundary`
  (`candidate: BoundaryCandidate`, `boundary_class: BoundaryClass`), and never itself
  call `classify_boundary()`.
- The existing `scripts/phase2c/calibrate_protection_round1.py` (informal calibration
  tooling, **not** an architectural precedent per its own module docstring: "NOT
  production code") instead takes a bare `BoundaryCandidate` and calls the real
  `classify_boundary(candidate)` function itself, inline, to obtain the `BoundaryClass`
  needed for the base score. This is not a re-implementation of Phase 2B's logic Ã¢â‚¬â€ it is
  a direct call into the real, unmodified Phase 2B function Ã¢â‚¬â€ so it does not, by itself,
  violate the "do not reconstruct classification" instruction. It does, however, depart
  from the one-directional "consume the prior phase's already-computed output object"
  discipline that `boundary_observation.py` and `boundary_classification.py` both
  establish and explicitly document as deliberate.

Neither authoritative Design Decision document (`PHASE_2C_NUMERIC_BASELINE_DECISION.md`,
`PHASE_2C_POSITIVE_EVIDENCE_CALIBRATION_DECISION.md`, or
`PHASE_2C_OVERALL_NUMERIC_RECONCILIATION.md`) specifies the scorer's function signature
or input type Ã¢â‚¬â€ all three discuss the model only at the semantic/arithmetic level
("Base Classification is read from Phase 2B output"), which is equally satisfied by
either shape. This contract does **not** silently pick one. Both of the following are
architecturally legitimate and must be decided by a small, explicit pre-coding choice
(not a new calibration round, not a numeric change):

- **Option A:** `score_boundary(classified: ClassifiedBoundary) -> WeightedBoundary` Ã¢â‚¬â€
  matches the established one-directional "consume the previous phase's output object"
  pattern exactly; the scorer never imports or calls `classify_boundary`.
- **Option B:** `score_boundary(candidate: BoundaryCandidate) -> WeightedBoundary` Ã¢â‚¬â€
  matches the calibration script's own tested arithmetic exactly; the scorer calls the
  real `classify_boundary(candidate)` once internally to obtain the `BoundaryClass` it
  needs for the base score.

Both options are deterministic, mechanical, and produce numerically identical scores for
the same underlying text Ã¢â‚¬â€ this is an interface-shape question, not a numeric or
behavioral ambiguity, and per Ã‚Â§27 of the governing instructions it does not, by itself,
block the Final Implementation Gate (Ã‚Â§25). Whoever begins coding must pick one
explicitly rather than have it fall out of the first draft unnoticed.

**Collections:** whichever option is chosen, the scorer must also accept a sequence of
its single-item input type (`Sequence[ClassifiedBoundary]` or
`Sequence[BoundaryCandidate]`) and return an ordered collection of `WeightedBoundary`,
preserving input order Ã¢â‚¬â€ mirroring `classify_boundaries()`'s and `observe_boundaries()`'s
existing "preserve order, one output per input" contract exactly.

## 7. Output Contract

The scorer's sole output type is `WeightedBoundary` (Ã‚Â§14). Exactly one `WeightedBoundary`
is produced per input candidate/classified-boundary, in the same order as the input
sequence Ã¢â‚¬â€ mirroring the "one output per input, order preserved" contract already
established by `observe_boundaries()` and `classify_boundaries()`.

`WeightedBoundary` must make the original `BoundaryCandidate` available (Ã‚Â§6's
"underlying boundary must remain available" requirement, Ã‚Â§15 of the governing
instructions) regardless of which input-shape option (Ã‚Â§6) is eventually chosen.

## 8. Score Composition

**LOCKED DESIGN DECISION.** The conceptual formula, reproduced exactly from the governing
instructions and consistent with every authoritative document reviewed:

```
score = base_classification_score
      + positive_evidence_score
      + protection_score
```

Each term is derived exclusively from fields Phase 2A (`BoundaryFeatures`) and Phase 2B
(`BoundaryClass`) already compute Ã¢â‚¬â€ never re-detected, never independently inferred from
`left_char`/`right_char` text beyond the specific field-level checks defined in Ã‚Â§9Ã¢â‚¬â€œÃ‚Â§11.
The scoring layer must not call `analyze_text_structure()`, and must not reconstruct
punctuation-sequence detection, terminal-ending-chain traversal, technical span
detection, or atomic span detection Ã¢â‚¬â€ all of that evidence already exists on
`BoundaryFeatures.structural_context` and `BoundaryFeatures.punctuation_sequence_state`
and must simply be read.

`positive_evidence_score` and `protection_score` are each computed independently of one
another and of `base_classification_score` Ã¢â‚¬â€ there is no shared state or short-circuit
between the three terms; every reachable/confirmed combination in Ã‚Â§13 is exact,
unweighted addition.

## 9. Base Classification Mapping

**LOCKED DESIGN DECISION.**

```
BoundaryClass.SENTENCE_FINAL -> base_classification_score = +80
BoundaryClass.ELLIPSIS       -> base_classification_score = +65
BoundaryClass.CLAUSE         -> base_classification_score = +35
BoundaryClass.OTHER          -> base_classification_score = 0
```

The `BoundaryClass` value itself must be read from Phase 2B's classification Ã¢â‚¬â€ either
already present on a `ClassifiedBoundary` input, or obtained via exactly one call to the
real, unmodified `classify_boundary()` function, per whichever input shape Ã‚Â§6 resolves
to. The scorer must never reorder, override, or reimplement Phase 2B's frozen
`SENTENCE_FINAL > ELLIPSIS > CLAUSE > OTHER` precedence (`boundary_classification.py`
module docstring, "CLASSIFICATION PRECEDENCE (frozen Ã¢â‚¬â€ do not reorder)"). If a candidate
has already been classified `SENTENCE_FINAL`, the scorer uses `+80` directly Ã¢â‚¬â€ it does
not re-derive or re-check the classification's correctness.

## 10. Positive Evidence Mapping

**LOCKED DESIGN DECISION**, with one implementation-detail warning made explicit below.

```
left_character_class == CJK   and right_character_class == LATIN  -> +15  ("CJK->LATIN")
left_character_class == LATIN and right_character_class == CJK    -> +15  ("LATIN->CJK")
left_character_class == WHITESPACE or right_character_class == WHITESPACE -> +10 (flat)
```

Both fields are read verbatim from `BoundaryFeatures.left_character_class` /
`BoundaryFeatures.right_character_class` (Phase 2A's `CharacterClass` enum). No
character-class re-detection occurs in the scorer.

**IMPLEMENTATION-DETAIL WARNING (not an ambiguity, but must not be silently mis-implemented):**
`BoundaryFeatures` also exposes a broader, pre-computed
`character_class_transition: bool` field, defined by `boundary_observation.py` as simply
`left_character_class != right_character_class` Ã¢â‚¬â€ true for **any** class change (e.g.
`CJK -> DIGIT`, `CJK -> PUNCTUATION`, `WHITESPACE -> CJK`), not only the specific
`{CJK, LATIN}` pair the Positive Evidence Decision actually calibrated and locked.
**The Positive Evidence `+15` value must be triggered only by the exact `{CJK, LATIN}` /
`{LATIN, CJK}` pair check shown above Ã¢â‚¬â€ never by `character_class_transition` alone** Ã¢â‚¬â€
because every piece of empirical evidence behind the `+15` lock (PE-01, PE-02, PE-03,
PE-09) was gathered against that exact pair check, not against the broader flag. This
mirrors the exact logic already implemented (for calibration purposes only) in
`scripts/phase2c/calibrate_protection_round1.py`'s `calibration_score()`. This is
recorded as an implementation-detail warning, not an open design question, because the
locked evidence unambiguously specifies which check is correct Ã¢â‚¬â€ the risk being guarded
against is a plausible-looking but wrong shortcut (using the pre-existing boolean field
because its name sounds relevant), not a genuine choice between two valid designs.

**Non-stacking (LOCKED):** whitespace contributes at most one `+10` per candidate,
regardless of how many characters are involved on either side Ã¢â‚¬â€ this is already
structurally guaranteed by the fact that `left_character_class`/`right_character_class`
each describe exactly one character adjacent to the boundary position, so no additional
non-stacking logic needs to be written; a single candidate can never carry more than one
whitespace bonus by construction of the Phase 2A data model. Multiple whitespace
characters in the source text simply produce multiple, separate `BoundaryCandidate`
objects (one per character gap), each independently scored Ã¢â‚¬â€ never one candidate scored
more than once. This is empirically confirmed by PE-05-04 (three space characters,
four separate candidates, every one scoring exactly `10.0`).

**Transition symmetry (LOCKED):** both directions use the identical `+15` value and the
identical mechanical trigger shape (character-class pair check); no separate code path,
sign convention, or magnitude distinction may be introduced between the two directions.

## 11. Protection Mapping

**LOCKED DESIGN DECISION.**

```
"technical" in {span_ref.type for span_ref in features.structural_context.containing_spans}
  -> technical = True
"atomic" in {span_ref.type for span_ref in features.structural_context.containing_spans}
  -> atomic = True
protection_penalty = -30.0 if (technical or atomic) else 0.0   # strongest-only, NOT additive

features.punctuation_sequence_state == PunctuationSequenceState.INTERNAL
  -> sequence_penalty = -20.0, else 0.0                         # fully independent, additive

protection_score = protection_penalty + sequence_penalty
```

Both checks are read verbatim from `BoundaryFeatures.structural_context.containing_spans`
(a `Tuple[SpanRef, ...]`, each with a `.type` string field already computed by Phase 2A)
and `BoundaryFeatures.punctuation_sequence_state` (Phase 2A's `PunctuationSequenceState`
enum). No span re-detection, no re-scanning of raw text, no independent
technical/atomic/punctuation-sequence pattern matching occurs in the scorer. This exactly
mirrors `scripts/phase2c/calibrate_protection_round1.py`'s `calibration_score()` logic,
which is cited here as verified-correct arithmetic (Ã‚Â§3), not copied as a runtime
dependency (Ã‚Â§20).

## 12. Interaction Rules

**LOCKED DESIGN DECISIONS**, reproduced exactly:

| Rule | Formula | Status |
|---|---|---|
| Technical + Atomic (same candidate) | `-30` (strongest-only, i.e. `max`, not `sum`) | LOCKED, confirmed exact (P04) |
| Technical + INTERNAL | `-30 + -20 = -50` | LOCKED, confirmed exact on a clean `OTHER`-class candidate (P11, post-correction) |
| Atomic + INTERNAL | `-30 + -20 = -50` | LOCKED formula; **mechanically defined, not empirically confirmed** Ã¢â‚¬â€ P12 remains an unreached `CASE ISSUE` (Ã‚Â§13) |
| Transition + Whitespace (any base class) | not defined; `+25` is **not** a valid score | LOCKED STRUCTURAL FINDING Ã¢â‚¬â€ structurally unreachable, not a calibration target (Ã‚Â§13) |
| Transition + `CLAUSE`/`ELLIPSIS`/`SENTENCE_FINAL` | not defined; hypothetical `50`/`80`/`95` are **not** valid scores | LOCKED STRUCTURAL FINDING Ã¢â‚¬â€ structurally unreachable (Ã‚Â§13) |
| Whitespace + any of the four Base Classes | additive, `+10` on top of the base value | LOCKED, all four confirmed reachable (Ã‚Â§13) |
| Positive Evidence + Protection (any base) | mechanically additive per Ã‚Â§8's formula if both fields are present | **empirically unverified**, not structurally proven either way (Ã‚Â§13) |
| Protection + `CLAUSE`/`ELLIPSIS`/`SENTENCE_FINAL` | mechanically additive per Ã‚Â§8's formula if both fields are present | **empirically unverified**, not structurally proven either way (Ã‚Â§13) |

The implementation must preserve the strongest-only vs. additive distinction exactly as
shown Ã¢â‚¬â€ it must not average, cap independently, or otherwise reinterpret either rule.

## 13. Reachability and Evidence Status

This section separates confirmed-reachable behavior, structurally unreachable
combinations, and mechanically-defined-but-empirically-unverified combinations. The
scorer's code must implement the same formula (Ã‚Â§8Ã¢â‚¬â€œÃ‚Â§11) regardless of which category a
given real candidate falls into Ã¢â‚¬â€ **the categories below describe evidence status, not
different code paths.** The implementation must not add a special case, exception, or
different arithmetic path for the "empirically unverified" rows; it applies the same
locked formula uniformly, and this section exists purely so nobody later mistakes an
unverified value for a validated one.

### Confirmed reachable (real pipeline evidence exists)

| Combination | Score | Evidence |
|---|---:|---|
| `OTHER` | 0 | Base case |
| `OTHER + Transition` | 15 | PE-01, PE-04-OTHER |
| `OTHER + Whitespace` | 10 | PE-05, PE-06-OTHER |
| `CLAUSE + Whitespace` | 45 | PE-06-CLAUSE |
| `ELLIPSIS + Whitespace` | 75 | PE-06-ELLIPSIS |
| `SENTENCE_FINAL + Whitespace` | 90 | PE-06-SENTENCE_FINAL |
| `OTHER + Technical` | -30 | P03 |
| `OTHER + Atomic` | -30 | P02 |
| `OTHER + Technical + Atomic` | -30 (strongest-only) | P04 |
| `OTHER + INTERNAL` | -20 | P08 |
| `OTHER + Technical + INTERNAL` | -50 | P11, post-correction, clean `OTHER`-class candidate |

### Structurally unreachable (proven impossible by field-level inspection, not merely unobserved)

| Combination | Hypothetical arithmetic | Why unreachable |
|---|---:|---|
| Transition + Whitespace (any base) | 25 | `left_character_class`/`right_character_class` cannot simultaneously be `{CJK,LATIN}` and `WHITESPACE` |
| `CLAUSE` + Transition | 50 | `CLAUSE` candidates always have `PUNCTUATION`-class on the left side; Transition requires `{CJK,LATIN}` on both sides |
| `ELLIPSIS` + Transition | 80 | Same mechanism Ã¢â‚¬â€ `ELLIPSIS`(END-state) candidates always have `PUNCTUATION`-class on one side |
| `SENTENCE_FINAL` + Transition | 95 | Same mechanism |

These four combinations must **never** be produced by the implementation as if they were
calibrated values. If a future candidate-model change ever made one of them reachable,
that would itself require a new Design Decision before any of these hypothetical numbers
could be treated as calibrated Ã¢â‚¬â€ this contract does not pre-authorize that.

### Mechanically defined, empirically unverified (formula applies if the data model ever produces the combination; no real observation confirms it)

| Combination | Score (per locked formula) | Status |
|---|---:|---|
| `OTHER + Atomic + INTERNAL` | -50 | Formula-derived; P12 (`Atomic+INTERNAL`) is an unreached `CASE ISSUE` Ã¢â‚¬â€ no real candidate observed |
| `OTHER + Transition + Technical` | 0 + 15 - 30 = **-15** | Formula-derived; not observed on any real candidate. PE-09-05 (`GPT-4`) placed a transition candidate immediately adjacent to, but structurally outside, a technical span Ã¢â‚¬â€ the transition candidate itself was clean (`tech=False`) |
| `OTHER + Whitespace + Technical` | 0 + 10 - 30 = **-20** | Formula-derived; not observed. PE-09-03 (`iPhone 15`) similarly placed whitespace candidates clean and outside the atomic span |
| `CLAUSE + Technical` | 35 - 30 = **5** | Formula-derived; no real candidate observed carrying both a `CLAUSE` classification and Technical protection |
| `ELLIPSIS + Technical` | 65 - 30 = **35** | Formula-derived; not observed |
| `SENTENCE_FINAL + Technical` | 80 - 30 = **50** | Formula-derived; not observed |

Per `PHASE_2C_OVERALL_NUMERIC_RECONCILIATION.md` Ã‚Â§9/Ã‚Â§13, these combinations are **not**
structurally proven impossible the way Transition+Whitespace is (no field-level
contradiction was found in `BoundaryFeatures`) Ã¢â‚¬â€ they are simply combinations no
calibration round has yet constructed a real candidate for. The implementation must
compute them using the exact same formula as every confirmed combination if the input
data ever exhibits them; it must not special-case, suppress, or silently clamp them.

## 14. WeightedBoundary Data Model

**LOCKED DESIGN DECISION (required fields):**

`WeightedBoundary` must expose:

- The underlying `BoundaryCandidate` (object-identity-preserved, not copied Ã¢â‚¬â€ Ã‚Â§16).
- The `BoundaryClass` this score was computed against (needed because every score
  example in every authoritative document, e.g. "`CLAUSE + Whitespace = 45`", is stated
  in terms of the boundary class Ã¢â‚¬â€ a `WeightedBoundary` without a visible
  `boundary_class` would make its own `score` uninterpretable without re-deriving the
  classification externally, which would defeat the "already-classified" input
  discipline in Ã‚Â§6). This is **not** the banned `category` field from Ã‚Â§6 of the
  governing instructions (a hypothetical new subjective preference bucket) Ã¢â‚¬â€ it is
  Phase 2B's own, already-locked, already-existing `BoundaryClass` value, carried
  forward for traceability, not invented by this document.
- The final signed relative `score` (the sum defined in Ã‚Â§8).

**OPEN DESIGN QUESTION Ã¢â‚¬â€ component-score fields (must be resolved before coding, not
chosen here, per the governing instructions' explicit direction):**

None of the authoritative Design Decision documents defines a production data-model
requirement for storing `base_classification_score`, `positive_evidence_score`, and
`protection_score` as individually addressable fields on the output object. The
calibration script's `breakdown` dict (Ã‚Â§3) stores these as separate keys, but that is
calibration-tooling convenience for producing human-readable dumps (`dump()`), not a
design requirement carried by any locked decision document. Per the governing
instructions ("Do not add fields simply because they would be convenient... If the
authoritative documents do not define component-score fields, record that as an
implementation decision that must be resolved before coding rather than inventing one
silently"), this contract does **not** decide whether `WeightedBoundary` exposes:

- only the final `score` (minimal, matches "do not invent fields" most conservatively), or
- `score` plus the three individual component contributions (more diagnostic/debuggable,
  useful for exactly the kind of "which factor produced this number" question every
  calibration report in this project has needed to answer, but not currently required by
  any locked decision).

This does not block implementation (Ã‚Â§25): the minimal shape (`candidate`,
`boundary_class`, `score`) is fully specified and sufficient to satisfy every acceptance
criterion in Ã‚Â§23; adding component fields later is a strictly additive, backward-compatible
change if a future need (e.g. debugging, a future Phase 2D consumer wanting to explain a
score) makes it necessary. Whoever begins coding must make this choice explicitly and
record it (e.g. in a short implementation note or commit message), not let it default
silently either way.

**Immutability:** `WeightedBoundary` must be a frozen/immutable object (mirroring
`BoundaryCandidate`, `BoundaryFeatures`, and `ClassifiedBoundary`, all frozen
dataclasses in the existing codebase), constructed once and never mutated after creation.

## 15. Public API Contract

**IMPLEMENTATION DETAIL (naming only Ã¢â‚¬â€ not a design decision):** matching the existing,
established naming convention (`observe_boundaries()` in `boundary_observation.py`;
`classify_boundary()` / `classify_boundaries()` in `boundary_classification.py`), the
smallest consistent API is:

```
score_boundary(<single input, per Ã‚Â§6's unresolved Option A/B>) -> WeightedBoundary
score_boundaries(<sequence of the same input type>) -> Tuple[WeightedBoundary, ...]
```

This naming choice does not itself constitute a new design decision Ã¢â‚¬â€ it is a direct,
mechanical extension of the existing singular/plural naming pattern already used by both
Phase 2A and Phase 2B, and does not depend on which resolution Ã‚Â§6's open question
eventually receives. It does depend on that resolution for the parameter type, which
this contract leaves open per Ã‚Â§6.

**Explicitly not exposed by the public API:**

- No calibration-only function (e.g. anything resembling `calibration_score()`'s
  breakdown-dict return shape) is part of the production API.
- No test-only helper is exposed.
- No Phase 2D function (`should_cut`, candidate selection, ranking, DP, tie-breaking) is
  defined or stubbed here.

## 16. Immutability and Determinism

**LOCKED DESIGN DECISION**, mirroring the existing Phase 2A/2B discipline exactly:

- The original `BoundaryCandidate` (and, transitively, its `BoundaryFeatures`) must
  never be mutated by the scorer. Both are already frozen dataclasses in the existing
  codebase, so this is enforced structurally, not just by convention.
- `WeightedBoundary` must preserve the original candidate by object identity where the
  chosen input shape (Ã‚Â§6) makes that possible Ã¢â‚¬â€ i.e. `weighted.candidate is candidate`
  (or `weighted.candidate is classified.candidate`, per whichever `ClassifiedBoundary`
  the input traces back to) Ã¢â‚¬â€ never a copy, mirroring `ClassifiedBoundary.candidate`'s
  existing "never a copy" guarantee (`boundary_classification.py` module docstring).
- The scorer must be a pure function: same `BoundaryCandidate`/`ClassifiedBoundary` input
  always produces an equal `WeightedBoundary` output. No I/O, no randomness, no global or
  hidden state, no caching that could change behavior across calls.

## 17. Error Handling

**IMPLEMENTATION DETAIL (fail-fast, per the governing instructions' own preference for
programmer-error handling; not itself a new design decision):**

| Input | Expected behavior |
|---|---|
| Valid `BoundaryCandidate` / `ClassifiedBoundary` | Score normally per Ã‚Â§8Ã¢â‚¬â€œÃ‚Â§13 |
| Empty candidate collection | `score_boundaries(())` returns `()` Ã¢â‚¬â€ mirrors `observe_boundaries`/`classify_boundaries`'s behavior on an empty analysis with no internal character gaps |
| `None` (single-item API) | Fail fast (raise `TypeError` or equivalent) Ã¢â‚¬â€ programmer error, not a data condition to be tolerated silently |
| Malformed candidate (wrong type, missing fields) | Fail fast Ã¢â‚¬â€ the scorer trusts that Phase 2A/2B's frozen dataclasses were used to construct its input; it does not implement its own structural validation of `BoundaryFeatures` |
| Unknown `BoundaryClass` | Cannot occur if the input was produced by the real `classify_boundary()`/`classify_boundaries()` (a frozen 4-member enum, per `boundary_classification.py`'s "frozen taxonomy Ã¢â‚¬â€ do not extend"); if it somehow did, a direct dict/mapping lookup (mirroring `_BASE_SCORES[boundary_class]` in the calibration script) fails fast with a `KeyError` rather than silently defaulting to a score |
| Contradictory evidence fields on `BoundaryFeatures` (e.g. `character_class_transition` disagreeing with the individual class fields) | Not independently validated by the scorer Ã¢â‚¬â€ this would be an upstream Phase 2A invariant violation, which is Phase 2A's responsibility to prevent, not Phase 2C's responsibility to detect. The scorer trusts its input exactly as Phase 2B already trusts Phase 2A's fields without re-validation (`boundary_classification.py`'s own documented practice) |

This is recorded as an implementation-detail choice, consistent with the governing
instructions' explicit "prefer fail-fast behavior for programmer errors... document the
choice as implementation detail" Ã¢â‚¬â€ not a design decision requiring sign-off.

## 18. Test Contract

The eventual implementation (a future round, not this one) must include tests covering:

**Base Classification:** one test per class (`OTHER`, `CLAUSE`, `ELLIPSIS`,
`SENTENCE_FINAL`) confirming the exact locked base score.

**Positive Evidence:** `CJK Ã¢â€ â€™ LATIN` (+15), `LATIN Ã¢â€ â€™ CJK` (+15), `Whitespace` (+10), and
a dedicated non-stacking test (multiple whitespace-adjacent candidates in one text, each
independently `+10`, never summed onto one candidate).

**Protection:** `Technical` (-30), `Atomic` (-30), `INTERNAL` (-20), `Technical + Atomic`
(strongest-only, `-30` not `-60`), `Technical + INTERNAL` (additive, `-50`).

**Composition**, explicitly distinguishing confirmed-reachable from
mechanically-defined-but-empirically-unverified per Ã‚Â§13:

- Base + Positive (confirmed reachable: `OTHER+Transition=15`, `OTHER+Whitespace=10`,
  `CLAUSE+Whitespace=45`, `ELLIPSIS+Whitespace=75`, `SENTENCE_FINAL+Whitespace=90`)
- Base + Protection (confirmed reachable, `OTHER` only: `OTHER+Technical=-30`,
  `OTHER+Atomic=-30`, `OTHER+Technical+Atomic=-30`, `OTHER+INTERNAL=-20`,
  `OTHER+Technical+INTERNAL=-50`)
- Base + Positive + Protection Ã¢â‚¬â€ tests here must be clearly labeled or grouped as
  **formula/arithmetic tests using constructed `BoundaryFeatures` values**, not as tests
  claiming empirical/pipeline confirmation, for exactly the combinations listed in Ã‚Â§13's
  "mechanically defined, empirically unverified" table. This distinction (confirmed vs.
  unverified) must be visible in the test file itself (e.g. via test names, comments, or
  grouping), not just in this contract document, so a future reader of the test suite
  does not mistake an arithmetic sanity check for calibration evidence.

**Determinism:** same input produces the same `WeightedBoundary` (or equal-by-value
output) across repeated calls.

**Immutability:** the input `BoundaryCandidate` (and its `BoundaryFeatures`) is
unchanged after scoring Ã¢â‚¬â€ comparable before/after, or relying on frozen-dataclass
guarantees plus object-identity checks.

**API:** both single-candidate scoring and collection scoring, including the empty-
collection case (Ã‚Â§17).

This contract does not write these tests; it specifies what the eventual test file must
cover.

## 19. Regression Requirements

**LOCKED DESIGN DECISION.** The eventual implementation must not require any
modification to:

- `src/text_structure.py`
- `src/boundary_observation.py`
- `src/boundary_classification.py`

unless a separate, future, explicitly-scoped design decision authorizes such a change.
All existing Phase 1 / Phase 2A / Phase 2B tests (`tests/test_text_structure.py`,
`tests/test_boundary_observation.py`, `tests/test_boundary_classification.py`) must
continue to pass unmodified. The full existing regression suite
(`python3 -m pytest tests/ -q`, currently 397 passed) must continue to pass once the
scoring module and its tests are added Ã¢â‚¬â€ the new tests are additive, not replacements.

## 20. Historical Calibration Script Separation

**LOCKED DESIGN DECISION.** Production scoring code must **not** import:

- `scripts/phase2c/calibrate_numeric_round1.py`
- `scripts/phase2c/calibrate_numeric_round2.py`
- `scripts/phase2c/calibrate_protection_round1.py`
- any calibration script or calibration matrix file

Calibration artifacts are design evidence used to derive and validate the locked numeric
model (Ã‚Â§3) Ã¢â‚¬â€ they are not, and must never become, a runtime dependency of production
code. This is a one-directional relationship: this contract cites calibration scripts as
evidence of correct arithmetic (Ã‚Â§3, Ã‚Â§11), but the production module must reimplement
that arithmetic independently within `src/`, not call into `scripts/` at runtime.

**Historical script discrepancy, explicitly documented (not corrected, not modified):**
`scripts/phase2c/calibrate_numeric_round1.py` and `scripts/phase2c/calibrate_numeric_round2.py` both
implement **additive** Technical+Atomic combination (`-30 + -30 = -60` when both apply).
This is **not** the production rule. `PHASE_2C_NUMERIC_BASELINE_DECISION.md` Ã‚Â§10.3
explicitly records this as **HISTORICAL** Ã¢â‚¬â€ those two scripts predate the strongest-only
decision and were not designed to test that specific interaction; they are left exactly
as they are, unmodified, and are not authoritative for production scoring behavior. The
authoritative rule, confirmed by `scripts/phase2c/calibrate_protection_round1.py` and
formally adopted by `PHASE_2C_NUMERIC_BASELINE_DECISION.md` Ã‚Â§5/Ã‚Â§12, is **strongest-only**:
`Technical + Atomic = -30`, never `-60`. Neither historical script is modified by this
contract or is expected to be modified by the eventual implementation.

## 21. Phase 2D Boundary

**LOCKED DESIGN DECISION.** Phase 2C, including its production implementation, must not
decide, compute, or stub any of the following:

- `should_cut`
- any threshold
- candidate selection
- candidate ranking
- DP (dynamic programming) optimization
- subtitle grouping
- subtitle duration
- subtitle line length
- semantic phrase integrity
- final tie-breaking
- integration into `src/subtitle_segmenter.py`

Phase 2C ends at `WeightedBoundary`, carrying a signed relative score and the boundary
class/candidate it was computed from. Phase 2D Ã¢â‚¬â€ not designed, scoped, or authorized by
this document Ã¢â‚¬â€ is responsible for consuming that information and turning it into actual
segmentation behavior.

## 22. Implementation Architecture

**IMPLEMENTATION DETAIL (module name Ã¢â‚¬â€ not a design decision):** the smallest production
module necessary is a single new file, recommended as `src/boundary_scoring.py`,
directly matching the existing `boundary_observation.py` / `boundary_classification.py`
naming pattern already established in `src/`. No other module in the repository implies
a different name or location for this responsibility (repository inspection: `src/`
contains no existing scoring-related module, and `src/subtitle_segmenter.py` Ã¢â‚¬â€ confirmed
by `PHASE_2C_NUMERIC_BASELINE_DECISION.md` Ã‚Â§10.1 Ã¢â‚¬â€ has no `BoundaryClass`/
`CharacterClass`/Phase 2C references of any kind, so it is not a candidate location for
this responsibility). A corresponding `tests/test_boundary_scoring.py` follows the
existing `tests/test_<module>.py` convention exactly.

Only one new module is recommended Ã¢â‚¬â€ no additional splitting into multiple files is
implied by anything in the locked design.

**Purity constraints (LOCKED, mirroring Phase 2A/2B's own documented discipline):** the
scorer is a pure transformation, `BoundaryCandidate` (or `ClassifiedBoundary`, per Ã‚Â§6)
in, `WeightedBoundary` out. No text parsing. No span detection. No NLP model calls. No
I/O. No filesystem access. No global state.

## 23. Acceptance Criteria

The eventual implementation is acceptable only if all of the following hold:

1. All locked numeric values (Ã‚Â§5.1Ã¢â‚¬â€œÃ‚Â§5.3) are implemented exactly, with no value changed.
2. Base Classification is read from Phase 2B output, never recomputed independently of
   the real `classify_boundary()`/`classify_boundaries()` functions.
3. Positive Evidence is derived exclusively from existing `BoundaryCandidate`/
   `BoundaryFeatures` evidence fields (Ã‚Â§10), using the exact `{CJK,LATIN}` pair check,
   not the broader `character_class_transition` flag.
4. Protection uses strongest-only Technical/Atomic behavior (`-30` max, never `-60`).
5. INTERNAL is additive on top of any Technical/Atomic protection penalty.
6. Whitespace is `+10` and non-stacking (at most one whitespace bonus per candidate).
7. Transition is symmetric: `+15` in both `CJKÃ¢â€ â€™LATIN` and `LATINÃ¢â€ â€™CJK` directions, using
   the identical mechanical trigger.
8. No normalization exists anywhere in the implementation.
9. No threshold exists anywhere in the implementation.
10. No hard floor (class-specific or otherwise) exists anywhere in the implementation.
11. The input `BoundaryCandidate` (and its `BoundaryFeatures`) is never mutated.
12. Scoring is deterministic: same input always produces an equal output.
13. Calibration scripts (`scripts/calibrate_phase2c_*.py`) are not runtime dependencies
    of the production module.
14. Phase 1 / Phase 2A / Phase 2B (`text_structure.py`, `boundary_observation.py`,
    `boundary_classification.py`) remain untouched, and their existing tests continue to
    pass unmodified.
15. Phase 2D remains untouched Ã¢â‚¬â€ no `should_cut`, threshold, candidate-selection, DP,
    grouping, duration, line-length, or tie-breaking logic is implemented, stubbed, or
    implied.
16. The existing regression suite (397 tests as of this contract) continues to pass
    after the new module and its tests are added.
17. The implementation contains no score-based cut decision of any kind Ã¢â‚¬â€ its output is
    evidence (a `WeightedBoundary`'s `score`), never a boolean or categorical decision.

## 24. Open / Unverified Evidence

This section consolidates every place this contract knowingly leaves a question open,
so a future implementer cannot miss it by reading only one section.

**Interface-shape open questions (Ã‚Â§6, Ã‚Â§14) Ã¢â‚¬â€ must be resolved before coding, do not
block the Final Gate (Ã‚Â§27's own criteria: these are not authoritative contradictions):**

1. Whether `score_boundary()`/`score_boundaries()` accept `BoundaryCandidate` (mirroring
   the calibration script, requiring one internal `classify_boundary()` call) or
   `ClassifiedBoundary` (mirroring the established one-directional "consume the prior
   phase's output object" pattern, calling into Phase 2B logic never).
2. Whether `WeightedBoundary` exposes `base_classification_score`,
   `positive_evidence_score`, and `protection_score` as individually addressable fields,
   or only the final summed `score`.

**Empirically unverified numeric combinations (Ã‚Â§9, Ã‚Â§12, Ã‚Â§13) Ã¢â‚¬â€ mechanically defined by
the locked formula, not empirically observed on any real candidate, and must not be
described as calibrated in code comments, docstrings, or test names:**

3. `OTHER + Atomic + INTERNAL = -50` (P12 remains a `CASE ISSUE`).
4. `OTHER + Transition + Technical = -15`.
5. `OTHER + Whitespace + Technical = -20`.
6. `CLAUSE + Technical = 5`.
7. `ELLIPSIS + Technical = 35`.
8. `SENTENCE_FINAL + Technical = 50`.

**Explicitly not evidence gaps Ã¢â‚¬â€ carried forward from `PHASE_2C_OVERALL_NUMERIC_RECONCILIATION.md`
as already-settled, out-of-scope findings, restated here only for completeness, not
reopened:**

9. The `v1.2.3` second-period span-coverage gap (Phase 1 / Base Classification concern,
   not a Phase 2C scoring concern).
10. The `CI/CD` non-detection gap (Phase 1 / Protection pattern-detection concern, not a
    Phase 2C scoring concern).
11. The semantic usefulness of whitespace (explicitly deferred to Phase 2D).

None of items 1Ã¢â‚¬â€œ8 constitutes an authoritative design contradiction; each is either an
interface-shape choice with no behavioral ambiguity once made, or a numeric value that
the locked formula already determines mechanically. Items 9Ã¢â‚¬â€œ11 are pre-existing,
already-documented non-blocking findings, not new gaps introduced by this contract.

## 25. Final Implementation Gate

**READY FOR IMPLEMENTATION.**

Justification, evaluated against the governing instructions' own stated bar ("Choose
BLOCKED only if an actual authoritative design contradiction prevents a deterministic
implementation"):

- Every numeric value, every interaction rule, and every reachability classification
  needed to compute a score for any real or hypothetical `BoundaryCandidate` is fully and
  unambiguously specified (Ã‚Â§5, Ã‚Â§8Ã¢â‚¬â€œÃ‚Â§13). No two authoritative documents disagree with each
  other anywhere in this contract's scope Ã¢â‚¬â€ `PHASE_2C_OVERALL_NUMERIC_RECONCILIATION.md`
  already confirmed zero cross-layer contradiction, and nothing in this contract's own
  review of the source code changed that conclusion.
- The two open items (Ã‚Â§24, items 1Ã¢â‚¬â€œ2) are interface-shape choices, not numeric or
  behavioral contradictions. Either resolution of each produces a fully deterministic,
  internally consistent implementation; they do not change what score any given real
  candidate receives, only how that score is packaged and accessed. Per the governing
  instructions' explicit guidance, untested combinations and unresolved implementation
  details do not, by themselves, justify `BLOCKED`.
- The six empirically-unverified numeric combinations (Ã‚Â§24, items 3Ã¢â‚¬â€œ8) are mechanically
  determined by the already-locked formula and already-locked component values Ã¢â‚¬â€ nothing
  about implementing them requires a new design decision, only correct arithmetic
  composition of values that are already fixed.

**Before coding begins, the implementer must explicitly resolve (not silently default)
the two open items in Ã‚Â§24** (input shape, and whether component scores are individually
exposed) and must implement Ã‚Â§13's empirically-unverified combinations using the exact
same formula as every confirmed combination, without special-casing or suppressing them,
while ensuring code comments, docstrings, and test names do not describe them as
calibrated evidence.

---

## Files

**Created:** `docs/PHASE_2C_PRODUCTION_SCORING_IMPLEMENTATION_CONTRACT.md` (this
document) Ã¢â‚¬â€ the sole new file produced this round.

**Confirmed unmodified:** `src/*`, `tests/*`, `scripts/*`, and every existing file under
`docs/*`, including every calibration matrix, calibration report, protection report,
design decision, and `PHASE_2C_OVERALL_NUMERIC_RECONCILIATION.md`.

**Test results (health check only, not a requirement of this round):**
```
$ python3 -m pytest tests/ -q
397 passed, 2 warnings, 15 subtests passed
```
No test was run to validate this document's content (there is nothing executable in
it); this was a repository-health sanity check only, and nothing was modified as a
result.
