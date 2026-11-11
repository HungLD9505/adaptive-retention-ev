"""Common expert-bank confidence ablation and target-only Development comparison."""

import argparse
import copy
import json
from datetime import datetime, timedelta
from pathlib import Path

import torch

from ev_baselines.policies import Method, Policy
from ev_control.confidence import ControllerConfig, DailyScore, decide
from ev_models.checkpoint import digest
from ev_runner.continuous_run import execute
from ev_runner.replay import Replay
from tools.issue99_retention_screen import INPUT_SHA
from tools.issue99_study_support import PreparedInputs

ROOT = Path(__file__).resolve().parents[1]
DAY = timedelta(days=1)
LEVELS = (0.0, 0.1, 1.0)


def available_rows(rows: list[DailyScore], start: datetime, stop: datetime) -> list[DailyScore]:
    """Return only forecast days in the preceding block and labels arrived by decision."""
    return [
        r
        for r in rows
        if start <= r.origin < stop and r.available_at is not None and r.available_at <= stop
    ]


def select(
    rows: list[DailyScore],
    config: ControllerConfig,
    active: float,
    start: datetime,
    as_of: datetime,
    stream: str,
    scale_id: str,
    confidence: bool,
) -> tuple[float, dict]:
    """Use the same lowest-mean challenger; confidence only gates that challenger."""
    ready = available_rows(rows, start, as_of)
    mean_policy = Policy(Method("online_best"), None, initial_records=[], device="cpu")
    kwargs = dict(
        config=config,
        active_lambda=active,
        block_start=start,
        as_of=as_of,
        stream_id=stream,
        scale_id=scale_id,
    )
    mean = mean_policy.choose(ready, **kwargs)
    selected = mean.selected_lambda
    evidence = {"mean": mean.as_dict(), "gate": None, "recommended": selected}
    if confidence:
        bound = decide(ready, **kwargs)
        comparison = next((c for c in bound.comparisons if c.challenger == selected), None)
        if selected != active and (comparison is None or not comparison.qualifies):
            selected = active
        evidence["gate"] = bound.as_dict()
    evidence.update(active_before=active, selected=selected, decision_time=as_of.isoformat())
    return selected, evidence


