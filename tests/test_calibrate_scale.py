import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from pydub import AudioSegment

ROOT = Path(__file__).resolve().parent.parent
_FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None

# scripts/ isn't a package (no __init__.py, matches the rest of scripts/),
# so load calibrate_scale.py by path rather than a normal import - same
# approach other tools would use to reach a standalone script's internals.
_spec = importlib.util.spec_from_file_location("calibrate_scale", ROOT / "scripts" / "calibrate_scale.py")
calibrate_scale = importlib.util.module_from_spec(_spec)
sys.path.insert(0, str(ROOT))
_spec.loader.exec_module(calibrate_scale)


class FitScaleTests(unittest.TestCase):
    def test_recovers_known_constant_exactly(self):
        # Synthetic "measured" times with a known constant k applied to get
        # "observed" times - the fit should recover k exactly (no noise).
        k_true = 1.00121
        measured = [14.30 / k_true, 612.10 / k_true, 1340.85 / k_true, 3021.44 / k_true]
        observed = [m * k_true for m in measured]
        k_fit = calibrate_scale._fit_scale(measured, observed)
        self.assertAlmostEqual(k_fit, k_true, places=9)

    def test_no_correction_needed_gives_one(self):
        measured = [10.0, 20.0, 30.0]
        k_fit = calibrate_scale._fit_scale(measured, measured)
        self.assertAlmostEqual(k_fit, 1.0, places=9)

    def test_all_zero_measurements_raises(self):
        with self.assertRaises(ValueError):
            calibrate_scale._fit_scale([0.0, 0.0], [1.0, 2.0])


@unittest.skipUnless(_FFMPEG_AVAILABLE, "ffmpeg not available")
class CalibrateScaleEndToEndTests(unittest.TestCase):
    def test_cli_recovers_applied_constant_from_observations(self):
        # Build a small synthetic deck (two narrated slides) where the
        # "real" video has each slide's audio placed at a time scaled by a
        # known k relative to a naive back-to-back layout, then feed the
        # script observations equal to those true (scaled) positions and
        # confirm it recovers k close to the true value.
        k_true = 1.002
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            audio_dir = tmp_path

            def _noise_segment(duration_seconds, seed):
                rng = np.random.default_rng(seed)
                n = int(duration_seconds * calibrate_scale.__dict__.get("SAMPLE_RATE", 8000))
                samples = (rng.standard_normal(n) * 3000).astype(np.int16)
                return AudioSegment(
                    samples.tobytes(), frame_rate=8000, sample_width=2, channels=1
                )

            clip1 = _noise_segment(6.0, seed=11)
            clip2 = _noise_segment(6.0, seed=12)
            clip1.export(audio_dir / "slide_001.mp3", format="mp3")
            clip2.export(audio_dir / "slide_002.mp3", format="mp3")

            naive_start_1 = 0.0
            naive_start_2 = 8.0  # a few seconds of gap after slide 1's clip
            true_start_1 = naive_start_1 * k_true
            true_start_2 = naive_start_2 * k_true

            full = AudioSegment.silent(duration=int(true_start_1 * 1000)) + clip1
            gap = int((true_start_2 - (true_start_1 + clip1.duration_seconds)) * 1000)
            full += AudioSegment.silent(duration=max(0, gap))
            full += clip2

            full_wav = tmp_path / "full.wav"
            full.export(full_wav, format="wav")
            full_mp4 = tmp_path / "full.mp4"
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(full_wav), "-c:a", "aac", str(full_mp4)],
                check=True, capture_output=True,
            )

            slides = [{"slide_num": 1, "notes": "one"}, {"slide_num": 2, "notes": "two"}]
            manifest = {
                "output_dir": str(audio_dir),
                "slides": [
                    {"slide_num": 1, "audio_file": "slide_001.mp3"},
                    {"slide_num": 2, "audio_file": "slide_002.mp3"},
                ],
            }
            slides_json = tmp_path / "slides.json"
            slides_json.write_text(json.dumps(slides), encoding="utf-8")
            manifest_json = tmp_path / "manifest.json"
            manifest_json.write_text(json.dumps(manifest), encoding="utf-8")

            observations = {"1": true_start_1, "2": true_start_2}
            observations_json = tmp_path / "observations.json"
            observations_json.write_text(json.dumps(observations), encoding="utf-8")

            report_json = tmp_path / "report.json"
            result = subprocess.run(
                [
                    sys.executable, str(ROOT / "scripts" / "calibrate_scale.py"),
                    "--video", str(full_mp4),
                    "--manifest", str(manifest_json),
                    "--slides-json", str(slides_json),
                    "--observations", str(observations_json),
                    "--search-window-seconds", "5",
                    "--report", str(report_json),
                ],
                check=True, capture_output=True, text=True,
            )
            self.assertIn("Suggested --global-scale-correction", result.stdout)

            report = json.loads(report_json.read_text(encoding="utf-8"))
            self.assertAlmostEqual(report["suggested_global_scale_correction"], k_true, places=2)
            self.assertLess(report["rms_residual_seconds"], 0.5)


if __name__ == "__main__":
    unittest.main()
