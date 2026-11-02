"""Compare Block7/Main saved-journal daily event order after the resume boundary."""

from __future__ import annotations

import csv
import hashlib
import json

from tools import hung_block7_journal_stage as stage
from tools.hung_block7_journal_audit_v1 import load_segment

PAIRS = stage.ROOT / "docs/reports/hung-block7-manifest-pairs-20261028.csv"
OUT = stage.ROOT / "docs/reports/hung-block7-shared-event-order-20261030-v1.json"
AUDIT_TAG = "audit-update"


def classify_pair(historical: dict[str, list[str]], main: dict[str, list[str]]) -> dict:
    if not historical or not main:
        raise ValueError("Empty saved journal day map")
    first_main_day = min(main)
    common = sorted(set(historical) & set(main))
    if first_main_day not in common:
        raise ValueError("Main resume-boundary day missing from historical segment")
    full_differences = []
    audit_only_differences = []
    core_boundary_differences = []
    core_nonboundary_differences = []
    for day in common:
        if historical[day] == main[day]:
            continue
        full_differences.append(day)
        h_core = [tag for tag in historical[day] if tag != AUDIT_TAG]
        m_core = [tag for tag in main[day] if tag != AUDIT_TAG]
        if h_core == m_core:
            audit_only_differences.append(day)
        elif day == first_main_day:
            core_boundary_differences.append(day)
        else:
            core_nonboundary_differences.append(day)
    return {
        "first_main_day": first_main_day,
        "common_days": len(common),
        "nonboundary_common_days": len(common) - 1,
        "full_tag_differences": len(full_differences),
        "audit_only_differences": len(audit_only_differences),
        "core_boundary_differences": len(core_boundary_differences),
        "core_nonboundary_differences": len(core_nonboundary_differences),
    }


def main() -> int:
    records = stage.rows()
    if stage.REQUEST.read_bytes() != stage.render(records) or not stage.verify(records)["complete"]:
        raise ValueError("The 138 pinned journals have not passed the exact-byte gate")
    by_id = {row["run_id"]: row for row in records}
    with PAIRS.open(encoding="utf-8", newline="") as stream:
        pairs = list(csv.DictReader(stream))
    if len(pairs) != 69:
        raise ValueError("Expected exactly 69 historical/Main pairs")
    details = []
    for pair in pairs:
        maps = []
        for role in ("historical", "main"):
            row = by_id[pair[f"{role}_run_id"]]
            if row["role"] != role:
                raise ValueError("Pair role mismatch")
            _, days, _ = load_segment(stage.ROOT / row["staged_path"])
            maps.append(days)
        details.append({"cell_id": pair["cell_id"], **classify_pair(*maps)})
    totals = {
        key: sum(item[key] for item in details)
        for key in (
            "common_days",
            "nonboundary_common_days",
            "full_tag_differences",
            "audit_only_differences",
            "core_boundary_differences",
            "core_nonboundary_differences",
        )
    }
    result = {
        "schema": "hung-block7-shared-event-order-v1",
        "request_sha256": hashlib.sha256(stage.REQUEST.read_bytes()).hexdigest(),
        "pairs_sha256": stage.pairs.sha_file(PAIRS),
        "pair_count": len(details),
        "boundary_rule": "Exclude the first Main saved-journal day in every pair before comparing core tags",
        "core_tags": ["forecast", "skip", "score", "unscored", "update"],
        "excluded_separate_branch_tag": AUDIT_TAG,
        "totals": totals,
        "pairs": details,
    }
    payload = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        with OUT.open("xb") as stream:
            stream.write(payload)
    except FileExistsError:
        if OUT.read_bytes() != payload:
            raise ValueError("Existing shared-event audit differs") from None
    print(json.dumps(totals, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
