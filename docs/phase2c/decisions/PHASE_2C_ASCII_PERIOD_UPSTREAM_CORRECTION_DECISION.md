# Phase 2C ASCII Period Upstream Correction Ã¢â‚¬â€ Decision Record (Round A)

**Status:** Design / Behavioral Analysis Only Ã¢â‚¬â€ no production code changed
**Phase:** Cross-cutting (root cause in Phase 2A; observed effects in Phase 2C calibration)
**Purpose:** Determine the exact root cause, behavioral scope, and minimum correction
for the ASCII "." bare-fallback sentence-final leak identified in Phase 2C Protection
Calibration Round 1 (case P11), and produce an implementation-ready contract for Round B.

This document is the sole deliverable of Round A. It does **not** implement the
correction. No file under `src/` was modified to produce this document, and no test
was modified.

---

## 1. Root Cause (summary Ã¢â‚¬â€ full trace in Ã‚Â§4)

The leak originates entirely in **`src/boundary_observation.py`**, inside the private
helper `_walk_terminal_chain()`, specifically its base case (lines 414Ã¢â‚¬â€œ430):

```python
def _walk_terminal_chain(cur: int, siblings: Sequence[Span], source_text: str) -> bool:
    match = next((s for s in siblings if s.end == cur), None)

    if match is None:
        # Base case: no structural span ends exactly here. ...
        ch = source_text[cur - 1] if cur > 0 else ""
        return ch in _SENTENCE_FINAL_CHARS_BARE
    ...
```

The base case fires whenever **no span *ends* exactly at `cur`**. That is a weaker
condition than "no span *covers* the character at `cur - 1`". Whenever an ASCII `.`
sits *inside* (not at the trailing edge of) a multi-character `technical`, `atomic`,
or `punctuation_sequence` span Ã¢â‚¬â€ e.g. the first `.` in `3.14`, the internal dots of
`v1.2.3`, or any non-final position of an ASCII ellipsis run like `......` Ã¢â‚¬â€ no span
ends exactly at that boundary position, so the walk falls through to the bare-character
check, finds `.` in `_SENTENCE_FINAL_CHARS_BARE`, and incorrectly reports
`contains_sentence_final_punctuation = True`.

**Phase owning the behavior:** Phase 2A (`boundary_observation.py`), specifically the
terminal-ending chain / bare-fallback logic. Not Phase 1 (which already correctly
produces `atomic`/`technical`/`punctuation_sequence` spans covering these characters Ã¢â‚¬â€
Phase 2A simply never consults that already-computed structural coverage in this one
code path), and not Phase 2B (which reads `contains_sentence_final_punctuation`
verbatim, by explicit design Ã¢â‚¬â€ see Ã‚Â§10).

**Why the behavior exists:** the module docstring (`boundary_observation.py` lines
78Ã¢â‚¬â€œ86) explains the bare check exists because "Phase 1's own
`_detect_punctuation_sequences` deliberately never emits a span for a lone, single
occurrence of `Ã£â‚¬â€š`/`Ã¯Â¼Â`/`Ã¯Â¼Å¸`/`.`/`!`/`?`... so there is no span to look up for that
specific, narrow case." That justification is correct only when the character is
**truly unspanned** (no span of any kind touches it). The implementation approximates
"unspanned" as "no span ends here," which silently drops the case of a character that
is spanned but not at that span's boundary. This is an implementation gap relative to
the documented intent, not a deliberate design choice Ã¢â‚¬â€ see Ã‚Â§7.

---

## 2. Primary Objective Ã¢â‚¬â€ Answers

1. **Where does it originate?** `src/boundary_observation.py`, function
   `_walk_terminal_chain()`, base case (`match is None` branch). Confirmed by direct
   code trace in Ã‚Â§4.
2. **Which phase owns it?** Phase 2A (Boundary Observation). Not Phase 1, not Phase 2B.
3. **Why does it exist?** An incomplete base-case condition: "no span ends here" was
   used as a proxy for "this character is unspanned," but the two are not equivalent
   for interior characters of a multi-character span (Ã‚Â§1, Ã‚Â§6).
4. **Does it conflict with the approved Phase 2A design?** Yes, in effect, though not
   in explicit intent. The module docstring's own stated exclusion list for the
   terminal chain ("any other, non-transparent structural span... is ordinary
   structured content, so the answer is `False`") already establishes the intended
   rule for spans of type `technical`/`atomic` Ã¢â‚¬â€ that rule is applied correctly at a
   span's *end* position but is silently skipped for a span's *interior* positions,
   which the bare-fallback branch was never designed to check against. This is a gap
   in implementing the existing design, not a case of two conflicting design
   decisions (see Ã‚Â§6 and Ã‚Â§7).
5. **Minimum correction?** See Ã‚Â§8, Ã‚Â§12. Extend the base case's precondition from
   "no span ends at `cur`" to "no span (in the already-flattened, already-scoped
   sibling list) contains the character at `cur - 1`" Ã¢â‚¬â€ i.e. reuse structural
   coverage information Phase 2A already computes, rather than adding any new
   detection.
6. **Which behaviors/tests change?** See Ã‚Â§9 (regression table). Zero currently
   passing assertions change value; several previously untested internal positions
   change from (incorrect) `True`/`SENTENCE_FINAL` to (correct) `False`/`OTHER`.
7. **Which behaviors/tests must remain unchanged?** All currently-tested
   end-of-string / end-of-span SF evidence (`"Done."` with trailing content,
   `"......"` at its true end, `"1,000"` comma-CLAUSE-protection, `"3.14"`/`"v1.2.3"`
   at the specific positions the existing test suite already exercises). See Ã‚Â§9.
8. **Can it be done without changing the Phase 2A public data model?** Yes.
   `BoundaryFeatures`, `CharacterClass`, `PunctuationSequenceState`,
   `StructuralBoundaryContext`, and `BoundaryCandidate` are all unaffected Ã¢â‚¬â€ only the
   *value* computed for `contains_sentence_final_punctuation` at specific interior
   positions changes; no field is added, removed, or retyped.
