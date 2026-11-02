"""Use the shared authenticated input contract, independently of study model weights."""

from pathlib import Path

import torch

from ev_models.data import InputRun
from ev_runner.replay import Replay


def open_inputs(root: Path, manifest_sha256: str) -> InputRun:
    """Require an external manifest pin, ready Development roles and strict input validation."""
    if len(manifest_sha256) != 64:
        raise ValueError("An explicit SHA-256 input manifest pin is required")
    return InputRun(root, manifest_sha256)


def _tensors(rows: list[dict]) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    if not rows:
        return torch.empty(0, 24, 7), torch.empty(0, 24, 5), torch.empty(0, 24)
    return tuple(
        torch.tensor([r[name] for r in rows], dtype=torch.float32)
        for name in ("x_hist", "c_future", "y_scaled")
    )


def load_source_training_samples(
    inputs: InputRun, max_samples: int = 500
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Validate Source roles/prefixes/scalers before taking a declared bounded prefix."""
    if isinstance(max_samples, bool) or max_samples < 1:
        raise ValueError("Source sample limit must be positive")
    rows = inputs.training("source")[:max_samples]
    if not rows:
        raise ValueError("No complete permitted Source training examples")
    return _tensors(rows)


def load_initial_target_samples(
    inputs: InputRun, entity_id: list[str]
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Reject Final roles and invalid target prefix/scaler bindings."""
    if tuple(entity_id[:2]) != inputs.namespace or len(entity_id) != 3:
        raise ValueError("Target identity differs from the input namespace")
    return _tensors(inputs.training("development", entity_id[2]))


def load_development_stream(inputs: InputRun, entity_id: list[str], days: int) -> Replay:
    """Expose predictors and schedule without decoding future label arrays."""
    if tuple(entity_id[:2]) != inputs.namespace or len(entity_id) != 3:
        raise ValueError("Target identity differs from the input namespace")
    return Replay(inputs, entity_id[2], days)
