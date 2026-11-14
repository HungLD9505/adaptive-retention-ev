"""Offline readback checks; no Kaggle access or scored execution."""

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from tools.issue99_kaggle_readback_v2 import finite_cost, read_scores, sha256, validate_jobs


class FakeReplay:
    start = datetime.fromisoformat("2022-12-01T00:00:00+08:00")
    scale = 2.0

    def labels(self, origin, as_of):
        available = origin + timedelta(days=1)
        return SimpleNamespace(
            status="complete" if as_of >= available else "pending",
            values=(0.0,) * 24 if as_of >= available else None,
            available_at=available,
        )


class ReadbackTests(unittest.TestCase):
    def test_recomputes_arrived_score_and_rejects_wrong_tick(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            origin = FakeReplay.start.isoformat()
            forecast = {"origin": origin, "prediction": [1.0] * 24}
            first = run / "tick-0000"
            first.mkdir()
            (first / "forecasts.json").write_text(json.dumps(forecast))
            (first / "events.jsonl").write_text("")
            second = run / "tick-0001"
            second.mkdir()
            (second / "forecasts.json").write_text("{}")
            event = {
                "event": "score",
                "origin": origin,
                "as_of": (FakeReplay.start + timedelta(days=1)).isoformat(),
                "prediction_sha256": sha256(first / "forecasts.json"),
                "mae_kwh": 2.0,
                "mse_kwh2": 4.0,
            }
            (second / "events.jsonl").write_text(json.dumps(event) + "\n")
            self.assertEqual(
                read_scores(
                    run,
                    {"family": "continuous"},
                    FakeReplay(),
                    {"issued_days": 1, "scored_days": 1},
                ),
                {origin: (2.0, 4.0)},
            )
            event["mse_kwh2"] = 5.0
            (second / "events.jsonl").write_text(json.dumps(event) + "\n")
            with self.assertRaisesRegex(ValueError, "score differs"):
                read_scores(
                    run,
                    {"family": "continuous"},
                    FakeReplay(),
                    {"issued_days": 1, "scored_days": 1},
                )
            event["mse_kwh2"] = 4.0
            event["as_of"] = (FakeReplay.start + timedelta(days=2)).isoformat()
            (second / "events.jsonl").write_text(json.dumps(event) + "\n")
            with self.assertRaisesRegex(ValueError, "chronological tick"):
                read_scores(
                    run,
                    {"family": "continuous"},
                    FakeReplay(),
                    {"issued_days": 1, "scored_days": 1},
                )

    def test_rejects_bad_cost_and_incomplete_jobs(self):
        report = {
            "invocation_wall_seconds": 1.5,
            "cost_seconds": {"inference_seconds": 0.2},
            "gpu_peak_allocated_bytes": 100,
            "gpu_peak_reserved_bytes": 200,
        }
        self.assertEqual(finite_cost(report, "continuous")[0], 1.5)
        report["cost_seconds"]["inference_seconds"] = float("nan")
        with self.assertRaisesRegex(ValueError, "cost"):
            finite_cost(report, "continuous")
        with self.assertRaisesRegex(ValueError, "60-cell"):
            validate_jobs([])


if __name__ == "__main__":
    unittest.main()
