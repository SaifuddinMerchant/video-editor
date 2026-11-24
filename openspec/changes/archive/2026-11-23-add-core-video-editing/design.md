# Design

## Context

See `proposal.md` for motivation and the two capability deltas for the behavior contract. The repository contains an empty `src/video_editor/__init__.py`, an empty `requirements.txt`, setup documentation, and no tests. There is no application behavior or dependency integration to preserve. The user will supply `input/sample.mp4` and its matching `input/sample-selections.txt` for media integration testing; do not generate source recordings.

The user's exploration decisions supersede the MPG wording still in `README.md` and `openspec/config.yaml`. MP4 input/output and MoviePy are selected. This planning change does not edit those project files; the implementation tasks include reconciling their stale context.

The implementation focuses on validated segment lengths, clipping, merging, and safe file publication. MoviePy handles media details with its defaults.

## Goals / Non-Goals

**Goals:**
- Keep argument handling, pure range validation, and MoviePy resource management separable and easy to test.
- Establish a single boundary between complete preflight validation and output rendering.
- Make input protection and completion-only publication properties of the whole workflow, including handled failures.
- Use pip-provided Windows video tooling and verify the actual Python 3.14 environment.

**Non-Goals:**
- No frame-rate inspection or configuration, frame-level accuracy calculations, custom encoding settings, or quality/synchronization correction.
- No extensible engine interface, processing job framework, database, intermediate clip archive, or retained editing project format.
- No full-file corruption scan before every edit, decoded-frame cache, parallel chunk renderer, or performance service-level objective.
- No separate ffprobe installation, automatic dependency installation at runtime, or persistent application logs.

## Decisions

### 1. Use a small module-based CLI

Add a thin `__main__.py` entry point, a `cli.py` coordinator, a `segments.py` parser/validator, and an `editing.py` MoviePy workflow under `src/video_editor/`. Use `argparse`, `pathlib`, `tempfile`, and ordinary functions. A small immutable segment record needs only start, resolved end, and physical line number. Avoid an application framework or engine hierarchy.

The documented invocation will be `python -m video_editor --input input/recording.mp4 --segments keep.txt --output output/edited.mp4`. For this source-layout project, document setting `PYTHONPATH` to the repository's `src` directory before invoking the module or tests; no packaging framework is needed for the MVP. Paths are explicit, resolved relative to the working directory. Document `input/` and `output/` as storage conventions without moving source files or imposing a new directory confinement feature. The destination parent must already exist.

Load MoviePy only when editing or media inspection is requested so usage help remains available without processing dependencies. Convert argument, validation, import/setup, I/O, and processing failures into concise standard-error messages. Success is exit status 0, usage errors follow argparse's nonzero behavior, and other failures use a nonzero status; a distinct public error-code taxonomy is unnecessary. Use MoviePy's existing rendering progress display and a final output-path message instead of a custom progress or logging dependency.

Alternative: an interactive prompt or GUI would introduce an additional interaction model beyond the selected CLI workflow.

### 2. Parse all selections and validate before rendering

Read the text with `utf-8-sig`, preserve physical line numbers, ignore blank lines, and strip surrounding whitespace. Require two comma-separated values; comments, header rows, and hour/minute timestamp notation are not added. Require each numeric token to match ASCII `[0-9]+` and parse it as integer seconds. Reject decimals, including `5.0`, fractions, signs, exponents, and nonfinite values before conversion; never parse a float and round or truncate it. Thus `0,5` is valid and `0,2.4` is invalid. Resolve `end` only at the final nonblank line's second value to the exact video duration, which can have a fractional part. Keep media duration and resolved endpoints precise rather than converting them to whole seconds. Require at least one range.

