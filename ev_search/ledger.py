"""Append-only bounded Fixed trial ledger; execution is supplied by a caller."""

import hashlib
import json
import math
import os
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from ev_search.fixed import FixedSearchConfig, expanded_upper, propose_lambda, sensitivity_design


def canonical(value: dict) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


class FixedLedger:
    def __init__(
        self,
        root: Path,
        config: FixedSearchConfig,
        *,
        binding: dict | None = None,
        resume: bool = False,
    ) -> None:
        self.root = root
        self.config = config
        self.binding = binding or {}
        self.identity = hashlib.sha256(
            canonical({"config": asdict(config), "binding": self.binding})
        ).hexdigest()
        if resume:
            metadata = json.loads((root / "config.json").read_text())
            if (
                metadata.get("schema") != "issue99-fixed-ledger-v1"
                or metadata.get("config") != json.loads(json.dumps(asdict(config)))
                or metadata.get("binding") != self.binding
                or metadata.get("sha256") != self.identity
            ):
                raise ValueError("Fixed search config changed on resume")
            self.events = [
                json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()
            ]
            self.chain = "0" * 64
            pending = None
            completed = 0
            for event in self.events:
                body = {key: value for key, value in event.items() if key != "sha256"}
                expected = hashlib.sha256(canonical(body)).hexdigest()
                if body.get("previous") != self.chain or event.get("sha256") != expected:
                    raise ValueError("Fixed trial ledger event chain changed")
                self.chain = expected
                if event["event"] == "trial_start":
                    if pending is not None or event["trial"] != completed:
                        raise ValueError("Duplicate or out-of-order Fixed trial")
                    pending = (event["trial"], event["lambda"], event["role"])
                elif event["event"] == "trial_end":
                    if pending != (event["trial"], event["lambda"], event["role"]):
                        raise ValueError("Fixed trial end differs from start")
                    pending = None
                    completed += 1
                elif event["event"] == "domain_expansion":
                    if pending is not None or event["after_trial"] != completed - 1:
                        raise ValueError("Fixed domain expansion out of order")
                else:
                    raise ValueError("Unknown Fixed ledger event")
            if pending is not None:
                raise ValueError("Uncommitted trial; inspect before resume")
        else:
            root.mkdir(parents=True, exist_ok=False)
            (root / "config.json").write_bytes(
                canonical(
                    {
                        "schema": "issue99-fixed-ledger-v1",
                        "sha256": self.identity,
                        "config": asdict(config),
                        "binding": self.binding,
                    }
                )
            )
            (root / "events.jsonl").open("xb").close()
            self.events = []
            self.chain = "0" * 64

    def append(self, event: dict) -> None:
        event = {**event, "previous": self.chain}
        checksum = hashlib.sha256(canonical(event)).hexdigest()
        event["sha256"] = checksum
        with (self.root / "events.jsonl").open("ab") as stream:
            stream.write(canonical(event))
            stream.flush()
            os.fsync(stream.fileno())
        self.events.append(event)
        self.chain = checksum

    def completed(self) -> list[dict]:
        return [event for event in self.events if event["event"] == "trial_end"]

    def evaluate(
        self, weight: float, role: str, evaluator: Callable[[float, str, int], dict]
    ) -> dict:
        if (
            isinstance(weight, bool)
            or not isinstance(weight, (int, float))
            or not math.isfinite(weight)
            or (role == "zero_baseline" and weight != 0)
            or (role in {"initial", "bo_ei", "sensitivity"} and weight <= 0)
            or role not in {"zero_baseline", "initial", "bo_ei", "sensitivity"}
        ):
            raise ValueError("Invalid Fixed trial identity")
        trial = len(self.completed())
        self.append({"event": "trial_start", "trial": trial, "lambda": weight, "role": role})
        try:
            outcome = evaluator(weight, role, trial)
            score = outcome.get("objective_mae_kwh")
            if score is not None and (
                isinstance(score, bool)
                or not isinstance(score, (float, int))
                or not math.isfinite(score)
                or score < 0
            ):
                raise ValueError("Invalid original-unit trial objective")
            canonical(outcome)
            result = {
                "event": "trial_end",
                "trial": trial,
                "lambda": weight,
                "role": role,
                "status": "complete" if score is not None else "null",
                "outcome": outcome,
            }
        except Exception as error:
            result = {
                "event": "trial_end",
                "trial": trial,
                "lambda": weight,
                "role": role,
                "status": "failed",
                "outcome": {"objective_mae_kwh": None, "error": repr(error)},
            }
        self.append(result)
        return result


def record_due_expansion(ledger: FixedLedger) -> float:
    """Record a boundary expansion, including after a crash past trial_end."""
    config = ledger.config
    bo = [event for event in ledger.completed() if event["role"] in {"initial", "bo_ei"}]
    expansions = [event for event in ledger.events if event["event"] == "domain_expansion"]
    upper = expansions[-1]["upper"] if expansions else config.positive_upper
    if not bo or bo[-1]["status"] != "complete":
        return upper
    if expansions and expansions[-1]["after_trial"] == bo[-1]["trial"]:
        return upper
    finite = [
        (event["lambda"], event["outcome"]["objective_mae_kwh"])
        for event in bo
        if event["status"] == "complete"
    ]
    expanded = expanded_upper(config, upper, len(expansions), finite)
    if expanded > upper:
        ledger.append(
            {
                "event": "domain_expansion",
                "after_trial": bo[-1]["trial"],
                "previous_upper": upper,
                "upper": expanded,
            }
        )
    return expanded


def run_bounded_search(
    ledger: FixedLedger,
    evaluator: Callable[[float, str, int], dict],
    *,
    max_new_trials: int,
) -> list[dict]:
    """Advance a finite search; each invocation may stop at a trial boundary."""
    if (
        isinstance(max_new_trials, bool)
        or not isinstance(max_new_trials, int)
        or max_new_trials < 1
    ):
        raise ValueError("Positive invocation trial limit required")
    new = []
    config = ledger.config
    while len(new) < max_new_trials:
        completed = ledger.completed()
        if not any(event["role"] == "zero_baseline" for event in completed):
            new.append(ledger.evaluate(0.0, "zero_baseline", evaluator))
            continue
        bo = [event for event in completed if event["role"] in {"initial", "bo_ei"}]
        upper = record_due_expansion(ledger)
        if len(bo) < config.bo_trials:
            trials = [(event["lambda"], event["outcome"]["objective_mae_kwh"]) for event in bo]
            weight, role = propose_lambda(config, upper, trials)
            result = ledger.evaluate(weight, role, evaluator)
            new.append(result)
            record_due_expansion(ledger)
            continue
        sensitivity = sensitivity_design(config, upper)
        attempted = [event["lambda"] for event in completed]
        remaining = [
            weight
            for weight in sensitivity
            if all(not math.isclose(weight, old, rel_tol=1e-10, abs_tol=0) for old in attempted)
        ]
        if not remaining:
            break
        new.append(ledger.evaluate(remaining[0], "sensitivity", evaluator))
    return new
