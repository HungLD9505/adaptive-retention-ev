"""Compare full 90-day Block7/Main event tags from joined authenticated segments."""

from __future__ import annotations

import collections
import csv
import hashlib
import json
from pathlib import Path

from tools import hung_block7_journal_stage as stage

PREFIX = stage.ROOT / ".cache/block7-prefix-import-v1"
IMPORT = stage.ROOT / "docs/reports/hung-block7-prefix-import-20261030-v1.json"
PAIRS = stage.ROOT / "docs/reports/hung-block7-manifest-pairs-20261028.csv"
OUT = stage.ROOT / "docs/reports/hung-block7-full-event-order-20261030-v1.json"
DAILY = {"forecast", "skip", "score", "unscored", "update", "audit-update"}


def daily_tags(prefix: Path, suffix: Path) -> dict[str, list[str]]:
    days: dict[str, list[str]] = collections.defaultdict(list)
    expected_index = 0
    for path in (prefix, suffix):
        lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        if not lines or lines[0].get("start_event_index") != expected_index:
            raise ValueError(f"Discontinuous segment boundary: {path}")
        for event in lines[1:]:
            if event.get("kind") != "event" or event.get("event_index") != expected_index:
                raise ValueError(f"Discontinuous event index: {path}")
            expected_index += 1
            tag, _, rest = event["value"].partition(":")
            if tag in DAILY and rest[:4].isdigit():
                days[rest].append(tag)
    return dict(days)


def compare_days(historical: dict[str, list[str]], main: dict[str, list[str]]) -> dict:
    common = set(historical) & set(main)
    full_differences = 0
    audit_only = 0
    core_differences = 0
    for day in common:
        h_tags, m_tags = historical[day], main[day]
        if h_tags == m_tags:
            continue
        full_differences += 1
        if [tag for tag in h_tags if tag != "audit-update"] == [
            tag for tag in m_tags if tag != "audit-update"
        ]:
            audit_only += 1
        else:
            core_differences += 1
    return {
        "historical_days": len(historical),
        "main_days": len(main),
        "common_days": len(common),
        "historical_only_days": len(set(historical) - common),
        "main_only_days": len(set(main) - common),
        "full_tag_differences": full_differences,
        "audit_only_differences": audit_only,
        "core_tag_differences": core_differences,
    }


def main() -> int:
    records = stage.rows()
    if stage.REQUEST.read_bytes() != stage.render(records) or not stage.verify(records)["complete"]:
        raise ValueError("Saved suffix byte gate is incomplete")
    imported_bytes = IMPORT.read_bytes()
    imported = json.loads(imported_bytes)
    if imported["checked_stages"] != 138 or imported["checked_files"] != 414:
        raise ValueError("Prefix byte import is incomplete")
    by_id = {row["run_id"]: row for row in records}
    prefix_meta = {row["run_id"]: row for row in imported["details"]}
    if len(prefix_meta) != 138:
        raise ValueError("Duplicate prefix identity")
    with PAIRS.open(encoding="utf-8", newline="") as stream:
        pairs = list(csv.DictReader(stream))
    if len(pairs) != 69:
        raise ValueError("Expected 69 pairs")
    details = []
    for pair in pairs:
        maps = []
        for role in ("historical", "main"):
            run_id = pair[f"{role}_run_id"]
            if by_id[run_id]["role"] != role or prefix_meta[run_id]["role"] != role:
                raise ValueError("Pair role mismatch")
            prefix = PREFIX / run_id / "events.jsonl"
            suffix = stage.ROOT / by_id[run_id]["staged_path"]
            if (
                prefix.is_symlink()
                or stage.pairs.sha_file(prefix)
                != prefix_meta[run_id]["files"]["events.jsonl"]["sha256"]
            ):
                raise ValueError(f"Prefix journal SHA mismatch: {run_id}")
            maps.append(daily_tags(prefix, suffix))
        details.append({"cell_id": pair["cell_id"], **compare_days(*maps)})
    keys = (
        "historical_days",
        "main_days",
        "common_days",
        "historical_only_days",
        "main_only_days",
        "full_tag_differences",
        "audit_only_differences",
        "core_tag_differences",
    )
    totals = {key: sum(row[key] for row in details) for key in keys}
    result = {
        "schema": "hung-block7-full-event-order-v1",
        "scope": "Joined pre-resume and saved replay-90 journal segments for 69 pairs",
        "import_sha256": hashlib.sha256(imported_bytes).hexdigest(),
        "request_sha256": hashlib.sha256(stage.REQUEST.read_bytes()).hexdigest(),
        "pairs_sha256": stage.pairs.sha_file(PAIRS),
        "pair_count": len(details),
        "totals": totals,
        "pairs": details,
    }
    payload = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        with OUT.open("xb") as stream:
            stream.write(payload)
    except FileExistsError:
        if OUT.read_bytes() != payload:
            raise ValueError("Existing full-event audit differs") from None
    print(json.dumps(totals, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
