"""Bind 138 saved Block7/Main journal segments to their pinned manifests."""

from __future__ import annotations

import collections
import hashlib
import json

from tools import hung_block7_journal_stage as stage
from tools.hung_block7_journal_audit_v1 import load_segment

OUT = stage.ROOT / "docs/reports/hung-block7-journal-manifest-binding-20261030-v1.json"


def validate_binding(row: dict[str, str], manifest: dict, header: dict, event_count: int) -> None:
    journal = manifest["event_journal"]
    expected = {
        "file": "events.jsonl",
        "sha256": row["sha256"],
        "start_event_index": header["start_event_index"],
        "end_event_index": header["start_event_index"] + event_count,
        "events_written": event_count,
    }
    if journal != expected:
        raise ValueError(f"Journal manifest binding mismatch: {row['run_id']}")
    if header.get("schema") != "hung-sprint2-event-journal-v1":
        raise ValueError(f"Journal schema mismatch: {row['run_id']}")
    if header.get("input_binding") != manifest.get("input_binding"):
        raise ValueError(f"Input binding mismatch: {row['run_id']}")
    if header.get("resumed_from") != manifest.get("resumed_from"):
        raise ValueError(f"Resume binding mismatch: {row['run_id']}")
    if manifest.get("runner_cursor") != 90:
        raise ValueError(f"Unexpected runner cursor: {row['run_id']}")


def main() -> int:
    records = stage.rows()
    if stage.REQUEST.read_bytes() != stage.render(records) or not stage.verify(records)["complete"]:
        raise ValueError("The 138 pinned journal bytes have not passed the stage gate")
    counts = collections.Counter()
    details = []
    for row in records:
        path = stage.ROOT / row["staged_path"]
        header, _, tags = load_segment(path)
        event_count = sum(tags.values())
        manifest_path = stage.ROOT / ".cache/block7-review-v1/manifests" / f"{row['run_id']}.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        validate_binding(row, manifest, header, event_count)
        counts[row["role"]] += 1
        details.append(
            {
                "role": row["role"],
                "run_id": row["run_id"],
                "journal_sha256": row["sha256"],
                "manifest_sha256": stage.pairs.sha_file(manifest_path),
                "start_event_index": header["start_event_index"],
                "end_event_index": header["start_event_index"] + event_count,
                "events_written": event_count,
                "resumed_from_run_id": header["resumed_from"]["run_id"],
            }
        )
    if counts != {"historical": 69, "main": 69}:
        raise ValueError("Expected 69 historical and 69 Main segments")
    result = {
        "schema": "hung-block7-journal-manifest-binding-v1",
        "request_sha256": hashlib.sha256(stage.REQUEST.read_bytes()).hexdigest(),
        "checked": len(details),
        "role_counts": dict(counts),
        "bindings": details,
        "scope": "Saved replay-90 suffixes only; no numeric forecasts or pre-resume journals",
    }
    payload = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        with OUT.open("xb") as stream:
            stream.write(payload)
    except FileExistsError:
        if OUT.read_bytes() != payload:
            raise ValueError("Existing journal binding audit differs") from None
    print(json.dumps({"checked": len(details), "role_counts": dict(counts)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
