import unittest

from src.subtitle_segmenter import (
    DEFAULT_MAX_DISPLAY_WIDTH,
    _display_width,
    _normalize_whitespace,
    segment_notes_for_subtitles,
)


class DisplayWidthTests(unittest.TestCase):
    def test_fullwidth_chars_count_as_two_halfwidth_as_one(self):
        # CJK characters and CJK punctuation are East_Asian_Width W/F (2);
        # ASCII letters/digits/punctuation are Na/H (1).
        self.assertEqual(_display_width("測試"), 4)
        self.assertEqual(_display_width("test"), 4)
        self.assertEqual(_display_width("測test"), 6)
        self.assertEqual(_display_width(""), 0)


class NormalizeWhitespaceTests(unittest.TestCase):
    def test_removes_whitespace_between_two_cjk_characters(self):
        self.assertEqual(_normalize_whitespace("你好  世界"), "你好世界")

    def test_removes_fullwidth_space_between_two_cjk_characters(self):
        self.assertEqual(_normalize_whitespace("你好　世界"), "你好世界")

    def test_removes_whitespace_scattered_between_every_cjk_character(self):
        self.assertEqual(_normalize_whitespace("這 是 一 段 話"), "這是一段話")

    def test_collapses_multiple_spaces_between_english_words_to_one(self):
        self.assertEqual(_normalize_whitespace("Hello   world"), "Hello world")

    def test_keeps_single_space_at_cjk_latin_boundary(self):
        self.assertEqual(_normalize_whitespace("這是 word 測試"), "這是 word 測試")

    def test_collapses_extra_spaces_at_cjk_latin_boundary_to_one(self):
        self.assertEqual(_normalize_whitespace("這是   word   測試"), "這是 word 測試")


