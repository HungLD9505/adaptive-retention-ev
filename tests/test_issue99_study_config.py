"""Protocol-gate and real-lambda validation fixtures for the new study CLI."""

import copy
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import ev_runner.continuous_run as continuous_run
import ev_runner.run as discrete_run
from ev_runner.continuous_run import objective_summary, validate_origin_boundary, validate_study


def pilot_config():
    training = {
        "seed": 42,
        "epochs": 1,
        "batch_size": 1,
        "learning_rate": 0.001,
        "epsilon": 0.001,
        "head_width": 64,
    }
    return {
        "schema": "issue99-study-v1",
        "phase": "pilot",
        "targets": ["1405", "2152", "1153", "1693"],
        "initial_training": training,
        "online_training": copy.deepcopy(training),
        "window_rule": {
            "older_count": 1,
            "newer_count": 1,
            "upper_bound": 2.0,
            "meta_step_size": 0.01,
            "epsilon": 0.001,
        },
        "initial_lambda": 0.37251,
        "cadence": 1,
        "frozen_lambda": True,
        "replay_days": 90,
        "protocol_sha256": None,
        "objective_origins": [],
    }


class StudyConfigTests(unittest.TestCase):
    def test_verified_package_commit_without_git(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            commit = "c" * 40
            (root / ".issue99-code-commit").write_text(commit)
            with patch.object(continuous_run, "ROOT", root):
                self.assertEqual(continuous_run.code_identity(), {"commit": commit, "files": {}})
            (root / ".issue99-code-commit").write_text("malformed")
            with patch.object(continuous_run, "ROOT", root):
                with self.assertRaises(ValueError):
                    continuous_run.code_identity()

    def test_discrete_uses_verified_package_commit_without_git(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            commit = "a" * 40
            (root / ".issue99-code-commit").write_text(commit)
            with patch.object(discrete_run, "ROOT", root):
                self.assertEqual(
                    discrete_run.runtime_code(),
                    {"commit": commit, "dirty": False, "files": {}},
                )

    def test_real_fixed_lambda_is_accepted(self):
        initial, online, rule = validate_study(pilot_config())
        self.assertEqual(initial.seed, online.seed)
        self.assertEqual(rule.upper_bound, 2.0)

    def test_pilot_cannot_score_origin(self):
        config = pilot_config()
        config["objective_origins"] = ["2022-12-01T00:00:00+08:00"]
        with self.assertRaises(ValueError):
            validate_study(config)

    def test_scored_phase_requires_protocol(self):
        config = pilot_config()
        config["phase"] = "calibration"
        with self.assertRaises(ValueError):
            validate_study(config)

    def test_source_seed_and_lambda_bounds(self):
        config = pilot_config()
        config["initial_training"]["seed"] = 7
        with self.assertRaises(ValueError):
            validate_study(config)
        config = pilot_config()
        config["initial_lambda"] = 2.1
        with self.assertRaises(ValueError):
            validate_study(config)

    def test_protocol_requires_calibration_before_evaluation_with_embargo(self):
        start = datetime(2022, 12, 1, tzinfo=timezone.utc)
        stop = start + timedelta(days=90)

        def day(index):
            return (start + timedelta(days=index)).isoformat()

        protocol = {
            "embargo_days": 1,
            "calibration_origins": {"1405": [day(0), day(1)]},
            "evaluation_origins": {"1405": [day(4), day(5)]},
        }
        self.assertEqual(validate_origin_boundary(protocol, "1405", start, stop), [day(0), day(1)])
        protocol["evaluation_origins"]["1405"] = [day(1), day(5)]
        with self.assertRaises(ValueError):
            validate_origin_boundary(protocol, "1405", start, stop)
        protocol["evaluation_origins"]["1405"] = [day(91)]
        with self.assertRaises(ValueError):
            validate_origin_boundary(protocol, "1405", start, stop)

    def test_objective_is_null_below_registered_coverage(self):
        rows = [{"origin": "day-1", "mae_kwh": 3.0, "mse_kwh2": 10.0}]
        partial = objective_summary(rows, ["day-1", "day-2"], 2)
        self.assertIsNone(partial["mae_kwh"])
        self.assertEqual(partial["objective_missing_origins"], ["day-2"])
        complete = objective_summary(rows, ["day-1", "day-2"], 1)
        self.assertEqual(complete["mae_kwh"], 3.0)
        with self.assertRaises(ValueError):
            objective_summary(rows * 2, ["day-1"], 1)


if __name__ == "__main__":
    unittest.main()
