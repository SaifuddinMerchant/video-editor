# Spec Delta

## Purpose

Create a separate edited MP4 from validated sections of a screen recording through a small command-line workflow while protecting the original video.

## ADDED Requirements

### Requirement: Accept one edit through a command-line interface

The application SHALL provide a CLI accepting an explicit source video path, segment-file path, and output video path for one edit. It SHALL provide usage help, return zero only on successful completion, and return a nonzero status for invalid arguments, validation failures, or processing failures.

#### Scenario: Complete a valid invocation
- **GIVEN** a readable MP4 source, a valid segment file, and an available output destination
- **WHEN** the user invokes the CLI with all three paths
- **THEN** the application produces the edited MP4 and returns zero

#### Scenario: Explain missing arguments
- **GIVEN** an invocation omitting a required path
- **WHEN** the command is evaluated
- **THEN** it prints usage information, returns nonzero, and does not render output

#### Scenario: Show help without editing
- **GIVEN** an invocation requesting help
- **WHEN** the command is evaluated
- **THEN** it describes the required paths and segment-file format without opening or modifying any recording

### Requirement: Support MP4 screen recordings and MP4 output

The application SHALL accept readable MP4 video recordings from Windows Snipping Tool and produce an MP4 output. Source and output filename extensions SHALL be checked case-insensitively. A source that cannot be opened as a video or lacks a usable video stream SHALL fail validation. Other container formats are outside this capability's supported scope.

#### Scenario: Accept an uppercase MP4 extension
- **GIVEN** a valid Snipping Tool recording named `recording.MP4` and an output path named `edited.mp4`
- **WHEN** the invocation is validated
- **THEN** the source and output extensions are accepted

#### Scenario: Reject unsupported or invalid media
- **GIVEN** a non-MP4 source or output extension, or an MP4 source that cannot be opened as video
- **WHEN** the invocation is validated
- **THEN** the command fails before rendering with a description of the unsupported path or media problem

### Requirement: Join validated retained sections

After complete validation, the application SHALL join the selected source portions in their validated chronological order into one output video. It SHALL omit unselected footage and add no transitions, titles, or intentional gaps. A selection containing one range SHALL also be supported.

#### Scenario: Keep disjoint sections
- **GIVEN** a 60-second source and ranges `5,10` and `20,25`
- **WHEN** the edit completes
- **THEN** the output presents those two source portions consecutively in that order
- **AND** it omits the intervening source portion

#### Scenario: Keep the full recording
- **GIVEN** a valid source and a segment file containing only `0,end`
- **WHEN** the edit completes
- **THEN** the output contains the complete source presentation in a separate MP4

### Requirement: Match the expected retained duration

The expected output duration SHALL equal the sum of `end - start` for all validated ranges, with a final `end` resolved to the source duration. The completed video's duration SHALL differ from that sum by no more than 0.5 seconds. No frame-level boundary guarantee SHALL be required.

#### Scenario: Sum disjoint segment lengths
- **GIVEN** a 60-second source and ranges `5,10` and `20,25`
- **WHEN** the completed video's duration is compared with the expected duration
- **THEN** the expected duration is 10 seconds
- **AND** the completed duration differs from 10 seconds by no more than 0.5 seconds

#### Scenario: Include the final fractional duration
- **GIVEN** a source lasting 90.4 seconds and the range `60,end`
- **WHEN** the completed video's duration is compared with the expected duration
- **THEN** the expected duration is 30.4 seconds
- **AND** the completed duration differs from 30.4 seconds by no more than 0.5 seconds

### Requirement: Write output using default media settings

The application SHALL use the processing library's default MP4 writing settings. It SHALL NOT configure frame rates, codecs, bitrates, encoding presets, compression quality, or custom encoder options. Re-encoding SHALL be allowed; frame-rate preservation and perceptual quality guarantees are outside this change.

#### Scenario: Edit without encoding configuration
- **GIVEN** a supported source, valid keep ranges, and an available MP4 destination
- **WHEN** the edit completes
- **THEN** the output is written using default media settings without requiring encoding or frame-rate configuration

### Requirement: Carry selected audio through the edit

