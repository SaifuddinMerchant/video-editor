"""One real-media duration check using the user-provided sample pair."""

from pathlib import Path
import tempfile
import unittest

from video_editor.cli import main
from video_editor.editing import open_source


ROOT = Path(__file__).resolve().parents[1]


class EditingIntegrationTests(unittest.TestCase):
    def test_sample_edit_matches_selected_duration(self):
        video_path = ROOT / "input/sample.mp4"
        selections_path = ROOT / "input/sample-selections.txt"
        missing = [path for path in (video_path, selections_path) if not path.is_file()]
        if missing:
            self.fail(
                "Required integration sample files missing: "
                + ", ".join(str(path) for path in missing)
                + ". Provide input/sample.mp4 and input/sample-selections.txt; "
                "the test does not generate source fixtures."
            )

        with tempfile.TemporaryDirectory(prefix="duration-test-", dir=ROOT / "output") as temporary:
            output = Path(temporary) / "edited.mp4"
            with open_source(video_path) as source:
                # Calculate from the original text and duration, independently
                # of the application's parsed records and rendered clip.
                expected = 0
                for line in selections_path.read_text(encoding="utf-8-sig").splitlines():
                    if line.strip():
                        start, end = (value.strip() for value in line.split(","))
                        endpoint = source.duration if end.lower() == "end" else int(end)
                        expected += endpoint - int(start)

            status = main([
                "--input", str(video_path), "--segments", str(selections_path),
                "--output", str(output),
            ])
            self.assertEqual(status, 0, "Sample CLI edit failed; see the console error above")

            # Close all render resources before reopening the completed file.
            with open_source(output) as completed:
                actual = completed.duration
            tolerance = 0.5
            message = (
                f"Expected duration: {expected:.6f}s; actual duration: {actual:.6f}s; "
                f"absolute tolerance: {tolerance}s"
            )
            self.assertLessEqual(abs(actual - expected), tolerance, message)
            print(message)


if __name__ == "__main__":
    unittest.main()
