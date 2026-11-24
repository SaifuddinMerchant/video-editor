"""Test application media orchestration without loading MoviePy or media files."""

from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import Mock, call, patch

from video_editor.editing import EditingError, open_source, render_segments
from video_editor.segments import parse_segments


class SourceLifetimeTests(unittest.TestCase):
    def setUp(self):
        self.source = Mock(spec=["duration", "close", "subclipped"])
        self.source.duration = 90.4
        self.moviepy = ModuleType("moviepy")
        self.moviepy.VideoFileClip = Mock(return_value=self.source)
        self.moviepy.concatenate_videoclips = Mock()
        replacement = patch.dict(sys.modules, {"moviepy": self.moviepy})
        replacement.start()
        self.addCleanup(replacement.stop)

    def test_source_is_opened_with_defaults_and_kept_alive_until_context_exit(self):
        path = Path("input/recording with spaces.mp4")
        with open_source(path) as source:
            self.assertIs(source, self.source)
            self.assertEqual(source.duration, 90.4)
            self.source.close.assert_not_called()
        self.moviepy.VideoFileClip.assert_called_once_with(str(path))
        self.source.close.assert_called_once_with()

    def test_open_failures_include_source_path_and_cause(self):
        for error in (OSError("Access denied"), ValueError("Invalid media")):
            with self.subTest(error=error):
                self.moviepy.VideoFileClip.side_effect = error
                with self.assertRaises(EditingError) as caught:
                    with open_source("input/broken.mp4"):
                        self.fail("An invalid source must not be yielded")
                self.assertIn("input/broken.mp4", str(caught.exception))
                self.assertIn(str(error), str(caught.exception))
                self.assertIs(caught.exception.__cause__, error)
        self.source.close.assert_not_called()

    def test_invalid_duration_closes_source_before_raising(self):
        for duration in (None, 0, -1, float("nan"), float("inf"), -float("inf"), "90", True):
            with self.subTest(duration=duration):
                self.source.duration = duration
                self.source.close.reset_mock()
                with self.assertRaisesRegex(EditingError, "finite positive duration"):
                    with open_source("input/invalid-duration.mp4"):
                        self.fail("An invalid duration must not be yielded")
                self.source.close.assert_called_once_with()

    def test_source_is_closed_on_body_failure_or_interruption(self):
        for error in (RuntimeError("consumer failed"), KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__):
                self.source.close.reset_mock()
                with self.assertRaises(type(error)) as caught:
                    with open_source("input/sample.mp4"):
                        raise error
                self.assertIs(caught.exception, error)
                self.source.close.assert_called_once_with()


    def test_source_cleanup_error_does_not_mask_consumer_failure(self):
        self.source.close.side_effect = OSError("Reader close failed")
        failure = ValueError("Original validation failure")
        with self.assertRaises(ValueError) as caught:
            with open_source("input/sample.mp4"):
                raise failure
        self.assertIs(caught.exception, failure)
        self.assertIn("Reader close failed", " ".join(failure.__notes__))

    def test_unavailable_ffmpeg_reports_dependency_reinstall_command(self):
        self.moviepy.VideoFileClip.side_effect = FileNotFoundError("Bundled FFmpeg missing")
        with self.assertRaisesRegex(EditingError, "restore bundled FFmpeg.*pip install"):
            with open_source("input/sample.mp4"):
                self.fail("No usable reader should be yielded")

    def test_unusable_dependency_import_reports_setup_command(self):
        with patch.dict(sys.modules, {"moviepy": None}):
            with self.assertRaisesRegex(EditingError, "dependencies.*pip install.*requirements.txt"):
                with open_source("input/sample.mp4"):
                    self.fail("Unavailable MoviePy should not be used")


