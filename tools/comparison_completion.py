"""Schedule and due-label completeness checks after replay identity authorization."""

from __future__ import annotations

import io
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from ev_models.checkpoint import digest as sha

if TYPE_CHECKING:
    from tools.verify_comparison import InputSnapshots


def _first_daily_tick(start: datetime, moment: datetime) -> datetime:
    """Return the first declared midnight at or after a label-availability time."""
    elapsed = (moment - start).total_seconds()
    return start + timedelta(days=math.ceil(elapsed / timedelta(days=1).total_seconds()))


def verify_complete_run(
    report: dict,
    input_root: Path,
    labels: dict,
    predictions: dict,
    forecast_ticks: dict,
    scored_at: dict,
    skipped_at: dict,
    tick_count: int,
    snapshots: InputSnapshots | None,
    *,
    target_role: str = "development",
) -> dict:
    """Bind a full run to its authenticated schedule and every due label outcome."""
    if target_role not in {"development", "final"}:
        raise ValueError("Unsupported verification target role")
    binding = report["binding"]["input"]
    runtime = report["binding"]["config"]
    days = runtime["replay_days"]
    if (
        type(days) is not int
        or days < 1
        or type(report["scheduled_days"]) is not int
        or report["scheduled_days"] != days
        or type(report["ticks"]) is not int
        or type(report.get("pending_days")) is not int
        or report["pending_days"] != 0
    ):
        raise ValueError("Incomplete or inconsistent declared replay horizon")
    if snapshots is None:
        manifest = json.loads((input_root / "manifest.json").read_bytes())
        schedule_path = input_root / "schedule.jsonl"
        expected = manifest["files"]["schedule.jsonl"]
        if (
            schedule_path.stat().st_size != expected["size_bytes"]
            or sha(schedule_path) != expected["sha256"]
        ):
            raise ValueError("Changed identified replay schedule")
        schedule_bytes = schedule_path.read_bytes()
    else:
        source = snapshots.sources[input_root.resolve(strict=True)]
        manifest = json.loads(source["raw"]["manifest.json"])
        schedule_bytes = source["raw"]["schedule.jsonl"]
    config = manifest["config"]
    start = datetime.fromisoformat(config["deployment"])
    delay = config["availability_delay_hours"]
    if (
        type(delay) is not int
        or delay < 0
        or binding["input_run_id"] != manifest["run_id"]
        or binding["dataset_id"] != config["dataset_id"]
        or binding["city_id"] != config["city_id"]
        or binding["history_days"] != config["history_days"]
        or start + days * timedelta(days=1) > datetime.fromisoformat(config["replay_stop"])
    ):
        raise ValueError("Replay config differs from identified input schedule")
    # The runner polls once at deployment, through the last issued horizon plus
    # the configured availability delay and one extra daily boundary.
    expected_ticks = days + delay // 24 + 2
    if tick_count != expected_ticks or report["ticks"] != tick_count:
        raise ValueError("Run stopped before the declared terminal daily tick")
    terminal = start + (tick_count - 1) * timedelta(days=1)
    identity = [binding["dataset_id"], binding["city_id"], binding["entity_id"]]
    prefix = ('{"identity": ' + json.dumps(identity) + ", ").encode()
    schedule = {}
    for line in io.BytesIO(schedule_bytes):
        if not line.startswith(prefix):
            continue
        row = json.loads(line)
        origin = row["origin"]
        if (
            origin in schedule
            or row["role"] != target_role
            or row["input_run_id"] != manifest["run_id"]
            or row["status"] not in {"created", "skipped_all_missing_history"}
        ):
            raise ValueError("Duplicate or invalid target schedule row")
        stamp = datetime.fromisoformat(origin)
        if start <= stamp < start + days * timedelta(days=1):
            schedule[origin] = row["status"]
    expected_origins = {(start + i * timedelta(days=1)).isoformat() for i in range(days)}
    if set(schedule) != expected_origins:
        raise ValueError("Incomplete identified target schedule")
    created = {origin for origin, status in schedule.items() if status == "created"}
    if set(predictions) != created:
        raise ValueError("Issued forecasts differ from the identified schedule")
    if any(
        forecast_ticks[origin] != (datetime.fromisoformat(origin) - start).days
        for origin in created
    ):
        raise ValueError("Issued forecast is stored at a different daily tick")
    expected_scored, expected_skipped = {}, {}
    for origin in created:
        label = labels.get(origin)
        if label is None or len(label["file_valid"]) != 24 or len(label["available_at"]) != 24:
            raise ValueError("Missing or invalid scheduled target labels")
        stamp = datetime.fromisoformat(origin)
        lower_bound = stamp + timedelta(days=1, hours=delay)
        availability = label["available_at"]
        if all(label["file_valid"]) and all(value is not None for value in availability):
            values = label["energy_kwh"]
            if len(values) != 24 or any(
                value is None or not math.isfinite(value) or value < 0 for value in values
            ):
                raise ValueError("Invalid complete scheduled target labels")
            due = _first_daily_tick(
                start,
                max(lower_bound, *(datetime.fromisoformat(value) for value in availability)),
            )
            expected_scored[origin] = due
        else:
            expected_skipped[origin] = _first_daily_tick(start, lower_bound)
    if any(due > terminal for due in (*expected_scored.values(), *expected_skipped.values())):
        raise ValueError("Declared terminal tick cannot account for all labels")
    for actual, expected, name in (
        (scored_at, expected_scored, "score"),
        (skipped_at, expected_skipped, "incomplete-label skip"),
    ):
        if set(actual) != set(expected) or any(
            datetime.fromisoformat(actual[origin][0]) != due
            or actual[origin][1] != (due - start).days
            for origin, due in expected.items()
        ):
            raise ValueError(f"Missing, extra or mistimed {name} event")
    return {
        "scheduled_days": days,
        "terminal_tick": terminal.isoformat(),
        "schedule_created_days": len(created),
        "complete_labels_scored": len(expected_scored),
        "incomplete_labels_skipped": len(expected_skipped),
    }
