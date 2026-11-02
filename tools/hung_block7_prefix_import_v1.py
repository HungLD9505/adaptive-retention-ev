"""Import only the 414 explicitly approved pre-resume Block7/Main files."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PureWindowsPath

from tools import hung_block7_journal_stage as stage

STAGE = stage.ROOT / ".cache/block7-prefix-import-v1"
OUT = stage.ROOT / "docs/reports/hung-block7-prefix-import-20261030-v1.json"
FILES = ("run_manifest.json", "events.jsonl", "runner_checkpoint.pt")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_prior(
    run_id: str, saved: dict, prior: dict, journal_bytes: bytes, checkpoint_bytes: bytes
) -> dict:
    resume = saved["resumed_from"]
    prior_stage = resume["run_id"]
    if (
        prior.get("run_id") != prior_stage
        or prior.get("status") != "completed"
        or prior.get("runner_cursor") != int(prior_stage.split("-")[1])
        or prior.get("input_binding") != saved.get("input_binding")
        or prior.get("final_runner_checkpoint_sha256") != resume["checkpoint_sha256"]
        or digest(checkpoint_bytes) != resume["checkpoint_sha256"]
    ):
        raise ValueError(f"Pre-resume checkpoint/manifest mismatch: {run_id}")
    journal = prior["event_journal"]
    if journal.get("file") != "events.jsonl" or digest(journal_bytes) != journal.get("sha256"):
        raise ValueError(f"Pre-resume journal SHA mismatch: {run_id}")
    lines = [json.loads(line) for line in journal_bytes.decode("utf-8").splitlines()]
    if not lines:
        raise ValueError(f"Empty pre-resume journal: {run_id}")
    header = lines[0]
    start = journal["start_event_index"]
    count = len(lines) - 1
    if (
        header.get("kind") != "header"
        or header.get("run_id") != prior_stage
        or header.get("schema") != "hung-sprint2-event-journal-v1"
        or header.get("input_binding") != prior.get("input_binding")
        or header.get("start_event_index") != start
        or journal["events_written"] != count
        or journal["end_event_index"] != start + count
        or saved["event_journal"]["start_event_index"] != journal["end_event_index"]
    ):
        raise ValueError(f"Pre-resume event/header boundary mismatch: {run_id}")
    for index, event in enumerate(lines[1:], start):
        if event.get("kind") != "event" or event.get("event_index") != index:
            raise ValueError(f"Pre-resume event index mismatch: {run_id}")
    return {
        "prior_stage": prior_stage,
        "start_event_index": start,
        "end_event_index": journal["end_event_index"],
        "events_written": count,
    }


def main() -> int:
    records = stage.rows()
    if stage.REQUEST.read_bytes() != stage.render(records) or not stage.verify(records)["complete"]:
        raise ValueError("Saved replay-90 journal gate is incomplete")
    coverage = json.loads(stage.pairs.DEFAULT_COVERAGE.read_text(encoding="utf-8"))
    old_root = Path(str(stage.OLD_ROOT)).resolve(strict=True)
    STAGE.mkdir(parents=True, exist_ok=True)
    if not STAGE.resolve().is_relative_to(stage.ROOT.resolve()):
        raise ValueError("Prefix stage escapes the current repository")
    details = []
    copied = 0
    existing = 0
    for row in records:
        run_id, role = row["run_id"], row["role"]
        entry = (
            coverage["external_complete_jobs"][run_id]["run_manifest"]
            if role == "historical"
            else coverage["reused_jobs"][run_id]
        )
        original = PureWindowsPath(entry["path"])
        if stage.OLD_ROOT not in original.parents or original.name != "run_manifest.json":
            raise ValueError(f"Unapproved source path: {run_id}")
        saved_path = stage.ROOT / ".cache/block7-review-v1/manifests" / f"{run_id}.json"
        saved = stage.pairs.checked_manifest(entry, saved_path)
        prior_stage = saved["resumed_from"]["run_id"]
        if prior_stage != ("replay-21" if role == "historical" else "replay-42"):
            raise ValueError(f"Unexpected pre-resume stage: {run_id}")
        source_root = original.parent.parent / prior_stage
        sources = {name: Path(str(source_root / name)) for name in FILES}
        for name, source in sources.items():
            if source.is_symlink() or not source.resolve(strict=True).is_relative_to(old_root):
                raise ValueError(f"Source escapes approved worktree: {run_id}/{name}")
        blobs = {name: source.read_bytes() for name, source in sources.items()}
        prior = json.loads(blobs["run_manifest.json"].decode("utf-8"))
        boundary = validate_prior(
            run_id, saved, prior, blobs["events.jsonl"], blobs["runner_checkpoint.pt"]
        )
        target_dir = STAGE / run_id
        target_dir.mkdir(exist_ok=True)
        file_details = {}
        for name, data in blobs.items():
            target = target_dir / name
            try:
                with target.open("xb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                copied += 1
            except FileExistsError:
                if target.is_symlink() or target.read_bytes() != data:
                    raise ValueError(f"Existing staged file mismatch: {run_id}/{name}") from None
                existing += 1
            if digest(target.read_bytes()) != digest(data):
                raise ValueError(f"Staged SHA mismatch: {run_id}/{name}")
            file_details[name] = {"sha256": digest(data), "bytes": len(data)}
        details.append({"role": role, "run_id": run_id, **boundary, "files": file_details})
    if len(details) != 138 or copied + existing != 414:
        raise ValueError("Expected exactly 138 stages and 414 files")
    result = {
        "schema": "hung-block7-prefix-import-v1",
        "approved_scope": "138 exact replay-21/42 stages, three files each",
        "checked_stages": len(details),
        "checked_files": copied + existing,
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
        stable_fields = ("schema", "approved_scope", "checked_stages", "checked_files", "details")
        if any(previous.get(key) != result.get(key) for key in stable_fields):
            raise ValueError("Existing prefix-import evidence differs") from None
    print(
        json.dumps(
            {key: result[key] for key in ("checked_stages", "checked_files", "copied", "existing")},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
