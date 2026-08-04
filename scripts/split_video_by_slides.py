"""Split an already-exported MP4 into N segment files, with every cut landing
exactly at a slide-change boundary - not at an arbitrary duration mark.

Why this exists: PowerPoint's own "Create a Video" export
(``ppt_automation.export_video()`` / ``Presentation.CreateVideo()``) has no
slide-range parameter - it always exports the *entire* open presentation in
one pass, and re-running it per-segment would mean paying its (potentially
multi-hour, for a big deck) export cost 3x over. For a long deck where the
single-file export is simply too long to comfortably watch/upload/share in
one sitting, cutting the *already-exported* MP4 after the fact is much
cheaper - and this module's own ``locate_slide_start_and_end_times()`` (the
same true-start measurement ``regenerate_srt_from_export.py`` uses to
realign subtitles) already gives an accurate, per-slide "where does slide N
really start in this video" timestamp, which is exactly what's needed to
choose cut points that land precisely on a slide change instead of mid-
narration.

Usage (auto-pick 2 cut points that divide the deck into 3 roughly
equal-duration segments):
    python scripts/split_video_by_slides.py \\
        --video output/deck.mp4 \\
        --manifest output/audio/manifest.json \\
        --slides-json output/slides.json \\
        --output-dir output/segments \\
        --num-segments 3

Usage (cut after specific slide numbers instead - e.g. after slide 7 and
slide 14, producing 3 segments: 1-7, 8-14, 15-end):
    python scripts/split_video_by_slides.py \\
        --video output/deck.mp4 \\
        --manifest output/audio/manifest.json \\
        --slides-json output/slides.json \\
        --output-dir output/segments \\
        --split-after-slides 7 14

Add --subtitles output/captions.srt to either form above to also get a
matching segment_N.srt per video segment, retimed to start at 00:00:00 (see
"Subtitles" below).

Exactly one of --slides-json / --pptx must be given, same as
regenerate_srt_from_export.py - both are just different sources for the same
ordered slide list (notes text + slide numbers). Exactly one of
--num-segments / --split-after-slides must be given.

How the cut points are chosen: each candidate cut point is a slide
*boundary* - the measured real start time of the slide right after the cut,
i.e. cutting right before that slide's narration begins so nothing is
truncated mid-sentence. With --num-segments N, this script measures every
slide's true start time (the same call regenerate_srt_from_export.py makes),
then picks N-1 slide boundaries whose cumulative durations are closest to
equal thirds (or Nths) of the deck's total length - not just "the boundary
closest to the halfway/two-thirds mark in isolation", to avoid one segment
ending up much longer than the others when slide lengths are uneven.

The actual cut is done with ffmpeg's stream copy mode (-c copy, no
re-encoding) for speed - this means each cut snaps to the nearest keyframe
at or before the requested timestamp rather than being frame-exact. Since
PowerPoint's own video export normally keyframes far more often than once
per slide, this is not expected to be noticeable, but if you see a
segment's first frame briefly show the tail end of the previous slide, that
keyframe granularity is why - re-run with --reencode to force frame-exact
cuts (much slower - it re-encodes every segment instead of just copying).

Subtitles: pass --subtitles pointing at the deck's full, already-true-start-
aligned captions.srt (the one Step 10 writes when --subtitles-output and
--export-video are given together, or the output of
regenerate_srt_from_export.py) and this script will also slice it into one
.srt per video segment (segment_1.srt, segment_2.srt, ...), retimed to each
start at 00:00:00 - not just copy the same whole-deck .srt next to every
segment. This deliberately re-uses the *exact same* cut boundary timestamps
just chosen for the video (not a fresh, independent measurement), so a
segment's video and its .srt are guaranteed to agree on where time zero is,
even if the subtitle cross-correlation math would give a very slightly
different answer if re-run in isolation. Cues that fall entirely outside a
segment's time window are dropped from that segment's .srt; a cue would only
ever straddle a cut boundary if the true-start measurement that produced the
cut point and the one that produced the cue's own timing disagreed by a
sliver - in that rare case this script clips the cue to the segment's
window rather than dropping or duplicating it whole.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.audio_position_locator import (
    DEFAULT_ANCHOR_SECONDS,
    DEFAULT_GLOBAL_SCALE_CORRECTION,
    DEFAULT_SEARCH_WINDOW_SECONDS,
    locate_slide_start_and_end_times,
)
from src.pptx_parser import extract_notes
from src.subtitle_alignment import format_srt

_SRT_TIMESTAMP_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})"
)


def _parse_srt_timestamp(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def _parse_srt(text: str) -> list:
    """Parse standard SRT text into a list of {"start_seconds",
    "end_seconds", "text"} dicts, in file order.

    Deliberately hand-rolled rather than pulling in a dependency: the
    format this project ever writes (via
    ``src.subtitle_alignment.format_srt``) is plain - sequential index,
    one timestamp line, one-or-more text lines, blank line separator - and
    a small dedicated parser is easier to reason about here than adding a
    new external dependency just to read files this same project produced.
    Blocks that don't match the expected shape (e.g. stray blank lines) are
    skipped rather than raising, so minor formatting quirks in a hand-
    edited .srt don't hard-fail the split.
    """
    entries = []
    blocks = re.split(r"\r?\n\r?\n", text.strip())
    for block in blocks:
        lines = [line for line in block.splitlines() if line.strip() != ""]
        if len(lines) < 2:
            continue
        # lines[0] is normally the sequential index - not relied on, since
        # this script renumbers on output anyway. The timestamp line is
        # found by pattern match instead of a fixed position, so this
        # tolerates an index line being absent.
        timestamp_line_idx = None
        for i, line in enumerate(lines):
            if _SRT_TIMESTAMP_RE.search(line):
                timestamp_line_idx = i
                break
        if timestamp_line_idx is None:
            continue
        match = _SRT_TIMESTAMP_RE.search(lines[timestamp_line_idx])
        start = _parse_srt_timestamp(*match.groups()[0:4])
        end = _parse_srt_timestamp(*match.groups()[4:8])
        text_lines = lines[timestamp_line_idx + 1:]
        entries.append({"start_seconds": start, "end_seconds": end, "text": "\n".join(text_lines)})
    return entries


def _slice_srt_for_segment(entries: list, window_start: float, window_end: float) -> list:
    """Return the subset of entries overlapping [window_start, window_end),
    clipped to that window and retimed so window_start becomes 0.0."""
    sliced = []
    for entry in entries:
        clipped_start = max(entry["start_seconds"], window_start)
        clipped_end = min(entry["end_seconds"], window_end)
        if clipped_end <= clipped_start:
            continue  # entirely outside this segment's window
        sliced.append({
            "start_seconds": clipped_start - window_start,
            "end_seconds": clipped_end - window_start,
            "text": entry["text"],
        })
    return sliced


def _probe_duration_seconds(video_path: Path) -> float:
    """Total duration of video_path, via ffprobe - used as the deck's end
    boundary (the last segment runs from the last cut point to this)."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(video_path),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def _choose_equal_duration_cuts(slide_starts: dict, total_duration: float, num_segments: int) -> list:
    """Pick (num_segments - 1) slide-start boundaries out of slide_starts
    (slide_num -> real start time) that divide [0, total_duration] as evenly
    as possible into num_segments pieces.

    Greedy, one target at a time (not a joint optimization over all cuts at
    once): for each of the num_segments - 1 internal targets (at 1/N, 2/N,
    ... of total_duration), pick whichever *unused* slide boundary is
    closest to that target. This is deliberately simple - joint optimization
    (e.g. dynamic programming over all subsets) would do marginally better
    on pathological slide-length distributions, but for the common case
    (slide lengths not wildly different from each other) greedy-per-target
    already keeps every segment close to equal, and is far easier to reason
    about when a user is looking at the printed segment boundaries and
    asking "why did it cut there".
    """
    candidates = sorted(slide_starts.items(), key=lambda kv: kv[1])  # [(slide_num, start_time), ...]
    used_slide_nums = set()
    cuts = []  # list of (slide_num, start_time), in increasing time order
    for i in range(1, num_segments):
        target = total_duration * i / num_segments
        best = None
        best_dist = None
        for slide_num, start_time in candidates:
            if slide_num in used_slide_nums:
                continue
            # A cut at slide 1's own start (time 0) isn't a real cut - skip it.
            if start_time <= 0:
                continue
            dist = abs(start_time - target)
            if best_dist is None or dist < best_dist:
                best, best_dist = (slide_num, start_time), dist
        if best is None:
            continue
        used_slide_nums.add(best[0])
        cuts.append(best)
    cuts.sort(key=lambda sn_t: sn_t[1])
    return cuts


