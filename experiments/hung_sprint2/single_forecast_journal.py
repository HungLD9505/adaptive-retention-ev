"""Durable issued forecasts, with independent checkpoint and schedule verification."""

from __future__ import annotations

import json
import math
import os
import shutil
from pathlib import Path

import torch

from ev_inputs.hourly_reader import sha256_file
from ev_inputs.windows import ready_labels
from experiments.hung_sprint2.cli import _load_run
from experiments.hung_sprint2.replay_inputs import _label_record, _target_rows

SCHEMA = "hung-single-forecast-journal-v1"


def _append(stream, record: dict) -> None:
    stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
    stream.flush()
    os.fsync(stream.fileno())


def start_journal(
    path: Path,
    binding: dict,
    code: dict,
    prior_output: Path | None = None,
    prior_records: list[dict] | None = None,
):
    stream = path.open("x", encoding="utf-8", newline="\n")
    _append(
        stream,
        {
            "schema": SCHEMA,
            "binding": binding,
            "code": code["executed_sources"],
            "start_index": 0,
            "start_event_index": 0,
        },
    )
    if prior_output is not None:
        if prior_records is None:
            raise ValueError("Prior forecast records are required")
        for record in prior_records:
            source = prior_output / record["checkpoint"]
            destination = path.parent / record["checkpoint"]
            with source.open("rb") as reader, destination.open("xb") as writer:
                shutil.copyfileobj(reader, writer)
                writer.flush()
                os.fsync(writer.fileno())
            if sha256_file(destination) != record["checkpoint_sha256"]:
                raise ValueError("Copied forecast checkpoint differs")
            _append(stream, record)
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
        "start_index": records[0].get("start_index"),
        "start_event_index": records[0].get("start_event_index"),
    }:
        raise ValueError("Forecast journal header/binding/code differs")
    start_index = records[0]["start_index"]
    start_event_index = records[0]["start_event_index"]
    if (
        not isinstance(start_index, int)
        or isinstance(start_index, bool)
        or start_index < 0
        or not isinstance(start_event_index, int)
        or isinstance(start_event_index, bool)
        or start_event_index < 0
    ):
        raise ValueError("Forecast journal start cursor differs")
    manifest = _load_run(input_run, binding["input_manifest_sha256"])
    identity = [binding[key] for key in ("dataset_id", "city_id", "entity_id")]
    schedule = list(_target_rows(input_run / "schedule.jsonl", identity))
    for expected_index, record in enumerate(records[1:], start=start_index):
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
            or index != expected_index
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
        issued_events = [
            event
            for event in state["events"][start_event_index:]
            if event.startswith(("forecast:", "skip:"))
        ]
        expected_events = [
            ("forecast:" if row["status"] == "created" else "skip:") + row["day_id"]
            for row in records[1 : expected_index - start_index + 2]
        ]
        if issued_events != expected_events:
            raise ValueError("Forecast journal omits an issued origin in snapshot")
    return records[1:]


def verify_final_runner(records: list[dict], state: dict, input_run: Path, binding: dict) -> None:
    """Bind a completed runner's exact predictions and scores to issued records."""
    cursor = state.get("next_index")
    if (
        not isinstance(cursor, int)
        or cursor != len(records)
        or state.get("pending") is not None
        or [row["index"] for row in records] != list(range(cursor))
    ):
        raise ValueError("Final runner/journal origin coverage differs")
    expected_events = [
        ("forecast:" if row["status"] == "created" else "skip:") + row["day_id"] for row in records
    ]
    issued_events = [event for event in state["events"] if event.startswith(("forecast:", "skip:"))]
    if issued_events != expected_events or state.get("seen_days") != [
        row["day_id"] for row in sorted(records, key=lambda row: row["day_id"])
    ]:
        raise ValueError("Final runner/journal issued events differ")
    created = [row for row in records if row["status"] == "created"]
    if len(state["issued"]) != len(created):
        raise ValueError("Final runner/journal forecast count differs")
    _load_run(input_run, binding["input_manifest_sha256"])
    identity = [binding[key] for key in ("dataset_id", "city_id", "entity_id")]
    labels = {
        row["origin"]: _label_record(row, identity, row["origin"])
        for row in _target_rows(input_run / "labels.jsonl", identity)
    }
    for forecast, issued in zip(created, state["issued"], strict=True):
        if (
            issued["index"] != forecast["index"]
            or issued["day_id"] != forecast["day_id"]
            or issued["prediction"].squeeze(0).tolist() != forecast["prediction"]
        ):
            raise ValueError("Final runner prediction differs from issued journal")
        label = issued["y_scaled"]
        if label is None:
            if issued["normalized_mae"] is not None or issued["mae_kwh"] is not None:
                raise ValueError("Unscored final origin carries a score")
            continue
        if label.shape != (24,) or not torch.isfinite(label).all():
            raise ValueError("Final runner label vector differs")
        record = labels.get(issued["day_id"])
        available = None if record is None else record.available_at
        if available is None or any(value is None for value in available):
            raise ValueError("Final runner scored label lacks authenticated arrival")
        source_values = ready_labels(record, as_of=max(available))
        if source_values is None or not torch.equal(
            label, torch.tensor(source_values, dtype=torch.float32) / state["energy_scale"]
        ):
            raise ValueError("Final runner label differs from authenticated Development input")
        mae = float(torch.abs(issued["prediction"].squeeze(0) - label).mean())
        if not isinstance(issued["normalized_mae"], (int, float)) or not isinstance(
            issued["mae_kwh"], (int, float)
        ):
            raise ValueError("Final runner score differs from issued forecast")
        if not math.isclose(
            issued["normalized_mae"], mae, rel_tol=0, abs_tol=1e-7
        ) or not math.isclose(
            issued["mae_kwh"], mae * state["energy_scale"], rel_tol=0, abs_tol=1e-7
        ):
            raise ValueError("Final runner score differs from issued forecast")
