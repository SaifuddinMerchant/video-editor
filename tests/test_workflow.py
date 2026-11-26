"""Protect filesystem inputs and output publication using non-media files."""

from contextlib import contextmanager, redirect_stderr, redirect_stdout
import io
from pathlib import Path
import os
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from video_editor import cli, editing
from video_editor.segments import SelectionError


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.video = self.root / "original recording.MP4"
        self.selections = self.root / "keep ranges.txt"
        self.output = self.root / "edited recording.MP4"
        self.video.write_bytes(b"original video bytes")
        self.selections.write_bytes(b"0,5\n10,end\n")
        self.original_video = self.video.read_bytes()
        self.original_selections = self.selections.read_bytes()
        self.closed = False
        self.handle = None
        self.render_path = None
        self.source = SimpleNamespace(duration=20.4)
        source_patch = patch.object(editing, "open_source", side_effect=self.open_source)
        render_patch = patch.object(editing, "render_segments", side_effect=self.render)
        self.open_mock = source_patch.start()
        self.render_mock = render_patch.start()
        self.addCleanup(source_patch.stop)
        self.addCleanup(render_patch.stop)

    @contextmanager
    def open_source(self, path):
        with Path(path).open("rb") as handle:
            self.handle = handle
            try:
                yield self.source
            finally:
                self.closed = True

    def render(self, source, segments, path):
        self.render_path = Path(path)
        self.assertFalse(self.closed)
        self.assertFalse(self.handle.closed)
        self.assertEqual(self.render_path.parent.parent, self.output.parent)
        self.assertEqual(self.render_path.suffix, ".mp4")
        self.assertNotEqual(self.render_path, self.output)
        self.render_path.write_bytes(b"complete render")
        (self.render_path.parent / "temporary-audio.mp3").write_bytes(b"audio")

    def assert_inputs_unchanged(self):
        self.assertEqual(self.video.read_bytes(), self.original_video)
        self.assertEqual(self.selections.read_bytes(), self.original_selections)

    def assert_no_temporary_files(self):
        self.assertEqual(list(self.root.glob(".video-editor-*")), [])

    def test_success_publishes_only_after_source_is_closed(self):
        publish = editing._publish

        def check_closed(rendered, output):
            self.assertTrue(self.closed)
            self.assertTrue(self.handle.closed)
            self.assertFalse(output.exists())
            publish(rendered, output)

        with patch.object(editing, "_publish", side_effect=check_closed):
            result = editing.edit_video(self.video, self.selections, self.output)
        self.assertEqual(result, self.output.resolve())
        self.assertEqual(self.output.read_bytes(), b"complete render")
        self.open_mock.assert_called_once_with(self.video.resolve())
        self.assert_inputs_unchanged()
        self.assert_no_temporary_files()

    def test_invalid_late_selection_never_allocates_render_files(self):
        for invalid in ("10,20.5", "10,25", "5,8"):
            with self.subTest(invalid=invalid):
                self.selections.write_text("0,5\n10,15\n" + invalid, encoding="utf-8")
                with patch.object(editing.tempfile, "TemporaryDirectory") as allocate:
                    with self.assertRaisesRegex(SelectionError, "line 3:"):
                        editing.edit_video(self.video, self.selections, self.output)
                    allocate.assert_not_called()
                self.render_mock.assert_not_called()
                self.assertFalse(self.output.exists())
                self.assertTrue(self.handle.closed)
                self.assert_no_temporary_files()

    def test_cli_reports_actual_selection_line_error_without_rendering(self):
        self.selections.write_text("0,5\n10,15\n15,20.5", encoding="utf-8")
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = cli.main([
                "--input", str(self.video), "--segments", str(self.selections),
                "--output", str(self.output),
            ])
        self.assertEqual(status, 1)
        self.assertIn("line 3:", stderr.getvalue())
        self.assertIn("whole-number", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())
        self.assertNotIn("Saved edited video", stdout.getvalue())
        self.render_mock.assert_not_called()
        self.assertFalse(self.output.exists())
        self.assert_no_temporary_files()

    def test_non_mp4_extensions_are_rejected_before_opening_media(self):
        for video, output in ((self.video.with_suffix(".mov"), self.output),
                              (self.video, self.output.with_suffix(".avi"))):
            with self.subTest(video=video, output=output):
                with self.assertRaisesRegex(editing.EditingError, "MP4 extension"):
                    editing.edit_video(video, self.selections, output)
        self.open_mock.assert_not_called()
        self.render_mock.assert_not_called()

    def test_output_extension_error_precedes_missing_source(self):
        missing = self.root / "missing.mp4"
        output = self.output.with_suffix(".avi")
        with self.assertRaises(editing.EditingError) as raised:
            editing.edit_video(missing, self.selections, output)
        self.assertEqual(
            str(raised.exception), f"Output video must have an MP4 extension: '{output}'"
        )
        self.open_mock.assert_not_called()
        self.render_mock.assert_not_called()

    def test_missing_inputs_and_destination_parent_are_rejected(self):
        for video, selections, output in (
            (self.root / "missing.mp4", self.selections, self.output),
            (self.video, self.root / "missing.txt", self.output),
            (self.video, self.selections, self.root / "missing" / "edited.mp4"),
            (self.video, self.selections, self.video / "edited.mp4"),
        ):
            with self.subTest(output=output, video=video, selections=selections):
                with self.assertRaises(editing.EditingError):
                    editing.edit_video(video, selections, output)
        self.open_mock.assert_not_called()
        self.render_mock.assert_not_called()

    def test_unreadable_input_is_rejected_before_opening_media(self):
        with patch.object(Path, "open", side_effect=PermissionError("Access denied")):
            with self.assertRaisesRegex(editing.EditingError, "Cannot read.*Access denied"):
                editing.edit_video(self.video, self.selections, self.output)
        self.open_mock.assert_not_called()

    def test_existing_output_is_preserved(self):
        self.output.write_bytes(b"existing recording")
        with self.assertRaisesRegex(editing.EditingError, "already exists"):
            editing.edit_video(self.video, self.selections, self.output)
        self.assertEqual(self.output.read_bytes(), b"existing recording")
        self.open_mock.assert_not_called()
        self.assert_inputs_unchanged()

    def test_normalized_input_alias_is_rejected(self):
        alias = self.root / ".." / self.root.name / self.video.name
        with self.assertRaisesRegex(editing.EditingError, "aliases an input"):
            editing.edit_video(self.video, self.selections, alias)
        self.open_mock.assert_not_called()
        self.assert_inputs_unchanged()

    def test_hard_link_to_either_input_is_rejected(self):
        for original in (self.video, self.selections):
            with self.subTest(original=original):
                os.link(original, self.output)
                try:
                    with self.assertRaisesRegex(editing.EditingError, "aliases an input"):
                        editing.edit_video(self.video, self.selections, self.output)
                    self.assertEqual(self.output.read_bytes(), original.read_bytes())
                finally:
                    self.output.unlink()
        self.open_mock.assert_not_called()
        self.assert_inputs_unchanged()

    def test_destination_appearing_during_render_is_not_overwritten(self):
        render = self.render

        def competing_writer(*args):
            render(*args)
            self.output.write_bytes(b"another process won")

        self.render_mock.side_effect = competing_writer
        with self.assertRaisesRegex(editing.EditingError, "publishing output") as caught:
            editing.edit_video(self.video, self.selections, self.output)
        self.assertIsInstance(caught.exception.__cause__, FileExistsError)
        self.assertEqual(self.output.read_bytes(), b"another process won")
        self.assertTrue(self.handle.closed)
        self.assert_inputs_unchanged()
        self.assert_no_temporary_files()


    def test_render_failures_and_cancellation_remove_only_owned_files(self):
        unrelated = self.root / "unrelated.tmp"
        unrelated.write_bytes(b"leave this alone")
        for error in (RuntimeError("Encoder failed"), OSError("Disk full"),
                      PermissionError("Access denied"), KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__):
                def fail_after_partial_render(*args):
                    self.render(*args)
                    self.render_path.write_bytes(b"partial render")
                    raise error

                self.render_mock.side_effect = fail_after_partial_render
                self.closed = False
                expected = KeyboardInterrupt if isinstance(error, KeyboardInterrupt) else editing.EditingError
                with self.assertRaises(expected):
                    editing.edit_video(self.video, self.selections, self.output)
                self.assertFalse(self.output.exists())
                self.assertTrue(self.handle.closed)
                self.assertEqual(unrelated.read_bytes(), b"leave this alone")
                self.assert_inputs_unchanged()
                self.assert_no_temporary_files()

    def test_temporary_allocation_failure_closes_source(self):
        with patch.object(editing.tempfile, "TemporaryDirectory", side_effect=PermissionError("Access denied")):
            with self.assertRaisesRegex(editing.EditingError, "creating temporary output.*Access denied"):
                editing.edit_video(self.video, self.selections, self.output)
        self.assertTrue(self.handle.closed)
        self.render_mock.assert_not_called()
        self.assertFalse(self.output.exists())
        self.assert_inputs_unchanged()

    def test_publication_failure_removes_temporary_output(self):
        with patch.object(editing, "_publish", side_effect=PermissionError("Access denied")):
            with self.assertRaisesRegex(editing.EditingError, "publishing output.*Access denied"):
                editing.edit_video(self.video, self.selections, self.output)
        self.assertTrue(self.handle.closed)
        self.assertFalse(self.output.exists())
        self.assert_inputs_unchanged()
        self.assert_no_temporary_files()

    def test_source_close_failure_prevents_publication(self):
        @contextmanager
        def close_failure(path):
            with self.open_source(path) as source:
                yield source
            raise OSError("Could not close reader")

        self.open_mock.side_effect = close_failure
        with self.assertRaisesRegex(editing.EditingError, "closing source.*Could not close reader"):
            editing.edit_video(self.video, self.selections, self.output)
        self.assertFalse(self.output.exists())
        self.assertTrue(self.handle.closed)
        self.assert_inputs_unchanged()
        self.assert_no_temporary_files()

    def test_cleanup_failure_preserves_primary_error_and_reports_remaining_path(self):
        temporary = tempfile.TemporaryDirectory(prefix=".video-editor-", dir=self.root)
        self.addCleanup(temporary.cleanup)
        primary = OSError("Encoder failed")

        def fail_render(*args):
            self.render(*args)
            raise primary

        self.render_mock.side_effect = fail_render
        with patch.object(editing.tempfile, "TemporaryDirectory", return_value=temporary):
            with patch.object(temporary, "cleanup", side_effect=PermissionError("File locked")):
                with self.assertRaises(editing.EditingError) as caught:
                    editing.edit_video(self.video, self.selections, self.output)
        self.assertIs(caught.exception.__cause__, primary)
        self.assertIn("Encoder failed", str(caught.exception))
        notes = " ".join(caught.exception.__notes__)
        self.assertIn("Cleanup failed", notes)
        self.assertIn(temporary.name, notes)
        self.assertIn("File locked", notes)
        self.assertFalse(self.output.exists())
        self.assertTrue(self.handle.closed)
        self.assert_inputs_unchanged()

    def test_cleanup_failure_after_publication_is_not_reported_as_success(self):
        temporary = tempfile.TemporaryDirectory(prefix=".video-editor-", dir=self.root)
        self.addCleanup(temporary.cleanup)
        with patch.object(editing.tempfile, "TemporaryDirectory", return_value=temporary):
            with patch.object(temporary, "cleanup", side_effect=PermissionError("File locked")):
                with self.assertRaisesRegex(editing.EditingError, "Cleanup failed.*temporary directory.*File locked"):
                    editing.edit_video(self.video, self.selections, self.output)
        # A published file is complete even when subsequent temporary cleanup fails.
        self.assertEqual(self.output.read_bytes(), b"complete render")
        self.assertTrue(self.handle.closed)
        self.assert_inputs_unchanged()


if __name__ == "__main__":
    unittest.main()
