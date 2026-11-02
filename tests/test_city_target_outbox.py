"""Offline city publication, ordering and isolation gates; no cloud/real-data fitting."""

import argparse
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_charged_matched_development as city_fixtures

from ev_models.checkpoint import digest
from tools.charged_matched_development import backup_context
from tools.city_target_outbox import check_source_kit, run, target_plan
from tools.durable_run_backup import canonical
from tools.replay_checkpoint_chunk import check_handoff, select_chunk


class CityTargetOutboxTests(unittest.TestCase):
    def context(self) -> dict:
        fixture = city_fixtures.ChargedReplicationTests()
        fixture.setUp()
        return backup_context(
            fixture.cohort,
            fixture.summary,
            fixture.data,
            {"files": {}},
            {"device": "cuda"},
            cohort_sha256="a" * 64,
            primary_sha256="b" * 64,
        ) | {"environment_profile_sha256": "c" * 64}

    def kit(self, root: Path) -> tuple[dict, str]:
        context = self.context()
        root.mkdir()
        (root / "context.json").write_bytes(canonical(context))
        for seed in (42, 43, 44):
            pin = hashlib.sha256(str(seed).encode()).hexdigest()
            # Opaque transport gate fixture; actual CPU Source restoration is separately tested.
            (root / f"source-seed{seed}.zip").write_bytes(b"opaque fixture")
            (root / f"source-seed{seed}.receipt.json").write_text(
                json.dumps({"record": {"entry": {"sha256": pin}}})
            )
            pub = {
                "schema": "verified-city-source-publication-v1",
                "namespace": "charged-AMS",
                "seed": seed,
                "context_sha256": digest(root / "context.json"),
                "source_checkpoint_sha256": pin,
                "independent_content_verified": True,
                "remote_readback_verified": True,
                "verification_sha256": "d" * 64,
                "artifact": {
                    "drive_url": "https://drive.google.com/file/d/fixture_file_identifier_12345/view",
                    "bytes": 10,
                    "sha256": "e" * 64,
                },
                **{
                    k: context[k]
                    for k in ("cohort_sha256", "primary_sha256", "environment_profile_sha256")
                },
            }
            (root / f"publication-seed{seed}.json").write_text(json.dumps(pub))
        return context, self.pin(root)

    def pin(self, root: Path) -> str:
        files = {
            p.name: {"bytes": p.stat().st_size, "sha256": digest(p)}
            for p in root.iterdir()
            if p.name != "source-kit.json"
        }
        (root / "source-kit.json").write_text(
            json.dumps(
                {
                    "schema": "ev-published-city-source-kit-v1",
                    "namespace": ["charged", "AMS"],
                    "seeds": [42, 43, 44],
                    "files": files,
                }
            )
        )
        return digest(root / "source-kit.json")

    def test_complete_frozen_order_contains_every_budget_seed_and_method(self) -> None:
        context = self.context()
        pin, rows = target_plan(context, "f" * 64)
        self.assertEqual(len(rows), 3 * 3 * 14)
        self.assertEqual({r["history_days"] for r in rows}, {7, 14, 28})
        self.assertEqual({r["config"]["initial_training"]["seed"] for r in rows}, {42, 43, 44})
        self.assertEqual({r["comparison_variant"] for r in rows}, set(city_fixtures.NAMES))
        self.assertEqual(len(select_chunk(rows, 0, 12)), 12)
        self.assertEqual(len(select_chunk(rows, 120, 12)), 6)
        changed = copy.deepcopy(context)
        changed["expected_runs"] = dict(reversed(list(changed["expected_runs"].items())))
        self.assertNotEqual(target_plan(changed, "f" * 64)[0], pin)
        self.assertNotEqual(target_plan(context, "e" * 64)[0], pin)

    def test_exact_three_source_kit_requires_independent_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "kit"
            context, checksum = self.kit(root)
            pins = check_source_kit(root, checksum, context)
            self.assertEqual(set(pins), {42, 43, 44})
            self.assertEqual(len(set(pins.values())), 3)
            bad = copy.deepcopy(context)
            bad["namespace"] = ["charged", "LOA"]
            with self.assertRaises(ValueError):
                check_source_kit(root, checksum, bad)

    def test_freshly_repinned_unaccepted_or_wrong_publication_is_rejected(self) -> None:
        for field, value in (
            ("remote_readback_verified", False),
            ("independent_content_verified", False),
            ("seed", 43),
            ("source_checkpoint_sha256", "0" * 64),
            ("namespace", "urbanev-SZH"),
            ("cohort_sha256", "9" * 64),
            ("verification_sha256", ""),
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "kit"
                context, _ = self.kit(root)
                path = root / "publication-seed42.json"
                pub = json.loads(path.read_text()) | {field: value}
                path.write_text(json.dumps(pub))
                with self.assertRaises(ValueError):
                    check_source_kit(root, self.pin(root), context)

    def test_changed_missing_or_unexpected_source_files_do_not_pass(self) -> None:
        for failure in ("bytes", "missing", "extra", "pin"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "kit"
                context, checksum = self.kit(root)
                if failure == "bytes":
                    (root / "source-seed42.zip").write_bytes(b"changed")
                elif failure == "missing":
                    (root / "source-seed43.zip").unlink()
                elif failure == "extra":
                    (root / "unaccepted.pending").write_bytes(b"preserve")
                else:
                    checksum = "0" * 64
                with self.assertRaises(ValueError):
                    check_source_kit(root, checksum, context)

    def test_city_receipt_cannot_continue_another_city_or_changed_source_plan(self) -> None:
        context = self.context()
        plan, rows = target_plan(context, "e" * 64)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "publication.json"
            pub = {
                "schema": "verified-kaggle-outbox-publication-v1",
                "plan_sha256": plan,
                "family": "charged-AMS",
                "start": 0,
                "end": 12,
                "run_ids": [r["run_id"] for r in rows[:12]],
                "independent_content_verified": True,
                "remote_readback_verified": True,
                "artifact": {
                    "bytes": 10,
                    "sha256": "f" * 64,
                    "drive_url": "https://drive.google.com/file/d/fixture_file_identifier_12345/view",
                },
            }
            path.write_text(json.dumps(pub))
            check_handoff(rows, 12, plan, "charged-AMS", path, digest(path))
            for family, pin in (("charged-LOA", plan), ("charged-AMS", "d" * 64)):
                with self.assertRaises(ValueError):
                    check_handoff(rows, 12, pin, family, path, digest(path))

    def test_no_cloud_cuda_stops_before_reading_dependencies_or_fitting(self) -> None:
        with (
            patch("tools.city_target_outbox.torch.cuda.is_available", return_value=False),
            patch("tools.city_target_outbox.execute") as target,
            self.assertRaises(ValueError),
        ):
            run(argparse.Namespace())
        target.assert_not_called()


if __name__ == "__main__":
    unittest.main()
