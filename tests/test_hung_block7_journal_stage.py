"""Guards for the exact 138-journal request and repository-local byte stage."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from tools.hung_block7_journal_stage import ROOT, verify


class JournalStageTests(unittest.TestCase):
    def test_stage_requires_exact_hash_and_no_extra_files(self) -> None:
        payload = b"one\n"
        digest = hashlib.sha256(payload).hexdigest()
        record = {"sha256": digest}
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            stage = Path(folder)
            self.assertEqual(verify([record], stage)["counts"]["MISSING"], 1)
            journal = stage / f"{digest}.jsonl"
            journal.write_bytes(b"wrong\n")
            self.assertEqual(verify([record], stage)["counts"]["MISMATCH"], 1)
            journal.write_bytes(payload)
            self.assertTrue(verify([record], stage)["complete"])
            (stage / "extra.jsonl").write_bytes(b"extra\n")
            self.assertFalse(verify([record], stage)["complete"])
