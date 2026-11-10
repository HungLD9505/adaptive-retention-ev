"""Independent saved-vector and arrived-label audit for #99 persistent-lambda runs."""

import argparse
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path

from ev_models.checkpoint import digest
from ev_models.data import InputRun
from ev_runner.continuous_run import code_identity
from ev_runner.replay import Replay
from ev_runner.state import state_digest

TARGETS = ("1405", "2152", "1153", "1693")
SEEDS = (42, 43, 44)
METHODS = ("lambda0", "fixed", "immediate", "persistent")
SOURCE_SHA256 = {
    42: "a3d3485d8d9a3e96c0483ab61e659e3a31b0f9bd62cc51ae6b77c0d204920d8b",
    43: "2ad6ed33fb7e692eae5f8db6be075ce43564851f70390d19edb4314052a17f5f",
    44: "6f475e54768322c5b51f5837d6ce7e863cb9ef6d33aec05b4a1c2468cd0285a5",
}


def close(actual: float, expected: float, *, tolerance: float = 1e-9) -> bool:
    return math.isfinite(actual) and abs(actual - expected) <= tolerance


def prediction_id(origin: str, prediction: list[float]) -> str:
    value = {"origin": origin, "prediction": prediction}
    raw = (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def vector_error(
    prediction: list[float], labels: tuple[float, ...], scale: float
) -> tuple[float, float]:
    if len(prediction) != 24 or any(not math.isfinite(value) for value in prediction):
        raise ValueError("Invalid saved 24-hour forecast vector")
    errors = [value * scale - label for value, label in zip(prediction, labels, strict=True)]
    return sum(abs(error) for error in errors) / 24, sum(error * error for error in errors) / 24


def pilot_screen(rows: list[dict], cases: tuple[tuple[str, int], ...], max_case_harm_kwh: float) -> tuple[dict[str, float], float, bool]:
    """Screen actual paired trajectories; shadow forecasts never enter this gate."""
    by_key = {(row["target"], row["seed"], row["method"]): row for row in rows}
    harm: dict[str, float] = {}
    for target, seed in cases:
        fixed = by_key[(target, seed, "fixed")]
        persistent = by_key[(target, seed, "persistent")]
        if fixed["all_scored_origins"] != persistent["all_scored_origins"] or not fixed["all_scored_origins"]:
            raise ValueError("Pilot lacks nonempty paired complete scored origins")
        a, b = persistent["all_scored_mae_kwh"], fixed["all_scored_mae_kwh"]
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) or not (math.isfinite(a) and math.isfinite(b)):
            raise ValueError("Pilot actual trajectory MAE is missing or nonfinite")
        harm[f"{target}-seed{seed}"] = a - b
    maximum = max(harm.values())
    return harm, maximum, maximum <= max_case_harm_kwh


def committed_ticks(run_path: Path, report: dict) -> list[Path]:
    if json.loads((run_path / "binding.json").read_text()) != report["binding"]:
        raise ValueError("Run and saved binding differ")
    if list(run_path.glob(".pending-*")):
        raise ValueError("Uncommitted tick remains")
    ticks = sorted(run_path.glob("tick-*"))
    if not ticks:
        raise ValueError("Run has no committed ticks")
    previous = "0" * 64
    latest_only = report["binding"]["config"].get("state_retention") == "latest"
    for index, tick in enumerate(ticks):
        if tick.name != f"tick-{index:04d}":
            raise ValueError("Tick order or count differs")
        commit = json.loads((tick / "commit.json").read_text())
        if (
            commit["index"] != index
            or commit["previous"] != previous
            or set(commit["files"]) != {"state.pt", "events.jsonl", "forecasts.json"}
        ):
            raise ValueError("Broken tick commit chain")
        for filename, expected in commit["files"].items():
            path = tick / filename
            if (
                filename == "state.pt"
                and latest_only
                and index < len(ticks) - 1
                and not path.exists()
            ):
                continue
            if digest(path) != expected:
                raise ValueError(f"Changed committed {filename}")
        previous = digest(tick / "commit.json")
    if report["commit_chain"] != previous:
        raise ValueError("Run report differs from final commit")
    return ticks


