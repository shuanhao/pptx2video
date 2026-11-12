"""First-stage subtitle artifacts, with one localization pass and explicit provenance.

Each artifact is committed atomically and recorded separately: a failed corrected
version must not discard a valid initial version or overwrite an older candidate.
No PowerPoint or subtitle-burning operations are performed here.
"""
import copy
import hashlib
import json
import math
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.audio_position_locator import (locate_slide_start_and_end_times,
    DEFAULT_SEARCH_WINDOW_SECONDS, DEFAULT_ANCHOR_SECONDS)
from src.subtitle_alignment import format_srt
from src.subtitle_pipeline import build_caption_plan, render_caption_plan, SubtitleTimingError


def candidate_paths(output):
    path = Path(output)
    return {"preview": path.with_name(path.stem + "_preview.srt"),
            "initial": path.with_name(path.stem + "_initial.srt"),
            "captions": path,
            "report": path.with_name(path.stem + "_alignment_report.json")}


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _identity(path, hash_content=False):
    path = Path(path).resolve()
    info = {"path": str(path), "exists": path.is_file()}
    if info["exists"]:
        stat = path.stat()
        info.update(size_bytes=stat.st_size, mtime_ns=stat.st_mtime_ns)
        if hash_content:
            digest = hashlib.sha256()
            with path.open("rb") as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(block)
            info["sha256"] = digest.hexdigest()
    return info


def _video_duration(path):
    completed = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "json", str(path)], check=True, capture_output=True, timeout=60)
    duration = float(json.loads(completed.stdout)["format"]["duration"])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Invalid exported video duration")
    return duration


