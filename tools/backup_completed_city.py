"""Read-only rescue of existing completed city runs to an identified Drive mount."""

import argparse
import json
from pathlib import Path

from ev_models.checkpoint import digest, write_json
from ev_runner.run import runtime_code
from tools.charged_matched_development import backup_context, validate_cohort
from tools.comparison_matrix import CachedInputs
from tools.durable_run_backup import RunBackup, require_drive_mount


def run(args: argparse.Namespace) -> dict:
    """Authenticate a single snapshot and publish complete Sources/targets, never train."""
    require_drive_mount(args.backup_root, args.drive_mount)
    if (
        digest(args.cohort) != args.cohort_sha256
        or digest(args.primary_analysis) != args.primary_sha256
    ):
        raise ValueError("Changed accepted cohort/primary selection")
    # A progress file may keep growing atomically; this snapshot fixes our exact prefix.
    raw = args.snapshot.read_bytes()
    snapshot = json.loads(raw)
    cohort, primary = (json.loads(p.read_text()) for p in (args.cohort, args.primary_analysis))
    code = runtime_code()
    if (
        code["dirty"]
        or snapshot["code"]["dirty"]
        or snapshot["code"]["files"] != code["files"]
        or snapshot["namespace"] != cohort["namespace"]
        or snapshot["cohort_sha256"] != args.cohort_sha256
        or snapshot["primary_analysis_sha256"] != args.primary_sha256
        or snapshot.get("status") not in {"running", "failed", "technical_success"}
    ):
        raise ValueError("Changed identified city execution")
    if not snapshot["sources"]:
        raise ValueError("No completed Source checkpoint to preserve")
    data = {
        budget: CachedInputs(
            args.inputs_root / f"{cohort['namespace']}-{budget}d",
            cohort["budgets"][str(budget)]["manifest_sha256"],
        )
        for budget in (7, 14, 28)
    }
    validate_cohort(data, cohort)
    runtime = (
        snapshot["runs"][0]["binding"]["environment"]
        if snapshot["runs"]
        else snapshot["sources"][0]["run"]["environment"]
    )
    context = backup_context(
        cohort,
        primary,
        data,
        code,
        runtime,
        cohort_sha256=args.cohort_sha256,
        primary_sha256=args.primary_sha256,
    )
    expected = list(context["expected_runs"])
    names = [row["run_id"] for row in snapshot["runs"]]
    seeds = [source["seed"] for source in snapshot["sources"]]
    if (
        names != expected[: len(names)]
        or seeds != cohort["seeds"][: len(seeds)]
        or snapshot["source_epochs"] != context["source_epochs"]
    ):
        raise ValueError("Snapshot must be an original execution prefix, not selected results")
    backup = RunBackup(args.snapshot.parent, args.backup_root, context, data)
    # Preserve original identities; never modify the live study, inputs or Source files.
    with (args.backup_root / "original-snapshot.json").open("xb") as stream:
        stream.write(raw)
    for source in snapshot["sources"]:
        backup.source(source)
    for row in snapshot["runs"]:
        backup.target(row)
        print(
            json.dumps(
                {"verified_backed_up_targets": len(backup.runs), "snapshot_targets": len(names)}
            ),
            flush=True,
        )
    result = {
        "status": "verified_completed_prefix_on_mounted_filesystem",
        "scope": "Read-only rescue; no training, liveness claim, full-matrix or remote acceptance",
        "sources": len(backup.sources),
        "targets": len(backup.runs),
        "expected_targets": len(expected),
        "context_sha256": backup.context_sha,
        "original_snapshot_sha256": __import__("hashlib").sha256(raw).hexdigest(),
    }
    write_json(args.backup_root / "rescue-complete.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "snapshot",
        "inputs-root",
        "cohort",
        "primary-analysis",
        "backup-root",
        "drive-mount",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("cohort-sha256", "primary-sha256"):
        parser.add_argument("--" + name, required=True)
    print(json.dumps(run(parser.parse_args())))


if __name__ == "__main__":
    main()
