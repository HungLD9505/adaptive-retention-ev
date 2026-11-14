"""Stable Fixed plus rolling-target GRU, static blend and Fixed-share controller."""

import argparse
import copy
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

from ev_control.expert_mix import fit_static_weight, forecast_mixture
from ev_models.checkpoint import digest
from ev_models.training import train_epoch
from ev_runner.continuous_run import execute
from ev_runner.replay import Replay
from tools.issue99_confidence_readback import authenticated_scores
from tools.issue99_history_study import CALIBRATION
from tools.issue99_retention_screen import INPUT_SHA
from tools.issue99_study_support import PreparedInputs

ROOT = Path(__file__).resolve().parents[1]
DAY = timedelta(days=1)
RECIPES = [(days, rate) for days in (3, 7, 14) for rate in (0.001, 0.003)]


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False))


def read_vectors(folder: Path, replay: Replay) -> dict:
    """Authenticate canonical saved scores before returning complete-day vectors."""
    scores = authenticated_scores(folder, replay)
    predictions = {}
    for path in folder.glob("tick-*/forecasts.json"):
        row = json.loads(path.read_text())
        if row:
            predictions[row["origin"]] = row["prediction"]
    return {
        origin: {"prediction": [p * replay.scale for p in predictions[origin]], **event}
        for origin, event in scores.items()
    }


def pair_cell(stable: dict, fast: dict, replay: Replay, origins: set[str] | None) -> dict:
    """Require identical masks and expose labels only in this offline evaluator."""
    if set(stable) != set(fast):
        raise ValueError("Stable/fast score masks differ")
    selected = sorted(o for o in stable if origins is None or o in origins)
    labels = []
    for origin in selected:
        if stable[origin]["as_of"] != fast[origin]["as_of"]:
            raise ValueError("Expert availability clocks differ")
        outcome = replay.labels(
            datetime.fromisoformat(origin), datetime.fromisoformat(stable[origin]["as_of"])
        )
        labels.append(outcome.values)
    return {
        "origins": selected,
        "available_at": [stable[o]["as_of"] for o in selected],
        "stable": [stable[o]["prediction"] for o in selected],
        "fast": [fast[o]["prediction"] for o in selected],
        "labels": labels,
        "scale": replay.scale,
    }


