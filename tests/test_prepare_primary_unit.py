"""Independent metadata-only preparation tests, including fail-closed scope guards."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from ev_models.checkpoint import digest, write_json
from tools.prepare_primary_unit import prepare


class PrepareUnitTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, Path, dict]:
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
        pins = []
        for name, subset in (("proxy", rows[:4]), ("matched", rows[4:])):
            p = root / f"{name}-selected-original-matrix.json"
            write_json(p, {**template, "status": "technical_success", "runs": subset})
            pins.append({"path": str(p), "sha256": digest(p)})
        ledger = {
            "schema": "ev-current-whole-unit-remaining-ledger-v1",
            "pins": pins,
            "required_variants": methods,
            "retained_complete_units_excluding_JHB": [],
            "remaining_units": [
                {
                    "unit": ["urbanev", "SZH", 7, "fixture", 42],
                    "methods": expected,
                    "old_accepted_cells_to_repeat_if_migrating": 4,
                }
            ],
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


if __name__ == "__main__":
    unittest.main()
