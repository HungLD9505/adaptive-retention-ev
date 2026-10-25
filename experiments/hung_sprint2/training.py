"""Small source/target training primitives and bound #19 checkpoints."""

from __future__ import annotations

import os
import re
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import torch
from torch import Tensor

from experiments.hung_sprint2._create_only import publish_create_only
from experiments.hung_sprint2.model import ForecastGRU, ModelConfig
from experiments.hung_sprint2.retention import (
    frozen_source_reference,
    retention_loss,
    validate_latent_scale,
)

BINDING_FIELDS = {
    "schema",
    "feature_schema",
    "input_manifest_sha256",
    "input_run_id",
    "dataset_id",
    "city_id",
    "stage",
    "entity_id",
    "history_days",
    "scale_id",
    "source_checkpoint_sha256",
}
CHECKPOINT_SCHEMA = "hung-sprint2-model-v1"


def _checkpoint_rng(model: ForecastGRU) -> dict:
    """Capture PyTorch RNGs without changing the transfer-loading default."""
    devices = []
    cuda_states = []
    if torch.cuda.is_available():
        cuda_states = [state.clone() for state in torch.cuda.get_rng_state_all()]
        devices = [
            {
                "name": torch.cuda.get_device_name(index),
                "capability": list(torch.cuda.get_device_capability(index)),
            }
            for index in range(len(cuda_states))
        ]
    return {
        "schema": "hung-sprint2-model-rng-v1",
        "torch_version": str(torch.__version__),
        "model_device": str(next(model.parameters()).device),
        "cpu": torch.get_rng_state().clone(),
        "cuda": cuda_states,
        "cuda_devices": devices,
        "cuda_runtime": torch.version.cuda,
    }


def _validated_checkpoint_rng(payload: dict, device: torch.device) -> dict:
    """Reject missing/incompatible RNG snapshots before restoring any state."""
    rng = payload.get("rng_state")
    if not isinstance(rng, dict) or rng.get("schema") != "hung-sprint2-model-rng-v1":
        raise ValueError("Checkpoint has no supported RNG state; exact RNG resume is unavailable")
    if rng.get("torch_version") != str(torch.__version__):
        raise ValueError("Checkpoint RNG PyTorch version mismatch")
    saved_device = torch.device(rng["model_device"])
    if saved_device.type != device.type:
        raise ValueError("Checkpoint RNG device type mismatch")
    cpu, cuda, devices = rng.get("cpu"), rng.get("cuda"), rng.get("cuda_devices")
    if not isinstance(cuda, list) or not isinstance(devices, list) or len(cuda) != len(devices):
        raise ValueError("Invalid checkpoint CUDA RNG metadata")
    if any(
        not isinstance(state, Tensor)
        or state.dtype != torch.uint8
        or state.ndim != 1
        or not state.numel()
        for state in [cpu, *cuda]
    ):
        raise ValueError("Invalid checkpoint RNG tensor")
    if saved_device.type == "cuda" and not cuda:
        raise ValueError("Checkpoint CUDA RNG state is missing")
    if cuda:
        if not torch.cuda.is_available():
            raise ValueError("CUDA is unavailable for checkpoint RNG restoration")
        if len(cuda) != torch.cuda.device_count() or rng.get("cuda_runtime") != torch.version.cuda:
            raise ValueError("Checkpoint CUDA RNG environment mismatch")
        actual_devices = [
            {
                "name": torch.cuda.get_device_name(index),
                "capability": list(torch.cuda.get_device_capability(index)),
            }
            for index in range(len(cuda))
        ]
        if devices != actual_devices:
            raise ValueError("Checkpoint CUDA RNG device metadata mismatch")
        if saved_device.type == "cuda":
            requested_index = device.index
            if requested_index is None:
                requested_index = torch.cuda.current_device()
            if saved_device.index != requested_index:
                raise ValueError("Checkpoint CUDA RNG device index mismatch")
    return rng


@dataclass(frozen=True)
class StepLoss:
    forecast: float
    retention: float
    total: float


def forecast_mae(forecast: Tensor, y_scaled: Tensor) -> Tensor:
    """Mean absolute scaled error over complete 24-hour samples and the batch."""
    if forecast.ndim != 2 or forecast.shape[1] != 24 or forecast.shape[0] == 0:
        raise ValueError("Forecast must have shape [nonempty B,24]")
    if y_scaled.shape != forecast.shape:
        raise ValueError("All 24 target labels are required for every forecast")
    if not forecast.is_floating_point() or not y_scaled.is_floating_point():
        raise ValueError("Forecast and labels must be floating-point")
    if not torch.isfinite(forecast).all() or not torch.isfinite(y_scaled).all():
        raise ValueError("Forecast and labels must be finite")
    if torch.any(y_scaled < 0):
        raise ValueError("Energy labels cannot be negative")
    return torch.abs(forecast - y_scaled).mean()


