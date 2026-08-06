import unittest

from src.subtitle_alignment import (
    DEFAULT_TRAILING_GAP_SECONDS,
    align_segments_with_word_boundaries,
    find_suspected_dropped_narration,
    format_srt,
    _match_word_boundaries,
    _seconds_to_srt_timestamp,
)
from src.subtitle_segmenter import segment_notes_for_subtitles


def _wb(text, offset_seconds, duration_seconds):
    return {"text": text, "offset_seconds": offset_seconds, "duration_seconds": duration_seconds}


def _seg(text, start, end):
    return {"text": text, "source_start_offset": start, "source_end_offset": end}


class SecondsToSrtTimestampTests(unittest.TestCase):
    def test_formats_zero(self):
        self.assertEqual(_seconds_to_srt_timestamp(0.0), "00:00:00,000")

    def test_formats_sub_second_precision(self):
        self.assertEqual(_seconds_to_srt_timestamp(1.234), "00:00:01,234")

    def test_formats_hours_minutes_seconds(self):
        self.assertEqual(_seconds_to_srt_timestamp(3661.5), "01:01:01,500")

    def test_negative_input_is_clamped_to_zero(self):
        self.assertEqual(_seconds_to_srt_timestamp(-5.0), "00:00:00,000")


class AlignSegmentsWithWordBoundariesTests(unittest.TestCase):
    def test_basic_alignment_matches_offsets_in_order(self):
        text = "早安世界"
        segments = [_seg("早安世界", 0, 4)]
        word_boundaries = [
            _wb("早", 0.0, 0.2),
            _wb("安", 0.2, 0.2),
            _wb("世", 0.4, 0.2),
            _wb("界", 0.6, 0.2),
        ]

        aligned, warnings = align_segments_with_word_boundaries(text, segments, word_boundaries)

        self.assertEqual(warnings, [])
        self.assertEqual(len(aligned), 1)
        self.assertAlmostEqual(aligned[0]["start_seconds"], 0.0)
        # Last segment: no following segment to extend toward, so its end
        # time stays at the raw last-word end (0.6 + 0.2).
        self.assertAlmostEqual(aligned[0]["end_seconds"], 0.8)

    def test_unvoiced_punctuation_between_boundaries_is_skipped_over(self):
        # "，" between the two words has no WordBoundary event of its own -
        # the cursor should still find "世界" right after it.
        text = "早安，世界"
        segments = [_seg("早安，世界", 0, 5)]
        word_boundaries = [
            _wb("早", 0.0, 0.2),
            _wb("安", 0.2, 0.2),
            _wb("世", 0.4, 0.2),
            _wb("界", 0.6, 0.2),
        ]

        aligned, warnings = align_segments_with_word_boundaries(text, segments, word_boundaries)

        self.assertEqual(warnings, [])
        self.assertAlmostEqual(aligned[0]["start_seconds"], 0.0)
        self.assertAlmostEqual(aligned[0]["end_seconds"], 0.8)

    def test_end_time_extends_forward_to_next_segment_start_minus_gap(self):
        text = "第一句。第二句。"
        segments = [_seg("第一句", 0, 3), _seg("第二句", 4, 7)]
        word_boundaries = [
            _wb("第", 0.0, 0.2),
            _wb("一", 0.2, 0.2),
            _wb("句", 0.4, 0.2),
            # noticeable pause before the next sentence begins
            _wb("第", 2.0, 0.2),
            _wb("二", 2.2, 0.2),
            _wb("句", 2.4, 0.2),
        ]

        aligned, warnings = align_segments_with_word_boundaries(
            text, segments, word_boundaries, trailing_gap_seconds=0.15
        )

        self.assertEqual(warnings, [])
        # Raw end of segment 1 would be 0.4 + 0.2 = 0.6, but it should be
        # extended forward to just before segment 2 starts (2.0 - 0.15).
        self.assertAlmostEqual(aligned[0]["end_seconds"], 1.85)
        # Last segment keeps its raw end (2.4 + 0.2).
        self.assertAlmostEqual(aligned[1]["end_seconds"], 2.6)

    def test_end_time_extension_never_shrinks_below_raw_end(self):
        text = "第一句第二句"
        segments = [_seg("第一句", 0, 3), _seg("第二句", 3, 6)]
        # Back-to-back with almost no gap - extending "to just before the
        # next segment, minus 0.15s" would land *before* the raw end here,
        # which must not shrink the interval.
        word_boundaries = [
            _wb("第", 0.0, 0.2),
            _wb("一", 0.2, 0.2),
            _wb("句", 0.4, 0.2),
            _wb("第", 0.62, 0.2),
            _wb("二", 0.82, 0.2),
            _wb("句", 1.02, 0.2),
        ]

        aligned, warnings = align_segments_with_word_boundaries(
            text, segments, word_boundaries, trailing_gap_seconds=0.15
        )

        self.assertEqual(warnings, [])
        # Raw end (0.6) is kept, not shrunk to 0.62 - 0.15 = 0.47.
        self.assertAlmostEqual(aligned[0]["end_seconds"], 0.6)

    def test_straddling_word_boundary_event_does_not_overlap_adjacent_segments(self):
        # Real-world bug (2026-08, found by the project owner burning
        # subtitles into video): subtitle_segmenter can break a sentence
        # into two lines at a point that falls *inside* a single
        # WordBoundary event's own text span (no punctuation nearby to
        # break on cleanly). That one straddling event ("CD", spanning
        # offsets 2-4) then overlaps BOTH segments' offset ranges (segment
        # 0 is offsets 0-3, segment 1 is offsets 3-6) and gets counted
        # into both - pulling segment 0's end later and segment 1's start
        # earlier at the same time. Before the fix this produced two SRT
        # cues with genuinely overlapping timestamps (segment 1 starting
        # before segment 0 ends), which broke scripts/burn_subtitles.py's
        # fixed-height black bar (libass's collision avoidance pushed the
        # second cue's text off the bar entirely - see
        # docs/SUBTITLE_OVERLAP_INCIDENT.md).
        text = "ABCDEF"
        segments = [_seg("ABC", 0, 3), _seg("DEF", 3, 6)]
        word_boundaries = [
            _wb("AB", 0.0, 0.2),   # fully inside segment 0 (offsets 0-2)
            _wb("CD", 0.3, 0.2),   # straddles the split point (offsets 2-4)
            _wb("EF", 0.7, 0.2),   # fully inside segment 1 (offsets 4-6)
        ]

        aligned, warnings = align_segments_with_word_boundaries(text, segments, word_boundaries)

        self.assertEqual(warnings, [])
        # The straddling event must not be allowed to make these overlap -
        # segment 0 must end at or before segment 1 starts.
        self.assertLessEqual(aligned[0]["end_seconds"], aligned[1]["start_seconds"])
        # Segment 0's end is clamped down to segment 1's start (0.3), not
        # left at the raw max(0.0+0.2, 0.3+0.2) = 0.5 that caused the bug.
        self.assertAlmostEqual(aligned[0]["end_seconds"], 0.3)
        self.assertAlmostEqual(aligned[1]["start_seconds"], 0.3)
        self.assertAlmostEqual(aligned[1]["end_seconds"], 0.9)

    def test_clamping_never_inverts_a_segment_into_negative_duration(self):
        # Pathological case: if the overlap were somehow so severe that
        # clamping end down to the next segment's start would put it
        # *before* this segment's own start, the clamp must floor at this
        # segment's own start instead of producing end < start.
        text = "ABCDEF"
        segments = [_seg("ABC", 0, 3), _seg("DEF", 3, 6)]
        word_boundaries = [
            _wb("ABCD", 0.5, 0.4),  # spans both segments' offsets (0-4), starts late
            _wb("EF", 0.2, 0.2),    # fully inside segment 1, but starts *before* the above
        ]

        aligned, warnings = align_segments_with_word_boundaries(text, segments, word_boundaries)

        self.assertGreaterEqual(aligned[0]["end_seconds"], aligned[0]["start_seconds"])

    def test_unmatched_word_boundary_text_is_skipped_with_a_warning(self):
        text = "早安世界"
        segments = [_seg("早安世界", 0, 4)]
        word_boundaries = [
            _wb("早", 0.0, 0.2),
            _wb("XYZ_NOT_IN_TEXT", 0.2, 0.1),  # can never match
            _wb("安", 0.3, 0.2),
            _wb("世", 0.5, 0.2),
            _wb("界", 0.7, 0.2),
        ]

        aligned, warnings = align_segments_with_word_boundaries(text, segments, word_boundaries)

        self.assertEqual(len(warnings), 1)
        self.assertIn("XYZ_NOT_IN_TEXT", warnings[0])
        # Alignment still completes using the events that did match.
        self.assertAlmostEqual(aligned[0]["start_seconds"], 0.0)
        self.assertAlmostEqual(aligned[0]["end_seconds"], 0.9)

    def test_segment_with_no_matching_boundaries_is_interpolated_with_a_warning(self):
        text = "第一句第二句第三句"
        segments = [
            _seg("第一句", 0, 3),
            _seg("第二句", 3, 6),
            _seg("第三句", 6, 9),
        ]
        # No WordBoundary events at all fall inside segment 2's offset
        # range (3-6) - simulates edge-tts silently dropping that whole
        # span from its boundary events.
        word_boundaries = [
            _wb("第", 0.0, 0.2),
            _wb("一", 0.2, 0.2),
            _wb("句", 0.4, 0.2),
            _wb("第", 3.0, 0.2),  # this text is "第" from segment 3, offset 6
            _wb("三", 3.2, 0.2),
            _wb("句", 3.4, 0.2),
        ]
        # Rig the offsets so the second "第"/"三"/"句" trio is only found
        # starting from character offset 6 onward (segment 3) - the exact
        # substring search would otherwise (incorrectly, for this test)
        # match the first "第" again. Use a cursor-respecting variant by
        # replacing segment 2's characters with something distinguishable.
        text = "第一句　　　第三句"
        segments = [
            _seg("第一句", 0, 3),
            _seg("　　　", 3, 6),
            _seg("第三句", 6, 9),
        ]

        aligned, warnings = align_segments_with_word_boundaries(text, segments, word_boundaries)

        interpolation_warnings = [w for w in warnings if "interpolated" in w]
        self.assertEqual(len(interpolation_warnings), 1)
        self.assertIn("segment 1", interpolation_warnings[0])
        # Interpolated start = segment 1's (already extended) end time;
        # interpolated end = the next matched boundary's start (segment 3's
        # first matched "第" at 3.0s).
        self.assertAlmostEqual(aligned[1]["start_seconds"], aligned[0]["end_seconds"])
        self.assertAlmostEqual(aligned[1]["end_seconds"], 3.0)

    def test_negative_trailing_gap_raises(self):
        with self.assertRaises(ValueError):
            align_segments_with_word_boundaries("x", [], [], trailing_gap_seconds=-0.1)

    def test_default_trailing_gap_constant_is_used_by_default(self):
        text = "第一句第二句"
        segments = [_seg("第一句", 0, 3), _seg("第二句", 3, 6)]
        word_boundaries = [
            _wb("第", 0.0, 0.2),
            _wb("一", 0.2, 0.2),
            _wb("句", 0.4, 0.2),
            _wb("第", 2.0, 0.2),
            _wb("二", 2.2, 0.2),
            _wb("句", 2.4, 0.2),
        ]

        aligned, _ = align_segments_with_word_boundaries(text, segments, word_boundaries)

        self.assertAlmostEqual(aligned[0]["end_seconds"], 2.0 - DEFAULT_TRAILING_GAP_SECONDS)

    def test_end_to_end_with_real_segmenter_output(self):
        # A "\n" paragraph break forces two segments regardless of width
        # (paragraph boundaries are a hard boundary - see subtitle_segmenter's
        # design decision 3), unlike relying on the two sentences alone,
        # which are short enough that _pack_units could legally merge them
        # onto one line.
        text = "今天天氣很好。\n我們出去走走吧！"
        segments = segment_notes_for_subtitles(text)
        self.assertEqual(len(segments), 2)

        # Fabricate one WordBoundary event per character, in order, each
        # 0.2s long with no gaps - a simplified stand-in for real edge-tts
        # output good enough to exercise the alignment logic end-to-end.
        # Punctuation and the paragraph-break newline aren't voiced, so
        # they get no event of their own, same as real edge-tts output.
        word_boundaries = []
        t = 0.0
        for ch in text:
            if ch not in "。！\n":
                word_boundaries.append(_wb(ch, t, 0.2))
                t += 0.2

        aligned, warnings = align_segments_with_word_boundaries(text, segments, word_boundaries)

        self.assertEqual(warnings, [])
        self.assertEqual([a["text"] for a in aligned], [s["text"] for s in segments])
        self.assertLess(aligned[0]["start_seconds"], aligned[0]["end_seconds"])
        self.assertLess(aligned[1]["start_seconds"], aligned[1]["end_seconds"])
        self.assertLessEqual(aligned[0]["end_seconds"], aligned[1]["start_seconds"])


