"""Build, verify and stage an immutable issue #99 Kaggle input bundle."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import shutil
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from zipfile import ZIP_STORED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_NAME = "qyroven-issue23-source-duration-20261026-v1-seed{seed}.zip"
INPUT_NAME = "inputs-urbanev-SZH-v1.zip"
INPUT_PREFIX = "data/inputs/issue18-input-handoff-v1-20261019/urbanev-SZH-14d/"
INPUT_MEMBERS = {
    "entities.jsonl",
    "forecasts.jsonl",
    "labels.jsonl",
    "manifest.json",
    "schedule.jsonl",
    "training.jsonl",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact(path: Path) -> dict:
    return {"name": path.name, "size_bytes": path.stat().st_size, "sha256": sha256(path)}


def check_member(name: str) -> PurePosixPath:
    parsed = PurePosixPath(name)
    if (
        not name
        or "\\" in name
        or parsed.is_absolute()
        or any(part in {"", ".", ".."} for part in parsed.parts)
        or ":" in parsed.parts[0]
    ):
        raise ValueError(f"Unsafe ZIP member: {name}")
    return parsed


def zip_check(path: Path) -> None:
    with ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError(f"ZIP CRC failed: {path.name}")
        for info in archive.infolist():
            check_member(info.filename.rstrip("/"))
            mode = (info.external_attr >> 16) & 0o170000
            if mode == stat.S_IFLNK:
                raise ValueError(f"ZIP symlink not allowed: {info.filename}")


def historical_expectations(audit_path: Path) -> dict:
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("status") != "PASS" or audit.get("schema") != "issue99-local-audit-v1":
        raise ValueError("Missing PASS local audit")
    return {
        "input_sha256": audit["inputs"]["zip_sha256"],
        "input_manifest_sha256": audit["inputs"]["budgets"]["14"]["manifest_sha256"],
        "source": {seed: audit["source"][str(seed)] for seed in (42, 43, 44)},
    }


def committed_code(root: Path) -> tuple[str, dict[str, str]]:
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"], cwd=root, text=True
    )
    if status.strip():
        raise ValueError("Commit and clean the code worktree before Kaggle packaging")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    required = (
        "ev_control/continuous.py",
        "ev_control/hypergradient.py",
        "ev_runner/continuous.py",
        "ev_runner/continuous_run.py",
        "tools/issue99_kaggle_package.py",
    )
    hashes = {}
    for name in required:
        path = root / name
        committed = subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=root)
        actual = hashlib.sha256(committed).hexdigest()
        if actual != sha256(path):
            raise ValueError(f"Working code differs from commit: {name}")
        hashes[name] = actual
    return commit, hashes


def copy_checked(source: Path, destination: Path, expected: str) -> dict:
    if sha256(source) != expected:
        raise ValueError(f"Source SHA-256 differs: {source.name}")
    with source.open("rb") as incoming, destination.open("xb") as outgoing:
        shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
        outgoing.flush()
        os.fsync(outgoing.fileno())
    if sha256(destination) != expected:
        raise ValueError(f"Copied SHA-256 differs: {destination.name}")
    return artifact(destination)


def create_bundle(
    destination: Path,
    input_zip: Path,
    source_directory: Path,
    audit_path: Path,
    *,
    root: Path = ROOT,
) -> dict:
    """Create a new bundle; refuse any existing destination or uncommitted code."""
    if destination.exists():
        raise FileExistsError(destination)
    expected = historical_expectations(audit_path)
    commit, code_files = committed_code(root)
    # Authenticate every input before creating the destination.
    sources = {seed: source_directory / SOURCE_NAME.format(seed=seed) for seed in (42, 43, 44)}
    if sha256(input_zip) != expected["input_sha256"]:
        raise ValueError("Input ZIP differs from PASS audit")
    for seed, path in sources.items():
        if sha256(path) != expected["source"][seed]["zip_sha256"]:
            raise ValueError(f"Source ZIP differs from PASS audit: {seed}")
    destination.mkdir(parents=True, exist_ok=False)
    code_archive = destination / "issue99-code.zip"
    with code_archive.open("xb") as output:
        process = subprocess.run(
            ["git", "archive", "--format=zip", commit],
            cwd=root,
            stdout=output,
            stderr=subprocess.PIPE,
            check=False,
        )
        if process.returncode:
            raise RuntimeError(process.stderr.decode(errors="replace"))
        output.flush()
        os.fsync(output.fileno())
    files = {"code": artifact(code_archive)}
    files["input"] = copy_checked(input_zip, destination / INPUT_NAME, expected["input_sha256"])
    files["sources"] = {
        str(seed): copy_checked(
            path, destination / path.name, expected["source"][seed]["zip_sha256"]
        )
        for seed, path in sources.items()
    }
    files["preflight"] = copy_checked(
        root / "tools/issue99_kaggle_package.py",
        destination / "preflight.py",
        code_files["tools/issue99_kaggle_package.py"],
    )
    manifest = {
        "schema": "issue99-kaggle-bundle-v1",
        "scope": "Prepared authenticated inputs; no Kaggle upload or model run",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "code_commit": commit,
        "code_files_sha256": code_files,
        "local_audit_sha256": sha256(audit_path),
        "input_manifest_sha256": expected["input_manifest_sha256"],
        "source_checkpoint_sha256": {
            str(seed): expected["source"][seed]["checkpoint_sha256"] for seed in sources
        },
        "files": files,
    }
    with (destination / "manifest.json").open("xb") as output:
        output.write((json.dumps(manifest, indent=2, allow_nan=False) + "\n").encode())
        output.flush()
        os.fsync(output.fileno())
    verify_bundle(destination)
    return manifest


def verify_bundle(directory: Path, *, expected_manifest_sha256: str | None = None) -> dict:
    """Recompute every copied SHA and nested ZIP/checkpoint identity in place."""
    if (
        expected_manifest_sha256 is not None
        and sha256(directory / "manifest.json") != expected_manifest_sha256
    ):
        raise ValueError("Bundle manifest differs from locally pinned SHA-256")
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != "issue99-kaggle-bundle-v1":
        raise ValueError("Unsupported Kaggle bundle manifest")
    if not isinstance(manifest.get("code_commit"), str) or not re.fullmatch(
        r"[0-9a-f]{40}", manifest["code_commit"]
    ):
        raise ValueError("Invalid pinned code commit")
    file_records = [manifest["files"][key] for key in ("code", "input", "preflight")]
    file_records += list(manifest["files"]["sources"].values())
    for record in file_records:
        path = directory / record["name"]
        if path.name != record["name"] or path.stat().st_size != record["size_bytes"]:
            raise ValueError(f"Bundle size/name mismatch: {record['name']}")
        if sha256(path) != record["sha256"]:
            raise ValueError(f"Bundle SHA-256 mismatch: {record['name']}")
        if path.suffix == ".zip":
            zip_check(path)
    with ZipFile(directory / INPUT_NAME) as archive:
        inner = archive.read(INPUT_PREFIX + "manifest.json")
        if hashlib.sha256(inner).hexdigest() != manifest["input_manifest_sha256"]:
            raise ValueError("14-day input manifest mismatch in bundle")
    for seed, record in manifest["files"]["sources"].items():
        with ZipFile(directory / record["name"]) as archive:
            digest = hashlib.sha256(archive.read("epoch-10.pt")).hexdigest()
            if digest != manifest["source_checkpoint_sha256"][seed]:
                raise ValueError(f"Source10 checkpoint differs in bundle: {seed}")
    with ZipFile(directory / manifest["files"]["code"]["name"]) as archive:
        for name, expected in manifest["code_files_sha256"].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError(f"Committed code differs in bundle: {name}")
    return manifest


def wrap_bundle(directory: Path, outer_zip: Path, *, expected_manifest_sha256: str) -> dict:
    """Hide inner ZIP extensions from Kaggle's automatic dataset extraction."""
    manifest = verify_bundle(directory, expected_manifest_sha256=expected_manifest_sha256)
    if outer_zip.exists():
        raise FileExistsError(outer_zip)
    records = [manifest["files"][key] for key in ("code", "input")]
    records += list(manifest["files"]["sources"].values())
    with ZipFile(outer_zip, "x", compression=ZIP_STORED, allowZip64=True) as archive:
        archive.write(directory / "manifest.json", "manifest.json")
        archive.write(directory / "preflight.py", "preflight.py")
        for record in records:
            name = record["name"]
            if not name.endswith(".zip") or Path(name).name != name:
                raise ValueError(f"Invalid inner ZIP name: {name}")
            archive.write(directory / name, name + ".bin")
    zip_check(outer_zip)
    return {
        "schema": "issue99-kaggle-outer-zip-v1",
        "outer_zip": artifact(outer_zip),
        "manifest_sha256": expected_manifest_sha256,
        "inner_zip_suffix": ".zip.bin",
    }