9. **Any impact on Phase 2B?** No code change required in
   `src/boundary_classification.py` (see Ã‚Â§10) Ã¢â‚¬â€ `classify_boundary()` already reads
   `contains_sentence_final_punctuation` verbatim and applies the frozen
   `SENTENCE_FINAL > ELLIPSIS > CLAUSE > OTHER` precedence unchanged. Once Phase 2A
   reports the corrected (`False`) value at these positions, Phase 2B's existing,
   unmodified logic naturally reclassifies them (mostly to `OTHER`, in the
   `PunctuationSequenceState.INTERNAL` cases the classification stays `OTHER` since
   `_is_ellipsis` requires `END`, not `INTERNAL`).
10. **Does it unblock Technical + INTERNAL?** Yes, for the specific reachable
    construction already identified in Protection Calibration Round 1 (P11's
    URL-with-literal-ellipsis-path probe). See Ã‚Â§11 for the exact before/after
    computation. It does **not** unblock Atomic + INTERNAL (P12) Ã¢â‚¬â€ that remains a
    separate, unrelated reachability gap in Phase 1's atomic-numeric regex, untouched
    by this correction (see Ã‚Â§11).

---

## 3. Authoritative Design Context

Confirmed from the current repository (`src/text_structure.py`,
`src/boundary_observation.py`, `src/boundary_classification.py` module docstrings):

```
Phase 1 (Text Structure) -> Phase 2A (Boundary Observation)
    -> Phase 2B (Boundary Classification) -> Phase 2C (Numeric Calibration/Scoring)
    -> Phase 2D (Segmentation Integration)
```

The proposed correction stays entirely within Phase 2A's existing responsibility
(boundary-local structural evidence, already computed from Phase 1 spans it already
holds). It requires no new raw-text parsing, no new Phase 1 detector, no Phase 2B
change, and no Phase 2C weight change Ã¢â‚¬â€ see Ã‚Â§8 and Ã‚Â§12.

---

## 4. Code Inspection Ã¢â‚¬â€ Actual Execution Traces

All traces below were captured by running the real, unmodified pipeline
(`analyze_text_structure` Ã¢â€ â€™ `observe_boundaries` Ã¢â€ â€™ `classify_boundary`) via a
throwaway interactive interpreter session Ã¢â‚¬â€ no script file was added to the
repository, per the "do not create a Python script" restriction for this round.

### 4.1 `"Done."` (no trailing content)

```
pos=4  L='e' R='.'  sf=False  seq=none  containing=[]  class=other
```

No candidate exists for the position after the trailing `.` (position 5 = `len(text)`
is out of the `1 <= position < len(source_text)` range `observe_boundaries` generates)
Ã¢â‚¬â€ this is the separate, already-documented "string-final representation gap" from
Phase 2C Calibration Round 1/2, not the bug under analysis here. The one real
candidate this text produces (position 4, right *before* the `.`) is correctly
`False`.

### 4.2 `"Done. Next"` (genuine bare `.` **with** trailing content)

```
pos=4  L='e' R='.'  sf=False  seq=none  containing=[]        class=other
pos=5  L='.' R=' '  sf=True   seq=none  containing=[]        class=sentence_final
```

Position 5 is the genuine, intended bare-fallback case: `.` has no span of any kind
covering it (a single, un-spanned ASCII period), and correctly reports `True`. This is
exactly `test_direct_ascii_full_stop` in `tests/test_boundary_observation.py` (padded
with a trailing space to reach this same position) Ã¢â‚¬â€ **must remain `True`**.

### 4.3 `"......"` (pure ASCII ellipsis run, all 6 chars)

```
pos=1  L='.' R='.'  sf=True  seq=internal  containing=[('punctuation_sequence','ellipsis')]  class=sentence_final
pos=2  L='.' R='.'  sf=True  seq=internal  containing=[('punctuation_sequence','ellipsis')]  class=sentence_final
pos=3  L='.' R='.'  sf=True  seq=internal  containing=[('punctuation_sequence','ellipsis')]  class=sentence_final
pos=4  L='.' R='.'  sf=True  seq=internal  containing=[('punctuation_sequence','ellipsis')]  class=sentence_final
pos=5  L='.' R='.'  sf=True  seq=internal  containing=[('punctuation_sequence','ellipsis')]  class=sentence_final
```

**Every internal position is leaked** as `SENTENCE_FINAL`. The one `punctuation_sequence`
span here is `[0, 6)`; `observe_boundaries` only ever generates positions `1..5` for a
6-character string, so `s.end == cur` (`6 == cur`) is never true for any generated
position Ã¢â‚¬â€ the composition-check branch (`_sequence_contains_sentence_final`, which
correctly excludes ASCII `.`) is **never reached** for this string. All 5 candidates
fall through to the bare fallback and leak `True` purely because the character to the
left is `.`.

### 4.4 `"3.14"` (decimal)

```
pos=1  L='3' R='.'  sf=False  containing=[('atomic','numeric')]  class=other
pos=2  L='.' R='1'  sf=True   containing=[('atomic','numeric')]  class=sentence_final   <- LEAK
pos=3  L='1' R='4'  sf=False  containing=[('atomic','numeric')]  class=other
```

Phase 1's `NUMERIC_RE` recognizes `"3.14"` as one `atomic`/`numeric` span `[0, 4)`.
Position 2 sits strictly *inside* that span (`0 <= 1 < 4`), yet no span *ends* at
position 2, so the bare fallback fires and leaks `True`.

### 4.5 `"v1.2.3"` (version)

```
spans: technical/version [0,6) 'v1.2.3'; atomic/numeric [1,4) '1.2'; atomic/numeric [5,6) '3'
pos=1  L='v' R='1'  sf=False  containing=['technical/version']                     class=other
pos=2  L='1' R='.'  sf=False  containing=['technical/version','atomic/numeric']    class=other
pos=3  L='.' R='2'  sf=True   containing=['technical/version','atomic/numeric']    class=sentence_final  <- LEAK
pos=4  L='2' R='.'  sf=False  containing=['technical/version']                     class=other
pos=5  L='.' R='3'  sf=True   containing=['technical/version']                     class=sentence_final  <- LEAK
```

