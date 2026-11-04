"""Regression tests for the listings run status classification."""
import unittest

from src.write_snapshot_status import classify


class RunStatusTests(unittest.TestCase):
    def test_no_rows_is_not_zero_houses(self):
        self.assertEqual(classify("success", "success", "success", 0),
                         ("no_input_rows", "success_no_data"))

    def test_available_input(self):
        self.assertEqual(classify("success", "success", "success", 3),
                         ("input_rows_available", "success_with_data"))

    def test_failed_snapshot(self):
        self.assertEqual(classify("failure", "skipped", "skipped", 0),
                         ("incomplete", "failed"))

    def test_failed_downstream_job(self):
        self.assertEqual(classify("success", "failure", "skipped", 4),
                         ("incomplete", "failed"))


if __name__ == "__main__":
    unittest.main()
