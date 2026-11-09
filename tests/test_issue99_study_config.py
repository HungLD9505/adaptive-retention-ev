"""Protocol-gate and real-lambda validation fixtures for the new study CLI."""

import copy
import unittest

from ev_runner.continuous_run import validate_study


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


if __name__ == "__main__":
    unittest.main()
