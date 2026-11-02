"""Regressions for frozen Final daily schedule coverage."""

from __future__ import annotations

import unittest
from copy import deepcopy

from tools.hung_final_omitted_schedule_audit_v1 import validate_entity_schedule


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
    def test_valid_coverage(self) -> None:
        self.assertEqual(validate_entity_schedule(*fixture())["created"], 1)

    def test_duplicate_origin_rejected(self) -> None:
        rows, entity, origins = fixture()
        rows[1]["origin"] = rows[0]["origin"]
        with self.assertRaisesRegex(ValueError, "origin set"):
            validate_entity_schedule(rows, entity, origins)

    def test_status_count_mismatch_rejected(self) -> None:
        rows, entity, origins = fixture()
        rows = deepcopy(rows)
        rows[1]["status"] = "created"
        with self.assertRaisesRegex(ValueError, "coverage differs"):
            validate_entity_schedule(rows, entity, origins)

    def test_undefined_scale_must_be_blocked(self) -> None:
        rows, entity, origins = fixture()
        entity["status"] = "undefined_scale"
        entity["scheduled_forecasts"] = 0
        entity["skipped_all_missing_history"] = 0
        entity["skipped_undefined_scale"] = 2
        rows[0]["status"] = "skipped_undefined_scale"
        rows[1]["status"] = "skipped_undefined_scale"
        self.assertEqual(
            validate_entity_schedule(rows, entity, origins)["skipped_undefined_scale"], 2
        )
        rows[0]["status"] = "created"
        with self.assertRaises(ValueError):
            validate_entity_schedule(rows, entity, origins)


if __name__ == "__main__":
    unittest.main()
