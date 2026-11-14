"""Reviewer-side Cyber v3 byte/forecast audit and two independent baseline ledgers."""

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import torch

from ev_models.checkpoint import digest
from ev_runner.replay import Replay
from tools.issue99_retention_screen import INPUT_SHA
from tools.issue99_study_support import PreparedInputs

TARGETS = ("1405", "2152", "1153", "1693")


def ledger_summary(rows: list[dict], station_key: str) -> list[dict]:
    """Average seeds within station, then weight the four stations equally."""
    grouped = defaultdict(lambda: defaultdict(list))
    identities = set()
    for row in rows:
        identity = row["model"], row["mode"], row[station_key], row["seed"]
        if identity in identities:
            raise ValueError("Duplicate benchmark identity")
        identities.add(identity)
        if row[station_key] not in TARGETS or row.get("status", "ok") != "ok":
            raise ValueError("Wrong target or failed row")
        grouped[(row["model"], row["mode"])][row[station_key]].append(float(row["mae_kwh"]))
    result = []
    for (model, mode), stations in sorted(grouped.items()):
        if set(stations) != set(TARGETS):
            raise ValueError("Incomplete station coverage")
        result.append(
            {
                "model": model,
                "mode": mode,
                "mae_kwh": float(np.mean([np.mean(v) for v in stations.values()])),
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    for key in ("bundle", "cyber", "duc", "input", "output"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    root = args.bundle
    sub = Path("experiments/member_studies/cyber_baselines")
    artifacts = root / sub / "artifacts_v3"
    manifest = json.loads((artifacts / "manifest.json").read_bytes())
    for name, binding in manifest.items():
        path = root / name
        if path.resolve().is_relative_to(root.resolve()) is False:
            raise ValueError("Unsafe bundle path")
        if digest(path) != binding["sha256"] or path.stat().st_size != binding["bytes"]:
            raise ValueError(f"Bundle hash mismatch: {name}")
    for name in ("runs_v3.csv", "artifacts_v3/manifest.json"):
        if (root / sub / name).read_bytes() != (args.cyber / sub / name).read_bytes():
            raise ValueError("Bundle differs from committed Cyber evidence")
    environment = json.loads((artifacts / "environment.json").read_text())
    for name, sha in environment["code_sha256"].items():
        if digest(root / name) != sha:
            raise ValueError("Executed source identity differs")
    post_execution_changes = [
        name for name, sha in environment["code_sha256"].items() if digest(args.cyber / name) != sha
    ]
    inputs = PreparedInputs(args.input, INPUT_SHA, targets=TARGETS)
    replays = {t: Replay(inputs, t, 90) for t in TARGETS}
    cyber_rows = list(csv.DictReader((root / sub / "runs_v3.csv").open()))
    if len(cyber_rows) != 172:
        raise ValueError("Expected complete Cyber 172-row matrix")
    masks = {}
    daily_count = 0
    hourly_count = 0
    for row in cyber_rows:
        path = artifacts / f"{row['run_id']}_predictions.json"
        if digest(path) != row["predictions_sha256"]:
            raise ValueError("Forecast hash differs from ledger")
        forecast = json.loads(path.read_text())
        replay = replays[row["station_id"]]
        days = forecast["daily_results"]
        if len(days) != 90 or len({d["origin"] for d in days}) != 90:
            raise ValueError("Schedule coverage differs")
        errors, scored = [], []
        for day in days:
            origin = datetime.fromisoformat(day["origin"])
            if day["issued"] != (replay.forecast(origin) is not None):
                raise ValueError("Forecast schedule differs from authenticated input")
            labels = replay.labels(origin, origin + timedelta(days=1))
            expected = day["issued"] and labels.status == "complete"
            if bool(day["scored"]) != expected:
                raise ValueError("Complete-arrival score eligibility differs")
            if not day["scored"]:
                if day["ground_truth_kwh"] is not None or day["mae_kwh"] is not None:
                    raise ValueError("Unscored day carries labels or metrics")
                continue
            np.testing.assert_array_equal(day["ground_truth_kwh"], labels.values)
            error = np.asarray(day["predictions_kwh"]) - labels.values
            np.testing.assert_allclose(np.abs(error).mean(), day["mae_kwh"], atol=1e-10, rtol=1e-12)
            np.testing.assert_allclose(
                math.sqrt(np.square(error).mean()), day["rmse_kwh"], atol=1e-10, rtol=1e-12
            )
            errors.append(error)
            scored.append(day["origin"])
        mae = float(np.abs(errors).mean())
        rmse = float(np.sqrt(np.square(errors).mean()))
        if abs(mae - float(row["mae_kwh"])) > 5e-6 or abs(rmse - float(row["rmse_kwh"])) > 5e-6:
            raise ValueError("Ledger metric differs from hourly readback")
        if (len(days), sum(d["issued"] for d in days), len(scored)) != tuple(
            int(row[k]) for k in ("scheduled_days", "issued_days", "scored_days")
        ):
            raise ValueError("Ledger counts differ")
        if row["station_id"] in masks and masks[row["station_id"]] != scored:
            raise ValueError("Model score masks differ")
        masks[row["station_id"]] = scored
        daily_count += len(scored)
        hourly_count += 24 * len(scored)
    finite_states = 0
    for path in root.rglob("*.pt"):
        state = torch.load(path, map_location="cpu", weights_only=True)

        def check(value: object) -> None:
            if isinstance(value, torch.Tensor):
                if not torch.isfinite(value).all():
                    raise ValueError("Nonfinite tensor state")
            elif isinstance(value, dict):
                for item in value.values():
                    check(item)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    check(item)

        check(state)
        finite_states += 1
    duc_root = args.duc / "experiments/member_studies/duc_baselines"
    duc_rows = list(csv.DictReader((duc_root / "runs.csv").open())) + list(
        csv.DictReader((duc_root / "runs_graph.csv").open())
    )
    if len(duc_rows) != 172:
        raise ValueError("Expected complete Duc matrix")
    session = json.loads((duc_root / "session.json").read_text())
    if session["manifest_sha256"] != INPUT_SHA or session["source_count"] != 65888:
        raise ValueError("Duc session identity differs")
    summaries = {
        "cyber": ledger_summary(cyber_rows, "station_id"),
        "duc": ledger_summary(duc_rows, "target"),
    }
    for author, values in summaries.items():
        with (args.output / f"{author}-summary.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(values[0]))
            writer.writeheader()
            writer.writerows(values)
    inputs.reauthenticate()
    report = {
        "status": "passed",
        "cyber_manifest_entries": len(manifest),
        "cyber_executed_code_files": len(environment["code_sha256"]),
        "cyber_post_execution_source_changes": post_execution_changes,
        "cyber_runs": len(cyber_rows),
        "cyber_daily_scores": daily_count,
        "cyber_hourly_predictions": hourly_count,
        "cyber_finite_tensor_files": finite_states,
        "cyber_scored_origins": {t: len(v) for t, v in masks.items()},
        "duc_ledger_rows_recomputed": len(duc_rows),
        "duc_external_readback": "Reuse published reviewer receipt 6783698688 on unchanged ledgers/session; no new 737-file download",
        "summaries": summaries,
        "limits": [
            "No full training reproduction or fresh upstream raw archive audit",
            "Joblib states hashed only",
            "Cyber export lacks per-score issuance timestamps; current arrival eligibility and submitted code reviewed, no physical execution chronology proof",
            "Benchmark recipes differ from Source10 retention study; do not pool",
            "Duc external forecast/checkpoint audit is reused, not newly independently repeated",
        ],
    }
    (args.output / "verification.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({k: v for k, v in report.items() if k != "summaries"}, indent=2))


if __name__ == "__main__":
    main()
