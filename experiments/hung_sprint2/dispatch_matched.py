"""Dispatch explicit, create-only matched Development jobs.

The plan chooses every cell, config, method, and dependency. This module makes
no model or lambda selection and never reads Final inputs. Dry-run is default.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import torch

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2.cli import _binding, _code_identity, _examples, _load_run
from experiments.hung_sprint2.run_development import verification_split_limit
from experiments.hung_sprint2.single_baseline_cli import _code_identity as _single_code_identity
from experiments.hung_sprint2.training import load_checkpoint

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT.parents[1] if ROOT.parent.name == ".cache" else ROOT
MIN_FREE_BYTES = 8 * 1024**3
CONTROLLER_METHODS = {
    "confidence",
    "online_best_lambda",
    "without_confidence",
    "fixed_retention",
    "full_finetuning",
    "source_error",
    "uncertainty",
    "drift",
}
SINGLE_METHODS = {"seasonal_naive", "target_only", "frozen_source"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def project_path(value: str | Path) -> Path:
    path = Path(value).resolve()
    require(path.is_relative_to(PROJECT.resolve()), f"Path outside project: {path}")
    return path


def read_json(path: Path) -> dict:
    require(path.is_file(), f"Missing required JSON: {path}")

    def unique_pairs(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            require(key not in result, f"Duplicate JSON key in {path}: {key}")
            result[key] = value
        return result

    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs)
    require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def verify_file(path: Path, digest: str) -> None:
    require(isinstance(digest, str) and len(digest) == 64, "Expected SHA-256")
    require(path.is_file() and sha256_file(path) == digest, f"File SHA-256 mismatch: {path}")


def free_space(path: Path) -> int:
    ancestor = path
    while not ancestor.exists():
        ancestor = ancestor.parent
    return shutil.disk_usage(ancestor).free


def require_capacity(root: Path) -> None:
    require(free_space(root) >= MIN_FREE_BYTES, "Less than 8 GiB free at output location")


def checked_checkpoint(path: Path, digest: str, binding: dict, code: dict) -> dict:
    verify_file(path, digest)
    record = read_json(path.parent / "run_manifest.json")
    require(record.get("status") == "completed", f"Incomplete checkpoint run: {path}")
    require(record.get("checkpoint_sha256") == digest, f"Checkpoint manifest mismatch: {path}")
    require(record.get("input_binding") == binding, f"Checkpoint input binding mismatch: {path}")
    require(
        record.get("code", {}).get("executed_sources") == code["executed_sources"],
        f"Checkpoint code differs: {path}",
    )
    _, _, _, metadata = load_checkpoint(path, expected_binding=binding)
    require(metadata["code_sha"] == record["code"]["commit"], "Checkpoint code metadata differs")
    return record


def verify_target_schedule(record: dict, settings: dict, initial_trainable: int) -> None:
    """Require the full predeclared adaptation prefix and config for reused targets."""
    requested = max(1, math.ceil(initial_trainable / settings["batch_size"]))
    require(
        record.get("target_examples_available") == initial_trainable
        and record.get("requested_steps") == requested
        and record.get("steps") == math.ceil(initial_trainable / settings["batch_size"])
        and record.get("batch_size") == settings["batch_size"]
        and record.get("learning_rate") == settings["learning_rate"]
        and record.get("epsilon") == settings["epsilon"],
        "Target adaptation schedule/config differs",
    )


def verify_source_schedule(record: dict, settings: dict, input_run: Path, manifest: dict) -> None:
    """Require complete one-pass Source adaptation under the declared config."""
    _, available = _examples(input_run, manifest, "source", limit=1)
    requested = math.ceil(available / settings["batch_size"])
    require(
        available >= 2
        and record.get("source_examples_available") == available
        and record.get("source_examples_used") == available
        and record.get("requested_steps") == requested
        and record.get("steps") == requested
        and record.get("batch_size") == settings["batch_size"]
        and record.get("learning_rate") == settings["learning_rate"]
        and record.get("calendar_hidden") == settings["calendar_hidden"],
        "Source adaptation schedule/config differs",
    )


def parse_plan(path: Path) -> tuple[dict, dict[str, dict], dict[str, dict], dict[str, dict]]:
    plan = read_json(path)
    require(
        plan.get("schema") == "hung-matched-development-dispatch-v1"
        and plan.get("scope") == "development_only",
        "Unexpected dispatcher plan",
    )
    require(
        set(plan)
        == {
            "schema",
            "scope",
            "code_commit",
            "selection",
            "input_base",
            "budgets",
            "seeds",
            "configs",
            "cells",
            "jobs",
            "output_root",
        },
        "Plan fields mismatch",
    )
    code = _code_identity()
    require(plan["code_commit"] == code["commit"], "Plan code commit differs")
    require(
        code["worktree_status"] == [],
        "Tracked worktree changes would change execution identity",
    )
    budgets, seeds = plan["budgets"], plan["seeds"]
    require(
        isinstance(budgets, list)
        and budgets
        and len(budgets) == len(set(budgets))
        and set(budgets) <= {7, 14, 28},
        "Invalid budget list",
    )
    require(
        isinstance(seeds, list)
        and seeds
        and len(seeds) == len(set(seeds))
        and all(type(x) is int and x >= 0 for x in seeds),
        "Invalid seed list",
    )
    selection_spec = plan["selection"]
    require(set(selection_spec) == {"path", "sha256"}, "Selection fields mismatch")
    selection_path = project_path(selection_spec["path"])
    verify_file(selection_path, selection_spec["sha256"])
    selection = read_json(selection_path)
    input_base = project_path(plan["input_base"])
    require(input_base.is_dir(), "Accepted input base missing")
    output_root = project_path(plan["output_root"])
    require(
        output_root.is_relative_to(ROOT.resolve()), "Output root must be inside current worktree"
    )
    require(not output_root.exists(), f"Create-only output root already exists: {output_root}")
    ignored = (
        subprocess.run(
            ["git", "check-ignore", "-q", "--no-index", str(output_root)], cwd=ROOT, check=False
        ).returncode
        == 0
    )
    require(ignored, "Output root must be Git-ignored")
    require_capacity(output_root)

    configs = {}
    for item in plan["configs"]:
        require(
            isinstance(item, dict) and set(item) == {"id", "path", "sha256"},
            "Config fields mismatch",
        )
        key = item["id"]
        require(
            isinstance(key, str) and key.isidentifier() and key not in configs,
            "Duplicate/invalid config id",
        )
        config_path = project_path(item["path"])
        require(config_path.is_relative_to(ROOT.resolve()), "Config must stay in worktree")
        verify_file(config_path, item["sha256"])
        config = read_json(config_path)
        require(
            config.get("schema") == "hung-sprint2-development-config-v1",
            "Unsupported config schema",
        )
        require(
            isinstance(config.get("seeds"), list) and set(seeds) <= set(config["seeds"]),
            "Config seed grid differs",
        )
        require(
            config["target"].get("retention_kind", "latent")
            == config["replay"].get("retention_kind", "latent"),
            "Target/replay retention kind differs",
        )
        require(
            config["target"].get("initialization_kind", "source")
            == config["replay"].get("initialization_kind", "source"),
            "Target/replay initialization differs",
        )
        if config["target"].get("retention_kind", "latent") == "parameter":
            require(
                config["target"]["retention_weight"] == config["replay"]["initial_level"],
                "Parameter initial lambda differs from target adaptation",
            )
        configs[key] = {"path": config_path, "sha256": item["sha256"], "value": config}

    cells = {}
    physical_cells = set()
    for item in plan["cells"]:
        require(
            isinstance(item, dict)
            and set(item) == {"id", "budget", "seed", "entity_id", "input_manifest_sha256"},
            "Cell fields mismatch",
        )
        key, budget, seed, entity = item["id"], item["budget"], item["seed"], item["entity_id"]
        require(
            isinstance(key, str) and key.isidentifier() and key not in cells,
            "Duplicate/invalid cell id",
        )
        require(
            budget in budgets and seed in seeds and isinstance(entity, str) and entity,
            "Cell outside declared grid",
        )
        physical = (budget, seed, entity)
        require(physical not in physical_cells, "Duplicate physical Development cell")
        physical_cells.add(physical)
        selected = selection["budgets"][str(budget)]
        matches = [row for row in selected["representative_entities"] if row["entity_id"] == entity]
        require(
            len(matches) == 1 and selected["manifest_sha256"] == item["input_manifest_sha256"],
            "Cell is not predeclared representative",
        )
        input_run = project_path(input_base / f"urbanev-SZH-{budget}d")
        manifest = _load_run(input_run, item["input_manifest_sha256"])
        require(
            manifest["config"]["dataset_id"] == "urbanev"
            and manifest["config"]["city_id"] == "SZH"
            and manifest["config"]["history_days"] == budget,
            "Input namespace/budget mismatch",
        )
        rows = [
            json.loads(line)
            for line in (input_run / "entities.jsonl").read_text(encoding="utf-8").splitlines()
            if json.loads(line).get("identity") == ["urbanev", "SZH", entity]
        ]
        require(
            len(rows) == 1
            and rows[0].get("role") == "development"
            and rows[0].get("initialization") == matches[0]["initialization"],
            "Entity is not accepted Development",
        )
        cells[key] = {**item, "input_run": input_run, "manifest": manifest, "entity": rows[0]}

    jobs = {}
    seasonal = set()
    logical_jobs = set()
    shared_sources = {}
    for item in plan["jobs"]:
        require(
            isinstance(item, dict)
            and set(item) == {"id", "cell", "config", "method", "device", "source", "target"},
            "Job fields mismatch",
        )
        key = item["id"]
        require(
            isinstance(key, str) and key.isidentifier() and key not in jobs,
            "Duplicate/invalid job id",
        )
        require(
            item["cell"] in cells and item["config"] in configs, "Unknown cell/config reference"
        )
        require(item["method"] in CONTROLLER_METHODS | SINGLE_METHODS, "Unsupported method")
        require(item["device"] in {"cpu", "cuda"}, "Unsupported device")
        logical = (item["cell"], item["config"], item["method"])
        require(logical not in logical_jobs, "Duplicate method/config/cell job")
        logical_jobs.add(logical)
        if item["method"] == "seasonal_naive":
            require(
                item["device"] == "cpu" and item["source"] is None and item["target"] is None,
                "Seasonal must be CPU and source-free",
            )
            cell = cells[item["cell"]]
            seasonal_key = (cell["budget"], cell["entity_id"])
            require(
                seasonal_key not in seasonal, "Deterministic Seasonal run duplicated across seeds"
            )
            seasonal.add(seasonal_key)
        elif item["method"] == "target_only":
            require(
                item["source"] is None and item["target"] is None,
                "Target-only cannot reuse Source/target",
            )
        else:
            require(
                isinstance(item["source"], dict) and set(item["source"]) == {"path", "sha256"},
                "Source checkpoint declaration required",
            )
            require(
                item["target"] is None
                or isinstance(item["target"], dict)
                and set(item["target"]) == {"path", "sha256"},
                "Invalid target checkpoint declaration",
            )
            if item["method"] == "frozen_source":
                require(item["target"] is None, "Frozen Source has no target checkpoint")
            cell = cells[item["cell"]]
            source_key = (cell["budget"], cell["seed"])
            source_identity = item["source"]
            require(
                source_key not in shared_sources or shared_sources[source_key] == source_identity,
                "Matched Development stratum uses different Source checkpoints",
            )
            shared_sources[source_key] = source_identity
            if item["method"] in CONTROLLER_METHODS:
                config = configs[item["config"]]["value"]
                require(
                    config["replay"].get("selection_rule", "confidence") == item["method"],
                    "Method/config selection rule differs",
                )
                if item["method"] in {"fixed_retention", "full_finetuning"}:
                    level = config["replay"]["initial_level"]
                    require(
                        config["target"]["retention_weight"] == level
                        and (item["method"] == "full_finetuning") == (level == 0),
                        "Fixed policy target/initial lambda differs",
                    )
        jobs[key] = item
    require(jobs, "At least one explicit job required")
    return plan, configs, cells, jobs


def _flags(values: dict, *, exclude: set[str] = frozenset()) -> list[str]:
    return [
        piece
        for key, value in values.items()
        if key not in exclude
        for piece in ("--" + key.replace("_", "-"), str(value))
    ]


def build_stages(
    job: dict, cell: dict, config: dict, job_root: Path
) -> list[tuple[str, str, list[str]]]:
    """Return allowlisted module/subcommand arguments, never shell text."""
    input_run = cell["input_run"]
    digest = cell["input_manifest_sha256"]
    entity, seed = cell["entity_id"], cell["seed"]
    replay = config["replay"]
    limit = replay["max_origins"]
    split = verification_split_limit(replay["block_days"], limit)
    base = ["--input-run", str(input_run), "--manifest-sha256", digest, "--entity-id", entity]
    method = job["method"]
    if method in SINGLE_METHODS:
        module = "experiments.hung_sprint2.single_baseline_cli"
        stages = []
        initial = job_root / "target-only-init" / "initial.pt"
        if method == "target_only":
            count = cell["entity"]["initial_trainable"]
            target = config["target"]
            stages.append(
                (
                    "target-only-init",
                    module,
                    [
                        "target-only-init",
                        *base,
                        "--output",
                        str(initial.parent),
                        "--calendar-hidden",
                        str(config["source"]["calendar_hidden"]),
                        "--seed",
                        str(seed),
                        "--learning-rate",
                        str(target["learning_rate"]),
                        "--batch-size",
                        str(target["batch_size"]),
                        "--steps",
                        str(math.ceil(count / target["batch_size"])),
                        "--device",
                        job["device"],
                    ],
                )
            )
        common = [
            "replay-development",
            *base,
            "--method",
            method,
            "--block-days",
            str(replay["block_days"]),
            "--device",
            job["device"],
        ]
        if method == "target_only":
            common += ["--initial-checkpoint", str(initial)]
        if method == "frozen_source":
            common += [
                "--source-input-run",
                str(input_run),
                "--source-manifest-sha256",
                digest,
                "--source-checkpoint",
                str(project_path(job["source"]["path"])),
            ]
        first = job_root / f"replay-{split}"
        stages.append(
            (
                f"replay-{split}",
                module,
                [*common, "--max-origins", str(split), "--output", str(first)],
            )
        )
        stages.append(
            (
                f"replay-{limit}",
                module,
                [
                    *common,
                    "--max-origins",
                    str(limit),
                    "--resume-checkpoint",
                    str(first / "runner.pt"),
                    "--output",
                    str(job_root / f"replay-{limit}"),
                ],
            )
        )
        return stages

    module = "experiments.hung_sprint2.cli"
    source = project_path(job["source"]["path"])
    target = (
        project_path(job["target"]["path"])
        if job["target"] is not None
        else job_root / "target" / "target_checkpoint.pt"
    )
    stages = []
    if job["target"] is None:
        settings = config["target"]
        steps = max(1, math.ceil(cell["entity"]["initial_trainable"] / settings["batch_size"]))
        stages.append(
            (
                "target",
                module,
                [
                    "target-smoke",
                    "--input-run",
                    str(input_run),
                    "--manifest-sha256",
                    digest,
                    "--source-input-run",
                    str(input_run),
                    "--source-manifest-sha256",
                    digest,
                    "--source-checkpoint",
                    str(source),
                    "--entity-id",
                    entity,
                    "--output",
                    str(target.parent),
                    "--steps",
                    str(steps),
                    "--batch-size",
                    str(settings["batch_size"]),
                    "--learning-rate",
                    str(settings["learning_rate"]),
                    "--retention-weight",
                    str(settings["retention_weight"]),
                    "--retention-kind",
                    settings.get("retention_kind", "latent"),
                    "--initialization-kind",
                    settings.get("initialization_kind", "source"),
                    "--epsilon",
                    str(settings["epsilon"]),
                    "--seed",
                    str(seed),
                    "--device",
                    job["device"],
                ],
            )
        )
    common = [
        "replay-development",
        "--input-run",
        str(input_run),
        "--manifest-sha256",
        digest,
        "--source-input-run",
        str(input_run),
        "--source-manifest-sha256",
        digest,
        "--source-checkpoint",
        str(source),
        "--target-checkpoint",
        str(target),
        "--entity-id",
        entity,
        "--seed",
        str(seed),
        "--device",
        job["device"],
        "--epsilon",
        str(config["target"]["epsilon"]),
        *_flags(replay, exclude={"missing_day_bootstrap_policy", "max_origins"}),
    ]
    first = job_root / f"replay-{split}"
    stages.append(
        (f"replay-{split}", module, [*common, "--max-origins", str(split), "--output", str(first)])
    )
    stages.append(
        (
            f"replay-{limit}",
            module,
            [
                *common,
                "--max-origins",
                str(limit),
                "--resume-checkpoint",
                str(first / "runner_checkpoint.pt"),
                "--output",
                str(job_root / f"replay-{limit}"),
            ],
        )
    )
    return stages


def verify_dependencies(
    job: dict,
    cell: dict,
    config_spec: dict,
    code: dict,
    single_code: dict,
    job_root: Path,
    stage_name: str,
) -> None:
    """Rehash all immutable input/config/model dependencies before each stage."""
    verify_file(config_spec["path"], config_spec["sha256"])
    input_run = cell["input_run"]
    manifest = _load_run(input_run, cell["input_manifest_sha256"])
    if job["method"] == "target_only" and stage_name != "target-only-init":
        checkpoint = job_root / "target-only-init" / "initial.pt"
        record = read_json(checkpoint.parent / "run_manifest.json")
        verify_file(checkpoint, record["initial_checkpoint_sha256"])
        binding = record.get("binding", {})
        require(
            record.get("status") == "completed"
            and record.get("method") == "target_only"
            and record.get("code", {}).get("executed_sources") == single_code["executed_sources"],
            "Target-only initial run differs",
        )
        require(
            binding.get("input_manifest_sha256") == cell["input_manifest_sha256"]
            and binding.get("entity_id") == cell["entity_id"]
            and binding.get("seed") == cell["seed"],
            "Target-only initial binding differs",
        )
        state = torch.load(checkpoint, map_location="cpu", weights_only=True)
        require(
            state.get("schema") == "hung-target-only-initial-v1"
            and state.get("binding") == binding,
            "Target-only initial checkpoint payload differs",
        )
    if (
        stage_name.startswith("replay-")
        and stage_name
        != f"replay-{verification_split_limit(config_spec['value']['replay']['block_days'], config_spec['value']['replay']['max_origins'])}"
    ):
        split = verification_split_limit(
            config_spec["value"]["replay"]["block_days"],
            config_spec["value"]["replay"]["max_origins"],
        )
        first = job_root / f"replay-{split}"
        first_record = read_json(first / "run_manifest.json")
        checkpoint_name = "runner.pt" if job["method"] in SINGLE_METHODS else "runner_checkpoint.pt"
        verify_file(first / checkpoint_name, first_record["final_runner_checkpoint_sha256"])
        require(
            first_record.get("status") == "completed"
            and first_record.get("code", {}).get("executed_sources")
            == (single_code if job["method"] in SINGLE_METHODS else code)["executed_sources"],
            "Split replay differs",
        )
    if job["source"] is None:
        return
    source = project_path(job["source"]["path"])
    source_binding = _binding(manifest, cell["input_manifest_sha256"], stage="source")
    source_record = checked_checkpoint(source, job["source"]["sha256"], source_binding, code)
    require(source_record["seed"] == cell["seed"], "Source seed differs")
    verify_source_schedule(source_record, config_spec["value"]["source"], input_run, manifest)
    if job["method"] == "frozen_source" or stage_name == "target":
        return
    target = (
        project_path(job["target"]["path"])
        if job["target"]
        else job_root / "target" / "target_checkpoint.pt"
    )
    target_digest = (
        job["target"]["sha256"]
        if job["target"]
        else read_json(target.parent / "run_manifest.json")["checkpoint_sha256"]
    )
    target_binding = _binding(
        manifest,
        cell["input_manifest_sha256"],
        stage="target",
        entity_id=cell["entity_id"],
        scale_id=cell["entity"]["scale"]["fit_sha256"],
        source_checkpoint_sha256=job["source"]["sha256"],
    )
    target_record = checked_checkpoint(target, target_digest, target_binding, code)
    settings = config_spec["value"]["target"]
    verify_target_schedule(target_record, settings, cell["entity"]["initial_trainable"])
    require(
        target_record["seed"] == cell["seed"]
        and target_record["retention_weight"] == settings["retention_weight"]
        and target_record.get("retention_kind", "latent")
        == settings.get("retention_kind", "latent")
        and target_record.get("initialization_kind", "source")
        == settings.get("initialization_kind", "source"),
        "Target method/config differs",
    )


def verify_stage_output(path: Path, stage_name: str, method: str, code: dict) -> None:
    record = read_json(path / "run_manifest.json")
    require(
        record.get("status") == "completed"
        and record.get("run_id") == path.name
        and record.get("code", {}).get("executed_sources") == code["executed_sources"],
        f"Stage output identity differs: {path}",
    )
    if stage_name == "target-only-init":
        checkpoint, digest = "initial.pt", record.get("initial_checkpoint_sha256")
    elif stage_name == "target":
        checkpoint, digest = "target_checkpoint.pt", record.get("checkpoint_sha256")
    else:
        checkpoint = "runner.pt" if method in SINGLE_METHODS else "runner_checkpoint.pt"
        digest = record.get("final_runner_checkpoint_sha256")
    verify_file(path / checkpoint, digest)


def verify_execution_identity(
    path: Path, plan: dict, plan_sha256: str, code: dict, single_code: dict
) -> None:
    """Reject plan, selection, or tracked code changes before each subprocess."""
    verify_file(path, plan_sha256)
    selection = plan["selection"]
    verify_file(project_path(selection["path"]), selection["sha256"])
    current = _code_identity()
    current_single = _single_code_identity()
    require(
        current["commit"] == code["commit"]
        and current["executed_sources"] == code["executed_sources"]
        and current["worktree_status"] == [],
        "Execution code identity changed between stages",
    )
    require(
        current_single["commit"] == single_code["commit"]
        and current_single["executed_sources"] == single_code["executed_sources"],
        "Single baseline code identity changed between stages",
    )


def dispatch(path: Path, *, execute: bool, expected_plan_sha256: str | None = None) -> dict:
    plan_sha256 = expected_plan_sha256 or sha256_file(path)
    verify_file(path, plan_sha256)
    plan, configs, cells, jobs = parse_plan(path)
    verify_file(path, plan_sha256)
    root = project_path(plan["output_root"])
    code = _code_identity()
    single_code = _single_code_identity()
    require(single_code["commit"] == code["commit"], "CLI code commits differ")
    planned = []
    for job_id, job in jobs.items():
        cell = cells[job["cell"]]
        config = configs[job["config"]]
        job_root = root / "jobs" / job_id
        for name, module, args in build_stages(job, cell, config["value"], job_root):
            planned.append((job_id, job, cell, config, name, module, args, job_root))
    if not execute:
        for job_id, job in jobs.items():
            if job["source"] is not None:
                cell = cells[job["cell"]]
                config = configs[job["config"]]
                split = verification_split_limit(
                    config["value"]["replay"]["block_days"],
                    config["value"]["replay"]["max_origins"],
                )
                stage_name = f"replay-{split}" if job["target"] is not None else "target"
                verify_dependencies(
                    job, cell, config, code, single_code, root / "jobs" / job_id, stage_name
                )
        for job_id, job, cell, config, name, module, args, job_root in planned:
            print(
                json.dumps(
                    {"job": job_id, "stage": name, "argv": [sys.executable, "-m", module, *args]}
                )
            )
        return {"jobs": len(jobs), "stages": len(planned), "executed": False}

    require_capacity(root)
    root.mkdir(parents=True, exist_ok=False)
    temp_dir = root / "tmp"
    temp_dir.mkdir()
    with (root / "dispatch_identity.json").open("x", encoding="utf-8") as stream:
        json.dump(
            {
                "schema": plan["schema"],
                "plan_sha256": plan_sha256,
                "code": code,
                "single_code": single_code,
                "jobs": len(jobs),
                "stages": len(planned),
            },
            stream,
            indent=2,
            sort_keys=True,
        )
        stream.write("\n")
    for job_id, job, cell, config, name, module, args, job_root in planned:
        require_capacity(root)
        verify_execution_identity(path, plan, plan_sha256, code, single_code)
        verify_dependencies(job, cell, config, code, single_code, job_root, name)
        stage_output = job_root / name
        require(not stage_output.exists(), f"Stage output already exists: {stage_output}")
        log_path = root / "logs" / job_id / f"{name}.log"
        require(not log_path.exists(), f"Stage log already exists: {log_path}")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        job_root.mkdir(parents=True, exist_ok=True)
        command = [sys.executable, "-m", module, *args]
        with log_path.open("x", encoding="utf-8") as log:
            log.write(
                json.dumps(
                    {
                        "command": command,
                        "config_sha256": config["sha256"],
                        "input_manifest_sha256": cell["input_manifest_sha256"],
                    }
                )
                + "\n"
            )
            log.flush()
            result = subprocess.run(
                command,
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
                env={
                    **os.environ,
                    "PYTHONUTF8": "1",
                    "TEMP": str(temp_dir),
                    "TMP": str(temp_dir),
                    "TMPDIR": str(temp_dir),
                },
            )
        require(
            result.returncode == 0,
            f"Stage failed ({result.returncode}); preserve output and inspect {log_path}",
        )
        output_code = single_code if job["method"] in SINGLE_METHODS else code
        verify_stage_output(stage_output, name, job["method"], output_code)
        print(
            json.dumps({"job": job_id, "stage": name, "log": str(log_path), "status": "completed"}),
            flush=True,
        )
    return {"jobs": len(jobs), "stages": len(planned), "executed": True}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument(
        "--execute", action="store_true", help="Actually run jobs; default is dry-run"
    )
    args = parser.parse_args(argv)
    plan = project_path(args.plan)
    require(plan.is_relative_to(ROOT.resolve()), "Plan must be inside current worktree")
    verify_file(plan, args.plan_sha256)
    print(json.dumps(dispatch(plan, execute=args.execute, expected_plan_sha256=args.plan_sha256)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
