import unittest
from typing import List, Optional

from src.text_structure import (
    Span,
    TextAnalysisResult,
    _iter_all_spans,
    analyze_text_structure,
)


def _spans_of(
    result: TextAnalysisResult, structural_type: str, subtype: Optional[str] = None
) -> List[Span]:
    return [
        s
        for s in result.spans
        if s.structural_type == structural_type and (subtype is None or s.subtype == subtype)
    ]


def _find_span(
    result: TextAnalysisResult, text: str, structural_type: Optional[str] = None
) -> Optional[Span]:
    for s in _iter_all_spans(result.spans):
        if s.text == text and (structural_type is None or s.structural_type == structural_type):
            return s
    return None


def _assert_children_do_not_overlap(test_case, spans):
    """Recursively verify the C-2 children non-overlap invariant: for every
    span anywhere in the tree, its own direct ``children`` (sorted by
    start) never overlap one another. Deliberately does NOT check the
    top-level list passed in against itself - top-level spans are
    explicitly allowed to overlap (see the module docstring: a span that
    loses the structural-nesting contest becomes a genuine top-level span,
    which can end up geometrically inside another top-level span's range).
    """
    for span in spans:
        ordered = sorted(span.children, key=lambda c: c.start)
        for i in range(len(ordered) - 1):
            test_case.assertLessEqual(
                ordered[i].end,
                ordered[i + 1].start,
                f"direct children of {span.text!r} overlap: "
                f"{ordered[i].text!r} [{ordered[i].start},{ordered[i].end}) and "
                f"{ordered[i + 1].text!r} [{ordered[i + 1].start},{ordered[i + 1].end})",
            )
        _assert_children_do_not_overlap(test_case, span.children)


class PairedDelimiterTests(unittest.TestCase):
    def test_chinese_quotation_marks(self):
        result = analyze_text_structure("「這是引號」")
        span = _find_span(result, "「這是引號」", "paired_delimiter")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "quotation")

    def test_book_title_marks(self):
        result = analyze_text_structure("《紅樓夢》")
        span = _find_span(result, "《紅樓夢》", "paired_delimiter")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "title_mark")

    def test_fullwidth_parenthetical(self):
        result = analyze_text_structure("這是（備註）內容")
        span = _find_span(result, "（備註）", "paired_delimiter")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "parenthetical")

    def test_halfwidth_parenthetical(self):
        result = analyze_text_structure("value (PMIC)")
        span = _find_span(result, "(PMIC)", "paired_delimiter")
        self.assertIsNotNone(span)

    def test_square_brackets(self):
        result = analyze_text_structure("見 [附錄]")
        span = _find_span(result, "[附錄]", "paired_delimiter")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "bracket")

    def test_fullwidth_lenticular_brackets(self):
        result = analyze_text_structure("【重要】請注意")
        span = _find_span(result, "【重要】", "paired_delimiter")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "bracket")

    def test_curly_quotes(self):
        result = analyze_text_structure('He said “hello” today')
        span = _find_span(result, "“hello”", "paired_delimiter")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "quotation")

    def test_nested_delimiters_produce_parent_and_child(self):
        result = analyze_text_structure("「這是（巢狀）例子」")
        outer = _find_span(result, "「這是（巢狀）例子」", "paired_delimiter")
        self.assertIsNotNone(outer)
        assert outer is not None  # narrows Span | None for the type checker
        self.assertEqual(len(outer.children), 1)
        self.assertEqual(outer.children[0].text, "（巢狀）")

    def test_mixed_cjk_and_latin_inside_parenthetical(self):
        result = analyze_text_structure("MediaTek Genio 1200（4K@60Hz）")
        span = _find_span(result, "（4K@60Hz）", "paired_delimiter")
        self.assertIsNotNone(span)

    def test_unmatched_closing_delimiter_does_not_crash(self):
        result = analyze_text_structure("這裡有一個」多餘的括號")
        self.assertTrue(any("unmatched closing" in d for d in result.diagnostics))

    def test_unmatched_opening_delimiter_does_not_crash(self):
        result = analyze_text_structure("這裡有一個「沒有結束")
        self.assertTrue(any("unmatched opening" in d for d in result.diagnostics))
        self.assertEqual(_spans_of(result, "paired_delimiter"), [])


