"""Audit pinned Block7/Main manifest metrics without treating distinct policies as equivalent."""

from __future__ import annotations

import hashlib
import json

from tools import hung_block7_manifest_pairs as pairs
from tools import hung_block7_origin_events as origins

OUTPUT = pairs.ROOT / "docs/reports/evidence/hung-block7-manifest-metric-audit-20261030-v1.json"
ORIGIN_SHA256 = "2a025850fa4e363db173833ea6aa4b9a40b4bccc1dd0e545715984505e283955"


def metric_row(pair: dict, old: dict, main: dict) -> dict:
    """Keep null metrics null and expose both policies' recorded values."""
    if old["coverage"] != main["coverage"]:
        raise ValueError("Paired manifest coverage differs")
    old_live, main_live = old["metrics_kwh"]["live"], main["metrics_kwh"]["live"]
    scored_days = old["coverage"]["scored"]
    if (old_live is None) != (main_live is None):
        raise ValueError("Paired manifests disagree on live metric availability")
    if (old_live is None) != (scored_days == 0):
        raise ValueError("Live metric availability disagrees with scored coverage")
    if old_live is not None:
        if old_live["hours"] != main_live["hours"] or old_live["hours"] != scored_days * 24:
            raise ValueError("Paired live metric hours disagree with scored days")
    return {
        "cell_id": pair["cell_id"],
        "budget_days": pair["budget_days"],
        "seed": pair["seed"],
        "historical_run_id": pair["historical_run_id"],
        "main_run_id": pair["main_run_id"],
        "historical_manifest_sha256": pair["historical_manifest_sha256"],
        "main_manifest_sha256": pair["main_manifest_sha256"],
        "scored_days": scored_days,
        "live_hours": None if old_live is None else old_live["hours"],
        "historical_live_mae_kwh": None if old_live is None else old_live["mae_kwh"],
        "main_live_mae_kwh": None if main_live is None else main_live["mae_kwh"],
        "main_minus_historical_live_mae_kwh": (
            None if old_live is None else main_live["mae_kwh"] - old_live["mae_kwh"]
        ),
        "historical_live_rmse_kwh": None if old_live is None else old_live["rmse_kwh"],
        "main_live_rmse_kwh": None if main_live is None else main_live["rmse_kwh"],
        "historical_audit_scored_days": old["metrics_kwh"]["audit_scored_days"],
        "main_audit_scored_days": main["metrics_kwh"]["audit_scored_days"],
        "live_metric_equal": old_live == main_live,
        "full_metric_record_equal": old["metrics_kwh"] == main["metrics_kwh"],
        "review_status": "PENDING_PEER",
    }


def audit() -> dict:
    evidence = json.loads(pairs.EVIDENCE.read_text(encoding="utf-8"))
    expected_sha = evidence["audit"]["provenance"]["inputs"]["coverage"]["sha256"]
    if pairs.sha_file(pairs.DEFAULT_COVERAGE) != expected_sha:
        raise ValueError("Pinned coverage SHA mismatch")
    if pairs.sha_file(origins.OUTPUT) != ORIGIN_SHA256:
        raise ValueError("Pinned origin table SHA mismatch")
    coverage = json.loads(pairs.DEFAULT_COVERAGE.read_text(encoding="utf-8"))
    paired = origins.compare(coverage, pairs.DEFAULT_MANIFEST_DIR)
    if len(paired) != 69 or not all(row["origin_event_tags_equal"] for row in paired):
        raise ValueError("Pinned 69-cell origin eligibility audit failed")
    rows = []
    for pair in paired:
        old_id, main_id = pair["historical_run_id"], pair["main_run_id"]
        old = pairs.checked_manifest(
            coverage["external_complete_jobs"][old_id]["run_manifest"],
            pairs.DEFAULT_MANIFEST_DIR / f"{old_id}.json",
        )
        main = pairs.checked_manifest(
            coverage["reused_jobs"][main_id],
            pairs.DEFAULT_MANIFEST_DIR / f"{main_id}.json",
        )
        rows.append(metric_row(pair, old, main))
    return {
        "schema": "hung-block7-manifest-metric-audit-v1",
        "scope": "authenticated manifest summaries only; not event-journal numeric readback or peer approval",
        "coverage_sha256": expected_sha,
        "origin_table_sha256": ORIGIN_SHA256,
        "rows": rows,
        "counts": {
            "pairs": len(rows),
            "scored_pairs": sum(row["scored_days"] > 0 for row in rows),
            "null_pairs": sum(row["scored_days"] == 0 for row in rows),
            "live_metric_equal": sum(row["live_metric_equal"] for row in rows),
            "full_metric_record_equal": sum(row["full_metric_record_equal"] for row in rows),
            "audit_day_count_equal": sum(
                row["historical_audit_scored_days"] == row["main_audit_scored_days"] for row in rows
            ),
        },
    }


def main() -> None:
    result = audit()
    payload = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if OUTPUT.exists():
        if OUTPUT.read_bytes() != payload:
            raise ValueError("Existing metric audit differs; evidence is create-only")
    else:
        with OUTPUT.open("xb") as stream:
            stream.write(payload)
    print(json.dumps({"counts": result["counts"], "sha256": hashlib.sha256(payload).hexdigest()}))


if __name__ == "__main__":
    main()
