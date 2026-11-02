"""Fake-provider checks for create-once Final Kaggle transport preparation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ev_inputs.hourly_reader import sha256_file
from experiments.supporting_pipeline.final_archive import create_archive
from experiments.supporting_pipeline.final_transport import (
    cpu_kernel_spec,
    prepare_upload,
    upload_once,
    verify_remote_receipt,
)
from tests.test_hung_final_archive import ROOT, fixture, write


class FinalTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        (ROOT / ".cache").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".cache")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.context = fixture(self.root)
        self.jobset = self.root / "lock" / "jobset.json"
        self.plan = self.root / "lock" / "plan.json"
        write(self.jobset, {"schema": "hung-final-jobset-v1", "jobs": self.context["jobs"]})
        write(self.plan, {"schema": "hung-final-execution-plan-v1", "jobs": self.context["plan"]})
        self.context["lock"] = {
            "schema": "hung-final-lock-v1",
            "scope": "final_only",
            "jobset": self.pin(self.jobset),
            "execution_plan": self.pin(self.plan),
        }
        self.lock = self.root / "lock" / "lock.json"
        write(self.lock, self.context["lock"])
        self.context = fixture(self.root, sha256_file(self.lock))
        self.context["lock"] = json.loads(self.lock.read_text(encoding="utf-8"))
        self.archive = self.root / "local-final.zip"
        create_archive(self.context, self.archive)
        self.packet = self.root / "new-packet"

    @staticmethod
    def pin(path: Path) -> dict:
        return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}

    def prepare(self) -> dict:
        return prepare_upload(self.context, self.lock, self.archive, self.packet)

    def test_preparation_binds_archive_jobset_plan_and_cpu_source(self) -> None:
        prepared = self.prepare()
        self.assertEqual(prepared["dataset"].split("/")[-1], "1")
        self.assertIn(self.context["lock_sha256"][:12], prepared["dataset"])
        source = (self.packet / "cpu_readback.py").read_text(encoding="utf-8")
        self.assertEqual(
            sha256_file(self.packet / "cpu_readback.py"), prepared["cpu_source_sha256"]
        )
        self.assertIn("readback_archive", source)
        compile(source, "cpu_readback.py", "exec")
        spec = cpu_kernel_spec(self.packet)
        self.assertEqual(spec["dataset_data_sources"], [prepared["dataset"]])
        self.assertEqual(spec["expected_version"], 1)
        self.assertFalse(spec["enable_gpu"])
        self.assertFalse(spec["enable_internet"])
        self.assertTrue(spec["is_private"])
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.prepare()

    def test_acknowledged_upload_attempt_is_create_once(self) -> None:
        prepared = self.prepare()
        calls = []

        def create(owner: str, slug: str, folder: Path) -> None:
            calls.append((owner, slug, folder))

        result = upload_once(self.packet, create)
        self.assertEqual(result["status"], "CREATE_ACKNOWLEDGED_READBACK_PENDING")
        self.assertEqual(len(calls), 1)
        self.assertEqual(f"{calls[0][0]}/{calls[0][1]}/1", prepared["dataset"])
        self.assertEqual(calls[0][2], self.packet / "payload")
        with self.assertRaisesRegex(ValueError, "already attempted"):
            upload_once(self.packet, create)
        self.assertEqual(len(calls), 1)

    def test_http499_is_uncertain_and_never_retried(self) -> None:
        self.prepare()
        calls = []

        def create(*args) -> None:
            calls.append(args)
            error = RuntimeError("unknown create outcome")
            error.response = SimpleNamespace(status_code=499)
            raise error

        result = upload_once(self.packet, create)
        self.assertEqual(result["status"], "UNCERTAIN_HTTP499")
        with self.assertRaisesRegex(ValueError, "already attempted"):
            upload_once(self.packet, create)
        self.assertEqual(len(calls), 1)

    def test_remote_receipt_requires_exact_dataset_lock_archive_and_count(self) -> None:
        prepared = self.prepare()
        manifest = json.loads(
            (self.packet / "payload" / "final-transport-manifest.json").read_text(encoding="utf-8")
        )
        receipt = {
            "schema": "hung-final-remote-readback-v1",
            "status": "REMOTE_ARCHIVE_READBACK_VERIFIED",
            "dataset": prepared["dataset"],
            "readback_kernel": cpu_kernel_spec(self.packet)["slug"] + "/1",
            "manifest_sha256": prepared["manifest_sha256"],
            "lock_sha256": manifest["lock_sha256"],
            "archive": manifest["files"]["archive.zip"],
            "jobs": manifest["jobs"],
        }
        path = self.root / "remote-receipt.json"
        write(path, receipt)
        self.assertEqual(verify_remote_receipt(self.packet, path), receipt)
        for field, altered in (
            ("jobs", receipt["jobs"] - 1),
            ("dataset", "other/dataset/1"),
            ("readback_kernel", receipt["readback_kernel"].replace("/1", "/2")),
            ("lock_sha256", "f" * 64),
            ("archive", {**receipt["archive"], "bytes": receipt["archive"]["bytes"] - 1}),
        ):
            with self.subTest(field=field):
                changed = {**receipt, field: altered}
                write(path, changed)
                with self.assertRaisesRegex(ValueError, "receipt differs"):
                    verify_remote_receipt(self.packet, path)

    def test_changed_jobset_is_rejected_before_packet_creation(self) -> None:
        with self.jobset.open("a", encoding="utf-8") as stream:
            stream.write(" ")
        with self.assertRaisesRegex(ValueError, "jobset/plan pin differs"):
            self.prepare()
        self.assertFalse(self.packet.exists())


if __name__ == "__main__":
    unittest.main()