class FindSuspectedDroppedNarrationTests(unittest.TestCase):
    # Regression tests for a real finding (see subtitle_alignment.py's
    # find_suspected_dropped_narration docstring): a real deck's slide 9
    # showed edge-tts silently skip ~300 characters (two full bullet
    # points) of narration mid-slide - the WordBoundary stream jumped
    # straight from "操作" to "今天" with only ~4s of audio in between,
    # where that much source text should have taken ~55s at this slide's
    # own measured pace. The project owner confirmed by ear: listening to
    # the flagged audio position, the narration genuinely jumps straight
    # over the skipped text. These tests reproduce that shape synthetically
    # (one character per WordBoundary event, 0.2s apart - i.e. 5 chars/sec,
    # matching this module's other tests' convention) so they don't depend
    # on real edge-tts output.

    def _steady_pace_boundaries(self, text, seconds_per_char=0.2, skip_chars=frozenset("。！\n")):
        word_boundaries = []
        t = 0.0
        for ch in text:
            if ch not in skip_chars:
                word_boundaries.append(_wb(ch, t, seconds_per_char * 0.8))
            t += seconds_per_char
        return word_boundaries

    def test_no_suspects_when_narration_covers_text_at_a_steady_pace(self):
        text = "這是一段完全正常的講稿內容，語速穩定，沒有任何內容被跳過。"
        word_boundaries = self._steady_pace_boundaries(text)

        suspects = find_suspected_dropped_narration(text, word_boundaries)

        self.assertEqual(suspects, [])

    def test_flags_a_large_chunk_missing_with_only_a_brief_time_gap(self):
        prefix = "第三，是以讀取為主。CPU可以快速取得程式。但是寫入速度則比較慢。"
        # ~20 characters of real content that should take ~4s at this
        # slide's pace (0.2s/char) but is given almost no time at all -
        # same shape as the real slide_009 finding, just shorter.
        dropped = "因此Flash並不適合頻繁修改資料這也是後面會介紹的原因第四是可重複寫入"
        suffix = "今天大家先建立概念即可。"
        text = prefix + dropped + suffix

        word_boundaries = self._steady_pace_boundaries(prefix, seconds_per_char=0.2)
        last_prefix_end = word_boundaries[-1]["offset_seconds"] + word_boundaries[-1]["duration_seconds"]
        # The dropped text has NO word boundary events at all - simulating
        # edge-tts never having voiced it - and the suffix picks up only
        # 0.5s later, nowhere near the ~4s the dropped text's length would
        # imply at the established pace.
        suffix_start = last_prefix_end + 0.5
        suffix_boundaries = []
        t = suffix_start
        for ch in suffix:
            if ch not in "。！\n":
                suffix_boundaries.append(_wb(ch, t, 0.16))
            t += 0.2
        word_boundaries += suffix_boundaries

        suspects = find_suspected_dropped_narration(text, word_boundaries)

        self.assertEqual(len(suspects), 1)
        # skipped_text includes the trailing "。" of the previous sentence
        # too, since punctuation is never matched to a WordBoundary event
        # either - this matches the real slide_009 finding, whose
        # skipped_text also started with the prior sentence's own
        # unvoiced "。\n".
        self.assertEqual(suspects[0]["skipped_text"], "。" + dropped)
        self.assertLess(suspects[0]["gap_seconds"], suspects[0]["expected_seconds"] * 0.3)

    def test_short_gap_like_a_single_skipped_punctuation_mark_is_not_flagged(self):
        # A lone unvoiced character (e.g. a closing quote mark edge-tts
        # doesn't speak) is normal and far below min_gap_chars - must not
        # be treated the same as a real dropped chunk.
        text = "他說「這是重點」，大家要記住這一點。"
        word_boundaries = self._steady_pace_boundaries(text, skip_chars=frozenset("。！\n「」，"))

        suspects = find_suspected_dropped_narration(text, word_boundaries)

        self.assertEqual(suspects, [])

    def test_fewer_than_two_matched_events_returns_empty_list(self):
        text = "很短的一句話。"
        word_boundaries = [_wb("很", 0.0, 0.2)]

        self.assertEqual(find_suspected_dropped_narration(text, word_boundaries), [])
        self.assertEqual(find_suspected_dropped_narration(text, []), [])


