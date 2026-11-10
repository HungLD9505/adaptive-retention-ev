"""Independent vector/label readback and paired summaries for the review study."""

import argparse
import csv
import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np

from ev_models.checkpoint import digest
from ev_runner.replay import Replay
from tools.issue99_confidence_readback import authenticated_scores
from tools.issue99_history_study import INPUTS
from tools.issue99_study_support import PreparedInputs


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--input-parent", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    inventory = json.loads(args.inventory.read_text())
    targets = tuple(r["entity_id"] for r in inventory["selected"])
    strata = [
        [r["entity_id"] for r in inventory["selected"] if r["stratum"] == q] for q in range(4)
    ]
    naive = json.loads((args.root / "simple-baselines-v2/results.json").read_text())
    rng = np.random.default_rng(20261110)
    allrows = []
    summaries = []
    masks = {}
    verified = 0
    for budget in (7, 14, 28):
        root = args.root / f"history-{budget}"
        summary = json.loads((root / "summary.json").read_text())
        if summary["status"] != "completed":
            raise ValueError("Incomplete study")
        results = json.loads((root / "results.json").read_text())
        if len(results) != 36:
            raise ValueError("Expected 36 station/seed cells")
        inputs = PreparedInputs(
            args.input_parent / f"urbanev-SZH-{budget}d", INPUTS[budget], targets=targets
        )
        cells = []
        bank_const = {level: [] for level in (0.0, 0.1, 1.0)}
        for target in targets:
            replay = Replay(inputs, target, 90)
            for seed in (42, 43, 44):
                stored = next(c for c in results if c["target"] == target and c["seed"] == seed)
                bank = {}
                for level in (0.0, 0.1, 1.0):
                    folder = root / f"bank-{target}-{seed}-{level:g}"
                    bank[level] = authenticated_scores(folder, replay)
                    verified += len(bank[level])
                    bank_const[level].append(
                        sum(r["mae_kwh"] for r in bank[level].values()) / len(bank[level])
                    )
                random = authenticated_scores(root / f"target-only-{target}-{seed}", replay)
                verified += len(random)
                groups = {**bank, "random": random}
                mse = {}
                for level, values in groups.items():
                    folder = root / (
                        f"target-only-{target}-{seed}"
                        if level == "random"
                        else f"bank-{target}-{seed}-{level:g}"
                    )
                    vectors = {}
                    for file in folder.glob("tick-*/forecasts.json"):
                        row = json.loads(file.read_text())
                        if row:
                            vectors[row["origin"]] = row["prediction"]
                    for origin, score in values.items():
                        labels = replay.labels(
                            datetime.fromisoformat(origin), datetime.fromisoformat(score["as_of"])
                        )
                        value = (
                            sum(
                                (p * replay.scale - y) ** 2
                                for p, y in zip(vectors[origin], labels.values, strict=True)
                            )
                            / 24
                        )
                        if abs(value - score["mse_kwh2"]) > 1e-8:
                            raise ValueError("MSE mismatch")
                        mse[(level, origin)] = value
                expected = set(bank[0.0])
                if set(random) != expected:
                    raise ValueError("Random mask mismatch")
                key = (target, seed)
                if key in masks and masks[key] != expected:
                    raise ValueError("History masks differ")
                masks[key] = expected
                for method, arm in stored["arms"].items():
                    if {e["origin"] for e in arm["errors"]} != expected:
                        raise ValueError("Policy mask mismatch")
                    constants = {
                        "target_only": "random",
                        "source_finetune": 0.0,
                        "fixed_bank": summary["fixed_level"],
                    }
                    selected_mses = []
                    for error in arm["errors"]:
                        level = constants[method] if method in constants else error["lambda"]
                        if abs(groups[level][error["origin"]]["mae_kwh"] - error["mae_kwh"]) > 1e-9:
                            raise ValueError("Chosen forecast score mismatch")
                        selected_mses.append(mse[(level, error["origin"])])
                    value = sum(e["mae_kwh"] for e in arm["errors"]) / len(expected)
                    rmse = math.sqrt(sum(selected_mses) / len(expected))
                    cells.append(
                        dict(
                            history_days=budget,
                            target=target,
                            seed=seed,
                            method=method,
                            mae_kwh=value,
                            rmse_kwh=rmse,
                            days=len(expected),
                        )
                    )
            for baseline in (
                c for c in naive if c["history_days"] == budget and c["target"] == target
            ):
                if {r["origin"] for r in baseline["scores"]} != masks[(target, 42)]:
                    raise ValueError("Naive mask mismatch")
                cells.append(
                    dict(
                        history_days=budget,
                        target=target,
                        seed="deterministic",
                        method=baseline["method"],
                        mae_kwh=baseline["mae"],
                        rmse_kwh=baseline["rmse"],
                        days=len(baseline["scores"]),
                    )
                )
        methods = sorted({c["method"] for c in cells})
        station = {
            t: {
                m: float(
                    np.mean([c["mae_kwh"] for c in cells if c["target"] == t and c["method"] == m])
                )
                for m in methods
            }
            for t in targets
        }
        macro = {m: float(np.mean([v[m] for v in station.values()])) for m in methods}
        rmse = {
            m: float(np.mean([c["rmse_kwh"] for c in cells if c["method"] == m])) for m in methods
        }
        contrasts = []
        for method, baseline in (
            ("source_finetune", "target_only"),
            ("fixed_bank", "target_only"),
            ("confidence_gate", "mean_only"),
            ("confidence_gate", "fixed_bank"),
            ("mean_only", "fixed_bank"),
        ):
            draws = np.zeros(20000)
            for group in strata:
                delta = np.array([station[t][method] - station[t][baseline] for t in group])
                draws += delta[rng.integers(0, len(group), (20000, len(group)))].sum(1) / 12
            contrasts.append(
                dict(
                    method=method,
                    baseline=baseline,
                    delta_kwh=macro[method] - macro[baseline],
                    percent_reduction=100 * (macro[baseline] - macro[method]) / macro[baseline],
                    stations_improved=sum(
                        station[t][method] < station[t][baseline] for t in targets
                    ),
                    lower=float(np.quantile(draws, 0.025)),
                    upper=float(np.quantile(draws, 0.975)),
                )
            )
        summaries.append(
            dict(
                history_days=budget,
                mae=macro,
                rmse=rmse,
                station_means=station,
                contrasts=contrasts,
                chosen=summary["chosen"],
                fixed_level=summary["fixed_level"],
                retrospective_constant_bank_means={
                    str(k): float(np.mean(v)) for k, v in bank_const.items()
                },
                original_summary_sha256=digest(root / "summary.json"),
            )
        )
        allrows.extend(cells)
        inputs.reauthenticate()
    with (args.output / "cells.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=allrows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(allrows)
    result = {
        "status": "passed",
        "verified_neural_scores": verified,
        "histories": summaries,
        "paired_origins_match_across_all_methods_and_budgets": True,
        "seed_days_per_history": sum(len(v) for v in masks.values()),
    }
    (args.output / "summary.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
