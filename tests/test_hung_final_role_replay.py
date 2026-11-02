"""Synthetic Final-role isolation for the shared causal replay reader."""

from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

import torch

from ev_inputs.hourly_reader import sha256_file
from experiments.supporting_pipeline.cli import ARTIFACTS, _binding, _replay, _target
from experiments.supporting_pipeline.model import ForecastGRU, ModelConfig
from experiments.supporting_pipeline.replay_inputs import replay_target
from experiments.supporting_pipeline.training import save_checkpoint
from tests.test_hung_replay_inputs import START, bound_runner, input_run

ROOT = Path(__file__).resolve().parents[1]


def final_fixture(root: Path, *, days: int = 3) -> tuple[Path, str]:
    run, _ = input_run(root, days=days)
    for name in ("entities.jsonl", "schedule.jsonl", "forecasts.jsonl"):
        path = run / name
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        for row in rows:
            row["role"] = "final"
            if name == "forecasts.jsonl":
                for hour in row["x_hist"]:
                    hour[6] = 1.0
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8", newline="\n"
        )
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["config"]["deployment"] = START.isoformat()
    manifest["files"] = {name: {"sha256": sha256_file(run / name)} for name in ARTIFACTS}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8", newline="\n")
    return run, sha256_file(manifest_path)


class FinalRoleReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        torch.set_num_threads(1)

    def test_final_role_replays_synthetic_input_and_development_rejects_it(self) -> None:
        (ROOT / ".cache").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            run, digest = final_fixture(Path(directory))
            final = replay_target(
                run,
                manifest_sha256=digest,
                entity_id="dev-1",
                runner=bound_runner(digest),
                role="final",
            )
            self.assertEqual((final.requested, final.created, final.scored), (3, 2, 2))
            with self.assertRaisesRegex(ValueError, "development target identity"):
                replay_target(
                    run, manifest_sha256=digest, entity_id="dev-1", runner=bound_runner(digest)
                )

    def test_unknown_role_fails_before_input_read(self) -> None:
        with self.assertRaisesRegex(ValueError, "Replay role"):
            replay_target(
                Path("missing"), manifest_sha256="0" * 64, entity_id="x", runner=None, role="test"
            )

    def test_final_target_initialization_and_controller_replay_are_distinct(self) -> None:
        (ROOT / ".cache").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            root = Path(directory)
            run, digest = final_fixture(root)
            source_dir = root / "source"
            source_dir.mkdir()
            source = source_dir / "source_checkpoint.pt"
            model = ForecastGRU(ModelConfig(calendar_hidden=8))
            save_checkpoint(
                source,
                model,
                torch.optim.Adam(model.parameters(), lr=0.001),
                input_binding=_binding(
                    {
                        "config": {"dataset_id": "urbanev", "city_id": "SZH", "history_days": 7},
                        "run_id": run.name,
                    },
                    digest,
                    stage="source",
                ),
                latent_scale=torch.ones(64),
                seed=7,
                code_sha="fixture",
                training_step=1,
            )
            source_binding = _binding(
                {
                    "config": {"dataset_id": "urbanev", "city_id": "SZH", "history_days": 7},
                    "run_id": run.name,
                },
                digest,
                stage="source",
            )
            (source_dir / "run_manifest.json").write_text(
                json.dumps(
                    {"checkpoint_sha256": sha256_file(source), "input_binding": source_binding}
                ),
                encoding="utf-8",
            )
            target_dir = root / "target"
            lock_sha = "a" * 64
            initialized = _target(
                Namespace(
                    role="final",
                    final_lock_sha256=lock_sha,
                    final_job_id="fixture_final_job",
                    input_run=run,
                    manifest_sha256=digest,
                    source_input_run=run,
                    source_manifest_sha256=digest,
                    source_checkpoint=source,
                    entity_id="dev-1",
                    output=target_dir,
                    steps=1,
                    batch_size=1,
                    seed=7,
                    learning_rate=0.001,
                    retention_weight=0.0,
                    retention_kind="latent",
                    initialization_kind="source",
                    epsilon=1e-6,
                    device="cpu",
                )
            )
            self.assertEqual(initialized["scope"], "locked_final_prefix_initialization")
            replayed = _replay(
                Namespace(
                    role="final",
                    final_lock_sha256=lock_sha,
                    final_job_id="fixture_final_job",
                    input_run=run,
                    manifest_sha256=digest,
                    source_input_run=run,
                    source_manifest_sha256=digest,
                    source_checkpoint=source,
                    target_checkpoint=target_dir / "target_checkpoint.pt",
                    entity_id="dev-1",
                    output=root / "replay",
                    max_origins=3,
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
                    selection_rule="confidence",
                    device="cpu",
                )
            )
            self.assertEqual(replayed["schema"], "hung-sprint2-final-replay-v1")
            self.assertEqual(replayed["final_lock_sha256"], lock_sha)
