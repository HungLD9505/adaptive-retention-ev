"""Verified DATA-v1 Development replay for one target and initial budget."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

import torch

from ev_inputs.loader import iter_forecasts
from ev_inputs.windows import LabelRecord, ready_labels
from experiments.hung_sprint2.cli import _load_run
from experiments.hung_sprint2.runner import LabelArrival, Origin, PrequentialRunner


@dataclass(frozen=True)
class ReplaySummary:
    requested: int
    created: int
    skipped_all_missing_history: int
    skipped_undefined_scale: int
    scored: int
    delayed_or_incomplete: int


def _rows(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def _target_rows(path: Path, identity: list[str], role: str = "development") -> Iterator[dict]:
    for row in _rows(path):
        if row.get("identity") == identity and row.get("role", role) == role:
            yield row


def _label_record(row: dict, identity: list[str], origin: str) -> LabelRecord:
    if set(row) != {
        "identity", "origin", "clock_mode", "timestamps", "energy_kwh",
        "file_valid", "available_at",
    } or row["identity"] != identity or row["origin"] != origin:
        raise ValueError("Label identity/origin/schema mismatch")
    def parse(value: str | None) -> datetime | None:
        return None if value is None else datetime.fromisoformat(value)
    return LabelRecord(
        tuple(row["identity"]), datetime.fromisoformat(row["origin"]),
        row["clock_mode"], tuple(datetime.fromisoformat(x) for x in row["timestamps"]),
        tuple(row["energy_kwh"]), tuple(row["file_valid"]),
        tuple(parse(x) for x in row["available_at"]),
    )


def replay_target(
    input_run: Path,
    *,
    manifest_sha256: str,
    entity_id: str,
    runner: PrequentialRunner | None,
) -> ReplaySummary:
    """Replay the accepted schedule; parse each label only after forecasting.

    `as_of` is the exclusive horizon end for the accepted bin-end+0 profile.
    A later serialized availability time makes the day unscorable here. An
    undefined-scale target is returned as blocked coverage without a model.
    """
    input_run = Path(input_run).resolve()
    manifest = _load_run(input_run, manifest_sha256)
    identity = [manifest["config"]["dataset_id"], manifest["config"]["city_id"], entity_id]
    entities = list(_target_rows(input_run / "entities.jsonl", identity))
    if len(entities) != 1:
        raise ValueError("Development target identity is not unique in input run")
    entity = entities[0]
    schedule = list(_target_rows(input_run / "schedule.jsonl", identity))
    if not schedule:
        raise ValueError("Target has no requested replay origins")
    statuses = [row.get("status") for row in schedule]
    if any(status not in {"created", "skipped_all_missing_history", "skipped_undefined_scale"}
           for status in statuses):
        raise ValueError("Unknown schedule status")
    if any(row.get("input_run_id") != manifest["run_id"] for row in schedule):
        raise ValueError("Schedule input-run identity mismatch")
    origins = [datetime.fromisoformat(row["origin"]) for row in schedule]
    if any(later - earlier != timedelta(days=1)
           for earlier, later in zip(origins, origins[1:], strict=False)):
        raise ValueError("Target schedule is not consecutive daily origins")
    created = statuses.count("created")
    missing_history = statuses.count("skipped_all_missing_history")
    blocked = statuses.count("skipped_undefined_scale")
    if blocked:
        if blocked != len(schedule) or entity.get("initialization") != "blocked_undefined_scale":
            raise ValueError("Undefined-scale schedule/initialization mismatch")
        if any(_target_rows(input_run / "labels.jsonl", identity)) or any(
            row for row in iter_forecasts(input_run, expected_manifest_sha256=manifest_sha256)
            if row["role"] == "development" and row["identity"] == identity
        ):
            raise ValueError("Undefined-scale target has unexpected forecast/label records")
        if runner is not None:
            raise ValueError("Undefined-scale target cannot initialize a runner")
        return ReplaySummary(len(schedule), 0, 0, blocked, 0, 0)
    if runner is None:
        raise ValueError("A bound runner is required for defined-scale target")
    if entity.get("initialization") not in {"target_initial_adaptation", "source_checkpoint_only"}:
        raise ValueError("Unsupported target initialization")
    scale = entity.get("scale", {})
    binding = runner.binding
    if (
        binding["input_manifest_sha256"] != manifest_sha256
        or binding["input_run_id"] != manifest["run_id"]
        or [binding["dataset_id"], binding["city_id"], binding["entity_id"]] != identity
        or binding["history_days"] != manifest["config"]["history_days"]
        or binding["scale_id"] != scale.get("fit_sha256")
        or runner.energy_scale != scale.get("energy_scale")
    ):
        raise ValueError("Runner input binding/scale mismatch")
    if runner.next_index != 0:
        raise ValueError("This input adapter currently starts from the first origin")

    forecasts = (
        row for row in iter_forecasts(input_run, expected_manifest_sha256=manifest_sha256)
        if row["role"] == "development" and row["identity"] == identity
    )
    labels = _target_rows(input_run / "labels.jsonl", identity)
    scored = 0
    delayed = 0
    for index, scheduled in enumerate(schedule):
        if index and index % runner.controller.block_days == 0:
            runner.finish_block()
        origin_label = scheduled["origin"]
        if scheduled["status"] == "created":
            forecast = next(forecasts, None)
            if forecast is None or (
                forecast["origin"] != origin_label
                or forecast["input_run_id"] != manifest["run_id"]
                or forecast["scale_id"] != binding["scale_id"]
                or forecast["energy_scale"] != runner.energy_scale
            ):
                raise ValueError("Forecast identity/origin/scale mismatch")
            event = Origin(
                origin_label, index,
                torch.tensor(forecast["x_hist"], dtype=torch.float32).unsqueeze(0),
                torch.tensor(forecast["c_future"], dtype=torch.float32).unsqueeze(0),
            )
        else:
            event = Origin(origin_label, index, None, None, "skipped_all_missing_history")
        runner.forecast(event)
        # Labels are read and parsed only after all candidate forecasts persist.
        label_row = next(labels, None)
        record = _label_record(label_row, identity, origin_label) if label_row else None
        if record is None:
            raise ValueError("Created/skipped-history origin has no delayed-label record")
        if scheduled["status"] == "created" and record.clock_mode != forecast["clock_mode"]:
            raise ValueError("Forecast/label clock profile mismatch")
        ready = ready_labels(record, as_of=origins[index] + timedelta(days=1))
        if ready is None:
            runner.arrive(LabelArrival(origin_label, False))
            if scheduled["status"] == "created":
                delayed += 1
        else:
            if scheduled["status"] == "created":
                y_scaled = torch.tensor(ready, dtype=torch.float32) / runner.energy_scale
                runner.arrive(
                    LabelArrival(origin_label, True, y_scaled, torch.ones(24, dtype=torch.bool))
                )
                scored += 1
            else:
                runner.arrive(
                    LabelArrival(
                        origin_label, True,
                        torch.tensor(ready, dtype=torch.float32) / runner.energy_scale,
                        torch.ones(24, dtype=torch.bool),
                    )
                )
    if next(forecasts, None) is not None or next(labels, None) is not None:
        raise ValueError("Forecast/label artifacts have unmatched target records")
    if len(schedule) % runner.controller.block_days == 0:
        runner.finish_block()
    return ReplaySummary(len(schedule), created, missing_history, 0, scored, delayed)
