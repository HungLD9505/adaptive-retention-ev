"""Explicit comparison policies; example proxy mappings need Development selection."""

import copy
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Sequence

import torch

from ev_control.confidence import ALGORITHM, ControllerConfig, DailyScore, Decision, decide
from ev_models.model import ForecastGRU
from ev_runner.state import identity

METHODS = (
    "without_confidence",
    "adaptive",
    "seasonal_naive",
    "target_only",
    "frozen_source",
    "full_finetuning",
    "fixed_retention",
    "online_best",
    "source_error",
    "uncertainty",
    "drift",
    "parameter_retention",
    "without_source_initialization",
    "block7",
    "block28",
)


@dataclass(frozen=True)
class Method:
    name: str
    fixed_lambda: float = 0.01
    proxy_thresholds: tuple[float, float] = (0.1, 0.5)
    proxy_order: tuple[int, int, int] = (0, 1, 2)

    def __post_init__(self) -> None:
        if self.name not in METHODS:
            raise ValueError("Unknown method")
        if not math.isfinite(self.fixed_lambda) or self.fixed_lambda < 0:
            raise ValueError("Invalid fixed lambda")
        if (
            len(self.proxy_thresholds) != 2
            or not all(math.isfinite(x) and x >= 0 for x in self.proxy_thresholds)
            or self.proxy_thresholds[0] >= self.proxy_thresholds[1]
        ):
            raise ValueError("Explicit ordered proxy thresholds required")
        if tuple(sorted(self.proxy_order)) != (0, 1, 2):
            raise ValueError("Proxy mapping must be a permutation of level indices")

    @property
    def multiple(self) -> bool:
        return self.name in {
            "without_confidence",
            "adaptive",
            "online_best",
            "source_error",
            "uncertainty",
            "drift",
            "parameter_retention",
            "without_source_initialization",
            "block7",
            "block28",
        }

    @property
    def updates(self) -> bool:
        return self.name != "frozen_source"

    @property
    def source_initialization(self) -> bool:
        return self.name not in {"target_only", "without_source_initialization", "seasonal_naive"}

    def levels(self, config: ControllerConfig) -> tuple[float, ...]:
        return (
            config.levels
            if self.multiple
            else (self.fixed_lambda if self.name == "fixed_retention" else 0.0,)
        )


def ablation_aliases(config: ControllerConfig, fixed_lambda: float) -> dict[str, str]:
    """Alias only genuinely identical definitions; never double-count their runs."""
    result = {"fixed_lambda": "fixed_retention"}
    if config.delta == 0:
        result["without_confidence"] = "online_best"
    # Nonzero delta requires its own mean-margin ablation, not an incorrect alias.
    if config.delta != 0:
        result["without_confidence"] = "without_confidence"
    if fixed_lambda not in config.levels:
        raise ValueError("Fixed-retention ablation must match a configured level")
    return result


def descriptor(record: dict) -> tuple[float, float, float]:
    values = [row[0] for row in record["x_hist"] if row[-1]]
    if not values:
        raise ValueError("No observed history for drift descriptor")
    return sum(values) / len(values), max(values), sum(x == 0 for x in values) / len(values)


