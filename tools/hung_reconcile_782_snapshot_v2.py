import argparse
import csv
import hashlib
import io
import json
import pathlib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORTS = ROOT / "docs/reports"
parser = argparse.ArgumentParser(description="Reconcile pinned Hung Development archives")
parser.add_argument("--recovery-manifest", type=pathlib.Path)
parser.add_argument("--out", type=pathlib.Path)
args = parser.parse_args()
if args.recovery_manifest is not None and args.out is None:
    parser.error("--out is required with --recovery-manifest to preserve the v2 ledger")
ALLOCATION = json.loads(
    (REPORTS / "evidence/hung-development-allocation-20261027-v1.json").read_text(encoding="utf8")
)
PLAN_PATH = ROOT / ".cache/kaggle-payload-v2/payload/parent-plan.json"
SHARDS_PATH = ROOT / ".cache/kaggle-payload-v2/payload/parent-shards.json"
PLAN = json.loads(PLAN_PATH.read_text(encoding="utf8"))
SHARDS = json.loads(SHARDS_PATH.read_text(encoding="utf8"))


def sha_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha_zip_member(archive, name):
    digest = hashlib.sha256()
    size = 0
    with archive.open(name) as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(block)
            digest.update(block)
    return size, digest.hexdigest()


assert sha_file(PLAN_PATH) == ALLOCATION["plan_sha256"]
assert sha_file(SHARDS_PATH) == ALLOCATION["partition_sha256"]
assert PLAN["code_commit"] == ALLOCATION["canonical_code_sha"]
assert SHARDS["plan_sha256"] == ALLOCATION["plan_sha256"]
jobs = {job["id"]: job for job in PLAN["jobs"]}
cells = {cell["id"]: cell for cell in PLAN["cells"]}
configs = {config["id"]: config for config in PLAN["configs"]}
assert len(jobs) == len(PLAN["jobs"]) == 782
assert len(SHARDS["shards"]) == 40
assigned = [jid for shard in SHARDS["shards"] for jid in shard["job_ids"]]
assert len(assigned) == len(set(assigned)) == 782
assert set(assigned) == set(jobs)

rows = {}
for shard in SHARDS["shards"]:
    sid = shard["id"]
    provider = ALLOCATION["routes"][sid]
    for jid in shard["job_ids"]:
        job = jobs[jid]
        cell = cells[job["cell"]]
        config = configs[job["config"]]
        rows[jid] = {
            "job_id": jid,
            "shard_id": sid,
            "provider_route": provider,
            "method": job["method"],
            "config_id": job["config"],
            "config_sha256": config["sha256"],
            "cell_id": cell["id"],
            "budget_days": cell["budget"],
            "seed": cell["seed"],
            "entity_id": cell["entity_id"],
            "input_manifest_sha256": cell["input_manifest_sha256"],
            "source_checkpoint_sha256": (job.get("source") or {}).get("sha256", ""),
            "target_checkpoint_sha256": (job.get("target") or {}).get("sha256", ""),
            "archive_path": "",
            "archive_bytes": "",
            "archive_sha256": "",
            "job_receipt_path": "",
            "job_receipt_sha256": "",
            "stage_manifest_sha256": "",
            "status": "MISSING_REVIEWABLE_ARCHIVE",
            "reason": "Pinned allocation only; archive and per-job receipt bytes unavailable in this repository",
        }

pilot = REPORTS / "evidence/hung-development-local-pilot-20261027.json"
pilot_data = json.loads(pilot.read_text(encoding="utf8"))
local_dir = ROOT / ".cache/local-development-worker-v1"
archive_specs = [
    (
        "pilot_0000",
        ROOT / ".cache/readback-upload-v1/pilot-artifacts.zip.bin",
        pilot_data["artifact_archive"]["sha256"],
        pilot_data["artifact_archive"]["bytes"],
    )
]
for sid in [
    "shard_0004",
    "shard_0005",
    "shard_0006",
    "shard_0007",
    "shard_0029",
    "shard_0030",
    "shard_0031",
    "shard_0032",
    "shard_0037",
    "shard_0038",
]:
    base = local_dir / sid
    receipt = json.loads((base / "receipt.json").read_text(encoding="utf8"))
    assert receipt["shard_id"] == sid
    assert receipt["plan_sha256"] == ALLOCATION["plan_sha256"]
    assert receipt["partition_sha256"] == ALLOCATION["partition_sha256"]
    assert receipt["job_ids"] == next(s["job_ids"] for s in SHARDS["shards"] if s["id"] == sid)
    archive_specs.append(
        (sid, base / "artifacts.zip", receipt["artifact_sha256"], receipt["artifact_bytes"])
    )

