"""Bounded initial-adaptation study, followed by fixed-model Development evaluation."""

import argparse
import copy
import json
import platform
import subprocess
import time
from datetime import datetime
from pathlib import Path

import torch

from .data import (
    arrived,
    rows,
    select_entities,
    sha256,
    source_signature,
    tensors,
    training_rows,
    verified_manifest,
)
from .model import Forecaster, frozen_reference, objective


def write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)


def fit(
    model: Forecaster,
    examples: list,
    config: dict,
    epochs: int,
    reference: Forecaster | None = None,
    std: torch.Tensor | None = None,
    weight: float = 0.0,
) -> tuple[dict, list]:
    optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"])
    trace = []
    if not examples:
        return optimizer.state_dict(), trace
    x, c, y = tensors(examples)
    generator = torch.Generator().manual_seed(config["seed"])
    model.train()
    for epoch in range(epochs):
        order = torch.randperm(len(examples), generator=generator)
        for batch in order.split(config["batch_size"]):
            optimizer.zero_grad(set_to_none=True)
            if reference is None:
                forecast = (model(x[batch], c[batch]) - y[batch]).abs().mean()
                retain = torch.zeros(())
                total = forecast
            else:
                total, forecast, retain = objective(
                    model, reference, x[batch], c[batch], y[batch], std, weight, config["epsilon"]
                )
            if not torch.isfinite(total):
                raise ValueError("Nonfinite loss")
            total.backward()
            optimizer.step()
            trace.append(
                {
                    "epoch": epoch,
                    "step": len(trace) + 1,
                    "forecast_mae_scaled": forecast.item(),
                    "retention": retain.item(),
                    "total": total.item(),
                    "batch_size": len(batch),
                }
            )
    return optimizer.state_dict(), trace


def binding(root: Path, manifest: dict, entity: dict | None, source_hash: str | None) -> dict:
    return {
        "schema": "ev-checkpoint-input-binding-v1",
        "feature_schema": "ev-input-v1",
        "input_manifest_sha256": sha256(root / "manifest.json"),
        "input_run_id": manifest["run_id"],
        "dataset_id": "urbanev",
        "city_id": "SZH",
        "stage": "target" if entity else "source",
        "entity_id": entity["identity"][2] if entity else None,
        "history_days": entity["history_days"] if entity else None,
        "scale_id": entity["scale"]["fit_sha256"] if entity else None,
        "source_checkpoint_sha256": source_hash,
    }


def checkpoint(
    path: Path,
    model: Forecaster,
    optimizer: dict,
    std: torch.Tensor,
    input_binding: dict,
    config: dict,
    provenance: dict,
) -> None:
    with path.open("xb") as handle:
        torch.save(
            {
                "schema": "duc-retention-study-v1",
                "model": model.state_dict(),
                "optimizer": optimizer,
                "source_latent_std": std,
                "input_binding": input_binding,
                "config": config,
                "provenance": provenance,
                "torch_rng": torch.get_rng_state(),
                "architecture": "GRU(7,64,2,dropout=0);Linear(184,64);ReLU;Linear(64,24);Softplus",
            },
            handle,
        )
    restored = Forecaster()
    restored.load_state_dict(torch.load(path, weights_only=False, map_location="cpu")["model"])
    if any(not torch.equal(v, restored.state_dict()[k]) for k, v in model.state_dict().items()):
        raise ValueError("Checkpoint reload mismatch")


def evaluate(model: Forecaster, root: Path, entity: dict, manifest: dict, output: Path) -> dict:
    """Persist all predictions before opening labels; no post-deployment updates."""
    model.eval()
    identity = entity["identity"]
    predictions = {}
    with output.open("x", encoding="utf-8") as handle, torch.no_grad():
        for row in rows(root / "forecasts.jsonl"):
            if row["identity"] != identity:
                continue
            if row["role"] != "development" or row["scale_id"] != entity["scale"]["fit_sha256"]:
                raise ValueError("Forecast role/scaler mismatch")
            x = torch.tensor([row["x_hist"]], dtype=torch.float32)
            c = torch.tensor([row["c_future"]], dtype=torch.float32)
            prediction = (model(x, c)[0] * row["energy_scale"]).tolist()
            if row["origin"] in predictions:
                raise ValueError("Duplicate forecast origin")
            predictions[row["origin"]] = prediction
            handle.write(
                json.dumps(
                    {"identity": identity, "origin": row["origin"], "prediction_kwh": prediction}
                )
                + "\n"
            )
    if len(predictions) != entity["scheduled_forecasts"]:
        raise ValueError("Forecast coverage mismatch")
    errors = []
    stop = datetime.fromisoformat(manifest["config"]["replay_stop"])
    for row in rows(root / "labels.jsonl"):
        if row["identity"] != identity or row["origin"] not in predictions:
            continue
        labels = arrived(row, stop)
        if labels is not None:
            errors.append(
                sum(abs(a - b) for a, b in zip(predictions[row["origin"]], labels, strict=True))
                / 24
            )
    return {
        "mae_kwh": sum(errors) / len(errors) if errors else None,
        "scored_days": len(errors),
        "issued_days": len(predictions),
        "unscored_days": len(predictions) - len(errors),
        "requested_days": entity["requested_forecasts"],
        "skipped_all_missing_history": entity["skipped_all_missing_history"],
        "skipped_undefined_scale": entity["skipped_undefined_scale"],
    }


