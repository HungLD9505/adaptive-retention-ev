"""Create-only local Final archive with independent byte, SHA and CRC readback."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import zlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from experiments.hung_sprint2.dispatch_matched import require

SCHEMA = "hung-final-local-archive-v1"


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def _digest(path: Path) -> dict:
    size = 0
    sha = hashlib.sha256()
    crc = 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            size += len(block)
            sha.update(block)
            crc = zlib.crc32(block, crc)
    return {"bytes": size, "sha256": sha.hexdigest(), "crc32": f"{crc:08x}"}


def _expected_stages(jobs: list[dict], plan: list[dict]) -> dict[str, set[str]]:
    require(len(jobs) == len(plan) and bool(jobs), "Final archive jobset/plan size differs")
    expected = {}
    for job, planned in zip(jobs, plan, strict=True):
        job_id = job["job_id"]
        require(
            isinstance(job_id, str)
            and job_id
            and job_id not in expected
            and planned["job_id"] == job_id,
            "Final archive job identity differs",
        )
        stages = {"replay", "target_init"} if planned["target_init"] is not None else {"replay"}
        if job.get("method") == "drift":
            stages.add("drift_reference")
        expected[job_id] = stages
    return expected


def _inventory(root: Path, expected: dict[str, set[str]], lock_sha: str) -> dict:
    require(root.is_dir() and not root.is_symlink(), "Final output root is absent/unsafe")
    require(
        {item.name for item in root.iterdir()}
        <= {"final_lock_identity.json", ".dispatch.lock", "stages", "logs", "receipts"}
        and {"final_lock_identity.json", "stages", "logs", "receipts"}
        <= {item.name for item in root.iterdir()},
        "Final output root has missing/extra members",
    )
    identity = root / "final_lock_identity.json"
    require(
        identity.is_file() and not identity.is_symlink(), "Final lock identity is absent/unsafe"
    )
    require(not (root / ".dispatch.lock").is_symlink(), "Unsafe Final dispatch lock")
    require(
        json.loads(identity.read_text(encoding="utf-8"))
        == {"schema": "hung-final-output-identity-v1", "lock_sha256": lock_sha},
        "Final output lock identity differs",
    )
    paths = {"final_lock_identity.json": _digest(identity)}
    mapping = {}
    for category in ("stages", "logs", "receipts"):
        folder = root / category
        require(folder.is_dir() and not folder.is_symlink(), f"Missing/unsafe {category}")
        require(
            {item.name for item in folder.iterdir()} == set(expected), f"{category} jobset differs"
        )
        for job_id, stages in expected.items():
            job_folder = folder / job_id
            require(job_folder.is_dir() and not job_folder.is_symlink(), "Unsafe Final job folder")
            names = stages if category == "stages" else {f"{stage}.json" for stage in stages}
            require({item.name for item in job_folder.iterdir()} == names, "Final stages differ")
            for stage in stages:
                path = job_folder / (stage if category == "stages" else f"{stage}.json")
                if category == "stages":
                    require(path.is_dir() and not path.is_symlink(), "Unsafe Final stage folder")
                    files = sorted(path.rglob("*"))
                    require(
                        files and all(not item.is_symlink() for item in files),
                        "Unsafe/empty Final stage",
                    )
                    for item in files:
                        if item.is_dir():
                            continue
                        require(item.is_file(), "Unsafe Final stage member")
                        relative = item.relative_to(root).as_posix()
                        paths[relative] = _digest(item)
                    mapping.setdefault(job_id, {})[stage] = {
                        "manifest": (path / "run_manifest.json").relative_to(root).as_posix(),
                        "artifacts": [
                            item.relative_to(root).as_posix() for item in files if item.is_file()
                        ],
                    }
                else:
                    require(path.is_file() and not path.is_symlink(), "Unsafe Final log/receipt")
                    paths[path.relative_to(root).as_posix()] = _digest(path)
    return {"schema": SCHEMA, "lock_sha256": lock_sha, "jobs": mapping, "files": paths}


def _read_json_member(archive: ZipFile, name: str) -> dict:
    return json.loads(archive.read(name))


def readback_archive(
    archive_path: Path, archive_sha256: str, lock_sha: str, jobs: list[dict], plan: list[dict]
) -> dict:
    """Verify archive without accessing the original Final output directory."""
    expected = _expected_stages(jobs, plan)
    require(
        archive_path.is_file() and not archive_path.is_symlink(), "Final archive is absent/unsafe"
    )
    archive_identity = _digest(archive_path)
    require(archive_identity["sha256"] == archive_sha256, "Final archive SHA differs")
    with ZipFile(archive_path) as archive:
        names = archive.namelist()
        require(
            len(names) == len(set(names)) and "index.json" in names,
            "Duplicate/missing archive member",
        )
        require(
            all(not name.startswith("/") and ".." not in Path(name).parts for name in names),
            "Unsafe archive member",
        )
        index = _read_json_member(archive, "index.json")
        require(
            set(index) == {"schema", "lock_sha256", "jobs", "files"}
            and index["schema"] == SCHEMA
            and index["lock_sha256"] == lock_sha,
            "Final archive index/lock differs",
        )
        files = index["files"]
        require(set(names) == set(files) | {"index.json"}, "Final archive member set differs")
        require(set(index["jobs"]) == set(expected), "Final archive exact jobset differs")
        require(
            _read_json_member(archive, "final_lock_identity.json")
            == {"schema": "hung-final-output-identity-v1", "lock_sha256": lock_sha},
            "Final archive lock identity differs",
        )
        for name, identity in files.items():
            require(
                set(identity) == {"bytes", "sha256", "crc32"}, "Archive file identity fields differ"
            )
            member = archive.getinfo(name)
            require(
                not member.is_dir() and member.external_attr >> 16 & 0o170000 != 0o120000,
                "Unsafe archive file",
            )
            sha, crc, size = hashlib.sha256(), 0, 0
            with archive.open(name) as stream:
                while block := stream.read(1024 * 1024):
                    sha.update(block)
                    crc = zlib.crc32(block, crc)
                    size += len(block)
            require(
                identity == {"bytes": size, "sha256": sha.hexdigest(), "crc32": f"{crc:08x}"}
                and member.file_size == size
                and member.CRC == crc,
                f"Archive byte/SHA/CRC mismatch: {name}",
            )
        for job_id, stages in expected.items():
            mapping = index["jobs"][job_id]
            require(set(mapping) == stages, "Final archive stage mapping differs")
            for stage in stages:
                record = mapping[stage]
                prefix = f"stages/{job_id}/{stage}/"
                actual = sorted(name for name in files if name.startswith(prefix))
                require(
                    set(record) == {"manifest", "artifacts"}
                    and record["manifest"] == prefix + "run_manifest.json"
                    and record["artifacts"] == actual,
                    "Final archive job→artifact mapping differs",
                )
                manifest = _read_json_member(archive, record["manifest"])
                require(
                    manifest.get("status") == "completed"
                    and manifest.get("final_lock_sha256") == lock_sha
                    and manifest.get("final_job_id") == job_id,
                    "Final archive stage manifest differs",
                )
                log_name, receipt_name = (
                    f"logs/{job_id}/{stage}.json",
                    f"receipts/{job_id}/{stage}.json",
                )
                log = _read_json_member(archive, log_name)
                require(
                    log.get("schema") == "hung-final-stage-log-v1"
                    and log.get("lock_sha256") == lock_sha
                    and log.get("job_id") == job_id
                    and log.get("stage") == stage
                    and log.get("manifest_sha256") == files[record["manifest"]]["sha256"],
                    "Final archive stage log differs",
                )
                receipt = _read_json_member(archive, receipt_name)
                require(
                    receipt
                    == {
                        "schema": "hung-dispatch-stage-receipt-v1",
                        "binding": {
                            "schema": "hung-final-stage-binding-v1",
                            "lock_sha256": lock_sha,
                            "job_id": job_id,
                            "stage": stage,
                        },
                        "files": {
                            name.removeprefix(prefix): {
                                "bytes": files[name]["bytes"],
                                "sha256": files[name]["sha256"],
                            }
                            for name in actual
                        },
                        "log": {
                            "bytes": files[log_name]["bytes"],
                            "sha256": files[log_name]["sha256"],
                        },
                    },
                    "Final archive stage receipt differs",
                )
        allowed = {"final_lock_identity.json"}
        for job_id, stages in expected.items():
            for stage in stages:
                allowed.update((f"logs/{job_id}/{stage}.json", f"receipts/{job_id}/{stage}.json"))
        require(
            set(files)
            == allowed
            | {
                name
                for job in index["jobs"].values()
                for stage in job.values()
                for name in stage["artifacts"]
            },
            "Final archive has extra/unmapped files",
        )
    return {
        "status": "local_archive_readback_verified",
        "archive": {"path": str(archive_path), **archive_identity},
        "lock_sha256": lock_sha,
        "jobs": index["jobs"],
    }


def create_archive(context: dict, archive_path: Path) -> dict:
    """Publish once only after independent archive readback passes."""
    require(context.get("input_runs_verified") is True, "Final lock/input preflight is required")
    jobs, plan, lock_sha = context["jobs"], context["plan"], context["lock_sha256"]
    require(
        not archive_path.exists() and not archive_path.is_symlink(), "Final archive already exists"
    )
    root = context["output_root"]
    require(not archive_path.is_relative_to(root), "Final archive cannot be inside stage output")
    index = _inventory(root, _expected_stages(jobs, plan), lock_sha)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=".final-archive-", suffix=".tmp", dir=archive_path.parent
    )
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        with ZipFile(temporary, "w", compression=ZIP_DEFLATED, allowZip64=True) as archive:
            for name in sorted(index["files"]):
                archive.write(root / name, arcname=name)
            archive.writestr("index.json", _json_bytes(index))
        digest = _digest(temporary)
        result = readback_archive(temporary, digest["sha256"], lock_sha, jobs, plan)
        os.link(temporary, archive_path)
        return {**result, "archive": {"path": str(archive_path), **digest}}
    finally:
        temporary.unlink(missing_ok=True)
