"""Exact-coordinate diagnostics do not establish physical identity."""

import io
import unittest
from zipfile import ZipFile

from tools.charged_suitability import clock_span, coordinate_overlap, metadata


class SuitabilityTests(unittest.TestCase):
    def test_duplicates_do_not_become_one_to_one_matches(self) -> None:
        left = [
            {"id": "A", "longitude": "114.1", "latitude": "22.10"},
            {"id": "B", "longitude": "114.10", "latitude": "22.1"},
        ]
        right = [
            {"id": "X", "longitude": "114.1", "latitude": "22.1"},
            {"id": "Y", "longitude": "114.10000000000000001", "latitude": "22.1"},
        ]
        result = coordinate_overlap(left, right, "id", "id")
        self.assertEqual(result["shared_coordinate_pairs"], 1)
        self.assertEqual(result["left_rows_at_shared_coordinates"], 2)
        self.assertEqual(result["right_rows_at_shared_coordinates"], 1)
        self.assertIn("not a one-to-one", result["interpretation"])

    def test_invalid_coordinate_is_rejected(self) -> None:
        for value in ("NaN", "181"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                coordinate_overlap(
                    [{"id": "A", "longitude": value, "latitude": "0"}], [], "id", "id"
                )

    def test_clock_scope_and_ragged_metadata(self) -> None:
        stream = io.BytesIO()
        with ZipFile(stream, "w") as archive:
            archive.writestr("clock.csv", "time,value\n2023-01-02,1\n2023-01-01,0\n")
            archive.writestr("bad.csv", "id,value\nA,1,extra\n")
        stream.seek(0)
        with ZipFile(stream) as archive:
            result = clock_span(archive, "clock.csv")
            self.assertEqual(result["minimum_literal_clock"], "2023-01-01T00:00:00")
            self.assertIn("member only", result["sample_scope"])
            with self.assertRaisesRegex(ValueError, "Ragged metadata"):
                metadata(archive, "bad.csv")


if __name__ == "__main__":
    unittest.main()