def _cuts_from_slide_numbers(slide_starts: dict, split_after_slides: list) -> list:
    cuts = []
    for slide_num in split_after_slides:
        # Cut right before the *next* slide after split_after_slides[i] -
        # i.e. this segment includes slide_num in full, and the next
        # segment starts at the following slide's real start time.
        next_slide_num = slide_num + 1
        if next_slide_num not in slide_starts:
            raise SystemExit(
                f"--split-after-slides {slide_num}: no measured start time for slide {next_slide_num} "
                f"(either it doesn't exist in this deck, or it has no narration and so wasn't measured "
                f"- can only split after slides that are directly followed by a narrated slide)."
            )
        cuts.append((next_slide_num, slide_starts[next_slide_num]))
    cuts.sort(key=lambda sn_t: sn_t[1])
    return cuts


def _run_ffmpeg_segment(video_path: Path, start: float, end, output_path: Path, reencode: bool) -> None:
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning"]
    cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", str(video_path)]
    if end is not None:
        cmd += ["-t", f"{max(0.0, end - start):.3f}"]
    if reencode:
        cmd += ["-c:v", "libx264", "-c:a", "aac"]
    else:
        cmd += ["-c", "copy"]
    cmd += [str(output_path)]
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--video", required=True, type=Path, help="The exported MP4 (ppt_automation.export_video()'s output)")
    parser.add_argument("--manifest", required=True, type=Path, help="Path to manifest.json (from --generate-audio)")
    parser.add_argument(
        "--audio-dir", type=Path, default=None,
        help="Directory the manifest's audio_file names are relative to. Defaults to manifest.json's own directory, or manifest['output_dir'] if present.",
    )
    slide_source = parser.add_mutually_exclusive_group(required=True)
    slide_source.add_argument("--slides-json", type=Path, help="Path to a JSON file shaped like main.py's --output.")
    slide_source.add_argument("--pptx", type=Path, help="Path to the original .pptx, re-parsed if --slides-json isn't available.")

    split_choice = parser.add_mutually_exclusive_group(required=True)
    split_choice.add_argument(
        "--num-segments", type=int,
        help="Automatically choose (this - 1) slide-boundary cut points that divide the video into roughly equal-duration segments.",
    )
    split_choice.add_argument(
        "--split-after-slides", type=int, nargs="+",
        help="Explicit slide numbers to cut after (e.g. --split-after-slides 7 14 makes 3 segments: 1-7, 8-14, 15-end). Order doesn't matter, they're sorted by time.",
    )

    parser.add_argument("--output-dir", required=True, type=Path, help="Directory to write segment_1.mp4, segment_2.mp4, ... into")
    parser.add_argument("--output-prefix", default="segment", help="Segment filename prefix (default: 'segment', giving segment_1.mp4 etc.)")
    parser.add_argument(
        "--default-slide-duration", type=float, default=5.0,
        help="Must match whatever was used for --export-video's --video-default-duration originally.",
    )
    parser.add_argument("--search-window-seconds", type=float, default=DEFAULT_SEARCH_WINDOW_SECONDS)
    parser.add_argument("--anchor-seconds", type=float, default=DEFAULT_ANCHOR_SECONDS)
    parser.add_argument(
        "--global-scale-correction", type=float, default=DEFAULT_GLOBAL_SCALE_CORRECTION,
        help=(
            "Same meaning as in regenerate_srt_from_export.py / verify_srt_accuracy.py - a deck/"
            "environment-specific multiplier correcting a small systematic bias in this module's own "
            "measurement. Get it from scripts/calibrate_scale.py or scripts/verify_srt_accuracy.py's "
            "auto-suggestion. Getting this right matters more here than for subtitles: an uncorrected "
            "cut point can land a fraction of a second into the next slide's narration instead of "
            "exactly at the boundary."
        ),
    )
    parser.add_argument(
        "--reencode", action="store_true",
        help="Re-encode each segment (libx264/aac) for frame-exact cuts, instead of the default fast stream copy (-c copy), which snaps to the nearest keyframe at or before the cut point.",
    )
    parser.add_argument(
        "--subtitles", type=Path, default=None,
        help=(
            "Path to the deck's full, true-start-aligned captions.srt (from Step 10's "
            "--subtitles-output + --export-video, or scripts/regenerate_srt_from_export.py). If given, "
            "also slices it into one segment_N.srt per video segment, retimed to start at 00:00:00, "
            "reusing the exact same cut boundaries chosen for the video - so each segment's .srt is "
            "guaranteed to line up with that segment's .mp4."
        ),
    )
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    audio_dir = args.audio_dir or Path(manifest.get("output_dir") or args.manifest.parent)

    if args.slides_json:
        payload = json.loads(args.slides_json.read_text(encoding="utf-8"))
        slides = payload.get("slides", payload) if isinstance(payload, dict) else payload
    else:
        slides = extract_notes(str(args.pptx))

    print(f"Measuring true per-slide start times in {args.video} ...")
    if args.global_scale_correction != 1.0:
        print(f"Applying global scale correction: x{args.global_scale_correction}")
    bounds, locate_warnings = locate_slide_start_and_end_times(
        args.video, slides, manifest, audio_dir,
        default_slide_duration=args.default_slide_duration,
        search_window_seconds=args.search_window_seconds,
        anchor_seconds=args.anchor_seconds,
        global_scale_correction=args.global_scale_correction,
    )
    for w in locate_warnings:
        print(f"WARNING (locate): {w}")

    slide_starts = {slide_num: start for slide_num, (start, _end) in bounds.items()}
    if not slide_starts:
        raise SystemExit("No slide start times could be measured - can't choose cut points. See WARNING lines above.")

    total_duration = _probe_duration_seconds(args.video)

    if args.num_segments is not None:
        if args.num_segments < 2:
            raise SystemExit("--num-segments must be at least 2 (use the whole video as-is if you don't want to split it).")
        cuts = _choose_equal_duration_cuts(slide_starts, total_duration, args.num_segments)
        if len(cuts) < args.num_segments - 1:
            print(
                f"WARNING: only found {len(cuts)} usable cut point(s) for --num-segments {args.num_segments} "
                f"(need {args.num_segments - 1}) - producing {len(cuts) + 1} segment(s) instead."
            )
    else:
        cuts = _cuts_from_slide_numbers(slide_starts, args.split_after_slides)

    boundaries = [0.0] + [t for _slide_num, t in cuts] + [total_duration]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nSplitting into {len(boundaries) - 1} segment(s):")
    for i in range(len(boundaries) - 1):
        start, end = boundaries[i], boundaries[i + 1]
        seg_slide_num = cuts[i][0] if i < len(cuts) else None
        boundary_note = f" (cuts right before slide {seg_slide_num})" if i < len(cuts) else ""
        print(f"  segment {i + 1}: {start:.2f}s - {end:.2f}s ({end - start:.2f}s){boundary_note}")

    subtitle_entries = None
    if args.subtitles is not None:
        subtitle_entries = _parse_srt(args.subtitles.read_text(encoding="utf-8"))
        if not subtitle_entries:
            print(f"\nWARNING: {args.subtitles} parsed to 0 cues - no segment .srt files will be written.")

    for i in range(len(boundaries) - 1):
        start, end = boundaries[i], boundaries[i + 1]
        output_path = args.output_dir / f"{args.output_prefix}_{i + 1}.mp4"
        print(f"\nWriting {output_path} ...")
        _run_ffmpeg_segment(args.video, start, end, output_path, args.reencode)
        print(f"Wrote {output_path}")

        if subtitle_entries:
            sliced = _slice_srt_for_segment(subtitle_entries, start, end)
            srt_output_path = args.output_dir / f"{args.output_prefix}_{i + 1}.srt"
            srt_output_path.write_text(format_srt(sliced), encoding="utf-8")
            print(f"Wrote {srt_output_path} ({len(sliced)} cue(s))")

    print(f"\nDone: {len(boundaries) - 1} segment(s) in {args.output_dir}")


if __name__ == "__main__":
    main()
