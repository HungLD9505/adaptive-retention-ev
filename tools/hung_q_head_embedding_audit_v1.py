"""Compare trained Hùng/Qyroven heads on pinned Development data only.

The mapping is a diagnostic functional embedding, not a method migration or parity approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZipFile

import torch

from experiments.hung_sprint2.model import ForecastGRU as HForecastGRU
from experiments.hung_sprint2.model import ModelConfig as HModelConfig

ROOT = Path(__file__).resolve().parents[1]
Q_MODEL_SHA = "c427576885c322c9d604573740a2174a5717ed0b41b98aff9142d3d9af5be7c4"
H_MODEL_SHA = "c8303d1c9e83ee4bdaf6f5ce6c3e520dc22ce95d51c442375ea8fa3e9879ef76"
INPUT_ZIP_SHA = "2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7"
TARGET_SHA = "ec244e11a68b334200e80c2f2abf28a54f5dd834e81b2dc92d58c90cf032c5ff"
TARGET_MANIFEST_SHA = "a36894bed2b2add2bc3356f840acfeeef906bf2199b7091b1509a81c8e0c60d6"
MANIFEST_SHA = "66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9"
BASE = "data/inputs/issue18-input-handoff-v1-20261019/urbanev-SZH-14d/"
IDENTITY = ["urbanev", "SZH", "1153"]
ORIGINS = 14


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _inside(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT.resolve()) or path.is_symlink():
        raise ValueError(f"Path outside repository or symlink: {path}")
    return resolved


def _member_rows(
    archive: ZipFile, member: str, manifest: dict, *, selected_origin: str | None = None
) -> list[dict]:
    expected = manifest["files"][member]
    digest = hashlib.sha256()
    size = 0
    selected = []
    with archive.open(BASE + member) as stream:
        for line in stream:
            digest.update(line)
            size += len(line)
            if b'"SZH", "1153"' in line and (
                selected_origin is None
                or (b'"origin": "' + selected_origin.encode() + b'"') in line
            ):
                row = json.loads(line)
                if row.get("identity") == IDENTITY:
                    selected.append(row)
    if digest.hexdigest() != expected["sha256"] or size != expected["size_bytes"]:
        raise ValueError(f"Input member bytes/SHA differ: {member}")
    return selected


def load_development_fixture(
    input_zip: Path,
) -> tuple[torch.Tensor, torch.Tensor, dict]:
    """Read pinned Development predictors without opening the label member."""
    if sha256_file(input_zip) != INPUT_ZIP_SHA:
        raise ValueError("Input ZIP fingerprint differs")
    with ZipFile(input_zip) as archive:
        manifest_bytes = archive.read(BASE + "manifest.json")
        if hashlib.sha256(manifest_bytes).hexdigest() != MANIFEST_SHA:
            raise ValueError("Input manifest fingerprint differs")
        manifest = json.loads(manifest_bytes)
        if manifest["run_id"] != "urbanev-SZH-14d":
            raise ValueError("Input run differs")
        entities = _member_rows(archive, "entities.jsonl", manifest)
        forecasts = _member_rows(archive, "forecasts.jsonl", manifest)[:ORIGINS]
    if (
        len(entities) != 1
        or entities[0]["role"] != "development"
        or entities[0]["status"] != "ready"
    ):
        raise ValueError("Target is not one ready Development entity")
    scale = entities[0]["scale"]["energy_scale"]
    scale_id = entities[0]["scale"]["fit_sha256"]
    if not isinstance(scale, (float, int)) or not math.isfinite(scale) or scale <= 0:
        raise ValueError("Invalid Development scale")
    origins = [row["origin"] for row in forecasts]
    if len(origins) != ORIGINS or len(set(origins)) != ORIGINS:
        raise ValueError("Forecast origin count/identity differs")
    starts = [datetime.fromisoformat(origin) for origin in origins]
    if any(b - a != timedelta(days=1) for a, b in zip(starts, starts[1:])):
        raise ValueError("Development origins are not consecutive days")
    if any(
        row["role"] != "development"
        or row["input_run_id"] != manifest["run_id"]
        or row["energy_scale"] != scale
        or row["scale_id"] != scale_id
        for row in forecasts
    ):
        raise ValueError("Forecast identity/scale differs")
    history = torch.tensor([row["x_hist"] for row in forecasts], dtype=torch.float32)
    calendar = torch.tensor([row["c_future"] for row in forecasts], dtype=torch.float32)
    if (
        history.shape != (ORIGINS, 24, 7)
        or calendar.shape != (ORIGINS, 24, 5)
        or not all(torch.isfinite(value).all() for value in (history, calendar))
    ):
        raise ValueError("Development tensor shape/value differs")
    return (
        history,
        calendar,
        {
            "entity_id": IDENTITY[-1],
            "origins": origins,
            "first_label_available_by": (starts[0] + timedelta(days=1)).isoformat(),
            "first_clock_mode": forecasts[0]["clock_mode"],
            "scale": scale,
            "scale_id": scale_id,
            "input_manifest_sha256": MANIFEST_SHA,
        },
    )


def read_arrived_first_label(input_zip: Path, fixture: dict) -> torch.Tensor:
    """Open the label member only after the initial static forecasts are computed."""
    with ZipFile(input_zip) as archive:
        manifest_bytes = archive.read(BASE + "manifest.json")
        if hashlib.sha256(manifest_bytes).hexdigest() != MANIFEST_SHA:
            raise ValueError("Input manifest changed before label access")
        labels = _member_rows(
            archive,
            "labels.jsonl",
            json.loads(manifest_bytes),
            selected_origin=fixture["origins"][0],
        )
    if len(labels) != 1:
        raise ValueError("First Development label is missing or duplicated")
    label = labels[0]
    arrivals = [datetime.fromisoformat(value) for value in label["available_at"]]
    as_of = datetime.fromisoformat(fixture["first_label_available_by"])
    if (
        label["identity"] != IDENTITY
        or label["origin"] != fixture["origins"][0]
        or label["clock_mode"] != fixture["first_clock_mode"]
        or len(arrivals) != 24
        or max(arrivals) > as_of
        or not all(label["file_valid"])
        or len(label["energy_kwh"]) != 24
        or not all(
            value is not None and math.isfinite(value) and value >= 0
            for value in label["energy_kwh"]
        )
    ):
        raise ValueError("First Development label is not complete and arrived by next day")
    target = torch.tensor(label["energy_kwh"], dtype=torch.float32).unsqueeze(0)
    target /= fixture["scale"]
    if target.shape != (1, 24) or not torch.isfinite(target).all():
        raise ValueError("Scaled Development label differs")
    return target


def embed_hung_head(hung: HForecastGRU, qyroven: torch.nn.Module) -> None:
    """Represent the trained Hùng function in Qyroven's 64-unit ReLU head.

    ReLU(a)-ReLU(-a)=a represents each of 24 latent output forms with 48
    units. Eight more units reproduce the calendar ReLUs; eight are unused.
    This mapping is not an optimizer-state or gradient-parameter bijection.
    """
    source = hung.forecast_head[0]
    calendar = hung.calendar_mlp[0]
    first, second = qyroven.head[0], qyroven.head[2]
    if (
        source.weight.shape != (24, 72)
        or calendar.weight.shape != (8, 120)
        or first.weight.shape != (64, 184)
        or second.weight.shape != (24, 64)
    ):
        raise ValueError("Forecast head shape differs from reviewed mapping")
    with torch.no_grad():
        qyroven.encoder.load_state_dict(hung.encoder.state_dict())
        first.weight.zero_()
        first.bias.zero_()
        second.weight.zero_()
        second.bias.copy_(source.bias)
        for output in range(24):
            first.weight[2 * output, :64].copy_(source.weight[output, :64])
            first.weight[2 * output + 1, :64].copy_(-source.weight[output, :64])
            second.weight[output, 2 * output] = 1
            second.weight[output, 2 * output + 1] = -1
        first.weight[48:56, 64:].copy_(calendar.weight)
        first.bias[48:56].copy_(calendar.bias)
        second.weight[:, 48:56].copy_(source.weight[:, 64:])


def audit(qyroven_root: Path, input_zip: Path, target_checkpoint: Path) -> dict:
    if sha256_file(ROOT / "experiments/hung_sprint2/model.py") != H_MODEL_SHA:
        raise ValueError("Hùng model code differs")
    if sha256_file(qyroven_root / "ev_models/model.py") != Q_MODEL_SHA:
        raise ValueError("Qyroven model code differs")
    if sha256_file(target_checkpoint) != TARGET_SHA:
        raise ValueError("Development Target checkpoint differs")
    manifest_path = target_checkpoint.with_name("run_manifest.json")
    if sha256_file(manifest_path) != TARGET_MANIFEST_SHA:
        raise ValueError("Development Target run manifest differs")
    run_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    state = torch.load(target_checkpoint, map_location="cpu", weights_only=True)
    binding = state["input_binding"]
    if (
        state["schema"] != "hung-sprint2-model-v1"
        or state["seed"] != 11
        or binding["stage"] != "target"
        or binding["entity_id"] != IDENTITY[-1]
        or binding["history_days"] != 14
        or binding["input_manifest_sha256"] != MANIFEST_SHA
        or state["training_step"] < 0
        or run_manifest["checkpoint_sha256"] != TARGET_SHA
        or run_manifest["input_binding"] != binding
        or run_manifest["code"]["executed_sources"]["experiments/hung_sprint2/model.py"]
        != H_MODEL_SHA
        or run_manifest["steps"] != state["training_step"]
        or run_manifest["status"] != "completed"
    ):
        raise ValueError("Development Target checkpoint binding differs")
    sys.path.insert(0, str(qyroven_root))
    from ev_models.model import ForecastGRU as QForecastGRU
    from ev_models.model import ModelConfig as QModelConfig

    if (
        Path(sys.modules[QForecastGRU.__module__].__file__).resolve()
        != qyroven_root / "ev_models/model.py"
    ):
        raise ValueError("Loaded Qyroven module differs from pinned source")

    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    hung = HForecastGRU(HModelConfig(calendar_hidden=8))
    hung.load_state_dict(state["model_state"])
    qyroven = QForecastGRU(QModelConfig(head_width=64))
    embed_hung_head(hung, qyroven)
    history, calendar, fixture = load_development_fixture(input_zip)
    if binding["scale_id"] != fixture["scale_id"]:
        raise ValueError("Target checkpoint scale differs from Development input")
    hung.eval()
    qyroven.eval()
    with torch.no_grad():
        initial_h = hung(history, calendar)
        initial_q = qyroven(history, calendar)
    initial_max = (initial_h - initial_q).abs().max().item()
    initial_mean = (initial_h - initial_q).abs().mean().item()
    if initial_max > 1e-6:
        raise ValueError("Initial trained-state forecast embedding is not numerically close")
    target = read_arrived_first_label(input_zip, fixture)
    hung_optimizer = torch.optim.Adam(hung.parameters(), lr=0.001)
    q_optimizer = torch.optim.Adam(qyroven.parameters(), lr=0.001)
    hung.train()
    qyroven.train()
    hung_optimizer.zero_grad(set_to_none=True)
    q_optimizer.zero_grad(set_to_none=True)
    hung_loss = (hung(history[:1], calendar[:1]) - target).abs().mean()
    q_loss = (qyroven(history[:1], calendar[:1]) - target).abs().mean()
    hung_loss.backward()
    q_loss.backward()
    encoder_grad_max = (
        (hung.encoder.weight_ih_l0.grad - qyroven.encoder.weight_ih_l0.grad).abs().max().item()
    )
    hung_optimizer.step()
    q_optimizer.step()
    hung.eval()
    qyroven.eval()
    with torch.no_grad():
        after_h = hung(history, calendar)
        after_q = qyroven(history, calendar)
    after_step_max = (after_h - after_q).abs().max().item()
    if after_step_max <= 1e-5:
        raise ValueError("Expected diagnostic one-step update divergence was not observed")
    return {
        "schema": "hung-q-head-embedding-audit-v1",
        "scope": "Development trained-state diagnostic; not execution or controller parity",
        "qyroven_model_sha256": Q_MODEL_SHA,
        "hung_model_sha256": H_MODEL_SHA,
        "input_zip_sha256": INPUT_ZIP_SHA,
        "target_checkpoint_sha256": TARGET_SHA,
        "target_run_manifest_sha256": TARGET_MANIFEST_SHA,
        "target_checkpoint_training_step": state["training_step"],
        "target_checkpoint_optimizer_slots": len(state["optimizer_state"].get("state", {})),
        "one_step_optimizer_setup": "fresh_Adam_0.001_for_both; saved_Hung_slots_not_transplanted",
        "fixture": fixture,
        "initial_forecasts_before_label_member_read": True,
        "hung_parameters": sum(value.numel() for value in hung.parameters()),
        "qyroven_parameters": sum(value.numel() for value in qyroven.parameters()),
        "mapped_hidden_units": {"latent_positive_negative": 48, "calendar": 8, "unused": 8},
        "initial_forecast_max_abs_difference_normalized": initial_max,
        "initial_forecast_mean_abs_difference_normalized": initial_mean,
        "one_step_forecast_loss_hung": hung_loss.item(),
        "one_step_forecast_loss_qyroven": q_loss.item(),
        "one_step_encoder_gradient_max_abs_difference": encoder_grad_max,
        "after_one_adam_step_forecast_max_abs_difference_normalized": after_step_max,
        "disposition": "INITIAL_FUNCTION_EMBEDDING_ONLY_NOT_TRAINED_UPDATE_PARITY",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qyroven-root", type=Path, required=True)
    parser.add_argument("--input-zip", type=Path, required=True)
    parser.add_argument("--target-checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = [
        _inside(value)
        for value in (args.qyroven_root, args.input_zip, args.target_checkpoint, args.output)
    ]
    output = paths[-1]
    if output.exists():
        raise FileExistsError(output)
    result = audit(*paths[:3])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            {
                "output": str(output),
                "sha256": sha256_file(output),
                "initial_max": result["initial_forecast_max_abs_difference_normalized"],
                "after_step_max": result[
                    "after_one_adam_step_forecast_max_abs_difference_normalized"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
