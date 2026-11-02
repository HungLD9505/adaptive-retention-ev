"""Final cohort completeness and frozen density boundaries on independent fixtures."""

import copy
import unittest
from types import SimpleNamespace

from tools.analyze_final import expected_cells, frozen_density


class FinalAnalysisTests(unittest.TestCase):
    def test_budget_seed_variant_completeness_and_same_ids(self):
        access = SimpleNamespace(
            lock={
                "groups": [
                    {"namespace": ["charged", "JHB"], "history_days": b, "selected_ids": ["a", "b"]}
                    for b in (7, 14, 28)
                ],
                "seeds": [42, 43, 44],
                "required_unique_variants": ["adaptive", "target_only"],
            }
        )
        self.assertEqual(len(expected_cells(access, ("charged", "JHB"))), 36)
        changed = copy.deepcopy(access)
        changed.lock["groups"][1]["selected_ids"] = ["a", "c"]
        with self.assertRaisesRegex(ValueError, "identities differ"):
            expected_cells(changed, ("charged", "JHB"))
        changed.lock["groups"].pop()
        with self.assertRaisesRegex(ValueError, "three locked budgets"):
            expected_cells(changed, ("charged", "JHB"))

    def test_frozen_threshold_ties_and_undefined_prefix(self):
        rows = [
            {
                "identity": ["charged", "JHB", str(i)],
                "role": "final",
                "status": "ready",
                "scale": {"valid_count": n, "zero_count": z},
            }
            for i, (n, z) in enumerate(((10, 8), (10, 5), (0, 0)))
        ]
        result = frozen_density(rows, 0.5)
        self.assertEqual(result["entities"]["0"]["group"], "sparse")
        self.assertEqual(result["entities"]["1"]["group"], "dense")
        self.assertEqual(result["undefined_entities"], ["2"])
        self.assertEqual(frozen_density(rows, None)["entities"], {})
        rows[0]["role"] = "source"
        with self.assertRaises(ValueError):
            frozen_density(rows, 0.5)
