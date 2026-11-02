"""Metadata selection and CUDA replay/resume checks for #39."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch

from experiments.hung_sprint2.checkpoint import load_runner, save_runner
from experiments.hung_sprint2.runner import PrequentialRunner
from experiments.hung_sprint2.selection import select_development
from tests.test_hung_runner import binding, complete, origin, runner


class SelectionTests(unittest.TestCase):
    def test_selection_uses_only_entity_metadata_and_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runs = []
            for budget in (7, 14, 28):
                path = root / str(budget)
                path.mkdir()
                rows = [
                    {
                        "role": "development",
                        "identity": ["urbanev", "SZH", f"a-{number}"],
                        "initialization": "target_initial_adaptation",
                        "initial_trainable": number,
                    }
                    for number in range(1, 10)
                ]
                rows.append(
                    {
                        "role": "development",
                        "identity": ["urbanev", "SZH", "source-only"],
                        "initialization": "source_checkpoint_only",
                        "initial_trainable": 0,
                    }
                )
                (path / "entities.jsonl").write_text(
                    "\n".join(json.dumps(row) for row in rows), encoding="utf-8"
                )
                runs.append((path, str(budget).zfill(64)))

            def manifest(path: Path, _: str) -> dict:
                return {
                    "run_id": path.name,
                    "config": {
                        "dataset_id": "urbanev",
                        "city_id": "SZH",
                        "history_days": int(path.name),
                    },
                }

            with patch("experiments.hung_sprint2.selection._load_run", side_effect=manifest):
                first = select_development(runs)
                second = select_development(runs)
            self.assertEqual(first, second)
            self.assertEqual(first["seeds"], [7, 11, 19])
            self.assertEqual(first["budgets"]["7"]["adaptation_group_sizes"], [3, 3, 3])
            self.assertEqual(len(first["budgets"]["7"]["representative_entities"]), 7)
            self.assertIn("source-only", first["budgets"]["7"]["verification_entity_ids"])


@unittest.skipUnless(torch.cuda.is_available(), "CUDA unavailable")
class CudaRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        torch.set_num_threads(1)

    def test_cuda_checkpoint_restores_rng_and_issued_forecast(self) -> None:
        baseline = runner()
        gpu = PrequentialRunner(
            baseline.active_model.to("cuda"),
            baseline.active_optimizer,
            baseline.reference.to("cuda"),
            baseline.latent_scale.to("cuda"),
            binding=binding(),
            controller=baseline.controller,
            epsilon=baseline.epsilon,
            energy_scale=baseline.energy_scale,
        )
        gpu.forecast(origin(0))
        self.assertEqual(gpu.issued[0]["forecasts"][0].device.type, "cpu")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runner.pt"
            save_runner(path, gpu)
            restored = load_runner(path, expected_binding=binding(), device="cuda")
            self.assertEqual(restored.device.type, "cuda")
            self.assertEqual(restored.next_index, 0)
            gpu.arrive(complete(0))
            restored.arrive(complete(0))
            self.assertEqual(gpu.events, restored.events)
            self.assertEqual(gpu.issued[0]["normalized_mae"], restored.issued[0]["normalized_mae"])
            for (left, _), (right, _) in zip(gpu.candidates, restored.candidates, strict=True):
                for key, value in left.state_dict().items():
                    self.assertTrue(torch.equal(value, right.state_dict()[key]))
            with self.assertRaisesRegex(ValueError, "device type mismatch"):
                load_runner(path, expected_binding=binding(), device="cpu")


if __name__ == "__main__":
    unittest.main()
