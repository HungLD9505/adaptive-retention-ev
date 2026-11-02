"""Offline transport tests; no model training or provider credentials."""

import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.hung_provider import execute_shard, materialize, package, safe_members, save, sha256


class ProviderTransportTests(unittest.TestCase):
    def test_zip_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.zip"
            with zipfile.ZipFile(path, "x") as archive:
                archive.writestr("../escape", "bad")
            with zipfile.ZipFile(path) as archive, self.assertRaisesRegex(ValueError, "Unsafe"):
                safe_members(archive)

    def test_duplicate_members_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.zip"
            with zipfile.ZipFile(path, "x") as archive:
                archive.writestr("a", "first")
                with self.assertWarns(UserWarning):
                    archive.writestr("a", "second")
            with zipfile.ZipFile(path) as archive, self.assertRaisesRegex(ValueError, "Duplicate"):
                safe_members(archive)

    def test_corrupt_transport_does_not_create_destination(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "bad.bin"
            path.write_bytes(b"damaged")
            with self.assertRaisesRegex(ValueError, "Transport SHA"):
                materialize(path, "0" * 64, root / "destination")
            self.assertFalse((root / "destination").exists())

    def test_completed_pilot_never_reexecutes(self):
        with self.assertRaisesRegex(ValueError, "pilot must not execute"):
            execute_shard(Path("missing"), "pilot_0000", Path("missing-output"))

    def test_roundtrip_preserves_pins_and_only_relocates_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "source"
            repo.mkdir()
            subprocess.run(
                ["git", "init", "-b", "fixture", str(repo)], check=True, capture_output=True
            )
            (repo / ".gitignore").write_text(".cache/\ndata/\n", encoding="utf-8")
            subprocess.run(["git", "add", ".gitignore"], cwd=repo, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Fixture",
                    "-c",
                    "user.email=f@example.test",
                    "commit",
                    "-m",
                    "fixture",
                ],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip()
            cache = repo / ".cache"
            cache.mkdir()
            config = cache / "config.json"
            save(config, {"seed": 7})
            checkpoint = cache / "source" / "source_checkpoint.pt"
            checkpoint.parent.mkdir()
            checkpoint.write_bytes(b"immutable fixture checkpoint")
            record = checkpoint.parent / "run_manifest.json"
            save(record, {"checkpoint_sha256": sha256(checkpoint)})
            spec = {
                "path": str(checkpoint),
                "sha256": sha256(checkpoint),
                "run_manifest_sha256": sha256(record),
            }
            plan = cache / "plan.json"
            save(
                plan,
                {
                    "scope": "development_only",
                    "code_commit": commit,
                    "configs": [{"id": "main", "path": str(config), "sha256": sha256(config)}],
                    "selection": {"path": str(config), "sha256": sha256(config)},
                    "jobs": [{"id": "job1", "source": spec, "target": None}],
                    "cells": [{"seed": 7}],
                    "input_base": "old-input",
                    "output_root": "old-output",
                },
            )
            shards = cache / "shards.json"
            save(
                shards,
                {
                    "plan_sha256": sha256(plan),
                    "shards": [{"id": "shard_0001", "job_ids": ["job1"]}],
                },
            )
            inputs = cache / "inputs.zip"
            with zipfile.ZipFile(inputs, "x") as archive:
                archive.writestr("data/inputs/fixture.txt", "unchanged")
            transport = cache / "transport"
            result = package(
                repo, plan, sha256(plan), shards, sha256(shards), inputs, sha256(inputs), transport
            )
            restored, relocated = materialize(
                transport / "provider-payload.zip.bin", result["archive_sha256"], root / "restored"
            )
            value = json.loads(relocated.read_bytes())
            self.assertEqual(value["cells"], [{"seed": 7}])
            self.assertEqual(value["jobs"][0]["source"]["sha256"], spec["sha256"])
            self.assertEqual(sha256(Path(value["configs"][0]["path"])), sha256(config))
            self.assertEqual(sha256(Path(value["jobs"][0]["source"]["path"])), sha256(checkpoint))
            self.assertEqual(
                subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=restored, text=True
                ).strip(),
                commit,
            )
            with self.assertRaisesRegex(ValueError, "already exists"):
                materialize(
                    transport / "provider-payload.zip.bin",
                    result["archive_sha256"],
                    root / "restored",
                )


if __name__ == "__main__":
    unittest.main()
