"""Independent mounted-storage fixtures; no downloads, fitting, GPU or real labels."""

import copy
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import torch

from ev_models.checkpoint import digest, save_checkpoint
from ev_models.model import ForecastGRU
from ev_models.training import TrainingConfig
from ev_runner.state import state_digest
from tools.durable_run_backup import RunBackup, canonical, require_drive_mount


class DurableBackupTests(unittest.TestCase):
    def fixture(self, root):
        study, backup, inputs = (root / name for name in ("study", "backup", "inputs"))
        study.mkdir()
        inputs.mkdir()
        source = study / "source-seed42"
        source.mkdir()
        binding = {
            "schema": "ev-checkpoint-input-binding-v1",
            "feature_schema": "ev-input-v1",
            "input_manifest_sha256": "a" * 64,
            "input_run_id": "source-fixture",
            "dataset_id": "charged",
            "city_id": "AMS",
            "stage": "source",
            "entity_id": None,
            "history_days": None,
            "scale_id": None,
            "source_checkpoint_sha256": None,
        }
        training = TrainingConfig(epochs=10).as_dict()
        model = ForecastGRU()
        checkpoint = source / "epoch-10.pt"
        source_metadata = {
            "input_binding": binding,
            "source_population_sha256": "b" * 64,
            "training_config": training,
            "code": {"dirty": False, "files": {}},
            "environment": {"fixture_environment": 1},
        }
        checksum = save_checkpoint(
            checkpoint,
            model,
            torch.optim.Adam(model.parameters()),
            metadata=source_metadata,
            latent_scale=torch.ones(64),
            completed_epochs=10,
        )
        source_report = {
            **source_metadata,
            "status": "technical_success",
            "checkpoint_sha256": checksum,
        }
        entry = {"seed": 42, "path": str(checkpoint), "sha256": checksum, "run": source_report}
        for p, value in (
            (source / "run.json", source_report),
            (study / "source-seed42-complete.json", entry),
        ):
            p.write_text(json.dumps(value))
        (study / "source-seed42.log").write_text("Source fixture, no training\n")
        summary = {
            "identity": ["charged", "AMS", "fixture"],
            "role": "development",
            "status": "ready",
            "scale": {"energy_scale": 1.0},
        }
        (inputs / "entities.jsonl").write_text(json.dumps(summary) + "\n")
        (inputs / "labels.jsonl").write_text("")
        (inputs / "manifest.json").write_text(
            json.dumps(
                {
                    "files": {
                        name: {"sha256": digest(inputs / name)}
                        for name in ("entities.jsonl", "labels.jsonl")
                    }
                }
            )
        )
        target_binding = {
            **binding,
            "stage": "target",
            "entity_id": "fixture",
            "history_days": 7,
            "input_manifest_sha256": digest(inputs / "manifest.json"),
            "scale_id": "c" * 64,
            "source_checkpoint_sha256": checksum,
        }
        config = {
            "initial_training": {"seed": 42},
            "state_retention": "latest",
            "method": {"name": "target_only"},
        }
        environment, core = {"fixture_environment": 1}, {"core.py": "fixture-fingerprint"}
        context = {
            "namespace": ["charged", "AMS"],
            "seeds": [42],
            "source_epochs": 10,
            "source_training": {k: v for k, v in training.items() if k != "seed"},
            "source_population_sha256": "b" * 64,
            "source_manifest_sha256": "a" * 64,
            "core_files": core,
            "environment": environment,
            "expected_runs": {
                "fixture-target": {
                    "config": config,
                    "entity_id": "fixture",
                    "history_days": 7,
                    "input_manifest_sha256": target_binding["input_manifest_sha256"],
                }
            },
        }
        full_binding = {
            "input": target_binding,
            "config": config,
            "environment": environment,
            "source_population_sha256": "b" * 64,
        }
        run = study / "fixture-target"
        run.mkdir()
        (run / "binding.json").write_text(json.dumps(full_binding))
        branch = {0.0: {"model": torch.tensor([1.0]), "optimizer": {}, "rng": [42]}}
        previous = "0" * 64
        for index in (0, 1):
            tick = run / f"tick-{index:04d}"
            tick.mkdir()
            (tick / "forecasts.json").write_text("{}")
            (tick / "events.jsonl").write_text("")
            if index == 1:
                torch.save({"branches": branch}, tick / "state.pt")
            files = {name: digest(tick / name) for name in ("forecasts.json", "events.jsonl")}
            files["state.pt"] = digest(tick / "state.pt") if index == 1 else "d" * 64
            (tick / "commit.json").write_text(
                json.dumps({"index": index, "previous": previous, "files": files})
            )
            previous = digest(tick / "commit.json")
        row = {
            "run_id": run.name,
            "binding": full_binding,
            "code": {"dirty": False, "files": core},
            "source_checkpoint_sha256": checksum,
            "ticks": 2,
            "candidate_levels": [0],
            "issued_days": 0,
            "scored_days": 0,
            "commit_chain": previous,
            "active_mae_kwh": None,
            "active_rmse_kwh": None,
            "final_branch_state_sha256": {"0.0": state_digest(branch[0.0])},
        }
        (run / "run.json").write_text(json.dumps(row))
        (study / "fixture-target.log").write_text("No forecast issued; retain null score\n")
        data = SimpleNamespace(
            root=inputs,
            namespace=("charged", "AMS"),
            entities={("charged", "AMS", "fixture"): summary},
            binding=lambda *args: copy.deepcopy(target_binding),
        )
        storage = RunBackup(study, backup, context, {7: data})
        return storage, entry, row, data

    def test_completed_null_run_and_source_restore_byte_identically_after_runtime_loss(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage, entry, row, data = self.fixture(root)
            before_rng = torch.get_rng_state().clone()
            storage.source(entry)
            self.assertTrue(torch.equal(before_rng, torch.get_rng_state()))
            storage.target(row)
            hashes = {
                p.relative_to(storage.study): digest(p)
                for p in storage.study.rglob("*")
                if p.is_file()
            }
            shutil.rmtree(storage.study)
            restored = root / "restored"
            restored.mkdir()
            reader = RunBackup(restored, storage.root, storage.context, {7: data}, resume=True)
            sources, runs = reader.restore()
            self.assertEqual(runs, [row])
            self.assertIsNone(runs[0]["active_mae_kwh"])
            self.assertEqual(sources[0]["sha256"], entry["sha256"])
            self.assertTrue(Path(sources[0]["path"]).is_relative_to(restored))
            self.assertEqual(
                {p.relative_to(restored): digest(p) for p in restored.rglob("*") if p.is_file()},
                hashes,
            )
            self.assertFalse((restored / "fixture-target/tick-0000/state.pt").exists())

    def test_execution_tuples_match_json_lists_but_changed_values_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage, entry, row, _ = self.fixture(Path(tmp))
            storage.source(entry)
            # Dataclass reports contain tuples; persisted JSON necessarily contains lists.
            row["method"] = {"proxy_order": (0, 1, 2), "thresholds": (0.1, 0.5)}
            row["policy_state"] = {"descriptor": (1.0, 2.0, 3.0)}
            report = storage.study / row["run_id"] / "run.json"
            report.write_text(json.dumps(row))
            storage.check_run(row)
            changed = copy.deepcopy(row)
            changed["policy_state"]["descriptor"] = (1.0, 9.0, 3.0)
            with self.assertRaisesRegex(ValueError, "Saved run report differs"):
                storage.check_run(changed)
            storage.target(row)
            self.assertTrue((storage.root / (row["run_id"] + ".receipt.json")).is_file())

    def test_wrong_context_overwrite_and_unmounted_directory_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage, entry, _, data = self.fixture(root)
            storage.source(entry)
            before = digest(storage.root / "source-seed42.zip")
            with self.assertRaises(ValueError):
                storage.source(entry)
            self.assertEqual(digest(storage.root / "source-seed42.zip"), before)
            bad = {**storage.context, "environment": {"different_gpu": True}}
            with self.assertRaises(ValueError):
                RunBackup(root / "new", storage.root, bad, {7: data}, resume=True)
            with self.assertRaises(ValueError):
                require_drive_mount(root / "backup", root)
            with patch.object(Path, "is_mount", return_value=True):
                require_drive_mount(root / "backup", root)
                with self.assertRaises(ValueError):
                    require_drive_mount(root.parent / "outside", root)

    def test_failed_copy_never_commits_receipt_and_pending_blocks_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage, entry, _, data = self.fixture(Path(tmp))
            actual_digest = digest
            with patch(
                "tools.durable_run_backup.digest",
                side_effect=lambda p: "0" * 64 if p.name.endswith(".pending") else actual_digest(p),
            ):
                with self.assertRaises(ValueError):
                    storage.source(entry)
            self.assertFalse(list(storage.root.glob("*.receipt.json")))
            self.assertTrue(list(storage.root.glob("*.pending")))
            with self.assertRaises(ValueError):
                RunBackup(Path(tmp) / "new", storage.root, storage.context, {7: data}, resume=True)

    def test_target_role_config_corruption_and_extra_files_are_not_published(self):
        for failure in ("role", "config", "bytes", "extra", "pending"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                storage, entry, row, data = self.fixture(Path(tmp))
                storage.source(entry)
                if failure == "role":
                    data.entities[("charged", "AMS", "fixture")]["role"] = "final"
                elif failure == "config":
                    row = copy.deepcopy(row)
                    row["binding"]["config"]["initial_training"]["seed"] = 43
                elif failure == "bytes":
                    (storage.study / "fixture-target/tick-0001/forecasts.json").write_text(
                        "changed"
                    )
                elif failure == "pending":
                    (storage.study / "fixture-target/.pending-0002").mkdir()
                else:
                    (storage.study / "fixture-target/secret.env").write_text(
                        "fixture, not a secret"
                    )
                with self.assertRaises(ValueError):
                    storage.target(row)
                self.assertFalse((storage.root / "fixture-target.receipt.json").exists())

    def test_corrupt_archive_or_missing_receipt_is_rejected_before_restore(self):
        for failure in ("bytes", "receipt"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                storage, entry, row, data = self.fixture(root)
                storage.source(entry)
                storage.target(row)
                if failure == "bytes":
                    (storage.root / "source-seed42.zip").write_bytes(b"corrupt")
                else:
                    (storage.root / "source-seed42.receipt.json").unlink()
                destination = root / "restored"
                destination.mkdir()
                reader = RunBackup(
                    destination, storage.root, storage.context, {7: data}, resume=True
                )
                with self.assertRaises(ValueError):
                    reader.restore()

    def test_unsafe_payload_is_rejected_even_with_recomputed_transport_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage, _, _, data = self.fixture(root)
            envelope = {
                "schema": "ev-completed-backup-v1",
                "context_sha256": storage.context_sha,
                "name": "malicious",
                "record": {"kind": "source"},
            }
            archive = storage.root / "malicious.zip"
            with zipfile.ZipFile(archive, "x") as z:
                z.writestr("backup-record.json", canonical(envelope))
                z.writestr("study/../outside.txt", "must not escape")
            envelope.update(bytes=archive.stat().st_size, sha256=digest(archive))
            (storage.root / "malicious.receipt.json").write_bytes(canonical(envelope))
            destination = root / "restored"
            destination.mkdir()
            reader = RunBackup(destination, storage.root, storage.context, {7: data}, resume=True)
            with self.assertRaises(ValueError):
                reader.restore()
            self.assertFalse((root / "outside.txt").exists())


if __name__ == "__main__":
    unittest.main()
