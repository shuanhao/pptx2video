import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from src.subtitle_burner import (
    DEFAULT_BAR_BOTTOM_OFFSET_PX,
    DEFAULT_BAR_HEIGHT_PX,
    DEFAULT_BAR_WIDTH_PX,
    DEFAULT_FONT_NAME,
    DEFAULT_FONT_SIZE,
    DEFAULT_MARGIN_V,
    _escape_path_for_ffmpeg_filter,
    build_burn_filter,
    burn_subtitles_into_video,
)

_FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


class EscapePathForFfmpegFilterTests(unittest.TestCase):
    def test_backslashes_become_forward_slashes(self):
        # On POSIX, Path() doesn't treat "\\" as a separator, so it's
        # preserved verbatim in str(path) - exercising exactly the string
        # _escape_path_for_ffmpeg_filter() has to normalize, the same as it
        # would receive a real Windows path on Windows.
        result = _escape_path_for_ffmpeg_filter(Path(r"C:\Users\Shawn\output\captions.srt"))
        # The only backslashes left should be the escape character ffmpeg
        # itself requires in front of the drive-letter colon - none of the
        # original path-separator backslashes should survive.
        self.assertEqual(result, r"C\:/Users/Shawn/output/captions.srt")

    def test_windows_drive_letter_colon_is_escaped(self):
        # This is the specific real-world failure mode: an unescaped drive
        # letter colon breaks ffmpeg's filtergraph parsing (it looks like
        # the start of a new filter option), not a "file not found" error.
        result = _escape_path_for_ffmpeg_filter(Path("C:/output/captions.srt"))
        self.assertEqual(result, r"C\:/output/captions.srt")

    def test_single_quote_is_escaped(self):
        result = _escape_path_for_ffmpeg_filter(Path("output/it's_a_test.srt"))
        self.assertIn(r"it\'s_a_test.srt", result)

    def test_plain_relative_path_is_unchanged(self):
        result = _escape_path_for_ffmpeg_filter(Path("segment_1.srt"))
        self.assertEqual(result, "segment_1.srt")


class BuildBurnFilterTests(unittest.TestCase):
    def test_uses_default_bar_and_style_values(self):
        vf = build_burn_filter(Path("captions.srt"))

        self.assertIn(f"w={DEFAULT_BAR_WIDTH_PX}", vf)
        self.assertIn(f"h={DEFAULT_BAR_HEIGHT_PX}", vf)
        self.assertIn(f"y=ih-{DEFAULT_BAR_BOTTOM_OFFSET_PX}", vf)
        self.assertIn(f"FontName={DEFAULT_FONT_NAME}", vf)
        self.assertIn(f"FontSize={DEFAULT_FONT_SIZE}", vf)
        self.assertIn(f"MarginV={DEFAULT_MARGIN_V}", vf)

    def test_bar_is_horizontally_centered(self):
        vf = build_burn_filter(Path("captions.srt"), bar_width_px=650)
        self.assertIn("x=(iw-650)/2", vf)

    def test_custom_values_override_defaults(self):
        vf = build_burn_filter(
            Path("captions.srt"),
            bar_width_px=720, bar_height_px=50, bar_bottom_offset_px=90,
            font_name="Arial", font_size=24, margin_v=10,
        )
        self.assertIn("w=720", vf)
        self.assertIn("h=50", vf)
        self.assertIn("y=ih-90", vf)
        self.assertIn("FontName=Arial", vf)
        self.assertIn("FontSize=24", vf)
        self.assertIn("MarginV=10", vf)

    def test_drawbox_comes_before_subtitles_in_the_filter_chain(self):
        # Order matters: subtitles must be drawn *after* (on top of) the
        # black bar, or the box would paint over the text instead.
        vf = build_burn_filter(Path("captions.srt"))
        self.assertLess(vf.index("drawbox"), vf.index("subtitles"))

    def test_text_is_plain_white_without_outline_or_shadow(self):
        # BorderStyle=1 + Outline=0 + Shadow=0 is what removes libass's
        # default white-text-black-outline look, per the project owner's
        # explicit "白字、黑框" -> "黑底、白字" requirement.
        vf = build_burn_filter(Path("captions.srt"))
        self.assertIn("BorderStyle=1", vf)
        self.assertIn("Outline=0", vf)
        self.assertIn("Shadow=0", vf)
        self.assertIn("PrimaryColour=&HFFFFFF&", vf)

    def test_srt_path_with_drive_letter_colon_is_escaped_in_filter(self):
        vf = build_burn_filter(Path("C:/output/captions.srt"))
        self.assertIn(r"subtitles='C\:/output/captions.srt'", vf)


@unittest.skipUnless(_FFMPEG_AVAILABLE, "ffmpeg/ffprobe not available")
class BurnSubtitlesIntoVideoEndToEndTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.video = self.tmp_path / "test.mp4"
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=3",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
                "-c:v", "libx264", "-c:a", "aac", "-shortest", str(self.video),
            ],
            check=True,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _probe_duration_seconds(self, path: Path) -> float:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(path),
            ],
            capture_output=True, text=True, check=True,
        )
        return float(result.stdout.strip())

    def test_produces_a_playable_video_with_unchanged_duration(self):
        srt_path = self.tmp_path / "captions.srt"
        srt_path.write_text(
            "1\n00:00:00,000 --> 00:00:02,000\n測試字幕\n",
            encoding="utf-8",
        )
        output_path = self.tmp_path / "burned.mp4"

        burn_subtitles_into_video(self.video, srt_path, output_path)

        self.assertTrue(output_path.exists())
        self.assertGreater(output_path.stat().st_size, 0)
        # Burning subtitles shouldn't change the video's overall duration -
        # only re-encode its pixels, not trim/extend the timeline.
        self.assertAlmostEqual(
            self._probe_duration_seconds(output_path),
            self._probe_duration_seconds(self.video),
            delta=0.5,
        )

    def test_custom_bar_and_font_size_are_honored(self):
        srt_path = self.tmp_path / "captions.srt"
        srt_path.write_text(
            "1\n00:00:00,000 --> 00:00:02,000\n測試字幕\n",
            encoding="utf-8",
        )
        output_path = self.tmp_path / "burned_custom.mp4"

        # Just confirms passing overrides through to ffmpeg doesn't raise -
        # the actual pixel output isn't asserted on here (that's a visual
        # concern the project owner already confirmed by eye).
        burn_subtitles_into_video(
            self.video, srt_path, output_path,
            bar_width_px=200, bar_height_px=20, font_size=10, crf=28,
        )
        self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
