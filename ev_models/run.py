"""Issue #19 source/adaptation CLI; no controller, online updates or Final evaluation."""

import argparse
import json
import math
import os
import platform
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import torch

from ev_inputs.windows import LabelRecord, ready_labels
from ev_models.checkpoint import digest, load_checkpoint, save_checkpoint, write_json
from ev_models.data import InputRun
from ev_models.model import ForecastGRU, ModelConfig
from ev_models.training import (
    TrainingConfig,
    adapt_model,
    frozen_reference,
    seed_everything,
    source_latent_scale,
    train_epoch,
)

ROOT = Path(__file__).resolve().parents[1]


def code_identity() -> dict:
    """Record the executed implementation, not other people's experiment branches."""
    return {
        "commit": subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip(),
        "dirty": bool(
            subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"], text=True)
        ),
        "files": {
            p.relative_to(ROOT).as_posix(): digest(p)
            for p in sorted((ROOT / "ev_models").glob("*.py"))
        },
    }


def environment(device: str) -> dict:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": str(torch.__version__),
        "cuda": torch.version.cuda,
        "device": device,
        "device_name": torch.cuda.get_device_name(0) if device == "cuda" else "CPU",
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
    }


def validate_config(config: dict) -> TrainingConfig:
    if set(config) != {"training", "lambda", "development_entities", "evaluation_origins"}:
        raise ValueError("Unknown/missing experiment config fields")
    weight = config["lambda"]
    if (
        isinstance(weight, bool)
        or not isinstance(weight, (int, float))
        or not math.isfinite(weight)
        or weight < 0
    ):
        raise ValueError("lambda must be finite nonnegative")
    ids = config["development_entities"]
    if (
        not isinstance(ids, list)
        or not ids
        or len(set(ids)) != len(ids)
        or any(not isinstance(x, str) or not x for x in ids)
    ):
        raise ValueError("Explicit unique Development target IDs required")
    limit = config["evaluation_origins"]
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("Positive forecast-origin count required")
    return TrainingConfig(**config["training"])


def evaluate(
    model: ForecastGRU,
    inputs: InputRun,
    entity_id: str,
    out: Path,
    *,
    device: str,
    origin_count: int,
) -> dict:
    """Static post-adaptation smoke: write predictions BEFORE opening future labels.

    Evaluate a predeclared interval from deployment, not first N complete labels.
    This is not the chronological updating runner required by #21.
    """
    predictions = {}
    stop = inputs.deployment + timedelta(days=origin_count)
    with (out / "predictions.jsonl").open("x", encoding="utf-8") as stream:
        model.eval()
        with torch.no_grad():
            for rec in inputs.replay_forecasts(entity_id):
                if rec["role"] != "development" or rec["identity"][2] != entity_id:
                    continue
                origin = datetime.fromisoformat(rec["origin"])
                if origin >= stop:
                    continue
                rec = inputs.validate_forecast(rec, role="development", before_deployment=False)
                x = torch.tensor([rec["x_hist"]], dtype=torch.float32, device=device)
                c = torch.tensor([rec["c_future"]], dtype=torch.float32, device=device)
                y = (model(x, c)[0] * rec["energy_scale"]).cpu().tolist()
                if any(not math.isfinite(v) for v in y):
                    raise ValueError("Nonfinite prediction")
                if rec["origin"] in predictions:
                    raise ValueError("Duplicate forecast")
                predictions[rec["origin"]] = y
                stream.write(
                    json.dumps(
                        {
                            "identity": rec["identity"],
                            "origin": rec["origin"],
                            "prediction_kwh": y,
                            "scale_id": rec["scale_id"],
                            "as_of": rec["origin"],
                        }
                    )
                    + "\n"
                )
    # The predictor file is closed and hashed before the scoring path sees Y.
    prediction_sha256 = digest(out / "predictions.jsonl")
    scores = []
    seen = set()
    for rec in inputs.evaluation_labels(entity_id, set(predictions)):
        if (
            tuple(rec["identity"]) != (*inputs.namespace, entity_id)
            or rec["origin"] not in predictions
        ):
            continue
        if rec["origin"] in seen:
            raise ValueError("Duplicate label")
        seen.add(rec["origin"])
        origin = datetime.fromisoformat(rec["origin"])
        record = LabelRecord(
            tuple(rec["identity"]),
            origin,
            rec["clock_mode"],
            tuple(datetime.fromisoformat(t) for t in rec["timestamps"]),
            tuple(rec["energy_kwh"]),
            tuple(rec["file_valid"]),
            tuple(datetime.fromisoformat(t) if t else None for t in rec["available_at"]),
        )
        as_of = origin + timedelta(hours=24 + inputs.config["availability_delay_hours"])
        values = ready_labels(record, as_of=as_of)
        if values is not None:
            errors = [p - y for p, y in zip(predictions[rec["origin"]], values, strict=True)]
            scores.append(
                {
                    "origin": rec["origin"],
                    "mae_kwh": sum(abs(v) for v in errors) / 24,
                    "mse_kwh2": sum(v * v for v in errors) / 24,
                }
            )
    metrics = {
        "scope": "fixed-checkpoint Development smoke; no online updates; no effectiveness claim",
        "requested_origins": origin_count,
        "emitted_forecasts": len(predictions),
        "scored_complete_days": len(scores),
        "unscored_forecasts": len(predictions) - len(scores),
        "mae_kwh": sum(s["mae_kwh"] for s in scores) / len(scores) if scores else None,
        "rmse_kwh": math.sqrt(sum(s["mse_kwh2"] for s in scores) / len(scores)) if scores else None,
        "prediction_sha256_before_label_read": prediction_sha256,
        "daily": scores,
    }
    write_json(out / "metrics.json", metrics)
    return metrics


