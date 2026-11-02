"""Request and verify exact historical Block7/Main event journals without opening old worktrees."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from pathlib import Path, PureWindowsPath

from tools import hung_block7_manifest_pairs as pairs

ROOT = pairs.ROOT
STAGE = ROOT / ".cache/block7-journal-import-v1"
REQUEST = ROOT / "docs/reports/hung-block7-journal-request-20261030-v1.csv"
FIELDS = ("role", "run_id", "sha256", "staged_path")
OLD_ROOT = PureWindowsPath("D:/Đồ Án/.cache/hung-method-integration-v1")


def rows() -> list[dict[str, str]]:
    evidence = json.loads(pairs.EVIDENCE.read_text(encoding="utf-8"))
    expected_sha = evidence["audit"]["provenance"]["inputs"]["coverage"]["sha256"]
    if pairs.sha_file(pairs.DEFAULT_COVERAGE) != expected_sha:
        raise ValueError("Pinned Block7 coverage changed")
    coverage = json.loads(pairs.DEFAULT_COVERAGE.read_text(encoding="utf-8"))
    result = []
    for role, entries in (
        ("historical", coverage["external_complete_jobs"]),
        ("main", coverage["reused_jobs"]),
    ):
        for run_id, entry in entries.items():
            spec = entry["run_manifest"] if role == "historical" else entry
            original = PureWindowsPath(spec["path"])
            if OLD_ROOT not in original.parents or original.name != "run_manifest.json":
                raise ValueError("Manifest path is outside the pinned old worktree")
            manifest = pairs.checked_manifest(
                spec, ROOT / ".cache/block7-review-v1/manifests" / f"{run_id}.json"
            )
            filename = manifest["event_journal"]["file"]
            digest = manifest["event_journal"]["sha256"]
            if filename != "events.jsonl" or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("Invalid pinned event journal identity")
            result.append(
                {
                    "role": role,
                    "run_id": run_id,
                    "sha256": digest,
                    "staged_path": f".cache/block7-journal-import-v1/{digest}.jsonl",
                }
            )
    result.sort(key=lambda row: (row["role"], row["run_id"]))
    if len(result) != 138 or len({row["sha256"] for row in result}) != 138:
        raise ValueError("Expected 138 distinct historical/Main event journal hashes")
    return result


def render(records: list[dict[str, str]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return stream.getvalue().encode("utf-8")


def verify(records: list[dict[str, str]], stage: Path = STAGE) -> dict:
    if not stage.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Stage directory must remain within current repository")
    expected = {f"{row['sha256']}.jsonl" for row in records}
    present = {path.name for path in stage.iterdir()} if stage.is_dir() else set()
    counts = {"VERIFIED": 0, "MISSING": 0, "MISMATCH": 0}
    for row in records:
        path = stage / f"{row['sha256']}.jsonl"
        if not path.exists():
            status = "MISSING"
        elif path.is_symlink() or not path.is_file() or pairs.sha_file(path) != row["sha256"]:
            status = "MISMATCH"
        else:
            status = "VERIFIED"
        counts[status] += 1
    return {
        "expected": len(records),
        "counts": counts,
        "unexpected_entries": sorted(present - expected),
        "complete": counts["VERIFIED"] == len(records) and not (present - expected),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-request", action="store_true")
    args = parser.parse_args()
    records = rows()
    payload = render(records)
    if args.write_request:
        if REQUEST.exists():
            if REQUEST.read_bytes() != payload:
                raise ValueError("Existing journal request differs")
        else:
            with REQUEST.open("xb") as stream:
                stream.write(payload)
    result = verify(records)
    result["request_sha256"] = hashlib.sha256(payload).hexdigest()
    print(json.dumps(result, sort_keys=True))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
