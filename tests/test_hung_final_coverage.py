"""Synthetic physical seed coverage without reading Final inputs."""

import unittest
from copy import deepcopy

from experiments.hung_sprint2.final_coverage import _coverage_status


def _matrix() -> tuple[dict, list[dict], list[dict]]:
    coverage = {
        "selected_entities": [{"dataset_id": "urbanev", "city_id": "SZH", "entity_id": "e1"}],
        "budgets": [7, 14, 28],
        "seeds": [7, 11, 19],
        "variants": ["seasonal_naive", "target_only"],
        "variant_categories": {
            "seasonal_naive": ["baseline:seasonal_naive"],
            "target_only": ["baseline:target_only"],
        },
        "variant_seed_policy": {
            "seasonal_naive": {"deterministic_representative_seed": 7, "alias_seeds": [11, 19]},
            "target_only": "all_seeds",
        },
        "replay_origins": 90,
        "expected_jobs": 12,
        "missing_cells": [],
        "declared_shortfalls": ["Synthetic fixture omits other required methods and cities"],
    }
    jobs = [
        {
            "dataset_id": "urbanev",
            "city_id": "SZH",
            "entity_id": "e1",
            "budget_days": budget,
            "seed": seed,
            "variant": variant,
            "method": variant,
        }
        for budget in (7, 14, 28)
        for variant in ("seasonal_naive", "target_only")
        for seed in ((7,) if variant == "seasonal_naive" else (7, 11, 19))
    ]
    plans = [{"replay": {}, "target_init": None} for _ in jobs]
    return coverage, jobs, plans


class FinalCoverageTests(unittest.TestCase):
    def test_deterministic_alias_counts_one_physical_job_per_budget(self) -> None:
        coverage, jobs, plans = _matrix()
        self.assertEqual(_coverage_status(coverage, jobs, plans), "incomplete")

    def test_missing_stochastic_seed_requires_exact_cell_record(self) -> None:
        coverage, jobs, plans = _matrix()
        jobs.pop()
        plans.pop()
        with self.assertRaisesRegex(ValueError, "missing-cell ledger"):
            _coverage_status(coverage, jobs, plans)
        coverage["missing_cells"] = [
            {
                "dataset_id": "urbanev",
                "city_id": "SZH",
                "entity_id": "e1",
                "budget_days": 28,
                "seed": 19,
                "variant": "target_only",
                "reason": "Synthetic missing seed",
            }
        ]
        self.assertEqual(_coverage_status(coverage, jobs, plans), "incomplete")

    def test_seasonal_alias_cannot_hide_unrelated_variant(self) -> None:
        coverage, jobs, plans = _matrix()
        coverage = deepcopy(coverage)
        coverage["variant_seed_policy"]["target_only"] = {
            "deterministic_representative_seed": 7,
            "alias_seeds": [11, 19],
        }
        with self.assertRaisesRegex(ValueError, "Invalid deterministic seed aliases"):
            _coverage_status(coverage, jobs, plans)
