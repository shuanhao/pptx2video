#!/usr/bin/env python3
"""CALIBRATION TOOLING ONLY - Phase 2C Protection Calibration Round 1.

This script is NOT production code. It is not imported by, and does not
modify, any module under src/. It implements ONLY the provisional
"protection family" scoring formula documented in
docs/phase2c/calibration/matrices/PHASE_2C_PROTECTION_CALIBRATION_MATRIX.md section 4, applied on top
of the REAL, unmodified Phase 1 -> Phase 2A -> Phase 2B pipeline
(analyze_text_structure -> observe_boundaries -> classify_boundary).

Unlike scripts/phase2c/calibrate_numeric_round1.py and
scripts/phase2c/calibrate_numeric_round2.py (which additively combine Technical
and Atomic, i.e. -30 + -30 = -60 when both apply), this script implements
the Protection Calibration Matrix v0.1's alternative "strongest-only"
protection rule:

    ProtectionPenalty = -max(30 if technical else 0, 30 if atomic else 0)

so Technical+Atomic on the same candidate is -30, not -60. INTERNAL
(punctuation sequence suppression) remains a fully independent -20 that
can combine with the protection penalty (e.g. Technical+INTERNAL = -50)
if and only if the real pipeline ever exposes that combination on one
candidate - this script does not manufacture such a candidate.

It does not re-implement any Phase 1/2A/2B detection, observation, or
classification logic - every BoundaryClass, CharacterClass,
PunctuationSequenceState, and StructuralBoundaryContext value used below
comes directly from calling the real, unmodified functions in
src/text_structure.py, src/boundary_observation.py, and
src/boundary_classification.py.

Usage:
    python scripts/phase2c/calibrate_protection_round1.py > /tmp/calibration_protection_round1_raw.txt
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
# Calibration-only scoring (Protection Matrix v0.1 section 4) - NOT a
# production module. Base classes and positive modifiers are numerically
# identical to the Round 1/2 scripts; only the protection combination rule
# differs (strongest-only rather than additive).
# ---------------------------------------------------------------------------

_BASE_SCORES = {
    BoundaryClass.SENTENCE_FINAL: 80.0,
    BoundaryClass.ELLIPSIS: 65.0,
    BoundaryClass.CLAUSE: 35.0,
    BoundaryClass.OTHER: 0.0,
}


def calibration_score(candidate: BoundaryCandidate):
    """Return (boundary_class, score, breakdown_dict) for `candidate`, using
    ONLY evidence already present on the real Phase 2A/2B output - no
    re-detection, no inference from raw text. Protection (Technical/Atomic)
    uses strongest-only combination per the Protection Matrix v0.1; INTERNAL
    is fully independent and additive on top of whatever protection penalty
    (if any) applies.
    """
    features = candidate.features
    boundary_class = classify_boundary(candidate)  # real Phase 2B classification
    base = _BASE_SCORES[boundary_class]

    lc = features.left_character_class
    rc = features.right_character_class
    transition_bonus = 0.0
    transition_label = None
    if lc == CharacterClass.CJK and rc == CharacterClass.LATIN:
        transition_bonus = 15.0
        transition_label = "CJK->LATIN"
    elif lc == CharacterClass.LATIN and rc == CharacterClass.CJK:
        transition_bonus = 15.0
        transition_label = "LATIN->CJK"

    whitespace_bonus = 10.0 if (lc == CharacterClass.WHITESPACE or rc == CharacterClass.WHITESPACE) else 0.0

    containing_types = {s.type for s in features.structural_context.containing_spans}
    technical = "technical" in containing_types
    atomic = "atomic" in containing_types
    protection_penalty = -30.0 if (technical or atomic) else 0.0  # strongest-only, NOT additive

    is_internal = features.punctuation_sequence_state == PunctuationSequenceState.INTERNAL
    sequence_penalty = -20.0 if is_internal else 0.0

    score = base + transition_bonus + whitespace_bonus + protection_penalty + sequence_penalty

    breakdown = {
        "boundary_class": boundary_class,
        "base": base,
        "transition_bonus": transition_bonus,
        "transition_label": transition_label,
        "whitespace_bonus": whitespace_bonus,
        "technical": technical,
        "atomic": atomic,
        "protection_penalty": protection_penalty,
        "is_internal": is_internal,
        "sequence_penalty": sequence_penalty,
        "score": score,
    }
    return boundary_class, score, breakdown


def dump(text: str, label: str = ""):
    analysis = analyze_text_structure(text)
    candidates = observe_boundaries(analysis)
    print(f"### {label}")
    print(f"text = {text!r}  (len={len(text)})")
    for c in candidates:
        bclass, score, bd = calibration_score(c)
        containing = [f"{s.type}/{s.subtype}" for s in c.features.structural_context.containing_spans]
        print(
            f"  pos={c.position:3d}  L={c.left_char!r:>6s} R={c.right_char!r:>6s}  "
            f"LC={c.features.left_character_class.value:<10s} RC={c.features.right_character_class.value:<10s}  "
            f"seq_state={c.features.punctuation_sequence_state.value:<8s}  "
            f"sf_evidence={c.features.contains_sentence_final_punctuation!s:<5s}  "
            f"containing={containing}  "
            f"class={bclass.value:<14s} base={bd['base']:5.1f}  "
            f"trans={bd['transition_bonus']:4.1f}({bd['transition_label']})  "
            f"ws={bd['whitespace_bonus']:4.1f}  "
            f"tech={bd['technical']!s:<5s} atomic={bd['atomic']!s:<5s} "
            f"protection={bd['protection_penalty']:5.1f}  "
            f"internal={bd['is_internal']!s:<5s} seqpen={bd['sequence_penalty']:5.1f}  "
            f"SCORE={score:6.1f}"
        )
    print()
    return analysis, candidates


if __name__ == "__main__":
    print("=" * 100)
    print("PHASE 2C PROTECTION CALIBRATION ROUND 1 - RAW PIPELINE DUMP")
    print("(strongest-only Technical/Atomic protection; INTERNAL independent)")
    print("=" * 100)
    print()

    cases = [
        # ---- P01: plain OTHER baseline (search a few known-clean texts) ----
        ("P01_a", "中文中文"),
        ("P01_b", "首先，我們介紹 CPU，接著再看 GPU。"),
        # ---- P02: technical OTHER ----
        ("P02", "這個數值是 1,000，接下來我們繼續。"),
        # ---- P03: atomic OTHER / P04: technical+atomic same candidate ----
        ("P03_P04", "目前版本是 v1.2.3，接下來介紹新版。"),
        # ---- P05/P06/P07/P14/P15: transition-only and CLAUSE-only reference candidates ----
        ("P05_transition_only", "中文English"),
        ("P06_P15_clause_only", "首先，我們介紹 CPU，接著再看 GPU。"),
        # ---- P08/P09/P10: INTERNAL reference candidate (CJK ellipsis, clean) ----
        ("P08_P09_P10_internal", "這個問題嘛……接下來再討論。"),
        # ---- P11/P12 reachability probes: does Technical or Atomic ever
        # co-occur with PunctuationSequenceState.INTERNAL on the same
        # candidate? These are diagnostic reachability probes, not
        # manufactured production candidates - they use plausible realistic
        # text shapes to test whether the combination exists at all before
        # concluding CASE ISSUE. ----
        ("P11_probe_url_ellipsis", "請參考 http://example.com/a...b 這個頁面。"),
        ("P11_probe_version_ellipsis", "版本是 v1...2 這樣寫嗎。"),
        ("P12_probe_number_ellipsis", "數值是 100...200 這個範圍。"),
        ("P12_probe_decimal_then_ellipsis_touching", "數值是 3.14......接下來。"),
        ("P12_probe_malformed_decimal_double_dot", "數值是 3..14 接下來。"),
        ("P12_probe_malformed_decimal_quad_dot", "數值是 3....14 接下來。"),
    ]

    for entry in cases:
        case_id, text = entry
        dump(text, case_id)