class SubtitleCandidateRun:
    def __init__(self, payload, output, video_path, audio_dir, default_slide_duration=5.0,
                 global_scale_correction=1.0, search_window_seconds=DEFAULT_SEARCH_WINDOW_SECONDS,
                 anchor_seconds=DEFAULT_ANCHOR_SECONDS):
        if not math.isfinite(global_scale_correction) or global_scale_correction <= 0:
            raise ValueError("Global scale correction must be positive and finite")
        self.paths = candidate_paths(output)
        if len({p.resolve() for p in self.paths.values()}) != len(self.paths):
            raise ValueError("Subtitle candidate paths must be distinct")
        self.payload = copy.deepcopy(payload)
        self.audio_dir = Path(audio_dir)
        self.video = Path(video_path)
        self.default_duration = default_slide_duration
        self.correction = global_scale_correction
        for value in (default_slide_duration, search_window_seconds, anchor_seconds):
            if not math.isfinite(value) or value <= 0:
                raise ValueError("Durations and search settings must be positive and finite")
        self.search_window = search_window_seconds
        self.anchor_seconds = anchor_seconds
        self.plan = None
        manifest = self.payload.get("audio") or {}
        self.sources = []
        for entry in manifest.get("slides", []):
            for field in ("audio_file", "word_boundaries_file"):
                if entry.get(field):
                    self.sources.append(_identity(self.audio_dir / entry[field], hash_content=True))
        protected = {self.video.resolve(), *(Path(item["path"]) for item in self.sources)}
        if payload.get("source_pptx"):
            protected.add(Path(payload["source_pptx"]).resolve())
        if any(path.resolve() in protected for path in self.paths.values()):
            raise ValueError("Subtitle output paths must not overwrite video, PPTX or source audio/timing files")
        self.report = {
            "schema_version": 1, "run_id": uuid.uuid4().hex,
            "created_at": datetime.now(timezone.utc).isoformat(), "status": "pending",
            "global_scale_correction": self.correction, "default_slide_duration": self.default_duration,
            "search_window_seconds": self.search_window, "anchor_seconds": self.anchor_seconds,
            "source_pptx": payload.get("source_pptx"), "audio_dir": str(self.audio_dir.resolve()),
            "manifest_sha256": hashlib.sha256(json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
            "slides_sha256": hashlib.sha256(json.dumps(payload.get("slides", []), sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
            "sources": self.sources, "video": _identity(self.video), "video_status": "pending",
            "warnings": [], "slides": {},
            "artifacts": {name: {"path": str(path.resolve()), "status": "pending",
                                  "existing_before_run": path.exists()}
                          for name, path in self.paths.items() if name != "report"},
        }

    def save_report(self):
        atomic_write(self.paths["report"], json.dumps(self.report, ensure_ascii=False, indent=2, allow_nan=False))

    def fail(self, reason):
        self.report.update(status="failed", error=str(reason))
        for artifact in self.report["artifacts"].values():
            if artifact["status"] == "pending":
                artifact.update(status="not_generated", error=str(reason))
        self.save_report()

    def _publish(self, name, text):
        atomic_write(self.paths[name], text)
        self.report["artifacts"][name].update(status="ready", run_id=self.report["run_id"],
            sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(), cue_count=text.count(" --> "))
        # Record every independent commit; a later failure must not mask it.
        self.save_report()

    def preview(self):
        self.save_report()  # supersede an old success report before starting this run
        try:
            self.plan, warnings = build_caption_plan(self.payload.get("slides", []),
                self.payload.get("audio") or {}, self.audio_dir, self.default_duration)
            self.report["warnings"].extend(warnings)
            cues, offset = [], 0.0
            for slide in self.plan:
                for cue in slide["captions"]:
                    cues.append({"text": cue["text"], "start_seconds": cue["start_seconds"] + offset,
                                 "end_seconds": cue["end_seconds"] + offset})
                offset += slide["duration_seconds"]
            self._publish("preview", format_srt(cues))
            self.report["status"] = "awaiting_export"
            self.save_report()
        except Exception as exc:
            self.fail(f"Preview failed: {exc}")
            raise

    def finish(self, video_path=None):
        if self.plan is None:
            self.preview()
        plan = self.plan
        if plan is None:
            raise RuntimeError("Preview did not initialize the caption plan")
        if video_path is not None:
            self.video = Path(video_path)
        try:
            self.report.update(video=_identity(self.video), video_status="exported")
            duration = _video_duration(self.video)
            for identity in self.sources:
                if _identity(identity["path"], hash_content=True) != identity:
                    raise ValueError(f"Audio/timing source changed since preview: {identity['path']}")
            records = {}
            # Always measure with k=1.0. Both versions share these raw results.
            bounds, warnings = locate_slide_start_and_end_times(self.video, self.payload.get("slides", []),
                self.payload.get("audio") or {}, self.audio_dir, default_slide_duration=self.default_duration,
                global_scale_correction=1.0, diagnostics=records,
                search_window_seconds=self.search_window, anchor_seconds=self.anchor_seconds)
            self.report["warnings"].extend(warnings)
            predicted = 0.0
            for slide in plan:
                number = slide["slide_num"]
                if number not in records:
                    # Original MP3 uses the legacy locator: do not imply it passed
                    # the prepared-audio confidence checks introduced in Stage 3.
                    start, end = bounds.get(number, (predicted, predicted + slide["duration_seconds"]))
                    scale = (end - start) / slide["duration_seconds"] if slide["duration_seconds"] > 0 else 1.0
                    status = "legacy_measured" if number in bounds else ("predicted" if slide["has_narration"] else "silent")
                    records[number] = {"slide_num": number, "status": status, "reason": "legacy_locator" if number in bounds else "no_measurement",
                        "start_seconds": start, "end_seconds": end, "scale": scale,
                        "predicted_start_seconds": predicted, "media_duration_seconds": slide["duration_seconds"],
                        "head": None, "tail": None, "global_scale_correction": 1.0}
                records[number]["video_duration_seconds"] = duration
                records[number]["caption_count"] = len(slide["captions"])
                records[number]["review_interval_seconds"] = [max(0, records[number]["start_seconds"]),
                    min(duration, records[number]["end_seconds"])]
                predicted += slide["duration_seconds"]
            self.report["slides"] = records
            self.report["summary"] = {status: [n for n, r in records.items() if r["status"] == status]
                for status in ("matched", "head_only", "predicted", "silent", "legacy_measured")}
            self.report["missing_caption_slides"] = [s["slide_num"] for s in plan
                                                     if s["has_narration"] and not s["captions"]]
            self.report["counts"] = {status: len(numbers) for status, numbers in self.report["summary"].items()}
            self.save_report()
        except Exception as exc:
            self.fail(f"Localization failed: {exc}")
            raise SubtitleTimingError(f"Localization failed; preview retained: {exc}") from exc

        errors = []
        for name, coefficient in (("initial", 1.0), ("captions", self.correction)):
            self.report["artifacts"][name]["global_scale_correction"] = coefficient
            try:
                mapping = copy.deepcopy(records)
                for record in mapping.values():
                    record["start_seconds"] *= coefficient
                    record["scale"] *= coefficient
                text, warnings = render_caption_plan(plan, mapping)
                self.report["artifacts"][name]["warnings"] = warnings
                self.report["artifacts"][name]["global_scale_correction"] = coefficient
                self.report["artifacts"][name]["mapping_rule"] = "raw start and local scale multiplied once by global_scale_correction"
                self._publish(name, text)
            except (SubtitleTimingError, OSError, ValueError) as exc:
                self.report["artifacts"][name].update(status="failed", error=str(exc))
                errors.append(f"{name}: {exc}")
                self.save_report()
        self.report["status"] = "partial_failure" if errors else "awaiting_manual_review"
        self.save_report()
        if errors:
            raise SubtitleTimingError("; ".join(errors))
        return self.paths["captions"], self.report["warnings"] + [
            f"Review {status} slides: {numbers}" for status, numbers in self.report["summary"].items()
            if numbers and status not in ("matched", "silent")]
