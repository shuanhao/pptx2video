import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None

# scripts/ isn't a package (no __init__.py), so load by path - same approach
# tests/test_calibrate_scale.py uses for calibrate_scale.py.
_spec = importlib.util.spec_from_file_location("split_video_by_slides", ROOT / "scripts" / "split_video_by_slides.py")
split_video_by_slides = importlib.util.module_from_spec(_spec)
sys.path.insert(0, str(ROOT))
_spec.loader.exec_module(split_video_by_slides)


class ChooseEqualDurationCutsTests(unittest.TestCase):
    def test_evenly_spaced_slides_splits_into_thirds(self):
        # 9 slides, each exactly 10s apart, 0..90s total - the ideal 3-way
        # split points are at 30s and 60s, i.e. right at slide 4 (30s) and
        # slide 7 (60s).
        slide_starts = {n: (n - 1) * 10.0 for n in range(1, 10)}
        cuts = split_video_by_slides._choose_equal_duration_cuts(slide_starts, 90.0, 3)
        self.assertEqual([slide_num for slide_num, _t in cuts], [4, 7])

    def test_uneven_slide_lengths_still_picks_closest_boundaries(self):
        # One very long slide (slide 2, from 5s to 95s) dominates the deck;
        # the greedy target-based pick should still choose the boundaries
        # closest to the 1/3 and 2/3 marks of the *actual* total duration.
        slide_starts = {1: 0.0, 2: 5.0, 3: 95.0, 4: 100.0, 5: 105.0}
        total_duration = 110.0
        cuts = split_video_by_slides._choose_equal_duration_cuts(slide_starts, total_duration, 3)
        # targets are ~36.7s and ~73.3s; closest boundaries among {5, 95, 100, 105} are 5 and 95
        self.assertEqual([slide_num for slide_num, _t in cuts], [2, 3])

    def test_never_reuses_a_slide_boundary_for_two_cuts(self):
        slide_starts = {1: 0.0, 2: 50.0}
        cuts = split_video_by_slides._choose_equal_duration_cuts(slide_starts, 100.0, 3)
        slide_nums = [slide_num for slide_num, _t in cuts]
        self.assertEqual(len(slide_nums), len(set(slide_nums)))
        # Only one real usable boundary (slide 1's own start at 0 is excluded
        # as "not a real cut"), so only one cut can be produced even though
        # 3 segments were requested.
        self.assertEqual(slide_nums, [2])

    def test_skips_slide_one_own_start_as_not_a_real_cut(self):
        slide_starts = {1: 0.0, 2: 33.0, 3: 66.0}
        cuts = split_video_by_slides._choose_equal_duration_cuts(slide_starts, 100.0, 3)
        slide_nums = [slide_num for slide_num, _t in cuts]
        self.assertNotIn(1, slide_nums)


class CutsFromSlideNumbersTests(unittest.TestCase):
    def test_cuts_land_at_the_following_slides_start(self):
        slide_starts = {1: 0.0, 2: 10.0, 3: 20.0, 4: 30.0, 5: 40.0}
        cuts = split_video_by_slides._cuts_from_slide_numbers(slide_starts, [2, 4])
        self.assertEqual(cuts, [(3, 20.0), (5, 40.0)])

    def test_sorted_regardless_of_input_order(self):
        slide_starts = {1: 0.0, 2: 10.0, 3: 20.0, 4: 30.0}
        cuts = split_video_by_slides._cuts_from_slide_numbers(slide_starts, [3, 1])
        self.assertEqual(cuts, [(2, 10.0), (4, 30.0)])

    def test_missing_following_slide_raises(self):
        slide_starts = {1: 0.0, 2: 10.0}
        with self.assertRaises(SystemExit):
            split_video_by_slides._cuts_from_slide_numbers(slide_starts, [2])


