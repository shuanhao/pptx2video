"""Adapter for the existing edge-tts package; public wrappers remain compatible."""
from __future__ import annotations

import asyncio
from importlib.metadata import version
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import edge_tts
from src.tts_backend import SynthesisRequest, SynthesisResult

DEFAULT_RATE = "+0%"
WORD_BOUNDARY_TICKS_PER_SECOND = 10_000_000

async def _stream_edge_tts_audio_with_word_boundaries(
    text: str,
    output_path: Path,
    voice: str,
    rate: str = DEFAULT_RATE,
    pitch: str = "+0Hz",
    communicate_factory: Optional[Callable[..., Any]] = None,
) -> List[Dict[str, Any]]:
    """Write streamed MP3 and convert WordBoundary ticks to seconds.

    communicate_factory is retained for offline injection. The boundary keyword
    fallback preserves the pre-existing compatibility behavior. Retries and
    publication belong to the common workflow, not to this transport adapter.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    factory = communicate_factory or edge_tts.Communicate
    try:
        communicate = factory(text=text, voice=voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    except TypeError:
        # edge-tts < 7.2.0 (or any other Communicate-like factory that
        # doesn't understand this project's default) doesn't accept a
        # ``boundary`` keyword at all - retry once without it rather than
        # failing outright. On real edge-tts 6.x this produces the same
        # result anyway (WordBoundary is the only type those versions emit).
        communicate = factory(text=text, voice=voice, rate=rate, pitch=pitch)

    word_boundaries: List[Dict[str, Any]] = []
    with open(output_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                if "data" not in chunk:
                    raise ValueError("Edge-TTS audio chunk is missing data")
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                if "text" not in chunk or "offset" not in chunk or "duration" not in chunk:
                    raise ValueError("Edge-TTS WordBoundary chunk is missing text, offset or duration")
                word_boundaries.append({
                    "text": chunk["text"],
                    "offset_seconds": chunk["offset"] / WORD_BOUNDARY_TICKS_PER_SECOND,
                    "duration_seconds": chunk["duration"] / WORD_BOUNDARY_TICKS_PER_SECOND,
                })

    return word_boundaries


def synthesize_with_word_boundaries(
    text: str,
    output_path: Path | str,
    voice: str,
    rate: str = DEFAULT_RATE,
    pitch: str = "+0Hz",
    communicate_factory: Optional[Callable[..., Any]] = None,
) -> List[Dict[str, Any]]:
    """Compatibility API: one synthesis attempt, returning relative timings."""
    return asyncio.run(
        _stream_edge_tts_audio_with_word_boundaries(
            text,
            Path(output_path),
            voice,
            rate=rate,
            pitch=pitch,
            communicate_factory=communicate_factory,
        )
    )


class EdgeTTSBackend:
    name = "edge-tts"

    def __init__(self, communicate_factory=None):
        self.communicate_factory = communicate_factory

    def synthesize(self, request: SynthesisRequest, output_path: Path) -> SynthesisResult:
        boundaries = synthesize_with_word_boundaries(
            request.text, output_path, request.voice, rate=request.rate,
            pitch=request.pitch, communicate_factory=self.communicate_factory,
        )
        return SynthesisResult(boundaries, {
            "backend": self.name, "implementation_version": version("edge-tts"),
            "voice": request.voice, "rate": request.rate, "pitch": request.pitch,
        })


async def _save_edge_tts_audio(
    text: str,
    output_path: Path,
    voice: str,
    rate: str = DEFAULT_RATE,
    pitch: str = "+0Hz",
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(str(output_path))


def _default_generator(text: str, output_path: Path, voice: str, rate: str = DEFAULT_RATE, pitch: str = "+0Hz") -> None:
    asyncio.run(_save_edge_tts_audio(text, output_path, voice, rate=rate, pitch=pitch))


def _default_generator_with_word_boundaries(
    text: str,
    output_path: Path,
    voice: str,
    rate: str = DEFAULT_RATE,
    pitch: str = "+0Hz",
    communicate_factory: Optional[Callable[..., Any]] = None,
) -> List[Dict[str, Any]]:
    """Legacy callable retained for existing imports; use EdgeTTSBackend for selection."""
    return synthesize_with_word_boundaries(
        text, output_path, voice, rate=rate, pitch=pitch, communicate_factory=communicate_factory
    )
