"""Exact missing-artifact Development replay; original settings, no new selection."""

import argparse
import contextlib
import copy
import json
import shutil
import time
from pathlib import Path

import torch

from ev_models.checkpoint import digest, write_json
from ev_models.run import environment
from ev_runner.replay import Replay
from ev_runner.run import execute, runtime_code
from tools.charged_development_cohort import CITIES
from tools.comparison_matrix import CachedInputs
from tools.durable_run_backup import RunBackup, require_drive_mount
from tools.verify_comparison import InputSnapshots, verify_run
from tools.verify_latest_states import verify_state


def replay_namespace(plan: dict) -> tuple[str, str]:
    """Keep legacy primary recovery separate from explicitly declared city migration."""
    if plan.get("schema") == "exact-missing-development-recovery-v1":
        return "urbanev", "SZH"
    namespace = plan.get("namespace")
    if (
        plan.get("schema") != "exact-city-development-migration-v1"
        or not isinstance(namespace, list)
        or len(namespace) != 2
        or namespace[0] != "charged"
        or namespace[1] not in CITIES
    ):
        raise ValueError("Identified primary recovery or separate CHARGED migration required")
    return tuple(namespace)


def planned_rows(plan_path: Path, expected_sha: str, family: str) -> tuple[dict, dict, list]:
    """Authenticate exact original population and the physical-absence partition."""
    if digest(plan_path) != expected_sha:
        raise ValueError("Changed recovery plan")
    plan = json.loads(plan_path.read_text())
    namespace = replay_namespace(plan)
    city_migration = namespace[0] == "charged"
    if family not in ("proxy", "matched") or (city_migration and family != "matched"):
        raise ValueError("Unsupported Development execution family")
    scope = plan["families"][family]
    path = plan_path.parent / scope["original_matrix"]
    if (
        Path(scope["original_matrix"]).name != scope["original_matrix"]
        or digest(path) != scope["original_matrix_sha256"]
    ):
        raise ValueError("Changed or unsafe original matrix")
    original = json.loads(path.read_text())
    ids = [r["run_id"] for r in original["runs"]]
    kept, replay = scope["preserved_ids"], scope["replay_ids"]
    if (
        original["status"]
        != ("predeclared_development_reference" if city_migration else "technical_success")
        or (city_migration and original.get("namespace") != list(namespace))
        or len(ids) != len(set(ids))
        or len(ids) != scope["original_total"]
        or len(kept) != len(set(kept))
        or len(replay) != len(set(replay))
        or set(kept) & set(replay)
        or set(kept) | set(replay) != set(ids)
        or replay != [name for name in ids if name not in set(kept)]
    ):
        raise ValueError("Missing, extra, overlapping, duplicate or reordered recovery cells")
    if set(plan["sources"]) != {"42", "43", "44"}:
        raise ValueError("All three original Source seeds are required")
    for seed, value in plan["sources"].items():
        source = Path(value["path"])
        if (
            source.is_absolute()
            or ".." in source.parts
            or digest(plan_path.parent / source) != value["sha256"]
        ):
            raise ValueError("Changed or unsafe Source checkpoint")
        if original["sources"][seed]["sha256"] != value["sha256"]:
            raise ValueError("Source differs from original study")
    rows = [r for r in original["runs"] if r["run_id"] in set(replay)]
    if city_migration:
        declaration_path = plan_path.parent / "whole-unit.json"
        if digest(declaration_path) != plan["whole_unit_sha256"]:
            raise ValueError("Changed complete-unit city declaration")
        declaration = json.loads(declaration_path.read_text())
        units, variants = declaration["chosen_units"], declaration["required_variants"]
        if (
            not 1 <= len(units) <= 4
            or len({tuple(u) for u in units}) != len(units)
            or len(variants) != 14
            or len(set(variants)) != 14
            or rows != declaration["rows"]
            or len(rows) != 14 * len(units)
            or kept
            or declaration["producer_context_sha256"] != plan["producer_context_sha256"]
        ):
            raise ValueError("Complete predeclared city units required")
        for index, unit in enumerate(units):
            group = rows[index * 14 : (index + 1) * 14]
            if {r["comparison_variant"] for r in group} != set(variants) or any(
                [
                    r["binding"]["input"]["dataset_id"],
                    r["binding"]["input"]["city_id"],
                    r["binding"]["input"]["history_days"],
                    r["binding"]["input"]["entity_id"],
                    r["binding"]["config"]["initial_training"]["seed"],
                ]
                != unit
                for r in group
            ):
                raise ValueError("Missing, mixed or duplicate city methods")
    for row in rows:
        binding, config = row["binding"]["input"], row["binding"]["config"]
        if (
            Path(row["run_id"]).name != row["run_id"]
            or row["run_id"] in (".", "..")
            or (binding["dataset_id"], binding["city_id"], binding["stage"])
            != (*namespace, "target")
            or binding["history_days"] not in (7, 14, 28)
            or config["replay_days"] != 90
            or config["initial_training"]["seed"] not in (42, 43, 44)
            or binding.get("source_checkpoint_sha256")
            != plan["sources"][str(config["initial_training"]["seed"])]["sha256"]
            or row["code"]["dirty"]
            or row["code"]["files"] != original["code"]["files"]
        ):
            raise ValueError("Original Development binding/config/code population changed")
    return plan, original, rows


