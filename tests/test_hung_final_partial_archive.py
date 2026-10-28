"""Synthetic partial Final checkpoint, corruption and create-only restore checks."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiments.hung_sprint2.final_partial_archive import (
    create_partial_checkpoint,
    restore_partial_checkpoint,
    verify_partial_checkpoint,
)
from tests.test_hung_final_archive import ROOT, fixture

IDS = ["controller", "drift"]


class PartialCheckpointTests(unittest.TestCase):
    def setUp(self) -> None:
        (ROOT / ".cache").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".cache")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.context = fixture(self.root, selected_ids=set(IDS))
        self.context["lock"] = {
            "output_root": str(self.context["output_root"]),
            "jobset": {"count": 3, "sha256": "b" * 64},
            "execution_plan": {"sha256": "c" * 64},
        }
        self.package = self.root / "checkpoint-v1"

    def test_partial_restore_preserves_prior_root_and_rejects_overwrite(self) -> None:
        created = create_partial_checkpoint(self.context, IDS, self.package)
        self.assertEqual(created["status"], "PARTIAL_CHECKPOINT_VERIFIED_NOT_FINAL_RESULT")
        self.assertEqual((created["completed_jobs"], created["full_jobs"]), (2, 3))
        self.assertEqual(
            set(created["job_artifacts"]["drift"]), {"drift_reference", "target_init", "replay"}
        )
        with self.assertRaisesRegex(ValueError, "package exists"):
            create_partial_checkpoint(self.context, IDS, self.package)
        with self.assertRaisesRegex(ValueError, "target must be absent"):
            restore_partial_checkpoint(self.context, self.package, self.context["output_root"])
        old = self.root / "old-output-preserved"
        self.context["output_root"].rename(old)
        restored = restore_partial_checkpoint(
            self.context, self.package, self.context["output_root"]
        )
        self.assertEqual(restored["status"], "PARTIAL_CHECKPOINT_RESTORED_NOT_FINAL_RESULT")
        self.assertTrue((old / "stages" / "controller" / "replay" / "run_manifest.json").exists())
        self.assertTrue(
            (
                self.context["output_root"]
                / "stages"
                / "drift"
                / "drift_reference"
                / "run_manifest.json"
            ).exists()
        )
        with self.assertRaisesRegex(ValueError, "target must be absent"):
            restore_partial_checkpoint(self.context, self.package, self.context["output_root"])

    def test_unknown_full_and_partial_stage_sets_fail_closed(self) -> None:
        for ids, message in (
            (["unknown"], "Unknown"),
            (["controller", "drift", "seasonal"], "proper completed-job subset"),
        ):
            with self.subTest(ids=ids):
                with self.assertRaisesRegex(ValueError, message):
                    create_partial_checkpoint(self.context, ids, self.package)
                self.assertFalse(self.package.exists())
        receipt = self.context["output_root"] / "receipts" / "drift" / "drift_reference.json"
        receipt.unlink()
        with self.assertRaisesRegex(ValueError, "stages differ"):
            create_partial_checkpoint(self.context, IDS, self.package)

    def test_extra_job_and_changed_artifact_fail_closed(self) -> None:
        extra = self.context["output_root"] / "stages" / "seasonal"
        extra.mkdir()
        with self.assertRaisesRegex(ValueError, "jobset differs"):
            create_partial_checkpoint(self.context, IDS, self.package)
        self.assertFalse((self.package / "checkpoint.json").exists())

    def test_changed_stage_artifact_cannot_publish_checkpoint(self) -> None:
        artifact = (
            self.context["output_root"]
            / "stages"
            / "controller"
            / "replay"
            / "nested"
            / "artifact.bin"
        )
        artifact.write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "stage receipt differs"):
            create_partial_checkpoint(self.context, IDS, self.package)
        self.assertFalse((self.package / "checkpoint.json").exists())

    def test_archive_and_full_lock_pins_are_rechecked(self) -> None:
        create_partial_checkpoint(self.context, IDS, self.package)
        changed = {
            **self.context,
            "lock": {**self.context["lock"], "jobset": {"count": 3, "sha256": "d" * 64}},
        }
        with self.assertRaisesRegex(ValueError, "full lock/jobset/plan binding differs"):
            verify_partial_checkpoint(changed, self.package)
        archive = self.package / "completed-stages.zip"
        with archive.open("ab") as stream:
            stream.write(b"tamper")
        with self.assertRaisesRegex(ValueError, "archive bytes differ"):
            verify_partial_checkpoint(self.context, self.package)

    def test_package_extra_file_or_false_full_status_rejected(self) -> None:
        create_partial_checkpoint(self.context, IDS, self.package)
        (self.package / "unexpected.txt").write_text("extra", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing/extra members"):
            verify_partial_checkpoint(self.context, self.package)
        (self.package / "unexpected.txt").unlink()
        manifest = self.package / "checkpoint.json"
        value = json.loads(manifest.read_text(encoding="utf-8"))
        value["status"] = "FINAL_COMPLETE"
        manifest.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "schema/status differs"):
            verify_partial_checkpoint(self.context, self.package)


if __name__ == "__main__":
    unittest.main()