class RepeatedWordDisambiguationTests(unittest.TestCase):
    # Regression tests for a second real finding, on the same deck as the
    # FindSuspectedDroppedNarrationTests cases above (a different slide):
    # edge-tts dropped "SRAM 斷電後資料立即消失。Flash 則可以永久保存。第四。
    # SRAM 的讀寫速度非常快。" entirely, with the narration jumping straight
    # from "第三" to the word "Flash" that starts "Flash 的讀取速度雖然也很快"
    # a sentence later. The word "Flash" (and, immediately after it, "的")
    # both also occur earlier, inside the dropped span itself - so
    # _find_boundary_span's old "always take the first occurrence at or
    # after the cursor" behavior locked onto the *wrong*, earlier "Flash"/
    # "的" pair. That didn't just mislabel one word: every event after it
    # inherited a wrong text position, which fragmented what should have
    # been one large, obviously-anomalous gap into several small ones - two
    # of which were individually below find_suspected_dropped_narration's
    # threshold and went unreported, while the two that were reported had
    # the wrong skipped_text and position. The project owner confirmed the
    # real drop's true extent by ear before this was fixed.
    #
    # These tests reproduce the shape synthetically: a repeated word
    # appears once inside a dropped span and once again where the audio
    # actually resumes, with a short common word (here "的") repeating
    # right after each occurrence too - the exact "ambiguous word followed
    # by another ambiguous word" pattern that defeated a naive one-token
    # lookahead.

    def _tokenize(self, text):
        # Splits on ASCII-letter runs (e.g. "Flash", "SRAM") vs. individual
        # CJK characters - matching how edge-tts's real WordBoundary events
        # group an English word as one event but voice each Chinese
        # character as its own (see the real slide_006/009/010
        # wordboundaries.json files this bug was found from). Punctuation
        # is dropped entirely, same as real edge-tts output.
        tokens = []
        i = 0
        while i < len(text):
            ch = text[i]
            if ch in "。\n":
                i += 1
                continue
            if ch.isascii() and ch.isalpha():
                j = i
                while j < len(text) and text[j].isascii() and text[j].isalpha():
                    j += 1
                tokens.append(text[i:j])
                i = j
            else:
                tokens.append(ch)
                i += 1
        return tokens

    def test_disambiguates_repeated_word_using_lookahead_to_find_true_resume_point(self):
        prefix = "第三。SRAM斷電後資料立即消失。"
        dropped = "Flash則可以永久保存。第四。SRAM的讀寫速度非常快。"
        resumes_with = "Flash的讀取速度雖然也很快。"
        text = prefix + dropped + resumes_with

        prefix_end = len(prefix)
        resume_start = len(prefix) + len(dropped)

        # Audio: narrates the prefix at a steady pace, then - exactly like
        # the real case - jumps straight to "resumes_with" with almost no
        # elapsed time, i.e. "dropped" was never voiced at all.
        word_boundaries = []
        t = 0.0
        for token in self._tokenize(prefix):
            word_boundaries.append(_wb(token, t, 0.16))
            t += 0.2
        resume_audio_start = t + 0.1  # tiny gap, not the ~9s a 24-char skip would need
        t = resume_audio_start
        for token in self._tokenize(resumes_with):
            word_boundaries.append(_wb(token, t, 0.16))
            t += 0.2

        matched, alignment_warnings = _match_word_boundaries(text, word_boundaries)

        self.assertEqual(alignment_warnings, [])
        # The "Flash" WordBoundary event must be attributed to its real
        # (second) occurrence - the one that starts resumes_with - not the
        # one inside dropped.
        flash_events = [m for m in matched if text[m["source_start_offset"]:m["source_end_offset"]] == "Flash"]
        self.assertEqual(len(flash_events), 1)
        self.assertEqual(flash_events[0]["source_start_offset"], resume_start)

        suspects = find_suspected_dropped_narration(text, word_boundaries)

        self.assertEqual(len(suspects), 1)
        # Starts at (or just before, if the last prefix character was
        # unvoiced punctuation - same as the real case) where "dropped"
        # begins, and ends exactly where the real "Flash" resumes.
        self.assertLessEqual(suspects[0]["source_start_offset"], prefix_end)
        self.assertGreater(suspects[0]["source_start_offset"], prefix_end - 2)
        self.assertEqual(suspects[0]["source_end_offset"], resume_start)
        self.assertIn("Flash則可以永久保存", suspects[0]["skipped_text"])
        self.assertIn("SRAM的讀寫速度非常快", suspects[0]["skipped_text"])

    def test_near_duplicate_phrase_prefers_nearby_candidate_over_slightly_cleaner_far_one(self):
        # Regression test for a real finding from a *third* slide, on the
        # same deck, surfaced only after the "Flash" fix above was
        # deployed and a later full-deck subtitle regen reprocessed this
        # slide's untouched old data with the new code. The notes had two
        # near-duplicate phrases close together: a summary ("...分成四個
        # 階段：Input，也就是輸入。") immediately followed later by a
        # detail intro ("...第一個階段，Input，也就是輸入。") - nothing was
        # actually dropped here. The first version of the lookahead fix
        # picked the *second*, wrong "個" purely because "，Input" costs
        # one fewer skipped character than "：\nInput" before it - jumping
        # the cursor ~19 characters ahead here (135 in the real slide) and
        # silently discarding real, correctly-matched-so-far text, which
        # cascaded into a flood of "Could not locate" warnings afterward
        # (in the real case, over 700 of them). The fix must prefer the
        # nearby, correct "個" - a farther candidate should only win when
        # its continuation is *substantially* cleaner, not by a character
        # or two of punctuation (see _CONTINUATION_TIE_THRESHOLD).
        text = "分成四個階段：Input也就是輸入。第一個階段，Input也就是輸入。"
        near_start = text.index("四個") + 1  # the "個" right after "四"
        far_start = text.index("一個") + 1  # the "個" right after "一"
        self.assertLess(near_start, far_start)

        word_boundaries = []
        t = 0.0
        for token in self._tokenize(text):
            word_boundaries.append(_wb(token, t, 0.16))
            t += 0.2

        matched, alignment_warnings = _match_word_boundaries(text, word_boundaries)

        self.assertEqual(alignment_warnings, [])
        ge_events = [m for m in matched if text[m["source_start_offset"]:m["source_end_offset"]] == "個"]
        self.assertEqual(len(ge_events), 2)
        # The first "個" WordBoundary event (there are two - one per
        # occurrence, narrated in order) must resolve to the nearby
        # occurrence, not jump ahead to the far one.
        self.assertEqual(ge_events[0]["source_start_offset"], near_start)
        self.assertEqual(ge_events[1]["source_start_offset"], far_start)
        # Nothing was dropped, so no suspects should be reported.
        self.assertEqual(find_suspected_dropped_narration(text, word_boundaries), [])

    def test_unambiguous_repeated_words_still_resolve_in_order_when_not_dropped(self):
        # Sanity check: when nothing was actually dropped and a word simply
        # repeats normally (e.g. "的" used twice in an ordinary sentence),
        # disambiguation must not make things worse - each occurrence
        # should still resolve to its own correct, sequential position.
        text = "他的書和她的筆都放在桌上。"
        word_boundaries = []
        t = 0.0
        for ch in text:
            if ch not in "。":
                word_boundaries.append(_wb(ch, t, 0.16))
            t += 0.2

        matched, alignment_warnings = _match_word_boundaries(text, word_boundaries)

        self.assertEqual(alignment_warnings, [])
        starts = [m["source_start_offset"] for m in matched]
        self.assertEqual(starts, sorted(starts))
        self.assertEqual(len(starts), len(set(starts)))


class FormatSrtTests(unittest.TestCase):
    def test_empty_entries_returns_empty_string(self):
        self.assertEqual(format_srt([]), "")

    def test_formats_single_entry(self):
        entries = [{"text": "早安世界", "start_seconds": 0.0, "end_seconds": 1.5}]
        expected = "1\n00:00:00,000 --> 00:00:01,500\n早安世界\n"
        self.assertEqual(format_srt(entries), expected)

    def test_formats_multiple_entries_with_sequential_numbering(self):
        entries = [
            {"text": "第一句", "start_seconds": 0.0, "end_seconds": 1.0},
            {"text": "第二句", "start_seconds": 1.0, "end_seconds": 2.5},
        ]
        expected = (
            "1\n00:00:00,000 --> 00:00:01,000\n第一句\n"
            "\n"
            "2\n00:00:01,000 --> 00:00:02,500\n第二句\n"
        )
        self.assertEqual(format_srt(entries), expected)


if __name__ == "__main__":
    unittest.main()
