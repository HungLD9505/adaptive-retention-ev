"""Recompute experimental screen scores from saved vectors and delayed labels."""

import argparse
import json
import math
from datetime import datetime
from pathlib import Path

from ev_models.checkpoint import digest
from ev_runner.replay import Replay
from tools.issue99_retention_screen import INPUT_SHA
from tools.issue99_study_support import PreparedInputs


def verify(inputs: PreparedInputs, root: Path) -> dict:
    """Fail on changed vectors, unavailable labels, duplicate or inaccurate scores."""
    results = json.loads((root / "results.json").read_text())
    replays = {target: Replay(inputs, target, 90) for target in {c["target"] for c in results}}
    count = 0
    maximum_difference = 0.0
    for cell in results:
        replay = replays[cell["target"]]
        folder = root / f"{cell['target']}-{cell['seed']}-{cell['kind']}-{cell['strength']:g}"
        forecasts = {}
        for path in folder.glob("tick-*/forecasts.json"):
            record = json.loads(path.read_text())
            if record:
                if record["origin"] in forecasts:
                    raise ValueError("Duplicate forecast")
                forecasts[record["origin"]] = (record["prediction"], digest(path))
        origins = set()
        for score in cell["scores"]:
            if score["origin"] in origins:
                raise ValueError("Duplicate calibration score")
            origins.add(score["origin"])
            vector, fingerprint = forecasts[score["origin"]]
            if fingerprint != score["prediction_sha256"]:
                raise ValueError("Saved prediction checksum mismatch")
            labels = replay.labels(
                datetime.fromisoformat(score["origin"]), datetime.fromisoformat(score["as_of"])
            )
            if labels.status != "complete":
                raise ValueError("Labels not available at score time")
            error = (
                sum(abs(p * replay.scale - y) for p, y in zip(vector, labels.values, strict=True))
                / 24
            )
            difference = abs(error - score["mae_kwh"])
            maximum_difference = max(maximum_difference, difference)
            if difference > 1e-9 or not math.isfinite(error):
                raise ValueError("Saved error differs from vector/labels")
            count += 1
        if abs(sum(s["mae_kwh"] for s in cell["scores"]) / len(origins) - cell["mae"]) > 1e-10:
            raise ValueError("Cell mean mismatch")
    inputs.reauthenticate()
    return {
        "cells": len(results),
        "scores": count,
        "max_mae_difference": maximum_difference,
        "results_sha256": digest(root / "results.json"),
        "status": "passed",
    }


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path)
    args = parser.parse_args()
    value = verify(PreparedInputs(args.input, INPUT_SHA), args.run)
    with (args.run / "independent-score-verification.json").open("x") as stream:
        json.dump(value, stream, indent=2)
    print(json.dumps(value))


if __name__ == "__main__":
    main()
