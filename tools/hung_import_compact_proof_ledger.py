"""Import saved Kaggle compact proofs into a new Development ledger snapshot.

This validates local copies of proof/readback JSON. Caller-supplied provider version
IDs remain claims: this module does not query Kaggle or reopen the original archives.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import pathlib
import re
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORTS = ROOT / "docs/reports"
CACHE = ROOT / ".cache"
LEDGER_V2 = REPORTS / "hung-development-782-job-ledger-20261028-v2.csv"
RECOVERY_REGISTER = REPORTS / "hung-kaggle-560-recovery-register-20261028.csv"
ALLOCATION = REPORTS / "evidence/hung-development-allocation-20261027-v1.json"
LEDGER_V2_SHA256 = "1a2ad217184a38ae012de07c1bedf335712aa095c2b4e783495d42d2c94f1090"
RECOVERY_REGISTER_SHA256 = "9076d7eb550fd0701e60ab337a13efabd9f68e196de22a2785894d98705a51fc"
ALLOCATION_SHA256 = "8214c5aa5abb7958d4832d2948d4c868b1a35b7d0f2196f3f6eaa64ecda31906"
VERIFIER_SHA256 = "a7b6ebd0fbd69001e34b874fff0dba1c6d9ecc1e6dae682318a410074b537b90"
REMOTE_STATUS = "PROVISIONAL_REMOTE_COMPACT_PROOF"
EXTRA_FIELDS = (
    "stage_receipt_sha256",
    "proof_path",
    "proof_bytes",
    "proof_sha256",
    "proof_readback_path",
    "proof_readback_bytes",
    "proof_readback_sha256",
    "claimed_archive_carrier_version_id",
    "claimed_archive_readback_version_id",
    "claimed_proof_version_id",
    "claimed_proof_readback_version_id",
    "provider_version_binding",
)


class ProofImportError(ValueError):
    """A compact proof cannot be bound to the frozen Development ledger."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProofImportError(message)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_lf_sha256(raw: bytes, label: str) -> str:
    """Hash tracked text as stored in Git across LF and Windows CRLF checkouts."""
    without_crlf = raw.replace(b"\r\n", b"")
    require(b"\r" not in without_crlf, f"Bare carriage return in {label}")
    return sha256_bytes(raw.replace(b"\r\n", b"\n"))


