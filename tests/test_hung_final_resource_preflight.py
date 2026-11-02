"""Offline guards for Development-based Final resource scenarios."""

from __future__ import annotations

import unittest

from tools.hung_final_resource_preflight import (
    CONFIDENCE_CONFIGS,
    SEEDED_METHODS,
    percentile,
    scenarios,
)


def _development_records() -> list[dict]:
    records = []
    for budget, entities in ((7, 6), (14, 8), (28, 9)):
        for entity in range(entities):
            variants = [
                ("confidence", config, seed)
                for config in CONFIDENCE_CONFIGS
                for seed in (7, 11, 19)
            ]
            variants += [
                (method, "main", seed) for method in SEEDED_METHODS for seed in (7, 11, 19)
            ]
            variants.append(("seasonal_naive", "main", 7))
            for method, config, seed in variants:
                records.append(
                    {
                        "budget_days": budget,
                        "entity_id": str(entity),
                        "method": method,
                        "config_id": config,
                        "seed": seed,
                        "stage_wall_seconds": 10,
                        "stage_output_bytes_before_measurement": 20,
                        "zip_member_compressed_bytes": 5,
                    }
                )
    return records


class FinalResourceTests(unittest.TestCase):
    def test_nearest_rank_p95_observed_small_group(self) -> None:
        self.assertEqual(percentile([1, 2, 3, 4, 5, 6], 0.95), 6)

    def test_exact_method_coverage_required_for_scenarios(self) -> None:
        records = _development_records()
        rows, detail = scenarios(records)
        self.assertEqual([row["candidate_physical_jobs"] for row in rows], [360, 1200, 3600])
        self.assertEqual(
            [row["observed_entity_groups"] for row in detail["budget_strata"]], [6, 8, 9]
        )
        with self.assertRaisesRegex(ValueError, "coverage differs"):
            scenarios(records[:-1])


if __name__ == "__main__":
    unittest.main()
