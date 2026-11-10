"""Single-branch chronological replay with arrived-label hypergradient decisions."""

import math
import time
from datetime import datetime, timedelta

import torch

from ev_control.continuous import ArrivedWindow, WindowRule, decide
from ev_control.persistent import PersistentRule
from ev_models.model import ForecastGRU
from ev_models.training import TrainingConfig
from ev_runner.diagnostics import measure
from ev_runner.persistent import PersistentCandidate, branch_digests
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
        persistent_rule: PersistentRule | None = None,
    ) -> None:
        if not 0 <= initial_lambda <= rule.upper_bound or cadence < 1:
            raise ValueError("Invalid initial lambda or cadence")
        if persistent_rule is not None and (
            frozen_lambda
            or cadence != 1
            or training.epochs != 1
            or initial_lambda != persistent_rule.anchor
            or persistent_rule.anchor > rule.upper_bound
        ):
            raise ValueError("Persistent controller needs one daily step at its anchor")
        self.replay, self.branch, self.reference = replay, branch, reference
        self.latent_scale, self.rule, self.training, self.store = (
            latent_scale,
            rule,
            training,
            store,
        )
        self.current_lambda, self.device, self.cadence = initial_lambda, device, cadence
        self.frozen_lambda = frozen_lambda
        self.persistent = (
            PersistentCandidate(
                persistent_rule, training, reference, latent_scale, device=device
            )
            if persistent_rule is not None
            else None
        )
        self.window = ArrivedWindow()
        self.pending: list[dict] = []
        self.next_at = replay.start
        self.arrivals = 0
        self.actual_steps = 0
        self.virtual_steps = 0
        self.cost = {"inference_seconds": 0.0, "actual_update_seconds": 0.0, "meta_seconds": 0.0}
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
        if self.persistent is not None:
            result["persistent"] = self.persistent.snapshot()
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
        if self.persistent is not None:
            if "persistent" not in value:
                raise ValueError("Persistent candidate missing on resume")
            self.persistent.restore(value["persistent"])

    def _start_persistent(self, as_of: datetime, events: list[dict]) -> None:
        if self.persistent.block is not None:
            return
        selected = self.window.select(as_of, self.rule)
        if selected is None:
            events.append({"event": "persistent_skip", "reason": "insufficient_arrived_A_or_untrained_V"})
            return
        self.synchronize()
        started = time.perf_counter()
        suggestion = decide(
            self.branch.model, self.branch.optimizer, self.reference, self.latent_scale,
            *selected, self.current_lambda, self.rule, device=self.device,
        )
        self.synchronize()
        self.cost["meta_seconds"] += time.perf_counter() - started
        self.virtual_steps += 1
        event = self.persistent.start(
            self.branch, self.current_lambda, suggestion["hypergradient"],
            self.rule.upper_bound, as_of,
        )
        event["a_origins"] = suggestion["a_origins"]
        event["v_origins"] = suggestion["v_origins"]
        events.append(event)

    def _arrivals(self, as_of: datetime, events: list[dict]) -> None:
        waiting = []
        for issued in sorted(self.pending, key=lambda row: row["origin"]):
            origin = datetime.fromisoformat(issued["origin"])
            outcome = self.replay.labels(origin, as_of)
            if outcome.status == "pending":
                waiting.append(issued)
                continue
            if outcome.status == "incomplete":
                if self.persistent is not None:
                    event = self.persistent.incomplete(issued.get("paired"))
                    if event is not None:
                        event["origin"] = issued["origin"]
                        events.append(event)
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
            if self.persistent is not None:
                block = self.persistent.block
                final_pair = (
                    block is not None
                    and issued.get("paired", {}).get("block_id") == block["id"]
                    and len(block["differences_kwh"]) + 1
                    == self.persistent.rule.valid_complete_pairs
                )
                real_before = branch_digests(self.branch) if final_pair else None
                observation, decision = self.persistent.observe(
                    issued, normalized, outcome.available_at or as_of, as_of,
                    self.replay.scale,
                )
                if observation is not None:
                    events.append(observation)
                if decision is not None:
                    real_after = branch_digests(self.branch)
                    if real_before != real_after:
                        raise ValueError("Persistent decision mutated real model/Adam/RNG")
                    decision["real_state_before"] = real_before
                    decision["real_state_after"] = real_after
                    self.current_lambda = decision["lambda_after"]
                    events.append(decision)
            record = {**issued["record"], "y_scaled": normalized}
            self.window.add(
                origin=origin,
                available_at=outcome.available_at or as_of,
                as_of=as_of,
                record=record,
            )
            self.arrivals += 1
            if self.persistent is not None:
                self._start_persistent(as_of, events)
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
            if self.persistent is not None:
                shadow_block = self.persistent.block
                self.persistent.update(
                    record, event_index=self.arrivals - 1, real_steps=self.branch.steps
                )
                if shadow_block is not None:
                    events.append({
                        "event": "persistent_shadow_update",
                        "origin": issued["origin"],
                        "as_of": as_of.isoformat(),
                        "block_id": shadow_block["id"],
                        "event_index": self.arrivals - 1,
                        "real_steps": self.branch.steps,
                        "shadow_steps": self.persistent.branch.steps,
                    })
            self.window.mark_trained(origin)
            events.append(
                {
                    "event": "actual_update",
                    "origin": issued["origin"],
                    "lambda": self.current_lambda,
                    "logs": logs,
                }
            )
        self.pending = waiting
        if self.persistent is not None:
            timeout = self.persistent.expire(as_of)
            if timeout is not None:
                events.append(timeout)

    def tick(self) -> None:
        as_of = self.next_at
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
            if self.persistent is not None:
                paired = self.persistent.forecast(record, as_of)
                if paired is not None:
                    issued["paired"] = paired
        checksum = self.store.save_forecasts(transaction, issued)
        if issued:
            issued["prediction_sha256"] = checksum
            self.pending.append(issued)
            if self.persistent is not None:
                self.persistent.issued("paired" in issued)
            saved_event = {
                "event": "forecast_saved",
                "origin": issued["origin"],
                "prediction_sha256": checksum,
            }
            if "paired" in issued:
                saved_event["persistent_block_id"] = issued["paired"]["block_id"]
                saved_event["candidate_prediction_id"] = issued["paired"][
                    "candidate_prediction_id"
                ]
            events.append(saved_event)
        elif as_of < self.replay.stop:
            events.append({"event": "skip_all_missing_history", "origin": as_of.isoformat()})
        if state_digest(self.reference.state_dict()) != self.source_state_sha256:
            raise ValueError("Frozen source mutated")
        self.next_at += DAY
        self.store.commit(transaction, self.snapshot(), events)

    def run_until(self, end_inclusive: datetime) -> None:
        while self.next_at <= end_inclusive:
            self.tick()
