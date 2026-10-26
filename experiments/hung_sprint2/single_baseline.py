"""One-model Target-only/Frozen-Source replay on the accepted daily event schedule."""

from __future__ import annotations

import math
import re
import time
from copy import deepcopy
from types import SimpleNamespace

import torch

from experiments.hung_sprint2.model import ForecastGRU, ModelConfig
from experiments.hung_sprint2.runner import LabelArrival, Origin
from experiments.hung_sprint2.seasonal_naive import forecast_previous_day
from experiments.hung_sprint2.training import source_step

METHODS = ("target_only", "frozen_source", "seasonal_naive")
BINDING_FIELDS = {
    "schema",
    "method",
    "feature_schema",
    "input_manifest_sha256",
    "input_run_id",
    "dataset_id",
    "city_id",
    "entity_id",
    "history_days",
    "scale_id",
    "initial_checkpoint_sha256",
    "source_checkpoint_sha256",
    "source_input_manifest_sha256",
}


def validate_single_binding(binding: dict) -> None:
    if not isinstance(binding, dict) or set(binding) != BINDING_FIELDS:
        raise ValueError("Single-model input binding fields differ")
    if binding["schema"] != "hung-single-baseline-binding-v1" or binding["method"] not in METHODS:
        raise ValueError("Unsupported single-model binding")
    if binding["feature_schema"] != "ev-input-v1" or binding["history_days"] not in (7, 14, 28):
        raise ValueError("Single-model feature/history contract differs")
    for key in ("input_run_id", "dataset_id", "city_id", "entity_id", "scale_id"):
        if not isinstance(binding[key], str) or not binding[key]:
            raise ValueError(f"Missing single-model {key}")
    if not isinstance(binding["input_manifest_sha256"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", binding["input_manifest_sha256"]
    ):
        raise ValueError("Invalid single-model input_manifest_sha256")
    initial_sha = binding["initial_checkpoint_sha256"]
    if binding["method"] == "seasonal_naive":
        if any(binding[key] is not None for key in (
            "initial_checkpoint_sha256", "source_checkpoint_sha256",
            "source_input_manifest_sha256",
        )):
            raise ValueError("Seasonal Naive must not use a model or Source checkpoint")
        return
    if not isinstance(initial_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", initial_sha):
        raise ValueError("Invalid single-model initial_checkpoint_sha256")
    source_sha = binding["source_checkpoint_sha256"]
    source_manifest = binding["source_input_manifest_sha256"]
    if binding["method"] == "target_only" and (
        source_sha is not None or source_manifest is not None
    ):
        raise ValueError("Target-only must not use a Source checkpoint")
    if binding["method"] == "frozen_source" and source_sha != binding["initial_checkpoint_sha256"]:
        raise ValueError("Frozen Source must bind its exact Source checkpoint")
    if binding["method"] == "frozen_source" and (
        not isinstance(source_manifest, str) or not re.fullmatch(r"[0-9a-f]{64}", source_manifest)
    ):
        raise ValueError("Frozen Source must bind its Source input manifest")


class SingleBaselineRunner:
    """Issue one forecast per created day; update Target-only only on complete arrivals."""

    def __init__(
        self,
        model: ForecastGRU | None,
        optimizer: torch.optim.Adam | None,
        *,
        binding: dict,
        energy_scale: float,
        block_days: int,
    ) -> None:
        validate_single_binding(binding)
        if not math.isfinite(energy_scale) or energy_scale <= 0 or block_days < 1:
            raise ValueError("Invalid single-model scale/block length")
        if (binding["method"] == "target_only") != (optimizer is not None):
            raise ValueError("Target-only requires Adam; fixed baselines forbid updates")
        if (binding["method"] == "seasonal_naive") != (model is None):
            raise ValueError("Only Seasonal Naive is model-free")
        self.binding = deepcopy(binding)
        self.method = binding["method"]
        self.model = model
        self.optimizer = optimizer
        self.device = torch.device("cpu") if model is None else next(model.parameters()).device
        if self.device.type not in ("cpu", "cuda"):
            raise ValueError("Unsupported model device")
        if self.method == "frozen_source":
            self.model.eval().requires_grad_(False)
        self.energy_scale = energy_scale
        self.controller = SimpleNamespace(block_days=block_days)
        self.next_index = self.block_id = 0
        self.pending: dict | None = None
        self.late_pending: dict[str, dict] = {}
        self.days: list[str] = []
        self.issued: list[dict] = []
        self.events: list[str] = []
        self.seen_days: set[str] = set()
        self.cost = {
            "inference_calls": 0,
            "inference_ns": 0,
            "update_steps": 0,
            "update_ns": 0,
            "candidate_count": 1,
            "audit_calls": 0,
            "fallback_hours": 0,
        }

    def _sync(self) -> None:
        if self.device.type == "cuda":
            torch.cuda.synchronize(self.device)

    def forecast(self, origin: Origin) -> None:
        if self.pending is not None or len(self.days) == self.controller.block_days:
            raise ValueError("Previous event/block is unfinished")
        if origin.index != self.next_index or not origin.day_id or origin.day_id in self.seen_days:
            raise ValueError("Forecast origin sequence differs")
        if origin.status == "skipped_all_missing_history":
            if origin.x_hist is not None or origin.c_future is not None:
                raise ValueError("Skipped origin has predictor tensors")
            self.pending = {
                "day_id": origin.day_id,
                "index": origin.index,
                "status": origin.status,
                "block_id": self.block_id,
            }
            self.seen_days.add(origin.day_id)
            self.events.append(f"skip:{origin.day_id}")
            return
        if origin.status != "created" or origin.x_hist is None or origin.c_future is None:
            raise ValueError("Created origin requires predictor tensors")
        x, calendar = origin.x_hist.detach().clone(), origin.c_future.detach().clone()
        if x.device.type != "cpu" or calendar.device.type != "cpu":
            raise ValueError("Forecast inputs must arrive on CPU")
        if x.shape != (1, 24, 7) or calendar.shape != (1, 24, 5):
            raise ValueError("Forecast input shape differs")
        self._sync()
        start = time.perf_counter_ns()
        fallback_hours = 0
        if self.method == "seasonal_naive":
            seasonal = forecast_previous_day(x.squeeze(0))
            prediction = seasonal.scaled_kwh.unsqueeze(0)
            fallback_hours = seasonal.fallback_hours
        else:
            self.model.eval()
            with torch.no_grad():
                prediction = self.model(x.to(self.device), calendar.to(self.device)).cpu()
        self._sync()
        self.cost["inference_calls"] += 1
        self.cost["inference_ns"] += time.perf_counter_ns() - start
        self.cost["fallback_hours"] += fallback_hours
        if not torch.isfinite(prediction).all() or torch.any(prediction < 0):
            raise ValueError("Single-model forecast is invalid")
        self.pending = {
            "day_id": origin.day_id,
            "index": origin.index,
            "block_id": self.block_id,
            "status": "created",
            "x_hist": x,
            "c_future": calendar,
            "prediction": prediction.clone(),
            "fallback_hours": fallback_hours,
        }
        self.issued.append(
            {
                "day_id": origin.day_id,
                "index": origin.index,
                "block_id": self.block_id,
                "prediction": prediction.clone(),
                "fallback_hours": fallback_hours,
                "normalized_mae": None,
                "mae_kwh": None,
                "y_scaled": None,
            }
        )
        self.seen_days.add(origin.day_id)
        self.events.append(f"forecast:{origin.day_id}")

    def arrive(self, label: LabelArrival) -> None:
        current = self.pending is not None and label.day_id == self.pending["day_id"]
        pending = self.pending if current else self.late_pending.get(label.day_id)
        if pending is None or (not current and not label.arrived):
            raise ValueError("Label event has no matching pending origin")
        if label.deferred and (not current or label.arrived or pending["status"] != "created"):
            raise ValueError("Only a current created forecast may defer labels")
        if not label.arrived and (label.y_scaled is not None or label.valid is not None):
            raise ValueError("Unavailable label values cannot enter runner")
        if label.arrived and (
            label.y_scaled is None
            or label.valid is None
            or label.y_scaled.shape != (24,)
            or label.valid.shape != (24,)
            or label.valid.dtype != torch.bool
        ):
            raise ValueError("Arrived label requires 24 values and validity bits")
        valid = label.arrived and bool(label.valid.all())
        if valid and pending["status"] == "created":
            y = label.y_scaled.detach().clone()
            if y.device.type != "cpu" or not torch.isfinite(y).all() or torch.any(y < 0):
                raise ValueError("Complete label vector is invalid")
            forecast = pending["prediction"].squeeze(0)
            mae = float(torch.abs(forecast - y).mean())
            issued = next(row for row in self.issued if row["day_id"] == label.day_id)
            issued.update(normalized_mae=mae, mae_kwh=mae * self.energy_scale, y_scaled=y)
            self.events.append(f"score:{label.day_id}")
            if self.method == "target_only":
                self._sync()
                start = time.perf_counter_ns()
                source_step(
                    self.model,
                    self.optimizer,
                    pending["x_hist"].to(self.device),
                    pending["c_future"].to(self.device),
                    y.unsqueeze(0).to(self.device),
                )
                self._sync()
                self.cost["update_steps"] += 1
                self.cost["update_ns"] += time.perf_counter_ns() - start
                self.events.append(f"update:{label.day_id}")
        else:
            self.events.append(f"unscored:{label.day_id}")
        if current:
            self.days.append(label.day_id)
            if label.deferred:
                self.late_pending[label.day_id] = pending
            self.pending = None
            self.next_index += 1
        else:
            del self.late_pending[label.day_id]

    def finish_block(self) -> None:
        if self.pending is not None or len(self.days) != self.controller.block_days:
            raise ValueError("Cannot finish incomplete single-model block")
        self.events.append(f"fixed:{self.block_id}:{self.method}")
        self.block_id += 1
        self.days = []

    def state_dict(self) -> dict:
        return {
            "schema": "hung-single-baseline-runner-v1",
            "binding": deepcopy(self.binding),
            "architecture": None if self.model is None else self.model.config.to_dict(),
            "model": None if self.model is None else self.model.state_dict(),
            "optimizer": None if self.optimizer is None else self.optimizer.state_dict(),
            "energy_scale": self.energy_scale,
            "block_days": self.controller.block_days,
            "device_type": self.device.type,
            "next_index": self.next_index,
            "block_id": self.block_id,
            "pending": deepcopy(self.pending),
            "late_pending": deepcopy(self.late_pending),
            "days": list(self.days),
            "issued": deepcopy(self.issued),
            "events": list(self.events),
            "seen_days": sorted(self.seen_days),
            "cost": deepcopy(self.cost),
            "torch_rng": torch.get_rng_state().clone(),
            "cuda_rng": torch.cuda.get_rng_state(self.device).clone()
            if self.device.type == "cuda"
            else None,
        }

    @classmethod
    def from_state_dict(
        cls,
        state: dict,
        *,
        expected_binding: dict,
        device: str | torch.device = "cpu",
    ) -> SingleBaselineRunner:
        validate_single_binding(expected_binding)
        if (
            state.get("schema") != "hung-single-baseline-runner-v1"
            or state.get("binding") != expected_binding
        ):
            raise ValueError("Single-model checkpoint binding/schema mismatch")
        device = torch.device(device)
        if state["device_type"] != device.type or (
            device.type == "cuda" and not torch.cuda.is_available()
        ):
            raise ValueError("Single-model checkpoint device differs")
        model = None
        if expected_binding["method"] == "seasonal_naive":
            if state["architecture"] is not None or state["model"] is not None:
                raise ValueError("Seasonal Naive checkpoint contains model weights")
        else:
            model = ForecastGRU(ModelConfig(**state["architecture"])).to(device)
            model.load_state_dict(state["model"])
            model.encoder.flatten_parameters()
        optimizer = None
        if expected_binding["method"] == "target_only":
            optimizer = torch.optim.Adam(model.parameters(), lr=1.0)
            optimizer.load_state_dict(state["optimizer"])
        elif state["optimizer"] is not None:
            raise ValueError("Fixed baseline checkpoint contains optimizer")
        runner = cls(
            model,
            optimizer,
            binding=expected_binding,
            energy_scale=state["energy_scale"],
            block_days=state["block_days"],
        )
        for name in (
            "next_index",
            "block_id",
            "pending",
            "late_pending",
            "days",
            "issued",
            "events",
            "cost",
        ):
            setattr(runner, name, deepcopy(state[name]))
        runner.seen_days = set(state["seen_days"])
        if len(runner.seen_days) != len(state["seen_days"]):
            raise ValueError("Duplicate forecast day in checkpoint")
        if runner.cost["candidate_count"] != 1 or runner.cost["audit_calls"] != 0:
            raise ValueError("Single-model cost accounting differs")
        if runner.method == "seasonal_naive" and (
            runner.cost["update_steps"] != 0
            or runner.cost["update_ns"] != 0
            or runner.cost["fallback_hours"]
            != sum(row["fallback_hours"] for row in runner.issued)
        ):
            raise ValueError("Seasonal Naive checkpoint cost accounting differs")
        torch.set_rng_state(state["torch_rng"])
        if device.type == "cuda":
            torch.cuda.set_rng_state(state["cuda_rng"], device)
        return runner