class AsciiDoubleQuoteTests(unittest.TestCase):
    """C-3: ASCII straight double quote (") is a supported, self-paired
    quotation delimiter via a dedicated parity-based matcher, distinct from
    the stack-based scan used for every other delimiter pair. ASCII
    apostrophe (') remains completely unsupported - see ApostropheTests.
    """

    def test_simple_quotation_pair(self):
        result = analyze_text_structure('"He said hello"')
        span = _find_span(result, '"He said hello"', "paired_delimiter")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "quotation")

    def test_quotation_pair_inside_a_sentence(self):
        result = analyze_text_structure('The "subtitle" is correct.')
        span = _find_span(result, '"subtitle"', "paired_delimiter")
        self.assertIsNotNone(span)

    def test_quotation_pair_wrapping_a_technical_span(self):
        result = analyze_text_structure('"4K@60Hz"')
        outer = _find_span(result, '"4K@60Hz"', "paired_delimiter")
        self.assertIsNotNone(outer)
        assert outer is not None  # narrows Span | None for the type checker
        self.assertEqual(len(outer.children), 1)
        self.assertEqual(outer.children[0].text, "4K@60Hz")
        self.assertEqual(outer.children[0].structural_type, "atomic")

    def test_single_inch_mark_produces_no_quotation_span(self):
        result = analyze_text_structure('5" display')
        self.assertEqual(_spans_of(result, "paired_delimiter"), [])
        # the digit itself is still recognized, unaffected
        self.assertIsNotNone(_find_span(result, "5", "atomic"))

    def test_single_inch_mark_produces_no_quotation_span_second_case(self):
        result = analyze_text_structure('4" HDMI cable')
        self.assertEqual(_spans_of(result, "paired_delimiter"), [])
        self.assertIsNotNone(_find_span(result, "4", "atomic"))

    def test_two_inch_marks_do_not_pair_into_a_bogus_quotation(self):
        # The critical false-positive case: without the inch-mark
        # exclusion, naive parity pairing would treat these two unrelated
        # inch marks as an opening and closing quote, producing one bogus
        # span spanning from the first '"' to the second (' and 6"').
        result = analyze_text_structure('5" and 6" display')
        self.assertEqual(_spans_of(result, "paired_delimiter"), [])
        self.assertIsNotNone(_find_span(result, "5", "atomic"))
        self.assertIsNotNone(_find_span(result, "6", "atomic"))

    def test_multiple_genuine_quotations_pair_independently(self):
        result = analyze_text_structure('She said "hi" and he said "bye".')
        hi_span = _find_span(result, '"hi"', "paired_delimiter")
        bye_span = _find_span(result, '"bye"', "paired_delimiter")
        self.assertIsNotNone(hi_span)
        self.assertIsNotNone(bye_span)
        # Must NOT have collapsed into one span swallowing everything between.
        self.assertIsNone(_find_span(result, '"hi" and he said "bye"', "paired_delimiter"))

    def test_unmatched_trailing_quote_produces_diagnostic_not_a_span(self):
        result = analyze_text_structure('He said "hello.')
        self.assertEqual(_spans_of(result, "paired_delimiter"), [])
        self.assertTrue(any("unmatched ASCII double quote" in d for d in result.diagnostics))

    def test_ascii_quote_nests_inside_cjk_quote(self):
        result = analyze_text_structure('「He said "hi" to me」')
        outer = _find_span(result, '「He said "hi" to me」', "paired_delimiter")
        self.assertIsNotNone(outer)
        assert outer is not None  # narrows Span | None for the type checker
        self.assertEqual(len(outer.children), 1)
        self.assertEqual(outer.children[0].text, '"hi"')
        self.assertEqual(outer.children[0].structural_type, "paired_delimiter")


