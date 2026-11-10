"""Read-only paired-origin MAE and decision audit for the bounded #99 pilot."""

import argparse
import json
import math
from pathlib import Path


CASES = (("1405", 42), ("2152", 43), ("1693", 42))


def events(run: Path) -> list[dict]:
    return [
        json.loads(line)
        for tick in sorted(run.glob("tick-*"))
        for line in (tick / "events.jsonl").read_text().splitlines()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    protocol = json.loads(args.protocol.read_text())
    rows = []
    for target, seed in CASES:
        scores = {}
        details = {}
        for arm in ("fixed", "paired"):
            run = args.root / f"pilot-{arm}-{target}-{seed}-v1"
            report = json.loads((run / "run.json").read_text())
            stream = events(run)
            allowed = set(protocol["calibration_origins"][target])
            scored = [event for event in stream if event["event"] == "score" and event["origin"] in allowed]
            by_origin = {event["origin"]: event for event in scored}
            if len(by_origin) != len(scored):
                raise ValueError(f"Duplicate score origin in {run}")
            scores[arm] = by_origin
            decisions = [event for event in stream if event["event"] == "meta_decision"]
            observations = [event for event in stream if event["event"] == "paired_observation"]
            for observation in observations:
                score = by_origin.get(observation["origin"])
                if score is None or observation["forecast_sha256"] != score["prediction_sha256"]:
                    raise ValueError(f"Unbound paired observation in {run}")
                if not math.isclose(observation["incumbent_mae_kwh"], score["mae_kwh"], abs_tol=1e-8):
                    raise ValueError(f"Paired incumbent MAE differs from issued score in {run}")
                delta = observation["candidate_mae_kwh"] - observation["incumbent_mae_kwh"]
                if not math.isclose(delta, observation["candidate_minus_incumbent_mae_kwh"], abs_tol=1e-8):
                    raise ValueError(f"Incorrect paired MAE difference in {run}")
            details[arm] = {
                "run": str(run),
                "issued_days": report["issued_days"],
                "scored_days": report["scored_days"],
                "proposals": sum(event["event"] == "paired_proposal" for event in stream),
                "paired_observations": len(observations),
                "accepted": sum(bool(event["accepted"]) for event in decisions),
                "rejected": sum(not event["accepted"] for event in decisions),
                "timeouts": sum(event["event"] == "paired_block_timeout" for event in stream),
                "mismatch_skips": sum(event["event"] == "paired_skip" and event.get("reason") == "incumbent_shadow_mismatch" for event in stream),
                "virtual_steps": report["virtual_steps"],
                "final_lambda": report["final_lambda"],
                "invocation_wall_seconds": report["invocation_wall_seconds"],
                "gpu_peak_allocated_bytes": report["gpu_peak_allocated_bytes"],
                "commit_chain": report["commit_chain"],
            }
        if set(scores["fixed"]) != set(scores["paired"]):
            raise ValueError(f"Unpaired scored origins: {target}/{seed}")
        origins = sorted(scores["fixed"])
        if not origins:
            raise ValueError(f"No scored Calibration origins: {target}/{seed}")
        fixed = sum(scores["fixed"][origin]["mae_kwh"] for origin in origins) / len(origins)
        paired = sum(scores["paired"][origin]["mae_kwh"] for origin in origins) / len(origins)
        rows.append({
            "target": target,
            "seed": seed,
            "paired_days": len(origins),
            "origins": origins,
            "fixed_mae_kwh": fixed,
            "paired_mae_kwh": paired,
            "delta_paired_minus_fixed_kwh": paired - fixed,
            "arms": details,
        })
    result = {
        "schema": "issue99-paired-pilot-audit-v1",
        "rows": rows,
        "case_mean_delta_kwh": sum(row["delta_paired_minus_fixed_kwh"] for row in rows) / len(rows),
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
