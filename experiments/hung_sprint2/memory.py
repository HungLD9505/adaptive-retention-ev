"""Logical tensor-state size for a model and its optimizer."""

from __future__ import annotations

from collections.abc import Mapping

import torch


def _tensor_payload_bytes(value: object) -> int:
    if isinstance(value, torch.Tensor):
        return value.numel() * value.element_size()
    if isinstance(value, Mapping):
        return sum(_tensor_payload_bytes(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_tensor_payload_bytes(item) for item in value)
    return 0


def model_tensor_bytes(model: torch.nn.Module) -> int:
    """Count model state payloads, excluding gradients and temporary tensors."""
    return _tensor_payload_bytes(model.state_dict())


def model_optimizer_tensor_bytes(model: torch.nn.Module, optimizer: torch.optim.Optimizer) -> int:
    """Count state tensor payloads; this is not allocated or peak RSS."""
    return model_tensor_bytes(model) + _tensor_payload_bytes(optimizer.state)
