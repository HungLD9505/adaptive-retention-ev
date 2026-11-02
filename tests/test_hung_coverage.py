"""Mandatory matrix views and reuse accounting; synthetic metadata only."""

import copy
import unittest

from tools.hung_coverage import audit


class CoverageTests(unittest.TestCase):
    def fixture(self):
        cells = [
            {
                "id": f"b{budget}s{seed}ex",
                "budget": budget,
                "seed": seed,
                "entity_id": "x",
                "input_manifest_sha256": f"synthetic-input-{budget}",
            }
            for budget in (7, 14, 28)
            for seed in (7, 11, 19)
        ]
        families = [
            "target_only",
            "frozen_source",
            "seasonal_naive",
            "full_finetuning",
            "fixed_retention",
            "online_best",
            "source_error",
            "uncertainty",
            "drift",
            "parameter_retention",
            "block28",
            "no_source",
        ]
        jobs = [
            {"id": name + "_" + cell["id"], "cell": cell["id"]}
            for name in families
            for cell in cells
            if name != "seasonal_naive" or cell["seed"] == 7
        ]
        plan = {
            "scope": "development_only",
            "budgets": [7, 14, 28],
            "seeds": [7, 11, 19],
            "cells": cells,
            "jobs": jobs,
        }
        coverage = {
            "scope": "development_only",
            "reused_jobs": {"main_" + c["id"]: {} for c in cells},
            "external_complete_jobs": {"block7_" + c["id"]: {} for c in cells},
            "aliases": {"fixed_lambda": "fixed_retention", "without_confidence": "online_best"},
        }
        records = []
        for job in jobs + [{"id": "main_" + c["id"], "cell": c["id"]} for c in cells]:
            cell = next(c for c in cells if c["id"] == job["cell"])
            records.append(
                {
                    "job_id": job["id"],
                    "method": job["id"][: -len(cell["id"]) - 1],
                    "budget": cell["budget"],
                    "seed": cell["seed"],
                    "entity_id": "x",
                    "input_manifest_sha256": cell["input_manifest_sha256"],
                    "status": "DISPATCH_VERIFIED",
                    "metrics": {"synthetic": 1},
                }
            )
        return plan, coverage, records

    def test_reuse_is_logical_coverage_not_independent_runs(self):
        plan, coverage, records = self.fixture()
        result = audit(plan, coverage, records)
        rows = {r["family"]: r for r in result["rows"]}
        self.assertEqual(len(result["baseline_families"]), 9)
        self.assertEqual(len(result["ablation_categories"]), 5)
        self.assertEqual(rows["seasonal_naive"]["matched_logical_cells"], 9)
        self.assertEqual(rows["seasonal_naive"]["unique_authenticated_artifacts"], 3)
        self.assertFalse(rows["seasonal_naive"]["seed_views_are_independent"])
        self.assertEqual(rows["without_confidence"]["physical_family"], "online_best")
        self.assertEqual(rows["fixed_lambda"]["physical_family"], "fixed_retention")
        self.assertEqual(result["unique_authenticated_metric_artifacts"], len(records))

    def test_unmatched_block7_does_not_pass_full_coverage(self):
        plan, coverage, records = self.fixture()
        result = audit(plan, coverage, records)
        row = next(r for r in result["rows"] if r["family"] == "block7")
        self.assertEqual(len(row["unmatched_cells"]), 9)
        self.assertEqual(row["matched_logical_cells"], 0)
        self.assertFalse(result["matched_family_cell_coverage_complete"])
        with self.assertRaises(ValueError):
            forged = copy.deepcopy(records[0])
            forged.update(job_id="block7_b7s7ex", method="block7")
            audit(plan, coverage, records + [forged])

    def test_missing_metric_evidence_is_not_assumed_not_run(self):
        plan, coverage, records = self.fixture()
        removed = records.pop(0)
        result = audit(plan, coverage, records)
        row = next(r for r in result["rows"] if r["family"] == removed["method"])
        self.assertEqual(len(row["no_authenticated_metric_cells"]), 1)
        self.assertIn("does not prove", result["interpretation"])

    def test_zero_scored_is_matched_but_not_zero_error(self):
        plan, coverage, records = self.fixture()
        for record in records:
            record["metrics"] = None
        row = next(r for r in audit(plan, coverage, records)["rows"] if r["family"] == "main")
        self.assertEqual(row["matched_logical_cells"], 9)
        self.assertEqual(row["scorable_logical_cells"], 0)
        self.assertEqual(len(row["zero_scored_cells"]), 9)

    def test_changed_alias_input_and_initializer_stop(self):
        for key, value in [("input_manifest_sha256", "foreign"), ("target_sha256", "foreign")]:
            with self.subTest(key=key):
                plan, coverage, records = self.fixture()
                next(r for r in records if r["method"] == "seasonal_naive")[key] = value
                with self.assertRaises(ValueError):
                    audit(plan, coverage, records)

    def test_duplicate_artifact_and_missing_seed_stop(self):
        plan, coverage, records = self.fixture()
        with self.assertRaises(ValueError):
            audit(plan, coverage, records + [records[0]])
        plan["cells"].pop()
        with self.assertRaises(ValueError):
            audit(plan, coverage, records)

    def test_no_final_scope_or_approval_is_inferred(self):
        plan, coverage, records = self.fixture()
        result = audit(plan, coverage, records)
        self.assertIn("cannot approve", result["final_authorization"])
        plan["scope"] = "final"
        with self.assertRaises(ValueError):
            audit(plan, coverage, records)


if __name__ == "__main__":
    unittest.main()