def run(inputs: Path, output: Path, config: dict) -> None:
    if platform.python_version_tuple()[:2] != ("3", "12"):
        raise ValueError("Python 3.12 required")
    if config["budgets"] != [7, 14, 28] or config["lambdas"] != [0.0, 0.01, 0.1]:
        raise ValueError("This declared study requires 7/14/28 and lambda 0/.01/.1")
    output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(config["seed"])
    started = time.perf_counter()
    provenance = {
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "worktree": subprocess.check_output(["git", "status", "--porcelain"], text=True),
        "executed_sources": {p.name: sha256(p) for p in Path(__file__).parent.glob("*.py")},
        "python": platform.python_version(),
        "torch": str(torch.__version__),
        "platform": platform.platform(),
        "device": "cpu",
        "threads": 2,
        "run_id": output.name,
    }
    write_json(output / "config.json", config)
    write_json(output / "provenance.json", provenance)
    source_model = Forecaster()
    source_entities = None
    target_ids = None
    source_examples = None
    source_hash = None
    results = []
    for budget in config["budgets"]:
        root = inputs / f"urbanev-SZH-{budget}d"
        manifest = verified_manifest(root)
        if manifest["config"]["history_days"] != budget:
            raise ValueError("Wrong input budget")
        if source_entities is None:
            source_entities, selected = select_entities(
                root, config["source_count"], config["target_count"]
            )
            target_ids = [e["identity"] for e in selected]
            source_examples = training_rows(root, source_entities)
            source_started = time.perf_counter()
            optimizer, trace = fit(source_model, source_examples, config, config["source_epochs"])
            reference = frozen_reference(source_model)
            with torch.no_grad():
                x, _, _ = tensors(source_examples)
                latent = torch.cat(
                    [reference.latent(batch) for batch in x.split(config["batch_size"])]
                )
                std = latent.double().std(dim=0, correction=0).float()
            checkpoint(
                output / "source.pt",
                source_model,
                optimizer,
                std,
                binding(root, manifest, None, None),
                config,
                provenance,
            )
            source_hash = sha256(output / "source.pt")
            write_json(
                output / "source.json",
                {
                    "entities": [e["identity"] for e in source_entities],
                    "examples": len(source_examples),
                    "std_population": "all selected source prefix training inputs, one latent per example; correction=0",
                    "std": std.tolist(),
                    "epsilon": config["epsilon"],
                    "seconds": time.perf_counter() - source_started,
                    "trace": trace,
                },
            )
        else:
            inventory = list(rows(root / "entities.jsonl"))
            same_source = [
                e for e in inventory if e["identity"] in [s["identity"] for s in source_entities]
            ]
            if same_source != source_entities or source_signature(
                training_rows(root, same_source)
            ) != source_signature(source_examples):
                raise ValueError("Source population/scales/examples differ across budgets")
        inventory = list(rows(root / "entities.jsonl"))
        selected = [e for e in inventory if e["identity"] in target_ids]
        write_json(output / f"cohort-{budget}d.json", selected)
        for entity in selected:
            if entity["role"] != "development":
                raise ValueError("Only Development targets permitted")
            if entity["initialization"] == "blocked_undefined_scale":
                results.append(
                    {
                        "budget": budget,
                        "entity": entity["identity"][2],
                        "initialization": entity["initialization"],
                        "requested_days": entity["requested_forecasts"],
                        "skipped_undefined_scale": entity["skipped_undefined_scale"],
                    }
                )
                continue
            examples = training_rows(root, [entity])
            for weight in config["lambdas"]:
                target_started = time.perf_counter()
                model = copy.deepcopy(source_model)
                optimizer, trace = fit(
                    model, examples, config, config["target_epochs"], reference, std, weight
                )
                name = f"target-{entity['identity'][2]}-{budget}d-lambda{weight}"
                target_config = dict(config, active_lambda=weight)
                checkpoint(
                    output / f"{name}.pt",
                    model,
                    optimizer,
                    std,
                    binding(root, manifest, entity, source_hash),
                    target_config,
                    provenance,
                )
                write_json(output / f"{name}-loss.json", trace)
                metrics = evaluate(
                    model, root, entity, manifest, output / f"{name}-predictions.jsonl"
                )
                results.append(
                    {
                        "budget": budget,
                        "entity": entity["identity"][2],
                        "lambda": weight,
                        "initialization": entity["initialization"],
                        "initial_examples": len(examples),
                        "steps": len(trace),
                        "seconds": time.perf_counter() - target_started,
                        **metrics,
                    }
                )
                print(json.dumps(results[-1]), flush=True)
    write_json(
        output / "results.json",
        {
            "scope": "bounded independent initial adaptation; fixed-model held-out Development evaluation, no online updates or controller",
            "seconds": time.perf_counter() - started,
            "results": results,
        },
    )
    write_json(
        output / "artifacts.json",
        {
            p.name: {"sha256": sha256(p), "size_bytes": p.stat().st_size}
            for p in output.iterdir()
            if p.is_file()
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    args = parser.parse_args()
    run(args.inputs, args.output, json.loads(args.config.read_text()))


if __name__ == "__main__":
    main()