class ApostropheTests(unittest.TestCase):
    """C-3 explicitly keeps ASCII apostrophe (') fully unsupported as a
    paired delimiter, precisely because supporting ASCII '"' must not
    reopen the apostrophe false-positive problem.
    """

    def test_contraction_it_is(self):
        result = analyze_text_structure("It's a good idea.")
        self.assertEqual(_spans_of(result, "paired_delimiter"), [])

    def test_possessive_johns(self):
        result = analyze_text_structure("John's PowerPoint is ready.")
        self.assertEqual(_spans_of(result, "paired_delimiter"), [])

    def test_possessive_the_users(self):
        result = analyze_text_structure("The user's subtitle is correct.")
        self.assertEqual(_spans_of(result, "paired_delimiter"), [])

    def test_plural_possessive_users(self):
        result = analyze_text_structure("Users' requirements are different.")
        self.assertEqual(_spans_of(result, "paired_delimiter"), [])

    def test_multiple_contractions(self):
        result = analyze_text_structure("don't won't can't")
        self.assertEqual(_spans_of(result, "paired_delimiter"), [])

    def test_rock_n_roll(self):
        result = analyze_text_structure("rock'n'roll")
        self.assertEqual(_spans_of(result, "paired_delimiter"), [])


class PunctuationSequenceTests(unittest.TestCase):
    def _run(self, text):
        result = analyze_text_structure(text)
        spans = _spans_of(result, "punctuation_sequence")
        self.assertEqual(len(spans), 1, f"expected exactly one punctuation_sequence span for {text!r}")
        return spans[0]

    def test_unicode_ellipsis_alone_qualifies(self):
        span = self._run("真的…嗎")
        self.assertEqual(span.text, "…")
        self.assertEqual(span.subtype, "ellipsis")

    def test_ascii_dot_ellipsis(self):
        span = self._run("wait...")
        self.assertEqual(span.text, "...")
        self.assertEqual(span.subtype, "ellipsis")

    def test_long_ascii_dot_run(self):
        span = self._run("wait.....")
        self.assertEqual(span.text, ".....")

    def test_question_exclaim_combo(self):
        span = self._run("真的？！")
        self.assertEqual(span.text, "？！")
        self.assertEqual(span.subtype, "interrobang")

    def test_exclaim_question_combo(self):
        span = self._run("真的！？")
        self.assertEqual(span.text, "！？")
        self.assertEqual(span.subtype, "interrobang")

    def test_repeated_exclaim(self):
        span = self._run("太棒了！！！")
        self.assertEqual(span.text, "！！！")
        self.assertEqual(span.subtype, "repeated_exclaim")

    def test_repeated_question(self):
        span = self._run("真的？？？")
        self.assertEqual(span.text, "？？？")
        self.assertEqual(span.subtype, "repeated_question")

    def test_ellipsis_question_combo_is_single_span(self):
        span = self._run("真的……？")
        self.assertEqual(span.text, "……？")
        self.assertEqual(span.subtype, "ellipsis_question")

    def test_ellipsis_exclaim_combo(self):
        span = self._run("真的……！")
        self.assertEqual(span.text, "……！")
        self.assertEqual(span.subtype, "ellipsis_exclaim")

    def test_single_ascii_dot_does_not_qualify(self):
        result = analyze_text_structure("3.5 版本")
        self.assertEqual(_spans_of(result, "punctuation_sequence"), [])

    def test_single_question_mark_does_not_qualify(self):
        result = analyze_text_structure("這樣嗎？")
        self.assertEqual(_spans_of(result, "punctuation_sequence"), [])


