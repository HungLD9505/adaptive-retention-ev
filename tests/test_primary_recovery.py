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

    def city_fixture(self, root: Path) -> tuple[Path, dict, dict, dict]:
        path, plan, original = self.fixture(root)
        base = original["runs"][0]
        original.update(status="predeclared_development_reference", namespace=["charged", "AMS"])
        original["runs"] = []
        for index in range(14):
            row = copy.deepcopy(base)
            row["run_id"] = f"city-method-{index}"
            row["comparison_variant"] = f"method{index}"
            row["binding"]["input"].update(dataset_id="charged", city_id="AMS")
            original["runs"].append(row)
        declaration = {
            "chosen_units": [["charged", "AMS", 7, "fixture", 42]],
            "required_variants": [r["comparison_variant"] for r in original["runs"]],
            "rows": original["runs"],
            "producer_context_sha256": "producer-context",
        }
        (root / "whole-unit.json").write_text(json.dumps(declaration))
        (root / "matrix.json").write_text(json.dumps(original))
        plan.update(
            schema="exact-city-development-migration-v1",
            namespace=["charged", "AMS"],
            whole_unit_sha256=digest(root / "whole-unit.json"),
            producer_context_sha256="producer-context",
        )
        plan["families"] = {
            "matched": {
                "original_matrix": "matrix.json",
                "original_matrix_sha256": digest(root / "matrix.json"),
                "original_total": 14,
                "preserved_ids": [],
                "replay_ids": [r["run_id"] for r in original["runs"]],
            }
        }
        path.write_text(json.dumps(plan))
        return path, plan, original, declaration

    def test_city_reference_is_explicit_and_context_uses_actual_target_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path, plan, original, _ = self.city_fixture(Path(temp))
            _, _, rows = planned_rows(path, digest(path), "matched")
            self.assertEqual(len(rows), 14)
            producer = {
                "training_config": {"seed": 42, "epochs": 10},
                "source_population_sha256": "own-population",
                "input_binding": {"input_manifest_sha256": "own-input"},
                "environment": {"python": "producer"},
            }
            unchanged = copy.deepcopy(producer)
            context = recovery_context(plan, original, rows, {"python": "target"}, producer)
            self.assertEqual(context["namespace"], ["charged", "AMS"])
            self.assertEqual(context["environment"], {"python": "target"})
            self.assertEqual(producer, unchanged)
            with self.assertRaises(ValueError):
                planned_rows(path, digest(path), "proxy")

    def test_city_rejects_incomplete_mixed_or_changed_declaration(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for mutation in ("hash", "missing", "mixed", "namespace", "status", "stage"):
                path, plan, original, declaration = self.city_fixture(root)
                if mutation == "hash":
                    plan["whole_unit_sha256"] = "changed"
                elif mutation == "missing":
                    declaration["required_variants"].pop()
                elif mutation == "mixed":
                    declaration["chosen_units"][0][1] = "LOA"
                elif mutation == "namespace":
                    plan["namespace"] = ["urbanev", "SZH"]
                elif mutation == "status":
                    original["status"] = "technical_success"
                else:
                    original["runs"][0]["binding"]["input"]["stage"] = "source"
                    declaration["rows"] = original["runs"]
                (root / "whole-unit.json").write_text(json.dumps(declaration))
                (root / "matrix.json").write_text(json.dumps(original))
                if mutation != "hash":
                    plan["whole_unit_sha256"] = digest(root / "whole-unit.json")
                plan["families"]["matched"]["original_matrix_sha256"] = digest(root / "matrix.json")
                path.write_text(json.dumps(plan))
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    planned_rows(path, digest(path), "matched")


if __name__ == "__main__":
    unittest.main()
