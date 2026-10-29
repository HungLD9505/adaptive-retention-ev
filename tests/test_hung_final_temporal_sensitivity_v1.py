"""Guards for the post hoc Final temporal uncertainty calculation."""

from __future__ import annotations

import random
import unittest
from datetime import datetime, timedelta, timezone

from tools.hung_final_temporal_sensitivity_v1 import block_sample_mean, paired_series


class TemporalSensitivityTests(unittest.TestCase):
    def test_constant_series_remains_constant_under_circular_blocks(self) -> None:
        self.assertEqual(block_sample_mean([3.0] * 89, 7, random.Random(7)), 3.0)
        self.assertEqual(block_sample_mean([3.0] * 89, 14, random.Random(7)), 3.0)

    def test_block_draw_is_reproducible_and_rejects_invalid_length(self) -> None:
        values = list(range(90))
        self.assertEqual(
            block_sample_mean(values, 14, random.Random(19)),
            block_sample_mean(values, 14, random.Random(19)),
        )
        with self.assertRaisesRegex(ValueError, "Invalid temporal block length"):
            block_sample_mean(values, 91, random.Random(19))

    def panel(self) -> list[dict]:
        origin = datetime(2022, 12, 1, tzinfo=timezone.utc)
        dates = [(origin + timedelta(days=day)).isoformat() for day in range(89)]
        return [
            {
                "variant": variant,
                "budget_days": 7,
                "entity_id": entity,
                "seed": seed,
                "days": {
                    date: {
                        "absolute": 48.0 if variant == "target_only" else 24.0,
                        "label_sha256": "a" * 64,
                    }
                    for date in dates
                },
            }
            for variant in ("main", "target_only")
            for entity in ("2118", "2534", "2579")
            for seed in (7, 11, 19)
        ]

    def test_paired_daily_gain_and_label_identity(self) -> None:
        rows = self.panel()
        result = paired_series(rows, 7)
        self.assertEqual(set(result), {"2118", "2534", "2579"})
        self.assertTrue(all(value == 1.0 for days in result.values() for value in days))
        rows[0]["days"][next(iter(rows[0]["days"]))]["label_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "Paired label hash differs"):
            paired_series(rows, 7)
