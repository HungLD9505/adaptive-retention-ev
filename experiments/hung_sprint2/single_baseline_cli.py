"""Create-only Target-only initialization and single-model Development replay."""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import re
import subprocess
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

import torch

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2._create_only import publish_create_only
from experiments.hung_sprint2.cli import (
    ROOT,
    _binding,
    _device,
    _device_record,
    _identity,
    _load_run,
    _new_output,
    _process_memory,
    _tensors,
)
from experiments.hung_sprint2.evaluation import (
    aggregate_errors,
    complete_day_error_totals,
    coverage_from_replay,
)
from experiments.hung_sprint2.memory import model_optimizer_tensor_bytes, model_tensor_bytes
from experiments.hung_sprint2.model import ForecastGRU, ModelConfig
from experiments.hung_sprint2.replay_inputs import _target_rows, replay_target
from experiments.hung_sprint2.single_baseline import SingleBaselineRunner, validate_single_binding
from experiments.hung_sprint2.training import load_checkpoint, source_step


def _code_identity() -> dict:
    names = (
        "model.py",
        "training.py",
        "replay_inputs.py",
        "single_baseline.py",
        "single_baseline_cli.py",
        "evaluation.py",
    )
    return {
        "commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "executed_sources": {
            f"experiments/hung_sprint2/{name}": sha256_file(
                ROOT / "experiments/hung_sprint2" / name
            )
            for name in names
        },
    }


