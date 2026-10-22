"""Offline Development CLI replay and checkpoint lineage checks."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import torch

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2.checkpoint import load_runner
from experiments.hung_sprint2.cli import _binding, _load_run, _replay
from experiments.hung_sprint2.model import ForecastGRU, ModelConfig
from experiments.hung_sprint2.training import save_checkpoint
from tests.test_hung_replay_inputs import input_run


class ReplayCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        torch.set_num_threads(1)

    def _inputs(self, root: Path):
        run, digest = input_run(root, days=3)
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
        target_folder.mkdir()
        target_path = target_folder / "target_checkpoint.pt"
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
            checkpoint = args.output / "runner_checkpoint.pt"
            self.assertEqual(first["final_runner_checkpoint_sha256"], sha256_file(checkpoint))
            self.assertEqual(load_runner(checkpoint, expected_binding=binding).next_index, 1)
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
            with self.assertRaises(FileExistsError):
                _replay(args)

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


if __name__ == "__main__":
    unittest.main()
