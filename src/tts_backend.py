"""Small transport-independent contract for single-request speech synthesis."""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol


@dataclass(frozen=True)
class SynthesisRequest:
    text: str
    voice: str
    rate: str = "+0%"
    pitch: str = "+0Hz"


@dataclass
class SynthesisResult:
    # None is reserved for legacy audio-only generators; [] means no events.
    word_boundaries: Optional[List[Dict[str, Any]]]
    metadata: Dict[str, Any]


class TTSBackendError(Exception):
    """A safe-to-display transport failure, with an explicit retry decision."""

    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class TTSBackend(Protocol):
    name: str

    def synthesize(self, request: SynthesisRequest, output_path: Path) -> SynthesisResult:
        """Write one complete MP3, or raise. Timing is relative to that MP3."""
        ...


BACKEND_NAMES = ("edge-tts", "edge-websocket")


def create_backend(name: str, *, communicate_factory=None) -> TTSBackend:
    if name == "edge-tts":
        from src.tts_edge import EdgeTTSBackend
        return EdgeTTSBackend(communicate_factory=communicate_factory)
    if name == "edge-websocket":
        if communicate_factory is not None:
            raise ValueError("communicate_factory is only supported by edge-tts")
        from src.tts_websocket import EdgeWebSocketBackend
        return EdgeWebSocketBackend()
    raise ValueError(f"Unknown TTS backend: {name}")


def validate_result(result: SynthesisResult, audio_path: Path) -> None:
    """Validate shared structure without adding ffmpeg to basic TTS generation.

    This is not a decoded-media or spoken-content completeness check.
    Empty boundaries remain supported for the historical edge-tts adapter.
    """
    if not audio_path.is_file() or audio_path.stat().st_size == 0:
        raise TTSBackendError("No audio received; cause undetermined", retryable=True)
    if result.word_boundaries is None:
        return
    previous = -1.0
    for event in result.word_boundaries:
        start, duration = event["offset_seconds"], event["duration_seconds"]
        if (not isinstance(event["text"], str) or not event["text"].strip()
                or isinstance(start, bool) or isinstance(duration, bool)
                or not math.isfinite(start) or not math.isfinite(duration)
                or start < 0 or duration < 0 or start < previous):
            raise ValueError("Invalid or unordered TTS word boundaries")
        previous = start
