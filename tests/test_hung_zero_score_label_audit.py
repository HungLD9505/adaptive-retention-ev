"""Distinguish missing frozen labels from genuinely late complete horizons."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from ev_inputs.windows import LabelRecord
from tools.hung_zero_score_label_audit import classify_label


class ZeroScoreLabelClassificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.origin = datetime(2022, 12, 1, tzinfo=timezone(timedelta(hours=8)))
        self.timestamps = tuple(self.origin + timedelta(hours=hour) for hour in range(24))
        self.available = tuple(timestamp + timedelta(hours=1) for timestamp in self.timestamps)
        self.replay_end = self.origin + timedelta(days=1)

    def record(
        self,
        *,
        energy: tuple[float | None, ...] | None = None,
        valid: tuple[bool, ...] | None = None,
        available: tuple[datetime | None, ...] | None = None,
    ) -> LabelRecord:
        return LabelRecord(
            ("urbanev", "SZH", "1050"),
            self.origin,
            "offset-aware-local",
            self.timestamps,
            energy if energy is not None else (1.0,) * 24,
            valid if valid is not None else (True,) * 24,
            available if available is not None else self.available,
        )

    def test_frozen_missing_bin_blocks_complete_horizon(self) -> None:
        energy = (None,) + (1.0,) * 23
        valid = (False,) + (True,) * 23
        result = classify_label(self.record(energy=energy, valid=valid), self.replay_end)
        self.assertEqual(result["classification"], "incomplete_frozen_input")
        self.assertEqual(result["invalid_file_bins"], 1)
        self.assertEqual(result["missing_energy_bins"], 1)
        self.assertEqual(result["available_after_replay_end_bins"], 0)

    def test_complete_but_late_is_separate(self) -> None:
        available = self.available[:-1] + (self.replay_end + timedelta(hours=1),)
        result = classify_label(self.record(available=available), self.replay_end)
        self.assertEqual(result["classification"], "complete_but_late")
        self.assertEqual(result["available_after_replay_end_bins"], 1)

    def test_complete_horizon_is_ready(self) -> None:
        result = classify_label(self.record(), self.replay_end)
        self.assertEqual(result["classification"], "complete_by_replay_end")


if __name__ == "__main__":
    unittest.main()
