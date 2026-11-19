from __future__ import annotations

import inspect
import json
import copy
import math
import os
import tempfile
import uuid
import ssl
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

from aiohttp import WSServerHandshakeError
from edge_tts.exceptions import NoAudioReceived

from src.exceptions import TTSGenerationError
from src.tts_backend import (SynthesisRequest, SynthesisResult, TTSBackendError, create_backend, validate_result)
from src.subtitle_alignment import find_suspected_dropped_narration

DEFAULT_RATE = "+0%"

# Default retry policy for transient TTS failures (network blips, service
# hiccups). Deliberately NOT applied to COM/PowerPoint operations elsewhere
# in this project - retrying a failed COM launch without first confirming
# the previous attempt's PowerPoint process was cleaned up risks leaving
# orphaned background processes, which is a worse problem than the one
# retrying would solve. TTS calls have no such cleanup concern, so retrying
# here is safe.
DEFAULT_MAX_RETRIES = 10
DEFAULT_RETRY_DELAY_SECONDS = 5.0


def describe_tts_error(exc: Exception) -> str:
    """Summarize service errors without claiming a cause or exposing request URLs."""
    if isinstance(exc, TTSBackendError):
        return str(exc)
    if isinstance(exc, NoAudioReceived):
        return "No audio received; cause undetermined"
    if isinstance(exc, WSServerHandshakeError):
        return f"WebSocket handshake HTTP {exc.status}"
    return str(exc)


def _is_retryable(exc: Exception) -> bool:
    """Decide whether a TTS generation failure is worth retrying.

    Retried: connection/timeout-style errors, which are the shape of a
    transient network blip or a momentarily overloaded TTS service.
    NoAudioReceived is also retried within the same bounded policy: the
    service can return no audio intermittently for otherwise valid input.
    WebSocket handshake HTTP 408/429/500/502/503/504 responses use the same
    bounded retries; authentication and other HTTP errors are not retried.

    NOT retried:
    - FileNotFoundError - almost always means ffmpeg is missing, which a
      retry cannot fix (it's also a subclass of OSError, so it must be
      checked before the general OSError case below).
    - ssl.SSLCertVerificationError - a broken/untrusted/expired certificate
      needs a configuration fix, not a retry; trying again won't make a
      self-signed or expired cert suddenly valid. (This is also, separately,
      a subclass of ValueError in the standard library - checked explicitly
      here rather than relying on that as an implementation-detail
      coincidence, so the reasoning is documented instead of accidental.)
    - TypeError / ValueError - programming/usage errors (e.g. a bad
      argument), not transient failures.
    """
    if isinstance(exc, TTSBackendError):
        return exc.retryable
    if isinstance(exc, FileNotFoundError):
        return False
    if isinstance(exc, ssl.SSLCertVerificationError):
        return False
    if isinstance(exc, (TypeError, ValueError)):
        return False
    if isinstance(exc, WSServerHandshakeError):
        return exc.status in (408, 429, 500, 502, 503, 504)
    return isinstance(exc, (ConnectionError, TimeoutError, OSError, NoAudioReceived))


def _build_output_path(output_dir: Path, slide_num: int) -> Path:
    return output_dir / f"slide_{slide_num:03d}.mp3"


# Compatibility exports used by existing smoke scripts and callers.
from src.tts_edge import (
    WORD_BOUNDARY_TICKS_PER_SECOND,
    _stream_edge_tts_audio_with_word_boundaries,
    synthesize_with_word_boundaries,
    _save_edge_tts_audio, _default_generator, _default_generator_with_word_boundaries,
)


def _invoke_generator(generator_func: Callable[..., Any], text: str, output_path: Path, voice: str, rate: str, pitch: str) -> Any:
    """Call ``generator_func`` with the calling convention it appears to support,
    and return whatever it returns.

    Inspects the function's signature to decide whether to pass ``rate``/
    ``pitch`` as keyword arguments. If the signature check itself fails, or
    the signature said rate/pitch were accepted but the call still raised a
    ``TypeError`` (e.g. a stricter/mismatched fake used in tests), falls
    back to calling with just the required positional arguments.

    Deliberately narrow about what triggers that fallback: only a
    ``TypeError`` from the actual call (a real calling-convention mismatch)
    does. A ``ValueError`` raised by the generator's own logic (e.g. a bad
    certificate, a malformed voice name) must NOT be caught here and
    silently retried with different arguments - that would both mask the
    real error and call the generator a second time for no reason (this
    used to happen: a plain-signature generator that raised any
    ``ValueError`` would get invoked twice with byte-for-byte identical
    arguments, since the "fallback" call was indistinguishable from the one
    that just failed).

    The legacy generator path is audio-only; its return value is ignored by
    generate_audio_files. Select a TTSBackend to return structured timings.
    """
    try:
        signature = inspect.signature(generator_func)
        parameter_names = set(signature.parameters)
    except (TypeError, ValueError):
        parameter_names = set()

    if "rate" in parameter_names or "pitch" in parameter_names:
        try:
            return generator_func(text, output_path, voice, rate=rate, pitch=pitch)
        except TypeError:
            pass  # Fall through to the plain call below.

    return generator_func(text, output_path, voice)