class RenderingTests(unittest.TestCase):
    def setUp(self):
        self.source = Mock(spec=["duration", "close", "subclipped"])
        self.source.duration = 90.4
        self.merged = Mock(spec=["write_videofile", "close"])
        self.moviepy = ModuleType("moviepy")
        self.moviepy.VideoFileClip = Mock(return_value=self.source)
        self.moviepy.concatenate_videoclips = Mock(return_value=self.merged)
        replacement = patch.dict(sys.modules, {"moviepy": self.moviepy})
        replacement.start()
        self.addCleanup(replacement.stop)
        self.output = Path("output/private render/edited.mp4")

    def test_ranges_are_clipped_and_merged_in_order_with_default_writing(self):
        cases = (
            ("5,10", [(5, 10)], 5),
            ("5,10\n20,25", [(5, 10), (20, 25)], 10),
            ("0,5\n5,10", [(0, 5), (5, 10)], 10),
            ("60,end", [(60, 90.4)], 30.4),
            ("0,end", [(0, 90.4)], 90.4),
        )
        for text, expected_ranges, expected_length in cases:
            with self.subTest(text=text):
                self.source.reset_mock()
                self.merged.reset_mock()
                self.moviepy.concatenate_videoclips.reset_mock()
                clips = [Mock(spec=["close"]) for _ in expected_ranges]
                self.source.subclipped.side_effect = clips
                segments = parse_segments(text, self.source.duration)
                self.assertAlmostEqual(
                    sum(segment.end - segment.start for segment in segments), expected_length
                )

                def assert_readers_alive(*args, **kwargs):
                    self.source.close.assert_not_called()
                    self.merged.close.assert_not_called()
                    for clip in clips:
                        clip.close.assert_not_called()

                self.merged.write_videofile.side_effect = assert_readers_alive
                with open_source("input/sample.mp4") as source:
                    render_segments(source, segments, self.output)
                self.assertEqual(
                    self.source.subclipped.call_args_list,
                    [call(start, end) for start, end in expected_ranges],
                )
                self.moviepy.concatenate_videoclips.assert_called_once_with(clips)
                # Exact arguments exclude all media settings, including audio overrides.
                self.merged.write_videofile.assert_called_once_with(
                    str(self.output), temp_audiofile_path=str(self.output.parent)
                )
                self.merged.close.assert_called_once_with()
                for clip in clips:
                    clip.close.assert_called_once_with()
                self.source.close.assert_called_once_with()

    def test_write_failure_or_interruption_releases_all_owned_clips(self):
        for error in (OSError("Disk full"), KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__):
                self.source.reset_mock()
                self.merged.reset_mock()
                clip = Mock(spec=["close"])
                self.source.subclipped.return_value = clip
                self.merged.write_videofile.side_effect = error
                with self.assertRaises(type(error)) as caught:
                    with open_source("input/sample.mp4") as source:
                        render_segments(source, parse_segments("0,5", 90.4), self.output)
                self.assertIs(caught.exception, error)
                self.merged.close.assert_called_once_with()
                clip.close.assert_called_once_with()
                self.source.close.assert_called_once_with()

    def test_subclip_failure_closes_earlier_clip_and_source(self):
        clip = Mock(spec=["close"])
        self.source.subclipped.side_effect = [clip, OSError("Cannot decode")]
        with self.assertRaisesRegex(OSError, "Cannot decode"):
            with open_source("input/sample.mp4") as source:
                render_segments(source, parse_segments("0,5\n10,15", 90.4), self.output)
        clip.close.assert_called_once_with()
        self.source.close.assert_called_once_with()
        self.moviepy.concatenate_videoclips.assert_not_called()
        self.merged.write_videofile.assert_not_called()

    def test_concatenation_failure_closes_subclips_and_source(self):
        clip = Mock(spec=["close"])
        self.source.subclipped.return_value = clip
        self.moviepy.concatenate_videoclips.side_effect = ValueError("Cannot concatenate")
        with self.assertRaisesRegex(ValueError, "Cannot concatenate"):
            with open_source("input/sample.mp4") as source:
                render_segments(source, parse_segments("0,5", 90.4), self.output)
        clip.close.assert_called_once_with()
        self.source.close.assert_called_once_with()
        self.merged.write_videofile.assert_not_called()


    def test_clip_cleanup_errors_preserve_write_failure_and_attempt_all_closures(self):
        clip = Mock(spec=["close"])
        self.source.subclipped.return_value = clip
        failure = OSError("Encoder failed")
        self.merged.write_videofile.side_effect = failure
        self.merged.close.side_effect = OSError("Merged close failed")
        clip.close.side_effect = OSError("Subclip close failed")
        with self.assertRaises(OSError) as caught:
            with open_source("input/sample.mp4") as source:
                render_segments(source, parse_segments("0,5", 90.4), self.output)
        self.assertIs(caught.exception, failure)
        self.assertIn("Merged close failed", " ".join(failure.__notes__))
        self.assertIn("Subclip close failed", " ".join(failure.__notes__))
        self.source.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
