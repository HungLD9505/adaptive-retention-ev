"""City orchestration storage/failure fixtures; no model training or downloads."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.city_pipeline import (
    handoff_exports,
    publish_file,
    run_pipeline,
    run_stage,
    sha,
    training_command,
)


class CityPipelineTests(unittest.TestCase):
    def test_new_copy_readback_and_overwrite_refusal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, destination = root / "source", root / "copy"
            source.write_bytes(b"fixture original bytes")
            publish_file(source, destination)
            self.assertEqual(destination.read_bytes(), source.read_bytes())
            source.write_bytes(b"new bytes must not replace original")
            with self.assertRaises(ValueError):
                publish_file(source, destination)
            self.assertEqual(destination.read_bytes(), b"fixture original bytes")

    def test_corrupt_copy_preserves_pending_not_completed_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, destination = root / "source", root / "copy"
            source.write_bytes(b"original fixture")
            with patch(
                "tools.city_pipeline.shutil.copyfileobj", side_effect=lambda a, b: b.write(b"bad")
            ):
                with self.assertRaisesRegex(ValueError, "Handoff copy changed"):
                    publish_file(source, destination)
            self.assertFalse(destination.exists())
            self.assertEqual((root / "copy.pending").read_bytes(), b"bad")

    def test_source_change_during_copy_cannot_change_the_published_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, destination = root / "source", root / "copy"
            source.write_bytes(b"original")

            def changed(input_stream, output_stream):
                source.write_bytes(b"mutated!")
                output_stream.write(input_stream.read())

            with patch("tools.city_pipeline.shutil.copyfileobj", side_effect=changed):
                with self.assertRaisesRegex(ValueError, "Handoff copy changed"):
                    publish_file(source, destination)
            self.assertFalse(destination.exists())
            self.assertTrue((root / "copy.pending").exists())

    def test_wrong_checkout_is_rejected_before_any_output_or_training(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "same checkout"):
                run_pipeline(SimpleNamespace(repo=Path(temp)))

    def test_training_command_requires_backup_and_only_explicit_resume(self) -> None:
        args = SimpleNamespace(
            inputs_root=Path("inputs"),
            cohort_sha256="cohort-sha",
            primary_sha256="primary-sha",
            backup_root=Path("backup"),
            drive_mount=Path("mount"),
            resume_backup=False,
        )
        command = training_command(args, Path("root"), Path("study"))
        self.assertEqual(command[command.index("--backup-root") + 1], Path("backup"))
        self.assertEqual(command[command.index("--drive-mount") + 1], Path("mount"))
        self.assertNotIn("--resume-backup", command)
        args.resume_backup = True
        self.assertIn("--resume-backup", training_command(args, Path("root"), Path("study")))

    def test_stage_failure_is_logged_durably_and_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "root"
            handoff = Path(temp) / "handoff"
            root.mkdir()
            handoff.mkdir()
            metadata = {"stages": []}

            def failed(command, **kwargs):
                kwargs["stdout"].write("fixture failed before fitting\n")
                return SimpleNamespace(returncode=9)

            with patch("tools.city_pipeline.subprocess.run", side_effect=failed):
                with self.assertRaisesRegex(RuntimeError, "Stage failed"):
                    run_stage("training", ["fixture_only"], root, root, handoff, metadata)
            self.assertEqual(metadata["stages"][0]["exit_code"], 9)
            self.assertEqual(
                json.loads((handoff / "training-stage.json").read_text())["exit_code"], 9
            )
            self.assertEqual(
                (handoff / "training.log").read_bytes(), (root / "training.log").read_bytes()
            )
            self.assertFalse((handoff / "export-start.json").exists())

    def test_canonical_export_population_and_hashes_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            exports = root / "exports"
            exports.mkdir()
            part = exports / "code.bundle"
            part.write_bytes(b"opaque fixture bytes, not executable")
            catalog = {
                "status": "complete",
                "parts": [{"name": part.name, "bytes": part.stat().st_size, "sha256": sha(part)}],
            }
            (exports / "catalog.json").write_text(json.dumps(catalog))
            handoff_exports(exports, root / "handoff")
            self.assertEqual((root / "handoff/code.bundle").read_bytes(), part.read_bytes())
            part.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "Changed export"):
                handoff_exports(exports, root / "changed")
            part.write_bytes(b"opaque fixture bytes, not executable")
            (exports / "unknown").write_text("unexpected")
            with self.assertRaisesRegex(ValueError, "Missing/extra"):
                handoff_exports(exports, root / "extra")


if __name__ == "__main__":
    unittest.main()