def execute(
    stage: str,
    inputs: InputRun,
    config: dict,
    output: Path,
    *,
    device: str,
    source_path: Path | None = None,
    source_sha256: str | None = None,
    entity_id: str | None = None,
    resume: Path | None = None,
    resume_sha256: str | None = None,
) -> dict:
    training = validate_config(config)
    if stage not in ("source", "target") or (stage == "source" and config["lambda"] != 0):
        raise ValueError("Source uses MAE only; unsupported stage")
    if device not in ("cpu", "cuda") or (device == "cuda" and not torch.cuda.is_available()):
        raise ValueError("Requested device unavailable")
    seed_everything(training.seed)
    started = time.perf_counter()
    reference = latent_scale = None
    if stage == "source":
        records = inputs.training("source")
        model = ForecastGRU(ModelConfig(training.head_width)).to(device)
        binding = inputs.binding("source")
    else:
        if (
            entity_id not in config["development_entities"]
            or source_path is None
            or not source_sha256
        ):
            raise ValueError(
                "Explicit source checkpoint and configured Development target required"
            )
        source, _, source_value = load_checkpoint(source_path, sha256=source_sha256, device=device)
        source_meta = source_value["metadata"]
        if (
            source_meta["input_binding"]["stage"] != "source"
            or source_meta["source_population_sha256"] != inputs.source_hash
            or source_meta["training_config"]["seed"] != training.seed
            or source.architecture()["head_width"] != training.head_width
        ):
            raise ValueError("Source checkpoint population/profile/seed/architecture incompatible")
        records = inputs.training("development", entity_id)
        model = adapt_model(source)
        reference = frozen_reference(source)
        latent_scale = source_value["latent_scale"]
        if latent_scale is None:
            raise ValueError("Missing source-derived latent scale")
        binding = inputs.binding("target", entity_id, source_sha256)
    if stage == "source" and not records:
        raise ValueError("Source pool is empty")
    optimizer = torch.optim.Adam(model.parameters(), lr=training.learning_rate)
    metadata = {
        "input_binding": binding,
        "source_population_sha256": inputs.source_hash,
        "training_config": training.as_dict(),
        "experiment_config": config,
        "latent_scale_definition": "population std ddof=0 of final source encoder on every source training example",
        "code": code_identity(),
        "environment": environment(device),
    }
    start_epoch = 0
    if resume:
        model, optimizer, restored = load_checkpoint(
            resume, sha256=resume_sha256, device=device, restore_rng=True
        )
        previous = restored["metadata"]
        if any(
            previous[k] != metadata[k]
            for k in (
                "input_binding",
                "training_config",
                "experiment_config",
                "source_population_sha256",
            )
        ):
            raise ValueError("Resume binding/config differs")
        if (
            previous["code"]["files"] != metadata["code"]["files"]
            or previous["environment"] != metadata["environment"]
        ):
            raise ValueError("Exact resume requires matching code and runtime environment")
        start_epoch = restored["completed_epochs"]
        latent_scale = restored["latent_scale"]
        if start_epoch > training.epochs:
            raise ValueError("Resume checkpoint exceeds planned epochs")
    output = output.resolve()
    if any(
        output.is_relative_to(ROOT / p) for p in ("data/raw", "data/inputs", "data/processed")
    ) or output.is_relative_to(inputs.root.resolve()):
        raise ValueError("Run output must be separate from immutable data")
    output.mkdir(parents=True, exist_ok=False)
    metadata["run_id"] = output.name
    metadata["started_at_utc"] = datetime.now(timezone.utc).isoformat()
    metadata["resume_checkpoint_sha256"] = resume_sha256 if resume else None
    write_json(output / "config.json", config)
    logs = []
    try:
        for epoch in range(start_epoch, training.epochs):
            if records:
                log = train_epoch(
                    model,
                    optimizer,
                    records,
                    training,
                    epoch=epoch,
                    device=device,
                    reference=reference,
                    latent_scale=latent_scale,
                    retention_weight=config["lambda"],
                )
                logs.append(log)
                print(json.dumps({"run": output.name, **log}), flush=True)
            if stage == "source":
                latent_scale = source_latent_scale(
                    model, records, batch_size=training.batch_size, device=device
                )
            save_checkpoint(
                output / f"epoch-{epoch + 1}.pt",
                model,
                optimizer,
                metadata=metadata,
                latent_scale=latent_scale,
                completed_epochs=epoch + 1,
            )
        # Even a completed resume or a zero-example target gets a bound final checkpoint.
        final_sha = save_checkpoint(
            output / "final.pt",
            model,
            optimizer,
            metadata=metadata,
            latent_scale=latent_scale,
            completed_epochs=training.epochs,
        )
        reloaded, _, _ = load_checkpoint(output / "final.pt", sha256=final_sha, device=device)
        if any(not torch.equal(p, reloaded.state_dict()[k]) for k, p in model.state_dict().items()):
            raise ValueError("Checkpoint reload differs")
        metrics = (
            evaluate(
                reloaded,
                inputs,
                entity_id,
                output,
                device=device,
                origin_count=config["evaluation_origins"],
            )
            if stage == "target"
            else None
        )
        report = {
            **metadata,
            "status": "technical_success",
            "training_examples": len(records),
            "initialization": "source_training"
            if stage == "source"
            else "target_initial_adaptation"
            if records
            else "source_checkpoint_only",
            "logs": logs,
            "metrics": metrics,
            "checkpoint_sha256": final_sha,
            "elapsed_seconds": time.perf_counter() - started,
            "peak_cuda_memory_bytes": torch.cuda.max_memory_allocated()
            if device == "cuda"
            else None,
            "acceptance_scope": "Issue19 Development only; no controller or online-runner acceptance",
        }
        write_json(output / "run.json", report)
        return report
    except Exception as error:
        write_json(output / "failure.json", {"error": str(error), "metadata": metadata})
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("source", "target"))
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--source-sha256")
    parser.add_argument("--entity-id")
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--resume-sha256")
    args = parser.parse_args()
    try:
        result = execute(
            args.stage,
            InputRun(args.inputs, args.manifest_sha256),
            json.loads(args.config.read_text(encoding="utf-8")),
            args.output,
            device=args.device,
            source_path=args.source,
            source_sha256=args.source_sha256,
            entity_id=args.entity_id,
            resume=args.resume,
            resume_sha256=args.resume_sha256,
        )
        print(
            json.dumps(
                {"status": result["status"], "checkpoint_sha256": result["checkpoint_sha256"]}
            )
        )
        return 0
    except (ValueError, KeyError, OSError, RuntimeError) as error:
        parser.exit(1, f"Issue19 run failed: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