def valid_sha(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def read_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProofImportError(f"Invalid JSON in {label}: {error}") from error
    require(isinstance(value, dict), f"Expected JSON object in {label}")
    return value


def cache_file(cache_root: pathlib.Path, relative: Any, label: str) -> pathlib.Path:
    require(isinstance(relative, str) and relative, f"Missing {label} path")
    path = (cache_root.parent / relative).resolve()
    require(path.is_relative_to(cache_root.resolve()), f"{label} must be under repository .cache")
    require(path.is_file(), f"Missing {label}: {relative}")
    return path


def pinned_bytes(path: pathlib.Path, size: Any, sha: Any, label: str) -> bytes:
    require(type(size) is int and size > 0, f"Invalid {label} byte count")
    require(valid_sha(sha), f"Invalid {label} SHA-256")
    raw = path.read_bytes()
    require(len(raw) == size and sha256_bytes(raw) == sha, f"{label} bytes/SHA mismatch")
    return raw


def ordered_jobset_sha(job_ids: list[str]) -> str:
    return sha256_bytes(json.dumps(job_ids, separators=(",", ":")).encode("utf-8"))


def readback_entry(readback: dict[str, Any], shard_id: str) -> dict[str, Any]:
    require(readback.get("scope") == "development_only", "Readback scope mismatch")
    require(
        readback.get("status") == "REMOTE_PROOF_READBACK_VERIFIED",
        "Readback is not terminal verified",
    )
    schema = readback.get("schema")
    if schema == "hung-kaggle-compact-proof-readback-v1":
        require(readback.get("jobs") == 20, "Single-shard readback job count mismatch")
        return readback
    require(schema == "hung-kaggle-compact-proof-group-readback-v1", "Unknown readback schema")
    items = readback.get("readbacks")
    require(isinstance(items, list) and items, "Group readback has no shards")
    ids = [item.get("shard_id") for item in items if isinstance(item, dict)]
    require(len(ids) == len(items) == len(set(ids)), "Duplicate/invalid readback shard")
    require(all(item.get("jobs") == 20 for item in items), "Group shard job count mismatch")
    require(readback.get("jobs") == 20 * len(items), "Group job count mismatch")
    matches = [item for item in items if item["shard_id"] == shard_id]
    require(len(matches) == 1, f"Readback omits {shard_id}")
    require(matches[0].get("status") == "REMOTE_PROOF_READBACK_VERIFIED", "Shard readback failed")
    return matches[0]


def validate_stage_hashes(row: dict[str, Any], job_id: str) -> tuple[str, str]:
    manifests = row.get("stage_manifest_sha256")
    receipts = row.get("stage_receipt_sha256")
    require(isinstance(manifests, dict) and manifests, f"Missing manifest hashes: {job_id}")
    require(
        isinstance(receipts, dict) and set(receipts) == set(manifests), f"Stage mismatch: {job_id}"
    )
    require(
        all(valid_sha(value) for value in manifests.values()), f"Invalid manifest SHA: {job_id}"
    )
    require(
        all(valid_sha(value) for value in receipts.values()), f"Invalid stage receipt SHA: {job_id}"
    )
    return (
        ";".join(f"{stage}:{manifests[stage]}" for stage in sorted(manifests)),
        ";".join(f"{stage}:{receipts[stage]}" for stage in sorted(receipts)),
    )


def validate_proof_rows(
    proof: dict[str, Any],
    shard_id: str,
    base_by_id: dict[str, dict[str, str]],
    expected_ids: list[str],
) -> dict[str, dict[str, str]]:
    proof_rows = proof.get("rows")
    require(isinstance(proof_rows, list) and len(proof_rows) == 20, f"Proof count: {shard_id}")
    ids = [row.get("job_id") for row in proof_rows if isinstance(row, dict)]
    require(ids == expected_ids, f"Proof jobset/order mismatch: {shard_id}")
    result: dict[str, dict[str, str]] = {}
    matched = {
        "shard_id": "shard_id",
        "method": "method",
        "cell_id": "cell_id",
        "budget_days": "budget_days",
        "seed": "seed",
        "entity_id": "entity_id",
        "input_manifest_sha256": "input_manifest_sha256",
        "config_sha256": "config_sha256",
    }
    for row in proof_rows:
        jid = row["job_id"]
        base = base_by_id[jid]
        require(base["provider_route"] == "kaggle", f"Non-Kaggle proof row: {jid}")
        require(base["status"] == "MISSING_REVIEWABLE_ARCHIVE", f"Already resolved row: {jid}")
        require(row.get("status") == "VERIFIED_ARCHIVE_BYTES", f"Unverified proof row: {jid}")
        for field, base_field in matched.items():
            require(str(row.get(field)) == base[base_field], f"{field} mismatch: {jid}")
        require(valid_sha(row.get("job_receipt_sha256")), f"Invalid job receipt SHA: {jid}")
        require(
            type(row.get("verified_member_count")) is int and row["verified_member_count"] > 0,
            f"No verified members: {jid}",
        )
        manifests, receipts = validate_stage_hashes(row, jid)
        result[jid] = {
            "job_receipt_sha256": row["job_receipt_sha256"],
            "stage_manifest_sha256": manifests,
            "stage_receipt_sha256": receipts,
        }
    return result


def validate_entry(
    entry: dict[str, Any],
    base_by_id: dict[str, dict[str, str]],
    expected_jobsets: dict[str, tuple[list[str], str]],
    allocation: dict[str, Any],
    cache_root: pathlib.Path,
) -> tuple[str, dict[str, dict[str, str]], dict[str, str]]:
    sid = entry.get("shard_id")
    require(isinstance(sid, str) and sid in expected_jobsets, f"Unknown proof shard: {sid}")
    expected_ids, expected_jobset_sha = expected_jobsets[sid]
    for field in (
        "archive_carrier_version_id",
        "archive_readback_version_id",
        "proof_version_id",
        "proof_readback_version_id",
    ):
        require(type(entry.get(field)) is int and entry[field] > 0, f"Invalid {field}: {sid}")
    require(valid_sha(entry.get("provider_plan_sha256")), f"Invalid provider plan SHA: {sid}")
    require(
        valid_sha(entry.get("provider_partition_sha256")), f"Invalid provider partition SHA: {sid}"
    )
    require(valid_sha(entry.get("archive_sha256")), f"Invalid archive SHA: {sid}")
    require(
        type(entry.get("archive_bytes")) is int and entry["archive_bytes"] > 0,
        f"Invalid archive bytes: {sid}",
    )
    proof_path = cache_file(cache_root, entry.get("proof_path"), "proof")
    readback_path = cache_file(cache_root, entry.get("proof_readback_path"), "readback")
    proof = read_json_bytes(
        pinned_bytes(proof_path, entry.get("proof_bytes"), entry.get("proof_sha256"), "Proof"),
        "proof",
    )
    readback = read_json_bytes(
        pinned_bytes(
            readback_path,
            entry.get("proof_readback_bytes"),
            entry.get("proof_readback_sha256"),
            "Readback",
        ),
        "readback",
    )
    require(proof.get("schema") == "hung-kaggle-compact-shard-proof-v1", f"Proof schema: {sid}")
    require(proof.get("scope") == "development_only", f"Proof scope: {sid}")
    require(proof.get("shard_id") == sid, f"Proof shard mismatch: {sid}")
    require(proof.get("verifier_sha256") == VERIFIER_SHA256, f"Verifier pin mismatch: {sid}")
    require(
        proof.get("parent_plan_sha256") == allocation["plan_sha256"]
        and proof.get("parent_partition_sha256") == allocation["partition_sha256"]
        and proof.get("model_code_commit") == allocation["canonical_code_sha"],
        f"Frozen parent/model binding mismatch: {sid}",
    )
    for proof_field, manifest_field in (
        ("provider_plan_sha256", "provider_plan_sha256"),
        ("provider_partition_sha256", "provider_partition_sha256"),
        ("archive_sha256", "archive_sha256"),
        ("archive_bytes", "archive_bytes"),
        ("claimed_saved_version_id", "archive_carrier_version_id"),
        ("claimed_readback_version_id", "archive_readback_version_id"),
    ):
        require(proof.get(proof_field) == entry[manifest_field], f"{proof_field} mismatch: {sid}")
    require(
        proof.get("version_ids_independently_authenticated") is False,
        f"Unexpected version-authentication claim: {sid}",
    )
    source_notebook = entry.get("proof_source_notebook")
    require(isinstance(source_notebook, str) and source_notebook, f"Missing proof source: {sid}")
    require(readback.get("source_notebook") == source_notebook, f"Source notebook mismatch: {sid}")
    require(
        readback.get("claimed_source_version_id") == entry["proof_version_id"],
        f"Proof saved version mismatch: {sid}",
    )
    readback_row = readback_entry(readback, sid)
    for key, expected in (
        ("proof_bytes", entry["proof_bytes"]),
        ("proof_sha256", entry["proof_sha256"]),
        ("jobset_sha256", expected_jobset_sha),
        ("jobs", 20),
    ):
        require(readback_row.get(key) == expected, f"Readback {key} mismatch: {sid}")
    require(readback_row.get("job_ids") == expected_ids, f"Readback jobset/order mismatch: {sid}")
    rows = validate_proof_rows(proof, sid, base_by_id, expected_ids)
    require(ordered_jobset_sha(list(rows)) == expected_jobset_sha, f"Proof jobset SHA: {sid}")
    provenance = {
        "archive_bytes": str(entry["archive_bytes"]),
        "archive_sha256": entry["archive_sha256"],
        "proof_path": entry["proof_path"],
        "proof_bytes": str(entry["proof_bytes"]),
        "proof_sha256": entry["proof_sha256"],
        "proof_readback_path": entry["proof_readback_path"],
        "proof_readback_bytes": str(entry["proof_readback_bytes"]),
        "proof_readback_sha256": entry["proof_readback_sha256"],
        "claimed_archive_carrier_version_id": str(entry["archive_carrier_version_id"]),
        "claimed_archive_readback_version_id": str(entry["archive_readback_version_id"]),
        "claimed_proof_version_id": str(entry["proof_version_id"]),
        "claimed_proof_readback_version_id": str(entry["proof_readback_version_id"]),
        "provider_version_binding": "CLAIMED; compare against saved provider source list",
    }
    return sid, rows, provenance


def merge_rows(
    base_rows: list[dict[str, str]],
    entries: list[dict[str, Any]],
    expected_jobsets: dict[str, tuple[list[str], str]],
    allocation: dict[str, Any],
    cache_root: pathlib.Path,
) -> list[dict[str, str]]:
    require(entries, "No compact proof entries supplied")
    require(len({row["job_id"] for row in base_rows}) == len(base_rows), "Duplicate base job")
    base_by_id = {row["job_id"]: row for row in base_rows}
    result = [{**row, **{field: "" for field in EXTRA_FIELDS}} for row in base_rows]
    result_by_id = {row["job_id"]: row for row in result}
    seen_shards: set[str] = set()
    seen_jobs: set[str] = set()
    readback_groups: dict[pathlib.Path, set[str]] = {}
    submitted_readbacks: dict[pathlib.Path, set[str]] = {}
    for entry in entries:
        require(isinstance(entry, dict), "Invalid manifest entry")
        sid, proof_rows, provenance = validate_entry(
            entry, base_by_id, expected_jobsets, allocation, cache_root
        )
        require(sid not in seen_shards, f"Duplicate proof shard: {sid}")
        require(not seen_jobs.intersection(proof_rows), f"Duplicate proof job: {sid}")
        seen_shards.add(sid)
        seen_jobs.update(proof_rows)
        readback_path = cache_file(cache_root, entry["proof_readback_path"], "readback")
        submitted_readbacks.setdefault(readback_path, set()).add(sid)
        readback = read_json_bytes(readback_path.read_bytes(), "readback")
        if readback.get("schema") == "hung-kaggle-compact-proof-group-readback-v1":
            group_ids = {row["shard_id"] for row in readback["readbacks"]}
            previous = readback_groups.setdefault(readback_path, group_ids)
            require(previous == group_ids, "Inconsistent group readback")
        for jid, proof_row in proof_rows.items():
            result_by_id[jid].update(proof_row)
            result_by_id[jid].update(provenance)
            result_by_id[jid]["job_receipt_path"] = f"receipts/{jid}/job.json"
            result_by_id[jid]["status"] = REMOTE_STATUS
            result_by_id[jid]["reason"] = (
                "Saved verifier v1 proof and separate proof-byte readback imported; reviewer P1 "
                "empty-stage false-accept risk requires verifier v2 recheck before acceptance; "
                "provider source/version IDs remain claims"
            )
    for path, group_ids in readback_groups.items():
        require(
            submitted_readbacks[path] == group_ids,
            f"Incomplete group readback: {path.name}",
        )
    return result


def read_base_and_jobsets() -> tuple[
    list[dict[str, str]], dict[str, tuple[list[str], str]], dict[str, Any]
]:
    require(
        git_lf_sha256(LEDGER_V2.read_bytes(), "v2 ledger") == LEDGER_V2_SHA256,
        "Frozen v2 ledger SHA mismatch",
    )
    require(
        git_lf_sha256(RECOVERY_REGISTER.read_bytes(), "recovery register")
        == RECOVERY_REGISTER_SHA256,
        "Frozen recovery register SHA mismatch",
    )
    require(
        git_lf_sha256(ALLOCATION.read_bytes(), "allocation") == ALLOCATION_SHA256,
        "Frozen allocation SHA mismatch",
    )
    with LEDGER_V2.open(encoding="utf-8", newline="") as stream:
        base_rows = list(csv.DictReader(stream))
    require(len(base_rows) == 782, "Frozen ledger row count mismatch")
    require(
        sum(row["status"] == "VERIFIED_LOCAL_BYTES" for row in base_rows) == 222,
        "Local ledger count mismatch",
    )
    require(
        sum(row["status"] == "MISSING_REVIEWABLE_ARCHIVE" for row in base_rows) == 560,
        "Pending ledger count mismatch",
    )
    with RECOVERY_REGISTER.open(encoding="utf-8", newline="") as stream:
        register = list(csv.DictReader(stream))
    require(len(register) == 28, "Kaggle recovery register shard count mismatch")
    expected_jobsets: dict[str, tuple[list[str], str]] = {}
    for item in register:
        sid = item["shard_id"]
        require(sid not in expected_jobsets, f"Duplicate recovery shard: {sid}")
        ids = [row["job_id"] for row in base_rows if row["shard_id"] == sid]
        require(len(ids) == int(item["planned_jobs"]) == 20, f"Recovery count mismatch: {sid}")
        require(
            ordered_jobset_sha(ids) == item["planned_jobset_sha256"],
            f"Recovery jobset SHA mismatch: {sid}",
        )
        expected_jobsets[sid] = (ids, item["planned_jobset_sha256"])
    require(
        sum(len(ids) for ids, _ in expected_jobsets.values()) == 560, "Kaggle jobset count mismatch"
    )
    require(
        {row["job_id"] for row in base_rows if row["provider_route"] == "kaggle"}
        == {job for ids, _ in expected_jobsets.values() for job in ids},
        "Kaggle recovery register does not cover exact jobset",
    )
    allocation = read_json_bytes(ALLOCATION.read_bytes(), "allocation")
    return base_rows, expected_jobsets, allocation


def output_path(argument: pathlib.Path) -> pathlib.Path:
    path = argument.resolve()
    require(path.parent == REPORTS.resolve(), "Ledger output must be directly under docs/reports")
    match = re.fullmatch(r"hung-development-782-job-ledger-\d{8}-v(\d+)\.csv", path.name)
    require(match is not None and int(match.group(1)) >= 3, "Use a new v3+ ledger filename")
    require(not path.exists(), "Ledger output already exists; preserve the old snapshot")
    return path


def write_ledger(path: pathlib.Path, rows: list[dict[str, str]]) -> str:
    fieldnames = list(rows[0])
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    raw = stream.getvalue().encode("utf-8")
    with path.open("xb") as destination:
        destination.write(raw)
    return sha256_bytes(raw)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    arguments = parser.parse_args()
    try:
        manifest_path = cache_file(CACHE, str(arguments.manifest), "manifest")
        manifest = read_json_bytes(manifest_path.read_bytes(), "manifest")
        require(
            manifest.get("schema") == "hung-compact-ledger-import-v1", "Unknown manifest schema"
        )
        entries = manifest.get("entries")
        require(isinstance(entries, list), "Manifest entries must be an array")
        base_rows, expected_jobsets, allocation = read_base_and_jobsets()
        rows = merge_rows(base_rows, entries, expected_jobsets, allocation, CACHE)
        destination = output_path(arguments.out)
        digest = write_ledger(destination, rows)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.exit(1, f"Compact proof ledger import failed: {error}\n")
    print(
        json.dumps(
            {
                "ledger": str(destination),
                "ledger_sha256": digest,
                "rows": len(rows),
                "verified_local_bytes": sum(
                    row["status"] == "VERIFIED_LOCAL_BYTES" for row in rows
                ),
                "provisional_remote_compact_proof": sum(
                    row["status"] == REMOTE_STATUS for row in rows
                ),
                "pending": sum(row["status"] == "MISSING_REVIEWABLE_ARCHIVE" for row in rows),
                "provider_versions_independently_authenticated_by_importer": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
