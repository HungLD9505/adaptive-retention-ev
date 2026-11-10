"""The pilot safety screen uses real trajectories, not shadow candidates."""

import json
import unittest
from pathlib import Path

from ev_runner.continuous_run import validate_controller_protocol, validate_study
from tools.issue99_persistent_experiment import METHODS, config_for
from tools.issue99_persistent_verify import pilot_screen


class PilotScreenTest(unittest.TestCase):
    def test_packaged_protocol_loads_and_binds_every_comparison_arm(self) -> None:
        path = Path(__file__).resolve().parents[1] / "configs/issue99-persistent-protocol-v1.json"
        protocol = json.loads(path.read_text(encoding="utf-8"))
        for method in METHODS:
            with self.subTest(method=method):
                config = config_for(protocol, "a" * 64, method, 42, "1405", "calibration")
                validate_study(config)
                validate_controller_protocol(config, protocol)

    def test_rejected_shadow_harm_does_not_trigger_trajectory_stop(self) -> None:
        rows = [
            {
                "target": "1405",
                "seed": 42,
                "method": "fixed",
                "all_scored_origins": ["day-a", "day-b"],
                "all_scored_mae_kwh": 1.0,
                "persistent": None,
            },
            {
                "target": "1405",
                "seed": 42,
                "method": "persistent",
                "all_scored_origins": ["day-a", "day-b"],
                "all_scored_mae_kwh": 1.02,
                "persistent": {"paired_differences_kwh": [0.40], "acceptances": 0},
            },
        ]
        harm, maximum, passed = pilot_screen(rows, (("1405", 42),), 0.05)
        self.assertEqual(set(harm), {"1405-seed42"})
        self.assertAlmostEqual(harm["1405-seed42"], 0.02)
        self.assertAlmostEqual(maximum, 0.02)
        self.assertTrue(passed)

    def test_actual_trajectory_harm_stops_pilot(self) -> None:
        rows = [
            {
                "target": "1405",
                "seed": 42,
                "method": "fixed",
                "all_scored_origins": ["day-a"],
                "all_scored_mae_kwh": 1.0,
            },
            {
                "target": "1405",
                "seed": 42,
                "method": "persistent",
                "all_scored_origins": ["day-a"],
                "all_scored_mae_kwh": 1.06,
                "persistent": {"paired_differences_kwh": [-0.10]},
            },
        ]
        _, maximum, passed = pilot_screen(rows, (("1405", 42),), 0.05)
        self.assertAlmostEqual(maximum, 0.06)
        self.assertFalse(passed)


if __name__ == "__main__":
    unittest.main()
