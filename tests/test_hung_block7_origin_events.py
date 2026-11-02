"""Offline checks for recorded Block7/Main origin eligibility tags."""

from __future__ import annotations

import copy
import unittest

from tools.hung_block7_origin_events import event_schedule, schedule_sha256


def fixture() -> dict:
    origins = [f"origin-{index:03d}" for index in range(90)]
    issued, skipped = origins[:40], origins[40:]
    return {
        "coverage": {
            "requested": 90,
            "created": 40,
            "scored": 20,
            "skipped_all_missing_history": 50,
            "skipped_undefined_scale": 0,
            "unscored_created": 20,
        },
        "event_evidence": {
            "events": [
                *(f"forecast:{origin}" for origin in issued),
                *(f"skip:{origin}" for origin in skipped),
                *(f"unscored:{origin}" for origin in origins),
                *(f"score:{origin}" for origin in issued[:20]),
                *(f"update:{origin}" for origin in issued[:20]),
            ]
        },
    }


class OriginEventTests(unittest.TestCase):
    def test_accepts_complete_schedule_and_stable_digest(self) -> None:
        left = event_schedule(fixture())
        right = event_schedule(copy.deepcopy(fixture()))
        self.assertEqual(left, right)
        self.assertEqual(schedule_sha256(left), schedule_sha256(right))
        self.assertEqual(len(left["forecast"]), 40)

    def test_rejects_missing_issued_origin(self) -> None:
        manifest = fixture()
        manifest["event_evidence"]["events"].remove("forecast:origin-000")
        with self.assertRaisesRegex(ValueError, "event/coverage disagreement"):
            event_schedule(manifest)

    def test_rejects_duplicate_origin(self) -> None:
        manifest = fixture()
        events = manifest["event_evidence"]["events"]
        events[events.index("skip:origin-040")] = "skip:origin-041"
        with self.assertRaisesRegex(ValueError, "event/coverage disagreement"):
            event_schedule(manifest)

    def test_rejects_unmatched_label_update(self) -> None:
        manifest = fixture()
        events = manifest["event_evidence"]["events"]
        events[events.index("update:origin-000")] = "update:origin-020"
        with self.assertRaisesRegex(ValueError, "event/coverage disagreement"):
            event_schedule(manifest)


if __name__ == "__main__":
    unittest.main()
