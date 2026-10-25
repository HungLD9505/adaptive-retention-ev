"""Independent byte-preserving export fixtures; no raw inputs or model fitting."""

import copy
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

import torch

from ev_models.checkpoint import digest, save_checkpoint
from ev_models.model import ForecastGRU
from ev_runner.state import state_digest
from tools.export_development import checked_part, latest_proofs, put_run, put_sources, safe_name
from tools.verify_latest_states import verify_state


class ExportTests(unittest.TestCase):
    def fixture(self, parent: Path, omitted: int = 0) -> tuple[dict, dict]:
        root = parent / "fixture"
        root.mkdir()
        binding = {"config": {"state_retention": "latest"}}
        (root / "binding.json").write_text(json.dumps(binding))
        branches = {0.0: {"model": torch.tensor([1.0]), "optimizer": {}, "rng": [42]}}
        previous = "0" * 64
        for index in range(omitted + 1):
            tick = root / f"tick-{index:04d}"
            tick.mkdir()
            (tick / "forecasts.json").write_text("{}")
            (tick / "events.jsonl").write_text("")
            if index == omitted:
                torch.save({"branches": branches}, tick / "state.pt")
            files = {name: digest(tick / name) for name in ("forecasts.json", "events.jsonl")}
            files["state.pt"] = digest(tick / "state.pt") if index == omitted else "c" * 64
            (tick / "commit.json").write_text(
                json.dumps({"index": index, "previous": previous, "files": files})
            )
            previous = digest(tick / "commit.json")
        row = {
            "run_id": "fixture",
            "binding": binding,
            "ticks": omitted + 1,
            "candidate_levels": [0],
            "issued_days": 0,
            "scored_days": 0,
            "commit_chain": previous,
            "active_mae_kwh": None,
            "active_rmse_kwh": None,
            "final_branch_state_sha256": {"0.0": state_digest(branches[0.0])},
        }
        (root / "run.json").write_text(json.dumps(row))
        return row, verify_state(root, row)

    def test_complete_archive_preserves_bytes_and_declared_historical_omissions(self):
        for omitted in (0, 1):
            with self.subTest(omitted=omitted), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                row, proof = self.fixture(root, omitted)
                path = root / "part.zip"
                with zipfile.ZipFile(path, "x") as z:
                    put_run(z, root, row, proof, omitted)
                with zipfile.ZipFile(path) as z:
                    self.assertIsNone(z.testzip())
                    for p in (root / "fixture").rglob("*"):
                        if p.is_file():
                            self.assertEqual(
                                z.read(
                                    "study/fixture/" + p.relative_to(root / "fixture").as_posix()
                                ),
                                p.read_bytes(),
                            )
                    self.assertEqual(
                        "study/fixture/tick-0000/state.pt" in z.namelist(), omitted == 0
                    )
                self.assertEqual(checked_part(path, "fixture", ["fixture"])["sha256"], digest(path))

    def test_corruption_extra_files_changed_binding_and_wrong_omission_count_fail(self):
        for mode in ("forecast", "extra", "binding", "state", "omission"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                row, proof = self.fixture(root, omitted=1 if mode == "omission" else 0)
                if mode == "forecast":
                    (root / "fixture/tick-0000/forecasts.json").write_text("corrupt")
                elif mode == "extra":
                    (root / "fixture/secret.env").write_text("fixture-only-not-a-secret")
                elif mode == "binding":
                    (root / "fixture/binding.json").write_text("{}")
                elif mode == "state":
                    proof["latest_state_sha256"] = "0" * 64
                with zipfile.ZipFile(root / "bad.zip", "x") as z, self.assertRaises(ValueError):
                    put_run(z, root, row, proof, 0)

    @unittest.skipIf(os.name == "nt", "Creating symlinks requires extra Windows privileges")
    def test_symlinked_run_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row, proof = self.fixture(root)
            (root / "fixture/link").symlink_to(root / "fixture/run.json")
            with zipfile.ZipFile(root / "bad.zip", "x") as z, self.assertRaises(ValueError):
                put_run(z, root, row, proof, 0)

    def test_portable_names_and_complete_state_proof_population(self):
        for name in ("../x", "x/y", "x\\y", "C:evil", "CON", "LPT1.txt", ".", "a."):
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_name(name)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            m, v, s = [root / (name + ".json") for name in ("matrix", "daily", "states")]
            m.write_text("{}")
            v.write_text("{}")
            row = {"run_id": "fixture", "latest_state_sha256": "sha", "branches": {}}
            proof = {
                "status": "verified",
                "matrix_sha256": digest(m),
                "daily_verification_sha256": digest(v),
                "latest_states": 1,
                "runs": [row],
            }
            s.write_text(json.dumps(proof))
            self.assertEqual(
                latest_proofs(m, v, {"runs": [{"run_id": "fixture"}]}, s), {"fixture": row}
            )
            for bad in (
                {**proof, "runs": [row, row]},
                {**proof, "matrix_sha256": "changed"},
                {**proof, "runs": []},
                {**proof, "daily_verification_sha256": "changed"},
            ):
                s.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):
                    latest_proofs(m, v, {"runs": [{"run_id": "fixture"}]}, s)

    def test_source_models_are_cpu_loaded_and_bound_to_all_target_seeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "source-seed42"
            src.mkdir()
            model = ForecastGRU()
            binding = {
                "schema": "ev-checkpoint-input-binding-v1",
                "feature_schema": "ev-input-v1",
                "input_manifest_sha256": "a" * 64,
                "input_run_id": "fixture",
                "dataset_id": "fixture",
                "city_id": "CITY",
                "stage": "source",
                "entity_id": None,
                "history_days": None,
                "scale_id": None,
                "source_checkpoint_sha256": None,
            }
            sha = save_checkpoint(
                src / "epoch-10.pt",
                model,
                torch.optim.Adam(model.parameters()),
                metadata={
                    "input_binding": binding,
                    "source_population_sha256": "b" * 64,
                    "training_config": {"seed": 42, "learning_rate": 0.001},
                },
                latent_scale=torch.ones(64),
                completed_epochs=10,
            )
            row = {
                "source_checkpoint_sha256": sha,
                "binding": {
                    "config": {"initial_training": {"seed": 42}},
                    "input": {
                        "dataset_id": "fixture",
                        "city_id": "CITY",
                        "source_checkpoint_sha256": sha,
                    },
                    "source_population_sha256": "b" * 64,
                },
            }
            matrix = {"sources": {"42": {"sha256": sha}}, "runs": [row], "source_epochs": 10}
            with zipfile.ZipFile(root / "source.zip", "x") as z:
                self.assertEqual(put_sources(z, root, matrix)[0]["cpu_load"], "PASS")
            bad = copy.deepcopy(matrix)
            bad["runs"].append({**row, "source_checkpoint_sha256": "c" * 64})
            with zipfile.ZipFile(root / "bad.zip", "x") as z, self.assertRaises(ValueError):
                put_sources(z, root, bad)
