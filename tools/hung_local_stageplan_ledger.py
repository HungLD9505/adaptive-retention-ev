"""Build a create-only 782-job ledger from pinned local exact-stage proofs.

The input manifest lives under repository .cache and lists one entry per Kaggle
shard. Each entry pins proof, archive and shard receipt path/bytes/SHA. Saved
Kaggle version IDs in the proof remain caller claims; this module checks local
bytes and job bindings, not provider identity or scientific acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import zipfile
from typing import Any

from tools import hung_import_compact_proof_ledger as frozen

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache"
VERIFIER = ROOT / "tools/hung_kaggle_compact_proof.py"
VERIFIER_SHA256 = "412c5d3c2802f6c9ba072cef2efc80e9b6ea71bc0776f3468d6a638e573e77e5"
STATUS = "VERIFIED_LOCAL_ARCHIVE_STAGE_BYTES"
NEW_FIELDS = ("archive_receipt_path", "archive_receipt_bytes", "archive_receipt_sha256")
MAX_JSON_BYTES = 2 * 1024 * 1024


def require(condition: bool, message: str) -> None:
    if not condition:
        raise frozen.ProofImportError(message)


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pinned_path(entry: dict[str, Any], name: str, cache: pathlib.Path) -> pathlib.Path:
    pin = entry.get(name)
    require(isinstance(pin, dict), f"Missing {name} pin")
    path = frozen.cache_file(cache, pin.get("path"), name)
    size = pin.get("bytes")
    sha = pin.get("sha256")
    require(type(size) is int and size > 0, f"Invalid {name} byte count")
    require(frozen.valid_sha(sha), f"Invalid {name} SHA-256")
    require(path.stat().st_size == size and file_sha256(path) == sha, f"{name} bytes/SHA mismatch")
    return path


def pinned_json(entry: dict[str, Any], name: str, cache: pathlib.Path) -> dict[str, Any]:
    path = pinned_path(entry, name, cache)
    require(path.stat().st_size <= MAX_JSON_BYTES, f"Unbounded {name} JSON")
    return frozen.read_json_bytes(path.read_bytes(), name)


def stage_hashes(row: dict[str, Any], job_id: str) -> tuple[str, str]:
    manifests = row.get("stage_manifest_sha256")
    receipts = row.get("stage_receipt_sha256")
    require(isinstance(manifests, dict) and manifests, f"Missing stage manifests: {job_id}")
    require(
        isinstance(receipts, dict) and set(receipts) == set(manifests), f"Stage mismatch: {job_id}"
    )
    require(
        all(frozen.valid_sha(value) for value in manifests.values()),
        f"Stage manifest SHA: {job_id}",
    )
    require(
        all(frozen.valid_sha(value) for value in receipts.values()), f"Stage receipt SHA: {job_id}"
    )
    return (
        ";".join(f"{stage}:{manifests[stage]}" for stage in sorted(manifests)),
        ";".join(f"{stage}:{receipts[stage]}" for stage in sorted(receipts)),
    )


def validate_shard(
    entry: dict[str, Any],
    expected_ids: list[str],
    base_by_id: dict[str, dict[str, str]],
    allocation: dict[str, Any],
    cache: pathlib.Path,
) -> dict[str, dict[str, str]]:
    """Reopen a pinned archive and bind each corrected proof row to its bytes."""
    shard_id = entry.get("shard_id")
    require(isinstance(shard_id, str), "Missing shard ID")
    proof = pinned_json(entry, "proof", cache)
    receipt = pinned_json(entry, "receipt", cache)
    archive_path = pinned_path(entry, "archive", cache)
    archive_pin = entry["archive"]
    require(
        proof.get("schema") == "hung-kaggle-compact-shard-proof-v2", f"Proof schema: {shard_id}"
    )
    require(proof.get("scope") == "development_only", f"Proof scope: {shard_id}")
    require(
        proof.get("shard_id") == receipt.get("shard_id") == shard_id, f"Shard binding: {shard_id}"
    )
    require(
        proof.get("parent_plan_sha256") == allocation["plan_sha256"]
        and proof.get("parent_partition_sha256") == allocation["partition_sha256"]
        and proof.get("model_code_commit") == allocation["canonical_code_sha"],
        f"Frozen plan/model binding: {shard_id}",
    )
    require(
        proof.get("provider_plan_sha256") == receipt.get("plan_sha256")
        and proof.get("provider_partition_sha256") == receipt.get("shards_sha256"),
        f"Provider plan binding: {shard_id}",
    )
    require(
        proof.get("archive_sha256") == receipt.get("artifact_sha256") == archive_pin["sha256"]
        and proof.get("archive_bytes") == receipt.get("artifact_bytes") == archive_pin["bytes"],
        f"Archive binding: {shard_id}",
    )
    require(
        receipt.get("crc") == "passed"
        and receipt.get("exit_code") == 0
        and receipt.get("local_verify_exit_code") == 0,
        f"Execution/CRC receipt: {shard_id}",
    )
    require(receipt.get("job_ids") == expected_ids, f"Receipt jobset/order: {shard_id}")
    require(
        type(proof.get("claimed_saved_version_id")) is int
        and proof["claimed_saved_version_id"] > 0
        and type(proof.get("claimed_readback_version_id")) is int
        and proof["claimed_readback_version_id"] > 0
        and proof.get("version_ids_independently_authenticated") is False,
        f"Version claim fields: {shard_id}",
    )
    rows = proof.get("rows")
    require(isinstance(rows, list) and len(rows) == 20, f"Proof row count: {shard_id}")
    require(
        [row.get("job_id") for row in rows if isinstance(row, dict)] == expected_ids,
        f"Proof jobset/order: {shard_id}",
    )
    results: dict[str, dict[str, str]] = {}
    with zipfile.ZipFile(archive_path) as archive:
        require(archive.testzip() is None, f"Archive ZIP CRC failure: {shard_id}")
        names = archive.namelist()
        members = set(names)
        require(len(names) == len(members), f"Duplicate archive member: {shard_id}")
        for row in rows:
            job_id = row["job_id"]
            base = base_by_id[job_id]
            require(base["provider_route"] == "kaggle", f"Non-Kaggle job: {job_id}")
            require(
                row.get("status") == "VERIFIED_ARCHIVE_BYTES_AND_STAGE_PLAN",
                f"Proof status: {job_id}",
            )
            for field in (
                "job_id",
                "shard_id",
                "method",
                "cell_id",
                "budget_days",
                "seed",
                "entity_id",
                "input_manifest_sha256",
                "config_sha256",
            ):
                require(str(row.get(field)) == base[field], f"{field} mismatch: {job_id}")
            require(
                type(row.get("verified_member_count")) is int and row["verified_member_count"] > 0,
                f"No verified members: {job_id}",
            )
            manifest_text, receipt_text = stage_hashes(row, job_id)
            job_receipt = f"receipts/{job_id}/job.json"
            require(job_receipt in members, f"Missing job receipt: {job_id}")
            job_receipt_bytes = archive.read(job_receipt)
            require(
                frozen.sha256_bytes(job_receipt_bytes) == row.get("job_receipt_sha256"),
                f"Job receipt SHA: {job_id}",
            )
            job_claim = frozen.read_json_bytes(job_receipt_bytes, job_receipt)
            require(
                job_claim.get("schema") == "hung-dispatch-job-receipt-v1"
                and job_claim.get("job_id") == job_id
                and job_claim.get("plan_sha256") == proof["provider_plan_sha256"]
                and job_claim.get("shards_sha256") == proof["provider_partition_sha256"]
                and job_claim.get("stages") == row["stage_receipt_sha256"],
                f"Job receipt stage/plan binding: {job_id}",
            )
            for stage, sha in row["stage_receipt_sha256"].items():
                stage_receipt = f"receipts/{job_id}/{stage}.json"
                stage_manifest = f"jobs/{job_id}/{stage}/run_manifest.json"
                require(
                    stage_receipt in members and stage_manifest in members,
                    f"Missing stage: {job_id}/{stage}",
                )
                require(
                    frozen.sha256_bytes(archive.read(stage_receipt)) == sha,
                    f"Stage receipt SHA: {job_id}/{stage}",
                )
                require(
                    frozen.sha256_bytes(archive.read(stage_manifest))
                    == row["stage_manifest_sha256"][stage],
                    f"Stage manifest SHA: {job_id}/{stage}",
                )
            results[job_id] = {
                "archive_path": entry["archive"]["path"],
                "archive_bytes": str(archive_pin["bytes"]),
                "archive_sha256": archive_pin["sha256"],
                "job_receipt_path": job_receipt,
                "job_receipt_sha256": row["job_receipt_sha256"],
                "stage_manifest_sha256": manifest_text,
                "stage_receipt_sha256": receipt_text,
                "status": STATUS,
                "reason": (
                    "Corrected verifier v2 local archive/member SHA, ZIP CRC and exact stage plan "
                    "rechecked; saved version IDs remain caller claims; peer review pending"
                ),
                "proof_path": entry["proof"]["path"],
                "proof_bytes": str(entry["proof"]["bytes"]),
                "proof_sha256": entry["proof"]["sha256"],
                "claimed_archive_carrier_version_id": str(proof["claimed_saved_version_id"]),
                "claimed_archive_readback_version_id": str(proof["claimed_readback_version_id"]),
                "provider_version_binding": "CLAIMED; independently review saved provider source/version",
                "archive_receipt_path": entry["receipt"]["path"],
                "archive_receipt_bytes": str(entry["receipt"]["bytes"]),
                "archive_receipt_sha256": entry["receipt"]["sha256"],
            }
    return results


def build_rows(manifest: dict[str, Any], cache: pathlib.Path = CACHE) -> list[dict[str, str]]:
    require(manifest.get("schema") == "hung-local-stageplan-ledger-v1", "Manifest schema mismatch")
    require(manifest.get("scope") == "development_only", "Manifest scope mismatch")
    require(manifest.get("verifier_sha256") == VERIFIER_SHA256, "Verifier manifest pin mismatch")
    require(file_sha256(VERIFIER) == VERIFIER_SHA256, "Corrected verifier source changed")
    base_rows, jobsets, allocation = frozen.read_base_and_jobsets()
    entries = manifest.get("entries")
    require(isinstance(entries, list) and len(entries) == 28, "Expected exactly 28 Kaggle shards")
    ids = [entry.get("shard_id") for entry in entries if isinstance(entry, dict)]
    require(len(ids) == 28 and set(ids) == set(jobsets), "Manifest shard set/duplicates")
    base_by_id = {row["job_id"]: row for row in base_rows}
    fields = list(base_rows[0]) + list(frozen.EXTRA_FIELDS) + list(NEW_FIELDS)
    result = [{field: row.get(field, "") for field in fields} for row in base_rows]
    result_by_id = {row["job_id"]: row for row in result}
    seen_jobs: set[str] = set()
    for entry in entries:
        shard_id = entry["shard_id"]
        verified = validate_shard(entry, jobsets[shard_id][0], base_by_id, allocation, cache)
        require(not seen_jobs.intersection(verified), f"Duplicate verified jobs: {shard_id}")
        seen_jobs.update(verified)
        for job_id, values in verified.items():
            result_by_id[job_id].update(values)
    require(len(seen_jobs) == 560, "Verified Kaggle job count mismatch")
    require(
        sum(row["status"] == "VERIFIED_LOCAL_BYTES" for row in result) == 222, "Local rows changed"
    )
    require(sum(row["status"] == STATUS for row in result) == 560, "Kaggle rows incomplete")
    require(len(result) == 782 and len(result_by_id) == 782, "Ledger cardinality mismatch")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        path = frozen.cache_file(CACHE, str(args.manifest), "manifest")
        require(path.stat().st_size <= MAX_JSON_BYTES, "Unbounded manifest")
        rows = build_rows(frozen.read_json_bytes(path.read_bytes(), "manifest"))
        destination = frozen.output_path(args.out)
        digest = frozen.write_ledger(destination, rows)
    except (KeyError, OSError, TypeError, ValueError, zipfile.BadZipFile) as error:
        parser.exit(1, f"Local stage-plan ledger failed: {error}\n")
    print(
        json.dumps(
            {"ledger": str(destination), "sha256": digest, "rows": 782, "local": 222, "kaggle": 560}
        )
    )


if __name__ == "__main__":
    main()
