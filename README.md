# Video Editor

## Overview

A Python project for editing recorded video files by removing unwanted sections and generating a new video file while preserving the original recording.

## Objectives

- Accept recorded MPG video files.
- Identify video segments to remove.
- Remove unwanted segments.
- Combine retained segments into an edited recording.
- Preserve the original video file.

## Requirements

- Python 3.14+
- pip

## Setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate the virtual environment.

Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Project Structure

- src/video_editor/ - Application source code.
- tests/ - Application tests.
- input/ - Original video recordings.
- output/ - Generated video recordings.
- requirements.txt - Python dependencies.
- AGENTS.md - AI coding assistant instructions.

## Development Status

Project initialized. Implementation has not started.