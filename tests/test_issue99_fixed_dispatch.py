"""Station-first paired matrix aggregation and calibration-only dispatch fixture."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ev_search.execute import FixedMatrixEvaluator, aggregate_matrix


class FixedDispatchTests(unittest.TestCase):
    def rows(self):
        return [
            {
                "target": target,
                "seed": seed,
                "mae_kwh": float(int(target) % 10 + seed - 41),
                "objective_missing_origins": ["2023-01-01"],
            }
            for target in ("1405", "2152", "1153", "1693")
            for seed in (42, 43, 44)
        ]

    def test_station_first_with_null_and_pairing_guards(self):
        rows = self.rows()
        result = aggregate_matrix(rows)
        expected = sum((int(target) % 10 + 2) for target in ("1405", "2152", "1153", "1693")) / 4
        self.assertEqual(result["objective_mae_kwh"], expected)
        rows[0]["mae_kwh"] = None
        self.assertIsNone(aggregate_matrix(rows)["objective_mae_kwh"])
        rows[0]["objective_missing_origins"] = []
        with self.assertRaisesRegex(ValueError, "different target origins"):
            aggregate_matrix(rows)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            aggregate_matrix(self.rows() + [self.rows()[0]])

    @mock.patch("ev_search.execute.Replay")
    def test_dispatch_uses_all_twelve_fresh_calibration_runs(self, replay):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protocol = root / "protocol.json"
            origins = {
                target: ["2022-12-01T00:00:00+08:00"] for target in ("1405", "2152", "1153", "1693")
            }
            protocol.write_text(
                json.dumps({"status": "locked_owner_approved", "calibration_origins": origins})
            )
            sources = {
                str(seed): {"path": f"seed{seed}.pt", "sha256": str(seed) * 32}
                for seed in (42, 43, 44)
            }
            evaluator = FixedMatrixEvaluator(
                object(),
                protocol,
                {
                    "phase": "calibration",
                    "frozen_lambda": True,
                    "initial_training": {"seed": 0},
                    "online_training": {"seed": 0},
                },
                sources,
                root,
                device="cpu",
            )
            calls = []

            def fake_execute(inputs, target, path, sha256, config, output, **kwargs):
                calls.append(
                    (
                        target,
                        config["initial_training"]["seed"],
                        config["initial_lambda"],
                        config["objective_origins"],
                    )
                )
                output.mkdir()
                (output / "run.json").write_text("{}")
                return {
                    "mae_kwh": 2.0,
                    "objective_scored_days": 1,
                    "objective_missing_origins": [],
                    "invocation_wall_seconds": 1.0,
                }

            with mock.patch("ev_search.execute.execute", side_effect=fake_execute):
                result = evaluator(0.37251, "bo_ei", 0)
            self.assertEqual(replay.call_count, 4)
            self.assertEqual(len(calls), 12)
            self.assertEqual(result["objective_mae_kwh"], 2.0)
            self.assertEqual(len(result["runs"]), 12)
            self.assertTrue(all(call[2] == 0.37251 for call in calls))
            with self.assertRaises(FileExistsError):
                evaluator(0.37251, "bo_ei", 0)


if __name__ == "__main__":
    unittest.main()
