# segment-selection Specification

## Purpose

Define a manual file of sections to keep from an original recording and reject invalid selections before any edited video is rendered.

## Requirements

### Requirement: Read timestamp pairs from a text file

The application SHALL accept a readable UTF-8 segment file, allowing an optional UTF-8 BOM, with exactly two comma-separated values on each nonblank line. It SHALL trim whitespace around values, ignore blank lines, and retain physical line numbers for errors. Numeric values SHALL represent nonnegative whole-number seconds from the beginning of the original recording.

#### Scenario: Parse whole-number seconds and surrounding spaces
- **GIVEN** a segment file containing ` 0 , 5 ` followed by `10,20`
- **WHEN** the file is validated against a recording longer than 20 seconds
- **THEN** the selection contains the ranges from 0 to 5 seconds and from 10 to 20 seconds on the original timeline

#### Scenario: Allow blank lines and a BOM
- **GIVEN** a UTF-8 segment file with a BOM, blank lines, and a valid range on physical line 3
- **WHEN** the file is read
- **THEN** the BOM and blank lines do not create segments
- **AND** the range retains physical line number 3

#### Scenario: Reject malformed or nonfinite values
- **GIVEN** a line with a missing value, extra comma-separated value, nonnumeric timestamp, `NaN`, or infinity
- **WHEN** the file is validated
- **THEN** validation fails with the physical line number and a description of the invalid pair

#### Scenario: Reject unavailable or empty selection input
- **GIVEN** the segment file is missing, unreadable, invalid UTF-8, or contains only blank lines
- **WHEN** the application validates the selection input
- **THEN** validation fails with an actionable file-level error

### Requirement: Accept whole-number numeric timestamps only

After surrounding whitespace is trimmed, each numeric timestamp SHALL consist only of ASCII digits matching `[0-9]+`. The application SHALL reject decimal notation, fractions, signs, exponents, and other numeric forms without rounding or truncation. The final `end` keyword SHALL remain the only nonnumeric endpoint exception.

#### Scenario: Accept a whole-number range
- **GIVEN** a recording at least 5 seconds long and a segment file containing `0,5`
- **WHEN** the segment file is validated
- **THEN** the range is accepted as 0 through 5 seconds

#### Scenario: Reject decimal timestamps in either position
- **GIVEN** a segment line containing `0,2.4`, `2.4,5`, `0,5.0`, or `0.0,5`
- **WHEN** the segment file is validated
- **THEN** validation fails with the physical line number and an explanation that numeric timestamps must use whole-number seconds
- **AND** processing stops before any output is encoded or created

#### Scenario: Reject alternate numeric notation
- **GIVEN** a segment line containing `0,5e0`, `0,+5`, or `0,5/2`
- **WHEN** the segment file is validated
- **THEN** validation fails rather than coercing the value to an integer

### Requirement: Interpret ranges as sections to keep

The application SHALL interpret each range as a start-inclusive, end-exclusive portion of the original recording to retain. Output timeline changes SHALL NOT change how later input timestamps are interpreted.

#### Scenario: Later timestamps refer to the original video
- **GIVEN** the ranges `5,10` and `20,25`
- **WHEN** the selection is used for editing
- **THEN** the selected source portions are the original recording's 5-to-10-second and 20-to-25-second portions
- **AND** footage outside those portions is excluded

### Requirement: Support the final end keyword

The application SHALL accept case-insensitive `end` only as the second value of the final nonblank segment line and resolve it to the recording's exact duration without whole-second rounding. It SHALL reject the keyword in either the start position or any earlier range. The whole-number restriction SHALL apply to user-written numeric timestamps, not to video duration or resolved `end` values.

#### Scenario: Retain through the recording's end
- **GIVEN** a 90-second recording and final range `60,EnD`
- **WHEN** the selection is validated
- **THEN** the final range resolves to 60 through 90 seconds

#### Scenario: Reject misplaced end keyword
- **GIVEN** a range `end,90` or a range `10,end` followed by another nonblank segment line
- **WHEN** the selection is validated
- **THEN** validation fails with the offending line number and the allowed use of `end`

#### Scenario: Retain a fractional final second through end
- **GIVEN** a recording lasting 90.4 seconds and final range `90,end`
- **WHEN** the selection is validated
- **THEN** the endpoint resolves to exactly 90.4 seconds and the final partial second is retained
- **AND** writing the endpoint as `90,90.4` would fail the whole-number input rule

### Requirement: Validate every range against source duration

For source duration D, the application SHALL require every resolved range to satisfy `0 <= start < end <= D`. It SHALL reject invalid ranges rather than clamp timestamps or discard them. A recording with an unavailable, nonfinite, or nonpositive duration SHALL fail validation.

#### Scenario: Accept a numeric endpoint equal to duration
- **GIVEN** a 90-second recording and the range `0,90`
- **WHEN** the selection is validated
- **THEN** the range is valid and selects the complete recording

#### Scenario: Reject invalid bounds
- **GIVEN** a 90-second recording and a range with a negative start, equal endpoints, reversed endpoints, a start at or beyond 90 seconds, or an endpoint beyond 90 seconds
- **WHEN** the selection is validated
- **THEN** validation fails with the physical line number and the violated bound

#### Scenario: Cannot establish duration
- **GIVEN** the recording's duration cannot be established as a finite positive number
- **WHEN** the selection is validated against the recording
- **THEN** validation fails before any edit is rendered

### Requirement: Require chronological non-overlapping ranges

The application SHALL require each range after the first to start at or after the previous range's end. Adjacent ranges SHALL be valid. It SHALL reject overlaps and out-of-order ranges without sorting, merging, or otherwise repairing the file.

#### Scenario: Accept adjacent ranges
- **GIVEN** the ranges `0,5` and `5,10`
- **WHEN** the selection is validated against a recording at least 10 seconds long
- **THEN** the ranges are valid and their shared boundary does not repeat source footage

#### Scenario: Reject overlapping or out-of-order ranges
- **GIVEN** the ranges `10,20` followed by either `19,25` or `0,5`
- **WHEN** the selection is validated
- **THEN** validation fails and identifies the conflicting physical lines

### Requirement: Complete validation before rendering

The application SHALL validate the source recording and the entire segment file before starting output encoding. Any validation failure SHALL stop the edit with a nonzero exit status, an actionable error, and no new output video. Reporting the first detected error SHALL be sufficient; collecting every error is not required.

#### Scenario: A later invalid range prevents all rendering
- **GIVEN** valid early ranges and an invalid range later in the file
- **WHEN** the edit is invoked
- **THEN** no range is rendered, no new output video is created, and the command fails with the invalid line identified

#### Scenario: Invalid source prevents editing
- **GIVEN** a missing, unreadable, unsupported, or unopenable source recording
- **WHEN** the edit is invoked
- **THEN** validation fails before rendering and the command reports the source problem