Two independent leaked positions inside one technical span. Both are strictly inside
`technical/version [0,6)`, and neither is at that span's end.

### 4.6 A technical expression containing `.` inside a full sentence

`"Ã§â€ºÂ®Ã¥â€°ÂÃ§â€°Ë†Ã¦Å“Â¬Ã¦ËœÂ¯ v1.2.3Ã¯Â¼Å’Ã¦Å½Â¥Ã¤Â¸â€¹Ã¤Â¾â€ Ã¤Â»â€¹Ã§Â´Â¹Ã¦â€“Â°Ã§â€°Ë†Ã£â‚¬â€š"` (the real text used for Protection
Calibration Round 1's P02/P03/P04 cases) reproduces the identical leak at the
sentence-embedded positions (raw dump, `scripts/phase2c/calibrate_protection_round1.py`
output):

```
pos=9   L='.' R='2'  sf=True  containing=['technical/version','atomic/numeric']  class=sentence_final  base=80.0 SCORE=50.0
pos=11  L='.' R='3'  sf=True  containing=['technical/version']                   class=sentence_final  base=80.0 SCORE=50.0
```

Notably, the Round C report's actual P02/P03/P04 evidence used position 8
(`L='1' R='.'`, genuinely `OTHER`, Technical=Atomic=True, score Ã¢Ë†â€™30.0 exactly as
expected) Ã¢â‚¬â€ a **different**, non-leaked position in the same sentence. Positions 9 and
11 above are additional leak instances present in that same case that were not
separately called out as their own P-numbered case in the Protection Calibration
report (they were absorbed into the general "P11 upstream issue" discussion). This
document treats them as further confirming evidence of the same root cause, not a new
issue.

### 4.7 A punctuation sequence containing `.` (mixed run, `"......!"`)

```
spans: punctuation_sequence/ellipsis_exclaim [0,7) '......!'
pos=1..5  L='.' R='.'  sf=True  seq=internal  class=sentence_final   <- LEAK (x5)
pos=6     L='.' R='!'  sf=True  seq=internal  class=sentence_final   <- LEAK (the position immediately before the final '!' is *also* internal, not END, because span.end=7=len(text) is never a generated position)
```

Same mechanism as Ã‚Â§4.3, extended to a run that also contains a genuine sentence-final
character (`!`) Ã¢â‚¬â€ the composition check that would correctly return `True` here for
the *right* reason (the run contains `!`) is never reached either, because this text
also ends exactly on the run (the representation gap from Ã‚Â§4.1 compounds with this
bug here, though the observed symptom Ã¢â‚¬â€ `True` Ã¢â‚¬â€ happens to look "correct" for this
specific string purely by coincidence of the two independent effects; see Ã‚Â§5.

### 4.8 CJK ellipsis internal position (control Ã¢â‚¬â€ must **not** leak, and does not)

```
text = 'Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã¥â€¢ÂÃ©Â¡Å’Ã¥Ëœâ€ºÃ¢â‚¬Â¦Ã¢â‚¬Â¦Ã¥Â¥Â½'
pos=6  L='Ã¢â‚¬Â¦' R='Ã¢â‚¬Â¦'  sf=False  seq=internal  containing=[('punctuation_sequence','ellipsis')]  class=other
```

`Ã¢â‚¬Â¦` (U+2026) is not in `_SENTENCE_FINAL_CHARS_BARE`, so the bare fallback correctly
returns `False` today. This case is unaffected by the correction (Ã‚Â§9) Ã¢â‚¬â€ it is included
here to establish that the leak is specific to ASCII `.`, not a general internal-position
defect.

---

## 5. Required Behavioral Distinction

**A. Genuine standalone ASCII full stop Ã¢â‚¬â€ `"Done."` / `"Done. Next"`.**
Current design (module docstring) and current implementation agree: a truly unspanned
bare `.` **is** sentence-final evidence. Confirmed correct behavior at Ã‚Â§4.1/Ã‚Â§4.2. This
behavior **should remain** Ã¢â‚¬â€ it is exercised and required by
`test_direct_ascii_full_stop`.

**B. ASCII ellipsis run Ã¢â‚¬â€ `"......"`.**
Must **not** become sentence-final merely because `.` is present. This is already the
explicit, tested rule for the run's *end* position (`_SENTENCE_FINAL_CHARS_IN_SEQUENCE`
excludes `.`). Ã‚Â§4.3 shows the *interior* positions of the same run currently violate
this rule via the bare-fallback path that the composition check never reaches. This is
the core defect.

**C. Decimal / version / technical punctuation Ã¢â‚¬â€ `"3.14"`, `"v1.2.3"`,
`"1.000.000"`, `"example.com"`.**
`.` inside these structures should **not** be sentence-final evidence, by the same
principle already applied (correctly) when technical/atomic protection blocks CLAUSE
in Phase 2B, and by the module docstring's own general rule that "any other,
non-transparent structural span... is ordinary structured content." `3.14` and
`v1.2.3` are in scope for correction (Phase 1 already produces spans covering them Ã¢â‚¬â€
Ã‚Â§4.4/Ã‚Â§4.5). `1.000.000` (repeated-dot thousands notation) and bare `example.com`
(domain with no `http://`/`@` prefix) are **not** in scope Ã¢â‚¬â€ Phase 1's `_NUMERIC_RE`
and `_TECHNICAL_MATCHERS_DEFS` do not recognize either shape as a single covering
span at all (confirmed by trace: no span covers the leaking `.` in either case), so
there is no structural coverage for this correction to consult. These remain residual,
out-of-scope Phase 1 detection gaps Ã¢â‚¬â€ not part of the Round B correction, and not to
be conflated with it.

**D. `.` inside a punctuation sequence.**
The punctuation-sequence representation (specifically, the already-computed
`PunctuationSequenceState`/span containment) should override the bare-character
fallback whenever the character is interior to a `punctuation_sequence` span. Today it
does not (Ã‚Â§4.3/Ã‚Â§4.7) Ã¢â‚¬â€ the composition check is only ever reached at a span's exact
end position, never at an interior one. The correction must not change the *end*-of-
sequence composition-check logic at all Ã¢â‚¬â€ it already excludes `.` correctly.

**E. `.` adjacent to or inside protected structures.**
Technical/Atomic/INTERNAL evidence is computed entirely independently of
`contains_sentence_final_punctuation` (see `_structural_context_at` and
`_punctuation_sequence_state_at` in `boundary_observation.py` Ã¢â‚¬â€ neither is consulted
by `_walk_terminal_chain`). The correction reuses this already-independent evidence
(specifically: "does any span contain this character") purely to gate the bare
fallback; it does not entangle the SF evidence computation with the Technical/Atomic/
INTERNAL evidence computation, and does not change how Phase 2C's provisional protection
penalties are applied to whatever `BoundaryClass` results.

---

## 6. Existing Design Conflict Ã¢â‚¬â€ Analysis

The claimed "two concepts" resolution (`_SENTENCE_FINAL_CHARS_BARE` vs.
`_SENTENCE_FINAL_CHARS_IN_SEQUENCE`) **is** sufficient for the one narrow case it was
built for: the exact **end** boundary of a punctuation_sequence span, where
`match.end == cur` reliably routes to the composition check. It is **not** sufficient
for any position that is *interior* to a `punctuation_sequence`, `atomic`, or
`technical` span, because the base-case branch that performs the bare check is reached
only by testing "does any span *end* exactly here" Ã¢â‚¬â€ never "is this character *inside*
any span at all."

Observed behavior for the required probe set, confirmed by direct execution (Ã‚Â§4):

| Input | Observed `contains_sentence_final_punctuation` at the relevant boundary | Correct per design intent? |
|---|---|---|
| `.` (standalone, unspanned, trailing content) | `True` | Yes |
| `Done.` (trailing content) | `True` | Yes |
| `......` (interior positions) | `True` (leaked) | **No** Ã¢â‚¬â€ should be `False` |
| `Ã¢â‚¬Â¦Ã¢â‚¬Â¦` (CJK, interior) | `False` | Yes |
| `Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¯Â¼Å¸` (interior) | `False` | Yes (composition would also say `False` if reached, since `Ã¯Â¼Å¸` is not the char immediately checked here and these positions never reach `match.end==cur` either Ã¢â‚¬â€ both paths agree) |
| `......!` (interior, run also contains `!`) | `True` (leaked, but for the wrong reason Ã¢â‚¬â€ via bare fallback, not via composition) | Coincidentally matches what composition *would* say (`!` makes it genuinely SF), but only by accident Ã¢â‚¬â€ see Ã‚Â§4.7 |
| `3.14` (interior) | `True` (leaked) | **No** Ã¢â‚¬â€ should be `False` |
| `v1.2.3` (interior, both leak positions) | `True` (leaked) | **No** Ã¢â‚¬â€ should be `False` |

This distinction (bare vs. sequence-composition) is a correct idea, incompletely
applied: it correctly disambiguates "is this position the tail of a punctuation
sequence" but never asks "is this position anywhere *inside* a punctuation sequence,
technical span, or atomic span at all." The fix in Ã‚Â§8/Ã‚Â§12 closes exactly that gap.

---

## 7. Explicit Semantic Statement (do not silently decide)

1. **What the current design says:** the module docstring for
   `contains_sentence_final_punctuation` states ASCII `.` is supported "on equal
   footing with CJK punctuation" for the bare, fully-unspanned case, and that a `.`
   participating in an ellipsis-family `punctuation_sequence` must never make that
   sequence register as sentence-final on the strength of `.` alone. Both rules are
   stated unconditionally with respect to *any* boundary position that reaches the
   relevant branch Ã¢â‚¬â€ the docstring does not explicitly discuss interior-vs-end
   positions of a multi-character span as a distinct third case.
2. **What the current implementation does:** applies the "equal footing" bare rule to
   *any* position where no span happens to end, including positions that are
   demonstrably interior to a `technical`, `atomic`, or `punctuation_sequence` span
   (Ã‚Â§4.3Ã¢â‚¬â€œÃ‚Â§4.6). It applies the ellipsis-composition exclusion rule only at a span's
   exact end position.
3. **Where they differ:** the implementation is stricter/narrower in *scope of
   applicability* than the design's evident intent. The design's justification for
   the bare check ("no span to look up... for a lone, un-spanned terminal mark") is
   explicitly about characters with **no span at all** Ã¢â‚¬â€ the implementation's actual
   guard ("no span *ends* here") is weaker and lets spanned-but-interior characters
   through by accident.
4. **What behavioral rule should become authoritative:** the bare-fallback check must
   apply **only** when the character at `cur - 1` is not covered by any span at all
   (of any structural type) in the currently-scoped sibling list. If it is covered by
   a `technical` or `atomic` span, or is interior to a `punctuation_sequence` span
   (i.e. `PunctuationSequenceState.INTERNAL` in Phase 2A's own already-computed sense
   at that position), the walk must treat it as ordinary, non-bare structural content
   and return `False` Ã¢â‚¬â€ mirroring, not contradicting, the existing end-of-span rules.
   This does not need to be independently invented: it is a direct, mechanical
   extension of the "any other, non-transparent structural span... is ordinary
   structured content" rule the docstring already states for the end-of-span case,
   applied consistently to interior positions too.

There is no genuine remaining ambiguity in what the rule *should* be Ã¢â‚¬â€ the ambiguity
was only ever in the implementation's incomplete coverage of an already-stated rule.
The one open point requiring an explicit decision (rather than a mechanical
derivation) is Ã‚Â§5-C's boundary: whether `1.000.000` / bare `example.com` are in scope.
This document recommends **out of scope** (Phase 1 detection gap, not a Phase 2A
representation bug) Ã¢â‚¬â€ see Ã‚Â§8.

---

## 8. Minimum-Correction Principle

The smallest change that restores the intended behavior is a **single additional
containment check inside the existing base case** of `_walk_terminal_chain()` in
`src/boundary_observation.py`. It requires:

- No rewrite of Phase 1.
- No rewrite of punctuation detection (Phase 1's detectors are unchanged and already
  produce the necessary span coverage Ã¢â‚¬â€ the fix only *reads* spans Phase 1 already
  emits).
- No new NLP dependency, no new punctuation parser.
- No new scoring mechanism (Phase 2C weights untouched).
- No change to Phase 2B's classification architecture (its existing, unmodified logic
  naturally produces the corrected classification once Phase 2A reports the corrected
  evidence Ã¢â‚¬â€ see Ã‚Â§10).
