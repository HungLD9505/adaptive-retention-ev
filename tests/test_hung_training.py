"""Small manifest-bound Source/Development consumer fixture, without real data."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2.cli import ARTIFACTS, main
from experiments.hung_sprint2.model import ForecastGRU, ModelConfig
from experiments.hung_sprint2.training import load_checkpoint, save_checkpoint, source_step


def _input_run(
    root: Path, *, target_examples: int = 1, source_examples: int = 2
) -> tuple[Path, str]:
    run = root / "fixture-input-run"
    run.mkdir()

    def forecast(entity: str) -> dict:
        return {
            "identity": ["urbanev", "SZH", entity],
            "input_run_id": run.name,
            "schema_id": "ev-input-v1",
            "scale_id": "scale-target" if entity == "dev-1" else "scale-source",
            "x_hist": [[0.1] * 7 for _ in range(24)],
            "c_future": [[0.2] * 5 for _ in range(24)],
        }

    rows = [
        {
            "role": "source",
            "forecast": forecast("source-1"),
            "y_scaled": [0.3 if index == 0 else 0.5] * 24,
        }
        for index in range(source_examples)
    ]
    rows += [
        {"role": "development", "forecast": forecast("dev-1"), "y_scaled": [0.4] * 24}
        for _ in range(target_examples)
    ]
    (run / "training.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    entity = {
        "role": "development",
        "identity": ["urbanev", "SZH", "dev-1"],
        "initialization": (
            "target_initial_adaptation" if target_examples else "source_checkpoint_only"
        ),
        "scale": {"fit_sha256": "scale-target"},
    }
    source_entity = {"role": "source", "identity": ["urbanev", "SZH", "source-1"]}
    (run / "entities.jsonl").write_text(
        json.dumps(source_entity) + "\n" + json.dumps(entity) + "\n", encoding="utf-8"
    )
    for name in ARTIFACTS:
        path = run / name
        if not path.exists():
            path.write_text("", encoding="utf-8")
    manifest = {
        "schema": "ev-loader-run-v2",
        "feature_schema": "ev-input-v1",
        "missing_data_policy": "ev-missing-data-v1",
        "status": "technical_success",
        "run_id": run.name,
        "config": {"dataset_id": "urbanev", "city_id": "SZH", "history_days": 7},
        "files": {name: {"sha256": sha256_file(run / name)} for name in ARTIFACTS},
    }
    (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return run, sha256_file(run / "manifest.json")


class TrainingConsumerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        torch.set_num_threads(1)

    def test_source_limit_with_one_example_fails_before_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, digest = _input_run(root)
            output = root / "source-output"
            with self.assertRaisesRegex(ValueError, "at least two examples"):
                main(
                    [
                        "source-smoke",
                        "--input-run",
                        str(run),
                        "--manifest-sha256",
                        digest,
                        "--output",
                        str(output),
                        "--steps",
                        "1",
                        "--batch-size",
                        "1",
                        "--seed",
                        "17",
                        "--learning-rate",
                        "0.001",
                        "--calendar-hidden",
                        "8",
                    ]
                )
            self.assertFalse(output.exists())

    def test_source_smoke_counts_all_examples_but_uses_bounded_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, digest = _input_run(root, source_examples=5)
            output = root / "bounded-source"
            self.assertEqual(
                main(
                    [
                        "source-smoke",
                        "--input-run",
                        str(run),
                        "--manifest-sha256",
                        digest,
                        "--output",
                        str(output),
                        "--steps",
                        "1",
                        "--batch-size",
                        "2",
                        "--seed",
                        "17",
                        "--learning-rate",
                        "0.001",
                        "--calendar-hidden",
                        "8",
                    ]
                ),
                0,
            )
            evidence = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(evidence["source_examples_available"], 5)
            self.assertEqual(evidence["source_examples_used"], 2)
            self.assertEqual(evidence["steps"], 1)

    def test_source_then_independent_target_with_verified_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, digest = _input_run(root)
            source_output = root / "source-output"
            target_output = root / "target-output"
            source_args = [
                "source-smoke",
                "--input-run",
                str(run),
                "--manifest-sha256",
                digest,
                "--output",
                str(source_output),
                "--steps",
                "1",
                "--batch-size",
                "2",
                "--seed",
                "17",
                "--learning-rate",
                "0.001",
                "--calendar-hidden",
                "8",
            ]
            self.assertEqual(main(source_args), 0)
            source_manifest = json.loads((source_output / "run_manifest.json").read_text())
            self.assertEqual(source_manifest["source_examples_used"], 2)
            self.assertEqual(source_manifest["input_binding"]["stage"], "source")
            self.assertEqual(
                source_manifest["memory_usage"]["scope"].split(";")[0], "whole CLI process"
            )
            if source_manifest["memory_usage"]["peak_rss_bytes"] is not None:
                self.assertGreater(source_manifest["memory_usage"]["peak_rss_bytes"], 0)
            target_args = [
                "target-smoke",
                "--input-run",
                str(run),
                "--manifest-sha256",
                digest,
                "--output",
                str(target_output),
                "--steps",
                "1",
                "--batch-size",
                "1",
                "--seed",
                "19",
                "--learning-rate",
                "0.001",
                "--source-input-run",
                str(run),
                "--source-manifest-sha256",
                digest,
                "--source-checkpoint",
                str(source_output / "source_checkpoint.pt"),
                "--entity-id",
                "dev-1",
                "--retention-weight",
                "0.1",
                "--epsilon",
                "1e-6",
            ]
            self.assertEqual(main(target_args), 0)
            target_manifest = json.loads((target_output / "run_manifest.json").read_text())
            self.assertEqual(target_manifest["steps"], 1)
            self.assertEqual(target_manifest["input_binding"]["entity_id"], "dev-1")
            _, _, _, target_metadata = load_checkpoint(
                target_output / "target_checkpoint.pt",
                expected_binding=target_manifest["input_binding"],
            )
            self.assertEqual(target_metadata["training_step"], 1)
            self.assertEqual(target_metadata["initial_retention_weight"], 0.1)
            self.assertIn("peak_rss_bytes", target_manifest["memory_usage"])
            self.assertEqual(
                target_manifest["input_binding"]["source_checkpoint_sha256"],
                source_manifest["checkpoint_sha256"],
            )
            with self.assertRaises(FileExistsError):
                main(source_args)

    def test_tamper_and_source_checkpoint_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, digest = _input_run(root, target_examples=0)
            source_output = root / "source-output"
            source_args = [
                "source-smoke",
                "--input-run",
                str(run),
                "--manifest-sha256",
                digest,
                "--output",
                str(source_output),
                "--steps",
                "1",
                "--batch-size",
                "2",
                "--seed",
                "17",
                "--learning-rate",
                "0.001",
                "--calendar-hidden",
                "8",
            ]
            self.assertEqual(main(source_args), 0)
            target_output = root / "target-output"
            self.assertEqual(
                main(
                    [
                        "target-smoke",
                        "--input-run",
                        str(run),
                        "--manifest-sha256",
                        digest,
                        "--output",
                        str(target_output),
                        "--steps",
                        "1",
                        "--batch-size",
                        "1",
                        "--seed",
                        "19",
                        "--learning-rate",
                        "0.001",
                        "--source-input-run",
                        str(run),
                        "--source-manifest-sha256",
                        digest,
                        "--source-checkpoint",
                        str(source_output / "source_checkpoint.pt"),
                        "--entity-id",
                        "dev-1",
                        "--retention-weight",
                        "0.1",
                        "--epsilon",
                        "1e-6",
                    ]
                ),
                0,
            )
            target_manifest = json.loads((target_output / "run_manifest.json").read_text())
            self.assertEqual(target_manifest["initialization"], "source_checkpoint_only")
            self.assertEqual(target_manifest["steps"], 0)
            with (run / "training.jsonl").open("a", encoding="utf-8") as stream:
                stream.write("{}\n")
            with self.assertRaisesRegex(ValueError, "artifact SHA-256 mismatch"):
                main([*source_args[:5], "--output", str(root / "another-output"), *source_args[7:]])


class TrainingCheckpointRngTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        torch.set_num_threads(1)

    def _save(self, path: Path) -> tuple[ForecastGRU, torch.optim.Adam, dict]:
        binding = {
            "schema": "ev-checkpoint-input-binding-v1",
            "feature_schema": "ev-input-v1",
            "input_manifest_sha256": "a" * 64,
            "input_run_id": "rng-fixture",
            "dataset_id": "urbanev",
            "city_id": "SZH",
            "stage": "source",
            "entity_id": None,
            "history_days": None,
            "scale_id": None,
            "source_checkpoint_sha256": None,
        }
        model = ForecastGRU(ModelConfig(calendar_hidden=8))
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        source_step(
            model,
            optimizer,
            torch.full((2, 24, 7), 0.1),
            torch.full((2, 24, 5), 0.2),
            torch.full((2, 24), 0.3),
        )
        with patch("experiments.hung_sprint2.training.torch.cuda.is_available", return_value=False):
            save_checkpoint(
                path,
                model,
                optimizer,
                input_binding=binding,
                latent_scale=torch.ones(64),
                seed=7,
                code_sha="rng-fixture",
                training_step=1,
            )
        return model, optimizer, binding

    def test_opt_in_restores_cpu_rng_model_and_optimizer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.pt"
            model, optimizer, binding = self._save(path)
            expected_next = torch.rand(9)
            torch.rand(17)
            restored, restored_optimizer, scale, _ = load_checkpoint(
                path, expected_binding=binding, restore_rng=True
            )
            self.assertTrue(torch.equal(torch.rand(9), expected_next))
            self.assertTrue(torch.equal(scale, torch.ones(64)))
            for name, value in model.state_dict().items():
                self.assertTrue(torch.equal(value, restored.state_dict()[name]))
            original_state = optimizer.state_dict()
            restored_state = restored_optimizer.state_dict()
            self.assertEqual(original_state["param_groups"], restored_state["param_groups"])
            for key, values in original_state["state"].items():
                for name, value in values.items():
                    self.assertTrue(torch.equal(value, restored_state["state"][key][name]))

    def test_default_loading_keeps_transfer_behavior_and_accepts_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.pt"
            _, _, binding = self._save(path)
            with patch("experiments.hung_sprint2.training.torch.set_rng_state") as set_rng:
                load_checkpoint(path, expected_binding=binding)
                set_rng.assert_not_called()
            payload = torch.load(path, weights_only=True)
            del payload["rng_state"]
            legacy = Path(directory) / "legacy.pt"
            torch.save(payload, legacy)
            load_checkpoint(legacy, expected_binding=binding)
            with self.assertRaisesRegex(ValueError, "no supported RNG state"):
                load_checkpoint(legacy, expected_binding=binding, restore_rng=True)

    def test_opt_in_rejects_cuda_device_switch_or_unavailable_cuda(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.pt"
            _, _, binding = self._save(path)
            payload = torch.load(path, weights_only=True)
            payload["rng_state"]["model_device"] = "cuda:0"
            cuda_path = Path(directory) / "cuda-metadata.pt"
            torch.save(payload, cuda_path)
            with self.assertRaisesRegex(ValueError, "device type mismatch"):
                load_checkpoint(cuda_path, expected_binding=binding, restore_rng=True)
            payload["rng_state"]["model_device"] = "cpu"
            payload["rng_state"]["cuda"] = [torch.ones(8, dtype=torch.uint8)]
            payload["rng_state"]["cuda_devices"] = [{"name": "fixture", "capability": [8, 6]}]
            unavailable_path = Path(directory) / "unavailable-cuda.pt"
            torch.save(payload, unavailable_path)
            with patch(
                "experiments.hung_sprint2.training.torch.cuda.is_available", return_value=False
            ):
                with self.assertRaisesRegex(ValueError, "CUDA is unavailable"):
                    load_checkpoint(unavailable_path, expected_binding=binding, restore_rng=True)
            with (
                patch(
                    "experiments.hung_sprint2.training.torch.cuda.is_available", return_value=True
                ),
                patch("experiments.hung_sprint2.training.torch.cuda.device_count", return_value=1),
                patch(
                    "experiments.hung_sprint2.training.torch.cuda.get_device_name",
                    return_value="other",
                ),
                patch(
                    "experiments.hung_sprint2.training.torch.cuda.get_device_capability",
                    return_value=(8, 6),
                ),
            ):
                with self.assertRaisesRegex(ValueError, "device metadata mismatch"):
                    load_checkpoint(unavailable_path, expected_binding=binding, restore_rng=True)


if __name__ == "__main__":
    unittest.main()
