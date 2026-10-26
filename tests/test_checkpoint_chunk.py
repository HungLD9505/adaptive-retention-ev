"""Bounded replay/publication gates with independent files; no GPU, network or fitting."""

import copy
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from ev_models.checkpoint import digest
from tools.replay_checkpoint_chunk import check_handoff, package_outbox, select_chunk


class CheckpointChunkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = [{"run_id": f"fixture-{i}"} for i in range(31)]

    def receipt(self, root: Path) -> Path:
        p = root / "receipt.json"
        p.write_text(
            json.dumps(
                {
                    "schema": "verified-kaggle-outbox-publication-v1",
                    "plan_sha256": "a" * 64,
                    "family": "matched",
                    "start": 0,
                    "end": 12,
                    "run_ids": [r["run_id"] for r in self.rows[:12]],
                    "independent_content_verified": True,
                    "remote_readback_verified": True,
                    "artifact": {
                        "bytes": 123,
                        "sha256": "b" * 64,
                        "drive_url": "https://drive.google.com/file/d/fixture-publication-123456/view",
                    },
                }
            )
        )
        return p

    def test_order_bound_and_final_short_chunk(self) -> None:
        self.assertEqual(select_chunk(self.rows, 12, 12), self.rows[12:24])
        self.assertEqual(select_chunk(self.rows, 24, 12), self.rows[24:])
        for first, count in ((-1, 1), (31, 1), (0, 0), (0, 13), (True, 1), (0, False)):
            with self.subTest(first=first, count=count), self.assertRaises(ValueError):
                select_chunk(self.rows, first, count)

    def test_first_chunk_and_required_pinned_previous_receipt(self) -> None:
        check_handoff(self.rows, 0, "a" * 64, "matched", None, None)
        with self.assertRaises(ValueError):
            check_handoff(self.rows, 12, "a" * 64, "matched", None, None)
        with tempfile.TemporaryDirectory() as temp:
            p = self.receipt(Path(temp))
            check_handoff(self.rows, 12, "a" * 64, "matched", p, digest(p))
            for start, pin in ((0, digest(p)), (12, "0" * 64), (24, digest(p))):
                with self.subTest(start=start, pin=pin), self.assertRaises(ValueError):
                    check_handoff(self.rows, start, "a" * 64, "matched", p, pin)

    def test_reject_holes_changed_scope_and_unverified_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            p = self.receipt(Path(temp))
            original = json.loads(p.read_text())
            for field, value in (
                ("plan_sha256", "c" * 64),
                ("family", "proxy"),
                ("start", 1),
                ("end", 13),
                ("run_ids", ["fixture-1"]),
                ("independent_content_verified", False),
                ("remote_readback_verified", False),
            ):
                changed = copy.deepcopy(original)
                changed[field] = value
                p.write_text(json.dumps(changed))
                with self.subTest(field=field), self.assertRaises(ValueError):
                    check_handoff(self.rows, 12, "a" * 64, "matched", p, digest(p))
            changed = copy.deepcopy(original)
            changed["artifact"]["drive_url"] = "https://example.org/unrelated"
            p.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):
                check_handoff(self.rows, 12, "a" * 64, "matched", p, digest(p))

    def export_fixture(self, root: Path) -> tuple[Path, dict]:
        exports = root / "exports"
        exports.mkdir()
        data = exports / "runs-0000.zip"
        data.write_bytes(b"opaque original canonical part")
        catalog = {
            "schema": "ev-development-export-v1",
            "status": "complete",
            "target_runs": 1,
            "parts": [
                {
                    "name": data.name,
                    "bytes": data.stat().st_size,
                    "sha256": digest(data),
                    "kind": "target_runs",
                    "run_ids": ["fixture-0"],
                }
            ],
        }
        for name, kind in (("code.bundle", "code"), ("metadata.zip", "metadata_and_sources")):
            p = exports / name
            p.write_bytes(b"independent opaque transport fixture")
            catalog["parts"].append(
                {"name": name, "kind": kind, "bytes": p.stat().st_size, "sha256": digest(p)}
            )
        (exports / "catalog.json").write_text(json.dumps(catalog))
        return exports, {
            "run_ids": ["fixture-0"],
            "status": "awaiting_external_publication",
            "catalog_sha256": digest(exports / "catalog.json"),
        }

    def test_wrapper_preserves_parts_and_never_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            exports, record = self.export_fixture(root)
            output = root / "handoff.zip"
            result = package_outbox(exports, record, output)
            self.assertEqual(result["sha256"], digest(output))
            with zipfile.ZipFile(output) as z:
                self.assertIsNone(z.testzip())
                self.assertEqual(
                    z.read("package/runs-0000.zip"), (exports / "runs-0000.zip").read_bytes()
                )
                self.assertEqual(json.loads(z.read("handoff-record.json")), record)
            with self.assertRaises(FileExistsError):
                package_outbox(exports, record, output)

    def test_wrapper_rejects_tampering_and_unsafe_population(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            exports, record = self.export_fixture(root)
            (exports / "runs-0000.zip").write_bytes(b"changed")
            with self.assertRaises(ValueError):
                package_outbox(exports, record, root / "changed.zip")
            for name in ("../outside", "/absolute", "bad\\path", "catalog.json"):
                catalog = {
                    "status": "complete",
                    "target_runs": 1,
                    "parts": [{"name": name, "bytes": 1, "sha256": "a" * 64}],
                }
                (exports / "catalog.json").write_text(json.dumps(catalog))
                with self.subTest(name=name), self.assertRaises(ValueError):
                    package_outbox(exports, record, root / "unsafe.zip")

    def test_wrapper_rejects_same_count_wrong_ids_and_copy_time_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            exports, record = self.export_fixture(root)
            changed = {**record, "run_ids": ["other-fixture"]}
            with self.assertRaises(ValueError):
                package_outbox(exports, changed, root / "wrong-population.zip")
            original_write = zipfile.ZipFile.write

            def changing_write(archive, filename, arcname=None, *args, **kwargs):
                if arcname == "package/runs-0000.zip":
                    Path(filename).write_bytes(b"changed during copy")
                return original_write(archive, filename, arcname, *args, **kwargs)

            with (
                patch.object(zipfile.ZipFile, "write", changing_write),
                self.assertRaises(ValueError),
            ):
                package_outbox(exports, record, root / "retained-changed-copy.zip")
            self.assertTrue((root / "retained-changed-copy.zip").exists())


if __name__ == "__main__":
    unittest.main()
