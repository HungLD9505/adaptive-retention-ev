"""Cloud selection must preserve path admission, profile and CPU fitting boundaries."""

import argparse
import contextlib
import importlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.cloud_outbox import cloud_working_root, crosses_mounted_storage


class CloudOutboxTests(unittest.TestCase):
    def test_default_is_existing_kaggle_root_and_colab_is_explicit(self) -> None:
        self.assertEqual(cloud_working_root(), Path("/kaggle/working"))
        self.assertEqual(cloud_working_root("/content"), Path("/content"))

    def test_arbitrary_or_traversal_root_overrides_are_rejected(self) -> None:
        for value in ("/", "/tmp", "content", "/content/..", "/content/drive", "", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                cloud_working_root(value)

    def test_colab_reserved_drive_and_other_nested_mounts_are_not_local_outboxes(self) -> None:
        self.assertTrue(crosses_mounted_storage(Path("/content/drive/new"), Path("/content")))
        with tempfile.TemporaryDirectory() as temp:
            cloud = Path(temp).resolve()
            mounted = cloud / "external"
            with patch.object(Path, "is_mount", lambda p: p == mounted):
                self.assertTrue(crosses_mounted_storage(mounted / "new", cloud))
                self.assertFalse(crosses_mounted_storage(cloud / "scratch/new", cloud))

    def test_admission_rejects_nested_mount_without_creating_or_touching_outputs(self) -> None:
        from tools.city_source_outbox import require_outbox

        with tempfile.TemporaryDirectory() as temp:
            cloud = Path(temp).resolve()
            data = cloud / "inputs"
            data.mkdir()
            sentinel = data / "raw-fixture"
            sentinel.write_bytes(b"immutable fixture")
            mounted = cloud / "external"
            with (
                patch.object(Path, "is_mount", lambda p: p == mounted),
                self.assertRaises(ValueError),
            ):
                require_outbox(mounted / "new", data, cloud)
            self.assertFalse(mounted.exists())
            self.assertEqual(sentinel.read_bytes(), b"immutable fixture")

    def test_all_three_clis_select_root_without_running_a_fit(self) -> None:
        common = [
            "--inputs-root",
            "fixture-inputs",
            "--output",
            "fixture-output",
        ]
        city = [
            "--cohort",
            "fixture-cohort",
            "--cohort-sha256",
            "cohort-pin",
            "--primary-analysis",
            "fixture-primary",
            "--primary-sha256",
            "primary-pin",
            "--environment-profile",
            "fixture-profile",
            "--environment-sha256",
            "profile-pin",
        ]
        commands = {
            "tools.city_source_outbox": common + city + ["--seed", "42"],
            "tools.city_target_outbox": common
            + city
            + [
                "--sources-root",
                "fixture-sources",
                "--sources-sha256",
                "source-pin",
            ],
            "tools.replay_checkpoint_chunk": common
            + [
                "--plan",
                "fixture-plan",
                "--plan-sha256",
                "plan-pin",
                "--family",
                "matched",
            ],
        }
        for name, arguments in commands.items():
            module = importlib.import_module(name)
            for root in (None, "/kaggle/working", "/content", "/tmp"):
                argv = [name, *arguments] + ([] if root is None else ["--cloud-root", root])
                with (
                    self.subTest(cli=name, root=root),
                    patch("sys.argv", argv),
                    patch.object(module, "run") as runner,
                    contextlib.redirect_stderr(io.StringIO()),
                ):
                    if root == "/tmp":
                        with self.assertRaises(SystemExit) as error:
                            module.main()
                        self.assertEqual(error.exception.code, 2)
                        runner.assert_not_called()
                    else:
                        module.main()
                        runner.assert_called_once()
                        self.assertEqual(
                            runner.call_args.args[0].cloud_root, root or "/kaggle/working"
                        )

    def test_colab_selection_cannot_enable_local_cpu_training(self) -> None:
        for name, trainer_name in (
            ("tools.city_source_outbox", "train_source"),
            ("tools.city_target_outbox", "execute"),
        ):
            module = importlib.import_module(name)
            with (
                self.subTest(cli=name),
                patch.object(module.torch.cuda, "is_available", return_value=False),
                patch.object(module, trainer_name) as trainer,
                self.assertRaises(ValueError),
            ):
                module.run(argparse.Namespace(seed=42, cloud_root="/content"))
            trainer.assert_not_called()

    def test_primary_colab_selection_also_stops_before_cpu_fitting(self) -> None:
        from tools import replay_checkpoint_chunk as primary

        args = argparse.Namespace(
            plan=Path("fixture-plan"),
            plan_sha256="fixture-pin",
            family="matched",
            start=0,
            count=1,
            previous_handoff=None,
            previous_handoff_sha256=None,
            cloud_root="/content",
        )
        with (
            patch.object(primary, "planned_rows", return_value=({}, {}, [{"run_id": "fixture"}])),
            patch.object(primary.torch.cuda, "is_available", return_value=False),
            patch.object(primary, "execute") as trainer,
            self.assertRaises(ValueError),
        ):
            primary.run(args)
        trainer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
