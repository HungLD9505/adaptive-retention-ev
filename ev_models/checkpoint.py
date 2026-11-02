"""Bound, hash-checked, weights-only checkpoints with epoch-boundary resume."""

import hashlib
import json
import random
import re
from pathlib import Path

import torch

from ev_models.model import ForecastGRU, ModelConfig


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def validate_binding(binding: dict) -> None:
    required = {
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
    if (
        set(binding) != required
        or binding["schema"] != "ev-checkpoint-input-binding-v1"
        or binding["feature_schema"] != "ev-input-v1"
    ):
        raise ValueError("Invalid checkpoint input binding")
    if not isinstance(binding["input_manifest_sha256"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", binding["input_manifest_sha256"]
    ):
        raise ValueError("Missing input fingerprint")
    if any(
        not isinstance(binding[k], str) or not binding[k]
        for k in ("input_run_id", "dataset_id", "city_id")
    ):
        raise ValueError("Missing binding identity")
    if binding["stage"] == "source":
        if any(
            binding[k] is not None
            for k in ("entity_id", "history_days", "scale_id", "source_checkpoint_sha256")
        ):
            raise ValueError("Source binding cannot name target state")
    elif binding["stage"] == "target":
        if (
            not isinstance(binding["entity_id"], str)
            or not binding["entity_id"]
            or binding["history_days"] not in (7, 14, 28)
        ):
            raise ValueError("Invalid target identity/budget")
        for name in ("scale_id", "source_checkpoint_sha256"):
            if not isinstance(binding[name], str) or not re.fullmatch(
                r"[0-9a-f]{64}", binding[name]
            ):
                raise ValueError("Invalid target scaler/source fingerprint")
    else:
        raise ValueError("Unknown checkpoint stage")


def save_checkpoint(
    path: Path,
    model: ForecastGRU,
    optimizer: torch.optim.Optimizer,
    *,
    metadata: dict,
    latent_scale: torch.Tensor | None,
    completed_epochs: int,
) -> str:
    """Write a fresh checkpoint; never overwrite a previous epoch/run."""
    validate_binding(metadata["input_binding"])
    payload = {
        "schema": "ev-model-checkpoint-v1",
        "architecture": model.architecture(),
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "metadata": metadata,
        "latent_scale": latent_scale,
        "completed_epochs": completed_epochs,
        "rng_cpu": torch.get_rng_state(),
        "rng_cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
        "rng_python": random.getstate(),
    }
    with path.open("xb") as stream:
        torch.save(payload, stream)
    checksum = digest(path)
    path.with_suffix(path.suffix + ".sha256").write_text(checksum + "\n", encoding="utf-8")
    return checksum


def load_checkpoint(
    path: Path, *, sha256: str, device: str = "cpu", restore_rng: bool = False
) -> tuple[ForecastGRU, torch.optim.Optimizer, dict]:
    """Only load an explicitly identified artifact; no arbitrary pickle execution."""
    if digest(path) != sha256:
        raise ValueError("Checkpoint SHA-256 mismatch")
    value = torch.load(path, map_location="cpu", weights_only=True)
    if value.get("schema") != "ev-model-checkpoint-v1":
        raise ValueError("Unsupported checkpoint")
    metadata = value["metadata"]
    binding = metadata["input_binding"]
    validate_binding(binding)
    model = ForecastGRU(ModelConfig(value["architecture"]["head_width"]))
    if model.architecture() != value["architecture"]:
        raise ValueError("Architecture metadata differs")
    model.load_state_dict(value["model"], strict=True)
    model.to(device)
    optimizer = torch.optim.Adam(
        model.parameters(), lr=metadata["training_config"]["learning_rate"]
    )
    optimizer.load_state_dict(value["optimizer"])
    if restore_rng:
        torch.set_rng_state(value["rng_cpu"])
        random.setstate(value["rng_python"])
        if value["rng_cuda"]:
            if not torch.cuda.is_available() or len(value["rng_cuda"]) != torch.cuda.device_count():
                raise ValueError("CUDA topology differs; exact resume is unsupported")
            torch.cuda.set_rng_state_all(value["rng_cuda"])
    return model, optimizer, value


def write_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
