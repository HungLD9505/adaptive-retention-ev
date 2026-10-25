"""Multipart transport rejects overlaps even when all archive hashes are valid."""

import json
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

from ev_models.checkpoint import digest
from tools.export_development import checked_part
from tools.restore_development_export import restore


class RestoreTests(unittest.TestCase):
    def package(self, root: Path, mode: str = "valid") -> str:
        parts = []
        for index in (0, 1):
            path = root / f"runs-{index:04d}.zip"
            with zipfile.ZipFile(path, "x") as z:
                prefix = "STUDY" if mode == "directory_case" and index == 1 else "study"
                z.writestr(f"{prefix}/run{index}/run.json", json.dumps({"run_id": f"run{index}"}))
                if mode == "legacy_overlap":
                    z.writestr("completed-runs.json", json.dumps([{"run_id": f"run{index}"}]))
                else:
                    z.writestr(
                        f"part-records/runs-{index:04d}.json",
                        json.dumps([{"run_id": f"run{index}"}]),
                    )
                if mode == "traversal" and index == 1:
                    z.writestr("../outside", b"bad")
                if mode == "symlink" and index == 1:
                    info = zipfile.ZipInfo("study/link")
                    info.external_attr = (stat.S_IFLNK | 0o777) << 16
                    z.writestr(info, b"outside")
            parts.append(checked_part(path, "target_runs", [f"run{index}"]))
        metadata = root / "metadata.zip"
        matrix = {
            "status": "technical_success",
            "runs": [{"run_id": f"run{i}"} for i in (0, 1)],
            "source_epochs": 10,
        }
        payloads = {
            "matrix.json": json.dumps(matrix).encode(),
            "verification.json": b"{}",
            "latest-states.json": b"{}",
        }
        with zipfile.ZipFile(metadata, "x") as z:
            for name, data in payloads.items():
                z.writestr("study/" + name, data)
        parts.append(checked_part(metadata, "metadata_and_sources", []))
        code = root / "code.bundle"
        code.write_bytes(b"fixture transport only; do not execute")
        parts.append(
            {
                "name": code.name,
                "kind": "code",
                "bytes": code.stat().st_size,
                "sha256": digest(code),
            }
        )
        import hashlib

        catalog = {
            "schema": "ev-development-export-v1",
            "status": "complete",
            "parts": parts,
            "target_runs": 2,
            "sources": [],
            "matrix_sha256": hashlib.sha256(payloads["matrix.json"]).hexdigest(),
            "verification_sha256": hashlib.sha256(payloads["verification.json"]).hexdigest(),
            "latest_states_sha256": hashlib.sha256(payloads["latest-states.json"]).hexdigest(),
        }
        (root / "catalog.json").write_text(json.dumps(catalog))
        return digest(root / "catalog.json")

    def test_two_parts_restore_without_overwriting_per_part_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checksum = self.package(root)
            result = restore(root, root / "restored", checksum)
            self.assertEqual(result["status"], "transport_verified")
            self.assertEqual(result["runs"], 2)
            for i in (0, 1):
                self.assertTrue((root / "restored/part-records" / f"runs-{i:04d}.json").is_file())
                self.assertTrue((root / "restored/study" / f"run{i}/run.json").is_file())
            self.assertEqual(
                (root / "restored/code.bundle").read_bytes(), (root / "code.bundle").read_bytes()
            )

    def test_overlapping_legacy_headers_and_unsafe_payloads_fail_closed(self):
        for mode in ("legacy_overlap", "traversal", "symlink", "directory_case"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                checksum = self.package(root, mode)
                with self.assertRaises(ValueError):
                    restore(root, root / "restored", checksum)

    def test_changed_parts_and_wrong_catalog_identity_rejected_before_restore(self):
        for mode in ("part", "catalog"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                checksum = self.package(root)
                if mode == "part":
                    with (root / "runs-0000.zip").open("ab") as f:
                        f.write(b"changed")
                else:
                    checksum = "0" * 64
                with self.assertRaises(ValueError):
                    restore(root, root / "restored", checksum)
                self.assertFalse((root / "restored").exists())
