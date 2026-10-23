"""Predictor-only fixtures for the proposed seasonal-naive fallback."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import torch

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2.seasonal_naive import forecast_previous_day
from experiments.hung_sprint2.seasonal_naive_replay import evaluate_development, main
from tests.test_hung_replay_inputs import input_run


class SeasonalNaiveTests(unittest.TestCase):
    def test_repeats_observed_hours_without_fallback(self) -> None:
        history = torch.zeros(24, 7)
        history[:, 0] = torch.arange(24)
        history[:, 6] = 1
        forecast = forecast_previous_day(history)
        self.assertTrue(torch.equal(forecast.scaled_kwh, history[:, 0]))
        self.assertEqual(forecast.fallback_hours, 0)

    def test_masked_hours_use_last_observed_history_value(self) -> None:
        history = torch.zeros(24, 7)
        history[:, 0] = 999  # Masked filler must not enter the prediction.
        history[3, 0], history[3, 6] = 2.5, 1
        history[20, 0], history[20, 6] = 4.0, 1
        forecast = forecast_previous_day(history)
        self.assertEqual(forecast.scaled_kwh[3].item(), 2.5)
        self.assertEqual(forecast.scaled_kwh[20].item(), 4.0)
        self.assertEqual(forecast.scaled_kwh[0].item(), 4.0)
        self.assertEqual(forecast.scaled_kwh[23].item(), 4.0)
        self.assertEqual(forecast.fallback_hours, 22)
        self.assertEqual(history[0, 0].item(), 999)

    def test_all_missing_and_malformed_history_fail(self) -> None:
        history = torch.zeros(24, 7)
        with self.assertRaisesRegex(ValueError, "All-missing"):
            forecast_previous_day(history)
        history[0, 6] = 0.5
        with self.assertRaisesRegex(ValueError, "binary"):
            forecast_previous_day(history)
        with self.assertRaisesRegex(ValueError, "shape"):
            forecast_previous_day(torch.zeros(23, 7))

    def test_development_cutoff_and_coverage_match_replay_schedule(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run, _ = input_run(Path(directory))
            forecasts_path = run / "forecasts.jsonl"
            rows = [json.loads(line) for line in forecasts_path.read_text().splitlines()]
            for row in rows:
                for hour in row["x_hist"]:
                    hour[0] = 0.4  # Scale 5 gives the fixture's 2-kWh labels.
                    hour[6] = 1.0
            forecasts_path.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
            manifest_path = run / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"]["forecasts.jsonl"]["sha256"] = sha256_file(forecasts_path)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            digest = sha256_file(manifest_path)
            bounded = evaluate_development(
                run, manifest_sha256=digest, entity_id="dev-1", max_origins=2
            )
            self.assertEqual((bounded.coverage.requested, bounded.coverage.scored), (2, 1))
            self.assertEqual(bounded.metrics.mae_kwh, 0)
            full = evaluate_development(run, manifest_sha256=digest, entity_id="dev-1")
            self.assertEqual((full.coverage.requested, full.coverage.created), (3, 2))
            self.assertEqual(full.coverage.scored, 2)
            self.assertEqual(full.metrics.hours, 48)
            self.assertEqual(full.metrics.rmse_kwh, 0)
            self.assertEqual(full.issued_fallback_hours, 0)
            blocked = evaluate_development(run, manifest_sha256=digest, entity_id="blocked-1")
            self.assertEqual(blocked.coverage.skipped_undefined_scale, 3)
            self.assertIsNone(blocked.metrics)

    def test_development_rejects_changed_input_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run, digest = input_run(Path(directory))
            with (run / "forecasts.jsonl").open("a", encoding="utf-8") as stream:
                stream.write("{}\n")
            with self.assertRaisesRegex(ValueError, "artifact SHA-256 mismatch"):
                evaluate_development(run, manifest_sha256=digest, entity_id="dev-1")

    def test_cli_writes_create_only_diagnostic_and_forecasts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run, digest = input_run(Path(directory))
            forecasts_path = run / "forecasts.jsonl"
            rows = [json.loads(line) for line in forecasts_path.read_text().splitlines()]
            for row in rows:
                for hour in row["x_hist"]:
                    hour[6] = 1.0
            forecasts_path.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
            manifest_path = run / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"]["forecasts.jsonl"]["sha256"] = sha256_file(forecasts_path)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            output = Path(directory) / "baseline-output"
            command = [
                "seasonal_naive_replay",
                "--input-run",
                str(run),
                "--manifest-sha256",
                sha256_file(manifest_path),
                "--entity-id",
                "dev-1",
                "--max-origins",
                "2",
                "--output",
                str(output),
            ]
            with mock.patch("sys.argv", command):
                main()
            record = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(record["status"], "completed")
            self.assertEqual(record["coverage"]["scored"], 1)
            self.assertEqual(
                record["issued_forecasts_sha256"], sha256_file(output / "issued_forecasts.jsonl")
            )
            self.assertEqual(len((output / "issued_forecasts.jsonl").read_text().splitlines()), 2)
            with mock.patch("sys.argv", command):
                with self.assertRaises(FileExistsError):
                    main()


if __name__ == "__main__":
    unittest.main()