- No change to Phase 2D (not implemented; out of scope regardless).

The existing Phase 1 representation (spans already produced for `technical`, `atomic`,
`punctuation_sequence`) is sufficient for every in-scope case identified in this
round. `1.000.000` and bare `example.com` are explicitly **not** sufficient Ã¢â‚¬â€ Phase 1
currently produces **no span at all** covering the leaking `.` in either shape (Ã‚Â§4,
Ã‚Â§5-C) Ã¢â‚¬â€ so the proposed correction cannot and does not touch those two residual cases;
they are out of scope for Round B and should be tracked separately if ever prioritized.

---

## 9. Regression Impact Analysis

| Existing behavior / test | Classification |
|---|---|
| `test_direct_ascii_full_stop` (`"Done."` + trailing content, bare unspanned `.`) | **KEEP** Ã¢â‚¬â€ position has no covering span at all; unaffected by the added containment check |
| `test_direct_full_stop`/`_exclaim`/`_question` (CJK bare terminal chars) | **KEEP** Ã¢â‚¬â€ unrelated character set |
| `test_ellipsis_cjk_is_not_sentence_final` / `test_ellipsis_ascii_is_not_sentence_final` | **KEEP** Ã¢â‚¬â€ both check the position at the true *end* of the run (composition-check branch, `match.end==cur`), never an interior position; unaffected |
| `test_ellipsis_then_question_is_sentence_final` and siblings (interrobang family) | **KEEP** Ã¢â‚¬â€ all check end-of-sequence positions |
| `test_comma_is_not_sentence_final` | **KEEP** Ã¢â‚¬â€ `,` is not in either sentence-final character set; unrelated |
| `test_closing_quote_after/without_sentence_final_punctuation`, nested-delimiter, emoji/emoticon-attachment tests | **KEEP** Ã¢â‚¬â€ all exercise the transparent-attachment/paired-delimiter descent branches, not the bare base case for an interior technical/atomic/sequence character |
| `test_ordinary_text_terminates_the_chain`, `test_whitespace_between_punctuation_and_closing_delimiter_breaks_the_chain` | **KEEP** Ã¢â‚¬â€ ordinary-content termination is unaffected; these already return `False` for unrelated reasons |
| `test_comma_inside_thousands_separated_number_is_not_clause` (`"1,000"`) | **KEEP** Ã¢â‚¬â€ `,` is never sentence-final evidence in either character set; this test is about CLAUSE protection, a separate code path (`_is_technical_or_atomic_protected`), untouched by this correction |
| `test_decimal_point_is_not_clause_and_not_a_protection_exerciser` (`_classify_at("3.14", 1)`) | **KEEP** Ã¢â‚¬â€ exercises position 1 (`L='3' R='.'`), not position 2 (the leaking one); explicitly documented in its own test name as deliberately *not* a protection exerciser |
| `test_version_string_dot_is_not_clause_and_not_a_protection_exerciser` (`_classify_at("v1.2.3", 2)`) | **KEEP** Ã¢â‚¬â€ exercises position 2 (`L='1' R='.'`), not positions 3/5 (the leaking ones) |
| `test_internal_ellipsis_boundary_is_not_ellipsis` (CJK `"Ã¢â‚¬Â¦Ã¢â‚¬Â¦" + "Ã¢â‚¬Â¦Ã¢â‚¬Â¦"`, position 2) | **KEEP** Ã¢â‚¬â€ CJK ellipsis characters are not in `_SENTENCE_FINAL_CHARS_BARE`; already `False` for an independent reason, unaffected either way |
| `test_same_input_produces_equal_output` (determinism test, includes `"3.14"` and `"......"` substrings) | **KEEP** Ã¢â‚¬â€ only asserts two calls return an *equal* result to each other, not any specific value; unaffected by any value change |
| `test_no_candidate_carries_score_weight_or_should_cut_fields` | **KEEP** Ã¢â‚¬â€ field-shape test, unrelated to values |
| *(no existing test)* Ã¢â‚¬â€ internal positions of `"......"`, `"......!"` | **EXPECTED CHANGE** Ã¢â‚¬â€ `True`Ã¢â€ â€™`False` (SENTENCE_FINALÃ¢â€ â€™OTHER); not currently asserted anywhere, so this is a value correction with zero test-breakage, but is a real, user-visible behavior change worth calling out explicitly per Ã‚Â§5-D |
| *(no existing test)* Ã¢â‚¬â€ interior `.` positions of `"3.14"` (position 2) and `"v1.2.3"` (positions 3, 5) | **EXPECTED CHANGE** Ã¢â‚¬â€ `True`Ã¢â€ â€™`False` (SENTENCE_FINALÃ¢â€ â€™OTHER); not currently asserted |
| Bare `"1.000.000"` / bare `"example.com"` (`.` positions with no covering span at all) | **UNCERTAIN / OUT OF SCOPE** Ã¢â‚¬â€ remain `True` after the correction (no span exists for the check to consult); flagged as a residual Phase 1 detection gap, not touched by Round B |
| Protection Calibration Round 1's P02/P03/P04 real-pipeline candidate selection (position 8 in the full sentence) | **KEEP** Ã¢â‚¬â€ that candidate was never a leaked position to begin with (Ã‚Â§4.6) |
| Protection Calibration Round 1's P11 (Technical + INTERNAL reachability) | **EXPECTED CHANGE in classification, not in test** Ã¢â‚¬â€ no test currently encodes this expectation (calibration-only, not implemented in `tests/`); becomes reachable on a clean, non-leaked candidate after correction (Ã‚Â§11) |

