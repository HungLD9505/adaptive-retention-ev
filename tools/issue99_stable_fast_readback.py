"""Authenticate expert runs and independently recompute their causal blend scores."""

import argparse
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from ev_control.expert_mix import forecast_mixture
from ev_models.checkpoint import digest
from ev_runner.replay import Replay
from tools.issue99_history_study import CALIBRATION
from tools.issue99_retention_screen import INPUT_SHA
from tools.issue99_stable_fast import pair_cell, read_vectors
from tools.issue99_study_support import PreparedInputs


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    for key in ("input", "run", "output"):
        parser.add_argument("--" + key, required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    registration = json.loads((args.run / "registration.json").read_text())
    lock = json.loads((args.run / "selection-lock.json").read_text())
    results = json.loads((args.run / "results.json").read_text())
    original = json.loads((args.run / "summary.json").read_text())
    assert digest(args.run / "registration.json") == lock["registration_sha256"]
    assert digest(args.run / "results.json") == original["results_sha256"]
    targets = tuple(registration["evaluation_targets"])
    inputs = PreparedInputs(args.input, INPUT_SHA, targets=CALIBRATION + targets)
    replays = {t: Replay(inputs, t, 90) for t in CALIBRATION + targets}
    updates = 0
    authenticated_runs = 0
    for folder in sorted(args.run.iterdir()):
        if not folder.is_dir() or not (folder / "rolling-window-binding.json").exists():
            continue
        target = folder.name.split("-")[-2]
        read_vectors(folder, replays[target])
        authenticated_runs += 1
        binding = json.loads((folder / "rolling-window-binding.json").read_text())
        memory = {r["origin"] for r in inputs.training("development", target)}
        events = []
        for path in sorted(folder.glob("tick-*/events.jsonl")):
            events.extend(json.loads(line) for line in path.read_text().splitlines())
        scores = {e["origin"]: e for e in events if e["event"] == "score"}
        actual = [e for e in events if e["event"] == "actual_update"]
        assert len(actual) == len(binding["updates"])
        for update, event in zip(binding["updates"], actual, strict=True):
            origin = update["arrived_origin"]
            assert origin == event["origin"] and origin not in memory
            assert event["lambda"] == 0 and all(x["steps"] == 1 for x in event["logs"])
            clock = datetime.fromisoformat(origin)
            as_of = datetime.fromisoformat(scores[origin]["as_of"])
            assert replays[target].labels(clock, as_of) is not None
            assert as_of >= clock + timedelta(days=1)
            memory.add(origin)
            lower = clock - timedelta(days=binding["window_days"] - 1)
            expected = sorted(o for o in memory if lower <= datetime.fromisoformat(o) <= clock)
            assert update["used_origins"] == expected
            assert all(x["examples"] == len(expected) for x in event["logs"])
            updates += 1
    rows = []
    prediction_count = 0
    weight_count = 0
    for result in results:
        target, seed, cell = result["target"], result["seed"], result["cell"]
        stable = read_vectors(
            Path(registration["stable_root"]) / f"bank-{target}-{seed}-1", replays[target]
        )
        fast = read_vectors(args.run / f"evaluation-{target}-{seed}", replays[target])
        assert json.loads(json.dumps(pair_cell(stable, fast, replays[target], None))) == cell
        weight = lock["selected_fast"]["static_weight"]
        eta, share = (lock["controller"][k] for k in ("eta", "share"))
        stable, fast, labels = (np.asarray(cell[k]) for k in ("stable", "fast", "labels"))
        clocks = [datetime.fromisoformat(o) for o in cell["origins"]]
        arrivals = [datetime.fromisoformat(o) for o in cell["available_at"]]
        used = set()
        weights = []
        for i, clock in enumerate(clocks):
            for j in sorted(range(i), key=lambda j: (arrivals[j], clocks[j])):
                if j in used or arrivals[j] > clock:
                    continue
                loss = (
                    np.asarray(
                        [np.abs(stable[j] - labels[j]).mean(), np.abs(fast[j] - labels[j]).mean()]
                    )
                    / cell["scale"]
                )
                loss -= loss.min()
                probability = np.asarray([weight, 1 - weight]) * np.exp(-eta * loss)
                probability /= probability.sum()
                weight = float((1 - share) * probability[0] + share * probability[1])
                used.add(j)
                weight_count += 1
            weights.append(weight)
        np.testing.assert_allclose(
            weights, result["arms"]["fixed_share"]["weights"], rtol=0, atol=2e-14
        )
        for name, arm in result["arms"].items():
            ws = np.asarray(weights if name == "fixed_share" else arm["weights"])[:, None]
            vectors = ws * stable + (1 - ws) * fast
            np.testing.assert_allclose(vectors, arm["predictions_kwh"], rtol=0, atol=1e-10)
            mae = float(np.abs(vectors - labels).mean())
            assert abs(mae - arm["mae"]) < 1e-10
            prediction_count += len(vectors)
        # Final parsed-clock implementation must reproduce original executed outputs.
        recalculated = forecast_mixture(
            cell, lock["selected_fast"]["static_weight"], eta=eta, share=share
        )
        assert recalculated == result["arms"]["fixed_share"]
        rows.append(
            {
                "target": target,
                "seed": seed,
                "days": len(clocks),
                **{k: a["mae"] for k, a in result["arms"].items()},
            }
        )
    inputs.reauthenticate()
    with (args.output / "cells.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    methods = list(results[0]["arms"])
    means = {m: float(np.mean([r[m] for r in rows])) for m in methods}
    assert means == original["macro_mae"]
    station_wins = {}
    for comparator in ("stable_fixed", "static_mix", "fast_only"):
        differences = [
            np.mean([r["fixed_share"] - r[comparator] for r in rows if r["target"] == t])
            for t in targets
        ]
        station_wins[comparator] = {
            "lower": int(sum(x < 0 for x in differences)),
            "higher": int(sum(x > 0 for x in differences)),
        }
    report = {
        "status": "verified",
        "scope": registration["scope"],
        "macro_mae": means,
        "station_wins": station_wins,
        "authenticated_fast_runs": authenticated_runs,
        "rolling_updates_checked": updates,
        "independent_weight_updates": weight_count,
        "forecast_day_vectors_checked": prediction_count,
        "daily_expert_oracle_mae_hindsight_only": float(
            np.mean([r["daily_expert_oracle_mae"] for r in results])
        ),
        "registration_sha256": digest(args.run / "registration.json"),
        "results_sha256": digest(args.run / "results.json"),
        "final_mix_code_sha256": digest(
            Path(__file__).resolve().parents[1] / "ev_control/expert_mix.py"
        ),
        "executed_mix_code_sha256": registration["mix_code_sha256"],
    }
    (args.output / "verification.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
