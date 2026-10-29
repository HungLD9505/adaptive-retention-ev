"""Synthetic lock-first Final ZIP materialization checks."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from zipfile import ZipFile

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2.final_extract import materialize_locked_inputs
from experiments.hung_sprint2.final_lock import MIN_FREE_BYTES, ROOT, validate_lock
from tests.test_hung_final_dispatch import _fixture


def _archive_fixture(root: Path, *, unsafe: bool = False) -> tuple[Path, str, Path, Path]:
    lock_path, _, _, jobset_path = _fixture(root)
    job = json.loads(jobset_path.read_text(encoding="utf-8"))["jobs"][0]
    input_run = Path(job["input_run"])
    archive = root / "final-input-package.zip"
    with ZipFile(archive, "w") as target:
        for path in sorted(input_run.iterdir()):
            target.write(path, path.relative_to(ROOT).as_posix())
        if unsafe:
            target.writestr("../outside-final.txt", "unsafe")
    shutil.rmtree(input_run)
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["input"] = {
        "path": str(archive),
        "bytes": archive.stat().st_size,
        "sha256": sha256_file(archive),
    }
    lock_path.write_text(json.dumps(lock, sort_keys=True), encoding="utf-8")
    return lock_path, sha256_file(lock_path), input_run, archive


class FinalExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        (ROOT / "data" / "inputs").mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / "data" / "inputs")
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def _materialize(self, lock_path: Path, digest: str) -> dict:
        with (
            mock.patch(
                "experiments.hung_sprint2.final_extract.shutil.disk_usage",
                return_value=mock.Mock(free=100 * 1024**3),
            ),
            mock.patch(
                "experiments.hung_sprint2.final_extract._receipt_path",
                return_value=self.root / "receipt.json",
            ),
        ):
            return materialize_locked_inputs(lock_path, digest, check_code=False)

    def test_lock_before_extraction_and_create_only_readback(self) -> None:
        lock_path, digest, input_run, _ = _archive_fixture(self.root)
        preflight = validate_lock(lock_path, digest, check_code=False, verify_input_runs=False)
        self.assertFalse(preflight["input_runs_verified"])
        self.assertFalse(input_run.exists())
        result = self._materialize(lock_path, digest)
        self.assertTrue(result["input_runs_verified"])
        self.assertTrue((input_run / "manifest.json").is_file())
        with self.assertRaisesRegex(ValueError, "overwrite existing data"):
            self._materialize(lock_path, digest)

    def test_traversal_and_changed_zip_fail_before_write(self) -> None:
        lock_path, digest, input_run, archive = _archive_fixture(self.root, unsafe=True)
        with self.assertRaisesRegex(ValueError, "Unsafe Final ZIP member"):
            self._materialize(lock_path, digest)
        self.assertFalse(input_run.exists())
        with archive.open("ab") as stream:
            stream.write(b"tampered")
        with self.assertRaisesRegex(ValueError, "input bytes differ"):
            self._materialize(lock_path, digest)
        self.assertFalse(input_run.exists())

    def test_precheckout_capacity_witness_keeps_runtime_reserve(self) -> None:
        lock_path, digest, input_run, _ = _archive_fixture(self.root)
        with (
            mock.patch(
                "experiments.hung_sprint2.final_extract.shutil.disk_usage",
                return_value=mock.Mock(free=MIN_FREE_BYTES + 1),
            ),
            mock.patch(
                "experiments.hung_sprint2.final_extract._receipt_path",
                return_value=self.root / "receipt.json",
            ),
        ):
            with self.assertRaisesRegex(ValueError, "lacks locked capacity"):
                materialize_locked_inputs(
                    lock_path,
                    digest,
                    check_code=False,
                    provider_initial_free_bytes=MIN_FREE_BYTES + 999_999,
                )
            self.assertFalse(input_run.exists())
            result = materialize_locked_inputs(
                lock_path,
                digest,
                check_code=False,
                provider_initial_free_bytes=MIN_FREE_BYTES + 1_000_000,
            )
        self.assertTrue(result["input_runs_verified"])