def _write_json(path: Path, payload: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _save_state(path: Path, state: dict) -> str:
    if path.exists():
        raise FileExistsError(path)
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            torch.save(state, stream)
            stream.flush()
            os.fsync(stream.fileno())
        publish_create_only(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return sha256_file(path)


def _development_entity(path: Path, manifest: dict, entity_id: str) -> dict:
    identity = [*_identity(manifest), entity_id]
    matches = list(_target_rows(path / "entities.jsonl", identity))
    if len(matches) != 1 or matches[0].get("initialization") not in {
        "target_initial_adaptation",
        "source_checkpoint_only",
    }:
        raise ValueError("Unique ready Development target is required")
    scale = matches[0].get("scale", {})
    if (
        not isinstance(scale.get("fit_sha256"), str)
        or not math.isfinite(scale.get("energy_scale", float("nan")))
        or scale["energy_scale"] <= 0
    ):
        raise ValueError("Target frozen scale is invalid")
    return matches[0]


def _training_rows(path: Path, manifest: dict, entity_id: str, scale_id: str) -> list[dict]:
    """Decode only Development training rows from the authenticated writer format."""
    selected = []
    deployment = datetime.fromisoformat(manifest["config"]["deployment"])
    role_header = re.compile(r'^\s*\{\s*"role"\s*:\s*"development"\s*,')
    with (path / "training.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            if not role_header.match(line):
                continue
            row = json.loads(line)
            forecast = row["forecast"]
            if row["role"] != "development" or forecast["identity"][:2] != list(
                _identity(manifest)
            ):
                raise ValueError("Development training identity differs")
            if forecast["identity"][2] != entity_id:
                continue
            if (
                forecast["input_run_id"] != manifest["run_id"]
                or forecast["schema_id"] != "ev-input-v1"
                or forecast["scale_id"] != scale_id
            ):
                raise ValueError("Target training schema/run/scale differs")
            if (
                datetime.fromisoformat(forecast["origin"]) >= deployment
                or datetime.fromisoformat(forecast["future_labels"][-1]) >= deployment
            ):
                raise ValueError("Target-only initial example crosses deployment")
            selected.append(row)
    return selected


def _initialize_target_only(args: argparse.Namespace) -> dict:
    started = time.perf_counter()
    path = args.input_run.resolve()
    manifest = _load_run(path, args.manifest_sha256)
    entity = _development_entity(path, manifest, args.entity_id)
    if (
        args.seed < 0
        or args.batch_size < 1
        or args.steps < 0
        or not 0 < args.learning_rate < float("inf")
    ):
        raise ValueError("Invalid Target-only initialization settings")
    rows = _training_rows(path, manifest, args.entity_id, entity["scale"]["fit_sha256"])
    if entity.get("initial_trainable", len(rows)) != len(rows):
        raise ValueError("Target-only prefix count differs from inventory")
    if (entity["initialization"] == "source_checkpoint_only") != (len(rows) == 0):
        raise ValueError("Target-only prefix/initialization stratum differs")
    if args.steps != math.ceil(len(rows) / args.batch_size):
        raise ValueError("Target-only must use exactly one permitted prefix pass")
    device = _device(args.device)
    torch.manual_seed(args.seed)
    model = ForecastGRU(ModelConfig(calendar_hidden=args.calendar_hidden)).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    steps = 0
    for start in range(0, len(rows), args.batch_size):
        if steps == args.steps:
            break
        x, c, y = _tensors(rows[start : start + args.batch_size])
        source_step(model, optimizer, x.to(device), c.to(device), y.to(device))
        steps += 1
    output = _new_output(args.output, path)
    output.mkdir(parents=True, exist_ok=False)
    checkpoint = output / "initial.pt"
    binding = {
        "schema": "hung-target-only-initial-v1",
        "input_manifest_sha256": args.manifest_sha256,
        "input_run_id": manifest["run_id"],
        "dataset_id": _identity(manifest)[0],
        "city_id": _identity(manifest)[1],
        "entity_id": args.entity_id,
        "history_days": manifest["config"]["history_days"],
        "scale_id": entity["scale"]["fit_sha256"],
        "seed": args.seed,
        "steps": steps,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
    }
    initial_sha = _save_state(
        checkpoint,
        {
            "schema": "hung-target-only-initial-v1",
            "binding": binding,
            "architecture": model.config.to_dict(),
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "torch_rng": torch.get_rng_state().clone(),
        },
    )
    result = {
        "schema": "hung-target-only-init-run-v1",
        "status": "completed",
        "run_id": output.name,
        "scope": "Development prefix initialization only; no replay/Final",
        "method": "target_only",
        "binding": binding,
        "initial_checkpoint_sha256": initial_sha,
        "source_checkpoint_sha256": None,
        "training_examples": len(rows),
        "training_steps": steps,
        "initialization_seconds": time.perf_counter() - started,
        "device": _device_record(device),
        "code": _code_identity(),
    }
    _write_json(output / "run_manifest.json", result)
    return result


def _load_initial(
    args: argparse.Namespace, manifest: dict, entity: dict, device: torch.device
) -> tuple[ForecastGRU, torch.optim.Adam | None, str, str | None, dict]:
    if args.method == "target_only":
        if args.source_checkpoint is not None or args.source_input_run is not None:
            raise ValueError("Target-only must not receive a Source checkpoint/run")
        if args.initial_checkpoint is None:
            raise ValueError("Target-only requires its own initial checkpoint")
        path = args.initial_checkpoint.resolve()
        record = json.loads((path.parent / "run_manifest.json").read_text(encoding="utf-8"))
        digest = sha256_file(path)
        state = torch.load(path, map_location=device, weights_only=True)
        expected = state.get("binding", {})
        if (
            record.get("schema") != "hung-target-only-init-run-v1"
            or record.get("method") != "target_only"
            or record.get("source_checkpoint_sha256") is not None
            or record.get("initial_checkpoint_sha256") != digest
            or record.get("binding") != expected
            or state.get("schema") != "hung-target-only-initial-v1"
            or expected.get("input_manifest_sha256") != args.manifest_sha256
            or expected.get("input_run_id") != manifest["run_id"]
            or expected.get("entity_id") != args.entity_id
            or expected.get("scale_id") != entity["scale"]["fit_sha256"]
            or expected.get("dataset_id") != _identity(manifest)[0]
            or expected.get("city_id") != _identity(manifest)[1]
            or expected.get("history_days") != manifest["config"]["history_days"]
            or record.get("code", {}).get("executed_sources")
            != _code_identity()["executed_sources"]
        ):
            raise ValueError("Target-only initial checkpoint lineage differs")
        model = ForecastGRU(ModelConfig(**state["architecture"])).to(device)
        model.load_state_dict(state["model"])
        optimizer = torch.optim.Adam(model.parameters(), lr=1.0)
        optimizer.load_state_dict(state["optimizer"])
        return model, optimizer, digest, None, record
    if args.initial_checkpoint is not None:
        raise ValueError("Frozen Source uses --source-checkpoint, not --initial-checkpoint")
    if (
        args.source_checkpoint is None
        or args.source_input_run is None
        or args.source_manifest_sha256 is None
    ):
        raise ValueError("Frozen Source requires Source run, manifest and checkpoint")
    source_run = args.source_input_run.resolve()
    source_manifest = _load_run(source_run, args.source_manifest_sha256)
    if _identity(source_manifest) != _identity(manifest):
        raise ValueError("Frozen Source dataset/city differs from target")
    source_binding = _binding(source_manifest, args.source_manifest_sha256, stage="source")
    path = args.source_checkpoint.resolve()
    digest = sha256_file(path)
    record = json.loads((path.parent / "run_manifest.json").read_text(encoding="utf-8"))
    if record.get("checkpoint_sha256") != digest or record.get("input_binding") != source_binding:
        raise ValueError("Frozen Source checkpoint run lineage differs")
    model, _, _, _ = load_checkpoint(path, expected_binding=source_binding, map_location=device)
    return model, None, digest, digest, record


def _evaluate(runner: SingleBaselineRunner, replay) -> dict:
    coverage = coverage_from_replay(replay)
    if len(runner.issued) != coverage.created:
        raise ValueError("Single-model issued coverage differs")
    days = []
    for issued in runner.issued:
        y = issued["y_scaled"]
        if y is None:
            if issued["normalized_mae"] is not None:
                raise ValueError("Unscored day carries an MAE")
            continue
        if issued["normalized_mae"] is None:
            raise ValueError("Scored day is missing MAE")
        days.append(
            complete_day_error_totals(
                issued["prediction"].squeeze(0),
                y,
                torch.ones(24, dtype=torch.bool),
                energy_scale=runner.energy_scale,
            )
        )
    if len(days) != coverage.scored:
        raise ValueError("Single-model scored coverage differs")
    return {
        "coverage": asdict(coverage),
        "metrics_kwh": None if not days else asdict(aggregate_errors(days)),
    }


def _replay(args: argparse.Namespace) -> dict:
    started = time.perf_counter()
    path = args.input_run.resolve()
    manifest = _load_run(path, args.manifest_sha256)
    entity = _development_entity(path, manifest, args.entity_id)
    if (
        args.method not in ("target_only", "frozen_source")
        or args.block_days < 1
        or args.max_origins < 1
    ):
        raise ValueError("Invalid single-model method/block/horizon")
    device = _device(args.device)
    model, optimizer, initial_sha, source_sha, initial_record = _load_initial(
        args, manifest, entity, device
    )
    binding = {
        "schema": "hung-single-baseline-binding-v1",
        "method": args.method,
        "feature_schema": "ev-input-v1",
        "input_manifest_sha256": args.manifest_sha256,
        "input_run_id": manifest["run_id"],
        "dataset_id": _identity(manifest)[0],
        "city_id": _identity(manifest)[1],
        "entity_id": args.entity_id,
        "history_days": manifest["config"]["history_days"],
        "scale_id": entity["scale"]["fit_sha256"],
        "initial_checkpoint_sha256": initial_sha,
        "source_checkpoint_sha256": source_sha,
    }
    validate_single_binding(binding)
    code = _code_identity()
    config = {
        "method": args.method,
        "block_days": args.block_days,
        "max_origins": args.max_origins,
        "device": device.type,
    }
    if args.resume_checkpoint is None:
        runner = SingleBaselineRunner(
            model,
            optimizer,
            binding=binding,
            energy_scale=entity["scale"]["energy_scale"],
            block_days=args.block_days,
        )
        resumed_from = None
    else:
        resume_path = args.resume_checkpoint.resolve()
        previous = json.loads(
            (resume_path.parent / "run_manifest.json").read_text(encoding="utf-8")
        )
        resume_sha = sha256_file(resume_path)
        if (
            previous.get("schema") != "hung-single-baseline-replay-v1"
            or previous.get("status") != "completed"
            or previous.get("final_runner_checkpoint_sha256") != resume_sha
            or previous.get("input_binding") != binding
            or previous.get("config", {}).get("method") != args.method
            or previous.get("config", {}).get("block_days") != args.block_days
            or previous.get("config", {}).get("device") != device.type
            or previous.get("code", {}).get("executed_sources") != code["executed_sources"]
        ):
            raise ValueError("Single-model resume lineage/config/code differs")
        state = torch.load(resume_path, map_location="cpu", weights_only=True)
        runner = SingleBaselineRunner.from_state_dict(
            state, expected_binding=binding, device=device
        )
        if runner.next_index >= args.max_origins:
            raise ValueError("Resume horizon must extend the committed cursor")
        resumed_from = {"run_id": previous["run_id"], "checkpoint_sha256": resume_sha}
    output = _new_output(
        args.output,
        path,
        args.initial_checkpoint.parent
        if args.initial_checkpoint
        else args.source_checkpoint.parent,
        *([args.resume_checkpoint.parent] if args.resume_checkpoint else []),
    )
    output.mkdir(parents=True, exist_ok=False)
    replay = replay_target(
        path,
        manifest_sha256=args.manifest_sha256,
        entity_id=args.entity_id,
        runner=runner,
        max_origins=args.max_origins,
    )
    evaluation = _evaluate(runner, replay)
    checkpoint_sha = _save_state(output / "runner.pt", runner.state_dict())
    summary = {
        "schema": "hung-single-baseline-replay-v1",
        "status": "completed",
        "scope": "bounded Development single-model replay; no Final evaluation",
        "run_id": output.name,
        "input_binding": binding,
        "initial_checkpoint_sha256": initial_sha,
        "source_checkpoint_sha256": source_sha,
        "initial_run_id": initial_record.get("run_id"),
        "upstream_initialization_seconds": initial_record.get("initialization_seconds")
        if args.method == "target_only"
        else None,
        "reused_source_training_seconds": initial_record.get("duration_seconds")
        if args.method == "frozen_source"
        else None,
        "resumed_from": resumed_from,
        "config": config,
        **evaluation,
        "cost": runner.cost,
        "model_tensor_bytes": model_tensor_bytes(runner.model),
        "model_optimizer_tensor_bytes": model_optimizer_tensor_bytes(runner.model, runner.optimizer)
        if runner.optimizer is not None
        else model_tensor_bytes(runner.model),
        "cost_scope": "one-model inference/update timers; total duration includes validation, I/O and checkpointing; upstream training shown separately",
        "event_evidence": {"events": runner.events, "issued_count": len(runner.issued)},
        "runner_cursor": runner.next_index,
        "final_runner_checkpoint_sha256": checkpoint_sha,
        "duration_seconds": time.perf_counter() - started,
        "python": platform.python_version(),
        "torch": torch.__version__,
        "device": _device_record(device),
        "memory_usage": _process_memory(),
        "code": code,
    }
    _write_json(output / "run_manifest.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    initial = commands.add_parser("target-only-init")
    replay = commands.add_parser("replay-development")
    for command in (initial, replay):
        command.add_argument("--input-run", type=Path, required=True)
        command.add_argument("--manifest-sha256", required=True)
        command.add_argument("--entity-id", required=True)
        command.add_argument("--output", type=Path, required=True)
        command.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    initial.add_argument("--calendar-hidden", type=int, required=True)
    initial.add_argument("--seed", type=int, required=True)
    initial.add_argument("--learning-rate", type=float, required=True)
    initial.add_argument("--batch-size", type=int, required=True)
    initial.add_argument("--steps", type=int, required=True)
    replay.add_argument("--method", choices=("target_only", "frozen_source"), required=True)
    replay.add_argument("--initial-checkpoint", type=Path)
    replay.add_argument("--source-input-run", type=Path)
    replay.add_argument("--source-manifest-sha256")
    replay.add_argument("--source-checkpoint", type=Path)
    replay.add_argument("--resume-checkpoint", type=Path)
    replay.add_argument("--block-days", type=int, required=True)
    replay.add_argument("--max-origins", type=int, required=True)
    args = parser.parse_args(argv)
    result = _initialize_target_only(args) if args.command == "target-only-init" else _replay(args)
    print(json.dumps({key: result[key] for key in ("status", "run_id", "scope")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
