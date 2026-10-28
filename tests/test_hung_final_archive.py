"""Synthetic Final archive authentication; no Final data or training."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2.dispatch_state import stage_receipt
from experiments.hung_sprint2.final_archive import create_archive, readback_archive

ROOT = Path(__file__).resolve().parents[1]
LOCK_SHA = "a" * 64


def write(path: Path, value: dict | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True) if isinstance(value, dict) else value,
        encoding="utf-8",
    )


def fixture(root: Path) -> dict:
    output = root / "final-output"
    write(
        output / "final_lock_identity.json",
        {"schema": "hung-final-output-identity-v1", "lock_sha256": LOCK_SHA},
    )
    jobs = [
        {"job_id": "controller", "method": "confidence"},
        {"job_id": "drift", "method": "drift"},
        {"job_id": "seasonal", "method": "seasonal_naive"},
    ]
    plan = [
        {"job_id": "controller", "target_init": {"steps": 1}},
        {"job_id": "drift", "target_init": {"steps": 1}},
        {"job_id": "seasonal", "target_init": None},
    ]
    for job, stages in (
        ("controller", ("target_init", "replay")),
        ("drift", ("drift_reference", "target_init", "replay")),
        ("seasonal", ("replay",)),
    ):
        for stage in stages:
            stage_root = output / "stages" / job / stage
            write(
                stage_root / "run_manifest.json",
                {
                    "status": "completed",
                    "final_lock_sha256": LOCK_SHA,
                    "final_job_id": job,
                },
            )
            write(stage_root / "nested" / "artifact.bin", f"{job}-{stage}-bytes")
            log = output / "logs" / job / f"{stage}.json"
            write(
                log,
                {
                    "schema": "hung-final-stage-log-v1",
                    "lock_sha256": LOCK_SHA,
                    "job_id": job,
                    "stage": stage,
                    "manifest_sha256": sha256_file(stage_root / "run_manifest.json"),
                },
            )
            binding = {
                "schema": "hung-final-stage-binding-v1",
                "lock_sha256": LOCK_SHA,
                "job_id": job,
                "stage": stage,
            }
            write(
                output / "receipts" / job / f"{stage}.json",
                stage_receipt(binding, stage_root, log),
            )
    return {
        "input_runs_verified": True,
        "output_root": output,
        "lock_sha256": LOCK_SHA,
        "jobs": jobs,
        "plan": plan,
    }


class FinalArchiveTests(unittest.TestCase):
    def setUp(self) -> None:
        (ROOT / ".cache").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".cache")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.context = fixture(self.root)
        self.archive = self.root / "new-archive.zip"

    def test_independent_readback_and_create_only(self) -> None:
        result = create_archive(self.context, self.archive)
        self.assertEqual(result["status"], "local_archive_readback_verified")
        self.assertEqual(set(result["jobs"]), {"controller", "drift", "seasonal"})
        self.assertEqual(set(result["jobs"]["drift"]), {"drift_reference", "target_init", "replay"})
        self.assertEqual(len(result["jobs"]["controller"]["replay"]["artifacts"]), 2)
        again = readback_archive(
            self.archive,
            result["archive"]["sha256"],
            LOCK_SHA,
            self.context["jobs"],
            self.context["plan"],
        )
        self.assertEqual(again["jobs"], result["jobs"])
        with self.assertRaisesRegex(ValueError, "already exists"):
            create_archive(self.context, self.archive)

    def test_partial_extra_or_changed_stage_fails_before_publication(self) -> None:
        receipt = self.context["output_root"] / "receipts" / "controller" / "replay.json"
        receipt.unlink()
        with self.assertRaisesRegex(ValueError, "stages differ"):
            create_archive(self.context, self.archive)
        self.assertFalse(self.archive.exists())
        fixture(self.root)
        extra = self.context["output_root"] / "stages" / "unknown"
        extra.mkdir()
        with self.assertRaisesRegex(ValueError, "jobset differs"):
            create_archive(self.context, self.archive)
        self.assertFalse(self.archive.exists())
        extra.rmdir()
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
            create_archive(self.context, self.archive)
        self.assertFalse(self.archive.exists())

    def test_archive_tamper_and_wrong_jobset_fail_readback(self) -> None:
        result = create_archive(self.context, self.archive)
        with self.assertRaisesRegex(ValueError, "exact jobset differs"):
            readback_archive(
                self.archive,
                result["archive"]["sha256"],
                LOCK_SHA,
                [{"job_id": "other"}],
                [{"job_id": "other", "target_init": None}],
            )
        with self.archive.open("ab") as stream:
            stream.write(b"tamper")
        with self.assertRaisesRegex(ValueError, "archive SHA differs"):
            readback_archive(
                self.archive,
                result["archive"]["sha256"],
                LOCK_SHA,
                self.context["jobs"],
                self.context["plan"],
            )

    def test_missing_drift_reference_stage_fails_closed(self) -> None:
        drift_receipt = self.context["output_root"] / "receipts" / "drift" / "drift_reference.json"
        drift_receipt.unlink()
        with self.assertRaisesRegex(ValueError, "stages differ"):
            create_archive(self.context, self.archive)
        self.assertFalse(self.archive.exists())

    def test_archive_crc_detects_corrupt_member_even_with_new_outer_sha(self) -> None:
        create_archive(self.context, self.archive)
        corrupt = self.root / "corrupt-copy.zip"
        with ZipFile(self.archive) as source, ZipFile(corrupt, "x") as target:
            for name in source.namelist():
                content = source.read(name)
                if name == "stages/controller/replay/nested/artifact.bin":
                    content += b"corrupt"
                target.writestr(name, content)
        with self.assertRaisesRegex(ValueError, "byte/SHA/CRC mismatch"):
            readback_archive(
                corrupt,
                sha256_file(corrupt),
                LOCK_SHA,
                self.context["jobs"],
                self.context["plan"],
            )


if __name__ == "__main__":
    unittest.main()
