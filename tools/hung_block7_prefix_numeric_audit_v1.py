"""Compare authenticated pre-resume Block7/Main issued forecast snapshots."""

from __future__ import annotations

import collections
import csv
import hashlib
import json

import torch

from tools import hung_block7_journal_stage as stage

PREFIX = stage.ROOT / ".cache/block7-prefix-import-v1"
IMPORT = stage.ROOT / "docs/reports/hung-block7-prefix-import-20261030-v1.json"
PAIRS = stage.ROOT / "docs/reports/hung-block7-manifest-pairs-20261028.csv"
OUT = stage.ROOT / "docs/reports/hung-block7-prefix-numeric-audit-20261030-v1.json"


def compare_issued(historical: list[dict], main: list[dict]) -> tuple[dict, dict[int, dict]]:
    main_by_day = {row["day_id"]: row for row in main}
    if len(main_by_day) != len(main) or len({row["day_id"] for row in historical}) != len(
        historical
    ):
        raise ValueError("Duplicate issued day")
    if not {row["day_id"] for row in historical}.issubset(main_by_day):
        raise ValueError("Historical prefix contains an unmatched issued day")
    counts: collections.Counter[str] = collections.Counter()
    by_index: dict[int, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    first_difference = None
    max_abs_normalized_difference = 0.0
    for row in historical:
        other = main_by_day[row["day_id"]]
        index = row["index"]
        if other["index"] != index:
            raise ValueError("Issued day index differs")
        counts["common_issued"] += 1
        by_index[index]["common"] += 1
        if row["active_level"] != other["active_level"]:
            counts["active_level_differences"] += 1
            by_index[index]["active_level_differences"] += 1
        a_label, b_label = row["y_scaled"], other["y_scaled"]
        if a_label is None and b_label is None:
            counts["both_labels_absent_at_snapshot"] += 1
        elif a_label is None or b_label is None:
            counts["asymmetric_label_presence_at_different_cursors"] += 1
        else:
            counts["both_labels_present"] += 1
            if not torch.equal(a_label, b_label):
                counts["label_value_differences_when_both_present"] += 1
        a_forecasts, b_forecasts = row["forecasts"], other["forecasts"]
        if not isinstance(a_forecasts, list) or len(a_forecasts) != len(b_forecasts):
            raise ValueError("Candidate forecast inventory differs")
        changed = False
        for a, b in zip(a_forecasts, b_forecasts):
            if a.shape != b.shape or not torch.isfinite(a).all() or not torch.isfinite(b).all():
                raise ValueError("Invalid candidate forecast tensor")
            if not torch.equal(a, b):
                changed = True
                max_abs_normalized_difference = max(
                    max_abs_normalized_difference, float(torch.max(torch.abs(a - b)))
                )
        if changed:
            counts["forecast_different_origins"] += 1
            by_index[index]["forecast_different"] += 1
            if first_difference is None:
                first_difference = {"index": index, "day_id": row["day_id"]}
    result = {
        **counts,
        "forecast_equal_origins": counts["common_issued"] - counts["forecast_different_origins"],
        "first_forecast_difference": first_difference,
        "max_abs_normalized_candidate_difference": max_abs_normalized_difference,
    }
    return result, {index: dict(values) for index, values in sorted(by_index.items())}


def main() -> int:
    imported_bytes = IMPORT.read_bytes()
    imported = json.loads(imported_bytes)
    if imported["checked_stages"] != 138 or imported["checked_files"] != 414:
        raise ValueError("Pre-resume byte import is incomplete")
    identities = {item["run_id"]: item for item in imported["details"]}
    if len(identities) != 138:
        raise ValueError("Duplicate imported run identity")
    with PAIRS.open(encoding="utf-8", newline="") as stream:
        pairs = list(csv.DictReader(stream))
    if len(pairs) != 69:
        raise ValueError("Expected 69 Block7/Main pairs")
    states = {}
    for run_id, item in identities.items():
        root = PREFIX / run_id
        for name, meta in item["files"].items():
            path = root / name
            if path.is_symlink() or path.stat().st_size != meta["bytes"]:
                raise ValueError(f"Staged prefix file mismatch: {run_id}/{name}")
            if stage.pairs.sha_file(path) != meta["sha256"]:
                raise ValueError(f"Staged prefix SHA mismatch: {run_id}/{name}")
        manifest = json.loads((root / "run_manifest.json").read_text(encoding="utf-8"))
        journal = [
            json.loads(line)
            for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()[1:]
        ]
        state = torch.load(root / "runner_checkpoint.pt", map_location="cpu", weights_only=True)
        if (
            state["binding"] != manifest["input_binding"]
            or state["next_index"] != manifest["runner_cursor"]
            or state["events"] != [event["value"] for event in journal]
        ):
            raise ValueError(f"Checkpoint/journal/manifest state mismatch: {run_id}")
        states[run_id] = state
    rows = []
    index_totals: dict[int, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    for pair in pairs:
        h_id, m_id = pair["historical_run_id"], pair["main_run_id"]
        result, by_index = compare_issued(states[h_id]["issued"], states[m_id]["issued"])
        rows.append({"cell_id": pair["cell_id"], **result})
        for index, values in by_index.items():
            index_totals[index].update(values)
    count_keys = (
        "common_issued",
        "forecast_equal_origins",
        "forecast_different_origins",
        "active_level_differences",
        "both_labels_absent_at_snapshot",
        "both_labels_present",
        "asymmetric_label_presence_at_different_cursors",
        "label_value_differences_when_both_present",
    )
    totals = {key: sum(row.get(key, 0) for row in rows) for key in count_keys}
    totals["max_abs_normalized_candidate_difference"] = max(
        row["max_abs_normalized_candidate_difference"] for row in rows
    )
    result = {
        "schema": "hung-block7-prefix-numeric-audit-v1",
        "scope": "Shared issued origins in replay-21 historical and replay-42 Main checkpoints only",
        "import_sha256": hashlib.sha256(imported_bytes).hexdigest(),
        "pairs_sha256": stage.pairs.sha_file(PAIRS),
        "pair_count": len(rows),
        "totals": totals,
        "by_index": {str(index): dict(values) for index, values in sorted(index_totals.items())},
        "pairs": rows,
    }
    payload = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        with OUT.open("xb") as stream:
            stream.write(payload)
    except FileExistsError:
        if OUT.read_bytes() != payload:
            raise ValueError("Existing numeric audit differs") from None
    print(json.dumps(totals, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
