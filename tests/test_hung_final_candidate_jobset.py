"""Check the published Final candidate's physical coverage and unresolved fields."""

import json
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "docs/reports/hung-final-candidate-jobset-20261029-v1"


def load(name):
    return json.loads((PACKET / name).read_text(encoding="utf-8"))


class CandidatePacketTests(unittest.TestCase):
    def test_selected_matrix_has_exact_physical_cells(self):
        jobs = load("candidate_jobset.json")["jobs"]
        coverage = load("candidate_coverage.json")
        identities = [job["job_id"] for job in jobs]
        self.assertEqual(identities, sorted(set(identities)))
        self.assertEqual(len(jobs), 360)
        self.assertEqual(coverage["expected_jobs"], len(jobs))
        self.assertEqual(coverage["missing_cells"], [])
        self.assertEqual(
            {row["entity_id"] for row in coverage["selected_entities"]},
            {"2118", "2579", "2534"},
        )
        cells = Counter((row["entity_id"], row["budget_days"]) for row in jobs)
        self.assertEqual(set(cells.values()), {40})
        self.assertEqual(
            set(cells),
            {(entity, budget) for entity in ("2118", "2579", "2534") for budget in (7, 14, 28)},
        )
        for (entity, budget), _ in cells.items():
            cell = [
                row for row in jobs if (row["entity_id"], row["budget_days"]) == (entity, budget)
            ]
            seeds = Counter(row["seed"] for row in cell)
            self.assertEqual(seeds, {7: 14, 11: 13, 19: 13})
            self.assertEqual(
                [row["seed"] for row in cell if row["variant"] == "seasonal_naive"],
                [7],
            )
        self.assertEqual(
            coverage["variant_seed_policy"]["seasonal_naive"],
            {"deterministic_representative_seed": 7, "alias_seeds": [11, 19]},
        )

    def test_plan_matches_jobs_and_drift_is_explicitly_unresolved(self):
        jobs = load("candidate_jobset.json")["jobs"]
        plan = load("candidate_execution_plan.json")["jobs"]
        missing = load("missing_stage_args.json")
        self.assertEqual([row["job_id"] for row in plan], [row["job_id"] for row in jobs])
        unresolved = {row["job_id"] for row in missing}
        self.assertEqual(len(unresolved), 27)
        self.assertEqual(unresolved, {row["job_id"] for row in jobs if row["variant"] == "drift"})
        self.assertTrue(
            all(
                row["fields"] == ["replay.drift_reference_mean", "replay.drift_reference_scale"]
                for row in missing
            )
        )
        for row in plan:
            if row["job_id"] in unresolved:
                self.assertIsNone(row["replay"]["drift_reference_mean"])
                self.assertIsNone(row["replay"]["drift_reference_scale"])
        self.assertTrue(all(row["target_checkpoint_sha256"] is None for row in jobs))
        self.assertTrue(all(not (ROOT / row["input_run"]).exists() for row in jobs))


if __name__ == "__main__":
    unittest.main()
