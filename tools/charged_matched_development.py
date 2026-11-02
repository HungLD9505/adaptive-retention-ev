"""Separate-city CHARGED Development replication of the primary-selected recipe."""

import argparse
import contextlib
import copy
import json
import time
from pathlib import Path

import torch

from ev_models.checkpoint import digest, write_json
from ev_models.run import environment
from ev_models.run import execute as train_source
from ev_runner.replay import Replay
from ev_runner.run import execute, runtime_code
from tools.charged_development_cohort import CITIES, RULE, choose_entities
from tools.comparison_matrix import CachedInputs
from tools.controller_calibration import recipe_config as adaptive_config
from tools.durable_run_backup import RunBackup, require_drive_mount
from tools.matched_development import comparison_config, variants
from tools.proxy_calibration import METHODS as PROXY_METHODS
from tools.proxy_calibration import recipe_config as proxy_config


def primary_recipe(summary: dict, seed: int, entity: str) -> tuple[int, dict, dict]:
    """Use the authenticated primary recipe, never primary model weights or labels."""
    choice = summary["choices"]
    if type(choice["source_epochs"]) is not int or choice["source_epochs"] not in (1, 3, 10):
        raise ValueError("Unexpected primary Source duration")
    if type(choice["controller_recipe"]) is not int or choice["controller_recipe"] not in range(4):
        raise ValueError("Unexpected primary controller recipe")
    if type(choice["fixed_lambda"]) not in (float, int) or choice["fixed_lambda"] not in (
        0.001,
        0.01,
        0.1,
        1.0,
    ):
        raise ValueError("Unexpected primary fixed lambda")
    if set(choice["proxy_recipes"]) != set(PROXY_METHODS) or any(
        type(v) is not int or v not in range(4) for v in choice["proxy_recipes"].values()
    ):
        raise ValueError("Complete finite primary proxy/parameter choices required")
    profile = json.loads(Path("configs/issue23/source-epoch-study.json").read_text())
    base = copy.deepcopy(profile["runner_config"])
    base["development_entities"] = [entity]
    for key in ("initial_training", "online_training", "controller"):
        base[key]["seed"] = seed
    config = adaptive_config(base, choice["controller_recipe"], seed)
    expected = {"adaptive", "full_finetuning", "fixed_retention", *PROXY_METHODS, *variants(config)}
    if set(choice["unique_method_names"]) != expected:
        raise ValueError("Primary collection is missing required method/ablation names")
    return choice["source_epochs"], config, profile["source_training"]


def method_configs(summary: dict, seed: int, entity: str) -> dict:
    """Create all unique matched methods without silently dropping an ablation."""
    _, base, _ = primary_recipe(summary, seed, entity)
    output = {"adaptive": base}
    for name in ("full_finetuning", "fixed_retention"):
        config = copy.deepcopy(base)
        config["method"] = {"name": name}
        if name == "fixed_retention":
            config["method"]["fixed_lambda"] = summary["choices"]["fixed_lambda"]
        output[name] = config
    for name in PROXY_METHODS:
        output[name] = proxy_config(base, name, summary["choices"]["proxy_recipes"][name])
    output.update({name: comparison_config(base, name) for name in variants(base)})
    return output


def validate_cohort(data: dict, cohort: dict) -> None:
    """Recompute outcome-blind cohort identities and preserve the publisher clock."""
    if (
        cohort["namespace"] not in {f"charged-{c}" for c in CITIES}
        or cohort["selection_rule"] != RULE
        or cohort["seeds"] != [42, 43, 44]
        or cohort["days"] != 90
        or cohort["state_retention"] != "latest"
        or set(cohort["budgets"]) != {"7", "14", "28"}
    ):
        raise ValueError("Expected complete declared CHARGED scope")
    for budget, inputs in data.items():
        if (
            inputs.namespace != ("charged", cohort["namespace"].removeprefix("charged-"))
            or inputs.config["history_days"] != budget
            or inputs.clock != "publisher-local-naive"
            or inputs.source_hash != cohort["source_population_sha256"]
            or inputs.config["deployment"] != cohort["deployment"]
        ):
            raise ValueError("Changed city/clock/Source population/deployment")
        group = choose_entities(
            list(inputs.entities.values()), inputs.namespace, inputs.sha256, budget
        )
        if group != cohort["budgets"][str(budget)]:
            raise ValueError("Cohort selection changed from the predeclared rule")