def recovery_context(
    plan: dict, original: dict, rows: list, runtime: dict, source_report: dict
) -> dict:
    """Bind a missing-only replay to the original scope and current execution environment."""
    first = source_report
    training = dict(first["training_config"])
    training.pop("seed")
    return {
        "schema": "ev-primary-missing-backup-v1",
        "namespace": list(replay_namespace(plan)),
        "seeds": [42, 43, 44],
        "source_epochs": training["epochs"],
        "source_training": training,
        "source_population_sha256": first["source_population_sha256"],
        "source_manifest_sha256": first["input_binding"]["input_manifest_sha256"],
        "core_files": original["code"]["files"],
        "environment": runtime,
        "original_sources": {k: v["sha256"] for k, v in plan["sources"].items()},
        "expected_runs": {
            r["run_id"]: {
                "config": r["binding"]["config"],
                "entity_id": r["binding"]["input"]["entity_id"],
                "history_days": r["binding"]["input"]["history_days"],
                "input_manifest_sha256": r["binding"]["input"]["input_manifest_sha256"],
                "comparison_variant": r.get("comparison_variant"),
            }
            for r in rows
        },
    }


def stage_original_sources(
    source_root: Path, study: Path, original: dict, backup: RunBackup
) -> None:
    """Copy original selected bytes/logs; explicitly label new recovery descriptors."""
    for seed in (42, 43, 44):
        entry = copy.deepcopy(original["sources"][str(seed)])
        name = f"source-seed{seed}"
        folder = study / name
        folder.mkdir()
        checkpoint = folder / f"epoch-{backup.context['source_epochs']}.pt"
        for relative in (
            Path(name) / checkpoint.name,
            Path(name) / (checkpoint.name + ".sha256"),
            Path(name) / "run.json",
            Path(name + ".log"),
        ):
            shutil.copyfile(source_root / relative, study / relative)
        entry.update(
            seed=seed,
            run=json.loads((folder / "run.json").read_text()),
            path=str(checkpoint),
            recovery_descriptor="New outer descriptor; original weights/report/log unchanged",
        )
        write_json(study / (name + "-complete.json"), entry)
        backup.source(entry)


