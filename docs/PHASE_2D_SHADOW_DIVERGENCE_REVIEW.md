# Phase 2D Shadow Divergence Review / Production Cutover Readiness Review

Status of this document: a **review-only** artifact. It creates no new
implementation, modifies no existing code or test file, and does not wire
`src/boundary_segmentation_adapter.py` into any production call path. Its
sole purpose is to state, with cited evidence, what the shadow-mode
comparison of Phase 2D against production actually shows, and whether that
evidence is sufficient to begin designing a production cutover.

---

## 1. Review Status

**COMPLETE.** All corpus items were re-run against the current, unmodified
source tree in this review round. Every claim below is backed either by a
freshly captured shadow-mode run (this round), a checksum comparison
against the previously accepted/frozen state, or a direct citation of a
Phase 2C/2D design or calibration document already in the repository.

This review does not implement Step 2 of the migration plan (gated
production cutover). It answers only whether the evidence gathered so far
is sufficient to *begin designing* that step.

---

## 2. Baseline Verification

All files relevant to the Phase 1→2D→Adapter→Shadow chain were checksummed
at the start of this review round and found unchanged from their previously
accepted/frozen state:

| File | MD5 | Status |
|---|---|---|
| `src/text_structure.py` | `b1a7185f99d46741b30ffbf58208eda5` | unchanged (Phase 1, frozen) |
| `src/boundary_observation.py` | `292adeb728ccd6bd7661179459310c7e` | unchanged (Phase 2A, frozen) |
| `src/boundary_classification.py` | `b8df71e36ac65d7e3abb1d8ce8933334` | unchanged (Phase 2B, frozen) |
| `src/boundary_scoring.py` | `2a1ded4e11df16d976f5d7fa475204e6` | unchanged (Phase 2C, frozen) |
| `src/boundary_segmentation.py` | `eb4a3f49f72bb49918f83e66d49dba41` | unchanged (Phase 2D, frozen) |
| `src/boundary_segmentation_adapter.py` | `0adb935ab35132902189e9b324966495` | unchanged (adapter, frozen) |
| `src/subtitle_segmenter.py` | `9ecdb9741fabaac6fd4ccbaa643a6a58` | unchanged (production) |
| `src/subtitle_pipeline.py` | `2322747088fb9cfbc1eb3d30c4825e75` | unchanged (production) |
| `src/subtitle_alignment.py` | `9b14f0d6f68857e8630c9d97aa026e8a` | unchanged (production) |
| `tests/test_boundary_segmentation.py` | `f8ab97840e4ed6885f23356ccafb3e77` | unchanged |
| `tests/test_boundary_segmentation_adapter.py` | `26a3eba51d23296c717487a40299d108` | unchanged |
| `tests/test_shadow_mode_comparison.py` | `55d1cc45da517189a175f6201766bf7f` | unchanged |

Full suite: **531 passed, 30 subtests passed** (`python -m pytest tests/ -q`),
identical to the count recorded at the end of the correction round. No
regression. Shadow suite alone: **17 passed, 15 subtests passed**
(`python -m pytest tests/test_shadow_mode_comparison.py -q -s`).

No production import of `src.boundary_segmentation_adapter` exists anywhere
under `src/` (confirmed by grep in this round — only `tests/` imports it).
Production wiring remains absent.

---

## 3. Current Production Path

`subtitle_pipeline.py` calls `subtitle_segmenter.segment_notes_for_subtitles(text, max_display_width)`
for each slide's notes text. That function (unmodified, frozen production
code):

- Splits on primary sentence-ending punctuation and a fixed set of
  secondary "rhythmic" break characters, `_SECONDARY_BREAK_CHARS = "，、；：,;:"`
  (note: **colon is included** as a secondary break character).
