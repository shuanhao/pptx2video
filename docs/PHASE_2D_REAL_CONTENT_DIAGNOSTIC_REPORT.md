# Phase 2D Real-Content Diagnostic Report

Status of this document: a **diagnostic / architecture-validation** artifact.
It modifies no production code, no Phase 2D implementation, no adapter, and
no existing test. It creates no new heuristic and performs no production
cutover. Every claim below is labeled **FACT** (directly observed from
source code or from re-running the real pipeline against the real corpus
in this round), **INFERENCE** (a reasoned conclusion the observed facts
support), or **HYPOTHESIS** (a plausible but unproven explanation). Where
the evidence is insufficient to settle a question, that is stated
explicitly rather than resolved by assumption.

---

## 1. Executive Summary

**FACT.** The 39-file real corpus (`examples/notes/`, 21 `mcu1` slides + 18
`mcu2` slides, 87,774 characters, `max_display_width=18`) was re-run in
this sandbox against the exact same production/adapter functions the
user's local evaluation used. The result reproduces the user's numbers
exactly: 0/39 identical, 39/39 divergent, production 10,372 segments,
Phase 2D 9,985 segments, delta −387 (36 files fewer, 3 files more, 0 equal-
count-different-boundary). This match, byte-for-byte down to every segment
offset across all 39 files, confirms the uploaded corpus is the authentic
input behind the provided `real_content_shadow_results.json` and rules out
any transcription or environment discrepancy between the two evaluations.

**FACT, established this round via direct introspection of the frozen
`boundary_segmentation.py` source (not previously demonstrated at scale):**
the user's Section 6 hypothesis — that Phase 2D's fixed-`K` architecture
structurally prevents some positive-scored Phase 2C boundaries from ever
being selectable, regardless of score — is **not merely plausible, it is
demonstrated**. Across all 39 files, 3,070 interior cut positions exist
where production placed a cut that the adapter did not, and where a real,
positive-scored `WeightedBoundary` candidate sits at that exact position.
Of those 3,070, **1,847 (60.2%) are provably excluded by the fixed-`K`
constraint** — no `K`-segment partition of that paragraph can include that
position, regardless of its score, because forcing it would require more
than the paragraph's own computed minimum feasible segment count. The
remaining 1,223 (39.8%) are `K`-feasible but were simply outscored/not
selected by the DP's optimization — a different, non-architectural
explanation.

**FACT.** A second, independently significant mechanism was found and
quantified that is not one of the four previously-named shadow-mode
categories: Phase 2D measures width against the **raw** source span
(including not-yet-stripped trailing punctuation), while production
measures width against the **already-stripped, normalized** display text.
This is the same "raw vs. normalized width" limitation already documented
in the adapter's own docstring, but on this real corpus its dominant
manifestation is **not** whitespace runs (there are zero multi-space runs
anywhere in the entire 87,774-character corpus) but **trailing
punctuation inflating the raw width by one full-width unit at almost
every sentence-final position**. 208 of the corpus's 4,128 paragraphs
(5.0%) have a raw width that exceeds 18 while their stripped/normalized
width would fit — meaning production can keep them as one line and
Phase 2D structurally cannot. This mechanism pushes toward Phase 2D
needing **more** segments, the opposite direction from the net −387,
confirming that no single mechanism explains the aggregate number; several
distinct, independently-real mechanisms pull in different directions and
the net −387 is their combined, non-additive result.

**INFERENCE**, supported directly by source-code inspection (§7): the
current Phase 2D architecture computes the target segment count `K`
purely from width feasibility, **before** any Phase 2C score is consulted,
and then runs a score-maximizing DP constrained to produce exactly that
many segments. This means Phase 2C's scores can only ever influence
*which* positions are chosen among a fixed number of cuts — they can never
influence *how many* cuts there should be. This is a structural,
demonstrable property of the current design, not a bug in any one
function.

This report does not conclude Phase 2D is "wrong." It concludes the
current fixed-`K` architecture is **structurally inadequate to let
Phase 2C's boundary-strength signal express itself in the one place that
signal ought to matter most — the number of subtitle lines produced** —
and that a design-level reconsideration of the `K`-selection step is
warranted before any further implementation or cutover work proceeds. No
implementation change is made here.

---

## 2. Real-Content Corpus and Methodology

