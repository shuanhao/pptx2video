"""Verify that an AI-preprocessed speaker-notes file is safe to paste back
into a PowerPoint deck's notes pane, before running it through the rest of
the pipeline.

Why this exists: users can ask an external AI chatbot (ChatGPT, Gemini,
etc.) to pre-punctuate and pre-break long speaker notes at the same width
limit ``subtitle_segmenter.py`` uses (``DEFAULT_MAX_DISPLAY_WIDTH``), so that
every paragraph already fits on one subtitle line and the automatic
``_hard_split()`` fallback (which uses jieba, and jieba occasionally breaks
a real word in half - see docs/SUBTITLE_OVERLAP_INCIDENT.md section 10 for
the "廣泛" case that motivated this) never has to run at all.

That only works if the chatbot's output is trustworthy. Real testing (not
hypothetical - three separate rounds against real chatbot output) found
every one of the following failure modes actually happen in practice, not
just in theory:

- Content silently rewritten (synonyms swapped, examples replaced, whole
  clauses reworded) despite an explicit "don't change the wording"
  instruction - this is the most dangerous failure because it can
  introduce factual errors into training content without looking wrong at
  a glance.
- A chatbot going too far the other way: refusing to actually do the
  requested line-breaking out of over-caution, leaving most lines still
  over the width limit.
- Real words (Chinese compound words *and* English words) broken across a
  line boundary by the chatbot's own line-breaking choices, the exact
  class of bug this whole exercise is trying to avoid.
- Paragraph (blank-line) structure collapsed or merged, losing pacing
  structure the original speaker notes had.

This script runs four independent checks against an (original, processed)
pair of plain-text speaker notes files and prints a report - problems
only, each with the evidence it was flagged on, so the report doesn't
drown genuinely clean output in "no problem here" noise. See
docs/SPLIT_VIDEO.md or the project discussion log for the checks' design
rationale.

Usage:
    python scripts/verify_notes_preprocessing.py \\
        --original note.txt --processed note_aichatbot.txt

    # tighten/loosen the width budget away from the segmenter's own default
    # (matches DEFAULT_MAX_DISPLAY_WIDTH unless overridden):
    python scripts/verify_notes_preprocessing.py \\
        --original note.txt --processed note_aichatbot.txt --max-width 34

Exit code: 0 if all four checks are clean, 1 if any check found something -
so this can gate a "don't paste this back into PowerPoint yet" decision in
a script, not just in a human reading the printed report.
"""

import argparse
import difflib
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.logging_config import ensure_utf8_console
from src.subtitle_segmenter import (
    DEFAULT_MAX_DISPLAY_WIDTH,
    _display_width,
    _split_paragraphs_with_offsets,
    segment_notes_for_subtitles,
)

# Punctuation an AI preprocessing pass is explicitly allowed to insert (see
# the "只允許插入標點符號和換行" prompt rule this script is meant to check
# compliance with) - stripped out before the content-fidelity diff so that
# *adding* one of these doesn't register as a content change. Deliberately
# does not include quotes/brackets/parentheses/em-dash - those carry
# structural meaning (e.g. pairing) an AI has no business introducing on
# its own, so a change involving one of those should still surface as a
# content diff.
_ALLOWED_INSERTED_PUNCTUATION = "，。、；：？！,.;:?!"

_CJK_RANGE = ("一", "鿿")


def _is_cjk(ch: str) -> bool:
    return _CJK_RANGE[0] <= ch <= _CJK_RANGE[1]


def _normalize_for_content_diff(text: str) -> str:
    """Strip whitespace/newlines and the punctuation an AI pass is allowed
    to add, leaving only the "real content" characters - if this string is
    identical between the original and processed files, no wording was
    added, removed, or substituted (only permitted punctuation/newlines
    changed).
    """
    pattern = r"[\s" + re.escape(_ALLOWED_INSERTED_PUNCTUATION) + r"「」『』（）\(\)'\"“”…—\-]"
    return re.sub(pattern, "", text)


