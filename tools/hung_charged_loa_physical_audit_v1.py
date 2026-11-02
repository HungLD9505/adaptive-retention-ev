"""Compare one colliding CHARGED LOA run ID with its physical PR #52 archive."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "charged-LOA-201-7d-adaptive-seed42"
PR67_COMMIT = "c1c62fcb49bdedab42aeb913e8dc3c6821104a57"
PR67_PROOF_PATH = "docs/reports/issue23-charged-loa-development-verification-v2.json"
PR67_PROOF_SHA = "cb454462ccd10710d83086e119629674d4d9f730782659749219637032961ee5"
PR52_COMMIT = "377723f5d55a91cde6229807300429365c764117"
PR52_PLAN_PATH = "docs/reports/issue23-primary-recovery-plan-evidence.json"
PR52_PLAN_SHA = "c52031d0f33f19db14667b0059959eea772913ceca26b48fab454d6ddef66815"
PROOF_ZIP_SHA = "3f2ba5eb36af82751304586395c3b8bd47b2dd9eb04bacf9931c8bb47e0a93f9"
ARCHIVE_SHA = "cc24309d24cd473838b0ce3073d8aec328b6a104f563a6c0771bf5f2887073b5"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pinned_blob(commit: str, path: str, digest: str) -> dict:
    raw = subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)
    if sha256(raw) != digest:
        raise ValueError(f"Git blob SHA mismatch: {path}")
    return json.loads(raw)


def checked_zip(data: bytes) -> zipfile.ZipFile:
    archive = zipfile.ZipFile(io.BytesIO(data))
    if archive.testzip() is not None:
        raise ValueError("ZIP member CRC mismatch")
    return archive


def compare_records(pr67: dict, pr52: dict, proof: dict, archive: dict) -> dict:
    """Require source bindings and retain both noninterchangeable trajectories."""
    row67 = next((row for row in pr67["runs"] if row["run_id"] == RUN_ID), None)
    if row67 is None:
        raise ValueError("PR #67 run ID absent")
    publication = pr52["loa_first_target_publication"]
    receipt = proof["receipt"]
    verification = proof["verification"]
    daily = proof["daily"]
    row52 = daily["runs"][0]
    run = archive["run"]
    binding = archive["binding"]
    catalog = archive["catalog"]
    input_sha = binding["input"]["input_manifest_sha256"]
    if not (
        publication["run_id"] == receipt["run_ids"][0] == row52["run_id"] == run["run_id"] == RUN_ID
    ):
        raise ValueError("PR #52 run ID mismatch")
    if not (
        receipt["artifact"]["sha256"] == ARCHIVE_SHA
        and receipt["artifact"]["bytes"] == archive["bytes"]
        and publication["independent_proof_sha256"] == PROOF_ZIP_SHA
        and publication["publication_receipt_sha256"] == proof["receipt_sha256"]
        and receipt["verification_sha256"] == proof["verification_sha256"]
        and verification["wrapper_sha256"] == ARCHIVE_SHA
        and receipt["target_code"] == run["code"]["commit"]
        and catalog["matrix_sha256"] == daily["matrix_sha256"]
        and publication["active_mae_kwh"] == run["active_mae_kwh"]
        and publication["active_rmse_kwh"] == run["active_rmse_kwh"]
        and row52["mae_kwh"] == run["active_mae_kwh"]
        and abs(row52["rmse_kwh"] - run["active_rmse_kwh"]) < 1e-12
        and row52["commit_chain"] == run["commit_chain"]
        and verification["status"] == "actual_Drive_roundtrip_complete_content_verified"
    ):
        raise ValueError("PR #52 physical publication mismatch")
    source67 = pr67["input_authentication"]["sources"][0]
    source52 = daily["input_authentication"]["sources"][0]
    if not (
        source67["manifest_sha256"]
        == source52["manifest_sha256"]
        == input_sha
        == "cb09d9d5c751b3bc1fcbad79ef548800c33e1506e6863f2600f88b167ac5e384"
    ):
        raise ValueError("Input manifest identity mismatch")
    for name in ("manifest.json", "entities.jsonl", "labels.jsonl"):
        if source67["files"][name] != source52["files"][name]:
            raise ValueError(f"Input file identity mismatch: {name}")
    if (row67["issued"], row67["scored"]) != (row52["issued"], row52["scored"]):
        raise ValueError("Issued/scored coverage mismatch")
    if row67["commit_chain"] == row52["commit_chain"]:
        raise ValueError("Expected distinct recorded trajectories")
    return {
        "schema": "hung-charged-loa-physical-audit-v1",
        "classification": "SAME_ID_AND_INPUT_DIFFERENT_RECORDED_TRAJECTORY",
        "run_id": RUN_ID,
        "input_manifest_sha256": input_sha,
        "pr67": {
            "commit": PR67_COMMIT,
            "proof_sha256": PR67_PROOF_SHA,
            "matrix_sha256": pr67["matrix_sha256"],
            "mae_kwh": row67["mae_kwh"],
            "rmse_kwh": row67["rmse_kwh"],
            "commit_chain": row67["commit_chain"],
            "issued": row67["issued"],
            "scored": row67["scored"],
            "physical_archive_bound": False,
        },
        "pr52": {
            "commit": PR52_COMMIT,
            "plan_sha256": PR52_PLAN_SHA,
            "independent_proof_zip_sha256": PROOF_ZIP_SHA,
            "physical_archive_sha256": ARCHIVE_SHA,
            "physical_archive_bytes": archive["bytes"],
            "code_commit": run["code"]["commit"],
            "source_checkpoint_sha256": binding["input"]["source_checkpoint_sha256"],
            "matrix_sha256": daily["matrix_sha256"],
            "mae_kwh": row52["mae_kwh"],
            "rmse_kwh": row52["rmse_kwh"],
            "commit_chain": row52["commit_chain"],
            "issued": row52["issued"],
            "scored": row52["scored"],
            "physical_archive_bound": True,
        },
        "mae_difference_pr52_minus_pr67_kwh": row52["mae_kwh"] - row67["mae_kwh"],
        "rmse_difference_pr52_minus_pr67_kwh": row52["rmse_kwh"] - row67["rmse_kwh"],
        "interpretation_limit": (
            "The matching run ID and input do not make the metrics interchangeable; "
            "the PR67 physical archive/code/Source state remain unbound."
        ),
    }


def audit(proof_zip_path: Path, archive_path: Path, output_path: Path) -> dict:
    """Read pinned bytes and emit one create-only, bounded comparison."""
    for path in (proof_zip_path, archive_path, output_path):
        if not path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError("Paths must stay inside repository")
    if output_path.exists():
        raise ValueError("Output already exists")
    proof_bytes = proof_zip_path.read_bytes()
    archive_bytes = archive_path.read_bytes()
    if sha256(proof_bytes) != PROOF_ZIP_SHA or sha256(archive_bytes) != ARCHIVE_SHA:
        raise ValueError("Downloaded evidence SHA mismatch")
    proof_zip = checked_zip(proof_bytes)
    outer = checked_zip(archive_bytes)
    inner = checked_zip(outer.read("package/runs-0000.zip"))
    prefix = f"study/{RUN_ID}/"
    proof = {
        name: json.loads(proof_zip.read(member))
        for name, member in (
            ("receipt", "publication-receipt.json"),
            ("verification", "publication-verification.json"),
            ("daily", "daily.json"),
        )
    }
    proof["receipt_sha256"] = sha256(proof_zip.read("publication-receipt.json"))
    proof["verification_sha256"] = sha256(proof_zip.read("publication-verification.json"))
    physical = {
        "bytes": len(archive_bytes),
        "catalog": json.loads(outer.read("package/catalog.json")),
        "binding": json.loads(inner.read(prefix + "binding.json")),
        "run": json.loads(inner.read(prefix + "run.json")),
    }
    result = compare_records(
        pinned_blob(PR67_COMMIT, PR67_PROOF_PATH, PR67_PROOF_SHA),
        pinned_blob(PR52_COMMIT, PR52_PLAN_PATH, PR52_PLAN_SHA),
        proof,
        physical,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof-zip", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.proof_zip, args.archive, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