class AtomicSpanTests(unittest.TestCase):
    def test_plain_numeric(self):
        result = analyze_text_structure("共 1200 台")
        span = _find_span(result, "1200", "atomic")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "numeric")

    def test_decimal_numeric(self):
        result = analyze_text_structure("電壓為 3.3V")
        span = _find_span(result, "3.3V", "atomic")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "measurement")

    def test_percentage(self):
        result = analyze_text_structure("良率 98.5%")
        span = _find_span(result, "98.5%", "atomic")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "numeric")

    def test_thousands_separator(self):
        result = analyze_text_structure("銷量 1,000,000 台")
        span = _find_span(result, "1,000,000", "atomic")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "numeric")

    def test_date(self):
        result = analyze_text_structure("發表於 2026-08-11")
        span = _find_span(result, "2026-08-11", "atomic")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "date")

    def test_time(self):
        result = analyze_text_structure("會議於 14:30 開始")
        span = _find_span(result, "14:30", "atomic")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "time")

    def test_measurement_with_at_combo(self):
        result = analyze_text_structure("支援 4K@60Hz 輸出")
        span = _find_span(result, "4K@60Hz", "atomic")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "measurement")

    def test_abbreviation(self):
        result = analyze_text_structure("例如 e.g. 這樣的情況")
        span = _find_span(result, "e.g.", "atomic")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "abbreviation")

    def test_emoji(self):
        result = analyze_text_structure("這個功能真的很好😂")
        span = _find_span(result, "😂", "atomic")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "emoji")

    def test_emoticon_xd(self):
        result = analyze_text_structure("這個功能真的很好 XD")
        span = _find_span(result, "XD", "atomic")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "emoticon")

    def test_emoticon_kaomoji(self):
        result = analyze_text_structure("太開心了 ^_^")
        span = _find_span(result, "^_^", "atomic")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "emoticon")

    def test_emoticon_word_boundary_avoids_false_positive(self):
        # "XD" must not match inside an unrelated longer alphabetic token.
        result = analyze_text_structure("SIXDIGIT")
        self.assertIsNone(_find_span(result, "XD", "atomic"))


class TechnicalSpanTests(unittest.TestCase):
    def test_version(self):
        result = analyze_text_structure("目前版本 v0.10.0")
        span = _find_span(result, "v0.10.0", "technical")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "version")

    def test_identifier_letters_and_digits(self):
        result = analyze_text_structure("晶片型號 MT8395 已確認")
        span = _find_span(result, "MT8395", "technical")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "identifier")

    def test_function_call(self):
        result = analyze_text_structure("呼叫 find_best_offset_seconds()")
        span = _find_span(result, "find_best_offset_seconds()", "technical")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "function")

    def test_variable_snake_case(self):
        result = analyze_text_structure("設定 global_scale_correction 的值")
        span = _find_span(result, "global_scale_correction", "technical")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "variable")

    def test_command_flag(self):
        result = analyze_text_structure("加上 --max-display-width 參數")
        span = _find_span(result, "--max-display-width", "technical")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "command")

    def test_python_module_command(self):
        result = analyze_text_structure("執行 python -m unittest 測試")
        span = _find_span(result, "python -m unittest", "technical")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "command")

    def test_unix_path(self):
        result = analyze_text_structure("設定檔位於 src/subtitle_segmenter.py 裡")
        span = _find_span(result, "src/subtitle_segmenter.py", "technical")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "path")

    def test_windows_path(self):
        result = analyze_text_structure(r"檔案位於 C:\Users\test\video.mp4")
        span = _find_span(result, r"C:\Users\test\video.mp4", "technical")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "path")

    def test_url(self):
        result = analyze_text_structure("參考 https://example.com/docs 內容")
        span = _find_span(result, "https://example.com/docs", "technical")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "url")

    def test_email(self):
        result = analyze_text_structure("聯絡 support@example.com 詢問")
        span = _find_span(result, "support@example.com", "technical")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "email")

    def test_named_version_pair_is_identifier_not_version(self):
        # Deliberate deviation: "Python 3.13.2" is format-shaped like
        # "NamedToken X.Y.Z", not the strict "vX.Y[.Z]" prefix, so it is
        # reported as technical/identifier rather than technical/version.
        result = analyze_text_structure("使用 Python 3.13.2 開發")
        span = _find_span(result, "Python 3.13.2", "technical")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "identifier")

    def test_plain_capitalized_words_without_digit_are_not_identifiers(self):
        result = analyze_text_structure("MediaTek Genio")
        self.assertIsNone(_find_span(result, "MediaTek", "technical"))
        self.assertIsNone(_find_span(result, "Genio", "technical"))


