"""Reproducible controller fixtures; never a research effectiveness experiment."""

import argparse
import hashlib
import json
import platform
import subprocess
import time
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ev_control.confidence import ControllerConfig, DailyScore, decide


def run(config_path: Path, output: Path) -> dict:
    """Write a new fixture-only run directory, refusing to overwrite evidence."""
    config_bytes = config_path.read_bytes()
    config = ControllerConfig(**json.loads(config_bytes))
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    day = timedelta(days=1)
    start = datetime(2022, 12, 1, tzinfo=timezone(timedelta(hours=8)))
    rows = [
        DailyScore(
            start + i * day,
            start + i * day,
            start + (i + 1) * day,
            24,
            (3.0, 2.0, 1.0),
            "synthetic-fixed-scale",
            tuple(f"synthetic/{i}/{level}" for level in range(3)),
        )
        for i in range(config.block_days)
    ]
    cases = {
        "switch_high": (rows, config.lambda_low, config.lambda_high),
        "zero_active": (rows, 0.0, config.lambda_high),
        "switch_zero": (
            [replace(r, mae=(1.0, 2.0, 3.0)) for r in rows],
            config.lambda_high,
            0.0,
        ),
        "equal_keep": (
            [replace(r, mae=(2.0, 2.0, 2.0)) for r in rows],
            config.lambda_low,
            config.lambda_low,
        ),
        "insufficient": (
            rows[: config.min_valid_days - 1],
            config.lambda_low,
            config.lambda_low,
        ),
        "all_missing": ([], config.lambda_low, config.lambda_low),
    }
    # This declared smoke suite expects delta < 1 for its unit improvements.
    if config.delta >= 1:
        raise ValueError("Smoke fixture requires delta < 1; use the supplied example config")
    results = {}
    for name, (scores, active, expected) in cases.items():
        decision = decide(
            scores,
            config=config,
            active_lambda=active,
            block_start=start,
            as_of=start + config.block_days * day,
            stream_id=f"fixture/{name}",
            scale_id="synthetic-fixed-scale",
        )
        if decision.selected_lambda != expected:
            raise AssertionError(f"{name}: unexpected selected level")
        results[name] = decision.as_dict()
    evidence = {
        "run_id": output.name,
        "scope": "synthetic fixtures only; no training, data, Final or efficacy evaluation",
        "code_sha": sha,
        "working_tree_dirty": dirty,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "config": asdict(config),
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "module_sha256": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (Path("ev_control/confidence.py"), Path(__file__))
        },
        "cases_passed": len(results),
        "decisions": results,
        "runtime_seconds": time.perf_counter() - started,
    }
    (output / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence = run(args.config, args.output)
    print(json.dumps({key: evidence[key] for key in ("run_id", "code_sha", "cases_passed")}))


if __name__ == "__main__":
    main()
