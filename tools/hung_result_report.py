"""Write small provisional Markdown/CSV/JSON reports; no GitHub publication."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from tools.hung_results import file_sha, verified_file


def publish_report(result: dict, directory: Path, source_sha: str) -> dict:
    if result.get("scope") != "development_only":
        raise ValueError("Development-only results required")
    directory.mkdir(parents=True, exist_ok=False)
    methods = defaultdict(lambda: {"runs": 0, "scorable": 0, "scored_days": 0, "requested_days": 0})
    for run in result["runs"]:
        row = methods[run["method"]]
        row["runs"] += 1
        row["scorable"] += run["metrics"] is not None
        row["scored_days"] += run["coverage"]["scored"]
        row["requested_days"] += run["coverage"]["requested"]
    summary = {
        "schema": "hung-development-report-v2",
        "scope": "development_only",
        "acceptance": result["acceptance"],
        "result_sha256": source_sha,
        "catalog_sha256": result["catalog_sha256"],
        "counts": result["counts"],
        "method_coverage": dict(methods),
        "paired_cells": len(result["paired_cells"]),
        "blocked_pair_reasons": dict(Counter(r["reason"] for r in result["blocked_pairs"])),
        "station_first": result["station_first"],
        "aggregation": result["aggregation"],
        "code_commits": sorted({r["code_commit"] for r in result["runs"]}),
        "run_manifest_pins": [
            {
                "job_id": r["job_id"],
                "status": r["status"],
                "sha256": r["manifest"]["sha256"],
                "checkpoint_sha256": r["checkpoint"]["sha256"],
            }
            for r in result["runs"]
        ],
    }
    with (directory / "summary.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(summary, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
    rows = []
    for row in summary["station_first"]:
        rows.append(
            {k: v for k, v in row.items() if k not in {"method_metrics", "reference_metrics"}}
            | {
                f"{side}_{metric}": value
                for side in ("method_metrics", "reference_metrics")
                for metric, value in row[side].items()
            }
        )
    with (directory / "paired.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=list(rows[0]) if rows else ["method", "reference"]
        )
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# Provisional Development results",
        "",
        result["acceptance"],
        "",
        f"Recomputed runs: **{summary['counts']['runs']}**; scorable: **{summary['counts']['scorable_runs']}**; zero scored: **{summary['counts']['zero_scored_runs']}**.",
        "",
        result["aggregation"],
        "",
        "Only already-arrived labels saved with issued Development forecasts are scored. Each checkpoint, manifest and supporting proof is SHA-checked. Historical unmatched runs are excluded. This report does not select configurations or authorize Final.",
        "",
        "| Method | Runs | Scorable | Scored/requested days |",
        "|---|---:|---:|---:|",
    ]
    for method, row in sorted(methods.items()):
        lines.append(
            f"| {method} | {row['runs']} | {row['scorable']} | {row['scored_days']}/{row['requested_days']} |"
        )
    lines += [
        "",
        "Each method/reference table uses its own paired day intersection. Different rows can have different cohorts and must not be interpreted as a global performance ranking. Cells with missing labels or unequal input/initialization/labels remain blocked. Full baseline/ablation, seed and budget coverage plus independent review are required.",
        "",
        "| Budget | Method | Reference | Stations | Min seeds | MAE | RMSE | Reference MAE | MAE gain | Worse than reference | Negative transfer vs Target-only |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["station_first"]:
        ntr = (
            "n/a"
            if row["negative_transfer_station_fraction"] is None
            else f"{row['negative_transfer_station_fraction']:.3f}"
        )
        lines.append(
            f"| {row['budget']} | {row['method']} | {row['reference']} | {row['stations']} | {row['minimum_seeds_per_station']} | {row['method_metrics']['mae_kwh']:.6f} | {row['method_metrics']['rmse_kwh']:.6f} | {row['reference_metrics']['mae_kwh']:.6f} | {row['absolute_mae_gain_kwh']:.6f} | {row['worse_than_reference_station_fraction']:.3f} | {ntr} |"
        )
    lines += [
        "",
        f"Blocked pair reasons: `{json.dumps(summary['blocked_pair_reasons'], sort_keys=True)}`.",
        "",
        f"Full result SHA: `{source_sha}`.",
        f"Catalog SHA: `{result['catalog_sha256']}`.",
        "",
        "Runtime fields in the full JSON identify the device, final-stage duration and cumulative runner/proxy costs. Final-stage duration excludes earlier continuation/init stages; these values must not be presented as whole-job provider time. No independent acceptance, #39 completion or Final-lock claim is made.",
    ]
    (directory / "report.md").open("x", encoding="utf-8", newline="\n").write(
        "\n".join(lines) + "\n"
    )
    return {p.name: file_sha(p) for p in sorted(directory.iterdir())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    path = verified_file({"path": str(args.input), "sha256": args.sha256}, args.project_root)
    if not args.output_dir.resolve().is_relative_to(args.project_root.resolve()):
        raise ValueError("Report outside project")
    print(json.dumps(publish_report(json.loads(path.read_bytes()), args.output_dir, args.sha256)))


if __name__ == "__main__":
    main()
