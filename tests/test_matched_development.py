"""Matched baseline/ablation contracts, aliases and block sensitivity fixtures."""

import copy
import json
import unittest
from pathlib import Path

from tools.controller_calibration import recipe_config
from tools.matched_development import comparison_config, validate_cells, variants


class MatchedDevelopmentTests(unittest.TestCase):
    def setUp(self):
        self.base = json.loads(Path("configs/issue23/source-epoch-study.json").read_text())[
            "runner_config"
        ]

    def test_confidence_alias_only_at_zero_margin(self):
        base = recipe_config(self.base, 0, 42)
        self.assertNotIn("without_confidence", variants(base))
        self.assertNotIn("adaptive_bmin7_reference", variants(base))
        with self.assertRaises(ValueError):
            comparison_config(base, "without_confidence")
        base = recipe_config(self.base, 2, 42)
        self.assertIn("without_confidence", variants(base))
        self.assertEqual(
            comparison_config(base, "without_confidence")["controller"], base["controller"]
        )

    def test_block7_has_explicit_equal_bmin_bridge(self):
        base = recipe_config(self.base, 3, 42)
        short = comparison_config(base, "block7")
        bridge = comparison_config(base, "adaptive_bmin7_reference")
        long = comparison_config(base, "block28")
        self.assertEqual(short["controller"]["min_valid_days"], 7)
        self.assertEqual(short["controller"]["segment_days"], 5)
        changed = copy.deepcopy(short["controller"])
        changed["block_days"] = 14
        self.assertEqual(changed, bridge["controller"])
        changed = copy.deepcopy(base["controller"])
        changed["block_days"] = 28
        self.assertEqual(changed, long["controller"])
        self.assertEqual(base["controller"]["min_valid_days"], 10)

    def test_only_declared_comparator_change_no_mutation(self):
        base = recipe_config(self.base, 1, 42)
        saved = copy.deepcopy(base)
        for variant in variants(base):
            config = comparison_config(base, variant)
            self.assertEqual(config["initial_training"], base["initial_training"])
            self.assertEqual(config["online_training"], base["online_training"])
            if not variant.startswith("block"):
                self.assertEqual(config["controller"], base["controller"])
        self.assertEqual(base, saved)
        with self.assertRaises(ValueError):
            comparison_config(base, "made_up_method")

    def test_full_matrix_bindings_nulls_and_coverage_fail_closed(self):
        base = recipe_config(self.base, 2, 42)
        binding = {"history_days": 7, "entity_id": "fixture"}
        reference = {
            "binding": {"config": base, "input": binding},
            "issued_days": 5,
            "scored_days": 0,
        }
        refs = {(7, "fixture", 42): reference}
        rows = []
        for variant in variants(base):
            config = comparison_config(base, variant)
            rows.append(
                {
                    "comparison_variant": variant,
                    "binding": {"config": config, "input": binding},
                    "method": config["method"],
                    "issued_days": 5,
                    "scored_days": 0,
                    "active_mae_kwh": None,
                }
            )
        result = validate_cells(rows, refs)
        self.assertEqual(result["cells"], 9)
        self.assertEqual(result["block7_comparator"], "adaptive_bmin7_reference")
        for bad in (rows[:-1], rows + rows[:1]):
            with self.assertRaises(ValueError):
                validate_cells(bad, refs)
        for field, value in (("issued_days", 4), ("active_mae_kwh", 0)):
            bad = copy.deepcopy(rows)
            bad[0][field] = value
            with self.assertRaises(ValueError):
                validate_cells(bad, refs)


if __name__ == "__main__":
    unittest.main()