def publish_manifest(path, manifest):
    """Replace one JSON file atomically; caller owns the batch publication guard."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".manifest-{uuid.uuid4().hex}.json")
    try:
        temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def generate_audio_files(
    slides: List[Dict[str, Any]],
    output_dir: Path | str,
    voice: str = "Microsoft Server Speech Text to Speech Voice (zh-TW, YunJheNeural)",
    generator: Optional[Callable[..., Any]] = None,
    manifest_path: Optional[Path | str] = None,
    rate: str = DEFAULT_RATE,
    pitch: str = "+0Hz",
    progress_callback: Optional[Callable[[int, int, int], None]] = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
    on_retry: Optional[Callable[[int, int, int, Exception], None]] = None,
    communicate_factory: Optional[Callable[..., Any]] = None,
    on_narration_gap: Optional[Callable[[int, Dict[str, Any]], None]] = None,
    *, backend="edge-tts", previous_manifest=None,
) -> Dict[str, Any]:
    """Generate unpadded per-slide MP3s via a selectable single-attempt backend.

    Existing generator/factory injection and public wrappers remain supported.
    Legacy custom generators are audio-only. Both named backends share retries,
    boundary persistence, gap warnings, and staged batch publication. Progress
    callbacks report synthesis completion; publication follows the final slide.

    A failed synthesis leaves the previous published batch untouched. When a
    manifest is requested, publication first marks it incomplete, then replaces
    files, then publishes ready metadata. An interrupted publication is blocked
    by shared manifest validation. No concurrent writers are supported.

    previous_manifest is used by --slides so untouched per-slide provenance is
    preserved in the SAME publication. No old backend is inferred for legacy data.
    """
    max_retries = max(0, max_retries)
    if not math.isfinite(retry_delay_seconds) or retry_delay_seconds < 0:
        raise TTSGenerationError("TTS retry delay must be finite and nonnegative")
    if generator is not None and backend != "edge-tts":
        raise TTSGenerationError("A custom generator cannot be combined with a selected backend")
    if previous_manifest is not None:
        from src.audio_preparation import validate_audio_manifest
        validate_audio_manifest(previous_manifest)
    try:
        selected = None if generator else (create_backend(backend, communicate_factory=communicate_factory)
                                          if isinstance(backend, str) else backend)
    except (ValueError, TypeError) as exc:
        raise TTSGenerationError(str(exc)) from exc

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    narrated = [s for s in slides if s.get("notes") and str(s["notes"]).strip()]
    numbers = [int(s["slide_num"]) for s in narrated]
    if len(set(numbers)) != len(numbers) or any(n <= 0 for n in numbers):
        raise TTSGenerationError("Narrated slide numbers must be unique positive integers")
    entries = []
    with tempfile.TemporaryDirectory(prefix=".tts-", dir=output_path) as staging:
        staging = Path(staging)
        for index, slide in enumerate(narrated, 1):
            number = int(slide["slide_num"])
            audio = _build_output_path(staging, number)
            request = SynthesisRequest(str(slide["notes"]), voice, rate, pitch)
            for attempt in range(1, max_retries + 2):
                try:
                    audio.unlink(missing_ok=True)
                    if generator is not None:
                        _invoke_generator(generator, request.text, audio, voice, rate, pitch)
                        result = SynthesisResult(None, {"backend": "custom", "voice": voice,
                                                        "rate": rate, "pitch": pitch})
                    else:
                        result = selected.synthesize(request, audio)
                    if generator is None and result.word_boundaries is None:
                        raise ValueError("TTS backends must return word-boundary data")
                    validate_result(result, audio)
                    break
                except Exception as exc:
                    if attempt <= max_retries and _is_retryable(exc):
                        if on_retry:
                            on_retry(attempt, max_retries, number, exc)
                        time.sleep(retry_delay_seconds)
                        continue
                    hint = " (this often means ffmpeg is missing - install it and ensure it's on PATH)" if isinstance(exc, FileNotFoundError) else ""
                    raise TTSGenerationError(
                        f"Failed to generate audio for slide {number} after {attempt} attempt(s){hint}: "
                        f"{describe_tts_error(exc)}"
                    ) from exc
            boundaries_file = None
            warnings = []
            if result.word_boundaries is not None:
                sidecar = audio.with_suffix(".wordboundaries.json")
                sidecar.write_text(json.dumps(result.word_boundaries, ensure_ascii=False, indent=2), encoding="utf-8")
                boundaries_file = sidecar.name
                try:
                    warnings = find_suspected_dropped_narration(request.text, result.word_boundaries)
                except Exception:
                    warnings = []  # Historical heuristic must not prevent audio generation.
                if on_narration_gap:
                    for suspect in warnings:
                        on_narration_gap(number, suspect)
            entries.append({"slide_num": number, "title": slide.get("title"),
                            "audio_file": audio.name, "word_boundaries_file": boundaries_file,
                            "narration_gap_warnings": warnings, "tts": result.metadata})
            if progress_callback:
                progress_callback(index, len(narrated), number)

        manifest = copy.deepcopy(previous_manifest) if previous_manifest else {}
        merged = {int(e["slide_num"]): e for e in manifest.get("slides", [])}
        merged.update({e["slide_num"]: e for e in entries})
        manifest.update(voice=voice, rate=rate, pitch=pitch, output_dir=str(output_path),
                        slides=[merged[n] for n in sorted(merged)])
        destination = Path(manifest_path) if manifest_path is not None else None
        # Even low-level callers without manifest_path must invalidate an existing
        # standard manifest before replacing files it may still reference.
        guard = destination or (output_path / "manifest.json" if (output_path / "manifest.json").exists() else None)
        try:
            if guard:
                incomplete = copy.deepcopy(manifest)
                incomplete["generation"] = {"schema_version": 1, "status": "incomplete"}
                publish_manifest(guard, incomplete)
            for audio in staging.iterdir():
                os.replace(audio, output_path / audio.name)
            manifest["generation"] = {"schema_version": 1, "status": "ready"}
            if destination:
                publish_manifest(destination, manifest)
            # With no manifest_path, an existing guard intentionally remains
            # incomplete: the caller must publish the returned manifest itself.
        except OSError as exc:
            raise TTSGenerationError("TTS publication failed; inspect the manifest and regenerate audio") from exc
    return manifest
