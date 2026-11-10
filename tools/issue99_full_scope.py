"""Locked stable-fast and confidence follow-up on all 810 historical Final units."""

import argparse
import json
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

from ev_control.confidence import ControllerConfig, DailyScore
from ev_control.continuous import WindowRule
from ev_control.expert_mix import forecast_mixture
from ev_models.checkpoint import digest, load_checkpoint
from ev_models.run import environment
from ev_models.training import (
    TrainingConfig,
    adapt_model,
    frozen_reference,
    seed_everything,
    train_epoch,
)
from ev_runner.continuous import ContinuousRunner
from ev_runner.final_gate import FinalAccess
from ev_runner.replay import Replay
from ev_runner.state import Branch, rng_state, state_digest
from ev_runner.store import Store
from tools.issue99_confidence_evidence import policy_replay
from tools.issue99_full_scope_inputs import FollowupInputs, historical_vectors
from tools.issue99_stable_fast import pair_cell, read_vectors

ROOT = Path(__file__).resolve().parents[1]
DAY = timedelta(days=1)


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False))


def run_fast(
    inputs: FollowupInputs, replay: Replay, source: dict, base: Path, config: dict, output: Path
) -> dict:
    """Train the already selected rolling expert; never alter frozen historical outputs."""
    config = json.loads(json.dumps(config))
    config["method"] = {"name": "rolling_target", "lambda": 0.0, "window_days": 7}
    seed = config["initial_training"]["seed"]
    source_model, _, checkpoint = load_checkpoint(
        base / source["path"], sha256=source["sha256"], device="cpu"
    )
    meta = checkpoint["metadata"]
    if (
        meta["source_population_sha256"] != inputs.source_hash
        or meta["training_config"]["seed"] != seed
        or checkpoint["completed_epochs"] != 10
    ):
        raise ValueError("Source10 identity mismatch")
    seed_everything(seed)
    model = adapt_model(source_model)
    reference = frozen_reference(source_model)
    latent = checkpoint["latent_scale"]
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    prefix = inputs.training("final", replay.entity_id)
    initial = TrainingConfig(**config["initial_training"])
    online = TrainingConfig(**config["online_training"])
    logs = [
        train_epoch(
            model,
            optimizer,
            prefix,
            initial,
            epoch=e,
            device="cpu",
            reference=reference,
            latent_scale=latent,
            retention_weight=0,
        )
        for e in range(initial.epochs)
    ]
    memory = {r["origin"]: r for r in prefix}
    audit = []

    def rolling_epoch(model, optimizer, records, training, **kwargs):
        if len(records) != 1 or records[0]["origin"] in memory:
            raise ValueError("Rolling expert needs one new arrived day")
        current = records[0]
        memory[current["origin"]] = current
        anchor = datetime.fromisoformat(current["origin"])
        ready = [
            r
            for o, r in sorted(memory.items())
            if anchor - 6 * DAY <= datetime.fromisoformat(o) <= anchor
        ]
        if len(ready) > training.batch_size:
            raise ValueError("Rolling window exceeds single optimizer step")
        audit.append(
            {"arrived_origin": current["origin"], "used_origins": [r["origin"] for r in ready]}
        )
        return train_epoch(model, optimizer, ready, training, **kwargs)

    binding = {
        "input": inputs.binding("target", replay.entity_id, source["sha256"]),
        "config": {**config, "state_retention": "latest"},
        "source_population_sha256": inputs.source_hash,
        "followup_lock_sha256": inputs.final_access.sha256,
        "method": "rolling7_lambda0",
        "resume": "unsupported",
    }
    store = Store(output, binding)
    branch = Branch(model, optimizer, rng_state())
    branch.steps = sum(r["steps"] for r in logs)
    rule = WindowRule(
        **json.loads(
            (ROOT / "docs/reports/issue99-study-20261110/controller-lock.json").read_text()
        )["study_template"]["window_rule"]
    )
    runner = ContinuousRunner(
        replay,
        branch,
        reference,
        latent,
        rule,
        online,
        store,
        initial_lambda=0,
        device="cpu",
        cadence=1,
        frozen_lambda=True,
    )
    with patch("ev_runner.state.train_epoch", rolling_epoch):
        runner.run_until(
            replay.stop + (int(replay.delay.total_seconds() // DAY.total_seconds()) + 1) * DAY
        )
    save(
        output / "rolling-window-binding.json",
        {"updates": audit, "window_days": 7, "lambda": 0, "learning_rate": 0.001},
    )
    save(
        output / "run.json",
        {
            "binding": binding,
            "initial_logs": logs,
            "actual_steps": runner.actual_steps,
            "final_state_sha256": state_digest(runner.branch.snapshot()),
        },
    )
    return read_vectors(output, replay)


def execute_group(index: int, lock_path: str, base_path: str, output_path: str) -> dict:
    """Run one dataset/history group in an isolated one-thread CPU process."""
    torch.set_num_threads(1)
    base, output, lock_path = Path(base_path), Path(output_path), Path(lock_path)
    lock = json.loads(lock_path.read_text())
    group = lock["groups"][index]
    access = FinalAccess(
        ROOT, lock_path, lock["parent_commit"], {"mode": "owner_authorized_followup"}
    )
    ns, budget = "-".join(group["namespace"]), group["history_days"]
    folder = output / f"{ns}-{budget}d"
    folder.mkdir(exist_ok=False)
    inputs = FollowupInputs(
        base / "data/inputs/issue18-input-handoff-v1-20261019" / f"{ns}-{budget}d", group, access
    )
    analysis = base / "runs/issue23-final-analysis-20261028-root-v1"
    collection = analysis / f"{ns}-collection-v1.json"
    if digest(collection) != lock["collections"][ns]:
        raise ValueError("Historical collection changed")
    records = json.loads(collection.read_text())
    lookup = {
        (r["entity_id"], r["seed"], r["variant"]): r for r in records if r["budget"] == budget
    }
    selection = lock["selection"]
    initial_weight = selection["selected_fast"]["static_weight"]
    controller = selection["controller"]
    cells = []
    for target in group["selected_ids"]:
        replay = Replay(inputs, target, 90)
        for seed in (42, 43, 44):
            before = time.perf_counter()
            old_fixed = historical_vectors(lookup[(target, seed, "fixed_retention")], replay)
            old_adaptive = historical_vectors(lookup[(target, seed, "adaptive")], replay)
            if set(old_fixed["rows"]) != set(old_adaptive["rows"]):
                raise ValueError("Historical adaptive and Fixed masks differ")
            config = lock["method_configs"][str(seed)]["fixed_retention"]
            fast_path = folder / f"fast-{target}-{seed}"
            previous = Path(lock["reuse_fast"]["root"]) / folder.name / fast_path.name
            reused = (previous / "run.json").exists()
            if reused:
                saved = json.loads((previous / "run.json").read_text())
                expected_config = json.loads(json.dumps(config))
                expected_config["method"] = {
                    "name": "rolling_target",
                    "lambda": 0.0,
                    "window_days": 7,
                }
                expected_config["state_retention"] = "latest"
                if (
                    saved["binding"]["config"] != expected_config
                    or saved["binding"]["followup_lock_sha256"] != lock["reuse_fast"]["lock_sha256"]
                    or saved["binding"]["input"]
                    != inputs.binding("target", target, group["sources"][str(seed)]["sha256"])
                ):
                    raise ValueError("Partial-run expert does not match registered reuse")
                fast_path = previous
                fast = read_vectors(fast_path, replay)
            else:
                fast = run_fast(
                    inputs, replay, group["sources"][str(seed)], base, config, fast_path
                )
            stable = {
                o: {"as_of": r["as_of"], "prediction": r["vectors"][0]}
                for o, r in old_fixed["rows"].items()
            }
            if set(stable) != set(fast):
                raise ValueError("Historical Fixed and new fast coverage differ")
            arms = {
                "old_fixed": {"mae": old_fixed["mae"]},
                "old_adaptive": {"mae": old_adaptive["mae"]},
            }
            mixture = None
            if stable:
                mixture = pair_cell(stable, fast, replay, None)
                for name, weight in (("fast_only", 0), ("static_mix", initial_weight)):
                    arms[name] = forecast_mixture(mixture, weight)
                arms["fixed_share"] = forecast_mixture(
                    mixture, initial_weight, eta=controller["eta"], share=controller["share"]
                )
                rows = [
                    DailyScore(
                        datetime.fromisoformat(o),
                        datetime.fromisoformat(o),
                        datetime.fromisoformat(r["as_of"]),
                        24,
                        tuple(x / replay.scale for x in r["mae"]),
                        replay.scale_id,
                        tuple(r["prediction_ids"]),
                    )
                    for o, r in sorted(old_adaptive["rows"].items())
                ]
                cfg = ControllerConfig(0.1, 1, 0.1, 7, 5, 0, 0.05, 3, 2000, seed)
                for name, gate in (("mean7", False), ("confidence7", True)):
                    arms[name] = policy_replay(
                        rows,
                        cfg,
                        replay.start,
                        replay.stop,
                        f"historical-followup/{ns}/{target}/{seed}",
                        replay.scale_id,
                        gate,
                        scale=replay.scale,
                    )
            else:
                arms.update(
                    {
                        name: {"mae": None}
                        for name in (
                            "fast_only",
                            "static_mix",
                            "fixed_share",
                            "mean7",
                            "confidence7",
                        )
                    }
                )
            result = {
                "namespace": ns,
                "history_days": budget,
                "target": target,
                "seed": seed,
                "scored_days": len(stable),
                "fast_path": str(fast_path),
                "fast_reused": reused,
                "fast_report_sha256": digest(fast_path / "run.json"),
                "cell": mixture,
                "arms": arms,
                "wall_seconds": time.perf_counter() - before,
            }
            save(folder / f"cell-{target}-{seed}.json", result)
            cells.append(
                {k: v for k, v in result.items() if k not in ("cell", "arms")}
                | {"mae": {k: a["mae"] for k, a in arms.items()}}
            )
            print(
                json.dumps(
                    {"group": folder.name, "target": target, "seed": seed, "mae": cells[-1]["mae"]}
                ),
                flush=True,
            )
    inputs.reauthenticate()
    summary = summarize(cells, group)
    old_summary = analysis / f"{ns}-analysis-v1/summary.json"
    if digest(old_summary) != lock["historical_summaries"][ns]:
        raise ValueError("Historical summary changed")
    historical = json.loads(old_summary.read_text())
    for method, old in (("old_fixed", "fixed_retention"), ("old_adaptive", "adaptive")):
        expected = historical["station_first"][f"{budget}/{old}"]["macro_mae_kwh"]
        np.testing.assert_allclose(summary["macro_mae"][method], expected, rtol=1e-10, atol=1e-8)
    save(folder / "summary.json", summary)
    return summary


def summarize(cells: list[dict], group: dict) -> dict:
    """Average paired seeds within stations, then stations; preserve unscored nulls."""
    expected = {(t, s) for t in group["selected_ids"] for s in (42, 43, 44)}
    if {(r["target"], r["seed"]) for r in cells} != expected or len(cells) != len(expected):
        raise ValueError("Incomplete or duplicate group cells")
    methods = list(cells[0]["mae"])
    stations = {}
    for target in group["selected_ids"]:
        rows = [r for r in cells if r["target"] == target]
        if any((r["mae"][m] is None) != (r["scored_days"] == 0) for r in rows for m in methods):
            raise ValueError("Null/coverage mismatch")
        if len({r["scored_days"] for r in rows}) != 1:
            raise ValueError("Seed coverage mismatch")
        stations[target] = {
            m: float(np.mean([r["mae"][m] for r in rows])) if rows[0]["scored_days"] else None
            for m in methods
        }
    means = {
        m: float(np.mean([r[m] for r in stations.values() if r[m] is not None])) for m in methods
    }
    return {
        "namespace": "-".join(group["namespace"]),
        "history_days": group["history_days"],
        "units": len(cells),
        "scored_stations": sum(r["old_fixed"] is not None for r in stations.values()),
        "macro_mae": means,
        "station_means": stations,
        "cells": cells,
    }


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 3:
        raise ValueError("Use one to three bounded CPU workers")
    args.output.mkdir(exist_ok=False, parents=True)
    lock = json.loads(args.lock.read_text())
    access = FinalAccess(ROOT, args.lock, lock["parent_commit"], {})
    access.check()
    started = time.perf_counter()
    save(
        args.output / "registration.json",
        {
            "lock_sha256": digest(args.lock),
            "code_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "runtime": environment("cpu"),
            "jobs": args.jobs,
            "scope": "Owner-authorized follow-up on historical exposed Final cohort; no retuning",
        },
    )
    results = []
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        jobs = [
            pool.submit(
                execute_group,
                i,
                str(args.lock.resolve()),
                str(args.base.resolve()),
                str(args.output.resolve()),
            )
            for i in range(len(lock["groups"]))
        ]
        for future in as_completed(jobs):
            results.append(future.result())
            save(
                args.output / "progress.json", {"completed_groups": len(results), "groups": results}
            )
    results.sort(key=lambda r: (r["namespace"], r["history_days"]))
    wins = {
        m: sum(r["macro_mae"][m] < r["macro_mae"]["old_fixed"] for r in results)
        for m in results[0]["macro_mae"]
        if m != "old_fixed"
    }
    save(
        args.output / "summary.json",
        {
            "status": "completed",
            "groups": results,
            "lower_than_fixed_groups": wins,
            "wall_seconds": time.perf_counter() - started,
        },
    )
    print(
        json.dumps({"completed_groups": len(results), "lower_than_fixed_groups": wins}), flush=True
    )


if __name__ == "__main__":
    main()
