"""Saved prediction identity and scale checks without raw data or model fitting."""

import json
import tempfile
import unittest
from pathlib import Path

from ev_models.checkpoint import digest
from tools.analyze_core_comparisons import saved_errors


class SavedErrorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.origin = "2022-12-01T00:00:00+08:00"
        self.forecast = {
            "origin": self.origin,
            "active": 0.01,
            "record": {"energy_scale": 10, "x_hist": [[0, 1]] * 24},
        }
        self.previous = "0" * 64
        self.write_tick(0, self.forecast, [])
        self.checksum = digest(self.root / "tick-0000/forecasts.json")
        self.event = {
            "event": "score",
            "origin": self.origin,
            "prediction_sha256": self.checksum,
            "issued_active": 0.01,
            "mae_scaled": [2],
            "mse_scaled": [5],
        }
        self.write_tick(1, {}, [self.event])
        self.report = {
            "candidate_levels": [0.01],
            "issued_days": 1,
            "scored_days": 1,
            "commit_chain": self.previous,
        }

    def tearDown(self):
        self.temp.cleanup()

    def write_tick(self, index, forecast, events):
        tick = self.root / f"tick-{index:04d}"
        tick.mkdir()
        (tick / "forecasts.json").write_text(json.dumps(forecast))
        (tick / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
        meta = {
            "index": index,
            "previous": self.previous,
            "files": {name: digest(tick / name) for name in ("forecasts.json", "events.jsonl")},
        }
        (tick / "commit.json").write_text(json.dumps(meta))
        self.previous = digest(tick / "commit.json")

    def test_scaled_daily_errors_and_real_zero_history_coverage(self):
        errors, coverage = saved_errors(self.root, self.report)
        self.assertEqual(errors[0].mae, 20)
        self.assertEqual(errors[0].mse, 500)
        self.assertEqual(coverage["valid_history_hours_min"], 24)

    def test_changed_forecast_rejected_before_score_aggregation(self):
        (self.root / "tick-0000/forecasts.json").write_text("{}")
        with self.assertRaises(ValueError):
            saved_errors(self.root, self.report)

    def test_wrong_score_population_rejected(self):
        self.report["scored_days"] = 0
        with self.assertRaises(ValueError):
            saved_errors(self.root, self.report)


if __name__ == "__main__":
    unittest.main()
