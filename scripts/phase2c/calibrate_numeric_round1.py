#!/usr/bin/env python3
"""CALIBRATION TOOLING ONLY - Phase 2C Round 1.

This script is NOT production code. It is not imported by, and does not
modify, any module under src/. It implements ONLY the provisional
calibration formula documented in
docs/PHASE_2C_CALIBRATION_MATRIX.md section 13, applied on top of the
REAL, unmodified Phase 1 -> Phase 2A -> Phase 2B pipeline
(analyze_text_structure -> observe_boundaries -> classify_boundary).

It does not re-implement any Phase 1/2A/2B detection, observation, or
classification logic - every BoundaryClass, CharacterClass,
PunctuationSequenceState, and StructuralBoundaryContext value used below
comes directly from calling the real, unmodified functions in
src/text_structure.py, src/boundary_observation.py, and
src/boundary_classification.py.

Usage:
    python scripts/phase2c/calibrate_numeric_round1.py > /tmp/calibration_round1_raw.txt

This dumps, for a fixed set of calibration texts, every internal boundary
candidate's real pipeline evidence plus the calibration-only score, so the
Round 1 report can be written directly from real, captured output rather
than from hand-computed or assumed numbers.
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
# Calibration-only scoring (Matrix v0.1 section 13) - NOT a production module.
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
    print("PHASE 2C CALIBRATION ROUND 1 - RAW PIPELINE DUMP")
    print("=" * 100)
    print()

    cases = [
        ("C01", "今天我們介紹 CPU。"),
        ("C02", "這個問題嘛……"),
        ("C03", "首先，我們介紹 CPU"),
        ("C04", "中文中文"),
        ("C09", "中文English"),
        ("C10", "English中文"),
        ("C11", "中文 English"),
        ("C12", "English 中文"),
        ("C14_attempt", "首先， English"),
        ("C17", "1,000"),
        ("C18", "1, 000"),
        ("C19", "3.14"),
        ("C20/C21", "嗯......"),
        ("C20b_internal_run", "......"),
        ("C26_ordinary_clause", "第一，第二"),
        ("C30", "今天我們先介紹 CPU 的基本架構，接著再說明 GPU 與 NPU 的差異。"),
        ("C31", "我們使用 ARM Cortex-A 系列 CPU，並搭配 Linux OS。"),
        ("C32", "這個架構主要包含 CPU、GPU、NPU 三個主要運算單元，其中 CPU 負責一般運算。"),
        ("C33", "CPU / GPU / NPU 是目前常見的 AI accelerator。"),
        ("C34", "這個功能可以在 Linux OS 上執行，Windows 版本則需要另外設定。"),
        ("C35", "首先我們來看 API 的基本架構，然後再說明 SDK 的使用方式。"),
        ("C36", "例如我們可以使用 Python API 呼叫這個 function，接著再處理回傳結果。"),
        ("C37", "這個問題嘛……我們稍後再回來討論。"),
        ("C38", "如果設定完成，就可以開始執行。"),
        ("C39", "接下來我們會看到一個很重要的概念：CPU、GPU 與 NPU 的工作分工。"),
        ("C40", "換句話說，CPU 負責一般運算，而 GPU 比較適合平行運算。"),
        ("X01", "CPU、 GPU"),
        ("X01b_嗯……", "嗯……"),
        ("X03", "1,000"),
        ("X05", "見 v1.2.3-beta 版本說明 http://example.com/path 頁面。"),
        ("X06", "中文 English 中文 English 中文"),
        ("X07a", "真的？！"),
        ("X07b", "……|…… merged run", "……" + "……"),
        # ---------------------------------------------------------------
        # Round 1 supplementary probes (added after initial dump review).
        # Purpose: several matrix cases (C01, C02, X01) place their key
        # punctuation at the absolute end of the calibration string. Since
        # observe_boundaries() only yields candidates strictly BETWEEN two
        # existing adjacent characters, a boundary "after the very last
        # character" is never produced - so the matrix's intended
        # SENTENCE_FINAL/ELLIPSIS-at-string-end candidate is structurally
        # absent from the C01/C02/X01b dumps above. These probes append one
        # trailing character to reveal what the real pipeline scores at
        # that exact boundary once it CAN exist, purely as additional
        # calibration observation - this does not change or reinterpret
        # C01/C02/X01, it supplements them with same-shape evidence.
        # ---------------------------------------------------------------
        ("C01_ctx_probe", "今天我們介紹 CPU。好"),
        ("C02_ctx_probe", "這個問題嘛……好"),
        ("X01b_ctx_probe", "嗯……好"),
        ("C20_ascii_end_probe", "......好"),
    ]

    for entry in cases:
        if len(entry) == 3:
            case_id, label, text = entry
            dump(text, f"{case_id} {label}")
        else:
            case_id, text = entry
            dump(text, case_id)
