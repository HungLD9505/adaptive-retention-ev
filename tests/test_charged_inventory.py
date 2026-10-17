"""Independent fixtures for a read-only inventory, not research effectiveness tests."""

import csv
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from tools.charged_inventory import inspect_city, inspect_csv, time_inventory


class InventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write_csv(self, name: str, rows: list[list[str]]) -> Path:
        path = self.root / name
        with path.open("w", newline="") as stream:
            csv.writer(stream).writerows(rows)
        return path

    def test_missing_zero_nonfinite_negative_are_distinct(self) -> None:
        path = self.write_csv(
            "volume.csv",
            [
                ["", "0", "1", "2", "3", "4", "5"],
                ["2023-04-01 00:00:00", "0", "", "NaN", "-2", "bad", "2"],
                ["2023-04-01 01:00:00", "0", "0", "inf", "0", "0", "3"],
            ],
        )
        report = inspect_csv(path, "matrix")
        counts = report["numeric_cells"]
        self.assertEqual(counts["zero"], 5)
        self.assertEqual(counts["blank"], 1)
        self.assertEqual(counts["nonfinite"], 2)
        self.assertEqual(counts["nonnumeric"], 1)
        self.assertEqual(counts["negative"], 1)
        self.assertEqual(report["all_zero_sites"], ["0"])
        self.assertEqual(report["time"]["within_span_missing_hour_slots"], 0)

    def test_ragged_metadata_is_reported_without_column_repair(self) -> None:
        path = self.write_csv("info.csv", [["city", "total_siteBSCAN_eps"], ["X", "2", "40"]])
        before = path.read_bytes()
        report = inspect_csv(path, "info")
        self.assertEqual(report["header"], ["city", "total_siteBSCAN_eps"])
        self.assertEqual(report["rows_with_width_mismatch"], 1)
        self.assertEqual(report["missing_cells"]["extra_cells_in_long_rows"], 1)
        self.assertEqual(report["width_mismatch_examples"][0]["values"], ["X", "2", "40"])
        self.assertEqual(path.read_bytes(), before)

    def test_short_matrix_row_is_not_a_zero_or_an_all_zero_site(self) -> None:
        path = self.write_csv("volume.csv", [["", "0", "1"], ["2023-04-01", "0"]])
        report = inspect_csv(path, "matrix")
        self.assertEqual(report["all_zero_sites"], ["0"])
        self.assertEqual(report["missing_cells"]["absent_cells_in_short_rows"], 1)
        self.assertEqual(report["numeric_cells"]["zero"], 1)

    def test_clock_gaps_duplicates_and_unknown_timezone(self) -> None:
        report = time_inventory(
            ["2023-04-01 00:00:00", "2023-04-01 02:00:00", "2023-04-01 02:00:00", "bad"]
        )
        self.assertEqual(report["duplicates"], 1)
        self.assertEqual(report["parse_failures"], 1)
        self.assertEqual(report["within_span_missing_hour_slots"], 1)
        self.assertFalse(report["timezone_verified"])
        alternate = time_inventory(["2023/4/1 0:00"])
        iso = time_inventory(["2023-04-01 00:00:00"])
        self.assertEqual(alternate["parsed_sequence_sha256"], iso["parsed_sequence_sha256"])

    def test_city_aliases_missing_files_and_archive_mismatch(self) -> None:
        city = self.root / "AMS"
        city.mkdir()
        sites = city / "sites.csv"
        sites.write_text("site,longitude\n0,10\n")
        chargers = city / "chargers.csv"
        chargers.write_text("charger_id,site\n10,0\n")
        zip_path = self.root / "fixture.zip"
        with ZipFile(zip_path, "w") as archive:
            archive.write(sites, "AMS/sites.csv")
            archive.write(chargers, "AMS/chargers.csv")
        with ZipFile(zip_path) as archive:
            report = inspect_city(city, archive)
            self.assertEqual(report["site_id_header_observed"], "site")
            self.assertEqual(report["site_rows"], 1)
            self.assertIn("volume.csv", report["missing_expected_files"])
            self.assertIn("not_adjudicated", report["readiness"]["file_valid"])
            sites.write_text("site,longitude\n0,99\n")
            with self.assertRaisesRegex(ValueError, "differ from verified ZIP"):
                inspect_city(city, archive)


if __name__ == "__main__":
    unittest.main()
