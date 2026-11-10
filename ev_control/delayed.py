"""Pilot-only delayed, forecast-aligned retention hypergradient."""

import math
import statistics
from dataclasses import dataclass

import torch
from torch import Tensor

from ev_control.hypergradient import forecast_with_virtual, virtual_adam_step
from ev_models.model import ForecastGRU, forecast_loss, retention_loss


@dataclass(frozen=True)
class DelayedRule:
    anchor: float
    decay: float
    meta_step: float
    max_step: float
    trust_radius: float
    history: int = 5
    agreement: int = 4

    def __post_init__(self) -> None:
        values = (self.anchor, self.decay, self.meta_step, self.max_step, self.trust_radius)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Finite delayed-controller settings required")
        if (
            self.anchor < 0
            or not 0 <= self.decay < 1
            or self.meta_step <= 0
            or self.max_step <= 0
            or self.trust_radius <= 0
        ):
            raise ValueError("Invalid delayed-controller scale or anchor")
        if (
            isinstance(self.history, bool)
            or isinstance(self.agreement, bool)
            or not isinstance(self.history, int)
            or not isinstance(self.agreement, int)
            or not 1 <= self.agreement <= self.history
        ):
            raise ValueError("Invalid delayed-controller history gate")


def choose_lambda(
    current: float,
    history: list[float],
    gradient: float | None,
    rule: DelayedRule,
    upper_bound: float,
) -> dict:
    """Shrink to calibrated Fixed until recent causal gradients agree."""
    if not math.isfinite(current) or not math.isfinite(upper_bound) or upper_bound <= 0:
        raise ValueError("Invalid delayed-controller bounds")
    if any(not math.isfinite(value) for value in history):
        raise ValueError("Nonfinite saved hypergradient")
    if gradient is None:
        recent = history[-rule.history :]
    elif math.isfinite(gradient):
        recent = (history + [gradient])[-rule.history :]
    else:
        raise ValueError("Nonfinite delayed hypergradient")
    median = statistics.median(recent) if recent else None
    agree = (
        sum(value * median > 0 for value in recent) if median is not None and median != 0 else 0
    )
    gate = gradient is not None and len(recent) == rule.history and agree >= rule.agreement
    step = max(-rule.max_step, min(rule.max_step, rule.meta_step * median)) if gate else 0.0
    raw = rule.anchor + rule.decay * (current - rule.anchor) - step
    lower = max(0.0, rule.anchor - rule.trust_radius)
    upper = min(upper_bound, rule.anchor + rule.trust_radius)
    if lower > upper:
        raise ValueError("Empty delayed-controller trust interval")
    selected = max(lower, min(upper, raw))
    return {
        "lambda_before": current,
        "lambda_after": selected,
        "lambda_unclipped": raw,
        "bound_hit": selected != raw,
        "hypergradient_median": median,
        "gradient_agreement": agree,
        "gate_pass": gate,
        "gradient_history": recent,
        "applied_step": step,
    }


def observe_delayed_gradient(
    model: ForecastGRU,
    optimizer: torch.optim.Adam,
    reference: ForecastGRU,
    latent_scale: Tensor,
    v_record: dict,
    w_record: dict,
    expected_prediction: list[float],
    lambda_used: float,
    *,
    epsilon: float,
    device: str,
) -> dict:
    """Replay V's real Adam step and score its immediately following forecast W."""
    if not math.isfinite(lambda_used) or lambda_used < 0:
        raise ValueError("Invalid delayed coefficient")
    if reference.training or any(parameter.requires_grad for parameter in reference.parameters()):
        raise ValueError("Source reference must be frozen")
    if len(expected_prediction) != 24 or any(
        not math.isfinite(value) for value in expected_prediction
    ):
        raise ValueError("Invalid bound forecast")
    xv, cv, yv = (
        torch.tensor([v_record[key]], dtype=torch.float32, device=device)
        for key in ("x_hist", "c_future", "y_scaled")
    )
    xw, cw, yw = (
        torch.tensor([w_record[key]], dtype=torch.float32, device=device)
        for key in ("x_hist", "c_future", "y_scaled")
    )
    with torch.no_grad():
        source_latent = reference.encode(xv)
    coefficient = torch.tensor(lambda_used, dtype=xv.dtype, device=device, requires_grad=True)
    previous_mode = model.training
    try:
        model.train()
        with torch.backends.cudnn.flags(enabled=False):
            training_loss = forecast_loss(model(xv, cv), yv) + coefficient * retention_loss(
                model.encode(xv), source_latent, latent_scale.to(device), epsilon
            )
            virtual = virtual_adam_step(model, optimizer, training_loss)
            predicted = forecast_with_virtual(model, virtual, xw, cw)
            recorded = torch.tensor([expected_prediction], dtype=predicted.dtype, device=device)
            max_error = (predicted.detach() - recorded).abs().max().item()
            if not torch.allclose(predicted.detach(), recorded, rtol=1e-4, atol=1e-5):
                return {"status": "skip", "reason": "virtual_real_mismatch", "max_error": max_error}
            validation = forecast_loss(predicted, yw)
            gradient = torch.autograd.grad(validation, coefficient)[0]
    finally:
        model.train(previous_mode)
    if not torch.isfinite(gradient):
        raise ValueError("Nonfinite delayed hypergradient")
    return {
        "status": "observed",
        "hypergradient": gradient.item(),
        "validation_mae_scaled": validation.detach().item(),
        "virtual_real_max_error": max_error,
        "virtual_adam_steps": 1,
    }
