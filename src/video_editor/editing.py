"""MoviePy source lifetime and rendering for validated keep ranges."""

from collections.abc import Sequence
from contextlib import ExitStack, contextmanager
import math
import os
from pathlib import Path
import tempfile

from video_editor.segments import Segment, SelectionError, read_segments


class EditingError(RuntimeError):
    """An edit could not be validated or completed."""


@contextmanager
def _cleanup_after(cleanup, description: str):
    """Attempt cleanup without replacing an active failure or cancellation."""
    try:
        yield
    except BaseException as error:
        try:
            cleanup()
        except BaseException as cleanup_error:
            error.add_note(f"Cleanup failed for {description}: {cleanup_error}")
        raise
    else:
        try:
            cleanup()
        except Exception as error:
            raise EditingError(f"Cleanup failed for {description}: {error}") from error


@contextmanager
def open_source(path: str | Path):
    """Open a source for reading and keep it alive until the context exits."""
    VideoFileClip = _load_moviepy().VideoFileClip

    try:
        source = VideoFileClip(str(path))
    except FileNotFoundError as error:
        raise EditingError(
            f"Cannot open source video '{path}': {error}. Check the source path "
            "and restore bundled FFmpeg with: python -m pip install --force-reinstall "
            "-r requirements.txt"
        ) from error
    except (OSError, ValueError) as error:
        raise EditingError(f"Cannot open source video '{path}': {error}") from error
    with _cleanup_after(source.close, f"source video '{path}'"):
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


def render_segments(source, segments: Sequence[Segment], output: str | Path) -> None:
    """Render validated ranges to a caller-owned temporary MP4 path.

    The caller keeps the source context alive through rendering and owns output
    validation, temporary storage, and publication. Derived clips share its
    readers and are closed only after writing finishes (or fails).
    """
    concatenate_videoclips = _load_moviepy().concatenate_videoclips

    output = Path(output)
    with ExitStack() as resources:
        clips = []
        for segment in segments:
            clip = source.subclipped(segment.start, segment.end)
            resources.enter_context(_cleanup_after(clip.close, "selected clip"))
            clips.append(clip)
        merged = concatenate_videoclips(clips)
        resources.enter_context(_cleanup_after(merged.close, "merged video"))
        merged.write_videofile(str(output), temp_audiofile_path=str(output.parent))


def _load_moviepy():
    try:
        import moviepy
    except Exception as error:
        raise EditingError(
            "Video dependencies are unavailable or unusable. In the project .venv, "
            f"run: python -m pip install -r requirements.txt. Details: {error}"
        ) from error
    return moviepy


def _validate_paths(input_path: Path, segments_path: Path, output_path: Path):
    for label, path in (("Input", input_path), ("Output", output_path)):
        if path.suffix.lower() != ".mp4":
            raise EditingError(f"{label} video must have an MP4 extension: '{path}'")
    for label, path in (("Source video", input_path), ("Selection file", segments_path)):
        if not path.is_file():
            raise EditingError(f"{label} is missing or is not a file: '{path}'")
        try:
            with path.open("rb"):
                pass
        except OSError as error:
            raise EditingError(f"Cannot read {label.lower()} '{path}': {error}") from error

    source = input_path.resolve(strict=True)
    selections = segments_path.resolve(strict=True)
    output = output_path.resolve()
    exists = os.path.lexists(output_path)
    for original in (source, selections):
        if output == original or (exists and output_path.samefile(original)):
            raise EditingError(f"Output aliases an input file: '{output_path}'")
    if exists:
        raise EditingError(f"Output already exists; choose a new path: '{output_path}'")
    if not output.parent.is_dir():
        raise EditingError(f"Output parent directory must already exist: '{output.parent}'")
    return source, selections, output


def _publish(rendered: Path, output: Path) -> None:
    """Publish a closed file without replacing a destination created meanwhile."""
    if os.name == "nt":
        os.rename(rendered, output)  # Windows rename refuses an existing target.
    else:
        os.link(rendered, output)  # Preserve no-overwrite semantics on POSIX too.


def edit_video(input_path: str | Path, segments_path: str | Path, output_path: str | Path) -> Path:
    """Validate, render privately, close resources, and publish one new MP4."""
    operation = "validating input and output paths"
    try:
        source_path, selections_path, output = _validate_paths(
            Path(input_path), Path(segments_path), Path(output_path)
        )
        with ExitStack() as resources:
            operation = f"opening source video '{source_path}'"
            with open_source(source_path) as source:
                segments = read_segments(selections_path, source.duration)
                operation = f"creating temporary output in '{output.parent}'"
                temporary = tempfile.TemporaryDirectory(prefix=".video-editor-", dir=output.parent)
                resources.enter_context(_cleanup_after(
                    temporary.cleanup, f"temporary directory '{temporary.name}'"
                ))
                rendered = Path(temporary.name) / "edited.mp4"
                operation = "rendering selected video (check input media, free disk space, and permissions)"
                render_segments(source, segments, rendered)
                operation = "closing source video resources"
            operation = f"publishing output '{output}' (destination must not exist)"
            _publish(rendered, output)
    except (EditingError, SelectionError):
        raise
    except Exception as error:
        failure = EditingError(f"Failed while {operation}: {error}")
        for note in getattr(error, "__notes__", ()):
            failure.add_note(note)
        raise failure from error
    return output
