"""Paired one-step diagnostic on already inspected Development calibration."""

import argparse
import copy
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import torch

import ev_runner.continuous as continuous
from ev_models.checkpoint import digest
from ev_runner.continuous_run import code_identity, execute
from ev_runner.state import state_digest
from tools.issue99_study_support import PreparedInputs

ROOT = Path(__file__).resolve().parents[1]


class ProbeRunner(continuous.ContinuousRunner):
    """Keep the actual controller trajectory and score disposable paired branches."""

    observations: list[dict] = []

    def _arrivals(self, as_of: datetime, events: list[dict]) -> None:
        decision = None
        original_decide = continuous.decide
        original_update = self.branch.update

        def capture(*args, **kwargs):
            nonlocal decision
            decision = original_decide(*args, **kwargs)
            return decision

        def paired(record, **kwargs):
            nonlocal decision
            forecast = self.replay.forecast(as_of) if as_of < self.replay.stop else None
            if decision is not None and forecast is not None:
                before = state_digest(self.branch.snapshot())
                old, selected = decision["lambda_before"], decision["lambda_after"]
                opposite = min(self.rule.upper_bound, max(0.0, 2 * old - selected))
                predictions = {}
                for name, weight in (("hold", old), ("follow", selected), ("reverse", opposite)):
                    branch = self.branch.clone(
                        device=self.device, learning_rate=self.training.learning_rate
                    )
                    branch.update(record, **{**kwargs, "weight": weight})
                    predictions[name] = branch.predict(forecast, device=self.device)
                if state_digest(self.branch.snapshot()) != before:
                    raise ValueError("Disposable branches changed the actual branch")
                self.observations.append(
                    {
                        "origin": as_of.isoformat(),
                        "update_origin": record["origin"],
                        "decision": decision,
                        "reverse_lambda": opposite,
                        "asymmetric_projection": not math.isclose(
                            abs(opposite - old), abs(selected - old), rel_tol=1e-12, abs_tol=1e-14
                        ),
                        "predictions_scaled": predictions,
                    }
                )
            decision = None
            return original_update(record, **kwargs)

        self.branch.update = paired
        try:
            with patch.object(continuous, "decide", capture):
                super()._arrivals(as_of, events)
        finally:
            self.branch.update = original_update


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    protocol = json.loads(
        (ROOT / "docs/reports/issue99-study-20261110/protocol-lock.json").read_text()
    )
    template = json.loads(
        (ROOT / "docs/reports/issue99-study-20261110/controller-lock.json").read_text()
    )["study_template"]
    inputs = PreparedInputs(args.input, digest(args.input / "manifest.json"))
    identity = {
        "code": code_identity(),
        "script_sha256": digest(Path(__file__)),
        "input_manifest_sha256": digest(args.input / "manifest.json"),
        "scope": "Exploratory calibration, paired one-step diagnostic, continuous parent",
        "config": template,
        "label_policy": "Score only after replay ends; calibration origins only",
        "cells": [],
    }
    (args.output / "registration.json").write_text(json.dumps(identity, indent=2))
    for target in template["targets"]:
        for seed in (42, 43, 44):
            config = copy.deepcopy(template)
            config.update(phase="pilot", objective_origins=[], protocol_sha256=None)
            config["initial_training"]["seed"] = seed
            config["online_training"]["seed"] = seed
            source = args.sources / f"source-seed{seed}" / "epoch-10.pt"
            ProbeRunner.observations = []
            destination = args.output / f"{target}-{seed}"
            with patch("ev_runner.continuous_run.ContinuousRunner", ProbeRunner):
                execute(
                    inputs,
                    target,
                    source,
                    digest(source),
                    config,
                    destination,
                    device="cpu",
                    stop_after_ticks=28,
                )
            from ev_runner.replay import Replay

            replay = Replay(inputs, target, 90)
            rows = []
            for row in ProbeRunner.observations:
                if row["origin"] not in protocol["calibration_origins"][target]:
                    continue
                outcome = replay.labels(datetime.fromisoformat(row["origin"]), replay.stop)
                if outcome.status != "complete":
                    continue
                row["mae_kwh"] = {
                    name: sum(
                        abs(p * replay.scale - y) for p, y in zip(pred, outcome.values, strict=True)
                    )
                    / 24
                    for name, pred in row["predictions_scaled"].items()
                }
                rows.append(row)
            if not rows:
                raise ValueError("No complete paired calibration forecasts")
            result = {
                "target": target,
                "seed": seed,
                "source_sha256": digest(source),
                "pairs": len(rows),
                "rows": rows,
                "mean_mae": {
                    name: sum(r["mae_kwh"][name] for r in rows) / len(rows)
                    for name in ("hold", "follow", "reverse")
                },
            }
            (destination / "paired-diagnostic.json").write_text(json.dumps(result, indent=2))
            identity["cells"].append({k: v for k, v in result.items() if k != "rows"})
            print(json.dumps(identity["cells"][-1]), flush=True)
    inputs.reauthenticate()
    by_target = defaultdict(list)
    for cell in identity["cells"]:
        by_target[cell["target"]].append(cell)
    identity["target_means"] = {
        target: {
            name: sum(c["mean_mae"][name] for c in cells) / len(cells)
            for name in ("hold", "follow", "reverse")
        }
        for target, cells in by_target.items()
    }
    (args.output / "summary.json").write_text(json.dumps(identity, indent=2))


if __name__ == "__main__":
    main()