Open the source through MoviePy in read-only use and obtain a finite positive duration. Use that duration to resolve `end` and validate every range and its ordering. Adjacent ranges are valid under start-inclusive/end-exclusive semantics. Calculate each segment's length as `end - start`. Do not clamp, sort, silently drop, or repair user selections. Reporting the first detected error is enough; no aggregation mode is needed. Rely on MoviePy to open supported media instead of adding dimensions or frame-rate inspection.

Check MP4 extensions, input readability, destination parent, input/output aliases, and existing output before allocating render files. An unwritable directory or filesystem change can still fail later; handle that as a processing failure. No output render or output temporary file starts until all preflight checks pass.

Alternative: rendering one line as it is read would waste work and violate the confirmed all-or-nothing validation behavior.

### 3. Clip, merge, and write with MoviePy defaults

Use MoviePy 2.x APIs: open a `VideoFileClip`, derive subclips from the original timeline with `subclipped(start, end)`, concatenate them in order, and write one MP4 with `write_videofile`. Use the default concatenation and MP4 writing behavior; do not pass frame-rate, codec, bitrate, preset, compression-quality, or custom FFmpeg settings. Temporary-file locations can be specified for cleanup without changing media settings. All clips derive from the same source, so no layout composition or resizing is needed. Keep the source reader alive until rendering finishes.

Carry audio with the selected clips through MoviePy's normal behavior, including video-only sources. Do not implement audio correction or analyze synchronization, frame timing, dimensions, or visual quality. Use source timestamps in seconds directly; no conversion into frames is needed.

Alternative: custom encoder settings or direct FFmpeg commands would introduce tuning and additional validation beyond this simple workflow. Use the selected library's defaults instead.

MoviePy is the only directly selected editing library. Install a released MoviePy 2.x in the Python 3.14 venv and record the tested release in `requirements.txt`. Use the basic sample edit as the dependency smoke check without requiring system FFmpeg/ffprobe. Do not add a separate encoder-validation suite, downgrade Python, or introduce an alternative processing engine.

### 4. Calculate and verify retained duration

The expected output duration is `sum(end - start)` over the validated ranges. Resolve a final `end` to the exact source duration, including any fractional second. Do not round lengths or convert timestamps into frame indices.

Cover range calculations and their mapping to clipping calls with focused unit tests: disjoint and adjacent ranges, a single range, complete-source selection, and a fractional tail through `end`. Decimal user input remains invalid under the segment-selection spec.

Use a fixed absolute tolerance of 0.5 seconds when comparing completed output duration with the expected sum. This small allowance keeps the check independent of frame-rate calculations and accommodates normal media/container rounding. It replaces the earlier frame-based tolerance and boundary guarantees. Check final duration in the integration test; do not add a runtime media-analysis stage.

### 5. Render privately and publish without overwriting

Resolve and compare paths before rendering; reject any existing output and any alias of the source or segment file. Existing-file identity checks must handle hard links as well as normalized or symbolic paths. Keep input files read-only throughout.

After validation, create a uniquely named temporary directory in the destination's parent and keep the temporary MP4 and any library temporary audio there. Render and close the media resources, then publish the completed file through a no-overwrite filesystem operation on Windows. Same-filesystem placement avoids copying a completed large video to another volume. Do not add post-render metadata, frame-rate, or encoding inspection. Test a destination appearing between preflight and publication. Never use a replace-existing operation.

Use structured cleanup (`with`/`try`/`finally`) for the source, concatenated clip, readers, and temporary directory. Derived clips can share source readers: do not close them in an order that invalidates still-needed media. Handle interruption with the same no-publication guarantee as processing failures. Report cleanup failures without masking the original error and identify any remaining application-owned temporary path. Never delete paths outside this operation's temporary directory. An abrupt process kill or power loss can leave a temporary directory; automatic startup scavenging is not part of the MVP.

Alternative: writing directly to the requested output risks exposing a partial result and obscures whether an edit completed successfully.

### 6. Verify incrementally with standard-library tests