class ParseSrtTests(unittest.TestCase):
    def test_parses_standard_srt_text(self):
        srt_text = (
            "1\n00:00:00,000 --> 00:00:02,500\nHello there\n\n"
            "2\n00:00:02,500 --> 00:00:05,000\nSecond line\nwrapped\n"
        )
        entries = split_video_by_slides._parse_srt(srt_text)
        self.assertEqual(len(entries), 2)
        self.assertAlmostEqual(entries[0]["start_seconds"], 0.0)
        self.assertAlmostEqual(entries[0]["end_seconds"], 2.5)
        self.assertEqual(entries[0]["text"], "Hello there")
        self.assertAlmostEqual(entries[1]["start_seconds"], 2.5)
        self.assertAlmostEqual(entries[1]["end_seconds"], 5.0)
        self.assertEqual(entries[1]["text"], "Second line\nwrapped")

    def test_empty_text_returns_no_entries(self):
        self.assertEqual(split_video_by_slides._parse_srt(""), [])

    def test_skips_malformed_blocks_without_raising(self):
        srt_text = "not a real cue block\n\n1\n00:00:00,000 --> 00:00:01,000\nReal cue\n"
        entries = split_video_by_slides._parse_srt(srt_text)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["text"], "Real cue")


class SliceSrtForSegmentTests(unittest.TestCase):
    def test_keeps_only_cues_overlapping_window_and_retimes_to_zero(self):
        entries = [
            {"start_seconds": 0.0, "end_seconds": 5.0, "text": "before segment"},
            {"start_seconds": 10.0, "end_seconds": 15.0, "text": "inside segment"},
            {"start_seconds": 40.0, "end_seconds": 45.0, "text": "after segment"},
        ]
        sliced = split_video_by_slides._slice_srt_for_segment(entries, window_start=10.0, window_end=30.0)
        self.assertEqual(len(sliced), 1)
        self.assertEqual(sliced[0]["text"], "inside segment")
        self.assertAlmostEqual(sliced[0]["start_seconds"], 0.0)
        self.assertAlmostEqual(sliced[0]["end_seconds"], 5.0)

    def test_clips_a_cue_straddling_the_window_boundary(self):
        entries = [{"start_seconds": 8.0, "end_seconds": 12.0, "text": "straddles start"}]
        sliced = split_video_by_slides._slice_srt_for_segment(entries, window_start=10.0, window_end=30.0)
        self.assertEqual(len(sliced), 1)
        self.assertAlmostEqual(sliced[0]["start_seconds"], 0.0)
        self.assertAlmostEqual(sliced[0]["end_seconds"], 2.0)

    def test_drops_zero_length_overlap_at_exact_boundary(self):
        entries = [{"start_seconds": 0.0, "end_seconds": 10.0, "text": "ends exactly at window start"}]
        sliced = split_video_by_slides._slice_srt_for_segment(entries, window_start=10.0, window_end=30.0)
        self.assertEqual(sliced, [])


@unittest.skipUnless(_FFMPEG_AVAILABLE, "ffmpeg/ffprobe not available")
class FfmpegSegmentEndToEndTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.video = self.tmp_path / "test.mp4"
        # 30s synthetic video (blue color + a tone) - real content doesn't
        # matter here, only that ffmpeg can probe/cut it accurately.
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=30",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=30",
                "-c:v", "libx264", "-c:a", "aac", "-shortest", str(self.video),
            ],
            check=True,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_probe_duration_matches_generated_video(self):
        self.assertAlmostEqual(split_video_by_slides._probe_duration_seconds(self.video), 30.0, delta=0.1)

    def test_run_ffmpeg_segment_produces_correctly_sized_clip(self):
        out = self.tmp_path / "seg.mp4"
        split_video_by_slides._run_ffmpeg_segment(self.video, 10.0, 20.0, out, reencode=False)
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 0)
        self.assertAlmostEqual(split_video_by_slides._probe_duration_seconds(out), 10.0, delta=0.5)

    def test_run_ffmpeg_segment_to_end_of_video_when_end_is_none(self):
        out = self.tmp_path / "seg_to_end.mp4"
        split_video_by_slides._run_ffmpeg_segment(self.video, 20.0, None, out, reencode=False)
        self.assertTrue(out.exists())
        self.assertAlmostEqual(split_video_by_slides._probe_duration_seconds(out), 10.0, delta=0.5)


if __name__ == "__main__":
    unittest.main()
