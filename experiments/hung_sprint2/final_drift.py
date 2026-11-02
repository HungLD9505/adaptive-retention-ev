"""Derive the locked Final Drift reference from causal forecast history only."""

from __future__ import annotations

import json
import math

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2.dispatch_matched import require
from experiments.hung_sprint2.final_lock import _project_path
from experiments.hung_sprint2.replay_inputs import _target_forecasts


def derive_drift_reference(job: dict, spec: dict) -> dict:
    """Match Development's first-issued-history population SD and floor rule."""
    run = _project_path(job["input_run"])
    manifest_path = run / "manifest.json"
    require(
        sha256_file(manifest_path) == job["input_manifest_sha256"],
        "Final Drift input manifest changed",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    forecast_path = run / "forecasts.jsonl"
    forecast_sha = manifest["files"]["forecasts.jsonl"]["sha256"]
    require(sha256_file(forecast_path) == forecast_sha, "Final Drift history changed")
    identity = [job["dataset_id"], job["city_id"], job["entity_id"]]
    first = None
    for row in _target_forecasts(forecast_path, identity, role="final"):
        if first is None or row["origin"] < first["origin"]:
            first = row
    require(first is not None, "Final Drift has no issued forecast history")
    values = [
        hour[0]
        for hour in first["x_hist"]
        if len(hour) == 7 and hour[6] == 1 and math.isfinite(hour[0])
    ]
    require(bool(values), "Final Drift first history has no available load")
    mean = math.fsum(values) / len(values)
    variance = math.fsum((value - mean) ** 2 for value in values) / len(values)
    return {
        "schema": spec["schema"],
        "rule": spec["rule"],
        "scale_floor": spec["scale_floor"],
        "origin": first["origin"],
        "mean": mean,
        "scale": max(math.sqrt(variance), spec["scale_floor"]),
        "forecast_sha256": forecast_sha,
        "input_manifest_sha256": job["input_manifest_sha256"],
    }
