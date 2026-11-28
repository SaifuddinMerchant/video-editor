# Video Editor

Keep selected sections of a Windows Snipping Tool MP4 recording and save them
as a new MP4. The original recording stays intact.

## Setup

You need Windows, Python 3.14 or newer, and pip. From the repository root, run
these commands in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

[requirements.txt](requirements.txt) pins MoviePy 2.2.1. Pip installs its
dependencies, including `imageio-ffmpeg`, which supplies FFmpeg on Windows.
You can run the editor with the FFmpeg bundled in the virtual environment.

## Edit a recording

Put the recording and its selection file in `input/`. From the repository root,
run:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -m video_editor --input input/sample.mp4 --segments input/sample-selections.txt --output output/edited-sample.mp4
```

Choose a new filename in an existing output directory. Quote paths that contain
spaces. The editor prints the saved file's path when it finishes. Run
`python -m video_editor --help` with the virtual environment's interpreter to see
all arguments.

### Write a selection file

In a UTF-8 text file, write one `start,end` pair per line for each section you
want to keep. This example keeps the first five seconds, seconds 10 through 20,
and everything from second 90 to the end.

```text
0,5
10,20
90,end
```

Use whole seconds written with digits 0–9. Each range includes its start and
excludes its endpoint. List ranges in chronological order, within the
recording's duration. Ranges can touch at an endpoint but cannot overlap. Blank
lines and spaces around the values are ignored.

Use `end` as the endpoint of the last range to keep the full ending, including
any fractional second. The keyword is case-insensitive.

## Clipping and merging

The editor validates the selection file before rendering. MoviePy cuts the
selected sections, joins them in order, and saves the result using its default
MP4 settings. Audio from the selected sections carries over when the source
contains audio. Rendering uses temporary disk space beside the destination,
and the editor saves the final MP4 only after rendering finishes.

## Run the tests

To run the unit tests and the real-video integration test, provide
`input/sample.mp4` and a matching `input/sample-selections.txt`. The integration
test uses both files as supplied and fails with the missing paths if either is
absent.

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The integration test runs the CLI, checks that it succeeds, and opens the
finished MP4 to measure its duration. It calculates the expected duration
independently by adding up the selected ranges. The measured duration must be
within **0.5 seconds** of that total. The test creates its edited video in a
temporary folder under `output/` and cleans it up afterward.

## Project structure

- `src/video_editor/` — Application source code.
- `tests/` — Unit and integration tests.
- `input/` — Original recordings and selection files.
- `output/` — Edited recordings.
- `requirements.txt` — Python dependencies.
- `AGENTS.md` — Instructions for coding agents.
