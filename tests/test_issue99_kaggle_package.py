"""Synthetic bundle integrity, safe staging and no-overwrite fixtures."""

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from zipfile import ZipFile

from tools.issue99_kaggle_package import (
    INPUT_MEMBERS,
    INPUT_NAME,
    INPUT_PREFIX,
    artifact,
    check_member,
    create_bundle,
    sha256,
    stage_bundle,
    verify_bundle,
)


class KaggleBundleTests(unittest.TestCase):
    def test_create_requires_clean_commit_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(dir=".cache") as temp:
            root = Path(temp)
            code = root / "repo"
            code.mkdir()
            required = (
                "ev_control/continuous.py",
                "ev_control/hypergradient.py",
                "ev_runner/continuous.py",
                "ev_runner/continuous_run.py",
                "tools/issue99_kaggle_package.py",
            )
            for name in required:
                path = code / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"committed code")
            subprocess.run(["git", "init", "-q"], cwd=code, check=True)
            subprocess.run(["git", "add", "."], cwd=code, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=fixture",
                    "-c",
                    "user.email=fixture@example.invalid",
                    "commit",
                    "-qm",
                    "fixture",
                ],
                cwd=code,
                check=True,
            )
            inputs = root / INPUT_NAME
            with ZipFile(inputs, "w") as archive:
                for name in INPUT_MEMBERS:
                    archive.writestr(INPUT_PREFIX + name, b"input")
            sources = root / "sources"
            sources.mkdir()
            audit_sources = {}
            for seed in (42, 43, 44):
                path = sources / f"qyroven-issue23-source-duration-20261026-v1-seed{seed}.zip"
                content = f"checkpoint-{seed}".encode()
                with ZipFile(path, "w") as archive:
                    archive.writestr("epoch-10.pt", content)
                audit_sources[str(seed)] = {
                    "zip_sha256": sha256(path),
                    "checkpoint_sha256": hashlib.sha256(content).hexdigest(),
                }
            audit = root / "audit.json"
            audit.write_text(
                json.dumps(
                    {
                        "schema": "issue99-local-audit-v1",
                        "status": "PASS",
                        "inputs": {
                            "zip_sha256": sha256(inputs),
                            "budgets": {
                                "14": {
                                    "manifest_sha256": hashlib.sha256(b"input").hexdigest(),
                                }
                            },
                        },
                        "source": audit_sources,
                    }
                ),
                encoding="utf-8",
            )
            bundle = root / "new-bundle"
            result = create_bundle(bundle, inputs, sources, audit, root=code)
            self.assertEqual(
                result["code_commit"],
                subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    cwd=code,
                    text=True,
                ).strip(),
            )
            self.assertEqual(verify_bundle(bundle)["code_commit"], result["code_commit"])
            with self.assertRaises(FileExistsError):
                create_bundle(bundle, inputs, sources, audit, root=code)
            (code / "ev_control/continuous.py").write_bytes(b"dirty code")
            next_bundle = root / "should-not-exist"
            with self.assertRaisesRegex(ValueError, "clean"):
                create_bundle(next_bundle, inputs, sources, audit, root=code)
            self.assertFalse(next_bundle.exists())

    def make_bundle(self, root: Path) -> Path:
        bundle = root / "bundle"
        bundle.mkdir()
        code = bundle / "issue99-code.zip"
        with ZipFile(code, "w") as archive:
            archive.writestr("ev_control/continuous.py", b"code")
        inputs = bundle / INPUT_NAME
        with ZipFile(inputs, "w") as archive:
            for name in INPUT_MEMBERS:
                archive.writestr(INPUT_PREFIX + name, b"input")
        sources = {}
        source_hashes = {}
        for seed in (42, 43, 44):
            path = bundle / f"seed{seed}.zip"
            checkpoint = f"checkpoint-{seed}".encode()
            with ZipFile(path, "w") as archive:
                archive.writestr("epoch-10.pt", checkpoint)
            sources[str(seed)] = artifact(path)
            source_hashes[str(seed)] = hashlib.sha256(checkpoint).hexdigest()
        preflight = bundle / "preflight.py"
        preflight.write_bytes(b"preflight")
        manifest = {
            "schema": "issue99-kaggle-bundle-v1",
            "code_commit": "test-commit",
            "code_files_sha256": {"ev_control/continuous.py": hashlib.sha256(b"code").hexdigest()},
            "input_manifest_sha256": hashlib.sha256(b"input").hexdigest(),
            "source_checkpoint_sha256": source_hashes,
            "files": {
                "code": artifact(code),
                "input": artifact(inputs),
                "preflight": artifact(preflight),
                "sources": sources,
            },
        }
        (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return bundle

    def test_verify_and_stage_only_to_fresh_destination(self) -> None:
        with tempfile.TemporaryDirectory(dir=".cache") as temp:
            root = Path(temp)
            bundle = self.make_bundle(root)
            self.assertEqual(verify_bundle(bundle)["code_commit"], "test-commit")
            with self.assertRaisesRegex(ValueError, "locally pinned"):
                verify_bundle(bundle, expected_manifest_sha256="0" * 64)
            staged = root / "new-stage"
            runtime = stage_bundle(
                bundle, staged, expected_manifest_sha256=sha256(bundle / "manifest.json")
            )
            self.assertEqual(runtime["code_commit"], "test-commit")
            self.assertEqual((staged / "code/ev_control/continuous.py").read_bytes(), b"code")
            self.assertEqual(
                sha256(staged / "sources/seed42/epoch-10.pt"),
                hashlib.sha256(b"checkpoint-42").hexdigest(),
            )
            with self.assertRaises(FileExistsError):
                stage_bundle(bundle, staged)
            with mock.patch("torch.cuda.is_available", return_value=False):
                with self.assertRaisesRegex(ValueError, "active T4"):
                    stage_bundle(bundle, root / "no-gpu-stage", require_t4=True)
            self.assertFalse((root / "no-gpu-stage").exists())

    def test_changed_bytes_and_unsafe_member_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=".cache") as temp:
            bundle = self.make_bundle(Path(temp))
            (bundle / "preflight.py").write_bytes(b"changed!!")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                verify_bundle(bundle)
        for name in ("../outside", "/absolute", "C:/drive", "a\\b"):
            with self.assertRaises(ValueError):
                check_member(name)


if __name__ == "__main__":
    unittest.main()