No `POTENTIAL REGRESSION` items were identified: every existing assertion in
`tests/test_boundary_observation.py` and `tests/test_boundary_classification.py` that
touches sentence-final evidence, ellipsis, technical/atomic protection, or
punctuation sequences was individually traced against the proposed rule and found to
either check a position unaffected by the added containment check, or to already
assert the value the corrected rule also produces.

---

## 10. Phase 2B Impact

`src/boundary_classification.py`'s `_is_sentence_final()` reads
`candidate.features.contains_sentence_final_punctuation` verbatim (line 166) with no
re-derivation and no consultation of `structural_context`/`containing_spans` at all.
Its own module docstring states this explicitly and by design: "Sentence-final
punctuation immediately following technical/atomic content... is never suppressed by
this protection, because SENTENCE_FINAL is evaluated before CLAUSE ever runs, and
`contains_sentence_final_punctuation` does not consult containing-span type
information at all." This is confirmed, unmodified, current behavior Ã¢â‚¬â€ not an
assumption.

Consequently: correcting `contains_sentence_final_punctuation` in Phase 2A **does**
change `BoundaryClass` for the affected candidates (leaked `SENTENCE_FINAL` Ã¢â€ â€™
`OTHER`, per the classification precedence
`SENTENCE_FINAL > ELLIPSIS > CLAUSE > OTHER` Ã¢â‚¬â€ since `_is_ellipsis` requires
`PunctuationSequenceState.END`, not `INTERNAL`, and `_is_clause` requires
`left_char` to be a clause-punctuation character, which `.` never is, every corrected
position resolves to `OTHER`, never accidentally to `ELLIPSIS` or `CLAUSE`).