sid = "shard_0039"
recovered = ROOT / ".cache/recovered-shards-v2" / sid
recorded = json.loads(
    (REPORTS / "evidence/hung-local-shard0039-20261027.json").read_text(encoding="utf8")
)["archive"]
copied = json.loads((recovered / "archive.json").read_text(encoding="utf8"))
assert copied == recorded
assert recorded["job_ids"] == next(s["job_ids"] for s in SHARDS["shards"] if s["id"] == sid)
archive_specs.append((sid, recovered / "artifacts.zip", recorded["sha256"], recorded["bytes"]))

provider_versions = {}
if args.recovery_manifest is not None:
    manifest_path = args.recovery_manifest.resolve()
    if not manifest_path.is_relative_to(ROOT / ".cache"):
        raise SystemExit("Recovery manifest must be inside ignored repository .cache")
    recovery = json.loads(manifest_path.read_text(encoding="utf8"))
    if recovery.get("schema") != "hung-kaggle-archive-recovery-v1":
        raise SystemExit("Unexpected recovery manifest schema")
    if not recovery.get("archives"):
        raise SystemExit("Recovery manifest must contain at least one archive")
    seen_shards = {spec[0] for spec in archive_specs}
    for item in recovery["archives"]:
        sid = item["shard_id"]
        if sid in seen_shards or ALLOCATION["routes"].get(sid) != "kaggle":
            raise SystemExit(f"Duplicate or non-Kaggle recovered shard: {sid}")
        expected_jobs = next(s["job_ids"] for s in SHARDS["shards"] if s["id"] == sid)
        jobset_sha = hashlib.sha256(
            json.dumps(expected_jobs, separators=(",", ":")).encode("utf8")
        ).hexdigest()
        if item["planned_jobset_sha256"] != jobset_sha:
            raise SystemExit(f"Recovered shard jobset SHA mismatch: {sid}")
        if int(item["saved_version_id"]) <= 0 or int(item["readback_version_id"]) <= 0:
            raise SystemExit(f"Missing saved/readback version identity: {sid}")
        path = (ROOT / item["archive_path"]).resolve()
        if not path.is_relative_to(ROOT / ".cache") or not path.is_file():
            raise SystemExit(f"Missing ignored repository archive: {sid}")
        archive_specs.append((sid, path, item["archive_sha256"], int(item["archive_bytes"])))
        provider_versions[sid] = (
            int(item["saved_version_id"]),
            int(item["readback_version_id"]),
        )
        seen_shards.add(sid)

