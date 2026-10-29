"""Copy the 138 approved, pinned Block7 journals into create-only local staging."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PureWindowsPath

from tools import hung_block7_journal_stage as stage


def main() -> int:
    records = stage.rows()
    if stage.REQUEST.read_bytes() != stage.render(records):
        raise ValueError("Pinned journal request changed")
    coverage = json.loads(stage.pairs.DEFAULT_COVERAGE.read_text(encoding="utf-8"))
    sources: dict[tuple[str, str], Path] = {}
    for role, entries in (
        ("historical", coverage["external_complete_jobs"]),
        ("main", coverage["reused_jobs"]),
    ):
        for run_id, entry in entries.items():
            spec = entry["run_manifest"] if role == "historical" else entry
            original = PureWindowsPath(spec["path"])
            if stage.OLD_ROOT not in original.parents or original.name != "run_manifest.json":
                raise ValueError(f"Unapproved path for {run_id}")
            sources[(role, run_id)] = Path(str(original.with_name("events.jsonl")))

    stage.STAGE.mkdir(parents=True, exist_ok=True)
    if not stage.STAGE.resolve().is_relative_to(stage.ROOT.resolve()):
        raise ValueError("Staging escapes repository")
    old_root = Path(str(stage.OLD_ROOT)).resolve(strict=True)
    copied = 0
    existing = 0
    for row in records:
        source = sources[(row["role"], row["run_id"])]
        if source.is_symlink() or not source.resolve(strict=True).is_relative_to(old_root):
            raise ValueError(f"Source escapes approved worktree: {row['run_id']}")
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise ValueError(f"Source SHA mismatch: {row['run_id']}")
        target = stage.ROOT / row["staged_path"]
        try:
            with target.open("xb") as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            copied += 1
        except FileExistsError:
            if target.is_symlink() or stage.pairs.sha_file(target) != row["sha256"]:
                raise ValueError(f"Existing staged file mismatch: {row['run_id']}") from None
            existing += 1
        if stage.pairs.sha_file(target) != row["sha256"]:
            raise ValueError(f"Staged SHA mismatch: {row['run_id']}")
    result = stage.verify(records)
    print(json.dumps({"copied": copied, "existing": existing, **result}, sort_keys=True))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
