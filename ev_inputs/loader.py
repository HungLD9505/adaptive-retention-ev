"""Integrate hourly IO, splits, prefix scales and windows for development validation."""

from __future__ import annotations

import hashlib
import json
import logging
import platform
import re
import subprocess
import time
from dataclasses import asdict, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

from ev_inputs.features import CONTRACT_COMMIT, CONTRACT_SHA256, SCHEMA_ID, _validate_clock
from ev_inputs.hourly_reader import read_entity, read_source, sha256_file, stage_hourly
from ev_inputs.scaling import EnergySample, fit_energy_scale, target_prefix_start
from ev_inputs.splits import SPLIT_POLICY, entity_role
from ev_inputs.windows import (
    ForecastInput,
    build_forecast_input,
    build_initial_training_example,
    build_label_record,
    initial_training_origins,
    scheduled_origins,
)

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)
REQUIRED_CONFIG = {
    "producer_manifest",
    "producer_manifest_sha256",
    "dataset_id",
    "city_id",
    "deployment",
    "replay_stop",
    "source_start",
    "history_days",
    "split_salt",
    "availability_delay_hours",
}


def _json(value: object) -> str:
    def encode(item: object) -> str:
        if isinstance(item, (datetime, Path)):
            return str(item) if isinstance(item, Path) else item.isoformat()
        raise TypeError(f"Not serializable: {type(item).__name__}")

    return json.dumps(value, default=encode, allow_nan=False, ensure_ascii=False)


def _code_identity() -> dict:
    files = sorted((ROOT / "ev_inputs").glob("*.py")) + [ROOT / "tools/model_inputs.py"]
    return {
        "commit": subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip(),
        "worktree_status": subprocess.check_output(
            ["git", "-C", str(ROOT), "status", "--porcelain"], text=True
        ).splitlines(),
        "executed_sources": {str(path.relative_to(ROOT)): sha256_file(path) for path in files},
    }


