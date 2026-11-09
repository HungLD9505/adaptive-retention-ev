"""Causal arrived-label windows and one-step GRU retention decisions for #99."""

import math
from dataclasses import dataclass
from datetime import datetime

import torch
from torch import Tensor

from ev_control.hypergradient import forecast_with_virtual, validation_hypergradient
from ev_models.model import ForecastGRU, forecast_loss, retention_loss


@dataclass(frozen=True)
class WindowRule:
    older_count: int
    newer_count: int
    upper_bound: float
    meta_step_size: float
    epsilon: float

    def __post_init__(self) -> None:
        if self.older_count < 1 or self.newer_count < 1:
            raise ValueError("Positive A/V window sizes required")
        if not all(
            math.isfinite(x) and x > 0
            for x in (self.upper_bound, self.meta_step_size, self.epsilon)
        ):
            raise ValueError("Finite positive controller settings required")


class ArrivedWindow:
    """Track complete arrived labels and whether real training consumed each day."""

    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}

    def add(
        self, *, origin: datetime, available_at: datetime, as_of: datetime, record: dict
    ) -> None:
        key = origin.isoformat()
        if key in self.rows or available_at > as_of or origin >= as_of or "y_scaled" not in record:
            raise ValueError("Duplicate, future, or unlabeled window example")
        self.rows[key] = {
            "origin": key,
            "available_at": available_at.isoformat(),
            "record": record,
            "trained": False,
        }

    def select(self, as_of: datetime, rule: WindowRule) -> tuple[list[dict], list[dict]] | None:
        eligible = sorted(
            (
                row
                for row in self.rows.values()
                if datetime.fromisoformat(row["available_at"]) <= as_of
            ),
            key=lambda row: row["origin"],
        )
        untrained = [row for row in eligible if not row["trained"]]
        if len(untrained) < rule.newer_count:
            return None
        v = untrained[-rule.newer_count :]
        cutoff = v[0]["origin"]
        older = [row for row in eligible if row["origin"] < cutoff]
        if len(older) < rule.older_count:
            return None
        a = older[-rule.older_count :]
        return a, v

    def mark_trained(self, origin: datetime) -> None:
        self.rows[origin.isoformat()]["trained"] = True

    def snapshot(self) -> dict:
        return {key: value.copy() for key, value in self.rows.items()}

    @classmethod
    def restore(cls, value: dict) -> "ArrivedWindow":
        window = cls()
        if len(value) != len(set(value)):
            raise ValueError("Duplicate window identity")
        for key, row in value.items():
            if key != row["origin"] or not isinstance(row["trained"], bool):
                raise ValueError("Invalid saved window")
        window.rows = {key: row.copy() for key, row in value.items()}
        return window


def tensors(rows: list[dict], device: str) -> tuple[Tensor, Tensor, Tensor]:
    return tuple(
        torch.tensor([row["record"][name] for row in rows], dtype=torch.float32, device=device)
        for name in ("x_hist", "c_future", "y_scaled")
    )


def decide(
    model: ForecastGRU,
    optimizer: torch.optim.Adam,
    reference: ForecastGRU,
    latent_scale: Tensor,
    a_rows: list[dict],
    v_rows: list[dict],
    current_lambda: float,
    rule: WindowRule,
    *,
    device: str,
) -> dict:
    """Use arrived A/V labels; caller performs the later real update separately."""
    if not a_rows or not v_rows or not 0 <= current_lambda <= rule.upper_bound:
        raise ValueError("Invalid controller windows or coefficient")
    if max(row["origin"] for row in a_rows) >= min(row["origin"] for row in v_rows):
        raise ValueError("A must precede V without overlapping label days")
    if any(row["trained"] for row in v_rows):
        raise ValueError("V was already used for real training")
    if reference.training or any(parameter.requires_grad for parameter in reference.parameters()):
        raise ValueError("Source reference must be frozen")
    xa, ca, ya = tensors(a_rows, device)
    xv, cv, yv = tensors(v_rows, device)
    with torch.no_grad():
        source_latent = reference.encode(xa)
    coefficient = torch.tensor(current_lambda, dtype=xa.dtype, device=device, requires_grad=True)

    def training_objective(target, weight):
        forecast = forecast_loss(target(xa, ca), ya)
        retention = retention_loss(
            target.encode(xa), source_latent, latent_scale.to(device), rule.epsilon
        )
        return forecast + weight * retention

    def validation_objective(virtual):
        return forecast_loss(forecast_with_virtual(model, virtual, xv, cv), yv)

    gradient, validation = validation_hypergradient(
        model, optimizer, coefficient, training_objective, validation_objective
    )
    raw = current_lambda - rule.meta_step_size * gradient.item()
    if not math.isfinite(raw):
        raise ValueError("Nonfinite controller update")
    selected = min(rule.upper_bound, max(0.0, raw))
    return {
        "lambda_before": current_lambda,
        "hypergradient": gradient.item(),
        "validation_mae_scaled": validation.item(),
        "lambda_unclipped": raw,
        "lambda_after": selected,
        "bound_hit": selected != raw,
        "a_origins": [row["origin"] for row in a_rows],
        "v_origins": [row["origin"] for row in v_rows],
        "virtual_adam_steps": 1,
    }
