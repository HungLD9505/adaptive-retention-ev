"""Independent city migration admission tests; no real data or training."""

import copy
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ev_models.checkpoint import digest
from tools.prepare_city_units import city_rows, main, pending_prefix, prepare


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
            "source_epochs": 10,
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

    def test_reject_missing_changed_or_noninteger_original_source_epochs(self) -> None:
        for epochs in (None, 1, 11, 10.0, True):
            args = self.fixture()
            if epochs is None:
                del args[2]["source_epochs"]
            else:
                args[2]["source_epochs"] = epochs
            with self.subTest(epochs=epochs), self.assertRaises(ValueError):
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

    def test_second_publication_is_disjoint_and_does_not_advance_ledger(self) -> None:
        args = self.fixture()
        units, ledger = args[:2]
        following = copy.deepcopy(units[0])
        following["unit"][3] = "next"
        for entry in following["methods"].values():
            entry["run_id"] += "-next"
            entry["config"]["development_entities"] = ["next"]
        ledger["remaining_units"] = [units[0], following]
        reserved = {"chosen_units": [units[0]["unit"]], "rows": city_rows(*args)}
        before = copy.deepcopy(ledger)
        self.assertEqual(pending_prefix(ledger, 1, reserved), [following])
        self.assertEqual(pending_prefix(ledger, 1), [units[0]])
        self.assertEqual(ledger, before)
        for mutation in ("order", "missing", "duplicate", "config", "empty"):
            value = copy.deepcopy(reserved)
            if mutation == "order":
                value["chosen_units"] = [following["unit"]]
            elif mutation == "missing":
                value["rows"].pop()
            elif mutation == "duplicate":
                value["rows"][0] = value["rows"][1]
            elif mutation == "config":
                value["rows"][0]["binding"]["config"]["replay_days"] = 1
            else:
                value["chosen_units"] = []
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                pending_prefix(ledger, 1, value)
        with self.assertRaises(ValueError):
            pending_prefix(ledger, 2, reserved)

    def reservation_fixture(self, count: int = 10) -> tuple:
        units, ledger, context, data, sources = self.fixture()
        template = units.pop()
        context["expected_runs"].clear()
        for index in range(count):
            unit = copy.deepcopy(template)
            entity = f"target{index}"
            unit["unit"][3] = entity
            data[7].entities[("charged", "AMS", entity)] = {
                "role": "development",
                "status": "ready",
            }
            for variant, entry in unit["methods"].items():
                entry["run_id"] += f"-{index}"
                entry["config"]["development_entities"] = [entity]
                context["expected_runs"][entry["run_id"]] = {
                    "config": copy.deepcopy(entry["config"]),
                    "comparison_variant": variant,
                    "history_days": 7,
                    "entity_id": entity,
                    "input_manifest_sha256": "input7",
                }
            units.append(unit)
        ledger["remaining_units"] = units
        return units, ledger, context, data, sources

    def reserve(self, args: tuple, start: int, stop: int) -> dict:
        units, *rest = args
        return {
            "chosen_units": [u["unit"] for u in units[start:stop]],
            "rows": city_rows(units[start:stop], *rest),
        }

    def test_multiple_reservations_allow_later_workers_without_ledger_mutation(self) -> None:
        args = self.reservation_fixture()
        units, ledger = args[:2]
        reservations = [self.reserve(args, 0, 2), self.reserve(args, 2, 6)]
        before = copy.deepcopy(ledger)
        self.assertEqual(pending_prefix(ledger, 4, reservations), units[6:10])
        # More than two preceding publications are permitted; capacity is measured elsewhere.
        reservations.append(self.reserve(args, 6, 7))
        self.assertEqual(pending_prefix(ledger, 3, reservations), units[7:10])
        self.assertEqual(ledger, before)

    def test_multiple_reservations_reject_overlap_reorder_holes_and_changed_rows(self) -> None:
        args = self.reservation_fixture()
        ledger = args[1]
        first, following = self.reserve(args, 0, 2), self.reserve(args, 2, 4)
        cases = {
            "overlap": [first, self.reserve(args, 1, 3)],
            "reorder": [following, first],
            "hole": [first, self.reserve(args, 3, 4)],
            "duplicate_declaration": [first, first],
            "empty": [first, {"chosen_units": [], "rows": []}],
            "oversized": [first, self.reserve(args, 2, 6)],
        }
        cases["oversized"][1]["chosen_units"].append(args[0][6]["unit"])
        for mutation in ("config", "run_id", "missing", "duplicate_row"):
            changed = copy.deepcopy(following)
            if mutation == "config":
                changed["rows"][0]["binding"]["config"]["replay_days"] = 1
            elif mutation == "run_id":
                changed["rows"][0]["run_id"] = "other"
            elif mutation == "missing":
                changed["rows"].pop()
            else:
                changed["rows"][0] = changed["rows"][1]
            cases[mutation] = [first, changed]
        before = copy.deepcopy(ledger)
        for name, reservations in cases.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                pending_prefix(ledger, 1, reservations)
            self.assertEqual(ledger, before)
        for count in (0, 5, True):
            with self.subTest(count=count), self.assertRaises(ValueError):
                pending_prefix(ledger, count, [first, following])

    def test_pinned_reservation_authentication_and_argument_counts(self) -> None:
        args = self.reservation_fixture()
        ledger = {**args[1], "schema": "ev-current-whole-unit-remaining-ledger-v1"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ledger_path = root / "ledger.json"
            ledger_path.write_text(json.dumps(ledger))
            checksum = digest(ledger_path)
            paths = [root / "first.json", root / "second.json"]
            reservations = [self.reserve(args, 0, 1), self.reserve(args, 1, 2)]
            for path, reservation in zip(paths, reservations, strict=True):
                path.write_text(json.dumps({**reservation, "remaining_ledger_sha256": checksum}))
            hashes = [digest(path) for path in paths]
            before = ledger_path.read_bytes()
            cases = [
                (paths, hashes[:1], "One immutable hash"),
                (paths[:1], hashes, "One immutable hash"),
                (paths, [hashes[0], "changed"], "Changed reserved"),
                ([paths[0], paths[0]], [hashes[0], hashes[0]], "Duplicate"),
                (paths, None, "Both reserved"),
                (None, hashes, "Both reserved"),
            ]
            for reserved_paths, reserved_hashes, message in cases:
                with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                    prepare(
                        ledger_path,
                        checksum,
                        root,
                        root,
                        root / "out",
                        1,
                        reserved_path=reserved_paths,
                        reserved_sha256=reserved_hashes,
                    )
                self.assertEqual(ledger_path.read_bytes(), before)
                self.assertFalse((root / "out").exists())
            value = json.loads(paths[1].read_text())
            value["remaining_ledger_sha256"] = "other-ledger"
            paths[1].write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "another ledger"):
                prepare(
                    ledger_path,
                    checksum,
                    root,
                    root,
                    root / "out",
                    1,
                    reserved_path=paths,
                    reserved_sha256=[hashes[0], digest(paths[1])],
                )
            self.assertEqual(ledger_path.read_bytes(), before)

    def test_prepare_records_all_pins_and_preserves_scalar_compatibility(self) -> None:
        args = self.reservation_fixture(4)
        units, ledger, context, data, sources = args
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            kit = root / "source-kit"
            kit.mkdir()
            for seed in sources:
                checkpoint = root / f"checkpoint-{seed}"
                checkpoint.write_bytes(f"fixture-{seed}".encode())
                sources[seed] = digest(checkpoint)
                with zipfile.ZipFile(kit / f"source-seed{seed}.zip", "w") as archive:
                    for name in ("epoch-10.pt", "epoch-10.pt.sha256", "run.json"):
                        archive.writestr(f"study/source-seed{seed}/{name}", checkpoint.read_bytes())
                    archive.writestr(f"study/source-seed{seed}.log", "fixture")
                (kit / f"source-seed{seed}.receipt.json").write_text(
                    json.dumps({"record": {"entry": {"fixture": True}}})
                )
            for unit in units:
                for entry in unit["methods"].values():
                    entry["source_checkpoint_sha256"] = sources[42]
            context.update(
                cohort_sha256="cohort",
                primary_sha256="primary",
                environment_profile_sha256="environment",
            )
            target = {
                "source_kit_sha256": "source-kit",
                "source_checkpoints": {str(seed): value for seed, value in sources.items()},
                "run_ids": list(context["expected_runs"]),
                "cohort_sha256": "cohort",
                "primary_sha256": "primary",
                "environment_sha256": "environment",
            }
            context_path, target_path = kit / "context.json", root / "target-plan.json"
            context_path.write_text(json.dumps(context))
            target_path.write_text(json.dumps(target))
            ledger.update(
                schema="ev-current-whole-unit-remaining-ledger-v1",
                pins=[
                    {"path": str(path), "sha256": digest(path)}
                    for path in (context_path, target_path)
                ],
            )
            ledger_path = root / "ledger.json"
            ledger_path.write_text(json.dumps(ledger))
            checksum = digest(ledger_path)
            before = ledger_path.read_bytes()
            paths = [root / "reserved1.json", root / "reserved2.json"]
            for index, path in enumerate(paths):
                path.write_text(
                    json.dumps(
                        {
                            **self.reserve(args, index, index + 1),
                            "remaining_ledger_sha256": checksum,
                        }
                    )
                )
            hashes = [digest(path) for path in paths]
            with (
                patch("tools.prepare_city_units.check_source_kit", return_value=sources),
                patch("tools.prepare_city_units.InputRun", return_value=data[7]),
            ):
                declaration = prepare(
                    ledger_path,
                    checksum,
                    root,
                    root,
                    root / "multi",
                    2,
                    reserved_path=paths,
                    reserved_sha256=hashes,
                )
                scalar = prepare(
                    ledger_path,
                    checksum,
                    root,
                    root,
                    root / "single",
                    1,
                    reserved_path=paths[0],
                    reserved_sha256=hashes[0],
                )
            self.assertEqual(
                json.loads((root / "multi/reference.json").read_text())["source_epochs"], 10
            )
            self.assertEqual(declaration["chosen_units"], [u["unit"] for u in units[2:]])
            self.assertEqual(declaration["reserved_prefix_sha256s"], hashes)
            self.assertIsNone(declaration["reserved_prefix_sha256"])
            self.assertEqual(scalar["chosen_units"], [units[1]["unit"]])
            self.assertEqual(scalar["reserved_prefix_sha256"], hashes[0])
            self.assertEqual(scalar["reserved_prefix_sha256s"], hashes[:1])
            self.assertEqual(ledger_path.read_bytes(), before)

    def test_cli_preserves_order_of_repeated_reservation_pairs(self) -> None:
        argv = [
            "prepare",
            "--ledger",
            "ledger",
            "--ledger-sha256",
            "pin",
            "--city-kit",
            "kit",
            "--inputs-root",
            "inputs",
            "--output",
            "out",
            "--whole-unit-count",
            "2",
            "--reserved-prefix",
            "first",
            "--reserved-prefix-sha256",
            "hash1",
            "--reserved-prefix",
            "second",
            "--reserved-prefix-sha256",
            "hash2",
        ]
        with (
            patch("sys.argv", argv),
            patch("builtins.print"),
            patch("tools.prepare_city_units.prepare", return_value={"chosen_units": []}) as mocked,
        ):
            main()
        self.assertEqual(mocked.call_args.kwargs["reserved_path"], [Path("first"), Path("second")])
        self.assertEqual(mocked.call_args.kwargs["reserved_sha256"], ["hash1", "hash2"])


if __name__ == "__main__":
    unittest.main()