def run_inputs(config: dict, output: Path) -> dict:
    """Create a NEW development run. No official acceptance or training is performed.

    Config paths are explicit; the CLI resolves producer_manifest relative to its
    config file. Undefined scales are recorded for every affected entity and make
    the overall run incomplete, rather than silently excluding those entities.
    """
    if (
        not isinstance(config, dict)
        or not REQUIRED_CONFIG <= config.keys()
        or config.keys() - REQUIRED_CONFIG - {"entity_ids"}
    ):
        raise ValueError("Missing or unknown loader config fields")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}", output.name):
        raise ValueError("Unsafe run ID")
    delay = config["availability_delay_hours"]
    if isinstance(delay, bool) or not isinstance(delay, int) or delay < 0:
        raise ValueError("Availability delay must be a nonnegative integer")
    source = read_source(
        Path(config["producer_manifest"]),
        expected_manifest_sha256=config["producer_manifest_sha256"],
        dataset_id=config["dataset_id"],
        city_id=config["city_id"],
    )
    deployment, replay_stop, source_start = (
        datetime.fromisoformat(config[key]) for key in ("deployment", "replay_stop", "source_start")
    )
    for stamp in (deployment, replay_stop, source_start):
        _validate_clock(stamp, source.clock_mode)
        if stamp.utcoffset() != source.start.utcoffset() or stamp.hour:
            raise ValueError("Config must use local midnight and producer clock/offset")
    prefix = target_prefix_start(deployment, config["history_days"])
    if (
        not source.start <= source_start < deployment <= replay_stop <= source.stop
        or prefix < source.start
    ):
        raise ValueError("Fit/replay bounds must lie within the producer grid")
    # Validate salt even when an empty/broken producer will fail before role assignment.
    entity_role(source.dataset_id, source.city_id, "validation", salt=config["split_salt"])
    selected = config.get("entity_ids")
    if selected is not None and (
        not isinstance(selected, list)
        or not selected
        or any(not isinstance(x, str) or not x.strip() for x in selected)
        or len(set(selected)) != len(selected)
    ):
        raise ValueError("entity_ids must be unique nonempty strings")
    output = output.resolve()
    if (
        output.is_relative_to(source.manifest_path.parent)
        or source.manifest_path.parent.is_relative_to(output)
        or output.is_relative_to(ROOT / "data/raw")
        or any(output.parts[i : i + 2] == ("data", "raw") for i in range(len(output.parts) - 1))
    ):
        raise ValueError("Output must be separate from producer/raw storage")
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    manifest = {
        "schema": "ev-loader-run-v1",
        "feature_schema": SCHEMA_ID,
        "run_id": output.name,
        "status": "running",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "acceptance_scope": "development validation only; official inputs and #18 acceptance pending peer review",
        "strict_online_ready": False,
        "config": config,
        "config_sha256": hashlib.sha256(_json(config).encode("utf-8")).hexdigest(),
        "contract": {"commit": CONTRACT_COMMIT, "sha256": CONTRACT_SHA256},
        "split_policy": SPLIT_POLICY,
        "source": asdict(source),
        "availability_policy": "bin end plus explicit configured delay; unverified arrival assumption",
        "analysis_group": "shenzhen_later_period"
        if source.dataset_id == "charged" and source.city_id == "SZH"
        else "other_geographies"
        if source.dataset_id == "charged"
        else "primary_urbanev",
        "code": _code_identity(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "counts": {
            "source": 0,
            "development": 0,
            "final": 0,
            "undefined_scales": 0,
            "initial_candidates": 0,
            "initial_trainable": 0,
            "scheduled_forecasts": 0,
        },
    }
    connection = None
    index = output / "_hourly.sqlite"
    names = ("forecasts.jsonl", "labels.jsonl", "training.jsonl", "entities.jsonl")
    try:
        connection = stage_hourly(source, index)
        entities = [
            row[0]
            for row in connection.execute("SELECT DISTINCT entity FROM hourly ORDER BY entity")
        ]
        if selected is not None:
            if set(selected) - set(entities):
                raise ValueError("Requested entities are absent from producer inventory")
            entities = sorted(selected)
        with (
            (output / names[0]).open("x", encoding="utf-8") as forecasts,
            (output / names[1]).open("x", encoding="utf-8") as labels,
            (output / names[2]).open("x", encoding="utf-8") as training,
            (output / names[3]).open("x", encoding="utf-8") as summaries,
        ):
            for entity in entities:
                identity = (source.dataset_id, source.city_id, entity)
                role = entity_role(*identity, salt=config["split_salt"])
                manifest["counts"][role] += 1
                rows = read_entity(connection, source, entity, delay_hours=delay)
                by_time = {row.timestamp: row for row in rows}
                fit_start = source_start if role == "source" else prefix
                fit_rows = [row for row in rows if fit_start <= row.timestamp < deployment]
                available = [
                    row for row in fit_rows if row.file_valid and row.available_at <= deployment
                ]
                summary = {
                    "identity": identity,
                    "role": role,
                    "history_days": None if role == "source" else config["history_days"],
                    "fit_start": fit_start,
                    "cutoff": deployment,
                    "status": "ready",
                    "initial_candidates": 0,
                    "initial_trainable": 0,
                    "skipped_missing_labels": 0,
                    "skipped_delayed_labels": 0,
                    "scheduled_forecasts": 0,
                    "all_missing_replay_histories": 0,
                }
                if not available:
                    manifest["counts"]["undefined_scales"] += 1
                    summary.update(
                        status="undefined_scale",
                        reason="No valid available prefix energy; no fallback or automatic exclusion",
                    )
                    summaries.write(_json(summary) + "\n")
                    LOGGER.warning("Undefined scale for %s", identity)
                    continue
                scale = fit_energy_scale(
                    (
                        EnergySample(
                            row.timestamp, row.available_at, row.energy_kwh, row.file_valid
                        )
                        for row in fit_rows
                    ),
                    identity=identity,
                    start=fit_start,
                    cutoff=deployment,
                )
                summary["scale"] = asdict(scale)

                def forecast_at(origin: datetime) -> ForecastInput:
                    history = [by_time[origin - (24 - i) * HOUR] for i in range(24)]
                    return build_forecast_input(
                        history,
                        identity=identity,
                        origin=origin,
                        clock_mode=source.clock_mode,
                        energy_scale=scale.energy_scale,
                        scale_id=scale.fit_sha256,
                        input_run_id=output.name,
                    )

                def labels_at(origin: datetime):
                    return build_label_record(
                        [by_time[origin + i * HOUR] for i in range(24)],
                        identity=identity,
                        origin=origin,
                        clock_mode=source.clock_mode,
                    )

                for origin in initial_training_origins(
                    fit_start, deployment, clock_mode=source.clock_mode
                ):
                    summary["initial_candidates"] += 1
                    target = labels_at(origin)
                    example = build_initial_training_example(
                        forecast_at(origin), target, prefix_start=fit_start, cutoff=deployment
                    )
                    if example is None:
                        reason = (
                            "skipped_missing_labels"
                            if not all(target.file_valid)
                            else "skipped_delayed_labels"
                        )
                        summary[reason] += 1
                    else:
                        training.write(_json({"role": role, **asdict(example)}) + "\n")
                        summary["initial_trainable"] += 1
                if role != "source":
                    for origin in scheduled_origins(
                        deployment, replay_stop, clock_mode=source.clock_mode
                    ):
                        forecast = forecast_at(origin)
                        forecasts.write(_json({"role": role, **asdict(forecast)}) + "\n")
                        labels.write(_json(asdict(labels_at(origin))) + "\n")
                        summary["scheduled_forecasts"] += 1
                        summary["all_missing_replay_histories"] += all(
                            row[-1] == 0 for row in forecast.x_hist
                        )
                for key in ("initial_candidates", "initial_trainable", "scheduled_forecasts"):
                    manifest["counts"][key] += summary[key]
                summaries.write(_json(summary) + "\n")
        manifest["files"] = {
            name: {
                "sha256": sha256_file(output / name),
                "size_bytes": (output / name).stat().st_size,
            }
            for name in names
        }
        manifest["status"] = (
            "incomplete_undefined_scales"
            if manifest["counts"]["undefined_scales"]
            else "technical_success"
        )
    except BaseException as error:
        manifest.update(status="failed", error=str(error))
        raise
    finally:
        if connection is not None:
            connection.close()
        if index.exists():
            index.unlink()
        manifest["elapsed_seconds"] = time.perf_counter() - started
        with (output / "manifest.json").open("x", encoding="utf-8") as stream:
            stream.write(_json(manifest) + "\n")
    return manifest


def iter_forecasts(run: Path, *, expected_manifest_sha256: str) -> Iterator[dict]:
    """Stream predictor-only records from an identified successful development run.

    Consumers supply only x_hist/c_future to the model. Label files are not opened.
    This reader does not grant official research acceptance or implement a trainer.
    """
    if sha256_file(run / "manifest.json") != expected_manifest_sha256:
        raise ValueError("Input-run manifest fingerprint mismatch")
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    if (
        manifest["schema"] != "ev-loader-run-v1"
        or manifest["feature_schema"] != SCHEMA_ID
        or manifest["status"] != "technical_success"
    ):
        raise ValueError("Input run is not a successful supported development run")
    path = run / "forecasts.jsonl"
    if sha256_file(path) != manifest["files"][path.name]["sha256"]:
        raise ValueError("Forecast artifact fingerprint mismatch")
    expected = {field.name for field in fields(ForecastInput)} | {"role"}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            record = json.loads(line)
            if set(record) != expected:
                raise ValueError("Predictor record contains unexpected/missing fields")
            yield record