def rehydrate_bundle(
    extracted_outer: Path, destination: Path, *, expected_manifest_sha256: str
) -> dict:
    """Restore verified inner ZIP bytes under exact names in a fresh directory."""
    if sha256(extracted_outer / "manifest.json") != expected_manifest_sha256:
        raise ValueError("Auto-extracted manifest differs from locally pinned SHA-256")
    manifest = json.loads((extracted_outer / "manifest.json").read_text(encoding="utf-8"))
    if destination.exists():
        raise FileExistsError(destination)
    records = [manifest["files"][key] for key in ("code", "input")]
    records += list(manifest["files"]["sources"].values())
    for record in records:
        name = record["name"]
        if not name.endswith(".zip") or Path(name).name != name:
            raise ValueError(f"Invalid rehydrated ZIP name: {name}")
        source = extracted_outer / (name + ".bin")
        if source.stat().st_size != record["size_bytes"] or sha256(source) != record["sha256"]:
            raise ValueError(f"Auto-extracted inner ZIP differs: {name}")
    preflight = manifest["files"]["preflight"]
    if (
        preflight["name"] != "preflight.py"
        or sha256(extracted_outer / "preflight.py") != preflight["sha256"]
    ):
        raise ValueError("Auto-extracted preflight differs")
    destination.mkdir(parents=True, exist_ok=False)
    copy_checked(
        extracted_outer / "manifest.json", destination / "manifest.json", expected_manifest_sha256
    )
    copy_checked(
        extracted_outer / "preflight.py", destination / "preflight.py", preflight["sha256"]
    )
    for record in records:
        copy_checked(
            extracted_outer / (record["name"] + ".bin"),
            destination / record["name"],
            record["sha256"],
        )
    return verify_bundle(destination, expected_manifest_sha256=expected_manifest_sha256)


