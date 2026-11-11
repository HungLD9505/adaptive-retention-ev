"""Verify paired expanded-Development scores and summarize station uncertainty."""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

import numpy as np

from ev_models.checkpoint import digest
from ev_runner.replay import Replay
from tools.issue99_retention_screen import INPUT_SHA
from tools.issue99_study_support import PreparedInputs


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    inventory = json.loads(args.inventory.read_text())
    targets = tuple(r["entity_id"] for r in inventory["selected"])
    inputs = PreparedInputs(args.input, INPUT_SHA, targets=targets)
    cells = json.loads((args.run / "results.json").read_text())
    expected = {
        (t, s, m)
        for t in targets
        for s in (42, 43, 44)
        for m in ("lambda0", "fixed", "l2sp", "discrete")
    }
    if {(c["target"], c["seed"], c["method"]) for c in cells} != expected or len(cells) != len(
        expected
    ):
        raise ValueError("Expanded cell matrix mismatch")
    masks = {}
    difference = 0.0
    count = 0
    timings = {}
    for target in targets:
        replay = Replay(inputs, target, 90)
        for cell in [c for c in cells if c["target"] == target]:
            folder = args.run / f"evaluation-{target}-{cell['seed']}-{cell['method']}"
            report = json.loads((folder / "run.json").read_text())
            timings[(target, cell["seed"], cell["method"])] = report.get(
                "invocation_wall_seconds", report.get("elapsed_seconds")
            )
            forecasts = {}
            for file in folder.glob("tick-*/forecasts.json"):
                record = json.loads(file.read_text())
                if record:
                    if record["origin"] in forecasts:
                        raise ValueError("Duplicate forecast")
                    forecasts[record["origin"]] = (record, digest(file))
            seen = set()
            for score in cell["scores"]:
                origin = score["origin"]
                if origin in seen:
                    raise ValueError("Duplicate scored origin")
                seen.add(origin)
                record, checksum = forecasts[origin]
                if score["prediction_sha256"] != checksum:
                    raise ValueError("Prediction checksum mismatch")
                labels = replay.labels(
                    datetime.fromisoformat(origin), datetime.fromisoformat(score["as_of"])
                )
                if labels.status != "complete":
                    raise ValueError("Unavailable label scored")
                if cell["method"] == "discrete":
                    index = (0.0, 0.1, 1.0).index(score["issued_active"])
                    if record["active"] != score["issued_active"]:
                        raise ValueError("Active branch mismatch")
                    prediction = record["predictions"][index]
                else:
                    prediction = record["prediction"]
                value = (
                    sum(
                        abs(p * replay.scale - y)
                        for p, y in zip(prediction, labels.values, strict=True)
                    )
                    / 24
                )
                difference = max(difference, abs(value - score["mae_kwh"]))
                if abs(value - score["mae_kwh"]) > 1e-9:
                    raise ValueError("Recomputed score mismatch")
                count += 1
            key = (target, cell["seed"])
            if key in masks and masks[key] != seen:
                raise ValueError("Methods have unmatched score origins")
            masks[key] = seen
            if abs(sum(s["mae_kwh"] for s in cell["scores"]) / len(seen) - cell["mae"]) > 1e-10:
                raise ValueError("Cell mean mismatch")
    inputs.reauthenticate()
    station = {}
    for target in targets:
        station[target] = {
            method: sum(c["mae"] for c in cells if c["target"] == target and c["method"] == method)
            / 3
            for method in ("lambda0", "fixed", "l2sp", "discrete")
        }
    macro = {
        m: float(np.mean([v[m] for v in station.values()])) for m in next(iter(station.values()))
    }
    rng = np.random.default_rng(20261110)
    groups = [
        [r["entity_id"] for r in inventory["selected"] if r["stratum"] == q] for q in range(4)
    ]
    contrasts = []
    for baseline in ("lambda0", "fixed"):
        for method in ("fixed", "l2sp", "discrete"):
            if method == baseline:
                continue
            draws = np.zeros(20000)
            for group in groups:
                effects = np.array([station[t][method] - station[t][baseline] for t in group])
                draws += effects[rng.integers(0, len(group), (20000, len(group)))].sum(axis=1) / 12
            signed = [station[t][method] - station[t][baseline] for t in targets]
            contrasts.append(
                {
                    "method": method,
                    "baseline": baseline,
                    "delta_mae_kwh": macro[method] - macro[baseline],
                    "percent_reduction": 100 * (macro[baseline] - macro[method]) / macro[baseline],
                    "stations_improved": sum(v < 0 for v in signed),
                    "stations_worsened": sum(v > 0 for v in signed),
                    "station_bootstrap_lower": float(np.quantile(draws, 0.025)),
                    "station_bootstrap_upper": float(np.quantile(draws, 0.975)),
                }
            )
    summary = {
        "status": "passed",
        "cells": len(cells),
        "scores": count,
        "max_score_difference": difference,
        "results_sha256": digest(args.run / "results.json"),
        "macro_mae": macro,
        "station_means": station,
        "contrasts": contrasts,
        "scored_days_per_seed": {t: [len(masks[(t, s)]) for s in (42, 43, 44)] for t in targets},
        "summed_invocation_seconds": {
            m: sum(v for (t, s, k), v in timings.items() if k == m) for m in macro
        },
        "uncertainty_scope": "20,000 paired station bootstrap draws within four prefix sparsity strata, seeds averaged before resampling; exploratory selected-station uncertainty only",
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2))
    with (args.output / "station-results.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["target", *macro])
        writer.writeheader()
        writer.writerows({"target": t, **v} for t, v in station.items())
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
