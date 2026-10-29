"""Verify historical Block7/Main execution code against their recorded Git commits."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAIRS = ROOT / "docs/reports/hung-block7-manifest-pairs-20261028.csv"
PAIRS_SHA256 = "e260de421d6c53ef3dffe5901f9e3478708b9e578791d3f370588a0a508699de"
MANIFESTS = ROOT / ".cache/block7-review-v1/manifests"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_bytes(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def _read_manifest(run_id: str, expected_sha: str) -> dict:
    path = MANIFESTS / f"{run_id}.json"
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Missing or linked manifest: {run_id}")
    raw = path.read_bytes()
    if sha256(raw) != expected_sha:
        raise ValueError(f"Manifest SHA mismatch: {run_id}")
    manifest = json.loads(raw)
    if manifest["run_id"] != "replay-90" or manifest["code"]["worktree_status"] != []:
        raise ValueError(f"Manifest identity or dirty execution tree: {run_id}")
    return manifest


def _runtime_identity(manifest: dict) -> tuple[str, str, str, str, str, str]:
    device = manifest["device"]
    return (
        manifest["python"],
        manifest["torch"],
        device["type"],
        device["name"],
        device["cuda_runtime"],
        device["torch"],
    )


def assess(rows: list[dict[str, str]]) -> dict:
    """Bind each recorded execution source to both immutable Git trees."""
    if len(rows) != 69:
        raise ValueError("Expected 69 historical/Main pairs")
    seen: set[str] = set()
    commit_pairs: set[tuple[str, str]] = set()
    source_paths: set[str] = set()
    source_cache: dict[tuple[str, str], str] = {}
    for row in rows:
        cell = row["cell_id"]
        if cell in seen:
            raise ValueError(f"Duplicate logical cell: {cell}")
        seen.add(cell)
        old = _read_manifest(row["historical_run_id"], row["historical_manifest_sha256"])
        current = _read_manifest(row["main_run_id"], row["main_manifest_sha256"])
        if _runtime_identity(old) != _runtime_identity(current):
            raise ValueError(f"Recorded execution runtime differs: {cell}")
        old_config = json.loads(json.dumps(old["config"]))
        current_config = json.loads(json.dumps(current["config"]))
        if (
            old_config["controller"].pop("block_days") != 7
            or current_config["controller"].pop("block_days") != 14
            or old_config != current_config
        ):
            raise ValueError(f"Replay config differs beyond block length: {cell}")
        old_commit = old["code"]["commit"]
        current_commit = current["code"]["commit"]
        if old_commit == current_commit:
            raise ValueError(f"Expected distinct code commit metadata: {cell}")
        commit_pairs.add((old_commit, current_commit))
        old_sources = old["code"]["executed_sources"]
        current_sources = current["code"]["executed_sources"]
        if old_sources != current_sources or len(old_sources) != 11:
            raise ValueError(f"Recorded execution source maps differ: {cell}")
        source_paths.update(old_sources)
        for commit, recorded in ((old_commit, old_sources), (current_commit, current_sources)):
            for path, expected_sha in recorded.items():
                key = (commit, path)
                if key not in source_cache:
                    source_cache[key] = sha256(git_bytes("show", f"{commit}:{path}"))
                if source_cache[key] != expected_sha:
                    raise ValueError(f"Git source bytes differ from manifest: {commit}:{path}")
    if len(commit_pairs) != 1 or len(source_paths) != 11:
        raise ValueError("Unexpected commit or executed-source inventory")
    old_commit, current_commit = next(iter(commit_pairs))
    changed = []
    for line in (
        git_bytes("diff", "--name-status", "--no-renames", old_commit, current_commit)
        .decode("utf-8")
        .splitlines()
    ):
        status, path = line.split("\t", 1)
        changed.append({"status": status, "path": path})
    if not changed or any(not item["path"].startswith("docs/") for item in changed):
        raise ValueError("Execution commits differ outside documentation")
    return {
        "schema": "hung-block7-code-lineage-v1",
        "pairs_csv_sha256": PAIRS_SHA256,
        "manifest_pairs_checked": len(rows),
        "runtime_and_config_pairs_checked": len(rows),
        "historical_code_commit": old_commit,
        "main_code_commit": current_commit,
        "executed_source_paths_checked": sorted(source_paths),
        "unique_git_source_blobs_sha256_checked": len(source_cache),
        "changed_paths_between_commits": changed,
        "only_documentation_differs": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = PAIRS.read_bytes()
    if sha256(raw) != PAIRS_SHA256:
        raise ValueError("Pair table SHA mismatch")
    rows = list(csv.DictReader(raw.decode("utf-8").splitlines()))
    result = assess(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
