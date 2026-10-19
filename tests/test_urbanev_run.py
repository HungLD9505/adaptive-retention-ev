"""Tiny ZIP fixtures verify source binding, immutable inputs and failed-run evidence."""

import csv
import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from tools.sources import Archive
from tools.urbanev import main, run_pipeline
from tools.urbanev_hourly import RAW_FIELDS, HourlyConfig


class RunTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "extracted/station-raw"
        (self.source / "charge_5min").mkdir(parents=True)
        files = {
            "station_information.csv": (
                "station_id,longitude,latitude,slow_count,fast_count,charge_count,TAZID\n"
                "1001,113,22,1,0,1,559\n"
            ),
            "pile_rated_power.csv": "pile_id,power,pileType,station_id\n1,7,AC,1001\n",
            "station_distance.csv": "ID,1001\n1001,0\n",
        }
        for name, content in files.items():
            (self.source / name).write_text(content)
        with (self.source / "charge_5min/1001.csv").open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(RAW_FIELDS)
            for minute in range(0, 60, 5):
                writer.writerow(
                    [
                        f"2022-09-01 00:{minute:02}:00",
                        1,
                        0,
                        0,
                        0,
                        0,
                        0,
                        1,
                        0,
                        "0.08333333333333333",
                        "0.5",
                    ]
                )
        self.config = HourlyConfig(datetime(2022, 9, 1), datetime(2022, 9, 1, 1), "UTC", "start")
        self.spec = self.make_archive()

    def make_archive(self) -> Archive:
        archive = self.root / "data/raw/fixture/source.zip"
        archive.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(archive, "w") as out:
            for file in sorted(self.source.rglob("*.csv")):
                out.write(
                    file,
                    "UrbanEVDataset/20220901-20230228_station-raw/"
                    + file.relative_to(self.source).as_posix(),
                )
        return Archive(
            "urbanev-main",
            "urbanev",
            "https://example.invalid/source.zip",
            "data/raw/fixture/source.zip",
            archive.stat().st_size,
            hashlib.sha256(archive.read_bytes()).hexdigest(),
            True,
        )

    def run_fixture(self, name: str = "test-run", spec: Archive | None = None) -> tuple:
        return run_pipeline(
            self.source, self.root, spec or self.spec, self.root / "processed", self.config, name
        )

    def test_real_fixture_run_is_reproducible_and_raw_is_unchanged(self) -> None:
        paths = list(self.source.rglob("*.csv")) + [self.root / self.spec.relative_path]
        before = {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in paths}
        output, manifest = self.run_fixture()
        self.assertEqual(manifest["status"], "technical_qc_pass")
        self.assertEqual(manifest["research_acceptance"], "pending_peer_review")
        with (output / "hourly.csv").open() as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(rows[0]["energy_kwh"], "6")
        self.assertEqual(rows[0]["file_valid_mask"], "1")
        self.assertEqual(manifest["summary"]["counts"]["valid_hours"], 1)
        self.assertEqual(before, {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in paths})
        second, _ = self.run_fixture("second")
        self.assertEqual((output / "hourly.csv").read_bytes(), (second / "hourly.csv").read_bytes())
        with self.assertRaises(FileExistsError):
            self.run_fixture()

    def test_wrong_archive_and_changed_extraction_fail_with_manifest(self) -> None:
        with self.assertRaises(ValueError):
            self.run_fixture("bad-archive", replace(self.spec, sha256="0" * 64))
        manifest = json.loads((self.root / "processed/bad-archive/manifest.json").read_text())
        self.assertEqual(manifest["status"], "failed")
        with (self.source / "charge_5min/1001.csv").open("a") as stream:
            stream.write("changed")
        with self.assertRaises(ValueError):
            self.run_fixture("bad-extraction")
        manifest = json.loads((self.root / "processed/bad-extraction/manifest.json").read_text())
        self.assertIn("do not match", manifest["error"])

    def test_inventory_mismatch_is_not_silently_ignored(self) -> None:
        (self.source / "charge_5min/9999.csv").write_text("extra")
        with self.assertRaisesRegex(ValueError, "inventory"):
            self.run_fixture()

    def test_raw_destinations_and_unsafe_ids_are_rejected(self) -> None:
        for output in [self.source, self.root / "data/raw/fixture"]:
            with self.assertRaises(ValueError):
                run_pipeline(self.source, self.root, self.spec, output, self.config, "bad")
        with self.assertRaises(ValueError):
            self.run_fixture("../escape")

    def test_metadata_count_and_zero_power_remain_explicit_diagnostics(self) -> None:
        (self.source / "pile_rated_power.csv").write_text(
            "pile_id,power,pileType,station_id\n1,0,AC,1001\n2,7,AC,1001\n"
        )
        self.spec = self.make_archive()
        _, manifest = self.run_fixture()
        self.assertEqual(manifest["metadata_qc"]["nonpositive_or_nonfinite_power_entries"], 1)
        self.assertEqual(manifest["metadata_qc"]["charger_count_mismatch_stations"], ["1001"])

    def test_structural_qc_failure_returns_nonzero_and_preserves_evidence(self) -> None:
        path = self.source / "charge_5min/1001.csv"
        with path.open("a") as stream:
            stream.write("2022-09-01 00:00:00,1,0,0,0,0,0,1,0,0.1,0.5\n")
        self.spec = self.make_archive()
        args = [
            "--storage-root",
            str(self.root),
            "--source-root",
            str(self.source),
            "--output-root",
            str(self.root / "processed"),
            "--run-id",
            "cli",
            "--start",
            "2022-09-01T00:00:00",
            "--end",
            "2022-09-01T01:00:00",
            "--timezone",
            "UTC",
            "--interval-label",
            "start",
        ]
        with patch("tools.urbanev.load_catalog", return_value=[self.spec]):
            self.assertEqual(main(args), 1)
        manifest = json.loads((self.root / "processed/cli/manifest.json").read_text())
        self.assertEqual(manifest["status"], "structural_qc_failed")
        self.assertTrue((self.root / "processed/cli/hourly.csv").exists())
