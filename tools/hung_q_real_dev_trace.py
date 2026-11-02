"""Bounded same-input Hùng/Qyroven trace on pinned real Development input bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZipFile

import torch

ROOT = Path(__file__).resolve().parents[1]
INPUT_SHA256 = "2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7"
Q_SHA256 = {
    "ev_runner/engine.py": "2028daf8e503a382788093bb53200feffc40c2742f722b31ae8a7e9273cb6976",
    "ev_control/confidence.py": "27b8d7709fc07442cc4461082e4d6599108ed70591f4398c5c5cc062980c7174",
    "ev_models/model.py": "c427576885c322c9d604573740a2174a5717ed0b41b98aff9142d3d9af5be7c4",
}
BASE = "data/inputs/issue18-input-handoff-v1-20261019/urbanev-SZH-7d/"
IDENTITY = ["urbanev", "SZH", "1001"]
DAYS = 14


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def selected_rows(archive: ZipFile, name: str, expected: dict) -> list[bytes]:
    """Hash a full member but retain only selected Development row bytes."""
    rows: list[bytes] = []
    digest = hashlib.sha256()
    size = 0
    with archive.open(BASE + name) as stream:
        for line in stream:
            digest.update(line)
            size += len(line)
            if b'"SZH", "1001"' in line:
                rows.append(line)
    if digest.hexdigest() != expected["sha256"] or size != expected["size_bytes"]:
        raise ValueError(f"Input member SHA/size mismatch: {name}")
    return rows


def load_input(archive_path: Path) -> tuple[dict, dict]:
    if sha256_file(archive_path) != INPUT_SHA256:
        raise ValueError("Input ZIP differs from pinned DATA-v1 release")
    with ZipFile(archive_path) as archive:
        manifest_bytes = archive.read(BASE + "manifest.json")
        manifest = json.loads(manifest_bytes)
        if (
            manifest["run_id"] != "urbanev-SZH-7d"
            or manifest["config"]["history_days"] != 7
            or manifest["config"]["dataset_id"] != "urbanev"
            or manifest["config"]["city_id"] != "SZH"
        ):
            raise ValueError("Input run identity differs")
        raw = {
            name: selected_rows(archive, name, manifest["files"][name])
            for name in ("entities.jsonl", "schedule.jsonl", "forecasts.jsonl", "labels.jsonl")
        }
    entities = [json.loads(row) for row in raw["entities.jsonl"]]
    if len(entities) != 1 or entities[0]["identity"] != IDENTITY:
        raise ValueError("Selected station is not unique")
    entity = entities[0]
    if entity["role"] != "development" or entity["status"] != "ready":
        raise ValueError("Selected station is not a ready Development target")
    scale = entity["scale"]["energy_scale"]
    scale_id = entity["scale"]["fit_sha256"]
    schedules = [json.loads(row) for row in raw["schedule.jsonl"][:DAYS]]
    forecasts = [json.loads(row) for row in raw["forecasts.jsonl"][:DAYS]]
    label_bytes = raw["labels.jsonl"][:DAYS]
    if not all(len(raw[name]) >= DAYS for name in raw if name != "entities.jsonl"):
        raise ValueError("Selected station lacks the planned origin rows")
    starts = [datetime.fromisoformat(row["origin"]) for row in schedules]
    if any(b - a != timedelta(days=1) for a, b in zip(starts, starts[1:])):
        raise ValueError("Selected schedule is not daily")
    for index, (schedule, forecast, label) in enumerate(
        zip(schedules, forecasts, label_bytes, strict=True)
    ):
        if (
            schedule["identity"] != IDENTITY
            or schedule["role"] != "development"
            or schedule["status"] != "created"
            or schedule["input_run_id"] != manifest["run_id"]
            or forecast["identity"] != IDENTITY
            or forecast["role"] != "development"
            or forecast["origin"] != schedule["origin"]
            or forecast["scale_id"] != scale_id
            or forecast["energy_scale"] != scale
            or forecast["input_run_id"] != manifest["run_id"]
            or not label.startswith(
                (
                    '{"identity": ["urbanev", "SZH", "1001"], "origin": "' + schedule["origin"]
                ).encode()
            )
        ):
            raise ValueError(f"Selected input identity/scale/order mismatch at {index}")
        x = torch.tensor(forecast["x_hist"], dtype=torch.float32)
        c = torch.tensor(forecast["c_future"], dtype=torch.float32)
        if (
            x.shape != (24, 7)
            or c.shape != (24, 5)
            or not torch.isfinite(x).all()
            or not torch.isfinite(c).all()
        ):
            raise ValueError(f"Selected predictor shape/value mismatch at {index}")
    return (
        {
            "zip_sha256": INPUT_SHA256,
            "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "member_sha256": {name: manifest["files"][name]["sha256"] for name in raw},
            "input_run_id": manifest["run_id"],
            "entity_id": IDENTITY[-1],
            "origins": [row["origin"] for row in schedules],
            "scale": scale,
            "scale_id": scale_id,
            "selected_14_row_sha256": {
                name: hashlib.sha256(b"".join(raw[name][:DAYS])).hexdigest()
                for name in ("schedule.jsonl", "forecasts.jsonl", "labels.jsonl")
            },
        },
        {"forecasts": forecasts, "labels_raw": label_bytes},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qyroven-root", type=Path, required=True)
    parser.add_argument("--input-zip", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    q_root = args.qyroven_root.resolve()
    input_zip = args.input_zip.resolve()
    output = args.output_dir.resolve()
    if any(not p.is_relative_to(ROOT) for p in (q_root, input_zip, output)):
        parser.error("All paths must remain inside this repository")
    if output.exists():
        raise FileExistsError(output)
    for relative, expected in Q_SHA256.items():
        if sha256_file(q_root / relative) != expected:
            raise ValueError(f"Qyroven code differs from pinned commit: {relative}")
    identity, rows = load_input(input_zip)
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(q_root))

    from ev_control.confidence import ControllerConfig as QControllerConfig
    from ev_models.model import ForecastGRU as QForecastGRU
    from ev_models.model import ModelConfig as QModelConfig
    from ev_models.training import TrainingConfig, frozen_reference, seed_everything
    from ev_runner.engine import DAY, Runner
    from ev_runner.replay import Labels
    from ev_runner.state import Branch, rng_state, state_digest
    from ev_runner.store import Store
    from experiments.supporting_pipeline.controller import ControllerConfig as HControllerConfig
    from experiments.supporting_pipeline.model import ForecastGRU as HForecastGRU
    from experiments.supporting_pipeline.model import ModelConfig as HModelConfig
    from experiments.supporting_pipeline.retention import frozen_source_reference
    from experiments.supporting_pipeline.runner import LabelArrival, Origin, PrequentialRunner

    class RealReplay:
        def __init__(self) -> None:
            self.start = datetime.fromisoformat(identity["origins"][0])
            self.stop = self.start + DAYS * DAY
            self.scale = identity["scale"]
            self.scale_id = identity["scale_id"]
            self.by_origin = dict(zip(identity["origins"], rows["forecasts"], strict=True))
            self.raw_label = dict(zip(identity["origins"], rows["labels_raw"], strict=True))
            self.accesses: list[dict] = []

        def forecast(self, origin: datetime) -> dict | None:
            row = self.by_origin.get(origin.isoformat())
            if row is None:
                return None
            return {"origin": row["origin"], "x_hist": row["x_hist"], "c_future": row["c_future"]}

        def labels(self, origin: datetime, as_of: datetime) -> Labels:
            if as_of < origin + DAY:
                self.accesses.append(
                    {"origin": origin.isoformat(), "as_of": as_of.isoformat(), "status": "pending"}
                )
                return Labels("pending", None, origin + DAY)
            row = json.loads(self.raw_label[origin.isoformat()])
            if (
                row["identity"] != IDENTITY
                or row["origin"] != origin.isoformat()
                or row["clock_mode"] != self.by_origin[origin.isoformat()]["clock_mode"]
            ):
                raise ValueError("Late label identity differs")
            arrivals = [
                datetime.fromisoformat(v) if v is not None else None for v in row["available_at"]
            ]
            complete = (
                len(row["energy_kwh"]) == len(row["file_valid"]) == len(arrivals) == 24
                and all(row["file_valid"])
                and all(v is not None and math.isfinite(v) and v >= 0 for v in row["energy_kwh"])
                and all(v is not None for v in arrivals)
            )
            if not complete:
                status = "incomplete"
                outcome = Labels(status, None, as_of)
            elif max(arrivals) > as_of:
                status = "pending"
                outcome = Labels(status, None, max(arrivals))
            else:
                status = "complete"
                outcome = Labels(status, tuple(row["energy_kwh"]), max(arrivals))
            self.accesses.append(
                {"origin": origin.isoformat(), "as_of": as_of.isoformat(), "status": status}
            )
            return outcome

    torch.set_num_threads(1)
    seed_everything(7)
    q_model = QForecastGRU(QModelConfig(64))
    h_model = HForecastGRU(HModelConfig(calendar_hidden=8))
    h_model.encoder.load_state_dict(q_model.encoder.state_dict())
    encoder_before = max(
        (a - b).abs().max().item()
        for a, b in zip(
            q_model.encoder.state_dict().values(),
            h_model.encoder.state_dict().values(),
            strict=True,
        )
    )
    q_reference = frozen_reference(q_model)
    h_reference = frozen_source_reference(h_model)
    q_controller = QControllerConfig(0.1, 0.2, 0.0, 14, 5, 0.0, 0.05, 2, 100, 7)
    h_controller = HControllerConfig(
        (0.0, 0.1, 0.2), 0.0, 14, 5, 0.0, 0.05, 2, 100, 7, "bonferroni_two"
    )
    q_training = TrainingConfig(7, 1, 64, 0.001, 0.000001, 64)
    replay = RealReplay()
    output.mkdir()
    torch.save(h_model.state_dict(), output / "h_initial_state.pt")
    h_binding = {
        "schema": "ev-checkpoint-input-binding-v1",
        "feature_schema": "ev-input-v1",
        "input_manifest_sha256": identity["manifest_sha256"],
        "input_run_id": identity["input_run_id"],
        "dataset_id": "urbanev",
        "city_id": "SZH",
        "stage": "target",
        "entity_id": IDENTITY[-1],
        "history_days": 7,
        "scale_id": identity["scale_id"],
        "source_checkpoint_sha256": sha256_file(output / "h_initial_state.pt"),
    }
    q_runner = Runner(
        replay,
        Branch(q_model, torch.optim.Adam(q_model.parameters(), lr=0.001), rng_state()),
        q_reference,
        torch.ones(64),
        q_controller,
        q_training,
        Store(
            output / "q",
            {"input": identity["manifest_sha256"], "source": state_digest(q_model.state_dict())},
        ),
        device="cpu",
        stream_id="common-real-dev-input-v1",
    )
    h_runner = PrequentialRunner(
        h_model,
        torch.optim.Adam(h_model.parameters(), lr=0.001),
        h_reference,
        torch.ones(64),
        binding=h_binding,
        controller=h_controller,
        epsilon=0.000001,
        energy_scale=identity["scale"],
    )
    q_runner.run_until(replay.stop)
    q_accesses = list(replay.accesses)
    if len(q_accesses) != DAYS or any(
        item["status"] != "complete"
        or datetime.fromisoformat(item["as_of"]) != datetime.fromisoformat(item["origin"]) + DAY
        for item in q_accesses
    ):
        raise AssertionError("Qyroven label access differs from next-day complete-label gate")
    h_accesses: list[dict] = []
    for index, row in enumerate(rows["forecasts"]):
        origin = datetime.fromisoformat(row["origin"])
        if index:
            previous = datetime.fromisoformat(rows["forecasts"][index - 1]["origin"])
            outcome = replay.labels(previous, origin)
            h_accesses.append(replay.accesses[-1])
            if outcome.status != "complete":
                raise ValueError("Selected real Development label is not complete on next day")
            h_runner.arrive(
                LabelArrival(
                    previous.isoformat(),
                    True,
                    torch.tensor(outcome.values, dtype=torch.float32) / replay.scale,
                    torch.ones(24, dtype=torch.bool),
                )
            )
        h_runner.forecast(
            Origin(
                row["origin"],
                index,
                torch.tensor(row["x_hist"], dtype=torch.float32).unsqueeze(0),
                torch.tensor(row["c_future"], dtype=torch.float32).unsqueeze(0),
            )
        )
        h_runner.arrive(LabelArrival(row["origin"], False, deferred=True))
    last = datetime.fromisoformat(rows["forecasts"][-1]["origin"])
    outcome = replay.labels(last, replay.stop)
    h_accesses.append(replay.accesses[-1])
    if outcome.status != "complete":
        raise ValueError("Final selected Development label is not complete at block boundary")
    if h_accesses != q_accesses:
        raise AssertionError("Runner label access schedules differ")
    h_runner.arrive(
        LabelArrival(
            last.isoformat(),
            True,
            torch.tensor(outcome.values, dtype=torch.float32) / replay.scale,
            torch.ones(24, dtype=torch.bool),
        )
    )
    h_decision = h_runner.finish_block()
    q_events = [
        json.loads(line)
        for path in sorted((output / "q").glob("tick-*/events.jsonl"))
        for line in path.read_text().splitlines()
    ]
    q_tags = [item["event"] for item in q_events]
    h_tags = list(h_runner.events)
    q_core: list[str] = []
    for tag in q_tags:
        name = {"forecast_saved": "forecast"}.get(tag, tag)
        if name in {"forecast", "score", "update", "decision", "fork"} and not (
            name == "update" and q_core and q_core[-1] == "update"
        ):
            q_core.append(name)
    h_core = [
        tag.split(":", 1)[0]
        for tag in h_tags
        if tag.split(":", 1)[0] in {"forecast", "score", "update", "decision", "fork"}
        and tag != "fork:0"
    ]
    if q_core != h_core:
        raise AssertionError("Core causal chronology differs")
    diffs = []
    for index, issued in enumerate(h_runner.issued):
        q_forecast = json.loads((output / "q" / f"tick-{index:04d}" / "forecasts.json").read_text())
        if q_forecast["origin"] != issued["day_id"]:
            raise AssertionError("Saved forecast origin differs")
        values = [
            max(abs(a - b) for a, b in zip(q_values, h_values.squeeze(0).tolist(), strict=True))
            for q_values, h_values in zip(
                q_forecast["predictions"], issued["forecasts"], strict=True
            )
        ]
        diffs.append({"origin": issued["day_id"], "max_abs_by_level": values})
    q_post = q_runner.branches[q_runner.active].model.encoder.state_dict()
    h_post = h_runner.active_model.encoder.state_dict()
    encoder_after = max(
        (a - b).abs().max().item() for a, b in zip(q_post.values(), h_post.values(), strict=True)
    )
    result = {
        "schema": "hung-q-real-development-input-trace-v2",
        "scope": "bounded_14_origin_real_development_input_with_random_untrained_models",
        "q_commit": "83b877e16e7e690d93bb1f7736ce1870ef08fadd",
        "q_sha256": Q_SHA256,
        "h_runner_sha256": sha256_file(ROOT / "experiments/supporting_pipeline/runner.py"),
        "tool_sha256": sha256_file(ROOT / "tools/hung_q_real_dev_trace.py"),
        "input": identity,
        "initial_state_sha256": sha256_file(output / "h_initial_state.pt"),
        "torch_version": torch.__version__,
        "device": "cpu",
        "configuration": {
            "seed": 7,
            "levels": [0, 0.1, 0.2],
            "initial_level": 0,
            "block_days": 14,
            "min_complete_days": 5,
            "delta": 0,
            "alpha": 0.05,
            "segment_days": 2,
            "resamples": 100,
            "learning_rate": 0.001,
            "epsilon": 0.000001,
        },
        "encoder_before_max_abs": encoder_before,
        "forecast_max_abs_by_origin": diffs,
        "forecast_max_abs_all": max(max(row["max_abs_by_level"]) for row in diffs),
        "encoder_after_block_max_abs": encoder_after,
        "q_events": q_tags,
        "h_events": h_tags,
        "normalized_core_events": q_core,
        "q_decision": q_runner.decisions[0],
        "h_decision": asdict(h_decision),
        "q_label_accesses": q_accesses,
        "h_label_accesses": h_accesses,
        "limitations": [
            "Random untrained heads differ; no executed Source/Target checkpoint parity",
            "Not a full 90-origin real-input trajectory or resume test",
            "Observed controller outcome cannot choose the architecture or Final settings",
        ],
    }
    (output / "result.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            {
                "status": "completed",
                "output": str(output / "result.json"),
                "forecast_max_abs_all": result["forecast_max_abs_all"],
                "q_selected": result["q_decision"]["selected_lambda"],
                "h_selected": h_decision.selected_level,
            }
        )
    )


if __name__ == "__main__":
    main()
