"""Read manual keep ranges without importing video-processing dependencies."""

from dataclasses import dataclass
import math
from pathlib import Path
import re


class SelectionError(ValueError):
    """A selection file cannot be read or contains invalid ranges."""


@dataclass(frozen=True)
class Segment:
    """A start-inclusive, end-exclusive range on the original timeline."""

    start: int
    end: int | float
    line_number: int


def _whole_seconds(token: str, line_number: int) -> int:
    if re.fullmatch(r"[0-9]+", token) is None:
        raise SelectionError(
            f"line {line_number}: numeric timestamps must use whole-number "
            "seconds written as ASCII digits [0-9]+"
        )
    try:
        return int(token)
    except ValueError as error:
        raise SelectionError(
            f"line {line_number}: timestamp has too many digits"
        ) from error


def _parse_segment(line: str, line_number: int, duration: float, is_final: bool) -> Segment:
    """Parse and validate one range against the source duration."""
    values = line.split(",")
    if len(values) != 2:
        raise SelectionError(
            f"line {line_number}: expected exactly two comma-separated values"
        )
    start, end = (value.strip() for value in values)
    if start.lower() == "end" or (
        end.lower() == "end" and not is_final
    ):
        raise SelectionError(
            f"line {line_number}: 'end' is allowed only as the second value "
            "of the final nonblank line"
        )
    start_seconds = _whole_seconds(start, line_number)
    end_seconds = duration if end.lower() == "end" else _whole_seconds(end, line_number)
    if not 0 <= start_seconds < end_seconds <= duration:
        raise SelectionError(
            f"line {line_number}: range must satisfy 0 <= start < end <= "
            f"duration ({duration} seconds)"
        )
    return Segment(start_seconds, end_seconds, line_number)


def parse_segments(text: str, duration: float) -> list[Segment]:
    """Validate all keep ranges against a finite, positive source duration.

    Numeric tokens are integer seconds. Only the last endpoint may be ``end``,
    which preserves the supplied duration exactly. No partial result is returned.
    """
    if (
        not isinstance(duration, (int, float))
        or isinstance(duration, bool)
        or duration <= 0
        or (isinstance(duration, float) and not math.isfinite(duration))
    ):
        raise SelectionError("source duration must be a finite positive number of seconds")
    lines = [
        (number, line) for number, line in
        enumerate(text.removeprefix("\ufeff").splitlines(), 1) if line.strip()
    ]
    if not lines:
        raise SelectionError("selection file must contain at least one range")
    final_line = lines[-1][0]
    segments = []
    for line_number, line in lines:
        segment = _parse_segment(line, line_number, duration, line_number == final_line)
        if segments and segment.start < segments[-1].end:
            raise SelectionError(
                f"line {line_number}: range overlaps or is out of order with "
                f"line {segments[-1].line_number}; start must be at or after "
                "the previous end"
            )
        segments.append(segment)
    return segments


def read_segments(path: str | Path, duration: float) -> list[Segment]:
    """Read UTF-8 selections, accepting an optional BOM and leaving input intact."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeError as error:
        raise SelectionError(f"Cannot read selection file '{path}': expected UTF-8 text") from error
    except OSError as error:
        raise SelectionError(f"Cannot read selection file '{path}': {error}") from error
    return parse_segments(text, duration)
