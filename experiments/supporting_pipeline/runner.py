"""Causal replay for three retention trajectories on CPU or CUDA."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from time import perf_counter_ns
from typing import Any

import torch
from torch import Tensor

from experiments.supporting_pipeline.baseline_selection import (
    SelectionRule,
    decide_fixed_block,
    decide_mean_block,
)
from experiments.supporting_pipeline.controller import (
    ControllerConfig,
    DailyScore,
    Decision,
    decide_block,
)
from experiments.supporting_pipeline.memory import model_optimizer_tensor_bytes, model_tensor_bytes
from experiments.supporting_pipeline.model import ForecastGRU, ModelConfig
from experiments.supporting_pipeline.proxy_selection import ProxyConfig, decide_proxy_block
from experiments.supporting_pipeline.retention import validate_latent_scale
from experiments.supporting_pipeline.training import target_step, validate_binding


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
    deferred: bool = False


def _copy_pair(
    model: ForecastGRU, optimizer: torch.optim.Adam
) -> tuple[ForecastGRU, torch.optim.Adam]:
    """Copy model and optimizer together so parameter references stay paired."""
    copied_model, copied_optimizer = deepcopy((model, optimizer))
    copied_model.encoder.flatten_parameters()
    return copied_model, copied_optimizer


def _empty_cost_record() -> dict[str, int]:
    return {"inference_calls": 0, "inference_ns": 0, "update_steps": 0, "update_ns": 0}


def _runtime_costs(*, complete: bool) -> dict[str, Any]:
    return {
        "schema": "hung-sprint2-runtime-cost-v1",
        "clock": "perf_counter_ns",
        "scope": "CPU model.forward and target_step calls only",
        "complete": complete,
        "candidate": [_empty_cost_record() for _ in range(3)],
        "audit": _empty_cost_record(),
    }


def _validated_runtime_costs(
    payload: dict[str, Any], update_steps: list[int], audit_steps: int, device_type: str
) -> dict[str, Any]:
    expected = _runtime_costs(complete=True)
    if device_type == "cuda":
        expected["scope"] = "CUDA synchronized model.forward and target_step calls only"
    if (
        not isinstance(payload, dict)
        or any(payload.get(key) != expected[key] for key in ("schema", "clock", "scope"))
        or not isinstance(payload.get("complete"), bool)
        or not isinstance(payload.get("candidate"), list)
        or len(payload["candidate"]) != 3
    ):
        raise ValueError("Runner runtime cost schema mismatch")
    for record in [*payload["candidate"], payload.get("audit")]:
        if not isinstance(record, dict) or set(record) != set(_empty_cost_record()):
            raise ValueError("Runner runtime cost record mismatch")
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in record.values()
        ):
            raise ValueError("Runner runtime cost values must be nonnegative integers")
    if payload["complete"] and (
        [record["update_steps"] for record in payload["candidate"]] != update_steps
        or payload["audit"]["update_steps"] != audit_steps
    ):
        raise ValueError("Runner runtime cost and update counters disagree")
    return deepcopy(payload)


class PrequentialRunner:
    """Advance forecast and label events in causal order on one target/budget.

    The caller must feed accepted origins in order and complete deferred labels
    when they become available. Late labels update current candidate trajectories;
    a decision already issued for their original block is never revised. This
    RNG snapshots include the selected CUDA device when one is used.
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
        selection_rule: SelectionRule = "confidence",
        proxy_config: ProxyConfig | None = None,
        retention_kind: str = "latent",
    ) -> None:
        validate_binding(binding)
        if binding["stage"] != "target":
            raise ValueError("Runner requires a bound target checkpoint")
        self.device = next(model.parameters()).device
        if next(reference.parameters()).device != self.device or latent_scale.device != self.device:
            raise ValueError("Reference and latent scale must match target device")
        if self.device.type not in {"cpu", "cuda"}:
            raise ValueError("Runner supports CPU or CUDA")
        if model.config != reference.config:
            raise ValueError("Target and source reference architecture differ")
        if any(parameter.requires_grad for parameter in reference.parameters()):
            raise ValueError("Source reference must be frozen")
        if not 0 < epsilon < float("inf") or not 0 < energy_scale < float("inf"):
            raise ValueError("Epsilon and original-unit energy scale must be positive")
        validate_latent_scale(latent_scale)
        if selection_rule not in {
            "confidence",
            "online_best_lambda",
            "without_confidence",
            "fixed_retention",
            "full_finetuning",
            "source_error",
            "uncertainty",
            "drift",
        }:
            raise ValueError("Unsupported selection rule")
        if retention_kind not in {"latent", "parameter"}:
            raise ValueError("Unsupported retention kind")
        if selection_rule in {"source_error", "uncertainty", "drift"}:
            if proxy_config is None:
                raise ValueError("Proxy selection requires a locked Development configuration")
            proxy_config.validate(controller, selection_rule)
        elif proxy_config is not None:
            raise ValueError("Proxy configuration requires a proxy selection rule")
        if selection_rule == "full_finetuning" and controller.initial_level != 0.0:
            raise ValueError("Full fine-tuning must start at lambda zero")
        if selection_rule == "fixed_retention" and controller.initial_level == 0.0:
            raise ValueError("Fixed retention must start at a positive lambda")
        self.binding = deepcopy(binding)
        self.controller = controller
        self.selection_rule = selection_rule
        self.retention_kind = retention_kind
        self.proxy_config = proxy_config
        self.epsilon = epsilon
        self.energy_scale = energy_scale
        self.reference = deepcopy(reference).eval()
        self.reference.encoder.flatten_parameters()
        self.latent_scale = latent_scale.detach().clone()
        self.active_model, self.active_optimizer = _copy_pair(model, optimizer)
        self.current_level = controller.initial_level
        self.block_id = 0
        self.next_index = 0
        self.candidates: list[tuple[ForecastGRU, torch.optim.Adam]] = []
        self.audit: tuple[float, ForecastGRU, torch.optim.Adam] | None = None
        self.audit_rng: Tensor | None = None
        self.audit_cuda_rng: Tensor | None = None
        self.pending: dict[str, Any] | None = None
        self.late_pending: dict[str, dict[str, Any]] = {}
        self.days: list[DailyScore] = []
        self.issued: list[dict[str, Any]] = []
        self.decisions: list[Decision] = []
        self.events: list[str] = []
        self.update_steps = [0, 0, 0]
        self.audit_steps = 0
        self.runtime_costs = _runtime_costs(complete=True)
        self.proxy_costs = _empty_cost_record()
        if self.device.type == "cuda":
            self.runtime_costs["scope"] = (
                "CUDA synchronized model.forward and target_step calls only"
            )
        self._fork()

    def _cuda_rng(self) -> Tensor | None:
        return torch.cuda.get_rng_state(self.device).clone() if self.device.type == "cuda" else None

    def _set_cuda_rng(self, state: Tensor | None) -> None:
        if self.device.type == "cuda":
            if state is None:
                raise ValueError("CUDA RNG state is missing")
            torch.cuda.set_rng_state(state, self.device)

    def _synchronize(self) -> None:
        if self.device.type == "cuda":
            torch.cuda.synchronize(self.device)

    def _fork(self) -> None:
        self.candidates = [
            _copy_pair(self.active_model, self.active_optimizer) for _ in self.controller.levels
        ]
        self.events.append(f"fork:{self.block_id}")

    def state_tensor_memory(self) -> dict[str, Any]:
        """Snapshot logical model/optimizer tensor bytes for each trajectory."""
        return {
            "schema": "hung-sprint2-state-tensor-memory-v1",
            "unit": "bytes",
            "scope": "current model and optimizer state tensors; not peak RSS or activations",
            "active": model_optimizer_tensor_bytes(self.active_model, self.active_optimizer),
            "reference": model_tensor_bytes(self.reference),
            "latent_scale": self.latent_scale.numel() * self.latent_scale.element_size(),
            "candidate": [model_optimizer_tensor_bytes(*pair) for pair in self.candidates],
            "audit": None
            if self.audit is None
            else model_optimizer_tensor_bytes(self.audit[1], self.audit[2]),
        }

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
            raise ValueError("Runner inputs must be CPU tensors before transfer")
        if x_hist.shape != (1, 24, 7) or c_future.shape != (1, 24, 5):
            raise ValueError("Forecast tensors must have shapes [1,24,7] and [1,24,5]")
        forecasts = []
        model_x = x_hist.to(self.device)
        model_calendar = c_future.to(self.device)
        with torch.no_grad():
            source_forecast = None
            if self.proxy_config is not None:
                started = perf_counter_ns()
                source_output = self.reference(model_x, model_calendar)
                self._synchronize()
                elapsed = perf_counter_ns() - started
                source_forecast = source_output.detach().cpu().clone()
                self.proxy_costs["inference_calls"] += 1
                self.proxy_costs["inference_ns"] += elapsed
            for index, (model, _) in enumerate(self.candidates):
                model.eval()
                started = perf_counter_ns()
                output = model(model_x, model_calendar)
                self._synchronize()
                elapsed = perf_counter_ns() - started
                forecasts.append(output.detach().cpu().clone())
                cost = self.runtime_costs["candidate"][index]
                cost["inference_calls"] += 1
                cost["inference_ns"] += elapsed
            audit_forecast = None
            if self.audit is not None:
                self.audit[1].eval()
                started = perf_counter_ns()
                audit_output = self.audit[1](model_x, model_calendar)
                self._synchronize()
                elapsed = perf_counter_ns() - started
                audit_forecast = audit_output.detach().cpu().clone()
                self.runtime_costs["audit"]["inference_calls"] += 1
                self.runtime_costs["audit"]["inference_ns"] += elapsed
        self.pending = {
            "day_id": origin.day_id,
            "index": origin.index,
            "block_id": self.block_id,
            "status": "created",
            "issued_index": len(self.issued),
            "x_hist": x_hist,
            "c_future": c_future,
            "forecasts": forecasts,
            "audit_forecast": audit_forecast,
            "source_forecast": source_forecast,
        }
        proxy_value = None
        if self.selection_rule == "uncertainty":
            # Deterministic within-horizon Source dispersion; a heuristic to
            # validate on Development, not a calibrated predictive interval.
            proxy_value = float(source_forecast.std(unbiased=False))
        elif self.selection_rule == "drift":
            # x_hist channel zero is scaled historical load in the bound schema.
            observed = x_hist[0, :, 0][x_hist[0, :, 6] == 1]
            if observed.numel():
                descriptor = float(observed.mean())
                proxy_value = abs(descriptor - self.proxy_config.drift_reference_mean) / (
                    self.proxy_config.drift_reference_scale
                )
        self.issued.append(
            {
                "day_id": origin.day_id,
                "index": origin.index,
                "block_id": self.block_id,
                "active_level": self.current_level,
                "forecasts": [forecast.clone() for forecast in forecasts],
                "audit_forecast": audit_forecast,
                "source_forecast": source_forecast,
                "proxy_value": proxy_value,
                "normalized_mae": None,
                "mae_kwh": None,
                "y_scaled": None,
                "audit_normalized_mae": None,
                "audit_mae_kwh": None,
            }
        )
        self.events.append(f"forecast:{origin.day_id}")

    def arrive(self, label: LabelArrival) -> None:
        """Score stored forecasts, then train each candidate on complete labels."""
        current = self.pending is not None and label.day_id == self.pending["day_id"]
        pending = self.pending if current else self.late_pending.get(label.day_id)
        if pending is None:
            raise ValueError("Label event has no matching issued/scheduled origin")
        if not current and not label.arrived:
            raise ValueError("Deferred label event must contain complete arrived labels")
        if label.deferred and (label.arrived or not current or pending["status"] != "created"):
            raise ValueError("Only a current created origin may defer unavailable labels")
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
                issued_index = pending.get("issued_index")
                if issued_index is None:
                    issued_index = next(
                        (
                            index
                            for index, item in enumerate(self.issued)
                            if item["day_id"] == label.day_id
                        ),
                        None,
                    )
                if issued_index is None:
                    raise ValueError("Stored forecast is missing for arrived label")
                issued = self.issued[issued_index]
                issued["normalized_mae"] = scores
                issued["mae_kwh"] = tuple(value * self.energy_scale for value in scores)
                issued["y_scaled"] = y.squeeze(0).clone()
                if self.selection_rule == "source_error":
                    issued["proxy_value"] = float(torch.abs(pending["source_forecast"] - y).mean())
                if pending["audit_forecast"] is not None:
                    audit_mae = float(torch.abs(pending["audit_forecast"] - y).mean())
                    issued["audit_normalized_mae"] = audit_mae
                    issued["audit_mae_kwh"] = audit_mae * self.energy_scale
                self.events.append(f"score:{label.day_id}")
                shared_rng = torch.get_rng_state().clone()
                shared_cuda_rng = self._cuda_rng()
                post_rng: Tensor | None = None
                post_cuda_rng: Tensor | None = None
                model_y = y.to(self.device)
                for index, (model, optimizer) in enumerate(self.candidates):
                    torch.set_rng_state(shared_rng)
                    self._set_cuda_rng(shared_cuda_rng)
                    started = perf_counter_ns()
                    target_step(
                        model,
                        self.reference,
                        optimizer,
                        pending["x_hist"].to(self.device),
                        pending["c_future"].to(self.device),
                        model_y,
                        retention_weight=self.controller.levels[index],
                        latent_scale=self.latent_scale,
                        epsilon=self.epsilon,
                        retention_kind=self.retention_kind,
                    )
                    self._synchronize()
                    elapsed = perf_counter_ns() - started
                    if post_rng is None:
                        post_rng = torch.get_rng_state().clone()
                        post_cuda_rng = self._cuda_rng()
                    self.update_steps[index] += 1
                    cost = self.runtime_costs["candidate"][index]
                    cost["update_steps"] += 1
                    cost["update_ns"] += elapsed
                if post_rng is not None:
                    torch.set_rng_state(post_rng)
                    self._set_cuda_rng(post_cuda_rng)
                self.events.append(f"update:{label.day_id}")
                if self.audit is not None:
                    level, model, optimizer = self.audit
                    live_rng = torch.get_rng_state().clone()
                    live_cuda_rng = self._cuda_rng()
                    try:
                        torch.set_rng_state(self.audit_rng)
                        self._set_cuda_rng(self.audit_cuda_rng)
                        started = perf_counter_ns()
                        target_step(
                            model,
                            self.reference,
                            optimizer,
                            pending["x_hist"].to(self.device),
                            pending["c_future"].to(self.device),
                            model_y,
                            retention_weight=level,
                            latent_scale=self.latent_scale,
                            epsilon=self.epsilon,
                            retention_kind=self.retention_kind,
                        )
                        self._synchronize()
                        elapsed = perf_counter_ns() - started
                        self.audit_rng = torch.get_rng_state().clone()
                        self.audit_cuda_rng = self._cuda_rng()
                    finally:
                        torch.set_rng_state(live_rng)
                        self._set_cuda_rng(live_cuda_rng)
                    self.audit_steps += 1
                    self.runtime_costs["audit"]["update_steps"] += 1
                    self.runtime_costs["audit"]["update_ns"] += elapsed
                    self.events.append(f"audit-update:{label.day_id}")
        daily = DailyScore(label.day_id, label.arrived, bool(valid), scores)
        if current:
            self.days.append(daily)
        elif pending["block_id"] == self.block_id:
            for index, day in enumerate(self.days):
                if day.day_id == label.day_id:
                    self.days[index] = daily
                    break
            else:
                raise ValueError("Deferred day is absent from its current block")
        if scores is None:
            self.events.append(f"unscored:{label.day_id}")
        if current:
            if label.deferred:
                pending.setdefault("block_id", self.block_id)
                self.late_pending[label.day_id] = pending
            self.pending = None
            self.next_index += 1
        else:
            del self.late_pending[label.day_id]

    def finish_block(self) -> Decision:
        """Decide and carry the selected *trained* state into the next block."""
        if self.pending is not None:
            raise ValueError("Cannot decide before the final label event")
        if len(self.days) != self.controller.block_days:
            raise ValueError("A block requires its complete scheduled-day count")
        if self.selection_rule == "confidence":
            decision = decide_block(
                self.controller,
                current_level=self.current_level,
                block_id=self.block_id,
                days=self.days,
            )
        elif self.selection_rule in {"fixed_retention", "full_finetuning"}:
            decision = decide_fixed_block(
                self.controller,
                current_level=self.current_level,
                days=self.days,
                rule=self.selection_rule,
            )
        elif self.proxy_config is not None:
            values = [
                item["proxy_value"]
                for item in self.issued
                if item["block_id"] == self.block_id and item["proxy_value"] is not None
            ]
            decision = decide_proxy_block(
                self.controller,
                current_level=self.current_level,
                scheduled_days=len(self.days),
                values=values,
                config=self.proxy_config,
                rule=self.selection_rule,
            )
        else:
            decision = decide_mean_block(
                self.controller,
                current_level=self.current_level,
                days=self.days,
                rule=self.selection_rule,
            )
        current_index = self.controller.levels.index(self.current_level)
        selected_index = self.controller.levels.index(decision.selected_level)
        old_active = self.candidates[current_index]
        self.active_model, self.active_optimizer = self.candidates[selected_index]
        self.audit = (self.current_level, *old_active) if decision.switched else None
        self.audit_rng = torch.get_rng_state().clone() if decision.switched else None
        self.audit_cuda_rng = self._cuda_rng() if decision.switched else None
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
            "selection_rule": self.selection_rule,
            "retention_kind": self.retention_kind,
            "proxy_config": None if self.proxy_config is None else asdict(self.proxy_config),
            "model_config": self.active_model.config.to_dict(),
            "epsilon": self.epsilon,
            "energy_scale": self.energy_scale,
            "reference": self.reference.state_dict(),
            "latent_scale": self.latent_scale.clone(),
            "active": pair_state((self.active_model, self.active_optimizer)),
            "candidates": [pair_state(pair) for pair in self.candidates],
            "audit": None
            if self.audit is None
            else {"level": self.audit[0], **pair_state((self.audit[1], self.audit[2]))},
            "audit_rng": None if self.audit_rng is None else self.audit_rng.clone(),
            "audit_cuda_rng": None if self.audit_cuda_rng is None else self.audit_cuda_rng.clone(),
            "device_type": self.device.type,
            "current_level": self.current_level,
            "block_id": self.block_id,
            "next_index": self.next_index,
            "pending": deepcopy(self.pending),
            "late_pending": deepcopy(self.late_pending),
            "days": [asdict(day) for day in self.days],
            "issued": deepcopy(self.issued),
            "decisions": [asdict(decision) for decision in self.decisions],
            "events": list(self.events),
            "update_steps": list(self.update_steps),
            "audit_steps": self.audit_steps,
            "runtime_costs": deepcopy(self.runtime_costs),
            "proxy_costs": deepcopy(self.proxy_costs),
            "torch_rng": torch.get_rng_state().clone(),
            "cuda_rng": self._cuda_rng(),
        }

    @classmethod
    def from_state_dict(
        cls, state: dict, *, expected_binding: dict, device: str | torch.device = "cpu"
    ) -> PrequentialRunner:
        """Restore a validated bound state without replaying past events."""
        validate_binding(expected_binding)
        if (
            state.get("schema") != "hung-sprint2-runner-v1"
            or state.get("binding") != expected_binding
        ):
            raise ValueError("Runner checkpoint schema/input binding mismatch")
        device = torch.device(device)
        if state.get("device_type", "cpu") != device.type:
            raise ValueError("Runner checkpoint device type mismatch")
        if device.type == "cuda" and not torch.cuda.is_available():
            raise ValueError("CUDA is unavailable for runner resume")
        config = ModelConfig(**state["model_config"])

        def pair_from(payload: dict) -> tuple[ForecastGRU, torch.optim.Adam]:
            model = ForecastGRU(config).to(device)
            model.load_state_dict(payload["model"])
            model.encoder.flatten_parameters()
            optimizer = torch.optim.Adam(model.parameters(), lr=1.0)
            optimizer.load_state_dict(payload["optimizer"])
            return model, optimizer

        runner = cls.__new__(cls)
        runner.device = device
        runner.binding = deepcopy(expected_binding)
        runner.controller = ControllerConfig(**state["controller"])
        runner.selection_rule = state.get("selection_rule", "confidence")
        runner.retention_kind = state.get("retention_kind", "latent")
        if runner.retention_kind not in {"latent", "parameter"}:
            raise ValueError("Runner checkpoint retention kind mismatch")
        if runner.selection_rule not in {
            "confidence",
            "online_best_lambda",
            "without_confidence",
            "fixed_retention",
            "full_finetuning",
            "source_error",
            "uncertainty",
            "drift",
        }:
            raise ValueError("Runner checkpoint selection rule mismatch")
        proxy_payload = state.get("proxy_config")
        runner.proxy_config = None if proxy_payload is None else ProxyConfig(**proxy_payload)
        if runner.selection_rule in {"source_error", "uncertainty", "drift"}:
            if runner.proxy_config is None:
                raise ValueError("Proxy checkpoint lacks configuration")
            runner.proxy_config.validate(runner.controller, runner.selection_rule)
        elif runner.proxy_config is not None:
            raise ValueError("Nonproxy checkpoint has proxy configuration")
        if runner.selection_rule == "full_finetuning" and runner.controller.initial_level != 0.0:
            raise ValueError("Full fine-tuning checkpoint must start at lambda zero")
        if runner.selection_rule == "fixed_retention" and runner.controller.initial_level == 0.0:
            raise ValueError("Fixed retention checkpoint must start at positive lambda")
        runner.epsilon = state["epsilon"]
        runner.energy_scale = state["energy_scale"]
        runner.reference = ForecastGRU(config).to(device).eval()
        runner.reference.load_state_dict(state["reference"])
        runner.reference.requires_grad_(False)
        runner.latent_scale = state["latent_scale"].to(device).clone()
        validate_latent_scale(runner.latent_scale)
        runner.active_model, runner.active_optimizer = pair_from(state["active"])
        runner.candidates = [pair_from(payload) for payload in state["candidates"]]
        if len(runner.candidates) != 3:
            raise ValueError("Runner checkpoint must contain three candidates")
        audit = state["audit"]
        runner.audit = None if audit is None else (audit["level"], *pair_from(audit))
        runner.audit_rng = state["audit_rng"]
        runner.audit_cuda_rng = state.get("audit_cuda_rng")
        runner.current_level = state["current_level"]
        if runner.selection_rule in {"fixed_retention", "full_finetuning"} and (
            runner.current_level != runner.controller.initial_level
        ):
            raise ValueError("Fixed-policy checkpoint changed its selected level")
        runner.block_id = state["block_id"]
        runner.next_index = state["next_index"]
        runner.pending = state["pending"]
        runner.late_pending = state.get("late_pending", {})
        runner.days = [DailyScore(**day) for day in state["days"]]
        runner.issued = state["issued"]
        runner.decisions = [Decision(**decision) for decision in state["decisions"]]
        runner.events = state["events"]
        runner.update_steps = state["update_steps"]
        runner.audit_steps = state["audit_steps"]
        runner.runtime_costs = _validated_runtime_costs(
            state.get("runtime_costs", _runtime_costs(complete=False)),
            runner.update_steps,
            runner.audit_steps,
            device.type,
        )
        runner.proxy_costs = deepcopy(state.get("proxy_costs", _empty_cost_record()))
        if (
            not isinstance(runner.proxy_costs, dict)
            or set(runner.proxy_costs) != set(_empty_cost_record())
            or any(type(value) is not int or value < 0 for value in runner.proxy_costs.values())
            or runner.proxy_costs["update_steps"] != 0
            or runner.proxy_costs["update_ns"] != 0
            or runner.proxy_costs["inference_calls"]
            != sum(item.get("source_forecast") is not None for item in runner.issued)
        ):
            raise ValueError("Proxy checkpoint cost accounting mismatch")
        torch.set_rng_state(state["torch_rng"])
        runner._set_cuda_rng(state.get("cuda_rng"))
        return runner
