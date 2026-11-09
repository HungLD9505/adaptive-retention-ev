"""Calibration-only Fixed selection from a complete hash-bound ledger."""

import json
import tempfile
import unittest
from pathlib import Path

from ev_models.checkpoint import digest
from ev_search.fixed import FixedSearchConfig
from ev_search.ledger import FixedLedger
from ev_search.select import select_fixed


def fixture(root: Path):
    config = {
        "positive_lower": 0.1,
        "positive_upper": 1.0,
        "maximum_upper": 1.0,
        "expansion_factor": 2.0,
        "boundary_fraction": 0.1,
        "maximum_expansions": 0,
        "bo_trials": 2,
        "initial_lambdas": [0.1, 1.0],
        "sensitivity_points": 2,
        "acquisition_grid_points": 16,
        "kernel_length": 1.0,
        "signal_std": 0.1,
        "noise_std": 0.01,
        "expected_improvement_jitter": 0.001,
    }
    search = root / "search.json"
    search.write_text(json.dumps(config))
    protocol = root / "protocol.json"
    protocol.write_text(
        json.dumps(
            {
                "status": "locked_owner_approved",
                "owner_authorization": "fixture",
                "fixed_search_config_sha256": digest(search),
                "calibration_study_template_sha256": "a" * 64,
                "code_commit": "b" * 40,
                "input_manifest_sha256": "c" * 64,
                "source_population_sha256": "d" * 64,
                "source_checkpoint_sha256": {str(seed): str(seed) * 32 for seed in (42, 43, 44)},
                "practical_equivalence_tolerance_kwh": 0.05,
            }
        )
    )
    p = json.loads(protocol.read_text())
    binding = {
        "schema": "issue99-fixed-calibration-binding-v1",
        "protocol_sha256": digest(protocol),
        "fixed_search_config_sha256": digest(search),
        "calibration_study_template_sha256": p["calibration_study_template_sha256"],
        "code_commit": p["code_commit"],
        "input_manifest_sha256": p["input_manifest_sha256"],
        "source_population_sha256": p["source_population_sha256"],
        "sources": p["source_checkpoint_sha256"],
    }
    ledger = FixedLedger(root / "ledger", FixedSearchConfig(**config), binding=binding)
    return protocol, search, ledger


class SelectionTests(unittest.TestCase):
    def test_zero_wins_within_tolerance_and_ledger_is_read_only(self):
        with tempfile.TemporaryDirectory(dir=".cache") as temporary:
            protocol, search, ledger = fixture(Path(temporary))
            for weight, role, score in (
                (0.0, "zero_baseline", 1.03),
                (0.1, "initial", 1.0),
                (1.0, "initial", 0.99),
            ):
                ledger.evaluate(
                    weight, role, lambda *_args, score=score: {"objective_mae_kwh": score}
                )
            before = digest(ledger.root / "events.jsonl")
            result = select_fixed(ledger.root, protocol, search)
            self.assertEqual(result["selected_fixed_lambda"], 0.0)
            self.assertEqual(result["selected_trial"], 0)
            self.assertEqual(digest(ledger.root / "events.jsonl"), before)

    def test_null_failed_preserved_and_incomplete_or_changed_binding_rejected(self):
        with tempfile.TemporaryDirectory(dir=".cache") as temporary:
            protocol, search, ledger = fixture(Path(temporary))
            ledger.evaluate(0.0, "zero_baseline", lambda *_: {"objective_mae_kwh": 1.2})
            ledger.evaluate(0.1, "initial", lambda *_: {"objective_mae_kwh": None})
            with self.assertRaisesRegex(ValueError, "budget incomplete"):
                select_fixed(ledger.root, protocol, search)
            ledger.evaluate(1.0, "initial", lambda *_: {"objective_mae_kwh": 0.99})
            result = select_fixed(ledger.root, protocol, search)
            self.assertEqual(result["selected_fixed_lambda"], 1.0)
            self.assertEqual(
                [trial["status"] for trial in result["trials"]], ["complete", "null", "complete"]
            )
            search.write_text(search.read_text() + "\n")
            with self.assertRaisesRegex(ValueError, "hash binding differs"):
                select_fixed(ledger.root, protocol, search)

    def test_failed_trial_is_preserved_and_never_selected(self):
        with tempfile.TemporaryDirectory(dir=".cache") as temporary:
            protocol, search, ledger = fixture(Path(temporary))
            ledger.evaluate(0.0, "zero_baseline", lambda *_: {"objective_mae_kwh": 1.2})

            def failed(*_):
                raise RuntimeError("fixture crash")

            ledger.evaluate(0.1, "initial", failed)
            ledger.evaluate(1.0, "initial", lambda *_: {"objective_mae_kwh": 0.99})
            result = select_fixed(ledger.root, protocol, search)
            self.assertEqual(result["selected_fixed_lambda"], 1.0)
            self.assertEqual(result["trials"][1]["status"], "failed")
            self.assertIsNone(result["trials"][1]["objective_mae_kwh"])

    def test_extra_hash_valid_trial_cannot_change_selected_lambda(self):
        with tempfile.TemporaryDirectory(dir=".cache") as temporary:
            protocol, search, ledger = fixture(Path(temporary))
            for weight, role, score in (
                (0.0, "zero_baseline", 1.2),
                (0.1, "initial", 1.0),
                (1.0, "initial", 0.99),
            ):
                ledger.evaluate(
                    weight, role, lambda *_args, score=score: {"objective_mae_kwh": score}
                )
            self.assertEqual(
                select_fixed(ledger.root, protocol, search)["selected_fixed_lambda"], 0.1
            )
            ledger.evaluate(0.5, "sensitivity", lambda *_: {"objective_mae_kwh": 0.1})
            with self.assertRaisesRegex(ValueError, "sensitivity trial sequence"):
                select_fixed(ledger.root, protocol, search)


if __name__ == "__main__":
    unittest.main()
