# Proposal

## Why

Segment parsing, path validation, and edit orchestration mix several responsibilities inside individual functions. Compose focused helpers so readers can understand each operation and its sequence while preserving all working behavior.

## What Changes

- Separate parsing one selection line from validating the sequence of selections.
- Compose path validation from named checks for extensions, readable inputs, and a protected destination.
- Encapsulate temporary render allocation and cleanup in a context manager while keeping resource lifetimes and publication order explicit.
- Separate CLI parser construction and exception-note printing from command execution and exit-status decisions.
- Preserve public function signatures, validation order, errors, cancellation behavior, resource cleanup, and default MoviePy calls.
- Keep the existing module boundaries and use ordinary functions and context managers; add no dependency or framework.

Out of scope: new editing features, format changes, media settings, performance work, dependency upgrades, and changes to setup or CLI usage.

Assumptions: composition means small functions and existing context managers rather than a new class hierarchy. Existing specifications and tests are the behavior baseline. No unresolved scope questions remain.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is a pure refactor: `segment-selection` and `video-editing` remain unchanged. The change declares `skip_specs: true` because no observable requirement changes.

## Impact

- Application modules: `src/video_editor/segments.py`, `editing.py`, and `cli.py`.
- Verification: existing parsing, media orchestration, workflow, CLI, and real-media integration tests under `tests/`; add focused behavioral coverage only where extraction exposes a gap.
- Preserve imports and callable interfaces used by callers and tests. No new external dependencies, packaging changes, or migration.
- README setup and usage should remain accurate without edits; update it only if implementation reveals an actual documentation mismatch within this scope.
