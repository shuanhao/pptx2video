import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.subtitle_pipeline import _build_slide_captions
from src.subtitle_vtt import format_vtt, write_slide_vtt


class VttTests(unittest.TestCase):
    def test_literal_text_and_timestamp_rounding(self):
        result = format_vtt([dict(text="中文 <tag> &\n下一行", start_seconds=59.9996,
                                  end_seconds=3600.123)], 3601)
        self.assertEqual(result, "WEBVTT\n\n1\n00:01:00.000 --> 01:00:00.123\n"
                                 "中文 &lt;tag&gt; &amp;\n下一行\n\n")

    def test_invalid_cues_are_rejected_without_repair(self):
        for start, end in [(-1, 1), (1, 1), (2, 1), (float('nan'), 1),
                           (0, float('inf')), (0, 11), (0, .0001)]:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                format_vtt([dict(text="text", start_seconds=start, end_seconds=end)], 10)
        with self.assertRaises(ValueError):
            format_vtt([dict(text="a", start_seconds=0, end_seconds=2),
                        dict(text="b", start_seconds=1, end_seconds=3)], 10)

    @patch("src.subtitle_pipeline._measure_audio_duration_seconds", return_value=2.0)
    def test_shared_alignment_relative_times_and_unchanged_source(self, measure):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = root / "slide_002.mp3"
            audio.write_bytes(b"original mp3")
            boundaries = root / "slide_002.wordboundaries.json"
            boundaries.write_text(json.dumps([
                dict(text="Hello", offset_seconds=.2, duration_seconds=.5)
            ]), encoding="utf-8")
            slides = [dict(slide_num=1, notes=""), dict(slide_num=2, notes="Hello")]
            manifest = dict(slides=[dict(slide_num=2, audio_file=audio.name,
                                        word_boundaries_file=boundaries.name)])
            from src.subtitle_segmenter import DEFAULT_MAX_DISPLAY_WIDTH
            from src.subtitle_alignment import DEFAULT_TRAILING_GAP_SECONDS
            plan, warnings = _build_slide_captions(slides, manifest, root, 5,
                DEFAULT_MAX_DISPLAY_WIDTH, DEFAULT_TRAILING_GAP_SECONDS)
            paths = write_slide_vtt(slides, manifest, root, root / "vtt")
            self.assertEqual(warnings, [])
            self.assertEqual([p.name for p in paths], ["slide_002.vtt"])
            self.assertEqual(paths[0].read_text(encoding="utf-8"),
                             format_vtt(plan[1]["captions"], 2))
            self.assertIn("00:00:00.200 -->", paths[0].read_text(encoding="utf-8"))
            self.assertEqual(audio.read_bytes(), b"original mp3")
            self.assertEqual(DEFAULT_MAX_DISPLAY_WIDTH, 36)
            manifest['slides'][0].pop('word_boundaries_file')
            with self.assertRaises(ValueError):
                write_slide_vtt(slides, manifest, root, root / "bad")
            self.assertFalse((root / "bad").exists())

    def test_invalid_later_slide_does_not_publish_earlier_slide(self):
        plan = [dict(slide_num=n, has_narration=True, duration_seconds=2,
                     captions=[dict(text="a", start_seconds=0, end_seconds=end)])
                for n, end in [(1, 1), (2, 3)]]
        with tempfile.TemporaryDirectory() as tmp, patch(
            'src.subtitle_vtt._build_slide_captions', return_value=(plan, [])
        ):
            output = Path(tmp) / 'vtt'
            with self.assertRaises(ValueError):
                write_slide_vtt([], {}, tmp, output)
            self.assertFalse(output.exists())

    def test_prepared_manifest_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "original MP3"):
            write_slide_vtt([], {'preparation': {'kind': 'prepared'}}, '.', '.')

    @patch("src.subtitle_pipeline._measure_audio_duration_seconds", return_value=2.0)
    def test_cli_reuses_existing_manifest(self, measure):
        from pptx import Presentation
        from src.main import main
        from src.logging_config import shutdown_logging
        self.addCleanup(shutdown_logging)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            presentation = Presentation()
            slide = presentation.slides.add_slide(presentation.slide_layouts[1])
            slide.notes_slide.notes_text_frame.text = 'Hello'
            presentation.save(root / 'input.pptx')
            (root / 'words.json').write_text(json.dumps([
                dict(text='Hello', offset_seconds=.2, duration_seconds=.5)
            ]), encoding='utf-8')
            (root / 'manifest.json').write_text(json.dumps(dict(slides=[
                dict(slide_num=1, audio_file='slide_001.mp3', word_boundaries_file='words.json')
            ])), encoding='utf-8')
            with patch('sys.argv', ['pptx2video', str(root / 'input.pptx'),
                       '--audio-output-dir', tmp, '--vtt-output-dir', str(root / 'vtt'),
                       '--output', str(root / 'slides.json'), '--subtitles-output', '',
                       '--no-file-log']), patch(
                'src.main.generate_audio_files'
            ) as generate:
                main()
            generate.assert_not_called()
            self.assertIn('00:00:00.200 --> 00:00:00.700',
                          (root / 'vtt' / 'slide_001.vtt').read_text(encoding='utf-8'))
