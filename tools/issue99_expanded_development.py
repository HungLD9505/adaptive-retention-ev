"""Locked cross-station Development comparison with reused calibration evidence."""

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
from ev_models.model import forecast_loss
from ev_runner.continuous_run import execute as fixed_execute
from ev_runner.replay import Replay
from ev_runner.run import execute as discrete_execute
from tools.issue99_retention_screen import INPUT_SHA, encoder_norm, penalty
from tools.issue99_study_support import PreparedInputs

ROOT = Path(__file__).resolve().parents[1]


def scores_at(folder: Path, replay: Replay, origins: set[str] | None) -> list[dict]:
    """Convert both runner formats to original-unit active prediction error."""
    scores = []
    for path in sorted(folder.glob("tick-*/events.jsonl")):
        for row in map(json.loads, path.read_text().splitlines()):
            if row["event"] != "score" or (origins is not None and row["origin"] not in origins):
                continue
            if "mae_kwh" not in row:
                levels = (0.0, 0.1, 1.0)
                row = {
                    **row,
                    "mae_kwh": row["mae_scaled"][levels.index(row["issued_active"])] * replay.scale,
                }
            scores.append(row)
    if not scores or len({r["origin"] for r in scores}) != len(scores):
        raise ValueError("Empty or duplicate scored origins")
    return scores


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--calibration", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    protocol = json.loads(
        (ROOT / "docs/reports/issue99-study-20261110/protocol-lock.json").read_text()
    )
    template = json.loads(
        (ROOT / "docs/reports/issue99-study-20261110/controller-lock.json").read_text()
    )["study_template"]
    discrete_template = json.loads(
        (ROOT / "configs/issue99-discrete-comparator-v1.json").read_text()
    )
    inventory = json.loads(args.inventory.read_text())
    targets = tuple(r["entity_id"] for r in inventory["selected"])
    calibration_targets = tuple(template["targets"])
    if len(targets) != 12 or set(targets) & set(calibration_targets):
        raise ValueError("Expected twelve distinct additional targets")
    inputs = PreparedInputs(args.input, INPUT_SHA, targets=calibration_targets + targets)
    for target in calibration_targets + targets:
        inputs.check_target(target)
    calibration = json.loads((args.calibration / "results.json").read_text())
    selection = {}
    for kind in ("uniform", "l2sp"):
        means = {}
        for strength in (0.1, 1.0, 10.0):
            cells = [c for c in calibration if c["kind"] == kind and c["strength"] == strength]
            if {(c["target"], c["seed"]) for c in cells} != {
                (t, s) for t in calibration_targets for s in (42, 43, 44)
            }:
                raise ValueError("Incomplete calibration recipe")
            means[strength] = sum(c["mae"] for c in cells) / 12
        selection[kind] = min(means, key=means.get)
    registration = {
        "scope": "Additional Development stations, 14d, full 90-day replay; prior exposure uncertain",
        "script_sha256": digest(Path(__file__)),
        "inventory_sha256": digest(args.inventory),
        "calibration_results_sha256": digest(args.calibration / "results.json"),
        "targets": targets,
        "calibration_targets": calibration_targets,
        "source_paths": {
            str(s): str(args.sources / f"source-seed{s}" / "epoch-10.pt") for s in (42, 43, 44)
        },
        "source_sha256": {
            str(s): digest(args.sources / f"source-seed{s}" / "epoch-10.pt") for s in (42, 43, 44)
        },
        "fixed_selected_strengths": selection,
        "controller_candidates": [
            {"block_days": b, "min_valid_days": m} for b, m in ((7, 5), (14, 7), (21, 7))
        ],
        "controller_unchanged": "levels 0/0.1/1, initial 0.1, confidence bootstrap rule unchanged",
        "evaluation": "All complete full-replay origins, paired across four methods, macro equal station after equal seed average",
        "uncertainty": "Descriptive station-paired bootstrap after seed averaging, fixed RNG seed 20261110",
        "runtime": {"device": "cpu", "torch": torch.__version__},
    }
    (args.output / "registration.json").write_text(json.dumps(registration, indent=2))
    results = []
    started = time.perf_counter()
    for block, minimum in ((7, 5), (14, 7), (21, 7)):
        for target in calibration_targets:
            replay = Replay(inputs, target, 90)
            for seed in (42, 43, 44):
                config = copy.deepcopy(discrete_template)
                config["controller"].update(block_days=block, min_valid_days=minimum, seed=seed)
                for key in ("initial_training", "online_training"):
                    config[key]["seed"] = seed
                folder = args.output / f"calibration-{block}-{target}-{seed}"
                source = args.sources / f"source-seed{seed}" / "epoch-10.pt"
                discrete_execute(
                    inputs,
                    target,
                    source,
                    digest(source),
                    config,
                    folder,
                    device="cpu",
                    stop_after_ticks=30,
                    prepared_replay=replay,
                    cpu_development_diagnostic=True,
                )
                scores = scores_at(folder, replay, set(protocol["calibration_origins"][target]))
                if len(scores) != protocol["minimum_scored_days"]["calibration"][target]:
                    raise ValueError("Controller calibration coverage mismatch")
                results.append(
                    {
                        "block": block,
                        "minimum": minimum,
                        "target": target,
                        "seed": seed,
                        "mae": sum(s["mae_kwh"] for s in scores) / len(scores),
                    }
                )
                print(json.dumps(results[-1]), flush=True)
    means = {
        block: sum(c["mae"] for c in results if c["block"] == block) / 12 for block in (7, 14, 21)
    }
    selected_block = min(means, key=means.get)
    lock = {
        **registration,
        "controller_calibration": results,
        "controller_means": means,
        "selected_block": selected_block,
        "locked_before_additional_station_replay": True,
    }
    (args.output / "selection-lock.json").write_text(json.dumps(lock, indent=2))
    base_train = training.train_epoch
    evaluation = []
    for target in targets:
        replay = Replay(inputs, target, 90)
        prefix = inputs.training("development", target)
        for seed in (42, 43, 44):
            source_path = args.sources / f"source-seed{seed}" / "epoch-10.pt"
            source, _, saved = load_checkpoint(
                source_path, sha256=digest(source_path), device="cpu"
            )
            reference = training.frozen_reference(source)
            scales = saved["latent_scale"]
            training.seed_everything(seed)
            probe = training.adapt_model(source)
            cfg = training.TrainingConfig(seed=seed)
            optimizer = torch.optim.Adam(probe.parameters(), lr=cfg.learning_rate)
            base_train(probe, optimizer, prefix, cfg, epoch=0, device="cpu")
            x, c, y = next(training.batches(prefix, len(prefix), device="cpu"))
            z = probe.encode(x)
            with torch.no_grad():
                zs = reference.encode(x)
            f = forecast_loss(probe(x, c), y)
            fnorm = encoder_norm(f, probe)
            coefficients = {"lambda0": 0.0}
            for name, kind in (("fixed", "uniform"), ("l2sp", "l2sp")):
                r = penalty(kind, probe, reference, z, zs, scales, cfg.epsilon, torch.ones(64))
                norm = encoder_norm(r, probe)
                if norm <= 0 or not math.isfinite(norm):
                    raise ValueError("Invalid prefix gradient calibration")
                coefficients[name] = selection[kind] * fnorm / norm
            for method in ("lambda0", "fixed", "l2sp", "discrete"):
                folder = args.output / f"evaluation-{target}-{seed}-{method}"
                if method == "discrete":
                    config = copy.deepcopy(discrete_template)
                    config["development_entities"] = list(targets)
                    config["controller"].update(
                        block_days=selected_block,
                        min_valid_days=5 if selected_block == 7 else 7,
                        seed=seed,
                    )
                    for key in ("initial_training", "online_training"):
                        config[key]["seed"] = seed
                    discrete_execute(
                        inputs,
                        target,
                        source_path,
                        digest(source_path),
                        config,
                        folder,
                        device="cpu",
                        prepared_replay=replay,
                        cpu_development_diagnostic=True,
                    )
                    coefficient = None
                else:
                    kind = "l2sp" if method == "l2sp" else "uniform"
                    coefficient = coefficients[method]
                    config = copy.deepcopy(template)
                    config.update(
                        phase="pilot",
                        targets=list(targets),
                        protocol_sha256=None,
                        objective_origins=[],
                        initial_lambda=coefficient,
                        frozen_lambda=True,
                        diagnostic_every=0,
                    )
                    config["window_rule"]["upper_bound"] = max(coefficient, 1.0)
                    for key in ("initial_training", "online_training"):
                        config[key]["seed"] = seed

                    def experimental_train(model, optimizer, records, conf, **kwargs):
                        def selected_loss(z, zs, latent_scale, epsilon):
                            return penalty(
                                kind,
                                model,
                                kwargs["reference"],
                                z,
                                zs,
                                latent_scale,
                                epsilon,
                                torch.ones(64),
                            )

                        with patch.object(training, "retention_loss", selected_loss):
                            return base_train(model, optimizer, records, conf, **kwargs)

                    with (
                        patch("ev_runner.continuous_run.train_epoch", experimental_train),
                        patch("ev_runner.state.train_epoch", experimental_train),
                    ):
                        fixed_execute(
                            inputs,
                            target,
                            source_path,
                            digest(source_path),
                            config,
                            folder,
                            device="cpu",
                            prepared_replay=replay,
                            approved_targets=targets,
                        )
                scores = scores_at(folder, replay, None)
                row = {
                    "target": target,
                    "seed": seed,
                    "method": method,
                    "lambda": coefficient,
                    "mae": sum(s["mae_kwh"] for s in scores) / len(scores),
                    "scores": scores,
                }
                (folder / "expanded-loss-binding.json").write_text(
                    json.dumps(
                        {
                            "method": method,
                            "lambda": coefficient,
                            "selection_lock_sha256": digest(args.output / "selection-lock.json"),
                            "script_sha256": registration["script_sha256"],
                            "source_sha256": digest(source_path),
                        },
                        indent=2,
                    )
                )
                evaluation.append(row)
                (args.output / "results.json").write_text(json.dumps(evaluation, indent=2))
                print(json.dumps({k: v for k, v in row.items() if k != "scores"}), flush=True)
    inputs.reauthenticate()
    (args.output / "completion.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "calibration_cells": len(results),
                "evaluation_cells": len(evaluation),
                "wall_seconds": time.perf_counter() - started,
            }
        )
    )


if __name__ == "__main__":
    main()
