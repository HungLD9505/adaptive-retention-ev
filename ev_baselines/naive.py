"""Causal weekly naive with daily/available-history mean fallback."""

import copy
from datetime import datetime, timedelta


class SeasonalNaive:
    """Only identified available prefix samples and current masked history are consumed."""

    def __init__(self, records: list[dict]) -> None:
        self.history = {}
        self.steps = 0
        self.fallbacks = {"weekly": 0, "daily": 0, "mean": 0, "zero": 0}
        for record in records:
            self.ingest(record)
            for timestamp, value in zip(record["future_labels"], record["y_scaled"], strict=True):
                self.history[timestamp] = value

    def ingest(self, record: dict) -> None:
        for timestamp, row in zip(record["history_labels"], record["x_hist"], strict=True):
            if row[-1]:
                self.history[timestamp] = row[0]

    def snapshot(self) -> dict:
        return {
            "kind": "seasonal-naive-v1",
            "history": dict(self.history),
            "steps": self.steps,
            "fallbacks": dict(self.fallbacks),
        }

    @classmethod
    def from_snapshot(cls, value: dict, **kwargs: object) -> "SeasonalNaive":
        obj = cls([])
        obj.history = dict(value["history"])
        obj.steps = value["steps"]
        obj.fallbacks = dict(value["fallbacks"])
        return obj

    def clone(self, **kwargs: object) -> "SeasonalNaive":
        return self.from_snapshot(copy.deepcopy(self.snapshot()))

    def predict(self, record: dict, **kwargs: object) -> list[float]:
        self.ingest(record)
        origin = datetime.fromisoformat(record["origin"])
        # Availability is explicit: no values at or after the forecast origin.
        past = [v for t, v in self.history.items() if datetime.fromisoformat(t) < origin]
        fallback = sum(past) / len(past) if past else 0.0
        output = []
        for h in range(24):
            target = origin + timedelta(hours=h)
            for label, lag in (("weekly", 168), ("daily", 24)):
                key = (target - timedelta(hours=lag)).isoformat()
                if key in self.history:
                    output.append(self.history[key])
                    self.fallbacks[label] += 1
                    break
            else:
                output.append(fallback)
                self.fallbacks["mean" if past else "zero"] += 1
        return output

    def update(self, record: dict, **kwargs: object) -> list[dict]:
        # Label arrival is governed by the common runner; storing knowledge is not SGD.
        self.ingest(record)
        origin = datetime.fromisoformat(record["origin"])
        for h, value in enumerate(record["y_scaled"]):
            self.history[(origin + timedelta(hours=h)).isoformat()] = value
        return []