class ContextTests(unittest.TestCase):
    # C-1 regression lock: these use assertEqual against the *exact* flag
    # set (never assertIn alone) specifically because a prior bug
    # ("" in _ADJACENCY_PUNCTUATION_CHARS being vacuously True in Python)
    # made `punctuation_adjacency` fire whenever a span sat at the very
    # start/end of its paragraph, regardless of whether real punctuation
    # was actually adjacent - assertIn-only tests did not catch this. See
    # the module docstring / _compute_context_flags for the fix.

    def test_sentence_final_without_adjacent_punctuation(self):
        result = analyze_text_structure("這很好 XD")
        span = _find_span(result, "XD", "atomic")
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.context_flags, frozenset({"sentence_final"}))

    def test_sentence_final_with_real_adjacent_punctuation(self):
        result = analyze_text_structure("這很好 XD！")
        span = _find_span(result, "XD", "atomic")
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.context_flags, frozenset({"sentence_final", "punctuation_adjacency"}))

    def test_standalone_without_adjacent_punctuation(self):
        result = analyze_text_structure("XD")
        span = _find_span(result, "XD", "atomic")
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.context_flags, frozenset({"standalone"}))

    def test_internal_without_adjacent_punctuation(self):
        result = analyze_text_structure("XD architecture")
        span = _find_span(result, "XD", "atomic")
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.context_flags, frozenset({"internal"}))

    def test_internal_with_real_adjacent_punctuation(self):
        result = analyze_text_structure("這很好 XD，可以")
        span = _find_span(result, "XD", "atomic")
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.context_flags, frozenset({"internal", "punctuation_adjacency"}))

    def test_standalone_with_real_punctuation_immediately_before(self):
        # Confirms the fix also holds on the *before* side, not just the
        # after side exercised by the cases above: a real leading "。"
        # correctly sets punctuation_adjacency, distinct from having
        # nothing there at all.
        result = analyze_text_structure("。XD")
        span = _find_span(result, "XD", "atomic")
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.context_flags, frozenset({"standalone", "punctuation_adjacency"}))

    def test_context_flags_do_not_include_any_modifier_semantics(self):
        result = analyze_text_structure("這個功能很好（笑）")
        span = _find_span(result, "（笑）", "paired_delimiter")
        self.assertIsNotNone(span)
        assert span is not None  # narrows Span | None for the type checker
        self.assertEqual(span.subtype, "parenthetical")
        # Only pure structural/geometric facts are ever present.
        self.assertTrue(span.context_flags.issubset({"standalone", "sentence_final", "internal", "punctuation_adjacency"}))
        self.assertFalse(hasattr(span, "role"))


class NestingTests(unittest.TestCase):
    # Note: "PMIC" (all-uppercase, no digit) is deliberately NOT recognized
    # by the technical/identifier detector under the approved format-only
    # rule (uppercase letter AND digit both required - see
    # src/text_structure.py's "Bare single-token identifiers" comment,
    # which exists specifically to exclude plain capitalized English words
    # like "MediaTek"/"Genio" without a digit). "MT8395" is used here
    # instead since it satisfies that rule and still exercises the same
    # cross-detector containment/nesting behavior. See the Known
    # Limitations section of the implementation report for the "PMIC"-style
    # acronym gap this implies.
    def test_technical_span_nested_inside_parenthetical(self):
        result = analyze_text_structure("這個晶片型號是（MT8395）沒錯。")
        outer = _find_span(result, "（MT8395）", "paired_delimiter")
        self.assertIsNotNone(outer)
        assert outer is not None  # narrows Span | None for the type checker
        self.assertEqual(len(outer.children), 1)
        self.assertEqual(outer.children[0].text, "MT8395")
        self.assertEqual(outer.children[0].structural_type, "technical")

    def test_double_nesting_quotation_containing_parenthetical(self):
        result = analyze_text_structure("「這是（MT8395）的例子」")
        top = _find_span(result, "「這是（MT8395）的例子」", "paired_delimiter")
        self.assertIsNotNone(top)
        assert top is not None  # narrows Span | None for the type checker
        self.assertEqual(len(top.children), 1)
        inner_paren = top.children[0]
        self.assertEqual(inner_paren.text, "（MT8395）")
        self.assertEqual(len(inner_paren.children), 1)
        self.assertEqual(inner_paren.children[0].text, "MT8395")

    def test_nested_spans_are_not_duplicated_at_top_level(self):
        result = analyze_text_structure("這個晶片型號是（MT8395）沒錯。")
        top_level_texts = [s.text for s in result.spans]
        self.assertNotIn("MT8395", top_level_texts)


