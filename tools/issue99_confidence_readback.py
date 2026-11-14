"""Normalized-score causal readback of a common retention bank and target-only."""

import argparse
import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import numpy as np

from ev_control.confidence import ControllerConfig, DailyScore
from ev_models.checkpoint import digest
from ev_runner.replay import Replay
from tools.issue99_confidence_evidence import LEVELS, policy_replay
from tools.issue99_retention_screen import INPUT_SHA
from tools.issue99_study_support import PreparedInputs

ROOT = Path(__file__).resolve().parents[1]


def authenticated_scores(folder: Path, replay: Replay) -> dict:
    """Read predictions and recompute each score after its labels were available."""
    forecasts = {}
    for path in folder.glob("tick-*/forecasts.json"):
        value = json.loads(path.read_text())
        if value:
            if value["origin"] in forecasts:
                raise ValueError("Duplicate forecast origin")
            forecasts[value["origin"]] = (value["prediction"], digest(path))
    rows = {}
    for path in sorted(folder.glob("tick-*/events.jsonl")):
        for event in map(json.loads, path.read_text().splitlines()):
            if event["event"] != "score":
                continue
            origin = event["origin"]
            if origin in rows:
                raise ValueError("Duplicate score")
            vector, fingerprint = forecasts[origin]
            if fingerprint != event["prediction_sha256"]:
                raise ValueError("Prediction changed")
            labels = replay.labels(
                datetime.fromisoformat(origin), datetime.fromisoformat(event["as_of"])
            )
            if labels.status != "complete":
                raise ValueError("Unavailable score labels")
            mae = (
                sum(abs(p * replay.scale - y) for p, y in zip(vector, labels.values, strict=True))
                / 24
            )
            if abs(mae - event["mae_kwh"]) > 1e-9:
                raise ValueError("Prediction/label score mismatch")
            rows[origin] = event
    return rows


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
    calibration = ("1405", "2152", "1153", "1693")
    inputs = PreparedInputs(args.input, INPUT_SHA, targets=calibration + targets)
    protocol = json.loads(
        (ROOT / "docs/reports/issue99-study-20261110/protocol-lock.json").read_text()
    )
    evidence = {}
    verified = 0
    calibration_means = {level: [] for level in LEVELS}
    for target in calibration + targets:
        replay = Replay(inputs, target, 90)
        for seed in (42, 43, 44):
            bank = {}
            for level in LEVELS:
                bank[level] = authenticated_scores(
                    args.run / f"bank-{target}-{seed}-{level:g}", replay
                )
                verified += len(bank[level])
            if any(set(bank[level]) != set(bank[0.0]) for level in LEVELS):
                raise ValueError("Bank masks differ")
            rows = [
                DailyScore(
                    datetime.fromisoformat(origin),
                    datetime.fromisoformat(origin),
                    datetime.fromisoformat(bank[0.0][origin]["as_of"]),
                    24,
                    tuple(bank[level][origin]["mae_kwh"] / replay.scale for level in LEVELS),
                    replay.scale_id,
                    tuple(bank[level][origin]["prediction_sha256"] for level in LEVELS),
                )
                for origin in sorted(bank[0.0])
            ]
            evidence[(target, seed)] = (rows, replay.scale, replay.scale_id)
            if target in calibration:
                selected = [
                    r
                    for r in rows
                    if r.origin.isoformat() in protocol["calibration_origins"][target]
                ]
                for level in LEVELS:
                    calibration_means[level].append(
                        sum(r.mae[LEVELS.index(level)] * replay.scale for r in selected)
                        / len(selected)
                    )
    means = {k: sum(v) / len(v) for k, v in calibration_means.items()}
    selected_fixed = min(means, key=means.get)
    original = json.loads((args.run / "fixed-lock.json").read_text())
    if selected_fixed != original["selected"] or any(
        abs(means[k] - original["means"][str(k)]) > 1e-9 for k in LEVELS
    ):
        raise ValueError("Calibration lock readback mismatch")
    results = []
    for target in targets:
        replay = Replay(inputs, target, 90)
        for seed in (42, 43, 44):
            rows, scale, scale_id = evidence[(target, seed)]
            config = ControllerConfig(0.1, 1.0, 0.1, 7, 5, 0, 0.05, 3, 2000, seed)
            arms = {
                name: policy_replay(
                    rows,
                    config,
                    replay.start,
                    replay.stop,
                    f"common-bank/{target}/{seed}",
                    scale_id,
                    gate,
                    scale=scale,
                )
                for name, gate in (("mean_only", False), ("confidence_gate", True))
            }
            for name, gate in (
                ("mean_only_fixed_start", False),
                ("confidence_gate_fixed_start", True),
            ):
                arms[name] = policy_replay(
                    rows,
                    replace(config, initial_lambda=selected_fixed),
                    replay.start,
                    replay.stop,
                    f"common-bank/{target}/{seed}",
                    scale_id,
                    gate,
                    scale=scale,
                )
            for name, level in (("source_finetune", 0.0), ("fixed_bank", selected_fixed)):
                errors = [
                    {
                        "origin": r.origin.isoformat(),
                        "lambda": level,
                        "mae_kwh": r.mae[LEVELS.index(level)] * scale,
                    }
                    for r in rows
                ]
                arms[name] = {
                    "mae": sum(r["mae_kwh"] for r in errors) / len(errors),
                    "errors": errors,
                }
            folder = args.run / f"target-only-{target}-{seed}"
            binding = json.loads((folder / "binding.json").read_text())
            if (
                binding.get("source_initialization") is not False
                or binding["config"]["initial_lambda"] != 0
            ):
                raise ValueError("Target-only initialization binding missing")
            random = authenticated_scores(folder, replay)
            verified += len(random)
            if set(random) != {r.origin.isoformat() for r in rows}:
                raise ValueError("Random target mask differs")
            arms["target_only"] = {
                "mae": sum(r["mae_kwh"] for r in random.values()) / len(random),
                "errors": [{"origin": k, "mae_kwh": v["mae_kwh"]} for k, v in random.items()],
            }
            results.append({"target": target, "seed": seed, "arms": arms})
    methods = list(results[0]["arms"])
    stations = {
        t: {m: sum(c["arms"][m]["mae"] for c in results if c["target"] == t) / 3 for m in methods}
        for t in targets
    }
    macro = {m: float(np.mean([v[m] for v in stations.values()])) for m in methods}
    audit = {
        "accepted_beneficial": 0,
        "accepted_harmful": 0,
        "rejected_beneficial": 0,
        "rejected_harmful": 0,
        "no_future_labels": 0,
        "no_recommendation": 0,
    }
    reduce = []
    for c in results:
        for d in c["arms"]["confidence_gate"]["decisions"]:
            if d["recommended"] == d["active_before"]:
                audit["no_recommendation"] += 1
            elif not d["future_days"]:
                audit["no_future_labels"] += 1
            else:
                accepted = d["selected"] != d["active_before"]
                benefit = d["future_recommendation_minus_hold"] < 0
                audit[
                    ("accepted_" if accepted else "rejected_")
                    + ("beneficial" if benefit else "harmful")
                ] += 1
                if d["recommended"] < d["active_before"]:
                    reduce.append(d["future_recommendation_minus_hold"])
    rng = np.random.default_rng(20261110)
    strata = [
        [r["entity_id"] for r in inventory["selected"] if r["stratum"] == q] for q in range(4)
    ]
    contrasts = []
    for method, baseline in (
        ("source_finetune", "target_only"),
        ("fixed_bank", "target_only"),
        ("confidence_gate", "mean_only"),
        ("confidence_gate", "fixed_bank"),
        ("mean_only", "fixed_bank"),
        ("confidence_gate_fixed_start", "mean_only_fixed_start"),
        ("confidence_gate_fixed_start", "fixed_bank"),
        ("mean_only_fixed_start", "fixed_bank"),
    ):
        samples = np.zeros(20000)
        for group in strata:
            delta = np.array([stations[t][method] - stations[t][baseline] for t in group])
            samples += delta[rng.integers(0, len(group), (20000, len(group)))].sum(1) / 12
        contrasts.append(
            {
                "method": method,
                "baseline": baseline,
                "delta_kwh": macro[method] - macro[baseline],
                "stations_improved": sum(
                    stations[t][method] < stations[t][baseline] for t in targets
                ),
                "lower": float(np.quantile(samples, 0.025)),
                "upper": float(np.quantile(samples, 0.975)),
            }
        )
    subgroups = {
        str(q): {m: float(np.mean([stations[t][m] for t in group])) for m in methods}
        for q, group in enumerate(strata)
    }
    summary = {
        "status": "passed",
        "verified_saved_scores": verified,
        "fixed_bank_level": selected_fixed,
        "macro_mae": macro,
        "station_means": stations,
        "contrasts": contrasts,
        "gate_audit": audit,
        "lower_retention_recommendations_with_future_labels": len(reduce),
        "lower_retention_beneficial": sum(v < 0 for v in reduce),
        "prefix_strata": subgroups,
        "scope": "Normalized-score common-bank causal selection; exposed Development; target-only matched adaptation budget, no convergence tuning",
        "original_registration_sha256": digest(args.run / "registration.json"),
        "readback_script_sha256": digest(Path(__file__)),
        "policy_script_sha256": digest(ROOT / "tools/issue99_confidence_evidence.py"),
    }
    inputs.reauthenticate()
    (args.output / "results.json").write_text(json.dumps(results, indent=2))
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
