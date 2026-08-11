"""Phase 1 Behavioral Verification script for pptx2video's text_structure module.

USAGE
-----
Run it from anywhere inside your local pptx2video checkout - the repo root
(next to `src/` and `tests/`), a `scripts/` subfolder, or any other
subdirectory:

    python verify_phase1.py

It auto-detects the repo root by walking upward from both this script's own
location and the current working directory, looking for a folder that
contains `src/text_structure.py`. If that search fails (e.g. the script was
copied outside the repo entirely), pass the repo root explicitly as the
first argument:

    python verify_phase1.py D:\\WorkingCopy\\pptx2video

It imports `analyze_text_structure` / `_iter_all_spans` directly from
`src/text_structure.py` (read-only - this script never modifies any file in
the repo) and:

  1. Runs the full case corpus (groups A-K, 109 cases) used in the Phase 1
     Behavioral Verification rounds, printing the full span tree (including
     nested children, context_flags, and diagnostics) for every case.
  2. Checks offset integrity for every span in every case
     (span.text == source_text[span.start:span.end], with valid bounds).
  3. Checks the C-2 "direct children of the same span never overlap"
     invariant for every case (checked on `.children` groups only - NOT on
     the top-level span list, since a span that loses the structural-
     nesting contest is expected to surface as an independent top-level
     span that can geometrically overlap another top-level span - see the
     module docstring's "Structural containment vs. geometric containment"
     section).
  4. Prints a final PASS/FAIL summary for both checks across the whole
     corpus.

No third-party dependency is required - standard library only.
"""

import sys
import os


def _find_repo_root(start_dirs):
    """Walk upward from each of `start_dirs` looking for a directory that
    contains `src/text_structure.py`. Returns the first match, or None.
    This lets the script work whether it's placed at the repo root, in a
    `scripts/` subfolder, or anywhere else inside the checkout.
    """
    for start in start_dirs:
        current = os.path.abspath(start)
        while True:
            if os.path.isfile(os.path.join(current, "src", "text_structure.py")):
                return current
            parent = os.path.dirname(current)
            if parent == current:  # reached filesystem root
                break
            current = parent
    return None


if len(sys.argv) > 1:
    REPO_ROOT = sys.argv[1]
else:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    REPO_ROOT = _find_repo_root([script_dir, os.getcwd()])
    if REPO_ROOT is None:
        # Fall back to the script's own directory so the error message
        # below at least reports a sensible path.
        REPO_ROOT = script_dir

sys.path.insert(0, REPO_ROOT)

try:
    from src.text_structure import analyze_text_structure, _iter_all_spans
except ImportError as exc:
    sys.exit(
        "Could not import src.text_structure from "
        f"{REPO_ROOT!r}. Run this script from anywhere inside your "
        "pptx2video repo checkout, or pass the repo root explicitly:\n"
        "    python verify_phase1.py D:\\WorkingCopy\\pptx2video\n"
        f"(underlying error: {exc})"
    )


def dump_span(span, indent=0):
    pad = "  " * indent
    lines = []
    lines.append(f"{pad}type: {span.structural_type}")
    lines.append(f"{pad}subtype: {span.subtype}")
    lines.append(f"{pad}text: {span.text!r}")
    lines.append(f"{pad}start: {span.start}")
    lines.append(f"{pad}end: {span.end}")
    lines.append(f"{pad}source: {span.source}")
    lines.append(f"{pad}context_flags: {sorted(span.context_flags)}")
    lines.append(f"{pad}attributes: {dict(span.attributes)}")
    if span.children:
        lines.append(f"{pad}children:")
        for c in span.children:
            lines.extend(dump_span(c, indent + 2))
    else:
        lines.append(f"{pad}children: none")
    return lines


def check_offset_integrity(text, result):
    """Returns a list of (span, expected_text) mismatches; empty = PASS."""
    mismatches = []
    for span in _iter_all_spans(result.spans):
        expected = text[span.start:span.end]
        if span.text != expected or not (0 <= span.start < span.end <= len(text)):
            mismatches.append((span, expected))
    return mismatches


def check_children_non_overlap(result):
    """Returns a list of (parent_span, child_a, child_b) violations; empty = PASS.

    Only checks each span's own direct `.children` against each other -
    deliberately does NOT check the top-level span list against itself
    (top-level spans are allowed to overlap; see module docstring).
    """
    violations = []

    def walk(spans):
        for s in spans:
            ordered = sorted(s.children, key=lambda c: c.start)
            for i in range(len(ordered) - 1):
                if ordered[i].end > ordered[i + 1].start:
                    violations.append((s, ordered[i], ordered[i + 1]))
            walk(s.children)

    walk(result.spans)
    return violations


