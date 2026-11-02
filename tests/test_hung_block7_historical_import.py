"""Offline tests for the historical Block7 checkpoint request and byte gate."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from tools.hung_block7_historical_import import ROOT, render_request, request_rows, verify_stage


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def pair(run_id: str, source: str, target: str) -> dict[str, str]:
    return {
        "historical_run_id": run_id,
        "historical_source_sha256": source,
        "historical_target_sha256": target,
        "budget_days": "7",
        "seed": "7",
    }


class HistoricalImportTests(unittest.TestCase):
    def test_deduplicates_shared_source_and_reports_missing(self) -> None:
        rows = request_rows(
            [
                pair("block7_b7s7e101", digest(b"source"), digest(b"target-1")),
                pair("block7_b7s7e102", digest(b"source"), digest(b"target-2")),
            ],
            strict=False,
        )
        self.assertEqual(len(rows), 3)
        self.assertEqual(sum(row["role"] == "source" for row in rows), 1)
        self.assertIn("block7_b7s7e101;block7_b7s7e102", render_request(rows).decode())
        (ROOT / ".cache").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            result = verify_stage(rows, Path(directory))
        self.assertEqual(result["counts"]["MISSING"], 3)
        self.assertFalse(result["complete"])

    def test_checks_bytes_and_rejects_extra(self) -> None:
        payload = b"source"
        rows = request_rows(
            [pair("block7_b7s7e101", digest(payload), digest(b"target"))], strict=False
        )
        (ROOT / ".cache").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            root = Path(directory)
            (root / f"{digest(payload)}.pt").write_bytes(payload)
            (root / f"{digest(b'target')}.pt").write_bytes(b"wrong")
            (root / "unplanned.pt").write_bytes(b"extra")
            result = verify_stage(rows, root)
            (root / f"{digest(b'target')}.pt").write_bytes(b"target")
            (root / "unplanned.pt").unlink()
            repaired = verify_stage(rows, root)
        self.assertEqual(result["counts"], {"VERIFIED": 1, "MISSING": 0, "MISMATCH": 1})
        self.assertEqual(result["unexpected_entries"], ["unplanned.pt"])
        self.assertFalse(result["complete"])
        self.assertEqual(repaired["counts"]["VERIFIED"], 2)
        self.assertTrue(repaired["complete"])

    def test_rejects_invalid_digest_and_cross_stratum_source(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid source SHA"):
            request_rows([pair("block7_b7s7e101", "bad", digest(b"target"))], strict=False)
        first = pair("block7_b7s7e101", digest(b"source"), digest(b"target-1"))
        second = pair("block7_b14s7e102", digest(b"source"), digest(b"target-2"))
        second["budget_days"] = "14"
        with self.assertRaisesRegex(ValueError, "incompatible budget/seed"):
            request_rows([first, second], strict=False)


if __name__ == "__main__":
    unittest.main()