def calibrate_expert(
    inputs: PreparedInputs,
    target: str,
    seed: int,
    window: int,
    rate: float,
    folder: Path,
    source: Path,
    template: dict,
    replay: Replay,
    calibration: bool,
) -> dict:
    """Roll only authenticated prefix/arrived records into one full-batch update."""
    memory = {r["origin"]: r for r in inputs.training("development", target)}
    audit = []
    config = copy.deepcopy(template)
    config.update(
        phase="pilot",
        protocol_sha256=None,
        objective_origins=[],
        initial_lambda=0.0,
        frozen_lambda=True,
        diagnostic_every=0,
    )
    for key in ("initial_training", "online_training"):
        config[key].update(seed=seed, learning_rate=rate)

    def rolling_epoch(model, optimizer, records, training, **kwargs):
        if len(records) != 1:
            raise ValueError("Expected one newly arrived complete record")
        current = records[0]
        anchor = datetime.fromisoformat(current["origin"])
        if current["origin"] in memory:
            raise ValueError("Duplicate arrived label in rolling window")
        memory[current["origin"]] = current
        lower = anchor - (window - 1) * DAY
        ready = [
            r
            for origin, r in sorted(memory.items())
            if lower <= datetime.fromisoformat(origin) <= anchor
        ]
        if len(ready) > training.batch_size:
            raise ValueError("Window must fit one optimizer step")
        audit.append(
            {"arrived_origin": current["origin"], "used_origins": [r["origin"] for r in ready]}
        )
        return train_epoch(model, optimizer, ready, training, **kwargs)

    with patch("ev_runner.state.train_epoch", rolling_epoch):
        execute(
            inputs,
            target,
            source,
            digest(source),
            config,
            folder,
            device="cpu",
            stop_after_ticks=30 if calibration else None,
            prepared_replay=replay,
            approved_targets=tuple(config["targets"]),
        )
    save(
        folder / "rolling-window-binding.json",
        {
            "window_days": window,
            "learning_rate": rate,
            "lambda": 0.0,
            "initial_epochs": config["initial_training"]["epochs"],
            "source_sha256": digest(source),
            "updates": audit,
            "resume_scope": "Fresh run only; no rolling-memory resume",
        },
    )
    return read_vectors(folder, replay)


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    for name in ("input", "sources", "inventory", "stable-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    inventory = json.loads(args.inventory.read_text())
    targets = tuple(r["entity_id"] for r in inventory["selected"])
    all_targets = CALIBRATION + targets
    inputs = PreparedInputs(args.input, INPUT_SHA, targets=all_targets)
    prior = json.loads((args.stable_root / "selection-lock.json").read_text())
    if prior["fixed_level"] != 1.0 or prior["epochs"]["source_finetune"]["epochs"] != 3:
        raise ValueError("This bounded experiment requires the locked 14d Fixed profile")
    template = json.loads(
        (ROOT / "docs/reports/issue99-study-20261110/controller-lock.json").read_text()
    )["study_template"]
    template["targets"] = list(all_targets)
    template["initial_training"]["epochs"] = 3
    protocol = json.loads(
        (ROOT / "docs/reports/issue99-study-20261110/protocol-lock.json").read_text()
    )
    registration = {
        "scope": "Exposed UrbanEV/SZH Development, 14d, stable-fast forecast fusion; not lambda controller",
        "script_sha256": digest(Path(__file__)),
        "mix_code_sha256": digest(ROOT / "ev_control/expert_mix.py"),
        "input_sha256": INPUT_SHA,
        "inventory_sha256": digest(args.inventory),
        "stable_root": str(args.stable_root),
        "stable_lock_sha256": digest(args.stable_root / "selection-lock.json"),
        "calibration_targets": CALIBRATION,
        "evaluation_targets": targets,
        "recipes": RECIPES,
        "eta_candidates": [0.1, 1.0, 10.0],
        "share_candidates": [0.001, 0.01, 0.1],
        "static_weight": "Exact weighted median convex MAE minimizer across calibration cells",
        "selection": "Fast recipe minimizes calibrated static-mixture MAE; controller selected afterward on same fixed pair",
        "initial_weight": "Calibration-selected static weight, including endpoints",
        "reference": "Herbster and Warmuth 1998 Fixed-share, two-expert share-to-other update",
        "source_sha256": {
            str(s): digest(args.sources / f"source-seed{s}" / "epoch-10.pt") for s in (42, 43, 44)
        },
    }
    save(args.output / "registration.json", registration)
    started = time.perf_counter()
    replays = {t: Replay(inputs, t, 90) for t in all_targets}
    stable_cal = {}
    for target in CALIBRATION:
        for seed in (42, 43, 44):
            folder = args.stable_root / f"bank-cal-{target}-{seed}-1"
            stable_cal[(target, seed)] = read_vectors(folder, replays[target])
    candidates = []
    calibration_cells = {}
    for window, rate in RECIPES:
        cells = []
        for target in CALIBRATION:
            replay = replays[target]
            for seed in (42, 43, 44):
                folder = args.output / f"cal-{window}-{rate:g}-{target}-{seed}"
                fast = calibrate_expert(
                    inputs,
                    target,
                    seed,
                    window,
                    rate,
                    folder,
                    args.sources / f"source-seed{seed}" / "epoch-10.pt",
                    template,
                    replay,
                    True,
                )
                cells.append(
                    pair_cell(
                        stable_cal[(target, seed)],
                        fast,
                        replay,
                        set(protocol["calibration_origins"][target]),
                    )
                )
        weight = fit_static_weight(cells)
        mae = float(np.mean([forecast_mixture(c, weight)["mae"] for c in cells]))
        candidates.append(
            {
                "window": window,
                "learning_rate": rate,
                "static_weight": weight,
                "mae": mae,
                "fast_mae": float(np.mean([forecast_mixture(c, 0)["mae"] for c in cells])),
                "stable_mae": float(np.mean([forecast_mixture(c, 1)["mae"] for c in cells])),
            }
        )
        calibration_cells[(window, rate)] = cells
        save(args.output / "fast-calibration.json", candidates)
        print(json.dumps({"phase": "fast-calibration", **candidates[-1]}), flush=True)
    selected = min(candidates, key=lambda c: c["mae"])
    cells = calibration_cells[(selected["window"], selected["learning_rate"])]
    weights = selected["static_weight"]
    controllers = []
    for eta in (0.1, 1.0, 10.0):
        for share in (0.001, 0.01, 0.1):
            value = float(
                np.mean([forecast_mixture(c, weights, eta=eta, share=share)["mae"] for c in cells])
            )
            controllers.append({"eta": eta, "share": share, "mae": value})
    controller = min(controllers, key=lambda c: c["mae"])
    lock = {
        "selected_fast": selected,
        "controller": controller,
        "all_controller_candidates": controllers,
        "registration_sha256": digest(args.output / "registration.json"),
        "locked_before_evaluation": True,
    }
    save(args.output / "selection-lock.json", lock)
    results = []
    for target in targets:
        replay = replays[target]
        for seed in (42, 43, 44):
            stable = read_vectors(args.stable_root / f"bank-{target}-{seed}-1", replay)
            folder = args.output / f"evaluation-{target}-{seed}"
            fast = calibrate_expert(
                inputs,
                target,
                seed,
                selected["window"],
                selected["learning_rate"],
                folder,
                args.sources / f"source-seed{seed}" / "epoch-10.pt",
                template,
                replay,
                False,
            )
            cell = pair_cell(stable, fast, replay, None)
            arms = {
                name: forecast_mixture(cell, w)
                for name, w in (("stable_fixed", 1), ("fast_only", 0), ("static_mix", weights))
            }
            arms["fixed_share"] = forecast_mixture(
                cell, weights, eta=controller["eta"], share=controller["share"]
            )
            oracle = float(
                np.minimum(
                    np.abs(np.asarray(cell["stable"]) - cell["labels"]).mean(1),
                    np.abs(np.asarray(cell["fast"]) - cell["labels"]).mean(1),
                ).mean()
            )
            results.append(
                {
                    "target": target,
                    "seed": seed,
                    "cell": cell,
                    "arms": arms,
                    "daily_expert_oracle_mae": oracle,
                }
            )
            save(args.output / "results.json", results)
            print(
                json.dumps(
                    {
                        "phase": "evaluation",
                        "target": target,
                        "seed": seed,
                        "mae": {k: v["mae"] for k, v in arms.items()},
                    }
                ),
                flush=True,
            )
    inputs.reauthenticate()
    macro = {m: float(np.mean([c["arms"][m]["mae"] for c in results])) for m in results[0]["arms"]}
    save(
        args.output / "summary.json",
        {
            "status": "completed",
            "macro_mae": macro,
            "cells": len(results),
            "selection": lock,
            "wall_seconds": time.perf_counter() - started,
            "results_sha256": digest(args.output / "results.json"),
        },
    )


if __name__ == "__main__":
    main()
