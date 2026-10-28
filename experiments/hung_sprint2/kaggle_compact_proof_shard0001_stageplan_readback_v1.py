"""Independently read back the first saved exact-stage compact proof."""

import hashlib
import json
from pathlib import Path

SOURCE_NOTEBOOK = "hungluongduc/hung-compact-proof-shard0001-stageplan-20261028-v3"
SOURCE_VERSION_ID = 363123440
PROOF_BYTES = 21699
PROOF_SHA256 = "14ab3b12684f6358f628d1cc083470655acadde84ab8c0b475582abc64de2e11"
EXPECTED_JOBSET_SHA256 = "e2051de08dfb0f0ee91c3617151f08d5cd2c712bb88344244980e4ec2f350c69"

matches = list(Path("/kaggle/input").rglob("compact-proof.json"))
assert len(matches) == 1, "Exactly one saved proof output must be attached"
proof_path = matches[0]
assert "hung-compact-proof-shard0001-stageplan-20261028-v3" in str(proof_path)
raw = proof_path.read_bytes()
assert len(raw) == PROOF_BYTES and hashlib.sha256(raw).hexdigest() == PROOF_SHA256
proof = json.loads(raw)
assert proof["schema"] == "hung-kaggle-compact-shard-proof-v2"
assert proof["scope"] == "development_only"
assert proof["shard_id"] == "shard_0001"
assert proof["archive_sha256"] == "29e3db51106402942959f80762e4c27995ad4ec9f2253fd96cc8a4681d3b2dcd"
assert proof["archive_bytes"] == 65931034
assert (
    proof["verifier_sha256"] == "412c5d3c2802f6c9ba072cef2efc80e9b6ea71bc0776f3468d6a638e573e77e5"
)
rows = proof["rows"]
job_ids = [row["job_id"] for row in rows]
assert len(job_ids) == len(set(job_ids)) == 20
assert all(
    row["status"] == "VERIFIED_ARCHIVE_BYTES_AND_STAGE_PLAN"
    and row["shard_id"] == "shard_0001"
    and len(row["stage_receipt_sha256"]) >= 2
    and len(row["stage_manifest_sha256"]) == len(row["stage_receipt_sha256"])
    for row in rows
)
jobset_sha256 = hashlib.sha256(
    json.dumps(job_ids, separators=(",", ":")).encode("utf-8")
).hexdigest()
assert jobset_sha256 == EXPECTED_JOBSET_SHA256
readback = {
    "schema": "hung-kaggle-compact-proof-readback-v2",
    "scope": "development_only",
    "source_notebook": SOURCE_NOTEBOOK,
    "claimed_source_version_id": SOURCE_VERSION_ID,
    "proof_bytes": len(raw),
    "proof_sha256": hashlib.sha256(raw).hexdigest(),
    "jobset_sha256": jobset_sha256,
    "job_ids": job_ids,
    "jobs": 20,
    "status": "REMOTE_STAGEPLAN_PROOF_READBACK_VERIFIED",
}
out = Path("/kaggle/working/hung-compact-proof-shard0001-stageplan-readback-20261028-v1.json")
with out.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(readback, stream, sort_keys=True, indent=2, allow_nan=False)
    stream.write("\n")
print(
    json.dumps(
        {
            "status": readback["status"],
            "jobs": 20,
            "proof_bytes": readback["proof_bytes"],
            "proof_sha256": readback["proof_sha256"],
            "jobset_sha256": jobset_sha256,
        },
        sort_keys=True,
    )
)
