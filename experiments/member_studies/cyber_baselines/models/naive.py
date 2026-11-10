"""Daily Naive and Seasonal Naive baselines for Cyber benchmark."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from experiments.member_studies.cyber_baselines.models.base import BaseForecaster


class DailyNaive(BaseForecaster):
    """Daily Naive: forecasts same-hour previous-day energy with mean/zero fallback.

    Uses the 24-hour historical window visible at the origin.
    y_hat[t, h] = X_hist[h, 0] if mask[h] == 1, else historical mean fallback.
    """

    def __init__(self, initial_records: list[dict[str, Any]] | None = None) -> None:
        self.history_values: list[float] = []
        if initial_records:
            for rec in initial_records:
                self.ingest(rec.get("forecast", rec))

    @property
    def name(self) -> str:
        return "Daily Naive"

    @property
    def param_count(self) -> int:
        return 0

    def ingest(self, record: dict[str, Any]) -> None:
        x_hist = record.get("x_hist", [])
        for row in x_hist:
            if len(row) >= 7 and row[-1] > 0.5:  # valid mask
                self.history_values.append(float(row[0]))

    def predict(self, record: dict[str, Any]) -> list[float]:
        self.ingest(record)
        x_hist = record["x_hist"]
        fallback = (
            sum(self.history_values) / len(self.history_values) if self.history_values else 0.0
        )

        preds = []
        for h in range(24):
            val = x_hist[h][0]
            mask = x_hist[h][-1]
            if mask > 0.5:
                preds.append(float(val))
            else:
                preds.append(float(fallback))
        return preds

    def update(self, record: dict[str, Any], y_scaled: list[float]) -> dict[str, Any]:
        self.ingest(record)
        for v in y_scaled:
            self.history_values.append(float(v))
        return {"status": "ok", "buffer_size": len(self.history_values)}


class SeasonalNaive(BaseForecaster):
    """Seasonal Naive: forecasts same-hour previous-week (168h lag) energy.

    Cascading fallback:
    1. Weekly lag (t + h - 168h)
    2. Daily lag (t + h - 24h)
    3. Available history mean
    4. Zero
    """

    def __init__(self, initial_records: list[dict[str, Any]] | None = None) -> None:
        self.history_map: dict[str, float] = {}
        self.fallbacks = {"weekly": 0, "daily": 0, "mean": 0, "zero": 0}

        if initial_records:
            for rec in initial_records:
                fc = rec.get("forecast", rec)
                self.ingest_history(fc)
                # If ground truth labels are present in initial records
                if "future_labels" in fc and "y_scaled" in rec:
                    for ts, val in zip(fc["future_labels"], rec["y_scaled"], strict=True):
                        self.history_map[ts] = float(val)

    @property
    def name(self) -> str:
        return "Seasonal Naive"

    @property
    def param_count(self) -> int:
        return 0

    def ingest_history(self, record: dict[str, Any]) -> None:
        hist_labels = record.get("history_labels", [])
        x_hist = record.get("x_hist", [])
        for ts, row in zip(hist_labels, x_hist, strict=True):
            if len(row) >= 7 and row[-1] > 0.5:
                self.history_map[ts] = float(row[0])

    def predict(self, record: dict[str, Any]) -> list[float]:
        self.ingest_history(record)
        origin = datetime.fromisoformat(record["origin"])

        past_vals = [v for t_str, v in self.history_map.items() if datetime.fromisoformat(t_str) < origin]
        mean_fallback = sum(past_vals) / len(past_vals) if past_vals else 0.0

        output = []
        for h in range(24):
            target_dt = origin + timedelta(hours=h)
            weekly_key = (target_dt - timedelta(hours=168)).isoformat()
            daily_key = (target_dt - timedelta(hours=24)).isoformat()

            if weekly_key in self.history_map:
                output.append(self.history_map[weekly_key])
                self.fallbacks["weekly"] += 1
            elif daily_key in self.history_map:
                output.append(self.history_map[daily_key])
                self.fallbacks["daily"] += 1
            elif past_vals:
                output.append(mean_fallback)
                self.fallbacks["mean"] += 1
            else:
                output.append(0.0)
                self.fallbacks["zero"] += 1

        return output

    def update(self, record: dict[str, Any], y_scaled: list[float]) -> dict[str, Any]:
        self.ingest_history(record)
        origin = datetime.fromisoformat(record["origin"])
        for h, val in enumerate(y_scaled):
            ts = (origin + timedelta(hours=h)).isoformat()
            self.history_map[ts] = float(val)
        return {"status": "ok", "buffer_size": len(self.history_map), "fallbacks": dict(self.fallbacks)}
