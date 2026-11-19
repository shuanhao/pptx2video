"""Experimental direct Microsoft WebSocket transport, based on observed web frames.

No website proxy, browser automation, package monkeypatching, or automatic
fallback. One SSML request per slide; very long requests can fail explicitly.
The GEC helper remains coupled to edge-tts and is isolated in this module.
"""
from __future__ import annotations

import asyncio
import html
import json
import re
import ssl
import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiohttp
from edge_tts.constants import TRUSTED_CLIENT_TOKEN
from edge_tts.drm import DRM

from src.tts_backend import SynthesisRequest, SynthesisResult, TTSBackendError
from src.tts_boundary_text import normalize_boundary_text

ENDPOINT = "wss://api.msedgeservices.com/tts/cognitiveservices/websocket/v1"
PROTOCOL_VERSION = "2-155.0.4283.45"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36 Edg/155.0.0.0")
OUTPUT_FORMAT = "audio-24khz-48kbitrate-mono-mp3"
TICKS_PER_SECOND = 10_000_000


def normalize_settings(request):
    voice = request.voice
    full = re.fullmatch(r"Microsoft Server Speech Text to Speech Voice \(([^,]+),\s*([^\)]+)\)", voice)
    if full:
        voice = full[1] + "-" + full[2]
    if not re.fullmatch(r"[a-z]{2,}-[A-Z]{2,}(?:-[A-Za-z0-9]+)+Neural", voice):
        raise ValueError("Invalid TTS voice name")
    if not re.fullmatch(r"[+-]\d+%", request.rate):
        raise ValueError("TTS rate must be a signed integer percentage")
    # Zero is equivalent in either unit. Never guess a Hz-to-percent conversion.
    if request.pitch in ("+0Hz", "-0Hz", "0Hz"):
        pitch = "0%"
    elif re.fullmatch(r"[+-]?\d+%", request.pitch):
        pitch = request.pitch
    else:
        raise ValueError("edge-websocket supports percentage pitch or +0Hz; nonzero Hz is unsupported")
    return voice, request.rate, pitch


def build_frames(request, request_id, timestamp):
    voice, rate, pitch = normalize_settings(request)
    config = {"context": {"synthesis": {"audio": {
        "metadataoptions": {"sentenceBoundaryEnabled": False, "wordBoundaryEnabled": True},
        "outputFormat": OUTPUT_FORMAT,
    }}}}
    ssml = ("<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>"
            f"<voice name='{html.escape(voice, quote=True)}'>"
            f"<prosody pitch='{pitch}' rate='{rate}' volume='0%'>"
            f"{html.escape(request.text, quote=True)}</prosody></voice></speak>")
    return (
        f"X-Timestamp:{timestamp}\r\nContent-Type:application/json; charset=utf-8\r\n"
        f"Path:speech.config\r\n\r\n{json.dumps(config, separators=(',', ':'))}",
        f"X-RequestId:{request_id}\r\nContent-Type:application/ssml+xml\r\n"
        f"X-Timestamp:{timestamp}Z\r\nPath:ssml\r\n\r\n{ssml}",
    )


def _headers(raw):
    return {key.strip().lower(): value.strip()
            for line in raw.split("\r\n") if ":" in line
            for key, value in [line.split(":", 1)]}


async def _receive(ws, output, boundaries):
    completed = False
    async for message in ws:
        if message.type == aiohttp.WSMsgType.TEXT:
            head, separator, body = message.data.partition("\r\n\r\n")
            path = _headers(head).get("path")
            if path == "audio.metadata":
                if not separator:
                    raise ValueError("Missing metadata body")
                for event in json.loads(body)["Metadata"]:
                    if event.get("Type") == "WordBoundary":
                        data = event["Data"]
                        boundaries.append({"text": data["text"]["Text"],
                                           "offset_seconds": data["Offset"] / TICKS_PER_SECOND,
                                           "duration_seconds": data["Duration"] / TICKS_PER_SECOND})
            elif path == "turn.end":
                completed = True
                break
        elif message.type == aiohttp.WSMsgType.BINARY:
            data = message.data
            if len(data) < 2:
                raise ValueError("Truncated binary frame")
            end = 2 + int.from_bytes(data[:2], "big")
            if end <= 2 or end > len(data):
                raise ValueError("Invalid binary header length")
            if _headers(data[2:end].decode("utf-8")).get("path") == "audio":
                output.write(data[end:])
        elif message.type == aiohttp.WSMsgType.ERROR:
            raise TTSBackendError("TTS WebSocket stream failed", retryable=True)
    if not completed:
        raise TTSBackendError("TTS stream ended before turn.end", retryable=True)
    if not output.tell() or not boundaries:
        raise TTSBackendError("TTS completed without audio or word boundaries", retryable=True)


class EdgeWebSocketBackend:
    name = "edge-websocket"

    def __init__(self, *, session_factory=None):
        self.session_factory = session_factory or aiohttp.ClientSession

    async def _synthesize(self, request, output_path):
        params = {"TrustedClientToken": TRUSTED_CLIENT_TOKEN,
                  "Ocp-Apim-Subscription-Key": TRUSTED_CLIENT_TOKEN,
                  "Sec-MS-GEC": DRM.generate_sec_ms_gec(),
                  "Sec-MS-GEC-Version": PROTOCOL_VERSION,
                  "ConnectionId": uuid.uuid4().hex.upper()}
        timeout = aiohttp.ClientTimeout(total=90, connect=15, sock_read=30)
        headers = {"User-Agent": USER_AGENT, "Origin": "https://zh-tw.text-to-speech.online"}
        boundaries = []
        async with self.session_factory(timeout=timeout, trust_env=True) as session:
            async with session.ws_connect(ENDPOINT, params=params, headers=headers, compress=15) as ws:
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                for frame in build_frames(request, uuid.uuid4().hex.upper(), stamp):
                    await ws.send_str(frame)
                with output_path.open("wb") as output:
                    await _receive(ws, output, boundaries)
        voice, rate, pitch = normalize_settings(request)
        boundaries = normalize_boundary_text(request.text, boundaries)
        return SynthesisResult(boundaries, {
            "backend": self.name, "implementation_version": "2",
            "boundary_text_normalization": "source-checked-xml-v1",
            "protocol_version": PROTOCOL_VERSION, "voice": voice,
            "rate": rate, "pitch": pitch,
        })

    def synthesize(self, request: SynthesisRequest, output_path: Path) -> SynthesisResult:
        normalize_settings(request)  # Reject unsupported settings before opening a connection.
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            return asyncio.run(asyncio.wait_for(self._synthesize(request, output_path), timeout=90))
        except aiohttp.WSServerHandshakeError as exc:
            raise TTSBackendError(f"WebSocket handshake HTTP {exc.status}",
                                  retryable=exc.status in (408, 429, 500, 502, 503, 504)) from exc
        except (aiohttp.ClientConnectorCertificateError, ssl.SSLCertVerificationError) as exc:
            raise TTSBackendError("TTS certificate verification failed") from exc
        except (aiohttp.ClientError, ConnectionError, TimeoutError, asyncio.TimeoutError) as exc:
            raise TTSBackendError("TTS connection or timeout failure", retryable=True) from exc
        except (KeyError, ValueError, TypeError, UnicodeError) as exc:
            raise TTSBackendError("Invalid TTS protocol response") from exc
