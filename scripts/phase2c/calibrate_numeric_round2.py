#!/usr/bin/env python3
"""CALIBRATION TOOLING ONLY - Phase 2C Round 2.

This script is NOT production code. It is not imported by, and does not
modify, any module under src/. It implements ONLY the provisional
calibration formula documented in
docs/PHASE_2C_CALIBRATION_MATRIX.md (v0.2) section 2, applied on top of the
REAL, unmodified Phase 1 -> Phase 2A -> Phase 2B pipeline
(analyze_text_structure -> observe_boundaries -> classify_boundary).

This is a new script (rather than an in-place edit of
scripts/phase2c/calibrate_numeric_round1.py) because the v0.2 matrix uses a
different case grouping (A-H, X) and different case texts (every case now
embeds its target boundary with trailing context, per v0.2 section 3.1, so
no case text is string-final at its point of interest). The Round 1 script
and its raw output are left untouched for historical comparison.

It does not re-implement any Phase 1/2A/2B detection, observation, or
classification logic - every BoundaryClass, CharacterClass,
PunctuationSequenceState, and StructuralBoundaryContext value used below
comes directly from calling the real, unmodified functions in
src/text_structure.py, src/boundary_observation.py, and
src/boundary_classification.py.

Usage:
    python scripts/phase2c/calibrate_numeric_round2.py > /tmp/calibration_round2_raw.txt

This dumps, for every v0.2 calibration case, every real boundary
candidate's pipeline evidence plus the calibration-only score, so the
Round 2 report can be written directly from real, captured output.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.boundary_classification import BoundaryClass, classify_boundary
from src.boundary_observation import (
    BoundaryCandidate,
    CharacterClass,
    PunctuationSequenceState,
    observe_boundaries,
)
from src.text_structure import analyze_text_structure

# ---------------------------------------------------------------------------
# Calibration-only scoring (Matrix v0.2 section 2) - NOT a production module.
# Numerically identical to Round 1's formula; the weights are unchanged.
# ---------------------------------------------------------------------------

_BASE_SCORES = {
    BoundaryClass.SENTENCE_FINAL: 80.0,
    BoundaryClass.ELLIPSIS: 65.0,
    BoundaryClass.CLAUSE: 35.0,
    BoundaryClass.OTHER: 0.0,
}


def calibration_score(candidate: BoundaryCandidate):
    """Return (boundary_class, score, modifier_breakdown) for `candidate`,
    using ONLY evidence already present on the real Phase 2A/2B output -
    no re-detection, no inference from raw text.
    """
    features = candidate.features
    boundary_class = classify_boundary(candidate)  # real Phase 2B classification
    score = _BASE_SCORES[boundary_class]
    modifiers = []

    lc = features.left_character_class
    rc = features.right_character_class
    if lc == CharacterClass.CJK and rc == CharacterClass.LATIN:
        score += 15
        modifiers.append(("CJK->LATIN", +15))
    if lc == CharacterClass.LATIN and rc == CharacterClass.CJK:
        score += 15
        modifiers.append(("LATIN->CJK", +15))
    if lc == CharacterClass.WHITESPACE or rc == CharacterClass.WHITESPACE:
        score += 10
        modifiers.append(("Whitespace", +10))

    containing_types = {s.type for s in features.structural_context.containing_spans}
    if "technical" in containing_types:
        score -= 30
        modifiers.append(("Technical", -30))
    if "atomic" in containing_types:
        score -= 30
        modifiers.append(("Atomic", -30))

    if features.punctuation_sequence_state == PunctuationSequenceState.INTERNAL:
        score -= 20
        modifiers.append(("InternalSeq", -20))

    return boundary_class, score, modifiers


def dump(text: str, label: str = ""):
    analysis = analyze_text_structure(text)
    candidates = observe_boundaries(analysis)
    print(f"### {label}")
    print(f"text = {text!r}  (len={len(text)})")
    for c in candidates:
        bclass, score, mods = calibration_score(c)
        containing = [f"{s.type}/{s.subtype}" for s in c.features.structural_context.containing_spans]
        mod_str = ", ".join(f"{name}{val:+d}" for name, val in mods) if mods else "-"
        print(
            f"  pos={c.position:3d}  L={c.left_char!r:>6s} R={c.right_char!r:>6s}  "
            f"LC={c.features.left_character_class.value:<10s} RC={c.features.right_character_class.value:<10s}  "
            f"seq_state={c.features.punctuation_sequence_state.value:<8s}  "
            f"sf_evidence={c.features.contains_sentence_final_punctuation!s:<5s}  "
            f"containing={containing}  "
            f"class={bclass.value:<14s} score={score:6.1f}  mods=[{mod_str}]"
        )
    print()
    return analysis, candidates


if __name__ == "__main__":
    print("=" * 100)
    print("PHASE 2C CALIBRATION ROUND 2 - RAW PIPELINE DUMP (Matrix v0.2)")
    print("=" * 100)
    print()

    cases = [
        # ---------------- Group A - Base Boundary Classes ----------------
        ("A01", "今天我們介紹 CPU。接下來我們看 GPU。"),
        ("A02", "這個問題嘛……接下來我們再討論。"),
        ("A03", "首先，我們介紹 CPU，接著再看 GPU。"),
        ("A04", "中文English"),
        # ---------------- Group B - Base Pairwise Hierarchy ----------------
        # B01 as literally given in the matrix (embedded line break preserved).
        ("B01", "今天我們介紹 CPU。接下來我們看 GPU，\n然後再說明 NPU。"),
        # Diagnostic-only variant of B01 with the line break removed, to check
        # whether the embedded newline changes candidate topology. Excluded
        # from official B01 results; reported separately as a topology check.
        ("B01_diagnostic_no_newline", "今天我們介紹 CPU。接下來我們看 GPU，然後再說明 NPU。"),
        ("B02", "這個問題嘛……我們先暫停一下。接下來繼續。"),
        ("B03", "這個問題嘛……接下來再討論，現在先看 CPU。"),
        # ---------------- Group C - Language Transition ----------------
        ("C01", "我們使用 Linux。"),
        ("C02", "Linux 系統需要重新設定。"),
        # C03 reuses A03 (clause) and C01 (transition) - no new text.
        # ---------------- Group D - Whitespace Topology ----------------
        ("D01_D02_D04", "中文 English"),
        ("D03", "中文  English"),
        # ---------------- Group E - Technical / Atomic Protection ----------------
        ("E01", "這個值是 1,000，接下來繼續。"),
        ("E02", "目前使用 v1.2.3，接下來介紹新版。"),
        # E03/E04 reuse E01/E02 vs A03/C01/C02 - no new text.
        # ---------------- Group F - Punctuation Sequence ----------------
        ("F01", "這個問題嘛……接下來再討論。"),
        ("F02", "……接下來"),
        # F03 reuses F01 (END) vs F02 (INTERNAL) - no new text.
        # ---------------- Group G - Sentence-Final / Ellipsis Composition ----------------
        ("G01", "真的……？接下來我們說明。"),
        ("G02", "真的……！接下來我們說明。"),
        ("G03_diagnostic_upstream_probe", "真的......接下來我們說明。"),
        # ---------------- Group H - Realistic Mixed-Language Cases ----------------
        ("H01", "今天我們先介紹 CPU 的基本架構，接著再說明 GPU 與 NPU 的差異。"),
        ("H02", "我們使用 ARM Cortex-A 系列 CPU，並搭配 Linux OS。"),
        ("H03", "這個架構主要包含 CPU、GPU、NPU 三個主要運算單元，其中 CPU 負責一般運算。"),
        ("H04", "CPU / GPU / NPU 是目前常見的 AI accelerator。"),
        ("H05", "這個功能可以在 Linux OS 上執行，Windows 版本則需要另外設定。"),
        ("H06", "首先我們來看 API 的基本架構，然後再說明 SDK 的使用方式。"),
        ("H07", "例如我們可以使用 Python API 呼叫這個 function，接著再處理回傳結果。"),
        ("H08", "這個問題嘛……我們稍後再回來討論。"),
        # ---------------- Group X - Upstream Representation Probes (diagnostic-only) ----------------
        ("X01_decimal", "3.14 接下來我們說明。"),
        ("X02_version", "v1.2.3-beta 接下來介紹新版。"),
        ("X03_url", "請參考 http://example.com 接下來的說明。"),
        ("X04_ascii_ellipsis", "真的......接下來我們說明。"),
        ("X05_mixed_punct", "真的？！接下來我們說明。"),
        ("X06_paired_delimiter", "「真的？！」接下來我們說明。"),
    ]

    for entry in cases:
        if len(entry) == 3:
            case_id, label, text = entry
            dump(text, f"{case_id} {label}")
        else:
            case_id, text = entry
            dump(text, case_id)