def initialize_target(
    source: ForecastGRU, *, learning_rate: float
) -> tuple[ForecastGRU, ForecastGRU, torch.optim.Adam]:
    """Make independent trainable target and frozen reference from one source."""
    if not 0 < learning_rate < float("inf"):
        raise ValueError("learning_rate must be finite and positive")
    target = deepcopy(source)
    reference = frozen_source_reference(source)
    target.encoder.flatten_parameters()
    reference.encoder.flatten_parameters()
    optimizer = torch.optim.Adam(target.parameters(), lr=learning_rate)
    return target, reference, optimizer


def source_step(
    model: ForecastGRU,
    optimizer: torch.optim.Optimizer,
    x_hist: Tensor,
    c_future: Tensor,
    y_scaled: Tensor,
) -> StepLoss:
    model.train()
    optimizer.zero_grad(set_to_none=True)
    forecast = model(x_hist, c_future)
    loss = forecast_mae(forecast, y_scaled)
    if not torch.isfinite(loss):
        raise ValueError("Source loss is not finite; optimizer step was skipped")
    loss.backward()
    if any(
        parameter.grad is not None and not torch.isfinite(parameter.grad).all()
        for parameter in model.parameters()
    ):
        optimizer.zero_grad(set_to_none=True)
        raise ValueError("Source gradient is not finite; optimizer step was skipped")
    optimizer.step()
    value = float(loss.detach())
    return StepLoss(forecast=value, retention=0.0, total=value)


def target_step(
    target: ForecastGRU,
    reference: ForecastGRU,
    optimizer: torch.optim.Optimizer,
    x_hist: Tensor,
    c_future: Tensor,
    y_scaled: Tensor,
    *,
    retention_weight: float,
    latent_scale: Tensor | None,
    epsilon: float,
) -> StepLoss:
    """Use identical target-normalized X for the target and frozen source."""
    if not 0 <= retention_weight < float("inf"):
        raise ValueError("retention_weight must be finite and nonnegative")
    target.train()
    reference.eval()
    if any(parameter.requires_grad for parameter in reference.parameters()):
        raise ValueError("Reference encoder must be frozen")
    optimizer.zero_grad(set_to_none=True)
    forecast, target_latent = target.forecast_and_latent(x_hist, c_future)
    forecast_loss = forecast_mae(forecast, y_scaled)
    if retention_weight > 0:
        if latent_scale is None:
            raise ValueError("A fixed source-training latent scale is required")
        with torch.no_grad():
            source_latent = reference.encode(x_hist)
        keep_loss = retention_loss(target_latent, source_latent, latent_scale, epsilon=epsilon)
    else:
        keep_loss = forecast_loss.new_zeros(())
    total_loss = forecast_loss + retention_weight * keep_loss
    if not torch.isfinite(total_loss):
        raise ValueError("Target loss is not finite; optimizer step was skipped")
    total_loss.backward()
    if any(
        parameter.grad is not None and not torch.isfinite(parameter.grad).all()
        for parameter in target.parameters()
    ):
        optimizer.zero_grad(set_to_none=True)
        raise ValueError("Target gradient is not finite; optimizer step was skipped")
    optimizer.step()
    return StepLoss(
        forecast=float(forecast_loss.detach()),
        retention=float(keep_loss.detach()),
        total=float(total_loss.detach()),
    )


def validate_binding(binding: dict) -> None:
    """Validate the exact accepted checkpoint-input-binding-v1 identity fields."""
    if not isinstance(binding, dict) or set(binding) != BINDING_FIELDS:
        raise ValueError("Checkpoint input binding has missing or unknown fields")
    if binding["schema"] != "ev-checkpoint-input-binding-v1":
        raise ValueError("Unsupported checkpoint input binding schema")
    if binding["feature_schema"] != "ev-input-v1":
        raise ValueError("Unsupported feature schema")
    for key in ("input_run_id", "dataset_id", "city_id"):
        if not isinstance(binding[key], str) or not binding[key]:
            raise ValueError(f"Missing binding {key}")
    if not isinstance(binding["input_manifest_sha256"], str) or not re.fullmatch(
        r"[0-9a-fA-F]{64}", binding["input_manifest_sha256"]
    ):
        raise ValueError("Input manifest SHA-256 must be a complete hex digest")
    if binding["stage"] == "source":
        target_fields = ("entity_id", "history_days", "scale_id", "source_checkpoint_sha256")
        if any(binding[key] is not None for key in target_fields):
            raise ValueError("Source binding must not contain target identity")
    elif binding["stage"] == "target":
        if not isinstance(binding["entity_id"], str) or not binding["entity_id"]:
            raise ValueError("Target entity_id is required")
        if binding["history_days"] not in (7, 14, 28):
            raise ValueError("Target history_days must be 7, 14 or 28")
        for key in ("scale_id", "source_checkpoint_sha256"):
            if not isinstance(binding[key], str) or not binding[key]:
                raise ValueError(f"Target {key} is required")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", binding["source_checkpoint_sha256"]):
            raise ValueError("Source checkpoint SHA-256 must be a complete hex digest")
    else:
        raise ValueError("Checkpoint stage must be source or target")


