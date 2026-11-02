"""Independent report-release boundary checks with a standard SHA-256 vector."""

import json
import tempfile
import unittest
from pathlib import Path

from tools.check_release import verify_report


class ReportReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "report").mkdir()
        (self.root / "report/a.txt").write_bytes(b"abc")
        # Published SHA-256 test vector for the ASCII bytes abc.
        self.record = {
            "path": "a.txt",
            "bytes": 3,
            "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        }
        self.write([self.record])

    def write(self, rows):
        (self.root / "report/manifest.json").write_text(json.dumps({"files": rows}))

    def test_standard_vector_is_accepted_and_changed_bytes_are_rejected(self):
        self.assertEqual(verify_report(self.root), 1)
        (self.root / "report/a.txt").write_bytes(b"abd")
        with self.assertRaisesRegex(ValueError, "asset differs"):
            verify_report(self.root)

    def test_duplicate_or_empty_inventory_is_rejected(self):
        for rows, message in [([self.record, self.record], "Duplicate"), ([], "Empty")]:
            self.write(rows)
            with self.assertRaisesRegex(ValueError, message):
                verify_report(self.root)

    def test_external_file_is_not_followed_through_symlink(self):
        (self.root / "report/a.txt").unlink()
        (self.root / "outside.txt").write_bytes(b"abc")
        (self.root / "report/a.txt").symlink_to(self.root / "outside.txt")
        with self.assertRaisesRegex(ValueError, "Linked or escaping"):
            verify_report(self.root)

    def test_traversal_absolute_and_windows_paths_are_rejected(self):
        for name in ["../outside.txt", "/etc/hosts", "C:\\outside.txt", "..\\outside.txt"]:
            self.write([{**self.record, "path": name}])
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "Unsafe"):
                verify_report(self.root)