Use `unittest`, `unittest.mock`, and temporary directories for parser, ordering, bounds, path protection, and CLI behavior. Unit tests must demonstrate that a late validation failure never reaches the rendering operation. Keep tests independent of MoviePy where media is not involved.

Use the user-provided fixture pair `input/sample.mp4` and `input/sample-selections.txt` for the primary media integration test. Read the supplied selection file as-is so it determines the retained sections being tested. Do not synthesize source videos or create, replace, or modify either sample file. Resolve fixture paths from the repository root rather than relying on the test runner's working directory. If a required sample is absent, the media test must clearly identify its expected path instead of generating a substitute. These fixture paths are a test convention, not hardcoded CLI input defaults.

Implement one basic real-media integration test: run a valid edit with the supplied fixture pair to a separate temporary output path, reopen the completed MP4 through MoviePy, and compare its duration with an independently calculated `sum(end - start)` using the fixed 0.5-second absolute tolerance. Resolve a final `end` to source duration; do not derive the expectation from the edited clip or renderer result. Report expected duration, actual duration, and tolerance on failure.

Keep media integration assertions limited to successful editing and expected final duration. Do not add decoded-content comparisons, frame identities, dimensions/rate assertions, audio alignment analysis, fixture checksums, generated media variants, or manual quality acceptance gates. Use focused unit tests, temporary non-media files, and mocks for application parsing, clipping calls, default writing calls, input protection, publication, and handled failures; do not retest MoviePy or FFmpeg internals. The same basic edit serves as the Windows Python 3.14 dependency smoke check. Document where the user places both fixture files and that the existing `input/*` ignore rule keeps them local.

## Risks / Trade-offs

- Python 3.14 dependency compatibility is not established by a permissive version requirement -> install and smoke-test the chosen released dependency set in the intended venv before implementing around it.
- MoviePy moves decoded frames through Python and can render slowly -> use one source reader and lazy subclips, avoid loading recordings into memory, and expose progress without promising throughput.
- Library defaults determine media encoding, frame timing, and audio behavior -> delegate those details to MoviePy and scope acceptance to clipping, merging, and expected total duration.
- A recording can decode successfully at the start and fail later -> treat later decode failures like encoder failures and withhold publication.
- Temporary output and audio require additional disk capacity -> keep them together on the output filesystem, handle disk errors, and clean only owned temporary files. No full source copies or per-segment output files are needed.
- Windows media subprocesses can retain file locks -> close all owned readers/writers before output checks, publication, and temporary cleanup, and test error paths.
- Default encoding can change visual or audio quality -> document that output uses library defaults and no perceptual quality guarantee is part of this change.

## Migration Plan

There is no existing application or durable user state to migrate. Apply the change in small verified steps: establish the dependency/runtime baseline, implement selection validation, integrate rendering and safe publication, then complete CLI and media acceptance checks.

Update README setup/usage and replace stale MPG and undecided-feature descriptions in the existing OpenSpec context during implementation, preserving unrelated rules. Keep input and output recordings outside version control under the existing ignore conventions. Rolling back application/dependency changes does not require touching original recordings; completed outputs remain independent files.

## Open Questions

- Which exact MoviePy 2.x release and compatible transitive versions pass the Python 3.14 Windows smoke test? Selection is an implementation verification detail; the engine and runtime requirement are fixed.

## References

- [MoviePy package metadata](https://pypi.org/project/moviepy/) describes the supported Python baseline and decoded-frame editing model; it does not by itself prove Python 3.14 compatibility.
- [MoviePy loading and resource lifetime](https://zulko.github.io/moviepy/user_guide/loading.html) explains closing owned clips and the lifetime of derived clips.
- [MoviePy concatenation](https://zulko.github.io/moviepy/user_guide/compositing.html) documents chaining clips and carrying their audio.
- [imageio-ffmpeg installation](https://github.com/imageio/imageio-ffmpeg#installation) documents pip wheels containing the executable.
