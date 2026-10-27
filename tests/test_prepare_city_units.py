"""Independent city migration admission tests; no real data or training."""

import copy
import unittest
from types import SimpleNamespace

from tools.prepare_city_units import city_rows


class CityUnitTests(unittest.TestCase):
    def fixture(self) -> tuple:
        variants = [f"method{i}" for i in range(14)]
        sources = {42: "own42", 43: "own43", 44: "own44"}
        methods, recipes = {}, {}
        for variant in variants:
            config = {
                "initial_training": {"seed": 42},
                "development_entities": ["fixture"],
                "replay_days": 90,
                "method": {"name": variant},
            }
            name = "charged-AMS-" + variant
            methods[variant] = {
                "run_id": name,
                "config": config,
                "input_manifest_sha256": "input7",
                "source_checkpoint_sha256": "own42",
            }
            recipes[name] = {
                "config": copy.deepcopy(config),
                "comparison_variant": variant,
                "history_days": 7,
                "entity_id": "fixture",
                "input_manifest_sha256": "input7",
            }
        unit = {
            "unit": ["charged", "AMS", 7, "fixture", 42],
            "methods": methods,
            "old_accepted_cells_to_repeat_if_migrating": 3,
        }
        context = {
            "namespace": ["charged", "AMS"],
            "seeds": [42, 43, 44],
            "expected_runs": recipes,
            "core_files": {"core": "fixed"},
            "source_population_sha256": "own-population",
            "environment": {"python": "producer"},
        }
        ledger = {"required_variants": variants, "retained_complete_units_excluding_JHB": []}
        data = {
            7: SimpleNamespace(
                sha256="input7",
                namespace=("charged", "AMS"),
                source_hash="own-population",
                config={"history_days": 7},
                entities={
                    ("charged", "AMS", "fixture"): {"role": "development", "status": "ready"}
                },
                binding=lambda stage, entity, source: {
                    "dataset_id": "charged",
                    "city_id": "AMS",
                    "stage": stage,
                    "entity_id": entity,
                    "history_days": 7,
                    "source_checkpoint_sha256": source,
                },
            )
        }
        return [unit], ledger, context, data, sources

    def test_exact_fourteen_original_configs_and_own_city_source(self) -> None:
        args = self.fixture()
        rows = city_rows(*args)
        self.assertEqual(len(rows), 14)
        self.assertEqual(len({r["run_id"] for r in rows}), 14)
        self.assertEqual(
            {r["binding"]["input"]["source_checkpoint_sha256"] for r in rows}, {"own42"}
        )
        self.assertEqual(args[2]["environment"], {"python": "producer"})
        self.assertTrue(all("environment" not in r["binding"] for r in rows))
        self.assertTrue(all("mae" not in r for r in rows))

    def test_reject_changed_namespace_recipe_source_and_missing_method(self) -> None:
        for mutation in (
            "city",
            "config",
            "source",
            "missing",
            "complete",
            "duplicate",
            "bound",
            "seed",
            "manifest",
        ):
            args = self.fixture()
            units, ledger, context, _, _ = args
            first = units[0]["methods"]["method0"]
            if mutation == "city":
                units[0]["unit"][1] = "LOA"
            elif mutation == "config":
                first["config"]["replay_days"] = 1
            elif mutation == "source":
                first["source_checkpoint_sha256"] = "other-city"
            elif mutation == "missing":
                del units[0]["methods"]["method0"]
            elif mutation == "complete":
                ledger["retained_complete_units_excluding_JHB"].append({"unit": units[0]["unit"]})
            elif mutation == "duplicate":
                units.append(copy.deepcopy(units[0]))
            elif mutation == "bound":
                units.clear()
            elif mutation == "seed":
                units[0]["unit"][-1] = 45
            else:
                first["input_manifest_sha256"] = "changed"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                city_rows(*args)

    def test_reject_source_final_or_unready_target_before_value_access(self) -> None:
        for role, status in (
            ("source", "ready"),
            ("final", "ready"),
            ("development", "undefined_scale"),
        ):
            args = self.fixture()
            args[3][7].entities[("charged", "AMS", "fixture")] = {"role": role, "status": status}
            with self.subTest(role=role, status=status), self.assertRaises(ValueError):
                city_rows(*args)


if __name__ == "__main__":
    unittest.main()
