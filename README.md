# Video Editor

## Overview

A Python project for editing recorded video files by removing unwanted sections and generating a new video file while preserving the original recording.

## Objectives

- Accept MP4 screen recordings from Windows Snipping Tool.
- Read manually selected sections to keep from a text file.
- Remove unwanted segments.
- Combine retained segments into a separate MP4 using MoviePy's defaults.
- Preserve the original video file.

## Requirements

- Windows with Python 3.14+ and pip.
- MoviePy 2.2.1 and its transitive dependencies, installed through pip.

The Windows pip dependency stack supplies FFmpeg through `imageio-ffmpeg`;
no separate system FFmpeg or ffprobe installation is required.

## Setup

Run these PowerShell commands from the repository root. Confirm that `python`
is Python 3.14 or newer before creating the local environment:

```powershell
python --version
python -m venv .venv
```

If `python` resolves to an unavailable Windows Store alias, use the full path
to your installed Python 3.14+ executable for those two commands. An existing
`.venv` can be reused after checking `.\.venv\Scripts\python.exe --version`.

Activate the virtual environment, install dependencies, and set the source
directory for imports in the current shell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m pip check
python -c "import video_editor; from importlib.metadata import version; from moviepy import VideoFileClip, concatenate_videoclips; print('MoviePy', version('moviepy'))"
```

If PowerShell blocks activation, use the environment's interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -c "import video_editor; from importlib.metadata import version; from moviepy import VideoFileClip, concatenate_videoclips; print('MoviePy', version('moviepy'))"
```

Set `PYTHONPATH` again in each new shell before running application modules or
tests. The project uses source-layout imports without an installation or
packaging step.

### Setup verification

Verified on Windows with Python 3.14.5 and MoviePy 2.2.1. The installed dependency
set was decorator 5.3.2, imageio 2.38.2, imageio-ffmpeg 0.8.1, NumPy 2.5.5,
Pillow 11.3.0, proglog 0.1.12, python-dotenv 1.2.4, tqdm 4.70.1, and colorama
0.4.6. Only the directly selected MoviePy release is pinned in `requirements.txt`;
pip resolves its transitive dependencies.

An ad hoc duration integration test read the supplied `input/sample.mp4` and
`input/sample-selections.txt` as-is, clipped and merged their selected ranges
with MoviePy defaults, and reopened a separate temporary MP4. Expected duration
was 16.12 seconds and actual duration was 16.12 seconds (absolute tolerance:
0.5 seconds). The test ran with an empty `PATH` using pip's bundled FFmpeg;
temporary output was removed afterward. No source recording was generated or
modified. MoviePy emitted NumPy deprecation and subprocess resource warnings
during this passing check.

This verifies the dependency setup; the application and its permanent integration
test remain to be implemented.

## Project Structure

- src/video_editor/ - Application source code.
- tests/ - Application tests.
- input/ - Original video recordings.
- output/ - Generated video recordings.
- requirements.txt - Python dependencies.
- AGENTS.md - AI coding assistant instructions.

## Development Status

Runtime and dependency setup established. The approved workflow is a Python CLI
with explicit input, selection-file, and output paths, manual keep ranges, and
MoviePy's default MP4 writing and audio handling. Editing and CLI implementation
are pending. Automatic editing, other formats, custom encoding settings, and
quality, synchronization, frame-accuracy, or performance guarantees are outside
the current change.
