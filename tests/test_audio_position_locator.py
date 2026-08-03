import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import numpy as np
from pydub import AudioSegment
from pydub.generators import Sine

from src.audio_position_locator import (
    SAMPLE_RATE,
    find_best_offset_seconds,
    locate_slide_start_and_end_times,
    locate_slide_start_times,
)

_FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None


def _sine_mp3(path: Path, freq: int, duration_ms: int) -> None:
    Sine(freq).to_audio_segment(duration=duration_ms).export(path, format="mp3")


def _noise_segment(duration_seconds: float, seed: int) -> AudioSegment:
    # White noise, not a tone - a periodic signal (like Sine) gives
    # cross-correlation multiple near-equal peaks (one per wave period),
    # which would mask the stretch-bias effect these tests are after.
    # Speech has a broadband, non-periodic spectrum, which noise is a much
    # closer (if crude) stand-in for than a pure tone.
    rng = np.random.default_rng(seed)
    n = int(duration_seconds * SAMPLE_RATE)
    samples = (rng.standard_normal(n) * 3000).astype(np.int16)
    return AudioSegment(samples.tobytes(), frame_rate=SAMPLE_RATE, sample_width=2, channels=1)


def _stretch(segment: AudioSegment, ratio: float) -> AudioSegment:
    # Simulates PowerPoint's export very slightly time-stretching embedded
    # audio relative to the source mp3 (see audio_position_locator.py's
    # DEFAULT_ANCHOR_SECONDS docstring) - reinterpreting the same samples at
    # a different frame rate, then resampling back to the original rate,
    # changes both duration and pitch, same as real playback-speed changes.
    return segment._spawn(
        segment.raw_data, overrides={"frame_rate": int(segment.frame_rate * ratio)}
    ).set_frame_rate(segment.frame_rate)


def _wav_to_mp4(wav_path: Path, mp4_path: Path) -> None:
    # Audio-only "video" container - locate_slide_start_times only ever
    # extracts the audio track, so this is a faithful enough stand-in for a
    # real exported MP4 without needing PowerPoint/an actual video stream.
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav_path), "-c:a", "aac", str(mp4_path)],
        check=True,
        capture_output=True,
    )


class FindBestOffsetSecondsTests(unittest.TestCase):
    def test_finds_true_offset_within_search_window(self):
        sample_rate = 8000
        rng = np.random.default_rng(0)
        # Noise-like "full track" (stands in for real speech's broadband
        # spectrum better than a pure tone would) with a distinctive clip
        # embedded 3.7s in - deliberately not where a naive prediction of
        # 2.0s would look, to prove the search actually locates it rather
        # than just returning the prediction.
        full = rng.standard_normal(sample_rate * 10).astype(np.float32)
        clip = rng.standard_normal(sample_rate * 2).astype(np.float32)
        true_offset_seconds = 3.7
        start_sample = int(true_offset_seconds * sample_rate)
        full[start_sample:start_sample + len(clip)] = clip

        measured = find_best_offset_seconds(
            full, clip, predicted_start_seconds=2.0, sample_rate=sample_rate, search_window_seconds=10.0
        )

        self.assertAlmostEqual(measured, true_offset_seconds, delta=0.05)

    def test_returns_prediction_when_track_too_short_to_search(self):
        clip = np.zeros(100, dtype=np.float32)
        short_track = np.zeros(10, dtype=np.float32)

        measured = find_best_offset_seconds(short_track, clip, predicted_start_seconds=1.23)

        self.assertEqual(measured, 1.23)


