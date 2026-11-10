"""Versioned #99 Fixed/continuous Development replay; no scored search dispatcher."""

import argparse
import json
import math
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

import torch

from ev_control.continuous import WindowRule
from ev_models.checkpoint import digest, load_checkpoint, write_json
from ev_models.data import InputRun
from ev_models.model import ForecastGRU, ModelConfig
from ev_models.run import environment
from ev_models.training import (
    TrainingConfig,
    adapt_model,
    frozen_reference,
    seed_everything,
    train_epoch,
)
from ev_runner.continuous import DAY, ContinuousRunner
from ev_runner.replay import Replay
from ev_runner.state import Branch, rng_state, state_digest
from ev_runner.store import Store

ROOT = Path(__file__).resolve().parents[1]


def validate_origin_boundary(
    protocol: dict, entity_id: str, start: datetime, stop: datetime
) -> list[str]:
    """Require chronological disjoint scored windows with an explicit embargo."""
    embargo = protocol.get("embargo_days")
    if isinstance(embargo, bool) or not isinstance(embargo, int) or embargo < 0:
        raise ValueError("Protocol needs nonnegative integer embargo_days")
    checked = {}
    for name in ("calibration_origins", "evaluation_origins"):
        rows = protocol[name][entity_id]
        if (
            not isinstance(rows, list)
            or not rows
            or len(rows) != len(set(rows))
            or rows != sorted(rows)
        ):
            raise ValueError(f"Invalid chronological {name}")
        stamps = [datetime.fromisoformat(origin) for origin in rows]
        if any(not start <= stamp < stop for stamp in stamps):
            raise ValueError(f"{name} outside replay calendar")
        checked[name] = stamps
    if (
        checked["calibration_origins"][-1] + timedelta(days=1 + embargo)
        > checked["evaluation_origins"][0]
    ):
        raise ValueError("Evaluation must follow calibration horizon and embargo")
    return protocol["calibration_origins"][entity_id]


def objective_summary(scores: list[dict], origins: list[str], minimum_scored: int | None) -> dict:
    """Keep partial or low-coverage objectives null under the registered gate."""
    selected = set(origins)
    objective = [row for row in scores if row["origin"] in selected]
    if len({row["origin"] for row in objective}) != len(objective):
        raise ValueError("Duplicate scored objective origin")
    valid = minimum_scored is not None and len(objective) >= minimum_scored
    return {
        "objective_requested_days": len(origins),
        "objective_scored_days": len(objective),
        "objective_minimum_scored_days": minimum_scored,
        "objective_missing_origins": sorted(selected - {row["origin"] for row in objective}),
        "objective_coverage_pass": valid,
        "mae_kwh": sum(row["mae_kwh"] for row in objective) / len(objective) if valid else None,
        "rmse_kwh": math.sqrt(sum(row["mse_kwh2"] for row in objective) / len(objective))
        if valid
        else None,
    }


