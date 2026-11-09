"""Synthetic immutable Store records for the downloaded pilot verifier."""

import json
import tempfile
import unittest
from pathlib import Path

import torch

from ev_runner.state import canonical, state_digest
from ev_runner.store import Store
from tools.issue99_pilot_verify import sha256, verify_pilot

COMMIT = "a" * 40
SOURCE = "b" * 64
INPUT = "c" * 64


class PilotVerifyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bundle = self.root / "bundle-manifest.json"
        self.bundle.write_text(
            json.dumps(
                {
                    "schema": "issue99-kaggle-bundle-v1",
                    "code_commit": COMMIT,
                    "code_files_sha256": {"ev_runner/store.py": "d" * 64},
                    "input_manifest_sha256": INPUT,
                    "source_checkpoint_sha256": {"42": SOURCE},
                }
            ),
            encoding="utf-8",
        )
        self.runtime = self.root / "runtime.json"
        self.runtime.write_text(
            json.dumps(
                {
                    "schema": "issue99-kaggle-runtime-v1",
                    "code_commit": COMMIT,
                    "gpu": "Tesla T4",
                    "packages": {"torch": "2.4.0", "numpy": "2.0.0"},
                }
            ),
            encoding="utf-8",
        )
        self.run = self.root / "pilot-run"
        self.initial_logs = [{"steps": 1}]
        self.binding = {
            "schema": "issue99-run-binding-v1",
            "input": {
                "input_manifest_sha256": INPUT,
                "source_checkpoint_sha256": SOURCE,
            },
            "config": {
                "phase": "pilot",
                "objective_origins": [],
                "initial_training": {"seed": 42},
            },
            "environment": {
                "device": "cuda",
                "device_name": "Tesla T4",
                "torch": "2.4.0+cu121",
            },
            "code": {"commit": COMMIT, "files": {"ev_runner/store.py": "d" * 64}},
            "initial_adaptation_sha256": state_digest(self.initial_logs),
        }
        store = Store(self.run, self.binding)
        (self.run / "initial-adaptation.json").write_text(json.dumps(self.initial_logs))
        issued = {}
        final_branch = None
        for index in range(3):
            origin = f"2026-01-{index + 1:02d}T00:00:00"
            tick = store.begin()
            forecast = {"origin": origin, "prediction": [float(index)]}
            current_sha = store.save_forecasts(tick, forecast)
            events = []
            if index:
                previous_origin = f"2026-01-{index:02d}T00:00:00"
                if index == 1:
                    events.append(
                        {
                            "event": "skip_incomplete_labels",
                            "origin": previous_origin,
                            "as_of": origin,
                        }
                    )
                else:
                    events.extend(
                        [
                            {
                                "event": "score",
                                "origin": previous_origin,
                                "prediction_sha256": issued[previous_origin],
                                "mae_kwh": 0.5,
                                "mse_kwh2": 0.25,
                            },
                            {"event": "actual_update", "origin": previous_origin},
                        ]
                    )
            events.append(
                {"event": "forecast_saved", "origin": origin, "prediction_sha256": current_sha}
            )
            issued[origin] = current_sha
            final_branch = {"weight": torch.tensor([index], dtype=torch.float32)}
            state = {
                "branch": final_branch,
                "pending": [{"origin": origin}],
                "actual_steps": max(0, index - 1),
                "virtual_steps": 0,
                "cost": {"inference_seconds": 0.1, "actual_update_seconds": 0.2},
            }
            store.commit(tick, state, events)
        self.report = {
            "schema": "issue99-run-v1",
            "run_id": self.run.name,
            "phase": "pilot",
            "binding": self.binding,
            "initial_logs": self.initial_logs,
            "scheduled_days": 90,
            "issued_days": 3,
            "scored_days": 1,
            "objective_requested_days": 0,
            "objective_scored_days": 0,
            "objective_minimum_scored_days": None,
            "objective_missing_origins": [],
            "objective_coverage_pass": False,
            "mae_kwh": None,
            "rmse_kwh": None,
            "controller_decisions": 0,
            "actual_steps": 1,
            "virtual_steps": 0,
            "pending_days": 1,
            "cost_seconds": {"inference_seconds": 0.1, "actual_update_seconds": 0.2},
            "invocation_wall_seconds": 2.0,
            "source_load_wall_seconds_this_invocation": 0.1,
            "replay_load_wall_seconds_this_invocation": 0.1,
            "prefix_load_wall_seconds_this_invocation": 0.1,
            "initial_wall_seconds_this_invocation": 0.1,
            "gpu_peak_allocated_bytes": 1000,
            "gpu_peak_reserved_bytes": 2000,
            "commit_chain": store.previous,
            "final_state_sha256": state_digest(final_branch),
        }
        (self.run / "run.json").write_text(json.dumps(self.report))

    def verify(self):
        return verify_pilot(
            self.run,
            self.runtime,
            self.bundle,
            expected_manifest_sha256=sha256(self.bundle),
            expected_code_commit=COMMIT,
            expected_ticks=3,
        )

    def test_verifies_complete_pilot(self):
        result = self.verify()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual((result["ticks"], result["issued_days"], result["scored_days"]), (3, 3, 1))
        self.assertEqual(result["skipped_incomplete_days"], 1)
        self.assertEqual(result["skipped_origins"], ["2026-01-01T00:00:00"])
        self.assertIn("tick-0002/state.pt", result["files_sha256"])

    def test_rejects_changed_retained_state(self):
        state = self.run / "tick-0001" / "state.pt"
        with state.open("ab") as stream:
            stream.write(b"corrupt")
        with self.assertRaisesRegex(ValueError, "Changed retained pilot artifact"):
            self.verify()

    def test_rejects_skip_before_label_availability(self):
        tick = self.run / "tick-0001"
        events_path = tick / "events.jsonl"
        events = [json.loads(line) for line in events_path.read_text().splitlines()]
        events[0]["as_of"] = events[0]["origin"]
        events_path.write_bytes(b"".join(canonical(event) for event in events))
        commit_path = tick / "commit.json"
        commit = json.loads(commit_path.read_text())
        commit["files"]["events.jsonl"] = sha256(events_path)
        commit_path.write_bytes(canonical(commit))
        final_commit_path = self.run / "tick-0002" / "commit.json"
        final_commit = json.loads(final_commit_path.read_text())
        final_commit["previous"] = sha256(commit_path)
        final_commit_path.write_bytes(canonical(final_commit))
        self.report["commit_chain"] = sha256(final_commit_path)
        (self.run / "run.json").write_bytes(canonical(self.report))
        with self.assertRaisesRegex(ValueError, "Incomplete-label skip"):
            self.verify()

    def test_rejects_wrong_pinned_manifest(self):
        with self.assertRaisesRegex(ValueError, "pinned SHA-256"):
            verify_pilot(
                self.run,
                self.runtime,
                self.bundle,
                expected_manifest_sha256="e" * 64,
                expected_code_commit=COMMIT,
                expected_ticks=3,
            )

    def test_rejects_non_null_objective(self):
        self.report["mae_kwh"] = 0.1
        (self.run / "run.json").write_text(json.dumps(self.report))
        with self.assertRaisesRegex(ValueError, "null-objective"):
            self.verify()


if __name__ == "__main__":
    unittest.main()
