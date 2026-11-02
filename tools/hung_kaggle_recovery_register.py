"""Create the exact pending Kaggle archive retrieval checklist for Hung's ledger."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path

from tools.hung_kaggle_queue import EXPECTED_JOBSET_SHA

ROOT = Path(__file__).resolve().parents[1]
SHARDS = ROOT / ".cache/kaggle-payload-v2/payload/parent-shards.json"
ALLOCATION = ROOT / "docs/reports/evidence/hung-development-allocation-20261027-v1.json"
OUTPUT = ROOT / "docs/reports/hung-kaggle-560-recovery-register-20261028.csv"


def build_rows(shards: dict, allocation: dict) -> list[dict]:
    rows = []
    all_ids = []
    for shard in shards["shards"]:
        sid = shard["id"]
        if allocation["routes"][sid] != "kaggle":
            continue
        ids = shard["job_ids"]
        digest = hashlib.sha256(json.dumps(ids, separators=(",", ":")).encode("utf8")).hexdigest()
        if len(ids) != 20 or digest != EXPECTED_JOBSET_SHA[sid]:
            raise ValueError(f"Kaggle jobset mismatch: {sid}")
        all_ids.extend(ids)
        rows.append(
            {
                "shard_id": sid,
                "planned_jobs": len(ids),
                "planned_jobset_sha256": digest,
                "saved_version": "",
                "archive_bytes": "",
                "archive_sha256": "",
                "repository_ignored_archive_path": "",
                "per_job_status": "AWAITING_EXACT_ARCHIVE_BYTES",
            }
        )
    if len(rows) != 28 or len(all_ids) != 560 or len(set(all_ids)) != 560:
        raise ValueError("Expected 28 disjoint Kaggle shards and 560 jobs")
    return rows


def main() -> None:
    shards_raw = SHARDS.read_bytes()
    allocation = json.loads(ALLOCATION.read_text(encoding="utf8"))
    if hashlib.sha256(shards_raw).hexdigest() != allocation["partition_sha256"]:
        raise SystemExit("Partition SHA mismatch")
    rows = build_rows(json.loads(shards_raw), allocation)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    output = stream.getvalue().encode("utf8")
    if OUTPUT.exists():
        if OUTPUT.read_bytes() != output:
            raise SystemExit("Existing recovery checklist differs")
    else:
        OUTPUT.write_bytes(output)
    print(json.dumps({"shards": len(rows), "jobs": sum(row["planned_jobs"] for row in rows)}))


if __name__ == "__main__":
    main()
