"""GPU replay core; the ordinary CLI remains restricted to Development inputs."""

import argparse
import json
import math
import os
import subprocess
import time
from dataclasses import asdict
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import torch

from ev_baselines.naive import SeasonalNaive
from ev_baselines.policies import Method, Policy
from ev_baselines.retention import ParameterBranch, parameter_epoch
from ev_control.confidence import ControllerConfig
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
            for folder in ("ev_models", "ev_control", "ev_runner", "ev_baselines")
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
    ensemble_sources: tuple[tuple[Path, str], ...] = (),
    prepared_replay: Replay | None = None,
) -> dict:
    config = json.loads(json.dumps(config, allow_nan=False))
    if device != "cuda" or not torch.cuda.is_available():
        raise ValueError(
            "Real Development replay requires CUDA/Colab; local tests use independent fixtures"
        )
    if set(config) - {"method", "state_retention"} != {
        "controller",
        "initial_training",
        "online_training",
        "development_entities",
        "replay_days",
    }:
        raise ValueError("Unknown runner configuration fields")
    if config.get("state_retention", "all") not in {"all", "latest"}:
        raise ValueError("Unknown state-retention policy")
    if entity_id not in config["development_entities"]:
        raise ValueError("Target not in declared Development smoke cohort")
    final_access = getattr(inputs, "final_access", None)
    if getattr(inputs, "target_role", "development") == "final":
        if final_access is None:
            raise ValueError("Final execution requires approved immutable lock access")
        final_access.check_run(inputs, entity_id, config, source_sha)
        if environment(device) != final_access.lock["runtime_profile"]:
            raise ValueError("Final runtime differs from measured locked profile")
        if digest(source) != source_sha:
            raise ValueError("Reused Final Source bytes changed")
        group = final_access.input_group(inputs, entity_id)
        if config.get("method", {}).get("name") == "uncertainty" and {
            checksum for _, checksum in ensemble_sources
        } != {item["sha256"] for item in group["sources"].values()}:
            raise ValueError("Final uncertainty must reuse exactly the three locked Sources")
    method = Method(**config.get("method", {"name": "adaptive"}))
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
    replay = prepared_replay or Replay(inputs, entity_id, config["replay_days"])
    if (
        replay.inputs is not inputs
        or replay.entity_id != entity_id
        or replay.stop != replay.start + config["replay_days"] * DAY
    ):
        raise ValueError("Prepared replay differs from this run's input/entity/horizon")
    seed_everything(initial_config.seed)
    started = time.perf_counter()
    needs_source = method.name not in {"target_only", "seasonal_naive"}
    source_model = reference = latent = None
    if needs_source:
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
    # Random target initializations use a seed independent of Source-loading side effects.
    seed_everything(initial_config.seed)
    model = (
        None
        if method.name == "seasonal_naive"
        else adapt_model(source_model)
        if method.source_initialization
        else ForecastGRU(ModelConfig(initial_config.head_width)).to(device)
    )
    optimizer = (
        torch.optim.Adam(model.parameters(), lr=initial_config.learning_rate)
        if model is not None
        else None
    )
    initial_records = inputs.training(inputs.target_role, entity_id)
    restore_initial = final_access is not None and resume_from is not None
    initial_logs = (
        json.loads((resume_from / "initial-adaptation.json").read_text()) if restore_initial else []
    )
    for epoch in range(initial_config.epochs):
        if (
            not restore_initial
            and initial_records
            and method.name not in {"seasonal_naive", "frozen_source"}
        ):
            initial_logs.append(
                (
                    parameter_epoch(
                        model,
                        optimizer,
                        initial_records,
                        initial_config,
                        epoch=epoch,
                        weight=controller.initial_lambda,
                        reference=reference,
                        device=device,
                    )
                    if method.name == "parameter_retention"
                    else train_epoch(
                        model,
                        optimizer,
                        initial_records,
                        initial_config,
                        epoch=epoch,
                        device=device,
                        reference=reference,
                        latent_scale=latent,
                        retention_weight=(
                            method.fixed_lambda
                            if method.name == "fixed_retention"
                            else controller.initial_lambda
                            if method.multiple
                            else 0.0
                        ),
                    )
                )
            )
    initial = (
        SeasonalNaive(initial_records)
        if method.name == "seasonal_naive"
        else (ParameterBranch if method.name == "parameter_retention" else Branch)(
            model, optimizer, rng_state()
        )
    )
    initial.steps = sum(x["steps"] for x in initial_logs)
    ensemble = []
    member_ids = []
    if method.name == "uncertainty":
        for path, checksum in ensemble_sources:
            member, _, value = load_checkpoint(path, sha256=checksum, device=device)
            member_meta = value["metadata"]
            if (
                member_meta["input_binding"]["stage"] != "source"
                or member_meta["source_population_sha256"] != inputs.source_hash
                or member.architecture() != reference.architecture()
            ):
                raise ValueError("Uncertainty member must share the allowed Source population")
            member_ids.append({"sha256": checksum, "seed": member_meta["training_config"]["seed"]})
            ensemble.append(frozen_reference(member))
        if len({m["seed"] for m in member_ids}) < 3 or len(
            {m["sha256"] for m in member_ids}
        ) != len(member_ids):
            raise ValueError("Uncertainty estimator requires >=3 distinct Source seeds/checkpoints")
    policy = Policy(
        method, reference, initial_records=initial_records, device=device, ensemble=tuple(ensemble)
    )
    code = runtime_code()
    binding = {
        "schema": "ev-prequential-run-v1",
        "input": inputs.binding("target", entity_id, source_sha),
        "config": config,
        "environment": environment(device),
        "code_files": code["files"],
        "source_population_sha256": inputs.source_hash,
        "latent_sha256": state_digest(latent) if latent is not None else None,
        "source_checkpoint_used": needs_source,
        "method": json.loads(json.dumps(asdict(method))),
        "uncertainty_members": member_ids,
    }
    if final_access is not None:
        binding["final_authorization"] = final_access.provenance()
        binding["initial_adaptation_identity"] = state_digest(initial_logs)
    store = Store(output, binding, resume_from=resume_from)
    if final_access is not None:
        # Separate durable initialization record permits resume before run.json exists.
        # The Store binding commits its semantic identity; resume never refits it.
        with (output / "initial-adaptation.json").open("xb") as stream:
            stream.write(json.dumps(initial_logs, allow_nan=False).encode())
            stream.flush()
            os.fsync(stream.fileno())
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
        policy=policy,
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
        s["mae_scaled"][runner.levels.index(s["issued_active"])] * replay.scale for s in scores
    ]
    report = {
        "scope": "Development technical replay only; unvalidated example policy, no Final or effectiveness claim",
        "run_id": output.name,
        "method": asdict(method),
        "candidate_levels": list(runner.levels),
        "baseline_state_summary": {
            str(k): {
                "steps": v.steps,
                "fallbacks": v.fallbacks if isinstance(v, SeasonalNaive) else None,
            }
            for k, v in runner.branches.items()
        },
        "code": code,
        "binding": binding,
        "source_checkpoint_sha256": source_sha,
        "initial_examples": len(initial_records),
        "initial_logs": initial_logs,
        "initialization": "seasonal_prefix_history"
        if method.name == "seasonal_naive"
        else "frozen_source_checkpoint"
        if method.name == "frozen_source"
        else "random_target_initial_adaptation"
        if not method.source_initialization and initial_records
        else "random_checkpoint_only"
        if not method.source_initialization
        else "target_initial_adaptation"
        if initial_records
        else "source_checkpoint_only",
        "scheduled_days": config["replay_days"],
        "issued_days": len(predictions),
        "scored_days": len(scores),
        "active_mae_kwh": sum(active_errors) / len(active_errors) if active_errors else None,
        "active_rmse_kwh": math.sqrt(
            sum(s["mse_scaled"][runner.levels.index(s["issued_active"])] for s in scores)
            / len(scores)
        )
        * replay.scale
        if scores
        else None,
        "policy_state": policy.snapshot(),
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
    if final_access is not None:
        report["scope"] = (
            "Locked Final replay; interpretation requires independent artifact verification"
        )
        report["initial_adaptation_reused"] = restore_initial
        report["elapsed_seconds_scope"] = (
            "Current invocation only; resumed state component counters are cumulative. "
            "Retain predecessor invocations separately; missing elapsed costs are unknown, not zero."
        )
    write_json(output / "run.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("inputs", "source", "config", "output", "resume-from"):
        parser.add_argument(f"--{key}", type=Path, required=key != "resume-from")
    for key in ("manifest-sha256", "source-sha256", "entity-id"):
        parser.add_argument(f"--{key}", required=True)
    parser.add_argument("--stop-after-ticks", type=int)
    parser.add_argument("--ensemble", type=Path)
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
        ensemble_sources=tuple(
            (Path(x["path"]), x["sha256"]) for x in json.loads(args.ensemble.read_text())
        )
        if args.ensemble
        else (),
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
