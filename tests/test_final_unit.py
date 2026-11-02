"""Independent unit boundaries/receipts and actual fixture artifact roundtrip."""

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import test_final_gate as fixture_tests

from ev_models.checkpoint import digest, write_json
from tools.export_development import put_run
from tools.final_unit import check_receipt, unit_at
from tools.verify_comparison import verify_run
from tools.verify_latest_states import verify_state


class FinalUnitBoundaryTests(unittest.TestCase):
    def test_lane_and_verified_predecessor_are_required(self):
        lock = {"unit_order": [{"identity": i} for i in range(4)]}
        self.assertEqual(unit_at(lock, 2, 0), {"identity": 2})
        with self.assertRaises(ValueError):
            unit_at(lock, 2, 1)
        check_receipt("lock", 0, 0, None, None)
        with self.assertRaises(ValueError):
            check_receipt("lock", 2, 0, None, None)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "receipt.json"
            row = {
                "schema": "ev-final-unit-acceptance-v1",
                "lock_sha256": "lock",
                "unit_index": 0,
                "lane": 0,
                "independent_content_verified": True,
                "native_readback_verified": True,
                "accepted_method_cells": 14,
            }
            write_json(p, row)
            check_receipt("lock", 2, 0, p, digest(p))
            for name, value in (
                ("native_readback_verified", False),
                ("accepted_method_cells", 13),
                ("unit_index", 1),
            ):
                p.write_text(json.dumps({**row, name: value}))
                with self.subTest(name=name), self.assertRaises(ValueError):
                    check_receipt("lock", 2, 0, p, digest(p))

    def test_final_initialization_record_roundtrips_and_tamper_fails(self):
        fixture = fixture_tests.FinalFixtureTests()
        fixture.setUp()
        try:
            run, _ = fixture.run_fixture("export-fixture")
            report = json.loads((run / "run.json").read_text())
            # execute() returns dataclass tuples while run.json contains arrays.
            report["method"] = {"proxy_thresholds": (0.1, 0.5), "proxy_order": (0, 1, 2)}
            (run / "run.json").write_text(json.dumps(report))
            daily = verify_run(run, fixture.input_root, final_access=fixture.access)
            state = verify_state(run, report)
            path = fixture.root / "export.zip"
            with zipfile.ZipFile(path, "x") as archive:
                put_run(
                    archive,
                    fixture.root,
                    report,
                    state,
                    daily["historical_states_intentionally_omitted"],
                )
            with zipfile.ZipFile(path) as archive:
                self.assertIsNone(archive.testzip())
                self.assertIn("study/export-fixture/initial-adaptation.json", archive.namelist())
            changed = {**report, "method": {**report["method"], "proxy_order": (2, 1, 0)}}
            with zipfile.ZipFile(fixture.root / "changed-report.zip", "x") as archive:
                with self.assertRaisesRegex(ValueError, "Changed completed run report"):
                    put_run(
                        archive,
                        fixture.root,
                        changed,
                        state,
                        daily["historical_states_intentionally_omitted"],
                    )
            (run / "initial-adaptation.json").write_text('[{"steps":999}]')
            with zipfile.ZipFile(fixture.root / "bad.zip", "x") as archive:
                with self.assertRaisesRegex(ValueError, "initialization record"):
                    put_run(
                        archive,
                        fixture.root,
                        report,
                        state,
                        daily["historical_states_intentionally_omitted"],
                    )
        finally:
            fixture.doCleanups()
