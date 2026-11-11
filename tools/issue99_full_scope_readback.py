"""Independent mixture arithmetic and rolling-state readback for the full follow-up."""

import argparse
import csv
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import torch

from ev_models.checkpoint import digest
from ev_runner.final_gate import FinalAccess
from ev_runner.replay import Replay
from ev_runner.state import state_digest
from tools.issue99_full_scope import summarize
from tools.issue99_full_scope_inputs import FollowupInputs, historical_vectors
from tools.issue99_stable_fast import pair_cell, read_vectors

ROOT = Path(__file__).resolve().parents[1]


def independent_weights(cell: dict, initial: float, eta: float, share: float) -> list[float]:
    """Direct normalized exponential calculation, using only arrived past losses."""
    clocks = [datetime.fromisoformat(o) for o in cell["origins"]]
    arrivals = [datetime.fromisoformat(o) for o in cell["available_at"]]
    stable, fast, labels = (np.asarray(cell[k]) for k in ("stable", "fast", "labels"))
    consumed, weights = set(), []
    weight = initial
    for i, clock in enumerate(clocks):
        for j in sorted(range(i), key=lambda j: (arrivals[j], clocks[j])):
            if j in consumed or arrivals[j] > clock:
                continue
            losses = (
                np.asarray(
                    [np.abs(stable[j] - labels[j]).mean(), np.abs(fast[j] - labels[j]).mean()]
                )
                / cell["scale"]
            )
            losses -= losses.min()
            posterior = np.asarray([weight, 1 - weight]) * np.exp(-eta * losses)
            posterior /= posterior.sum()
            weight = float((1 - share) * posterior[0] + share * posterior[1])
            consumed.add(j)
        weights.append(weight)
    return weights


