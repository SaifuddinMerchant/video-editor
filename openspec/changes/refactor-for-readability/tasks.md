# Tasks

## 1. Establish the behavior baseline

- [x] 1.1 Confirm `.venv` uses Python 3.14+ and run the existing suite with `PYTHONPATH` set to `src`: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`. Record results and any pre-existing failures before editing; do not generate or replace missing integration samples.

## 2. Compose selection parsing

- [x] 2.1 Extract single-line parsing in `segments.py` as described in design decision 2, retaining duration, nonblank-line, and predecessor checks in `parse_segments`. Verify with `test_segments.py`, including ASCII timestamps, BOM/physical lines, exact fractional `end`, bounds, adjacency, and unchanged errors.
- [x] 2.2 Add a focused parser regression for an earlier overlapping range followed by a later malformed range if existing coverage does not establish error precedence; verify the earlier overlap is reported and no partial result is returned. Keep helper docstrings accurate and avoid tests tied to private helper calls.

## 3. Compose path validation

- [x] 3.1 Extract named extension, readable-input, and destination-protection checks in `editing.py`; preserve `_validate_paths` signature and resolved tuple, original-path diagnostics, check order, and `_publish`. Verify existing `test_workflow.py` path cases, input preservation, hard-link aliases, and destination-appears-during-render behavior.
- [x] 3.2 Add behavioral coverage only for uncovered validation-precedence cases affected by extraction, such as an invalid output extension alongside a missing source. Verify unchanged first-error messages and that media is never opened for rejected paths; document helper responsibilities locally.

## 4. Compose temporary render ownership

- [x] 4.1 Extract a temporary-render context manager using `_cleanup_after` and enter it through the existing outer `ExitStack` after all selections validate. Verify `test_workflow.py` establishes no allocation on invalid selections, source closure before publication, cleanup on render/publication failures and cancellation, and complete output retained on post-publication cleanup failure.
- [x] 4.2 Preserve `_cleanup_after`, `open_source`, `render_segments`, lazy dependency loading, operation messages, exception causes/notes, and default MoviePy arguments. Verify `test_editing.py` and workflow cleanup-failure tests, and update local ownership docstrings to describe the retained lifetime order.

## 5. Compose CLI setup and reporting

- [x] 5.1 Extract parser construction and exception-note printing in `cli.py`, keeping execution and status selection in `main`. Verify `test_cli.py` covers help without MoviePy, required arguments, paths with spaces, success, ordinary errors, cleanup notes, and cancellation with unchanged output and statuses.
- [x] 5.2 Review README setup, usage, and troubleshooting against the refactored CLI. Leave correct instructions intact; correct any actual discrepancy within scope and verify documented `--help` usage against the command.

## 6. Verify the complete refactor

- [x] 6.1 Run the full existing test suite in `.venv`, including the user-supplied real-media sample test, and record results. Verify retained duration remains within the existing 0.5-second absolute tolerance and originals remain unchanged; report missing samples as a verification blocker.
- [x] 6.2 Review the final diff against both unchanged capability specs and the design's order/lifetime decisions. Verify no new dependencies, public signature changes, altered media options, changed error precedence/messages, or setup/usage changes, and run `openspec validate refactor-for-readability --strict` successfully.
