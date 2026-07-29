import logging
import tempfile
import unittest
from pathlib import Path

from src.logging_config import setup_logging, shutdown_logging

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


if __name__ == "__main__":
    unittest.main()
