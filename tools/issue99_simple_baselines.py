"""Two authenticated deterministic baselines for the history-review cohort."""

import argparse
import json
import math
from datetime import datetime, timedelta
from pathlib import Path

from ev_runner.replay import Replay
from tools.issue99_history_study import INPUTS
from tools.issue99_study_support import PreparedInputs

DAY = timedelta(days=1)
HOUR = timedelta(hours=1)


def daily_prediction(record: dict) -> list[float]:
    """Use previous-day observed hours; missing hours use the observed-day mean."""
    valid = [r[0] for r in record["x_hist"] if r[-1]]
    if not valid:
        raise ValueError("No known daily history")
    fallback = sum(valid) / len(valid)
    return [r[0] if r[-1] else fallback for r in record["x_hist"]]


def prefix_hours(records: list[dict]) -> dict:
    """Index only the authenticated permitted predeployment observations."""
    known = {}
    for record in records:
        origin = datetime.fromisoformat(record["origin"])
        for j, row in enumerate(record["x_hist"]):
            if row[-1]:
                known[origin - DAY + j * HOUR] = row[0]
        for j, value in enumerate(record["y_scaled"]):
            known[origin + j * HOUR] = value
    return known


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--input-parent", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    targets = tuple(r["entity_id"] for r in json.loads(args.inventory.read_text())["selected"])
    results = []
    for budget in (7, 14, 28):
        inputs = PreparedInputs(
            args.input_parent / f"urbanev-SZH-{budget}d", INPUTS[budget], targets=targets
        )
        for target in targets:
            replay = Replay(inputs, target, 90)
            known = prefix_hours(inputs.training("development", target))
            rows = {"daily_naive": [], "weekly_naive": []}
            fallbacks = 0
            predictions = []
            for day in range(90):
                origin = replay.start + day * DAY
                record = replay.forecast(origin)
                if record is None:
                    continue
                daily = daily_prediction(record)
                past = origin - 7 * DAY
                if past >= replay.start:
                    available = replay.labels(past, origin)
                    if available.status == "complete":
                        for j, value in enumerate(available.values):
                            known[past + j * HOUR] = value / replay.scale
                weekly = [known.get(past + j * HOUR, daily[j]) for j in range(24)]
                fallbacks += sum(past + j * HOUR not in known for j in range(24))
                predictions.append(
                    {"origin": origin.isoformat(), "daily_naive": daily, "weekly_naive": weekly}
                )
            # Persist the complete predictor-only pass before opening scoring labels.
            with (args.output / f"predictions-{budget}-{target}.json").open("x") as stream:
                json.dump(predictions, stream)
            for issued in predictions:
                origin = datetime.fromisoformat(issued["origin"])
                outcome = replay.labels(origin, replay.stop + 2 * DAY)
                if outcome.status != "complete":
                    continue
                for name in ("daily_naive", "weekly_naive"):
                    vector = issued[name]
                    errors = [
                        p * replay.scale - y for p, y in zip(vector, outcome.values, strict=True)
                    ]
                    rows[name].append(
                        {
                            "origin": origin.isoformat(),
                            "prediction_scaled": vector,
                            "mae_kwh": sum(abs(e) for e in errors) / 24,
                            "mse_kwh2": sum(e * e for e in errors) / 24,
                        }
                    )
            for name, values in rows.items():
                results.append(
                    {
                        "history_days": budget,
                        "target": target,
                        "method": name,
                        "scores": values,
                        "mae": sum(r["mae_kwh"] for r in values) / len(values),
                        "rmse": math.sqrt(sum(r["mse_kwh2"] for r in values) / len(values)),
                        "weekly_fallback_hours": fallbacks if name == "weekly_naive" else None,
                    }
                )
        inputs.reauthenticate()
    (args.output / "results.json").write_text(json.dumps(results, indent=2))
    print(json.dumps({"status": "completed", "cells": len(results)}))


if __name__ == "__main__":
    main()
