"""Prepare a strict whole-unit CHARGED Development prefix with original city Sources."""

import argparse
import copy
import json
import zipfile
from pathlib import Path

from ev_models.checkpoint import digest, write_json
from ev_models.data import InputRun
from tools.charged_development_cohort import CITIES
from tools.city_target_outbox import check_source_kit
from tools.export_development import safe_name


def pending_prefix(
    ledger: dict, count: int, reserved: dict | list[dict] | None = None
) -> list[dict]:
    """Skip contiguous reserved whole-unit declarations in their declared order."""
    if type(count) is not int or not 1 <= count <= 4:
        raise ValueError("One to four pending whole units required")
    offset = 0
    reservations = [reserved] if isinstance(reserved, dict) else reserved or []
    for reservation in reservations:
        chosen = reservation["chosen_units"]
        size = len(chosen)
        prefix = ledger["remaining_units"][offset : offset + size]
        if (
            not 1 <= size <= 4
            or [u["unit"] for u in prefix] != chosen
            or len(reservation["rows"]) != size * 14
            or len({r["run_id"] for r in reservation["rows"]}) != size * 14
        ):
            raise ValueError("Reserved publication must be the exact pending whole-unit prefix")
        expected = {
            entry["run_id"]: entry["config"]
            for unit in prefix
            for entry in unit["methods"].values()
        }
        if {r["run_id"]: r["binding"]["config"] for r in reservation["rows"]} != expected:
            raise ValueError("Reserved methods/configs differ from the pending ledger")
        offset += size
    units = ledger["remaining_units"][offset : offset + count]
    if len(units) != count:
        raise ValueError("Requested disjoint pending prefix unavailable")
    return units


def city_rows(units: list[dict], ledger: dict, context: dict, data: dict, sources: dict) -> list:
    """Bind every method to the pinned producer recipe and ready Development metadata."""
    namespace = context["namespace"]
    required = set(ledger["required_variants"])
    if (
        namespace[0] != "charged"
        or namespace[1] not in CITIES
        or context["seeds"] != [42, 43, 44]
        or type(context.get("source_epochs")) is not int
        or context["source_epochs"] != 10
        or len(required) != 14
        or len(ledger["required_variants"]) != 14
        or not 1 <= len(units) <= 4
        or len({tuple(u["unit"]) for u in units}) != len(units)
    ):
        raise ValueError("One to four complete units in one CHARGED namespace required")
    rows = []
    complete = [u["unit"] for u in ledger["retained_complete_units_excluding_JHB"]]
    for unit in units:
        dataset, city, budget, entity, seed = unit["unit"]
        repeats = unit["old_accepted_cells_to_repeat_if_migrating"]
        if (
            [dataset, city] != namespace
            or budget not in (7, 14, 28)
            or seed not in (42, 43, 44)
            or unit["unit"] in complete
            or type(repeats) is not int
            or not 0 <= repeats < 14
            or set(unit["methods"]) != required
        ):
            raise ValueError("Changed, complete, duplicate or cross-city pending unit")
        inputs = data[budget]
        summary = inputs.entities.get((dataset, city, entity), {})
        if (
            inputs.namespace != tuple(namespace)
            or inputs.source_hash != context["source_population_sha256"]
            or inputs.config["history_days"] != budget
            or summary.get("role") != "development"
            or summary.get("status") != "ready"
        ):
            raise ValueError("Only ready Development targets may be prepared")
        for variant in sorted(required):
            expected = unit["methods"][variant]
            name = safe_name(expected["run_id"])
            recipe = context["expected_runs"].get(name)
            config = expected["config"]
            binding = inputs.binding("target", entity, sources[seed])
            if (
                recipe is None
                or recipe["config"] != config
                or recipe["comparison_variant"] != variant
                or (recipe["history_days"], recipe["entity_id"]) != (budget, entity)
                or recipe["input_manifest_sha256"] != inputs.sha256
                or expected["input_manifest_sha256"] != inputs.sha256
                or expected["source_checkpoint_sha256"] != sources[seed]
                or config["initial_training"]["seed"] != seed
                or config["replay_days"] != 90
                or config["development_entities"] != [entity]
            ):
                raise ValueError("Changed original city recipe/input/Source binding")
            rows.append(
                {
                    "run_id": name,
                    "comparison_variant": variant,
                    "binding": {"input": binding, "config": copy.deepcopy(config)},
                    "code": {"dirty": False, "files": context["core_files"]},
                    "reference_kind": "Predeclared configuration, not an executed historical result",
                }
            )
    if len({r["run_id"] for r in rows}) != 14 * len(units):
        raise ValueError("Duplicate or missing target method identities")
    return rows


