"""Verify catalog/path/checksum failures without fetching or changing real datasets."""

import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from tools.sources import CATALOG, Archive, load_catalog, main, select_archives, verify_archive


class SourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.payload = b"synthetic fixture bytes\n"
        self.archive = Archive(
            source_id="fixture",
            dataset="urbanev",
            download_url="https://example.invalid/archive.zip",
            relative_path="data/raw/fixture/archive.zip",
            size_bytes=len(self.payload),
            sha256=hashlib.sha256(self.payload).hexdigest(),
            required=True,
        )

    def write_fixture(self, content: bytes) -> Path:
        path = self.root / self.archive.relative_path
        path.parent.mkdir(parents=True)
        path.write_bytes(content)
        return path

    def test_committed_catalog_and_selection(self) -> None:
        archives = load_catalog()
        self.assertEqual(len(archives), 3)
        self.assertEqual(len(select_archives(archives, None, False)), 2)
        self.assertEqual(len(select_archives(archives, "urbanev", True)), 2)
        self.assertEqual(len(select_archives(archives, "charged", False)), 1)

    def test_matching_file_is_not_modified(self) -> None:
        path = self.write_fixture(self.payload)
        before = (path.read_bytes(), path.stat().st_mtime_ns)
        self.assertEqual(verify_archive(self.archive, self.root), (True, "PASS"))
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_missing_file_is_not_created(self) -> None:
        self.assertEqual(verify_archive(self.archive, self.root), (False, "MISSING"))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_size_and_same_size_corruption_are_rejected(self) -> None:
        path = self.write_fixture(self.payload + b"x")
        self.assertEqual(verify_archive(self.archive, self.root), (False, "SIZE MISMATCH"))
        corrupted = b"X" * len(self.payload)
        path.write_bytes(corrupted)
        self.assertEqual(verify_archive(self.archive, self.root), (False, "CHECKSUM MISMATCH"))
        self.assertEqual(path.read_bytes(), corrupted)

    def test_publisher_checksum_is_also_required(self) -> None:
        self.write_fixture(self.payload)
        md5 = hashlib.md5(self.payload, usedforsecurity=False).hexdigest()
        source = replace(self.archive, publisher_checksum="md5:" + md5)
        self.assertEqual(verify_archive(source, self.root), (True, "PASS"))
        source = replace(source, publisher_checksum="md5:" + "0" * 32)
        self.assertEqual(verify_archive(source, self.root), (False, "CHECKSUM MISMATCH"))

    def test_publisher_sha256_cannot_override_recorded_sha256(self) -> None:
        self.write_fixture(self.payload)
        source = replace(
            self.archive,
            sha256="0" * 64,
            publisher_checksum="sha256:" + self.archive.sha256,
        )
        self.assertEqual(verify_archive(source, self.root), (False, "CHECKSUM MISMATCH"))

    def test_unsafe_and_duplicate_paths_are_rejected(self) -> None:
        original = json.loads(CATALOG.read_text(encoding="utf-8"))
        for value in ["../escape.zip", "/tmp/escape.zip", "data/raw/../escape.zip"]:
            with self.subTest(path=value):
                catalog = json.loads(json.dumps(original))
                catalog["archives"][0]["relative_path"] = value
                path = self.root / "catalog.json"
                path.write_text(json.dumps(catalog), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_catalog(path)
        original["archives"][1]["relative_path"] = original["archives"][0]["relative_path"]
        path.write_text(json.dumps(original), encoding="utf-8")
        with self.assertRaises(ValueError):
            load_catalog(path)

    def test_resolved_path_cannot_escape_root(self) -> None:
        source = replace(self.archive, relative_path="../escape.zip")
        with self.assertRaises(ValueError):
            verify_archive(source, self.root)

    def test_cli_reports_failure_for_missing_or_corrupt_files(self) -> None:
        with patch("tools.sources.load_catalog", return_value=[self.archive]):
            self.assertEqual(main(["verify", "--root", str(self.root)]), 1)
            self.write_fixture(self.payload)
            self.assertEqual(main(["verify", "--root", str(self.root)]), 0)
            with patch("tools.sources.verify_archive", return_value=(False, "CHECKSUM MISMATCH")):
                self.assertEqual(main(["verify", "--root", str(self.root)]), 1)


if __name__ == "__main__":
    unittest.main()