def verify_binding(
    report: dict,
    method: str,
    target: str,
    seed: int,
    inputs: InputRun,
    protocol: dict,
    protocol_sha: str,
    phase: str,
) -> None:
    binding = report["binding"]
    config = binding["config"]
    expected_lambda = 0.0 if method == "lambda0" else protocol["persistent_rule"]["anchor"]
    if (
        report["run_id"] != f"{method}-{target}-seed{seed}"
        or report["phase"] != phase
        or config["phase"] != phase
        or config["protocol_sha256"] != protocol_sha
        or config["objective_origins"]
        != (
            []
            if phase == "pilot"
            else protocol[
                "calibration_origins" if phase == "calibration" else "evaluation_origins"
            ][target]
        )
        or config["initial_lambda"] != expected_lambda
        or config["initial_training"]["seed"] != seed
        or config["online_training"]["seed"] != seed
        or config["frozen_lambda"] != (method in {"lambda0", "fixed"})
        or config.get("controller_variant", "immediate")
        != ("persistent_v1" if method == "persistent" else "immediate")
        or binding["input"] != inputs.binding("target", target, SOURCE_SHA256[seed])
        or binding["source_population_sha256"] != protocol["source_population_sha256"]
    ):
        raise ValueError("Run identity, source, config, or objective differs")
    if method == "persistent" and config.get("persistent_rule") != protocol["persistent_rule"]:
        raise ValueError("Persistent rule differs from protocol")
    if method != "persistent" and "persistent_rule" in config:
        raise ValueError("Nonpersistent run contains persistent rule")
    if report["scheduled_days"] != 90:
        raise ValueError("Wrong replay schedule")


