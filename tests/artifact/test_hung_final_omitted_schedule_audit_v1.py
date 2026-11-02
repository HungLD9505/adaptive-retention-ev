"""External-artifact checks; intentionally excluded from offline discovery."""

from __future__ import annotations

import unittest

from tools.hung_final_omitted_schedule_audit_v1 import audit


def fixture() -> tuple[list[dict], dict, set[str]]:
    origins = {"2022-12-01T00:00:00+08:00", "2022-12-02T00:00:00+08:00"}
    identity = ["urbanev", "SZH", "1003"]
    rows = [
        {"identity": identity, "role": "final", "origin": origin, "status": status}
        for origin, status in zip(
            sorted(origins), ("created", "skipped_all_missing_history"), strict=True
        )
    ]
    entity = {
        "identity": identity,
        "status": "ready",
        "requested_forecasts": 2,
        "scheduled_forecasts": 1,
        "skipped_all_missing_history": 1,
        "skipped_undefined_scale": 0,
    }
    return rows, entity, origins


class FinalOmittedScheduleAuditTests(unittest.TestCase):
    def test_real_frozen_schedule(self) -> None:
        result = audit()
        self.assertEqual(len(result["budgets"]), 3)
        for row in result["budgets"]:
            self.assertEqual(row["final_role_entities"], 373)
            self.assertEqual(row["daily_origins_per_entity"], 90)
            self.assertEqual(row["invalid_or_missing_entity_schedules"], 0)