@unittest.skipUnless(_FFMPEG_AVAILABLE, "ffmpeg not available on PATH")
class LocateSlideStartTimesTests(unittest.TestCase):
    def test_measures_real_positions_despite_extra_gaps_not_in_prediction(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            audio_dir = tmp_path

            # Two distinct-frequency slides, each with its own mp3 (as the
            # real pipeline would produce).
            _sine_mp3(audio_dir / "slide_001.mp3", freq=440, duration_ms=2000)
            _sine_mp3(audio_dir / "slide_002.mp3", freq=880, duration_ms=1500)

            # Build the "exported video"'s audio track with EXTRA padding a
            # naive sum-of-durations prediction wouldn't know about - this
            # is standing in for the drift the whole module exists to
            # correct for.
            slide1 = Sine(440).to_audio_segment(duration=2000)
            slide2 = Sine(880).to_audio_segment(duration=1500)
            from pydub import AudioSegment
            full_track = (
                AudioSegment.silent(duration=300)  # slide 1 doesn't start at t=0
                + slide1
                + AudioSegment.silent(duration=700)  # extra "dead space" before slide 2
                + slide2
            )
            full_wav = tmp_path / "full.wav"
            full_track.export(full_wav, format="wav")
            full_mp4 = tmp_path / "full.mp4"
            _wav_to_mp4(full_wav, full_mp4)

            slides = [
                {"slide_num": 1, "notes": "one"},
                {"slide_num": 2, "notes": "two"},
            ]
            manifest = {
                "output_dir": str(audio_dir),
                "slides": [
                    {"slide_num": 1, "audio_file": "slide_001.mp3"},
                    {"slide_num": 2, "audio_file": "slide_002.mp3"},
                ],
            }

            start_times, warnings = locate_slide_start_times(
                full_mp4, slides, manifest, audio_dir, search_window_seconds=5.0
            )

            self.assertEqual(warnings, [])
            # Naive prediction would say slide 1 starts at 0.0s and slide 2
            # at 2.0s - the measured values should reflect the real extra
            # padding instead (0.3s and 3.0s respectively).
            self.assertAlmostEqual(start_times[1], 0.3, delta=0.05)
            self.assertAlmostEqual(start_times[2], 3.0, delta=0.05)

    def test_anchor_avoids_bias_from_slightly_time_stretched_embedded_audio(self):
        # Regression test for a real symptom reported against this feature:
        # correlating the *whole* (multi-minute) clip against a slightly
        # time-stretched copy of itself embedded in the video produced a
        # measured start time biased by several hundred ms to multiple
        # seconds - worse than the drift this module exists to fix in the
        # first place. Anchoring on a short leading window (see
        # DEFAULT_ANCHOR_SECONDS) keeps that bias negligible regardless of
        # how long the full slide's audio is.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            audio_dir = tmp_path

            original = _noise_segment(duration_seconds=60.0, seed=1)
            original.export(audio_dir / "slide_001.mp3", format="mp3")

            # The "embedded in the export" copy is 0.1% faster/shorter than
            # the source mp3 - matching the ratio observed on a real deck
            # (see CHANGELOG v0.6.0 / project discussion).
            stretched = _stretch(original, ratio=1.001)
            true_start = 0.3
            full_track = AudioSegment.silent(duration=int(true_start * 1000)) + stretched
            full_wav = tmp_path / "full.wav"
            full_track.export(full_wav, format="wav")
            full_mp4 = tmp_path / "full.mp4"
            _wav_to_mp4(full_wav, full_mp4)

            slides = [{"slide_num": 1, "notes": "one"}]
            manifest = {
                "output_dir": str(audio_dir),
                "slides": [{"slide_num": 1, "audio_file": "slide_001.mp3"}],
            }

            start_times, warnings = locate_slide_start_times(
                full_mp4, slides, manifest, audio_dir, search_window_seconds=5.0
            )

            self.assertEqual(warnings, [])
            # With DEFAULT_ANCHOR_SECONDS (8s) the accumulated stretch over
            # the anchor is only ~8ms - comfortably inside this tolerance,
            # unlike whole-clip correlation which biases by hundreds of ms
            # on a clip this length (see this file's manual verification in
            # the project discussion for the whole-clip comparison numbers).
            self.assertAlmostEqual(start_times[1], true_start, delta=0.05)

    def test_start_and_end_measured_independently_reflect_real_stretch(self):
        # Regression test for the follow-up finding after the anchor fix
        # (see CHANGELOG v0.6.1's second Fixed entry): a slide's *start*
        # being measured accurately doesn't tell you its own real duration
        # in the export - inferring that from the *next* slide's measured
        # start conflates this slide's own stretch with any gap PowerPoint
        # inserts *between* slides. Measuring the end directly (trailing
        # anchor) instead should recover the real (stretched) duration on
        # its own, with no other slide involved at all.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            audio_dir = tmp_path

            original = _noise_segment(duration_seconds=60.0, seed=2)
            original.export(audio_dir / "slide_001.mp3", format="mp3")
            original_duration = len(original) / 1000.0

            stretched = _stretch(original, ratio=1.001)
            true_start = 0.3
            full_track = AudioSegment.silent(duration=int(true_start * 1000)) + stretched
            full_wav = tmp_path / "full.wav"
            full_track.export(full_wav, format="wav")
            full_mp4 = tmp_path / "full.mp4"
            _wav_to_mp4(full_wav, full_mp4)

            slides = [{"slide_num": 1, "notes": "one"}]
            manifest = {
                "output_dir": str(audio_dir),
                "slides": [{"slide_num": 1, "audio_file": "slide_001.mp3"}],
            }

            bounds, warnings = locate_slide_start_and_end_times(
                full_mp4, slides, manifest, audio_dir, search_window_seconds=5.0
            )

            self.assertEqual(warnings, [])
            measured_start, measured_end = bounds[1]
            self.assertAlmostEqual(measured_start, true_start, delta=0.05)

            measured_duration = measured_end - measured_start
            # _stretch(ratio=1.001) shortens playback duration by ~1/1.001
            # (samples reinterpreted at a slightly higher rate then
            # resampled back) - the measured (end - start) should reflect
            # that real, shortened duration, not the original mp3's own
            # (unstretched) duration.
            expected_duration = original_duration / 1.001
            self.assertAlmostEqual(measured_duration, expected_duration, delta=0.1)
            self.assertLess(measured_duration, original_duration - 0.02)

    def test_global_scale_correction_multiplies_every_returned_time(self):
        # Regression test for the fourth v0.6.1 fix (see CHANGELOG): a real
        # deck showed this module's own measured times running consistently
        # ~0.12% "early" relative to true elapsed video time, confirmed via
        # the project owner's precise real-playback checks - NOT explained
        # by PowerPoint's export, the exported file's own A/V sync, or this
        # module's ffmpeg/pydub resampling (all independently ruled out).
        # global_scale_correction is the calibrated fix: every returned
        # time (both locate_slide_start_times and
        # locate_slide_start_and_end_times) should simply be the
        # uncorrected measurement multiplied by this factor.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            audio_dir = tmp_path

            clip = _noise_segment(duration_seconds=20.0, seed=3)
            clip.export(audio_dir / "slide_001.mp3", format="mp3")

            true_start = 2.0
            full_track = AudioSegment.silent(duration=int(true_start * 1000)) + clip
            full_wav = tmp_path / "full.wav"
            full_track.export(full_wav, format="wav")
            full_mp4 = tmp_path / "full.mp4"
            _wav_to_mp4(full_wav, full_mp4)

            slides = [{"slide_num": 1, "notes": "one"}]
            manifest = {
                "output_dir": str(audio_dir),
                "slides": [{"slide_num": 1, "audio_file": "slide_001.mp3"}],
            }

            uncorrected_starts, _ = locate_slide_start_times(
                full_mp4, slides, manifest, audio_dir, search_window_seconds=5.0
            )
            k = 1.00121
            corrected_starts, _ = locate_slide_start_times(
                full_mp4, slides, manifest, audio_dir, search_window_seconds=5.0,
                global_scale_correction=k,
            )
            self.assertAlmostEqual(corrected_starts[1], uncorrected_starts[1] * k, places=6)

            uncorrected_bounds, _ = locate_slide_start_and_end_times(
                full_mp4, slides, manifest, audio_dir, search_window_seconds=5.0
            )
            corrected_bounds, _ = locate_slide_start_and_end_times(
                full_mp4, slides, manifest, audio_dir, search_window_seconds=5.0,
                global_scale_correction=k,
            )
            self.assertAlmostEqual(corrected_bounds[1][0], uncorrected_bounds[1][0] * k, places=6)
            self.assertAlmostEqual(corrected_bounds[1][1], uncorrected_bounds[1][1] * k, places=6)

    def test_missing_audio_file_is_skipped_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            audio_dir = tmp_path

            slide1 = Sine(440).to_audio_segment(duration=1000)
            full_wav = tmp_path / "full.wav"
            slide1.export(full_wav, format="wav")
            full_mp4 = tmp_path / "full.mp4"
            _wav_to_mp4(full_wav, full_mp4)

            slides = [{"slide_num": 1, "notes": "one"}]
            manifest = {
                "output_dir": str(audio_dir),
                "slides": [{"slide_num": 1, "audio_file": "missing.mp3"}],
            }

            start_times, warnings = locate_slide_start_times(full_mp4, slides, manifest, audio_dir)

            self.assertEqual(start_times, {})
            self.assertEqual(len(warnings), 1)
            self.assertIn("audio file not found", warnings[0])


if __name__ == "__main__":
    unittest.main()
