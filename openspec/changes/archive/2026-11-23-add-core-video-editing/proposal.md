# Proposal

## Why

Recorded screen videos need a simple way to retain selected portions and produce a separate edited recording. The project currently has no implementation; this change establishes the first usable editing workflow without modifying original recordings.

## What Changes

- Accept one MP4 recording from Windows Snipping Tool and a text file describing the portions to keep.
- Read one comma-separated pair of original-recording timestamps per line, requiring nonnegative whole-number seconds written as digits only. For example, `0,5` is valid; `0,2.4` and `0,5.0` are invalid. Allow case-insensitive `end` as the final range's endpoint, resolving to the exact video duration without rounding.
- Validate the recording and the complete segment file before rendering. Reject malformed, negative, empty, reversed, overlapping, out-of-order, and out-of-bounds ranges; stop on any validation failure.
- Join retained sections chronologically into a separate MP4 through a Python CLI using MoviePy and its pip-supplied FFmpeg dependency.
- Calculate each retained segment's length as `end - start`, clip those ranges, and merge them using MoviePy's default MP4 writing settings. Compare final duration with the sum of the selected lengths, allowing a fixed 0.5-second difference.
- Provide actionable console errors and basic progress, protect the original and existing files, and avoid publishing incomplete output.
- Document setup, usage, limitations, and verification on Python 3.14+ in a local virtual environment.
- Replace the earlier MPG input requirement with MP4. README and OpenSpec context still contain the superseded MPG wording; reconcile them during implementation.

Out of scope: automatic segment detection, a GUI or preview player, batch editing, rearranging or repeating footage, effects or transitions, other input/output formats, frame-rate handling or frame-level accuracy guarantees, custom encoding settings, perceptual quality guarantees, measured audio synchronization, persistent log files, packaging as a standalone executable, and performance guarantees.

## Capabilities

### New Capabilities

- `segment-selection`: Parse and validate a manual keep-ranges file against the original recording's timeline before editing starts.
- `video-editing`: Clip validated ranges, merge them into a protected, separate MP4, and produce the expected retained duration.

### Modified Capabilities

None. There are no existing capability specifications.

## Impact

- Application changes will live under `src/video_editor/`, with automated tests under `tests/` and documentation showing recordings under `input/` and results under `output/`.
- One basic media integration test will use the user-provided `input/sample.mp4` and `input/sample-selections.txt`, render a separate output, and compare its duration with the sum of the selected range lengths using a fixed 0.5-second absolute tolerance. Do not generate substitute source recordings or create/overwrite the supplied sample files. Extensive validation of MoviePy/FFmpeg is outside the test scope.
- MoviePy is the user-selected processing dependency. Record a Python 3.14-compatible release in `requirements.txt`; its transitive dependency stack supplies FFmpeg through `imageio-ffmpeg` Windows wheels. A separate system FFmpeg or ffprobe installation must not be required for the normal workflow.
- Use standard-library argument parsing, file handling, error reporting, and test support where practical. No service, database, plugin framework, or processing-engine abstraction is needed.
- Proposed minor defaults for review: UTF-8 text with an optional BOM, ignored blank lines, trimmed surrounding whitespace, adjacent ranges allowed, start-inclusive/end-exclusive ranges, refusal to overwrite existing output, and support for recordings with or without audio. These complete the workflow without adding user-facing feature modes.
- Remaining setup verification is to select a working dependency release on Python 3.14. This revision replaces the earlier frame-accuracy, frame-rate preservation, custom encoding, and quality/synchronization requirements with default library behavior and a basic duration check. Audio follows the selected clips through MoviePy without custom processing.
