"""CPU fixture-stage causal replay for three retention trajectories."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any

import torch
from torch import Tensor

from experiments.hung_sprint2.controller import ControllerConfig, DailyScore, Decision, decide_block
from experiments.hung_sprint2.model import ForecastGRU, ModelConfig
from experiments.hung_sprint2.retention import validate_latent_scale
from experiments.hung_sprint2.training import target_step, validate_binding


@dataclass(frozen=True)
class Origin:
    """Predictor-visible daily event. A skipped day has no X or calendar."""

    day_id: str
    index: int
    x_hist: Tensor | None
    c_future: Tensor | None
    status: str = "created"


@dataclass(frozen=True)
class LabelArrival:
    """A separate label event after a forecast or scheduled skip."""

    day_id: str
    arrived: bool
    y_scaled: Tensor | None = None
    valid: Tensor | None = None


def _copy_pair(
    model: ForecastGRU, optimizer: torch.optim.Adam
) -> tuple[ForecastGRU, torch.optim.Adam]:
    """Copy model and optimizer together so parameter references stay paired."""
    return deepcopy((model, optimizer))


class PrequentialRunner:
    """Advance forecast and label events in causal order on one target/budget.

    The caller must feed the accepted input schedule and delayed labels in order.
    This fixture-stage runner operates on CPU so a torch RNG snapshot suffices.
    Real-input adapters, GPU RNG, durable per-event output and cost probes are
    separate #21 integration work.
    """

    def __init__(
        self,
        model: ForecastGRU,
        optimizer: torch.optim.Adam,
        reference: ForecastGRU,
        latent_scale: Tensor,
        *,
        binding: dict,
        controller: ControllerConfig,
        epsilon: float,
        energy_scale: float,
    ) -> None:
        validate_binding(binding)
        if binding["stage"] != "target":
            raise ValueError("Runner requires a bound target checkpoint")
        if next(model.parameters()).device.type != "cpu":
            raise ValueError("Fixture runner currently requires CPU model state")
        if next(reference.parameters()).device.type != "cpu" or latent_scale.device.type != "cpu":
            raise ValueError("Reference and latent scale must also be on CPU")
        if model.config != reference.config:
            raise ValueError("Target and source reference architecture differ")
        if any(parameter.requires_grad for parameter in reference.parameters()):
            raise ValueError("Source reference must be frozen")
        if not 0 < epsilon < float("inf") or not 0 < energy_scale < float("inf"):
            raise ValueError("Epsilon and original-unit energy scale must be positive")
        validate_latent_scale(latent_scale)
        self.binding = deepcopy(binding)
        self.controller = controller
        self.epsilon = epsilon
        self.energy_scale = energy_scale
        self.reference = deepcopy(reference).eval()
        self.latent_scale = latent_scale.detach().clone()
        self.active_model, self.active_optimizer = _copy_pair(model, optimizer)
        self.current_level = controller.initial_level
        self.block_id = 0
        self.next_index = 0
        self.candidates: list[tuple[ForecastGRU, torch.optim.Adam]] = []
        self.audit: tuple[float, ForecastGRU, torch.optim.Adam] | None = None
        self.audit_rng: Tensor | None = None
        self.pending: dict[str, Any] | None = None
        self.days: list[DailyScore] = []
        self.issued: list[dict[str, Any]] = []
        self.decisions: list[Decision] = []
        self.events: list[str] = []
        self.update_steps = [0, 0, 0]
        self.audit_steps = 0
        self._fork()

    def _fork(self) -> None:
        self.candidates = [
            _copy_pair(self.active_model, self.active_optimizer) for _ in self.controller.levels
        ]
        self.events.append(f"fork:{self.block_id}")

    def forecast(self, origin: Origin) -> None:
        """Store all predictions before a matching label event may be accepted."""
        if self.pending is not None:
            raise ValueError("Previous day has not received its label event")
        if len(self.days) == self.controller.block_days:
            raise ValueError("Finish block decision before the next forecast")
        if origin.index != self.next_index or not origin.day_id:
            raise ValueError("Daily origins must be unique and consecutive")
        if any(day.day_id == origin.day_id for day in self.days) or any(
            issued["day_id"] == origin.day_id for issued in self.issued
        ):
            raise ValueError("Duplicate forecast day identity")
        if origin.status not in {"created", "skipped_all_missing_history"}:
            raise ValueError("Unsupported scheduled origin status")
        if origin.status != "created":
            if origin.x_hist is not None or origin.c_future is not None:
                raise ValueError("Skipped origin cannot contain predictor tensors")
            self.pending = {"day_id": origin.day_id, "index": origin.index, "status": origin.status}
            self.events.append(f"skip:{origin.day_id}")
            return
        if origin.x_hist is None or origin.c_future is None:
            raise ValueError("Created origin requires predictor-only tensors")
        x_hist = origin.x_hist.detach().clone()
        c_future = origin.c_future.detach().clone()
        if x_hist.device.type != "cpu" or c_future.device.type != "cpu":
            raise ValueError("Fixture runner currently requires CPU input tensors")
        if x_hist.shape != (1, 24, 7) or c_future.shape != (1, 24, 5):
            raise ValueError("Forecast tensors must have shapes [1,24,7] and [1,24,5]")
        forecasts = []
        with torch.no_grad():
            for model, _ in self.candidates:
                model.eval()
                forecasts.append(model(x_hist, c_future).detach().clone())
            audit_forecast = None
            if self.audit is not None:
                self.audit[1].eval()
                audit_forecast = self.audit[1](x_hist, c_future).detach().clone()
        self.pending = {
            "day_id": origin.day_id,
            "index": origin.index,
            "status": "created",
            "x_hist": x_hist,
            "c_future": c_future,
            "forecasts": forecasts,
            "audit_forecast": audit_forecast,
        }
        self.issued.append(
            {
                "day_id": origin.day_id,
                "index": origin.index,
                "block_id": self.block_id,
                "active_level": self.current_level,
                "forecasts": [forecast.clone() for forecast in forecasts],
                "audit_forecast": audit_forecast,
                "normalized_mae": None,
                "mae_kwh": None,
                "audit_normalized_mae": None,
                "audit_mae_kwh": None,
            }
        )
        self.events.append(f"forecast:{origin.day_id}")

    def arrive(self, label: LabelArrival) -> None:
        """Score stored forecasts, then train each candidate on complete labels."""
        pending = self.pending
        if pending is None or label.day_id != pending["day_id"]:
            raise ValueError("Label event has no matching issued/scheduled origin")
        scores: tuple[float, float, float] | None = None
        if not label.arrived and (label.y_scaled is not None or label.valid is not None):
            raise ValueError("Unavailable labels must not enter the runner")
        if label.arrived and (
            label.y_scaled is None
            or label.valid is None
            or label.y_scaled.shape != (24,)
            or label.valid.shape != (24,)
            or label.valid.dtype != torch.bool
        ):
            raise ValueError("Arrived label event requires 24 values and 24 validity bits")
        valid = label.arrived and bool(label.valid.all())
        if valid:
            if label.y_scaled.device.type != "cpu" or label.valid.device.type != "cpu":
                raise ValueError("Fixture runner currently requires CPU labels")
            if not torch.isfinite(label.y_scaled).all() or torch.any(label.y_scaled < 0):
                raise ValueError("Complete labels must be finite nonnegative energy")
            if pending["status"] == "created":
                y = label.y_scaled.detach().clone().unsqueeze(0)
                scores = tuple(
                    float(torch.abs(forecast - y).mean()) for forecast in pending["forecasts"]
                )
                self.issued[-1]["normalized_mae"] = scores
                self.issued[-1]["mae_kwh"] = tuple(value * self.energy_scale for value in scores)
                if pending["audit_forecast"] is not None:
                    audit_mae = float(torch.abs(pending["audit_forecast"] - y).mean())
                    self.issued[-1]["audit_normalized_mae"] = audit_mae
                    self.issued[-1]["audit_mae_kwh"] = audit_mae * self.energy_scale
                self.events.append(f"score:{label.day_id}")
                shared_rng = torch.get_rng_state().clone()
                post_rng: Tensor | None = None
                for index, (model, optimizer) in enumerate(self.candidates):
                    torch.set_rng_state(shared_rng)
                    target_step(
                        model, self.reference, optimizer, pending["x_hist"],
                        pending["c_future"], y,
                        retention_weight=self.controller.levels[index],
                        latent_scale=self.latent_scale, epsilon=self.epsilon,
                    )
                    if post_rng is None:
                        post_rng = torch.get_rng_state().clone()
                    self.update_steps[index] += 1
                if post_rng is not None:
                    torch.set_rng_state(post_rng)
                self.events.append(f"update:{label.day_id}")
                if self.audit is not None:
                    level, model, optimizer = self.audit
                    live_rng = torch.get_rng_state().clone()
                    try:
                        torch.set_rng_state(self.audit_rng)
                        target_step(
                            model, self.reference, optimizer, pending["x_hist"],
                            pending["c_future"], y, retention_weight=level,
                            latent_scale=self.latent_scale, epsilon=self.epsilon,
                        )
                        self.audit_rng = torch.get_rng_state().clone()
                    finally:
                        torch.set_rng_state(live_rng)
                    self.audit_steps += 1
                    self.events.append(f"audit-update:{label.day_id}")
        self.days.append(
            DailyScore(
                label.day_id,
                label.arrived,
                bool(valid),
                scores,
            )
        )
        if scores is None:
            self.events.append(f"unscored:{label.day_id}")
        self.pending = None
        self.next_index += 1

    def finish_block(self) -> Decision:
        """Decide and carry the selected *trained* state into the next block."""
        if self.pending is not None:
            raise ValueError("Cannot decide before the final label event")
        if len(self.days) != self.controller.block_days:
            raise ValueError("A block requires its complete scheduled-day count")
        decision = decide_block(
            self.controller, current_level=self.current_level,
            block_id=self.block_id, days=self.days,
        )
        current_index = self.controller.levels.index(self.current_level)
        selected_index = self.controller.levels.index(decision.selected_level)
        old_active = self.candidates[current_index]
        self.active_model, self.active_optimizer = self.candidates[selected_index]
        self.audit = (
            (self.current_level, *old_active) if decision.switched else None
        )
        self.audit_rng = torch.get_rng_state().clone() if decision.switched else None
        self.current_level = decision.selected_level
        self.decisions.append(decision)
        self.events.append(f"decision:{self.block_id}:{decision.selected_level}")
        self.block_id += 1
        self.days = []
        self._fork()
        return decision

    def state_dict(self) -> dict:
        """Primitive/tensor state for exact CPU resumption at an event boundary."""
        def pair_state(pair: tuple[ForecastGRU, torch.optim.Adam]) -> dict:
            return {"model": pair[0].state_dict(), "optimizer": pair[1].state_dict()}

        return {
            "schema": "hung-sprint2-runner-v1",
            "binding": deepcopy(self.binding),
            "controller": asdict(self.controller),
            "model_config": self.active_model.config.to_dict(),
            "epsilon": self.epsilon,
            "energy_scale": self.energy_scale,
            "reference": self.reference.state_dict(),
            "latent_scale": self.latent_scale.clone(),
            "active": pair_state((self.active_model, self.active_optimizer)),
            "candidates": [pair_state(pair) for pair in self.candidates],
            "audit": None if self.audit is None else {
                "level": self.audit[0], **pair_state((self.audit[1], self.audit[2]))
            },
            "audit_rng": None if self.audit_rng is None else self.audit_rng.clone(),
            "current_level": self.current_level,
            "block_id": self.block_id,
            "next_index": self.next_index,
            "pending": deepcopy(self.pending),
            "days": [asdict(day) for day in self.days],
            "issued": deepcopy(self.issued),
            "decisions": [asdict(decision) for decision in self.decisions],
            "events": list(self.events),
            "update_steps": list(self.update_steps),
            "audit_steps": self.audit_steps,
            "torch_rng": torch.get_rng_state().clone(),
        }

    @classmethod
    def from_state_dict(cls, state: dict, *, expected_binding: dict) -> PrequentialRunner:
        """Restore a validated bound state without replaying past events."""
        validate_binding(expected_binding)
        if (
            state.get("schema") != "hung-sprint2-runner-v1"
            or state.get("binding") != expected_binding
        ):
            raise ValueError("Runner checkpoint schema/input binding mismatch")
        config = ModelConfig(**state["model_config"])

        def pair_from(payload: dict) -> tuple[ForecastGRU, torch.optim.Adam]:
            model = ForecastGRU(config)
            model.load_state_dict(payload["model"])
            optimizer = torch.optim.Adam(model.parameters(), lr=1.0)
            optimizer.load_state_dict(payload["optimizer"])
            return model, optimizer

        runner = cls.__new__(cls)
        runner.binding = deepcopy(expected_binding)
        runner.controller = ControllerConfig(**state["controller"])
        runner.epsilon = state["epsilon"]
        runner.energy_scale = state["energy_scale"]
        runner.reference = ForecastGRU(config).eval()
        runner.reference.load_state_dict(state["reference"])
        runner.reference.requires_grad_(False)
        runner.latent_scale = state["latent_scale"].clone()
        validate_latent_scale(runner.latent_scale)
        runner.active_model, runner.active_optimizer = pair_from(state["active"])
        runner.candidates = [pair_from(payload) for payload in state["candidates"]]
        if len(runner.candidates) != 3:
            raise ValueError("Runner checkpoint must contain three candidates")
        audit = state["audit"]
        runner.audit = None if audit is None else (audit["level"], *pair_from(audit))
        runner.audit_rng = state["audit_rng"]
        runner.current_level = state["current_level"]
        runner.block_id = state["block_id"]
        runner.next_index = state["next_index"]
        runner.pending = state["pending"]
        runner.days = [DailyScore(**day) for day in state["days"]]
        runner.issued = state["issued"]
        runner.decisions = [Decision(**decision) for decision in state["decisions"]]
        runner.events = state["events"]
        runner.update_steps = state["update_steps"]
        runner.audit_steps = state["audit_steps"]
        torch.set_rng_state(state["torch_rng"])
        return runner
