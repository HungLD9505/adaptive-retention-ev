"""GPU Development runner CLI; online policy/config is unvalidated until review."""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import torch

from ev_control.confidence import ControllerConfig
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
from ev_runner.engine import DAY, Runner
from ev_runner.replay import Replay
from ev_runner.state import Branch, rng_state, state_digest
from ev_runner.store import Store

ROOT = Path(__file__).resolve().parents[1]


def runtime_code() -> dict:
    return {
        "commit": subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip(),
        "dirty": bool(
            subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"], text=True)
        ),
        "files": {
            str(p.relative_to(ROOT)): digest(p)
            for folder in ("ev_models", "ev_control", "ev_runner")
            for p in sorted((ROOT / folder).glob("*.py"))
        },
    }


def execute(
    inputs: InputRun,
    entity_id: str,
    source: Path,
    source_sha: str,
    config: dict,
    output: Path,
    *,
    device: str,
    resume_from: Path | None = None,
    stop_after_ticks: int | None = None,
) -> dict:
    if device != "cuda" or not torch.cuda.is_available():
        raise ValueError(
            "Real Development replay requires CUDA/Colab; local tests use independent fixtures"
        )
    if set(config) != {
        "controller",
        "initial_training",
        "online_training",
        "development_entities",
        "replay_days",
    }:
        raise ValueError("Unknown runner configuration fields")
    if entity_id not in config["development_entities"]:
        raise ValueError("Target not in declared Development smoke cohort")
    controller = ControllerConfig(**config["controller"])
    initial_config = TrainingConfig(**config["initial_training"])
    online_config = TrainingConfig(**config["online_training"])
    if (
        any(
            getattr(initial_config, k) != getattr(online_config, k)
            for k in ("seed", "learning_rate", "epsilon", "head_width")
        )
        or controller.seed != online_config.seed
    ):
        raise ValueError("Seed/optimizer/architecture/retention profiles must agree")
    if output.resolve().is_relative_to(inputs.root.resolve()) or any(
        output.resolve().is_relative_to(ROOT / p)
        for p in ("data/raw", "data/processed", "data/inputs")
    ):
        raise ValueError("Output must be separate from immutable data")
    replay = Replay(inputs, entity_id, config["replay_days"])
    seed_everything(initial_config.seed)
    started = time.perf_counter()
    source_model, _, source_value = load_checkpoint(source, sha256=source_sha, device=device)
    meta = source_value["metadata"]
    if (
        meta["input_binding"]["stage"] != "source"
        or meta["source_population_sha256"] != inputs.source_hash
        or meta["training_config"]["seed"] != initial_config.seed
        or source_model.architecture()["head_width"] != initial_config.head_width
    ):
        raise ValueError("Source provenance/population/seed/architecture mismatch")
    latent = source_value["latent_scale"]
    if (
        latent is None
        or latent.shape != (64,)
        or not torch.isfinite(latent).all()
        or (latent < 0).any()
    ):
        raise ValueError("Missing/invalid fixed source-derived latent scale")
    reference = frozen_reference(source_model)
    model = adapt_model(source_model)
    optimizer = torch.optim.Adam(model.parameters(), lr=initial_config.learning_rate)
    initial_records = inputs.training("development", entity_id)
    initial_logs = []
    for epoch in range(initial_config.epochs):
        if initial_records:
            initial_logs.append(
                train_epoch(
                    model,
                    optimizer,
                    initial_records,
                    initial_config,
                    epoch=epoch,
                    device=device,
                    reference=reference,
                    latent_scale=latent,
                    retention_weight=controller.initial_lambda,
                )
            )
    initial = Branch(model, optimizer, rng_state())
    initial.steps = sum(x["steps"] for x in initial_logs)
    code = runtime_code()
    binding = {
        "schema": "ev-prequential-run-v1",
        "input": inputs.binding("target", entity_id, source_sha),
        "config": config,
        "environment": environment(device),
        "code_files": code["files"],
        "source_population_sha256": inputs.source_hash,
        "latent_sha256": state_digest(latent),
    }
    store = Store(output, binding, resume_from=resume_from)
    runner = Runner(
        replay,
        initial,
        reference,
        latent,
        controller,
        online_config,
        store,
        device=device,
        stream_id=f"{inputs.namespace}/{entity_id}/{inputs.config['history_days']}d/seed{initial_config.seed}",
    )
    if stop_after_ticks is not None and stop_after_ticks < 1:
        raise ValueError("stop_after_ticks must be positive")
    # Daily midnight polling: continue long enough for declared delay plus final horizon.
    end = replay.stop + (int(replay.delay.total_seconds() // DAY.total_seconds()) + 1) * DAY
    if stop_after_ticks:
        end = min(end, runner.next_at + (stop_after_ticks - 1) * DAY)
    runner.run_until(end)
    predictions = []
    scores = []
    audits = []
    for tick in sorted(output.glob("tick-*")):
        forecast = json.loads((tick / "forecasts.json").read_bytes())
        if forecast:
            predictions.append(
                {
                    "origin": forecast["origin"],
                    "active": forecast["active"],
                    "predictions": forecast["predictions"],
                    "prediction_ids": forecast["prediction_ids"],
                }
            )
        for line in (tick / "events.jsonl").read_text().splitlines():
            event = json.loads(line)
            if event["event"] == "score":
                scores.append(event)
            if event["event"] == "audit_summary":
                audits.append(event)
    active_errors = [
        s["mae_scaled"][controller.levels.index(s["issued_active"])] * replay.scale for s in scores
    ]
    report = {
        "scope": "Development technical replay only; unvalidated example policy, no Final or effectiveness claim",
        "run_id": output.name,
        "code": code,
        "binding": binding,
        "source_checkpoint_sha256": source_sha,
        "initial_examples": len(initial_records),
        "initial_logs": initial_logs,
        "initialization": "target_initial_adaptation"
        if initial_records
        else "source_checkpoint_only",
        "scheduled_days": config["replay_days"],
        "issued_days": len(predictions),
        "scored_days": len(scores),
        "active_mae_kwh": sum(active_errors) / len(active_errors) if active_errors else None,
        "decisions": runner.decisions,
        "audits": audits,
        "candidate_steps": runner.steps,
        "audit_steps": runner.audit_steps,
        "cost": runner.cost,
        "elapsed_seconds": time.perf_counter() - started,
        "gpu_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
        "gpu_peak_reserved_bytes": torch.cuda.max_memory_reserved(),
        "pending_days": len(runner.pending),
        "ticks": store.count,
        "commit_chain": store.previous,
        "prediction_identity_sha256": __import__("hashlib")
        .sha256(json.dumps(predictions, sort_keys=True).encode())
        .hexdigest(),
        "final_branch_state_sha256": {
            str(k): state_digest(v.snapshot()) for k, v in runner.branches.items()
        },
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
    parser.add_argument("--stop-after-ticks", type=int)
    args = parser.parse_args()
    report = execute(
        InputRun(args.inputs, args.manifest_sha256),
        args.entity_id,
        args.source,
        args.source_sha256,
        json.loads(args.config.read_text()),
        args.output,
        device="cuda",
        resume_from=args.resume_from,
        stop_after_ticks=args.stop_after_ticks,
    )
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "run_id",
                    "issued_days",
                    "scored_days",
                    "candidate_steps",
                    "audit_steps",
                    "elapsed_seconds",
                    "pending_days",
                )
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
