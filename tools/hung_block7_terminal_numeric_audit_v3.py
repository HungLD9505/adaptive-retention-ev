"""Audit full 90-day issued forecasts in authenticated Block7/Main checkpoints."""

from __future__ import annotations

import collections
import csv
import hashlib
import json
import math

import torch

from tools import hung_block7_journal_stage as stage
from tools.hung_block7_prefix_numeric_audit_v1 import compare_issued

PREFIX = stage.ROOT / ".cache/block7-prefix-import-v1"
TERMINAL = stage.ROOT / ".cache/block7-terminal-checkpoint-import-v1"
PREFIX_IMPORT = stage.ROOT / "docs/reports/hung-block7-prefix-import-20261030-v1.json"
TERMINAL_IMPORT = (
    stage.ROOT / "docs/reports/hung-block7-terminal-checkpoint-import-20261030-v1.json"
)
PAIRS = stage.ROOT / "docs/reports/hung-block7-manifest-pairs-20261028.csv"
OUT = stage.ROOT / "docs/reports/hung-block7-terminal-numeric-audit-20261030-v3.json"


def recompute_candidate_scores(state: dict, candidate_count: int) -> dict:
    scale = float(state["energy_scale"])
    if not math.isfinite(scale) or scale <= 0 or candidate_count < 1:
        raise ValueError("Invalid checkpoint energy scale or candidate count")
    checked = 0
    max_abs_error_kwh = 0.0
    max_abs_normalized_error = 0.0
    above_1e_minus_5 = 0
    above_1e_minus_6_normalized = 0
    unscored = 0
    for row in state["issued"]:
        forecasts = row["forecasts"]
        if not isinstance(forecasts, list) or len(forecasts) != candidate_count:
            raise ValueError("Candidate forecast inventory differs from config")
        if any(
            not isinstance(forecast, torch.Tensor)
            or tuple(forecast.shape) != (1, 24)
            or not bool(torch.isfinite(forecast).all())
            for forecast in forecasts
        ):
            raise ValueError("Invalid candidate forecast tensor")
        labels = row["y_scaled"]
        if labels is None:
            if row["mae_kwh"] is not None or row["normalized_mae"] is not None:
                raise ValueError("Unscored origin contains saved candidate scores")
            unscored += 1
            continue
        if (
            not isinstance(labels, torch.Tensor)
            or tuple(labels.shape) != (24,)
            or not bool(torch.isfinite(labels).all())
        ):
            raise ValueError("Invalid complete-day label tensor")
        kwh_scores = row["mae_kwh"]
        normalized_scores = row["normalized_mae"]
        if (
            not isinstance(kwh_scores, (list, tuple))
            or not isinstance(normalized_scores, (list, tuple))
            or len(kwh_scores) != candidate_count
            or len(normalized_scores) != candidate_count
        ):
            raise ValueError("Candidate forecast/score inventory differs")
        for forecast, saved_kwh, saved_normalized in zip(
            forecasts, kwh_scores, normalized_scores, strict=True
        ):
            if (
                not math.isfinite(float(saved_kwh))
                or not math.isfinite(float(saved_normalized))
                or float(saved_kwh) < 0
                or float(saved_normalized) < 0
            ):
                raise ValueError("Nonfinite or negative saved candidate score")
            calculated_normalized = float(
                torch.mean(torch.abs(forecast.flatten().double() - labels.flatten().double()))
            )
            error_normalized = abs(calculated_normalized - float(saved_normalized))
            error_kwh = abs(calculated_normalized * scale - float(saved_kwh))
            max_abs_normalized_error = max(max_abs_normalized_error, error_normalized)
            max_abs_error_kwh = max(max_abs_error_kwh, error_kwh)
            above_1e_minus_5 += error_kwh > 1e-5
            above_1e_minus_6_normalized += error_normalized > 1e-6
            checked += 1
    return {
        "recomputed_candidate_scores": checked,
        "unscored_issued_origins": unscored,
        "max_abs_recomputed_score_error_kwh": max_abs_error_kwh,
        "score_abs_error_above_1e_minus_5_kwh": above_1e_minus_5,
        "max_abs_recomputed_normalized_error": max_abs_normalized_error,
        "normalized_abs_error_above_1e_minus_6": above_1e_minus_6_normalized,
    }


