import io
import logging
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.logging_config import ensure_utf8_console, setup_logging, shutdown_logging

class LoggingConfigTests(unittest.TestCase):

    def tearDown(self):
        # Release every logger created by this test so Windows can
        # delete TemporaryDirectory().
        manager = logging.Logger.manager

        for name, obj in list(manager.loggerDict.items()):
            if isinstance(obj, logging.Logger) and name.startswith("pptx2video-test-"):
                shutdown_logging(obj)

    def _fresh_logger_name(self) -> str:
        # Use a unique logger name per test so handlers from one test don't
        # leak into another (logging.getLogger caches by name globally).
        self._counter = getattr(self, "_counter", 0) + 1
        return f"pptx2video-test-{id(self)}-{self._counter}"

    def test_setup_logging_creates_console_and_file_handlers(self):
        with tempfile.TemporaryDirectory() as tmp:
            logger_name = self._fresh_logger_name()
            logger = setup_logging(log_dir=tmp, logger_name=logger_name)

            self.assertEqual(len(logger.handlers), 2)
            handler_types = {type(h) for h in logger.handlers}
            self.assertIn(logging.StreamHandler, handler_types)
            self.assertIn(logging.FileHandler, handler_types)
            shutdown_logging(logger)

    def test_setup_logging_writes_to_dated_log_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            logger_name = self._fresh_logger_name()
            logger = setup_logging(log_dir=tmp, logger_name=logger_name)
            logger.info("hello from test")

            log_files = list(Path(tmp).glob("*.log"))
            self.assertEqual(len(log_files), 1)
            content = log_files[0].read_text(encoding="utf-8")
            self.assertIn("hello from test", content)
            # File records include timestamp + level, unlike the console.
            self.assertIn("[INFO]", content)
            shutdown_logging(logger)

    def test_setup_logging_respects_verbose_for_console_level_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            logger_name = self._fresh_logger_name()
            logger = setup_logging(verbose=False, log_dir=tmp, logger_name=logger_name)

            console_handler = next(
                h for h in logger.handlers if isinstance(h, logging.StreamHandler)
                and not isinstance(h, logging.FileHandler)
            )
            file_handler = next(h for h in logger.handlers if isinstance(h, logging.FileHandler))

            self.assertEqual(console_handler.level, logging.INFO)
            # File handler stays at DEBUG regardless of verbose - full trace
            # should always be available after the fact.
            self.assertEqual(file_handler.level, logging.DEBUG)
            shutdown_logging(logger)

    def test_setup_logging_verbose_lowers_console_level_to_debug(self):
        with tempfile.TemporaryDirectory() as tmp:
            logger_name = self._fresh_logger_name()
            logger = setup_logging(verbose=True, log_dir=tmp, logger_name=logger_name)

            console_handler = next(
                h for h in logger.handlers if isinstance(h, logging.StreamHandler)
                and not isinstance(h, logging.FileHandler)
            )
            self.assertEqual(console_handler.level, logging.DEBUG)
            shutdown_logging(logger)

    def test_setup_logging_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            logger_name = self._fresh_logger_name()
            logger1 = setup_logging(log_dir=tmp, logger_name=logger_name)
            logger2 = setup_logging(log_dir=tmp, logger_name=logger_name)

            # Calling setup_logging twice must not duplicate handlers - each
            # log message should only be recorded once.
            self.assertIs(logger1, logger2)
            self.assertEqual(len(logger1.handlers), 2)
            handler_ids = {id(h) for h in logger1.handlers}
            self.assertEqual(
                len(handler_ids),
                len(logger1.handlers),
            )
            shutdown_logging(logger1)

    def test_setup_logging_with_log_dir_none_skips_file_handler(self):
        logger_name = self._fresh_logger_name()
        logger = setup_logging(log_dir=None, logger_name=logger_name)

        self.assertEqual(len(logger.handlers), 1)
        self.assertIsInstance(logger.handlers[0], logging.StreamHandler)
        shutdown_logging(logger)

    def test_setup_logging_rebuilds_file_handler_when_log_dir_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            first_dir = Path(tmp) / "first"
            second_dir = Path(tmp) / "second"
            logger_name = self._fresh_logger_name()

            logger = setup_logging(log_dir=first_dir, logger_name=logger_name)
            logger.info("message in first dir")

            # Calling again with a different log_dir must rebuild the file
            # handler to point at the new location, not silently keep
            # writing to the old one.
            logger = setup_logging(log_dir=second_dir, logger_name=logger_name)
            logger.info("message in second dir")

            self.assertEqual(len(logger.handlers), 2)

            first_logs = list(first_dir.glob("*.log"))
            second_logs = list(second_dir.glob("*.log"))
            self.assertEqual(len(first_logs), 1)
            self.assertEqual(len(second_logs), 1)
            self.assertIn("message in first dir", first_logs[0].read_text(encoding="utf-8"))
            self.assertIn("message in second dir", second_logs[0].read_text(encoding="utf-8"))
            # The old file handler should no longer receive new messages.
            self.assertNotIn("message in second dir", first_logs[0].read_text(encoding="utf-8"))

            shutdown_logging(logger)

    def test_setup_logging_falls_back_gracefully_when_log_dir_unwritable(self):
        # Pointing the log dir at a path that can't be created as a
        # directory (a file already occupies that name) simulates an
        # unwritable filesystem without needing real permission changes.
        with tempfile.TemporaryDirectory() as tmp:
            blocked_path = Path(tmp) / "blocked"
            blocked_path.write_text("not a directory")

            logger_name = self._fresh_logger_name()
            # Must not raise - logging setup failures should degrade to
            # console-only, not crash the program.
            logger = setup_logging(log_dir=blocked_path, logger_name=logger_name)

            self.assertEqual(len(logger.handlers), 1)
            self.assertIsInstance(logger.handlers[0], logging.StreamHandler)
            shutdown_logging(logger)


