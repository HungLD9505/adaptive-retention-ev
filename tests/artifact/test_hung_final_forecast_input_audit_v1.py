"""External-artifact checks; intentionally excluded from offline discovery."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from tools.hung_final_forecast_input_audit_v1 import audit


def fixture() -> tuple[dict, dict]:
    origin = datetime.fromisoformat("2022-12-01T00:00:00+08:00")
    entity = {
        "identity": ["urbanev", "SZH", "1003"],
        "status": "ready",
        "scale": {"fit_sha256": "a" * 64, "energy_scale": 2.0},
    }
    row = {
        "role": "final",
        "identity": entity["identity"],
        "origin": origin.isoformat(),
        "input_run_id": "urbanev-SZH-7d",
        "schema_id": "ev-input-v1",
        "clock_mode": "offset-aware-local",
        "scale_id": entity["scale"]["fit_sha256"],
        "energy_scale": entity["scale"]["energy_scale"],
        "history_labels": [
            (origin - timedelta(hours=24 - index)).isoformat() for index in range(24)
        ],
        "future_labels": [(origin + timedelta(hours=index)).isoformat() for index in range(24)],
        "x_hist": [[0.0] * 7 for _ in range(24)],
        "c_future": [[0.0] * 5 for _ in range(24)],
    }
    return row, entity


class FinalForecastInputAuditTests(unittest.TestCase):
    def test_real_pinned_forecasts_match_created_schedule(self) -> None:
        result = audit()
        self.assertEqual(
            [row["final_created_and_forecast_inputs"] for row in result["budgets"]],
            [25978, 26022, 26146],
        )
        self.assertEqual(
            [row["missing_or_extra_forecast_inputs"] for row in result["budgets"]],
            [0, 0, 0],
        )
