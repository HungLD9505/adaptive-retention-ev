"""Historical-cohort follow-up aggregation and artifact-authentication regressions."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ev_models.checkpoint import digest
from tools.issue99_full_scope import summarize
from tools.issue99_full_scope_inputs import FollowupInputs, historical_vectors


class FullScopeTests(unittest.TestCase):
    def test_equal_station_weighting_and_null_preservation(self):
        rows = [
            {"target": t, "seed": s, "scored_days": days, "mae": {"old_fixed": value, "new": value}}
            for t, days, value in (("a", 90, 2), ("b", 1, 4), ("c", 0, None))
            for s in (42, 43, 44)
        ]
        group = {
            "selected_ids": ["a", "b", "c"],
            "namespace": ["charged", "AMS"],
            "history_days": 7,
        }
        result = summarize(rows, group)
        self.assertEqual(result["macro_mae"]["new"], 3)
        self.assertEqual(result["scored_stations"], 2)
        self.assertIsNone(result["station_means"]["c"]["new"])
        self.assertEqual(result["units"], 9)
        for malformed in (rows[:-1], rows + rows[:1]):
            with self.assertRaises(ValueError):
                summarize(malformed, group)
        rows[0]["mae"]["new"] = None
        with self.assertRaises(ValueError):
            summarize(rows, group)

    def test_new_access_requires_explicit_owner_followup_record(self):
        for lock in ({}, {"schema": "issue99-owner-followup-v1"}):
            with self.assertRaises(ValueError):
                FollowupInputs(Path("absent"), {}, SimpleNamespace(lock=lock))

    def test_historical_vector_hash_and_label_availability(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            tick = folder / "tick-0000"
            tick.mkdir()
            origin = "2020-01-01T00:00:00"
            forecast = {"origin": origin, "predictions": [[1.0] * 24], "prediction_ids": ["id1"]}
            path = tick / "forecasts.json"
            path.write_text(json.dumps(forecast))
            event = {
                "event": "score",
                "origin": origin,
                "as_of": "2020-01-02T00:00:00",
                "mae_scaled": [1.0],
                "issued_active": 1.0,
                "prediction_sha256": digest(path),
            }
            events = tick / "events.jsonl"
            events.write_text(json.dumps(event) + "\n")
            report = {
                "binding": {
                    "input": {"input_manifest_sha256": "pin", "entity_id": "a", "history_days": 7}
                },
                "candidate_levels": [1.0],
                "scored_days": 1,
                "active_mae_kwh": 2.0,
            }
            (folder / "run.json").write_text(json.dumps(report))
            record = {"path": str(folder), "report_sha256": digest(folder / "run.json")}
            outcome = SimpleNamespace(status="complete", values=[0.0] * 24)
            replay = SimpleNamespace(
                inputs=SimpleNamespace(sha256="pin", config={"history_days": 7}),
                entity_id="a",
                scale=2.0,
                labels=lambda origin, as_of: outcome,
            )
            self.assertEqual(historical_vectors(record, replay)["mae"], 2)
            self.assertEqual(
                historical_vectors(record, replay)["rows"][origin]["prediction_ids"], ["id1"]
            )
            outcome.status = "pending"
            with self.assertRaises(ValueError):
                historical_vectors(record, replay)
            outcome.status = "complete"
            path.write_text(json.dumps(forecast) + " ")
            with self.assertRaises(ValueError):
                historical_vectors(record, replay)

    def test_empty_prefix_keeps_source_initialization_then_learns_arrivals(self):
        from datetime import timedelta
        from unittest.mock import patch

        import torch

        from ev_models.model import ForecastGRU
        from tests.test_issue99_continuous_runner import ToyReplay
        from tools.issue99_full_scope import run_fast

        torch.set_num_threads(1)
        replay = ToyReplay()
        replay.entity_id = "a"
        replay.delay = timedelta(0)
        for origin, record in replay.records.items():
            record["origin"] = origin.isoformat()
        inputs = SimpleNamespace(
            source_hash="population",
            training=lambda role, entity: [],
            binding=lambda *args: {},
            final_access=SimpleNamespace(sha256="lock"),
        )
        checkpoint = {
            "metadata": {"source_population_sha256": "population", "training_config": {"seed": 42}},
            "completed_epochs": 10,
            "latent_scale": torch.ones(64),
        }
        config = {
            "initial_training": {"seed": 42, "epochs": 3},
            "online_training": {"seed": 42, "epochs": 1},
        }
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch(
                "tools.issue99_full_scope.load_checkpoint",
                return_value=(ForecastGRU(), None, checkpoint),
            ),
        ):
            folder = Path(tmp) / "run"
            result = run_fast(
                inputs, replay, {"path": "source.pt", "sha256": "pin"}, Path(tmp), config, folder
            )
            report = json.loads((folder / "run.json").read_text())
            self.assertEqual(report["initial_logs"], [])
            self.assertEqual(report["actual_steps"], 3)
            self.assertEqual(len(result), 3)


class IndependentReadbackTests(unittest.TestCase):
    def test_independent_weights_match_and_ignore_future_labels(self):
        from copy import deepcopy

        from ev_control.expert_mix import forecast_mixture
        from tests.test_expert_mix import cell
        from tools.issue99_full_scope_readback import independent_weights

        original = cell(labels=0)
        expected = forecast_mixture(original, 0.43, eta=0.1, share=0.1)["weights"]
        actual = independent_weights(original, 0.43, 0.1, 0.1)
        for a, b in zip(actual, expected, strict=True):
            self.assertAlmostEqual(a, b)
        changed = deepcopy(original)
        changed["labels"][1:] = [[100] * 24] * 3
        new = independent_weights(changed, 0.43, 0.1, 0.1)
        self.assertEqual(actual[:2], new[:2])
        self.assertNotEqual(actual[2], new[2])


if __name__ == "__main__":
    unittest.main()