class SegmentNotesForSubtitlesTests(unittest.TestCase):
    def test_default_width_matches_18_fullwidth_cjk_characters(self):
        # The project owner's requirement is "全形18個字" (18 full-width CJK
        # characters per line), not 18 display-width units - each CJK
        # character is worth 2 display width, so the default must be 36,
        # not 18. An 18-character CJK sentence (width 36) must fit on one
        # line by default; adding one more character (width 38) must not.
        self.assertEqual(DEFAULT_MAX_DISPLAY_WIDTH, 36)

        exactly_18_chars = "測" * 18 + "。"
        segments = segment_notes_for_subtitles(exactly_18_chars)
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["text"], "測" * 18)

        nineteen_chars = "測" * 19 + "。"
        segments = segment_notes_for_subtitles(nineteen_chars)
        self.assertGreater(len(segments), 1)

    def test_empty_or_whitespace_only_text_returns_empty_list(self):
        self.assertEqual(segment_notes_for_subtitles(""), [])
        self.assertEqual(segment_notes_for_subtitles("   \n  \n "), [])
        self.assertEqual(segment_notes_for_subtitles(None), [])

    def test_single_short_sentence_strips_trailing_period(self):
        text = "這是一句測試。"
        segments = segment_notes_for_subtitles(text)

        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["text"], "這是一句測試")
        self.assertEqual(segments[0]["source_start_offset"], 0)
        self.assertEqual(segments[0]["source_end_offset"], len(text))

    def test_keeps_question_and_exclamation_marks(self):
        self.assertEqual(segment_notes_for_subtitles("你好嗎？")[0]["text"], "你好嗎？")
        self.assertEqual(segment_notes_for_subtitles("太棒了！")[0]["text"], "太棒了！")

    def test_merges_short_adjacent_sentences_within_paragraph(self):
        # "好。" (width 2) and "你好。" (width 4) comfortably fit together
        # under the width-20 limit used here, so paragraph-aware merging
        # should combine them into a single line - only the very last
        # punctuation mark (trailing "。") gets stripped, the one in the
        # middle stays as-is since it isn't at the line's own end.
        text = "好。你好。"
        segments = segment_notes_for_subtitles(text, max_display_width=20)

        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["text"], "好。你好")
        self.assertEqual(segments[0]["source_start_offset"], 0)
        self.assertEqual(segments[0]["source_end_offset"], len(text))

    def test_balances_two_lines_instead_of_stranding_a_short_orphan(self):
        # Regression test for real content: greedily maximizing the first
        # line before starting the second used to split the compound word
        # "控制核心" ("control core") apart, stranding "核心" alone on its
        # own line ("...的控制" / "核心"). Rebalancing to even out line
        # widths (still never crossing max_display_width) keeps "控制核心"
        # together and produces two comparably-sized lines instead.
        text = "而是它扮演了整個 Embedded System 的控制核心。"
        segments = segment_notes_for_subtitles(text, max_display_width=32)

        self.assertEqual(len(segments), 2)
        self.assertTrue(any("控制核心" in s["text"] for s in segments))
        for segment in segments:
            self.assertLessEqual(_display_width(segment["text"]), 32)
        # "Balanced" means neither line is drastically shorter than the
        # other - specifically, no line should be under half the width of
        # the other (a loose bound; the old greedy behavior produced a
        # ~26-vs-4 width split here, which this must not reproduce).
        widths = [_display_width(s["text"]) for s in segments]
        self.assertLessEqual(max(widths), 2 * min(widths))

    def test_balances_three_lines_by_overall_evenness_not_just_the_worst_line(self):
        # Regression test for real content: with 4 candidate units of
        # width [16, 10, 10, 28] needing 3 lines, minimizing only the
        # *worst* line picked a 24/8/26 split (max=26) over an available
        # 14/18/26 split (max~28) purely because 26 < 28 - even though
        # the second option is far more evenly distributed and doesn't
        # strand an 8-width line. Balancing by sum-of-squared-widths
        # (rather than just the max) must prefer the more even split.
        text = "它負責接收資訊、分析狀態、做出判斷，再控制整個系統完成各種工作。"
        segments = segment_notes_for_subtitles(text, max_display_width=32)

        self.assertEqual(len(segments), 3)
        widths = [_display_width(s["text"]) for s in segments]
        self.assertLessEqual(max(widths), 2 * min(widths))
        self.assertNotIn(8, widths)

    def test_repeated_ellipsis_does_not_produce_a_punctuation_only_orphan_line(self):
        # Regression test for real content: a Chinese ellipsis is
        # conventionally written as two consecutive "…" characters, both
        # individually in _PRIMARY_BREAK_CHARS. Splitting at every
        # occurrence (rather than the whole run) used to produce a
        # trailing unit containing nothing but the second "…", stranded
        # alone on its own line with no other content
        # ("...印表機…" / "…").
        text = "可能包括牙刷、手錶、耳機、汽車、冷氣、電梯、門禁、咖啡機、印表機……"
        segments = segment_notes_for_subtitles(text)

        self.assertFalse(any(s["text"] == "…" for s in segments))
        self.assertTrue(any(s["text"].endswith("……") for s in segments))

    def test_mixed_question_and_exclamation_marks_are_not_split_apart(self):
        # Same underlying bug, different punctuation combination - "？！"
        # are both primary break characters, and splitting at each one
        # individually would strand the "！" alone right after "？".
        segments = segment_notes_for_subtitles("真的假的？！")

        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["text"], "真的假的？！")

    def test_balancing_does_not_strand_a_single_trailing_character(self):
        # Same bug, different shape: a lone trailing "中" ("in"/"among")
        # used to end up alone on its own line.
        text = "理解 MCU 為什麼會廣泛出現在各種電子產品中。"
        segments = segment_notes_for_subtitles(text, max_display_width=32)

        self.assertFalse(any(s["text"] == "中" for s in segments))

    def test_paragraph_boundary_is_never_crossed_even_when_both_sides_are_short(self):
        # "第一段" (width 6) and "第二段" (width 6) would easily fit
        # together under the width limit, but they're in different
        # paragraphs (separated by a blank line) - paragraphs are a hard
        # boundary, so this must stay two lines, never merged into one.
        text = "第一段。\n\n第二段。"
        segments = segment_notes_for_subtitles(text, max_display_width=20)

        self.assertEqual([s["text"] for s in segments], ["第一段", "第二段"])
        # Offsets should point back at the two paragraph spans, skipping
        # the blank line in between.
        self.assertEqual((segments[0]["source_start_offset"], segments[0]["source_end_offset"]), (0, 4))
        self.assertEqual((segments[1]["source_start_offset"], segments[1]["source_end_offset"]), (6, 10))
        for segment in segments:
            self.assertEqual(
                text[segment["source_start_offset"]:segment["source_end_offset"]].rstrip("。"),
                segment["text"],
            )

    def test_splits_long_sentence_at_secondary_punctuation_when_clauses_dont_fit_together(self):
        # Three comma-separated clauses, each individually under the
        # width-20 limit (16, 16, 12) but no two of them fit together
        # (16+16=32, 16+12=28) - each clause should end up as its own line.
        text = "這是一段測試文字，用來確認斷句效果，看看結果如何。"
        segments = segment_notes_for_subtitles(text, max_display_width=20)

        self.assertEqual(
            [s["text"] for s in segments],
            ["這是一段測試文字", "用來確認斷句效果", "看看結果如何"],
        )
        for segment in segments:
            self.assertLessEqual(_display_width(segment["text"]), 20)
            # Offsets must reconstruct back to a contiguous slice of the
            # original input - this is what Phase 3's alignment will rely
            # on to line these segments up against WordBoundary events.
            self.assertIn(
                segment["text"],
                text[segment["source_start_offset"]:segment["source_end_offset"]],
            )

    def test_hard_split_uses_jieba_token_boundaries_not_raw_character_count(self):
        # Regression test for a real bug found by running this against an
        # actual (longer, more realistic) speaker-notes sample: a
        # character-count-only hard cut split "我們" ("we") into "我" at
        # the end of one line and "們" at the start of the next, because
        # the cut landed exactly at the width limit with no punctuation
        # nearby to break at instead. No comma anywhere in this clause
        # (deliberately, to force the hard-split path), and the width-20
        # cut point falls squarely in the middle of "我們" under a naive
        # per-character count - jieba tokenizing the clause first and only
        # cutting between tokens must avoid that.
        text = "這份簡報要介紹的是我們在今年推出的新產品"
        segments = segment_notes_for_subtitles(text, max_display_width=20)

        combined = "".join(s["text"] for s in segments)
        self.assertEqual(combined, text)
        # "我們" must appear intact within a single segment somewhere,
        # never split into a trailing "我" in one segment followed by a
        # leading "們" in the next.
        self.assertTrue(any("我們" in s["text"] for s in segments))
        self.assertFalse(any(s["text"].endswith("我") for s in segments))

    def test_decimal_point_is_not_treated_as_sentence_ending_punctuation(self):
        # Regression test for a real bug found on actual course-notes
        # content: "." is a primary (sentence-ending) break character for
        # real English/ASCII sentences, but "3.3V" isn't a sentence at
        # all - it's a number. This used to split it into "3" and "3V".
        text = "把市電轉換成 MCU 所需要的 3.3V 或 5V 電源。"
        segments = segment_notes_for_subtitles(text, max_display_width=20)

        combined = "".join(s["text"] for s in segments)
        self.assertIn("3.3V", combined)
        self.assertNotIn("3", [s["text"] for s in segments])

    def test_thousands_separator_comma_is_not_treated_as_clause_punctuation(self):
        # max_display_width=20 forces this to actually go through the
        # split path - at a wider limit the whole sentence fits on one
        # line and this wouldn't exercise the fix being tested here.
        text = "這台設備造價超過 1,000,000 元。"
        segments = segment_notes_for_subtitles(text, max_display_width=20)

        combined = "".join(s["text"] for s in segments)
        self.assertIn("1,000,000", combined)

    def test_hard_splits_long_run_with_no_punctuation_at_all(self):
        # No punctuation anywhere to break at - falls back to a hard cut
        # at the width limit. 30 fullwidth characters (width 60 total)
        # should become three width-20 chunks of 10 characters each.
        text = "測" * 30
        segments = segment_notes_for_subtitles(text, max_display_width=20)

        self.assertEqual(len(segments), 3)
        for segment in segments:
            self.assertEqual(segment["text"], "測" * 10)
            self.assertLessEqual(_display_width(segment["text"]), 20)
        self.assertEqual(
            "".join(s["text"] for s in segments),
            text,
        )

    def test_hard_split_prefers_cutting_at_whitespace_for_mixed_content(self):
        # A long run of English words (space-separated, no punctuation) -
        # the cut should land on a space rather than mid-word.
        text = "alpha beta gamma delta epsilon zeta eta theta iota kappa"
        segments = segment_notes_for_subtitles(text, max_display_width=20)

        self.assertGreater(len(segments), 1)
        for segment in segments:
            self.assertLessEqual(_display_width(segment["text"]), 20)
            # None of the produced lines should start or end with a
            # partial word glued to nothing - i.e. no line should contain
            # a run of non-space characters longer than the longest word
            # in the source ("epsilon", 7 chars) unless the cut had no
            # choice (it always has a choice here, since every word is
            # short and spaces are frequent).
            for word in segment["text"].split():
                self.assertIn(word, text.split())

    def test_source_offsets_always_index_into_the_original_text(self):
        text = "第一句話，第二句話。第二段開始了，這裡也有內容。"
        segments = segment_notes_for_subtitles(text)

        for segment in segments:
            start, end = segment["source_start_offset"], segment["source_end_offset"]
            self.assertGreaterEqual(start, 0)
            self.assertLessEqual(end, len(text))
            self.assertLess(start, end)

    def test_removes_stray_whitespace_scattered_between_cjk_characters(self):
        # PowerPoint notes pasted from elsewhere sometimes end up with
        # stray spaces between individual Chinese characters - none of
        # that is intentional content, so it should disappear from the
        # displayed line entirely (not just get collapsed to one space).
        text = "這 是 一 段 話。"
        segments = segment_notes_for_subtitles(text)

        self.assertEqual(segments[0]["text"], "這是一段話")

    def test_keeps_single_space_between_english_words_and_at_cjk_latin_boundary(self):
        text = "這是 word 測試，Hello   world 也在這裡。"
        segments = segment_notes_for_subtitles(text)

        combined = "".join(s["text"] for s in segments)
        self.assertIn("這是 word 測試", combined)
        self.assertIn("Hello world 也在這裡", combined)
        self.assertNotIn("word  測試", combined)
        self.assertNotIn("Hello   world", combined)

    def test_whitespace_normalization_does_not_shift_source_offsets(self):
        # _normalize_whitespace only touches the *display* text - the
        # source offsets must still point at the untouched original span,
        # since Phase 3's alignment against edge-tts WordBoundary events
        # depends on these offsets matching the exact text sent to TTS.
        text = "這 是 測試。"
        segments = segment_notes_for_subtitles(text)

        self.assertEqual(segments[0]["text"], "這是測試")
        self.assertEqual(
            text[segments[0]["source_start_offset"]:segments[0]["source_end_offset"]],
            "這 是 測試。",
        )


if __name__ == "__main__":
    unittest.main()
