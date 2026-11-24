"""CLI argument and reporting tests, independent of installed media libraries."""

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from video_editor import cli
from video_editor.segments import SelectionError


ROOT = Path(__file__).resolve().parents[1]


class ArgumentTests(unittest.TestCase):
    def run_module(self, *arguments):
        environment = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        return subprocess.run(
            [sys.executable, "-S", "-m", "video_editor", *arguments],
            cwd=ROOT, env=environment, capture_output=True, text=True,
        )

    def test_module_help_works_without_moviepy(self):
        result = self.run_module("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for text in ("--input", "--segments", "--output", "whole-number", "original timeline"):
            self.assertIn(text, result.stdout)
        self.assertEqual(result.stderr, "")

    def test_all_paths_are_required(self):
        options = {"--input": "input.mp4", "--segments": "keep.txt", "--output": "out.mp4"}
        for missing in options:
            with self.subTest(missing=missing):
                arguments = [value for key, path in options.items() if key != missing for value in (key, path)]
                result = self.run_module(*arguments)
                self.assertEqual(result.returncode, 2)
                self.assertIn(missing, result.stderr)
                self.assertIn("usage:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_paths_with_spaces_are_forwarded_as_paths(self):
        with patch.object(cli.editing, "edit_video") as edit, redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main([
                "--input", "input/original recording.mp4",
                "--segments", "input/keep ranges.txt",
                "--output", "output/edited recording.mp4",
            ]), 0)
        edit.assert_called_once_with(
            Path("input/original recording.mp4"),
            Path("input/keep ranges.txt"),
            Path("output/edited recording.mp4"),
        )


    def test_missing_dependencies_report_setup_command_without_traceback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            video = root / "original.mp4"
            selections = root / "keep.txt"
            output = root / "edited.mp4"
            video.write_bytes(b"unopened source")
            selections.write_text("0,5", encoding="utf-8")
            result = self.run_module(
                "--input", str(video), "--segments", str(selections), "--output", str(output)
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("dependencies", result.stderr)
            self.assertIn("python -m pip install -r requirements.txt", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertNotIn("Saved edited video", result.stdout)
            self.assertFalse(output.exists())


class ConsoleTests(unittest.TestCase):
    def invoke(self, **mock_options):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(cli.editing, "edit_video", **mock_options):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = cli.main([
                    "--input", "input/source.mp4", "--segments", "input/keep.txt",
                    "--output", "output/edited.mp4",
                ])
        return status, stdout.getvalue(), stderr.getvalue()

    def test_success_confirms_output_path(self):
        output = (ROOT / "output/edited.mp4").resolve()
        status, stdout, stderr = self.invoke(return_value=output)
        self.assertEqual(status, 0)
        self.assertIn(f"Saved edited video: {output}", stdout)
        self.assertEqual(stderr, "")

    def test_failures_have_no_false_success_or_traceback(self):
        for error in (
            SelectionError("line 4: numeric timestamps must use whole-number seconds"),
            cli.editing.EditingError("Failed while publishing output: already exists"),
            cli.editing.EditingError("Cleanup failed for temporary directory: Access denied"),
            PermissionError("Output directory is not writable"),
        ):
            with self.subTest(error=error):
                error.add_note("Cleanup failed for temporary directory 'owned-path': File locked")
                status, stdout, stderr = self.invoke(side_effect=error)
                self.assertEqual(status, 1)
                self.assertIn(str(error), stderr)
                self.assertIn("owned-path", stderr)
                self.assertNotIn("Traceback", stderr)
                self.assertNotIn("Saved edited video", stdout)

    def test_cancellation_returns_nonzero_and_reports_cleanup_notes(self):
        error = KeyboardInterrupt()
        error.add_note("Cleanup failed for temporary directory 'owned-path': File locked")
        status, stdout, stderr = self.invoke(side_effect=error)
        self.assertEqual(status, 130)
        self.assertIn("cancelled", stderr)
        self.assertIn("owned-path", stderr)
        self.assertNotIn("Traceback", stderr)
        self.assertNotIn("Saved edited video", stdout)


if __name__ == "__main__":
    unittest.main()