def compare_live_forecasts(historical: list[dict], main: list[dict], levels: list[float]) -> dict:
    by_day = {row["day_id"]: row for row in main}
    equal = 0
    different = 0
    max_abs_difference = 0.0
    first_index = None
    for row in historical:
        other = by_day[row["day_id"]]
        a = row["forecasts"][levels.index(row["active_level"])]
        b = other["forecasts"][levels.index(other["active_level"])]
        if a.shape != b.shape or not torch.isfinite(a).all() or not torch.isfinite(b).all():
            raise ValueError("Invalid live forecast tensor")
        if torch.equal(a, b):
            equal += 1
        else:
            different += 1
            max_abs_difference = max(max_abs_difference, float(torch.max(torch.abs(a - b))))
            first_index = row["index"] if first_index is None else min(first_index, row["index"])
    return {
        "live_equal_origins": equal,
        "live_different_origins": different,
        "first_live_difference_index": first_index,
        "max_abs_normalized_live_difference": max_abs_difference,
    }


def validate_issued_forecast_order(state: dict, events: list[str], run_id: str) -> None:
    forecast_days = [event.split(":", 1)[1] for event in events if event.startswith("forecast:")]
    issued_days = [row["day_id"] for row in state["issued"]]
    if forecast_days != issued_days:
        raise ValueError(f"Issued origins differ from ordered journal forecasts: {run_id}")


