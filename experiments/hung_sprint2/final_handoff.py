"""Create-once private Kaggle handoff packet from an authenticated Final lock."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

from experiments.hung_sprint2.final_lock import ROOT, _project_path, validate_lock
from experiments.hung_sprint2.kaggle_final_locked_v1 import SCHEMA, _relative, digest, require

WRAPPER = ROOT / "experiments" / "hung_sprint2" / "kaggle_final_locked_v1.py"
WRAPPER_GIT_PATH = "experiments/hung_sprint2/kaggle_final_locked_v1.py"


def _source_at_commit(commit: str) -> bytes:
    try:
        return subprocess.check_output(
            ["git", "show", f"{commit}:{WRAPPER_GIT_PATH}"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError as error:
        raise ValueError("Pinned code commit lacks the Kaggle Final wrapper") from error


def _bundle(path: Path, commit: str) -> None:
    require(not path.exists(), "Final code bundle already exists")
    subprocess.run(["git", "bundle", "create", str(path), "HEAD"], cwd=ROOT, check=True)
    subprocess.run(["git", "bundle", "verify", str(path)], cwd=ROOT, check=True)
    contains = subprocess.run(
        ["git", "bundle", "list-heads", str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    require(bool(contains) and _source_at_commit(commit), "Final code bundle is empty")


def _relative_cache(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    require(_relative(rel).parts[0] == ".cache", "Final handoff requires ignored .cache pins")
    return rel


def _sources(context: dict, lock_path: Path) -> dict[str, tuple[Path, str]]:
    lock = context["lock"]
    items = {
        "lock.json": (lock_path, _relative_cache(lock_path)),
        "jobset.json": (
            _project_path(lock["jobset"]["path"]),
            _relative_cache(_project_path(lock["jobset"]["path"])),
        ),
        "execution_plan.json": (
            _project_path(lock["execution_plan"]["path"]),
            _relative_cache(_project_path(lock["execution_plan"]["path"])),
        ),
        "analysis.json": (
            _project_path(lock["analysis"]["path"]),
            _relative_cache(_project_path(lock["analysis"]["path"])),
        ),
        "inputs.zip": (
            _project_path(lock["input"]["path"]),
            _relative_cache(_project_path(lock["input"]["path"])),
        ),
    }
    for index, reference in enumerate(lock["source_checkpoints"]):
        source = _project_path(reference["path"])
        record = source.parent / "run_manifest.json"
        require(record.is_file() and not record.is_symlink(), "Final Source run manifest is absent")
        manifest = json.loads(record.read_text(encoding="utf-8"))
        require(
            manifest.get("checkpoint_sha256") == reference["sha256"]
            and isinstance(manifest.get("input_binding"), dict),
            "Final Source checkpoint/manifest lineage differs",
        )
        stem = f"source-{index:02d}-{reference['sha256'][:12]}"
        items[f"{stem}.pt"] = (source, _relative_cache(source))
        items[f"{stem}-manifest.json"] = (record, _relative_cache(record))
    require(
        len({target for _, target in items.values()}) == len(items),
        "Duplicate Final handoff overlay target",
    )
    return items


def prepare_handoff(
    lock_path: Path,
    lock_sha256: str,
    dataset_version: str,
    packet: Path,
    *,
    check_code: bool = True,
    create_bundle=_bundle,
) -> dict:
    """Package only authenticated bytes; never extract Final-role ZIP members."""
    require(
        re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/1", dataset_version) is not None,
        "Final private Dataset identity must name version one",
    )
    context = validate_lock(lock_path, lock_sha256, check_code=check_code, verify_input_runs=False)
    lock_path = _project_path(str(lock_path))
    commit = context["lock"]["code_commit"]
    require(
        hashlib.sha256(_source_at_commit(commit)).hexdigest() == digest(WRAPPER)["sha256"],
        "Kaggle wrapper differs from pinned code commit",
    )
    sources = _sources(context, lock_path)
    packet = _project_path(str(packet))
    require(
        packet.is_relative_to((ROOT / ".cache").resolve())
        and not packet.exists()
        and not packet.is_symlink()
        and not packet.is_relative_to(context["output_root"]),
        "Final handoff packet must be a new ignored path outside output",
    )
    total_bytes = sum(source.stat().st_size for source, _ in sources.values())
    require(
        shutil.disk_usage(ROOT).free
        >= context["lock"]["resources"]["min_free_bytes"] + total_bytes,
        "Insufficient disk for create-only Final handoff copy",
    )
    payload = packet / "payload"
    payload.mkdir(parents=True, exist_ok=False)
    bundle = payload / "code.bundle"
    create_bundle(bundle, commit)
    files = {"code.bundle": {**digest(bundle), "target": None}}
    for name, (source, target) in sources.items():
        destination = payload / name
        require(not destination.exists(), "Duplicate Final handoff package file")
        with source.open("rb") as incoming, destination.open("xb") as outgoing:
            shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
        identity = digest(destination)
        require(identity == digest(source), f"Final handoff copy changed: {name}")
        files[name] = {**identity, "target": target}
    manifest = {
        "schema": SCHEMA,
        "dataset_version": dataset_version,
        "code_commit": commit,
        "lock_sha256": lock_sha256,
        "wrapper_sha256": digest(WRAPPER)["sha256"],
        "files": files,
    }
    manifest_path = payload / "final-handoff-manifest.json"
    with manifest_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, sort_keys=True, indent=2)
        stream.write("\n")
    require(
        {path.name for path in payload.iterdir()} == set(files) | {manifest_path.name},
        "Final handoff package member set differs",
    )
    return {
        "status": "PREPARED_ONLY_PRIVATE_UPLOAD_PENDING",
        "packet": str(packet),
        "dataset_version": dataset_version,
        "manifest_sha256": digest(manifest_path)["sha256"],
        "files": len(files),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--lock-sha256", required=True)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--packet", type=Path, required=True)
    args = parser.parse_args(argv)
    print(
        json.dumps(
            prepare_handoff(args.lock, args.lock_sha256, args.dataset_version, args.packet),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
