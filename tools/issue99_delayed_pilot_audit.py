"""Independently summarize the bounded #99 delayed-controller pilot."""

import argparse
import json
from pathlib import Path


CASES = (("1405", 42), ("2152", 43), ("1693", 42))


def read_events(run: Path) -> list[dict]:
    events = []
    for tick in sorted(run.glob("tick-*")):
        events.extend(json.loads(line) for line in (tick / "events.jsonl").read_text().splitlines())
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate", choices=("delayed", "delayed-strong"), default="delayed")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    protocol = json.loads(args.protocol.read_text())
    rows = []
    for target, seed in CASES:
        runs = {
            arm: args.root / f"pilot-{run_arm}-{target}-{seed}-v1"
            for arm, run_arm in (("fixed", "fixed"), ("delayed", args.candidate))
        }
        scores = {}
        details = {}
        for arm, run in runs.items():
            report = json.loads((run / "run.json").read_text())
            events = read_events(run)
            selected = set(protocol["calibration_origins"][target])
            score_rows = [e for e in events if e["event"] == "score" and e["origin"] in selected]
            by_origin = {e["origin"]: e["mae_kwh"] for e in score_rows}
            if len(by_origin) != len(score_rows):
                raise ValueError(f"Duplicate score origin: {run}")
            scores[arm] = by_origin
            decisions = [e for e in events if e["event"] == "meta_decision"]
            details[arm] = {
                "run": str(run),
                "issued_days": report["issued_days"],
                "scored_days": report["scored_days"],
                "decisions": len(decisions),
                "gate_passes": sum(bool(e.get("gate_pass")) for e in decisions),
                "virtual_steps": report["virtual_steps"],
                "final_lambda": report["final_lambda"],
                "invocation_wall_seconds": report["invocation_wall_seconds"],
                "commit_chain": report["commit_chain"],
            }
        if set(scores["fixed"]) != set(scores["delayed"]):
            raise ValueError(f"Unpaired score origins: {target}/{seed}")
        origins = sorted(scores["fixed"])
        if not origins:
            raise ValueError(f"No Calibration scores: {target}/{seed}")
        fixed = sum(scores["fixed"][origin] for origin in origins) / len(origins)
        delayed = sum(scores["delayed"][origin] for origin in origins) / len(origins)
        rows.append({
            "target": target,
            "seed": seed,
            "paired_calibration_origins": origins,
            "paired_days": len(origins),
            "fixed_mae_kwh": fixed,
            "delayed_mae_kwh": delayed,
            "delta_delayed_minus_fixed_kwh": delayed - fixed,
            "arms": details,
        })
    result = {
        "schema": "issue99-delayed-pilot-screen-summary-v1",
        "candidate": args.candidate,
        "rows": rows,
        "case_mean_delta_kwh": sum(r["delta_delayed_minus_fixed_kwh"] for r in rows) / len(rows),
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