def main() -> int:
    prefix_bytes = PREFIX_IMPORT.read_bytes()
    terminal_bytes = TERMINAL_IMPORT.read_bytes()
    prefix_import = json.loads(prefix_bytes)
    terminal_import = json.loads(terminal_bytes)
    if prefix_import["checked_files"] != 414 or terminal_import["checked"] != 138:
        raise ValueError("Prefix or terminal byte import incomplete")
    prefix_by_id = {row["run_id"]: row for row in prefix_import["details"]}
    terminal_by_id = {row["run_id"]: row for row in terminal_import["details"]}
    if len(prefix_by_id) != 138 or len(terminal_by_id) != 138:
        raise ValueError("Duplicate imported run identity")
    saved_by_id = {row["run_id"]: row for row in stage.rows()}
    if not stage.verify(list(saved_by_id.values()))["complete"]:
        raise ValueError("Saved replay-90 journal gate incomplete")
    with PAIRS.open(encoding="utf-8", newline="") as stream:
        pairs = list(csv.DictReader(stream))
    if len(pairs) != 69:
        raise ValueError("Expected 69 pairs")
    states = {}
    manifests = {}
    score_totals: collections.Counter[str] = collections.Counter()
    max_score_error = 0.0
    max_normalized_error = 0.0
    for run_id, meta in terminal_by_id.items():
        checkpoint = TERMINAL / f"{run_id}.pt"
        if checkpoint.is_symlink() or stage.pairs.sha_file(checkpoint) != meta["sha256"]:
            raise ValueError(f"Terminal checkpoint SHA mismatch: {run_id}")
        manifest_path = stage.ROOT / ".cache/block7-review-v1/manifests" / f"{run_id}.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if stage.pairs.sha_file(manifest_path) != meta["saved_manifest_sha256"]:
            raise ValueError(f"Saved manifest SHA mismatch: {run_id}")
        prefix_journal = PREFIX / run_id / "events.jsonl"
        suffix_journal = stage.ROOT / saved_by_id[run_id]["staged_path"]
        if (
            stage.pairs.sha_file(prefix_journal)
            != prefix_by_id[run_id]["files"]["events.jsonl"]["sha256"]
        ):
            raise ValueError(f"Prefix journal SHA mismatch: {run_id}")
        events = [
            json.loads(line)["value"]
            for path in (prefix_journal, suffix_journal)
            for line in path.read_text(encoding="utf-8").splitlines()[1:]
        ]
        state = torch.load(checkpoint, map_location="cpu", weights_only=True)
        if (
            state["binding"] != manifest["input_binding"]
            or state["next_index"] != manifest["runner_cursor"]
            or state["next_index"] != 90
            or state["events"] != events
        ):
            raise ValueError(f"Terminal checkpoint state/manifest/journal mismatch: {run_id}")
        validate_issued_forecast_order(state, events, run_id)
        score_result = recompute_candidate_scores(
            state, len(manifest["config"]["controller"]["levels"])
        )
        score_totals.update(
            {
                key: score_result[key]
                for key in (
                    "recomputed_candidate_scores",
                    "unscored_issued_origins",
                    "score_abs_error_above_1e_minus_5_kwh",
                    "normalized_abs_error_above_1e_minus_6",
                )
            }
        )
        max_score_error = max(max_score_error, score_result["max_abs_recomputed_score_error_kwh"])
        max_normalized_error = max(
            max_normalized_error, score_result["max_abs_recomputed_normalized_error"]
        )
        states[run_id] = state
        manifests[run_id] = manifest
    details = []
    by_index: dict[int, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    for pair in pairs:
        h_id, m_id = pair["historical_run_id"], pair["main_run_id"]
        h, m = states[h_id], states[m_id]
        h_days = {row["day_id"] for row in h["issued"]}
        m_days = {row["day_id"] for row in m["issued"]}
        if h_days != m_days:
            raise ValueError(f"Issued forecast day set differs: {pair['cell_id']}")
        h_levels = manifests[h_id]["config"]["controller"]["levels"]
        m_levels = manifests[m_id]["config"]["controller"]["levels"]
        if h_levels != m_levels:
            raise ValueError(f"Candidate level inventory differs: {pair['cell_id']}")
        candidate_result, per_index = compare_issued(h["issued"], m["issued"])
        live_result = compare_live_forecasts(h["issued"], m["issued"], h_levels)
        details.append({"cell_id": pair["cell_id"], **candidate_result, **live_result})
        for index, counts in per_index.items():
            by_index[index].update(counts)
    keys = (
        "common_issued",
        "forecast_equal_origins",
        "forecast_different_origins",
        "active_level_differences",
        "both_labels_absent_at_snapshot",
        "both_labels_present",
        "asymmetric_label_presence_at_different_cursors",
        "label_value_differences_when_both_present",
        "live_equal_origins",
        "live_different_origins",
    )
    totals = {key: sum(row.get(key, 0) for row in details) for key in keys}
    totals.update(
        {
            **score_totals,
            "max_abs_recomputed_score_error_kwh": max_score_error,
            "max_abs_recomputed_normalized_error": max_normalized_error,
            "max_abs_normalized_candidate_difference": max(
                row["max_abs_normalized_candidate_difference"] for row in details
            ),
            "max_abs_normalized_live_difference": max(
                row["max_abs_normalized_live_difference"] for row in details
            ),
        }
    )
    if (
        totals["score_abs_error_above_1e_minus_5_kwh"]
        or totals["normalized_abs_error_above_1e_minus_6"]
        or totals["label_value_differences_when_both_present"]
        or totals["asymmetric_label_presence_at_different_cursors"]
    ):
        raise ValueError("Terminal score or paired-label audit failed")
    result = {
        "schema": "hung-block7-terminal-numeric-audit-v3",
        "scope": "All 90-day issued origins in 69 historical Block7/Main checkpoint pairs",
        "prefix_import_sha256": hashlib.sha256(prefix_bytes).hexdigest(),
        "terminal_import_sha256": hashlib.sha256(terminal_bytes).hexdigest(),
        "pairs_sha256": stage.pairs.sha_file(PAIRS),
        "pair_count": len(details),
        "totals": totals,
        "by_index": {str(index): dict(counts) for index, counts in sorted(by_index.items())},
        "pairs": details,
    }
    payload = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        with OUT.open("xb") as stream:
            stream.write(payload)
    except FileExistsError:
        if OUT.read_bytes() != payload:
            raise ValueError("Existing terminal numeric audit differs") from None
    print(json.dumps(totals, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
