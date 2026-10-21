"""DATA-v1 replay fixture checks with separate forecasts, labels and schedule."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import torch

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2.cli import ARTIFACTS
from experiments.hung_sprint2.model import ForecastGRU, ModelConfig
from experiments.hung_sprint2.replay_inputs import replay_target
from experiments.hung_sprint2.retention import frozen_source_reference
from experiments.hung_sprint2.runner import PrequentialRunner
from tests.test_hung_runner import runner as fixture_runner


START = datetime(2022, 12, 1, tzinfo=timezone(timedelta(hours=8)))
IDENTITY = ["urbanev", "SZH", "dev-1"]
BLOCKED = ["urbanev", "SZH", "blocked-1"]


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def input_run(root: Path, *, delayed: bool = True, missing_y: bool = False) -> tuple[Path, str]:
    run = root / "fixture-target"
    run.mkdir()
    forecast_rows = []
    label_rows = []
    schedule_rows = []
    for day in range(3):
        origin = START + timedelta(days=day)
        origin_text = origin.isoformat()
        status = "skipped_all_missing_history" if day == 2 else "created"
        schedule_rows.append({
            "identity": IDENTITY, "role": "development", "origin": origin_text,
            "input_run_id": run.name, "status": status,
        })
        if status == "created":
            forecast_rows.append({
                "role": "development", "identity": IDENTITY, "origin": origin_text,
                "clock_mode": "offset-aware-local", "schema_id": "ev-input-v1",
                "input_run_id": run.name, "scale_id": "scale-1", "energy_scale": 5.0,
                "history_labels": [(origin - timedelta(hours=24 - h)).isoformat()
                                   for h in range(24)],
                "future_labels": [(origin + timedelta(hours=h)).isoformat()
                                  for h in range(24)],
                "x_hist": [[0.1] * 7 for _ in range(24)],
                "c_future": [[0.2] * 5 for _ in range(24)],
            })
        times = [origin + timedelta(hours=h) for h in range(24)]
        late = delayed and day == 1
        energy: list[float | None] = [2.0] * 24
        validity = [True] * 24
        if missing_y and day == 1:
            energy[3] = None
            validity[3] = False
        label_rows.append({
            "identity": IDENTITY, "origin": origin_text,
            "clock_mode": "offset-aware-local",
            "timestamps": [stamp.isoformat() for stamp in times],
            "energy_kwh": energy,
            "file_valid": validity,
            "available_at": [
                (
                    stamp + timedelta(hours=1) +
                    (timedelta(hours=2) if late else timedelta())
                ).isoformat()
                for stamp in times
            ],
        })
        schedule_rows.append({
            "identity": BLOCKED, "role": "development", "origin": origin_text,
            "input_run_id": run.name, "status": "skipped_undefined_scale",
        })
    _write_rows(run / "schedule.jsonl", schedule_rows)
    _write_rows(run / "forecasts.jsonl", forecast_rows)
    _write_rows(run / "labels.jsonl", label_rows)
    _write_rows(run / "entities.jsonl", [
        {"identity": IDENTITY, "role": "development", "initialization": "source_checkpoint_only",
         "scale": {"fit_sha256": "scale-1", "energy_scale": 5.0}},
        {"identity": BLOCKED, "role": "development", "initialization": "blocked_undefined_scale"},
    ])
    _write_rows(run / "training.jsonl", [])
    manifest = {
        "schema": "ev-loader-run-v2", "feature_schema": "ev-input-v1",
        "missing_data_policy": "ev-missing-data-v1",
        "status": "technical_success_with_coverage_limits", "run_id": run.name,
        "config": {"dataset_id": "urbanev", "city_id": "SZH", "history_days": 7},
        "files": {name: {"sha256": sha256_file(run / name)} for name in ARTIFACTS},
    }
    (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return run, sha256_file(run / "manifest.json")


def bound_runner(digest: str) -> PrequentialRunner:
    base = fixture_runner()
    binding = dict(base.binding)
    binding.update(
        input_manifest_sha256=digest, input_run_id="fixture-target",
        entity_id="dev-1", scale_id="scale-1",
    )
    model = ForecastGRU(ModelConfig(calendar_hidden=8))
    return PrequentialRunner(
        model, torch.optim.Adam(model.parameters(), lr=0.001),
        frozen_source_reference(model), torch.ones(64), binding=binding,
        controller=base.controller, epsilon=1e-6, energy_scale=5.0,
    )


class ReplayInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        torch.set_num_threads(1)

    def test_forecast_first_delay_and_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run, digest = input_run(Path(directory))
            replay = bound_runner(digest)
            from experiments.hung_sprint2 import replay_inputs

            original = replay_inputs._label_record

            def after_forecast(row, identity, origin):
                self.assertEqual(replay.pending["day_id"], origin)
                self.assertIn(replay.events[-1], {f"forecast:{origin}", f"skip:{origin}"})
                return original(row, identity, origin)

            with mock.patch.object(replay_inputs, "_label_record", side_effect=after_forecast):
                summary = replay_target(
                    run, manifest_sha256=digest, entity_id="dev-1", runner=replay
                )
            self.assertEqual(
                (summary.requested, summary.created, summary.skipped_all_missing_history),
                (3, 2, 1),
            )
            self.assertEqual((summary.scored, summary.delayed_or_incomplete), (1, 1))
            self.assertEqual(replay.update_steps, [1, 1, 1])
            self.assertEqual(len(replay.issued), 2)
            self.assertIsNone(replay.issued[1]["normalized_mae"])
            blocked = replay_target(run, manifest_sha256=digest, entity_id="blocked-1", runner=None)
            self.assertEqual((blocked.requested, blocked.skipped_undefined_scale), (3, 3))

    def test_tamper_and_binding_fail_before_forecast(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run, digest = input_run(Path(directory))
            replay = bound_runner(digest)
            wrong = bound_runner(digest)
            wrong.binding["scale_id"] = "other"
            with self.assertRaisesRegex(ValueError, "binding/scale"):
                replay_target(run, manifest_sha256=digest, entity_id="dev-1", runner=wrong)
            with (run / "labels.jsonl").open("a", encoding="utf-8") as stream:
                stream.write("{}\n")
            with self.assertRaisesRegex(ValueError, "artifact SHA-256 mismatch"):
                replay_target(run, manifest_sha256=digest, entity_id="dev-1", runner=replay)
            self.assertEqual(replay.issued, [])

    def test_missing_y_does_not_fill_or_update(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run, digest = input_run(Path(directory), delayed=False, missing_y=True)
            replay = bound_runner(digest)
            summary = replay_target(run, manifest_sha256=digest, entity_id="dev-1", runner=replay)
            self.assertEqual((summary.scored, summary.delayed_or_incomplete), (1, 1))
            self.assertEqual(replay.update_steps, [1, 1, 1])
            self.assertIsNone(replay.issued[1]["normalized_mae"])


if __name__ == "__main__":
    unittest.main()