def prepare(
    ledger_path: Path,
    ledger_sha256: str,
    city_kit: Path,
    inputs_root: Path,
    output: Path,
    count: int,
    *,
    reserved_path: Path | list[Path] | None = None,
    reserved_sha256: str | list[str] | None = None,
) -> dict:
    """Authenticate original producer evidence without relabeling its environment."""
    if type(count) is not int or not 1 <= count <= 4 or digest(ledger_path) != ledger_sha256:
        raise ValueError("Pinned ledger and1..4 whole units required")
    ledger = json.loads(ledger_path.read_text())
    if ledger["schema"] != "ev-current-whole-unit-remaining-ledger-v1":
        raise ValueError("Current remaining ledger required")
    if (reserved_path is None) != (reserved_sha256 is None):
        raise ValueError("Both reserved declaration and its immutable hash required")
    paths = [reserved_path] if isinstance(reserved_path, Path) else reserved_path or []
    hashes = [reserved_sha256] if isinstance(reserved_sha256, str) else reserved_sha256 or []
    if len(paths) != len(hashes):
        raise ValueError("One immutable hash per reserved declaration required")
    if len(set(hashes)) != len(hashes) or len({p.resolve() for p in paths}) != len(paths):
        raise ValueError("Duplicate reserved declarations")
    reservations = []
    for path, checksum in zip(paths, hashes, strict=True):
        if digest(path) != checksum:
            raise ValueError("Changed reserved in-flight declaration")
        reserved = json.loads(path.read_text())
        if reserved["remaining_ledger_sha256"] != ledger_sha256:
            raise ValueError("Reservation belongs to another ledger state")
        reservations.append(reserved)
    units = pending_prefix(ledger, count, reservations)
    pins = {Path(p["path"]).resolve(): p["sha256"] for p in ledger["pins"]}
    context_path = city_kit / "source-kit/context.json"
    target_path = city_kit / "target-plan.json"
    for path in (context_path, target_path):
        if pins.get(path.resolve()) != digest(path):
            raise ValueError("City context/target plan differs from pinned ledger")
    context = json.loads(context_path.read_text())
    target = json.loads(target_path.read_text())
    sources_root = context_path.parent
    source_pins = check_source_kit(sources_root, target["source_kit_sha256"], context)
    if (
        context["namespace"] != units[0]["unit"][:2]
        or target["source_checkpoints"] != {str(k): v for k, v in source_pins.items()}
        or set(target["run_ids"]) != set(context["expected_runs"])
        or len(target["run_ids"]) != len(context["expected_runs"])
        or target["cohort_sha256"] != context["cohort_sha256"]
        or target["primary_sha256"] != context["primary_sha256"]
        or target["environment_sha256"] != context["environment_profile_sha256"]
    ):
        raise ValueError("Changed original city Source/cohort/recipe/producer identity")
    data = {}
    for unit in units:
        budget = unit["unit"][2]
        checksums = {v["input_manifest_sha256"] for v in unit["methods"].values()}
        if len(checksums) != 1:
            raise ValueError("One input identity per unit required")
        data[budget] = InputRun(
            inputs_root / f"{'-'.join(context['namespace'])}-{budget}d", checksums.pop()
        )
    rows = city_rows(units, ledger, context, data, source_pins)
    output.mkdir(parents=True, exist_ok=False)
    descriptors = {}
    for seed, checksum in source_pins.items():
        entry = json.loads((sources_root / f"source-seed{seed}.receipt.json").read_text())[
            "record"
        ]["entry"]
        # Copy exact known members only. Never unpack arbitrary provider paths.
        names = [
            f"source-seed{seed}/epoch-10.pt",
            f"source-seed{seed}/epoch-10.pt.sha256",
            f"source-seed{seed}/run.json",
            f"source-seed{seed}.log",
        ]
        with zipfile.ZipFile(sources_root / f"source-seed{seed}.zip") as archive:
            if archive.testzip() is not None:
                raise ValueError("Corrupt original Source archive")
            for name in names:
                path = output / name
                path.parent.mkdir(exist_ok=True)
                with path.open("xb") as stream:
                    stream.write(archive.read("study/" + name))
        if digest(output / names[0]) != checksum:
            raise ValueError("Original Source checkpoint changed")
        descriptors[str(seed)] = {**entry, "epochs": 10, "path": names[0]}
    declaration = {
        "schema": "ev-colab-whole-unit-migration-v1",
        "scope": "Predeclared CHARGED Development migration; no fits, outcomes or Final",
        "remaining_ledger_sha256": ledger_sha256,
        "producer_context_sha256": digest(context_path),
        "producer_environment": context["environment"],
        "source_kit_sha256": target["source_kit_sha256"],
        "chosen_units": [u["unit"] for u in units],
        "declared_repeat_cells": sum(u["old_accepted_cells_to_repeat_if_migrating"] for u in units),
        "required_variants": ledger["required_variants"],
        "rows": rows,
        "reserved_prefix_sha256": hashes[0] if len(hashes) == 1 else None,
        "reserved_prefix_sha256s": hashes,
        "coordination": (
            "Disjoint in-flight publication after reserved prefixes; one coordinator advances ledger"
            if reservations
            else "Strict pending prefix; one coordinator advances ledger"
        ),
    }
    write_json(output / "whole-unit.json", declaration)
    reference = {
        "status": "predeclared_development_reference",
        "namespace": context["namespace"],
        "source_epochs": context["source_epochs"],
        "scope": declaration["scope"],
        "code": {"dirty": False, "files": context["core_files"]},
        "sources": descriptors,
        "runs": rows,
    }
    write_json(output / "reference.json", reference)
    plan = {
        "schema": "exact-city-development-migration-v1",
        "namespace": context["namespace"],
        "whole_unit_sha256": digest(output / "whole-unit.json"),
        "producer_context_sha256": digest(context_path),
        "sources": {
            str(s): {"path": f"source-seed{s}/epoch-10.pt", "sha256": h}
            for s, h in source_pins.items()
        },
        "families": {
            "matched": {
                "original_matrix": "reference.json",
                "original_matrix_sha256": digest(output / "reference.json"),
                "original_total": len(rows),
                "preserved_ids": [],
                "replay_ids": [r["run_id"] for r in rows],
            }
        },
    }
    write_json(output / "plan.json", plan)
    return declaration


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("ledger", "city-kit", "inputs-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--ledger-sha256", required=True)
    parser.add_argument("--whole-unit-count", type=int, choices=range(1, 5), required=True)
    parser.add_argument("--reserved-prefix", type=Path, action="append")
    parser.add_argument("--reserved-prefix-sha256", action="append")
    args = parser.parse_args()
    value = prepare(
        args.ledger,
        args.ledger_sha256,
        args.city_kit,
        args.inputs_root,
        args.output,
        args.whole_unit_count,
        reserved_path=args.reserved_prefix,
        reserved_sha256=args.reserved_prefix_sha256,
    )
    print(json.dumps({"prepared_units": value["chosen_units"], "dispatch": False}))


if __name__ == "__main__":
    main()
