import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src import ppt_automation
from src.exceptions import (
    AudioInsertionError,
    PowerPointLaunchError,
    VideoExportError,
    VideoExportTimeoutError,
)


class FakePlaySettings:
    def __init__(self):
        self.PlayOnEntry = False
        self.HideWhileNotPlaying = False


class FakeAnimationSettings:
    def __init__(self):
        self.PlaySettings = FakePlaySettings()


class FakeShape:
    def __init__(self, file_name, left, top, width, height):
        self.file_name = file_name
        self.Left = left
        self.Top = top
        self.Width = width
        self.Height = height
        self.AnimationSettings = FakeAnimationSettings()


class FakeShapes:
    def __init__(self):
        self.added = []

    def AddMediaObject2(self, FileName, LinkToFile, SaveWithDocument, Left, Top, Width, Height):
        shape = FakeShape(FileName, Left, Top, Width, Height)
        self.added.append(shape)
        return shape


class FakeSlide:
    def __init__(self, slide_num):
        self.slide_num = slide_num
        self.Shapes = FakeShapes()


class FakeSlides:
    def __init__(self, slide_nums):
        self._slides = {n: FakeSlide(n) for n in slide_nums}

    def __call__(self, slide_num):
        if slide_num not in self._slides:
            raise Exception(f"Slide {slide_num} does not exist")
        return self._slides[slide_num]


class FakePageSetup:
    def __init__(self, slide_width=960):
        self.SlideWidth = slide_width


class FakePresentation:
    def __init__(
        self,
        slide_nums,
        slide_width=960,
        video_status_sequence=None,
        write_output_on_create_video=True,
        fail_save_as=False,
    ):
        self.Slides = FakeSlides(slide_nums)
        self.PageSetup = FakePageSetup(slide_width)
        self.saved_to = None
        self.closed = False
        self._fail_save_as = fail_save_as

        # --- export_video / CreateVideo simulation ---
        # Each read of CreateVideoStatus advances through this sequence,
        # then repeats the last value - simulating PowerPoint's async
        # export progressing through states over successive polls.
        self._video_status_sequence = (
            list(video_status_sequence)
            if video_status_sequence is not None
            else [ppt_automation.PP_MEDIA_TASK_STATUS_DONE]
        )
        self._video_status_index = 0
        self._write_output_on_create_video = write_output_on_create_video
        self.create_video_calls = []

    def SaveAs(self, path):
        if self._fail_save_as:
            raise Exception("simulated disk full error")
        self.saved_to = path

    def Close(self):
        self.closed = True

    def CreateVideo(
        self,
        FileName,
        UseTimingsAndNarrations,
        DefaultSlideDuration,
        VertResolution,
        FramesPerSecond,
        Quality,
    ):
        self.create_video_calls.append(
            {
                "FileName": FileName,
                "UseTimingsAndNarrations": UseTimingsAndNarrations,
                "DefaultSlideDuration": DefaultSlideDuration,
                "VertResolution": VertResolution,
                "FramesPerSecond": FramesPerSecond,
                "Quality": Quality,
            }
        )
        if self._write_output_on_create_video:
            out = Path(FileName)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fake-mp4-bytes")

    @property
    def CreateVideoStatus(self):
        idx = min(self._video_status_index, len(self._video_status_sequence) - 1)
        value = self._video_status_sequence[idx]
        self._video_status_index += 1
        return value


class FakePresentations:
    def __init__(self, presentation, fail_open=False):
        self._presentation = presentation
        self.opened_with = None
        self._fail_open = fail_open

    def Open(self, path, WithWindow=True):
        if self._fail_open:
            raise Exception("simulated COM error: presentation is corrupt")
        self.opened_with = (path, WithWindow)
        return self._presentation


class FakeApplication:
    def __init__(self, presentation, fail_open=False):
        self.Presentations = FakePresentations(presentation, fail_open=fail_open)
        self.Visible = False


