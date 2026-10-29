"""Offline checks for final-role cohort gap accounting."""

import unittest

from tools.hung_final_scope_gap import BUDGETS, scope_gap


def fixture() -> tuple[dict, dict[int, dict]]:
    jobs = [
        {
            "job_id": f"job-{index}",
            "dataset_id": "urbanev",
            "city_id": "SZH",
            "entity_id": str(1 + index % 3),
        }
        for index in range(360)
    ]
    entities = {
        budget: {
            str(entity_id): {
                "identity": ["urbanev", "SZH", str(entity_id)],
                "status": "ready",
                "initial_trainable": 2,
                "scheduled_forecasts": 90,
            }
            for entity_id in range(1, 374)
        }
        for budget in BUDGETS
    }
    return {"jobs": jobs}, entities


class FinalScopeGapTests(unittest.TestCase):
    def test_gap_preserves_undefined_scale_and_zero_initialization(self) -> None:
        jobset, entities = fixture()
        entities[7]["4"]["status"] = "undefined_scale"
        entities[7]["4"]["initial_trainable"] = 0
        rows, summary = scope_gap(jobset, entities)
        self.assertEqual(len(rows), 370)
        self.assertEqual(summary["locked_entity_ids"], ["1", "2", "3"])
        self.assertEqual(summary["undefined_scale_any_budget"], 1)
        self.assertEqual(summary["ready_all_budgets"], 369)
        self.assertEqual(summary["zero_initial_trainable_by_budget"]["7"], 1)
        self.assertEqual(rows[0]["entity_id"], "4")

    def test_unmatched_budget_or_duplicate_job_fails(self) -> None:
        jobset, entities = fixture()
        del entities[14]["373"]
        with self.assertRaisesRegex(ValueError, "cohort"):
            scope_gap(jobset, entities)
        jobset, entities = fixture()
        jobset["jobs"][1]["job_id"] = jobset["jobs"][0]["job_id"]
        with self.assertRaisesRegex(ValueError, "distinct frozen jobs"):
            scope_gap(jobset, entities)


if __name__ == "__main__":
    unittest.main()
