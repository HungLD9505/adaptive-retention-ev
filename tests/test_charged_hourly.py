"""Independent hourly adapter fixtures; no downloads or research-effectiveness claims."""

import csv
import hashlib
import io
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from tools.charged_hourly import BROKEN_INFO_HEADER, INFO_HEADER, adapt_city, metadata, run
from tools.sources import Archive


class ChargedHourlyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.start = datetime(2023, 4, 1)
        self.end = datetime(2023, 4, 1, 3)

    def fixture(self, clock: str | None = None, broken: bool = False) -> ZipFile:
        stream = io.BytesIO()
        with ZipFile(stream, "w") as archive:
            archive.writestr("AMS/sites.csv", "site,charger_num\n001,1\n2,1\n")
            archive.writestr("AMS/chargers.csv", "charger_id,site\na,001\nb,2\n")
            archive.writestr(
                "AMS/info.csv",
                ",".join(BROKEN_INFO_HEADER if broken else INFO_HEADER)
                + "\nAmsterdam,Netherlands,AMS,2,2,40,0,0,0\n",
            )
            archive.writestr(
                "AMS/volume.csv",
                clock or ",001,2\n2023-04-01 00:00:00,0,NaN\n2023-04-01 02:00:00,1,2\n",
            )
            archive.writestr(
                "AMS/duration.csv",
                clock or ",2,001\n2023-04-01 00:00:00,0,1\n2023-04-01 02:00:00,,0\n",
            )
        stream.seek(0)
        archive = ZipFile(stream)
        self.addCleanup(archive.close)
        return archive

    def test_zero_invalid_missing_and_duration_diagnostics(self) -> None:
        qc = adapt_city(
            self.fixture(broken=True), "AMS", self.root / "out", self.start, self.end, "start"
        )
        with (self.root / "out/hourly.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[0]["entity_id"], "001")
        self.assertEqual(rows[0]["energy_kwh"], "0")
        self.assertEqual(rows[0]["file_valid_mask"], "1")
        self.assertEqual(rows[1]["energy_kwh"], "")
        self.assertEqual(rows[1]["file_valid_mask"], "0")
        self.assertEqual(rows[2]["qc_flags"], "missing_hour")
        self.assertEqual(rows[2]["expected_sample_count"], "1")
        self.assertEqual(rows[2]["valid_sample_count"], "0")
        self.assertEqual(rows[4]["file_valid_mask"], "1")
        self.assertEqual(qc["counts"]["invalid_duration"], 1)
        self.assertEqual(qc["counts"]["positive_volume_zero_duration"], 1)
        self.assertEqual(qc["counts"]["zero_volume_positive_duration"], 1)
        self.assertTrue(qc["info_header_override"])
        self.assertEqual(qc["site_id_source_field"], "site")
        self.assertEqual(qc["counts"]["valid_energy_rows"], 3)

    def test_duplicates_and_out_of_order_fail(self) -> None:
        for second in ("00", "01", "02"):
            text = f",001,2\n2023-04-01 02:00:00,1,1\n2023-04-01 {second}:00:00,1,1\n"
            with self.subTest(second=second), self.assertRaisesRegex(ValueError, "out-of-order"):
                adapt_city(
                    self.fixture(text), "AMS", self.root / second, self.start, self.end, "start"
                )

    def test_all_zero_sites_are_retained(self) -> None:
        text = ",001,2\n2023-04-01 00:00:00,0,0\n2023-04-01 01:00:00,0,0\n2023-04-01 02:00:00,0,0\n"
        qc = adapt_city(
            self.fixture(text), "AMS", self.root / "zeros", self.start, self.end, "start"
        )
        self.assertEqual(qc["all_zero_volume_sites"], 2)
        self.assertEqual(qc["counts"]["rows"], 6)
        self.assertEqual(qc["counts"]["valid_energy_rows"], 6)

    def test_end_label_shifts_one_hour_without_timezone_assignment(self) -> None:
        text = ",001,2\n2023-04-01 01:00:00,1,1\n"
        adapt_city(
            self.fixture(text), "AMS", self.root / "end", self.start, datetime(2023, 4, 1, 1), "end"
        )
        with (self.root / "end/hourly.csv").open() as stream:
            row = next(csv.DictReader(stream))
        self.assertEqual(row["timestamp"], "2023-04-01T00:00:00")
        self.assertEqual(row["file_valid_mask"], "1")

    def test_unknown_info_header_is_not_silently_fixed(self) -> None:
        archive = self.fixture()
        with patch("tools.charged_hourly.table") as read:
            read.side_effect = [
                (["site", "charger_num"], [["0", "1"]]),
                (["charger_id", "site"], [["a", "0"]]),
                (["unknown"], [["x"]]),
            ]
            with self.assertRaisesRegex(ValueError, "unrecognized info.csv"):
                metadata(archive, "AMS")

    def test_failed_run_manifest_and_immutable_archive(self) -> None:
        raw = self.root / "data/raw/charged"
        raw.mkdir(parents=True)
        path = raw / "tiny.zip"
        with ZipFile(path, "w") as archive:
            archive.writestr("unrelated.txt", "fixture")
        before = path.read_bytes()
        spec = Archive(
            "charged-hourly",
            "charged",
            "https://example.test/fixture",
            "data/raw/charged/tiny.zip",
            len(before),
            hashlib.sha256(before).hexdigest(),
            True,
        )
        output = self.root / "new-run"
        with (
            patch("tools.charged_hourly.load_catalog", return_value=[spec]),
            self.assertRaises(KeyError),
        ):
            run(self.root, output, self.start, self.end, "start")
        self.assertEqual(json.loads((output / "manifest.json").read_text())["status"], "failed")
        self.assertEqual(path.read_bytes(), before)
        with self.assertRaises(FileExistsError):
            run(self.root, output, self.start, self.end, "start")
        with self.assertRaisesRegex(ValueError, "separate from raw"):
            run(self.root, raw / "out", self.start, self.end, "start")


if __name__ == "__main__":
    unittest.main()
