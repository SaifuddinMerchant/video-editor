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
```

If PowerShell blocks activation, use the environment's interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONPATH = (Resolve-Path .\src).Path
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

Final acceptance: **63 tests passed, with no skips**, after removing the
privilege-dependent symbolic-link test. The single CLI integration test read the supplied sample pair
as-is and passed: **16.12 seconds expected, 16.12 seconds actual**, with a fixed
**0.5-second absolute tolerance**. Temporary output was removed afterward.

MoviePy uses FFmpeg bundled inside `.venv`; neither system FFmpeg nor ffprobe is
on `PATH`. Originals were preserved. Review against both capability specs
confirmed segment validation, clipping/merging, and protected publication with
library defaults, without custom media settings or additional installation
requirements. MoviePy emitted NumPy deprecation and subprocess resource warnings
during the passing test run.

The CLI validates all selections before rendering, keeps temporary video/audio
beside the destination, and publishes only a completed, closed result without
overwriting existing files.

## Usage

From the repository root, with your recording and selections under `input/`:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -m video_editor --input input/sample.mp4 --segments input/sample-selections.txt --output output/edited-sample.mp4
```

The output parent directory must already exist, and the output filename must be
new. Quote paths containing spaces. Use `--help` for argument help. MoviePy shows
rendering progress; success prints the output path and returns exit status 0.
Errors go to standard error and return nonzero. Originals are never overwritten.

### Troubleshooting

| Problem | Action |
| --- | --- |
| Missing or unusable dependencies | Activate `.venv` and run `python -m pip install -r requirements.txt`; use `--force-reinstall` if bundled FFmpeg needs restoring. |
| Invalid selections | Correct the reported line; use whole-number seconds and chronological, non-overlapping ranges within the recording. |
| Existing output or input alias | Choose a different output filename. Files created during rendering are also protected. |
| Rendering or permission failure | Check source readability, destination permissions, and free disk space. Partial renders are not published. |
| Cancellation | Press Ctrl+C; the command attempts cleanup and returns status 130. |
| Cleanup failure | Close programs holding files open and remove only the reported temporary directory. A completed output may already exist. |

## Manual selection files

Use a UTF-8 text file with one `start,end` range per line to select sections to
**keep** on the original recording's timeline:

```text
0,5
10,20
90,end
```

Use whole-number seconds written as ASCII digits (`[0-9]+`): `0,5` is valid;
`0,2.4` and `0,5.0` are invalid. Ranges include the start and exclude the end,
must stay within the recording, and must be chronological without overlap.
Adjacent ranges are allowed. Blank lines and surrounding whitespace are ignored.

The case-insensitive `end` keyword is allowed only as the final range's endpoint
and preserves the exact video duration, including fractional seconds.

## Clipping and merging

Each selected segment has length `end - start`. MoviePy clips these ranges from
the original recording and merges them in order, using default MP4 writing
settings. Selected audio follows the clips automatically; recordings without
audio produce video-only output.

The integration test checks that final duration differs from the sum of selected
lengths by no more than **0.5 seconds**. Rendering uses memory and needs extra disk
space for temporary video and audio; large recordings may take time. Frame-rate,
frame-accuracy, encoding-quality, and measured audio-sync guarantees are outside
scope.

Provide your own `input/sample.mp4` and matching `input/sample-selections.txt`
for the single media integration test; both files are read as-is. Missing samples
fail with `Required integration sample files missing` and the expected paths;
the test never generates or replaces them. Run the unit and integration tests:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Project Structure

- src/video_editor/ - Application source code.
- tests/ - Application tests.
- input/ - Original video recordings.
- output/ - Generated video recordings.
- requirements.txt - Python dependencies.
- AGENTS.md - AI coding assistant instructions.
