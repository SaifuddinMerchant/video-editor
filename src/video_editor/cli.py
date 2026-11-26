"""Command-line arguments and console reporting for one video edit."""

import argparse
from pathlib import Path
import sys

from video_editor import editing


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Keep selected sections of an MP4 recording in a separate MP4.",
        epilog=(
            "Selections: one start,end pair per line, using whole-number seconds "
            "on the original timeline; the final endpoint may be 'end'."
        ),
    )
    parser.add_argument("--input", required=True, type=Path, help="original MP4 recording")
    parser.add_argument("--segments", required=True, type=Path, help="UTF-8 keep-ranges file")
    parser.add_argument("--output", required=True, type=Path, help="new MP4 path (must not exist)")
    return parser


def _print_exception_notes(error: BaseException) -> None:
    for note in getattr(error, "__notes__", ()):
        print(note, file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        output = editing.edit_video(args.input, args.segments, args.output)
    except KeyboardInterrupt as error:
        print("Edit cancelled; incomplete video was not published.", file=sys.stderr)
        _print_exception_notes(error)
        return 130
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        _print_exception_notes(error)
        return 1
    print(f"Saved edited video: {output}")
    return 0
