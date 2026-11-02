"""Independent transport/profile fixtures; no real data, network, GPU or fitting."""

import argparse
import copy
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from ev_models.checkpoint import digest
from tools.city_source_outbox import package_source, require_outbox, run, validate_environment


class CitySourceOutboxTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, dict]:
        backup = root / "backup"
        backup.mkdir()
        context = {"schema": "ev-kaggle-city-source-outbox-v1", "namespace": ["charged", "LOA"]}
        (backup / "context.json").write_text(json.dumps(context))
        envelope = {
            "schema": "ev-completed-backup-v1",
            "context_sha256": digest(backup / "context.json"),
            "name": "source-seed42",
            "record": {"kind": "source", "entry": {"seed": 42, "sha256": "a" * 64}},
        }
        archive = backup / "source-seed42.zip"
        with zipfile.ZipFile(archive, "x") as output:
            output.writestr("backup-record.json", json.dumps(envelope))
            output.writestr("study/opaque-fixture.txt", "not a model or training result")
        receipt = {**envelope, "bytes": archive.stat().st_size, "sha256": digest(archive)}
        (backup / "source-seed42.receipt.json").write_text(json.dumps(receipt))
        return backup, {
            "schema": "ev-one-city-source-outbox-v1",
            "status": "awaiting_external_publication",
            "namespace": "charged-LOA",
            "seed": 42,
            "context_sha256": envelope["context_sha256"],
            "source_checkpoint_sha256": "a" * 64,
        }

    def test_one_source_wrapper_hashes_every_exact_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            backup, record = self.fixture(root)
            path = root / "handoff.zip"
            artifact = package_source(backup, record, path)
            self.assertEqual(artifact["sha256"], digest(path))
            with zipfile.ZipFile(path) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                self.assertEqual(len(manifest), 3)
                self.assertEqual(json.loads(archive.read("source-handoff-record.json")), record)
                for name in manifest:
                    self.assertEqual(archive.read("backup/" + name), (backup / name).read_bytes())
            with self.assertRaises(FileExistsError):
                package_source(backup, record, path)

    def test_unexpected_or_pending_payload_stops_export(self) -> None:
        for name in ("unaccepted.zip", "source-seed43.zip", "interrupted.pending"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                backup, record = self.fixture(root)
                (backup / name).write_bytes(b"preserve me")
                with self.assertRaises(ValueError):
                    package_source(backup, record, root / "never.zip")
                self.assertEqual((backup / name).read_bytes(), b"preserve me")

    def test_changed_city_seed_checkpoint_or_acceptance_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            backup, record = self.fixture(root)
            for key, value in (
                ("namespace", "charged-AMS"),
                ("seed", True),
                ("seed", 41),
                ("context_sha256", "0" * 64),
                ("source_checkpoint_sha256", "b" * 64),
                ("status", "remote_verified"),
            ):
                bad = {**record, key: value}
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    package_source(backup, bad, root / "never.zip")
            self.assertFalse((root / "never.zip").exists())

    def test_changed_source_archive_fails_without_repairing_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            backup, record = self.fixture(root)
            before = (backup / "source-seed42.receipt.json").read_bytes()
            (backup / "source-seed42.zip").write_bytes(b"changed bytes")
            with self.assertRaises(ValueError):
                package_source(backup, record, root / "never.zip")
            self.assertEqual((backup / "source-seed42.receipt.json").read_bytes(), before)

    def test_archive_record_must_match_committed_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            backup, record = self.fixture(root)
            archive = backup / "source-seed42.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("backup-record.json", json.dumps({"schema": "wrong"}))
            receipt_path = backup / "source-seed42.receipt.json"
            receipt = json.loads(receipt_path.read_text())
            receipt.update(bytes=archive.stat().st_size, sha256=digest(archive))
            receipt_path.write_text(json.dumps(receipt))
            with self.assertRaises(ValueError):
                package_source(backup, record, root / "never.zip")

    def test_output_cannot_overwrite_data_existing_runs_or_cloud_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cloud = root / "cloud"
            cloud.mkdir()
            data = cloud / "inputs"
            data.mkdir()
            require_outbox(cloud / "new-run", data, cloud)
            existing = cloud / "existing"
            existing.mkdir()
            for path in (cloud, cloud / "inputs/overwrite", root / "outside", existing):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    require_outbox(path, data, cloud)

    def test_runtime_profile_rejects_cpu_numpy_or_environment_drift(self) -> None:
        actual = {"device": "cuda", "deterministic_algorithms": True, "torch": "fixture"}
        profile = {
            "schema": "ev-city-cloud-environment-v1",
            "environment": actual,
            "numpy": "fixture",
        }
        validate_environment(actual, profile, "fixture")
        for change in (
            {**actual, "device": "cpu"},
            {**actual, "deterministic_algorithms": False},
            {**actual, "torch": "changed"},
        ):
            with self.assertRaises(ValueError):
                validate_environment(change, profile, "fixture")
        bad = copy.deepcopy(profile)
        bad["numpy"] = "changed"
        with self.assertRaises(ValueError):
            validate_environment(actual, bad, "fixture")

    def test_no_cuda_stops_before_dependencies_or_fitting(self) -> None:
        with (
            patch("tools.city_source_outbox.torch.cuda.is_available", return_value=False),
            patch("tools.city_source_outbox.train_source") as trainer,
            self.assertRaises(ValueError),
        ):
            run(argparse.Namespace(seed=42))
        trainer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
