"""One-target daily score/update/boundary/forecast transactions, no Final entry point."""

import time
from datetime import datetime, timedelta
from typing import Protocol

import torch

from ev_control.confidence import ControllerConfig, DailyScore, decide
from ev_models.model import ForecastGRU
from ev_models.training import TrainingConfig
from ev_runner.replay import Labels
from ev_runner.state import Branch, identity, state_digest
from ev_runner.store import Store

DAY = timedelta(days=1)


class ReplaySource(Protocol):
    start: datetime
    stop: datetime
    scale_id: str
    scale: float

    def forecast(self, origin: datetime) -> dict | None: ...
    def labels(self, origin: datetime, as_of: datetime) -> Labels: ...


class Runner:
    """Resume is at committed daily boundaries; uncommitted ticks fail closed."""

    def __init__(
        self,
        replay: ReplaySource,
        initial: Branch,
        reference: ForecastGRU,
        latent_scale: torch.Tensor,
        controller: ControllerConfig,
        training: TrainingConfig,
        store: Store,
        *,
        device: str,
        stream_id: str,
    ) -> None:
        self.replay, self.reference, self.latent = replay, reference, latent_scale
        self.controller, self.training, self.store = controller, training, store
        self.device, self.stream_id = device, stream_id
        self.active = controller.initial_lambda
        self.block_start = self.next_at = replay.start
        self.branches = self.fork(initial)
        self.pending = []
        self.scores = []
        self.audit = None
        self.audit_origin = None
        self.audit_pairs = []
        self.decisions = []
        self.update_events = 0
        self.cost = {
            k: 0.0
            for k in (
                "inference_seconds",
                "update_seconds",
                "audit_inference_seconds",
                "audit_update_seconds",
                "controller_seconds",
            )
        }
        self.steps = self.audit_steps = 0
        self.reference_sha = state_digest(reference.state_dict())
        if store.restored is not None:
            self.restore(store.restored)

    def fork(self, active: Branch) -> dict[float, Branch]:
        return {
            level: active.clone(device=self.device, learning_rate=self.training.learning_rate)
            for level in self.controller.levels
        }

    def sync(self) -> None:
        if self.device == "cuda":
            torch.cuda.synchronize()

    def snapshot(self) -> dict:
        return {
            "active": self.active,
            "block_start": self.block_start.isoformat(),
            "next_at": self.next_at.isoformat(),
            "branches": {k: v.snapshot() for k, v in self.branches.items()},
            "pending": self.pending,
            "scores": self.scores,
            "audit": self.audit.snapshot() if self.audit else None,
            "audit_origin": self.audit_origin,
            "audit_pairs": self.audit_pairs,
            "decisions": self.decisions,
            "update_events": self.update_events,
            "cost": self.cost,
            "steps": self.steps,
            "audit_steps": self.audit_steps,
            "reference_sha": self.reference_sha,
        }

    def restore(self, state: dict) -> None:
        if state["reference_sha"] != self.reference_sha:
            raise ValueError("Frozen source differs on resume")
        for name in (
            "active",
            "pending",
            "scores",
            "audit_origin",
            "audit_pairs",
            "decisions",
            "update_events",
            "cost",
            "steps",
            "audit_steps",
        ):
            setattr(self, name, state[name])
        self.block_start = datetime.fromisoformat(state["block_start"])
        self.next_at = datetime.fromisoformat(state["next_at"])
        self.branches = {
            k: Branch.from_snapshot(
                v, device=self.device, learning_rate=self.training.learning_rate
            )
            for k, v in state["branches"].items()
        }
        self.audit = (
            Branch.from_snapshot(
                state["audit"], device=self.device, learning_rate=self.training.learning_rate
            )
            if state["audit"]
            else None
        )

    def update(self, branch: Branch, record: dict, weight: float, *, audit: bool) -> list[dict]:
        self.sync()
        started = time.perf_counter()
        before = branch.steps
        logs = branch.update(
            record,
            weight=weight,
            config=self.training,
            device=self.device,
            reference=self.reference,
            latent_scale=self.latent,
            event_index=self.update_events,
        )
        self.sync()
        self.cost["audit_update_seconds" if audit else "update_seconds"] += (
            time.perf_counter() - started
        )
        if audit:
            self.audit_steps += branch.steps - before
        else:
            self.steps += branch.steps - before
        return logs

    def arrived(self, as_of: datetime, events: list[dict]) -> None:
        waiting = []
        for issued in self.pending:
            origin = datetime.fromisoformat(issued["origin"])
            outcome = self.replay.labels(origin, as_of)
            if outcome.status == "pending":
                waiting.append(issued)
                continue
            if outcome.status not in {"complete", "incomplete"}:
                raise ValueError("Unknown label outcome")
            maes = None
            if outcome.status == "complete":
                y = outcome.values
                if (
                    y is None
                    or len(y) != 24
                    or any(not torch.isfinite(torch.tensor(v)) or v < 0 for v in y)
                ):
                    raise ValueError("Complete label vector is invalid")
                normalized = [v / self.replay.scale for v in y]
                maes = [
                    sum(abs(a - b) for a, b in zip(p, normalized, strict=True)) / 24
                    for p in issued["predictions"]
                ]
                events.append(
                    {
                        "event": "score",
                        "origin": issued["origin"],
                        "as_of": as_of.isoformat(),
                        "mae_scaled": maes,
                        "issued_active": issued["active"],
                        "prediction_sha256": issued["prediction_sha256"],
                    }
                )
                record = {**issued["record"], "y_scaled": normalized}
                for level, branch in self.branches.items():
                    logs = self.update(branch, record, level, audit=False)
                    events.append(
                        {
                            "event": "update",
                            "origin": issued["origin"],
                            "as_of": as_of.isoformat(),
                            "lambda": level,
                            "logs": logs,
                        }
                    )
                if self.audit and issued.get("audit_origin") == self.audit_origin:
                    audit_mae = (
                        sum(
                            abs(a - b)
                            for a, b in zip(issued["audit_prediction"], normalized, strict=True)
                        )
                        / 24
                    )
                    active_mae = maes[self.controller.levels.index(issued["active"])]
                    self.audit_pairs.append(
                        {"origin": issued["origin"], "new_minus_old": active_mae - audit_mae}
                    )
                    self.update(self.audit, record, self.audit_origin["lambda"], audit=True)
                self.update_events += 1
            else:
                events.append(
                    {
                        "event": "skip_incomplete_labels",
                        "origin": issued["origin"],
                        "as_of": as_of.isoformat(),
                    }
                )
            if issued["block_start"] == self.block_start.isoformat():
                self.scores.append(
                    {
                        "origin": issued["origin"],
                        "issued_at": issued["origin"],
                        "available_at": as_of.isoformat(),
                        "valid_labels": 24 if maes is not None else 0,
                        "mae": maes,
                        "scale_id": self.replay.scale_id,
                        "prediction_ids": issued["prediction_ids"],
                    }
                )
        self.pending = waiting

    def boundary(self, as_of: datetime, events: list[dict]) -> None:
        if as_of != self.block_start + self.controller.block_days * DAY:
            return
        rows = []
        for s in self.scores:
            rows.append(
                DailyScore(
                    datetime.fromisoformat(s["origin"]),
                    datetime.fromisoformat(s["issued_at"]),
                    datetime.fromisoformat(s["available_at"]),
                    s["valid_labels"],
                    tuple(s["mae"]) if s["mae"] is not None else None,
                    s["scale_id"],
                    tuple(s["prediction_ids"]),
                )
            )
        for issued in self.pending:
            if issued["block_start"] == self.block_start.isoformat():
                rows.append(
                    DailyScore(
                        datetime.fromisoformat(issued["origin"]),
                        datetime.fromisoformat(issued["origin"]),
                        None,
                        0,
                        None,
                        self.replay.scale_id,
                        tuple(issued["prediction_ids"]),
                    )
                )
        started = time.perf_counter()
        decision = decide(
            rows,
            config=self.controller,
            active_lambda=self.active,
            block_start=self.block_start,
            as_of=as_of,
            stream_id=self.stream_id,
            scale_id=self.replay.scale_id,
        )
        self.cost["controller_seconds"] += time.perf_counter() - started
        self.decisions.append(decision.as_dict())
        events.append({"event": "decision", "as_of": as_of.isoformat(), **decision.as_dict()})
        if self.audit:
            events.append(
                {
                    "event": "audit_summary",
                    "scope": "retrospective only; not supplied to controller",
                    "switch": self.audit_origin,
                    "paired_days": len(self.audit_pairs),
                    "mean_new_minus_old": sum(p["new_minus_old"] for p in self.audit_pairs)
                    / len(self.audit_pairs)
                    if self.audit_pairs
                    else None,
                    "daily": self.audit_pairs,
                }
            )
        old = self.active
        self.audit = (
            self.branches[old].clone(device=self.device, learning_rate=self.training.learning_rate)
            if decision.selected_lambda != old
            else None
        )
        self.audit_origin = {"start": as_of.isoformat(), "lambda": old} if self.audit else None
        self.audit_pairs = []
        self.active = decision.selected_lambda
        selected_digest = state_digest(self.branches[self.active].snapshot())
        self.branches = self.fork(self.branches[self.active])
        if any(state_digest(b.snapshot()) != selected_digest for b in self.branches.values()):
            raise ValueError("Candidate fork is not identical")
        events.append(
            {
                "event": "fork",
                "as_of": as_of.isoformat(),
                "selected_trained_state_sha256": selected_digest,
            }
        )
        self.block_start, self.scores = as_of, []

    def tick(self) -> None:
        as_of = self.next_at
        transaction = self.store.begin()
        events = []
        self.arrived(as_of, events)
        self.boundary(as_of, events)
        record = self.replay.forecast(as_of) if as_of < self.replay.stop else None
        issued = {}
        if record:
            predictions = []
            self.sync()
            started = time.perf_counter()
            for branch in self.branches.values():
                predictions.append(branch.predict(record, device=self.device))
            self.sync()
            self.cost["inference_seconds"] += time.perf_counter() - started
            issued = {
                "origin": as_of.isoformat(),
                "block_start": self.block_start.isoformat(),
                "active": self.active,
                "predictions": predictions,
                "record": record,
                "scale_id": self.replay.scale_id,
                "audit_origin": self.audit_origin,
            }
            issued["prediction_ids"] = [
                identity(
                    {
                        "stream": self.stream_id,
                        "origin": issued["origin"],
                        "lambda": level,
                        "prediction": prediction,
                    }
                )
                for level, prediction in zip(self.controller.levels, predictions, strict=True)
            ]
            if self.audit:
                self.sync()
                started = time.perf_counter()
                issued["audit_prediction"] = self.audit.predict(record, device=self.device)
                self.sync()
                self.cost["audit_inference_seconds"] += time.perf_counter() - started
        checksum = self.store.save_forecasts(transaction, issued)
        if issued:
            issued["prediction_sha256"] = checksum
            self.pending.append(issued)
            events.append(
                {
                    "event": "forecast_saved",
                    "origin": as_of.isoformat(),
                    "active": self.active,
                    "prediction_sha256": checksum,
                }
            )
        elif as_of < self.replay.stop:
            events.append({"event": "skip_all_missing_history", "origin": as_of.isoformat()})
        if state_digest(self.reference.state_dict()) != self.reference_sha:
            raise ValueError("Frozen source mutated")
        self.next_at += DAY
        self.store.commit(transaction, self.snapshot(), events)

    def run_until(self, end_inclusive: datetime) -> None:
        while self.next_at <= end_inclusive:
            self.tick()
