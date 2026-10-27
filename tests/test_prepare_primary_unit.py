"""Independent metadata-only preparation tests, including fail-closed scope guards."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from ev_models.checkpoint import digest, write_json
from tools.prepare_primary_unit import prepare


class PrepareUnitTests(unittest.TestCase):
    def fixture(self, root: Path, count: int = 1) -> tuple[Path, Path, dict]:
        methods = [f"method{i:02d}" for i in range(14)]
        sources = {str(s): {"sha256": str(s), "epochs": 10} for s in (42, 43, 44)}
        template = {"code": {"dirty": False, "files": {"core": "fixed"}}, "sources": sources}
        write_json(root / "template.json", template)
        rows, expected = [], {}
        for name in methods:
            binding = {
                "dataset_id": "urbanev",
                "city_id": "SZH",
                "stage": "target",
                "entity_id": "fixture",
                "history_days": 7,
                "input_manifest_sha256": "input",
                "source_checkpoint_sha256": "42",
            }
            config = {"initial_training": {"seed": 42}, "method": {"name": name}, "replay_days": 90}
            rows.append(
                {
                    "run_id": name,
                    "binding": {"input": binding, "config": config},
                    "code": template["code"],
                }
            )
            expected[name] = {
                "run_id": name,
                "config": config,
                "input_manifest_sha256": "input",
                "source_checkpoint_sha256": "42",
            }
        units = [
            {
                "unit": ["urbanev", "SZH", 7, "fixture", 42],
                "methods": expected,
                "old_accepted_cells_to_repeat_if_migrating": 4,
            }
        ]
        base = copy.deepcopy(rows)
        for index in range(1, count):
            entity, seed, budget = f"fixture{index}", 42 + index % 3, (7, 14, 28)[index % 3]
            new_rows = copy.deepcopy(base)
            methods_by_name = {}
            for row in new_rows:
                binding, config = row["binding"]["input"], row["binding"]["config"]
                row["run_id"] = entity + "-" + row["run_id"]
                binding.update(
                    entity_id=entity, history_days=budget, source_checkpoint_sha256=str(seed)
                )
                config["initial_training"]["seed"] = seed
                methods_by_name[config["method"]["name"]] = {
                    "run_id": row["run_id"],
                    "config": config,
                    "input_manifest_sha256": binding["input_manifest_sha256"],
                    "source_checkpoint_sha256": binding["source_checkpoint_sha256"],
                }
            rows.extend(new_rows)
            units.append(
                {
                    "unit": ["urbanev", "SZH", budget, entity, seed],
                    "methods": methods_by_name,
                    "old_accepted_cells_to_repeat_if_migrating": 4,
                }
            )
        pins = []
        proxy = [row for i, row in enumerate(rows) if i % 14 < 4]
        matched = [row for i, row in enumerate(rows) if i % 14 >= 4]
        for name, subset in (("proxy", proxy), ("matched", matched)):
            p = root / f"{name}-selected-original-matrix.json"
            write_json(p, {**template, "status": "technical_success", "runs": subset})
            pins.append({"path": str(p), "sha256": digest(p)})
        ledger = {
            "schema": "ev-current-whole-unit-remaining-ledger-v1",
            "pins": pins,
            "required_variants": methods,
            "retained_complete_units_excluding_JHB": [],
            "remaining_units": units,
        }
        p = root / "ledger.json"
        write_json(p, ledger)
        return p, root / "template.json", ledger

    def test_all_fourteen_exact_configs_and_non_overlapping_partitions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger, template, _ = self.fixture(root)
            result = prepare(ledger, digest(ledger), template, digest(template), root / "out")
            self.assertEqual(result["declared_repeat_cells"], 4)
            seen = []
            for name, count in (("0000-0012", 12), ("0012-0014", 2)):
                plan = json.loads((root / "out" / name / "plan.json").read_text())
                self.assertEqual(plan["families"]["matched"]["original_total"], count)
                seen.extend(plan["families"]["matched"]["replay_ids"])
            self.assertEqual(len(set(seen)), 14)
            with self.assertRaises(FileExistsError):
                prepare(ledger, digest(ledger), template, digest(template), root / "out")

    def test_reject_changed_pin_completed_unit_and_changed_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger, template, original = self.fixture(root)
            with self.assertRaises(ValueError):
                prepare(ledger, "bad", template, digest(template), root / "out")
            for mutation in ("complete", "config", "city", "method"):
                value = copy.deepcopy(original)
                unit = value["remaining_units"][0]
                if mutation == "complete":
                    value["retained_complete_units_excluding_JHB"] = [{"unit": unit["unit"]}]
                elif mutation == "config":
                    unit["methods"]["method00"]["config"]["replay_days"] = 1
                elif mutation == "city":
                    unit["unit"][:2] = ["charged", "AMS"]
                else:
                    del unit["methods"]["method00"]
                ledger.write_text(json.dumps(value))
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    prepare(ledger, digest(ledger), template, digest(template), root / "out")
                self.assertFalse((root / "out").exists())

    def test_reject_changed_ensemble_source_even_when_initial_source_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger, template, _ = self.fixture(root)
            value = json.loads(template.read_text())
            value["sources"]["44"]["sha256"] = "wrong ensemble"
            template.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                prepare(ledger, digest(ledger), template, digest(template), root / "out")

    def test_complete_unit_prefix_publication_preserves_each_seed_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger, template, value = self.fixture(root, count=4)
            result = prepare(
                ledger, digest(ledger), template, digest(template), root / "out", whole_unit_count=4
            )
            self.assertEqual(result["chosen_units"], [u["unit"] for u in value["remaining_units"]])
            self.assertEqual(result["publication_mode"], "complete_unit_prefix")
            self.assertEqual(result["declared_repeat_cells"], 16)
            self.assertEqual(len(result["rows"]), 56)
            plan = json.loads((root / "out/0000-0056/plan.json").read_text())
            self.assertEqual(plan["families"]["matched"]["original_total"], 56)
            self.assertEqual(len(set(plan["families"]["matched"]["replay_ids"])), 56)
            for i, unit in enumerate(value["remaining_units"]):
                group = result["rows"][14 * i : 14 * (i + 1)]
                self.assertEqual(
                    {r["binding"]["input"]["entity_id"] for r in group}, {unit["unit"][3]}
                )
                for row in group:
                    self.assertEqual(
                        row["binding"]["config"],
                        unit["methods"][row["comparison_variant"]]["config"],
                    )

    def test_complete_single_unit_and_invalid_batch_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger, template, _ = self.fixture(root)
            for count in (-1, 0, 5, True, 2):
                with self.subTest(count=count), self.assertRaises(ValueError):
                    prepare(
                        ledger,
                        digest(ledger),
                        template,
                        digest(template),
                        root / "bad",
                        whole_unit_count=count,
                    )
                self.assertFalse((root / "bad").exists())
            result = prepare(
                ledger, digest(ledger), template, digest(template), root / "out", whole_unit_count=1
            )
            self.assertEqual(len(result["rows"]), 14)
            self.assertTrue((root / "out/0000-0014/plan.json").is_file())

    def test_reject_bad_later_unit_before_creating_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger, template, original = self.fixture(root, count=2)
            for mutation in ("city", "duplicate", "complete", "config"):
                value = copy.deepcopy(original)
                unit = value["remaining_units"][1]
                if mutation == "city":
                    unit["unit"][:2] = ["charged", "AMS"]
                elif mutation == "duplicate":
                    value["remaining_units"][1] = copy.deepcopy(value["remaining_units"][0])
                elif mutation == "complete":
                    value["retained_complete_units_excluding_JHB"] = [{"unit": unit["unit"]}]
                else:
                    unit["methods"]["method00"]["config"]["replay_days"] = 1
                ledger.write_text(json.dumps(value))
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    prepare(
                        ledger,
                        digest(ledger),
                        template,
                        digest(template),
                        root / "out",
                        whole_unit_count=2,
                    )
                self.assertFalse((root / "out").exists())


if __name__ == "__main__":
    unittest.main()
