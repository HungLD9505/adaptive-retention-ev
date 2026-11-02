"""Regressions for frozen Final forecast-input and schedule binding."""

from __future__ import annotations

import unittest
from copy import deepcopy
from datetime import datetime, timedelta

from tools.hung_final_forecast_input_audit_v1 import validate_forecast


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
    def test_valid_forecast_binding(self) -> None:
        row, entity = fixture()
        self.assertEqual(
            validate_forecast(row, entity, run_id="urbanev-SZH-7d"), ("1003", row["origin"])
        )

    def test_wrong_scale_rejected(self) -> None:
        row, entity = fixture()
        row = deepcopy(row)
        row["scale_id"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "binding differs"):
            validate_forecast(row, entity, run_id="urbanev-SZH-7d")

    def test_wrong_hourly_clock_rejected(self) -> None:
        row, entity = fixture()
        row = deepcopy(row)
        row["future_labels"][23] = row["future_labels"][22]
        with self.assertRaisesRegex(ValueError, "hourly clock differs"):
            validate_forecast(row, entity, run_id="urbanev-SZH-7d")

    def test_label_payload_rejected(self) -> None:
        row, entity = fixture()
        row["y_kwh"] = [0.0] * 24
        with self.assertRaisesRegex(ValueError, "binding differs"):
            validate_forecast(row, entity, run_id="urbanev-SZH-7d")


if __name__ == "__main__":
    unittest.main()
