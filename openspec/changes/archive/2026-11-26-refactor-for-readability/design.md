# Design

## Context

See `proposal.md` for motivation. The application has three substantive modules: pure selection parsing, MoviePy/filesystem orchestration, and CLI reporting. Existing tests cover line-level validation, source and clip lifetimes, protected publication, cleanup failures, cancellation, and real-media duration. Both durable capability specs remain the acceptance contract.

This design spans those modules and includes resource-lifetime decisions, so a design artifact is warranted even though observable behavior does not change.

## Goals / Non-Goals

**Goals:** Make orchestrating functions read as ordered operations, give extracted helpers one coherent responsibility, and preserve current interfaces and failure semantics.

**Non-Goals:** A new object model, generic validation framework, shared utility package, altered exception policy, changed MoviePy configuration, or a guarantee of byte-identical encoded output.

## Decisions

### 1. Compose functions inside the existing modules

Use private helpers with explicit arguments and descriptive names. Retain `Segment`, `SelectionError`, `EditingError`, `parse_segments`, `read_segments`, `open_source`, `render_segments`, `edit_video`, and `main` at their existing import locations with unchanged callable interfaces. Prefer a few coherent extractions over a helper for every conditional. Add useful concrete return annotations where straightforward without importing MoviePy eagerly.

Alternative: new service classes or modules for each responsibility. Rejected because this application has no stateful service boundary that would justify the extra navigation and indirection. Keep the small duration checks local rather than adding a shared module solely to remove that duplication.

### 2. Separate individual range parsing from sequence validation

Extract `_parse_segment(line, line_number, duration, is_final)` returning a `Segment`. It owns comma count, whitespace trimming, placement of `end`, numeric conversion, and bounds checks, in that order. `parse_segments` retains duration validation, BOM/blank-line handling, empty-file rejection, and the loop that checks each parsed range against its predecessor before appending.

Keep physical line numbers and original ordering. Preserve ASCII-only numeric syntax, the too-many-digits error, exact fractional resolution of `end`, adjacent ranges, current error text, and first-error precedence. A two-pass approach that parses every line before checking overlap is rejected because it could report a later syntax failure before an earlier overlap. Do not replace the regex with `isdigit()`, sort ranges, merge adjacency, or round endpoints.

### 3. Name path checks without changing their sequence

Compose `_validate_paths` from helpers for MP4 extensions, readable files, and output protection. Keep both extension checks before input readability checks, strict input resolution before destination checks, input-alias rejection before existing-output rejection, and the parent-directory check last. Return the same resolved path tuple with a concrete return annotation.

Keep the original output path available for `lexists`, `samefile`, and diagnostics while using the resolved destination for publication. Replacing these checks with `exists()` or only string comparison is rejected because it weakens alias and dangling-link handling. Preserve `_publish` and its Windows rename/POSIX hard-link distinction, including protection against a destination appearing during rendering.

### 4. Encapsulate temporary output ownership while retaining the outer ExitStack

Add a private context manager such as `_temporary_render_path(parent)` that allocates the existing `.video-editor-` temporary directory, wraps its cleanup in `_cleanup_after`, and yields its `edited.mp4` path. Enter it through the outer `ExitStack` only after `read_segments` has validated every range. Keep the source context nested inside that stack, as today.

```text
validate paths
  --> enter outer resource stack
  --> open source
  --> validate all selections
  --> enter temporary render context through outer stack
  --> render; close merged video and selected clips
  --> close source
  --> publish closed render
  --> exit outer stack; clean temporary directory
```

The temporary directory must outlive the source context and publication. A simple nested temporary-directory `with` inside the source block would delete the render too soon; allocating it before reading selections would change failure behavior. Keep the current operation descriptions and exception wrapping in `edit_video` rather than introducing mutable phase objects or a generic execution framework.

Retain `_cleanup_after` semantics: cleanup on cancellation, attempts to close all registered resources, notes on the original failure when cleanup also fails, and an `EditingError` when cleanup alone fails. Source-close failure prevents publication; temporary cleanup failure after publication reports failure while leaving the completed output intact. Do not replace this policy with default context-manager cleanup or plain ExitStack callbacks.

### 5. Keep CLI control flow explicit

Extract `_build_parser()` and `_print_exception_notes(error)` within `cli.py`. `main` still parses before its edit try-block, calls `editing.edit_video`, chooses exit statuses 0/1/130, and prints the existing success, failure, and cancellation messages. Preserve argparse status 2 and help behavior. Keep MoviePy lazy loading so help and selection parsing do not require installed video dependencies.

Alternative: unify cancellation and ordinary exceptions in a generic reporter. Rejected because their messages and exit statuses differ and are clearer as separate branches.

## Risks / Trade-offs

- Helper extraction can change which error is reported first -> preserve evaluation order and add behavioral regression coverage only for uncovered competing-error cases.
- Cleanup nesting can change file lifetime or suppress a primary error -> preserve the outer stack and `_cleanup_after`, and run existing failure/cancellation tests.
- More helpers can increase navigation -> keep related helpers near their orchestrator and avoid generic wrappers or trivial forwarding functions.
- Test mocks refer to existing orchestration entry points -> preserve those seams; tests should assert behavior rather than the new helper arrangement.
- Rendering remains subject to MoviePy defaults and existing platform behavior -> preserve all media call arguments, audio handling, and the fixed 0.5-second integration tolerance. No new quality, synchronization, or frame-accuracy guarantee is introduced.
- Large recordings retain the current memory/disk profile -> do not materialize media beyond current clips or add another copy of the rendered video. Temporary media stays beside the destination.

## Migration Plan

Run the existing suite in the Python 3.14+ `.venv` as a baseline, then refactor parsing, path checks, temporary ownership, and CLI in that order with focused checks between changes. Finish with the full suite, including the supplied sample integration test, and review the diff against both capability specs. Missing sample media must be reported as a verification blocker, never replaced or generated. Keep setup and CLI usage unchanged; adjust README only for an actual discrepancy.

No data or dependency migration is needed. Rollback consists of reverting the refactor; original recordings and selection files remain untouched. Existing tests establish behavioral confidence, not a new performance or encoding-quality guarantee.