errors = []
verified_shards = []
for sid, path, expected_sha, expected_bytes in archive_specs:
    expected_jobs = next(s["job_ids"] for s in SHARDS["shards"] if s["id"] == sid)
    if path.stat().st_size != expected_bytes or sha_file(path) != expected_sha:
        errors.append(f"{sid}: archive bytes/SHA mismatch")
        continue
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            errors.append(f"{sid}: duplicate ZIP member")
            continue
        if archive.testzip() is not None:
            errors.append(f"{sid}: ZIP CRC failed")
            continue
        receipt_jobs = {
            name.split("/")[1]
            for name in names
            if name.startswith("receipts/") and name.endswith("/job.json")
        }
        if receipt_jobs != set(expected_jobs):
            errors.append(f"{sid}: receipt jobset mismatch")
            continue
        shard_good = True
        for jid in expected_jobs:
            job = jobs[jid]
            cell = cells[job["cell"]]
            jr_path = f"receipts/{jid}/job.json"
            jr_raw = archive.read(jr_path)
            jr = json.loads(jr_raw)
            if (
                jr["job_id"] != jid
                or jr["plan_sha256"] != ALLOCATION["plan_sha256"]
                or jr["shards_sha256"] != ALLOCATION["partition_sha256"]
            ):
                errors.append(f"{sid}/{jid}: job receipt binding mismatch")
                shard_good = False
                continue
            manifests = []
            job_good = True
            for stage, stage_sha in jr["stages"].items():
                sr_path = f"receipts/{jid}/{stage}.json"
                sr_raw = archive.read(sr_path)
                if hashlib.sha256(sr_raw).hexdigest() != stage_sha:
                    errors.append(f"{sid}/{jid}/{stage}: stage receipt SHA mismatch")
                    job_good = False
                    break
                sr = json.loads(sr_raw)
                binding = sr["binding"]
                if (
                    binding["job"] != job
                    or binding["input_manifest_sha256"] != cell["input_manifest_sha256"]
                    or binding["config_sha256"] != configs[job["config"]]["sha256"]
                    or binding["stage"] != stage
                ):
                    errors.append(f"{sid}/{jid}/{stage}: plan/config/input binding mismatch")
                    job_good = False
                    break
                for name, expected in sr["files"].items():
                    member = f"jobs/{jid}/{stage}/{name}"
                    size, digest = sha_zip_member(archive, member)
                    if size != expected["bytes"] or digest != expected["sha256"]:
                        errors.append(f"{sid}/{jid}/{stage}/{name}: member bytes/SHA mismatch")
                        job_good = False
                        break
                if not job_good:
                    break
                log_size, log_sha = sha_zip_member(archive, f"logs/{jid}/{stage}.log")
                if log_size != sr["log"]["bytes"] or log_sha != sr["log"]["sha256"]:
                    errors.append(f"{sid}/{jid}/{stage}: log bytes/SHA mismatch")
                    job_good = False
                    break
                manifest = json.loads(archive.read(f"jobs/{jid}/{stage}/run_manifest.json"))
                input_binding = manifest.get("input_binding", manifest.get("binding", {}))
                if (
                    manifest["status"] != "completed"
                    or manifest["code"]["commit"] != ALLOCATION["canonical_code_sha"]
                    or input_binding["entity_id"] != str(cell["entity_id"])
                    or input_binding["history_days"] != cell["budget"]
                    or input_binding["input_manifest_sha256"] != cell["input_manifest_sha256"]
                ):
                    errors.append(f"{sid}/{jid}/{stage}: run manifest identity/status mismatch")
                    job_good = False
                    break
                manifests.append(f"{stage}:{sr['files']['run_manifest.json']['sha256']}")
            if job_good:
                row = rows[jid]
                row.update(
                    {
                        "archive_path": str(path.relative_to(ROOT)).replace("\\", "/"),
                        "archive_bytes": expected_bytes,
                        "archive_sha256": expected_sha,
                        "job_receipt_path": jr_path,
                        "job_receipt_sha256": hashlib.sha256(jr_raw).hexdigest(),
                        "stage_manifest_sha256": ";".join(manifests),
                        "status": "VERIFIED_LOCAL_BYTES",
                        "reason": "Archive SHA/CRC and all listed member bytes/SHA, receipt and manifest bindings rechecked locally",
                    }
                )
            else:
                shard_good = False
                rows[jid]["status"] = "INVALID"
                rows[jid]["reason"] = "; ".join(errors[-2:])
        if shard_good:
            verified_shards.append(sid)

if errors:
    print("ERRORS", len(errors), errors[:30])
    raise SystemExit(1)

out = args.out or REPORTS / "hung-development-782-job-ledger-20261028-v2.csv"
out = out.resolve()
if (
    not out.is_relative_to(REPORTS)
    or not out.name.startswith("hung-development-782-job-ledger-")
    or out.suffix != ".csv"
    or (
        args.recovery_manifest is not None
        and out.name == "hung-development-782-job-ledger-20261028-v2.csv"
    )
):
    raise SystemExit("Recovery output must be a new versioned file under docs/reports")
if args.recovery_manifest is not None:
    for row in rows.values():
        saved, readback = provider_versions.get(row["shard_id"], ("", ""))
        row["claimed_saved_provider_version_id"] = saved
        row["claimed_readback_provider_version_id"] = readback
stream = io.StringIO(newline="")
writer = csv.DictWriter(stream, fieldnames=list(next(iter(rows.values()))))
writer.writeheader()
writer.writerows(rows[jid] for jid in assigned)
output_bytes = stream.getvalue().encode("utf8")
if out.exists():
    if out.read_bytes() != output_bytes:
        raise SystemExit("Existing ledger differs; preserve it and investigate")
else:
    out.write_bytes(output_bytes)
print(
    json.dumps(
        {
            "rows": len(rows),
            "verified_local_bytes": sum(
                row["status"] == "VERIFIED_LOCAL_BYTES" for row in rows.values()
            ),
            "missing_reviewable_archive": sum(
                row["status"] == "MISSING_REVIEWABLE_ARCHIVE" for row in rows.values()
            ),
            "duplicate": len(assigned) - len(set(assigned)),
            "invalid": len(errors),
            "verified_shards": verified_shards,
            "ledger": str(out),
        },
        indent=2,
    )
)
