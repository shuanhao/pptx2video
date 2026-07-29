import asyncio
import inspect
import json
import ssl
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

import edge_tts

from src.exceptions import TTSGenerationError

# Default retry policy for transient TTS failures (network blips, service
# hiccups). Deliberately NOT applied to COM/PowerPoint operations elsewhere
# in this project - retrying a failed COM launch without first confirming
# the previous attempt's PowerPoint process was cleaned up risks leaving
# orphaned background processes, which is a worse problem than the one
# retrying would solve. TTS calls have no such cleanup concern, so retrying
# here is safe.
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY_SECONDS = 2.0


def _is_retryable(exc: Exception) -> bool:
    """Decide whether a TTS generation failure is worth retrying.

    Retried: connection/timeout-style errors, which are the shape of a
    transient network blip or a momentarily overloaded TTS service.

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
    if isinstance(exc, FileNotFoundError):
        return False
    if isinstance(exc, ssl.SSLCertVerificationError):
        return False
    if isinstance(exc, (TypeError, ValueError)):
        return False
    return isinstance(exc, (ConnectionError, TimeoutError, OSError))


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
    await communicate.save(str(output_path))


def _default_generator(text: str, output_path: Path, voice: str, rate: str = "-10%", pitch: str = "+0Hz") -> None:
    asyncio.run(_save_edge_tts_audio(text, output_path, voice, rate=rate, pitch=pitch))


def _invoke_generator(generator_func: Callable[..., None], text: str, output_path: Path, voice: str, rate: str, pitch: str) -> None:
    """Call ``generator_func`` with the calling convention it appears to support.

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
    """
    try:
        signature = inspect.signature(generator_func)
        parameter_names = set(signature.parameters)
    except (TypeError, ValueError):
        parameter_names = set()

    if "rate" in parameter_names or "pitch" in parameter_names:
        try:
            generator_func(text, output_path, voice, rate=rate, pitch=pitch)
            return
        except TypeError:
            pass  # Fall through to the plain call below.

    generator_func(text, output_path, voice)


def generate_audio_files(
    slides: List[Dict[str, Any]],
    output_dir: Path | str,
    voice: str = "Microsoft Server Speech Text to Speech Voice (zh-TW, YunJheNeural)",
    generator: Optional[Callable[..., None]] = None,
    manifest_path: Optional[Path | str] = None,
    rate: str = "-10%",
    pitch: str = "+0Hz",
    progress_callback: Optional[Callable[[int, int, int], None]] = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
    on_retry: Optional[Callable[[int, int, int, Exception], None]] = None,
) -> Dict[str, Any]:
    """Generate MP3 files for slides that have notes.

    Slides without notes are skipped and omitted from the manifest.

    Args:
        progress_callback: Optional callback invoked as
            ``progress_callback(current, total, slide_num)`` right after each
            audio file finishes generating - ``current`` is 1-based (e.g.
            ``2, 5, 4`` means "2nd of 5 audio files done, was slide 4"). Use
            this to print progress instead of only being able to tell how far
            along generation is by counting files in the output directory.
        max_retries: How many extra attempts to make after an initial
            failure that looks transient (see ``_is_retryable``), before
            giving up and raising ``TTSGenerationError``. 0 disables
            retrying entirely.
        retry_delay_seconds: How long to wait between retry attempts.
        on_retry: Optional callback invoked as
            ``on_retry(attempt, max_retries, slide_num, exception)`` right
            before each retry sleep/attempt - ``attempt`` is 1-based (the
            attempt that just failed). Use this to log/print retry activity
            instead of it happening silently.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    generator_func = generator or _default_generator

    slides_with_notes = [
        slide for slide in slides if slide.get("notes") and str(slide.get("notes")).strip()
    ]
    total = len(slides_with_notes)
    manifest_entries = []

    for index, slide in enumerate(slides_with_notes, start=1):
        slide_num = int(slide["slide_num"])
        output_file = _build_output_path(output_path, slide_num)

        last_exc: Optional[Exception] = None
        for attempt in range(1, max_retries + 2):  # 1 initial attempt + max_retries retries
            try:
                _invoke_generator(generator_func, str(slide["notes"]), output_file, voice, rate, pitch)
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                is_last_attempt = attempt == max_retries + 1
                if not _is_retryable(exc) or is_last_attempt:
                    break
                if on_retry is not None:
                    on_retry(attempt, max_retries, slide_num, exc)
                time.sleep(retry_delay_seconds)

        if last_exc is not None:
            hint = ""
            if isinstance(last_exc, FileNotFoundError):
                hint = " (this often means ffmpeg is missing - install it and ensure it's on PATH)"
            raise TTSGenerationError(
                f"Failed to generate audio for slide {slide_num}{hint}: {last_exc}"
            ) from last_exc

        manifest_entries.append({
            "slide_num": slide_num,
            "title": slide.get("title"),
            "audio_file": output_file.name,
        })

        if progress_callback is not None:
            progress_callback(index, total, slide_num)

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
