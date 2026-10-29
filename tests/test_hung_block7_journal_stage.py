"""Guards for the exact 138-journal request and repository-local byte stage."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from tools.hung_block7_journal_stage import ROOT, render, rows, verify


class JournalStageTests(unittest.TestCase):
    def test_pinned_request_has_exact_138_distinct_journals(self) -> None:
        records = rows()
        self.assertEqual(len(records), 138)
        self.assertEqual(len({record["sha256"] for record in records}), 138)
        self.assertEqual(
            hashlib.sha256(render(records)).hexdigest(),
            "38295dade44c779b381cd7b54fe7983699c688754e597d88ede50c1e1127fc02",
        )

    def test_stage_requires_exact_hash_and_no_extra_files(self) -> None:
        payload = b"one\n"
        digest = hashlib.sha256(payload).hexdigest()
        record = {"sha256": digest}
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as folder:
            stage = Path(folder)
            self.assertEqual(verify([record], stage)["counts"]["MISSING"], 1)
            journal = stage / f"{digest}.jsonl"
            journal.write_bytes(b"wrong\n")
            self.assertEqual(verify([record], stage)["counts"]["MISMATCH"], 1)
            journal.write_bytes(payload)
            self.assertTrue(verify([record], stage)["complete"])
            (stage / "extra.jsonl").write_bytes(b"extra\n")
            self.assertFalse(verify([record], stage)["complete"])
