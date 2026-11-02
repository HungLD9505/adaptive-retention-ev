"""External-artifact checks; intentionally excluded from offline discovery."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from tools.hung_final_prefix_inventory_v1 import audit


def fixture() -> tuple[dict, dict, dict, datetime]:
    origin = datetime.fromisoformat("2022-11-25T00:00:00+08:00")
    deployment = datetime.fromisoformat("2022-12-01T00:00:00+08:00")
    entity = {
        "identity": ["urbanev", "SZH", "1003"],
        "scale": {"fit_sha256": "scale-pin", "energy_scale": 7.0},
    }
    row = {
        "role": "final",
        "forecast": {
            "identity": entity["identity"],
            "input_run_id": "urbanev-SZH-7d",
            "scale_id": "scale-pin",
            "clock_mode": "offset-aware-local",
            "energy_scale": 7.0,
            "origin": origin.isoformat(),
            "history_labels": [
                (origin - timedelta(hours=24 - hour)).isoformat() for hour in range(24)
            ],
            "future_labels": [(origin + timedelta(hours=hour)).isoformat() for hour in range(24)],
            "x_hist": [[0.0] * 7 for _ in range(24)],
            "c_future": [[0.0] * 5 for _ in range(24)],
        },
        "y_kwh": [0.0] * 24,
        "y_scaled": [0.0] * 24,
    }
    return row, entity, {"run_id": "urbanev-SZH-7d"}, deployment


class FinalPrefixInventoryTests(unittest.TestCase):
    def test_pinned_real_inventory(self) -> None:
        result = audit()
        self.assertEqual(result["all_budget_qualifying_omitted_ids"], 326)
        self.assertEqual(
            [item["final_prefix_rows"] for item in result["budgets"]], [1974, 4275, 8746]
        )
        self.assertEqual(
            [item["invalid_or_late_prefix_rows"] for item in result["budgets"]], [0, 0, 0]
        )
