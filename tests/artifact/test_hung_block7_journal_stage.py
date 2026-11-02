"""External-artifact checks; intentionally excluded from offline discovery."""

from __future__ import annotations

import hashlib
import unittest

from tools.hung_block7_journal_stage import render, rows


class JournalStageTests(unittest.TestCase):
    def test_pinned_request_has_exact_138_distinct_journals(self) -> None:
        records = rows()
        self.assertEqual(len(records), 138)
        self.assertEqual(len({record["sha256"] for record in records}), 138)
        self.assertEqual(
            hashlib.sha256(render(records)).hexdigest(),
            "38295dade44c779b381cd7b54fe7983699c688754e597d88ede50c1e1127fc02",
        )
