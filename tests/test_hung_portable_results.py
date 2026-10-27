"""Cross-provider daily-error reconciliation uses disjoint, hash-pinned evidence."""

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch

from tools import hung_portable_results as portable
from tools import hung_results as scorer


class PortableTests(unittest.TestCase):
    def record(self, method="main", days=None):
        days = (
            days
            if days is not None
            else {"d1": {"absolute": 48, "squared": 96, "label_sha256": "a" * 64}}
        )
        return {
            "job_id": method + "_b7s7e1",
            "method": method,
            "budget": 7,
            "seed": 7,
            "entity_id": "1",
            "status": "DISPATCH_VERIFIED",
            "input_manifest_sha256": "b" * 64,
            "source_sha256": "c" * 64,
            "target_sha256": "d" * 64,
            "days": days,
            "coverage": {"requested": 90, "created": 1, "scored": len(days)},
            "metrics": scorer.metrics(list(days.values())),
        }

    def merge(self, root, groups):
        spec = {"scope": "development_only", "spec_sha256": "f" * 64, "collections": []}
        for i, rows in enumerate(groups):
            path = root / f"export{i}.json"
            value = {
                "schema": "hung-portable-daily-errors-v1",
                "scope": "development_only",
                "canonical_plan_sha256": portable.PLAN_SHA,
                "scorer_sha256": portable.SCORER_SHA,
                "records": rows,
            }
            path.write_text(json.dumps(value), encoding="utf-8")
            spec["collections"].append(
                {
                    "export": {"path": str(path), "sha256": scorer.file_sha(path)},
                    "job_ids": [r["job_id"] for r in rows],
                }
            )
        return portable.merge_collections(spec, root)

    def test_cross_collection_pair_uses_common_days_not_summary_average(self):
        candidate = self.record(
            "online_best",
            {
                "d1": {"absolute": 24, "squared": 24, "label_sha256": "a" * 64},
                "d2": {"absolute": 2400, "squared": 240000, "label_sha256": "b" * 64},
            },
        )
        candidate["coverage"]["created"] = 2
        with tempfile.TemporaryDirectory(dir=".") as directory:
            result = self.merge(Path(directory).resolve(), [[self.record()], [candidate]])
        self.assertEqual(result["counts"]["runs"], 2)
        self.assertEqual(result["paired_cells"][0]["paired_days"], 1)
        self.assertEqual(result["station_first"][0]["method_metrics"]["mae_kwh"], 1)

    def test_duplicate_main_anchor_fails(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                self.merge(Path(directory).resolve(), [[self.record()], [self.record()]])

    def test_different_job_id_same_cell_method_fails(self):
        other = self.record()
        other["job_id"] = "forged-other-id"
        with tempfile.TemporaryDirectory(dir=".") as directory:
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                self.merge(Path(directory).resolve(), [[self.record()], [other]])

    def test_forged_metrics_and_nonfinite_errors_fail(self):
        for change in ("metric", "nonfinite", "negative", "coverage"):
            row = self.record()
            if change == "metric":
                row["metrics"]["mae_kwh"] = 0
            elif change == "coverage":
                row["coverage"]["scored"] = 2
            else:
                row["days"]["d1"]["absolute"] = float("nan") if change == "nonfinite" else -1
            with self.subTest(change=change), tempfile.TemporaryDirectory(dir=".") as directory:
                with self.assertRaises(ValueError):
                    self.merge(Path(directory).resolve(), [[row]])

    def test_missing_labels_stay_zero_scored(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            result = self.merge(Path(directory).resolve(), [[self.record(days={})]])
        self.assertEqual(result["counts"]["zero_scored_runs"], 1)
        self.assertIsNone(result["runs"][0]["metrics"])

    def test_changed_label_and_initialization_block_pair(self):
        for key in ("label", "source"):
            candidate = self.record("online_best")
            if key == "label":
                candidate["days"]["d1"]["label_sha256"] = "e" * 64
            else:
                candidate["source_sha256"] = "e" * 64
            with self.subTest(key=key), tempfile.TemporaryDirectory(dir=".") as directory:
                result = self.merge(Path(directory).resolve(), [[self.record()], [candidate]])
            self.assertFalse(result["paired_cells"])
            self.assertEqual(len(result["blocked_pairs"]), 1)

    def test_relocation_preserves_hashes_and_original(self):
        original = {
            "runs": [{"checkpoint": {"path": "/kaggle/working/run/repo/a.pt", "sha256": "a" * 64}}]
        }
        untouched = copy.deepcopy(original)
        result = portable.relocate_catalog(original, "/kaggle/working/run", Path("mounted"))
        self.assertEqual(result["runs"][0]["checkpoint"]["sha256"], "a" * 64)
        self.assertEqual(original, untouched)
        for bad in ("/elsewhere/a.pt", "/kaggle/working/run/../a.pt"):
            original["runs"][0]["checkpoint"]["path"] = bad
            with self.assertRaises(ValueError):
                portable.relocate_catalog(original, "/kaggle/working/run", Path("mounted"))

    def test_export_rechecks_real_checkpoint_and_retains_daily_errors(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            root = Path(directory).resolve()
            binding = {"input_manifest_sha256": "a" * 64, "entity_id": "1", "history_days": 7}
            state = {
                "schema": "hung-single-baseline-runner-v1",
                "binding": binding,
                "energy_scale": 1,
                "issued": [
                    {
                        "day_id": "d1",
                        "prediction": torch.ones(1, 24),
                        "y_scaled": torch.zeros(24),
                        "normalized_mae": 1,
                    }
                ],
            }
            checkpoint = root / "checkpoint.pt"
            torch.save(state, checkpoint)
            manifest = {
                "status": "completed",
                "input_binding": binding,
                "config": {"seed": 7},
                "code": {"commit": "fixture-code"},
                "coverage": {"created": 1, "scored": 1},
                "metrics_kwh": {"hours": 24, "mae_kwh": 1, "rmse_kwh": 1},
                "final_runner_checkpoint_sha256": scorer.file_sha(checkpoint),
            }
            path = root / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            entry = {
                "job_id": "target_only_b7s7e1",
                "method": "target_only",
                "budget": 7,
                "seed": 7,
                "entity_id": "1",
                "input_manifest_sha256": "a" * 64,
                "status": "DISPATCH_VERIFIED",
                "manifest": scorer.pin(path, root),
                "checkpoint": scorer.pin(checkpoint, root),
                "proofs": [scorer.pin(path, root)],
            }
            plan = root / "plan.json"
            plan.write_text(json.dumps({"scope": "development_only"}), encoding="utf-8")
            catalog = {
                "scope": "development_only",
                "runs": [entry],
                "spec": {"plan": scorer.pin(plan, root)},
            }
            with patch.object(portable, "PLAN_SHA", scorer.file_sha(plan)):
                result = portable.export_catalog(catalog, root, {})
                self.assertEqual(result["records"][0]["days"]["d1"]["absolute"], 24)
                checkpoint.write_bytes(b"damaged")
                with self.assertRaises(ValueError):
                    portable.export_catalog(catalog, root, {})

    def test_export_source_change_stops(self):
        with patch.object(
            scorer, "file_sha", return_value=hashlib.sha256(b"different").hexdigest()
        ):
            with self.assertRaisesRegex(ValueError, "Scorer"):
                portable.export_catalog({}, Path("."), {})

    def receiver_fixture(self, root):
        mounted = root / "run"
        evidence = mounted / "cpu-readback"
        evidence.mkdir(parents=True)
        log = evidence / "verify.log"
        log.write_text("verified fixture only", encoding="utf-8")
        terminal = {
            "exit_code": 0,
            "executed": False,
            "log_sha256": scorer.file_sha(log),
            "command": [
                "python",
                "--plan",
                "/kaggle/working/run/repo/.cache/provider/plan.json",
                "--verify-only",
            ],
        }
        (evidence / "verify-exit.json").write_text(json.dumps(terminal), encoding="utf-8")
        catalog = evidence / "catalog.json"
        catalog.write_text(
            json.dumps(
                {
                    "runs": [
                        {
                            "manifest": {
                                "path": "/kaggle/working/run/repo/a.json",
                                "sha256": "a" * 64,
                            }
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        proof = {
            "scope": "development_only",
            "passed": True,
            "executed": False,
            "model_code_commit": portable.MODEL_CODE,
            "scorer_sha256": portable.SCORER_SHA,
            "derivation": {"parent_plan_sha256": portable.PLAN_SHA},
            "verification": terminal,
            "catalog_sha256": scorer.file_sha(catalog),
            "jobs": 1,
        }
        path = mounted / "receiver-proof.json"
        path.write_text(json.dumps(proof), encoding="utf-8")
        return mounted, scorer.file_sha(path)

    def test_receiver_relocation_uses_exact_pinned_proof(self):
        with tempfile.TemporaryDirectory(dir=".") as directory:
            mounted, digest = self.receiver_fixture(Path(directory).resolve())
            with patch.object(
                portable, "export_catalog", return_value={"passed_fixture": True}
            ) as export:
                result = portable.export_receiver(mounted, digest)
            self.assertTrue(result["passed_fixture"])
            relocated = export.call_args.args[0]
            self.assertEqual(relocated["runs"][0]["manifest"]["path"], str(mounted / "repo/a.json"))

    def test_receiver_damaged_log_or_failed_exit_never_exports(self):
        for damage in ("log", "exit", "proof"):
            with self.subTest(damage=damage), tempfile.TemporaryDirectory(dir=".") as directory:
                mounted, digest = self.receiver_fixture(Path(directory).resolve())
                path = mounted / (
                    "receiver-proof.json"
                    if damage == "proof"
                    else "cpu-readback/verify.log"
                    if damage == "log"
                    else "cpu-readback/verify-exit.json"
                )
                path.write_text("{}", encoding="utf-8")
                with (
                    patch.object(portable, "export_catalog") as export,
                    self.assertRaises(ValueError),
                ):
                    portable.export_receiver(mounted, digest)
                export.assert_not_called()


if __name__ == "__main__":
    unittest.main()
