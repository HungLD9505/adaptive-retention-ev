"""Verified DATA-v1 Development replay for one target and initial budget."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Iterator

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
    if (
        set(row)
        != {
            "identity",
            "origin",
            "clock_mode",
            "timestamps",
            "energy_kwh",
            "file_valid",
            "available_at",
        }
        or row["identity"] != identity
        or row["origin"] != origin
    ):
        raise ValueError("Label identity/origin/schema mismatch")

    def parse(value: str | None) -> datetime | None:
        return None if value is None else datetime.fromisoformat(value)

    return LabelRecord(
        tuple(row["identity"]),
        datetime.fromisoformat(row["origin"]),
        row["clock_mode"],
        tuple(datetime.fromisoformat(x) for x in row["timestamps"]),
        tuple(row["energy_kwh"]),
        tuple(row["file_valid"]),
        tuple(parse(x) for x in row["available_at"]),
    )


def replay_target(
    input_run: Path,
    *,
    manifest_sha256: str,
    entity_id: str,
    runner: PrequentialRunner | None,
    max_origins: int | None = None,
    event_sink: Callable[[int, str], None] | None = None,
    event_start_index: int = 0,
) -> ReplaySummary:
    """Replay the accepted schedule; parse each label only after forecasting.

    Deferred labels are delivered in availability order before subsequent
    forecasts, or at the final horizon end. A label still unavailable then
    remains unscored. An undefined-scale target returns blocked coverage.
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
    if max_origins is not None and (
        isinstance(max_origins, bool) or max_origins <= 0 or max_origins > len(schedule)
    ):
        raise ValueError("Replay origin limit must fit the requested schedule")
    statuses = [row.get("status") for row in schedule]
    if any(
        status not in {"created", "skipped_all_missing_history", "skipped_undefined_scale"}
        for status in statuses
    ):
        raise ValueError("Unknown schedule status")
    if any(row.get("input_run_id") != manifest["run_id"] for row in schedule):
        raise ValueError("Schedule input-run identity mismatch")
    origins = [datetime.fromisoformat(row["origin"]) for row in schedule]
    if any(
        later - earlier != timedelta(days=1)
        for earlier, later in zip(origins, origins[1:], strict=False)
    ):
        raise ValueError("Target schedule is not consecutive daily origins")
    created = statuses.count("created")
    missing_history = statuses.count("skipped_all_missing_history")
    blocked = statuses.count("skipped_undefined_scale")
    if blocked:
        if blocked != len(schedule) or entity.get("initialization") != "blocked_undefined_scale":
            raise ValueError("Undefined-scale schedule/initialization mismatch")
        if any(_target_rows(input_run / "labels.jsonl", identity)) or any(
            row
            for row in iter_forecasts(input_run, expected_manifest_sha256=manifest_sha256)
            if row["role"] == "development" and row["identity"] == identity
        ):
            raise ValueError("Undefined-scale target has unexpected forecast/label records")
        if runner is not None:
            raise ValueError("Undefined-scale target cannot initialize a runner")
        return ReplaySummary(len(schedule), 0, 0, blocked, 0, 0)
    if runner is None:
        raise ValueError("A bound runner is required for defined-scale target")
    if not 0 <= event_start_index <= len(runner.events):
        raise ValueError("Event journal start index is outside runner history")
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
    limit = len(schedule) if max_origins is None else max_origins
    if not 0 <= runner.next_index <= limit:
        raise ValueError("Runner cursor is outside the accepted schedule")
    if runner.next_index != runner.block_id * runner.controller.block_days + len(runner.days):
        raise ValueError("Runner block/cursor state is inconsistent")
    pending_index = runner.next_index if runner.pending is not None else None
    if pending_index is not None and (
        pending_index >= len(schedule)
        or runner.pending["day_id"] != schedule[pending_index]["origin"]
        or runner.pending["status"] != schedule[pending_index]["status"]
    ):
        raise ValueError("Runner pending origin differs from accepted schedule")
    issued_origins = [
        (index, row["origin"])
        for index, row in enumerate(schedule)
        if row["status"] == "created" and (index < runner.next_index or index == pending_index)
    ]
    if [(row["index"], row["day_id"]) for row in runner.issued] != issued_origins:
        raise ValueError("Runner issued forecasts differ from accepted schedule")
    prior_created = {origin for index, origin in issued_origins if index < runner.next_index}
    if not set(runner.late_pending).issubset(prior_created):
        raise ValueError("Runner deferred labels differ from accepted schedule")

    forecasts = (
        row
        for row in iter_forecasts(input_run, expected_manifest_sha256=manifest_sha256)
        if row["role"] == "development" and row["identity"] == identity
    )
    labels = _target_rows(input_run / "labels.jsonl", identity)
    late_records: dict[str, LabelRecord] = {}
    next_event_index = event_start_index

    def flush_events() -> None:
        nonlocal next_event_index
        if event_sink is not None:
            for event_index in range(next_event_index, len(runner.events)):
                event_sink(event_index, runner.events[event_index])
        next_event_index = len(runner.events)

    flush_events()

    def deliver_ready(as_of: datetime) -> None:
        # Ties retain origin order; updates occur before the next affected forecast.
        ready = sorted(
            (
                (
                    max(value for value in record.available_at if value is not None),
                    origin_label,
                    record,
                )
                for origin_label, record in late_records.items()
            ),
            key=lambda item: (item[0], item[1]),
        )
        for available_at, origin_label, record in ready:
            if available_at > as_of:
                break
            values = ready_labels(record, as_of=as_of)
            if values is None:
                raise ValueError("Deferred label became available without a complete horizon")
            runner.arrive(
                LabelArrival(
                    origin_label,
                    True,
                    torch.tensor(values, dtype=torch.float32) / runner.energy_scale,
                    torch.ones(24, dtype=torch.bool),
                )
            )
            flush_events()
            del late_records[origin_label]

    for index, scheduled in enumerate(schedule):
        if index == limit:
            break
        origin_label = scheduled["origin"]
        forecast = None
        if scheduled["status"] == "created":
            forecast = next(forecasts, None)
            if forecast is None or (
                forecast["origin"] != origin_label
                or forecast["input_run_id"] != manifest["run_id"]
                or forecast["scale_id"] != binding["scale_id"]
                or forecast["energy_scale"] != runner.energy_scale
            ):
                raise ValueError("Forecast identity/origin/scale mismatch")
        if index >= runner.next_index:
            if index != pending_index:
                deliver_ready(origins[index])
                if len(runner.days) == runner.controller.block_days:
                    runner.finish_block()
                    flush_events()
                if forecast is not None:
                    event = Origin(
                        origin_label,
                        index,
                        torch.tensor(forecast["x_hist"], dtype=torch.float32).unsqueeze(0),
                        torch.tensor(forecast["c_future"], dtype=torch.float32).unsqueeze(0),
                    )
                else:
                    event = Origin(origin_label, index, None, None, "skipped_all_missing_history")
                runner.forecast(event)
                flush_events()
        # A resumed prior origin was already forecast. New labels are parsed
        # only after the matching forecast or scheduled skip was persisted.
        label_row = next(labels, None)
        record = _label_record(label_row, identity, origin_label) if label_row else None
        if record is None:
            raise ValueError("Created/skipped-history origin has no delayed-label record")
        if scheduled["status"] == "created" and record.clock_mode != forecast["clock_mode"]:
            raise ValueError("Forecast/label clock profile mismatch")
        if index < runner.next_index:
            if origin_label in runner.late_pending:
                if not (
                    all(record.file_valid)
                    and all(value is not None for value in record.energy_kwh)
                    and all(value is not None for value in record.available_at)
                ):
                    raise ValueError("Runner deferred record is not potentially complete")
                late_records[origin_label] = record
            continue
        # Validate the serialized record, but deliver it only at a later event
        # boundary. This keeps update order aligned with label availability.
        ready_labels(record, as_of=origins[index] + timedelta(days=1))
        deferred = scheduled["status"] == "created" and (
            all(record.file_valid)
            and all(value is not None for value in record.energy_kwh)
            and all(value is not None for value in record.available_at)
        )
        runner.arrive(LabelArrival(origin_label, False, deferred=deferred))
        flush_events()
        if deferred:
            late_records[origin_label] = record
    if limit == len(schedule) and (
        next(forecasts, None) is not None or next(labels, None) is not None
    ):
        raise ValueError("Forecast/label artifacts have unmatched target records")
    if set(late_records) != set(runner.late_pending):
        raise ValueError("Runner deferred-label queue differs from replay inputs")
    if limit == len(schedule):
        deliver_ready(origins[-1] + timedelta(days=1))
    # A bounded replay may stop exactly at a block boundary. Leave its
    # decision pending until the next origin, after newly arrived labels have
    # been delivered, so split/resumed replay matches uninterrupted replay.
    if limit == len(schedule) and len(runner.days) == runner.controller.block_days:
        runner.finish_block()
        flush_events()
    scored = sum(row["normalized_mae"] is not None for row in runner.issued)
    if limit < len(schedule):
        created = statuses[:limit].count("created")
        missing_history = statuses[:limit].count("skipped_all_missing_history")
    return ReplaySummary(limit, created, missing_history, 0, scored, created - scored)