**FACT.** Corpus: `examples/notes/*.txt`, 39 files, uploaded by the user
this round and confirmed identical to the source behind the previously
supplied results (verification below). Two presentations: `mcu1` (21
slides) and `mcu2` (18 slides). Total characters: 87,774 (recomputed in
this sandbox, matches the user's summary exactly).

**FACT — corpus integrity verification.** Every one of the 39 uploaded
files was run through the exact same call shape as the user's
`scripts/evaluate_phase2d_real_content.py` (`segment_notes_for_subtitles(text, max_display_width=18)`
and `segment_notes_for_subtitles_via_boundary_engine(text, max_display_width=18)`,
both unmodified, no transformation of the input text) and diffed
programmatically against every field of the provided
`real_content_shadow_results.json`. Result: **0 mismatches across all 39
files** — every production segment, every adapter segment, every offset,
and every character count matches exactly. The uploaded files are
confirmed to be the authentic original corpus, not a reconstruction.

**FACT.** No project file was modified to perform this round's analysis.
All diagnostic code (score-distribution extraction, fixed-`K` feasibility
probes, mechanism tagging) was written as ad hoc, throwaway Python run
directly against the unmodified `src/` modules via their existing public
and module-private functions (the latter accessed by direct import, the
same technique the adapter itself already uses for
`_display_text_for_span`/`_strip_trailing_punctuation`). None of this
diagnostic code was added to the repository; it exists only in this
session's scratch space, exactly as the user's own reference script was
described as "not a project file."

**FACT — functions called for this analysis, all pre-existing and
unmodified:** `src.boundary_segmentation_adapter._weighted_boundaries_for_text`
(runs the real Phase 1→2A→2B→2C chain), `src.boundary_segmentation._split_paragraphs`,
`_internal_positions`, `_greedy_min_k_boundaries`, `_fits`, `_display_width`
(Phase 2D's own internal helpers, called directly for introspection —
never edited), `src.subtitle_segmenter._display_text_for_span`,
`_strip_trailing_punctuation`, `_display_width` (production's own
internal helpers), and `tests.test_shadow_mode_comparison`'s existing
constants (`_COLON_CHARS`, `_TRAILING_STRIP_CHARS`, `_WHITESPACE_RUN_RE`)
imported for consistent mechanism-tagging vocabulary with the prior
review round — none of these were modified.

**FACT — baseline verification.** All twelve files from the prior two
review rounds' baseline table were re-checksummed after this round's work
and are unchanged from their previously accepted values (identical to the
values reported in `PHASE_2D_SHADOW_DIVERGENCE_REVIEW.md` §2 and
`PHASE_2D_REAL_CONTENT_SHADOW_EVALUATION.md` §5). Full suite:
**531 passed, 30 subtests** (unchanged). Shadow suite: **17 passed, 15
subtests** (unchanged). This repository has no `.git` directory (confirmed
again); checksums and a recent-file-modification-time scan are used in
place of a git diff. Only one file in the repository has a modification
time within this round's working window: this document.

---

## 3. Overall Results

**FACT**, reproduced exactly from the corpus:

| Metric | Value |
|---|---:|
| Total files | 39 |
| Identical | 0 (0%) |
| Divergent | 39 (100%) |
| Total production segments | 10,372 |
| Total Phase 2D segments | 9,985 |
| Total segment delta | −387 |
| Files where Phase 2D has fewer segments | 36 |
| Files where Phase 2D has more segments | 3 |
| Files with equal count, different boundaries | 0 |
| Minimum per-file delta | −30 |
| Maximum per-file delta | +8 |
| Total Phase 2C candidates across corpus | 87,735 |
| Total paragraphs across corpus | 4,128 |

**FACT.** The shape of each file's *first* divergence, re-derived directly
from the real corpus (not merely the JSON): **37 of 39 files' first
divergence shares one structural pattern** — production's and the
adapter's diverging segment start at the identical offset but end at
different offsets. Only 2 files (`mcu2_slide_03`, `mcu2_slide_11`) diverge
with a shifted *start* instead of end, and in both of those the resulting
*display text is byte-identical* between the two systems (`'是什麼」'`,
`'Flash 與 SRAM'`) — the offset shift lands on a bare space character
(`「MCU␣是什麼」`, `了␣Flash`) that normalizes away in the final display text
either way. These two files' "first divergence" is cosmetic, not a
content difference.

---

## 4. Divergence Taxonomy

**FACT.** The four previously-named shadow-mode categories
(colon, width-measurement, word-boundary, closing-delimiter) do not, by
themselves, explain the shape of divergence on this real corpus, because
this corpus does not exercise them in the same proportions the earlier
synthetic and small-sample corpora did. A direct, corpus-wide mechanism
sweep (not limited to each file's *first* divergence — every interior
cut-position disagreement in every file) found:

| Mechanism | Status on this corpus | Evidence |
|---|---|---|
| Colon-driven divergence | **Present, minor** | 176 colon characters total; 155 cut identically by both systems, 20 cut by production only, 1 cut by neither, 0 cut by adapter only |
| Whitespace-*run* width inflation (the mechanism named in the prior synthetic-corpus review) | **Absent** | 0 occurrences of any 2+ character whitespace run anywhere in 87,774 characters |
| Trailing-*punctuation* width inflation (a distinct sub-mechanism of "raw vs. normalized width," newly isolated and quantified this round) | **Present, systematic** | 208 of 4,128 paragraphs (5.0%) have raw width > 18 but stripped/normalized width ≤ 18 |
| CJK word-boundary splits (no jieba awareness) | **Present, substantial** | 1,369 of 3,151 adapter-only cut positions (43.4%) confirmed via `jieba.cut()` to split a real token |
| Fixed-`K` candidate exclusion (the user's Section 6 hypothesis) | **Present, dominant** | 1,847 of 3,070 meaningful production-only bypassed positions (60.2%) are provably `K`-infeasible |
| `K`-feasible but outscored (a distinct, non-architectural sub-cause) | **Present** | The remaining 1,223 of 3,070 (39.8%) |
| Closing-paired-delimiter `SENTENCE_FINAL` duplication (§8 of the prior shadow review) | **Not specifically searched this round** | Out of scope for this quantitative pass; not the dominant pattern observed in the taxonomy above |

**INFERENCE.** The dominant story on real content is different from the
dominant story the earlier, smaller/synthetic corpora suggested. There,
whitespace-run inflation was the concrete example of "raw vs. normalized
width." Here, that specific sub-mechanism does not occur at all, but a
different, more pervasive sub-mechanism of the same underlying limitation
(raw vs. normalized width measurement) — trailing punctuation — affects
5% of all paragraphs. Separately and more consequentially, the majority of
meaningful divergence traces not to width measurement at all but to the
fixed-`K` DP's candidate-selection behavior.

---

## 5. Quantitative Cause Analysis

**FACT.** Across all 39 files, the complete set of interior cut positions
was computed for both systems and compared (not just each file's first
divergence):

- Production-only cut positions (production cut here, adapter did not):
  **4,753**
- Adapter-only cut positions (adapter cut here, production did not):
  **3,151**
- Of the 4,753 production-only positions, **3,070 (64.6%)** coincide with
  a real Phase 2C candidate carrying a **positive** score — i.e., a
  "meaningful" bypassed boundary, not merely a zero-score position
  production happened to cut at for its own reasons (e.g., production's
  own last-resort width-forced splitting, or the 20 zero-scored colon
  positions from §4). The remaining 1,683 (35.4%) are positions with no
  positive Phase 2C evidence at all — not part of the fixed-K
  investigation below, since a zero-or-negative-scored position was never
  going to be selected by a score-maximizing DP regardless of `K`.

**FACT — mechanism-tagging of the 3,070 meaningful bypassed positions**
(every position accounted for, no unexplained residue):

| Tag | Count | % of 3,070 |
|---|---:|---:|
| Single-space-adjacent only (e.g. a boundary next to `MCU`/`CPU`/`SoC`-style bare acronym spacing) | 1,706 | 55.6% |
| Trailing-punctuation-adjacent only (comma/period/etc.) | 1,356 | 44.2% |
| Both | 8 | 0.3% |
| Neither | 0 | 0% |

**FACT — score-value breakdown of the 3,070:** every one of them scores
either exactly 35.0 (`CLAUSE`, 1,337 positions) or exactly 10.0
(`BoundaryClass.OTHER` with a whitespace-adjacency bonus, 1,706
positions), plus 27 genuine `SENTENCE_FINAL` positions (80.0 or 90.0).
There is no case among these 3,070 where production bypassed a
Phase 2C candidate scoring anything other than one of these known,
documented values — no unexplained score value appears.

---

## 6. Fixed-K Constraint Analysis

**FACT, directly quoted from `src/boundary_segmentation.py`
(`_select_cut_positions`, unmodified, lines ~241–246):**

```python
anchors = [p_start] + list(positions) + [p_end]
greedy_boundaries = _greedy_min_k_boundaries(anchors, source_text, max_width)
target_k = len(greedy_boundaries) - 1
if target_k <= 1:
    return greedy_boundaries
```

`_greedy_min_k_boundaries` (also quoted, unmodified) computes its result
purely from `anchors` and `max_width` via `_fits()`, a pure width check —
it never receives or references `score_map` or any `WeightedBoundary`.
`target_k` is therefore fixed **before** the score-maximizing DP that
follows ever runs, and that DP (`dp[i][k]` for `k` in `1..target_k`,
same function, lines ~273–298) is combinatorially constrained to produce
**exactly** `target_k` segments — never fewer, never more.

**FACT, method:** for a production-only, positive-scored candidate
position `p` inside paragraph `[p_start, p_end]`, define `forced_k` as
the sum of the paragraph's own minimum feasible segment count for
`[p_start, p]` plus `[p, p_end]` — i.e., the minimum number of segments
needed if a cut at `p` is mandatory — computed by calling
`_greedy_min_k_boundaries` (unmodified) on each half independently. If
`forced_k > target_k` (the paragraph's actual, unconstrained minimum),
then **no** `target_k`-segment partition of that paragraph can include
`p` as a cut point, regardless of its score. This is a direct, mechanical
consequence of `_select_cut_positions`'s DP being restricted to exactly
`target_k` segments, not an approximation or a heuristic added by this
analysis.

**FACT, result:** applying this test to all 3,070 meaningful production-
only positions:

| | Count | % |
|---|---:|---:|
| Structurally excluded by fixed-`K` (`forced_k > target_k`) | 1,847 | 60.2% |
| `K`-feasible, but not selected by score-maximization | 1,223 | 39.8% |

Within the excluded 1,847: 1,088 are `CLAUSE` (score 35.0), 734 are
whitespace-adjacent `OTHER` (10.0), 25 are `SENTENCE_FINAL` (80.0/90.0).

**FACT — concrete, fully reproduced worked example.**
`mcu1_slide_02.txt`, paragraph `[7, 57]`:
`'各位同仁，歡迎來到 MCU Fundamentals Training Program 第一週課程。'`
(this is the single largest per-file delta in the corpus, −29 segments).
Position 12 (immediately after `，`) carries a genuine
`BoundaryClass.CLAUSE`, score 35.0 candidate — this is production's
actual, real cut point (`{'text': '各位同仁', ..., 'source_end_offset': 12}`).
The paragraph's own unconstrained minimum feasible segment count,
computed via `_greedy_min_k_boundaries` on the full paragraph, is
**`target_k = 4`**. Forcing a cut at position 12 requires
`forced_k = left_k(1) + right_k(4) = 5` — one more than the paragraph
actually needs. Since `5 > 4`, position 12 is **provably, structurally
excluded** from every possible 4-segment partition of this paragraph,
independent of its 35.0 score. The adapter's actual output instead cuts
at position 16 (`各位同仁，歡迎來到` as one segment) — a whitespace-adjacent
`OTHER`, score 10.0 position, *lower*-scoring than the excluded
candidate, selected only because it is one of the finitely many positions
that *is* compatible with a 4-segment partition.

**FACT — a second worked example distinguishing the "K-feasible but
outscored" case from structural exclusion**, so the two are not
conflated: `mcu1_slide_01.txt`, paragraph containing `'...Unit，微控制器的基礎知識，並了解它在現代電子產品與 Embedded System...'`.
Position 90 (immediately after `，`) is a genuine `CLAUSE`, score 35.0
candidate — production's actual cut
(`{'text': '微控制器的基礎知識', ..., 'source_end_offset': 90}'`). Here,
`forced_k = target_k = 10` — **including position 90 would not require
any additional segment**. The adapter's DP nonetheless chose a different
10-segment partition, cutting instead at position 87 (a plain, unscored
`OTHER` boundary mid-word: `'微控制器的基礎'` / `'知識，並了解它在'`). This is
not a structural exclusion; it is a case where a *different* 10-segment
combination achieved an equal-or-higher total score (or won the
sum-of-squared-widths tie-break), and the DP's global optimization simply
did not happen to include position 90 in its winning combination — a
genuinely different, non-architectural cause from the 1,847 excluded
cases above.

**Answer to the user's item B/3 ("is the fixed-K constraint actually
preventing positive-score boundaries from being selected?"):** **Yes,
confirmed as FACT for 60.2% of the meaningful, quantified sample** (1,847
of 3,070 positions), with two fully worked, source-cited, reproducible
examples above. The remaining 39.8% is a separate, also-real phenomenon
(pure score/tie-break optimization choosing a different combination) that
should not be attributed to the fixed-`K` architecture specifically.

---

## 7. Phase 2C Score Utilization Analysis

**FACT — score distribution across the entire real corpus** (87,735
candidates, one per integer position `1 ≤ pos < len(text)` per file,
summed across all 39 files):

| | Count | % |
|---|---:|---:|
| Positive score | 21,085 | 24.03% |
| Zero score | 66,602 | 75.91% |
| Negative score | 48 | 0.05% |

By `BoundaryClass`: `OTHER` 80,614 (91.9%), `SENTENCE_FINAL` 3,984 (4.5%),
`CLAUSE` 3,135 (3.6%), `ELLIPSIS` 2 (~0%).

Score-value histogram (every distinct value observed, with count):
`0.0`→66,602; `10.0`→13,960 (whitespace-adjacent `OTHER`); `90.0`→3,948
(`SENTENCE_FINAL` + whitespace bonus); `35.0`→3,135 (`CLAUSE`); `−30.0`→46
(Technical/Atomic-protected); `80.0`→36 (bare `SENTENCE_FINAL`, no
whitespace bonus); `15.0`→4 (CJK↔LATIN transition); `−20.0`→2 (`INTERNAL`
punctuation sequence); `75.0`→2 (`ELLIPSIS` + whitespace).

**FACT** — a specific, corpus-driven observation not previously reported
in any prior round: **3,948 of the corpus's 3,984 `SENTENCE_FINAL`
candidates (99.1%) score 90.0, not the documented 80.0 baseline**, because
this course-narration corpus is formatted with (largely) one sentence per
line/paragraph, so a `SENTENCE_FINAL` position is very often immediately
followed by `\n` — classified `WHITESPACE` by the frozen Phase 1–2C
pipeline exactly as previously documented (`PHASE_2C_CALIBRATION_ROUND2_REPORT.md`,
Group D/B01) — adding the +10 whitespace bonus. This is not a defect; it
is the already-known, already-accepted whitespace-modifier behavior,
simply now observed at scale on real, naturally-line-broken content for
the first time.

**INFERENCE, directly answering the user's item D.** The Phase 2C scoring
model *does* contain information the current Phase 2D objective fails to
fully use: 24% of all real candidates carry positive evidence, and among
the subset production actually chose to cut at but the adapter did not
(the 3,070-position set), every single one traces to a known, principled
positive-evidence category (`CLAUSE`=35, whitespace-`OTHER`=10, or
`SENTENCE_FINAL`=80/90) — none is spurious or unexplained. The scores are
real, structured, and locally meaningful; what §6 demonstrates is that the
current architecture prevents 60.2% of the ones that matter most for
these divergences from ever being reachable at all, independent of their
magnitude, because `K` is fixed before scores are consulted.

**Not addressed here (explicitly out of scope, per the task's "do not
invent thresholds" instruction):** whether a *specific* score value (e.g.,
35.0) is "high enough to justify an extra segment" is a policy/design
judgment, not a fact this diagnostic can establish. This report reports
what score information exists and how it is structurally used, not what
threshold would be correct.

---

## 8. Width Constraint Analysis

**FACT, answering the user's item 4/E directly: is width measurement the
primary cause of the −387 delta?** No — and the evidence separates cleanly
into two sub-mechanisms with **opposite** net directions:

1. **Whitespace-run inflation** (the mechanism most concretely
   demonstrated in the prior synthetic-corpus review): **zero occurrences**
   anywhere in this 87,774-character real corpus (confirmed by direct
   regex scan for any 2+ consecutive space/tab character run). This
   sub-mechanism contributes **nothing** to the −387 delta on this corpus.
2. **Trailing-punctuation inflation** (a distinct sub-mechanism of the
   same documented "raw vs. normalized width" limitation, isolated and
   quantified for the first time this round): **208 of 4,128 paragraphs
   (5.0%)** have `_display_width(raw_span) > 18` while
   `_display_width(strip_trailing_punctuation(display_text_for_span(span))) ≤ 18`
   — meaning production's own width check (which measures the final,
   stripped display text, confirmed by direct inspection of
   `src/subtitle_segmenter.py` lines 155–156 and 317–318) allows the
   paragraph to fit as one line, while Phase 2D's `_fits()` (which
   measures the raw, unstripped source slice, confirmed by direct
   inspection of `src/boundary_segmentation.py` line 146–147) does not.
   Concrete, fully reproduced example: `mcu1_slide_02.txt` offset
   [583, 593], `'首先請看畫面的中央。'` — raw width 20 (10 chars × 2), stripped
   width 18 (9 chars × 2, after the trailing `。` is removed). Production
   keeps this as one segment (18 ≤ 18); the adapter splits it into two
   (`'首先請看畫'` / `'面的中央'`) because 20 > 18.

**FACT.** Sub-mechanism 2 necessarily pushes Phase 2D toward **more**
segments than production wherever it fires (an extra, otherwise-avoidable
split), which is the *opposite* direction from the observed net −387.
This is direct, quantified confirmation that width measurement — in
either of its two forms — is **not** the primary driver of the net
segment-count reduction; if anything, on this corpus it works
mechanically against the observed direction. The dominant driver of the
net −387 is the fixed-`K`/score-optimization mechanism from §6, which
tends to consolidate more content per line (fewer segments) by choosing
different, sometimes lower-scoring cut combinations across a whole
paragraph rather than following production's per-piece greedy packing.

**INFERENCE.** Because the trailing-punctuation-inflation mechanism (5.0%
of paragraphs) and the fixed-`K` consolidation mechanism (§6, present in
the large majority of paragraphs) operate simultaneously and interact
through the same paragraph-wide DP, their effects are not cleanly
additive — a paragraph affected by both can end up with a final segment
count that is neither the "expected from sub-mechanism 1 alone" nor
"expected from sub-mechanism 2 alone" value. This report does not attempt
to force an additive decomposition of the −387 total; doing so would
overstate the precision the evidence supports.

---

## 9. Word-Boundary Analysis

**FACT.** Of the 3,151 total adapter-only cut positions (positions where
the adapter cut but production did not), **2,187 (69.4%)** sit between two
CJK characters — the structural precondition for a mid-word split, since
neither system has CJK word-segmentation awareness (confirmed: no
`jieba` or other tokenizer import anywhere in
`text_structure.py`/`boundary_observation.py`/`boundary_classification.py`/
`boundary_scoring.py`/`boundary_segmentation.py`/`boundary_segmentation_adapter.py`).
Of those 2,187, **1,369 (62.6%, or 43.4% of all 3,151 adapter-only cuts)**
were confirmed, by running the same `jieba.cut()` tokenization the
existing shadow classifier already uses (imported, not modified), to
split an actual, complete jieba token — not just any CJK-CJK boundary,
but one falling strictly inside a real multi-character word (examples
captured this round: `'對象'`, `'將先'`, `'認識'`, `'建立'`, `'接觸'`,
`'門禁系統'`, `'網路'`, `'背後幾乎'`).

**INFERENCE, answering the user's item 5/F.** Word-boundary/jieba-fallback
absence is a **substantial**, not marginal, contributor to the divergence
picture on real content — 43.4% of the adapter's own extra/different cut
positions land inside a real word. This is a materially higher share than
the prior smaller real-content sample suggested (2 of 4 items there) and
confirms, at scale, that the "known, accepted limitation" framing from
`PHASE_2D_SCOPE_AND_ARCHITECTURE.md` §11 is not a rare edge case on
technical/course narration text — it is one of the more frequent
individual mechanisms observed, on par in scale with the fixed-`K`
mechanism's position count. This report does not add jieba or any word
segmentation to Phase 2D; per the design doc, this was already an
accepted, explicit trade-off, and this round's contribution is only to
quantify its real-content frequency, not to revisit the decision.

**Not established here:** whether these 1,369 mid-word splits *cause*
more or fewer total segments than production's own (also word-blind)
choices at the same positions — a mid-word split is a *positional*
divergence, not inherently a *count* divergence, and this report does not
claim a causal link between word-boundary frequency and the −387 total.

---

## 10. "More Segments" Case Analysis

**FACT.** The three files where Phase 2D produces more segments than
production — `mcu1_slide_19` (+1), `mcu2_slide_09` (+3), `mcu2_slide_10`
(+8) — share a structural property distinct from the corpus median: they
are unusually **paragraph-dense** relative to their length (76 paragraphs
in 1,676 characters; 148 paragraphs in 2,543 characters; 161 paragraphs in
2,526 characters — roughly one paragraph per 16–22 characters, i.e., one
short sentence per line/paragraph in the original notes), compared to the
corpus-wide average of ~21 characters/paragraph overall but with
substantially more variance and many longer, multi-sentence paragraphs in
most other files.

**FACT, per-paragraph breakdown** (re-derived directly from the real
files this round): in all three files, paragraph-level segment-count
differences run in **both directions simultaneously** — e.g. in
`mcu1_slide_19`, 17 of 76 paragraphs have a differing prod-vs-adapter
segment count; of those, most (e.g. `(42,120)`: prod 8 vs. new 7;
`(307,334)`: prod 4 vs. new 3) show the *same* fewer-segments-via-
consolidation pattern seen throughout the rest of the corpus, while a
smaller number of very short, single-sentence paragraphs (e.g.
`(184,194)`: `'首先請看畫面左上角。'`, prod 1 vs. new 2; `(561,571)`:
`'它們並沒有誰比較好。'`, prod 1 vs. new 2) show the trailing-punctuation
raw-width-inflation pattern from §8, needing one *more* segment under
Phase 2D. The net delta for each file (+1, +3, +8) is the arithmetic sum
of many small pulls in both directions, and for these three files
specifically, the width-inflation-driven "+1 per short paragraph" pulls
happen to outweigh the consolidation-driven "−1 per longer paragraph"
pulls — unlike the other 36 files, where the reverse is true.

**INFERENCE, directly answering the user's item G ("this disproves
simplistic explanations such as 'Phase 2D just needs to cut more'").**
Confirmed: these three files are not evidence that Phase 2D is
systematically under-segmenting or over-segmenting in one direction. They
are evidence that (a) at least two distinct, independently-real mechanisms
(§6's consolidation effect and §8's trailing-punctuation-inflation effect)
are simultaneously present in every file, pulling in opposite directions,
and (b) which one dominates a given file's *net* delta depends on that
file's specific mix of paragraph lengths and punctuation placement, not on
any single "Phase 2D over/under-cuts" rule. A model that explained the
data as "Phase 2D always consolidates more" would be contradicted by these
three files; a model that explains it as "two real, opposite-direction
mechanisms whose relative weight varies per paragraph" is consistent with
all 39 files, including these three.

---

## 11. Root Cause Assessment

**FACT (architectural, from §6–§7).** The current
`_select_cut_positions()` implementation computes `target_k` from a pure
width-feasibility scan (`_greedy_min_k_boundaries`, which never consults
`score_map`) before running any score-aware optimization. The
score-maximizing DP that follows is combinatorially restricted to produce
exactly `target_k` segments. This is a direct, unambiguous property of the
code, not an inference from behavior.

**FACT (measured consequence, from §6).** On real content, this
architecture demonstrably and structurally excludes 60.2% of the
"meaningful" (positive-scored) boundaries production would have used,
independent of how strong their score is — a `CLAUSE`-scored (35.0)
position is excluded by the same mechanism, at the same rate in this
sample, as an `OTHER`-with-whitespace-bonus (10.0) position; score
magnitude plays no role in whether a candidate is even eligible once `K`
is fixed too low to admit it.

**FACT (a second, independent, measured consequence, from §8).** The same
general limitation (Phase 2D's width measurement operating on raw,
unstripped source text) manifests differently on this corpus than the
synthetic corpus previously suggested — not via whitespace runs, but via
systematic trailing-punctuation inflation affecting 5.0% of all
paragraphs — and works in the **opposite net direction** from the
architectural exclusion effect.

**INFERENCE.** The −387 net segment delta is not attributable to one
root cause. It is the superposition of at least three distinct,
independently-demonstrated mechanisms: (1) fixed-`K` candidate exclusion
(§6, dominant, segment-count-*reducing* in aggregate), (2) raw-vs-
normalized width measurement via trailing punctuation (§8, real but
smaller, segment-count-*increasing*), and (3) CJK word-boundary
positional drift (§9, real and substantial, but a *positional*, not
directly *count*-affecting, mechanism on its own). The user's Section 6
hypothesis — that the fixed-`K` architecture is a genuine, not merely
theoretical, cause of Phase 2D's divergence from production — is
**supported by direct evidence**, but it is one of several real causes,
not the sole explanation for every observed number.

**HYPOTHESIS, not established by this round's evidence:** whether fixing
the `K`-selection step (letting Phase 2C scores influence segment count,
not just position, within it) would bring Phase 2D's aggregate segment
count and per-paragraph choices closer to production's, or whether it
would diverge further in a different way. This report does not test any
alternative architecture, per its explicit scope.

---

## 12. Impact on Current Phase 2D Architecture

**FACT.** No test currently in the repository (`tests/test_boundary_segmentation.py`,
28 tests; `tests/test_boundary_segmentation_adapter.py`, 39 tests;
`tests/test_shadow_mode_comparison.py`, 17 tests/15 subtests) exercises
the specific fixed-`K`-exclusion scenario demonstrated in §6 as a named,
asserted behavior — the existing test suites verify that the current
algorithm behaves *consistently with itself* (deterministic, respects
width, respects paragraph boundaries, etc.), not that its `K`-selection
step is the *right* design relative to Phase 2C's scoring intent. This is
not a criticism of test coverage; it is a scope observation: the existing
tests were written to pin the accepted Round 1 design, and they do so
correctly and completely for what that design specifies. §6's finding is
a question about whether that design specification itself fully realizes
Phase 2C's intent, which is a different question from "does the code
match its own spec."

**INFERENCE.** The architecture's core algorithmic properties that make it
*safe* — deterministic, no re-detection of upstream evidence, no
production wiring, paragraph boundaries respected, D04 resolved generically
(all re-confirmed unchanged this round) — are untouched by this finding.
What is in question is narrower and more specific: the two-phase
"fix `K` by width alone, then optimize position given that `K`" sequencing
inside `_select_cut_positions()`.

---

## 13. What Remains Valid

**FACT/INFERENCE**, unaffected by this round's findings:

- The overall Phase 1→2A→2B→2C→2D pipeline separation of concerns
  (evidence gathering, classification, scoring, and segmentation as
  distinct, composable stages) remains sound — this round's findings are
  entirely about *how* Phase 2D's segmentation stage consumes Phase 2C's
  scores, not about the staging itself.
- Paragraph boundaries as hard, non-crossable structural boundaries:
  unaffected, still correctly enforced (confirmed again via
  `_split_paragraphs`, unmodified).
- D04's generic resolution via the general DP with no CJK/whitespace
  special-casing: unaffected, re-confirmed via source inspection this
  round exactly as in the prior review.
- The `WeightedBoundary` score values themselves (Phase 1–2C, frozen):
  unaffected — this round found no new evidence that any individual score
  value is wrong; the scores observed on real content (35.0 `CLAUSE`, 90.0
  `SENTENCE_FINAL`+whitespace, 10.0 whitespace-`OTHER`, etc.) all match
  their documented, calibrated values exactly.
- The decision NOT to add jieba/word-segmentation to Phase 2D: unaffected
  by this round — §9 quantifies the cost of that decision on real content
  more precisely than before, but does not present new evidence that the
  decision itself was wrong, only that its real-world frequency is higher
  than the small samples previously available could show.
- The width-safety guarantee ("Phase 2D never produces an over-width
  line"): re-confirmed, not contradicted — every mechanism described in
  this report is about *count* and *position* choices, not about any
  output exceeding `max_display_width`.

---

## 14. What Must Be Reconsidered

**INFERENCE**, directly supported by §6–§11:

- **The sequencing inside `_select_cut_positions()`** — computing
  `target_k` from width alone, then optimizing position within a fixed
  `K` — is the specific place where Phase 2C's scoring signal is
  prevented from influencing segment count. This is the concrete locus of
  the architectural question raised by the user's Section 6 hypothesis,
  now demonstrated rather than merely hypothesized.
- **The "raw source width vs. normalized display width" measurement gap**
  (`boundary_segmentation.py`'s own documented, accepted limitation) is
  confirmed to matter on real content at a non-trivial, quantified rate
  (5.0% of paragraphs) via a mechanism (trailing punctuation) distinct
  from the one previously demonstrated (whitespace runs) — worth
  recording explicitly as a second, separately-caused instance of the
  same named limitation, not folding the two together as if one example
  covered both.
- **The real-content frequency of word-boundary divergence** (43.4% of
  adapter-only cuts) is higher than prior evidence suggested and should be
  weighed, as a quantified fact rather than a qualitative caveat, in any
  future cutover-readiness discussion — without this report proposing
  that the underlying design decision be changed.

**HYPOTHESIS, explicitly not tested or endorsed by this report:** any
specific alternative to fixed-`K` DP (e.g., score-aware variable-`K`
optimization, a penalty-per-additional-segment formulation, or a
constrained optimization letting Phase 2C scores directly influence `K`)
is a candidate direction for a future design discussion, not a
recommendation made here. This report does not evaluate, prototype, or
favor any of these; naming them is only to make clear what kind of
follow-up question §6–§11's findings raise.

---

## 15. Recommended Next Design Step

**INFERENCE**, following directly from §11–§14 without proposing a
specific implementation: before any further Phase 2D implementation or
cutover-design work proceeds, the `K`-selection step inside
`_select_cut_positions()` should be the subject of an explicit design
review that asks whether Phase 2C's boundary scores are intended to be
able to influence segment count, and if so, what mechanism would let them
do so without abandoning the current architecture's other, still-valid
properties (determinism, no upstream re-detection, paragraph-boundary
enforcement, width-safety). This report does not propose that review's
outcome. It recommends that the review happen before Step 2 (production
cutover design) proceeds, because §6 establishes that the current
architecture's fixed-`K` behavior is not an edge case on real content — it
is the majority explanation (60.2% of the quantified sample) for why
Phase 2D bypasses boundaries production considers important.

---

## 16. Explicit Non-Goals / No Implementation Changes

This round did not, and this report does not:

- Modify `src/boundary_segmentation.py`, `src/boundary_segmentation_adapter.py`,
  `src/subtitle_segmenter.py`, `src/subtitle_pipeline.py`, or any Phase
  1–2C source file.
- Modify any existing test file or change any existing behavioral
  expectation.
- Add a threshold, a new heuristic, colon handling, jieba/word
  segmentation, or any semantic-phrase logic to Phase 2D.
- Change any Phase 2C score value.
- Perform, wire, or gate a production cutover.
- Propose or implement a replacement segmentation algorithm — §14's named
  conceptual alternatives are listed only to characterize the shape of the
  open design question, not as a recommendation.
- Change the evaluation methodology (width value, corpus, or comparison
  functions) to make the divergence numbers look better or worse than
  they are.

**Verification performed after writing this document:**

- Exactly one new file was created: `docs/phase2d/PHASE_2D_REAL_CONTENT_DIAGNOSTIC_REPORT.md`.
- All twelve previously-baselined implementation/test files re-checksummed
  as unchanged (§2).
- `pytest tests/ -q` → 531 passed, 30 subtests passed (unchanged from
  baseline).
- `pytest tests/test_shadow_mode_comparison.py -q` → 17 passed, 15
  subtests passed (unchanged from baseline).
- `src.boundary_segmentation_adapter` remains unimported by any file under
  `src/` other than its own module (confirmed by direct grep this round).
- No production cutover, feature flag, or wiring was introduced.