class PptAutomationTests(unittest.TestCase):
    def test_require_windows_raises_on_non_windows(self):
        with mock.patch("sys.platform", "linux"):
            with self.assertRaises(PowerPointLaunchError):
                ppt_automation._require_windows()

    def test_build_slide_audio_map_skips_entries_without_audio(self):
        manifest = {
            "slides": [
                {"slide_num": 1, "audio_file": "slide_001.mp3"},
                {"slide_num": 2, "audio_file": None},
            ]
        }
        result = ppt_automation._build_slide_audio_map(manifest, Path("/tmp/audio"))
        self.assertEqual(list(result.keys()), [1])
        self.assertEqual(result[1], Path("/tmp/audio/slide_001.mp3"))

    def test_insert_audio_reports_progress_for_inserted_and_skipped_slides(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pptx_path = tmp_path / "deck.pptx"
            pptx_path.write_bytes(b"fake-pptx")

            audio_dir = tmp_path / "audio"
            audio_dir.mkdir()
            (audio_dir / "slide_002.mp3").write_bytes(b"fake-audio")
            # slide_003.mp3 deliberately not created, to trigger a "skipped"
            # progress event (missing audio file).

            manifest = {
                "slides": [
                    {"slide_num": 2, "audio_file": "slide_002.mp3"},
                    {"slide_num": 3, "audio_file": "slide_003.mp3"},
                ]
            }

            presentation = FakePresentation(slide_nums=[1, 2, 3], slide_width=960)
            app = FakeApplication(presentation)

            progress_events = []

            def track_progress(current, total, slide_num, status):
                progress_events.append((current, total, slide_num, status))

            with mock.patch("sys.platform", "win32"):
                ppt_automation.insert_audio(
                    pptx_path,
                    manifest,
                    audio_dir,
                    powerpoint_app=app,
                    progress_callback=track_progress,
                )

            # One callback per slide referenced in the manifest (2 total),
            # in order, each correctly labeled inserted vs skipped.
            self.assertEqual(
                progress_events,
                [(1, 2, 2, "inserted"), (2, 2, 3, "skipped")],
            )

    def test_insert_audio_works_without_progress_callback(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pptx_path = tmp_path / "deck.pptx"
            pptx_path.write_bytes(b"fake-pptx")

            audio_dir = tmp_path / "audio"
            audio_dir.mkdir()
            (audio_dir / "slide_002.mp3").write_bytes(b"fake-audio")

            manifest = {"slides": [{"slide_num": 2, "audio_file": "slide_002.mp3"}]}
            presentation = FakePresentation(slide_nums=[1, 2, 3], slide_width=960)
            app = FakeApplication(presentation)

            # Should not raise even though no progress_callback is passed.
            with mock.patch("sys.platform", "win32"):
                result = ppt_automation.insert_audio(
                    pptx_path,
                    manifest,
                    audio_dir,
                    powerpoint_app=app,
                )
            self.assertEqual(result["inserted_slides"], [2])

    def test_insert_audio_inserts_only_matching_slides(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pptx_path = tmp_path / "deck.pptx"
            pptx_path.write_bytes(b"fake-pptx")

            audio_dir = tmp_path / "audio"
            audio_dir.mkdir()
            (audio_dir / "slide_002.mp3").write_bytes(b"fake-audio")
            (audio_dir / "slide_003.mp3").write_bytes(b"fake-audio")

            manifest = {
                "slides": [
                    {"slide_num": 2, "audio_file": "slide_002.mp3"},
                    {"slide_num": 3, "audio_file": "slide_003.mp3"},
                ]
            }

            presentation = FakePresentation(slide_nums=[1, 2, 3, 4, 5], slide_width=960)
            app = FakeApplication(presentation)

            with mock.patch("sys.platform", "win32"):
                result = ppt_automation.insert_audio(
                    pptx_path,
                    manifest,
                    audio_dir,
                    powerpoint_app=app,
                )

            self.assertEqual(sorted(result["inserted_slides"]), [2, 3])
            self.assertEqual(result["skipped_slides"], [])
            self.assertEqual(Path(presentation.saved_to).resolve(), pptx_path.resolve())
            self.assertTrue(presentation.closed)

            # Slides without audio were never touched.
            self.assertEqual(len(presentation.Slides(1).Shapes.added), 0)
            self.assertEqual(len(presentation.Slides(4).Shapes.added), 0)

            # Matching slides got exactly one small icon, tucked top-right.
            slide_2_shape = presentation.Slides(2).Shapes.added[0]
            self.assertEqual(slide_2_shape.Width, ppt_automation.ICON_SIZE_PT)
            self.assertEqual(slide_2_shape.Height, ppt_automation.ICON_SIZE_PT)
            self.assertEqual(slide_2_shape.Top, ppt_automation.ICON_MARGIN_PT)
            expected_left = (
                presentation.PageSetup.SlideWidth
                - ppt_automation.ICON_SIZE_PT
                - ppt_automation.ICON_MARGIN_PT
            )
            self.assertEqual(slide_2_shape.Left, expected_left)

            # Hidden while not playing, and PlayOnEntry set (empirically
            # required for PowerPoint's video export to use this audio).
            self.assertTrue(slide_2_shape.AnimationSettings.PlaySettings.HideWhileNotPlaying)
            self.assertTrue(slide_2_shape.AnimationSettings.PlaySettings.PlayOnEntry)

    def test_insert_audio_skips_missing_audio_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pptx_path = tmp_path / "deck.pptx"
            pptx_path.write_bytes(b"fake-pptx")

            audio_dir = tmp_path / "audio"
            audio_dir.mkdir()
            # Note: slide_002.mp3 is referenced but never actually created.

            manifest = {"slides": [{"slide_num": 2, "audio_file": "slide_002.mp3"}]}

            presentation = FakePresentation(slide_nums=[1, 2])
            app = FakeApplication(presentation)

            with mock.patch("sys.platform", "win32"):
                result = ppt_automation.insert_audio(
                    pptx_path,
                    manifest,
                    audio_dir,
                    powerpoint_app=app,
                )

            self.assertEqual(result["inserted_slides"], [])
            self.assertEqual(len(result["skipped_slides"]), 1)
            self.assertEqual(result["skipped_slides"][0]["slide_num"], 2)
            self.assertIn("not found", result["skipped_slides"][0]["reason"])

    def test_insert_audio_skips_slide_not_in_presentation(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pptx_path = tmp_path / "deck.pptx"
            pptx_path.write_bytes(b"fake-pptx")

            audio_dir = tmp_path / "audio"
            audio_dir.mkdir()
            (audio_dir / "slide_099.mp3").write_bytes(b"fake-audio")

            manifest = {"slides": [{"slide_num": 99, "audio_file": "slide_099.mp3"}]}

            # Presentation only has slides 1-3, so slide 99 does not exist.
            presentation = FakePresentation(slide_nums=[1, 2, 3])
            app = FakeApplication(presentation)

            with mock.patch("sys.platform", "win32"):
                result = ppt_automation.insert_audio(
                    pptx_path,
                    manifest,
                    audio_dir,
                    powerpoint_app=app,
                )

            self.assertEqual(result["inserted_slides"], [])
            self.assertEqual(len(result["skipped_slides"]), 1)
            self.assertEqual(result["skipped_slides"][0]["slide_num"], 99)

    def test_insert_audio_raises_when_pptx_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_path = Path(tmp) / "does_not_exist.pptx"
            manifest = {"slides": []}
            app = FakeApplication(FakePresentation(slide_nums=[]))

            with mock.patch("sys.platform", "win32"):
                with self.assertRaises(FileNotFoundError):
                    ppt_automation.insert_audio(
                        missing_path,
                        manifest,
                        Path(tmp),
                        powerpoint_app=app,
                    )

    def test_export_video_success_uses_expected_default_parameters(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pptx_path = tmp_path / "deck.pptx"
            pptx_path.write_bytes(b"fake-pptx")
            video_path = tmp_path / "out" / "deck.mp4"

            presentation = FakePresentation(
                slide_nums=[1, 2, 3],
                video_status_sequence=[
                    ppt_automation.PP_MEDIA_TASK_STATUS_QUEUED,
                    ppt_automation.PP_MEDIA_TASK_STATUS_IN_PROGRESS,
                    ppt_automation.PP_MEDIA_TASK_STATUS_IN_PROGRESS,
                    ppt_automation.PP_MEDIA_TASK_STATUS_DONE,
                ],
            )
            app = FakeApplication(presentation)

            progress_events = []

            with mock.patch("sys.platform", "win32"):
                result = ppt_automation.export_video(
                    pptx_path,
                    video_path,
                    powerpoint_app=app,
                    poll_interval_seconds=0,
                    progress_callback=progress_events.append,
                )

            self.assertEqual(result["output_path"], str(video_path.resolve()))
            self.assertGreaterEqual(result["elapsed_seconds"], 0)
            self.assertTrue(video_path.exists())
            self.assertTrue(presentation.closed)

            # Progress callback fires once per distinct status, in order.
            self.assertEqual(progress_events, ["queued", "in_progress", "done"])

            # Defaults match PowerPoint's "HD (720p)" / "Don't use recorded
            # timings" / 5 seconds-per-slide export dialog settings.
            call = presentation.create_video_calls[0]
            self.assertEqual(call["VertResolution"], 720)
            self.assertEqual(call["FramesPerSecond"], 30)
            self.assertEqual(call["Quality"], 85)
            self.assertEqual(call["DefaultSlideDuration"], 5.0)
            self.assertEqual(call["UseTimingsAndNarrations"], False)

    def test_export_video_accepts_custom_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pptx_path = tmp_path / "deck.pptx"
            pptx_path.write_bytes(b"fake-pptx")
            video_path = tmp_path / "deck.mp4"

            presentation = FakePresentation(slide_nums=[1])
            app = FakeApplication(presentation)

            with mock.patch("sys.platform", "win32"):
                ppt_automation.export_video(
                    pptx_path,
                    video_path,
                    resolution_height=1080,
                    powerpoint_app=app,
                    poll_interval_seconds=0,
                )

            self.assertEqual(presentation.create_video_calls[0]["VertResolution"], 1080)

    def test_export_video_raises_on_failed_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pptx_path = tmp_path / "deck.pptx"
            pptx_path.write_bytes(b"fake-pptx")
            video_path = tmp_path / "deck.mp4"

            presentation = FakePresentation(
                slide_nums=[1],
                video_status_sequence=[
                    ppt_automation.PP_MEDIA_TASK_STATUS_IN_PROGRESS,
                    ppt_automation.PP_MEDIA_TASK_STATUS_FAILED,
                ],
            )
            app = FakeApplication(presentation)

            with mock.patch("sys.platform", "win32"):
                with self.assertRaises(VideoExportError):
                    ppt_automation.export_video(
                        pptx_path,
                        video_path,
                        powerpoint_app=app,
                        poll_interval_seconds=0,
                    )

    def test_export_video_times_out_when_stuck_in_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pptx_path = tmp_path / "deck.pptx"
            pptx_path.write_bytes(b"fake-pptx")
            video_path = tmp_path / "deck.mp4"

            # Never reaches DONE/FAILED - stays stuck at IN_PROGRESS forever.
            presentation = FakePresentation(
                slide_nums=[1],
                video_status_sequence=[ppt_automation.PP_MEDIA_TASK_STATUS_IN_PROGRESS],
            )
            app = FakeApplication(presentation)

            with mock.patch("sys.platform", "win32"):
                with self.assertRaises(VideoExportTimeoutError) as ctx:
                    ppt_automation.export_video(
                        pptx_path,
                        video_path,
                        powerpoint_app=app,
                        timeout_seconds=0.05,
                        poll_interval_seconds=0.01,
                    )

            # VideoExportTimeoutError must also be catchable as the builtin
            # TimeoutError, so code that only knows to catch TimeoutError
            # generically keeps working.
            self.assertIsInstance(ctx.exception, TimeoutError)

    def test_export_video_raises_when_output_file_missing_despite_done_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pptx_path = tmp_path / "deck.pptx"
            pptx_path.write_bytes(b"fake-pptx")
            video_path = tmp_path / "deck.mp4"

            # PowerPoint reports "done" but never actually wrote the file -
            # the safety net should catch this instead of reporting success.
            presentation = FakePresentation(
                slide_nums=[1],
                video_status_sequence=[ppt_automation.PP_MEDIA_TASK_STATUS_DONE],
                write_output_on_create_video=False,
            )
            app = FakeApplication(presentation)

            with mock.patch("sys.platform", "win32"):
                with self.assertRaises(VideoExportError):
                    ppt_automation.export_video(
                        pptx_path,
                        video_path,
                        powerpoint_app=app,
                        poll_interval_seconds=0,
                    )

    def test_export_video_raises_when_pptx_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            missing_path = tmp_path / "does_not_exist.pptx"
            video_path = tmp_path / "deck.mp4"
            app = FakeApplication(FakePresentation(slide_nums=[]))

            with mock.patch("sys.platform", "win32"):
                with self.assertRaises(FileNotFoundError):
                    ppt_automation.export_video(
                        missing_path,
                        video_path,
                        powerpoint_app=app,
                        poll_interval_seconds=0,
                    )

    def test_insert_audio_raises_audioinsertionerror_when_save_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pptx_path = tmp_path / "deck.pptx"
            pptx_path.write_bytes(b"fake-pptx")

            audio_dir = tmp_path / "audio"
            audio_dir.mkdir()
            (audio_dir / "slide_002.mp3").write_bytes(b"fake-audio")

            manifest = {"slides": [{"slide_num": 2, "audio_file": "slide_002.mp3"}]}

            presentation = FakePresentation(slide_nums=[1, 2, 3], fail_save_as=True)
            app = FakeApplication(presentation)

            with mock.patch("sys.platform", "win32"):
                with self.assertRaises(AudioInsertionError):
                    ppt_automation.insert_audio(
                        pptx_path,
                        manifest,
                        audio_dir,
                        powerpoint_app=app,
                    )

            # Even though saving failed, the presentation must still have
            # been closed - the cleanup context manager doesn't skip Close()
            # just because the code inside raised.
            self.assertTrue(presentation.closed)

    def test_insert_audio_raises_powerpointlauncherror_when_open_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pptx_path = tmp_path / "deck.pptx"
            pptx_path.write_bytes(b"fake-pptx")
            audio_dir = tmp_path / "audio"
            audio_dir.mkdir()

            manifest = {"slides": []}
            presentation = FakePresentation(slide_nums=[])
            app = FakeApplication(presentation, fail_open=True)

            with mock.patch("sys.platform", "win32"):
                with self.assertRaises(PowerPointLaunchError):
                    ppt_automation.insert_audio(
                        pptx_path,
                        manifest,
                        audio_dir,
                        powerpoint_app=app,
                    )

    def test_export_video_raises_powerpointlauncherror_when_open_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pptx_path = tmp_path / "deck.pptx"
            pptx_path.write_bytes(b"fake-pptx")
            video_path = tmp_path / "deck.mp4"

            presentation = FakePresentation(slide_nums=[])
            app = FakeApplication(presentation, fail_open=True)

            with mock.patch("sys.platform", "win32"):
                with self.assertRaises(PowerPointLaunchError):
                    ppt_automation.export_video(
                        pptx_path,
                        video_path,
                        powerpoint_app=app,
                        poll_interval_seconds=0,
                    )


if __name__ == "__main__":
    unittest.main()