class Policy:
    def __init__(
        self,
        method: Method,
        reference: ForecastGRU | None,
        *,
        initial_records: list[dict],
        device: str,
        ensemble: tuple[ForecastGRU, ...] = (),
    ) -> None:
        self.method, self.reference, self.device, self.ensemble = (
            method,
            reference,
            device,
            ensemble,
        )
        if any(
            model.training or any(p.requires_grad for p in model.parameters())
            for model in (reference, *ensemble)
            if model is not None
        ):
            raise ValueError("Proxy Source estimators must be frozen in evaluation mode")
        if method.name == "source_error" and reference is None:
            raise ValueError("Source-error proxy requires its frozen Source")
        if method.name == "uncertainty" and len(ensemble) < 3:
            raise ValueError("Uncertainty proxy requires at least three identified source members")
        self.signals = []
        descriptions = [descriptor(r) for r in initial_records]
        self.reference_descriptor = (
            [sum(x[k] for x in descriptions) / len(descriptions) for k in range(3)]
            if descriptions
            else None
        )
        self.reference_std = (
            [
                math.sqrt(
                    sum((x[k] - self.reference_descriptor[k]) ** 2 for x in descriptions)
                    / len(descriptions)
                )
                or 1.0
                for k in range(3)
            ]
            if descriptions
            else None
        )

    @property
    def updates(self) -> bool:
        return self.method.updates

    def levels(self, config: ControllerConfig) -> tuple[float, ...]:
        return self.method.levels(config)

    def snapshot(self) -> dict:
        return copy.deepcopy(
            {
                "method": asdict(self.method),
                "signals": self.signals,
                "reference_descriptor": self.reference_descriptor,
                "reference_std": self.reference_std,
            }
        )

    def restore(self, value: dict) -> None:
        if value["method"] != asdict(self.method):
            raise ValueError("Resume method differs")
        self.signals = copy.deepcopy(value["signals"])
        self.reference_descriptor = value["reference_descriptor"]
        self.reference_std = value["reference_std"]

    def predict(self, record: dict) -> dict:
        name = self.method.name
        if name not in {"source_error", "uncertainty", "drift"}:
            return {}
        origin = record["origin"]
        if name == "drift":
            desc = descriptor(record)
            if self.reference_descriptor is None:
                # Prefix with no trainable windows: initialize from first available X,
                # never from future labels or full-release activity statistics.
                self.reference_descriptor, self.reference_std = list(desc), [1.0] * 3
            signal = math.sqrt(
                sum(
                    ((a - b) / s) ** 2
                    for a, b, s in zip(
                        desc, self.reference_descriptor, self.reference_std, strict=True
                    )
                )
                / 3
            )
            self.signals.append({"origin": origin, "value": signal, "available_at": origin})
            return {"signal": signal}
        x = torch.tensor([record["x_hist"]], dtype=torch.float32, device=self.device)
        c = torch.tensor([record["c_future"]], dtype=torch.float32, device=self.device)
        with torch.no_grad():
            if name == "source_error":
                prediction = self.reference(x, c)[0]
                if not torch.isfinite(prediction).all():
                    raise ValueError("Nonfinite frozen-Source forecast")
                return {"source_prediction": prediction.cpu().tolist()}
            members = torch.stack([model(x, c)[0] for model in self.ensemble])
            if not torch.isfinite(members).all():
                raise ValueError("Nonfinite uncertainty-member forecast")
            signal = members.std(0, correction=0).mean().item()
        self.signals.append({"origin": origin, "value": signal, "available_at": origin})
        return {"signal": signal}

    def observe(self, issued: dict, labels: list[float], as_of: datetime) -> None:
        if self.method.name == "source_error":
            prediction = issued["proxy"]["source_prediction"]
            value = sum(abs(a - b) for a, b in zip(prediction, labels, strict=True)) / 24
            self.signals.append(
                {"origin": issued["origin"], "value": value, "available_at": as_of.isoformat()}
            )

    def choose(
        self,
        rows: Sequence[DailyScore],
        *,
        config: ControllerConfig,
        active_lambda: float,
        block_start: datetime,
        as_of: datetime,
        stream_id: str,
        scale_id: str,
    ) -> Decision:
        if self.method.name in {
            "adaptive",
            "parameter_retention",
            "without_source_initialization",
            "block7",
            "block28",
        }:
            return decide(
                rows,
                config=config,
                active_lambda=active_lambda,
                block_start=block_start,
                as_of=as_of,
                stream_id=stream_id,
                scale_id=scale_id,
            )
        valid = [
            r
            for r in rows
            if r.available_at is not None
            and r.available_at <= as_of
            and r.valid_labels == 24
            and r.mae is not None
        ]
        levels = self.method.levels(config)
        selected, reason = active_lambda, "fixed_policy"
        statistics = {}
        if self.method.name in {"online_best", "without_confidence"}:
            if len(valid) >= config.min_valid_days:
                means = [sum(r.mae[i] for r in valid) / len(valid) for i in range(3)]
                best = min(range(3), key=lambda i: (means[i], abs(levels[i] - active_lambda), i))
                selected, reason = levels[best], "lowest_observed_mean"
                if (
                    self.method.name == "without_confidence"
                    and means[levels.index(active_lambda)] - means[best] <= config.delta
                ):
                    selected, reason = active_lambda, "mean_margin_not_met"
                statistics = {
                    "mean_daily_mae": means,
                    "statistic": "observed mean, not confidence bound",
                }
            else:
                reason = "insufficient_valid_days"
        elif self.method.name in {"source_error", "uncertainty", "drift"}:
            valid_origins = {r.origin.isoformat() for r in valid}
            signals = [
                s["value"]
                for s in self.signals
                if s["origin"] in valid_origins
                and block_start <= datetime.fromisoformat(s["origin"]) < as_of
                and datetime.fromisoformat(s["available_at"]) <= as_of
            ]
            if len(signals) >= config.min_valid_days:
                signal = sum(signals) / len(signals)
                index = sum(signal >= threshold for threshold in self.method.proxy_thresholds)
                statistics = {"mean_available_signal": signal, "signal_days": len(signals)}
                selected = levels[self.method.proxy_order[index]]
                reason = f"{self.method.name}_mapped_available_signal"
            else:
                reason = "insufficient_available_proxy_days"
        origins = tuple(r.origin.isoformat() for r in valid)
        return Decision(
            ALGORITHM + "/" + self.method.name,
            stream_id,
            scale_id,
            block_start.isoformat(),
            as_of.isoformat(),
            active_lambda,
            selected,
            reason,
            len(valid),
            sum(r.available_at is None or r.available_at > as_of for r in rows),
            sum(
                r.available_at is not None and r.available_at <= as_of and r.valid_labels != 24
                for r in rows
            ),
            config.block_days - len(rows),
            0,
            origins,
            (),
            {
                **asdict(config),
                "method_statistics": statistics,
                "method": asdict(self.method),
                "comparison_statistic": "mean improvement, NOT LCB"
                if self.method.name == "online_best"
                else "proxy/fixed policy",
            },
            config.seed,
            identity([(r.origin.isoformat(), r.mae) for r in valid]),
        )
