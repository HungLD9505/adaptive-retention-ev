"""CPU checkpoint transport verification; synthetic weights, never real-data fitting."""

import copy
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import test_durable_run_backup as backup_fixtures

from ev_models.checkpoint import digest
from tools.city_source_outbox import package_source
from tools.durable_run_backup import canonical
from tools.verify_city_source import restore_source


class VerifyCitySourceTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, dict, dict]:
        storage, entry, _, data = backup_fixtures.DurableBackupTests().fixture(root)
        storage.context.update(
            schema="ev-kaggle-city-source-outbox-v1",
            backend="local_pending_external_publication",
            cohort_sha256="c" * 64,
            primary_sha256="d" * 64,
            environment_profile_sha256="e" * 64,
            core_files={"ev_runner/run.py": "fixture-runner-fingerprint"},
            numpy_version="fixture",
        )
        (storage.root / "context.json").write_bytes(canonical(storage.context))
        storage.context_sha = digest(storage.root / "context.json")
        entry["run"]["training_examples"] = 3
        (storage.study / "source-seed42/run.json").write_text(json.dumps(entry["run"]))
        (storage.study / "source-seed42-complete.json").write_text(json.dumps(entry))
        data.entities[("charged", "AMS", "fixture-source")] = {
            "role": "source",
            "initial_trainable": 3,
        }
        storage.source(entry)
        record = {
            "schema": "ev-one-city-source-outbox-v1",
            "status": "awaiting_external_publication",
            "namespace": "charged-AMS",
            "seed": 42,
            "context_sha256": storage.context_sha,
            "source_checkpoint_sha256": entry["sha256"],
            "expected_source_examples": 3,
            "code": {**entry["run"]["code"], "files": storage.context["core_files"]},
            **{
                key: storage.context[key]
                for key in (
                    "source_epochs",
                    "cohort_sha256",
                    "primary_sha256",
                    "environment_profile_sha256",
                    "source_population_sha256",
                    "source_manifest_sha256",
                    "environment",
                )
            },
        }
        archive = root / "source-handoff.zip"
        package_source(storage.root, record, archive)
        return archive, storage.context, {7: data}

    def rewrite(self, archive: Path, record_change=None, extra=None) -> Path:
        result = archive.with_name("modified.zip")
        with zipfile.ZipFile(archive) as source, zipfile.ZipFile(result, "x") as target:
            for name in source.namelist():
                value = source.read(name)
                if name == "source-handoff-record.json" and record_change:
                    value = json.dumps({**json.loads(value), **record_change}).encode()
                target.writestr(name, value)
            if extra:
                target.writestr(extra, b"preserve outside")
        return result

    def test_source_cpu_restore_rechecks_actual_checkpoint_without_training(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive, context, data = self.fixture(root)
            proof = restore_source(archive, digest(archive), root / "verified", context, data)
            self.assertEqual(proof["source_examples"], 3)
            self.assertEqual(proof["namespace"], "charged-AMS")
            self.assertEqual(proof["status"], "independent_source_content_verified")
            self.assertTrue((root / "verified/study/source-seed42/epoch-10.pt").is_file())
            self.assertFalse((root / "verified/study/fixture-target").exists())
            source_report = json.loads((root / "verified/study/source-seed42/run.json").read_text())
            self.assertNotEqual(source_report["code"]["files"], proof["producer_code"]["files"])
            with self.assertRaises(ValueError):
                restore_source(archive, digest(archive), root / "verified", context, data)

    def test_changed_pin_context_or_producer_claim_is_not_accepted(self) -> None:
        for failure in ("pin", "context", "claim", "count", "producer", "final"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                archive, context, data = self.fixture(root)
                checksum = digest(archive)
                if failure == "pin":
                    checksum = "0" * 64
                elif failure == "context":
                    context = {**context, "source_manifest_sha256": "9" * 64}
                else:
                    changes = {
                        "claim": {"status": "remote_verified"},
                        "count": {"expected_source_examples": 9},
                        "producer": {"code": {"dirty": False, "files": {}, "commit": "wrong"}},
                    }
                    if failure == "final":
                        data[7].entities[("charged", "AMS", "fixture-source")]["role"] = "final"
                    else:
                        archive = self.rewrite(archive, record_change=changes[failure])
                        checksum = digest(archive)
                with self.assertRaises(ValueError):
                    restore_source(archive, checksum, root / "rejected", context, data)
                self.assertFalse((root / "rejected/source-verification.json").exists())

    def test_extra_traversal_alias_or_unaccepted_seed_is_rejected(self) -> None:
        for name in ("../escape", "backup/CONTEXT.JSON", "backup/source-seed43.zip"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                archive, context, data = self.fixture(root)
                changed = self.rewrite(archive, extra=name)
                with self.assertRaises(ValueError):
                    restore_source(changed, digest(changed), root / "rejected", context, data)
                self.assertFalse((root / "escape").exists())
                self.assertFalse((root / "rejected").exists())

    def test_incomplete_source_payload_is_rejected_after_transport_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive, context, data = self.fixture(root)
            wrong = copy.deepcopy(context)
            wrong["source_training"]["epochs"] = 9
            with self.assertRaises(ValueError):
                restore_source(archive, digest(archive), root / "rejected", wrong, data)


if __name__ == "__main__":
    unittest.main()
