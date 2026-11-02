"""Independent metadata fixtures for same-ID, outcome-blind bounded selection."""

import copy
import unittest

from tools.final_cohort import select_shared_ids


class FinalCohortTests(unittest.TestCase):
    def setUp(self):
        self.rows = {
            b: [
                {
                    "identity": ["urbanev", "SZH", str(i)],
                    "role": "final",
                    "status": "ready",
                    "initial_trainable": 0 if i == 0 and b == 7 else b,
                }
                for i in range(9)
            ]
            for b in (7, 14, 28)
        }

    def test_same_ids_empty_case_and_order_invariance(self):
        a = select_shared_ids(self.rows, ("urbanev", "SZH"), 4)
        b = select_shared_ids(
            {k: list(reversed(v)) for k, v in self.rows.items()}, ("urbanev", "SZH"), 4
        )
        self.assertEqual(a, b)
        self.assertIn("0", a["selected_ids"])
        self.assertEqual(len(a["selected_ids"]), 4)
        self.assertEqual(a["entities"][0]["initial_trainable"], {"7": 0, "14": 14, "28": 28})

    def test_excludes_nonshared_and_nonfinal_not_missing_outcomes(self):
        self.rows[14][1]["status"] = "undefined_scale"
        for b in self.rows:
            self.rows[b][2]["role"] = "source"
            for row in self.rows[b]:
                row["future_error"] = "must never affect selection"
        result = select_shared_ids(self.rows, ("urbanev", "SZH"), 7)
        self.assertEqual(result["shared_ready_population"], 7)
        self.assertNotIn("1", result["selected_ids"])
        self.assertNotIn("2", result["selected_ids"])

    def test_shortfall_and_duplicates_fail(self):
        with self.assertRaisesRegex(ValueError, "Insufficient"):
            select_shared_ids(self.rows, ("urbanev", "SZH"), 10)
        rows = copy.deepcopy(self.rows)
        rows[7].append(rows[7][0])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            select_shared_ids(rows, ("urbanev", "SZH"), 4)
