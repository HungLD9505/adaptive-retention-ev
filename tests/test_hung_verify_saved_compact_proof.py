"""Local readback must reject missing proof stages and changed bytes."""

from __future__ import annotations

import json

import pytest

from tools.hung_verify_saved_compact_proof import readback, sha256


def test_version_pinned_local_readback(tmp_path):
    ids = [f"job_{index:02d}" for index in range(20)]
    stage_sha = "a" * 64
    rows = [
        {
            "job_id": job_id,
            "shard_id": "shard_0001",
            "status": "VERIFIED_ARCHIVE_BYTES_AND_STAGE_PLAN",
            "stage_manifest_sha256": {"source": stage_sha},
            "stage_receipt_sha256": {"source": stage_sha},
        }
        for job_id in ids
    ]
    proof = {
        "schema": "hung-kaggle-compact-shard-proof-v2",
        "scope": "development_only",
        "shard_id": "shard_0001",
        "rows": rows,
    }
    raw = json.dumps(proof).encode()
    path = tmp_path / "proof.json"
    path.write_bytes(raw)
    expected = {
        "expected_bytes": len(raw),
        "expected_sha256": sha256(raw),
        "expected_shard": "shard_0001",
        "expected_jobset_sha256": sha256(json.dumps(ids, separators=(",", ":")).encode()),
        "source_kernel": "owner/kernel",
        "source_version_ordinal": 1,
        "source_script_version_id": 123,
    }
    result = readback(path, **expected)
    assert result["jobs"] == 20
    assert result["proof_sha256"] == sha256(raw)

    with pytest.raises(ValueError, match="Proof SHA-256 mismatch"):
        readback(path, **{**expected, "expected_sha256": "0" * 64})

    rows[0]["stage_receipt_sha256"] = {}
    changed = json.dumps(proof).encode()
    path.write_bytes(changed)
    with pytest.raises(ValueError, match="Stage manifest/receipt mismatch"):
        readback(
            path,
            **{**expected, "expected_bytes": len(changed), "expected_sha256": sha256(changed)},
        )
