"""Finite positive-lambda calibration must preserve pairing and provenance."""

import copy
import json
import unittest
from pathlib import Path

import test_source_epoch_sweep as source_fixtures

from ev_evaluation.selection import score_candidates
from tools.fixed_retention_sweep import selected_sources, validate_profile


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        fixture = source_fixtures.SourceStudyTests()
        fixture.setUp()
        self.cohort, self.rows = fixture.cohort, fixture.rows
        self.profile = json.loads(Path("configs/issue23/fixed-retention-study.json").read_text())

    def test_finite_grid_and_seed_profile(self):
        validate_profile(self.profile)
        for value in ([0, 0.01, 0.1, 1], [0.001, 0.01, 0.1, 1, 10]):
            with self.assertRaises(ValueError):
                validate_profile({**self.profile, "lambdas": value})

    def test_lambda_scoring_weights_stations_and_breaks_exact_ties(self):
        rows = copy.deepcopy(self.rows)
        for row in rows:
            row["fixed_lambda"] = {1: 0.001, 3: 0.01, 10: 0.1}[row.pop("source_epochs")]
            row["method"]["name"] = "fixed_retention"
        result = score_candidates(
            rows,
            self.cohort,
            [0.001, 0.01, 0.1],
            choice_field="fixed_lambda",
            method_name="fixed_retention",
        )
        self.assertEqual(result["provisional_choice"], 0.001)
        self.assertEqual(result["candidates"]["0.001"]["selection_score"], 5)

    def test_source_choice_is_recomputed_and_requires_all_seeds(self):
        study = {
            "status": "technical_success",
            "profile_sha256": self.profile["source_profile_sha256"],
            "selection_sha256": self.profile["selection_sha256"],
            "code": {"commit": self.profile["source_study_code"], "dirty": False},
            "runs": self.rows,
            "sources": [
                {"seed": s, "candidates": [{"epochs": 1, "path": str(s), "sha256": "known"}]}
                for s in [42, 43, 44]
            ],
        }
        self.assertEqual(selected_sources(study, self.cohort, self.profile)[0], 1)
        for field, value in (("status", "failed"), ("sources", study["sources"][:-1])):
            with self.assertRaises(ValueError):
                selected_sources({**study, field: value}, self.cohort, self.profile)

    def test_score_count_contradiction_and_wrong_method_fail(self):
        for change in ({"scored_days": 0}, {"method": {"name": "adaptive"}}):
            rows = copy.deepcopy(self.rows)
            rows[0].update(change)
            with self.assertRaises(ValueError):
                score_candidates(
                    rows,
                    self.cohort,
                    [1, 3, 10],
                    choice_field="source_epochs",
                    method_name="full_finetuning",
                )

    def test_equal_counts_different_scored_origins_fail_for_full_runs(self):
        rows = copy.deepcopy(self.rows)
        for row in rows:
            row["binding"]["schema"] = "ev-prequential-run-v1"
            row["binding"]["input"]["input_manifest_sha256"] = "a" * 64
            row["issued_origins_sha256"] = "b" * 64
            row["scored_origins_sha256"] = "c" * 64
        self.assertEqual(
            score_candidates(
                rows,
                self.cohort,
                [1, 3, 10],
                choice_field="source_epochs",
                method_name="full_finetuning",
            )["provisional_choice"],
            1,
        )
        rows[0]["scored_origins_sha256"] = "d" * 64
        with self.assertRaisesRegex(ValueError, "origin coverage"):
            score_candidates(
                rows,
                self.cohort,
                [1, 3, 10],
                choice_field="source_epochs",
                method_name="full_finetuning",
            )
        del rows[0]["scored_origins_sha256"]
        with self.assertRaisesRegex(ValueError, "origin identities"):
            score_candidates(
                rows,
                self.cohort,
                [1, 3, 10],
                choice_field="source_epochs",
                method_name="full_finetuning",
            )


if __name__ == "__main__":
    unittest.main()
