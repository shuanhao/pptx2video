"""Exercise CLI callbacks through offline TTS retries, without media tools."""

import logging
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from aiohttp import WSServerHandshakeError
from edge_tts.exceptions import NoAudioReceived

from src.main import main
from src.tts import generate_audio_files


class TtsStatusMessageTests(unittest.TestCase):
    def test_cli_reports_completed_audio_and_concise_retries_with_default_or_override(self):
        for override, limit, delay_override, delay in ((None, 10, None, 5.0), (2, 2, .25, .25)):
            with self.subTest(override=override, delay=delay), tempfile.TemporaryDirectory() as tmp:
                failures = [
                    WSServerHandshakeError(
                        SimpleNamespace(real_url="wss://example.invalid/speech?token=test"),
                        (), status=503, message="Invalid response status",
                    ),
                    NoAudioReceived("No audio was received. Please verify that your parameters are correct."),
                ]
                calls = []

                class SuccessfulCommunicate:
                    async def stream(self):
                        yield {"type": "audio", "data": b"offline-audio"}
                        yield {"type": "WordBoundary", "text": "Hello", "offset": 0,
                               "duration": 2000000}

                def factory(**kwargs):
                    calls.append(kwargs)
                    if len(calls) <= len(failures):
                        raise failures[len(calls) - 1]
                    return SuccessfulCommunicate()

                def offline_generate(*args, **kwargs):
                    return generate_audio_files(*args, communicate_factory=factory, **kwargs)

                argv = ["pptx2video", "offline.pptx", "--generate-audio",
                        "--audio-output-dir", str(Path(tmp) / "audio"),
                        "--output", str(Path(tmp) / "slides.json"),
                        "--subtitles-output=", "--no-file-log"]
                if override is not None:
                    argv += ["--tts-max-retries", str(override)]
                if delay_override is not None:
                    argv += ["--tts-retry-delay", str(delay_override)]
                logger = logging.Logger("tts-status-test", level=logging.DEBUG)
                with patch.object(sys, "argv", argv), \
                     patch("src.main.extract_notes", return_value=[{"slide_num": 6, "notes": "Hello"}]), \
                     patch("src.main.setup_logging", return_value=logger), \
                     patch("src.main.generate_audio_files", side_effect=offline_generate) as generate, \
                     patch("src.tts.time.sleep") as sleep, \
                     self.assertLogs(logger, level="DEBUG") as captured:
                    main()

                self.assertEqual(generate.call_args.kwargs["max_retries"], limit)
                self.assertEqual(generate.call_args.kwargs["retry_delay_seconds"], delay)
                self.assertEqual(len(calls), 3)
                self.assertEqual(sleep.call_count, 2)
                sleep.assert_called_with(delay)
                warnings = [r.getMessage() for r in captured.records if r.levelno == logging.WARNING]
                self.assertEqual(warnings, [
                    f"Slide 6: attempt 1/{limit + 1} failed (WebSocket handshake HTTP 503); retrying in {delay:g}s...",
                    f"Slide 6: attempt 2/{limit + 1} failed (No audio received; cause undetermined); retrying in {delay:g}s...",
                ])
                infos = [r.getMessage() for r in captured.records if r.levelno == logging.INFO]
                self.assertIn("Generated audio 1/1 (slide 6).", infos)
                self.assertFalse(any("Generating audio" in message for message in infos))
                debug = [r for r in captured.records if r.levelno == logging.DEBUG]
                self.assertTrue(any("wss://example.invalid" in r.getMessage() and r.exc_info for r in debug))


if __name__ == "__main__":
    unittest.main()