def verify_persistent_events(
    events: list[dict],
    forecasts: dict[str, dict],
    forecast_hashes: dict[str, str],
    scored: set[str],
    replay: Replay,
    rule: dict,
    upper_bound: float,
) -> dict:
    proposals: dict[int, dict] = {}
    observations: dict[int, list[float]] = {}
    decisions = 0
    acceptances = 0
    observed_pairs = 0
    shadow_updates = 0
    paired_differences: list[float] = []
    for event in events:
        kind = event["event"]
        if kind == "persistent_proposal":
            block = event["block_id"]
            if block in proposals:
                raise ValueError("Duplicate persistent block")
            lower = max(0.0, rule["anchor"] - rule["anchor_trust_radius"])
            upper = min(upper_bound, rule["anchor"] + rule["anchor_trust_radius"])
            step = max(
                -rule["max_abs_lambda_step"],
                min(rule["max_abs_lambda_step"], rule["eta"] * event["hypergradient"]),
            )
            candidate = max(lower, min(upper, event["incumbent"] - step))
            if not close(event["candidate"], candidate, tolerance=1e-12):
                raise ValueError("Persistent proposal differs from locked rule")
            proposals[block] = event
            observations[block] = []
        elif kind == "persistent_observation":
            block = event["block_id"]
            origin = event["origin"]
            issued = forecasts.get(origin)
            paired = issued.get("paired") if issued else None
            if (
                block not in proposals
                or paired is None
                or paired["block_id"] != block
                or origin not in scored
            ):
                raise ValueError("Persistent observation lacks issued pair")
            if event["forecast_sha256"] != forecast_hashes[origin] or paired[
                "candidate_prediction_id"
            ] != prediction_id(origin, paired["candidate_prediction"]):
                raise ValueError("Persistent pair changed after forecast issuance")
            as_of = datetime.fromisoformat(event["as_of"])
            labels = replay.labels(datetime.fromisoformat(origin), as_of)
            if labels.status != "complete" or labels.values is None or labels.available_at is None:
                raise ValueError("Persistent observation lacks arrived complete labels")
            if (
                labels.available_at > as_of
                or event["available_at"] != labels.available_at.isoformat()
            ):
                raise ValueError("Persistent observation used early label")
            incumbent, _ = vector_error(issued["prediction"], labels.values, replay.scale)
            candidate, _ = vector_error(paired["candidate_prediction"], labels.values, replay.scale)
            difference = candidate - incumbent
            if not all(
                close(actual, expected)
                for actual, expected in (
                    (event["incumbent_mae_kwh"], incumbent),
                    (event["candidate_mae_kwh"], candidate),
                    (event["candidate_minus_incumbent_mae_kwh"], difference),
                )
            ):
                raise ValueError("Persistent observed metric differs from vectors and labels")
            observations[block].append(difference)
            observed_pairs += 1
            paired_differences.append(difference)
        elif kind == "meta_decision" and "candidate_lambda" in event:
            block = event["block_id"]
            values = observations.get(block)
            if values is None or len(values) != rule["valid_complete_pairs"]:
                raise ValueError("Persistent decision lacks exactly K completed pairs")
            mean = sum(values) / len(values)
            wins = sum(value < 0 for value in values)
            maximum = max(values)
            accepted = (
                mean < rule["mean_candidate_minus_incumbent_mae_kwh_below"]
                and wins >= rule["minimum_candidate_wins"]
                and maximum <= rule["max_candidate_harm_kwh"]
            )
            proposal = proposals[block]
            if (
                event["accepted"] != accepted
                or not close(event["mean_candidate_minus_incumbent_mae_kwh"], mean)
                or event["candidate_wins"] != wins
                or not close(event["max_candidate_harm_kwh"], maximum)
                or event["real_state_before"] != event["real_state_after"]
                or set(event["real_state_before"]) != {"model_sha256", "adam_sha256", "rng_sha256"}
                or set(event["candidate_state"]) != {"model_sha256", "adam_sha256", "rng_sha256"}
                or any(
                    len(value) != 64
                    for value in (
                        *event["real_state_before"].values(),
                        *event["candidate_state"].values(),
                    )
                )
                or event["lambda_before"] != proposal["incumbent"]
                or event["candidate_lambda"] != proposal["candidate"]
                or event["lambda_after"]
                != (proposal["candidate"] if accepted else proposal["incumbent"])
                or len(event["paired_differences_kwh"]) != len(values)
                or any(
                    not close(a, b)
                    for a, b in zip(event["paired_differences_kwh"], values, strict=True)
                )
            ):
                raise ValueError("Persistent acceptance or lambda-only state differs")
            decisions += 1
            acceptances += accepted
            del observations[block]
        elif kind == "persistent_shadow_update":
            if event["real_steps"] != event["shadow_steps"]:
                raise ValueError("Shadow and primary update counts differ")
            shadow_updates += 1
    return {
        "proposals": len(proposals),
        "observed_pairs": observed_pairs,
        "decisions": decisions,
        "acceptances": acceptances,
        "shadow_updates": shadow_updates,
        "paired_differences_kwh": paired_differences,
    }


