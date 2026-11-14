"""Locked new-entity stable/fast execution with causal matched mixture readback."""

import argparse
import json
import multiprocessing
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import torch

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
from ev_runner.continuous_run import code_identity
from ev_runner.replay import Replay
from ev_runner.state import Branch, rng_state, state_digest
from ev_runner.store import Store
from tools.issue99_stable_fast import pair_cell, read_vectors
from tools.issue99_study_support import PreparedInputs

ROOT = Path(__file__).resolve().parents[1]
DAY = timedelta(days=1)


def save(path: Path, value: object) -> None:
    """Write a new immutable JSON result, refusing replacement."""
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def run_expert(
    inputs: PreparedInputs,
    replay: Replay,
    source_path: Path,
    source_sha256: str,
    output: Path,
    *,
    seed: int,
    fast: bool,
    protocol_sha256: str,
) -> dict:
    """Use the frozen Source10 recipe and the existing chronological runner."""
    started = time.perf_counter()
    source, _, checkpoint = load_checkpoint(source_path, sha256=source_sha256, device="cpu")
    meta = checkpoint["metadata"]
    if (
        checkpoint["completed_epochs"] != 10
        or meta["source_population_sha256"] != inputs.source_hash
        or meta["training_config"]["seed"] != seed
    ):
        raise ValueError("Namespace-specific Source10 identity mismatch")
    seed_everything(seed)
    model, reference = adapt_model(source), frozen_reference(source)
    latent = checkpoint["latent_scale"]
    if latent is None or latent.shape != (64,) or not torch.isfinite(latent).all():
        raise ValueError("Invalid frozen source latent scale")
    coefficient = 0.0 if fast else 1.0
    initial = TrainingConfig(seed=seed, epochs=3)
    online = TrainingConfig(seed=seed, epochs=1)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    prefix = inputs.training("development", replay.entity_id)
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
            retention_weight=coefficient,
        )
        for e in range(3)
        if prefix
    ]
    memory = {r["origin"]: r for r in prefix}
    update_origins = []

    def rolling_epoch(target, adam, records, training, **kwargs):
        if len(records) != 1 or records[0]["origin"] in memory:
            raise ValueError("Exactly one new complete arrived day is required")
        current = records[0]
        memory[current["origin"]] = current
        anchor = datetime.fromisoformat(current["origin"])
        ready = [
            r
            for stamp, r in sorted(memory.items())
            if anchor - 6 * DAY <= datetime.fromisoformat(stamp) <= anchor
        ]
        if not ready or len(ready) > training.batch_size:
            raise ValueError("Rolling seven-calendar-day window must fit one optimizer step")
        update_origins.append({"arrived": current["origin"], "used": [r["origin"] for r in ready]})
        return train_epoch(target, adam, ready, training, **kwargs)

    binding = {
        "schema": "new-entity-confirmation-run-v1",
        "protocol_sha256": protocol_sha256,
        "input": inputs.binding("target", replay.entity_id, source_sha256),
        "source_population_sha256": inputs.source_hash,
        "config": {
            "state_retention": "latest",
            "seed": seed,
            "initial": initial.as_dict(),
            "online": online.as_dict(),
            "lambda": coefficient,
            "rolling_days": 7 if fast else None,
        },
        "environment": environment("cpu"),
        "code": code_identity(),
    }
    store = Store(output, binding)
    save(output / "initial-adaptation.json", logs)
    branch = Branch(model, optimizer, rng_state())
    branch.steps = sum(row["steps"] for row in logs)
    # No hypergradient is evaluated: this rule only supplies validated fixed-domain metadata.
    rule = WindowRule(2, 1, 33.84424612726798, 211.29500343057222, 0.001)
    runner = ContinuousRunner(
        replay,
        branch,
        reference,
        latent,
        rule,
        online,
        store,
        initial_lambda=coefficient,
        device="cpu",
        cadence=1,
        frozen_lambda=True,
    )
    end = replay.stop + (int(replay.delay.total_seconds() // DAY.total_seconds()) + 1) * DAY
    if fast:
        with patch("ev_runner.state.train_epoch", rolling_epoch):
            runner.run_until(end)
    else:
        runner.run_until(end)
    if runner.virtual_steps != 0:
        raise ValueError("Unexpected coefficient tuning in frozen expert recipe")
    vectors = read_vectors(output, replay)
    save(
        output / "run.json",
        {
            "binding": binding,
            "initial_steps": sum(row["steps"] for row in logs),
            "online_steps": runner.actual_steps,
            "actual_cost": runner.cost,
            "scored_days": len(vectors),
            "scheduled_days": 90,
            "wall_seconds": time.perf_counter() - started,
            "final_state_sha256": state_digest(runner.branch.snapshot()),
            "source_frozen_sha256": runner.source_state_sha256,
        },
    )
    if fast:
        save(
            output / "rolling-window-binding.json",
            {
                "window_days": 7,
                "lambda": 0.0,
                "updates": update_origins,
                "resume": "Fresh execution only; rolling memory resume is not supported",
            },
        )
    return vectors


def execute_group(
    protocol_path: str, input_parent: str, base_path: str, output_root: str, index: int
) -> dict:
    """Execute one namespace in an isolated single-thread process."""
    torch.set_num_threads(1)
    protocol_path = Path(protocol_path)
    protocol = json.loads(protocol_path.read_text())
    group = protocol["groups"][index]
    output = Path(output_root) / group["namespace"]
    output.mkdir(exist_ok=False)
    inputs = PreparedInputs(
        Path(input_parent) / (group["namespace"] + "-14d"),
        group["input_manifest_sha256"],
        targets=tuple(group["selected_ids"]),
    )
    if inputs.source_hash != group["source_population_sha256"]:
        raise ValueError("Source population differs from the locked namespace")
    cells = []
    for target in group["selected_ids"]:
        replay = Replay(inputs, target, 90)
        for seed in protocol["seeds"]:
            before = time.perf_counter()
            source = group["sources"][str(seed)]
            source_path = Path(base_path) / source["path"]
            stable = run_expert(
                inputs,
                replay,
                source_path,
                source["sha256"],
                output / f"stable-{target}-{seed}",
                seed=seed,
                fast=False,
                protocol_sha256=digest(protocol_path),
            )
            fast = run_expert(
                inputs,
                replay,
                source_path,
                source["sha256"],
                output / f"fast-{target}-{seed}",
                seed=seed,
                fast=True,
                protocol_sha256=digest(protocol_path),
            )
            if set(stable) != set(fast):
                raise ValueError("Expert scoring masks differ")
            cell = pair_cell(stable, fast, replay, None) if stable else None
            arms = {}
            if cell is not None:
                for name, weight in (
                    ("fixed", 1.0),
                    ("fast_only", 0.0),
                    ("static", protocol["recipe"]["initial_weight"]),
                ):
                    arms[name] = forecast_mixture(cell, weight)
                arms["adaptive"] = forecast_mixture(
                    cell,
                    protocol["recipe"]["initial_weight"],
                    eta=protocol["recipe"]["eta"],
                    share=protocol["recipe"]["share"],
                )
            else:
                arms = {
                    name: {"mae": None} for name in ("fixed", "fast_only", "static", "adaptive")
                }
            result = {
                "namespace": group["namespace"],
                "target": target,
                "seed": seed,
                "history_days": 14,
                "scored_days": len(stable),
                "scheduled_days": 90,
                "protocol_sha256": digest(protocol_path),
                "cell": cell,
                "arms": arms,
                "wall_seconds": time.perf_counter() - before,
                "mixture_scope": "Offline causal replay of issued expert forecasts; no physical online issuance claim",
            }
            path = output / f"cell-{target}-{seed}.json"
            save(path, result)
            cells.append(
                {"path": str(path), "sha256": digest(path), "target": target, "seed": seed}
            )
            print(
                json.dumps(
                    {
                        "completed": group["namespace"],
                        "target": target,
                        "seed": seed,
                        "scored_days": len(stable),
                        "elapsed_seconds": result["wall_seconds"],
                    }
                ),
                flush=True,
            )
    inputs.reauthenticate()
    save(output / "manifest.json", cells)
    return {
        "namespace": group["namespace"],
        "cells": len(cells),
        "manifest_sha256": digest(output / "manifest.json"),
    }


def validate_recipe(lock: dict) -> None:
    """Reject any change to the previously selected expert or weighting recipe."""
    expected = {
        "initial_weight": 0.4307815378871372,
        "eta": 0.1,
        "share": 0.1,
        "stable_lambda": 1.0,
        "fast_lambda": 0.0,
        "fast_window_days": 7,
        "initial_epochs": 3,
        "online_epochs": 1,
        "learning_rate": 0.001,
        "batch_size": 64,
    }
    if lock["recipe"] != expected or any(isinstance(v, bool) for v in lock["recipe"].values()):
        raise ValueError("Confirmation cannot retune the frozen historical recipe")
    if lock["seeds"] != [42, 43, 44] or lock["history_days"] != 14 or lock["scheduled_days"] != 90:
        raise ValueError("Paired seeds, prefix or horizon differ from the registered task")
    for group in lock["groups"]:
        ids = group["selected_ids"]
        if (
            not ids
            or len(ids) != len(set(ids))
            or len(ids) > 10
            or any(not str(i).isdigit() for i in ids)
        ):
            raise ValueError("Invalid unique bounded confirmation cohort")
        if set(group["sources"]) != {"42", "43", "44"}:
            raise ValueError("Incomplete namespace-specific Source10 set")


def validate_lock(path: Path) -> dict:
    """Require a committed lock and exact executed source hashes before any target IO."""
    relative = path.resolve().relative_to(ROOT).as_posix()
    committed = subprocess.check_output(["git", "show", f"HEAD:{relative}"], cwd=ROOT)
    if committed != path.read_bytes():
        raise ValueError("Protocol must be committed unchanged before execution")
    lock = json.loads(committed)
    if lock["schema"] != "new-entity-confirmation-lock-v1" or not lock["execution_authorized"]:
        raise ValueError("Explicit confirmation execution lock required")
    for name, sha in lock["executed_code_sha256"].items():
        if digest(ROOT / name) != sha:
            raise ValueError("Executed code changed after the confirmation lock")
    validate_recipe(lock)
    return lock


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--input-parent", type=Path, required=True)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    lock = validate_lock(args.protocol)
    args.output.mkdir(parents=True, exist_ok=False)
    save(
        args.output / "execution.json",
        {
            "protocol_sha256": digest(args.protocol),
            "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "workers": args.workers,
            "environment": environment("cpu"),
        },
    )
    failures, groups = [], []
    with ProcessPoolExecutor(
        max_workers=args.workers, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        futures = {
            pool.submit(
                execute_group,
                str(args.protocol.resolve()),
                str(args.input_parent.resolve()),
                str(args.base.resolve()),
                str(args.output.resolve()),
                index,
            ): index
            for index in range(len(lock["groups"]))
        }
        for future in as_completed(futures):
            try:
                groups.append(future.result())
            except Exception as error:
                failures.append({"group_index": futures[future], "error": repr(error)})
    save(
        args.output / "completion.json",
        {
            "complete_groups": groups,
            "failures": failures,
            "complete": not failures and len(groups) == len(lock["groups"]),
        },
    )
    if failures:
        raise RuntimeError(f"Confirmation groups failed: {failures}")


if __name__ == "__main__":
    main()
