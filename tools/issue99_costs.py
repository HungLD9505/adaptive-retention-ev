"""Account measured invocation costs without inventing missing historical costs."""

import json
from collections import defaultdict
from pathlib import Path


def summarize(root: Path, jobs: list[dict]) -> dict:
    """Keep source cost unknown and count exact-reuse rows separately."""
    by_method = {job["job_id"]: job["method"] for job in jobs}
    phases = defaultdict(
        lambda: {"invocations": 0, "known_wall_seconds": 0.0, "unknown_wall_invocations": 0}
    )
    comparison = defaultdict(lambda: {"invocations": 0, "known_wall_seconds": 0.0})
    peak = 0
    for path in root.rglob("run.json"):
        report = json.loads(path.read_text())
        parts = path.relative_to(root).parts
        phase = (
            "controller_calibration" if parts[0].startswith("controller-calibration-") else parts[0]
        )
        elapsed = report.get("invocation_wall_seconds", report.get("elapsed_seconds"))
        row = phases[phase]
        row["invocations"] += 1
        if elapsed is None:
            row["unknown_wall_invocations"] += 1
        else:
            row["known_wall_seconds"] += elapsed
        if phase == "comparison":
            method = by_method[parts[1]]
            comparison[method]["invocations"] += 1
            if elapsed is not None:
                comparison[method]["known_wall_seconds"] += elapsed
        peak = max(peak, report.get("gpu_peak_allocated_bytes") or 0)
    for job in jobs:
        if job["reuse_job_id"]:
            comparison[job["method"]]["exact_reuse_rows"] = (
                comparison[job["method"]].get("exact_reuse_rows", 0) + 1
            )
    incomplete = sum(not (p.parent / "run.json").exists() for p in root.rglob("binding.json"))
    return {
        "phases": dict(phases),
        "comparison_by_method": dict(comparison),
        "incomplete_invocations_without_report": incomplete,
        "source_pretraining_wall_seconds": None,
        "source_retrains_in_this_study": 0,
        "pytorch_peak_allocated_bytes": peak,
        "timing_scope": "Invocation wall includes IO and checkpoint work; component timers overlap these totals and must not be added again. Failed/unreported invocation costs remain unknown. Exact reuse has no additional model invocation, not zero bookkeeping cost. Tests, provisioning, transfer and prior pilots are outside these totals. PyTorch peak is not total device memory.",
    }