The application SHALL include the audio associated with selected portions when the source has audio, using the processing library's default handling. A source without audio SHALL produce a video-only MP4. Custom synchronization correction, measured drift limits, and audio quality guarantees are outside this change.

#### Scenario: Include audio for retained sections
- **GIVEN** a source with audio and valid keep ranges
- **WHEN** the edit completes
- **THEN** the output includes the audio belonging to those retained sections

#### Scenario: Edit a recording without audio
- **GIVEN** a valid source video with no audio stream and valid keep ranges
- **WHEN** editing completes
- **THEN** the output is a playable video-only MP4

### Requirement: Protect input and existing destination files

The application SHALL leave the source recording and segment file unchanged on success and failure. It SHALL reject an output destination that aliases an input, already exists, or has no usable parent directory before rendering. It SHALL NOT overwrite an existing destination, including one created by another process before publication.

#### Scenario: Refuse an input alias
- **GIVEN** the output path refers to the source recording or the segment file, including a filesystem alias
- **WHEN** paths are validated
- **THEN** the edit fails before rendering and all input bytes remain unchanged

#### Scenario: Preserve an existing output
- **GIVEN** a file already exists at the requested destination
- **WHEN** the edit is invoked
- **THEN** the command fails before rendering and preserves the existing file

#### Scenario: Preserve original bytes on success
- **GIVEN** recorded checksums of both input files and an available output destination
- **WHEN** the edit completes
- **THEN** both input checksums are unchanged and a separate output file exists

#### Scenario: Destination appears during rendering
- **GIVEN** the destination was absent during validation but another process creates it before output publication
- **WHEN** the edited video is ready to publish
- **THEN** publication fails without overwriting the new destination or either input file

### Requirement: Report progress and actionable errors

The application SHALL provide basic console progress while rendering and identify the output path on success. Validation and processing failures SHALL produce an actionable message on standard error and a nonzero status without a raw traceback by default. Segment errors SHALL identify their physical line numbers. Persistent log files are not required.

#### Scenario: Explain an invalid selection
- **GIVEN** an invalid range on physical line 4
- **WHEN** validation fails
- **THEN** standard error identifies line 4 and the validation problem
- **AND** the command returns nonzero before encoding

#### Scenario: Explain a rendering failure
- **GIVEN** valid inputs followed by an encoder, permission, or disk-space failure during rendering
- **WHEN** the failure is handled
- **THEN** standard error identifies the failed operation with available actionable details
- **AND** the command returns nonzero without reporting success

### Requirement: Publish only completed output

The application SHALL make the requested output available as a successful result only after rendering and closing the complete edited video. On a handled rendering failure or user cancellation, it SHALL close media resources and remove temporary files it created where possible. Cleanup failures SHALL be reported, and an incomplete render SHALL NOT be published at the requested output path.

#### Scenario: Rendering fails after writing partial data
- **GIVEN** an available destination and a rendering failure after some output data is written
- **WHEN** the command exits
- **THEN** the requested output path does not contain a partial render
- **AND** input files remain unchanged and application-owned temporary files are removed where possible

#### Scenario: User cancels rendering
- **GIVEN** an edit currently rendering
- **WHEN** the user interrupts the command
- **THEN** the command exits nonzero, closes media resources, and does not publish the incomplete video

### Requirement: Run with dependencies installed through pip

The normal Windows workflow SHALL run on Python 3.14+ in a local virtual environment using dependencies declared in `requirements.txt` and installed through pip. It SHALL NOT require the user to install a separate system FFmpeg or ffprobe executable. Missing or unusable processing dependencies SHALL produce an actionable setup error.

#### Scenario: Run without system video tools
- **GIVEN** a clean supported Windows virtual environment with the declared dependencies installed and no system FFmpeg or ffprobe on PATH
- **WHEN** a valid edit is run
- **THEN** it completes using the video-processing executable supplied by the pip dependency stack

#### Scenario: Processing dependencies are unavailable
- **GIVEN** the required Python dependency or supplied video-processing executable is missing or unusable
- **WHEN** an edit is invoked
- **THEN** it fails with a setup message directing the user to the documented dependency installation steps
