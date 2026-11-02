"""Offline regressions for exact-stage compact saved-shard verification."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from tools import hung_kaggle_compact_proof as proof


def encoded(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True).encode()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class CompactProofTests(unittest.TestCase):
    def setUp(self) -> None:
        cache = Path(__file__).resolve().parents[1] / ".cache"
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fixture(
        self,
        *,
        receipt_stages: list[str] | None = None,
        omit_file: str | None = None,
        add_foreign: bool = False,
        manifest_status: str = "completed",
    ) -> tuple:
        cell = {
            "id": "cell",
            "budget": 7,
            "seed": 11,
            "entity_id": "1405",
            "input_manifest_sha256": "a" * 64,
        }
        job = {
            "id": "job_a",
            "cell": "cell",
            "config": "main",
            "method": "target_only",
            "device": "cpu",
            "source": None,
            "target": None,
        }
        config_bytes = encoded({"replay": {"block_days": 7, "max_origins": 22}})
        config_sha = digest(config_bytes)
        config = {
            "id": "main",
            "sha256": config_sha,
        }
        plan = {
            "code_commit": proof.MODEL_CODE,
            "scope": "development_only",
            "output_root": "/p/output",
            "jobs": [job],
            "cells": [cell],
            "configs": [config],
        }
        plan_bytes = encoded(plan)
        partition = {
            "plan_sha256": digest(plan_bytes),
            "shards": [{"id": "shard_test", "job_ids": ["job_a"]}],
        }
        partition_bytes = encoded(partition)
        plan_path, partition_path = self.root / "plan.json", self.root / "shards.json"
        plan_path.write_bytes(plan_bytes)
        partition_path.write_bytes(partition_bytes)

        code = {"commit": proof.MODEL_CODE, "executed_sources": {"module": "c" * 64}}
        members = {
            "dispatch_identity.json": encoded(
                {
                    "schema": "hung-resumable-dispatch-v1",
                    "plan_sha256": digest(plan_bytes),
                    "shards_sha256": digest(partition_bytes),
                    "jobs": 1,
                    "stages": 3,
                    "code": code,
                    "single_code": code,
                }
            )
        }
        names = proof.planned_stages(job, json.loads(config_bytes))
        stage_pins = {}
        cell_digest = digest(encoded(cell))
        for stage in names:
            checkpoint, journal = proof.expected_stage_files(stage, job["method"])
            is_replay = stage.startswith("replay-")
            fields = {
                "status": manifest_status,
                "run_id": stage,
                "code": {"commit": proof.MODEL_CODE, **code},
                "binding": {
                    "entity_id": "1405",
                    "history_days": 7,
                    "input_manifest_sha256": "a" * 64,
                },
                "initial_checkpoint_sha256"
                if not is_replay
                else "final_runner_checkpoint_sha256": digest(b"checkpoint"),
            }
            files = {
                "run_manifest.json": encoded(fields),
                "dispatch_measurement.json": b"{}",
                checkpoint: b"checkpoint",
            }
            if journal:
                files[journal] = b"journal\n"
                fields["forecast_journal"] = {"file": journal, "sha256": digest(files[journal])}
                files["run_manifest.json"] = encoded(fields)
            if omit_file:
                files.pop(omit_file, None)
            stage_root = f"jobs/job_a/{stage}/"
            members.update({stage_root + name: content for name, content in files.items()})
            args = [
                "target-only-init" if stage == "target-only-init" else "replay-development",
                "--manifest-sha256",
                "a" * 64,
                "--entity-id",
                "1405",
                "--output",
                "/p/output/jobs/job_a/" + stage,
            ]
            if is_replay:
                args += [
                    "--max-origins",
                    stage.removeprefix("replay-"),
                    "--device",
                    "cpu",
                    "--method",
                    "target_only",
                ]
            module = "experiments.supporting_pipeline.single_baseline_cli"
            log = (
                encoded(
                    {
                        "command": ["python", "-m", module, *args],
                        "config_sha256": config_sha,
                        "input_manifest_sha256": "a" * 64,
                    }
                )
                + b"\n"
            )
            members[f"logs/job_a/{stage}.log"] = log
            stage_receipt = {
                "binding": {
                    "job": job,
                    "stage": stage,
                    "plan_sha256": digest(plan_bytes),
                    "shards_sha256": digest(partition_bytes),
                    "input_manifest_sha256": "a" * 64,
                    "config_sha256": config_sha,
                    "cell_sha256": cell_digest,
                    "module": module,
                    "args": args,
                },
                "files": {
                    name: {"bytes": len(content), "sha256": digest(content)}
                    for name, content in files.items()
                },
                "log": {"bytes": len(log), "sha256": digest(log)},
            }
            stage_bytes = encoded(stage_receipt)
            members[f"receipts/job_a/{stage}.json"] = stage_bytes
            stage_pins[stage] = digest(stage_bytes)
        if receipt_stages is not None:
            stage_pins = {name: stage_pins[name] for name in receipt_stages if name in stage_pins}
            for name in receipt_stages:
                stage_pins.setdefault(name, "f" * 64)
        members["receipts/job_a/job.json"] = encoded(
            {
                "job_id": "job_a",
                "plan_sha256": digest(plan_bytes),
                "shards_sha256": digest(partition_bytes),
                "stages": stage_pins,
            }
        )
        if add_foreign:
            members["jobs/job_a/replay-21/foreign.txt"] = b"unexpected"
        archive_path = self.root / "artifacts.zip"
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in members.items():
                archive.writestr(name, content)
        return (
            plan_path,
            partition_path,
            plan_path,
            partition_path,
            archive_path,
            "shard_test",
            proof.file_sha256(archive_path),
            archive_path.stat().st_size,
            1,
            2,
            {"main": config_bytes},
        )

    def run_fixture(self, args: tuple) -> dict:
        with (
            patch.object(proof, "PARENT_PLAN_SHA", proof.file_sha256(args[0])),
            patch.object(proof, "PARENT_PARTITION_SHA", proof.file_sha256(args[1])),
        ):
            return proof.verify_shard(*args)

    def test_accepts_exact_stage_set_and_inventory(self) -> None:
        result = self.run_fixture(self.fixture())
        self.assertEqual(result["schema"], "hung-kaggle-compact-shard-proof-v2")
        self.assertEqual(result["rows"][0]["status"], "VERIFIED_ARCHIVE_BYTES_AND_STAGE_PLAN")
        self.assertEqual(len(result["rows"][0]["stage_receipt_sha256"]), 3)

    def test_rejects_empty_or_subset_or_unexpected_stages(self) -> None:
        for stages in (
            [],
            ["replay-21"],
            ["target-only-init", "replay-21", "replay-22", "foreign"],
        ):
            with (
                self.subTest(stages=stages),
                self.assertRaisesRegex(ValueError, "Job receipt binding"),
            ):
                self.run_fixture(self.fixture(receipt_stages=stages))

    def test_rejects_missing_checkpoint_or_journal(self) -> None:
        for filename in ("runner.pt", "forecasts.jsonl"):
            with (
                self.subTest(filename=filename),
                self.assertRaisesRegex(ValueError, "Missing required stage files"),
            ):
                self.run_fixture(self.fixture(omit_file=filename))

    def test_rejects_unreceipted_archive_member(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unexpected or unreceipted"):
            self.run_fixture(self.fixture(add_foreign=True))

    def test_rejects_wrong_archive_sha(self) -> None:
        args = self.fixture()
        with self.assertRaisesRegex(ValueError, "Archive SHA mismatch"):
            self.run_fixture(args[:6] + ("0" * 64,) + args[7:])

    def test_rejects_missing_or_changed_pinned_config_bytes(self) -> None:
        args = self.fixture()
        with self.assertRaisesRegex(ValueError, "Pinned config set mismatch"):
            self.run_fixture(args[:-1] + ({},))
        with self.assertRaisesRegex(ValueError, "Pinned config SHA mismatch"):
            self.run_fixture(args[:-1] + ({"main": b"{}"},))

    def test_rejects_failed_manifest(self) -> None:
        with self.assertRaisesRegex(ValueError, "Run manifest identity mismatch"):
            self.run_fixture(self.fixture(manifest_status="failed"))


if __name__ == "__main__":
    unittest.main()
