"""Offline transport, publication and subtitle compatibility tests."""
import asyncio
import io
import json
import tempfile
import unittest
import sys
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import aiohttp

from src.audio_preparation import validate_audio_manifest, prepare_audio_manifest, AudioPreparationOptions
from src.exceptions import AudioPreparationError, TTSGenerationError
from src.tts import generate_audio_files
from src.tts_backend import SynthesisRequest, SynthesisResult, TTSBackendError, create_backend
from src.tts_websocket import EdgeWebSocketBackend, build_frames, normalize_settings, _receive


BOUNDARIES = [{"text": "Hello", "offset_seconds": 0.05, "duration_seconds": 0.5}]


class FakeBackend:
    name = "edge-websocket"

    def synthesize(self, request, output_path):
        output_path.write_bytes(b"complete")
        return SynthesisResult(BOUNDARIES, {"backend": self.name, "voice": request.voice,
                                            "rate": request.rate, "pitch": request.pitch})


class FakeWebSocket:
    def __init__(self, messages):
        self.messages = messages
        self.sent = []

    def __aiter__(self):
        async def stream():
            for message in self.messages:
                yield message
        return stream()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def send_str(self, frame):
        self.sent.append(frame)


def text_frame(path, body=""):
    return SimpleNamespace(type=aiohttp.WSMsgType.TEXT, data=f"Path:{path}\r\n\r\n{body}")


def audio_frame(payload=b"audio"):
    header = b"Path:audio\r\nContent-Type:audio/mpeg\r\n"
    return SimpleNamespace(type=aiohttp.WSMsgType.BINARY,
                           data=len(header).to_bytes(2, "big") + header + payload)


def successful_messages():
    metadata = {"Metadata": [{"Type": "WordBoundary", "Data": {
        "Offset": 500000, "Duration": 5000000, "text": {"Text": "Hello"}}}]}
    return [text_frame("turn.start"), audio_frame(),
            text_frame("audio.metadata", json.dumps(metadata)), text_frame("turn.end")]


class BackendProtocolTests(unittest.TestCase):
    def test_settings_and_frames_preserve_text_and_explicit_parameters(self):
        request = SynthesisRequest("A & B\n<測試>",
            "Microsoft Server Speech Text to Speech Voice (zh-TW, YunJheNeural)", "-10%", "+0Hz")
        self.assertEqual(normalize_settings(request), ("zh-TW-YunJheNeural", "-10%", "0%"))
        config, ssml = build_frames(request, "request-id", "stamp")
        self.assertIs(json.loads(config.partition("\r\n\r\n")[2])["context"]["synthesis"]["audio"]
                      ["metadataoptions"]["wordBoundaryEnabled"], True)
        self.assertIn("A &amp; B\n&lt;測試&gt;", ssml)
        self.assertIn("rate='-10%'", ssml)
        self.assertIn("pitch='0%'", ssml)
        self.assertEqual(normalize_settings(SynthesisRequest("Hi", "en-US-AriaNeural", pitch="+5%"))[2], "+5%")

    def test_unsupported_pitch_fails_before_connecting(self):
        with tempfile.TemporaryDirectory() as tmp, patch("src.tts_websocket.aiohttp.ClientSession") as session:
            with self.assertRaisesRegex(ValueError, "nonzero Hz"):
                EdgeWebSocketBackend().synthesize(
                    SynthesisRequest("Hi", "zh-TW-YunJheNeural", pitch="+5Hz"), Path(tmp) / "audio.mp3")
            session.assert_not_called()

    def test_parser_requires_completion_audio_and_timing(self):
        for messages in (successful_messages()[:-1], [text_frame("turn.end")],
                         [audio_frame(), text_frame("turn.end")]):
            with self.subTest(messages=messages), self.assertRaises(TTSBackendError):
                asyncio.run(_receive(FakeWebSocket(messages), io.BytesIO(), []))
        boundaries, output = [], io.BytesIO()
        asyncio.run(_receive(FakeWebSocket(successful_messages()), output, boundaries))
        self.assertEqual(output.getvalue(), b"audio")
        self.assertEqual(boundaries, BOUNDARIES)

    def test_malformed_binary_and_metadata_do_not_pass(self):
        malformed = [SimpleNamespace(type=aiohttp.WSMsgType.BINARY, data=b"x"),
                     SimpleNamespace(type=aiohttp.WSMsgType.BINARY, data=b"\xff\xffx"),
                     text_frame("audio.metadata", "{}")]
        for message in malformed:
            with self.subTest(message=message), self.assertRaises((ValueError, KeyError)):
                asyncio.run(_receive(FakeWebSocket([message]), io.BytesIO(), []))

    def test_real_adapter_with_injected_session_and_common_sidecars(self):
        ws = FakeWebSocket(successful_messages())

        class Session:
            def __init__(self, **kwargs):
                pass
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            def ws_connect(self, url, **kwargs):
                self.url = url
                return ws

        with tempfile.TemporaryDirectory() as tmp:
            manifest = generate_audio_files([{"slide_num": 7, "notes": "Hello"}], tmp,
                backend=EdgeWebSocketBackend(session_factory=Session), max_retries=0)
            self.assertEqual((Path(tmp) / "slide_007.mp3").read_bytes(), b"audio")
            self.assertEqual(json.loads((Path(tmp) / "slide_007.wordboundaries.json").read_text()), BOUNDARIES)
            self.assertEqual(manifest["slides"][0]["tts"]["backend"], "edge-websocket")
            self.assertIn("voice name='zh-TW-YunJheNeural'", ws.sent[1])

    def test_handshake_classification_and_no_request_url_in_summary(self):
        for status in (403, 503):
            error = aiohttp.WSServerHandshakeError(SimpleNamespace(real_url="wss://secret?token=value"),
                                                   (), status=status)
            backend = EdgeWebSocketBackend()
            with tempfile.TemporaryDirectory() as tmp, patch.object(backend, "_synthesize", side_effect=error):
                with self.assertRaises(TTSBackendError) as caught:
                    backend.synthesize(SynthesisRequest("Hi", "zh-TW-YunJheNeural"), Path(tmp) / "audio.mp3")
            self.assertEqual(caught.exception.retryable, status == 503)
            self.assertNotIn("secret", str(caught.exception))

    def test_factory_rejects_ambiguous_injection(self):
        with self.assertRaises(ValueError):
            create_backend("edge-websocket", communicate_factory=object())


