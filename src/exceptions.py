"""Custom exception hierarchy for pptx2video.

Before this module, most failures surfaced as generic ``RuntimeError`` (or
occasionally plain ``Exception``), which made it impossible for callers to
tell "PowerPoint failed to launch" apart from "the TTS service is down"
without parsing error message text. Every exception below carries enough
context to log and handle each failure mode differently, while still being
catchable as a single group via the shared ``Pptx2VideoError`` base class.

``FileNotFoundError`` and ``ValueError`` are intentionally left as Python's
builtins where they're already the exact right fit (e.g. "the input .pptx
doesn't exist") - there's no need to re-wrap something that's already
semantically correct and universally understood.
"""


class Pptx2VideoError(Exception):
    """Base class for all errors raised by this project's own logic.

    Catch this to handle any pptx2video-specific failure in one place,
    without also swallowing unrelated errors (e.g. a plain ``KeyError`` from
    a programming mistake elsewhere).
    """


class PptParseError(Pptx2VideoError):
    """Raised when a .pptx file exists but cannot be parsed.

    Covers cases like a corrupt file, an unsupported/legacy format, or any
    other failure from the underlying python-pptx library while reading
    slides, titles, or notes.
    """


class TTSGenerationError(Pptx2VideoError):
    """Raised when edge-tts fails to generate audio for a slide.

    Covers network failures, service errors, and missing-ffmpeg failures
    during MP3 generation. The error message includes which slide failed.
    """


class PowerPointLaunchError(Pptx2VideoError):
    """Raised when PowerPoint cannot be started or a presentation opened.

    Covers: running on a non-Windows platform, ``pywin32``/PowerPoint not
    installed, the COM ``Application`` object failing to start, and
    ``Presentations.Open`` failing on a given .pptx file.
    """


class AudioInsertionError(Pptx2VideoError):
    """Raised for unrecoverable failures while inserting audio into a PPTX.

    Per-slide problems (a missing audio file, a slide number that doesn't
    exist) are intentionally NOT raised as this - they're recorded in the
    ``skipped_slides`` list instead, so one bad slide doesn't abort the
    whole deck. This is reserved for failures that affect the operation as
    a whole, such as being unable to save the resulting .pptx.
    """


class VideoExportError(Pptx2VideoError):
    """Raised when PowerPoint's video export fails or produces no output.

    Covers ``CreateVideoStatus`` reporting failure, and the safety-net case
    where "done" was reported but no non-empty output file was found.
    """


class VideoExportTimeoutError(VideoExportError, TimeoutError):
    """Raised when waiting for PowerPoint's video export exceeds the timeout.

    Inherits from both ``VideoExportError`` (so it's catchable alongside
    other pptx2video errors via ``Pptx2VideoError``) and the builtin
    ``TimeoutError`` (so code that only knows to catch ``TimeoutError``
    generically - e.g. a caller unaware of this project's exception types -
    still works unchanged).
    """
