"""Synthetic approval and producer fixtures; never access real Final values."""

import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_input_loader as fixtures
import torch

from ev_control.confidence import ControllerConfig
from ev_inputs.loader import MISSING_DATA_POLICY
from ev_models.checkpoint import digest, write_json
from ev_models.data import InputRun
from ev_models.model import ForecastGRU, ModelConfig
from ev_models.training import TrainingConfig, frozen_reference, seed_everything
from ev_runner.engine import DAY, Runner
from ev_runner.final_gate import MARKERS, FinalAccess, FinalInputRun, authorize
from ev_runner.replay import Replay
from ev_runner.run import execute
from ev_runner.state import Branch, rng_state, state_digest
from ev_runner.store import Store
from tools.verify_comparison import verify_run


class ApprovalTests(unittest.TestCase):
    def test_live_review_and_explicit_markers_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lock_path = root / "lock.json"
            lock = {
                "schema": "ev-final-execution-lock-v1",
                "runtime_profile": {"device": "cuda"},
                "method_seed_cells": 11340,
                "files": {},
            }
            write_json(lock_path, lock)
            sha = digest(lock_path)
            for mode in ("accepted", "author", "stale", "changes", "missing", "wrong-lead"):
                reviews = [
                    {
                        "user": {"login": "peer"},
                        "state": "APPROVED",
                        "commit_id": "head",
                        "id": 1,
                        "html_url": "fixture",
                    }
                ]
                if mode == "author":
                    reviews[0]["user"]["login"] = "author"
                if mode == "stale":
                    reviews[0]["commit_id"] = "old"
                if mode == "changes":
                    reviews.append(
                        {
                            "user": {"login": "peer"},
                            "state": "CHANGES_REQUESTED",
                            "commit_id": "head",
                        }
                    )
                comments = [
                    {
                        "user": {"login": "other" if mode == "wrong-lead" else "HungLD9505"},
                        "body": "\n".join(f"{m} {sha}" for m in MARKERS),
                    }
                ]
                if mode == "missing":
                    comments = []

                def command(args, **kwargs):
                    if "--porcelain" in args:
                        return ""
                    if "rev-parse" in args:
                        return "head\n"
                    if "show" in args:
                        return lock_path.read_bytes()
                    return json.dumps(
                        {
                            "state": "open",
                            "head": {"sha": "head"},
                            "base": {"ref": "dev"},
                            "user": {"login": "author"},
                        }
                    )

                with (
                    self.subTest(mode=mode),
                    patch("ev_runner.final_gate.subprocess.check_output", side_effect=command),
                    patch("ev_runner.final_gate.github_pages", side_effect=[reviews, comments]),
                ):
                    if mode == "accepted":
                        self.assertEqual(authorize(lock_path, root).sha256, sha)
                    else:
                        with self.assertRaises(ValueError):
                            authorize(lock_path, root)


class FinalFixtureTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        self.fixture = fixtures.LoaderTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.run_loader("inputs", missing_data_policy=MISSING_DATA_POLICY)
        self.root = self.fixture.root
        self.input_root = self.root / "inputs"
        data = InputRun(self.input_root, digest(self.input_root / "manifest.json"))
        self.config = {
            "controller": {
                "lambda_low": 0.1,
                "lambda_high": 1.0,
                "initial_lambda": 0.1,
                "block_days": 2,
                "min_valid_days": 2,
                "delta": 0.0,
                "alpha": 0.05,
                "segment_days": 1,
                "resamples": 20,
                "seed": 42,
            },
            "initial_training": {
                "seed": 42,
                "epochs": 1,
                "batch_size": 64,
                "learning_rate": 0.001,
                "epsilon": 0.001,
                "head_width": 4,
            },
            "online_training": {
                "seed": 42,
                "epochs": 1,
                "batch_size": 64,
                "learning_rate": 0.001,
                "epsilon": 0.001,
                "head_width": 4,
            },
            "development_entities": ["001"],
            "replay_days": 2,
            "state_retention": "latest",
        }
        self.lock_path = self.root / "fixture-lock.json"
        write_json(
            self.lock_path,
            {
                "files": {},
                "method_configs": {"42": {"adaptive": self.config}},
                "groups": [
                    {
                        "namespace": list(data.namespace),
                        "history_days": 7,
                        "selected_ids": ["001"],
                        "input_manifest_sha256": data.sha256,
                        "source_population_sha256": data.source_hash,
                        "sources": {"42": {"sha256": "a" * 64}},
                    }
                ],
            },
        )
        # Synthetic evidence only. Production CLI calls authorize(), never this constructor.
        self.access = FinalAccess(self.root, self.lock_path, "fixture", {"id": 1})
        self.inputs = FinalInputRun(self.input_root, data.sha256, self.access)

    def test_reader_rejects_unselected_and_future_labels_stay_opaque(self):
        with self.assertRaises(ValueError):
            list(self.inputs.replay_forecasts("005"))
        with self.assertRaises(ValueError):
            self.inputs.training("source")
        replay = Replay(self.inputs, "001", 2)
        with patch("pathlib.Path.open", side_effect=AssertionError("future Y opened")):
            self.assertEqual(replay.labels(replay.start, replay.start).status, "pending")
        self.assertEqual(replay.labels(replay.start, replay.start + DAY).status, "complete")
        self.assertEqual(len(self.inputs.training("final", "001")), 6)

    def run_fixture(self, name, resume=None, partial=False):
        seed_everything(42)
        model = ForecastGRU(ModelConfig(4))
        reference = frozen_reference(model)
        initial = Branch(model, torch.optim.Adam(model.parameters(), lr=0.001), rng_state())
        replay = Replay(self.inputs, "001", 2)
        binding = {
            "input": self.inputs.binding("target", "001", "a" * 64),
            "config": self.config,
            "final_authorization": self.access.provenance(),
            "initial_adaptation_identity": state_digest([]),
        }
        output = self.root / name
        store = Store(output, binding, resume_from=resume)
        (output / "initial-adaptation.json").write_text("[]")
        runner = Runner(
            replay,
            initial,
            reference,
            torch.ones(64),
            ControllerConfig(**self.config["controller"]),
            TrainingConfig(**self.config["online_training"]),
            store,
            device="cpu",
            stream_id="fixture",
        )
        runner.run_until(replay.start if partial else replay.stop + DAY)
        scores, forecasts = [], []
        for tick in sorted(output.glob("tick-*")):
            forecast = json.loads((tick / "forecasts.json").read_text())
            if forecast:
                forecasts.append(forecast)
            scores.extend(
                json.loads(line)
                for line in (tick / "events.jsonl").read_text().splitlines()
                if json.loads(line)["event"] == "score"
            )
        active_maes = [
            s["mae_scaled"][runner.levels.index(s["issued_active"])] * replay.scale for s in scores
        ]
        active_mses = [
            s["mse_scaled"][runner.levels.index(s["issued_active"])] * replay.scale**2
            for s in scores
        ]
        write_json(
            output / "run.json",
            {
                "run_id": output.name,
                "binding": binding,
                "initial_logs": [],
                "ticks": store.count,
                "final_branch_state_sha256": {
                    str(k): state_digest(v.snapshot()) for k, v in runner.branches.items()
                },
                "candidate_levels": list(runner.levels),
                "commit_chain": store.previous,
                "issued_days": len(forecasts),
                "scored_days": len(scores),
                "active_mae_kwh": sum(active_maes) / len(scores) if scores else None,
                "active_rmse_kwh": math.sqrt(sum(active_mses) / len(scores)) if scores else None,
                "decisions": runner.decisions,
                "audits": [],
                "scheduled_days": 2,
            },
        )
        return output, runner

    def test_final_reader_engine_resume_and_independent_verifier(self):
        full_path, full = self.run_fixture("full")
        partial_path, _ = self.run_fixture("partial", partial=True)
        resumed_path, resumed = self.run_fixture("resumed", resume=partial_path)
        for name in ("branches", "pending", "scores", "active", "next_at", "audit", "steps"):
            self.assertEqual(
                state_digest(full.snapshot()[name]), state_digest(resumed.snapshot()[name])
            )
        for path in (full_path, resumed_path):
            result = verify_run(path, self.input_root, final_access=self.access)
            self.assertEqual((result["issued"], result["scored"]), (2, 2))
            with self.assertRaisesRegex(ValueError, "approved lock"):
                verify_run(path, self.input_root)
        (resumed_path / "tick-0000" / "forecasts.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "changed"):
            verify_run(resumed_path, self.input_root, final_access=self.access)

    def test_changed_lock_source_config_or_entity_fails(self):
        self.access.check_run(self.inputs, "001", self.config, "a" * 64)
        with self.assertRaises(ValueError):
            self.access.check_run(self.inputs, "001", self.config, "b" * 64)
        changed = {**self.config, "replay_days": 1}
        with self.assertRaises(ValueError):
            self.access.check_run(self.inputs, "001", changed, "a" * 64)
        self.lock_path.write_text(self.lock_path.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "lock changed"):
            list(self.inputs.replay_forecasts("001"))

    def test_final_resume_reuses_durable_initialization_before_run_report_exists(self):
        resume = self.root / "resume-before-report"
        resume.mkdir()
        (resume / "initial-adaptation.json").write_text("[]")
        self.assertFalse((resume / "run.json").exists())
        model = ForecastGRU(ModelConfig(4))
        source_value = {
            "metadata": {
                "input_binding": {"stage": "source"},
                "source_population_sha256": self.inputs.source_hash,
                "training_config": {"seed": 42},
            },
            "latent_scale": torch.ones(64),
        }
        self.access.lock["runtime_profile"] = {"device": "cuda"}
        # Stop at Store creation: this verifies the CUDA wrapper's initialization
        # branch with synthetic Source tensors, without running a real CUDA fit.
        with (
            patch("ev_runner.run.torch.cuda.is_available", return_value=True),
            patch("ev_runner.run.environment", return_value={"device": "cuda"}),
            patch("ev_runner.run.digest", return_value="a" * 64),
            patch("ev_runner.run.load_checkpoint", return_value=(model, None, source_value)),
            patch("ev_runner.run.runtime_code", return_value={"files": {}}),
            patch("ev_runner.run.train_epoch") as train,
            patch("ev_runner.run.Store", side_effect=RuntimeError("fixture Store boundary")),
        ):
            with self.assertRaisesRegex(RuntimeError, "fixture Store boundary"):
                execute(
                    self.inputs,
                    "001",
                    Path("unused"),
                    "a" * 64,
                    self.config,
                    self.root / "new",
                    device="cuda",
                    resume_from=resume,
                )
            train.assert_not_called()
