"""Read-only DATA-v1 package verification before any real-data run."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from zipfile import ZIP_STORED, ZipFile

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2.cli import _verify_input_zip, main


class InputReleaseTests(unittest.TestCase):
    def test_catalog_size_digest_and_crc_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "inputs-urbanev-SZH-v1.zip"
            with ZipFile(archive, "w", compression=ZIP_STORED) as package:
                package.writestr("data/inputs/run/manifest.json", b"payload")
            catalog = root / "release.json"

            def write_catalog() -> None:
                catalog.write_text(
                    json.dumps(
                        {
                            "release_id": "DATA-v1-20261019",
                            "packages": [
                                {
                                    "kind": "inputs",
                                    "name": archive.name,
                                    "size_bytes": archive.stat().st_size,
                                    "sha256": sha256_file(archive),
                                }
                            ],
                        }
                    ),
                    encoding="utf-8",
                )

            write_catalog()
            before = archive.read_bytes()
            result = _verify_input_zip(archive, archive.name, catalog)
            self.assertEqual(result["status"], "verified")
            self.assertEqual(archive.read_bytes(), before)
            with mock.patch("experiments.hung_sprint2.cli.RELEASE_CATALOG", catalog):
                self.assertEqual(
                    main(
                        ["verify-input-zip", "--archive", str(archive), "--package", archive.name]
                    ),
                    0,
                )
            with self.assertRaisesRegex(ValueError, "not unique"):
                _verify_input_zip(archive, "other.zip", catalog)
            archive.write_bytes(before + b"x")
            with self.assertRaisesRegex(ValueError, "name/size"):
                _verify_input_zip(archive, archive.name, catalog)
            damaged = before.replace(b"payload", b"payloae", 1)
            self.assertNotEqual(damaged, before)
            archive.write_bytes(damaged)
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                _verify_input_zip(archive, archive.name, catalog)
            write_catalog()
            with self.assertRaisesRegex(ValueError, "CRC failed"):
                _verify_input_zip(archive, archive.name, catalog)


if __name__ == "__main__":
    unittest.main()
