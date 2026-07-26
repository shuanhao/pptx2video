import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import ppt_automation
from src.pptx_parser import extract_notes
from src.subtitle_generator import write_srt
from src.tts import generate_audio_files


def build_payload(slides, pptx_path, audio_manifest=None, audio_output_dir=None):
    enriched_slides = []
    for slide in slides:
        notes = slide.get("notes")
        slide_num = int(slide.get("slide_num", 0))
        audio_file = None
        if audio_manifest is not None:
            for entry in audio_manifest.get("slides", []):
                if int(entry.get("slide_num", 0)) == slide_num:
                    audio_file = str((Path(audio_output_dir or "") / entry.get("audio_file", "")).as_posix()) if audio_output_dir else entry.get("audio_file")
                    break

        enriched_slides.append({
            "slide_num": slide_num,
            "title": slide.get("title"),
            "notes": notes,
            "subtitle_text": notes if notes else None,
            "has_notes": bool(notes and str(notes).strip()),
            "audio_file": audio_file,
        })

    payload = {
        "source_pptx": pptx_path,
        "slide_count": len(enriched_slides),
        "slides": enriched_slides,
        "audio": audio_manifest or {},
        "metadata": {
            "generated_by": "pptx2video",
            "audio_output_dir": audio_output_dir,
        },
    }
    return payload


def write_subtitle_output(payload, output_path, audio_dir=None):
    slides = payload.get("slides", [])
    output_path = Path(output_path)
    return write_srt(slides, output_path, audio_dir=audio_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse a PowerPoint file and optionally generate MP3 audio files from slide notes.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("pptx_path", help="Path to the input .pptx file")
    parser.add_argument(
        "--output",
        "-o",
        help="Path to write the parsed notes JSON output file",
        default="output/slides.json",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON result to stdout",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Number of spaces to use for JSON indentation",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed progress information while processing the file",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail the run if any slide has missing or unreadable content",
    )
    parser.add_argument(
        "--generate-audio",
        action="store_true",
        help="Generate MP3 audio files from slide notes using edge-tts",
    )
    parser.add_argument(
        "--audio-output-dir",
        default="output/audio",
        help="Directory where generated MP3 files should be written",
    )
    parser.add_argument(
        "--voice",
        default="Microsoft Server Speech Text to Speech Voice (zh-TW, YunJheNeural)",
        help="Edge-TTS voice name to use for audio generation (full style, e.g. Microsoft Server Speech Text to Speech Voice (zh-TW, YunJheNeural))",
    )
    parser.add_argument(
        "--rate",
        default="-10%",
        help="Speech rate for edge-tts (for example -10%% or +5%%)",
    )
    parser.add_argument(
        "--pitch",
        default="+0Hz",
        help="Pitch for edge-tts (use +0Hz to keep the pitch unchanged)",
    )
    parser.add_argument(
        "--subtitles-output",
        default="output/captions.srt",
        help="Path to write the generated subtitles .srt file",
    )
    parser.add_argument(
        "--insert-audio",
        action="store_true",
        help=(
            "Insert generated audio into the PPTX, shrunk and tucked into "
            "the top-right corner. Requires Windows with Microsoft "
            "PowerPoint and pywin32 installed. Slides without notes/audio "
            "are left untouched, and slide transition timing is not changed."
        ),
    )
    parser.add_argument(
        "--pptx-output",
        default=None,
        help=(
            "Path to save the PPTX with inserted audio (used with "
            "--insert-audio). Defaults to overwriting the input file."
        ),
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    pptx_path = args.pptx_path
    output_path = Path(args.output) if args.output else None

    if args.verbose:
        print(f"Parsing PowerPoint file: {pptx_path}")

    try:
        slides = extract_notes(pptx_path)
    except FileNotFoundError as exc:
        parser.error(str(exc))
    except ValueError as exc:
        parser.error(str(exc))
    except RuntimeError as exc:
        parser.error(str(exc))
    except Exception as exc:
        parser.error(f"Unexpected error: {exc}")

    if args.verbose:
        print(f"Loaded {len(slides)} slide(s)")

    if args.strict:
        for slide in slides:
            if slide.get("notes") is None:
                parser.error(f"Strict mode: slide {slide['slide_num']} has no notes")

    audio_manifest = None
    if args.generate_audio:
        def _print_audio_progress(current: int, total: int, slide_num: int) -> None:
            print(f"Generating audio {current}/{total} (slide {slide_num})...")

        audio_manifest = generate_audio_files(
            slides,
            args.audio_output_dir,
            voice=args.voice,
            manifest_path=Path(args.audio_output_dir) / "manifest.json",
            rate=args.rate,
            pitch=args.pitch,
            progress_callback=_print_audio_progress,
        )
        if args.verbose:
            print(json.dumps(audio_manifest, ensure_ascii=False, indent=args.indent))
        print(f"Generated {len(audio_manifest['slides'])} audio file(s) in {args.audio_output_dir}")

    payload = build_payload(
        slides,
        pptx_path,
        audio_manifest=audio_manifest,
        audio_output_dir=args.audio_output_dir,
    )

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=args.indent),
            encoding="utf-8",
        )
        print(f"Saved JSON to {output_path}")

    subtitle_output_path = Path(args.subtitles_output)
    if subtitle_output_path:
        subtitle_output_path = write_subtitle_output(
            payload,
            subtitle_output_path,
            audio_dir=args.audio_output_dir,
        )
        print(f"Saved subtitles to {subtitle_output_path}")

    if args.insert_audio:
        manifest_for_insert = audio_manifest
        if manifest_for_insert is None:
            manifest_path = Path(args.audio_output_dir) / "manifest.json"
            try:
                manifest_for_insert = ppt_automation.load_audio_manifest(manifest_path)
            except FileNotFoundError:
                parser.error(
                    "--insert-audio requires an audio manifest. Run with "
                    f"--generate-audio first, or ensure {manifest_path} exists."
                )

        pptx_output_path = args.pptx_output or pptx_path
        try:
            insert_result = ppt_automation.insert_audio(
                pptx_path,
                manifest_for_insert,
                args.audio_output_dir,
                output_path=pptx_output_path,
            )
        except (RuntimeError, FileNotFoundError) as exc:
            parser.error(str(exc))

        if args.verbose:
            print(json.dumps(insert_result, ensure_ascii=False, indent=args.indent))
        print(
            f"Inserted audio into {len(insert_result['inserted_slides'])} slide(s); "
            f"skipped {len(insert_result['skipped_slides'])}. "
            f"Saved to {insert_result['output_path']}"
        )

    if args.pretty or output_path is None:
        print(json.dumps(payload, ensure_ascii=False, indent=args.indent))


if __name__ == "__main__":
    main()