def validate_matrix(rows: list[dict], cohort: dict, summary: dict) -> None:
    expected = {
        (int(b), item["entity_id"], seed, name)
        for b, group in cohort["budgets"].items()
        for item in group["entities"]
        for seed in cohort["seeds"]
        for name in method_configs(summary, seed, item["entity_id"])
    }
    seen, coverage, source_ids, bindings = set(), {}, {}, {}
    for row in rows:
        b, c = row["binding"]["input"], row["binding"]["config"]
        seed = c["initial_training"]["seed"]
        key = b["history_days"], b["entity_id"], seed, row["comparison_variant"]
        if (
            key not in expected
            or key in seen
            or c != method_configs(summary, seed, b["entity_id"])[key[-1]]
        ):
            raise ValueError("Missing/extra/duplicate or mislabeled CHARGED cell")
        if (b["dataset_id"], b["city_id"]) != (
            "charged",
            cohort["namespace"].removeprefix("charged-"),
        ) or b["input_manifest_sha256"] != cohort["budgets"][str(key[0])]["manifest_sha256"]:
            raise ValueError("Cross-city/dataset/input contamination")
        if row["method"]["name"] != c["method"]["name"]:
            raise ValueError("Executed CHARGED method contradicts recipe")
        checksum = row["source_checkpoint_sha256"]
        if (
            checksum != b["source_checkpoint_sha256"]
            or seed in source_ids
            and source_ids[seed] != checksum
        ):
            raise ValueError("Source weights differ across matched city methods/budgets")
        source_ids[seed] = checksum
        if key[:3] in bindings and bindings[key[:3]] != b:
            raise ValueError("Matched target input/normalization bindings differ")
        bindings[key[:3]] = b
        seen.add(key)
        signature = row["issued_days"], row["scored_days"]
        if key[:3] in coverage and coverage[key[:3]] != signature:
            raise ValueError("Matched CHARGED coverage differs")
        coverage[key[:3]] = signature
        if (row["active_mae_kwh"] is None) != (row["scored_days"] == 0):
            raise ValueError("Null score/count contradiction")
    if seen != expected:
        raise ValueError("All declared CHARGED method/seed/entity/budget cells required")


def backup_context(
    cohort: dict,
    summary: dict,
    data: dict,
    code: dict,
    runtime: dict,
    *,
    cohort_sha256: str,
    primary_sha256: str,
) -> dict:
    """Bind recovery to the original complete execution, never observed results."""
    epoch, _, training = primary_recipe(summary, 42, "not-used-by-source")
    return {
        "schema": "ev-mounted-drive-execution-v1",
        "namespace": list(data[7].namespace),
        "cohort_sha256": cohort_sha256,
        "primary_sha256": primary_sha256,
        "source_population_sha256": data[7].source_hash,
        "source_manifest_sha256": data[7].sha256,
        "source_epochs": epoch,
        "source_training": {**training, "epochs": epoch},
        "seeds": cohort["seeds"],
        "core_files": code["files"],
        "environment": runtime,
        "expected_runs": {
            f"{cohort['namespace']}-{item['entity_id']}-{budget}d-{name}-seed{seed}": {
                "config": config,
                "entity_id": item["entity_id"],
                "history_days": budget,
                "input_manifest_sha256": data[budget].sha256,
                "comparison_variant": name,
            }
            for budget in (7, 14, 28)
            for item in cohort["budgets"][str(budget)]["entities"]
            for seed in cohort["seeds"]
            for name, config in method_configs(summary, seed, item["entity_id"]).items()
        },
    }


