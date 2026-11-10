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


if __name__ == "__main__":
    unittest.main()
