"""Create descriptive #99 Development reports from verified Kaggle artifacts.

This is an after-run reader. It never trains, tunes thresholds, or uses Final.
Stationary bootstrap intervals describe the observed registered daily windows;
they are not an independent test-set claim.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
from datetime import datetime, timedelta
from pathlib import Path

from ev_models.data import InputRun
from ev_runner.replay import Replay
from tools.issue99_persistent_verify import METHODS, SEEDS, TARGETS, vector_error


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def read_run(
    root: Path,
    phase: str,
    method: str,
    target: str,
    seed: int,
    replay: Replay,
    registered: set[str],
) -> tuple[list[dict], list[dict], dict]:
    path = root / phase / f"{method}-{target}-seed{seed}"
    report = read_json(path / "run.json")
    forecasts = {}
    scored = {}
    decisions = []
    event_counts = {}
    for tick in sorted(path.glob("tick-*")):
        issued = read_json(tick / "forecasts.json")
        if issued:
            origin = issued["origin"]
            if origin in forecasts:
                raise ValueError(f"Duplicate issued origin: {path.name} {origin}")
            forecasts[origin] = issued
        for line in (tick / "events.jsonl").read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            kind = event["event"]
            event_counts[kind] = event_counts.get(kind, 0) + 1
            if kind == "score":
                if event["origin"] in scored:
                    raise ValueError(f"Duplicate score: {path.name} {event['origin']}")
                scored[event["origin"]] = event
            elif kind == "meta_decision":
                decisions.append(event)
    daily = []
    for origin in sorted(registered & scored.keys()):
        issued = forecasts[origin]
        event = scored[origin]
        arrived = replay.labels(
            datetime.fromisoformat(origin), datetime.fromisoformat(event["as_of"])
        )
        if arrived.status != "complete" or arrived.values is None:
            raise ValueError(f"Label was not complete on score event: {path.name} {origin}")
        mae, mse = vector_error(issued["prediction"], arrived.values, replay.scale)
        if not math.isclose(mae, event["mae_kwh"], abs_tol=1e-6, rel_tol=1e-6):
            raise ValueError(f"Saved score differs from raw labels: {path.name} {origin}")
        daily.append(
            {
                "phase": phase,
                "target": target,
                "seed": seed,
                "method": method,
                "origin": origin,
                "score_as_of": event["as_of"],
                "mae_kwh": mae,
                "rmse_kwh": math.sqrt(mse),
                "lambda_at_forecast": issued["lambda"],
                "candidate_lambda": issued.get("paired", {}).get("candidate_lambda"),
                "paired_block_id": issued.get("paired", {}).get("block_id"),
            }
        )
    trajectory = [
        {
            "phase": phase,
            "target": target,
            "seed": seed,
            "method": method,
            "origin": origin,
            "lambda_at_forecast": issued["lambda"],
            "candidate_lambda": issued.get("paired", {}).get("candidate_lambda"),
            "paired_block_id": issued.get("paired", {}).get("block_id"),
        }
        for origin, issued in sorted(forecasts.items())
    ]
    artifact_bytes = sum(item.stat().st_size for item in path.rglob("*") if item.is_file())
    cost = {
        "phase": phase,
        "target": target,
        "seed": seed,
        "method": method,
        "invocation_wall_seconds": report["invocation_wall_seconds"],
        "source_load_wall_seconds": report["source_load_wall_seconds_this_invocation"],
        "replay_load_wall_seconds": report["replay_load_wall_seconds_this_invocation"],
        "prefix_load_wall_seconds": report["prefix_load_wall_seconds_this_invocation"],
        "initial_wall_seconds": report["initial_wall_seconds_this_invocation"],
        "gpu_peak_allocated_bytes": report["gpu_peak_allocated_bytes"],
        "gpu_peak_reserved_bytes": report["gpu_peak_reserved_bytes"],
        "actual_steps": report["actual_steps"],
        "virtual_steps": report["virtual_steps"],
        "shadow_steps": report.get("shadow_steps", 0),
        "artifact_bytes": artifact_bytes,
        "registered_scored_days": len(daily),
        "issued_days": report["issued_days"],
        "scored_days": report["scored_days"],
        "proposal_count": event_counts.get("persistent_proposal", 0),
        "accepted_count": sum(bool(event.get("accepted")) for event in decisions),
        "rejected_count": sum(event.get("accepted") is False for event in decisions),
        "timeout_count": event_counts.get("persistent_timeout", 0),
        "skip_count": event_counts.get("persistent_skip", 0),
        "observed_pair_count": event_counts.get("persistent_observation", 0),
        "cost_seconds_json": json.dumps(report["cost_seconds"], sort_keys=True),
        "run_json_sha256": sha256(path / "run.json"),
    }
    return daily, trajectory, cost


def paired_by_cell(rows: list[dict], phase: str) -> dict[tuple[str, int], dict[str, list[dict]]]:
    cells: dict[tuple[str, int], dict[str, list[dict]]] = {}
    for row in rows:
        if row["phase"] == phase:
            cells.setdefault((row["target"], row["seed"]), {}).setdefault(row["method"], []).append(
                row
            )
    for (target, seed), methods in cells.items():
        if set(methods) != set(METHODS):
            raise ValueError(f"Missing paired method: {phase} {target} seed{seed}")
        origins = [{row["origin"] for row in methods[method]} for method in METHODS]
        if any(value != origins[0] for value in origins[1:]):
            raise ValueError(f"Paired scored origins differ: {phase} {target} seed{seed}")
        if not origins[0]:
            raise ValueError(f"No paired scored origins: {phase} {target} seed{seed}")
        for method in METHODS:
            methods[method].sort(key=lambda row: row["origin"])
    if len(cells) != len(TARGETS) * len(SEEDS):
        raise ValueError(f"Expected 12 paired target/seed cells for {phase}")
    for target in TARGETS:
        reference = [row["origin"] for row in cells[(target, SEEDS[0])]["fixed"]]
        for seed in SEEDS[1:]:
            if [row["origin"] for row in cells[(target, seed)]["fixed"]] != reference:
                raise ValueError(f"Seed origin calendars differ within target: {phase} {target}")
    return cells


def stationary_indices(origins: list[str], rng: random.Random, mean_block: int) -> list[int]:
    """Resample within observed calendar runs; gaps and wrap always restart."""
    count = len(origins)
    stamps = [datetime.fromisoformat(origin) for origin in origins]
    index = rng.randrange(count)
    result = []
    for _ in range(count):
        result.append(index)
        next_index = index + 1
        continuous = next_index < count and stamps[next_index] - stamps[index] == timedelta(days=1)
        index = (
            next_index if continuous and rng.random() >= 1 / mean_block else rng.randrange(count)
        )
    return result


def quantile(sorted_values: list[float], fraction: float) -> float:
    position = fraction * (len(sorted_values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    return sorted_values[lower] + (position - lower) * (sorted_values[upper] - sorted_values[lower])


def summarize_phase(
    rows: list[dict], phase: str, seed: int, replicates: int, block_days: int
) -> dict:
    cells = paired_by_cell(rows, phase)
    gap_counts = {}
    for target in TARGETS:
        for source_seed in SEEDS:
            origins = [row["origin"] for row in cells[(target, source_seed)]["fixed"]]
            stamps = [datetime.fromisoformat(origin) for origin in origins]
            gap_counts[f"{target}-seed{source_seed}"] = sum(
                right - left != timedelta(days=1)
                for left, right in zip(stamps, stamps[1:], strict=False)
            )
    cell_means = {
        f"{target}-seed{source_seed}": {
            method: statistics.mean(row["mae_kwh"] for row in cells[(target, source_seed)][method])
            for method in METHODS
        }
        for target in TARGETS
        for source_seed in SEEDS
    }
    macro = {
        method: statistics.mean(
            cell_means[f"{target}-seed{source_seed}"][method]
            for target in TARGETS
            for source_seed in SEEDS
        )
        for method in METHODS
    }
    target_means = {
        target: {
            method: statistics.mean(
                cell_means[f"{target}-seed{source_seed}"][method] for source_seed in SEEDS
            )
            for method in METHODS
        }
        for target in TARGETS
    }
    seed_means = {
        str(source_seed): {
            method: statistics.mean(
                cell_means[f"{target}-seed{source_seed}"][method] for target in TARGETS
            )
            for method in METHODS
        }
        for source_seed in SEEDS
    }
    rng = random.Random(seed + (0 if phase == "calibration" else 1))
    bootstrap = {method: [] for method in METHODS}
    gains = {method: [] for method in METHODS if method != "fixed"}
    for _ in range(replicates):
        sampled = {method: [] for method in METHODS}
        for target in TARGETS:
            shared_origins = [row["origin"] for row in cells[(target, SEEDS[0])]["fixed"]]
            indices = stationary_indices(shared_origins, rng, block_days)
            for source_seed in SEEDS:
                methods = cells[(target, source_seed)]
                for method in METHODS:
                    sampled[method].append(
                        statistics.mean(methods[method][index]["mae_kwh"] for index in indices)
                    )
        means = {method: statistics.mean(sampled[method]) for method in METHODS}
        for method in METHODS:
            bootstrap[method].append(means[method])
        for method in gains:
            gains[method].append(means["fixed"] - means[method])
    intervals = {}
    for key, values in {
        **{f"mae_{method}": value for method, value in bootstrap.items()},
        **{f"fixed_minus_{method}": value for method, value in gains.items()},
    }.items():
        values.sort()
        intervals[key] = [quantile(values, 0.025), quantile(values, 0.975)]
    return {
        "phase": phase,
        "scope": "Exploratory Development; descriptive stationary bootstrap, not held-out inference",
        "bootstrap": {
            "seed": seed,
            "replicates": replicates,
            "mean_block_days": block_days,
            "paired_origin_resampling": True,
            "shared_indices_across_seeds_within_target": True,
            "calendar_gap_counts_by_target_seed": gap_counts,
            "boundary_rule": "Restart at every missing-calendar-day gap and at the end of each registered phase; no circular end-to-start adjacency.",
            "cross_target_dependence_limit": "Targets are resampled separately because their complete-label calendars can differ; intervals may not capture shared shocks across targets.",
        },
        "macro_mae_kwh": macro,
        "fixed_minus_method_kwh": {
            method: macro["fixed"] - macro[method] for method in METHODS if method != "fixed"
        },
        "target_mean_mae_kwh": target_means,
        "seed_macro_mae_kwh": seed_means,
        "cell_mean_mae_kwh": cell_means,
        "descriptive_95pct_intervals_kwh": intervals,
    }


def match_independent(summary: dict, verified: dict, phase: str) -> None:
    """Refuse a report whose raw-vector cells differ from the prior verifier."""
    if verified.get("status") != "PASS" or verified.get("phase") != (
        "evaluation" if phase == "later" else phase
    ):
        raise ValueError(f"Independent {phase} verification is missing or failed")
    rows = verified.get("run_rows", [])
    if len(rows) != len(TARGETS) * len(SEEDS) * len(METHODS):
        raise ValueError(f"Independent {phase} verifier lacks 48 run rows")
    by_key = {(row["target"], row["seed"], row["method"]): row for row in rows}
    if len(by_key) != len(rows):
        raise ValueError(f"Independent {phase} verifier has duplicate cells")
    for target in TARGETS:
        for source_seed in SEEDS:
            cell = summary["cell_mean_mae_kwh"][f"{target}-seed{source_seed}"]
            for method in METHODS:
                expected = by_key[(target, source_seed, method)]["mae_kwh"]
                if not math.isclose(cell[method], expected, abs_tol=1e-9, rel_tol=1e-9):
                    raise ValueError(
                        f"Report cell differs from independent verifier: {phase} {target} seed{source_seed} {method}"
                    )
    for method in METHODS:
        if not math.isclose(
            summary["macro_mae_kwh"][method],
            verified["macro_mae_kwh"][method],
            abs_tol=1e-9,
            rel_tol=1e-9,
        ):
            raise ValueError(f"Report macro differs from independent verifier: {phase} {method}")


def plots(output: Path, daily: list[dict], trajectory: list[dict]) -> list[str]:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    names = []
    for phase in ("calibration", "later"):
        phase_daily = [row for row in daily if row["phase"] == phase]
        if not phase_daily:
            continue
        lookup = {
            (row["target"], row["seed"], row["origin"], row["method"]): row["mae_kwh"]
            for row in phase_daily
        }
        fig, axes = plt.subplots(2, 2, figsize=(11, 7), sharex=False)
        for axis, target in zip(axes.flat, TARGETS, strict=True):
            origins = sorted({row["origin"] for row in phase_daily if row["target"] == target})
            points = []
            for origin in origins:
                pairs = [
                    lookup[(target, seed, origin, "fixed")]
                    - lookup[(target, seed, origin, "persistent")]
                    for seed in SEEDS
                    if (target, seed, origin, "fixed") in lookup
                    and (target, seed, origin, "persistent") in lookup
                ]
                if len(pairs) == len(SEEDS):
                    points.append(statistics.mean(pairs))
            axis.plot(range(len(points)), points, linewidth=1)
            axis.axhline(0, color="black", linewidth=0.5)
            axis.set_title(f"Target {target}")
            axis.set_ylabel("Fixed − persistent MAE (kWh)")
            axis.set_xlabel("Registered origin index")
        fig.tight_layout()
        name = f"{phase}-daily-paired-difference.png"
        fig.savefig(output / name, dpi=150)
        plt.close(fig)
        names.append(name)
        fig, axes = plt.subplots(2, 2, figsize=(11, 7), sharex=False)
        for axis, target in zip(axes.flat, TARGETS, strict=True):
            for seed in SEEDS:
                values = [
                    row["lambda_at_forecast"]
                    for row in trajectory
                    if row["phase"] == phase
                    and row["target"] == target
                    and row["seed"] == seed
                    and row["method"] == "persistent"
                ]
                axis.plot(range(len(values)), values, label=f"seed {seed}", linewidth=1)
            axis.set_title(f"Target {target}")
            axis.set_ylabel("Persistent λ at forecast")
            axis.set_xlabel("Issued origin index")
        axes.flat[0].legend(fontsize=8)
        fig.tight_layout()
        name = f"{phase}-persistent-lambda.png"
        fig.savefig(output / name, dpi=150)
        plt.close(fig)
        names.append(name)
    return names


def markdown(summaries: dict, costs: list[dict], verification: dict, output: Path) -> None:
    lines = [
        "# Issue #99 persistent λ: after-run Development analysis",
        "",
        "All values below come from saved Kaggle forecasts and labels available at each recorded score time. This is exploratory because the Development cohort was previously inspected. Intervals are descriptive stationary bootstrap intervals over the registered time windows; they are not independent confirmation.",
        "",
        f"Independent Calibration integrity: **{verification['status']}**; registered promotion gate: **{verification.get('gate_pass')}**.",
        "",
    ]
    for phase, summary in summaries.items():
        lines += [
            f"## {phase.title()}",
            "",
            "| Method | Macro MAE (kWh) | Fixed minus method (kWh) | Descriptive 95% interval for difference |",
            "|---|---:|---:|---:|",
        ]
        for method in METHODS:
            gain = summary["fixed_minus_method_kwh"].get(method)
            interval = summary["descriptive_95pct_intervals_kwh"].get(f"fixed_minus_{method}")
            lines.append(
                f"| {method} | {summary['macro_mae_kwh'][method]:.6f} | {gain:.6f} | [{interval[0]:.6f}, {interval[1]:.6f}] |"
                if gain is not None
                else f"| {method} | {summary['macro_mae_kwh'][method]:.6f} | — | — |"
            )
        gap_counts = summary["bootstrap"]["calendar_gap_counts_by_target_seed"]
        lines += [
            "",
            "Target means use three seeds each; the macro gives equal weight to the four targets. Each bootstrap replicate uses the same day indices for all methods and seeds within a target, after checking their scored-origin calendars match. Blocks restart at missing calendar days and at phase boundaries; they never wrap the last day to the first. Targets are resampled separately because their complete-label calendars can differ, so intervals may miss shocks shared across targets.",
            "",
            "Calendar gaps among scored origins by target/seed: "
            + ", ".join(f"{key}={value}" for key, value in gap_counts.items())
            + ".",
            "",
        ]
        relevant = [row for row in costs if row["phase"] == phase]
        fixed_wall = sum(
            row["invocation_wall_seconds"] for row in relevant if row["method"] == "fixed"
        )
        persistent_wall = sum(
            row["invocation_wall_seconds"] for row in relevant if row["method"] == "persistent"
        )
        lines += [
            f"Measured persistent/Fixed invocation wall ratio: **{persistent_wall / fixed_wall:.3f}×**. Fixed ran before persistent in Calibration, so cache and GPU warmup can affect this ratio. Per-run VRAM, step counts, event counts, component costs and artifact bytes are in `run-costs.csv`.",
            "",
        ]
    lines += [
        "## Files",
        "",
        "`daily-errors.csv` contains original-unit MAE/RMSE recomputed from the saved 24-hour vectors and arrived labels. `lambda-timeline.csv` lists λ at every issued forecast. `run-costs.csv` records runtime, VRAM, decisions, timeouts and artifact size. `summary.json` contains all cell, target, seed and bootstrap summaries. `artifact-manifest.json` binds this report to file hashes.",
        "",
    ]
    with (output / "report.md").open("x", encoding="utf-8") as stream:
        stream.write("\n".join(lines))


def run(
    root: Path,
    inputs_path: Path,
    protocol_path: Path,
    output: Path,
    *,
    seed: int,
    replicates: int,
    block_days: int,
) -> dict:
    if output.exists():
        raise FileExistsError(output)
    if replicates < 100 or block_days < 1:
        raise ValueError("Need at least 100 bootstrap replicates and positive block length")
    protocol = read_json(protocol_path)
    locked = root / "protocol-lock.json"
    if sha256(locked) != sha256(protocol_path):
        raise ValueError("Protocol differs from run lock")
    verification = read_json(root / "independent-verification.json")
    if verification.get("status") != "PASS" or verification.get("protocol_sha256") != sha256(
        locked
    ):
        raise ValueError("Independent Calibration integrity audit is absent or mismatched")
    later_path = root / "later"
    if later_path.exists():
        later = read_json(root / "later-independent-verification.json")
        if later.get("status") != "PASS" or later.get("protocol_sha256") != sha256(locked):
            raise ValueError("Independent Later integrity audit is absent or mismatched")
    inputs = InputRun(inputs_path, protocol["input_manifest_sha256"])
    replays = {target: Replay(inputs, target, 90) for target in TARGETS}
    daily, trajectory, costs = [], [], []
    phases = ("calibration", "later") if later_path.exists() else ("calibration",)
    for phase in phases:
        origins = protocol[
            "calibration_origins" if phase == "calibration" else "evaluation_origins"
        ]
        for target in TARGETS:
            for source_seed in SEEDS:
                for method in METHODS:
                    a, b, c = read_run(
                        root,
                        phase,
                        method,
                        target,
                        source_seed,
                        replays[target],
                        set(origins[target]),
                    )
                    daily.extend(a)
                    trajectory.extend(b)
                    costs.append(c)
    summaries = {
        phase: summarize_phase(daily, phase, seed, replicates, block_days) for phase in phases
    }
    match_independent(summaries["calibration"], verification, "calibration")
    if later_path.exists():
        match_independent(summaries["later"], later, "later")
    output.mkdir(parents=True, exist_ok=False)
    write_csv(
        output / "daily-errors.csv",
        daily,
        [
            "phase",
            "target",
            "seed",
            "method",
            "origin",
            "score_as_of",
            "mae_kwh",
            "rmse_kwh",
            "lambda_at_forecast",
            "candidate_lambda",
            "paired_block_id",
        ],
    )
    write_csv(
        output / "lambda-timeline.csv",
        trajectory,
        [
            "phase",
            "target",
            "seed",
            "method",
            "origin",
            "lambda_at_forecast",
            "candidate_lambda",
            "paired_block_id",
        ],
    )
    write_csv(output / "run-costs.csv", costs, list(costs[0]))
    summary = {
        "schema": "issue99-persistent-after-run-report-v1",
        "scope": "Exploratory Development only; no Final replay",
        "protocol_sha256": sha256(locked),
        "independent_calibration_verification_sha256": sha256(
            root / "independent-verification.json"
        ),
        "independent_later_verification_sha256": sha256(
            root / "later-independent-verification.json"
        )
        if later_path.exists()
        else None,
        "phases": summaries,
        "run_count": len(costs),
        "daily_row_count": len(daily),
    }
    write_json(output / "summary.json", summary)
    plot_names = plots(output, daily, trajectory)
    markdown(summaries, costs, verification, output)
    manifest = {
        "schema": "issue99-persistent-after-run-manifest-v1",
        "files": [
            {"path": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in sorted(output.iterdir())
            if path.is_file()
        ],
        "plots": plot_names,
    }
    write_json(output / "artifact-manifest.json", manifest)
    print(
        json.dumps(
            {
                "status": "PREPARED_FROM_VERIFIED_RUNS",
                "run_count": len(costs),
                "daily_rows": len(daily),
                "phases": list(summaries),
                "macro_mae_kwh": {
                    phase: summary["macro_mae_kwh"] for phase, summary in summaries.items()
                },
                "report": str(output),
                "artifact_manifest_sha256": sha256(output / "artifact-manifest.json"),
            },
            allow_nan=False,
        ),
        flush=True,
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-seed", type=int, default=20261110)
    parser.add_argument("--bootstrap-replicates", type=int, default=2000)
    parser.add_argument("--mean-block-days", type=int, default=7)
    args = parser.parse_args()
    run(
        args.root,
        args.inputs,
        args.protocol,
        args.output,
        seed=args.bootstrap_seed,
        replicates=args.bootstrap_replicates,
        block_days=args.mean_block_days,
    )


if __name__ == "__main__":
    main()
