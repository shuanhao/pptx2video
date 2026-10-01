"""Optional derived audio preparation; no CLI or PowerPoint dependencies.

Original files are never modified. Every enabled run rebuilds all entries using
fixed filenames. An incomplete manifest blocks consumers until the batch succeeds.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from src.exceptions import AudioPreparationError


@dataclass(frozen=True)
class AudioPreparationOptions:
    tail_silence: float = 0
    format: str = "m4a"
    bitrate: Optional[str] = None
    sample_rate: int = 24000
    channels: int = 1

    def settings(self):
        result = asdict(self)
        result["bitrate"] = (self.bitrate or "64k") if self.format == "m4a" else None
        return result


def validate_preparation_options(options, source_dir=None, output_dir=None,
                                 explicit_options=()):
    """Return whether enabled. CLI callers must supply explicitly given options."""
    seconds = options.tail_silence
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds):
        raise ValueError("tail_silence must be finite: 0 or 1..10 seconds")
    if seconds != 0 and not 1 <= seconds <= 10:
        raise ValueError("tail_silence must be 0 or 1..10 seconds")
    if seconds == 0:
        if explicit_options or options != AudioPreparationOptions():
            raise ValueError("Preparation settings require nonzero tail_silence")
        return False
    if options.format not in ("m4a", "wav"):
        raise ValueError("Prepared format must be m4a or wav")
    if options.format == "wav" and options.bitrate is not None:
        raise ValueError("WAV does not accept AAC bitrate")
    if options.bitrate is not None and not re.fullmatch(r"[1-9][0-9]*k", options.bitrate):
        raise ValueError("Bitrate must be a positive integer followed by k")
    if type(options.sample_rate) is not int or options.sample_rate not in (8000, 16000, 22050, 24000, 32000, 44100, 48000):
        raise ValueError("Unsupported sample rate")
    if type(options.channels) is not int or options.channels not in (1, 2):
        raise ValueError("Channels must be 1 or 2")
    if source_dir is not None and output_dir is not None:
        source, output = Path(source_dir).resolve(), Path(output_dir).resolve()
        if source == output or source in output.parents or output in source.parents:
            raise ValueError("Source and prepared directories must be separate, not nested")
    return True


def _run(argv):
    try:
        result = subprocess.run(argv, capture_output=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AudioPreparationError(f"Cannot run {argv[0]}: {exc}") from exc
    if result.returncode:
        raise AudioPreparationError(f"{argv[0]} failed: {result.stderr.decode('utf-8', errors='replace')[-4000:]}")
    return result.stdout


def probe_audio(path):
    """Probe format and measure decoded sample duration (bounded memory)."""
    path = Path(path)
    try:
        data = json.loads(_run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                               "-show_streams", "-of", "json", str(path)]))
        stream = data["streams"][0]
        rate, channels = int(stream["sample_rate"]), int(stream["channels"])
        # FFmpeg reports bytes written to a null PCM muxer; no large PCM buffer.
        progress = _run(["ffmpeg", "-v", "error", "-xerror", "-nostdin", "-i", str(path),
                         "-map", "0:a:0", "-c:a", "pcm_s16le", "-f", "s16le",
                         "-progress", "pipe:1", "-nostats", "-y", os.devnull])
        sizes = re.findall(rb"total_size=(\d+)", progress)
        duration = int(sizes[-1]) / (rate * channels * 2)
        if duration <= 0 or not math.isfinite(duration):
            raise ValueError("Empty decoded audio")
        return {"codec": stream["codec_name"], "sample_rate": rate,
                "channels": channels, "duration_seconds": duration}
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise AudioPreparationError(f"Invalid audio {path}: {exc}") from exc


def _hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inside(root, name):
    path = (root / name).resolve()
    if path == root or root not in path.parents:
        raise ValueError(f"File escapes audio directory: {name}")
    return path


def prepare_audio_file(source, output, options) -> Dict[str, Any]:
    """Convert an original MP3; publish only a fully decoded, validated result."""
    if not validate_preparation_options(options):
        raise ValueError("prepare_audio_file requires nonzero tail_silence")
    source, output = Path(source).resolve(), Path(output).resolve()
    if source.suffix.lower() != ".mp3" or output.suffix.lower() != "." + options.format or source == output:
        raise ValueError("Use an original MP3 and a distinct output with the requested suffix")
    original = probe_audio(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{uuid.uuid4().hex}{output.suffix}")
    try:
        codec = (["-c:a", "aac", "-profile:a", "aac_low", "-b:a", options.settings()["bitrate"]]
                 if options.format == "m4a" else ["-c:a", "pcm_s16le"])
        _run(["ffmpeg", "-v", "error", "-xerror", "-nostdin", "-y", "-i", str(source),
              "-map", "0:a:0", "-vn", "-af", f"apad=pad_dur={options.tail_silence}",
              "-ar", str(options.sample_rate), "-ac", str(options.channels),
              *codec, str(temporary)])
        prepared = probe_audio(temporary)
        expected_codec = "aac" if options.format == "m4a" else "pcm_s16le"
        # AAC decoding can expose a final padded frame; permit two AAC frames.
        tolerance = 2 * 1024 / options.sample_rate if options.format == "m4a" else 2 / options.sample_rate
        if (prepared["codec"] != expected_codec or prepared["sample_rate"] != options.sample_rate
                or prepared["channels"] != options.channels
                or abs(prepared["duration_seconds"] - original["duration_seconds"] - options.tail_silence) > tolerance):
            raise AudioPreparationError(f"Prepared audio validation failed: {prepared}")
        os.replace(temporary, output)
        return {"source_probe": original, "prepared_probe": prepared}
    finally:
        temporary.unlink(missing_ok=True)


def validate_audio_manifest(manifest):
    """Reject unfinished fixed-name batches; accept original and legacy manifests."""
    metadata = manifest.get("preparation") or {}
    if not isinstance(metadata, dict):
        raise AudioPreparationError("Invalid prepared audio metadata")
    if metadata.get("status") not in (None, "ready") or (
            metadata.get("schema_version", 1) >= 2 and metadata.get("status") != "ready"):
        raise AudioPreparationError("Prepared audio manifest is incomplete; rerun preparation from originals")


def _publish_manifest(destination, manifest):
    temporary = destination.with_name(f".manifest-{uuid.uuid4().hex}.json")
    try:
        temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, destination)
    except OSError as exc:
        raise AudioPreparationError(f"Cannot publish prepared manifest: {exc}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def prepare_audio_manifest(manifest, source_dir, output_dir, options,
                           explicit_options=()):
    """Return effective manifest/directory and converted slide numbers.

    Caller supplies the already merged original manifest. Missing WordBoundary is
    supported. Unknown manifest/slide fields are preserved. No TTS is invoked.
    """
    source, output = Path(source_dir).resolve(), Path(output_dir).resolve()
    enabled = validate_preparation_options(options, source, output, explicit_options)
    if not enabled:
        return {"manifest": copy.deepcopy(manifest), "audio_dir": source, "converted": []}
    if manifest.get("preparation"):
        raise ValueError("Prepared manifests cannot be preparation sources")
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise AudioPreparationError(f"Required tool not found: {tool}")
    tools = {tool: _run([tool, "-version"]).decode("utf-8", errors="replace")
             for tool in ("ffmpeg", "ffprobe")}
    entries, numbers = [], set()
    # Validate and fingerprint every source before starting any output work.
    for entry in manifest["slides"]:
        number = entry["slide_num"]
        if type(number) is not int or number <= 0 or number in numbers or entry.get("preparation"):
            raise ValueError(f"Invalid, duplicate or prepared slide: {number}")
        numbers.add(number)
        audio = _inside(source, entry["audio_file"])
        if audio.suffix.lower() != ".mp3":
            raise ValueError(f"Slide {number}: expected original MP3")
        boundary = _inside(source, entry["word_boundaries_file"]) if entry.get("word_boundaries_file") else None
        try:
            fingerprint = {"schema_version": 1, "source_audio": str(audio), "audio_sha256": _hash(audio),
                           "boundary_sha256": _hash(boundary) if boundary else None,
                           "settings": options.settings(), "tools": tools}
        except OSError as exc:
            raise AudioPreparationError(f"Slide {number}: cannot read source: {exc}") from exc
        entries.append((entry, audio, boundary, fingerprint))
    destination = output / "manifest.json"
    if destination.exists():
        try:
            old = json.loads(destination.read_text(encoding="utf-8"))
            if not old.get("preparation"):
                raise ValueError("Refusing to overwrite a non-prepared manifest")
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise AudioPreparationError(f"Cannot read prepared manifest: {exc}") from exc
    result = copy.deepcopy(manifest)
    result.update(output_dir=str(output), slides=[], preparation={"schema_version": 2, "kind": "prepared", "status": "incomplete"})
    converted = []
    output.mkdir(parents=True, exist_ok=True)
    _publish_manifest(destination, result)
    for entry, audio, boundary, fingerprint in entries:
        number = entry["slide_num"]
        new = copy.deepcopy(entry)
        relative = Path(f"slide_{number:03d}.{options.format}")
        _inside(output, str(relative))
        _inside(output, str(relative.with_suffix(".wordboundaries.json")))
        try:
            metadata = prepare_audio_file(audio, output / relative, options)
            new["audio_file"] = relative.as_posix()
            new["word_boundaries_file"] = None
            if boundary:
                copied = relative.with_suffix(".wordboundaries.json")
                shutil.copyfile(boundary, output / copied)
                new["word_boundaries_file"] = copied.as_posix()
            # Catch input changes during conversion/copy before publishing.
            if _hash(audio) != fingerprint["audio_sha256"] or (boundary and _hash(boundary) != fingerprint["boundary_sha256"]):
                raise AudioPreparationError("Source changed during preparation")
            metadata.update(fingerprint=fingerprint,
                            output_hashes={field: _hash(output / new[field]) for field in
                                           ("audio_file", "word_boundaries_file") if new.get(field)})
            new["preparation"] = metadata
            converted.append(number)
        except (OSError, AudioPreparationError) as exc:
            raise AudioPreparationError(f"Slide {number}, {audio}: {exc}") from exc
        result["slides"].append(new)
    # Recheck all sources: originals may have changed during a long batch.
    for entry, audio, boundary, fingerprint in entries:
        try:
            if (_hash(audio) != fingerprint["audio_sha256"]
                    or (boundary and _hash(boundary) != fingerprint["boundary_sha256"])):
                raise AudioPreparationError(f"Slide {entry['slide_num']}: source changed during batch")
        except OSError as exc:
            raise AudioPreparationError(f"Slide {entry['slide_num']}: source became unreadable") from exc
    result["preparation"]["status"] = "ready"
    _publish_manifest(destination, result)
    return {"manifest": result, "audio_dir": output, "converted": converted}
