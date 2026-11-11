"""Strict CPU readback of retained issue99 model/Adam snapshots."""

import json
from pathlib import Path

import torch

from ev_models.model import ForecastGRU, ModelConfig


def check_branch(branch: dict) -> None:
    """Require compatible GRU weights and finite model/Adam state."""
    model = ForecastGRU(ModelConfig(branch["architecture"]["head_width"]))
    model.load_state_dict(branch["model"], strict=True)

    def finite(value):
        if isinstance(value, torch.Tensor):
            if not torch.isfinite(value).all():
                raise ValueError("Nonfinite retained model/optimizer tensor")
        elif isinstance(value, dict):
            for item in value.values():
                finite(item)
        elif isinstance(value, (tuple, list)):
            for item in value:
                finite(item)

    finite(branch["model"])
    finite(branch["optimizer"])
    if branch["steps"] < 0:
        raise ValueError("Negative retained optimizer step count")


def audit(root: Path) -> dict:
    """Decode the latest checkpoint after its byte commitments are verified."""
    torch.set_num_threads(1)
    checkpoints = models = 0
    for path in root.rglob("run.json"):
        report = json.loads(path.read_text())
        ticks = sorted(path.parent.glob("tick-*"))
        state = torch.load(ticks[-1] / "state.pt", map_location="cpu", weights_only=True)
        branches = [state["branch"]] if "branch" in state else list(state["branches"].values())
        for branch in branches:
            check_branch(branch)
            models += 1
        if "branch" in state:
            upper = report["binding"]["config"]["window_rule"]["upper_bound"]
            if not 0 <= state["current_lambda"] <= upper:
                raise ValueError("Retained controller coefficient outside registered bounds")
        checkpoints += 1
    return {
        "status": "PASS",
        "retained_checkpoints_read_back": checkpoints,
        "gru_model_states_loaded_strictly": models,
        "scope": "Latest-only snapshots, strict architecture and finite model/Adam tensors; byte commitments and forecast metrics are verified separately. No research-effectiveness claim.",
    }
