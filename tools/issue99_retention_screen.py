"""Separate exploratory loss ablation on the issue99 Development calibration."""

import argparse
import copy
import json
import math
import time
from pathlib import Path
from unittest.mock import patch

import torch

import ev_models.training as training
from ev_models.checkpoint import digest, load_checkpoint
from ev_models.model import ForecastGRU, forecast_loss, retention_loss
from ev_runner.continuous_run import execute
from ev_runner.replay import Replay
from tools.issue99_study_support import PreparedInputs

ROOT = Path(__file__).resolve().parents[1]
INPUT_SHA = "66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9"


def importance_weights(model: ForecastGRU, rows: list[dict]) -> torch.Tensor:
    """Prefix-only feature ablation, with 10% uniform mixing to limit suppression."""
    x, c, y = next(training.batches(rows, len(rows), device="cpu"))
    with torch.no_grad():
        z = model.encode(x)
        baseline = forecast_loss(model(x, c), y)
        effects = []
        for k in range(64):
            ablated = z.clone()
            ablated[:, k] = 0
            prediction = model.head(torch.cat((ablated, c.flatten(1)), dim=1))
            effects.append((forecast_loss(prediction, y) - baseline).clamp_min(0))
        values = torch.stack(effects)
        if values.sum() == 0:
            return torch.ones(64)
        return 0.1 + 0.9 * values / values.mean()


def penalty(
    kind: str,
    model: ForecastGRU,
    reference: ForecastGRU,
    z: torch.Tensor,
    zs: torch.Tensor,
    scales: torch.Tensor,
    epsilon: float,
    weights: torch.Tensor,
) -> torch.Tensor:
    """Keep each experimental penalty explicit; L2-SP applies to encoder only."""
    if kind == "uniform":
        return retention_loss(z, zs, scales, epsilon)
    if kind == "selective":
        return (((z - zs.detach()) / (scales + epsilon)).square() * weights).mean()
    if kind == "l2sp":
        return sum(
            (p - q.detach()).square().sum() / 2
            for p, q in zip(model.encoder.parameters(), reference.encoder.parameters(), strict=True)
        )
    raise ValueError("Unknown experimental retention")