**No Phase 2B implementation code needs to change.** This confirms the preferred
result the contract asked to verify (Ã‚Â§10 of the round contract): "Phase 2A correction
Ã¢â€ â€™ correct `BoundaryFeatures` Ã¢â€ â€™ existing Phase 2B logic naturally produces correct
classification." Verified directly by tracing `classify_boundary()`'s logic against
the corrected evidence values, not assumed.

**Affected classes of cases (by structural shape):** any boundary position that is
(a) interior to a `technical` or `atomic` span and (b) immediately preceded by an
ASCII `.`; or (c) interior (not END) to a `punctuation_sequence` span and (d)
immediately preceded by an ASCII `.`. No other shape is affected.

---

## 11. Phase 2C Impact

The correction changes **zero** Phase 2C numeric values. The provisional values
remain exactly as specified: `Technical = -30`, `Atomic = -30`,
`INTERNAL = -20` (and, orthogonally, whichever Technical+Atomic combination rule a
future "Phase 2C Numeric Strategy v1" adopts Ã¢â‚¬â€ additive or strongest-only, per Round
1/2 vs. Protection Round 1 Ã¢â‚¬â€ is entirely unaffected by this correction). The
correction only changes which `BoundaryClass` a small set of candidates receive,
making the *evidence* Phase 2C consumes accurate.