def rehydrate_and_stage(
    extracted_outer: Path,
    bundle_destination: Path,
    stage_destination: Path,
    *,
    expected_manifest_sha256: str,
    require_t4: bool = False,
) -> dict:
    """Rehydrate Kaggle's auto-extracted outer ZIP, verify, then stage."""
    rehydrate_bundle(
        extracted_outer,
        bundle_destination,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    return stage_bundle(
        bundle_destination,
        stage_destination,
        expected_manifest_sha256=expected_manifest_sha256,
        require_t4=require_t4,
    )


def extract_member(archive: ZipFile, name: str, destination: Path) -> None:
    check_member(name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with archive.open(name) as incoming, destination.open("xb") as outgoing:
        shutil.copyfileobj(incoming, outgoing, 1024 * 1024)


def stage_bundle(
    directory: Path,
    destination: Path,
    *,
    expected_manifest_sha256: str | None = None,
    require_t4: bool = False,
) -> dict:
    """Verify mounted Kaggle bytes, then extract only into a fresh stage root."""
    manifest = verify_bundle(directory, expected_manifest_sha256=expected_manifest_sha256)
    runtime = {
        "schema": "issue99-kaggle-runtime-v1",
        "code_commit": manifest["code_commit"],
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {},
    }
    for package in ("torch", "numpy", "scipy", "scikit-learn"):
        try:
            runtime["packages"][package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            runtime["packages"][package] = None
    try:
        import torch
    except ImportError:
        runtime["cuda"] = None
        runtime["gpu"] = None
    else:
        runtime["cuda"] = torch.version.cuda
        runtime["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    if require_t4 and (runtime["gpu"] is None or "T4" not in runtime["gpu"]):
        raise ValueError("Kaggle pilot requires an active T4 GPU")
    if destination.exists():
        raise FileExistsError(destination)
    destination.mkdir(parents=True, exist_ok=False)
    with ZipFile(directory / manifest["files"]["code"]["name"]) as archive:
        for info in archive.infolist():
            name = info.filename.rstrip("/")
            check_member(name)
            if not info.is_dir():
                extract_member(archive, info.filename, destination / "code" / name)
    with ZipFile(directory / INPUT_NAME) as archive:
        for filename in INPUT_MEMBERS:
            extract_member(archive, INPUT_PREFIX + filename, destination / "inputs" / filename)
    for seed, record in manifest["files"]["sources"].items():
        with ZipFile(directory / record["name"]) as archive:
            checkpoint = destination / "sources" / f"seed{seed}" / "epoch-10.pt"
            extract_member(archive, "epoch-10.pt", checkpoint)
            if sha256(checkpoint) != manifest["source_checkpoint_sha256"][seed]:
                raise ValueError(f"Extracted Source10 differs: {seed}")
    with (destination / "runtime.json").open("xb") as output:
        output.write((json.dumps(runtime, indent=2, allow_nan=False) + "\n").encode())
    with (destination / "code" / ".issue99-code-commit").open("xb") as output:
        output.write((manifest["code_commit"] + "\n").encode())
    return runtime


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    create = subcommands.add_parser("create")
    create.add_argument("--destination", type=Path, required=True)
    create.add_argument("--input-zip", type=Path, required=True)
    create.add_argument("--source-directory", type=Path, required=True)
    create.add_argument("--audit", type=Path, required=True)
    verify = subcommands.add_parser("verify")
    verify.add_argument("--bundle", type=Path, required=True)
    verify.add_argument("--expected-manifest-sha256", required=True)
    stage = subcommands.add_parser("stage")
    stage.add_argument("--bundle", type=Path, required=True)
    stage.add_argument("--destination", type=Path, required=True)
    stage.add_argument("--expected-manifest-sha256", required=True)
    stage.add_argument("--require-t4", action="store_true")
    wrap = subcommands.add_parser("wrap")
    wrap.add_argument("--bundle", type=Path, required=True)
    wrap.add_argument("--destination", type=Path, required=True)
    wrap.add_argument("--expected-manifest-sha256", required=True)
    rehydrate = subcommands.add_parser("rehydrate")
    rehydrate.add_argument("--extracted-outer", type=Path, required=True)
    rehydrate.add_argument("--bundle-destination", type=Path, required=True)
    rehydrate.add_argument("--stage-destination", type=Path, required=True)
    rehydrate.add_argument("--expected-manifest-sha256", required=True)
    rehydrate.add_argument("--require-t4", action="store_true")
    args = parser.parse_args()
    if args.command == "create":
        report = create_bundle(args.destination, args.input_zip, args.source_directory, args.audit)
        report = {"manifest_sha256": sha256(args.destination / "manifest.json"), "manifest": report}
    elif args.command == "verify":
        report = verify_bundle(args.bundle, expected_manifest_sha256=args.expected_manifest_sha256)
    elif args.command == "stage":
        report = stage_bundle(
            args.bundle,
            args.destination,
            expected_manifest_sha256=args.expected_manifest_sha256,
            require_t4=args.require_t4,
        )
    elif args.command == "wrap":
        report = wrap_bundle(
            args.bundle,
            args.destination,
            expected_manifest_sha256=args.expected_manifest_sha256,
        )
    else:
        report = rehydrate_and_stage(
            args.extracted_outer,
            args.bundle_destination,
            args.stage_destination,
            expected_manifest_sha256=args.expected_manifest_sha256,
            require_t4=args.require_t4,
        )
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
