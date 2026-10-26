"""Durable issued forecasts, with independent checkpoint and schedule verification."""

from __future__ import annotations

import json
import os
from pathlib import Path

import torch

from ev_inputs.hourly_reader import sha256_file
from experiments.hung_sprint2.cli import _load_run
from experiments.hung_sprint2.replay_inputs import _target_rows

SCHEMA = "hung-single-forecast-journal-v1"


def _append(stream, record: dict) -> None:
    stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
    stream.flush()
    os.fsync(stream.fileno())


def start_journal(path: Path, binding: dict, code: dict):
    stream = path.open("x", encoding="utf-8", newline="\n")
    _append(
        stream,
        {"schema": SCHEMA, "binding": binding, "code": code["executed_sources"]},
    )
    return stream


def append_forecast(stream, output: Path, runner, index: int, day_id: str, save_state) -> None:
    """Publish snapshot and forecast before replay may inspect this origin's label."""
    if runner.pending is None or runner.pending["index"] != index:
        raise ValueError("Forecast journal has no matching pending origin")
    checkpoint_name = f"forecast-{index:06d}.pt"
    digest = save_state(output / checkpoint_name, runner.state_dict())
    issued = next((row for row in runner.issued if row["index"] == index), None)
    _append(
        stream,
        {
            "index": index,
            "day_id": day_id,
            "status": runner.pending["status"],
            "prediction": None if issued is None else issued["prediction"].squeeze(0).tolist(),
            "checkpoint": checkpoint_name,
            "checkpoint_sha256": digest,
        },
    )


def verify_forecast_journal(output: Path, input_run: Path, binding: dict, code: dict) -> list[dict]:
    """Verify every immutable forecast against its snapshot and accepted schedule."""
    journal = output / "forecasts.jsonl"
    raw = journal.read_bytes()
    # A process/OS crash may tear the final append. A complete fsynced prefix
    # remains verifiable; the torn tail was never a committed issued forecast.
    lines = raw.split(b"\n")
    records = [json.loads(line) for line in lines[:-1] if line]
    if not records or records[0] != {
        "schema": SCHEMA,
        "binding": binding,
        "code": code["executed_sources"],
    }:
        raise ValueError("Forecast journal header/binding/code differs")
    manifest = _load_run(input_run, binding["input_manifest_sha256"])
    identity = [binding[key] for key in ("dataset_id", "city_id", "entity_id")]
    schedule = list(_target_rows(input_run / "schedule.jsonl", identity))
    previous = -1
    for record in records[1:]:
        if set(record) != {
            "index",
            "day_id",
            "status",
            "prediction",
            "checkpoint",
            "checkpoint_sha256",
        }:
            raise ValueError("Forecast journal row schema differs")
        index = record.get("index")
        if (
            not isinstance(index, int)
            or isinstance(index, bool)
            or index <= previous
            or index >= len(schedule)
        ):
            raise ValueError("Forecast journal origin order differs")
        scheduled = schedule[index]
        if (
            scheduled["input_run_id"] != manifest["run_id"]
            or record.get("day_id") != scheduled["origin"]
            or record.get("status") != scheduled["status"]
        ):
            raise ValueError("Forecast journal schedule identity differs")
        name = record.get("checkpoint")
        if name != f"forecast-{index:06d}.pt":
            raise ValueError("Forecast journal checkpoint name differs")
        path = output / name
        if sha256_file(path) != record.get("checkpoint_sha256"):
            raise ValueError("Forecast journal checkpoint hash differs")
        state = torch.load(path, map_location="cpu", weights_only=True)
        pending = state.get("pending")
        if (
            state.get("binding") != binding
            or state.get("next_index") != index
            or not isinstance(pending, dict)
            or pending.get("day_id") != record["day_id"]
            or pending.get("status") != record["status"]
            or not state.get("events")
            or state["events"][-1]
            != ("forecast:" if record["status"] == "created" else "skip:") + record["day_id"]
        ):
            raise ValueError("Forecast journal snapshot differs")
        issued = next((row for row in state["issued"] if row["index"] == index), None)
        if record["status"] == "created":
            if (
                issued is None
                or issued["normalized_mae"] is not None
                or issued["y_scaled"] is not None
                or issued["prediction"].squeeze(0).tolist() != record["prediction"]
            ):
                raise ValueError("Issued forecast was changed before label")
        elif issued is not None or record["prediction"] is not None:
            raise ValueError("Skipped origin carries a forecast")
        previous = index
    return records[1:]
