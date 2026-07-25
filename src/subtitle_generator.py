import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from pydub import AudioSegment
except ImportError:  # pragma: no cover
    AudioSegment = None


def is_structural_slide(slide: Dict[str, Any]) -> bool:
    title = str(slide.get("title") or "").strip().lower()
    if not title:
        return False

    keywords = [
        "cover",
        "封面",
        "title page",
        "thanks",
        "thank you",
        "thank-you",
        "q&a",
        "qa",
        "questions",
        "closing",
        "結尾",
        "結束",
        "ending",
        "end",
    ]
    return any(keyword in title for keyword in keywords)


def format_timestamp(seconds: float) -> str:
    total_ms = int(seconds * 1000)
    hours, remainder = divmod(total_ms, 3600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, ms = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def _get_audio_duration(audio_path: str | Path) -> Optional[float]:
    if AudioSegment is None:
        return None

    path = Path(audio_path)
    if not path.exists():
        return None

    try:
        audio = AudioSegment.from_file(path)
        return audio.duration_seconds
    except Exception:
        return None


def split_text_into_segments(text: str) -> List[str]:
    cleaned = re.sub(r"\s+", " ", str(text or "").strip())
    if not cleaned:
        return []

    parts = re.split(r"(?<=[。！？.!?])\s+", cleaned)
    segments = [part.strip() for part in parts if part and part.strip()]
    if segments:
        return segments
    return [cleaned]


def build_subtitle_entries(
    slides: List[Dict[str, Any]],
    durations: Optional[List[float]] = None,
    audio_dir: Optional[str | Path] = None,
) -> List[Dict[str, Any]]:
    entries = []
    for index, slide in enumerate(slides, start=1):
        if is_structural_slide(slide):
            continue

        notes = slide.get("subtitle_text") or slide.get("notes")
        if not notes or not str(notes).strip():
            continue

        slide_duration = None
        if durations is not None and index - 1 < len(durations):
            slide_duration = durations[index - 1]

        if slide_duration is None and audio_dir is not None:
            audio_path = Path(audio_dir) / f"slide_{int(slide.get('slide_num', index)):03d}.mp3"
            slide_duration = _get_audio_duration(audio_path)

        segments = split_text_into_segments(notes)
        if not segments:
            continue

        if slide_duration is not None and len(segments) > 1:
            per_segment_duration = slide_duration / len(segments)
        else:
            per_segment_duration = slide_duration

        for segment in segments:
            entries.append({
                "index": len(entries) + 1,
                "slide_num": int(slide.get("slide_num", index)),
                "text": segment,
                "duration": per_segment_duration,
            })
    return entries


def write_srt(
    slides: List[Dict[str, Any]],
    output_path: str | Path,
    durations: Optional[List[float]] = None,
    audio_dir: Optional[str | Path] = None,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    entries = build_subtitle_entries(slides, durations=durations, audio_dir=audio_dir)
    lines = []
    start_time = 0.0

    for entry in entries:
        duration = entry["duration"]
        if duration is None:
            duration = 3.0

        end_time = start_time + duration
        lines.append(str(entry["index"]))
        lines.append(f"{format_timestamp(start_time)} --> {format_timestamp(end_time)}")
        lines.append(entry["text"])
        lines.append("")
        start_time = end_time

    output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return output_path


def load_slides_from_json(json_path: str | Path) -> List[Dict[str, Any]]:
    with open(json_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload.get("slides", [])
