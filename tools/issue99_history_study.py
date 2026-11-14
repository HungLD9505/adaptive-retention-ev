"""Calibration-selected GRU training budgets and matched 7/14/28d retention study."""

import argparse
import copy
import json
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import torch

from ev_control.confidence import ControllerConfig, DailyScore
from ev_models.checkpoint import digest
from ev_runner.continuous_run import execute
from ev_runner.replay import Replay
from tools.issue99_confidence_evidence import LEVELS, policy_replay
from tools.issue99_confidence_readback import authenticated_scores
from tools.issue99_study_support import PreparedInputs

ROOT = Path(__file__).resolve().parents[1]
INPUTS = {
    7: "fd1b5d1767e94a3e5c6f62447d446e1f13859b823c5fe14c51b5055d8e67169c",
    14: "66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9",
    28: "cdd43152bbda3de9f468938262a8bf00e041a9f264cf29051b71d06e788beadd",
}
CALIBRATION = ("1405", "2152", "1153", "1693")


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False))


def mean_cells(cells: list[dict]) -> float:
    return sum(c["mae"] for c in cells) / len(cells)


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--input-parent", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--history-days", type=int, choices=(7, 14, 28), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    targets = tuple(r["entity_id"] for r in json.loads(args.inventory.read_text())["selected"])
    cohort = CALIBRATION + targets
    inputs = PreparedInputs(
        args.input_parent / f"urbanev-SZH-{args.history_days}d",
        INPUTS[args.history_days],
        targets=cohort,
    )
    template = json.loads(
        (ROOT / "docs/reports/issue99-study-20261110/controller-lock.json").read_text()
    )["study_template"]
    protocol = json.loads(
        (ROOT / "docs/reports/issue99-study-20261110/protocol-lock.json").read_text()
    )
    start = time.perf_counter()
    registration = {
        "history_days": args.history_days,
        "input_sha256": INPUTS[args.history_days],
        "script_sha256": digest(Path(__file__)),
        "source_population_sha256": inputs.source_hash,
        "inventory_sha256": digest(args.inventory),
        "source_sha256": {
            str(s): digest(args.sources / f"source-seed{s}" / "epoch-10.pt") for s in (42, 43, 44)
        },
        "calibration_targets": CALIBRATION,
        "evaluation_targets": targets,
        "epoch_candidates": [3, 10, 30, 100, 300],
        "boundary_extension": 900,
        "selection": "minimum equal-station, equal-seed calibration MAE per initialization; extend 900 if 300 wins",
        "scope": "Exposed Development, no convergence optimality or untouched holdout claim",
        "online_epochs": 1,
        "learning_rate": 0.001,
        "policy": "Independent common bank, same lowest-past-MAE challenger and optional normalized bootstrap gate; start at calibration Fixed",
        "controller": {
            "block_days": 7,
            "min_valid_days": 5,
            "segment_days": 3,
            "resamples": 2000,
            "alpha": 0.05,
            "delta": 0.0,
        },
    }
    save(args.output / "registration.json", registration)
    for t in cohort:
        inputs.check_target(t)
    replays = {t: Replay(inputs, t, 90) for t in cohort}
    cal = []

    def run(
        target: str,
        seed: int,
        epochs: int,
        level: float,
        source_initialization: bool,
        folder: Path,
        calibration: bool,
    ) -> dict:
        config = copy.deepcopy(template)
        config.update(
            phase="pilot",
            targets=list(cohort),
            protocol_sha256=None,
            objective_origins=[],
            initial_lambda=level,
            frozen_lambda=True,
            diagnostic_every=0,
        )
        for key in ("initial_training", "online_training"):
            config[key]["seed"] = seed
        config["initial_training"]["epochs"] = epochs
        source = args.sources / f"source-seed{seed}" / "epoch-10.pt"
        execute(
            inputs,
            target,
            source,
            digest(source),
            config,
            folder,
            device="cpu",
            stop_after_ticks=30 if calibration else None,
            prepared_replay=replays[target],
            approved_targets=cohort,
            source_initialization=source_initialization,
            approved_history_days=(7, 14, 28),
        )
        scores = authenticated_scores(folder, replays[target])
        if calibration:
            scores = {
                k: v for k, v in scores.items() if k in protocol["calibration_origins"][target]
            }
        if not scores:
            raise ValueError("No complete scored origins")
        return {
            "target": target,
            "seed": seed,
            "epochs": epochs,
            "lambda": level,
            "source_initialization": source_initialization,
            "folder": folder.name,
            "days": len(scores),
            "mae": sum(r["mae_kwh"] for r in scores.values()) / len(scores),
            "scores": scores,
        }

    chosen = {}
    for mode, source_initialization in (("target_only", False), ("source_finetune", True)):
        candidates = [3, 10, 30, 100, 300]
        for epochs in candidates:
            for target in CALIBRATION:
                for seed in (42, 43, 44):
                    folder = args.output / f"cal-{mode}-{epochs}-{target}-{seed}"
                    result = run(target, seed, epochs, 0.0, source_initialization, folder, True)
                    cal.append({"mode": mode, **{k: v for k, v in result.items() if k != "scores"}})
            save(args.output / "epoch-calibration.json", cal)
            print(
                json.dumps(
                    {
                        "phase": "epoch-calibration",
                        "mode": mode,
                        "epochs": epochs,
                        "mae": mean_cells(
                            [c for c in cal if c["mode"] == mode and c["epochs"] == epochs]
                        ),
                    }
                ),
                flush=True,
            )
        means = {
            e: mean_cells([c for c in cal if c["mode"] == mode and c["epochs"] == e])
            for e in candidates
        }
        if min(means, key=means.get) == 300:
            epochs = 900
            for target in CALIBRATION:
                for seed in (42, 43, 44):
                    folder = args.output / f"cal-{mode}-{epochs}-{target}-{seed}"
                    result = run(target, seed, epochs, 0.0, source_initialization, folder, True)
                    cal.append({"mode": mode, **{k: v for k, v in result.items() if k != "scores"}})
            means[900] = mean_cells([c for c in cal if c["mode"] == mode and c["epochs"] == 900])
            save(args.output / "epoch-calibration.json", cal)
        best = min(means, key=means.get)
        chosen[mode] = {
            "epochs": best,
            "calibration_mae": means[best],
            "curve": means,
            "upper_boundary_unresolved": best == max(means),
        }
    save(
        args.output / "epoch-lock.json",
        {"chosen": chosen, "registration_sha256": digest(args.output / "registration.json")},
    )
    bank_cal = []
    source_epochs = chosen["source_finetune"]["epochs"]
    for level in LEVELS:
        for target in CALIBRATION:
            for seed in (42, 43, 44):
                folder = args.output / f"bank-cal-{target}-{seed}-{level:g}"
                row = run(target, seed, source_epochs, level, True, folder, True)
                bank_cal.append({k: v for k, v in row.items() if k != "scores"})
    bank_means = {
        level: mean_cells([c for c in bank_cal if c["lambda"] == level]) for level in LEVELS
    }
    fixed = min(bank_means, key=bank_means.get)
    lock = {
        "epochs": chosen,
        "bank_calibration": bank_cal,
        "bank_means": bank_means,
        "fixed_level": fixed,
        "epoch_lock_sha256": digest(args.output / "epoch-lock.json"),
        "locked_before_evaluation": True,
    }
    save(args.output / "selection-lock.json", lock)
    evaluation = []
    verified = 0
    for target in targets:
        replay = replays[target]
        for seed in (42, 43, 44):
            bank = {}
            for level in LEVELS:
                folder = args.output / f"bank-{target}-{seed}-{level:g}"
                bank[level] = run(target, seed, source_epochs, level, True, folder, False)["scores"]
                verified += len(bank[level])
            if any(set(bank[level]) != set(bank[0.0]) for level in LEVELS):
                raise ValueError("Bank mask mismatch")
            rows = [
                DailyScore(
                    datetime.fromisoformat(origin),
                    datetime.fromisoformat(origin),
                    datetime.fromisoformat(bank[0.0][origin]["as_of"]),
                    24,
                    tuple(bank[level][origin]["mae_kwh"] / replay.scale for level in LEVELS),
                    replay.scale_id,
                    tuple(bank[level][origin]["prediction_sha256"] for level in LEVELS),
                )
                for origin in sorted(bank[0.0])
            ]
            config = ControllerConfig(0.1, 1.0, fixed, 7, 5, 0.0, 0.05, 3, 2000, seed)
            arms = {
                name: policy_replay(
                    rows,
                    config,
                    replay.start,
                    replay.stop,
                    f"history/{args.history_days}/{target}/{seed}",
                    replay.scale_id,
                    confidence,
                    scale=replay.scale,
                )
                for name, confidence in (("mean_only", False), ("confidence_gate", True))
            }
            for name, level in (("source_finetune", 0.0), ("fixed_bank", fixed)):
                errors = [
                    {"origin": origin, "mae_kwh": score["mae_kwh"]}
                    for origin, score in bank[level].items()
                ]
                arms[name] = {
                    "mae": sum(r["mae_kwh"] for r in errors) / len(errors),
                    "errors": errors,
                }
            folder = args.output / f"target-only-{target}-{seed}"
            random = run(target, seed, chosen["target_only"]["epochs"], 0.0, False, folder, False)
            if set(random["scores"]) != set(bank[0.0]):
                raise ValueError("Target-only mask mismatch")
            verified += len(random["scores"])
            arms["target_only"] = {
                "mae": random["mae"],
                "errors": [
                    {"origin": k, "mae_kwh": v["mae_kwh"]} for k, v in random["scores"].items()
                ],
            }
            evaluation.append(
                {"history_days": args.history_days, "target": target, "seed": seed, "arms": arms}
            )
            save(args.output / "results.json", evaluation)
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
    methods = list(evaluation[0]["arms"])
    station = {
        t: {
            m: mean_cells([{"mae": c["arms"][m]["mae"]} for c in evaluation if c["target"] == t])
            for m in methods
        }
        for t in targets
    }
    macro = {m: float(np.mean([v[m] for v in station.values()])) for m in methods}
    inputs.reauthenticate()
    save(
        args.output / "summary.json",
        {
            "history_days": args.history_days,
            "macro_mae": macro,
            "station_means": station,
            "chosen": chosen,
            "fixed_level": fixed,
            "verified_evaluation_scores": verified,
            "evaluation_cells": len(evaluation) * 5,
            "wall_seconds": time.perf_counter() - start,
            "results_sha256": digest(args.output / "results.json"),
            "status": "completed",
        },
    )


if __name__ == "__main__":
    main()
