"""Regression: the CUDA CLI must accept the opt-in persistence field."""

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from ev_runner.run import execute


class RunnerPersistenceConfigTests(unittest.TestCase):
    def test_latest_reaches_cohort_gate_without_gpu_or_training(self):
        config = json.loads(Path("configs/issue21/development-smoke.json").read_text())
        config["state_retention"] = "latest"
        config["development_entities"] = []
        with patch("ev_runner.run.torch.cuda.is_available", return_value=True):
            with self.assertRaisesRegex(ValueError, "declared Development"):
                execute(
                    None,
                    "fixture",
                    Path("unused"),
                    "unused",
                    config,
                    Path("unused-output"),
                    device="cuda",
                )
        self.assertFalse(Path("unused-output").exists())

    def test_invalid_retention_rejected_before_training(self):
        config = json.loads(Path("configs/issue21/development-smoke.json").read_text())
        config["state_retention"] = "typo"
        with patch("ev_runner.run.torch.cuda.is_available", return_value=True):
            with self.assertRaisesRegex(ValueError, "state-retention"):
                execute(
                    None,
                    "fixture",
                    Path("unused"),
                    "unused",
                    config,
                    Path("unused-output"),
                    device="cuda",
                )


if __name__ == "__main__":
    unittest.main()