def verify_run(
    run_path: Path,
    method: str,
    target: str,
    seed: int,
    inputs: InputRun,
    replay: Replay,
    protocol: dict,
    protocol_sha: str,
    phase: str,
) -> dict:
    report = json.loads((run_path / "run.json").read_text())
    verify_binding(report, method, target, seed, inputs, protocol, protocol_sha, phase)
    if (
        report["binding"]["code"] != code_identity()
        or report["binding"]["source_population_sha256"] != inputs.source_hash
        or report["initial_logs"] != json.loads((run_path / "initial-adaptation.json").read_text())
        or report["binding"]["initial_adaptation_sha256"] != state_digest(report["initial_logs"])
    ):
        raise ValueError("Code, Source population, or initial adaptation binding differs")
    forecasts: dict[str, dict] = {}
    forecast_hashes: dict[str, str] = {}
    events: list[dict] = []
    for tick in committed_ticks(run_path, report):
        issued = json.loads((tick / "forecasts.json").read_text())
        tick_events = [
            json.loads(line) for line in (tick / "events.jsonl").read_text().splitlines()
        ]
        if issued:
            origin = issued["origin"]
            if origin in forecasts:
                raise ValueError("Duplicate issued origin")
            forecasts[origin] = issued
            forecast_hashes[origin] = digest(tick / "forecasts.json")
            saved = [row for row in tick_events if row["event"] == "forecast_saved"]
            if (
                len(saved) != 1
                or saved[0]["origin"] != origin
                or saved[0]["prediction_sha256"] != forecast_hashes[origin]
            ):
                raise ValueError("Issued forecast and saved event differ")
        events.extend(tick_events)
    scored: dict[str, tuple[float, float]] = {}
    for event in events:
        if event["event"] != "score":
            continue
        origin = event["origin"]
        if (
            origin in scored
            or origin not in forecasts
            or event["prediction_sha256"] != forecast_hashes[origin]
        ):
            raise ValueError("Duplicate, unissued or changed score")
        as_of = datetime.fromisoformat(event["as_of"])
        label = replay.labels(datetime.fromisoformat(origin), as_of)
        if (
            label.status != "complete"
            or label.values is None
            or label.available_at is None
            or label.available_at > as_of
        ):
            raise ValueError("Score used unavailable/incomplete label")
        value = vector_error(forecasts[origin]["prediction"], label.values, replay.scale)
        if not close(event["mae_kwh"], value[0]) or not close(event["mse_kwh2"], value[1]):
            raise ValueError("Score differs from independently recomputed vector error")
        scored[origin] = value
    requested = (
        set()
        if phase == "pilot"
        else set(
            protocol["calibration_origins" if phase == "calibration" else "evaluation_origins"][
                target
            ]
        )
    )
    selected = requested & scored.keys()
    minimum = 0 if phase == "pilot" else protocol["minimum_scored_days"][phase][target]
    if (
        len(selected) < minimum
        or report["issued_days"] != len(forecasts)
        or report["scored_days"] != len(scored)
        or report["objective_requested_days"] != len(requested)
        or report["objective_scored_days"] != len(selected)
        or set(report["objective_missing_origins"]) != requested - selected
        or (phase != "pilot" and not report["objective_coverage_pass"])
    ):
        raise ValueError("Objective coverage differs")
    if phase == "pilot" and (
        len(list(run_path.glob("tick-*"))) != 22 or report["objective_coverage_pass"]
    ):
        raise ValueError("Pilot is not exactly 22 unscored ticks")
    mae = sum(scored[origin][0] for origin in selected) / len(selected) if selected else None
    rmse = (
        math.sqrt(sum(scored[origin][1] for origin in selected) / len(selected))
        if selected
        else None
    )
    if phase == "pilot" and (report["mae_kwh"] is not None or report["rmse_kwh"] is not None):
        raise ValueError("Pilot has a scored objective")
    if phase != "pilot" and (
        not close(report["mae_kwh"], mae) or not close(report["rmse_kwh"], rmse)
    ):
        raise ValueError("Objective differs from saved vectors and arrived labels")
    persistent = (
        verify_persistent_events(
            events,
            forecasts,
            forecast_hashes,
            set(scored),
            replay,
            protocol["persistent_rule"],
            report["binding"]["config"]["window_rule"]["upper_bound"],
        )
        if method == "persistent"
        else None
    )
    if persistent is not None and report["controller_decisions"] != persistent["decisions"]:
        raise ValueError("Persistent decision count differs from report")
    return {
        "run_id": report["run_id"],
        "target": target,
        "seed": seed,
        "method": method,
        "mae_kwh": mae,
        "rmse_kwh": rmse,
        "all_scored_mae_kwh": sum(value[0] for value in scored.values()) / len(scored) if scored else None,
        "scored_origins": sorted(selected),
        "all_scored_origins": sorted(scored),
        "issued_days": len(forecasts),
        "scored_days": len(scored),
        "wall_seconds": report["invocation_wall_seconds"],
        "source_checkpoint_sha256": report["binding"]["input"]["source_checkpoint_sha256"],
        "initial_adaptation_sha256": report["binding"]["initial_adaptation_sha256"],
        "first_forecast_sha256": forecast_hashes[min(forecasts)],
        "code_sha256": hashlib.sha256(
            json.dumps(report["binding"]["code"], sort_keys=True).encode()
        ).hexdigest(),
        "code_commit": report["binding"]["code"]["commit"],
        "environment": report["binding"]["environment"],
        "persistent": persistent,
    }


