"""Check expanded-cohort opt-in while preserving ordinary runner restrictions."""

import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from ev_runner.continuous_run import validate_study
from ev_runner.run import execute
from tools.issue99_study_support import PreparedInputs


class ExpandedDevelopmentTests(unittest.TestCase):
    def test_expanded_targets_require_explicit_approval(self):
        config = json.loads(
            Path("docs/reports/issue99-study-20261110/controller-lock.json").read_text()
        )["study_template"]
        config = copy.deepcopy(config)
        config["targets"] = ["fixture"]
        config.update(phase="pilot", objective_origins=[], protocol_sha256=None)
        with self.assertRaisesRegex(ValueError, "cohort"):
            validate_study(config)
        validate_study(config, approved_targets=("fixture",))
        with self.assertRaisesRegex(ValueError, "cohort"):
            validate_study(config, approved_targets=("fixture", "fixture"))

    def test_default_runner_still_rejects_cpu(self):
        with self.assertRaisesRegex(ValueError, "CUDA"):
            execute(None, "fixture", Path("unused"), "unused", {}, Path("unused"), device="cpu")

    def test_cpu_opt_in_rejects_final_and_other_budgets(self):
        for role, budget in (("final", 14), ("development", 7)):
            inputs = SimpleNamespace(target_role=role, config={"history_days": budget})
            with self.assertRaisesRegex(ValueError, "CUDA"):
                execute(
                    inputs,
                    "fixture",
                    Path("unused"),
                    "unused",
                    {"method": {"name": "adaptive"}},
                    Path("unused"),
                    device="cpu",
                    cpu_development_diagnostic=True,
                )

    def test_cache_rejects_ambiguous_cohort(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            PreparedInputs(Path("unused"), "unused", targets=("same", "same"))


if __name__ == "__main__":
    unittest.main()
