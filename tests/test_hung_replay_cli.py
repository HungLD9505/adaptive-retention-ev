"""Offline Development CLI replay and checkpoint lineage checks."""

from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import torch

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2.checkpoint import load_runner
from experiments.hung_sprint2.cli import _binding, _load_run, _replay, _target
from experiments.hung_sprint2.model import ForecastGRU, ModelConfig
from experiments.hung_sprint2.training import load_checkpoint, save_checkpoint
from tests.test_hung_replay_inputs import input_run
from tests.test_hung_resume import assert_same_replay


class ReplayCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        torch.set_num_threads(1)

    def _inputs(
        self,
        root: Path,
        *,
        trained_weight: float | None = None,
        proxy_history: bool = False,
        retention_kind: str = "latent",
        days: int = 3,
    ):
        run, digest = input_run(root, days=days)
        if proxy_history:
            forecasts_path = run / "forecasts.jsonl"
            forecasts = [json.loads(line) for line in forecasts_path.read_text().splitlines()]
            for index, forecast in enumerate(forecasts):
                for hour, row in enumerate(forecast["x_hist"]):
                    row[0] = 0.0 if index == 1 and hour < 12 else (0.1 if index == 0 else 0.9)
                    row[6] = 0.0 if index == 1 and hour < 12 else 1.0
            forecasts_path.write_text(
                "".join(json.dumps(row) + "\n" for row in forecasts), encoding="utf-8"
            )
            input_manifest = run / "manifest.json"
            manifest_data = json.loads(input_manifest.read_text(encoding="utf-8"))
            manifest_data["files"]["forecasts.jsonl"]["sha256"] = sha256_file(forecasts_path)
            input_manifest.write_text(json.dumps(manifest_data), encoding="utf-8")
            digest = sha256_file(input_manifest)
        if trained_weight is not None:
            entities_path = run / "entities.jsonl"
            entities = [json.loads(line) for line in entities_path.read_text().splitlines()]
            entities[0]["initialization"] = "target_initial_adaptation"
            entities[0]["initial_trainable"] = 1
            entities_path.write_text(
                "".join(json.dumps(row) + "\n" for row in entities), encoding="utf-8"
            )
            training_path = run / "training.jsonl"
            training_path.write_text(
                json.dumps(
                    {
                        "role": "development",
                        "forecast": {
                            "identity": ["urbanev", "SZH", "dev-1"],
                            "input_run_id": run.name,
                            "schema_id": "ev-input-v1",
                            "scale_id": "scale-1",
                            "x_hist": [[0.1] * 7 for _ in range(24)],
                            "c_future": [[0.2] * 5 for _ in range(24)],
                        },
                        "y_scaled": [0.4] * 24,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            input_manifest = run / "manifest.json"
            manifest_data = json.loads(input_manifest.read_text(encoding="utf-8"))
            for name in ("entities.jsonl", "training.jsonl"):
                manifest_data["files"][name]["sha256"] = sha256_file(run / name)
            input_manifest.write_text(json.dumps(manifest_data), encoding="utf-8")
            digest = sha256_file(input_manifest)
        manifest = _load_run(run, digest)
        source_binding = _binding(manifest, digest, stage="source")
        source_folder = root / "source-model"
        source_folder.mkdir()
        source_path = source_folder / "source_checkpoint.pt"
        model = ForecastGRU(ModelConfig(calendar_hidden=8))
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        save_checkpoint(
            source_path,
            model,
            optimizer,
            input_binding=source_binding,
            latent_scale=torch.ones(64),
            seed=7,
            code_sha="fixture",
            training_step=1,
        )
        source_sha = sha256_file(source_path)
        (source_folder / "run_manifest.json").write_text(
            json.dumps({"checkpoint_sha256": source_sha, "input_binding": source_binding}),
            encoding="utf-8",
        )
        target_binding = _binding(
            manifest,
            digest,
            stage="target",
            entity_id="dev-1",
            scale_id="scale-1",
            source_checkpoint_sha256=source_sha,
        )
        target_folder = root / "target-model"
        target_path = target_folder / "target_checkpoint.pt"
        if trained_weight is not None:
            result = _target(
                Namespace(
                    input_run=run,
                    manifest_sha256=digest,
                    source_input_run=run,
                    source_manifest_sha256=digest,
                    source_checkpoint=source_path,
                    entity_id="dev-1",
                    output=target_folder,
                    steps=1,
                    batch_size=1,
                    seed=7,
                    learning_rate=0.001,
                    retention_weight=trained_weight,
                    retention_kind=retention_kind,
                    epsilon=1e-6,
                    device="cpu",
                )
            )
            self.assertEqual(result["steps"], 1)
            self.assertEqual(result["retention_weight"], trained_weight)
            return run, digest, source_path, target_path, target_binding
        target_folder.mkdir()
        save_checkpoint(
            target_path,
            model,
            optimizer,
            input_binding=target_binding,
            latent_scale=torch.ones(64),
            seed=7,
            code_sha="fixture",
            training_step=0,
        )
        (target_folder / "run_manifest.json").write_text(
            json.dumps(
                {"checkpoint_sha256": sha256_file(target_path), "input_binding": target_binding}
            ),
            encoding="utf-8",
        )
        return run, digest, source_path, target_path, target_binding

    def _args(self, root, run, digest, source, target, output, limit):
        from argparse import Namespace

        return Namespace(
            input_run=run,
            manifest_sha256=digest,
            source_input_run=run,
            source_manifest_sha256=digest,
            source_checkpoint=source,
            target_checkpoint=target,
            entity_id="dev-1",
            output=root / output,
            max_origins=limit,
            level_one=0.1,
            level_two=0.2,
            initial_level=0.0,
            block_days=2,
            min_complete_days=1,
            delta=0.0,
            alpha=0.05,
            bootstrap_segment_days=1,
            bootstrap_resamples=10,
            challenger_rule="bonferroni_two",
            epsilon=1e-6,
            seed=7,
            resume_checkpoint=None,
        )

    def test_proxy_replay_binds_config_cost_and_resume(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, digest, source, target, binding = self._inputs(root)
            args = self._args(root, run, digest, source, target, "proxy-first", 1)
            args.selection_rule = "source_error"
            args.proxy_low = 0.1
            args.proxy_high = 0.5
            args.proxy_level_low = 0.0
            args.proxy_level_mid = 0.1
            args.proxy_level_high = 0.2
            first = _replay(args)
            self.assertEqual(first["config"]["proxy_config"]["levels_by_bin"], [0.0, 0.1, 0.2])
            self.assertEqual(first["proxy_costs"]["inference_calls"], 1)
            checkpoint = args.output / "runner_checkpoint.pt"
            self.assertEqual(
                load_runner(checkpoint, expected_binding=binding).proxy_costs, first["proxy_costs"]
            )
            args.output = root / "proxy-resume"
            args.resume_checkpoint = checkpoint
            args.max_origins = 3
            args.proxy_high = 0.6
            with self.assertRaisesRegex(ValueError, "lineage/config/code mismatch"):
                _replay(args)
            args.proxy_high = 0.5
            resumed = _replay(args)
            self.assertEqual(
                resumed["proxy_costs"]["inference_calls"], resumed["coverage"]["created"]
            )

    def test_all_proxy_cli_split_matches_uninterrupted(self) -> None:
        for rule in ("source_error", "uncertainty", "drift"):
            with self.subTest(rule=rule), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                run, digest, source, target, binding = self._inputs(root, proxy_history=True)
                args = self._args(root, run, digest, source, target, "uninterrupted", 3)
                args.selection_rule = rule
                args.proxy_low = 0.2
                args.proxy_high = 0.8
                args.proxy_level_low = 0.0
                args.proxy_level_mid = 0.1
                args.proxy_level_high = 0.2
                if rule == "drift":
                    args.drift_reference_mean = 0.0
                    args.drift_reference_scale = 1.0
                full = _replay(args)
                full_runner = load_runner(
                    args.output / "runner_checkpoint.pt", expected_binding=binding
                )
                args.output = root / "prefix"
                args.max_origins = 1
                _replay(args)
                args.resume_checkpoint = args.output / "runner_checkpoint.pt"
                args.output = root / "resumed"
                args.max_origins = 3
                resumed = _replay(args)
                resumed_runner = load_runner(
                    args.output / "runner_checkpoint.pt", expected_binding=binding
                )
                assert_same_replay(self, full_runner, resumed_runner)
                self.assertEqual(full_runner.decisions, resumed_runner.decisions)
                self.assertEqual(
                    full_runner.proxy_costs["inference_calls"],
                    resumed_runner.proxy_costs["inference_calls"],
                )
                self.assertEqual(
                    full_runner.proxy_costs["inference_calls"], full["coverage"]["created"]
                )
                self.assertEqual(
                    resumed_runner.proxy_costs["inference_calls"], resumed["coverage"]["created"]
                )
                for left, right in zip(full_runner.issued, resumed_runner.issued, strict=True):
                    self.assertEqual(left["proxy_value"], right["proxy_value"])
                    self.assertTrue(torch.equal(left["source_forecast"], right["source_forecast"]))

    def test_bounded_replay_and_resume_create_new_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, digest, source, target, binding = self._inputs(root)
            args = self._args(root, run, digest, source, target, "first", 1)
            first = _replay(args)
            self.assertEqual(first["coverage"]["requested"], 1)
            self.assertEqual(first["coverage"]["created"], 1)
            self.assertEqual(first["runner_cursor"], 1)
            self.assertTrue(first["runtime_costs"]["complete"])
            self.assertIn("peak_rss_bytes", first["memory_usage"])
            checkpoint = args.output / "runner_checkpoint.pt"
            self.assertEqual(first["final_runner_checkpoint_sha256"], sha256_file(checkpoint))
            loaded = load_runner(checkpoint, expected_binding=binding)
            self.assertEqual(loaded.next_index, 1)
            self.assertEqual(first["state_tensor_memory"], loaded.state_tensor_memory())
            first_journal = args.output / "events.jsonl"
            first_records = [json.loads(line) for line in first_journal.read_text().splitlines()]
            self.assertEqual(first["event_journal"]["sha256"], sha256_file(first_journal))
            self.assertEqual(first_records[0]["kind"], "header")
            self.assertEqual(first_records[0]["start_event_index"], 0)
            self.assertEqual(
                [(row["event_index"], row["value"]) for row in first_records[1:]],
                list(enumerate(first["event_evidence"]["events"])),
            )
            args.output = root / "resumed"
            args.max_origins = 3
            args.resume_checkpoint = checkpoint
            resumed = _replay(args)
            self.assertEqual(resumed["coverage"]["requested"], 3)
            self.assertEqual(resumed["coverage"]["created"], 2)
            self.assertEqual(resumed["runner_cursor"], 3)
            self.assertEqual(len(resumed["event_evidence"]["decisions"]), 1)
            self.assertEqual(resumed["resumed_from"]["checkpoint_sha256"], sha256_file(checkpoint))
            self.assertIsNotNone(resumed["metrics_kwh"]["live"])
            resumed_journal = args.output / "events.jsonl"
            resumed_records = [
                json.loads(line) for line in resumed_journal.read_text().splitlines()
            ]
            previous_events = len(first["event_evidence"]["events"])
            self.assertEqual(resumed_records[0]["start_event_index"], previous_events)
            self.assertEqual(
                [(row["event_index"], row["value"]) for row in resumed_records[1:]],
                list(enumerate(resumed["event_evidence"]["events"]))[previous_events:],
            )
            with self.assertRaises(FileExistsError):
                _replay(args)

    def test_interrupted_replay_preserves_partial_journal_without_success_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, digest, source, target, _ = self._inputs(root)
            args = self._args(root, run, digest, source, target, "interrupted", 1)
            with patch(
                "experiments.hung_sprint2.replay_inputs.ready_labels",
                side_effect=ValueError("simulated input failure"),
            ):
                with self.assertRaisesRegex(ValueError, "simulated input failure"):
                    _replay(args)
            journal = args.output / "events.jsonl"
            records = [json.loads(line) for line in journal.read_text().splitlines()]
            self.assertEqual(records[0]["kind"], "header")
            self.assertTrue(any(row.get("value", "").startswith("forecast:") for row in records))
            self.assertFalse((args.output / "run_manifest.json").exists())
            self.assertFalse((args.output / "runner_checkpoint.pt").exists())

    def test_tampered_checkpoint_and_resume_config_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, digest, source, target, _ = self._inputs(root)
            args = self._args(root, run, digest, source, target, "first", 1)
            _replay(args)
            checkpoint = args.output / "runner_checkpoint.pt"
            args.output = root / "wrong-config"
            args.resume_checkpoint = checkpoint
            args.level_one = 0.3
            with self.assertRaises(ValueError):
                _replay(args)
            args.level_one = 0.1
            target.write_bytes(target.read_bytes() + b"tamper")
            with self.assertRaises(ValueError):
                _replay(args)

    def test_tampered_previous_event_journal_blocks_resume(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, digest, source, target, _ = self._inputs(root)
            args = self._args(root, run, digest, source, target, "first", 1)
            _replay(args)
            checkpoint = args.output / "runner_checkpoint.pt"
            journal = args.output / "events.jsonl"
            with journal.open("a", encoding="utf-8") as stream:
                stream.write('{"kind":"event","event_index":999,"value":"tamper"}\n')
            args.output = root / "resume-rejected"
            args.max_origins = 3
            args.resume_checkpoint = checkpoint
            with self.assertRaisesRegex(ValueError, "lineage/config/code mismatch"):
                _replay(args)
            self.assertFalse(args.output.exists())

    def test_online_best_policy_is_bound_and_cannot_resume_as_confidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, digest, source, target, binding = self._inputs(root)
            args = self._args(root, run, digest, source, target, "online-best", 3)
            args.selection_rule = "online_best_lambda"
            result = _replay(args)
            self.assertEqual(result["config"]["selection_rule"], "online_best_lambda")
            self.assertEqual(result["coverage"]["requested"], 3)
            self.assertEqual(
                [item["update_steps"] for item in result["runtime_costs"]["candidate"]],
                [2, 2, 2],
            )
            loaded = load_runner(args.output / "runner_checkpoint.pt", expected_binding=binding)
            self.assertEqual(loaded.selection_rule, "online_best_lambda")
            args.resume_checkpoint = args.output / "runner_checkpoint.pt"
            args.output = root / "wrong-policy"
            args.max_origins = 4
            args.selection_rule = "confidence"
            with self.assertRaisesRegex(ValueError, "lineage/config/code mismatch"):
                _replay(args)
            self.assertFalse(args.output.exists())

    def test_fixed_policy_requires_matching_target_initialization_and_resumes(self) -> None:
        for rule, level in (("fixed_retention", 0.1), ("full_finetuning", 0.0)):
            with self.subTest(rule=rule), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                run, digest, source, target, binding = self._inputs(root, trained_weight=level)
                target_manifest = target.parent / "run_manifest.json"
                record = json.loads(target_manifest.read_text(encoding="utf-8"))
                _, _, _, target_metadata = load_checkpoint(target, expected_binding=binding)
                self.assertEqual(target_metadata["training_step"], 1)
                self.assertEqual(target_metadata["initial_retention_weight"], level)
                args = self._args(root, run, digest, source, target, "first", 1)
                args.selection_rule = rule
                args.initial_level = level
                first = _replay(args)
                self.assertEqual(first["config"]["selection_rule"], rule)
                checkpoint = args.output / "runner_checkpoint.pt"
                args.output = root / "resumed"
                args.resume_checkpoint = checkpoint
                args.max_origins = 3
                resumed = _replay(args)
                self.assertEqual(
                    resumed["event_evidence"]["decisions"][0]["reason"], "fixed_policy"
                )
                self.assertEqual(resumed["event_evidence"]["decisions"][0]["selected_level"], level)
                self.assertEqual(
                    [item["update_steps"] for item in resumed["runtime_costs"]["candidate"]],
                    [2, 2, 2],
                )
                loaded = load_runner(args.output / "runner_checkpoint.pt", expected_binding=binding)
                self.assertEqual(loaded.selection_rule, rule)
                self.assertEqual(loaded.current_level, level)
                self.assertEqual(loaded.audit_steps, 0)
                args.output = root / "uninterrupted"
                args.resume_checkpoint = None
                uninterrupted = _replay(args)
                direct = load_runner(args.output / "runner_checkpoint.pt", expected_binding=binding)
                self.assertEqual(resumed["event_evidence"], uninterrupted["event_evidence"])
                self.assertEqual(resumed["metrics_kwh"], uninterrupted["metrics_kwh"])
                self.assertEqual(loaded.update_steps, direct.update_steps)
                for resumed_day, direct_day in zip(loaded.issued, direct.issued, strict=True):
                    for resumed_forecast, direct_forecast in zip(
                        resumed_day["forecasts"], direct_day["forecasts"], strict=True
                    ):
                        self.assertTrue(torch.equal(resumed_forecast, direct_forecast))
                args.output = root / "mismatched-initialization"
                record["retention_weight"] = 0.2 if level == 0.0 else 0.0
                target_manifest.write_text(json.dumps(record), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "initialization lambda"):
                    _replay(args)
                self.assertFalse(args.output.exists())

    def test_full_finetuning_rejects_positive_initial_level(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, digest, source, target, _ = self._inputs(root)
            args = self._args(root, run, digest, source, target, "wrong-level", 1)
            args.selection_rule = "full_finetuning"
            args.initial_level = 0.1
            with self.assertRaisesRegex(ValueError, "inconsistent"):
                _replay(args)
            self.assertFalse(args.output.exists())

    def test_trained_positive_lambda_cannot_be_relabelled_full_finetuning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, digest, source, target, binding = self._inputs(root, trained_weight=0.1)
            before_hash = sha256_file(target)
            _, _, _, metadata = load_checkpoint(target, expected_binding=binding)
            self.assertEqual(metadata["training_step"], 1)
            self.assertEqual(metadata["initial_retention_weight"], 0.1)
            manifest_path = target.parent / "run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["retention_weight"] = 0.0
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            args = self._args(root, run, digest, source, target, "relabelled-full-ft", 3)
            args.selection_rule = "full_finetuning"
            args.initial_level = 0.0
            with self.assertRaisesRegex(ValueError, "manifest lambda disagrees with checkpoint"):
                _replay(args)
            self.assertEqual(sha256_file(target), before_hash)
            self.assertFalse(args.output.exists())

    def test_legacy_target_lambda_is_explicitly_unverified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, digest, source, target, binding = self._inputs(root)
            _, _, _, metadata = load_checkpoint(target, expected_binding=binding)
            self.assertIsNone(metadata["initial_retention_weight"])
            target_manifest = target.parent / "run_manifest.json"
            record = json.loads(target_manifest.read_text(encoding="utf-8"))
            record["retention_weight"] = 0.1
            target_manifest.write_text(json.dumps(record), encoding="utf-8")
            args = self._args(root, run, digest, source, target, "legacy-fixed", 1)
            args.selection_rule = "fixed_retention"
            args.initial_level = 0.1
            with self.assertRaisesRegex(ValueError, "Legacy target checkpoint"):
                _replay(args)
            self.assertFalse(args.output.exists())
            args.output = root / "legacy-confidence"
            args.selection_rule = "confidence"
            result = _replay(args)
            self.assertFalse(result["config"]["target_initial_retention_weight_verified"])
            self.assertIsNone(result["config"]["target_initial_retention_weight"])

    def test_fixed_policy_resume_rejects_changed_lambda_proof(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, digest, source, target, _ = self._inputs(root, trained_weight=0.1)
            args = self._args(root, run, digest, source, target, "first", 1)
            args.selection_rule = "fixed_retention"
            args.initial_level = 0.1
            _replay(args)
            checkpoint = args.output / "runner_checkpoint.pt"
            first_manifest = args.output / "run_manifest.json"
            record = json.loads(first_manifest.read_text(encoding="utf-8"))
            record["config"]["target_initial_retention_weight"] = 0.0
            first_manifest.write_text(json.dumps(record), encoding="utf-8")
            args.resume_checkpoint = checkpoint
            args.output = root / "changed-lambda-proof"
            args.max_origins = 3
            with self.assertRaisesRegex(ValueError, "lineage/config/code mismatch"):
                _replay(args)
            self.assertFalse(args.output.exists())

    def test_parameter_retention_initialization_replay_and_resume_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, digest, source, target, binding = self._inputs(
                root, trained_weight=0.1, retention_kind="parameter"
            )
            _, _, _, metadata = load_checkpoint(target, expected_binding=binding)
            self.assertEqual(metadata["initial_retention_kind"], "parameter")
            self.assertEqual(metadata["initial_retention_weight"], 0.1)
            args = self._args(root, run, digest, source, target, "parameter-first", 1)
            args.retention_kind = "parameter"
            args.initial_level = 0.1
            first = _replay(args)
            self.assertEqual(first["config"]["retention_kind"], "parameter")
            checkpoint = args.output / "runner_checkpoint.pt"
            resumed_args = deepcopy(args)
            resumed_args.resume_checkpoint = checkpoint
            resumed_args.output = root / "parameter-resumed"
            resumed_args.max_origins = 3
            resumed = _replay(resumed_args)
            direct_args = deepcopy(resumed_args)
            direct_args.output = root / "parameter-direct"
            direct_args.resume_checkpoint = None
            direct = _replay(direct_args)
            resumed_runner = load_runner(
                resumed_args.output / "runner_checkpoint.pt", expected_binding=binding
            )
            direct_runner = load_runner(
                direct_args.output / "runner_checkpoint.pt", expected_binding=binding
            )
            self.assertEqual(resumed_runner.retention_kind, "parameter")
            assert_same_replay(self, resumed_runner, direct_runner)
            self.assertEqual(resumed["metrics_kwh"], direct["metrics_kwh"])
            self.assertEqual(
                [item["update_steps"] for item in resumed["runtime_costs"]["candidate"]],
                [2, 2, 2],
            )
            self.assertEqual(resumed_runner.proxy_costs["update_steps"], 0)
            wrong = deepcopy(args)
            wrong.output = root / "wrong-kind"
            wrong.retention_kind = "latent"
            with self.assertRaisesRegex(ValueError, "cannot be replayed as latent"):
                _replay(wrong)
            self.assertFalse(wrong.output.exists())
            target_record_path = target.parent / "run_manifest.json"
            target_record = json.loads(target_record_path.read_text(encoding="utf-8"))
            target_record["retention_kind"] = "latent"
            target_record_path.write_text(json.dumps(target_record), encoding="utf-8")
            wrong = deepcopy(args)
            wrong.output = root / "changed-manifest-kind"
            with self.assertRaisesRegex(ValueError, "manifest retention kind disagrees"):
                _replay(wrong)
            self.assertFalse(wrong.output.exists())
            target_record["retention_kind"] = "parameter"
            payload = torch.load(target, map_location="cpu", weights_only=True)
            payload["initial_retention_kind"] = "latent"
            torch.save(payload, target)
            target_record["checkpoint_sha256"] = sha256_file(target)
            target_record_path.write_text(json.dumps(target_record), encoding="utf-8")
            wrong = deepcopy(args)
            wrong.output = root / "changed-checkpoint-kind"
            with self.assertRaisesRegex(ValueError, "manifest retention kind disagrees"):
                _replay(wrong)
            self.assertFalse(wrong.output.exists())

    def test_declarative_seven_and_twenty_eight_day_blocks_resume_at_boundary(self) -> None:
        for block_days in (7, 28):
            with self.subTest(block_days=block_days), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                run, digest, source, target, binding = self._inputs(root, days=block_days + 1)
                first_args = self._args(root, run, digest, source, target, "first", block_days)
                first_args.block_days = block_days
                first = _replay(first_args)
                self.assertEqual(first["config"]["controller"]["block_days"], block_days)
                resumed_args = deepcopy(first_args)
                resumed_args.output = root / "resumed"
                resumed_args.max_origins = block_days + 1
                resumed_args.resume_checkpoint = first_args.output / "runner_checkpoint.pt"
                resumed = _replay(resumed_args)
                direct_args = deepcopy(resumed_args)
                direct_args.output = root / "direct"
                direct_args.resume_checkpoint = None
                direct = _replay(direct_args)
                self.assertEqual(len(resumed["event_evidence"]["decisions"]), 1)
                self.assertEqual(resumed["metrics_kwh"], direct["metrics_kwh"])
                assert_same_replay(
                    self,
                    load_runner(
                        resumed_args.output / "runner_checkpoint.pt", expected_binding=binding
                    ),
                    load_runner(
                        direct_args.output / "runner_checkpoint.pt", expected_binding=binding
                    ),
                )


if __name__ == "__main__":
    unittest.main()
