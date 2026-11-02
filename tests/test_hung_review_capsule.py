"""Archive integrity and preservation tests; synthetic metadata, no model runs."""

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools import hung_review_capsule as capsule


class CapsuleTests(unittest.TestCase):
    def fixture(self, root):
        def save(name, data):
            path = root / name
            path.write_bytes(data if isinstance(data, bytes) else json.dumps(data).encode())
            return {
                "path": str(path.resolve()),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }

        plan = save(
            "plan.json",
            {
                "scope": "development_only",
                "code_commit": "synthetic-fixture",
                "cells": [],
                "jobs": [],
                "configs": [],
            },
        )
        spec = {
            "plan": plan,
            "partition": save("partition.json", {"plan_sha256": plan["sha256"], "shards": []}),
            "ledger": save("ledger.json", {"jobs": []}),
            "scorer": save("scorer.py", b"# synthetic metadata fixture; no training\n"),
            "local_shards": [],
        }
        path = root / "capsule.zip.bin"
        receipt = capsule.build(spec, root, path)
        return path, receipt, spec

    def test_roundtrip_preserves_original_bytes(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            root = Path(directory)
            path, receipt, spec = self.fixture(root)
            before = Path(spec["plan"]["path"]).read_bytes()
            proof = capsule.verify(path, receipt["sha256"])
            self.assertTrue(proof["passed"])
            self.assertEqual(Path(spec["plan"]["path"]).read_bytes(), before)
            with self.assertRaises(FileExistsError):
                capsule.build(spec, root, path)

    def test_corrupt_bytes_fail(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            path, receipt, _ = self.fixture(Path(directory))
            corrupted = path.with_name("corrupt.zip.bin")
            corrupted.write_bytes(path.read_bytes() + b"bad")
            with self.assertRaises(ValueError):
                capsule.verify(corrupted, receipt["sha256"])

    def test_partial_inventory_fails_even_when_zip_crc_passes(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            root = Path(directory)
            path, _, _ = self.fixture(root)
            partial = root / "partial.zip.bin"
            with zipfile.ZipFile(path) as source, zipfile.ZipFile(partial, "x") as target:
                for name in source.namelist():
                    if name != "code/hung_results.py":
                        target.writestr(name, source.read(name))
            with self.assertRaises(ValueError):
                capsule.verify(partial, hashlib.sha256(partial.read_bytes()).hexdigest())

    def test_unsafe_member_fails_before_any_extraction(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            path = Path(directory) / "unsafe.zip.bin"
            with zipfile.ZipFile(path, "x") as stream:
                stream.writestr("../escape", "fixture")
            with self.assertRaises(ValueError):
                capsule.verify(path, hashlib.sha256(path.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
