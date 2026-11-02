"""Regression checks for historical/Main Git code identity evidence."""

from __future__ import annotations

import csv
import unittest

from tools.hung_block7_code_lineage_v1 import PAIRS, assess


def _rows() -> list[dict[str, str]]:
    with PAIRS.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


class Block7CodeLineageTests(unittest.TestCase):
    def test_real_manifest_and_git_source_identity(self) -> None:
        summary = assess(_rows())
        self.assertEqual(summary["manifest_pairs_checked"], 69)
        self.assertEqual(len(summary["executed_source_paths_checked"]), 11)
        self.assertEqual(summary["unique_git_source_blobs_sha256_checked"], 22)
        self.assertEqual(
            summary["changed_paths_between_commits"],
            [{"status": "D", "path": "docs/reports/hung-integrated-development-20261026.md"}],
        )

    def test_duplicate_cell_rejected(self) -> None:
        rows = _rows()
        rows[1] = dict(rows[0])
        with self.assertRaisesRegex(ValueError, "Duplicate logical cell"):
            assess(rows)

    def test_manifest_sha_mismatch_rejected(self) -> None:
        rows = _rows()
        rows[0]["historical_manifest_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Manifest SHA mismatch"):
            assess(rows)


if __name__ == "__main__":
    unittest.main()
