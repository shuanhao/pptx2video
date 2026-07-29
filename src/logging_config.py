"""Centralized logging setup for pptx2video.

Previously, every stage printed straight to stdout via ``print()``. That's
fine while a run is happening in front of you, but once it's done, that
output is gone unless you happened to redirect it - which makes it hard to
diagnose an intermittent PowerPoint COM failure (the kind this project has
already run into more than once) after the fact.

This module sets up a logger that:
- Writes to the console in the same plain, timestamp-free style the CLI
  already used with ``print()`` (INFO level, or DEBUG when ``--verbose``),
  so the interactive experience doesn't change.
- ALSO always writes a timestamped, full-detail copy to a dated file under
  ``logs/`` at DEBUG level, regardless of ``--verbose`` - so a full trace is
  available after the fact even for a run where ``--verbose`` wasn't passed.
"""

import logging
import sys
from datetime import date
from pathlib import Path
from typing import Optional

LOGGER_NAME = "pptx2video"


def setup_logging(
    verbose: bool = False,
    log_dir: Optional[Path | str] = "logs",
    logger_name: str = LOGGER_NAME,
) -> logging.Logger:
    """Configure and return the project's logger.

    Safe to call more than once (e.g. across multiple tests importing
    ``main``) - existing handlers are left alone rather than duplicated.

    Args:
        verbose: If True, the console handler shows DEBUG-level messages
            (matching the existing ``--verbose`` behavior); otherwise only
            INFO and above. The file handler is always DEBUG, independent
            of this flag.
        log_dir: Directory to write the dated log file into. Pass ``None``
            to disable file logging entirely (console-only) - useful for
            tests or environments without a writable filesystem.
        logger_name: Name of the logger to configure/return.

    Returns:
        The configured ``logging.Logger``. If the log directory can't be
        created or written to (e.g. read-only filesystem), file logging is
        skipped with a console warning rather than crashing the program -
        logging problems should never take down the actual task.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    normalized_log_dir = str(Path(log_dir)) if log_dir is not None else None
    previous_log_dir = getattr(logger, "_pptx2video_log_dir", "__unset__")

    if logger.handlers:
        if previous_log_dir == normalized_log_dir:
            # Same configuration as last time - just refresh the console
            # level in case `verbose` changed, and leave everything else
            # alone to avoid duplicate handlers / duplicate log lines.
            for handler in logger.handlers:
                if (
                    isinstance(handler, logging.StreamHandler)
                    and not isinstance(handler, logging.FileHandler)
                ):
                    handler.setLevel(
                        logging.DEBUG if verbose else logging.INFO
                    )
            return logger

        # log_dir changed since the last setup_logging() call for this
        # logger - tear down the old handlers (closing the old file handle)
        # and fall through to rebuild, so the file handler points at the
        # new location instead of silently keeping writing to the old one.
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)

    # Console output mirrors the plain style the CLI already used with
    # print() - no timestamp/level clutter for the person watching it run.
    console_formatter = logging.Formatter("%(message)s")
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    if log_dir is not None:
        try:
            log_dir_path = Path(log_dir)
            log_dir_path.mkdir(parents=True, exist_ok=True)
            log_file = log_dir_path / f"{date.today().isoformat()}.log"

            file_formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except OSError as exc:
            logger.warning(f"Could not set up file logging in {log_dir}: {exc}")

    logger._pptx2video_log_dir = normalized_log_dir
    return logger


def get_logger(logger_name: str = LOGGER_NAME) -> logging.Logger:
    """Get the project logger, configuring it with defaults if not already set up.

    Prefer calling ``setup_logging()`` explicitly once at program start (so
    ``--verbose`` and ``--log-dir`` take effect); this is a convenience
    fallback for code paths (like library usage or tests) that need a logger
    without wiring through CLI args.
    """
    logger = logging.getLogger(logger_name)
    if not logger.handlers:
        return setup_logging()
    return logger


def shutdown_logging(logger: logging.Logger | None = None) -> None:
    """Close and remove all handlers from a logger.

    Useful for unit tests and for applications that want to explicitly
    release log files before exiting.
    """
    if logger is None:
        logger = logging.getLogger(LOGGER_NAME)

    handlers = list(logger.handlers)
    for handler in handlers:
        try:
            handler.flush()
        finally:
            handler.close()
            logger.removeHandler(handler)