def policy_replay(
    rows: list[DailyScore],
    config: ControllerConfig,
    start: datetime,
    stop: datetime,
    stream: str,
    scale_id: str,
    confidence: bool,
    scale: float = 1.0,
) -> dict:
    """Decisions read arrived past rows; subsequent scoring is a separate pass."""
    active = config.initial_lambda
    choices = {}
    decisions = []
    block_start = start
    for day in range((stop - start).days):
        origin = start + day * DAY
        if origin == block_start + config.block_days * DAY:
            selected, evidence = select(
                rows, config, active, block_start, origin, stream, scale_id, confidence
            )
            # Each decision also audits the same-start mean recommendation on future days.
            evidence["effective_stop"] = min(origin + config.block_days * DAY, stop).isoformat()
            decisions.append(evidence)
            active = selected
            block_start = origin
        choices[origin.isoformat()] = active
    errors = []
    for row in rows:
        if start <= row.origin < stop:
            errors.append(
                {
                    "origin": row.origin.isoformat(),
                    "lambda": choices[row.origin.isoformat()],
                    "mae_kwh": row.mae[LEVELS.index(choices[row.origin.isoformat()])] * scale,
                }
            )
    for event in decisions:
        lower, upper = (
            datetime.fromisoformat(event["decision_time"]),
            datetime.fromisoformat(event["effective_stop"]),
        )
        future = [r for r in rows if lower <= r.origin < upper]
        event["future_days"] = len(future)
        if future:
            old = LEVELS.index(event["active_before"])
            rec = LEVELS.index(event["recommended"])
            chosen = LEVELS.index(event["selected"])
            event["future_recommendation_minus_hold"] = sum(
                (r.mae[rec] - r.mae[old]) * scale for r in future
            ) / len(future)
            event["future_selected_minus_hold"] = sum(
                (r.mae[chosen] - r.mae[old]) * scale for r in future
            ) / len(future)
    return {
        "mae": sum(r["mae_kwh"] for r in errors) / len(errors),
        "errors": errors,
        "decisions": decisions,
        "choices": choices,
    }


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    inventory = json.loads(args.inventory.read_text())
    targets = tuple(r["entity_id"] for r in inventory["selected"])
    calibration = ("1405", "2152", "1153", "1693")
    all_targets = calibration + targets
    inputs = PreparedInputs(args.input, INPUT_SHA, targets=all_targets)
    protocol = json.loads(
        (ROOT / "docs/reports/issue99-study-20261110/protocol-lock.json").read_text()
    )
    template = json.loads(
        (ROOT / "docs/reports/issue99-study-20261110/controller-lock.json").read_text()
    )["study_template"]
    registration = {
        "scope": "Exploratory same-bank confidence ablation and random target-only, exposed Development",
        "script_sha256": digest(Path(__file__)),
        "input_sha256": INPUT_SHA,
        "inventory_sha256": digest(args.inventory),
        "targets": targets,
        "calibration_targets": calibration,
        "bank_levels": LEVELS,
        "bank_policy": "Independent constant-retention trajectories; selection never changes their training",
        "controller": {
            "block_days": 7,
            "min_valid_days": 5,
            "segment_days": 3,
            "resamples": 2000,
            "alpha": 0.05,
            "delta": 0,
            "initial_lambda": 0.1,
        },
        "comparison": "Same lowest-past-MAE challenger, optional paired-bootstrap LCB>0 gate",
        "target_only": "Random GRU, 3 prefix epochs + 1 epoch per arrived day, no source-weight initialization or retention",
        "subgroups": "Four predeclared prefix zero-fraction rank strata from inventory",
        "selection": "Fixed bank level selected by original-four calibration macro MAE",
        "source_sha256": {
            str(s): digest(args.sources / f"source-seed{s}" / "epoch-10.pt") for s in (42, 43, 44)
        },
    }
    (args.output / "registration.json").write_text(json.dumps(registration, indent=2))
    bank_data = {}
    for target in all_targets:
        replay = Replay(inputs, target, 90)
        for seed in (42, 43, 44):
            bank = {}
            for level in LEVELS:
                config = copy.deepcopy(template)
                config.update(
                    phase="pilot",
                    targets=list(all_targets),
                    protocol_sha256=None,
                    objective_origins=[],
                    initial_lambda=level,
                    frozen_lambda=True,
                    diagnostic_every=0,
                )
                for key in ("initial_training", "online_training"):
                    config[key]["seed"] = seed
                source = args.sources / f"source-seed{seed}" / "epoch-10.pt"
                folder = args.output / f"bank-{target}-{seed}-{level:g}"
                execute(
                    inputs,
                    target,
                    source,
                    digest(source),
                    config,
                    folder,
                    device="cpu",
                    stop_after_ticks=30 if target in calibration else None,
                    prepared_replay=replay,
                    approved_targets=all_targets,
                )
                values = {}
                for path in sorted(folder.glob("tick-*/events.jsonl")):
                    for row in map(json.loads, path.read_text().splitlines()):
                        if row["event"] == "score":
                            values[row["origin"]] = row
                bank[level] = values
            if any(set(bank[level]) != set(bank[0.0]) for level in LEVELS):
                raise ValueError("Expert score masks differ")
            bank_data[(target, seed)] = {
                "scale_id": replay.scale_id,
                "scale": replay.scale,
                "rows": [
                    DailyScore(
                        datetime.fromisoformat(origin),
                        datetime.fromisoformat(origin),
                        max(
                            datetime.fromisoformat(bank[level][origin]["as_of"]) for level in LEVELS
                        ),
                        24,
                        tuple(bank[level][origin]["mae_kwh"] / replay.scale for level in LEVELS),
                        replay.scale_id,
                        tuple(bank[level][origin]["prediction_sha256"] for level in LEVELS),
                    )
                    for origin in sorted(bank[0.0])
                ],
            }
            print(
                json.dumps(
                    {"phase": "bank", "target": target, "seed": seed, "days": len(bank[0.0])}
                ),
                flush=True,
            )
        # Lock Fixed after original four calibration targets, before new-target runs.
        if target == calibration[-1]:
            means = {}
            for level in LEVELS:
                per_cell = []
                for t in calibration:
                    for seed in (42, 43, 44):
                        rows = [
                            r
                            for r in bank_data[(t, seed)]["rows"]
                            if r.origin.isoformat() in protocol["calibration_origins"][t]
                        ]
                        per_cell.append(
                            sum(r.mae[LEVELS.index(level)] for r in rows)
                            / len(rows)
                            * bank_data[(t, seed)]["scale"]
                        )
                means[str(level)] = sum(per_cell) / 12
            selected = min(LEVELS, key=lambda k: means[str(k)])
            (args.output / "fixed-lock.json").write_text(
                json.dumps(
                    {
                        "means": means,
                        "selected": selected,
                        "registration_sha256": digest(args.output / "registration.json"),
                    },
                    indent=2,
                )
            )
    lock = json.loads((args.output / "fixed-lock.json").read_text())
    results = []
    for target in targets:
        replay = Replay(inputs, target, 90)
        for seed in (42, 43, 44):
            rows = bank_data[(target, seed)]["rows"]
            cfg = ControllerConfig(0.1, 1.0, 0.1, 7, 5, 0.0, 0.05, 3, 2000, seed)
            arms = {}
            for name, confidence in (("mean_only", False), ("confidence_gate", True)):
                arms[name] = policy_replay(
                    rows,
                    cfg,
                    replay.start,
                    replay.stop,
                    f"common-bank/{target}/{seed}",
                    replay.scale_id,
                    confidence,
                    scale=replay.scale,
                )
            for name, level in (("source_finetune", 0.0), ("fixed_bank", lock["selected"])):
                errors = [
                    {
                        "origin": r.origin.isoformat(),
                        "lambda": level,
                        "mae_kwh": r.mae[LEVELS.index(level)] * replay.scale,
                    }
                    for r in rows
                ]
                arms[name] = {
                    "mae": sum(r["mae_kwh"] for r in errors) / len(errors),
                    "errors": errors,
                }
            config = copy.deepcopy(template)
            config.update(
                phase="pilot",
                targets=list(all_targets),
                protocol_sha256=None,
                objective_origins=[],
                initial_lambda=0.0,
                frozen_lambda=True,
                diagnostic_every=0,
            )
            for key in ("initial_training", "online_training"):
                config[key]["seed"] = seed
            source = args.sources / f"source-seed{seed}" / "epoch-10.pt"
            folder = args.output / f"target-only-{target}-{seed}"
            execute(
                inputs,
                target,
                source,
                digest(source),
                config,
                folder,
                device="cpu",
                prepared_replay=replay,
                approved_targets=all_targets,
                source_initialization=False,
            )
            scores = []
            for path in sorted(folder.glob("tick-*/events.jsonl")):
                for row in map(json.loads, path.read_text().splitlines()):
                    if row["event"] == "score":
                        scores.append({"origin": row["origin"], "mae_kwh": row["mae_kwh"]})
            if {r["origin"] for r in scores} != {r.origin.isoformat() for r in rows}:
                raise ValueError("Target-only origin mask differs from expert bank")
            arms["target_only"] = {
                "mae": sum(r["mae_kwh"] for r in scores) / len(scores),
                "errors": scores,
            }
            results.append({"target": target, "seed": seed, "arms": arms})
            (args.output / "results.json").write_text(json.dumps(results, indent=2))
            print(
                json.dumps(
                    {
                        "phase": "comparison",
                        "target": target,
                        "seed": seed,
                        "means": {k: v["mae"] for k, v in arms.items()},
                    }
                ),
                flush=True,
            )
    inputs.reauthenticate()
    (args.output / "completion.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "bank_cells": len(all_targets) * 9,
                "target_only_cells": 36,
                "comparison_cells": len(results) * 5,
            }
        )
    )


if __name__ == "__main__":
    main()