def verify_matrix(root: Path, inputs: InputRun, protocol_path: Path, phase_name: str) -> dict:
    protocol = json.loads(protocol_path.read_text())
    protocol_sha = digest(protocol_path)
    if phase_name not in {"pilot", "calibration", "evaluation"}:
        raise ValueError("Unknown verification phase")
    phase = root / ("later" if phase_name == "evaluation" else phase_name)
    pilot_cases = (("1405", 42), ("2152", 43), ("1693", 42))
    expected = (
        {
            f"{method}-{target}-seed{seed}"
            for method in ("fixed", "persistent")
            for target, seed in pilot_cases
        }
        if phase_name == "pilot"
        else {
            f"{method}-{target}-seed{seed}"
            for method in METHODS
            for target in TARGETS
            for seed in SEEDS
        }
    )
    found = {path.name for path in phase.iterdir() if path.is_dir()}
    if found != expected:
        raise ValueError(
            f"Calibration matrix differs: missing={sorted(expected - found)}, extra={sorted(found - expected)}"
        )
    replay = {target: Replay(inputs, target, 90) for target in TARGETS}
    rows = []
    cases = (
        [
            (method, target, seed)
            for target, seed in pilot_cases
            for method in ("fixed", "persistent")
        ]
        if phase_name == "pilot"
        else [(method, target, seed) for method in METHODS for target in TARGETS for seed in SEEDS]
    )
    for method, target, seed in cases:
        rows.append(
            verify_run(
                phase / f"{method}-{target}-seed{seed}",
                method,
                target,
                seed,
                inputs,
                replay[target],
                protocol,
                protocol_sha,
                phase_name,
            )
        )
    if phase_name == "pilot":
        by_key = {(row["target"], row["seed"], row["method"]): row for row in rows}
        for target, seed in pilot_cases:
            fixed = by_key[(target, seed, "fixed")]
            persistent = by_key[(target, seed, "persistent")]
            if (
                fixed["source_checkpoint_sha256"] != persistent["source_checkpoint_sha256"]
                or fixed["code_sha256"] != persistent["code_sha256"]
                or fixed["initial_adaptation_sha256"] != persistent["initial_adaptation_sha256"]
                or fixed["first_forecast_sha256"] != persistent["first_forecast_sha256"]
                or fixed["all_scored_origins"] != persistent["all_scored_origins"]
            ):
                raise ValueError("Pilot paired source, prefix, or scored origins differ")
        technical = {
            key: sum(row["persistent"][key] for row in rows if row["method"] == "persistent")
            for key in ("proposals", "observed_pairs", "decisions", "shadow_updates")
        }
        trajectory_harm, maximum_harm, screen_pass = pilot_screen(
            rows, pilot_cases, protocol["persistent_experiment"]["pilot_max_case_harm_kwh"]
        )
        return {
            "schema": "issue99-persistent-independent-verification-v1",
            "phase": "pilot",
            "status": "PASS" if screen_pass else "PILOT_HARM_STOP",
            "screen_pass": screen_pass,
            "persistent_minus_fixed_trajectory_mae_kwh": trajectory_harm,
            "max_trajectory_harm_kwh": maximum_harm,
            "protocol_sha256": protocol_sha,
            "runs_verified": len(rows),
            "run_rows": rows,
            "technical_counts": technical,
        }
    by_key = {(row["target"], row["seed"], row["method"]): row for row in rows}
    for target in TARGETS:
        for seed in SEEDS:
            groups = [set(by_key[(target, seed, method)]["scored_origins"]) for method in METHODS]
            if any(group != groups[0] for group in groups[1:]):
                raise ValueError("Paired methods scored different complete origins")
            bindings = [by_key[(target, seed, method)] for method in METHODS]
            if (
                len({row["source_checkpoint_sha256"] for row in bindings}) != 1
                or len({row["code_sha256"] for row in bindings}) != 1
            ):
                raise ValueError("Paired source or code identity differs")
            nonzero = [
                by_key[(target, seed, method)] for method in ("fixed", "immediate", "persistent")
            ]
            if (
                len({row["initial_adaptation_sha256"] for row in nonzero}) != 1
                or len({row["first_forecast_sha256"] for row in nonzero}) != 1
            ):
                raise ValueError("Paired Fixed/controller prefix differs")
    target_means = {
        method: {
            target: sum(by_key[(target, seed, method)]["mae_kwh"] for seed in SEEDS) / len(SEEDS)
            for target in TARGETS
        }
        for method in METHODS
    }
    macro = {method: sum(target_means[method].values()) / len(TARGETS) for method in METHODS}
    if phase_name == "evaluation":
        return {
            "schema": "issue99-persistent-independent-verification-v1",
            "phase": "evaluation",
            "status": "PASS",
            "protocol_sha256": protocol_sha,
            "runs_verified": len(rows),
            "run_rows": rows,
            "target_mean_mae_kwh": target_means,
            "macro_mae_kwh": macro,
            "persistent_minus_fixed_target_mae_kwh": {
                target: target_means["persistent"][target] - target_means["fixed"][target]
                for target in TARGETS
            },
            "persistent_gain_vs_fixed_kwh": macro["fixed"] - macro["persistent"],
        }
    seed_macro = {
        method: {
            seed: sum(by_key[(target, seed, method)]["mae_kwh"] for target in TARGETS)
            / len(TARGETS)
            for seed in SEEDS
        }
        for method in METHODS
    }
    gate_rule = protocol["persistent_experiment"]["go_to_later_gate"]
    gain = macro["fixed"] - macro["persistent"]
    harm = {
        target: target_means["persistent"][target] - target_means["fixed"][target]
        for target in TARGETS
    }
    improved_seeds = sum(
        seed_macro["persistent"][seed] < seed_macro["fixed"][seed] for seed in SEEDS
    )
    persistent_wall = sum(row["wall_seconds"] for row in rows if row["method"] == "persistent")
    fixed_wall = sum(row["wall_seconds"] for row in rows if row["method"] == "fixed")
    ratio = persistent_wall / fixed_wall
    checks = {
        "macro_gain": gain >= gate_rule["macro_mae_improvement_vs_fixed_at_least_kwh"],
        "target_harm": max(harm.values()) <= gate_rule["max_target_mean_mae_harm_vs_fixed_kwh"],
        "seed_macro": improved_seeds >= gate_rule["min_seed_macro_improvements_vs_fixed"],
        "wall_ratio": ratio <= gate_rule["persistent_wall_time_over_fixed_max"],
        "coverage": True,
    }
    gate_path = root / "calibration-gate.json"
    gate = json.loads(gate_path.read_text())
    if (
        gate.get("protocol_sha256") != protocol_sha
        or gate.get("checks") != checks
        or gate.get("go_to_later") != all(checks.values())
        or gate.get("failures") != []
    ):
        raise ValueError("Registered calibration gate differs from independent vector audit")
    return {
        "schema": "issue99-persistent-independent-verification-v1",
        "phase": "calibration",
        "status": "PASS",
        "gate_pass": all(checks.values()),
        "calibration_gate_sha256": digest(gate_path),
        "protocol_sha256": protocol_sha,
        "runs_verified": len(rows),
        "run_rows": rows,
        "target_mean_mae_kwh": target_means,
        "macro_mae_kwh": macro,
        "seed_macro_mae_kwh": seed_macro,
        "persistent_minus_fixed_target_mae_kwh": harm,
        "persistent_gain_vs_fixed_kwh": gain,
        "improved_seeds": improved_seeds,
        "persistent_over_fixed_wall_ratio": ratio,
        "gate_checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=("pilot", "calibration", "evaluation"), required=True)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text())
    inputs = InputRun(args.inputs, protocol["input_manifest_sha256"])
    report = verify_matrix(args.root, inputs, args.protocol, args.phase)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(
        json.dumps(
            {
                key: report[key]
                for key in ("status", "phase", "runs_verified", "gate_pass")
                if key in report
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
