"""Predeclared three-budget Development replay/resume, no local training entry point."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from ev_models.checkpoint import digest, write_json


def run_matrix(inputs_root: Path, source: Path, source_sha: str, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    repo = Path(__file__).resolve().parents[1]
    config = repo / "configs/issue21/development-smoke.json"
    results = []
    commands = []

    def call(days, name, extra=()):
        inputs = inputs_root / f"urbanev-SZH-{days}d"
        destination = output / name
        command = [
            sys.executable,
            "-m",
            "ev_runner.run",
            "--inputs",
            str(inputs),
            "--manifest-sha256",
            digest(inputs / "manifest.json"),
            "--source",
            str(source),
            "--source-sha256",
            source_sha,
            "--config",
            str(config),
            "--output",
            str(destination),
            "--entity-id",
            "1001",
            *extra,
        ]
        commands.append(command)
        with (output / f"{name}.log").open("x") as stream:
            subprocess.run(command, cwd=repo, stdout=stream, stderr=subprocess.STDOUT, check=True)
        result = json.loads((destination / "run.json").read_text())
        print(
            json.dumps(
                {
                    k: result[k]
                    for k in (
                        "run_id",
                        "issued_days",
                        "scored_days",
                        "candidate_steps",
                        "audit_steps",
                        "elapsed_seconds",
                    )
                }
            ),
            flush=True,
        )
        results.append(result)
        return result

    for days in (7, 14, 28):
        whole = call(days, f"target1001-{days}d-whole")
        if days == 7:
            call(days, "target1001-7d-partial", ("--stop-after-ticks", "10"))
            resumed = call(
                days,
                "target1001-7d-resumed",
                ("--resume-from", str(output / "target1001-7d-partial")),
            )
            if any(
                whole[k] != resumed[k]
                for k in ("prediction_identity_sha256", "final_branch_state_sha256", "decisions")
            ):
                raise ValueError("GPU resumed forecasts/state/decisions differ")
    main_runs = [r for r in results if r["run_id"].endswith("whole")]
    total_days = sum(r["scored_days"] for r in main_runs)
    seconds = sum(r["elapsed_seconds"] for r in main_runs)
    cost = {
        "scope": "planning estimate from one target/seed; not a locked Final matrix or measured baseline suite",
        "measured_target_days": total_days,
        "measured_three_candidate_seconds": seconds,
        "seconds_per_target_day_including_initialization_io_checkpoints": seconds / total_days
        if total_days
        else None,
        "formula": "observed seconds/target-day x target-days x seeds x method-equivalent cost; source training and baseline/ablation differences must be measured separately",
        "projection_example": {
            "target_count": 100,
            "stream_days": 29,
            "budgets": 3,
            "seeds": 3,
            "methods": 10,
            "all_methods_assumed_three_candidate_equivalent_seconds": seconds
            / total_days
            * 100
            * 29
            * 3
            * 3
            * 10
            if total_days
            else None,
            "limitation": "Illustrative capacity scenario, not cohort selection or official matrix. Methods have different costs; no claimed upper bound. Excludes extra source/tuning/ablation runs and hardware variability.",
        },
    }
    write_json(
        output / "matrix.json",
        {
            "scope": "Development technical smoke only",
            "commands": commands,
            "runs": results,
            "cost_estimate": cost,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs-root", "source", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    args = parser.parse_args()
    run_matrix(
        args.inputs_root.resolve(), args.source.resolve(), args.source_sha256, args.output.resolve()
    )
