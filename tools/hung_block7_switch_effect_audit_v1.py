"""Recompute retrospective old-policy audit errors from authenticated Development checkpoints."""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
IMPORT = ROOT / "docs/reports/hung-block7-terminal-checkpoint-import-20261030-v1.json"
IMPORT_SHA256 = "009fce2052b69bae7dde12d80b1d9e7cec28459d6f5531ce17ad76c489f535f5"
CHECKPOINTS = ROOT / ".cache/block7-terminal-checkpoint-import-v1"
SCORE_TOLERANCE_KWH = 1e-5


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _recompute_mae_kwh(forecast: torch.Tensor, labels: torch.Tensor, scale: float) -> float:
    if (
        not isinstance(forecast, torch.Tensor)
        or tuple(forecast.shape) != (1, 24)
        or not isinstance(labels, torch.Tensor)
        or tuple(labels.shape) != (24,)
        or not bool(torch.isfinite(forecast).all())
        or not bool(torch.isfinite(labels).all())
    ):
        raise ValueError("Invalid complete-day audit forecast or label tensor")
    return float(torch.mean(torch.abs(forecast.flatten().double() - labels.double()))) * scale


def switch_rows(state: dict, run_id: str, role: str) -> list[dict]:
    """Compare the selected forecast with the old-policy audit in the next block."""
    levels = tuple(float(level) for level in state["controller"]["levels"])
    scale = float(state["energy_scale"])
    delta = float(state["controller"]["delta"])
    if len(levels) != 3 or len(set(levels)) != 3 or not math.isfinite(scale) or scale <= 0:
        raise ValueError("Invalid controller levels or energy scale")
    if not math.isfinite(delta) or delta < 0:
        raise ValueError("Invalid controller threshold")
    issued = state["issued"]
    decisions = state["decisions"]
    if not isinstance(issued, list) or not isinstance(decisions, list):
        raise ValueError("Invalid issued or decision inventory")
    rows = []
    for decision_index, decision in enumerate(decisions):
        old_level = float(decision["current_level"])
        selected_level = float(decision["selected_level"])
        if old_level not in levels or selected_level not in levels:
            raise ValueError("Decision level outside the locked controller")
        if old_level == selected_level:
            continue
        next_block = decision_index + 1
        candidate_index = levels.index(selected_level)
        block_issued = [row for row in issued if row["block_id"] == next_block]
        if not block_issued:
            status = "NO_NEXT_BLOCK_FORECAST"
            paired = []
        else:
            paired = []
            for row in block_issued:
                if float(row["active_level"]) != selected_level:
                    raise ValueError(f"Selected level differs in next block: {run_id}")
                if row["y_scaled"] is None:
                    if row["audit_mae_kwh"] is not None:
                        raise ValueError("Unscored origin contains an audit score")
                    continue
                if row["audit_forecast"] is None or row["audit_mae_kwh"] is None:
                    raise ValueError("Scored next-block origin lacks old-policy audit")
                saved_live = float(row["mae_kwh"][candidate_index])
                saved_audit = float(row["audit_mae_kwh"])
                recomputed_live = _recompute_mae_kwh(
                    row["forecasts"][candidate_index], row["y_scaled"], scale
                )
                recomputed_audit = _recompute_mae_kwh(row["audit_forecast"], row["y_scaled"], scale)
                if (
                    not math.isfinite(saved_live)
                    or not math.isfinite(saved_audit)
                    or abs(saved_live - recomputed_live) > SCORE_TOLERANCE_KWH
                    or abs(saved_audit - recomputed_audit) > SCORE_TOLERANCE_KWH
                ):
                    raise ValueError(f"Saved next-block audit score mismatch: {run_id}")
                paired.append((saved_live, saved_audit))
            status = "PAIRED_SCORED_DAYS" if paired else "NO_PAIRED_SCORED_DAY"
        mean_live = sum(item[0] for item in paired) / len(paired) if paired else None
        mean_audit = sum(item[1] for item in paired) / len(paired) if paired else None
        difference = mean_live - mean_audit if paired else None
        rows.append(
            {
                "role": role,
                "run_id": run_id,
                "decision_index": decision_index,
                "next_block_id": next_block,
                "old_level": old_level,
                "selected_level": selected_level,
                "next_block_issued": len(block_issued),
                "paired_scored_days": len(paired),
                "mean_live_mae_kwh": mean_live,
                "mean_old_policy_audit_mae_kwh": mean_audit,
                "live_minus_audit_mae_kwh": difference,
                "delta_kwh": delta * scale,
                "audit_better_beyond_delta": difference > delta * scale if paired else None,
                "status": status,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if sha256(IMPORT) != IMPORT_SHA256:
        raise ValueError("Terminal checkpoint import evidence SHA mismatch")
    evidence = json.loads(IMPORT.read_text(encoding="utf-8"))
    details = evidence["details"]
    if evidence["checked"] != 138 or len(details) != 138:
        raise ValueError("Terminal checkpoint import is incomplete")
    roles = collections.Counter(item["role"] for item in details)
    if roles != {"historical": 69, "main": 69}:
        raise ValueError("Expected 69 historical Block7 and 69 Main checkpoints")
    if len({item["run_id"] for item in details}) != 138:
        raise ValueError("Duplicate checkpoint run ID")
    rows = []
    for item in sorted(details, key=lambda entry: entry["run_id"]):
        path = CHECKPOINTS / f"{item['run_id']}.pt"
        if (
            path.is_symlink()
            or path.stat().st_size != item["bytes"]
            or sha256(path) != item["sha256"]
        ):
            raise ValueError(f"Terminal checkpoint bytes differ: {item['run_id']}")
        state = torch.load(path, map_location="cpu", weights_only=True)
        rows.extend(switch_rows(state, item["run_id"], item["role"]))
    fieldnames = list(rows[0]) if rows else []
    summary = {
        "schema": "hung-block7-switch-effect-audit-v1",
        "terminal_import_sha256": IMPORT_SHA256,
        "checkpoints_verified": len(details),
        "score_tolerance_kwh": SCORE_TOLERANCE_KWH,
        "by_role": {
            role: {
                "switches": sum(row["role"] == role for row in rows),
                "paired_evaluable": sum(
                    row["role"] == role and row["status"] == "PAIRED_SCORED_DAYS" for row in rows
                ),
                "audit_better_beyond_delta": sum(
                    row["role"] == role and row["audit_better_beyond_delta"] is True for row in rows
                ),
                "paired_scored_days": sum(
                    row["paired_scored_days"] for row in rows if row["role"] == role
                ),
            }
            for role in ("historical", "main")
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=False)
    with (args.output_dir / "switches.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
