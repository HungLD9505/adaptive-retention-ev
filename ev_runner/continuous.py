"""Single-branch chronological replay with arrived-label hypergradient decisions."""

import math
import time
from datetime import datetime, timedelta

import torch

from ev_control.continuous import ArrivedWindow, WindowRule, decide
from ev_control.paired import PairedRule, accept, propose
from ev_models.model import ForecastGRU
from ev_models.training import TrainingConfig
from ev_runner.diagnostics import measure
from ev_runner.replay import Replay
from ev_runner.state import Branch, identity, state_digest
from ev_runner.store import Store

DAY = timedelta(days=1)


class ContinuousRunner:
    """Resume only from committed daily boundaries, using one real Adam branch."""

    def __init__(
        self,
        replay: Replay,
        branch: Branch,
        reference: ForecastGRU,
        latent_scale: torch.Tensor,
        rule: WindowRule,
        training: TrainingConfig,
        store: Store,
        *,
        initial_lambda: float,
        device: str,
        cadence: int,
        frozen_lambda: bool = False,
        paired_rule: PairedRule | None = None,
    ) -> None:
        if not 0 <= initial_lambda <= rule.upper_bound or cadence < 1:
            raise ValueError("Invalid initial lambda or cadence")
        if paired_rule is not None and (
            frozen_lambda
            or cadence != 1
            or training.epochs != 1
            or initial_lambda != paired_rule.anchor
            or paired_rule.anchor > rule.upper_bound
        ):
            raise ValueError("Paired pilot needs one daily real step at its anchor")
        self.replay, self.branch, self.reference = replay, branch, reference
        self.latent_scale, self.rule, self.training, self.store = (
            latent_scale,
            rule,
            training,
            store,
        )
        self.current_lambda, self.device, self.cadence = initial_lambda, device, cadence
        self.frozen_lambda = frozen_lambda
        self.paired_rule = paired_rule
        self.active_block: dict | None = None
        self.next_block_id = 0
        self.last_update_for_pair: dict | None = None
        self.window = ArrivedWindow()
        self.pending: list[dict] = []
        self.next_at = replay.start
        self.arrivals = 0
        self.actual_steps = 0
        self.virtual_steps = 0
        self.cost = {"inference_seconds": 0.0, "actual_update_seconds": 0.0, "meta_seconds": 0.0}
        if paired_rule is not None:
            self.cost["paired_seconds"] = 0.0
        self.source_state_sha256 = state_digest(reference.state_dict())
        if store.restored is not None:
            self.restore(store.restored)

    def synchronize(self) -> None:
        if self.device == "cuda":
            torch.cuda.synchronize()

    def snapshot(self) -> dict:
        result = {
            "branch": self.branch.snapshot(),
            "window": self.window.snapshot(),
            "pending": self.pending,
            "next_at": self.next_at.isoformat(),
            "current_lambda": self.current_lambda,
            "arrivals": self.arrivals,
            "actual_steps": self.actual_steps,
            "virtual_steps": self.virtual_steps,
            "cost": self.cost,
            "source_state_sha256": self.source_state_sha256,
        }
        if self.paired_rule is not None:
            result["active_block"] = self.active_block
            result["next_block_id"] = self.next_block_id
        return result

    def restore(self, value: dict) -> None:
        if value["source_state_sha256"] != self.source_state_sha256:
            raise ValueError("Frozen source differs on resume")
        self.branch = Branch.from_snapshot(
            value["branch"], device=self.device, learning_rate=self.training.learning_rate
        )
        self.window = ArrivedWindow.restore(value["window"])
        self.pending = value["pending"]
        self.next_at = datetime.fromisoformat(value["next_at"])
        self.current_lambda = value["current_lambda"]
        self.arrivals = value["arrivals"]
        self.actual_steps = value["actual_steps"]
        self.virtual_steps = value["virtual_steps"]
        self.cost = value["cost"]
        if self.paired_rule is not None:
            if "active_block" not in value or "next_block_id" not in value:
                raise ValueError("Paired-controller state missing on resume")
            self.active_block = value["active_block"]
            self.next_block_id = value["next_block_id"]
            if "paired_seconds" not in self.cost:
                raise ValueError("Paired-controller cost missing on resume")

    def _paired_outcome(
        self, issued: dict, normalized: list[float], available_at: datetime,
        as_of: datetime, events: list[dict],
    ) -> None:
        paired = issued.get("paired")
        if paired is None:
            return
        if (
            datetime.fromisoformat(paired["v_origin"]) >= datetime.fromisoformat(issued["origin"])
            or datetime.fromisoformat(paired["v_available_at"])
            > datetime.fromisoformat(issued["origin"])
            or available_at > as_of
            or paired["incumbent_lambda"] != issued["lambda"]
        ):
            raise ValueError("Noncausal paired forecast binding")
        block = self.active_block
        if block is None or paired["block_id"] != block["id"]:
            events.append({"event": "paired_skip", "origin": issued["origin"], "reason": "stale_block"})
            return
        block["pending_pairs"] -= 1
        candidate_errors = [
            abs(prediction - label)
            for prediction, label in zip(paired["candidate_prediction"], normalized, strict=True)
        ]
        incumbent_errors = [
            abs(prediction - label)
            for prediction, label in zip(issued["prediction"], normalized, strict=True)
        ]
        candidate_mae = sum(candidate_errors) * self.replay.scale / 24
        incumbent_mae = sum(incumbent_errors) * self.replay.scale / 24
        difference = candidate_mae - incumbent_mae
        if not all(math.isfinite(value) for value in (candidate_mae, incumbent_mae, difference)):
            raise ValueError("Nonfinite paired MAE")
        block["differences_kwh"].append(difference)
        events.append({
            "event": "paired_observation",
            "origin": issued["origin"],
            "as_of": as_of.isoformat(),
            "available_at": available_at.isoformat(),
            "forecast_sha256": issued["prediction_sha256"],
            "block_id": block["id"],
            "v_origin": paired["v_origin"],
            "incumbent_mae_kwh": incumbent_mae,
            "candidate_mae_kwh": candidate_mae,
            "candidate_minus_incumbent_mae_kwh": difference,
        })
        if len(block["differences_kwh"]) == self.paired_rule.valid_complete_pairs:
            verdict = accept(block["differences_kwh"], self.paired_rule)
            before = self.current_lambda
            self.current_lambda = block["candidate"] if verdict["accepted"] else before
            events.append({
                "event": "meta_decision",
                "origin": issued["origin"],
                "as_of": as_of.isoformat(),
                "block_id": block["id"],
                "lambda_before": before,
                "lambda_after": self.current_lambda,
                "candidate_lambda": block["candidate"],
                "proposal_hypergradient": block["hypergradient"],
                **verdict,
            })
            self.active_block = None

    def _open_paired_block(self, as_of: datetime, events: list[dict]) -> None:
        if self.active_block is not None:
            return
        selected = self.window.select(as_of, self.rule)
        if selected is None:
            events.append({"event": "meta_skip", "reason": "insufficient_arrived_A_or_untrained_V"})
            return
        self.synchronize()
        started = time.perf_counter()
        suggested = decide(
            self.branch.model, self.branch.optimizer, self.reference, self.latent_scale,
            *selected, self.current_lambda, self.rule, device=self.device,
        )
        self.synchronize()
        self.cost["meta_seconds"] += time.perf_counter() - started
        self.virtual_steps += 1
        proposal = propose(
            self.current_lambda, suggested["hypergradient"], self.paired_rule,
            self.rule.upper_bound,
        )
        if proposal["candidate"] == self.current_lambda:
            events.append({"event": "meta_skip", "reason": "zero_proposal_step", **proposal})
            return
        self.active_block = {
            "id": self.next_block_id,
            "incumbent": self.current_lambda,
            "candidate": proposal["candidate"],
            "hypergradient": suggested["hypergradient"],
            "started_at": as_of.isoformat(),
            "issued_days": 0,
            "pending_pairs": 0,
            "differences_kwh": [],
        }
        self.next_block_id += 1
        events.append({
            "event": "paired_proposal",
            "as_of": as_of.isoformat(),
            "block_id": self.active_block["id"],
            "a_origins": suggested["a_origins"],
            "v_origins": suggested["v_origins"],
            **proposal,
        })

    def _expire_paired_block(self, as_of: datetime, events: list[dict]) -> None:
        block = self.active_block
        if block is not None and block["issued_days"] >= self.paired_rule.max_wait_issued_days:
            events.append({
                "event": "paired_block_timeout",
                "as_of": as_of.isoformat(),
                "block_id": block["id"],
                "valid_complete_pairs": len(block["differences_kwh"]),
                "pending_pairs": block["pending_pairs"],
                "lambda_after": self.current_lambda,
            })
            self.active_block = None

    def _arrivals(self, as_of: datetime, events: list[dict]) -> None:
        waiting = []
        for issued in sorted(self.pending, key=lambda row: row["origin"]):
            origin = datetime.fromisoformat(issued["origin"])
            outcome = self.replay.labels(origin, as_of)
            if outcome.status == "pending":
                waiting.append(issued)
                continue
            if outcome.status == "incomplete":
                paired = issued.get("paired")
                if self.paired_rule is not None and paired is not None:
                    block = self.active_block
                    if block is not None and paired["block_id"] == block["id"]:
                        block["pending_pairs"] -= 1
                    events.append({
                        "event": "paired_skip", "origin": issued["origin"],
                        "reason": "incomplete_labels",
                    })
                events.append(
                    {
                        "event": "skip_incomplete_labels",
                        "origin": issued["origin"],
                        "as_of": as_of.isoformat(),
                    }
                )
                continue
            if outcome.status != "complete" or outcome.values is None or len(outcome.values) != 24:
                raise ValueError("Invalid complete replay label")
            normalized = [value / self.replay.scale for value in outcome.values]
            if any(not math.isfinite(value) or value < 0 for value in normalized):
                raise ValueError("Invalid arrived label")
            errors = [a - b for a, b in zip(issued["prediction"], normalized, strict=True)]
            events.append(
                {
                    "event": "score",
                    "origin": issued["origin"],
                    "as_of": as_of.isoformat(),
                    "prediction_sha256": issued["prediction_sha256"],
                    "mae_kwh": sum(abs(error) for error in errors) * self.replay.scale / 24,
                    "mse_kwh2": sum(error * error for error in errors) * self.replay.scale**2 / 24,
                }
            )
            if self.paired_rule is not None:
                self._paired_outcome(
                    issued, normalized, outcome.available_at or as_of, as_of, events
                )
            record = {**issued["record"], "y_scaled": normalized}
            self.window.add(
                origin=origin,
                available_at=outcome.available_at or as_of,
                as_of=as_of,
                record=record,
            )
            self.arrivals += 1
            if self.paired_rule is not None:
                self._open_paired_block(as_of, events)
            elif not self.frozen_lambda and self.arrivals % self.cadence == 0:
                selected = self.window.select(as_of, self.rule)
                if selected is None:
                    events.append(
                        {
                            "event": "meta_skip",
                            "origin": issued["origin"],
                            "reason": "insufficient_arrived_A_or_untrained_V",
                        }
                    )
                else:
                    self.synchronize()
                    started = time.perf_counter()
                    decision = decide(
                        self.branch.model,
                        self.branch.optimizer,
                        self.reference,
                        self.latent_scale,
                        *selected,
                        self.current_lambda,
                        self.rule,
                        device=self.device,
                    )
                    self.synchronize()
                    self.cost["meta_seconds"] += time.perf_counter() - started
                    self.current_lambda = decision["lambda_after"]
                    self.virtual_steps += 1
                    events.append(
                        {"event": "meta_decision", "origin": issued["origin"], **decision}
                    )
            diagnostic_every = self.store.binding.get("config", {}).get("diagnostic_every", 0)
            if diagnostic_every and self.arrivals % diagnostic_every == 0:
                self.synchronize()
                diagnostic_started = time.perf_counter()
                diagnostic = measure(
                    self.branch.model,
                    self.reference,
                    self.latent_scale,
                    record,
                    self.current_lambda,
                    epsilon=self.training.epsilon,
                    device=self.device,
                )
                self.synchronize()
                self.cost["diagnostic_seconds"] = (
                    self.cost.get("diagnostic_seconds", 0.0)
                    + time.perf_counter()
                    - diagnostic_started
                )
                events.append({"event": "loss_gradient", "origin": issued["origin"], **diagnostic})
            before = self.branch.steps
            paired_snapshot = None
            block = self.active_block
            if block is not None and (
                len(block["differences_kwh"]) + block["pending_pairs"]
                < self.paired_rule.valid_complete_pairs
            ):
                paired_snapshot = self.branch.snapshot()
            self.synchronize()
            started = time.perf_counter()
            logs = self.branch.update(
                record,
                weight=self.current_lambda,
                config=self.training,
                device=self.device,
                reference=self.reference,
                latent_scale=self.latent_scale,
                event_index=self.arrivals - 1,
            )
            self.synchronize()
            self.cost["actual_update_seconds"] += time.perf_counter() - started
            self.actual_steps += self.branch.steps - before
            self.window.mark_trained(origin)
            if paired_snapshot is not None:
                self.last_update_for_pair = {
                    "pre_branch": paired_snapshot,
                    "v_record": record,
                    "v_origin": issued["origin"],
                    "v_available_at": (outcome.available_at or as_of).isoformat(),
                    "incumbent_lambda": self.current_lambda,
                    "candidate_lambda": block["candidate"],
                    "block_id": block["id"],
                    "event_index": self.arrivals - 1,
                }
            events.append(
                {
                    "event": "actual_update",
                    "origin": issued["origin"],
                    "lambda": self.current_lambda,
                    "logs": logs,
                }
            )
        self.pending = waiting
        if self.paired_rule is not None:
            self._expire_paired_block(as_of, events)

    def _paired_forecast(self, record: dict, actual: list[float], events: list[dict]) -> dict | None:
        context = self.last_update_for_pair
        block = self.active_block
        if (
            context is None
            or block is None
            or context["block_id"] != block["id"]
            or context["incumbent_lambda"] != self.current_lambda
        ):
            return None
        self.synchronize()
        started = time.perf_counter()
        forecasts = []
        for weight in (context["incumbent_lambda"], context["candidate_lambda"]):
            shadow = Branch.from_snapshot(
                context["pre_branch"], device=self.device,
                learning_rate=self.training.learning_rate,
            )
            shadow.update(
                context["v_record"], weight=weight, config=self.training,
                device=self.device, reference=self.reference,
                latent_scale=self.latent_scale, event_index=context["event_index"],
            )
            forecasts.append(shadow.predict(record, device=self.device))
        self.synchronize()
        self.cost["paired_seconds"] += time.perf_counter() - started
        self.virtual_steps += 2
        max_error = max(abs(left - right) for left, right in zip(forecasts[0], actual, strict=True))
        if any(
            abs(left - right) > 1e-5 + 1e-4 * abs(right)
            for left, right in zip(forecasts[0], actual, strict=True)
        ):
            events.append({
                "event": "paired_skip", "reason": "incumbent_shadow_mismatch",
                "v_origin": context["v_origin"], "max_error": max_error,
            })
            return None
        return {
            "block_id": block["id"],
            "incumbent_lambda": context["incumbent_lambda"],
            "candidate_lambda": context["candidate_lambda"],
            "candidate_prediction": forecasts[1],
            "candidate_prediction_id": identity({
                "origin": self.next_at.isoformat(), "prediction": forecasts[1],
            }),
            "incumbent_shadow_max_error": max_error,
            "v_origin": context["v_origin"],
            "v_available_at": context["v_available_at"],
        }

    def tick(self) -> None:
        as_of = self.next_at
        self.last_update_for_pair = None
        transaction = self.store.begin()
        events: list[dict] = []
        self._arrivals(as_of, events)
        record = self.replay.forecast(as_of) if as_of < self.replay.stop else None
        issued = {}
        if record is not None:
            self.synchronize()
            started = time.perf_counter()
            prediction = self.branch.predict(record, device=self.device)
            self.synchronize()
            self.cost["inference_seconds"] += time.perf_counter() - started
            issued = {
                "origin": as_of.isoformat(),
                "lambda": self.current_lambda,
                "prediction": prediction,
                "prediction_id": identity({"origin": as_of.isoformat(), "prediction": prediction}),
                "record": record,
            }
            if self.paired_rule is not None:
                paired = self._paired_forecast(record, prediction, events)
                if paired is not None:
                    issued["paired"] = paired
                if self.active_block is not None:
                    self.active_block["issued_days"] += 1
        checksum = self.store.save_forecasts(transaction, issued)
        if issued:
            issued["prediction_sha256"] = checksum
            self.pending.append(issued)
            if "paired" in issued:
                self.active_block["pending_pairs"] += 1
            events.append(
                {
                    "event": "forecast_saved",
                    "origin": issued["origin"],
                    "prediction_sha256": checksum,
                }
            )
        elif as_of < self.replay.stop:
            events.append({"event": "skip_all_missing_history", "origin": as_of.isoformat()})
        if state_digest(self.reference.state_dict()) != self.source_state_sha256:
            raise ValueError("Frozen source mutated")
        self.next_at += DAY
        self.store.commit(transaction, self.snapshot(), events)

    def run_until(self, end_inclusive: datetime) -> None:
        while self.next_at <= end_inclusive:
            self.tick()
