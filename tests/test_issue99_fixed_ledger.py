"""Append-only Fixed search ledger, resume and failure accounting fixtures."""

import json
import math
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from ev_search.fixed import FixedSearchConfig
from ev_search.ledger import FixedLedger, run_bounded_search


def config():
    return FixedSearchConfig(
        positive_lower=0.001,
        positive_upper=1.0,
        maximum_upper=8.0,
        expansion_factor=2.0,
        boundary_fraction=0.1,
        maximum_expansions=2,
        bo_trials=5,
        initial_lambdas=(0.001, 0.1, 1.0),
        sensitivity_points=4,
        acquisition_grid_points=32,
        kernel_length=1.0,
        signal_std=0.2,
        noise_std=0.01,
        expected_improvement_jitter=0.001,
    )


class FixedLedgerTests(unittest.TestCase):
    def test_bounded_run_resume_preserves_trials_and_nulls(self):
        def evaluator(weight, role, trial):
            if math.isclose(weight, 0.1):
                return {"objective_mae_kwh": None, "reason": "coverage_below_minimum"}
            score = 1.0 if weight == 0 else (math.log(weight) - math.log(0.5)) ** 2
            return {"objective_mae_kwh": score, "cost_seconds": float(trial + 1)}

        with tempfile.TemporaryDirectory(dir=".cache") as temporary:
            root = Path(temporary) / "search"
            ledger = FixedLedger(root, config())
            first = run_bounded_search(ledger, evaluator, max_new_trials=3)
            self.assertEqual(
                [event["role"] for event in first], ["zero_baseline", "initial", "initial"]
            )
            self.assertEqual(first[-1]["status"], "null")
            resumed = FixedLedger(root, config(), resume=True)
            later = run_bounded_search(resumed, evaluator, max_new_trials=20)
            self.assertTrue(later)
            self.assertEqual(
                len([e for e in resumed.completed() if e["role"] in {"initial", "bo_ei"}]),
                config().bo_trials,
            )
            self.assertEqual(
                len([e for e in resumed.completed() if e["role"] == "zero_baseline"]), 1
            )
            self.assertTrue(any(event["event"] == "domain_expansion" for event in resumed.events))
            self.assertLessEqual(
                len(resumed.completed()), 1 + config().bo_trials + config().sensitivity_points
            )
            self.assertEqual(run_bounded_search(resumed, evaluator, max_new_trials=1), [])
            self.assertEqual(FixedLedger(root, config(), resume=True).chain, resumed.chain)

    def test_failed_trial_is_recorded_and_not_retried(self):
        def evaluator(weight, role, trial):
            if weight == config().initial_lambdas[0]:
                raise RuntimeError("synthetic_failure")
            return {"objective_mae_kwh": 1.0}

        with tempfile.TemporaryDirectory(dir=".cache") as temporary:
            ledger = FixedLedger(Path(temporary) / "search", config())
            events = run_bounded_search(ledger, evaluator, max_new_trials=3)
            self.assertEqual(events[1]["status"], "failed")
            self.assertIn("synthetic_failure", events[1]["outcome"]["error"])
            more = run_bounded_search(ledger, evaluator, max_new_trials=2)
            self.assertNotIn(config().initial_lambdas[0], [event["lambda"] for event in more])

    def test_nonserializable_outcome_is_recorded_as_failure(self):
        with tempfile.TemporaryDirectory(dir=".cache") as temporary:
            ledger = FixedLedger(Path(temporary) / "search", config())
            result = ledger.evaluate(
                0.0,
                "zero_baseline",
                lambda *_: {"objective_mae_kwh": 1.0, "diagnostic": float("nan")},
            )
            self.assertEqual(result["status"], "failed")
            self.assertIsNone(result["outcome"]["objective_mae_kwh"])
            self.assertEqual(len(FixedLedger(ledger.root, config(), resume=True).completed()), 1)

    def test_all_failed_initial_trials_stop_without_repeating(self):
        with tempfile.TemporaryDirectory(dir=".cache") as temporary:
            ledger = FixedLedger(Path(temporary) / "search", config())
            with self.assertRaisesRegex(ValueError, "No finite initial observation"):
                run_bounded_search(
                    ledger,
                    lambda *_: {"objective_mae_kwh": None},
                    max_new_trials=1 + len(config().initial_lambdas) + 1,
                )
            self.assertEqual(len(ledger.completed()), 1 + len(config().initial_lambdas))

    def test_changed_binding_chain_or_uncommitted_trial_rejected(self):
        with tempfile.TemporaryDirectory(dir=".cache") as temporary:
            root = Path(temporary) / "search"
            ledger = FixedLedger(root, config())
            run_bounded_search(ledger, lambda *_: {"objective_mae_kwh": 1.0}, max_new_trials=1)
            with self.assertRaisesRegex(ValueError, "config changed"):
                FixedLedger(root, replace(config(), noise_std=0.02), resume=True)
            with self.assertRaisesRegex(ValueError, "config changed"):
                FixedLedger(root, config(), binding={"source": "changed"}, resume=True)
            events_path = root / "events.jsonl"
            original = events_path.read_text()
            modified = original.replace('"lambda":0.0', '"lambda":0.1', 1)
            self.assertNotEqual(modified, original)
            events_path.write_text(modified)
            with self.assertRaisesRegex(ValueError, "event chain"):
                FixedLedger(root, config(), resume=True)
            events_path.write_text(original)
            ledger.append({"event": "trial_start", "trial": 1, "lambda": 0.001, "role": "initial"})
            with self.assertRaisesRegex(ValueError, "Uncommitted trial"):
                FixedLedger(root, config(), resume=True)

    def test_resume_rejects_changed_metadata_content_even_with_old_hash(self):
        with tempfile.TemporaryDirectory(dir=".cache") as temporary:
            root = Path(temporary) / "search"
            FixedLedger(root, config())
            metadata_path = root / "config.json"
            metadata = json.loads(metadata_path.read_text())
            metadata["config"]["positive_upper"] = 2.0
            metadata_path.write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, "config changed"):
                FixedLedger(root, config(), resume=True)

    def test_resume_records_due_expansion_after_completed_boundary_trial(self):
        with tempfile.TemporaryDirectory(dir=".cache") as temporary:
            root = Path(temporary) / "search"
            ledger = FixedLedger(root, config())

            def evaluator(weight, role, trial):
                return {"objective_mae_kwh": 0.0 if weight == 1.0 else 1.0}

            ledger.evaluate(0.0, "zero_baseline", evaluator)
            for weight in config().initial_lambdas:
                ledger.evaluate(weight, "initial", evaluator)
            self.assertFalse(any(event["event"] == "domain_expansion" for event in ledger.events))
            resumed = FixedLedger(root, config(), resume=True)
            run_bounded_search(resumed, evaluator, max_new_trials=1)
            expansions = [event for event in resumed.events if event["event"] == "domain_expansion"]
            self.assertEqual(expansions[0]["after_trial"], 3)
            self.assertEqual(expansions[0]["upper"], 2.0)


if __name__ == "__main__":
    unittest.main()
