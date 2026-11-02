"""Offline provider-source and handoff preflight fixtures; no Kaggle call."""

import hashlib
import json
import tempfile
import unittest
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from experiments.supporting_pipeline.kaggle_final_locked_v1 import (
    _quota_gate,
    inspect_handoff,
    run_all,
)

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "experiments/supporting_pipeline/kaggle_final_locked_v1.py"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _handoff(root: Path) -> tuple[Path, str, str]:
    dataset = root / "private-v1"
    dataset.mkdir()
    (dataset / "code.bundle").write_bytes(b"synthetic bundle")
    lock_sha = "a" * 64
    (dataset / "lock.json").write_text(
        json.dumps(
            {"schema": "hung-final-lock-v1", "scope": "final_only", "code_commit": "b" * 40}
        ),
        encoding="utf-8",
    )
    lock_sha = _sha(dataset / "lock.json")
    manifest = {
        "schema": "hung-final-provider-handoff-v1",
        "dataset_version": "example/final-private/1",
        "code_commit": "b" * 40,
        "lock_sha256": lock_sha,
        "wrapper_sha256": _sha(SOURCE),
        "files": {
            "code.bundle": {
                "bytes": (dataset / "code.bundle").stat().st_size,
                "sha256": _sha(dataset / "code.bundle"),
                "target": None,
            },
            "lock.json": {
                "bytes": (dataset / "lock.json").stat().st_size,
                "sha256": lock_sha,
                "target": ".cache/final/lock.json",
            },
        },
    }
    path = dataset / "final-handoff-manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path, _sha(path), manifest["dataset_version"]


class KaggleFinalSourceTests(unittest.TestCase):
    def test_source_compiles_and_mount_is_exact(self) -> None:
        compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec")
        with tempfile.TemporaryDirectory() as directory:
            manifest, sha, version = _handoff(Path(directory))
            root, record = inspect_handoff(Path(directory), sha, version, SOURCE)
            self.assertEqual(root, manifest.parent)
            self.assertEqual(record["lock_sha256"], _sha(root / "lock.json"))
            with self.assertRaisesRegex(ValueError, "Explicit --run-all"):
                run_all(Namespace(run_all=False))

    def test_changed_mount_and_extra_file_fail_before_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest, sha, version = _handoff(Path(directory))
            (manifest.parent / "code.bundle").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "handoff bytes differ"):
                inspect_handoff(Path(directory), sha, version, SOURCE)
            (manifest.parent / "code.bundle").write_bytes(b"synthetic bundle")
            (manifest.parent / "extra.txt").write_text("unexpected", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "extra or missing files"):
                inspect_handoff(Path(directory), sha, version, SOURCE)

    def test_stale_or_insufficient_quota_fails_before_gpu_access(self) -> None:
        resources = {
            "provider": "kaggle",
            "device": "cuda",
            "estimated_gpu_seconds": 7200,
            "estimated_output_bytes": 100,
            "min_free_bytes": 100,
        }
        args = Namespace(
            quota_observed_utc=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            available_gpu_seconds=20000,
            available_session_seconds=20000,
            available_output_bytes=1000,
        )
        with self.assertRaisesRegex(ValueError, "stale"):
            _quota_gate(args, resources, 1000)
        args.quota_observed_utc = datetime.now(timezone.utc).isoformat()
        args.available_gpu_seconds = 7201
        with self.assertRaisesRegex(ValueError, "GPU/session quota"):
            _quota_gate(args, resources, 1000)