def run(args: argparse.Namespace) -> None:
    if not torch.cuda.is_available():
        raise ValueError("Real CHARGED Source/target training requires CUDA")
    if (
        digest(args.cohort) != args.cohort_sha256
        or digest(args.primary_analysis) != args.primary_sha256
    ):
        raise ValueError("Changed identified primary recipe/cohort")
    cohort = json.loads(args.cohort.read_text())
    summary = json.loads(args.primary_analysis.read_text())
    if not summary.get("collection_lineage") or not summary.get("matrix_identities"):
        raise ValueError("Authenticated full primary collection lineage required")
    epoch, _, source_config = primary_recipe(summary, 42, "not-used-by-source")
    namespace = cohort["namespace"]
    data = {
        budget: CachedInputs(
            args.inputs_root / f"{namespace}-{budget}d",
            cohort["budgets"][str(budget)]["manifest_sha256"],
        )
        for budget in (7, 14, 28)
    }
    validate_cohort(data, cohort)
    code = runtime_code()
    if code["dirty"]:
        raise ValueError("Clean identified code required")
    backup_root, mount = getattr(args, "backup_root", None), getattr(args, "drive_mount", None)
    resume = getattr(args, "resume_backup", False)
    if bool(backup_root) != bool(mount) or resume and not backup_root:
        raise ValueError(
            "Backup requires both --backup-root and --drive-mount; resume needs backup"
        )
    if backup_root:
        require_drive_mount(backup_root, mount)
    args.output.mkdir(parents=True, exist_ok=False)
    matrix = {
        "scope": "Separate-city supplementary Development configuration replication; no Final or strict-online effectiveness claim",
        "namespace": namespace,
        "cohort_sha256": args.cohort_sha256,
        "primary_analysis_sha256": args.primary_sha256,
        "source_epochs": epoch,
        "code": code,
        "sources": [],
        "runs": [],
        "status": "running",
        "limits": "Primary hyperparameters transferred, never UrbanEV weights. No city-specific tuning; small prefix-selected cohort; publisher preprocessing/clock limitations; SZH separate overlap analysis.",
    }
    backup = None
    if backup_root:
        context = backup_context(
            cohort,
            summary,
            data,
            code,
            {**environment("cuda"), "deterministic_algorithms": True},
            cohort_sha256=args.cohort_sha256,
            primary_sha256=args.primary_sha256,
        )
        expected = context["expected_runs"]
        backup = RunBackup(args.output, backup_root, context, data, resume=resume)
        if resume:
            restore_started = time.perf_counter()
            sources, rows = backup.restore()
            matrix["restore_verification_seconds"] = time.perf_counter() - restore_started
            source_order = [s for s in cohort["seeds"] if s in backup.sources]
            if source_order != cohort["seeds"][: len(sources)] or set(backup.runs) != set(
                list(expected)[: len(rows)]
            ):
                raise ValueError(
                    "Completed backups must be an execution prefix, never outcome-selected"
                )
            matrix["sources"] = [backup.sources[s] for s in source_order]
            matrix["runs"] = [backup.runs[name] for name in expected if name in backup.runs]
            matrix["resume_backup"] = str(backup_root)
        matrix["backup"] = {
            "root": str(backup_root),
            "context_sha256": backup.context_sha,
            "acceptance": "Mounted-filesystem readback; independent remote acceptance pending",
        }
    write_json(args.output / "cohort.json", cohort)
    backup_seconds = 0.0
    started = time.perf_counter()
    try:
        for seed in cohort["seeds"]:
            if backup and seed in backup.sources:
                continue
            training = {**source_config, "seed": seed, "epochs": epoch}
            config = {
                "training": training,
                "lambda": 0,
                "development_entities": ["not-used-by-source"],
                "evaluation_origins": 90,
            }
            out = args.output / f"source-seed{seed}"
            torch.cuda.reset_peak_memory_stats()
            with (
                (args.output / f"source-seed{seed}.log").open("x") as log,
                contextlib.redirect_stdout(log),
            ):
                source_report = train_source("source", data[7], config, out, device="cuda")
            path = out / f"epoch-{epoch}.pt"
            matrix["sources"].append(
                {"seed": seed, "run": source_report, "path": str(path), "sha256": digest(path)}
            )
            write_json(args.output / f"source-seed{seed}-complete.json", matrix["sources"][-1])
            if backup:
                before_backup = time.perf_counter()
                backup.source(matrix["sources"][-1])
                backup_seconds += time.perf_counter() - before_backup
            print(
                json.dumps(
                    {"city": namespace, "source_seed": seed, "epochs": epoch, "status": "complete"}
                ),
                flush=True,
            )
        sources = {item["seed"]: (Path(item["path"]), item["sha256"]) for item in matrix["sources"]}
        for budget in (7, 14, 28):
            for item in cohort["budgets"][str(budget)]["entities"]:
                entity = item["entity_id"]
                replay = Replay(data[budget], entity, 90)
                replay.prepare_label_index()
                data[budget].training("development", entity)
                for seed in cohort["seeds"]:
                    for name, config in method_configs(summary, seed, entity).items():
                        run_id = f"{namespace}-{entity}-{budget}d-{name}-seed{seed}"
                        if backup and run_id in backup.runs:
                            continue
                        torch.cuda.reset_peak_memory_stats()
                        with (
                            (args.output / f"{run_id}.log").open("x") as log,
                            contextlib.redirect_stdout(log),
                        ):
                            row = execute(
                                data[budget],
                                entity,
                                *sources[seed],
                                config,
                                args.output / run_id,
                                device="cuda",
                                prepared_replay=replay,
                                ensemble_sources=tuple(sources[s] for s in cohort["seeds"])
                                if name == "uncertainty"
                                else (),
                            )
                        row["comparison_variant"] = name
                        matrix["runs"].append(row)
                        if backup:
                            before_backup = time.perf_counter()
                            backup.target(row)
                            backup_seconds += time.perf_counter() - before_backup
                        progress = args.output / "progress.next.json"
                        progress.write_text(json.dumps(matrix, indent=2, allow_nan=False))
                        progress.replace(args.output / "progress.json")
                        print(
                            json.dumps(
                                {k: row[k] for k in ("run_id", "scored_days", "active_mae_kwh")}
                            ),
                            flush=True,
                        )
        validate_matrix(matrix["runs"], cohort, summary)
        matrix["status"] = "technical_success"
    except Exception as error:
        matrix.update(status="failed", error=repr(error))
        raise
    finally:
        matrix["wall_seconds"] = time.perf_counter() - started
        if resume:
            matrix["wall_seconds_scope"] = (
                "Current invocation only; original pre-interruption wall/backup overhead is not reconstructed. "
                "Source/run component timers remain in their original records."
            )
        if backup:
            matrix["backup_io_verification_seconds"] = backup_seconds
        write_json(args.output / "matrix.json", matrix)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs-root", "cohort", "primary-analysis", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("cohort-sha256", "primary-sha256"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--backup-root", type=Path, help="Unique directory below mounted Drive")
    parser.add_argument(
        "--drive-mount", type=Path, help="Existing DriveFS mount, e.g. /content/drive"
    )
    parser.add_argument(
        "--resume-backup",
        action="store_true",
        help="Restore verified completed prefix into NEW --output",
    )
    run(parser.parse_args())


if __name__ == "__main__":
    main()
