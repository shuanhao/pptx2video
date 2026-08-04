import asyncio
import inspect
import json
import ssl
import time
from functools import partial
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

import edge_tts

from src.exceptions import TTSGenerationError
from src.subtitle_alignment import find_suspected_dropped_narration

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


# edge-tts reports WordBoundary/SentenceBoundary "Offset"/"Duration" in
# 100-nanosecond ticks (the classic Windows FILETIME-style unit used by
# Azure Speech) - confirmed by reading edge_tts.communicate's
# __parse_metadata, NOT from the library's public docs, which don't state
# the unit. The TypedDict type hint for these fields says ``float``, which
# is easy to misread as "already in seconds" - it isn't. Divide by this
# constant to convert to seconds.
WORD_BOUNDARY_TICKS_PER_SECOND = 10_000_000


async def _stream_edge_tts_audio_with_word_boundaries(
    text: str,
    output_path: Path,
    voice: str,
    rate: str = "-10%",
    pitch: str = "+0Hz",
    communicate_factory: Optional[Callable[..., Any]] = None,
) -> List[Dict[str, Any]]:
    """Synthesize speech via edge-tts's streaming API, capturing per-word
    timing (``WordBoundary``) events alongside the MP3 output.

    Unlike ``_save_edge_tts_audio`` (which just calls ``communicate.save()``
    and discards all timing metadata), this uses ``communicate.stream()``
    and separates the two chunk types it yields: ``"audio"`` chunks are
    written straight to ``output_path`` exactly as before, and
    ``"WordBoundary"`` chunks are collected and returned as a list of
    plain dicts (matching this project's style elsewhere - manifest
    entries, CLI payloads - of using plain dicts rather than introducing a
    dataclass for a single small structure).

    ``boundary="WordBoundary"`` is passed explicitly because edge-tts
    >=7.2.0 defaults ``Communicate``'s ``boundary`` parameter to the
    coarser ``"SentenceBoundary"`` - the whole point of this function is
    per-word timing precise enough to align subtitle segment boundaries
    against, so that default would silently defeat the purpose.

    That parameter itself was only added in edge-tts 7.2.0 (confirmed by
    installing older releases and inspecting ``Communicate.__init__``'s
    signature directly - it isn't called out in the library's changelog).
    Versions before that don't accept a ``boundary`` keyword at all and
    raise ``TypeError`` if given one; 6.x versions hardcode ``"WordBoundary"``
    as the only type they ever emit (confirmed the same way, by reading
    ``__parse_metadata``'s source), so simply omitting the keyword on those
    versions produces the same result anyway. If the call with
    ``boundary=`` raises ``TypeError``, this retries once without it - this
    project pins ``edge-tts>=7.2.0`` in requirements.txt specifically so
    this fallback is a defensive backstop (e.g. a stale environment that
    didn't pick up the pin bump) rather than the expected path.

    Args:
        communicate_factory: Optional factory for the
            ``edge_tts.Communicate``-like object to use, defaulting to
            ``edge_tts.Communicate`` itself. Exists so tests can inject a
            fake that yields canned chunks without a real network call -
            the same dependency-injection approach ``generate_audio_files``
            uses for its ``generator`` parameter, and ``ppt_automation.py``
            uses for its ``powerpoint_app`` parameter.

    Returns:
        A list of ``{"text": str, "offset_seconds": float,
        "duration_seconds": float}`` dicts, one per ``WordBoundary`` event,
        in the order edge-tts emitted them (which is text order). Empty if
        edge-tts reported no boundary events for this text (e.g. an empty
        or whitespace-only string).
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
        # result anyway (WordBoundary is the only type those versions ever
        # emit); see the docstring above for the full version history this
        # was confirmed against.
        communicate = factory(text=text, voice=voice, rate=rate, pitch=pitch)

    word_boundaries: List[Dict[str, Any]] = []
    with open(output_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
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
    rate: str = "-10%",
    pitch: str = "+0Hz",
    communicate_factory: Optional[Callable[..., Any]] = None,
) -> List[Dict[str, Any]]:
    """Synchronous wrapper around ``_stream_edge_tts_audio_with_word_boundaries``.

    This was originally Phase 1 of the SRT subtitle segmentation work,
    added as a standalone building block before being wired into anything.
    As of Phase 4, ``generate_audio_files()`` uses this (via
    ``_default_generator_with_word_boundaries``) as its default generator
    whenever the caller doesn't supply a custom ``generator`` - so a normal
    ``--generate-audio`` run now captures WordBoundary timing data for
    every slide as a side effect of the same TTS call that produces the
    mp3, with no second network round-trip needed later just to get timing
    data for subtitles. Calling this function directly still works exactly
    as before for standalone use (e.g. the smoke test scripts).

    Does not retry on failure (unlike ``generate_audio_files``) - this is a
    standalone building block; retrying is handled one level up, by
    ``generate_audio_files``'s own retry loop, when this is used as its
    generator.

    Returns:
        The MP3 is written to ``output_path`` exactly as
        ``generate_audio_files`` would; the return value is the list of
        word-boundary events described in
        ``_stream_edge_tts_audio_with_word_boundaries``.
    """
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


def _default_generator_with_word_boundaries(
    text: str,
    output_path: Path,
    voice: str,
    rate: str = "-10%",
    pitch: str = "+0Hz",
    communicate_factory: Optional[Callable[..., Any]] = None,
) -> List[Dict[str, Any]]:
    """The generator ``generate_audio_files()`` uses by default (when the
    caller doesn't supply a custom ``generator``): writes the mp3 exactly
    as ``_default_generator`` did, and additionally returns the captured
    WordBoundary events, via ``synthesize_with_word_boundaries``.

    ``communicate_factory`` is threaded through for the same reason
    ``synthesize_with_word_boundaries`` accepts it: so tests can inject a
    fake edge-tts response instead of making a real network call, without
    needing to bypass this default generator entirely via a custom
    ``generator=`` (which would also - correctly - skip word-boundary
    capture, since a custom generator isn't guaranteed to support it).
    """
    return synthesize_with_word_boundaries(
        text, output_path, voice, rate=rate, pitch=pitch, communicate_factory=communicate_factory
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

    The return value matters as of Phase 4: ``_default_generator_with_word_boundaries``
    returns the captured WordBoundary events, which ``generate_audio_files``
    needs in order to persist them. Custom generators (most existing tests,
    and any caller not using the default) typically return ``None``, which
    is a perfectly valid "no word-boundary data available" signal - callers
    must not assume a non-``None`` return.
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


def generate_audio_files(
    slides: List[Dict[str, Any]],
    output_dir: Path | str,
    voice: str = "Microsoft Server Speech Text to Speech Voice (zh-TW, YunJheNeural)",
    generator: Optional[Callable[..., Any]] = None,
    manifest_path: Optional[Path | str] = None,
    rate: str = "-10%",
    pitch: str = "+0Hz",
    progress_callback: Optional[Callable[[int, int, int], None]] = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
    on_retry: Optional[Callable[[int, int, int, Exception], None]] = None,
    communicate_factory: Optional[Callable[..., Any]] = None,
    on_narration_gap: Optional[Callable[[int, Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """Generate MP3 files for slides that have notes.

    Slides without notes are skipped and omitted from the manifest.

    As of Phase 4 of the SRT subtitle work, this also captures WordBoundary
    timing data as a side effect of the same TTS call, whenever the caller
    doesn't override ``generator`` - see ``communicate_factory`` and the
    "Word-boundary capture" note below.

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
            retrying entirely. Negative values are clamped to 0 rather than
            silently skipping generation altogether (see note below).
        retry_delay_seconds: How long to wait between retry attempts.
        on_retry: Optional callback invoked as
            ``on_retry(attempt, max_retries, slide_num, exception)`` right
            before each retry sleep/attempt - ``attempt`` is 1-based (the
            attempt that just failed). Use this to log/print retry activity
            instead of it happening silently.
        communicate_factory: Only used when ``generator`` is NOT supplied
            (i.e. the real default edge-tts path is in effect). Passed
            through to ``synthesize_with_word_boundaries`` - exists so tests
            can inject a fake edge-tts response and exercise the real
            word-boundary-capturing default generator without a network
            call, instead of having to bypass it entirely with a custom
            ``generator`` (which would also, correctly, skip word-boundary
            capture). Ignored if ``generator`` is supplied.
        on_narration_gap: Optional callback invoked as
            ``on_narration_gap(slide_num, suspect)`` once per suspected
            dropped-narration finding (see
            ``subtitle_alignment.find_suspected_dropped_narration``) for a
            slide, right after that slide's audio finishes generating -
            ``suspect`` is one of that function's returned dicts (has
            ``skipped_text``, ``gap_seconds``, ``expected_seconds``,
            ``audio_position_seconds``). This check only runs when the
            default generator is used (word-boundary data is required for
            it) and is a heuristic, not a certainty - see that function's
            docstring for why it exists (a real deck showed edge-tts
            silently skip ~300 characters of a slide's notes with no error
            of any kind) and how it decides something looks wrong. Findings
            are also always recorded in the slide's manifest entry as
            ``"narration_gap_warnings"`` regardless of whether this
            callback is supplied, so they survive being written to
            manifest.json and can be reviewed later even without one.

    Word-boundary capture: when the default generator is used (``generator``
    left as ``None``), each slide's WordBoundary events (see
    ``synthesize_with_word_boundaries``) are written alongside its mp3 as
    ``slide_XXX.wordboundaries.json``, and that filename is recorded in the
    slide's manifest entry as ``"word_boundaries_file"``. When a custom
    ``generator`` is supplied, ``"word_boundaries_file"`` is always ``None``
    in the manifest - a custom generator isn't guaranteed to produce timing
    data, so no file is written and downstream code (e.g. SRT generation)
    must treat a ``None`` here as "not available for this slide" rather than
    an error.
    """
    # A negative max_retries would make range(1, max_retries + 2) empty,
    # meaning the loop below never runs the generator even once, yet
    # last_exc would stay None the whole time - which the code below reads
    # as "succeeded". That used to silently fabricate a manifest entry for
    # audio that was never actually generated. Clamp instead of trusting
    # the caller, so the only way to skip generation is the documented
    # code path (a slide with no notes), never an off-by-one on this value.
    if max_retries < 0:
        max_retries = 0

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    using_default_generator = generator is None
    generator_func = generator or partial(
        _default_generator_with_word_boundaries, communicate_factory=communicate_factory
    )

    slides_with_notes = [
        slide for slide in slides if slide.get("notes") and str(slide.get("notes")).strip()
    ]
    total = len(slides_with_notes)
    manifest_entries = []

    for index, slide in enumerate(slides_with_notes, start=1):
        slide_num = int(slide["slide_num"])
        output_file = _build_output_path(output_path, slide_num)

        last_exc: Optional[Exception] = None
        generator_result: Any = None
        for attempt in range(1, max_retries + 2):  # 1 initial attempt + max_retries retries
            try:
                generator_result = _invoke_generator(generator_func, str(slide["notes"]), output_file, voice, rate, pitch)
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

        word_boundaries_file = None
        narration_gap_warnings: List[Dict[str, Any]] = []
        if using_default_generator:
            # generator_result is the list of WordBoundary events returned
            # by _default_generator_with_word_boundaries (possibly empty,
            # e.g. edge-tts reported none - but never None here, since that
            # function always returns a list). Persisted as a sidecar file
            # rather than inlined into manifest.json so the manifest stays
            # small and readable even for decks with many/long slides.
            word_boundaries_path = output_file.with_suffix(".wordboundaries.json")
            word_boundaries_path.write_text(
                json.dumps(generator_result or [], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            word_boundaries_file = word_boundaries_path.name

            # Safety net for a real, observed failure mode: edge-tts can
            # silently skip a whole chunk of a slide's notes while
            # synthesizing - no exception, no error, just audio that's
            # shorter than it should be and a WordBoundary stream that
            # jumps over the missing text. This is otherwise invisible
            # until someone happens to notice the video is missing content
            # (or diffs the per-segment subtitle warnings by hand, as this
            # was first found). Runs here, right after generation, so it
            # fires even for callers that never touch subtitle generation
            # at all (e.g. --generate-audio + --insert-audio + --export-video
            # with no --subtitles-output).
            try:
                narration_gap_warnings = find_suspected_dropped_narration(
                    str(slide["notes"]), generator_result or []
                )
            except Exception:  # noqa: BLE001 - this safety net must never itself break audio generation
                narration_gap_warnings = []
            if on_narration_gap is not None:
                for suspect in narration_gap_warnings:
                    on_narration_gap(slide_num, suspect)

        manifest_entries.append({
            "slide_num": slide_num,
            "title": slide.get("title"),
            "audio_file": output_file.name,
            "word_boundaries_file": word_boundaries_file,
            "narration_gap_warnings": narration_gap_warnings,
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
