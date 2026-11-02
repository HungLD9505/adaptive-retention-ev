"""Summarize pinned Final manifest decisions and measured stage costs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_SHA = "e5e8fe1cb5636e508b3edbcedbbd00a72d9d8230041bf383eeba3d1133883e5e"
ARCHIVE_SHA = "531bff0d24ddf7eb0a08d4ed9d97976e55140b81025db0d91c28c557684e1114"
SOURCE = "hungluongduc/hung-final-e5e8fe1c-360-20261029-v1/1"
LEDGER_SHA = "0dca10975d5431ac199909ccb5bf69298040d6e4a21d3424bd15986a26cfa0a8"
SCORES_SHA = "9e09ae4f72b13c03ed029deb338301753ae377c15cbbfa7414433c5538cba73a"


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def pinned(path: Path, expected: str) -> dict:
    assert path.resolve().is_relative_to(ROOT.resolve())
    assert path.is_file() and sha256(path) == expected, f"SHA differs: {path.name}"
    return json.loads(path.read_text(encoding="utf-8"))


def optional_sum(values: list[int | float | None]) -> int | float | None:
    if any(value is None for value in values):
        return None
    return math.fsum(values)


def audit(events: dict, scores: dict, ledger: dict) -> tuple[list[dict], list[dict]]:
    assert events["schema"] == "hung-final-remote-event-audit-v1"
    assert scores["schema"] == "hung-final-remote-run-scores-v1"
    assert ledger["schema"] == "hung-final-job-artifact-ledger-v1"
    for document in (events, scores, ledger):
        assert document["source_kernel"] == SOURCE
        assert document["lock_sha256"] == LOCK_SHA
        assert document["archive_sha256"] == ARCHIVE_SHA
    event_rows = events["jobs"]
    score_rows = {row["job_id"]: row for row in scores["jobs"]}
    assert len(event_rows) == len(score_rows) == len(ledger["jobs"]) == 360
    assert {row["job_id"] for row in event_rows} == set(score_rows) == set(ledger["jobs"])
    rows = []
    for row in event_rows:
        job_id = row["job_id"]
        assert row["variant"] == score_rows[job_id]["variant"]
        assert set(row["stages"]) == set(ledger["jobs"][job_id])
        replay = row["stages"]["replay"]
        assert replay["coverage"] == score_rows[job_id]["coverage"]
        evidence = replay["event_evidence"]
        assert isinstance(evidence, dict)
        decisions = evidence.get("decisions")
        if decisions is None:
            decision_count = switches = None
            reasons = None
        else:
            assert isinstance(decisions, list)
            reasons = Counter()
            for decision in decisions:
                reason = decision["reason"]
                assert reason in {"switch", "no_qualifying_challenger", "fixed_policy"}
                assert isinstance(decision["current_level"], (int, float))
                assert isinstance(decision["selected_level"], (int, float))
                assert (reason == "switch") == (
                    decision["current_level"] != decision["selected_level"]
                )
                reasons[reason] += 1
            decision_count = len(decisions)
            switches = reasons["switch"]
        costs = replay["runtime_costs"]
        if isinstance(costs, dict) and costs.get("complete") is True:
            candidates = costs["candidate"]
            assert len(candidates) == 3
            candidate_updates = sum(item["update_steps"] for item in candidates)
            candidate_inferences = sum(item["inference_calls"] for item in candidates)
            audit_updates = costs["audit"]["update_steps"]
            audit_inferences = costs["audit"]["inference_calls"]
        else:
            candidate_updates = candidate_inferences = audit_updates = audit_inferences = None
        durations = [stage["duration_seconds"] for stage in row["stages"].values()]
        assert all(value is None or (math.isfinite(value) and value >= 0) for value in durations)
        rows.append(
            {
                "job_id": job_id,
                "variant": row["variant"],
                "decisions": decision_count,
                "switches": switches,
                "no_qualifying_challenger": None
                if reasons is None
                else reasons["no_qualifying_challenger"],
                "fixed_policy_decisions": None if reasons is None else reasons["fixed_policy"],
                "candidate_update_steps": candidate_updates,
                "candidate_inference_calls": candidate_inferences,
                "audit_update_steps": audit_updates,
                "audit_inference_calls": audit_inferences,
                "replay_duration_seconds": replay["duration_seconds"],
                "all_stage_duration_seconds": optional_sum(durations),
                "observed_stage_duration_seconds": math.fsum(
                    value for value in durations if value is not None
                ),
                "missing_stage_duration_count": sum(value is None for value in durations),
            }
        )
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["variant"]].append(row)
    variants = []
    for variant, members in sorted(grouped.items()):
        variants.append(
            {
                "variant": variant,
                "jobs": len(members),
                **{
                    key: optional_sum([row[key] for row in members])
                    for key in (
                        "decisions",
                        "switches",
                        "no_qualifying_challenger",
                        "fixed_policy_decisions",
                        "candidate_update_steps",
                        "candidate_inference_calls",
                        "audit_update_steps",
                        "audit_inference_calls",
                        "replay_duration_seconds",
                        "all_stage_duration_seconds",
                        "observed_stage_duration_seconds",
                        "missing_stage_duration_count",
                    )
                },
            }
        )
    return rows, variants


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    assert receipt["schema"] == "hung-final-remote-event-audit-receipt-v1"
    assert receipt["status"] == "FINAL_STAGE_MANIFEST_EVENTS_EXPORTED"
    assert receipt["source_kernel"] == SOURCE and receipt["lock_sha256"] == LOCK_SHA
    assert args.events.stat().st_size == receipt["output_bytes"]
    events = pinned(args.events, receipt["output_sha256"])
    scores = pinned(args.scores, SCORES_SHA)
    ledger = pinned(args.ledger, LEDGER_SHA)
    rows, variants = audit(events, scores, ledger)
    assert receipt["jobs"] == len(rows)
    output = args.output.resolve()
    assert output.is_relative_to(ROOT.resolve()) and not output.exists()
    output.mkdir(parents=True)
    write_csv(output / "job_events.csv", rows)
    write_csv(output / "variant_events.csv", variants)
    summary = {
        "schema": "hung-final-event-audit-v1",
        "jobs": len(rows),
        "events_sha256": sha256(args.events),
        "scores_sha256": SCORES_SHA,
        "decision_rows": sum(row["decisions"] is not None for row in rows),
        "decisions": sum(row["decisions"] or 0 for row in rows),
        "switches": sum(row["switches"] or 0 for row in rows),
        "replay_duration_seconds_sum": math.fsum(
            row["replay_duration_seconds"]
            for row in rows
            if row["replay_duration_seconds"] is not None
        ),
        "all_stage_duration_seconds_sum": math.fsum(
            row["all_stage_duration_seconds"]
            for row in rows
            if row["all_stage_duration_seconds"] is not None
        ),
        "observed_stage_duration_seconds_sum": math.fsum(
            row["observed_stage_duration_seconds"] for row in rows
        ),
        "missing_stage_duration_count": sum(row["missing_stage_duration_count"] for row in rows),
        "files": {name: sha256(output / name) for name in ("job_events.csv", "variant_events.csv")},
    }
    with (output / "summary.json").open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
