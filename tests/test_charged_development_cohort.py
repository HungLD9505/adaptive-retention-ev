"""Outcome-blind, deterministic supplementary cohort selection checks."""

import copy
import unittest

from tools.charged_development_cohort import choose_entities


class ChargedCohortTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {
                "identity": ["charged", "AMS", str(i)],
                "role": "development",
                "status": "ready",
                "initial_trainable": 6,
            }
            for i in range(12)
        ]

    def test_three_distinct_ids_even_with_identical_prefix_counts(self):
        first = choose_entities(self.rows, ("charged", "AMS"), "manifest", 7)
        second = choose_entities(list(reversed(self.rows)), ("charged", "AMS"), "manifest", 7)
        self.assertEqual(first, second)
        self.assertEqual(len(first["entities"]), 3)
        self.assertEqual(len({r["entity_id"] for r in first["entities"]}), 3)
        self.assertEqual(first["positive_prefix_population"], 12)

    def test_source_only_retained_and_final_excluded_before_prefix_read(self):
        self.rows.append(
            {
                "identity": ["charged", "AMS", "empty"],
                "role": "development",
                "status": "ready",
                "initial_trainable": 0,
            }
        )
        self.rows.append(
            {
                "identity": ["charged", "AMS", "never-read"],
                "role": "final",
                "status": "ready",
                "initial_trainable": "not accessed",
            }
        )
        result = choose_entities(self.rows, ("charged", "AMS"), "manifest", 14)
        self.assertEqual(len(result["entities"]), 4)
        self.assertEqual(result["entities"][-1]["entity_id"], "empty")
        self.assertEqual(result["ready_development_population"], 13)

    def test_counts_rank_not_future_activity_or_zero_filter(self):
        for i, row in enumerate(self.rows):
            row.update(
                initial_trainable=i + 1,
                full_future_energy="must not inspect",
                all_zero_release=True,
            )
        before = copy.deepcopy(self.rows)
        result = choose_entities(self.rows, ("charged", "AMS"), "manifest", 28)
        self.assertTrue(1 <= result["entities"][0]["initial_trainable"] <= 4)
        self.assertTrue(5 <= result["entities"][1]["initial_trainable"] <= 8)
        self.assertTrue(9 <= result["entities"][2]["initial_trainable"] <= 12)
        self.assertEqual(self.rows, before)

    def test_empty_invalid_duplicate_or_wrong_city_fails(self):
        bad = [[], self.rows + self.rows[:1]]
        for change in (
            {"initial_trainable": True},
            {"initial_trainable": -1},
            {"identity": ["charged", "JHB", "wrong"]},
        ):
            rows = copy.deepcopy(self.rows)
            rows[0].update(change)
            bad.append(rows)
        for rows in bad:
            with self.assertRaises(ValueError):
                choose_entities(rows, ("charged", "AMS"), "manifest", 7)
        one = choose_entities(self.rows[:1], ("charged", "AMS"), "manifest", 7)
        self.assertEqual(len(one["entities"]), 1)


if __name__ == "__main__":
    unittest.main()