- Packs consecutive pieces up to `max_display_width` (default 36 — "18
  full-width characters" per the project owner's original spec), using a
  hand-written greedy/width-driven packer, not a scoring model.
- Constructs each segment's displayed text via `_display_text_for_span()`
  and strips trailing rhythmic/terminal punctuation via
  `_strip_trailing_punctuation()`, against `_STRIP_TRAILING_CHARS =
  "。，、；：.,;:"` (colon **is** one of the stripped trailing characters).
  `_display_width()` in this module measures the **normalized, already
  display-processed** string.
- Returns `{"text", "source_start_offset", "source_end_offset"}` dicts in
  reading order; offsets index into the original notes text.
- Has no concept of a scored "boundary strength" — decisions are entirely
  rule- and width-based.

`subtitle_alignment.py` consumes this function's output downstream for
audio/timing alignment; it is not itself part of the segmentation decision
and is unaffected by anything evaluated in this review.

---

## 4. Phase 2D Path

`boundary_segmentation_adapter.segment_notes_for_subtitles_via_boundary_engine(text, max_display_width)`
composes the real, unmodified Phase 1→2A→2B→2C chain
(`analyze_text_structure` → `observe_boundaries` → `classify_boundaries` →
`score_boundaries`), then calls the frozen `boundary_segmentation.segment_boundaries()`:

- Splits the source into paragraphs, computes the minimum feasible cut
  count `K` per paragraph from a **pure width constraint measured on the
  raw source-text span** (`_display_width(source_text[start:end])`, not a
  normalized/stripped display string), then chooses, among all
  width-feasible partitions into exactly `K` segments, the one maximizing
  total boundary score, tie-broken by lowest sum-of-squared-widths.
- Never reimplements or second-guesses a `WeightedBoundary.score` — every
  score is read verbatim from the frozen Phase 2C output (confirmed by
  source inspection: no scoring logic exists in
  `boundary_segmentation.py` or the adapter).
- Never uses a fixed score threshold — only relative comparisons (per
  `PHASE_2D_SCOPE_AND_ARCHITECTURE.md` §9, confirmed by source: no
  `score >= X` pattern anywhere in the module).
- Has no CJK word-segmentation awareness (no jieba import in
  `boundary_segmentation.py` or the adapter) — an explicitly accepted,
  documented gap, not an oversight.
- The adapter constructs display text via `_display_text_for_span`/
  `_strip_trailing_punctuation`, imported directly (not reimplemented)
  from `src.subtitle_segmenter` — the same normalization/stripping
  functions production itself uses for its own display text.
- Returns offsets into the original `text` argument, in the same
  `{"text", "source_start_offset", "source_end_offset"}` shape as
  production.

No file in this path is imported by, or imports from, any production
call-path module. This was re-confirmed by grep in this round.

---

## 5. Shadow Corpus Results (freshly captured this round)

| Item | max_width | Expected | Actual | prod segments | adapter segments |
|---|---:|---|---|---:|---:|
| A_ordinary_punctuation | 36 | IDENTICAL | IDENTICAL | 1 | 1 |
| B_chinese_punctuation | 36 | IDENTICAL | IDENTICAL | 2 | 2 |
| C_colon_cjk_forced_split | 20 | COLON_DRIVEN_DIVERGENCE | COLON_DRIVEN_DIVERGENCE | 4 | 4 |
| D_colon_ascii_forced_split | 20 | COLON_DRIVEN_DIVERGENCE | COLON_DRIVEN_DIVERGENCE | 5 | 5 |
| E_time_notation_short | 36 | IDENTICAL | IDENTICAL | 1 | 1 |
| F_ratio_notation_short | 36 | IDENTICAL | IDENTICAL | 1 | 1 |
| G_resolution_notation_short | 36 | IDENTICAL | IDENTICAL | 1 | 1 |
| H_long_cjk_width_driven_identical | 12 | IDENTICAL | IDENTICAL | 5 | 5 |
| H2_long_cjk_width_driven_diverges | 16 | WIDTH_MEASUREMENT_DIVERGENCE | WIDTH_MEASUREMENT_DIVERGENCE | 5 | 4 |
| I_whitespace_candidates | 20 | WIDTH_MEASUREMENT_DIVERGENCE | WIDTH_MEASUREMENT_DIVERGENCE | 2 | 3 |
| J_competing_boundary_candidates | 18 | WIDTH_MEASUREMENT_DIVERGENCE | WIDTH_MEASUREMENT_DIVERGENCE | 4 | 4 |
| K_multiple_paragraphs | 20 | IDENTICAL | IDENTICAL | 4 | 4 |
| L_last_resort_splitting | 5 | WIDTH_MEASUREMENT_DIVERGENCE | WIDTH_MEASUREMENT_DIVERGENCE | 10 | 11 |
| M_word_boundary_case | 16 | WORD_BOUNDARY_DIVERGENCE | WORD_BOUNDARY_DIVERGENCE | 5 | 5 |
| N_closing_delimiter_after_sentence_final | 20 | OTHER_UNCLASSIFIED | OTHER_UNCLASSIFIED | 3 | 3 |

Totals: **15/15 expected == actual** (no classifier drift since the
correction round). 7 IDENTICAL, 2 COLON_DRIVEN_DIVERGENCE, 4
WIDTH_MEASUREMENT_DIVERGENCE, 1 WORD_BOUNDARY_DIVERGENCE, 1
OTHER_UNCLASSIFIED.

**Note on corpus composition (relevant to Step 11):** 8 of 15 items are
already non-IDENTICAL. This corpus was authored to *exhibit* divergences
for classifier-correctness testing, not to represent a realistic
distribution of production slide text. The 7/15 IDENTICAL rate here must
not be read as "roughly half of real slides will diverge" — see §13.

---

## 6. Divergence Evidence Table

For every non-IDENTICAL item, the first divergent cut and the concrete
mechanism behind it:

| Item | First divergence | Production cut | Adapter cut | Mechanism | Category | New decision needed? |
|---|---|---|---|---|---|---|
| C | offset 8 vs 16 | after `。`-preceding CJK sentence, colon triggers immediate split | colon is `OTHER`-scored, not force-split; next cut chosen by width/score DP | production's `_SECONDARY_BREAK_CHARS` includes `：`; Phase 1–2C's clause taxonomy deliberately excludes colon (per adapter docstring "COLON HANDLING") | COLON_DRIVEN_DIVERGENCE | No — already investigated and accepted as expected in the adapter's own docstring |
| D | offset ~11 (`Conclusion:`) | colon forces split | colon not force-split | identical mechanism, ASCII colon | COLON_DRIVEN_DIVERGENCE | No |
| H2 | offset 16 vs 18 | production keeps a narrower cut nearer the sentence punctuation | adapter's DP finds a width-feasible, higher-total-score partition that packs one extra clause per line (`也談時程。還談` = one adapter segment vs. two production segments) | Phase 2D's global per-paragraph DP optimizes total score across the whole paragraph; production's packer is local/greedy | WIDTH_MEASUREMENT_DIVERGENCE | No — direct, verified consequence of the accepted DP-vs-greedy design difference (§8) |
| I | first cut position differs; adapter produces 3 segments vs. production's 2 | production's width measurement operates on normalized (whitespace-collapsed at display time) text | adapter's `_fits()` measures raw `source_text[start:end]`, so literal whitespace runs count fully toward the raw width, forcing an earlier/extra cut | Phase 2D's raw-vs-normalized width measurement, documented as "conservative" in `boundary_segmentation.py`'s own module docstring | WIDTH_MEASUREMENT_DIVERGENCE | No — matches the documented, accepted mechanism exactly; see §8 for whether "conservative" fully holds |
| J | differs at a boundary adjacent to a double-space run | same raw-width mechanism as I | same | same as I | WIDTH_MEASUREMENT_DIVERGENCE | No |
| L | `abcdefghij   klmnopqrst   uvwxyzabcdefghijklmnopqrstuv`, mw=5 — adapter produces 11 segments vs. production's 10 | last-resort width-forced splitting on both sides, but raw-width measurement of the spaced runs shifts the adapter's cut positions | same raw-width mechanism as I/J, exercised under `max_display_width=5` (an extreme, near-minimum value) | WIDTH_MEASUREMENT_DIVERGENCE | No |
| M | offset 26 vs 27, inside "周邊" | production's greedy packer happens to cut before "周" | adapter's DP, driven purely by width-feasibility and boundary score with no word-boundary evidence available to either system, cuts between "周" and "邊", splitting a real two-character CJK word | no jieba/word-segmentation awareness anywhere in Phase 1–2D | WORD_BOUNDARY_DIVERGENCE | No — explicitly accepted, documented gap; see §11 |
| N | offset 7 vs 8, at `？」` | cuts immediately after `？` (sentence-final punctuation itself) | cuts immediately after `」` (the closing quotation mark) | Phase 2A's terminal-ending-chain traversal is transparent through a closing paired delimiter, so the boundary just outside `」` scores `SENTENCE_FINAL` (80) exactly like the boundary just inside it (`？｜」`) — **independently confirmed as a known Phase 2C topology property, not a new finding of this adapter**: `PHASE_2C_CALIBRATION_ROUND2_REPORT.md` §5 Group X, case X06, describes exactly this mechanism ("terminal punctuation just inside a closing delimiter and the boundary just outside it can both independently classify SENTENCE_FINAL, producing two adjacent full-strength candidates for one semantic sentence end") | OTHER_UNCLASSIFIED | **Yes — see §6 (Step 6 special review) and §15** |

No item's classification in this table was reached by elimination; each
category assignment above cites the specific, checkable mechanism that
produced it, and for N specifically, an independent Phase 2C-era document
(not authored as part of the adapter or shadow-mode work) that predicted
this exact topology before the adapter existed.

---

## 7. Category-by-Category Review

Each category evaluated against: (A) is the mechanism technically sound,
(B) is it actually caused by the claimed mechanism, (C) is it acceptable
under the current design, (D) is it a production-quality problem, (E) does
it require a policy/design decision before cutover.

**IDENTICAL.** (A) N/A — no divergence. (B) N/A. (C) Yes. (D) No. (E) No.
7/15 corpus items, spanning short single-segment cases, multi-paragraph
text, and a width-driven case narrow enough to force multiple cuts
(H, mw=12) that still agree exactly with production. This demonstrates the
two systems are not *incidentally* different everywhere — under matching
conditions (no colon, no whitespace runs, width comfortably resolved) they
converge exactly, including on cut *count*, not just overall shape.

**COLON_DRIVEN_DIVERGENCE.** (A) Sound — traced to one concrete, textually
locatable cause (colon membership in production's `_SECONDARY_BREAK_CHARS`
vs. its absence from the Phase 1–2C clause-punctuation taxonomy). (B)
Confirmed on both a CJK colon (C) and an ASCII colon (D) case. (C)
Acceptable under the current design — this is explicitly the "approved v1
clause-punctuation taxonomy" per the adapter's own docstring, and is
already the single-most-documented divergence in this project's history
(surfaced originally during the Phase 2D Production Integration Design
round, §8, before the adapter was even built). (D) Not on its own a defect
— colon-triggered splits and non-splits are both defensible subtitle
segmentations; whether production's finer-grained colon splitting is
*preferred* is a stylistic/product question, not a correctness one. (E)
**Yes, but already flagged as a known, pre-existing open item, not new to
this review** — whether colon should be added to Phase 2D's evidence model
before cutover is a legitimate design question, but it is not raised for
the first time here.

**WIDTH_MEASUREMENT_DIVERGENCE.** (A) Sound — two distinct sub-mechanisms
are both represented in the corpus and both textually verifiable: (i) the
DP-vs-greedy global/local optimization difference (H2), and (ii)
raw-vs-normalized width measurement inflating raw width around whitespace
runs (I, J, L). (B) Confirmed per-item in §6. (C) Acceptable under the
current design for mechanism (i) — this is the intended, designed
consequence of choosing a global-optimum DP over a greedy local packer
(`PHASE_2D_SCOPE_AND_ARCHITECTURE.md` explicitly selects the DP approach).
Mechanism (ii) is also explicitly documented as an accepted trade-off
("conservative... which is safe... even though it is not byte-for-byte the
same measurement"), but see §10 for whether "safe" holds under every
observed condition. (D) Mechanism (i) — no; a globally-optimized packing
is arguably an improvement, not a regression. Mechanism (ii) — see §10,
partially open. (E) Mechanism (i) — no. Mechanism (ii) — **yes, flagged as
CUTOVER DECISION ITEM in §15**, because "conservative" is a directional
claim (never over-width) that has not been verified against extra-segment
count or display-shape cost.

**WORD_BOUNDARY_DIVERGENCE.** (A) Sound — the mechanism (no
word-segmentation evidence anywhere upstream of Phase 2D) is verifiable
directly from source (no jieba import in any Phase 1–2D production file).
(B) Confirmed on item M. (C) Explicitly accepted by design
(`PHASE_2D_SCOPE_AND_ARCHITECTURE.md` §11/§16, "known gap, not solved").
(D) Yes, in the narrow sense that a mid-word cut is a lower subtitle
*quality* outcome than production's (accidental, not principled) avoidance
of it in this one example — see §11. (E) **Yes — flagged as CUTOVER
DECISION ITEM in §15**, because unlike the colon divergence this one was
never previously evaluated for whether production's avoidance of it is
systematic or coincidental (see §11).

**OTHER_UNCLASSIFIED.** (A) Sound by construction — this category exists
specifically to avoid forcing evidence-less divergences into a
misleading label (per the correction round). (B) N/A — by definition, no
positive evidence for any of the other three categories was found in
item N's divergence window. (C) The classifier's behavior here (declining
to invent a label) is itself correct and was the entire point of the
correction round. Whether the underlying *divergence* is acceptable is a
separate question — see §8 below. (D) The underlying divergence (N) is a
different question from the classification mechanism; see §8. (E) **Yes —
this is exactly what OTHER_UNCLASSIFIED exists to surface for policy
review, and this review treats it as the central open item.**

---

## 8. Closing-Delimiter Review (Step 6 special review)

Subject: item N, `「這樣可以嗎？」大家都點頭表示同意，準備開始下一步工作。`
at `max_display_width=20`. Production cuts at offset 7, immediately after
`？`. The adapter cuts at offset 8, immediately after `」`.

**Why do the two systems differ?** Not from an implementation bug in
either the adapter or Phase 2D. The divergence originates in Phase 2A
(`boundary_observation.py`, frozen, unrelated to this adapter round): the
terminal-ending detection chain treats a closing paired delimiter (`」`,
here classified `paired_delimiter/quotation`, not a protected type) as
transparent when walking outward from sentence-final punctuation. This
means **both** the boundary immediately inside the delimiter (`？｜」`) and
the boundary immediately outside it (`」｜大`) are independently classified
`SENTENCE_FINAL` and both score 80 under the frozen Phase 2C model. This is
not speculation for this review — it is independently documented, in a
different document, from before this adapter existed:
`PHASE_2C_CALIBRATION_ROUND2_REPORT.md` §5 Group X, case X06 (`「真的？！」接下來...`),
which states plainly: "terminal punctuation just inside a closing delimiter
and the boundary just outside it can both independently classify
`SENTENCE_FINAL`, producing two adjacent full-strength candidates for one
semantic sentence end. Not itself an error under the current per-candidate
scoring model... but worth flagging for Phase 2D as a place where two
strong candidates sit one character apart." That flag was raised for
Phase 2D and, per this review's evidence, was never resolved — Phase 2D's
DP has no tie-breaking preference between two equal-score adjacent
candidates other than the width/squared-width objective, so which of the
two candidates wins is effectively incidental to which one yields a better
width-balance for the rest of the paragraph, not a deliberate choice about
delimiter placement.

**Is it deterministic and reproducible?** Yes — re-run in this round with
identical results to the correction round; confirmed by direct source
inspection of the Phase 2A terminal-chain transparency rule cited above,
not merely by observing the test's output.

**Is it legitimate under the current design?** Partially. It is legitimate
in the narrow sense that no component is misbehaving relative to its own
specification — Phase 2C scores each candidate correctly per its own
formula (as X06 itself concludes), and Phase 2D's DP correctly picks the
higher-total-score, width-feasible partition. But the *design* never made
an explicit decision about which of the two equal-score candidates should
be preferred when they are one character apart around a closing delimiter
— X06 flagged this as an open item for Phase 2D and no subsequent
Phase 2D document (`PHASE_2D_SCOPE_AND_ARCHITECTURE.md`,
`PHASE_2D_PRODUCTION_INTEGRATION_DESIGN.md`) records a decision resolving
it.

**Does accepting it change subtitle semantics?** Yes, in a small but
concrete way: production keeps the closing quotation mark attached to the
end of the quoted material's own line (`「這樣可以嗎？` / `」大家都點頭...`),
while the adapter keeps the full quotation, including its closer, on one
line (`「這樣可以嗎？」` / `大家都點頭...`). The adapter's placement is
arguably the more typographically conventional one (a closing quotation
mark is not normally stranded at the start of the next line), but this is
a legitimate readability/style judgment, not a mechanically forced
outcome, and no prior document endorses one placement over the other.

**Should it block cutover?** Not by itself, but it must be a named,
explicit decision before cutover, not an implicit byproduct. It is flagged
in §15 as a **CUTOVER DECISION REQUIRED** item — not a blocker, because
both placements are defensible and the mechanism is fully understood and
deterministic, but not silently acceptable either, because no design
document has actually decided this question. This review does not resolve
it and does not modify `boundary_observation.py`, `boundary_scoring.py`,
or `boundary_segmentation.py`.

---

## 9. Short-Input Review (Step 7 special review)

Subject: the adapter's documented behavior of returning `[]` for any input
whose total text is 0 or 1 characters, versus production's
`segment_notes_for_subtitles()` returning one segment for a lone character.

Root cause (confirmed by source inspection, not just the adapter's own
docstring): `boundary_observation.observe_boundaries()` enumerates exactly
one boundary candidate per integer position `1 <= position < len(source_text)`,
so any source text of length 0 or 1 produces zero candidates; Phase 2D's
`segment_boundaries()` returns `()` unconditionally whenever its
`weighted_boundaries` argument is empty (confirmed: this is a top-level
early-return in the frozen module, not adapter-added logic).

Classification: this is an **acceptable contract difference**, not a
correctness defect and not a cutover blocker, for three concrete reasons
distinct from "it's rare": (1) it is fully deterministic and pinned by a
dedicated regression test (`ShortInputContractTests` in
`test_boundary_segmentation_adapter.py`), so it cannot silently regress
further; (2) fixing it would require modifying the frozen
`boundary_segmentation.py`, which is out of scope for both this review and
the adapter round that discovered it; (3) the practical exposure is a
single slide whose *entire* narration text is one character — a case this
review has no evidence is a real occurrence in this project's actual slide
content (no slide-content sample was reviewed in this round to confirm or
refute frequency, so this is a bounded, not zero, uncertainty — see §13).
This review does not treat "we don't have evidence it happens" as proof it
never will; it records the gap as intentionally unresolved rather than
implicitly cleared. If a production cutover design is later drafted, this
contract difference must be explicitly listed as a pre-cutover fix-or-accept
item, not silently inherited.

---

## 10. Width Measurement Review (Step 8 special review)

Phase 2D's own module docstring characterizes its raw-vs-normalized width
measurement as "conservative... which is safe (never produces an
over-width final line)." This review tested whether "conservative" holds
uniformly across the observed evidence, and what its cost is where it does
hold.

**Does "never over-width" hold on the observed cases?** Yes, on every
corpus item examined (H2, I, J, L) — the adapter's segments are always at
or under `max_display_width` when measured by production's own
`_display_width()` on the *final, normalized* display text. This was
spot-checked by inspecting the printed segment text length for each
divergent item's adapter output in §5/§6 against the case's configured
`max_display_width`. No case in this corpus contradicts the "never
over-width" claim.

**What does "conservative" cost?** Concretely, on the whitespace-run cases
(I, J, L), the adapter produces **one more segment than production**
in every single instance (I: 3 vs 2; J: 4 vs 4 — tie on count but
divergent boundary; L: 11 vs 10). This is not "no visible cost" — extra
segments mean an extra subtitle line is shown for the same narration
audio, with direct downstream consequences for `subtitle_alignment.py`'s
timing allocation (more, shorter-duration segments to place across the
same audio span) even though this review did not execute the alignment
module to quantify that consequence. On J specifically, both systems
happen to produce 4 segments, but at a different boundary — showing the
raw-width effect does not *always* manifest as a segment-count increase,
sometimes only as a boundary-position shift.

**Does "conservative" ever produce an unnecessarily narrow/awkward cut
relative to what the normalized width would have permitted?** Yes — this
is exactly the mechanism behind I/J/L: a literal multi-space run inflates
the *raw* width measurement above `max_display_width` at a point that,
after normalization (whitespace collapsing at display time in
production's `_display_text_for_span`/packer), would not actually have
exceeded the limit. The adapter is safe in the sense of never showing
over-width text, but not free of the "unnecessary extra segment / awkward
cut" cost the design doc's own framing ("can cut more eagerly than
necessary") already anticipated.

**Conclusion:** the "conservative, therefore safe" characterization is
accurate as a *width ceiling* guarantee (confirmed, no counterexample in
this corpus) but should not be read as cost-free. This is not a new
defect discovered by this review — the adapter's own docstring already
uses the phrase "can cut more eagerly than necessary" — but this review
is the first place the concrete, measured cost (consistently one extra
segment on multi-space-run text) has been quantified against real corpus
runs rather than described qualitatively. Flagged in §15 as a CUTOVER
DECISION ITEM: whether this extra-segment cost is acceptable, or whether
the adapter should eventually measure normalized width, is a design
decision for the (not-yet-started) cutover step, not resolved here.

---

## 11. Word-Boundary Review (Step 9 special review)

Subject: item M, where the adapter cuts inside "周邊" ("周" | "邊").

**Why can Phase 2D cut inside a CJK word?** Neither Phase 1 nor any
upstream phase provides word-segmentation evidence of any kind (confirmed
by source: no `jieba` or other CJK-tokenization import anywhere in
`text_structure.py`, `boundary_observation.py`, `boundary_classification.py`,
`boundary_scoring.py`, or `boundary_segmentation.py`). Every unpunctuated
CJK-CJK boundary scores identically (`BoundaryClass.OTHER`, base 0, no
positive evidence, since CJK→CJK is not a language-transition pair) —
Phase 2D's DP therefore has no signal at all to prefer a word-respecting
cut over a word-splitting one; the only thing it optimizes across such
positions is width-balance (lowest sum-of-squared-widths).

**Is this explicitly accepted by design?** Yes —
`PHASE_2D_SCOPE_AND_ARCHITECTURE.md` §11/§16 records this as a "known gap,
not solved," and the adapter's own docstring repeats the same framing
verbatim ("a long, unpunctuated CJK run with no character-class transition
anywhere in it will be cut based on width alone... This is a known,
accepted limitation... not an oversight").

**Is production's behavior materially better, or only accidentally
different?** This review finds it is **accidental, not systematic** —
production's packer has no word-boundary awareness either (confirmed: no
jieba/tokenization import in `subtitle_segmenter.py`). Production avoided
splitting "周邊" in this specific example only because its local greedy
width-packing happened to land its cut point one character earlier for
reasons unrelated to word identity. This is a materially different
finding from "production handles this correctly" — **neither system
respects CJK word boundaries**; the divergence merely means the two
systems' independent, word-blind algorithms happened to choose different
split points, and in this one example production's choice happened not to
bisect a word while the adapter's did. This is worth stating plainly
because "accept as known limitation" could otherwise be misread as
"accept that we are worse than production here" — the more accurate
framing is "this specific example demonstrates a shared blind spot that
happens to manifest more often, less often, or differently under either
algorithm, not a case where production is designed to avoid it and Phase 2D
is not."

**Classification:** known limitation, not a blocker, but the "shared blind
spot, not solved-by-production" framing was not previously stated this
directly in prior rounds and should be part of the cutover record — this
review does not add jieba to Phase 2D and does not modify any file, per
the task's explicit instruction.

---

## 12. D04 Review (Step 10 special review)

Subject: whether D04 (the CJK↔LATIN transition-vs-whitespace ranking
property) remains resolved genuinely generically by Phase 2D's DP, with no
hidden special-case code.

Re-confirmed by direct source inspection in this round: `boundary_segmentation.py`
contains no CJK/LATIN-specific branching, no whitespace-specific branching,
and no reference to `CharacterClass`, transitions, or any Phase 2C
evidence type by name anywhere in its ~370 lines — its entire logic
surface is paragraph splitting, width-feasibility (`_fits`/`_display_width`
on raw slices), greedy minimum-K estimation, and a generic score-maximizing
DP over candidate positions and their already-computed scores. D04 (a
Phase 2C-layer candidate-topology fact: inserting whitespace replaces the
15-scoring transition candidate with a 10-scoring whitespace candidate at
a nearby position, rather than modifying one candidate's score) is
resolved purely as a byproduct of Phase 2D consuming whichever candidates
and scores Phase 2C happens to hand it, with no D04-aware code path. This
matches `PHASE_2C_OVERALL_NUMERIC_RECONCILIATION.md` §8's own conclusion
and `PHASE_2D_SCOPE_AND_ARCHITECTURE.md` §8's design intent exactly.

No file was modified to perform this check. **Classification: confirmed
sound, no action needed.**

---

## 13. Hidden Divergence Review (Step 11 special review)

Searching for divergence mechanisms not represented in the current
15-item corpus but plausible on real slide content:

1. **Corpus is divergence-weighted, not representative of a real slide
   population.** 7/15 (47%) of this corpus diverges from production. This
   corpus was deliberately constructed to exercise each classifier
   category, not sampled from real slide notes. No claim in this review or
   any prior round establishes what fraction of *actual* project slide
   content would diverge — this is a genuine, currently unfilled evidence
   gap, reported here as **NEW / UNCLASSIFIED DIVERGENCE RISK** in the
   sense that its shape and frequency on real content is simply unknown,
   not that any specific new mechanism was found.
2. **Mid-word CJK splits away from any punctuation** (§11's mechanism)
   could occur anywhere in a long unpunctuated CJK run, not just at the
   one location item M exercises. The corpus contains exactly one such
   case; real slide narration with long unpunctuated technical
   explanations could exercise this far more often than the 1/15 rate
   here suggests. No new category is warranted — this is the same
   WORD_BOUNDARY_DIVERGENCE mechanism, just potentially under-sampled.
3. **The closing-delimiter mechanism (§8) is not limited to `？」` /
   `！」`.** The same terminal-chain transparency applies to any
   sentence-final punctuation immediately followed by any closing paired
   delimiter Phase 2A recognizes as `paired_delimiter` (e.g. `。」`,
   `」`, `』`, `）` after terminal punctuation, or `"`/`'`/`)` in
   Latin-script material) — X06 in the Phase 2C calibration report used
   `？！」` specifically, and this review's own item N uses `？」`; no
   corpus item exercises `。」` or a Latin closing-parenthesis variant.
   This is the same OTHER_UNCLASSIFIED mechanism as N, not a new one, but
   its surface area (which specific delimiter/punctuation pairs trigger
   it) is broader than the single pinned example demonstrates.
4. **No hidden divergence mechanism distinct from the four already-named
   categories (colon, width-measurement, word-boundary, closing-delimiter)
   was found.** This review specifically checked for: nested/nested-mixed
   punctuation sequences, numeric-literal edge cases (16:9-style patterns
   — confirmed by the adapter's own docstring item 4 to route through the
   already-known COLON_DRIVEN_DIVERGENCE category, not a hidden one), and
   nested nested nested-paragraph structures (K's multi-paragraph case
   remains IDENTICAL, giving no evidence of a paragraph-splitting
   divergence). None of these produced evidence of a fifth, unnamed
   mechanism in this round's inspection.

No new classifier category is proposed. No classifier code was modified.
These findings are reported as scope/coverage gaps in the *evidence base*,
not as newly discovered bugs.

---

## 14. Cutover Classification (Step 12)

Every known divergence mechanism, classified into exactly one bucket:

| Divergence mechanism | Classification |
|---|---|
| COLON_DRIVEN_DIVERGENCE (colon not force-split by Phase 1–2C taxonomy) | **A. ACCEPTED** — investigated and documented before this adapter existed; both behaviors are defensible; no correctness defect |
| WIDTH_MEASUREMENT_DIVERGENCE, mechanism (i): global DP vs. local greedy packing | **A. ACCEPTED** — the intended, designed consequence of choosing a global-optimum model |
| WIDTH_MEASUREMENT_DIVERGENCE, mechanism (ii): raw vs. normalized width measurement on whitespace runs | **C. CUTOVER DECISION REQUIRED** — width-ceiling-safe but measurably produces extra segments; whether that cost is acceptable is undecided (§10) |
| WORD_BOUNDARY_DIVERGENCE (no jieba awareness in either system) | **B. KNOWN LIMITATION** — explicitly accepted by design in `PHASE_2D_SCOPE_AND_ARCHITECTURE.md`; both systems share the blind spot |
| Closing-delimiter OTHER_UNCLASSIFIED (`SENTENCE_FINAL` tie inside/outside a closing paired delimiter) | **C. CUTOVER DECISION REQUIRED** — deterministic, understood, semantically small but real; no prior document actually decided which placement is preferred (§8) |
| 0–1 character short-input contract difference (adapter returns `[]`, production returns one segment) | **B. KNOWN LIMITATION** — pinned by regression test, narrow exposure, real occurrence rate on actual slide content unverified (§9) |
| Corpus representativeness gap (§13 item 1) | Not a divergence mechanism itself — an **evidence gap**, listed separately in §16, not classified A–D |
| Closing-delimiter surface-area breadth beyond `？」`/`！」` (§13 item 3) | Same underlying mechanism as the closing-delimiter item above — **C. CUTOVER DECISION REQUIRED**, inherits that item's classification, not a separate bucket |

No item in this table was assigned by elimination or by a subjective
severity judgment — each classification cites the specific finding in §6–§13
that supports it.

**No item is classified D. BLOCKER.** Nothing found in this review
represents non-deterministic behavior, an outright incorrect segmentation
(offsets outside source bounds, corrupted text, crash, or similar), or a
divergence whose mechanism is not understood.

---

## 15. Cutover Blockers

**None identified.** No BLOCKER-classified item exists per §14. This is a
direct finding, not an assumption — every divergence mechanism examined in
this review traces to an understood, deterministic, previously-documented-
or-newly-explained cause.

This does **not** mean cutover is ready to design without further work —
see §16 for the required decisions and §13 for the evidence gap that must
be closed first.

---

## 16. Required Decisions

Before a cutover *design* (Step 2 of the migration plan) can be
responsibly started, the following must be explicitly decided or
investigated — none of them are resolved by this review, and this review
does not propose specific resolutions, only names them:

1. **Colon handling** — should Phase 1–2C's clause taxonomy be extended to
   treat colon as clause-eligible, matching production's
   `_SECONDARY_BREAK_CHARS`? (Pre-existing open item, not new to this
   review.)
2. **Raw vs. normalized width measurement** — should Phase 2D measure
   width against the normalized/stripped display text instead of the raw
   source slice, to eliminate the extra-segment cost quantified in §10?
   Or is the current "safe ceiling, occasional extra segment" trade-off
   acceptable?
3. **Closing-delimiter placement** — when a closing paired delimiter
   immediately follows sentence-final punctuation, should the cut land
   immediately after the punctuation (production's current behavior) or
   immediately after the delimiter (Phase 2D's current behavior, and the
   more typographically conventional one)? This decision was flagged as
   open in `PHASE_2C_CALIBRATION_ROUND2_REPORT.md` (X06) before this
   adapter existed and has never been resolved.
4. **0–1 character input contract** — should the adapter/Phase 2D chain be
   changed (in a future round, not this one) to match production's
   one-segment behavior for extremely short input, or is `[]` acceptable
   given the narrow, currently-unverified real-world exposure?
5. **Corpus representativeness** — before treating shadow-mode results as
   predictive of production impact, a sample of real project slide notes
   (not hand-authored corpus text) should be run through both systems to
   establish an actual divergence rate and mechanism-frequency
   distribution. The current 15-item corpus was built to exercise
   categories, not to estimate real-world impact, and should not be
   substituted for that evidence.

---

## 17. Production Cutover Readiness

Per the evidence gathered in this review:

- Adapter, Phase 2D, and shadow-mode classifier all remain byte-for-byte
  unchanged from their previously accepted state (§2).
- Every currently known divergence mechanism is deterministic, understood,
  and traced to a specific, cited cause — none is unexplained (§6–§13).
- No BLOCKER-classified item exists (§14–§15).
- However, three CUTOVER DECISION REQUIRED items remain genuinely
  undecided (§16 items 2, 3, and implicitly 1), and one material evidence
  gap (real-slide-content divergence rate, §16 item 5) has not been
  closed — shadow-mode testing to date has validated the *classifier* and
  the *mechanisms*, not the *real-world impact* of shipping Phase 2D to
  production slide content.

---

## 18. Final Recommendation

**NOT READY — ADDITIONAL INVESTIGATION REQUIRED**

This is not a design-change recommendation: no evidence in this review
indicates the accepted Option B architecture, the frozen Phase 2D DP
model, or the adapter's integration approach is structurally wrong. It is
also not a "ready to design cutover" recommendation, because §16's five
items — three genuine, currently-undecided product/design questions (colon
handling, width measurement mode, closing-delimiter placement) and one
material evidence gap (real-slide-content divergence rate) — have not been
addressed. Designing a gated cutover (Step 2) before these are resolved
risks encoding an unreviewed default for each open question rather than a
deliberate one.

**Recommended next action (not started by this review, not implemented
here):** run the existing shadow-mode harness (unmodified) against a
sample of real project slide notes text to close the representativeness
gap (§16 item 5), and bring §16 items 1–4 to whoever owns product/UX
decisions for this project for an explicit ruling. Once those are
resolved, a Step 2 cutover design (feature-flagged, defaulted off, per the
already-accepted Option B plan) can be responsibly started.

This review does not begin that design work.