def restored_prefix(rows: list, restored: list) -> set[str]:
    """Only a contiguous original missing-cell prefix may be skipped on resume."""
    ids = {r["run_id"] for r in restored}
    if len(ids) != len(restored) or ids != {r["run_id"] for r in rows[: len(restored)]}:
        raise ValueError("Recovered targets are not the declared missing-cell prefix")
    return ids


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "inputs-root", "output", "source-root", "backup-root", "drive-mount"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--family", choices=("proxy", "matched"), required=True)
    parser.add_argument("--resume-backup", action="store_true")
    args = parser.parse_args()
    plan, original, rows = planned_rows(args.plan, args.plan_sha256, args.family)
    namespace = replay_namespace(plan)
    code = runtime_code()
    if code["dirty"] or code["files"] != original["code"]["files"]:
        raise ValueError("Recovery requires clean byte-identical core algorithms")
    if not torch.cuda.is_available():
        raise ValueError("Real recovery requires cloud CUDA; no local training")
    if args.output.resolve().is_relative_to(args.inputs_root.resolve()):
        raise ValueError("Keep recovery outputs outside immutable inputs")
    inputs = {}
    for budget in sorted({r["binding"]["input"]["history_days"] for r in rows}):
        checksums = {
            r["binding"]["input"]["input_manifest_sha256"]
            for r in rows
            if r["binding"]["input"]["history_days"] == budget
        }
        if len(checksums) != 1:
            raise ValueError("Exactly one original input identity per budget required")
        inputs[budget] = CachedInputs(
            args.inputs_root / f"{'-'.join(namespace)}-{budget}d", checksums.pop()
        )
    sources = {
        int(k): (args.plan.parent / v["path"], v["sha256"]) for k, v in plan["sources"].items()
    }
    # Validate all Development roles/scalers before creating any output or running a model.
    for row in rows:
        binding = row["binding"]["input"]
        data = inputs[binding["history_days"]]
        if (
            data.entities.get((*data.namespace, binding["entity_id"]), {}).get("role")
            != "development"
            or data.binding("target", binding["entity_id"], binding["source_checkpoint_sha256"])
            != binding
        ):
            raise ValueError("Recovery input role/scaler differs from original")
    require_drive_mount(args.backup_root, args.drive_mount)
    args.output.mkdir(parents=True, exist_ok=False)
    context = recovery_context(
        plan,
        original,
        rows,
        {**environment("cuda"), "deterministic_algorithms": True},
        json.loads((args.source_root / "source-seed42" / "run.json").read_text()),
    )
    context.update(recovery_plan_sha256=args.plan_sha256, recovery_family=args.family)
    backup = RunBackup(args.output, args.backup_root, context, inputs, resume=args.resume_backup)
    if args.resume_backup:
        recovered_sources, recovered_rows = backup.restore()
        if len(recovered_sources) != 3:
            raise ValueError("Completed Source publication required before automatic resume")
    else:
        stage_original_sources(args.source_root, args.output, original, backup)
        recovered_rows = []
    completed = restored_prefix(rows, recovered_rows)
    sources = {
        seed: (Path(entry["path"]), entry["sha256"]) for seed, entry in backup.sources.items()
    }
    output = {
        k: copy.deepcopy(v)
        for k, v in original.items()
        if k not in ("runs", "status", "wall_seconds")
    }
    output.update(
        scope=(
            "Predeclared separate-city Development migration; not original-byte recovery or Final"
            if namespace[0] == "charged"
            else "Exact missing-artifact subset recovery; not complete original matrix acceptance or recalibration"
        ),
        recovery_plan_sha256=args.plan_sha256,
        recovery_family=args.family,
        original_matrix_sha256=plan["families"][args.family]["original_matrix_sha256"],
        code=code,
        runs=recovered_rows,
        status="running",
        differences=[],
        daily_proofs=[],
        latest_states=[],
        restored_prefix_count=len(recovered_rows),
        proof_scope="Newly executed rows only; restored rows independently reverified by RunBackup",
    )
    write_json(args.output / "recovery-plan.json", plan)
    write_json(args.output / "original-matrix.json", original)
    snapshots = InputSnapshots()
    started, last_key, replay = time.perf_counter(), None, None
    try:
        for reference in rows:
            if reference["run_id"] in completed:
                continue
            binding, config = reference["binding"]["input"], reference["binding"]["config"]
            budget, entity, seed = (
                binding["history_days"],
                binding["entity_id"],
                config["initial_training"]["seed"],
            )
            key = budget, entity
            if key != last_key:
                replay = Replay(inputs[budget], entity, config["replay_days"])
                replay.prepare_label_index()
                last_key = key
            destination = args.output / reference["run_id"]
            torch.cuda.reset_peak_memory_stats()
            with (
                (args.output / (reference["run_id"] + ".log")).open("x") as log,
                contextlib.redirect_stdout(log),
            ):
                row = execute(
                    inputs[budget],
                    entity,
                    *sources[seed],
                    config,
                    destination,
                    device="cuda",
                    prepared_replay=replay,
                    ensemble_sources=tuple(sources[s] for s in (42, 43, 44))
                    if config["method"]["name"] == "uncertainty"
                    else (),
                )
            for field in ("recipe", "comparison_variant"):
                if field in reference:
                    row[field] = reference[field]
            if row["binding"]["input"] != binding or row["binding"]["config"] != config:
                raise ValueError("Executed configuration differs from original")
            daily = verify_run(destination, inputs[budget].root, input_snapshots=snapshots)
            state = verify_state(destination, json.loads((destination / "run.json").read_text()))
            fields = (
                "active_mae_kwh",
                "active_rmse_kwh",
                "scheduled_days",
                "issued_days",
                "scored_days",
                "prediction_identity_sha256",
                "candidate_steps",
                "audit_steps",
            )
            output["differences"].append(
                {
                    "run_id": row["run_id"],
                    "comparison_scope": (
                        "No historical outcomes in predeclared city reference"
                        if namespace[0] == "charged"
                        else "Original recorded outcomes versus new recovery"
                    ),
                    "fields": {
                        f: {"original": reference[f], "recovery": row[f]}
                        for f in fields
                        if namespace[0] != "charged" and reference[f] != row[f]
                    },
                }
            )
            backup_started = time.perf_counter()
            backup.target(row)
            output["backup_seconds_this_invocation"] = (
                output.get("backup_seconds_this_invocation", 0)
                + time.perf_counter()
                - backup_started
            )
            output["runs"].append(row)
            output["daily_proofs"].append(daily)
            output["latest_states"].append(state)
            temporary = args.output / "progress.next.json"
            write_json(temporary, output)
            temporary.replace(args.output / "progress.json")
            print(
                json.dumps(
                    {
                        "family": args.family,
                        "verified_completed": len(output["runs"]),
                        "required": len(rows),
                        "run_id": row["run_id"],
                    }
                ),
                flush=True,
            )
        output["status"] = "technical_success"
    except Exception as error:
        output.update(status="failed", error=repr(error))
        raise
    finally:
        output["wall_seconds_this_invocation"] = time.perf_counter() - started
        write_json(args.output / "matrix.json", output)


if __name__ == "__main__":
    main()