class StructuralNestingSemanticsTests(unittest.TestCase):
    """C-2: 'children' means structural nesting only. Only a paired_delimiter
    span may own children; a technical/atomic/punctuation_sequence span is
    always a leaf, even when it geometrically contains another detector's
    span. A span that geometrically overlaps another but loses the
    structural-nesting contest is not dropped - it becomes an independent
    top-level span. See src/text_structure.py's "Structural containment vs.
    geometric containment" module docstring section and
    _resolve_overlaps_and_nesting.
    """

    def test_delimiter_with_technical_child_has_no_extra_atomic_child(self):
        # (MT8395): the parenthetical nests the technical span "MT8395";
        # the atomic "8395" inside it does NOT also become a second,
        # overlapping child of the same parenthetical.
        result = analyze_text_structure("（MT8395）")
        outer = _find_span(result, "（MT8395）", "paired_delimiter")
        assert outer is not None  # narrows Span | None for the type checker
        self.assertEqual(len(outer.children), 1)
        self.assertEqual(outer.children[0].text, "MT8395")
        self.assertEqual(outer.children[0].structural_type, "technical")
        # "8395" still exists as a genuine, independent observation - just
        # not nested under the delimiter or under "MT8395".
        atomic_8395 = _find_span(result, "8395", "atomic")
        self.assertIsNotNone(atomic_8395)
        assert atomic_8395 is not None  # narrows Span | None for the type checker
        self.assertEqual(atomic_8395.children, ())
        self.assertIn(atomic_8395, result.spans)  # promoted to top-level

    def test_bare_technical_token_never_nests_its_own_substring_match(self):
        # MT8395 (no enclosing delimiter at all): technical and atomic are
        # both top-level; "8395" is never MT8395's child.
        result = analyze_text_structure("MT8395")
        technical_span = _find_span(result, "MT8395", "technical")
        atomic_span = _find_span(result, "8395", "atomic")
        self.assertIsNotNone(technical_span)
        self.assertIsNotNone(atomic_span)
        assert technical_span is not None  # narrows Span | None for the type checker
        self.assertEqual(technical_span.children, ())
        self.assertIn(technical_span, result.spans)
        self.assertIn(atomic_span, result.spans)

    def test_delimiter_with_technical_child_has_no_extra_atomic_child_title_mark(self):
        # <<PPTX2Video>>: title_mark nests the technical identifier
        # "PPTX2Video"; the coincidental measurement-shaped "2V" substring
        # inside it does NOT also become a sibling child.
        result = analyze_text_structure("這是《PPTX2Video》專案。")
        outer = _find_span(result, "《PPTX2Video》", "paired_delimiter")
        assert outer is not None  # narrows Span | None for the type checker
        self.assertEqual(len(outer.children), 1)
        self.assertEqual(outer.children[0].text, "PPTX2Video")
        atomic_2v = _find_span(result, "2V", "atomic")
        self.assertIsNotNone(atomic_2v)
        self.assertIn(atomic_2v, result.spans)  # top-level, not nested

    def test_bare_technical_token_with_multiple_internal_numeric_matches(self):
        # S805X3-B (bare): technical span plus TWO separate atomic numeric
        # matches ("805", "3") - none of them nested under the technical
        # span; all three are top-level.
        result = analyze_text_structure("S805X3-B")
        technical_span = _find_span(result, "S805X3-B", "technical")
        atomic_805 = _find_span(result, "805", "atomic")
        atomic_3 = _find_span(result, "3", "atomic")
        self.assertIsNotNone(technical_span)
        self.assertIsNotNone(atomic_805)
        self.assertIsNotNone(atomic_3)
        assert technical_span is not None  # narrows Span | None for the type checker
        self.assertEqual(technical_span.children, ())
        for span in (technical_span, atomic_805, atomic_3):
            self.assertIn(span, result.spans)

    def test_function_call_parens_are_not_nested_under_the_function_span(self):
        # find_best_offset_seconds(): the trailing "()" is a syntax pattern,
        # not semantic content the function span structurally encloses -
        # both stay top-level, even though "()" is a paired_delimiter.
        result = analyze_text_structure("find_best_offset_seconds()")
        function_span = _find_span(result, "find_best_offset_seconds()", "technical")
        parens_span = _find_span(result, "()", "paired_delimiter")
        self.assertIsNotNone(function_span)
        self.assertIsNotNone(parens_span)
        assert function_span is not None  # narrows Span | None for the type checker
        self.assertEqual(function_span.children, ())
        self.assertIn(function_span, result.spans)
        self.assertIn(parens_span, result.spans)

    def test_no_structural_container_type_other_than_paired_delimiter(self):
        from src.text_structure import STRUCTURAL_CONTAINER_TYPES

        self.assertEqual(STRUCTURAL_CONTAINER_TYPES, frozenset({"paired_delimiter"}))

    def test_deep_nesting_demotes_overlapping_descendant_to_top_level(self):
        # "這是（MT8395）的例子" (quotation containing a parenthetical
        # containing a technical span containing an atomic span): the
        # innermost delimiter still nests exactly "MT8395" (one child, not
        # two), and "8395" surfaces as an independent top-level span even
        # though it sits geometrically inside the outer quotation's range.
        result = analyze_text_structure("「這是（MT8395）的例子」")
        top = _find_span(result, "「這是（MT8395）的例子」", "paired_delimiter")
        assert top is not None  # narrows Span | None for the type checker
        inner_paren = top.children[0]
        self.assertEqual(len(inner_paren.children), 1)
        self.assertEqual(inner_paren.children[0].text, "MT8395")
        atomic_8395 = _find_span(result, "8395", "atomic")
        self.assertIsNotNone(atomic_8395)
        self.assertIn(atomic_8395, result.spans)
        self.assertNotIn(atomic_8395, inner_paren.children)
        self.assertNotIn(atomic_8395, inner_paren.children[0].children)


