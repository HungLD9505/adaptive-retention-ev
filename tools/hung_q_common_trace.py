"""Bounded same-input synthetic runner trace for two pinned implementations."""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--qyroven-root", required=True, type=Path)
parser.add_argument("--output-dir", required=True, type=Path)
args = parser.parse_args()
Q_ROOT = args.qyroven_root.resolve()
OUTPUT = args.output_dir.resolve()
if not Q_ROOT.is_relative_to(ROOT) or not OUTPUT.is_relative_to(ROOT):
    parser.error("Qyroven extraction and output must remain inside this repository")
if not (Q_ROOT / "ev_runner/engine.py").is_file():
    parser.error("Qyroven extraction is missing ev_runner/engine.py")
Q_REQUIRED_SHA256 = {
    "ev_runner/engine.py": "2028daf8e503a382788093bb53200feffc40c2742f722b31ae8a7e9273cb6976",
    "ev_control/confidence.py": "27b8d7709fc07442cc4461082e4d6599108ed70591f4398c5c5cc062980c7174",
    "ev_models/model.py": "c427576885c322c9d604573740a2174a5717ed0b41b98aff9142d3d9af5be7c4",
}
for relative_path, expected_sha256 in Q_REQUIRED_SHA256.items():
    if hashlib.sha256((Q_ROOT / relative_path).read_bytes()).hexdigest() != expected_sha256:
        parser.error(f"Qyroven extraction differs from pinned commit: {relative_path}")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Q_ROOT))

from ev_control.confidence import ControllerConfig as QControllerConfig  # noqa: E402
from ev_models.model import ForecastGRU as QForecastGRU  # noqa: E402
from ev_models.model import ModelConfig as QModelConfig  # noqa: E402
from ev_models.training import TrainingConfig, frozen_reference, seed_everything  # noqa: E402
from ev_runner.engine import DAY, Runner  # noqa: E402
from ev_runner.replay import Labels  # noqa: E402
from ev_runner.state import Branch, rng_state, state_digest  # noqa: E402
from ev_runner.store import Store  # noqa: E402
from experiments.supporting_pipeline.controller import ControllerConfig as HControllerConfig  # noqa: E402
from experiments.supporting_pipeline.model import ForecastGRU as HForecastGRU  # noqa: E402
from experiments.supporting_pipeline.model import ModelConfig as HModelConfig  # noqa: E402
from experiments.supporting_pipeline.retention import frozen_source_reference  # noqa: E402
from experiments.supporting_pipeline.runner import LabelArrival, Origin, PrequentialRunner  # noqa: E402


