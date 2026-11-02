"""Independent finite proxy mappings, parameter units and controller pairing."""

import copy
import json
import unittest
from pathlib import Path

import test_controller_calibration as controller_fixtures

from tools.proxy_calibration import (
    METHODS,
    recipe_config,
    selected_controller,
    summarize,
    validate_profile,
)


class ProxyCalibrationTests(unittest.TestCase):
    def setUp(self):
        fixture = controller_fixtures.ControllerCalibrationTests()
        fixture.setUp()
        self.base, self.cohort, self.rows = fixture.base, fixture.cohort, fixture.rows
        for group in self.cohort["budgets"].values():
            group["manifest_sha256"] = "fixture-manifest"
        for row in self.rows:
            row["binding"]["input"].update(
                dataset_id="urbanev", city_id="SZH", input_manifest_sha256="fixture-manifest"
            )
            row["code"] = {"dirty": False, "files": {"fixture": "sha"}}
        self.matrix = {
            "status": "technical_success",
            "code": {"dirty": False, "files": {"fixture": "sha"}},
            "runs": self.rows,
        }

    def test_four_recipes_per_method_and_independent_parameter_units(self):
        before = copy.deepcopy(self.base)
        for method in METHODS:
            configs = [recipe_config(self.base, method, i) for i in range(4)]
            self.assertEqual(len({json.dumps(c, sort_keys=True) for c in configs}), 4)
            for c in configs:
                self.assertEqual(c["initial_training"], self.base["initial_training"])
                if method != "parameter_retention":
                    self.assertEqual(c["controller"], self.base["controller"])
        self.assertEqual(self.base, before)
        self.assertEqual(
            recipe_config(self.base, "parameter_retention", 3)["controller"]["lambda_high"], 10
        )
        self.assertEqual(recipe_config(self.base, "drift", 1)["method"]["proxy_order"], [2, 1, 0])

    def test_controller_choice_requires_complete_unchanged_actual_recipes(self):
        choice, refs = selected_controller(self.matrix, self.cohort, {"fixture": "sha"})
        self.assertEqual(choice, 1)
        self.assertEqual(len(refs), 9)
        for code in ({"fixture": "different"}, {}):
            with self.assertRaises(ValueError):
                selected_controller(self.matrix, self.cohort, code)
        bad = copy.deepcopy(self.matrix)
        bad["runs"][0]["binding"]["config"]["controller"]["delta"] = 1
        with self.assertRaises(ValueError):
            selected_controller(bad, self.cohort, {"fixture": "sha"})

    def test_all_method_cells_and_config_binding_required(self):
        _, refs = selected_controller(self.matrix, self.cohort, {"fixture": "sha"})
        rows = []
        for ref in refs.values():
            for method in METHODS:
                for recipe in range(4):
                    row = copy.deepcopy(ref)
                    row.update(
                        recipe=recipe, method={"name": method}, active_mae_kwh=float(recipe + 1)
                    )
                    row["binding"]["config"] = recipe_config(
                        ref["binding"]["config"], method, recipe
                    )
                    rows.append(row)
        result = summarize(rows, self.cohort, refs)
        self.assertTrue(all(r["provisional_choice"] == 0 for r in result.values()))
        for bad in (rows[:-1], rows + rows[:1]):
            with self.assertRaises(ValueError):
                summarize(bad, self.cohort, refs)
        rows[0]["binding"]["config"]["method"]["proxy_order"] = [1, 0, 2]
        with self.assertRaises(ValueError):
            summarize(rows, self.cohort, refs)

    def test_profile_prevents_hidden_budget_or_direction_changes(self):
        p = json.loads(Path("configs/issue23/proxy-calibration.json").read_text())
        validate_profile(p)
        for field, value in (("recipes_per_method", 8), ("orders", [[0, 1, 2]]), ("seeds", [42])):
            with self.assertRaises(ValueError):
                validate_profile({**p, field: value})
        for method, recipe in (("adaptive", 0), ("drift", True), ("drift", 4)):
            with self.assertRaises(ValueError):
                recipe_config(self.base, method, recipe)


if __name__ == "__main__":
    unittest.main()