def validate_study(
    config: dict, *, approved_targets: tuple[str, ...] = ("1405", "2152", "1153", "1693")
) -> tuple[TrainingConfig, TrainingConfig, WindowRule]:
    required = {
        "schema",
        "phase",
        "targets",
        "initial_training",
        "online_training",
        "window_rule",
        "initial_lambda",
        "cadence",
        "frozen_lambda",
        "replay_days",
        "protocol_sha256",
        "objective_origins",
    }
    if (
        set(config) - {"state_retention", "diagnostic_every"} != required
        or config["schema"] != "issue99-study-v1"
    ):
        raise ValueError("Invalid issue #99 study config")
    if config.get("state_retention", "all") not in {"all", "latest"}:
        raise ValueError("Invalid state retention")
    diagnostic_every = config.get("diagnostic_every", 0)
    if (
        isinstance(diagnostic_every, bool)
        or not isinstance(diagnostic_every, int)
        or diagnostic_every < 0
    ):
        raise ValueError("Invalid diagnostic cadence")
    if config["phase"] not in {"pilot", "calibration", "evaluation"}:
        raise ValueError("Unknown study phase")
    if config["phase"] != "pilot" and not config["protocol_sha256"]:
        raise ValueError("Scored execution needs reviewed protocol hash")
    if config["phase"] == "pilot" and config["objective_origins"]:
        raise ValueError("Pilot cannot declare a scored objective")
    if not isinstance(config["objective_origins"], list) or any(
        not isinstance(origin, str) for origin in config["objective_origins"]
    ):
        raise ValueError("Invalid objective origins")
    if config["phase"] != "pilot" and not config["objective_origins"]:
        raise ValueError("Scored phase needs declared objective origins")
    if (
        not approved_targets
        or len(set(approved_targets)) != len(approved_targets)
        or config["targets"] != list(approved_targets)
    ):
        raise ValueError("Issue #99 targets differ from the explicit approved cohort")
    if config["replay_days"] != 90 or not isinstance(config["frozen_lambda"], bool):
        raise ValueError("Issue #99 requires 90-day replay and explicit frozen flag")
    if (
        isinstance(config["cadence"], bool)
        or not isinstance(config["cadence"], int)
        or config["cadence"] < 1
    ):
        raise ValueError("Invalid cadence")
    initial = TrainingConfig(**config["initial_training"])
    online = TrainingConfig(**config["online_training"])
    rule = WindowRule(**config["window_rule"])
    if initial.seed not in (42, 43, 44) or online.seed != initial.seed:
        raise ValueError("Source10 paired seed mismatch")
    if any(
        getattr(initial, name) != getattr(online, name)
        for name in ("learning_rate", "epsilon", "head_width")
    ):
        raise ValueError("Initial/online model and optimizer profiles differ")
    weight = config["initial_lambda"]
    if (
        isinstance(weight, bool)
        or not isinstance(weight, (int, float))
        or not math.isfinite(weight)
        or not 0 <= weight <= rule.upper_bound
    ):
        raise ValueError("Invalid initial lambda")
    return initial, online, rule


def code_identity() -> dict:
    marker = ROOT / ".issue99-code-commit"
    if marker.exists():
        commit = marker.read_text(encoding="ascii").strip()
        if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
            raise ValueError("Invalid verified package commit marker")
    else:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    paths = [
        path.relative_to(ROOT).as_posix()
        for folder in ("ev_inputs", "ev_models", "ev_control", "ev_runner")
        for path in sorted((ROOT / folder).glob("*.py"))
    ]
    return {
        "commit": commit,
        "files": {name: digest(ROOT / name) for name in paths},
    }


