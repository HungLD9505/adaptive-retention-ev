"""Matched persistent candidate trajectory for the issue #99 controller."""

import math
import time
from datetime import datetime

import torch

from ev_control.persistent import PersistentRule, accept, propose
from ev_models.model import ForecastGRU
from ev_models.training import TrainingConfig
from ev_runner.state import Branch, identity, state_digest


def branch_digests(branch: Branch) -> dict[str, str]:
    """Record model, Adam, and RNG identities without changing their state."""
    return {
        "model_sha256": state_digest(branch.model.state_dict()),
        "adam_sha256": state_digest(branch.optimizer.state_dict()),
        "rng_sha256": state_digest(branch.rng),
    }


class PersistentCandidate:
    """Clone once per block; never transplant candidate weights into the real branch."""

    def __init__(
        self,
        rule: PersistentRule,
        training: TrainingConfig,
        reference: ForecastGRU,
        latent_scale: torch.Tensor,
        *,
        device: str,
    ) -> None:
        self.rule, self.training = rule, training
        self.reference, self.latent_scale = reference, latent_scale
        self.device = device
        self.branch: Branch | None = None
        self.block: dict | None = None
        self.next_block_id = 0
        self.shadow_steps = 0
        self.shadow_seconds = 0.0

    def synchronize(self) -> None:
        if self.device == "cuda":
            torch.cuda.synchronize()

    def snapshot(self) -> dict:
        return {
            "branch": self.branch.snapshot() if self.branch is not None else None,
            "block": self.block,
            "next_block_id": self.next_block_id,
            "shadow_steps": self.shadow_steps,
            "shadow_seconds": self.shadow_seconds,
        }

    def restore(self, value: dict) -> None:
        required = {"branch", "block", "next_block_id", "shadow_steps", "shadow_seconds"}
        if set(value) != required or (value["branch"] is None) != (value["block"] is None):
            raise ValueError("Invalid persistent candidate checkpoint")
        self.branch = (
            Branch.from_snapshot(
                value["branch"], device=self.device, learning_rate=self.training.learning_rate
            )
            if value["branch"] is not None
            else None
        )
        self.block = value["block"]
        self.next_block_id = value["next_block_id"]
        self.shadow_steps = value["shadow_steps"]
        self.shadow_seconds = value["shadow_seconds"]

    def start(
        self, incumbent: Branch, current_lambda: float, hypergradient: float,
        upper_bound: float, as_of: datetime,
    ) -> dict:
        if self.block is not None:
            raise ValueError("Persistent block already active")
        offered = propose(current_lambda, hypergradient, self.rule, upper_bound)
        if offered["candidate"] == current_lambda:
            return {"event": "persistent_skip", "reason": "zero_proposal_step", **offered}
        self.branch = incumbent.clone(device=self.device, learning_rate=self.training.learning_rate)
        self.block = {
            "id": self.next_block_id,
            "incumbent": current_lambda,
            "candidate": offered["candidate"],
            "hypergradient": hypergradient,
            "started_at": as_of.isoformat(),
            "issued_days": 0,
            "pending_pairs": 0,
            "differences_kwh": [],
            "initial_real_steps": incumbent.steps,
        }
        self.next_block_id += 1
        return {
            "event": "persistent_proposal",
            "as_of": as_of.isoformat(),
            "block_id": self.block["id"],
            **offered,
        }

    def update(self, record: dict, *, event_index: int, real_steps: int) -> None:
        if self.branch is None or self.block is None:
            return
        self.synchronize()
        started = time.perf_counter()
        before = self.branch.steps
        self.branch.update(
            record,
            weight=self.block["candidate"],
            config=self.training,
            device=self.device,
            reference=self.reference,
            latent_scale=self.latent_scale,
            event_index=event_index,
        )
        self.synchronize()
        self.shadow_seconds += time.perf_counter() - started
        self.shadow_steps += self.branch.steps - before
        if self.branch.steps != real_steps:
            raise ValueError("Candidate and incumbent consumed different update counts")

    def forecast(self, record: dict, origin: datetime) -> dict | None:
        block = self.block
        if block is None or self.branch is None:
            return None
        if len(block["differences_kwh"]) + block["pending_pairs"] >= self.rule.valid_complete_pairs:
            return None
        self.synchronize()
        started = time.perf_counter()
        prediction = self.branch.predict(record, device=self.device)
        self.synchronize()
        self.shadow_seconds += time.perf_counter() - started
        return {
            "block_id": block["id"],
            "candidate_lambda": block["candidate"],
            "candidate_prediction": prediction,
            "candidate_prediction_id": identity(
                {"origin": origin.isoformat(), "prediction": prediction}
            ),
        }

    def issued(self, paired: bool) -> None:
        if self.block is None:
            return
        self.block["issued_days"] += 1
        if paired:
            self.block["pending_pairs"] += 1

    def incomplete(self, paired: dict | None) -> dict | None:
        if paired is None:
            return None
        if self.block is not None and paired["block_id"] == self.block["id"]:
            # Eligibility is label completeness, never the observed error value.
            self.block["pending_pairs"] -= 1
        return {"event": "persistent_skip", "reason": "incomplete_labels", "block_id": paired["block_id"]}

    def observe(
        self, issued: dict, normalized: list[float], available_at: datetime,
        as_of: datetime, scale: float,
    ) -> tuple[dict | None, dict | None]:
        paired = issued.get("paired")
        if paired is None:
            return None, None
        origin = datetime.fromisoformat(issued["origin"])
        if (
            available_at > as_of
            or available_at <= origin
            or origin >= as_of
            or len(paired["candidate_prediction"]) != 24
            or paired.get("candidate_prediction_id")
            != identity({"origin": issued["origin"], "prediction": paired["candidate_prediction"]})
        ):
            raise ValueError("Noncausal or malformed persistent forecast")
        block = self.block
        if block is None or paired["block_id"] != block["id"]:
            return {"event": "persistent_skip", "reason": "stale_block", "origin": issued["origin"]}, None
        if (
            issued["lambda"] != block["incumbent"]
            or paired["candidate_lambda"] != block["candidate"]
            or origin < datetime.fromisoformat(block["started_at"])
        ):
            raise ValueError("Persistent forecast does not match candidate block")
        self.block["pending_pairs"] -= 1
        incumbent_mae = sum(
            abs(value - label)
            for value, label in zip(issued["prediction"], normalized, strict=True)
        ) * scale / 24
        candidate_mae = sum(
            abs(value - label)
            for value, label in zip(paired["candidate_prediction"], normalized, strict=True)
        ) * scale / 24
        difference = candidate_mae - incumbent_mae
        if not all(math.isfinite(value) for value in (incumbent_mae, candidate_mae, difference)):
            raise ValueError("Nonfinite persistent paired score")
        block["differences_kwh"].append(difference)
        observation = {
            "event": "persistent_observation",
            "origin": issued["origin"],
            "as_of": as_of.isoformat(),
            "available_at": available_at.isoformat(),
            "forecast_sha256": issued["prediction_sha256"],
            "block_id": block["id"],
            "incumbent_mae_kwh": incumbent_mae,
            "candidate_mae_kwh": candidate_mae,
            "candidate_minus_incumbent_mae_kwh": difference,
        }
        if len(block["differences_kwh"]) != self.rule.valid_complete_pairs:
            return observation, None
        verdict = accept(block["differences_kwh"], self.rule)
        if self.branch is None:
            raise ValueError("Persistent candidate disappeared before decision")
        decision = {
            "event": "meta_decision",
            "origin": issued["origin"],
            "as_of": as_of.isoformat(),
            "block_id": block["id"],
            "lambda_before": block["incumbent"],
            "lambda_after": block["candidate"] if verdict["accepted"] else block["incumbent"],
            "candidate_lambda": block["candidate"],
            "proposal_hypergradient": block["hypergradient"],
            "candidate_state": branch_digests(self.branch),
            **verdict,
        }
        self.branch = None
        self.block = None
        return observation, decision

    def expire(self, as_of: datetime) -> dict | None:
        block = self.block
        if block is None or block["issued_days"] < self.rule.max_wait_issued_days:
            return None
        event = {
            "event": "persistent_timeout",
            "status": "expired",
            "as_of": as_of.isoformat(),
            "block_id": block["id"],
            "issued_days": block["issued_days"],
            "valid_complete_pairs": len(block["differences_kwh"]),
            "pending_pairs": block["pending_pairs"],
            "lambda_after": block["incumbent"],
        }
        self.branch = None
        self.block = None
        return event
