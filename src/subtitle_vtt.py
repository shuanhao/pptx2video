"""WebVTT output for original, unpadded per-slide narration audio."""

import math
from html import escape
from pathlib import Path

from src.subtitle_alignment import DEFAULT_TRAILING_GAP_SECONDS
from src.subtitle_pipeline import _build_slide_captions, DEFAULT_SLIDE_DURATION_SECONDS
from src.subtitle_segmenter import DEFAULT_MAX_DISPLAY_WIDTH


def format_vtt(captions, duration_seconds):
    """Validate relative cues without repairing timing or changing segmentation.

    Validate at millisecond precision too, so rounding cannot publish a
    zero-length cue or an overlap. Text is literal, not WebVTT markup.
    """
    if not math.isfinite(duration_seconds) or duration_seconds <= 0:
        raise ValueError("VTT requires a measured positive audio duration")
    lines = ["WEBVTT", ""]
    previous_end = 0
    previous_end_seconds = 0.0
    for index, cue in enumerate(captions, 1):
        start, end = cue["start_seconds"], cue["end_seconds"]
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start:
            raise ValueError(f"cue {index}: invalid time range")
        start_ms, end_ms = round(start * 1000), round(end * 1000)
        if (start < previous_end_seconds or start_ms < previous_end
                or end_ms <= start_ms or end > duration_seconds + .001):
            raise ValueError(f"cue {index}: overlapping, collapsed or out-of-audio time range")
        text = str(cue["text"]).replace("\r\n", "\n").replace("\r", "\n")
        if not text.strip() or any(not line.strip() for line in text.split("\n")):
            raise ValueError(f"cue {index}: empty text or blank cue line")
        def timestamp(milliseconds):
            hours, remainder = divmod(milliseconds, 3600000)
            minutes, remainder = divmod(remainder, 60000)
            seconds, ms = divmod(remainder, 1000)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms:03d}"
        lines.extend([str(index), f"{timestamp(start_ms)} --> {timestamp(end_ms)}",
                      escape(text, quote=False), ""])
        previous_end = end_ms
        previous_end_seconds = end
    return "\n".join(lines) + "\n"


def write_slide_vtt(slides, manifest, audio_dir, output_dir):
    """Write slide_NNN.vtt for narrated slides; fail before writing on bad data.

    Missing narration timing must not silently publish empty captions.
    Silent slides have no audio object and receive no VTT file.
    """
    if manifest.get("preparation") or any(
        Path(entry["audio_file"]).suffix.lower() != ".mp3"
        for entry in manifest.get("slides", [])
    ):
        raise ValueError("Per-slide VTT requires the original MP3 manifest")
    per_slide, warnings = _build_slide_captions(
        slides, manifest, audio_dir, DEFAULT_SLIDE_DURATION_SECONDS,
        DEFAULT_MAX_DISPLAY_WIDTH, DEFAULT_TRAILING_GAP_SECONDS,
    )
    if warnings:
        raise ValueError("Cannot publish per-slide VTT: " + "; ".join(warnings))
    outputs = {}
    for slide in per_slide:
        if not slide["has_narration"]:
            continue
        if not slide["captions"]:
            raise ValueError(f"slide {slide['slide_num']}: narration has no subtitle cues")
        outputs[f"slide_{slide['slide_num']:03d}.vtt"] = format_vtt(
            slide["captions"], slide["duration_seconds"]
        )
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, text in outputs.items():
        (output_dir / filename).write_text(text, encoding="utf-8")
    return [output_dir / filename for filename in outputs]
