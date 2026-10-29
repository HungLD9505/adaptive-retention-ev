"""Offline create-only Final Kaggle Dataset packet checks."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2.final_handoff import WRAPPER, prepare_handoff
from experiments.hung_sprint2.kaggle_final_locked_v1 import inspect_handoff
from tests.test_hung_final_dispatch import _fixture

ROOT = Path(__file__).resolve().parents[1]
VERSION = "hungluongduc/hung-final-fixture/1"


def _locked_fixture(
    root: Path, *, wrong_commit: bool = False, with_source: bool = False
) -> tuple[Path, str]:
    lock_path, _, _, _ = _fixture(root)
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["code_commit"] = (
        "0" * 40
        if wrong_commit
        else subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    )
    if with_source:
        source = root / "source" / "source_checkpoint.pt"
        source.parent.mkdir()
        source.write_bytes(b"synthetic Source checkpoint")
        source_sha = sha256_file(source)
        (source.parent / "run_manifest.json").write_text(
            json.dumps({"checkpoint_sha256": source_sha, "input_binding": {}}),
            encoding="utf-8",
        )
        lock["source_checkpoints"] = [
            {
                "path": str(source),
                "bytes": source.stat().st_size,
                "sha256": source_sha,
            }
        ]
    lock_path.write_text(json.dumps(lock, sort_keys=True), encoding="utf-8")
    return lock_path, sha256_file(lock_path)


def _fixture_bundle(path: Path, _commit: str) -> None:
    path.write_bytes(b"synthetic git bundle")


class FinalHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        (ROOT / ".cache").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / ".cache")
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def _prepare(self, lock_path: Path, digest: str, packet: Path) -> dict:
        with (
            mock.patch(
                "experiments.hung_sprint2.final_handoff._source_at_commit",
                return_value=WRAPPER.read_bytes(),
            ),
            mock.patch(
                "experiments.hung_sprint2.final_handoff.shutil.disk_usage",
                return_value=mock.Mock(free=100 * 1024**3),
            ),
        ):
            return prepare_handoff(
                lock_path, digest, VERSION, packet, check_code=False, create_bundle=_fixture_bundle
            )

    def test_exact_packet_and_duplicate_or_changed_bytes(self) -> None:
        lock_path, digest = _locked_fixture(self.root, with_source=True)
        packet = self.root / "packet"
        result = self._prepare(lock_path, digest, packet)
        self.assertEqual(result["status"], "PREPARED_ONLY_PRIVATE_UPLOAD_PENDING")
        self.assertEqual(result["files"], 8)
        self.assertTrue(
            (packet / "payload" / "analysis.json").samefile(self.root / "analysis.json")
        )
        inspect_handoff(packet, result["manifest_sha256"], VERSION, WRAPPER)
        with self.assertRaisesRegex(ValueError, "new ignored path"):
            self._prepare(lock_path, digest, packet)
        original_analysis_sha = sha256_file(self.root / "analysis.json")
        (packet / "payload" / "analysis.json").unlink()  # Disposable fixture hard link only.
        (packet / "payload" / "analysis.json").write_text("changed", encoding="utf-8")
        self.assertEqual(sha256_file(self.root / "analysis.json"), original_analysis_sha)
        with self.assertRaisesRegex(ValueError, "handoff bytes differ"):
            inspect_handoff(packet, result["manifest_sha256"], VERSION, WRAPPER)

    def test_missing_source_extra_package_and_path_escape(self) -> None:
        lock_path, digest = _locked_fixture(self.root)
        analysis = self.root / "analysis.json"
        analysis.unlink()  # Synthetic disposable fixture only.
        with self.assertRaisesRegex(ValueError, "analysis bytes differ"):
            self._prepare(lock_path, digest, self.root / "missing-packet")
        self.assertFalse((self.root / "missing-packet").exists())
        analysis.write_text("{}\n", encoding="utf-8")
        packet = self.root / "packet"
        result = self._prepare(lock_path, digest, packet)
        (packet / "payload" / "extra.txt").write_text("unexpected", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "extra or missing files"):
            inspect_handoff(packet, result["manifest_sha256"], VERSION, WRAPPER)
        with self.assertRaisesRegex(ValueError, "new ignored path"):
            self._prepare(lock_path, digest, ROOT / "docs" / "escaped-packet")

    def test_wrong_code_commit_is_refused(self) -> None:
        lock_path, digest = _locked_fixture(self.root, wrong_commit=True)
        with self.assertRaisesRegex(ValueError, "lacks the Kaggle Final wrapper"):
            prepare_handoff(
                lock_path,
                digest,
                VERSION,
                self.root / "packet",
                check_code=False,
                create_bundle=_fixture_bundle,
            )
        self.assertFalse((self.root / "packet").exists())
