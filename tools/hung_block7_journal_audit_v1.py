"""Audit the exact staged Block7/Main replay-90 event-journal segments."""

from __future__ import annotations

import collections
import csv
import hashlib
import json
from pathlib import Path

from tools import hung_block7_journal_stage as stage

PAIRS = stage.ROOT / "docs/reports/hung-block7-manifest-pairs-20261028.csv"
OUT = stage.ROOT / "docs/reports/hung-block7-journal-audit-20261030-v1.json"
DAILY = {"forecast", "skip", "score", "unscored", "update", "audit-update"}


def load_segment(path: Path) -> tuple[dict, dict[str, list[str]], dict[str, int]]:
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if not lines or lines[0].get("kind") != "header" or lines[0].get("run_id") != "replay-90":
        raise ValueError(f"Invalid replay-90 header: {path.name}")
    header = lines[0]
    start = header["start_event_index"]
    days: dict[str, list[str]] = collections.defaultdict(list)
    tags: collections.Counter[str] = collections.Counter()
    for offset, event in enumerate(lines[1:]):
        if event.get("kind") != "event" or event.get("event_index") != start + offset:
            raise ValueError(f"Non-contiguous event index: {path.name}")
        value = event.get("value")
        if not isinstance(value, str):
            raise ValueError(f"Invalid event value: {path.name}")
        tag, _, rest = value.partition(":")
        tags[tag] += 1
        if tag in DAILY and rest[:4].isdigit():
            days[rest].append(tag)
    return header, dict(days), dict(tags)


def main() -> int:
    records = stage.rows()
    if stage.REQUEST.read_bytes() != stage.render(records) or not stage.verify(records)["complete"]:
        raise ValueError("The 138 pinned journal bytes have not passed the stage gate")
    by_id = {row["run_id"]: row for row in records}
    segments = {}
    role_tags = {"historical": collections.Counter(), "main": collections.Counter()}
    starts = {"historical": collections.Counter(), "main": collections.Counter()}
    for row in records:
        header, days, tags = load_segment(stage.ROOT / row["staged_path"])
        segments[row["run_id"]] = (header, days)
        role_tags[row["role"]].update(tags)
        starts[row["role"]][str(header["start_event_index"])] += 1

    with PAIRS.open(encoding="utf-8", newline="") as stream:
        pairs = list(csv.DictReader(stream))
    if len(pairs) != 69:
        raise ValueError("Expected exactly 69 Block7/Main pairs")
    pair_rows = []
    for pair in pairs:
        h_id, m_id = pair["historical_run_id"], pair["main_run_id"]
        if by_id[h_id]["role"] != "historical" or by_id[m_id]["role"] != "main":
            raise ValueError("Pair role mismatch")
        h_header, h_days = segments[h_id]
        m_header, m_days = segments[m_id]
        common = sorted(set(h_days) & set(m_days))
        differences = [day for day in common if h_days[day] != m_days[day]]
        pair_rows.append(
            {
                "cell_id": pair["cell_id"],
                "historical_start_event_index": h_header["start_event_index"],
                "main_start_event_index": m_header["start_event_index"],
                "historical_journal_days": len(h_days),
                "main_journal_days": len(m_days),
                "common_journal_days": len(common),
                "common_days_with_different_tag_sequences": len(differences),
            }
        )
    result = {
        "schema": "hung-block7-journal-audit-v1",
        "scope": "replay-90 saved journal segments only; resumed prefixes are absent",
        "request_sha256": hashlib.sha256(stage.REQUEST.read_bytes()).hexdigest(),
        "pairs_sha256": stage.pairs.sha_file(PAIRS),
        "journal_count": len(records),
        "role_tag_counts": {role: dict(tags) for role, tags in role_tags.items()},
        "start_event_index_counts": {role: dict(counts) for role, counts in starts.items()},
        "pair_count": len(pair_rows),
        "common_journal_days": sum(row["common_journal_days"] for row in pair_rows),
        "common_days_with_different_tag_sequences": sum(
            row["common_days_with_different_tag_sequences"] for row in pair_rows
        ),
        "pairs_with_different_common_day_tags": sum(
            row["common_days_with_different_tag_sequences"] > 0 for row in pair_rows
        ),
        "pairs": pair_rows,
    }
    payload = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        with OUT.open("xb") as stream:
            stream.write(payload)
    except FileExistsError:
        if OUT.read_bytes() != payload:
            raise ValueError("Existing audit differs") from None
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "journal_count",
                    "pair_count",
                    "common_journal_days",
                    "common_days_with_different_tag_sequences",
                    "pairs_with_different_common_day_tags",
                )
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