def save_checkpoint(
    path: Path,
    model: ForecastGRU,
    optimizer: torch.optim.Adam,
    *,
    input_binding: dict,
    latent_scale: Tensor | None,
    seed: int,
    code_sha: str,
    training_step: int,
) -> None:
    """Create a new bound checkpoint; an existing path is never overwritten."""
    validate_binding(input_binding)
    if type(optimizer) is not torch.optim.Adam:
        raise ValueError("Only Adam optimizer checkpoints are supported")
    if latent_scale is not None:
        validate_latent_scale(latent_scale)
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    if not isinstance(code_sha, str) or not code_sha:
        raise ValueError("code_sha is required")
    if isinstance(training_step, bool) or not isinstance(training_step, int) or training_step < 0:
        raise ValueError("training_step must be a nonnegative integer")
    payload = {
        "schema": CHECKPOINT_SCHEMA,
        "architecture": model.config.to_dict(),
        "input_binding": dict(input_binding),
        "seed": seed,
        "code_sha": code_sha,
        "training_step": training_step,
        "model_state": model.state_dict(),
        "optimizer_type": "Adam",
        "optimizer_state": optimizer.state_dict(),
        "latent_scale": None if latent_scale is None else latent_scale.detach().clone(),
        "rng_state": _checkpoint_rng(model),
    }
    destination = Path(path)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            torch.save(payload, stream)
            stream.flush()
            os.fsync(stream.fileno())
        publish_create_only(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def load_checkpoint(
    path: Path,
    *,
    expected_binding: dict,
    map_location: str | torch.device = "cpu",
    restore_rng: bool = False,
) -> tuple[ForecastGRU, torch.optim.Adam, Tensor | None, dict]:
    """Reload bound model/optimizer; RNG restoration is explicit and same-environment only."""
    if not isinstance(restore_rng, bool):
        raise ValueError("restore_rng must be a boolean")
    validate_binding(expected_binding)
    payload = torch.load(Path(path), map_location=map_location, weights_only=True)
    if payload.get("schema") != CHECKPOINT_SCHEMA or payload.get("optimizer_type") != "Adam":
        raise ValueError("Unsupported model checkpoint")
    if payload.get("input_binding") != expected_binding:
        raise ValueError("Checkpoint input binding mismatch")
    if (
        isinstance(payload.get("seed"), bool)
        or not isinstance(payload.get("seed"), int)
        or payload["seed"] < 0
        or isinstance(payload.get("training_step"), bool)
        or not isinstance(payload.get("training_step"), int)
        or payload["training_step"] < 0
        or not isinstance(payload.get("code_sha"), str)
        or not payload["code_sha"]
    ):
        raise ValueError("Invalid checkpoint execution metadata")
    rng = _validated_checkpoint_rng(payload, torch.device(map_location)) if restore_rng else None
    config = ModelConfig(**payload["architecture"])
    model = ForecastGRU(config).to(map_location)
    model.load_state_dict(payload["model_state"])
    model.encoder.flatten_parameters()
    optimizer = torch.optim.Adam(model.parameters(), lr=1.0)
    optimizer.load_state_dict(payload["optimizer_state"])
    scale = payload["latent_scale"]
    if scale is not None:
        scale = scale.to(map_location)
        validate_latent_scale(scale)
    if rng is not None:
        torch.set_rng_state(rng["cpu"].cpu())
        if rng["cuda"]:
            torch.cuda.set_rng_state_all([state.cpu() for state in rng["cuda"]])
    return (
        model,
        optimizer,
        scale,
        {
            "seed": payload["seed"],
            "code_sha": payload["code_sha"],
            "training_step": payload["training_step"],
        },
    )
