"""Readiness selection uses only declared Development prefix metadata."""

import copy
import unittest
from types import SimpleNamespace

from tools.development_readiness import validate_cohort


class CohortTests(unittest.TestCase):
    def setUp(self):
        self.cohort = {
            "namespace": "urbanev-SZH",
            "methods": ["adaptive", "target_only"],
            "seeds": [42, 43, 44],
            "days": 90,
            "state_retention": "latest",
            "budgets": {
                str(b): {
                    "manifest_sha256": str(b),
                    "entities": [{"entity_id": "a", "initial_trainable": 0}],
                }
                for b in (7, 14, 28)
            },
        }
        self.inputs = {
            b: SimpleNamespace(
                source_hash="source",
                sha256=str(b),
                namespace=("urbanev", "SZH"),
                entities={
                    ("urbanev", "SZH", "a"): {
                        "role": "development",
                        "status": "ready",
                        "initial_trainable": 0,
                    }
                },
            )
            for b in (7, 14, 28)
        }

    def test_source_checkpoint_only_is_retained_without_future_filter(self):
        validate_cohort(self.inputs, self.cohort)

    def test_final_entity_is_rejected(self):
        self.inputs[7].entities[("urbanev", "SZH", "a")]["role"] = "final"
        with self.assertRaises(ValueError):
            validate_cohort(self.inputs, self.cohort)

    def test_changed_prefix_and_manifest_rejected(self):
        for key, value in [
            ("manifest_sha256", "different"),
            ("entities", [{"entity_id": "a", "initial_trainable": 1}]),
        ]:
            cohort = copy.deepcopy(self.cohort)
            cohort["budgets"]["7"][key] = value
            with self.assertRaises(ValueError):
                validate_cohort(self.inputs, cohort)

    def test_duplicate_entities_rejected(self):
        self.cohort["budgets"]["7"]["entities"] *= 2
        with self.assertRaises(ValueError):
            validate_cohort(self.inputs, self.cohort)


if __name__ == "__main__":
    unittest.main()
