"""Selection tests use only the standard library and temporary text files."""

from dataclasses import FrozenInstanceError
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from video_editor.segments import Segment, SelectionError, parse_segments, read_segments


class SegmentParsingTests(unittest.TestCase):
    def test_whole_seconds_and_surrounding_whitespace(self):
        self.assertEqual(
            parse_segments(" 0 , 5 \n\t10,20\t", 90),
            [Segment(0, 5, 1), Segment(10, 20, 2)],
        )

    def test_bom_blank_lines_and_physical_line_numbers(self):
        self.assertEqual(
            parse_segments("\ufeff\r\n \t\r\n 0,5\r\n\r\n10,20\r\n", 90),
            [Segment(0, 5, 3), Segment(10, 20, 5)],
        )

    def test_leading_zeroes_are_ascii_digits(self):
        self.assertEqual(parse_segments("000,005", 90), [Segment(0, 5, 1)])

    def test_segment_is_immutable(self):
        segment = parse_segments("0,5", 90)[0]
        with self.assertRaises(FrozenInstanceError):
            segment.end = 10

    def test_empty_input_is_rejected(self):
        for text in ("", " \n\t\r\n", "\ufeff", "\ufeff\n \n"):
            with self.subTest(text=text):
                with self.assertRaisesRegex(SelectionError, "at least one range"):
                    parse_segments(text, 90)

    def test_exactly_two_values_are_required(self):
        for line in ("0", "0,5,10", "0;5", "# comment", "start,end"):
            with self.subTest(line=line):
                with self.assertRaisesRegex(SelectionError, "line 3:"):
                    parse_segments("\n0,1\n" + line, 90)

    def test_non_digit_numeric_forms_are_rejected_in_either_position(self):
        tokens = (
            "", "2.4", "5.0", "0.0", "5/2", "-1", "+5", "-0", "5e0",
            "NaN", "inf", "Infinity", "-inf", "abc", "0x5", "00:05",
            "1 0", "\u0665", "\uff15", "\u00b2", "5\x00", "5 # comment",
        )
        for token in tokens:
            for line in (f"{token},5", f"0,{token}"):
                with self.subTest(line=line):
                    with self.assertRaisesRegex(
                        SelectionError, r"line 3:.*whole-number.*ASCII digits"
                    ):
                        parse_segments("\n0,1\n" + line, 90)

    def test_decimal_examples_fail_without_rounding_or_truncation(self):
        for line in ("0,2.4", "2.4,5", "0,5.0", "0.0,5"):
            with self.subTest(line=line):
                with self.assertRaisesRegex(SelectionError, "line 1:.*whole-number"):
                    parse_segments(line, 90)


class SelectionFileTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "keep ranges.txt"

    def test_utf8_with_or_without_bom_and_input_unchanged(self):
        for encoding in ("utf-8", "utf-8-sig"):
            with self.subTest(encoding=encoding):
                contents = "\n\n 0 , 5 \r\n".encode(encoding)
                self.path.write_bytes(contents)
                self.assertEqual(read_segments(self.path, 90), [Segment(0, 5, 3)])
                self.assertEqual(self.path.read_bytes(), contents)

    def test_missing_file_has_path_in_error(self):
        with self.assertRaises(SelectionError) as caught:
            read_segments(str(self.path), 90)
        self.assertIn(str(self.path), str(caught.exception))
        self.assertIn("Cannot read selection file", str(caught.exception))

    def test_unreadable_file_has_actionable_error(self):
        with patch.object(Path, "read_text", side_effect=PermissionError("Access denied")):
            with self.assertRaisesRegex(SelectionError, "Cannot read.*Access denied"):
                read_segments(self.path, 90)

    def test_directory_cannot_be_read_as_selection_file(self):
        with self.assertRaisesRegex(SelectionError, "Cannot read selection file"):
            read_segments(self.path.parent, 90)

    def test_invalid_utf8_has_path_and_encoding_in_error(self):
        self.path.write_bytes(b"0,5\n\xff")
        with self.assertRaises(SelectionError) as caught:
            read_segments(self.path, 90)
        self.assertIn(str(self.path), str(caught.exception))
        self.assertIn("UTF-8", str(caught.exception))

    def test_empty_file_is_rejected(self):
        self.path.write_bytes(b"")
        with self.assertRaisesRegex(SelectionError, "at least one range"):
            read_segments(self.path, 90)

    def test_file_end_resolution_preserves_fractional_duration(self):
        self.path.write_text("0,5\n\n90,EnD\n\n", encoding="utf-8-sig")
        self.assertEqual(
            read_segments(self.path, 90.4),
            [Segment(0, 5, 1), Segment(90, 90.4, 3)],
        )


