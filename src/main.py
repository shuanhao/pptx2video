import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pptx_parser import extract_notes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse a PowerPoint file and export slide metadata as JSON.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("pptx_path", help="Path to the input .pptx file")
    parser.add_argument(
        "--output",
        "-o",
        help="Path to write the JSON output file",
        default=None,
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

    payload = {
        "source_pptx": pptx_path,
        "slide_count": len(slides),
        "slides": slides,
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=args.indent),
            encoding="utf-8",
        )
        print(f"Saved JSON to {output_path}")

    if args.pretty or output_path is None:
        print(json.dumps(payload, ensure_ascii=False, indent=args.indent))


if __name__ == "__main__":
    main()