class CommonReplay:
    def __init__(self):
        self.start = datetime(2022, 12, 1, tzinfo=timezone(timedelta(hours=8)))
        self.stop = self.start + 2 * DAY
        self.scale_id = "fixture-scale"
        self.scale = 10.0
        self.accesses = []

    def forecast(self, origin):
        if not self.start <= origin < self.stop:
            return None
        return {
            "origin": origin.isoformat(),
            "x_hist": [[0.2, 0, 1, 0, 1, 0, 1] for _ in range(24)],
            "c_future": [[0, 1, 0, 1, 0] for _ in range(24)],
        }

    def labels(self, origin, as_of):
        self.accesses.append((origin.isoformat(), as_of.isoformat()))
        if as_of < origin + DAY:
            raise AssertionError("future label access")
        if origin == self.start + DAY:
            return Labels("incomplete", None, as_of)
        return Labels("complete", (4.0,) * 24, as_of)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    torch.set_num_threads(1)
    seed_everything(42)
    q_model = QForecastGRU(QModelConfig(64))
    h_model = HForecastGRU(HModelConfig(calendar_hidden=8))
    h_model.encoder.load_state_dict(q_model.encoder.state_dict())
    x = torch.tensor([[[0.2, 0, 1, 0, 1, 0, 1]] * 24], dtype=torch.float32)
    cal = torch.tensor([[[0, 1, 0, 1, 0]] * 24], dtype=torch.float32)
    encoder_before = max(
        (a - b).abs().max().item()
        for a, b in zip(
            q_model.encoder.state_dict().values(), h_model.encoder.state_dict().values()
        )
    )
    with torch.no_grad():
        initial_forecast_max_abs = (q_model(x, cal) - h_model(x, cal)).abs().max().item()
    q_reference = frozen_reference(q_model)
    h_reference = frozen_source_reference(h_model)
    q_controller = QControllerConfig(0.1, 0.2, 0.1, 2, 2, 100.0, 0.05, 1, 20, 42)
    h_controller = HControllerConfig(
        (0.0, 0.1, 0.2), 0.1, 2, 2, 100.0, 0.05, 1, 20, 42, "bonferroni_two"
    )
    q_training = TrainingConfig(42, 1, 64, 0.001, 0.001, 64)
    replay = CommonReplay()
    output = OUTPUT
    if output.exists():
        raise FileExistsError(output)
    output.mkdir()
    initial = Branch(q_model, torch.optim.Adam(q_model.parameters(), lr=0.001), rng_state())
    q_binding = {
        "config": "common-synthetic-fixture-v1",
        "source": state_digest(q_model.state_dict()),
    }
    q_runner = Runner(
        replay,
        initial,
        q_reference,
        torch.ones(64),
        q_controller,
        q_training,
        Store(output / "q", q_binding),
        device="cpu",
        stream_id="common-synthetic-fixture-v1",
    )
    h_binding = {
        "schema": "ev-checkpoint-input-binding-v1",
        "feature_schema": "ev-input-v1",
        "input_manifest_sha256": "a" * 64,
        "input_run_id": "common-synthetic-fixture-v1",
        "dataset_id": "urbanev",
        "city_id": "SZH",
        "stage": "target",
        "entity_id": "fixture-station",
        "history_days": 7,
        "scale_id": "fixture-scale",
        "source_checkpoint_sha256": "b" * 64,
    }
    h_runner = PrequentialRunner(
        h_model,
        torch.optim.Adam(h_model.parameters(), lr=0.001),
        h_reference,
        torch.ones(64),
        binding=h_binding,
        controller=h_controller,
        epsilon=0.001,
        energy_scale=10.0,
    )
    q_runner.run_until(replay.start + 2 * DAY)
    h_runner.forecast(Origin("day-0", 0, x, cal))
    h_runner.arrive(
        LabelArrival("day-0", True, torch.full((24,), 0.4), torch.ones(24, dtype=torch.bool))
    )
    h_runner.forecast(Origin("day-1", 1, x, cal))
    h_runner.arrive(LabelArrival("day-1", False))
    h_runner.finish_block()
    q_events = [
        json.loads(line)
        for path in sorted((output / "q").glob("tick-*/events.jsonl"))
        for line in path.read_text().splitlines()
    ]
    q_tags = [event["event"] for event in q_events]
    h_tags = list(h_runner.events)
    q_normalized = []
    for tag in q_tags:
        normalized = {"forecast_saved": "forecast", "skip_incomplete_labels": "unscored"}.get(
            tag, tag
        )
        if normalized != "update" or not q_normalized or q_normalized[-1] != "update":
            q_normalized.append(normalized)
    h_normalized = [tag.split(":", 1)[0] for tag in h_tags if tag != "fork:0"]
    if q_normalized != h_normalized:
        raise AssertionError(f"Chronological event mismatch: {q_normalized} != {h_normalized}")
    q_decision = q_runner.decisions[0]["selected_lambda"]
    h_decision = h_runner.decisions[0].selected_level
    if q_decision != h_decision or q_decision != 0.1:
        raise AssertionError("The low-information keep decision differs")
    q_post = q_runner.branches[0.1].model.encoder.state_dict()
    h_post = h_runner.candidates[1][0].encoder.state_dict()
    encoder_after = max(
        (a - b).abs().max().item() for a, b in zip(q_post.values(), h_post.values())
    )
    fixture_payload = {
        "x_hist": x.tolist(),
        "c_future": cal.tolist(),
        "day_0_label_kwh": [4.0] * 24,
        "day_1_label": "incomplete",
        "origin_start": replay.start.isoformat(),
    }
    result = {
        "scope": "synthetic_fixture_only",
        "q_commit": "83b877e16e7e690d93bb1f7736ce1870ef08fadd",
        "tool_sha256": digest(ROOT / "tools/hung_q_common_trace.py"),
        "q_code_sha256": digest(Q_ROOT / "ev_runner/engine.py"),
        "q_controller_sha256": digest(Q_ROOT / "ev_control/confidence.py"),
        "q_model_sha256": digest(Q_ROOT / "ev_models/model.py"),
        "h_code_sha256": digest(ROOT / "experiments/supporting_pipeline/runner.py"),
        "fixture_sha256": hashlib.sha256(
            json.dumps(fixture_payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "torch_version": torch.__version__,
        "device": "cpu",
        "fixture": "two daily origins, same predictor arrays, first day complete at next tick, second incomplete; initial lambda 0.1, Bmin 2, delta 100",
        "encoder_before_max_abs": encoder_before,
        "initial_forecast_max_abs": initial_forecast_max_abs,
        "encoder_after_one_update_max_abs": encoder_after,
        "q_events": q_tags,
        "h_events": h_tags,
        "normalized_events": q_normalized,
        "q_decision": q_decision,
        "h_decision": h_decision,
        "q_label_accesses": replay.accesses,
    }
    (output / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
