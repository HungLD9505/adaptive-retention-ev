"""Versioned #99 Fixed/continuous Development replay; no scored search dispatcher."""

import argparse
import json
import math
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

import torch

from ev_control.continuous import WindowRule
from ev_models.checkpoint import digest, load_checkpoint, write_json
from ev_models.data import InputRun
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


def validate_study(config: dict) -> tuple[TrainingConfig, TrainingConfig, WindowRule]:
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
    if set(config) != required or config["schema"] != "issue99-study-v1":
        raise ValueError("Invalid issue #99 study config")
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
    if config["targets"] != ["1405", "2152", "1153", "1693"]:
        raise ValueError("Issue #99 uses the declared four targets")
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
    paths = [
        path.relative_to(ROOT).as_posix()
        for folder in ("ev_inputs", "ev_models", "ev_control", "ev_runner")
        for path in sorted((ROOT / folder).glob("*.py"))
    ]
    return {
        "commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
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
) -> dict:
    initial, online, rule = validate_study(config)
    if entity_id not in config["targets"] or inputs.config["history_days"] != 14:
        raise ValueError("Wrong Development target or history budget")
    if device not in ("cpu", "cuda") or (device == "cuda" and not torch.cuda.is_available()):
        raise ValueError("Requested device unavailable")
    if output.resolve().is_relative_to(inputs.root.resolve()):
        raise ValueError("Output cannot be within immutable input")
    if config["phase"] != "pilot":
        if protocol_path is None or digest(protocol_path) != config["protocol_sha256"]:
            raise ValueError("Missing or changed reviewed protocol")
        protocol = json.loads(protocol_path.read_text())
        if protocol.get("status") != "locked_reviewed" or not protocol.get("review"):
            raise ValueError("Scored execution requires recorded peer review")
        calibration = protocol["calibration_origins"][entity_id]
        evaluation = protocol["evaluation_origins"][entity_id]
        if set(calibration) & set(evaluation) or not calibration or not evaluation:
            raise ValueError("Calibration/evaluation origins overlap or are empty")
        selected = calibration if config["phase"] == "calibration" else evaluation
        if config["objective_origins"] != selected:
            raise ValueError("Objective origins differ from reviewed protocol")
    source, _, source_value = load_checkpoint(source_path, sha256=source_sha256, device=device)
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
    replay = Replay(inputs, entity_id, config["replay_days"])
    seed_everything(initial.seed)
    target = adapt_model(source)
    reference = frozen_reference(source)
    optimizer = torch.optim.Adam(target.parameters(), lr=initial.learning_rate)
    prefix = inputs.training("development", entity_id)
    initial_logs = []
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
    started = time.perf_counter()
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
    objective = (
        [row for row in scores if row["origin"] in config["objective_origins"]]
        if config["phase"] != "pilot"
        else []
    )
    report = {
        "schema": "issue99-run-v1",
        "run_id": output.name,
        "phase": config["phase"],
        "method": "fixed_real_lambda" if config["frozen_lambda"] else "continuous_one_step_adam",
        "binding": binding,
        "initial_logs": initial_logs,
        "scheduled_days": 90,
        "issued_days": issued,
        "scored_days": len(scores),
        "objective_requested_days": len(config["objective_origins"]),
        "objective_scored_days": len(objective),
        "mae_kwh": sum(row["mae_kwh"] for row in objective) / len(objective) if objective else None,
        "rmse_kwh": math.sqrt(sum(row["mse_kwh2"] for row in objective) / len(objective))
        if objective
        else None,
        "actual_steps": runner.actual_steps,
        "virtual_steps": runner.virtual_steps,
        "controller_decisions": decisions,
        "final_lambda": runner.current_lambda,
        "pending_days": len(runner.pending),
        "cost_seconds": runner.cost,
        "invocation_wall_seconds": time.perf_counter() - started,
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
