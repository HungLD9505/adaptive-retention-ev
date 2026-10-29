"""Tests for frozen omitted-ID accounting and fail-closed input strata."""

from __future__ import annotations

import unittest
from copy import deepcopy

from tools.hung_final_omitted_disposition_v1 import audit, classify_entity


def fixture() -> dict[int, dict]:
    return {
        budget: {
            "status": "ready",
            "initialization": "target_initial_adaptation",
            "initial_trainable": 2,
            "scheduled_forecasts": 90,
            "scale": {"fit_sha256": "a" * 64, "energy_scale": 1.0},
        }
        for budget in (7, 14, 28)
    }


class FinalOmittedDispositionTests(unittest.TestCase):
    def test_real_frozen_partition(self) -> None:
        result = audit()
        self.assertEqual(result["omitted_count"], 370)
        self.assertEqual(
            result["disposition_counts"],
            {
                "POSITIVE_PREFIX_ALL_BUDGETS": 326,
                "UNDEFINED_SCALE_ANY_BUDGET": 33,
                "ZERO_PREFIX_ANY_BUDGET_READY": 11,
            },
        )
        self.assertEqual(len({row["entity_id"] for row in result["records"]}), 370)
        mixed = next(row for row in result["records"] if row["entity_id"] == "1004")
        self.assertEqual(mixed["disposition"], "ZERO_PREFIX_ANY_BUDGET_READY")
        self.assertEqual([budget["initial_trainable"] for budget in mixed["budgets"]], [0, 0, 11])

    def test_mixed_zero_prefix_is_preserved(self) -> None:
        entities = fixture()
        for budget in (7, 14):
            entities[budget]["initial_trainable"] = 0
            entities[budget]["initialization"] = "source_checkpoint_only"
        disposition, budgets = classify_entity(entities)
        self.assertEqual(disposition, "ZERO_PREFIX_ANY_BUDGET_READY")
        self.assertEqual([row["initial_trainable"] for row in budgets], [0, 0, 2])

    def test_undefined_scale_requires_blocked_coverage(self) -> None:
        entities = fixture()
        entities[7] = {
            "status": "undefined_scale",
            "initialization": "blocked_undefined_scale",
            "initial_trainable": 0,
            "scheduled_forecasts": 0,
            "scale": None,
        }
        self.assertEqual(classify_entity(entities)[0], "UNDEFINED_SCALE_ANY_BUDGET")
        bad = deepcopy(entities)
        bad[7]["scheduled_forecasts"] = 1
        with self.assertRaisesRegex(ValueError, "blocked coverage"):
            classify_entity(bad)

    def test_incorrect_ready_mode_is_rejected(self) -> None:
        entities = fixture()
        entities[14]["initial_trainable"] = 0
        with self.assertRaisesRegex(ValueError, "initialization contract"):
            classify_entity(entities)


if __name__ == "__main__":
    unittest.main()
