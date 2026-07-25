import asyncio
import inspect
import json
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

import edge_tts


def _build_output_path(output_dir: Path, slide_num: int) -> Path:
    return output_dir / f"slide_{slide_num:03d}.mp3"


async def _save_edge_tts_audio(
    text: str,
    output_path: Path,
    voice: str,
    rate: str = "-10%",
    pitch: str = "+0Hz",
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    try:
        await communicate.save(str(output_path))
    except FileNotFoundError as exc:
        raise RuntimeError(
            "ffmpeg is required to save MP3 files. Install ffmpeg and ensure it is on PATH."
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to generate audio with edge-tts: {exc}") from exc


def _default_generator(text: str, output_path: Path, voice: str, rate: str = "-10%", pitch: str = "+0Hz") -> None:
    asyncio.run(_save_edge_tts_audio(text, output_path, voice, rate=rate, pitch=pitch))


def _invoke_generator(generator_func: Callable[..., None], text: str, output_path: Path, voice: str, rate: str, pitch: str) -> None:
    try:
        signature = inspect.signature(generator_func)
        parameter_names = set(signature.parameters)
        if "rate" in parameter_names or "pitch" in parameter_names:
            generator_func(text, output_path, voice, rate=rate, pitch=pitch)
        else:
            generator_func(text, output_path, voice)
    except (TypeError, ValueError):
        generator_func(text, output_path, voice)


def generate_audio_files(
    slides: List[Dict[str, Any]],
    output_dir: Path | str,
    voice: str = "Microsoft Server Speech Text to Speech Voice (zh-TW, YunJheNeural)",
    generator: Optional[Callable[..., None]] = None,
    manifest_path: Optional[Path | str] = None,
    rate: str = "-10%",
    pitch: str = "+0Hz",
) -> Dict[str, Any]:
    """Generate MP3 files for slides that have notes.

    Slides without notes are skipped and omitted from the manifest.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    generator_func = generator or _default_generator
    manifest_entries = []

    for slide in slides:
        notes = slide.get("notes")
        if not notes or not str(notes).strip():
            continue

        slide_num = int(slide["slide_num"])
        output_file = _build_output_path(output_path, slide_num)

        _invoke_generator(generator_func, str(notes), output_file, voice, rate, pitch)
        manifest_entries.append({
            "slide_num": slide_num,
            "title": slide.get("title"),
            "audio_file": output_file.name,
        })

    manifest = {
        "voice": voice,
        "rate": rate,
        "pitch": pitch,
        "output_dir": str(output_path),
        "slides": manifest_entries,
    }

    if manifest_path is not None:
        manifest_file = Path(manifest_path)
        manifest_file.parent.mkdir(parents=True, exist_ok=True)
        manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return manifest
