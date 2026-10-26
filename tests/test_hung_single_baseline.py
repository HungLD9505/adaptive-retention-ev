"""Bounded same-origin Target-only/Frozen-Source replay and provenance checks."""

from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import torch

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2.cli import ARTIFACTS, _binding, _load_run
from experiments.hung_sprint2.model import ForecastGRU, ModelConfig
from experiments.hung_sprint2.runner import LabelArrival, Origin
from experiments.hung_sprint2.single_baseline import SingleBaselineRunner
from experiments.hung_sprint2.single_baseline_cli import _initialize_target_only, _replay
from experiments.hung_sprint2.single_forecast_journal import verify_forecast_journal
from experiments.hung_sprint2.training import save_checkpoint
from tests import test_hung_replay_cli as replay_fixture
from tests.test_hung_replay_inputs import START, input_run


def target_input(root: Path, *, missing_y: bool = False) -> tuple[Path, str]:
    run, _ = input_run(root, days=3, missing_y=missing_y)
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["config"]["deployment"] = START.isoformat()
    entities_path = run / "entities.jsonl"
    entities = [json.loads(line) for line in entities_path.read_text(encoding="utf-8").splitlines()]
    entities[0]["initialization"] = "target_initial_adaptation"
    entities[0]["initial_trainable"] = 1
    entities_path.write_text("".join(json.dumps(row) + "\n" for row in entities), encoding="utf-8")
    forecast = json.loads((run / "forecasts.jsonl").read_text(encoding="utf-8").splitlines()[0])
    forecast["origin"] = (START - timedelta(days=1)).isoformat()
    forecast["future_labels"] = [
        (START - timedelta(hours=24 - hour)).isoformat() for hour in range(24)
    ]
    training = {"role": "development", "forecast": forecast, "y_scaled": [0.4] * 24}
    (run / "training.jsonl").write_text(json.dumps(training) + "\n", encoding="utf-8")
    manifest["files"] = {name: {"sha256": sha256_file(run / name)} for name in ARTIFACTS}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return run, sha256_file(manifest_path)


def source_checkpoint(root: Path, run: Path, digest: str) -> Path:
    binding = _binding(_load_run(run, digest), digest, stage="source")
    folder = root / "source"
    folder.mkdir()
    path = folder / "source_checkpoint.pt"
    torch.manual_seed(11)
    model = ForecastGRU(ModelConfig(calendar_hidden=8))
    save_checkpoint(
        path,
        model,
        torch.optim.Adam(model.parameters(), lr=0.01),
        input_binding=binding,
        latent_scale=torch.ones(64),
        seed=11,
        code_sha="fixture",
        training_step=1,
    )
    (folder / "run_manifest.json").write_text(
        json.dumps({"checkpoint_sha256": sha256_file(path), "input_binding": binding}),
        encoding="utf-8",
    )
    return path


def replay_args(
    root: Path, run: Path, digest: str, method: str, output: str, limit: int
) -> Namespace:
    return Namespace(
        method=method,
        input_run=run,
        manifest_sha256=digest,
        entity_id="dev-1",
        output=root / output,
        device="cpu",
        block_days=2,
        max_origins=limit,
        initial_checkpoint=None,
        source_input_run=None,
        source_manifest_sha256=None,
        source_checkpoint=None,
        resume_checkpoint=None,
    )


class SingleBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        torch.set_num_threads(1)

    def test_target_only_prefix_and_split_resume_match_uninterrupted(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            root = Path(directory)
            run, digest = target_input(root)
            init_args = Namespace(
                input_run=run,
                manifest_sha256=digest,
                entity_id="dev-1",
                output=root / "target-initial",
                device="cpu",
                calendar_hidden=8,
                seed=7,
                learning_rate=0.01,
                batch_size=1,
                steps=1,
            )
            initial = _initialize_target_only(init_args)
            self.assertEqual(initial["training_steps"], 1)
            self.assertIsNone(initial["source_checkpoint_sha256"])
            checkpoint = init_args.output / "initial.pt"
            first_args = replay_args(root, run, digest, "target_only", "first", 1)
            first_args.initial_checkpoint = checkpoint
            first = _replay(first_args)
            self.assertEqual(first["coverage"]["requested"], 1)
            self.assertIsNone(first["metrics_kwh"])
            resumed_args = deepcopy(first_args)
            resumed_args.output = root / "resumed"
            resumed_args.max_origins = 3
            resumed_args.resume_checkpoint = first_args.output / "runner.pt"
            resumed = _replay(resumed_args)
            direct_args = deepcopy(resumed_args)
            direct_args.output = root / "direct"
            direct_args.resume_checkpoint = None
            direct = _replay(direct_args)
            self.assertEqual(resumed["input_binding"], direct["input_binding"])
            self.assertIsNone(resumed["source_checkpoint_sha256"])
            self.assertEqual(resumed["metrics_kwh"], direct["metrics_kwh"])
            self.assertEqual(resumed["coverage"], direct["coverage"])
            self.assertEqual(resumed["event_evidence"], direct["event_evidence"])
            self.assertEqual(resumed["cost"]["candidate_count"], 1)
            self.assertEqual(resumed["cost"]["update_steps"], direct["cost"]["update_steps"])
            self.assertGreater(resumed["cost"]["update_steps"], 0)
            states = [
                torch.load(path / "runner.pt", map_location="cpu", weights_only=True)
                for path in (resumed_args.output, direct_args.output)
            ]
            for left, right in zip(
                states[0]["model"].values(), states[1]["model"].values(), strict=True
            ):
                self.assertTrue(torch.equal(left, right))
            self.assertEqual(
                [row["day_id"] for row in states[0]["issued"]],
                [row["day_id"] for row in states[1]["issued"]],
            )

    def test_frozen_source_keeps_weights_and_nulls_incomplete_labels(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            root = Path(directory)
            fixture = replay_fixture.ReplayCliTests()
            run, digest, source, _, _ = fixture._inputs(root)
            args = replay_args(root, run, digest, "frozen_source", "frozen", 3)
            args.source_input_run = run
            args.source_manifest_sha256 = digest
            args.source_checkpoint = source
            result = _replay(args)
            self.assertEqual(result["source_checkpoint_sha256"], sha256_file(source))
            self.assertEqual(result["cost"]["candidate_count"], 1)
            self.assertEqual(result["cost"]["update_steps"], 0)
            self.assertEqual(result["cost"]["inference_calls"], result["coverage"]["created"])
            self.assertEqual(result["coverage"]["scored"], 2)
            self.assertIsNotNone(result["metrics_kwh"])
            state = torch.load(args.output / "runner.pt", map_location="cpu", weights_only=True)
            loaded = SingleBaselineRunner.from_state_dict(
                state, expected_binding=result["input_binding"]
            )
            source_state = torch.load(source, map_location="cpu", weights_only=True)["model_state"]
            for name, value in loaded.model.state_dict().items():
                self.assertTrue(torch.equal(value, source_state[name]))
            self.assertIsNone(loaded.optimizer)
            self.assertTrue(all(not p.requires_grad for p in loaded.model.parameters()))

    def test_frozen_source_split_resume_preserves_forecasts_and_source_binding(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            root = Path(directory)
            fixture = replay_fixture.ReplayCliTests()
            run, digest, source, _, _ = fixture._inputs(root)
            first_args = replay_args(root, run, digest, "frozen_source", "first", 1)
            first_args.source_input_run = run
            first_args.source_manifest_sha256 = digest
            first_args.source_checkpoint = source
            first = _replay(first_args)
            resumed_args = deepcopy(first_args)
            resumed_args.output = root / "resumed"
            resumed_args.resume_checkpoint = first_args.output / "runner.pt"
            resumed_args.max_origins = 3
            resumed = _replay(resumed_args)
            direct_args = deepcopy(resumed_args)
            direct_args.output = root / "direct"
            direct_args.resume_checkpoint = None
            direct = _replay(direct_args)
            self.assertEqual(first["runner_cursor"], 1)
            self.assertEqual(resumed["source_checkpoint_sha256"], sha256_file(source))
            self.assertEqual(resumed["metrics_kwh"], direct["metrics_kwh"])
            self.assertEqual(resumed["coverage"], direct["coverage"])
            self.assertEqual(resumed["event_evidence"], direct["event_evidence"])
            for left, right in zip(
                (torch.load(resumed_args.output / "runner.pt", weights_only=True)["issued"]),
                torch.load(direct_args.output / "runner.pt", weights_only=True)["issued"],
                strict=True,
            ):
                self.assertTrue(torch.equal(left["prediction"], right["prediction"]))
            source.write_bytes(source.read_bytes() + b"tamper")
            wrong_args = deepcopy(resumed_args)
            wrong_args.output = root / "wrong-source"
            with self.assertRaisesRegex(ValueError, "lineage differs"):
                _replay(wrong_args)
            self.assertFalse(wrong_args.output.exists())

    def test_wrong_source_use_or_tampered_initial_fails_before_output(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            root = Path(directory)
            run, digest = target_input(root)
            init_args = Namespace(
                input_run=run,
                manifest_sha256=digest,
                entity_id="dev-1",
                output=root / "initial",
                device="cpu",
                calendar_hidden=8,
                seed=7,
                learning_rate=0.01,
                batch_size=1,
                steps=1,
            )
            _initialize_target_only(init_args)
            args = replay_args(root, run, digest, "target_only", "wrong", 3)
            args.initial_checkpoint = init_args.output / "initial.pt"
            args.source_input_run = run
            with self.assertRaisesRegex(ValueError, "must not receive a Source"):
                _replay(args)
            self.assertFalse(args.output.exists())
            args.source_input_run = None
            args.initial_checkpoint.write_bytes(args.initial_checkpoint.read_bytes() + b"tamper")
            with self.assertRaisesRegex(ValueError, "lineage differs"):
                _replay(args)
            self.assertFalse(args.output.exists())

    def test_both_methods_share_origins_and_incomplete_day_stays_null(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            root = Path(directory)
            run, digest = target_input(root, missing_y=True)
            init_args = Namespace(
                input_run=run,
                manifest_sha256=digest,
                entity_id="dev-1",
                output=root / "target-initial",
                device="cpu",
                calendar_hidden=8,
                seed=7,
                learning_rate=0.01,
                batch_size=1,
                steps=1,
            )
            _initialize_target_only(init_args)
            target = replay_args(root, run, digest, "target_only", "target", 3)
            target.initial_checkpoint = init_args.output / "initial.pt"
            frozen = replay_args(root, run, digest, "frozen_source", "frozen", 3)
            frozen.source_input_run = run
            frozen.source_manifest_sha256 = digest
            frozen.source_checkpoint = source_checkpoint(root, run, digest)
            target_result, frozen_result = _replay(target), _replay(frozen)
            self.assertEqual(target_result["coverage"], frozen_result["coverage"])
            self.assertEqual(target_result["coverage"]["scored"], 1)
            target_state = torch.load(target.output / "runner.pt", weights_only=True)
            frozen_state = torch.load(frozen.output / "runner.pt", weights_only=True)
            self.assertEqual(
                [row["day_id"] for row in target_state["issued"]],
                [row["day_id"] for row in frozen_state["issued"]],
            )
            for state in (target_state, frozen_state):
                self.assertIsNone(state["issued"][1]["normalized_mae"])
                self.assertIsNone(state["issued"][1]["y_scaled"])
            self.assertEqual(target_result["cost"]["update_steps"], 1)
            self.assertEqual(frozen_result["cost"]["update_steps"], 0)
            self.assertEqual(target_result["cost"]["inference_calls"], 2)
            self.assertEqual(frozen_result["cost"]["inference_calls"], 2)

    def test_non_target_payloads_are_not_decoded_and_selected_scores_match(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            root = Path(directory)
            results = []
            for name, poison in (("plain", False), ("non-target-poison", True)):
                parent = root / name
                parent.mkdir()
                run, digest = target_input(parent)
                if poison:
                    for artifact, header in (
                        ("training.jsonl", '{"role": "final", "forecast": BROKEN}\n'),
                        (
                            "forecasts.jsonl",
                            '{"role": "final", "identity": ["urbanev", "SZH", "final-1"], "x_hist": BROKEN}\n',
                        ),
                        (
                            "labels.jsonl",
                            '{"identity": ["urbanev", "SZH", "final-1"], "energy_kwh": BROKEN}\n',
                        ),
                        (
                            "schedule.jsonl",
                            '{"identity": ["urbanev", "SZH", "final-1"], "status": BROKEN}\n',
                        ),
                        (
                            "entities.jsonl",
                            '{"identity": ["urbanev", "SZH", "final-1"], "scale": BROKEN}\n',
                        ),
                    ):
                        with (run / artifact).open("a", encoding="utf-8") as stream:
                            stream.write(header)
                    manifest_path = run / "manifest.json"
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    manifest["files"] = {
                        item: {"sha256": sha256_file(run / item)} for item in ARTIFACTS
                    }
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    digest = sha256_file(manifest_path)
                init_args = Namespace(
                    input_run=run,
                    manifest_sha256=digest,
                    entity_id="dev-1",
                    output=parent / "target-initial",
                    device="cpu",
                    calendar_hidden=8,
                    seed=7,
                    learning_rate=0.01,
                    batch_size=1,
                    steps=1,
                )
                _initialize_target_only(init_args)
                replay = replay_args(parent, run, digest, "target_only", "replay", 3)
                replay.initial_checkpoint = init_args.output / "initial.pt"
                results.append(_replay(replay))
            self.assertEqual(results[0]["coverage"], results[1]["coverage"])
            self.assertEqual(results[0]["metrics_kwh"], results[1]["metrics_kwh"])
            self.assertEqual(results[0]["event_evidence"], results[1]["event_evidence"])

    def test_forecast_is_durable_before_label_and_crash_resume_matches(self) -> None:
        for method in ("target_only", "frozen_source"):
            with (
                self.subTest(method=method),
                tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory,
            ):
                root = Path(directory)
                run, digest = target_input(root)
                args = replay_args(root, run, digest, method, "interrupted", 3)
                if method == "target_only":
                    initial_args = Namespace(
                        input_run=run,
                        manifest_sha256=digest,
                        entity_id="dev-1",
                        output=root / "initial",
                        device="cpu",
                        calendar_hidden=8,
                        seed=7,
                        learning_rate=0.01,
                        batch_size=1,
                        steps=1,
                    )
                    _initialize_target_only(initial_args)
                    args.initial_checkpoint = initial_args.output / "initial.pt"
                else:
                    args.source_input_run = run
                    args.source_manifest_sha256 = digest
                    args.source_checkpoint = source_checkpoint(root, run, digest)
                from experiments.hung_sprint2 import replay_inputs

                observed = []

                def crash_after_forecast(*call_args):
                    journal = args.output / "forecasts.jsonl"
                    records = [json.loads(line) for line in journal.read_text().splitlines()]
                    self.assertEqual(len(records), 2)
                    issued = records[1]
                    self.assertEqual(issued["day_id"], call_args[2])
                    self.assertIsNotNone(issued["prediction"])
                    self.assertEqual(
                        sha256_file(args.output / issued["checkpoint"]),
                        issued["checkpoint_sha256"],
                    )
                    observed.append(issued)
                    raise RuntimeError("simulated label-read crash")

                with patch.object(replay_inputs, "_label_record", side_effect=crash_after_forecast):
                    with self.assertRaisesRegex(RuntimeError, "simulated label-read crash"):
                        _replay(args)
                self.assertEqual(len(observed), 1)
                self.assertFalse((args.output / "run_manifest.json").exists())
                with (args.output / "forecasts.jsonl").open("ab") as stream:
                    stream.write(b'{"index":')
                interrupted = args.output / observed[0]["checkpoint"]
                resume = deepcopy(args)
                resume.output = root / "resumed"
                resume.resume_checkpoint = interrupted
                result = _replay(resume)
                direct = deepcopy(args)
                direct.output = root / "direct"
                expected = _replay(direct)
                self.assertEqual(result["coverage"], expected["coverage"])
                self.assertEqual(result["metrics_kwh"], expected["metrics_kwh"])
                self.assertEqual(result["event_evidence"], expected["event_evidence"])
                self.assertTrue(result["resumed_from"]["interrupted"])
                self.assertEqual(
                    len(
                        verify_forecast_journal(
                            direct.output,
                            run,
                            expected["input_binding"],
                            expected["code"],
                        )
                    ),
                    3,
                )
                broken = json.loads((args.output / "forecasts.jsonl").read_text().splitlines()[1])
                broken["prediction"][0] += 1
                header = (args.output / "forecasts.jsonl").read_text().splitlines()[0]
                (args.output / "forecasts.jsonl").write_text(
                    header + "\n" + json.dumps(broken) + "\n", encoding="utf-8"
                )
                tampered = deepcopy(resume)
                tampered.output = root / "tampered"
                with self.assertRaisesRegex(ValueError, "Issued forecast was changed"):
                    _replay(tampered)
                self.assertFalse(tampered.output.exists())

    def test_runner_rejects_reused_day_identity(self) -> None:
        binding = {
            "schema": "hung-single-baseline-binding-v1",
            "method": "frozen_source",
            "feature_schema": "ev-input-v1",
            "input_manifest_sha256": "a" * 64,
            "input_run_id": "run",
            "dataset_id": "dataset",
            "city_id": "city",
            "entity_id": "target",
            "history_days": 14,
            "scale_id": "scale",
            "initial_checkpoint_sha256": "b" * 64,
            "source_checkpoint_sha256": "b" * 64,
            "source_input_manifest_sha256": "c" * 64,
        }
        runner = SingleBaselineRunner(
            ForecastGRU(ModelConfig(calendar_hidden=8)),
            None,
            binding=binding,
            energy_scale=1.0,
            block_days=2,
        )
        runner.forecast(Origin("day-a", 0, None, None, "skipped_all_missing_history"))
        runner.arrive(LabelArrival("day-a", False))
        with self.assertRaisesRegex(ValueError, "origin sequence differs"):
            runner.forecast(Origin("day-a", 1, None, None, "skipped_all_missing_history"))


if __name__ == "__main__":
    unittest.main()
