"""MoviePy source lifetime and rendering for validated keep ranges."""

from collections.abc import Sequence
from contextlib import ExitStack, contextmanager
import math
from pathlib import Path

from video_editor.segments import Segment


class EditingError(RuntimeError):
    """A source video could not be opened or has no usable duration."""


@contextmanager
def open_source(path: str | Path):
    """Open a source for reading and keep it alive until the context exits."""
    from moviepy import VideoFileClip

    try:
        source = VideoFileClip(str(path))
    except (OSError, ValueError) as error:
        raise EditingError(f"Cannot open source video '{path}': {error}") from error
    try:
        duration = source.duration
        if (
            not isinstance(duration, (int, float))
            or isinstance(duration, bool)
            or duration <= 0
            or (isinstance(duration, float) and not math.isfinite(duration))
        ):
            raise EditingError(
                f"Source video '{path}' must have a finite positive duration"
            )
        yield source
    finally:
        source.close()


def render_segments(source, segments: Sequence[Segment], output: str | Path) -> None:
    """Render validated ranges to a caller-owned temporary MP4 path.

    The caller keeps the source context alive through rendering and owns output
    validation, temporary storage, and publication. Derived clips share its
    readers and are closed only after writing finishes (or fails).
    """
    from moviepy import concatenate_videoclips

    output = Path(output)
    with ExitStack() as resources:
        clips = []
        for segment in segments:
            clip = source.subclipped(segment.start, segment.end)
            resources.callback(clip.close)
            clips.append(clip)
        merged = concatenate_videoclips(clips)
        resources.callback(merged.close)
        merged.write_videofile(str(output), temp_audiofile_path=str(output.parent))