def verify_fast(folder: Path, inputs: FollowupInputs, target: str, fast: dict) -> int:
    """Rebuild every rolling window and verify the retained model/Adam/RNG snapshot."""
    report = json.loads((folder / "run.json").read_text())
    latest = sorted(folder.glob("tick-*/state.pt"))
    if len(latest) != 1:
        raise ValueError("Exactly one retained final state required")
    commit = json.loads((latest[0].parent / "commit.json").read_text())
    if digest(latest[0]) != commit["files"]["state.pt"]:
        raise ValueError("Final state checksum differs")
    snapshot = torch.load(latest[0], map_location="cpu", weights_only=False)
    if state_digest(snapshot["branch"]) != report["final_state_sha256"]:
        raise ValueError("Final branch digest differs")
    for tensor in snapshot["branch"]["model"].values():
        if not torch.isfinite(tensor).all():
            raise ValueError("Nonfinite model state")
    for state in snapshot["branch"]["optimizer"]["state"].values():
        if any(
            isinstance(value, torch.Tensor) and not torch.isfinite(value).all()
            for value in state.values()
        ):
            raise ValueError("Nonfinite Adam state")
    events = []
    for path in sorted(folder.glob("tick-*/events.jsonl")):
        events.extend(json.loads(line) for line in path.read_text().splitlines())
    updates = [e for e in events if e["event"] == "actual_update"]
    binding = json.loads((folder / "rolling-window-binding.json").read_text())
    if len(updates) != len(binding["updates"]):
        raise ValueError("Rolling audit count differs")
    memory = {r["origin"] for r in inputs.training("final", target)}
    for event, audit in zip(updates, binding["updates"], strict=True):
        origin = audit["arrived_origin"]
        if event["origin"] != origin or origin in memory or origin not in fast:
            raise ValueError("Rolling arrival identity differs")
        memory.add(origin)
        anchor = datetime.fromisoformat(origin)
        expected = sorted(
            o for o in memory if anchor - timedelta(days=6) <= datetime.fromisoformat(o) <= anchor
        )
        if expected != audit["used_origins"] or event["lambda"] != 0:
            raise ValueError("Rolling window or retention differs")
        if any(log["examples"] != len(expected) or log["steps"] != 1 for log in event["logs"]):
            raise ValueError("Rolling optimizer-step accounting differs")
    return len(updates)


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    for key in ("base", "run", "lock", "output"):
        parser.add_argument("--" + key, required=True, type=Path)
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for this task's active producer to commit each group",
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    lock = json.loads(args.lock.read_text())
    registration = json.loads((args.run / "registration.json").read_text())
    if registration["lock_sha256"] != digest(args.lock):
        raise ValueError("Executed lock differs")

    def await_artifact(path: Path) -> None:
        deadline = time.monotonic() + 3600
        while not path.exists():
            if not args.wait or time.monotonic() >= deadline:
                raise FileNotFoundError(path)
            time.sleep(1)

    access = FinalAccess(ROOT, args.lock, lock["parent_commit"], {})
    analysis = args.base / "runs/issue23-final-analysis-20261028-root-v1"
    selection = lock["selection"]
    w = selection["selected_fast"]["static_weight"]
    eta, share = (selection["controller"][k] for k in ("eta", "share"))
    summaries, rows, manifests = [], [], []
    vectors = rolling = nulls = states = 0
    for group in lock["groups"]:
        ns, budget = "-".join(group["namespace"]), group["history_days"]
        folder = args.run / f"{ns}-{budget}d"
        await_artifact(folder / "summary.json")
        inputs = FollowupInputs(
            args.base / "data/inputs/issue18-input-handoff-v1-20261019" / folder.name, group, access
        )
        collection = analysis / f"{ns}-collection-v1.json"
        if digest(collection) != lock["collections"][ns]:
            raise ValueError("Historical collection changed")
        lookup = {
            (r["entity_id"], r["seed"], r["variant"]): r
            for r in json.loads(collection.read_text())
            if r["budget"] == budget
        }
        cells = []
        for target in group["selected_ids"]:
            replay = Replay(inputs, target, 90)
            for seed in (42, 43, 44):
                path = folder / f"cell-{target}-{seed}.json"
                result = json.loads(path.read_text())
                fixed = historical_vectors(lookup[(target, seed, "fixed_retention")], replay)
                adaptive = historical_vectors(lookup[(target, seed, "adaptive")], replay)
                fast_path = Path(result["fast_path"])
                if digest(fast_path / "run.json") != result["fast_report_sha256"]:
                    raise ValueError("Fast report changed")
                fast = read_vectors(fast_path, replay)
                rolling += verify_fast(fast_path, inputs, target, fast)
                states += 1
                stable = {
                    o: {"as_of": r["as_of"], "prediction": r["vectors"][0]}
                    for o, r in fixed["rows"].items()
                }
                if set(stable) != set(fast) or set(stable) != set(adaptive["rows"]):
                    raise ValueError("Score masks differ")
                if result["scored_days"] != len(stable):
                    raise ValueError("Scored count differs")
                if stable:
                    actual_cell = json.loads(json.dumps(pair_cell(stable, fast, replay, None)))
                    if actual_cell != result["cell"]:
                        raise ValueError("Expert vectors or labels differ")
                    cell = result["cell"]
                    weights = independent_weights(cell, w, eta, share)
                    np.testing.assert_allclose(
                        weights, result["arms"]["fixed_share"]["weights"], atol=2e-14, rtol=0
                    )
                    for name, ws in (
                        ("fast_only", [0] * len(weights)),
                        ("static_mix", [w] * len(weights)),
                        ("fixed_share", weights),
                    ):
                        probability = np.asarray(ws)[:, None]
                        predictions = probability * np.asarray(cell["stable"]) + (
                            1 - probability
                        ) * np.asarray(cell["fast"])
                        arm = result["arms"][name]
                        np.testing.assert_allclose(
                            predictions, arm["predictions_kwh"], atol=1e-9, rtol=1e-12
                        )
                        np.testing.assert_allclose(
                            np.abs(predictions - cell["labels"]).mean(),
                            arm["mae"],
                            atol=1e-9,
                            rtol=1e-12,
                        )
                        vectors += len(predictions)
                    for name in ("mean7", "confidence7"):
                        arm = result["arms"][name]
                        # Reconstruct effective forecast choices from recorded decisions.
                        active = 0.1
                        decisions = {d["decision_time"]: d for d in arm["decisions"]}
                        errors = []
                        clock = replay.start
                        while clock < replay.stop:
                            origin = clock.isoformat()
                            if origin in decisions:
                                active = decisions[origin]["selected"]
                            if arm["choices"][origin] != active:
                                raise ValueError("Decision applied at wrong forecast time")
                            if origin in adaptive["rows"]:
                                errors.append(
                                    adaptive["rows"][origin]["mae"][
                                        adaptive["levels"].index(active)
                                    ]
                                )
                            clock += timedelta(days=1)
                        np.testing.assert_allclose(
                            np.mean(errors), arm["mae"], atol=1e-9, rtol=1e-12
                        )
                else:
                    nulls += 1
                    if any(a["mae"] is not None for a in result["arms"].values()):
                        raise ValueError("Null cell was filled")
                for name, value in (("old_fixed", fixed["mae"]), ("old_adaptive", adaptive["mae"])):
                    if value != result["arms"][name]["mae"]:
                        raise ValueError("Historical MAE differs")
                row = {
                    k: result[k]
                    for k in ("namespace", "history_days", "target", "seed", "scored_days")
                }
                row.update({k: a["mae"] for k, a in result["arms"].items()})
                rows.append(row)
                cells.append(
                    {
                        "target": target,
                        "seed": seed,
                        "scored_days": len(stable),
                        "mae": {k: a["mae"] for k, a in result["arms"].items()},
                    }
                )
                manifests.append(
                    {
                        "path": str(path),
                        "sha256": digest(path),
                        "fast_path": str(fast_path),
                        "fast_report_sha256": result["fast_report_sha256"],
                    }
                )
        summary = summarize(cells, group)
        saved = json.loads((folder / "summary.json").read_text())
        if summary["macro_mae"] != saved["macro_mae"]:
            raise ValueError("Group aggregate differs")
        summaries.append(
            {
                k: summary[k]
                for k in ("namespace", "history_days", "units", "scored_stations", "macro_mae")
            }
        )
        inputs.reauthenticate()
        print(json.dumps({"verified_group": folder.name, "units": len(rows)}), flush=True)
    wins = {
        m: sum(g["macro_mae"][m] < g["macro_mae"]["old_fixed"] for g in summaries)
        for m in summaries[0]["macro_mae"]
        if m != "old_fixed"
    }
    await_artifact(args.run / "summary.json")
    original = json.loads((args.run / "summary.json").read_text())
    if wins != original["lower_than_fixed_groups"]:
        raise ValueError("Group win counts differ")
    with (args.output / "cells.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report = {
        "status": "verified",
        "units": len(rows),
        "null_units": nulls,
        "groups": summaries,
        "lower_than_fixed_groups": wins,
        "mixture_daily_vectors_checked": vectors,
        "rolling_updates_checked": rolling,
        "finite_final_states_checked": states,
        "lock_sha256": digest(args.lock),
        "run_summary_sha256": digest(args.run / "summary.json"),
    }
    (args.output / "verification.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    (args.output / "artifact-manifest.json").write_text(json.dumps(manifests, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
