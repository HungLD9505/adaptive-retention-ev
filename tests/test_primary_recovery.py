"""Missing-only replay identity and resume tests; no downloads or real training."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from ev_models.checkpoint import digest
from tools.replay_missing_primary import planned_rows, recovery_context, restored_prefix


class PrimaryRecoveryTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, dict, dict]:
        sources = {}
        for seed in (42, 43, 44):
            p = root / f"source-{seed}.pt"
            p.write_bytes(f"opaque-independent-fixture-{seed}".encode())
            sources[str(seed)] = {"path": p.name, "sha256": digest(p)}
        config = {"initial_training": {"seed": 42}, "replay_days": 90}
        binding = {
            "dataset_id": "urbanev",
            "city_id": "SZH",
            "stage": "target",
            "history_days": 7,
            "entity_id": "fixture",
            "input_manifest_sha256": "manifest",
        }
        rows = [
            {
                "run_id": f"fixture-{i}",
                "binding": {"input": binding, "config": config},
                "code": {"dirty": False, "files": {"core": "original"}},
            }
            for i in range(3)
        ]
        original = {
            "status": "technical_success",
            "sources": sources,
            "runs": rows,
            "code": rows[0]["code"],
        }
        matrix = root / "matrix.json"
        matrix.write_text(json.dumps(original))
        scope = {
            "original_matrix": matrix.name,
            "original_matrix_sha256": digest(matrix),
            "original_total": 3,
            "preserved_ids": ["fixture-0"],
            "replay_ids": ["fixture-1", "fixture-2"],
        }
        plan = {
            "schema": "exact-missing-development-recovery-v1",
            "sources": sources,
            "families": {"proxy": scope, "matched": copy.deepcopy(scope)},
        }
        path = root / "plan.json"
        path.write_text(json.dumps(plan))
        return path, plan, original

    def test_authenticated_missing_subset_and_source_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path, _, _ = self.fixture(Path(temp))
            _, _, rows = planned_rows(path, digest(path), "proxy")
            self.assertEqual([r["run_id"] for r in rows], ["fixture-1", "fixture-2"])
            (path.parent / "source-43.pt").write_bytes(b"changed")
            with self.assertRaises(ValueError):
                planned_rows(path, digest(path), "proxy")

    def test_reject_scope_mutations_even_with_fresh_plan_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path, plan, _ = self.fixture(Path(temp))
            for field, value in (
                ("replay_ids", ["fixture-2", "fixture-1"]),
                ("replay_ids", ["fixture-0", "fixture-2"]),
                ("replay_ids", ["fixture-1", "fixture-1"]),
                ("original_total", 4),
                ("original_matrix", "../matrix.json"),
            ):
                with self.subTest(field=field, value=value):
                    changed = copy.deepcopy(plan)
                    changed["families"]["proxy"][field] = value
                    path.write_text(json.dumps(changed))
                    with self.assertRaises(ValueError):
                        planned_rows(path, digest(path), "proxy")
            path.write_text(json.dumps(plan))
            with self.assertRaises(ValueError):
                planned_rows(path, "0" * 64, "proxy")

    def test_no_final_or_changed_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path, plan, original = self.fixture(Path(temp))
            for edit in ("dataset", "days", "dirty"):
                changed = copy.deepcopy(original)
                if edit == "dataset":
                    changed["runs"][1]["binding"]["input"]["dataset_id"] = "other"
                elif edit == "days":
                    changed["runs"][1]["binding"]["config"]["replay_days"] = 1
                else:
                    changed["runs"][1]["code"]["dirty"] = True
                matrix = path.parent / "matrix.json"
                matrix.write_text(json.dumps(changed))
                plan["families"]["proxy"]["original_matrix_sha256"] = digest(matrix)
                path.write_text(json.dumps(plan))
                with self.assertRaises(ValueError):
                    planned_rows(path, digest(path), "proxy")

    def test_prefix_resume_rejects_holes_duplicates_extras(self) -> None:
        rows = [{"run_id": x} for x in ("a", "b", "c")]
        self.assertEqual(restored_prefix(rows, rows[:2]), {"a", "b"})
        self.assertEqual(restored_prefix(rows, []), set())
        for restored in (
            [rows[1]],
            [rows[0], rows[0]],
            [{"run_id": "x"}],
            rows + [{"run_id": "extra"}],
        ):
            with self.assertRaises(ValueError):
                restored_prefix(rows, restored)

    def test_context_binds_full_missing_execution_without_source_retraining(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path, plan, original = self.fixture(Path(temp))
            _, _, rows = planned_rows(path, digest(path), "proxy")
            report = {
                "training_config": {"seed": 42, "epochs": 10, "batch_size": 64},
                "source_population_sha256": "population",
                "input_binding": {"input_manifest_sha256": "source-manifest"},
            }
            context = recovery_context(plan, original, rows, {"device": "fixture"}, report)
            self.assertEqual(context["source_training"], {"epochs": 10, "batch_size": 64})
            self.assertEqual(set(context["expected_runs"]), {"fixture-1", "fixture-2"})
            self.assertEqual(
                context["original_sources"], {k: v["sha256"] for k, v in plan["sources"].items()}
            )
            self.assertEqual(context["source_manifest_sha256"], "source-manifest")


if __name__ == "__main__":
    unittest.main()