def run_case(label, text, log):
    log("=" * 100)
    log(f"CASE: {label}")
    log(f"TEXT: {text!r}")
    result = analyze_text_structure(text)
    if not result.spans:
        log("SPANS: none")
    else:
        for span in result.spans:
            log("-" * 60)
            for line in dump_span(span):
                log(line)
    if result.diagnostics:
        log("DIAGNOSTICS:")
        for d in result.diagnostics:
            log(f"  - {d}")
    else:
        log("DIAGNOSTICS: none")

    offset_mismatches = check_offset_integrity(text, result)
    if offset_mismatches:
        log("OFFSET INTEGRITY: FAIL")
        for span, expected in offset_mismatches:
            log(f"  span={span.text!r} start={span.start} end={span.end} expected={expected!r}")
    else:
        log("OFFSET INTEGRITY: PASS")

    overlap_violations = check_children_non_overlap(result)
    if overlap_violations:
        log("CHILDREN NON-OVERLAP: FAIL")
        for parent, a, b in overlap_violations:
            log(
                f"  under {parent.text!r}: {a.text!r} [{a.start},{a.end}) "
                f"overlaps {b.text!r} [{b.start},{b.end})"
            )
    else:
        log("CHILDREN NON-OVERLAP: PASS")

    log("")
    return result, offset_mismatches, overlap_violations


GROUPS = {}

GROUPS["A - ASCII Apostrophe"] = [
    ("A1", "It's a good idea."),
    ("A2", "John's PowerPoint is ready."),
    ("A3", "The user's subtitle is correct."),
    ("A4", "Users' requirements are different."),
    ("A5", "don't won't can't"),
    ("A6", "rock'n'roll"),
]

GROUPS["B - ASCII Double Quote"] = [
    ("B1", 'He said "hello".'),
    ("B2", 'The "subtitle" is correct.'),
    ("B3", '"Hello world"'),
    ("B4", '5" display'),
    ("B5", '4" HDMI cable'),
    ("B6", 'The value is "4K@60Hz".'),
]

GROUPS["C - CJK Paired Delimiters"] = [
    ("C1", "這是「一個測試」。"),
    ("C2", "這是「一個（巢狀）測試」。"),
    ("C3", "這是《PPTX2Video》專案。"),
    ("C4", "這是（PMIC）的例子。"),
    ("C5", "這是（MT8395）的例子。"),
    ("C6", "「這是『巢狀引用』的測試」"),
]

GROUPS["D - Technical Abbreviations"] = [
    (f"D-{w}", w) for w in
    ["PMIC", "SoC", "MCU", "MPU", "CPU", "GPU", "HDMI", "USB", "BSP", "SDK", "API",
     "DDR", "MIPI", "I2C", "SPI", "UART", "CAN", "PCIe"]
]

GROUPS["E - Technical Tokens With Clear Format"] = [
    (f"E-{i}", w) for i, w in enumerate([
        "MT8395", "S805X3-B", "v0.10.0", "v1.2", "Python 3.13.2", "USB 3.2", "HDMI 2.1",
        "4K@60Hz", "global_scale_correction", "find_best_offset_seconds()", "--export-video",
        "python -m pptx2video", "src/subtitle_segmenter.py", r"D:\WorkingCopy\pptx2video\src",
        "https://example.com", "support@example.com",
    ], 1)
]

GROUPS["F - Emoji"] = [
    ("F1", "這個真的很好 😂"),
    ("F2", "這個真的很好 👍"),
    ("F3", "太好了 ❤️"),
    ("F4", "完成了 🔥"),
    ("F5", "😂"),
    ("F6", "👍"),
    ("F7", "❤️"),
    ("F8", "這個真的很好😂！"),
    ("F9", "😂！"),
]

GROUPS["G - Emoticon"] = [
    ("G1", "這個真的很好 XD"),
    ("G2", "這個真的很好 ^_^"),
    ("G3", "這個真的很好 T_T"),
    ("G4", "這個真的很好 >_<"),
    ("G5", "這個真的很好 @@"),
    ("G6", "這個真的很好 orz"),
    ("G7", "XD"),
    ("G8", "^_^"),
    ("G9", "T_T"),
    ("G10", ">_<"),
    ("G11", "@@"),
    ("G12", "orz"),
    ("G13", "SIXDIGIT"),
    ("G14", "ORZ"),
    ("G15", "xd"),
]

