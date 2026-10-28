"""Bound receipt backpressure without changing Final model or acceptance rules."""

import hashlib
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReceiptPolicy:
    """One completed unit may wait; no speculative same-lane fit is admitted."""

    receipt_seconds: int = 600
    unit_seconds: int = 1200
    release_seconds: int = 300
    quota_age_seconds: int = 900
    reserve: int = 30
    completed_inflight: int = 1

    def __post_init__(self) -> None:
        if any(type(value) is not int for value in vars(self).values()):
            raise ValueError("Policy limits must be explicit integer bounds")
        if not 180 <= self.receipt_seconds <= 900:
            raise ValueError("Receipt deadline must be finite and reviewed")
        if self.unit_seconds != 1200 or self.release_seconds < 300:
            raise ValueError("Preserve the unit cap and release margin")
        if self.quota_age_seconds > 900 or self.quota_age_seconds <= 0:
            raise ValueError("Actual quota must be fresh within15minutes")
        if self.reserve != 30 or self.completed_inflight != 1:
            raise ValueError("Preserve shared reserve and one-unit backpressure")


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    """Reject ambiguous JSON objects instead of accepting the last duplicate key."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def verified_receipt(path: Path, lock_sha: str, index: int, lane: int) -> str:
    """Validate the original Root acceptance contract and return its actual hash."""
    raw = path.read_bytes()
    record = json.loads(raw, object_pairs_hook=unique_object)
    required = {
        "schema": "ev-final-unit-acceptance-v1",
        "lock_sha256": lock_sha,
        "unit_index": index,
        "lane": lane,
        "accepted_method_cells": 14,
        "native_readback_verified": True,
        "independent_content_verified": True,
    }
    for key, value in required.items():
        if type(record.get(key)) is not type(value) or record[key] != value:
            raise ValueError(f"Root receipt differs: {key}")
    return hashlib.sha256(raw).hexdigest()


def dispatch_budget(observation: dict, now: float, policy: ReceiptPolicy) -> dict:
    """Budget a full unit, its bounded receipt wait and safe release from real quota."""
    balance, rate, observed = (
        observation["balance"],
        observation["aggregatePerHour"],
        observation["observedEpoch"],
    )
    for value in (balance, rate, observed, now):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Quota values must be actual finite numbers")
        if not math.isfinite(value):
            raise ValueError("Nonfinite quota")
    age = now - observed
    if not 0 <= age <= policy.quota_age_seconds or balance < 0 or rate <= 0:
        raise ValueError("Actual quota stale, future-dated or invalid")
    if observation.get("reserve") != policy.reserve:
        raise ValueError("Shared reserve changed")
    sessions = observation.get("activeSessions")
    if type(sessions) is not int or not 1 <= sessions <= 2:
        raise ValueError("Unexpected aggregate allocation count")
    estimated_balance = balance - rate * age / 3600
    required = (
        policy.reserve
        + rate * (policy.unit_seconds + policy.receipt_seconds + policy.release_seconds) / 3600
    )
    if estimated_balance <= required:
        raise ValueError("Worst-case unit/wait/release would threaten reserve")
    return {
        "actual_observed_epoch": observed,
        "actual_balance": balance,
        "actual_aggregate_per_hour": rate,
        "observation_age_seconds": age,
        "estimated_balance_now": estimated_balance,
        "required_balance": required,
    }


def wait_expired(start: float, now: float, policy: ReceiptPolicy) -> bool:
    """Use elapsed monotonic time; a completed fit never silently restarts."""
    if not math.isfinite(start) or not math.isfinite(now) or now < start:
        raise ValueError("Invalid monotonic receipt clock")
    return now - start >= policy.receipt_seconds


def claim_undispatched(path: Path, forbidden: tuple[Path, ...], identity: dict) -> None:
    """Persist an exclusive intent before Popen; any uncertain restart fails closed."""
    if any(item.exists() for item in forbidden):
        raise FileExistsError("Existing output/log/native process; never refit implicitly")
    raw = (json.dumps(identity, sort_keys=True, allow_nan=False) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
