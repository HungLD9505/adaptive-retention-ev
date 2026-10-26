"""DATA-v1 ZIP preflight and bounded, manifest-bound training smoke runs."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import time
from dataclasses import asdict
from pathlib import Path
from zipfile import BadZipFile, ZipFile

import torch

from ev_inputs.features import SCHEMA_ID
from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2.checkpoint import load_runner, save_runner
from experiments.hung_sprint2.controller import ControllerConfig
from experiments.hung_sprint2.evaluation import evaluate_replay
from experiments.hung_sprint2.model import ForecastGRU, ModelConfig
from experiments.hung_sprint2.retention import frozen_source_reference, source_latent_scale
from experiments.hung_sprint2.runner import PrequentialRunner
from experiments.hung_sprint2.training import (
    initialize_target,
    load_checkpoint,
    save_checkpoint,
    source_step,
    target_step,
)

ROOT = Path(__file__).resolve().parents[2]
RELEASE_CATALOG = ROOT / "data" / "releases" / "DATA-v1-20261019.json"
ARTIFACTS = (
    "training.jsonl",
    "entities.jsonl",
    "forecasts.jsonl",
    "labels.jsonl",
    "schedule.jsonl",
)


def _load_run(path: Path, expected_sha256: str) -> dict:
    """Verify the accepted v2 input manifest and every bound artifact."""
    if sha256_file(path / "manifest.json") != expected_sha256:
        raise ValueError("Input manifest SHA-256 mismatch")
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    if (
        manifest.get("schema") != "ev-loader-run-v2"
        or manifest.get("feature_schema") != SCHEMA_ID
        or manifest.get("missing_data_policy") != "ev-missing-data-v1"
        or manifest.get("status")
        not in {"technical_success", "technical_success_with_coverage_limits"}
    ):
        raise ValueError("Input run does not satisfy the accepted v2 policy")
    if manifest.get("run_id") != path.name:
        raise ValueError("Input run ID and directory differ")
    for name in ARTIFACTS:
        entry = manifest.get("files", {}).get(name)
        if not isinstance(entry, dict) or sha256_file(path / name) != entry.get("sha256"):
            raise ValueError(f"Input artifact SHA-256 mismatch: {name}")
    config = manifest.get("config", {})
    if config.get("dataset_id") not in {"urbanev", "charged"}:
        raise ValueError("Unknown dataset profile")
    if not isinstance(config.get("city_id"), str) or not config["city_id"]:
        raise ValueError("Missing city profile")
    if config.get("history_days") not in (7, 14, 28):
        raise ValueError("Input history budget is not 7/14/28 days")
    return manifest


def _records(path: Path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def _process_memory() -> dict:
    """Record the CLI process peak RSS when Linux exposes it."""
    if platform.system() != "Linux":
        return {"peak_rss_bytes": None, "scope": "whole CLI process", "source": "unavailable"}
    import resource

    peak_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {
        "peak_rss_bytes": int(peak_kib) * 1024,
        "scope": "whole CLI process; maximum since process start",
        "source": "resource.RUSAGE_SELF.ru_maxrss (Linux KiB)",
    }


def _device(name: str) -> torch.device:
    if name not in {"cpu", "cuda"}:
        raise ValueError("Device must be cpu or cuda")
    if name == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA was requested but is unavailable in this PyTorch runtime")
    return torch.device(name)


def _device_record(device: torch.device) -> dict:
    record = {"type": device.type, "torch": torch.__version__}
    if device.type == "cuda":
        torch.cuda.synchronize(device)
        record.update(
            name=torch.cuda.get_device_name(device),
            cuda_runtime=torch.version.cuda,
            peak_allocated_bytes=torch.cuda.max_memory_allocated(device),
            peak_reserved_bytes=torch.cuda.max_memory_reserved(device),
        )
    return record


def _identity(manifest: dict) -> tuple[str, str]:
    config = manifest["config"]
    return config["dataset_id"], config["city_id"]


def _examples(
    path: Path,
    manifest: dict,
    role: str,
    entity_id: str | None = None,
    *,
    limit: int | None = None,
) -> tuple[list[dict], int]:
    if limit is not None and limit <= 0:
        raise ValueError("Example retention limit must be positive")
    dataset, city = _identity(manifest)
    eligible = {
        tuple(row["identity"]) for row in _records(path / "entities.jsonl") if row["role"] == role
    }
    selected = []
    available = 0
    for row in _records(path / "training.jsonl"):
        if row["role"] != role:
            continue
        forecast = row["forecast"]
        if (
            tuple(forecast["identity"][:2]) != (dataset, city)
            or forecast["input_run_id"] != manifest["run_id"]
            or forecast["schema_id"] != SCHEMA_ID
            or tuple(forecast["identity"]) not in eligible
        ):
            raise ValueError("Training record identity/schema mismatch")
        if entity_id is None or forecast["identity"][2] == entity_id:
            available += 1
            if limit is None or len(selected) < limit:
                selected.append(row)
    return selected, available


def _tensors(rows: list[dict]) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    history = torch.tensor([row["forecast"]["x_hist"] for row in rows], dtype=torch.float32)
    calendar = torch.tensor([row["forecast"]["c_future"] for row in rows], dtype=torch.float32)
    labels = torch.tensor([row["y_scaled"] for row in rows], dtype=torch.float32)
    if history.shape != (len(rows), 24, 7) or calendar.shape != (len(rows), 24, 5):
        raise ValueError("Training tensor shape violates ev-input-v1")
    if labels.shape != (len(rows), 24) or not torch.isfinite(labels).all():
        raise ValueError("Training labels require 24 finite values")
    if torch.any(labels < 0):
        raise ValueError("Training labels cannot be negative")
    return history, calendar, labels


def _code_identity() -> dict:
    source_paths = [
        ROOT / "experiments" / "hung_sprint2" / name
        for name in (
            "model.py",
            "retention.py",
            "training.py",
            "cli.py",
            "controller.py",
            "baseline_selection.py",
            "runner.py",
            "replay_inputs.py",
            "checkpoint.py",
            "evaluation.py",
        )
    ]
    return {
        "commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "worktree_status": subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True
        ).splitlines(),
        "executed_sources": {
            path.relative_to(ROOT).as_posix(): sha256_file(path) for path in source_paths
        },
    }


def _binding(
    manifest: dict,
    manifest_sha256: str,
    *,
    stage: str,
    entity_id: str | None = None,
    scale_id: str | None = None,
    source_checkpoint_sha256: str | None = None,
) -> dict:
    dataset, city = _identity(manifest)
    return {
        "schema": "ev-checkpoint-input-binding-v1",
        "feature_schema": SCHEMA_ID,
        "input_manifest_sha256": manifest_sha256,
        "input_run_id": manifest["run_id"],
        "dataset_id": dataset,
        "city_id": city,
        "stage": stage,
        "entity_id": entity_id,
        "history_days": manifest["config"]["history_days"] if stage == "target" else None,
        "scale_id": scale_id,
        "source_checkpoint_sha256": source_checkpoint_sha256,
    }


def _validate_limits(args: argparse.Namespace) -> None:
    if args.steps <= 0 or args.batch_size <= 0 or args.seed < 0:
        raise ValueError("steps, batch size and seed must be positive/nonnegative")
    if not 0 < args.learning_rate < float("inf"):
        raise ValueError("learning rate must be finite and positive")


def _new_output(output: Path, *inputs: Path) -> Path:
    destination = output.resolve()
    if any(destination.is_relative_to(path.resolve()) for path in inputs):
        raise ValueError("Output must not be inside an input run or source checkpoint folder")
    if destination.exists():
        raise FileExistsError("Output run already exists")
    return destination


def _write_run(output: Path, summary: dict) -> None:
    with (output / "run_manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _verify_input_zip(archive: Path, package_name: str, catalog: Path | None = None) -> dict:
    """Read-only check of one fixed DATA-v1 input package before extraction."""
    catalog = RELEASE_CATALOG if catalog is None else catalog
    release = json.loads(catalog.read_text(encoding="utf-8"))
    if release.get("release_id") != "DATA-v1-20261019":
        raise ValueError("Unexpected input release identity")
    matches = [
        item
        for item in release.get("packages", [])
        if item.get("kind") == "inputs" and item.get("name") == package_name
    ]
    if len(matches) != 1:
        raise ValueError("Input package is not unique in DATA-v1 catalog")
    expected = matches[0]
    if archive.name != package_name or archive.stat().st_size != expected["size_bytes"]:
        raise ValueError("Input package name/size differs from DATA-v1 catalog")
    digest = sha256_file(archive)
    if digest != expected["sha256"]:
        raise ValueError("Input package SHA-256 differs from DATA-v1 catalog")
    try:
        with ZipFile(archive) as package:
            damaged = package.testzip()
    except BadZipFile as error:
        raise ValueError("Input package ZIP structure is invalid") from error
    if damaged is not None:
        raise ValueError(f"Input package CRC failed: {damaged}")
    return {
        "status": "verified",
        "release_id": release["release_id"],
        "package": package_name,
        "size_bytes": expected["size_bytes"],
        "sha256": digest,
        "scope": "archive integrity only; no extraction, input-manifest check or training",
    }


def _source(args: argparse.Namespace) -> dict:
    started = time.perf_counter()
    _validate_limits(args)
    if args.calendar_hidden <= 0:
        raise ValueError("calendar_hidden must be positive")
    run = args.input_run.resolve()
    manifest = _load_run(run, args.manifest_sha256)
    examples, available = _examples(run, manifest, "source", limit=args.steps * args.batch_size)
    if not examples:
        raise ValueError("The selected input run has no Source training examples")
    if min(len(examples), args.steps * args.batch_size) < 2:
        raise ValueError("Source smoke requires at least two examples before training")
    output = _new_output(args.output, run)
    device = _device(getattr(args, "device", "cpu"))
    torch.manual_seed(args.seed)
    model = ForecastGRU(ModelConfig(calendar_hidden=args.calendar_hidden)).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    steps = 0
    used = []
    for start in range(0, len(examples), args.batch_size):
        if steps == args.steps:
            break
        batch = examples[start : start + args.batch_size]
        x_hist, c_future, y_scaled = _tensors(batch)
        x_hist, c_future, y_scaled = (x_hist.to(device), c_future.to(device), y_scaled.to(device))
        source_step(model, optimizer, x_hist, c_future, y_scaled)
        used.extend(batch)
        steps += 1
    source_scale = source_latent_scale(
        model,
        (
            _tensors(used[start : start + args.batch_size])[0].to(device)
            for start in range(0, len(used), args.batch_size)
        ),
    )
    code = _code_identity()
    output.mkdir(parents=True, exist_ok=False)
    checkpoint = output / "source_checkpoint.pt"
    binding = _binding(manifest, args.manifest_sha256, stage="source")
    save_checkpoint(
        checkpoint,
        model,
        optimizer,
        input_binding=binding,
        latent_scale=source_scale,
        seed=args.seed,
        code_sha=code["commit"],
        training_step=steps,
    )
    summary = {
        "scope": "bounded_source_smoke; not full source pretraining or effectiveness evidence",
        "status": "completed",
        "run_id": output.name,
        "input_binding": binding,
        "source_examples_available": available,
        "source_examples_used": len(used),
        "steps": steps,
        "requested_steps": args.steps,
        "batch_size": args.batch_size,
        "seed": args.seed,
        "learning_rate": args.learning_rate,
        "calendar_hidden": args.calendar_hidden,
        "device": _device_record(device),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "duration_seconds": time.perf_counter() - started,
        "memory_usage": _process_memory(),
        "code": code,
        "checkpoint_sha256": sha256_file(checkpoint),
    }
    _write_run(output, summary)
    return summary


def _target(args: argparse.Namespace) -> dict:
    started = time.perf_counter()
    _validate_limits(args)
    if not 0 <= args.retention_weight < float("inf") or not 0 < args.epsilon < float("inf"):
        raise ValueError("retention weight/epsilon must be valid")
    source_run = args.source_input_run.resolve()
    source_manifest = _load_run(source_run, args.source_manifest_sha256)
    target_run = args.input_run.resolve()
    manifest = _load_run(target_run, args.manifest_sha256)
    if _identity(source_manifest) != _identity(manifest):
        raise ValueError("Source and target must have the same dataset/city profile")
    source_binding = _binding(source_manifest, args.source_manifest_sha256, stage="source")
    device = _device(getattr(args, "device", "cpu"))
    source_model, _, latent_scale, _ = load_checkpoint(
        args.source_checkpoint, expected_binding=source_binding, map_location=device
    )
    if latent_scale is None:
        raise ValueError("Source checkpoint lacks fixed latent scale")
    source_sha = sha256_file(args.source_checkpoint)
    source_run_record = args.source_checkpoint.parent / "run_manifest.json"
    if not source_run_record.is_file():
        raise ValueError("Source checkpoint run manifest is required")
    source_record = json.loads(source_run_record.read_text(encoding="utf-8"))
    if (
        source_record.get("checkpoint_sha256") != source_sha
        or source_record.get("input_binding") != source_binding
    ):
        raise ValueError("Source checkpoint lineage mismatch")
    matches = [
        row
        for row in _records(target_run / "entities.jsonl")
        if row["role"] == "development"
        and row["identity"] == [*_identity(manifest), args.entity_id]
    ]
    if len(matches) != 1:
        raise ValueError("Development target entity not found uniquely")
    entity = matches[0]
    mode = entity["initialization"]
    if mode not in {"target_initial_adaptation", "source_checkpoint_only"}:
        raise ValueError(f"Target initialization is blocked: {mode}")
    scale_id = entity["scale"]["fit_sha256"]
    examples, available = _examples(target_run, manifest, "development", args.entity_id)
    if "initial_trainable" in entity and entity["initial_trainable"] != available:
        raise ValueError("Target example count disagrees with entity inventory")
    if (mode == "source_checkpoint_only") != (len(examples) == 0):
        raise ValueError("Target initialization mode disagrees with training records")
    if any(row["forecast"]["scale_id"] != scale_id for row in examples):
        raise ValueError("Target examples use a different frozen scale")
    output = _new_output(args.output, target_run, source_run, args.source_checkpoint.parent)
    torch.manual_seed(args.seed)
    target, reference, optimizer = initialize_target(source_model, learning_rate=args.learning_rate)
    steps = 0
    for start in range(0, len(examples), args.batch_size):
        if steps == args.steps:
            break
        x_hist, c_future, y_scaled = _tensors(examples[start : start + args.batch_size])
        x_hist, c_future, y_scaled = (x_hist.to(device), c_future.to(device), y_scaled.to(device))
        target_step(
            target,
            reference,
            optimizer,
            x_hist,
            c_future,
            y_scaled,
            retention_weight=args.retention_weight,
            latent_scale=latent_scale,
            epsilon=args.epsilon,
        )
        steps += 1
    code = _code_identity()
    output.mkdir(parents=True, exist_ok=False)
    checkpoint = output / "target_checkpoint.pt"
    binding = _binding(
        manifest,
        args.manifest_sha256,
        stage="target",
        entity_id=args.entity_id,
        scale_id=scale_id,
        source_checkpoint_sha256=source_sha,
    )
    save_checkpoint(
        checkpoint,
        target,
        optimizer,
        input_binding=binding,
        latent_scale=latent_scale,
        seed=args.seed,
        code_sha=code["commit"],
        training_step=steps,
    )
    summary = {
        "scope": "bounded_development_initialization; no online replay or effectiveness evidence",
        "status": "completed",
        "run_id": output.name,
        "input_binding": binding,
        "initialization": mode,
        "target_examples_available": len(examples),
        "steps": steps,
        "requested_steps": args.steps,
        "batch_size": args.batch_size,
        "seed": args.seed,
        "learning_rate": args.learning_rate,
        "retention_weight": args.retention_weight,
        "epsilon": args.epsilon,
        "device": _device_record(device),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "duration_seconds": time.perf_counter() - started,
        "memory_usage": _process_memory(),
        "source_scope": source_record.get("scope"),
        "code": code,
        "checkpoint_sha256": sha256_file(checkpoint),
    }
    _write_run(output, summary)
    return summary


def _replay(args: argparse.Namespace) -> dict:
    from experiments.hung_sprint2.replay_inputs import replay_target

    started = time.perf_counter()
    selection_rule = getattr(args, "selection_rule", "confidence")
    if selection_rule not in {
        "confidence",
        "online_best_lambda",
        "without_confidence",
        "fixed_retention",
        "full_finetuning",
    }:
        raise ValueError("Unsupported selection rule")
    device = _device(getattr(args, "device", "cpu"))
    if args.seed < 0 or not 0 < args.epsilon < float("inf"):
        raise ValueError("Replay seed/epsilon is invalid")
    controller = ControllerConfig(
        levels=(0.0, args.level_one, args.level_two),
        initial_level=args.initial_level,
        block_days=args.block_days,
        min_complete_days=args.min_complete_days,
        delta=args.delta,
        alpha=args.alpha,
        bootstrap_segment_days=args.bootstrap_segment_days,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=args.seed,
        challenger_rule=args.challenger_rule,
    )
    input_run = args.input_run.resolve()
    source_run = args.source_input_run.resolve()
    manifest = _load_run(input_run, args.manifest_sha256)
    source_manifest = _load_run(source_run, args.source_manifest_sha256)
    if _identity(manifest) != _identity(source_manifest):
        raise ValueError("Source and target dataset/city differ")
    if args.entity_id == "" or args.max_origins <= 0:
        raise ValueError("Entity and positive origin limit are required")
    source_binding = _binding(source_manifest, args.source_manifest_sha256, stage="source")
    source_sha = sha256_file(args.source_checkpoint)
    source_record = json.loads(
        (args.source_checkpoint.parent / "run_manifest.json").read_text(encoding="utf-8")
    )
    if (
        source_record.get("checkpoint_sha256") != source_sha
        or source_record.get("input_binding") != source_binding
    ):
        raise ValueError("Source checkpoint run lineage mismatch")
    source_model, _, source_scale, _ = load_checkpoint(
        args.source_checkpoint, expected_binding=source_binding, map_location=device
    )
    if source_scale is None:
        raise ValueError("Source checkpoint lacks fixed latent scale")
    entities = [
        row
        for row in _records(input_run / "entities.jsonl")
        if row.get("role") == "development"
        and row.get("identity") == [*_identity(manifest), args.entity_id]
    ]
    if len(entities) != 1 or entities[0].get("initialization") not in {
        "target_initial_adaptation",
        "source_checkpoint_only",
    }:
        raise ValueError("Unique, trainable Development entity is required")
    scale = entities[0]["scale"]
    target_binding = _binding(
        manifest,
        args.manifest_sha256,
        stage="target",
        entity_id=args.entity_id,
        scale_id=scale["fit_sha256"],
        source_checkpoint_sha256=source_sha,
    )
    target_sha = sha256_file(args.target_checkpoint)
    target_record = json.loads(
        (args.target_checkpoint.parent / "run_manifest.json").read_text(encoding="utf-8")
    )
    if (
        target_record.get("checkpoint_sha256") != target_sha
        or target_record.get("input_binding") != target_binding
    ):
        raise ValueError("Target checkpoint run lineage mismatch")
    if selection_rule in {"fixed_retention", "full_finetuning"}:
        expected_weight = controller.initial_level
        if (selection_rule == "full_finetuning") != (expected_weight == 0.0):
            raise ValueError("Fixed policy and initial lambda are inconsistent")
        if target_record.get("retention_weight") != expected_weight:
            raise ValueError("Target initialization lambda does not match fixed replay policy")
    target_model, optimizer, target_scale, _ = load_checkpoint(
        args.target_checkpoint, expected_binding=target_binding, map_location=device
    )
    if target_scale is None or not torch.equal(target_scale, source_scale):
        raise ValueError("Target latent scale differs from bound Source")
    config = {
        "controller": {**asdict(controller), "levels": list(controller.levels)},
        "selection_rule": selection_rule,
        "epsilon": args.epsilon,
        "seed": args.seed,
        "max_origins": args.max_origins,
        "device": device.type,
    }
    code = _code_identity()
    if args.resume_checkpoint is None:
        torch.manual_seed(args.seed)
        runner = PrequentialRunner(
            target_model,
            optimizer,
            frozen_source_reference(source_model),
            source_scale,
            binding=target_binding,
            controller=controller,
            epsilon=args.epsilon,
            energy_scale=scale["energy_scale"],
            selection_rule=selection_rule,
        )
        resumed_from = None
    else:
        resume_sha = sha256_file(args.resume_checkpoint)
        previous = json.loads(
            (args.resume_checkpoint.parent / "run_manifest.json").read_text(encoding="utf-8")
        )
        previous_journal = previous.get("event_journal")
        journal_file = args.resume_checkpoint.parent / "events.jsonl"
        if not isinstance(previous_journal, dict) or not journal_file.is_file():
            raise ValueError("Previous replay event journal is missing")
        journal_start = previous_journal.get("start_event_index")
        journal_end = previous_journal.get("end_event_index")
        journal_events = previous_journal.get("events_written")
        if (
            any(
                isinstance(value, bool) or not isinstance(value, int)
                for value in (journal_start, journal_end, journal_events)
            )
            or not 0 <= journal_start <= journal_end
            or journal_events != journal_end - journal_start
        ):
            raise ValueError("Previous replay event journal index range is invalid")
        if (
            previous.get("schema") != "hung-sprint2-development-replay-v1"
            or previous.get("status") != "completed"
            or previous.get("run_id") != args.resume_checkpoint.parent.name
            or previous.get("final_runner_checkpoint_sha256") != resume_sha
            or previous.get("target_checkpoint_sha256") != target_sha
            or previous.get("source_checkpoint_sha256") != source_sha
            or previous.get("input_binding") != target_binding
            or previous.get("source_input_binding") != source_binding
            or previous.get("config", {}).get("controller") != config["controller"]
            or previous.get("config", {}).get("selection_rule", "confidence") != selection_rule
            or previous.get("config", {}).get("epsilon") != args.epsilon
            or previous.get("config", {}).get("seed") != args.seed
            or previous.get("config", {}).get("device", "cpu") != device.type
            or previous.get("code", {}).get("executed_sources") != code["executed_sources"]
            or previous_journal.get("file") != "events.jsonl"
            or sha256_file(journal_file) != previous_journal.get("sha256")
        ):
            raise ValueError("Runner resume lineage/config/code mismatch")
        runner = load_runner(args.resume_checkpoint, expected_binding=target_binding, device=device)
        if (
            runner.controller != controller
            or runner.selection_rule != selection_rule
            or runner.epsilon != args.epsilon
            or runner.energy_scale != scale["energy_scale"]
            or runner.next_index != previous.get("runner_cursor")
            or runner.next_index >= args.max_origins
            or journal_end != len(runner.events)
        ):
            raise ValueError("Restored runner configuration differs")
        resumed_from = {"run_id": previous["run_id"], "checkpoint_sha256": resume_sha}
    output = _new_output(
        args.output,
        input_run,
        source_run,
        args.source_checkpoint.parent,
        args.target_checkpoint.parent,
        *([args.resume_checkpoint.parent] if args.resume_checkpoint else []),
    )
    output.mkdir(parents=True, exist_ok=False)
    journal_path = output / "events.jsonl"
    event_start_index = 0 if resumed_from is None else len(runner.events)
    journal_count = 0
    with journal_path.open("x", encoding="utf-8", newline="\n") as journal:
        header = {
            "schema": "hung-sprint2-event-journal-v1",
            "kind": "header",
            "run_id": output.name,
            "input_binding": target_binding,
            "resumed_from": resumed_from,
            "start_event_index": event_start_index,
        }
        journal.write(json.dumps(header, sort_keys=True, allow_nan=False) + "\n")
        journal.flush()
        os.fsync(journal.fileno())

        def record_event(event_index: int, event: str) -> None:
            nonlocal journal_count
            journal.write(
                json.dumps(
                    {"kind": "event", "event_index": event_index, "value": event},
                    sort_keys=True,
                    allow_nan=False,
                )
                + "\n"
            )
            journal.flush()
            os.fsync(journal.fileno())
            journal_count += 1

        replay = replay_target(
            input_run,
            manifest_sha256=args.manifest_sha256,
            entity_id=args.entity_id,
            runner=runner,
            max_origins=args.max_origins,
            event_sink=record_event,
            event_start_index=event_start_index,
        )
    if journal_count != len(runner.events) - event_start_index:
        raise ValueError("Event journal does not cover the replayed runner events")
    evaluation = evaluate_replay(runner, replay)
    final_checkpoint = output / "runner_checkpoint.pt"
    save_runner(final_checkpoint, runner)
    summary = {
        "schema": "hung-sprint2-development-replay-v1",
        "scope": "bounded_development_replay; fixture/Development evidence only; no Final evaluation",
        "status": "completed",
        "run_id": output.name,
        "input_binding": target_binding,
        "source_input_binding": source_binding,
        "source_checkpoint_sha256": source_sha,
        "target_checkpoint_sha256": target_sha,
        "final_runner_checkpoint_sha256": sha256_file(final_checkpoint),
        "resumed_from": resumed_from,
        "config": config,
        "coverage": asdict(evaluation.coverage),
        "metrics_kwh": {
            "live": None if evaluation.live is None else asdict(evaluation.live),
            "candidates": [None if x is None else asdict(x) for x in evaluation.candidates],
            "audit": None if evaluation.audit is None else asdict(evaluation.audit),
            "audit_scored_days": evaluation.audit_scored_days,
        },
        "runtime_costs": runner.runtime_costs,
        "state_tensor_memory": runner.state_tensor_memory(),
        "event_evidence": {
            "events": runner.events,
            "decisions": [asdict(x) for x in runner.decisions],
        },
        "event_journal": {
            "file": journal_path.name,
            "sha256": sha256_file(journal_path),
            "start_event_index": event_start_index,
            "end_event_index": len(runner.events),
            "events_written": journal_count,
        },
        "runner_cursor": runner.next_index,
        "python": platform.python_version(),
        "torch": torch.__version__,
        "device": _device_record(device),
        "duration_seconds": time.perf_counter() - started,
        "memory_usage": _process_memory(),
        "code": code,
    }
    _write_run(output, summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    source = subparsers.add_parser("source-smoke")
    target = subparsers.add_parser("target-smoke")
    verify = subparsers.add_parser("verify-input-zip")
    replay = subparsers.add_parser("replay-development")
    verify.add_argument("--archive", type=Path, required=True)
    verify.add_argument("--package", required=True)
    for subparser in (source, target):
        subparser.add_argument("--input-run", type=Path, required=True)
        subparser.add_argument("--manifest-sha256", required=True)
        subparser.add_argument("--output", type=Path, required=True)
        subparser.add_argument("--steps", type=int, required=True)
        subparser.add_argument("--batch-size", type=int, required=True)
        subparser.add_argument("--seed", type=int, required=True)
        subparser.add_argument("--learning-rate", type=float, required=True)
        subparser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    source.add_argument("--calendar-hidden", type=int, required=True)
    target.add_argument("--source-input-run", type=Path, required=True)
    target.add_argument("--source-manifest-sha256", required=True)
    target.add_argument("--source-checkpoint", type=Path, required=True)
    target.add_argument("--entity-id", required=True)
    target.add_argument("--retention-weight", type=float, required=True)
    target.add_argument("--epsilon", type=float, required=True)
    for name in (
        "input-run",
        "source-input-run",
        "source-checkpoint",
        "target-checkpoint",
        "output",
    ):
        replay.add_argument(f"--{name}", type=Path, required=True)
    for name in ("manifest-sha256", "source-manifest-sha256", "entity-id", "challenger-rule"):
        replay.add_argument(f"--{name}", required=True)
    for name in (
        "max-origins",
        "block-days",
        "min-complete-days",
        "bootstrap-segment-days",
        "bootstrap-resamples",
        "seed",
    ):
        replay.add_argument(f"--{name}", type=int, required=True)
    for name in ("level-one", "level-two", "initial-level", "delta", "alpha", "epsilon"):
        replay.add_argument(f"--{name}", type=float, required=True)
    replay.add_argument("--resume-checkpoint", type=Path)
    replay.add_argument(
        "--selection-rule",
        choices=(
            "confidence",
            "online_best_lambda",
            "without_confidence",
            "fixed_retention",
            "full_finetuning",
        ),
        default="confidence",
    )
    replay.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    args = parser.parse_args(argv)
    if args.command == "verify-input-zip":
        print(json.dumps(_verify_input_zip(args.archive, args.package)))
        return 0
    result = {"source-smoke": _source, "target-smoke": _target, "replay-development": _replay}[
        args.command
    ](args)
    print(json.dumps({key: result[key] for key in ("status", "run_id", "scope")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