GROUPS["H - Punctuation Sequences"] = [
    ("H1", "……"),
    ("H2", "..."),
    ("H3", "....."),
    ("H4", "？！"),
    ("H5", "！？"),
    ("H6", "！！！"),
    ("H7", "？？？"),
    ("H8", "……？"),
    ("H9", "……！"),
    ("H10", "真的……？"),
    ("H11", "真的……！"),
    ("H12", "What...?"),
    ("H13", "Really?!"),
]

GROUPS["I - Mixed Chinese / English"] = [
    ("I1", "這個 PMIC 可以控制 SoC 的電源。"),
    ("I2", "我們使用 MediaTek Genio 1200 搭配 Linux kernel。"),
    ("I3", "這個平台支援 4K@60Hz HDMI output。"),
    ("I4", "使用 Python 3.13.2 執行 subtitle segmentation。"),
    ("I5", "這個功能真的很好 XD，可以直接使用。"),
    ("I6", "這個功能真的很好 😂，可以直接使用。"),
    ("I7", "這個功能真的很好（笑），可以直接使用。"),
    ("I8", "真的……？這樣就完成了。"),
    ("I9", "我們使用（MT8395）作為 platform。"),
    ("I10", "我們使用（PMIC）控制 power rail。"),
]

GROUPS["J - Structural Span vs Semantic Unit"] = [
    ("J1", "MediaTek Genio 1200"),
    ("J2", "Power Management IC"),
    ("J3", "Linux kernel"),
    ("J4", "subtitle segmentation engine"),
]

GROUPS["K - Context Flags"] = [
    ("K1", "XD"),
    ("K2", "這很好 XD"),
    ("K3", "這很好 XD！"),
    ("K4", "XD architecture"),
    ("K5", "😂！"),
    ("K6", "這很好 😂！"),
]

# Correction-round (C-1/C-2/C-3) focus cases not already covered above by an
# identical string - kept as a separate group so the original A-K corpus
# stays exactly reproducible on its own, while still letting a single run
# of this script cover the correction-specific cases too.
GROUPS["L - C1/C2/C3 Correction Focus Cases"] = [
    ("L1", "。XD"),
    ("L2", "這很好 XD，可以"),
    ("L3", "PPTX2Video"),
    ("L4", "S805X3-B"),
    ("L5", "find_best_offset_seconds()"),
    ("L6", "（PMIC）"),
    ("L7", "「這是（MT8395）的例子」"),
    ("L8", "5\" and 6\" display"),
    ("L9", 'She said "hi" and he said "bye".'),
    ("L10", 'He said "hello.'),
    ("L11", '「He said "hi" to me」'),
]


def main():
    out_path = os.path.join(os.getcwd(), "verify_phase1_output.txt")
    lines = []

    def log(msg=""):
        lines.append(msg)

    total_cases = 0
    offset_fail_cases = []
    overlap_fail_cases = []

    for group_name, cases in GROUPS.items():
        log("#" * 100)
        log(f"GROUP {group_name}")
        log("#" * 100)
        for label, text in cases:
            total_cases += 1
            _, offset_mismatches, overlap_violations = run_case(label, text, log)
            if offset_mismatches:
                offset_fail_cases.append(label)
            if overlap_violations:
                overlap_fail_cases.append(label)

    log("=" * 100)
    log("ALL DONE")

    output_text = "\n".join(lines)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output_text)

    # Print full output to stdout as well (so `python verify_phase1.py |
    # less` / redirection both work), followed by a short summary.
    print(output_text)
    print()
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"Total cases run: {total_cases}")
    print(f"Offset integrity: {'PASS' if not offset_fail_cases else 'FAIL'} "
          f"({total_cases - len(offset_fail_cases)}/{total_cases})")
    if offset_fail_cases:
        print(f"  Failing cases: {', '.join(offset_fail_cases)}")
    print(f"Children non-overlap invariant: {'PASS' if not overlap_fail_cases else 'FAIL'} "
          f"({total_cases - len(overlap_fail_cases)}/{total_cases})")
    if overlap_fail_cases:
        print(f"  Failing cases: {', '.join(overlap_fail_cases)}")
    print()
    print(f"Full per-case output written to: {out_path}")


if __name__ == "__main__":
    main()
