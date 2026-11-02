"""Verify a version-pinned Kaggle compact proof downloaded into this repository."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

EXPECTED_SCHEMA = "hung-kaggle-compact-shard-proof-v2"
EXPECTED_STATUS = "VERIFIED_ARCHIVE_BYTES_AND_STAGE_PLAN"
READBACK_SCHEMA = "hung-kaggle-compact-proof-local-readback-v1"


def sha256(raw: bytes) -> str:
    """Return a lowercase SHA-256 digest."""
    return hashlib.sha256(raw).hexdigest()


def require(condition: bool, message: str) -> None:
    """Reject an invalid proof even when Python assertions are disabled."""
    if not condition:
        raise ValueError(message)


def readback(
    proof_path: Path,
    *,
    expected_bytes: int,
    expected_sha256: str,
    expected_shard: str,
    expected_jobset_sha256: str,
    source_kernel: str,
    source_version_ordinal: int,
    source_script_version_id: int,
) -> dict:
    """Check saved bytes and the frozen shard identity before issuing a receipt."""
    raw = proof_path.read_bytes()
    require(len(raw) == expected_bytes, "Proof byte count mismatch")
    require(sha256(raw) == expected_sha256, "Proof SHA-256 mismatch")
    proof = json.loads(raw)
    require(proof["schema"] == EXPECTED_SCHEMA, "Proof schema mismatch")
    require(proof["scope"] == "development_only", "Proof scope mismatch")
    require(proof["shard_id"] == expected_shard, "Proof shard mismatch")
    rows = proof["rows"]
    require(len(rows) == 20, "Expected one 20-job shard")
    job_ids = [row["job_id"] for row in rows]
    require(len(set(job_ids)) == 20, "Duplicate job ID")
    jobset_sha256 = sha256(json.dumps(job_ids, separators=(",", ":")).encode("utf-8"))
    require(jobset_sha256 == expected_jobset_sha256, "Ordered jobset mismatch")
    for row in rows:
        require(row["shard_id"] == expected_shard, "Row shard mismatch")
        require(row["status"] == EXPECTED_STATUS, "Row status mismatch")
        manifests = row["stage_manifest_sha256"]
        receipts = row["stage_receipt_sha256"]
        require(isinstance(manifests, dict) and manifests, "Missing stage manifests")
        require(isinstance(receipts, dict), "Missing stage receipts")
        require(set(manifests) == set(receipts), "Stage manifest/receipt mismatch")
        require(
            all(
                isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
                for value in [*manifests.values(), *receipts.values()]
            ),
            "Invalid stage SHA-256",
        )
    return {
        "schema": READBACK_SCHEMA,
        "scope": "development_only",
        "status": "LOCAL_SAVED_OUTPUT_BYTES_VERIFIED",
        "source_kernel": source_kernel,
        "source_version_ordinal": source_version_ordinal,
        "source_script_version_id_observed_in_ui": source_script_version_id,
        "proof_path": proof_path.as_posix(),
        "proof_bytes": len(raw),
        "proof_sha256": sha256(raw),
        "shard_id": expected_shard,
        "jobset_sha256": jobset_sha256,
        "job_ids": job_ids,
        "jobs": 20,
    }


def main() -> None:
    """Write a create-only local receipt after all checks pass."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--expected-bytes", type=int, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--expected-shard", required=True)
    parser.add_argument("--expected-jobset-sha256", required=True)
    parser.add_argument("--source-kernel", required=True)
    parser.add_argument("--source-version-ordinal", type=int, required=True)
    parser.add_argument("--source-script-version-id", type=int, required=True)
    args = parser.parse_args()
    result = readback(
        args.proof,
        expected_bytes=args.expected_bytes,
        expected_sha256=args.expected_sha256,
        expected_shard=args.expected_shard,
        expected_jobset_sha256=args.expected_jobset_sha256,
        source_kernel=args.source_kernel,
        source_version_ordinal=args.source_version_ordinal,
        source_script_version_id=args.source_script_version_id,
    )
    with args.receipt.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "jobs": 20}, sort_keys=True))


if __name__ == "__main__":
    main()