def check_content_fidelity(original: str, processed: str) -> List[str]:
    """Check 1: does the processed file contain the same content as the
    original, once whitespace/newlines and AI-permitted punctuation are
    stripped out? Reports every non-matching span with surrounding context
    so it's clear whether it's an insertion, deletion, or substitution.
    """
    orig_norm = _normalize_for_content_diff(original)
    proc_norm = _normalize_for_content_diff(processed)

    if orig_norm == proc_norm:
        return []

    findings = []
    matcher = difflib.SequenceMatcher(None, orig_norm, proc_norm, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        context_before = orig_norm[max(0, i1 - 8):i1]
        context_after = proc_norm[j2:j2 + 8]
        orig_span = orig_norm[i1:i2]
        proc_span = proc_norm[j1:j2]
        kind = {"replace": "替換", "delete": "刪除", "insert": "新增"}[tag]
        findings.append(
            f"  位置：...{context_before}【{orig_span or '(無)'}】→【{proc_span or '(無)'}】{context_after}...\n"
            f"  判斷依據：內容{kind}（不是標點或換行的差異）"
        )
    return findings


def check_line_width(processed: str, max_width: int) -> List[str]:
    """Check 2: run the *actual* production segmenter
    (``segment_notes_for_subtitles``) over the processed text and see
    whether any input paragraph still needed further splitting - the
    ground-truth signal for "this line is still too wide and will trigger
    the jieba hard-split fallback", rather than an approximated width
    check reimplemented separately from the real code path.
    """
    paragraphs = _split_paragraphs_with_offsets(processed)
    segments = segment_notes_for_subtitles(processed, max_display_width=max_width)

    # Count how many output segments came from each input paragraph, by
    # matching each segment's source_start_offset to the paragraph whose
    # [start, end) range contains it.
    segment_counts: Dict[int, int] = {}
    for seg in segments:
        for idx, (p_start, p_end) in enumerate(paragraphs):
            if p_start <= seg["source_start_offset"] < p_end:
                segment_counts[idx] = segment_counts.get(idx, 0) + 1
                break

    findings = []
    lines_before_each_paragraph = processed[: paragraphs[0][0]].count("\n") if paragraphs else 0
    for idx, (p_start, p_end) in enumerate(paragraphs):
        count = segment_counts.get(idx, 0)
        if count > 1:
            para_text = processed[p_start:p_end].strip()
            line_no = processed[:p_start].count("\n") + 1
            width = _display_width(para_text)
            findings.append(
                f"  第 {line_no} 行（顯示寬度 {width}，上限 {max_width}）\n"
                f"    {para_text}\n"
                f"  判斷依據：這一段被 segment_notes_for_subtitles() 實際切成了 {count} 段字幕，"
                f"代表它還是太寬、系統會啟動 jieba 硬斷字"
            )
    return findings


def check_word_splits(original: str, processed: str) -> List[str]:
    """Check 3: for every line-break in the processed text, see whether the
    last character of one line plus the first character of the next forms
    either (a) a real Chinese word per jieba's dictionary, or (b) a
    contiguous run of ASCII letters split with no space - both patterns
    observed on real chatbot output (e.g. "重要" -> "重"/"要", "Program" ->
    "P"/"rogram"). This is a heuristic with real false-positive risk
    (coincidental sentence-boundary bigrams that happen to also be words -
    see docs/SUBTITLE_OVERLAP_INCIDENT.md section 10's "廣泛" discussion for
    why dictionary membership alone isn't proof) - every finding carries its
    evidence so it can be triaged, not blindly trusted.

    The English-word check cross-references the *original* text: two
    adjacent English words split at their natural space (e.g. "...
    Fundamentals" / "Training ...") are not a bug, only a genuinely
    contiguous word broken mid-token is. Confirmed both patterns occur on
    real chatbot output (see the "Fundamentals"/"Training" false positive
    this cross-check exists to rule out, versus the real "Program" ->
    "P"/"rogram" split it still catches).
    """
    import jieba

    jieba.setLogLevel(logging.WARNING)
    jieba.initialize()
    freq = jieba.dt.FREQ

    lines = [l for l in processed.split("\n") if l.strip()]
    # Track line numbers against the *original* (non-stripped) line list so
    # findings point at real file line numbers.
    raw_lines = processed.split("\n")
    non_blank_line_numbers = [i + 1 for i, l in enumerate(raw_lines) if l.strip()]

    findings = []
    for i in range(len(lines) - 1):
        t1, t2 = lines[i], lines[i + 1]
        last, first = t1[-1], t2[0]
        line_no_1 = non_blank_line_numbers[i]
        line_no_2 = non_blank_line_numbers[i + 1]

        if last.isascii() and last.isalpha() and first.isascii() and first.isalpha():
            trailing_token = re.search(r"[A-Za-z0-9]+$", t1)
            leading_token = re.search(r"^[A-Za-z0-9]+", t2)
            trailing_token = trailing_token.group(0) if trailing_token else last
            leading_token = leading_token.group(0) if leading_token else first
            merged_word = trailing_token + leading_token
            # Only a real split if the merged form exists as one contiguous
            # word in the original - two separate words that happened to be
            # broken at their natural space (e.g. "Fundamentals" / "Training")
            # would only appear in the original with a space between them,
            # never merged.
            if re.search(re.escape(merged_word), original):
                findings.append(
                    f"  第 {line_no_1}/{line_no_2} 行 —— 疑似拆開英文單字「{merged_word}」\n"
                    f"    前一行結尾：...{t1[-15:]}\n"
                    f"    後一行開頭：{t2[:15]}...\n"
                    f"  判斷依據：原文裡「{merged_word}」是連續出現、中間沒有空格的同一個單字"
                )
            continue

        if not (_is_cjk(last) and _is_cjk(first)):
            continue
        bigram = last + first
        if bigram in freq and freq[bigram] > 0:
            findings.append(
                f"  第 {line_no_1}/{line_no_2} 行 —— 疑似拆開「{bigram}」\n"
                f"    前一行結尾：...{t1[-8:]}\n"
                f"    後一行開頭：{t2[:8]}...\n"
                f"  判斷依據：詞典比對，「{bigram}」為 jieba 詞典收錄的詞（詞頻 {freq[bigram]}）"
            )
    return findings


def check_paragraph_structure(original: str, processed: str) -> List[str]:
    """Check 4: compare the number of blank-line-separated blocks between
    the original and processed text. If the processed file has fewer
    blocks, some blank-line separator was lost - report which original
    blocks got merged together (matched by concatenated normalized
    content), so it can be traced back to roughly where in the source it
    happened.
    """

    def blocks(text: str) -> List[str]:
        return [b for b in re.split(r"\n\s*\n", text) if b.strip()]

    orig_blocks = blocks(original)
    proc_blocks = blocks(processed)

    if len(orig_blocks) == len(proc_blocks):
        return []

    orig_norms = [_normalize_for_content_diff(b) for b in orig_blocks]
    proc_norms = [_normalize_for_content_diff(b) for b in proc_blocks]

    findings = []
    oi = 0
    for pi, proc_norm in enumerate(proc_norms):
        merged_orig_previews = []
        accumulated = ""
        while oi < len(orig_norms) and accumulated != proc_norm:
            accumulated += orig_norms[oi]
            merged_orig_previews.append(orig_blocks[oi].strip().splitlines()[0][:20])
            oi += 1
            if len(accumulated) > len(proc_norm):
                break
        if len(merged_orig_previews) > 1:
            findings.append(
                "  AI 版本把原文這幾個小節合併成一段：\n"
                + "\n".join(f"    - {p}..." for p in merged_orig_previews)
                + "\n  判斷依據：這幾段原文內容合併後，跟 AI 版本裡的同一段完全對應"
            )

    if not findings:
        findings.append(
            f"  原文有 {len(orig_blocks)} 組段落分隔，AI 版本有 {len(proc_blocks)} 組\n"
            f"  判斷依據：段落區塊數量不一致，但無法自動定位是哪裡被合併，建議人工比對"
        )
    return findings


def _print_section(title: str, findings: List[str]) -> None:
    print(f"【{title}】：發現 {len(findings)} 處" if findings else f"【{title}】：無問題")
    if findings:
        print()
        for f in findings:
            print(f)
            print()


def main() -> int:
    ensure_utf8_console()

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--original", required=True, help="原始備忘稿純文字檔路徑")
    parser.add_argument("--processed", required=True, help="AI 處理後的備忘稿純文字檔路徑")
    parser.add_argument(
        "--max-width",
        type=int,
        default=DEFAULT_MAX_DISPLAY_WIDTH,
        help=f"顯示寬度上限（預設跟 subtitle_segmenter.py 一致：{DEFAULT_MAX_DISPLAY_WIDTH}）",
    )
    args = parser.parse_args()

    original = Path(args.original).read_text(encoding="utf-8")
    processed = Path(args.processed).read_text(encoding="utf-8")

    print("=" * 40)
    print("字幕前處理驗證報告")
    print(f"比對對象：{args.original}（原文） vs {args.processed}（AI 處理後）")
    print("=" * 40)
    print()

    content_findings = check_content_fidelity(original, processed)
    _print_section("1. 內容保真度", content_findings)
    print("-" * 40)

    width_findings = check_line_width(processed, args.max_width)
    _print_section("2. 行寬檢查（透過 subtitle_segmenter.py 實際跑一遍）", width_findings)
    print("-" * 40)

    word_split_findings = check_word_splits(original, processed)
    _print_section("3. 疑似拆詞", word_split_findings)
    print("-" * 40)

    paragraph_findings = check_paragraph_structure(original, processed)
    _print_section("4. 段落結構（空白行分隔）", paragraph_findings)
    print("=" * 40)

    total = len(content_findings) + len(width_findings) + len(word_split_findings) + len(paragraph_findings)
    ok = lambda findings: "✅" if not findings else f"⚠️ {len(findings)} 處"
    print(
        f"摘要：內容保真 {ok(content_findings)} ｜ "
        f"行寬超標 {ok(width_findings)} ｜ "
        f"疑似拆詞 {ok(word_split_findings)} ｜ "
        f"段落結構 {ok(paragraph_findings)}"
    )
    print("=" * 40)

    return 1 if total > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
