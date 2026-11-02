"""Import only 138 approved replay-90 runner checkpoints with pinned SHA checks."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PureWindowsPath

from tools import hung_block7_journal_stage as stage

STAGE = stage.ROOT / ".cache/block7-terminal-checkpoint-import-v1"
OUT = stage.ROOT / "docs/reports/hung-block7-terminal-checkpoint-import-20261030-v1.json"


def main() -> int:
    records = stage.rows()
    if stage.REQUEST.read_bytes() != stage.render(records) or not stage.verify(records)["complete"]:
        raise ValueError("Saved replay-90 journal gate is incomplete")
    coverage = json.loads(stage.pairs.DEFAULT_COVERAGE.read_text(encoding="utf-8"))
    old_root = Path(str(stage.OLD_ROOT)).resolve(strict=True)
    STAGE.mkdir(parents=True, exist_ok=True)
    if not STAGE.resolve().is_relative_to(stage.ROOT.resolve()):
        raise ValueError("Terminal checkpoint stage escapes repository")
    details = []
    copied = 0
    existing = 0
    for row in records:
        run_id, role = row["run_id"], row["role"]
        spec = (
            coverage["external_complete_jobs"][run_id]["run_manifest"]
            if role == "historical"
            else coverage["reused_jobs"][run_id]
        )
        original = PureWindowsPath(spec["path"])
        if stage.OLD_ROOT not in original.parents or original.name != "run_manifest.json":
            raise ValueError(f"Unapproved source path: {run_id}")
        manifest = stage.pairs.checked_manifest(
            spec, stage.ROOT / ".cache/block7-review-v1/manifests" / f"{run_id}.json"
        )
        expected_sha = manifest["final_runner_checkpoint_sha256"]
        if not isinstance(expected_sha, str) or len(expected_sha) != 64:
            raise ValueError(f"Invalid pinned checkpoint SHA: {run_id}")
        source = Path(str(original.with_name("runner_checkpoint.pt")))
        if source.is_symlink() or not source.resolve(strict=True).is_relative_to(old_root):
            raise ValueError(f"Source escapes approved worktree: {run_id}")
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected_sha:
            raise ValueError(f"Source checkpoint SHA mismatch: {run_id}")
        target = STAGE / f"{run_id}.pt"
        try:
            with target.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            copied += 1
        except FileExistsError:
            if target.is_symlink() or stage.pairs.sha_file(target) != expected_sha:
                raise ValueError(f"Existing staged checkpoint mismatch: {run_id}") from None
            existing += 1
        if stage.pairs.sha_file(target) != expected_sha:
            raise ValueError(f"Staged checkpoint SHA mismatch: {run_id}")
        details.append(
            {
                "role": role,
                "run_id": run_id,
                "sha256": expected_sha,
                "bytes": len(data),
                "saved_manifest_sha256": spec["sha256"],
            }
        )
    if len(details) != 138 or copied + existing != 138:
        raise ValueError("Expected exactly 138 terminal runner checkpoints")
    result = {
        "schema": "hung-block7-terminal-checkpoint-import-v1",
        "approved_scope": "138 exact replay-90 runner_checkpoint.pt files",
        "checked": len(details),
        "copied": copied,
        "existing": existing,
        "details": details,
    }
    payload = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        with OUT.open("xb") as stream:
            stream.write(payload)
    except FileExistsError:
        previous = json.loads(OUT.read_text(encoding="utf-8"))
        stable_fields = ("schema", "approved_scope", "checked", "details")
        if any(previous.get(key) != result.get(key) for key in stable_fields):
            raise ValueError("Existing terminal checkpoint evidence differs") from None
    print(
        json.dumps(
            {"checked": len(details), "copied": copied, "existing": existing}, sort_keys=True
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