**Does the P11 target case become observable?** Yes, for the specific real
construction already used in Protection Calibration Round 1
(`"Ã¨Â«â€¹Ã¥ÂÆ’Ã¨â‚¬Æ’ http://example.com/a...b Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã©Â ÂÃ©ÂÂ¢Ã£â‚¬â€š"`). Before correction (Ã‚Â§4 of the
Protection Calibration Round 1 report): positions 25/26 (the internal `...` inside the
URL's path segment) were classified `SENTENCE_FINAL` (leaked), yielding
`base=80, protection=-30 Ã¢â€ â€™ score=30.0` under the strongest-only model Ã¢â‚¬â€ the reported
`UPSTREAM ISSUE`. After correction, those same two positions:

```
containing = [('technical','url'), ('punctuation_sequence','ellipsis')]
```

no longer satisfy the bare fallback (the `.` is interior to both a `technical` span
and a `punctuation_sequence` span), so `contains_sentence_final_punctuation` becomes
`False`. `PunctuationSequenceState` at these positions is already (and remains)
`INTERNAL` Ã¢â‚¬â€ that field is untouched by this correction. `_is_ellipsis` requires
`END`, so still `False`. `_is_clause` requires a clause-punctuation `left_char`
(`.` is not one), so still `False`. Result: `BoundaryClass.OTHER`, `Technical=True`,
`INTERNAL=True` Ã¢â‚¬â€ exactly the target case:

```
score = 0 (OTHER) - 30 (Technical, strongest-only) - 20 (INTERNAL) = -50
```

This matches the matrix's expected value for P11 exactly, and Ã¢â‚¬â€ per Ã‚Â§9's regression
scan Ã¢â‚¬â€ reaches this value via a real pipeline candidate, not a synthetic one.

**Does it unblock P12 (Atomic + INTERNAL)?** No. P12's non-reachability is unrelated
to this bug: Phase 1's `_NUMERIC_RE` never produces an `atomic`/`numeric` span that
geometrically overlaps a multi-character `punctuation_sequence` span in any of the
four constructions tested in Protection Calibration Round 1 (`100...200`,
`3.14......`, `3..14`, `3....14` Ã¢â‚¬â€ in every case the atomic numeric span and the
ellipsis span are adjacent, never overlapping). This correction only changes how the
*existing* structural coverage is consulted for the SF-evidence computation; it does
not change what structural coverage Phase 1 produces in the first place. P12 remains
a genuine, unrelated `CASE ISSUE`.

---

## 12. Required Design Decision

**Decision:**
Extend `_walk_terminal_chain()`'s base case in `src/boundary_observation.py` so the
bare-character sentence-final fallback fires only when the character immediately
before the boundary position is not covered by *any* span (of any structural type) in
the currently-scoped sibling list Ã¢â‚¬â€ not merely when no span happens to *end* exactly
at that position.

**Scope:**
File: `src/boundary_observation.py`. Function: `_walk_terminal_chain()` only (its
`match is None` base-case branch specifically). No other function in this file, and
no other file, needs to change.

**Behavior:**
In the base case, additionally check whether any span `s` in the current `siblings`
list satisfies `s.start <= cur - 1 < s.end` (i.e. the character at index `cur - 1` is
strictly within that span's character range). If such a span exists, treat this
exactly like the existing "any other, non-transparent structural span... is ordinary
structured content" branch and return `False`, regardless of what the literal
character is. Only when no span at all covers `cur - 1` does the existing
`ch in _SENTENCE_FINAL_CHARS_BARE` check apply.

**Examples:**

| Input Ã¢â€ â€™ position | Current result | Corrected result |
|---|---|---|
| `"Done. Next"` Ã¢â€ â€™ pos 5 (bare, unspanned `.`) | `True` | `True` (unchanged) |
| `"......"` Ã¢â€ â€™ pos 1Ã¢â‚¬â€œ5 (interior to `punctuation_sequence`) | `True` (leaked) | `False` |
| `"3.14"` Ã¢â€ â€™ pos 2 (interior to `atomic/numeric`) | `True` (leaked) | `False` |
| `"v1.2.3"` Ã¢â€ â€™ pos 3, pos 5 (interior to `technical/version`) | `True` (leaked) | `False` |
| `"1,000"` Ã¢â€ â€™ pos 2 (interior to `atomic/numeric`, but `,` is not a sentence-final char in either set regardless) | `False` | `False` (unchanged) |
| `"1.000.000"` Ã¢â€ â€™ pos 6 (no covering span at all Ã¢â‚¬â€ Phase 1 detection gap) | `True` | `True` (unchanged Ã¢â‚¬â€ out of scope) |

**Rationale:**
This is the minimum change that makes the already-computed, already-correct Phase 1
span coverage authoritative for the one code path that was not yet consulting it. It
adds no new detection, no new dependency, no new data model field Ã¢â‚¬â€ it is a single
`any(...)` guard reusing data already available in the function's own `siblings`
parameter.

**Non-goals:**
Do not change `_SENTENCE_FINAL_CHARS_BARE`, `_SENTENCE_FINAL_CHARS_IN_SEQUENCE`,
`_sequence_contains_sentence_final()`, the transparent-attachment (emoji/emoticon) or
paired-delimiter descent branches, `PunctuationSequenceState` computation, structural
context computation, any Phase 2B classification rule, or any Phase 2C weight. Do not
attempt to also fix the `1.000.000` / bare `example.com` residual cases (Ã‚Â§5-C, Ã‚Â§8) Ã¢â‚¬â€
those require a Phase 1 detection change, which is explicitly out of scope for this
correction and for Round B.

**Regression impact:**
Zero existing test regressions (Ã‚Â§9, full table). Several previously-untested interior
positions change value from `True`/`SENTENCE_FINAL` to `False`/`OTHER`, which is the
intended correction.

**Phase boundary impact:**
Phase 1: none. Phase 2A: the only phase whose implementation changes. Phase 2B: none
required (existing logic naturally propagates the fix Ã¢â‚¬â€ verified in Ã‚Â§10). Phase 2C:
none (no weight change; only the input evidence becomes accurate). Phase 2D: none
(not implemented, not touched).

**Calibration impact:**
Unblocks Protection Calibration's P11 (Technical + INTERNAL) on the real, previously
leak-contaminated candidate Ã¢â‚¬â€ see Ã‚Â§11 for the exact before/after score. Does not
unblock P12 (Atomic + INTERNAL), which remains a separate, unrelated Phase 1
detection-coverage gap.

---

## 13. Before / After Behavior Table

| Input | Current behavior | Intended behavior | Correction needed |
|---|---|---|---|
| `Done.` (no trailing content) | No candidate exists after the `.` (string-final representation gap Ã¢â‚¬â€ separate, already-documented issue) | Same (out of scope for this correction) | No |
| `Done. Next` | Boundary after `.`: `SENTENCE_FINAL` (`True`) | Same | No |
| `.` (bare, unspanned, mid-string) | `SENTENCE_FINAL` (`True`) | Same | No |
| `......` (interior positions) | `SENTENCE_FINAL` (`True`, leaked) | `OTHER` (`False`) | **Yes** |
| `Ã¢â‚¬Â¦Ã¢â‚¬Â¦` (CJK, interior) | `OTHER` (`False`) | Same | No |
| `Ã¢â‚¬Â¦Ã¢â‚¬Â¦Ã¯Â¼Å¸` (interior positions) | `OTHER` (`False`) | Same | No |
| `3.14` (interior `.`) | `SENTENCE_FINAL` (`True`, leaked) | `OTHER` (`False`) | **Yes** |
| `v1.2.3` (both interior `.` positions) | `SENTENCE_FINAL` (`True`, leaked) Ãƒâ€”2 | `OTHER` (`False`) Ãƒâ€”2 | **Yes** |
| technical `.` case (`v1.2.3` embedded in a full sentence, P02/P03/P04 case) | `SENTENCE_FINAL` (`True`, leaked) at positions 9/11 of the raw dump; position 8 (the calibration-report candidate) already correct | Positions 9/11 become `OTHER`; position 8 unchanged | **Yes** (for positions 9/11 only) |
| P11 probe (`http://example.com/a...b`, interior of the literal `...` path segment) | `SENTENCE_FINAL` (`True`, leaked); Technical+INTERNAL scores `+30` instead of `-50` | `OTHER` (`False`); Technical+INTERNAL scores `-50` as intended | **Yes** |
| `1.000.000` (no covering span) | `SENTENCE_FINAL` (`True`) at the ungoverned `.` | Ideally `False`, but no structural coverage exists to key off of | **No** (out of scope Ã¢â‚¬â€ Phase 1 gap) |
| bare `example.com` (no `http://`/`@`, no covering span) | `SENTENCE_FINAL` (`True`) | Ideally `False`, but no structural coverage exists to key off of | **No** (out of scope Ã¢â‚¬â€ Phase 1 gap) |

---

## 14. Implementation Contract for Round B

This section is self-contained and implementation-ready; a Round B engineer/session
should be able to execute it without repeating the analysis above.

1. **Exact file(s) allowed to change:** `src/boundary_observation.py` only.
2. **Exact function(s) allowed to change:** `_walk_terminal_chain()` only. Do not
   change `_contains_sentence_final_punctuation()`, `_sequence_contains_sentence_final()`,
   `_punctuation_sequence_state_at()`, `_structural_context_at()`,
   `observe_boundaries()`, `classify_character()`, or any other function in this
   file or any other file.
3. **Exact behavioral rule:** in `_walk_terminal_chain()`'s `match is None` branch,
   before returning `ch in _SENTENCE_FINAL_CHARS_BARE`, check whether any span `s` in
   `siblings` satisfies `s.start <= cur - 1 < s.end`. If such a span exists, return
   `False` instead (do not evaluate the character-membership check at all in that
   case). If no such span exists, behavior is unchanged (evaluate
   `ch in _SENTENCE_FINAL_CHARS_BARE` exactly as today).
4. **Exact test cases to add:** new tests in `tests/test_boundary_observation.py`
   (`SentenceFinalEvidenceTests` class or a new class in the same file) asserting:
   - `"......"` interior position (e.g. position 2 of a 6-dot run, or equivalently a
     position produced by embedding the run mid-string so an interior position is
     unambiguous) Ã¢â€ â€™ `contains_sentence_final_punctuation == False`.
   - `"3.14"` position 2 Ã¢â€ â€™ `False`.
   - `"v1.2.3"` positions 3 and 5 Ã¢â€ â€™ `False`.
   - Corresponding `classify_boundary()` tests in `tests/test_boundary_classification.py`
     asserting `BoundaryClass.OTHER` (not `SENTENCE_FINAL`) at the same positions.
   - A retained/positive test that `"Done. Next"`'s bare, unspanned `.` (no covering
     span) still evaluates to `True`/`SENTENCE_FINAL` Ã¢â‚¬â€ guards against
     over-correction.
5. **Tests that must remain unchanged (do not edit):** every test enumerated as
   `KEEP` in Ã‚Â§9's regression table, in both `tests/test_boundary_observation.py` and
   `tests/test_boundary_classification.py`, in particular
   `test_direct_ascii_full_stop`, `test_ellipsis_ascii_is_not_sentence_final`,
   `test_decimal_point_is_not_clause_and_not_a_protection_exerciser`,
   `test_version_string_dot_is_not_clause_and_not_a_protection_exerciser`, and
   `test_comma_inside_thousands_separated_number_is_not_clause`.
6. **Expected regression count behavior:** the full existing suite (389 tests as of
   this round, both under `pytest` and `python -m unittest discover`) must continue
   to pass unmodified, with only new test cases added (test count increases; zero
   existing test bodies change; zero existing assertions change value).
7. **What must NOT be modified:** `src/text_structure.py` (Phase 1), any file in
   `src/boundary_classification.py` (Phase 2B), `src/subtitle_segmenter.py`, any
   calibration script under `scripts/`, any of the three existing calibration report
   documents, and no Phase 2C production module (none exists yet Ã¢â‚¬â€ do not create
   one). No git commit.
8. **How to verify the Technical + INTERNAL case afterward:** re-run
   `scripts/calibrate_phase2c_protection_round1.py` (unmodified Ã¢â‚¬â€ it is calibration
   tooling, not production code, and already implements the strongest-only scoring
   formula) against the existing `P11_probe_url_ellipsis` case
   (`"Ã¨Â«â€¹Ã¥ÂÆ’Ã¨â‚¬Æ’ http://example.com/a...b Ã©â‚¬â„¢Ã¥â‚¬â€¹Ã©Â ÂÃ©ÂÂ¢Ã£â‚¬â€š"`). After the Round B correction, the
   two candidates at the interior `...` positions should report
   `class=other`, `containing=[('technical','url'), ('punctuation_sequence','ellipsis')]`,
   and `SCORE=-50.0`. This confirms both the correction itself and its calibration
   impact without requiring any new script or production module.

---

## 15. Testing (baseline, observation only)

Run for observation only Ã¢â‚¬â€ nothing modified as a result:

```
$ python3 -m pytest tests/ -q
389 passed, 2 warnings, 15 subtests passed in 22.83s

$ python3 -m unittest discover -s tests -v
Ran 389 tests in 19.612s
OK
```

Baseline unchanged from all three prior calibration rounds (389 passed / OK). No test
was modified to produce this result.

---

## 16. Git

No `git add`, `git commit`, `git reset`, `git checkout`, or `git restore` was run.
The only repository change made during this round is the addition of this single
document.

---

## Files created / modified / untouched

**Created:**
- `docs/phase2c/decisions/PHASE_2C_ASCII_PERIOD_UPSTREAM_CORRECTION_DECISION.md` (this document)

**Modified:** none.

**Untouched:** `src/text_structure.py`, `src/boundary_observation.py`,
`src/boundary_classification.py`, `src/subtitle_segmenter.py`, every file under
`tests/`, every file under `scripts/`, every previously-produced calibration
document/matrix/script from Rounds A/B/C.

**Test results:** `pytest tests/ -q` Ã¢â€ â€™ 389 passed, 2 warnings, 15 subtests passed
(22.83s). `python -m unittest discover -s tests -v` Ã¢â€ â€™ Ran 389 tests, OK (19.612s).
No regressions; no test modified.