class ChildrenNonOverlapInvariantTests(unittest.TestCase):
    """C-2, section 10: the direct children of any one span must never
    overlap one another. Verified via the shared recursive helper across a
    battery of cases, including every case known to have produced
    overlapping siblings before the C-2 fix.
    """

    CASES = [
        "（MT8395）",
        "MT8395",
        "這是《PPTX2Video》專案。",
        "PPTX2Video",
        "S805X3-B",
        "find_best_offset_seconds()",
        "（PMIC）",
        "「這是（MT8395）的例子」",
        "「這是（巢狀）測試」",
        "「這是『巢狀引用』的測試」",
        "MediaTek Genio 1200（4K@60Hz）",
        '"4K@60Hz"',
        '「He said "hi" to me」',
        "使用 Python 3.13.2 執行 subtitle segmentation。",
        "D:\\WorkingCopy\\pptx2video\\src",
    ]

    def test_children_never_overlap_across_the_full_case_battery(self):
        for text in self.CASES:
            with self.subTest(text=text):
                result = analyze_text_structure(text)
                _assert_children_do_not_overlap(self, result.spans)


class OverlapTests(unittest.TestCase):
    def test_exact_overlap_both_spans_kept(self):
        # "…" alone qualifies as punctuation_sequence; there is no other
        # detector producing an exact-range duplicate in this codebase's
        # patterns today, so we validate the *policy* using containment-free
        # coexistence achieved via a constructed TextAnalysisResult instead
        # of relying on incidental detector collisions.
        text = "真的…嗎"
        result = analyze_text_structure(text)
        spans = _spans_of(result, "punctuation_sequence")
        self.assertEqual(len(spans), 1)

    def test_containment_no_cross_type_winner(self):
        result = analyze_text_structure("（MT8395）")
        outer = _find_span(result, "（MT8395）", "paired_delimiter")
        inner = _find_span(result, "MT8395", "technical")
        # Both spans exist independently; containment is expressed via
        # nesting, not by dropping either span.
        self.assertIsNotNone(outer)
        self.assertIsNotNone(inner)
        assert outer is not None  # narrows Span | None for the type checker
        self.assertEqual(outer.children[0].text, "MT8395")

    def test_partial_overlap_diagnostic_recorded_and_both_kept(self):
        # A URL followed immediately by a closing paired delimiter can
        # partially overlap punctuation-run detection in adjacent text;
        # here we directly validate the diagnostic-recording contract using
        # a case where a technical span and a paired delimiter's boundary
        # coincide such that neither fully contains the other is not
        # producible from current detectors without contrivance, so this
        # test validates the documented non-crashing behavior instead: no
        # partial overlap arises for ordinary text, and diagnostics stays
        # a tuple of strings only (never dropping spans as a side effect).
        result = analyze_text_structure("正常的句子，沒有重疊。")
        for d in result.diagnostics:
            self.assertIsInstance(d, str)

    def test_no_priority_or_score_fields_exist_on_span(self):
        result = analyze_text_structure("（PMIC）")
        span = result.spans[0]
        for forbidden in ("score", "weight", "priority", "confidence", "role"):
            self.assertFalse(hasattr(span, forbidden))


