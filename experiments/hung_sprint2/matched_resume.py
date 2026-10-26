"""Fail-closed proof for resuming completed Development dispatcher stages."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from experiments.hung_sprint2 import dispatch_matched as dispatch

MARKER = "CODEX_VERIFIED_STAGE "


def _checkpoint_name(stage_name: str, method: str) -> str:
    if stage_name == "target-only-init":
        return "initial.pt"
    if stage_name == "target":
        return "target_checkpoint.pt"
    return "runner.pt" if method in dispatch.SINGLE_METHODS else "runner_checkpoint.pt"


def stage_receipt(
    stage_output: Path,
    stage_name: str,
    job_id: str,
    job: dict,
    cell: dict,
    config: dict,
    code: dict,
) -> dict:
    """Rehash a complete stage and check its input/method binding."""
    dispatch.verify_stage_output(stage_output, stage_name, job["method"], code)
    manifest_path = stage_output / "run_manifest.json"
    manifest_sha = dispatch.sha256_file(manifest_path)
    record = dispatch.read_verified_json(manifest_path, manifest_sha)
    binding = (
        record.get("binding") if stage_name == "target-only-init" else record.get("input_binding")
    )
    dispatch.require(
        isinstance(binding, dict)
        and binding.get("input_manifest_sha256") == cell["input_manifest_sha256"]
        and binding.get("entity_id") == cell["entity_id"],
        f"Completed stage input binding differs: {stage_output}",
    )
    if stage_name == "target-only-init":
        dispatch.require(
            record.get("method") == "target_only"
            and binding.get("seed") == cell["seed"]
            and record.get("training_steps")
            == (cell["entity"]["initial_trainable"] + config["target"]["batch_size"] - 1)
            // config["target"]["batch_size"],
            f"Completed target-only initialization differs: {stage_output}",
        )
    elif stage_name == "target":
        dispatch.require(
            record.get("seed") == cell["seed"]
            and binding.get("source_checkpoint_sha256") == job["source"]["sha256"]
            and record.get("retention_weight") == config["target"]["retention_weight"]
            and record.get("retention_kind", "latent")
            == config["target"].get("retention_kind", "latent")
            and record.get("initialization_kind", "source")
            == config["target"].get("initialization_kind", "source"),
            f"Completed target method/binding differs: {stage_output}",
        )
        dispatch.verify_target_schedule(
            record, config["target"], cell["entity"]["initial_trainable"]
        )
    else:
        limit = int(stage_name.removeprefix("replay-"))
        replay = record.get("config", {})
        expected_rule = job["method"]
        dispatch.require(
            record.get("runner_cursor") == limit
            and replay.get("max_origins") == limit
            and (
                replay.get("method") == expected_rule
                if job["method"] in dispatch.SINGLE_METHODS
                else replay.get("selection_rule", "confidence") == expected_rule
            )
            and (
                job["source"] is None
                or record.get("source_checkpoint_sha256") == job["source"]["sha256"]
            ),
            f"Completed replay method/cursor/source differs: {stage_output}",
        )
        if job["method"] not in dispatch.SINGLE_METHODS:
            target = job["target"]
            target_sha = (
                target["sha256"]
                if target is not None
                else dispatch.read_json(stage_output.parent / "target" / "run_manifest.json")[
                    "checkpoint_sha256"
                ]
            )
            dispatch.require(
                record.get("target_checkpoint_sha256") == target_sha,
                f"Completed replay target differs: {stage_output}",
            )
        journal = record.get(
            "forecast_journal" if job["method"] in dispatch.SINGLE_METHODS else "event_journal",
            {},
        )
        dispatch.require(
            isinstance(journal.get("file"), str) and journal["file"],
            f"Completed replay journal missing: {stage_output}",
        )
        dispatch.verify_file(stage_output / journal["file"], journal.get("sha256"))
    checkpoint_name = _checkpoint_name(stage_name, job["method"])
    checkpoint_sha = dispatch.sha256_file(stage_output / checkpoint_name)
    return {
        "job": job_id,
        "stage": stage_name,
        "manifest_sha256": manifest_sha,
        "checkpoint_sha256": checkpoint_sha,
        "code_commit": code["commit"],
    }


def append_receipt(log_path: Path, receipt: dict) -> None:
    body_sha = hashlib.sha256(log_path.read_bytes()).hexdigest()
    footer = json.dumps({**receipt, "log_body_sha256": body_sha}, sort_keys=True)
    with log_path.open("ab") as stream:
        stream.write(("\n" + MARKER + footer + "\n").encode("utf-8"))


def verify_completed_log(
    log_path: Path, command: list[str], config_sha: str, input_sha: str, receipt: dict
) -> None:
    dispatch.require(log_path.is_file(), f"Completed stage log missing: {log_path}")
    raw = log_path.read_bytes()
    delimiter = ("\n" + MARKER).encode("utf-8")
    marker_at = raw.rfind(delimiter)
    dispatch.require(marker_at >= 0 and raw.endswith(b"\n"), f"Stage log incomplete: {log_path}")
    body = raw[:marker_at]
    first_line = body.splitlines()[0]
    footer = json.loads(raw[marker_at + len(delimiter) :].decode("utf-8"))
    expected_header = {
        "command": command,
        "config_sha256": config_sha,
        "input_manifest_sha256": input_sha,
    }
    dispatch.require(
        json.loads(first_line) == expected_header
        and footer == {**receipt, "log_body_sha256": hashlib.sha256(body).hexdigest()},
        f"Completed stage log/receipt differs: {log_path}",
    )
