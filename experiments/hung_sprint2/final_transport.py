"""Prepare a create-once private Kaggle handoff for a locked Final archive."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Callable

from experiments.hung_sprint2.dispatch_state import atomic_create
from experiments.hung_sprint2.final_archive import readback_archive, require

ARCHIVE_MODULE = Path(__file__).with_name("final_archive.py")
FILE_NAMES = ("archive.zip", "lock.json", "jobset.json", "execution_plan.json", "final_archive.py")


def _identity(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink(), f"Missing/unsafe transport input: {path}")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"bytes": path.stat().st_size, "sha256": digest}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _packet_manifest(packet: Path) -> dict:
    manifest = _read_json(packet / "payload" / "final-transport-manifest.json")
    require(
        set(manifest) == {"schema", "dataset", "lock_sha256", "files", "jobs"}
        and manifest["schema"] == "hung-final-transport-manifest-v1"
        and set(manifest["files"]) == set(FILE_NAMES),
        "Final transport manifest differs",
    )
    payload = packet / "payload"
    require(
        {item.name for item in payload.iterdir()}
        == set(FILE_NAMES) | {"final-transport-manifest.json"},
        "Final transport payload differs",
    )
    for name, expected in manifest["files"].items():
        require(_identity(payload / name) == expected, f"Final transport file differs: {name}")
    require(
        manifest["files"]["lock.json"]["sha256"] == manifest["lock_sha256"],
        "Final lock SHA differs",
    )
    return manifest


def _readback_source(manifest: dict, manifest_sha: str) -> str:
    # The mounted bundle includes only this stdlib verifier and three lock-bound JSON files.
    dataset = manifest["dataset"]
    owner, dataset_slug, _ = dataset.split("/")
    kernel = f"{owner}/{dataset_slug}-readback/1"
    return f'''"""Independent CPU readback of an exact Hùng Final private Dataset v1."""
import hashlib
import json
import runpy
from pathlib import Path

DATASET = {dataset!r}
KERNEL = {kernel!r}
MANIFEST_SHA = {manifest_sha!r}
roots = []
for candidate in Path("/kaggle/input").rglob("final-transport-manifest.json"):
    raw = candidate.read_bytes()
    if hashlib.sha256(raw).hexdigest() == MANIFEST_SHA:
        roots.append(candidate.parent)
assert len(roots) == 1, "Pinned Final Dataset missing or ambiguous"
root = roots[0]
manifest = json.loads((root / "final-transport-manifest.json").read_text())
assert manifest["schema"] == "hung-final-transport-manifest-v1"
assert manifest["dataset"] == DATASET
assert set(root.iterdir()) == {{root / name for name in manifest["files"]}} | {{root / "final-transport-manifest.json"}}
for name, pin in manifest["files"].items():
    path = root / name
    assert path.stat().st_size == pin["bytes"], name
    with path.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == pin["sha256"], name
assert manifest["files"]["lock.json"]["sha256"] == manifest["lock_sha256"]
lock = json.loads((root / "lock.json").read_text())
assert lock["schema"] == "hung-final-lock-v1" and lock["scope"] == "final_only"
assert lock["jobset"]["sha256"] == manifest["files"]["jobset.json"]["sha256"]
assert lock["execution_plan"]["sha256"] == manifest["files"]["execution_plan.json"]["sha256"]
jobs = json.loads((root / "jobset.json").read_text())["jobs"]
plan = json.loads((root / "execution_plan.json").read_text())["jobs"]
assert len(jobs) == lock["jobset"]["count"] == manifest["jobs"]
readback = runpy.run_path(str(root / "final_archive.py"))["readback_archive"]
verified = readback(root / "archive.zip", manifest["files"]["archive.zip"]["sha256"], manifest["lock_sha256"], jobs, plan)
receipt = {{"schema": "hung-final-remote-readback-v1", "status": "REMOTE_ARCHIVE_READBACK_VERIFIED",
           "dataset": DATASET, "readback_kernel": KERNEL, "manifest_sha256": MANIFEST_SHA,
           "lock_sha256": manifest["lock_sha256"], "archive": manifest["files"]["archive.zip"],
           "jobs": len(verified["jobs"])}}
Path("/kaggle/working/final-remote-readback.json").open("x", encoding="utf-8").write(json.dumps(receipt, sort_keys=True))
print(json.dumps(receipt, sort_keys=True), flush=True)
'''


def prepare_upload(context: dict, lock_path: Path, archive_path: Path, packet: Path) -> dict:
    """Bind a verified local archive and exact lock files to a new packet."""
    require(context.get("input_runs_verified") is True, "Final input/lock preflight is required")
    lock_sha = context["lock_sha256"]
    require(_identity(lock_path)["sha256"] == lock_sha, "Final lock file SHA differs")
    lock = context["lock"]
    jobset = Path(lock["jobset"]["path"])
    plan = Path(lock["execution_plan"]["path"])
    require(
        _identity(jobset) == {key: lock["jobset"][key] for key in ("bytes", "sha256")}
        and _identity(plan) == {key: lock["execution_plan"][key] for key in ("bytes", "sha256")},
        "Final jobset/plan pin differs",
    )
    archive_identity = _identity(archive_path)
    readback_archive(
        archive_path, archive_identity["sha256"], lock_sha, context["jobs"], context["plan"]
    )
    slug = f"hung-final-{lock_sha[:12]}-{archive_identity['sha256'][:12]}"
    dataset = f"hungluongduc/{slug}/1"
    require(
        not packet.exists() and not packet.is_symlink(), "Final transport packet already exists"
    )
    payload = packet / "payload"
    payload.mkdir(parents=True, exist_ok=False)
    sources = {
        "archive.zip": archive_path,
        "lock.json": lock_path,
        "jobset.json": jobset,
        "execution_plan.json": plan,
        "final_archive.py": ARCHIVE_MODULE,
    }
    for name, source in sources.items():
        os.link(source, payload / name)
    manifest = {
        "schema": "hung-final-transport-manifest-v1",
        "dataset": dataset,
        "lock_sha256": lock_sha,
        "files": {name: _identity(payload / name) for name in FILE_NAMES},
        "jobs": len(context["jobs"]),
    }
    atomic_create(payload / "final-transport-manifest.json", manifest)
    _packet_manifest(packet)
    manifest_sha = _identity(payload / "final-transport-manifest.json")["sha256"]
    source = _readback_source(manifest, manifest_sha)
    source_path = packet / "cpu_readback.py"
    with source_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(source)
    return {
        "dataset": dataset,
        "manifest_sha256": manifest_sha,
        "cpu_source_sha256": _identity(source_path)["sha256"],
        "cpu_source_path": str(source_path),
    }


def upload_once(packet: Path, create_private: Callable[[str, str, Path], None]) -> dict:
    """Issue one private Dataset create; HTTP499 is uncertain and never retried."""
    manifest = _packet_manifest(packet)
    owner, slug, version = manifest["dataset"].split("/")
    require(version == "1", "Final Dataset version must be one")
    attempt = packet / "upload-attempt.json"
    require(not attempt.exists(), "Final Dataset creation was already attempted")
    atomic_create(
        attempt,
        {
            "schema": "hung-final-upload-attempt-v1",
            "dataset": manifest["dataset"],
            "manifest_sha256": _identity(packet / "payload" / "final-transport-manifest.json")[
                "sha256"
            ],
        },
    )
    try:
        create_private(owner, slug, packet / "payload")
    except Exception as error:
        status = getattr(getattr(error, "response", None), "status_code", None)
        result = {
            "schema": "hung-final-upload-result-v1",
            "dataset": manifest["dataset"],
            "status": "UNCERTAIN_HTTP499" if status == 499 else "FAILED_UNCONFIRMED",
        }
        atomic_create(packet / "upload-result.json", result)
        if status == 499:
            return result
        raise
    result = {
        "schema": "hung-final-upload-result-v1",
        "dataset": manifest["dataset"],
        "status": "CREATE_ACKNOWLEDGED_READBACK_PENDING",
    }
    atomic_create(packet / "upload-result.json", result)
    return result


def kaggle_create_private(owner: str, slug: str, folder: Path) -> None:
    """Production adapter; caller supplies credentials and calls this explicitly."""
    from tools.hung_kaggle_storage import upload_private

    upload_private(slug, folder, owner)


def cpu_kernel_spec(packet: Path) -> dict:
    """Prepare the exact CPU-only saved-version request without submitting it."""
    manifest = _packet_manifest(packet)
    owner, dataset_slug, _ = manifest["dataset"].split("/")
    source_path = packet / "cpu_readback.py"
    require(source_path.is_file() and not source_path.is_symlink(), "CPU readback source is absent")
    source = source_path.read_text(encoding="utf-8")
    compile(source, str(source_path), "exec")
    return {
        "slug": f"{owner}/{dataset_slug}-readback",
        "expected_version": 1,
        "source": source,
        "source_sha256": _identity(source_path)["sha256"],
        "dataset_data_sources": [manifest["dataset"]],
        "enable_gpu": False,
        "enable_internet": False,
        "is_private": True,
    }


def verify_remote_receipt(packet: Path, receipt_path: Path) -> dict:
    """Check a downloaded saved-version receipt against the frozen local packet.

    Caller must additionally authenticate the provider's saved version/source list.
    """
    manifest = _packet_manifest(packet)
    receipt = _read_json(receipt_path)
    require(
        receipt
        == {
            "schema": "hung-final-remote-readback-v1",
            "status": "REMOTE_ARCHIVE_READBACK_VERIFIED",
            "dataset": manifest["dataset"],
            "readback_kernel": cpu_kernel_spec(packet)["slug"] + "/1",
            "manifest_sha256": _identity(packet / "payload" / "final-transport-manifest.json")[
                "sha256"
            ],
            "lock_sha256": manifest["lock_sha256"],
            "archive": manifest["files"]["archive.zip"],
            "jobs": manifest["jobs"],
        },
        "Final remote receipt differs",
    )
    return receipt
