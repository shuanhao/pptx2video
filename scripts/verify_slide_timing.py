"""Verify PowerPoint's real per-slide timing in an exported MP4 against the
naive "sum of embedded audio durations" prediction Phase 4's SRT-merging
logic is considering using.

Why this exists: multiple independent user reports (e.g. a Microsoft Q&A
thread - see the project discussion this script was written in response to)
describe PowerPoint's "Create a Video" export adding inconsistent extra
"dead space" (silence) after a slide's audio finishes, even when the slide's
duration is supposed to be driven entirely by its embedded audio - anywhere
from 2 to 15 seconds, and not consistently on every slide. If that's
happening in this project's decks, computing subtitle timestamps by just
adding up mp3 file durations (the simple approach) would silently drift out
of sync with the real exported video, slide by slide. This script instead
measures where each slide's audio *actually* starts in the real exported
MP4 - via cross-correlation against that slide's own known mp3, not by
trusting any PowerPoint-reported number - and compares it to the naive
prediction, so it can be decided whether the simple approach is safe to
build into Phase 4, or whether something more robust (locating each slide's
real audio start directly in the final video, every time) is needed instead.

Requires numpy and scipy (NOT normal project dependencies - only needed to
run this one-off diagnostic script, not part of the pipeline itself):
    pip install numpy scipy

Also requires ffmpeg/ffprobe on PATH (already a project prerequisite - see
tts.py's FileNotFoundError hint) to extract the MP4's audio track.

Usage:
    python scripts/verify_slide_timing.py <final.mp4> <manifest.json> <original.pptx> [--default-slide-duration 5.0]

Where:
    final.mp4       - the video exported by ppt_automation.export_video()
    manifest.json   - the manifest written by tts.generate_audio_files()
                       (has each audio slide's mp3 filename + output_dir)
    original.pptx   - the source deck (used only to get the full slide
                       list, including slides with no notes/no audio, so
                       gaps are accounted for in the predicted timeline)

What to look for when you run this:

- A table of predicted vs. measured start time for every slide with audio,
  and the delta between them.
- "Max |delta| observed" at the end. If everything stayed under ~0.5s, the
  naive "sum of mp3 durations" approach is safe to build the SRT merge on.
  If it grows slide over slide (drift) or jumps unpredictably, the
  dead-space issue is real for this project's decks and Phase 4's merge
  logic needs the more robust (cross-correlation-based) approach instead of
  the simple one.
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from pydub import AudioSegment
from scipy.signal import correlate

from src.pptx_parser import extract_notes

# Downsampled rate used for cross-correlation - plenty for locating a
# speech onset to well under 100ms precision, and keeps the FFT-based
# correlation fast even for long decks.
SAMPLE_RATE = 8000

# How far around the naive prediction to search for the real match -
# generous relative to the 2-15s dead-space reports this script is
# investigating, while still bounding the search (and ruling out false
# matches against a completely different slide's audio far away in the
# track).
SEARCH_WINDOW_SECONDS = 30.0

# A delta beyond this is flagged as a likely dead-space/drift symptom
# rather than ordinary correlation noise.
DRIFT_WARNING_THRESHOLD_SECONDS = 0.5


def _extract_audio_track(video_path: Path, out_wav: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(video_path),
            "-ar", str(SAMPLE_RATE), "-ac", "1", "-vn",
            str(out_wav),
        ],
        check=True,
        capture_output=True,
    )


def _load_mono_array(audio_path: Path) -> np.ndarray:
    audio = AudioSegment.from_file(audio_path).set_frame_rate(SAMPLE_RATE).set_channels(1)
    return np.array(audio.get_array_of_samples()).astype(np.float32)


def _normalize(x: np.ndarray) -> np.ndarray:
    std = x.std()
    return (x - x.mean()) / std if std > 1e-6 else x - x.mean()


def find_best_offset_seconds(
    full_track: np.ndarray,
    clip: np.ndarray,
    predicted_start_seconds: float,
    sample_rate: int = SAMPLE_RATE,
    search_window_seconds: float = SEARCH_WINDOW_SECONDS,
) -> float:
    """Cross-correlate ``clip`` against a window of ``full_track`` centered
    on ``predicted_start_seconds`` (+/- ``search_window_seconds``),
    returning the real start time (seconds) that best matches.

    Uses FFT-based correlation (``scipy.signal.correlate(..., method="fft")``)
    rather than ``numpy.correlate``'s direct method, which is O(n*m) and far
    too slow for anything beyond a few seconds of audio at this sample rate.
    Both signals are mean/std-normalized first so the match is driven by
    waveform shape, not loudness.
    """
    center = int(predicted_start_seconds * sample_rate)
    window = int(search_window_seconds * sample_rate)
    lo = max(0, center - window)
    hi = min(len(full_track), center + window + len(clip))
    segment = full_track[lo:hi]

    if len(segment) < len(clip) or len(clip) == 0:
        return predicted_start_seconds  # not enough data to search - give up gracefully

    correlation = correlate(_normalize(segment), _normalize(clip), mode="valid", method="fft")
    best_index = int(np.argmax(correlation))
    return (lo + best_index) / sample_rate


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("video_path", type=Path)
    parser.add_argument("manifest_path", type=Path)
    parser.add_argument("pptx_path", type=Path)
    parser.add_argument("--default-slide-duration", type=float, default=5.0)
    args = parser.parse_args()

    manifest = json.loads(args.manifest_path.read_text(encoding="utf-8"))
    audio_dir = Path(manifest.get("output_dir") or args.manifest_path.parent)
    audio_by_slide = {int(e["slide_num"]): e["audio_file"] for e in manifest.get("slides", [])}

    slides = sorted(extract_notes(str(args.pptx_path)), key=lambda s: int(s["slide_num"]))

    print(f"Extracting audio track from {args.video_path} ...")
    with tempfile.TemporaryDirectory() as tmp:
        full_wav = Path(tmp) / "full.wav"
        _extract_audio_track(args.video_path, full_wav)
        full_track = _load_mono_array(full_wav)

        predicted_start = 0.0
        max_abs_delta = 0.0
        print(f"\n{'slide':>5} {'predicted':>10} {'measured':>10} {'delta':>8}")

        for slide in slides:
            slide_num = int(slide["slide_num"])
            audio_file = audio_by_slide.get(slide_num)

            if audio_file is None:
                # No narration - this slide occupies default_slide_duration
                # seconds with nothing to cross-correlate against, so it's
                # skipped from measurement (but still advances
                # predicted_start for the slides after it).
                print(f"{slide_num:>5} {predicted_start:>9.2f}s   (no audio - default duration)")
                predicted_start += args.default_slide_duration
                continue

            mp3_path = audio_dir / audio_file
            clip = _load_mono_array(mp3_path)
            clip_duration = len(clip) / SAMPLE_RATE

            measured_start = find_best_offset_seconds(full_track, clip, predicted_start)
            delta = measured_start - predicted_start
            max_abs_delta = max(max_abs_delta, abs(delta))

            flag = "  <-- possible dead-space drift" if abs(delta) > DRIFT_WARNING_THRESHOLD_SECONDS else ""
            print(f"{slide_num:>5} {predicted_start:>9.2f}s {measured_start:>9.2f}s {delta:>+7.2f}s{flag}")

            predicted_start += clip_duration

        print(f"\nMax |delta| observed: {max_abs_delta:.2f}s")
        if max_abs_delta > DRIFT_WARNING_THRESHOLD_SECONDS:
            print(
                "WARNING: predicted and measured slide start times drift "
                "apart - the naive 'sum of mp3 durations' approach is NOT "
                "safe to use for SRT merging as-is. This matches the "
                "reported PowerPoint dead-space export issue; Phase 4's "
                "merge logic will need to locate each slide's real audio "
                "start in the exported video directly, not predict it."
            )
        else:
            print(
                "Predicted and measured slide start times stayed closely "
                "in sync - the naive 'sum of mp3 durations' approach looks "
                "safe to use for SRT merging."
            )


if __name__ == "__main__":
    main()