class FakeStream:
    """Minimal stand-in for sys.stdout/sys.stderr with a configurable
    ``encoding`` attribute and a mockable ``reconfigure()`` method, so tests
    don't have to touch the real process streams."""

    def __init__(self, encoding, support_reconfigure=True, raise_on_reconfigure=None):
        self.encoding = encoding
        if support_reconfigure:
            self.reconfigure = mock.Mock(side_effect=raise_on_reconfigure)
        # else: no `.reconfigure` attribute at all, like older Python.


class EnsureUtf8ConsoleTests(unittest.TestCase):

    def test_reconfigures_non_utf8_stdout_and_stderr(self):
        fake_out = FakeStream(encoding="cp1252")
        fake_err = FakeStream(encoding="cp1252")

        with mock.patch("sys.stdout", fake_out), mock.patch("sys.stderr", fake_err):
            ensure_utf8_console()

        fake_out.reconfigure.assert_called_once_with(encoding="utf-8", errors="replace")
        fake_err.reconfigure.assert_called_once_with(encoding="utf-8", errors="replace")

    def test_skips_stream_already_utf8(self):
        # Also covers the case-insensitive/hyphen-insensitive match (e.g.
        # "UTF-8" reported by some platforms rather than "utf-8").
        fake_out = FakeStream(encoding="UTF-8")

        with mock.patch("sys.stdout", fake_out), mock.patch("sys.stderr", fake_out):
            ensure_utf8_console()

        fake_out.reconfigure.assert_not_called()

    def test_skips_stream_without_reconfigure_method(self):
        fake_out = FakeStream(encoding="cp1252", support_reconfigure=False)

        with mock.patch("sys.stdout", fake_out), mock.patch("sys.stderr", fake_out):
            # Must not raise even though .reconfigure doesn't exist.
            ensure_utf8_console()

        self.assertFalse(hasattr(fake_out, "reconfigure"))

    def test_swallows_value_error_from_reconfigure(self):
        fake_out = FakeStream(encoding="cp1252", raise_on_reconfigure=ValueError("closed"))
        fake_err = FakeStream(encoding="cp1252")

        with mock.patch("sys.stdout", fake_out), mock.patch("sys.stderr", fake_err):
            # Must not propagate - this is a defensive helper and should
            # never itself crash a run. The failure on stdout also must not
            # prevent stderr from still being reconfigured.
            ensure_utf8_console()

        fake_out.reconfigure.assert_called_once()
        fake_err.reconfigure.assert_called_once()

    def test_swallows_os_error_from_reconfigure(self):
        fake_out = FakeStream(encoding="cp1252", raise_on_reconfigure=OSError("detached"))
        fake_err = FakeStream(encoding="cp1252")

        with mock.patch("sys.stdout", fake_out), mock.patch("sys.stderr", fake_err):
            ensure_utf8_console()

        fake_out.reconfigure.assert_called_once()
        fake_err.reconfigure.assert_called_once()

    def test_skips_none_stream(self):
        # e.g. `python -OO` with PYTHONIOENCODING weirdness, or a stream
        # explicitly set to None by some embedding host - must not crash
        # on attribute access.
        with mock.patch("sys.stdout", None), mock.patch("sys.stderr", None):
            ensure_utf8_console()

    def test_real_stringio_stream_is_left_alone_without_crashing(self):
        # io.StringIO has no .reconfigure() at all (it's not a text-wrapper
        # around a buffer) - exercise the real object, not just a mock, to
        # confirm getattr(..., None) handles it rather than raising
        # AttributeError.
        fake_out = io.StringIO()

        with mock.patch("sys.stdout", fake_out), mock.patch("sys.stderr", fake_out):
            ensure_utf8_console()  # Must not raise.


if __name__ == "__main__":
    unittest.main()