class SegmentValidationTests(unittest.TestCase):
    def test_numeric_endpoint_can_equal_integer_source_duration(self):
        self.assertEqual(parse_segments("0,90", 90), [Segment(0, 90, 1)])
        self.assertEqual(parse_segments("0,90", 90.0), [Segment(0, 90, 1)])

    def test_final_end_is_case_insensitive_and_ignores_trailing_blanks(self):
        for keyword in ("end", "EnD", "END"):
            with self.subTest(keyword=keyword):
                self.assertEqual(
                    parse_segments(f"0,5\n\n60, {keyword} \n\t\n", 90),
                    [Segment(0, 5, 1), Segment(60, 90, 3)],
                )

    def test_full_source_and_fractional_tail_keep_exact_duration(self):
        duration = 90.43210987654321
        self.assertEqual(parse_segments("0,end", duration), [Segment(0, duration, 1)])
        tail = parse_segments("90,end", duration)[0]
        self.assertEqual(tail.end, duration)
        self.assertEqual(tail.end - tail.start, duration - 90)

    def test_whole_numeric_endpoint_below_fractional_duration_is_valid(self):
        self.assertEqual(parse_segments("0,90", 90.4), [Segment(0, 90, 1)])

    def test_end_in_start_or_earlier_endpoint_is_rejected(self):
        for text, line_number in (
            ("end,90", 1), ("EnD,end", 1),
            ("\n0,end\n\n60,90", 2), ("0,END\n60,end", 1),
        ):
            with self.subTest(text=text):
                with self.assertRaisesRegex(
                    SelectionError, f"line {line_number}:.*second value.*final nonblank"
                ):
                    parse_segments(text, 90)

    def test_duration_must_be_available_finite_and_positive(self):
        for duration in (None, 0, -1, float("nan"), float("inf"), -float("inf"), "90", True):
            with self.subTest(duration=duration):
                with self.assertRaisesRegex(SelectionError, "source duration.*finite positive"):
                    parse_segments("0,end", duration)

    def test_reversed_zero_length_and_out_of_bounds_ranges_are_rejected(self):
        for text in ("5,5", "20,10", "0,91", "90,91", "91,92", "90,end"):
            with self.subTest(text=text):
                with self.assertRaisesRegex(
                    SelectionError, r"line 2:.*0 <= start < end <= duration"
                ):
                    parse_segments("\n" + text, 90)
        with self.assertRaisesRegex(SelectionError, "line 1:.*duration"):
            parse_segments("0,91", 90.4)

    def test_negative_bounds_are_rejected_as_invalid_numeric_syntax(self):
        for text in ("-1,5", "0,-1"):
            with self.subTest(text=text):
                with self.assertRaisesRegex(SelectionError, "line 1:.*whole-number"):
                    parse_segments(text, 90)

    def test_adjacent_ranges_are_preserved_in_order_without_merging(self):
        self.assertEqual(
            parse_segments("0,5\n5,10\n10,end", 10.4),
            [Segment(0, 5, 1), Segment(5, 10, 2), Segment(10, 10.4, 3)],
        )

    def test_disjoint_ranges_use_original_timeline(self):
        self.assertEqual(
            parse_segments("5,10\n20,25", 60),
            [Segment(5, 10, 1), Segment(20, 25, 2)],
        )

    def test_earlier_overlap_takes_precedence_over_later_malformed_range(self):
        with self.assertRaises(SelectionError) as raised:
            parse_segments("0,5\n4,8\nmalformed", 10)
        self.assertEqual(
            str(raised.exception),
            "line 2: range overlaps or is out of order with line 1; "
            "start must be at or after the previous end",
        )

    def test_overlap_duplicates_and_out_of_order_ranges_identify_both_lines(self):
        for second in ("19,25", "0,5", "10,20", "12,15"):
            with self.subTest(second=second):
                with self.assertRaisesRegex(
                    SelectionError, "line 4:.*overlaps or is out of order.*line 2"
                ):
                    parse_segments("\n10,20\n\n" + second, 90)

    def test_late_error_raises_instead_of_returning_partial_selection(self):
        with self.assertRaisesRegex(SelectionError, "line 4:.*whole-number"):
            parse_segments("0,5\n5,10\n\n10,20.5", 90)


if __name__ == "__main__":
    unittest.main()