class PublicationTests(unittest.TestCase):
    def test_failed_later_slide_preserves_whole_previous_batch(self):
        class FailsLater(FakeBackend):
            def synthesize(self, request, path):
                if request.text == "fail":
                    path.write_bytes(b"partial")
                    raise TTSBackendError("No audio", retryable=True)
                return super().synthesize(request, path)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("manifest.json", "slide_001.mp3", "slide_001.wordboundaries.json"):
                (root / name).write_bytes(b"previous")
            with self.assertRaises(TTSGenerationError):
                generate_audio_files([{"slide_num": 1, "notes": "Hello"}, {"slide_num": 2, "notes": "fail"}],
                                     root, backend=FailsLater(), max_retries=0, manifest_path=root / "manifest.json")
            for name in ("manifest.json", "slide_001.mp3", "slide_001.wordboundaries.json"):
                self.assertEqual((root / name).read_bytes(), b"previous")
            self.assertFalse((root / "slide_002.mp3").exists())
            self.assertFalse(list(root.glob(".tts-*")))

    def test_common_retries_and_gap_check_apply_to_second_backend(self):
        calls = []
        class Flaky(FakeBackend):
            def synthesize(self, request, path):
                calls.append(request)
                if len(calls) == 1:
                    path.write_bytes(b"partial")
                    raise TTSBackendError("temporary", retryable=True)
                return super().synthesize(request, path)
        with tempfile.TemporaryDirectory() as tmp, patch("src.tts.find_suspected_dropped_narration", return_value=[{"gap": 1}]) as gap:
            notices = []
            manifest = generate_audio_files([{"slide_num": 1, "notes": "Hello"}], tmp,
                backend=Flaky(), retry_delay_seconds=0, max_retries=1,
                on_narration_gap=lambda *args: notices.append(args))
            self.assertEqual(len(calls), 2)
            gap.assert_called_once_with("Hello", BOUNDARIES)
            self.assertEqual(notices, [(1, {"gap": 1})])
            self.assertEqual(manifest["slides"][0]["narration_gap_warnings"], [{"gap": 1}])
            self.assertEqual((Path(tmp) / "slide_001.mp3").read_bytes(), b"complete")

    def test_partial_regeneration_preserves_other_backend_provenance(self):
        old = {"slides": [{"slide_num": 1, "audio_file": "slide_001.mp3", "tts": {"backend": "edge-tts"}}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            result = generate_audio_files([{"slide_num": 2, "notes": "Hello"}], tmp,
                backend=FakeBackend(), previous_manifest=old, manifest_path=path)
            saved = json.loads(path.read_text())
            self.assertEqual(saved, result)
            self.assertEqual(saved["slides"][0], old["slides"][0])
            self.assertEqual(saved["slides"][1]["tts"]["backend"], "edge-websocket")

    def test_interrupted_publication_blocks_existing_consumers(self):
        import os
        real_replace = os.replace
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def interrupt(source, dest):
                if Path(dest).suffix == ".mp3":
                    raise OSError("disk unavailable")
                return real_replace(source, dest)
            with patch("src.tts.os.replace", side_effect=interrupt), self.assertRaises(TTSGenerationError):
                generate_audio_files([{"slide_num": 1, "notes": "Hello"}], root,
                    backend=FakeBackend(), manifest_path=root / "manifest.json")
            manifest = json.loads((root / "manifest.json").read_text())
            with self.assertRaises(AudioPreparationError):
                validate_audio_manifest(manifest)
            with self.assertRaises(AudioPreparationError):
                prepare_audio_manifest(manifest, root, root / "prepared", AudioPreparationOptions())
            from src.ppt_automation import load_audio_manifest
            with self.assertRaises(AudioPreparationError):
                load_audio_manifest(root / "manifest.json")

    def test_invalid_boundaries_fail_without_publication(self):
        for start in (float("nan"), -1):
            class Bad(FakeBackend):
                def synthesize(self, request, path):
                    result = super().synthesize(request, path)
                    result.word_boundaries = [{"text": "Hello", "offset_seconds": start, "duration_seconds": .5}]
                    return result
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(TTSGenerationError):
                    generate_audio_files([{"slide_num": 1, "notes": "Hello"}], tmp, backend=Bad(), max_retries=0)
                self.assertFalse((Path(tmp) / "slide_001.mp3").exists())

    def test_legacy_manifest_is_still_accepted(self):
        validate_audio_manifest({"slides": []})


class BackendIntegrationTests(unittest.TestCase):
    def test_cli_selects_default_or_explicit_backend_and_forwards_settings(self):
        from src.main import main
        from src.logging_config import shutdown_logging
        self.addCleanup(shutdown_logging)
        for option, expected in (([], "edge-tts"), (["--tts-backend", "edge-websocket"], "edge-websocket")):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                backend = FakeBackend()
                argv = ["pptx2video", "input.pptx", "--generate-audio", "--no-file-log",
                        "--audio-output-dir", str(root / "audio"), "--output", str(root / "slides.json"),
                        "--subtitles-output=", "--rate=-10%", "--voice", "en-US-AriaNeural"] + option
                with patch.object(sys, "argv", argv), \
                     patch("src.main.extract_notes", return_value=[{"slide_num": 1, "notes": "Hello"}]), \
                     patch("src.tts.create_backend", return_value=backend) as select, \
                     patch.object(backend, "synthesize", wraps=backend.synthesize) as synthesize, \
                     redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    main()
                select.assert_called_once_with(expected, communicate_factory=None)
                request = synthesize.call_args.args[0]
                self.assertEqual((request.voice, request.rate, request.pitch), ("en-US-AriaNeural", "-10%", "+0Hz"))

    def test_second_backend_outputs_feed_existing_vtt_and_srt_without_shift_changes(self):
        from src.subtitle_pipeline import generate_srt_for_deck
        from src.subtitle_vtt import write_slide_vtt
        slides = [{"slide_num": 1, "notes": ""}, {"slide_num": 2, "notes": "Hello"}]
        with tempfile.TemporaryDirectory() as tmp, patch(
                "src.subtitle_pipeline._measure_audio_duration_seconds", return_value=2.0):
            root = Path(tmp)
            manifest = generate_audio_files(slides, root, backend=FakeBackend())
            paths = write_slide_vtt(slides, manifest, root, root / "vtt")
            srt, warnings = generate_srt_for_deck(slides, manifest, root)
            self.assertEqual(warnings, [])
            self.assertIn("Hello", srt)
            self.assertIn("00:00:05,050", srt)
            self.assertIn("00:00:00.050", paths[0].read_text(encoding="utf-8"))

    def test_reusing_audio_does_not_create_a_backend(self):
        from src.main import main
        from src.logging_config import shutdown_logging
        self.addCleanup(shutdown_logging)
        with tempfile.TemporaryDirectory() as tmp:
            argv = ["pptx2video", "input.pptx", "--tts-backend", "edge-websocket", "--no-file-log",
                    "--audio-output-dir", str(Path(tmp) / "audio"), "--output", str(Path(tmp) / "slides.json"),
                    "--subtitles-output="]
            with patch.object(sys, "argv", argv), patch("src.main.extract_notes", return_value=[]), \
                 patch("src.tts.create_backend") as select, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                main()
            select.assert_not_called()


if __name__ == "__main__":
    unittest.main()