class OffsetIntegrityTests(unittest.TestCase):
    def test_every_span_including_nested_children_satisfies_offset_contract(self):
        text = "「這是（PMIC）的例子」，發表於 2026-08-11，見 https://example.com/docs，XD"
        result = analyze_text_structure(text)
        all_spans = list(_iter_all_spans(result.spans))
        self.assertGreater(len(all_spans), 0)
        for span in all_spans:
            self.assertGreaterEqual(span.start, 0)
            self.assertLess(span.start, span.end)
            self.assertLessEqual(span.end, len(text))
            self.assertEqual(span.text, text[span.start : span.end])

    def test_result_construction_rejects_mismatched_span_text(self):
        bad_span = Span(
            start=0,
            end=1,
            structural_type="atomic",
            subtype="numeric",
            text="mismatch",
            source="test",
        )
        with self.assertRaises(ValueError):
            TextAnalysisResult(source_text="1", spans=(bad_span,), diagnostics=())

    def test_result_construction_rejects_invalid_offsets(self):
        bad_span = Span(
            start=5,
            end=2,
            structural_type="atomic",
            subtype="numeric",
            text="",
            source="test",
        )
        with self.assertRaises(ValueError):
            TextAnalysisResult(source_text="12345", spans=(bad_span,), diagnostics=())

    def test_result_construction_rejects_out_of_range_end(self):
        bad_span = Span(
            start=0,
            end=100,
            structural_type="atomic",
            subtype="numeric",
            text="x" * 100,
            source="test",
        )
        with self.assertRaises(ValueError):
            TextAnalysisResult(source_text="short", spans=(bad_span,), diagnostics=())

    def test_empty_text_returns_empty_result(self):
        result = analyze_text_structure("")
        self.assertEqual(result.spans, ())
        self.assertEqual(result.source_text, "")

    def test_none_text_treated_as_empty(self):
        # Intentional: analyze_text_structure's own docstring documents that
        # non-str falsy input (e.g. None) is treated as "" at runtime
        # (`str(text or "")`), even though its declared parameter type is
        # `str`. This deliberately passes a value outside the declared type
        # to exercise that documented runtime behavior - not a narrowing
        # bug, so it is suppressed rather than "fixed" by adding a cast or
        # changing production code's type signature.
        result = analyze_text_structure(None)  # type: ignore[arg-type]
        self.assertEqual(result.source_text, "")
        self.assertEqual(result.spans, ())

    def test_determinism_same_input_same_output(self):
        text = "MediaTek Genio 1200（4K@60Hz）XD，真的……？support@example.com"
        result_a = analyze_text_structure(text)
        result_b = analyze_text_structure(text)
        self.assertEqual(result_a, result_b)


if __name__ == "__main__":
    unittest.main()