def execute(
    inputs: InputRun,
    entity_id: str,
    source_path: Path,
    source_sha256: str,
    config: dict,
    output: Path,
    *,
    device: str,
    resume_from: Path | None = None,
    stop_after_ticks: int | None = None,
    protocol_path: Path | None = None,
    prepared_replay: Replay | None = None,
    approved_targets: tuple[str, ...] = ("1405", "2152", "1153", "1693"),
    source_initialization: bool = True,
    approved_history_days: tuple[int, ...] = (14,),
) -> dict:
    invocation_started = time.perf_counter()
    initial, online, rule = validate_study(config, approved_targets=approved_targets)
    if not source_initialization and (config["initial_lambda"] != 0 or not config["frozen_lambda"]):
        raise ValueError("Random target initialization requires fixed zero retention")
    if (
        entity_id not in config["targets"]
        or inputs.config["history_days"] not in approved_history_days
        or inputs.target_role != "development"
    ):
        raise ValueError("Wrong Development target or history budget")
    if device not in ("cpu", "cuda") or (device == "cuda" and not torch.cuda.is_available()):
        raise ValueError("Requested device unavailable")
    if output.resolve().is_relative_to(inputs.root.resolve()):
        raise ValueError("Output cannot be within immutable input")
    if config["phase"] != "pilot":
        if protocol_path is None or digest(protocol_path) != config["protocol_sha256"]:
            raise ValueError("Missing or changed reviewed protocol")
        protocol = json.loads(protocol_path.read_text())
        if protocol.get("status") != "locked_owner_approved" or not protocol.get(
            "owner_authorization"
        ):
            raise ValueError("Scored execution requires recorded owner authorization")
        calibration = validate_origin_boundary(
            protocol,
            entity_id,
            inputs.deployment,
            inputs.deployment + config["replay_days"] * DAY,
        )
        evaluation = protocol["evaluation_origins"][entity_id]
        selected = calibration if config["phase"] == "calibration" else evaluation
        if config["objective_origins"] != selected:
            raise ValueError("Objective origins differ from reviewed protocol")
        minimum_scored = protocol["minimum_scored_days"][config["phase"]][entity_id]
        if (
            isinstance(minimum_scored, bool)
            or not isinstance(minimum_scored, int)
            or not 1 <= minimum_scored <= len(selected)
        ):
            raise ValueError("Invalid registered objective coverage minimum")
        if stop_after_ticks is not None:
            raise ValueError("Scored phase cannot stop before its declared horizon")
    else:
        minimum_scored = None
    source_load_started = time.perf_counter()
    source, _, source_value = load_checkpoint(source_path, sha256=source_sha256, device=device)
    source_load_wall_seconds = time.perf_counter() - source_load_started
    meta = source_value["metadata"]
    if (
        meta["input_binding"]["stage"] != "source"
        or meta["source_population_sha256"] != inputs.source_hash
        or meta["training_config"]["seed"] != initial.seed
        or source_value["completed_epochs"] != 10
        or source.architecture()["head_width"] != initial.head_width
    ):
        raise ValueError("Source10 checkpoint incompatible with target input/config")
    latent = source_value["latent_scale"]
    if (
        latent is None
        or latent.shape != (64,)
        or not torch.isfinite(latent).all()
        or (latent < 0).any()
    ):
        raise ValueError("Invalid source-derived latent scale")
    replay_load_started = time.perf_counter()
    replay = prepared_replay or Replay(inputs, entity_id, config["replay_days"])
    if (
        replay.inputs is not inputs
        or replay.entity_id != entity_id
        or replay.stop != replay.start + config["replay_days"] * DAY
    ):
        raise ValueError("Prepared replay differs from input/entity/horizon")
    replay_load_wall_seconds = time.perf_counter() - replay_load_started
    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    seed_everything(initial.seed)
    target = (
        adapt_model(source)
        if source_initialization
        else ForecastGRU(ModelConfig(initial.head_width)).to(device)
    )
    reference = frozen_reference(source)
    optimizer = torch.optim.Adam(target.parameters(), lr=initial.learning_rate)
    prefix_load_started = time.perf_counter()
    prefix = inputs.training("development", entity_id)
    prefix_load_wall_seconds = time.perf_counter() - prefix_load_started
    initial_logs = []
    if device == "cuda":
        torch.cuda.synchronize()
    initial_started = time.perf_counter()
    if resume_from is None:
        for epoch in range(initial.epochs):
            initial_logs.append(
                train_epoch(
                    target,
                    optimizer,
                    prefix,
                    initial,
                    epoch=epoch,
                    device=device,
                    reference=reference,
                    latent_scale=latent,
                    retention_weight=config["initial_lambda"],
                )
            )
    else:
        initial_logs = json.loads((resume_from / "initial-adaptation.json").read_text())
    if device == "cuda":
        torch.cuda.synchronize()
    initial_wall_seconds = time.perf_counter() - initial_started if resume_from is None else None
    binding = {
        "schema": "issue99-run-binding-v1",
        "input": inputs.binding("target", entity_id, source_sha256),
        "source_population_sha256": inputs.source_hash,
        "latent_sha256": state_digest(latent),
        "config": config,
        "environment": environment(device),
        "code": code_identity(),
        "initial_adaptation_sha256": state_digest(initial_logs),
    }
    if not source_initialization:
        binding["source_initialization"] = False
        binding["source_weights_used_for_training"] = False
    store = Store(output, binding, resume_from=resume_from)
    with (output / "initial-adaptation.json").open("xb") as stream:
        stream.write(json.dumps(initial_logs, allow_nan=False).encode())
        stream.flush()
        os.fsync(stream.fileno())
    branch = Branch(target, optimizer, rng_state())
    branch.steps = sum(row["steps"] for row in initial_logs)
    runner = ContinuousRunner(
        replay,
        branch,
        reference,
        latent,
        rule,
        online,
        store,
        initial_lambda=config["initial_lambda"],
        device=device,
        cadence=config["cadence"],
        frozen_lambda=config["frozen_lambda"],
    )
    if stop_after_ticks is not None and stop_after_ticks < 1:
        raise ValueError("stop_after_ticks must be positive")
    end = replay.stop + (int(replay.delay.total_seconds() // DAY.total_seconds()) + 1) * DAY
    if config["phase"] == "calibration":
        end = min(
            end,
            max(datetime.fromisoformat(origin) for origin in config["objective_origins"])
            + DAY
            + replay.delay,
        )
    if stop_after_ticks:
        end = min(end, runner.next_at + (stop_after_ticks - 1) * DAY)
    runner.run_until(end)
    scores = []
    issued = 0
    decisions = 0
    for tick in sorted(output.glob("tick-*")):
        if json.loads((tick / "forecasts.json").read_text()):
            issued += 1
        for line in (tick / "events.jsonl").read_text().splitlines():
            event = json.loads(line)
            if event["event"] == "score":
                scores.append(event)
            elif event["event"] == "meta_decision":
                decisions += 1
    objective = objective_summary(scores, config["objective_origins"], minimum_scored)
    report = {
        "schema": "issue99-run-v1",
        "run_id": output.name,
        "phase": config["phase"],
        "method": "target_only"
        if not source_initialization
        else "fixed_real_lambda"
        if config["frozen_lambda"]
        else "continuous_one_step_adam",
        "binding": binding,
        "initial_logs": initial_logs,
        "initial_wall_seconds_this_invocation": initial_wall_seconds,
        "source_load_wall_seconds_this_invocation": source_load_wall_seconds,
        "replay_load_wall_seconds_this_invocation": replay_load_wall_seconds,
        "prefix_load_wall_seconds_this_invocation": prefix_load_wall_seconds,
        "scheduled_days": 90,
        "issued_days": issued,
        "scored_days": len(scores),
        **objective,
        "actual_steps": runner.actual_steps,
        "virtual_steps": runner.virtual_steps,
        "controller_decisions": decisions,
        "final_lambda": runner.current_lambda,
        "pending_days": len(runner.pending),
        "cost_seconds": runner.cost,
        "invocation_wall_seconds": time.perf_counter() - invocation_started,
        "gpu_peak_allocated_bytes": torch.cuda.max_memory_allocated() if device == "cuda" else None,
        "gpu_peak_reserved_bytes": torch.cuda.max_memory_reserved() if device == "cuda" else None,
        "commit_chain": store.previous,
        "final_state_sha256": state_digest(runner.branch.snapshot()),
        "resume_from": str(resume_from) if resume_from else None,
    }
    write_json(output / "run.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("inputs", "source", "config", "output", "resume-from"):
        parser.add_argument(f"--{key}", type=Path, required=key != "resume-from")
    for key in ("manifest-sha256", "source-sha256", "entity-id"):
        parser.add_argument(f"--{key}", required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--stop-after-ticks", type=int)
    parser.add_argument("--protocol", type=Path)
    args = parser.parse_args()
    result = execute(
        InputRun(args.inputs, args.manifest_sha256),
        args.entity_id,
        args.source,
        args.source_sha256,
        json.loads(args.config.read_text()),
        args.output,
        device=args.device,
        resume_from=args.resume_from,
        stop_after_ticks=args.stop_after_ticks,
        protocol_path=args.protocol,
    )
    print(
        json.dumps(
            {key: result[key] for key in ("run_id", "issued_days", "scored_days", "mae_kwh")}
        )
    )


if __name__ == "__main__":
    main()