def encoder_norm(loss: torch.Tensor, model: ForecastGRU) -> float:
    gradients = torch.autograd.grad(loss, tuple(model.encoder.parameters()), retain_graph=True)
    return math.sqrt(sum(g.double().square().sum().item() for g in gradients))


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--calibration-from", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    protocol = json.loads(
        (ROOT / "docs/reports/issue99-study-20261110/protocol-lock.json").read_text()
    )
    config0 = json.loads(
        (ROOT / "docs/reports/issue99-study-20261110/controller-lock.json").read_text()
    )["study_template"]
    selections = None
    if args.calibration_from:
        cells = json.loads((args.calibration_from / "results.json").read_text())
        if len(cells) != 120:
            raise ValueError("Complete 120-cell calibration required")
        selections = {}
        for kind in ("uniform", "selective", "l2sp"):
            candidates = (0.1, 1.0, 10.0)
            selections[kind] = min(
                candidates,
                key=lambda strength: (
                    sum(c["mae"] for c in cells if c["kind"] == kind and c["strength"] == strength)
                    / 12
                ),
            )
    score_phase = "evaluation" if selections else "calibration"
    registration = {
        "scope": "Exposed Development calibration, exploratory loss ablation",
        "script_sha256": digest(Path(__file__)),
        "weights_rule": "prefix source feature ablation positive MAE impact, 10% uniform mix, mean one",
        "strengths": [0.1, 1, 10],
        "lambda_rule": "strength * encoder gradient F norm / penalty gradient norm after one prefix-only unregularized epoch",
        "config": config0,
        "score_phase": score_phase,
        "selected_strengths": selections,
        "selection_sha256": digest(args.calibration_from / "results.json") if selections else None,
        "runtime": {
            "python": __import__("platform").python_version(),
            "torch": torch.__version__,
            "device": "cpu",
        },
    }
    (args.output / "registration.json").write_text(json.dumps(registration, indent=2))
    inputs = PreparedInputs(args.input, INPUT_SHA)
    base_train = training.train_epoch
    results = []
    audits = []
    started = time.perf_counter()
    for target in config0["targets"]:
        replay = Replay(inputs, target, 90)
        prefix = inputs.training("development", target)
        for seed in (42, 43, 44):
            source_path = args.sources / f"source-seed{seed}" / "epoch-10.pt"
            source, _, saved = load_checkpoint(
                source_path, sha256=digest(source_path), device="cpu"
            )
            reference = training.frozen_reference(source)
            scales = saved["latent_scale"]
            weights = importance_weights(reference, prefix)
            cfg = training.TrainingConfig(seed=seed, epochs=1)
            training.seed_everything(seed)
            probe = training.adapt_model(source)
            adam = torch.optim.Adam(probe.parameters(), lr=cfg.learning_rate)
            base_train(probe, adam, prefix, cfg, epoch=0, device="cpu")
            x, c, y = next(training.batches(prefix, len(prefix), device="cpu"))
            z = probe.encode(x)
            with torch.no_grad():
                zs = reference.encode(x)
            f = forecast_loss(probe(x, c), y)
            fnorm = encoder_norm(f, probe)
            dimensions = ((z - zs) / (scales + cfg.epsilon)).square().mean(0).detach()
            shares = dimensions / dimensions.sum()
            audit = {
                "target": target,
                "seed": seed,
                "source_sha256": digest(source_path),
                "source_scales": scales.tolist(),
                "weights": weights.tolist(),
                "normalized_retention_by_dimension": dimensions.tolist(),
                "top_5_penalty_share": shares.topk(5).values.sum().item(),
                "lambda_balance": {},
            }
            for kind in ("uniform", "selective", "l2sp"):
                r = penalty(kind, probe, reference, z, zs, scales, cfg.epsilon, weights)
                rnorm = encoder_norm(r, probe)
                if not math.isfinite(rnorm) or rnorm <= 0:
                    raise ValueError("Penalty calibration has no finite nonzero gradient")
                audit["lambda_balance"][kind] = fnorm / rnorm
            audits.append(audit)
            (args.output / "dimension-audit.json").write_text(json.dumps(audits, indent=2))
            arms = [("uniform", 0.0)] + [
                (kind, strength)
                for kind in ("uniform", "selective", "l2sp")
                for strength in (0.1, 1.0, 10.0)
            ]
            if selections:
                arms = [("uniform", 0.0)] + list(selections.items())
            for kind, strength in arms:
                coefficient = strength * audit["lambda_balance"][kind]
                config = copy.deepcopy(config0)
                config.update(
                    phase="pilot",
                    protocol_sha256=None,
                    objective_origins=[],
                    frozen_lambda=True,
                    initial_lambda=coefficient,
                    diagnostic_every=0,
                )
                config["window_rule"]["upper_bound"] = max(coefficient, 1.0)
                config["initial_training"]["seed"] = seed
                config["online_training"]["seed"] = seed

                def experimental_train(model, optimizer, records, conf, **kwargs):
                    ref = kwargs.get("reference")

                    # This patch is confined to this single-threaded experimental invocation.
                    def selected_loss(z, zs, latent_scale, epsilon):
                        return penalty(kind, model, ref, z, zs, latent_scale, epsilon, weights)

                    with patch.object(training, "retention_loss", selected_loss):
                        return base_train(model, optimizer, records, conf, **kwargs)

                destination = args.output / f"{target}-{seed}-{kind}-{strength:g}"
                with (
                    patch("ev_runner.continuous_run.train_epoch", experimental_train),
                    patch("ev_runner.state.train_epoch", experimental_train),
                ):
                    execute(
                        inputs,
                        target,
                        source_path,
                        digest(source_path),
                        config,
                        destination,
                        device="cpu",
                        stop_after_ticks=None if selections else 30,
                        prepared_replay=replay,
                    )
                scores = []
                for path in sorted(destination.glob("tick-*/events.jsonl")):
                    for event in map(json.loads, path.read_text().splitlines()):
                        if (
                            event["event"] == "score"
                            and event["origin"] in protocol[f"{score_phase}_origins"][target]
                        ):
                            scores.append(event)
                if len(scores) != protocol["minimum_scored_days"][score_phase][target]:
                    raise ValueError("Calibration coverage mismatch")
                result = {
                    "target": target,
                    "seed": seed,
                    "kind": kind,
                    "strength": strength,
                    "lambda": coefficient,
                    "scores": scores,
                    "mae": sum(s["mae_kwh"] for s in scores) / len(scores),
                }
                (destination / "experimental-loss-binding.json").write_text(
                    json.dumps(
                        {
                            **registration,
                            "kind": kind,
                            "strength": strength,
                            "lambda": coefficient,
                            "weights": weights.tolist(),
                        },
                        indent=2,
                    )
                )
                results.append(result)
                (args.output / "results.json").write_text(json.dumps(results, indent=2))
                print(json.dumps({k: v for k, v in result.items() if k != "scores"}), flush=True)
    inputs.reauthenticate()
    (args.output / "completion.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "cells": len(results),
                "wall_seconds": time.perf_counter() - started,
            }
        )
    )


if __name__ == "__main__":
    main()
