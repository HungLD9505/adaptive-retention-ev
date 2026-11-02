"""External-artifact checks; intentionally excluded from offline discovery."""

from __future__ import annotations

import unittest

from tools.hung_final_omitted_disposition_v1 import audit


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
