"""Burn (hardsub) an already-generated .srt into a video as a fixed-width
black bar with white, borderless text - as opposed to a "soft" subtitle
track that a player can toggle on/off, or libass's own auto-sized
per-line box (``BorderStyle=3``), which grows/shrinks with each line's
actual text length instead of staying a constant width.

Why a fixed-width bar instead of libass's own box: the project owner
wanted the black background to always be the same size regardless of how
long a given line of narration is, positioned to sit in a specific spot
relative to other on-screen elements (e.g. a slide template's own footer
row) - a per-line auto-sized box can't give that. The default bar
geometry and text styling below (``DEFAULT_BAR_WIDTH_PX = 650``,
``DEFAULT_FONT_SIZE = 15``, ...) are values the project owner tuned by
eye against a real exported slide and confirmed worked - see
``docs/SPLIT_VIDEO.md`` for the reasoning (in particular: empirically,
each full-width CJK glyph rendered at ``FontSize=15`` with
``Noto Sans CJK TC`` measured out to roughly 31px wide on a 1280x720
frame - notably NOT simply "1 char = FontSize px" - so re-tune these by
eye again if the export resolution, font, or subtitle line-width limit
(``src.subtitle_segmenter.DEFAULT_MAX_DISPLAY_WIDTH``) changes).

This always re-encodes the video track (burning pixels into every frame
can't be done with a stream copy); the audio track is always copied
untouched, since nothing here touches audio.
"""

import subprocess
from pathlib import Path
from typing import Optional

# Tuned by the project owner against a real 1280x720 exported slide with
# Noto Sans CJK TC - see this module's docstring. Not a universal constant;
# re-tune if resolution/font/line-width-limit changes.
DEFAULT_BAR_WIDTH_PX = 650
DEFAULT_BAR_HEIGHT_PX = 38
# The black bar's *top* edge sits this many pixels above the very bottom of
# the frame (i.e. drawbox's y = ih - DEFAULT_BAR_BOTTOM_OFFSET_PX). Because
# the bar is DEFAULT_BAR_HEIGHT_PX tall, its bottom edge ends up
# (DEFAULT_BAR_BOTTOM_OFFSET_PX - DEFAULT_BAR_HEIGHT_PX) px above the very
# bottom edge of the frame.
DEFAULT_BAR_BOTTOM_OFFSET_PX = 40
DEFAULT_FONT_NAME = "Noto Sans CJK TC"
DEFAULT_FONT_SIZE = 15
# Distance (px) from the very bottom of the frame to the bottom of the
# subtitle text itself (libass's own MarginV, for Alignment=2/bottom-
# center) - kept small since the text is meant to sit inside the black bar
# above, not floating independently.
DEFAULT_MARGIN_V = 1
DEFAULT_CRF = 20


def _escape_path_for_ffmpeg_filter(path: Path) -> str:
    """Escape a filesystem path for safe use as the filename argument of
    ffmpeg's ``subtitles=`` filter.

    Why this is needed: within an ffmpeg filtergraph string, ``:`` and
    ``'`` are syntactically significant (``:`` separates a filter's
    key=value options, ``'`` is used for quoting a value that itself
    contains special characters). An absolute Windows path like
    ``C:\\Users\\Shawn\\output\\captions.srt`` contains a drive-letter
    colon that, left unescaped, ffmpeg would parse as the start of a new
    filter option and fail with a confusing "No such filter" or similar
    error - not fail *because* the file doesn't exist, but because the
    filtergraph string itself doesn't parse as intended. Backslashes are
    also normalized to forward slashes, which ffmpeg accepts on Windows
    and which avoids a second layer of escaping backslashes themselves.
    """
    normalized = str(path).replace("\\", "/")
    # Order matters: escape backslash-introducing colons before quotes,
    # then quotes - there are no backslashes left to conflict with by this
    # point since they were already normalized away above.
    escaped = normalized.replace(":", r"\:").replace("'", r"\'")
    return escaped


def build_burn_filter(
    srt_path: Path,
    *,
    bar_width_px: int = DEFAULT_BAR_WIDTH_PX,
    bar_height_px: int = DEFAULT_BAR_HEIGHT_PX,
    bar_bottom_offset_px: int = DEFAULT_BAR_BOTTOM_OFFSET_PX,
    font_name: str = DEFAULT_FONT_NAME,
    font_size: int = DEFAULT_FONT_SIZE,
    margin_v: int = DEFAULT_MARGIN_V,
) -> str:
    """Build the ``-vf`` filtergraph string: a fixed-size black bar
    (``drawbox``) with the given .srt's text burned on top of it in plain
    white, borderless text (``subtitles`` + ``force_style``).

    Split out from ``burn_subtitles_into_video()`` so the filter string
    itself can be unit-tested (escaping, parameter interpolation) without
    needing ffmpeg installed.
    """
    escaped_srt = _escape_path_for_ffmpeg_filter(srt_path)
    drawbox = (
        f"drawbox=x=(iw-{bar_width_px})/2:y=ih-{bar_bottom_offset_px}:"
        f"w={bar_width_px}:h={bar_height_px}:color=black@1:t=fill"
    )
    force_style = (
        f"FontName={font_name},FontSize={font_size},"
        f"PrimaryColour=&HFFFFFF&,BorderStyle=1,Outline=0,Shadow=0,"
        f"Alignment=2,MarginV={margin_v}"
    )
    subtitles = f"subtitles='{escaped_srt}':force_style='{force_style}'"
    return f"{drawbox},{subtitles}"


def burn_subtitles_into_video(
    video_path: Path,
    srt_path: Path,
    output_path: Path,
    *,
    bar_width_px: int = DEFAULT_BAR_WIDTH_PX,
    bar_height_px: int = DEFAULT_BAR_HEIGHT_PX,
    bar_bottom_offset_px: int = DEFAULT_BAR_BOTTOM_OFFSET_PX,
    font_name: str = DEFAULT_FONT_NAME,
    font_size: int = DEFAULT_FONT_SIZE,
    margin_v: int = DEFAULT_MARGIN_V,
    crf: int = DEFAULT_CRF,
    extra_ffmpeg_args: Optional[list] = None,
) -> None:
    """Burn ``srt_path``'s cues into ``video_path`` as a fixed-width black
    bar with white text, writing the result to ``output_path``.

    Always re-encodes video (``libx264``, ``-crf``); always copies audio
    untouched (``-c:a copy``) since burning subtitles never touches audio.
    Raises ``subprocess.CalledProcessError`` if ffmpeg exits non-zero.
    """
    vf = build_burn_filter(
        srt_path,
        bar_width_px=bar_width_px,
        bar_height_px=bar_height_px,
        bar_bottom_offset_px=bar_bottom_offset_px,
        font_name=font_name,
        font_size=font_size,
        margin_v=margin_v,
    )
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(video_path),
        "-vf", vf,
        "-c:v", "libx264", "-crf", str(crf),
        "-c:a", "copy",
    ]
    if extra_ffmpeg_args:
        cmd += extra_ffmpeg_args
    cmd += [str(output_path)]
    subprocess.run(cmd, check=True)
