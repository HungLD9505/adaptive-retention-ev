"""Policy regressions using independently authored hourly fixtures."""

import unittest
from datetime import datetime, timedelta

from ev_inputs.loader import MISSING_DATA_POLICY, iter_forecasts
from tests import test_input_loader as fixtures

digest = fixtures.digest
json_lines = fixtures.json_lines


class MissingPolicyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.LoaderTests(
            methodName="test_complete_charged_integration_and_predictor_reader"
        )
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.config["missing_data_policy"] = MISSING_DATA_POLICY

    def records(self, name, file):
        return json_lines(self.fixture.root / name / file)

    def missing(self, predicate):
        def mutate(rows):
            for row in rows:
                if predicate(row):
                    row[4], row[5], row[6] = "", "0", "0"
            return rows

        self.fixture.change_rows(mutate)

    def test_partial_history_keeps_input_and_missing_label_does_not_select_origin(self):
        f = self.fixture
        self.missing(
            lambda row: row[2] == "001" and row[3] in ("2023-06-30T01:00:00", "2023-07-01T03:00:00")
        )
        result = f.run_loader(entity_ids=["001"])
        self.assertEqual(result["counts"]["requested_forecasts"], 2)
        self.assertEqual(result["counts"]["scheduled_forecasts"], 2)
        first = self.records("run", "forecasts.jsonl")[0]
        self.assertEqual(first["x_hist"][1][0], 0)
        self.assertEqual(first["x_hist"][1][-1], 0)
        self.assertIsNone(self.records("run", "labels.jsonl")[0]["energy_kwh"][3])
        self.assertEqual(result["schema"], "ev-loader-run-v2")

    def test_all_missing_history_skips_invocation_but_retains_schedule_and_labels(self):
        f = self.fixture
        self.missing(lambda row: row[2] == "001" and row[3].startswith("2023-06-30"))
        result = f.run_loader(entity_ids=["001"])
        self.assertEqual(result["status"], "technical_success_with_coverage_limits")
        self.assertEqual(result["counts"]["requested_forecasts"], 2)
        self.assertEqual(result["counts"]["skipped_all_missing_history"], 1)
        self.assertEqual(result["counts"]["scheduled_forecasts"], 1)
        self.assertEqual(len(self.records("run", "labels.jsonl")), 2)
        schedule = self.records("run", "schedule.jsonl")
        self.assertEqual(
            [r["status"] for r in schedule], ["skipped_all_missing_history", "created"]
        )
        # A predictor consumer never needs to open future labels.
        (f.root / "run/labels.jsonl").unlink()
        self.assertEqual(
            len(
                list(
                    iter_forecasts(
                        f.root / "run",
                        expected_manifest_sha256=digest(f.root / "run/manifest.json"),
                    )
                )
            ),
            1,
        )

    def test_undefined_scale_is_accounted_without_hiding_other_entities(self):
        f = self.fixture
        self.missing(lambda row: row[2] == "001" and datetime.fromisoformat(row[3]) < f.deployment)
        result = f.run_loader(entity_ids=["001", "005"])
        self.assertEqual(result["status"], "technical_success_with_coverage_limits")
        self.assertEqual(result["counts"]["requested_forecasts"], 4)
        self.assertEqual(result["counts"]["skipped_undefined_scale"], 2)
        self.assertEqual(result["counts"]["scheduled_forecasts"], 2)
        blocked = self.records("run", "entities.jsonl")[0]
        self.assertEqual(blocked["initialization"], "blocked_undefined_scale")
        self.assertEqual(blocked["status"], "undefined_scale")
        self.assertNotIn("scale", blocked)

    def test_all_targets_blocked_is_not_a_success(self):
        f = self.fixture
        self.missing(lambda row: row[2] == "001")
        result = f.run_loader(entity_ids=["001"])
        self.assertEqual(result["status"], "incomplete_no_usable_forecasts")
        with self.assertRaises(ValueError):
            list(
                iter_forecasts(
                    f.root / "run", expected_manifest_sha256=digest(f.root / "run/manifest.json")
                )
            )

    def test_no_initial_examples_gets_source_only_initialization(self):
        f = self.fixture
        start = f.deployment - timedelta(days=7)
        self.missing(
            lambda row: (
                row[2] == "001"
                and start <= datetime.fromisoformat(row[3]) < f.deployment
                and datetime.fromisoformat(row[3]).hour == 1
            )
        )
        result = f.run_loader(entity_ids=["001"])
        self.assertEqual(result["counts"]["initial_trainable"], 0)
        self.assertEqual(result["counts"]["targets_without_initial_adaptation"], 1)
        self.assertEqual(
            self.records("run", "entities.jsonl")[0]["initialization"], "source_checkpoint_only"
        )
        self.assertEqual(result["counts"]["scheduled_forecasts"], 2)

    def test_initial_all_missing_history_is_not_a_training_example(self):
        f = self.fixture
        self.missing(lambda row: row[2] == "001" and row[3].startswith("2023-06-24"))
        result = f.run_loader(entity_ids=["001"])
        self.assertEqual(result["counts"]["skipped_initial_history"], 1)
        self.assertEqual(result["counts"]["initial_trainable"], 5)

    def test_future_label_mutation_does_not_change_first_origin_gate_or_initialization(self):
        f = self.fixture
        f.run_loader("before", entity_ids=["001"])
        self.missing(lambda row: row[2] == "001" and row[3] == "2023-07-01T03:00:00")
        f.run_loader("after", entity_ids=["001"])
        a, b = (
            self.records("before", "forecasts.jsonl")[0],
            self.records("after", "forecasts.jsonl")[0],
        )
        a.pop("input_run_id")
        b.pop("input_run_id")
        self.assertEqual(a, b)
        ea, eb = (
            self.records("before", "entities.jsonl")[0],
            self.records("after", "entities.jsonl")[0],
        )
        self.assertEqual(ea["scale"], eb["scale"])
        self.assertEqual(ea["initialization"], eb["initialization"])

    def test_zero_is_observed_and_unknown_policy_is_rejected(self):
        f = self.fixture

        def zeros(rows):
            for row in rows:
                row[4] = "0"
            return rows

        f.change_rows(zeros)
        result = f.run_loader(entity_ids=["001"])
        self.assertEqual(result["counts"]["skipped_all_missing_history"], 0)
        self.assertEqual(result["counts"]["initial_trainable"], 6)
        self.assertEqual(
            self.records("run", "entities.jsonl")[0]["scale"]["fallback"], "zero-p95-unit-kwh"
        )
        for value in (None, "unknown", False):
            with self.subTest(policy=value), self.assertRaises(ValueError):
                f.run_loader("bad", missing_data_policy=value)
