"""History opt-in and missing-history baseline fallback regression checks."""

import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ev_runner.continuous_run import execute
from tools.issue99_simple_baselines import daily_prediction


class HistoryReviewTests(unittest.TestCase):
    def test_daily_missing_values_use_observed_mean(self):
        record = {"x_hist": [[0.0] * 7 for _ in range(24)]}
        record["x_hist"][0] = [2.0, 0, 0, 0, 0, 0, 1]
        record["x_hist"][1] = [4.0, 0, 0, 0, 0, 0, 1]
        prediction = daily_prediction(record)
        self.assertEqual(prediction[:3], [2, 4, 3])
        with self.assertRaisesRegex(ValueError, "No known"):
            daily_prediction({"x_hist": [[0.0] * 7 for _ in range(24)]})

    def test_expanded_history_is_explicit_and_default_remains_fourteen(self):
        config = copy.deepcopy(
            json.loads(
                Path("docs/reports/issue99-study-20261110/controller-lock.json").read_text()
            )["study_template"]
        )
        config.update(
            phase="pilot",
            protocol_sha256=None,
            objective_origins=[],
            initial_lambda=0,
            frozen_lambda=True,
        )
        inputs = SimpleNamespace(
            config={"history_days": 7}, target_role="development", root=Path("unused-input")
        )
        kwargs = dict(
            inputs=inputs,
            entity_id="1405",
            source_path=Path("unused"),
            source_sha256="unused",
            config=config,
            output=Path("unused-output"),
            device="cpu",
        )
        with self.assertRaisesRegex(ValueError, "history budget"):
            execute(**kwargs)
        with patch(
            "ev_runner.continuous_run.load_checkpoint", side_effect=RuntimeError("checkpoint gate")
        ):
            with self.assertRaisesRegex(RuntimeError, "checkpoint gate"):
                execute(**kwargs, approved_history_days=(7, 14, 28))


if __name__ == "__main__":
    unittest.main()
