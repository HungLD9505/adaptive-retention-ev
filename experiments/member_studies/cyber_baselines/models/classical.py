"""Classical statistical and machine learning baselines for Cyber benchmark."""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

try:
    import xgboost as xgb

    HAS_XGBOOST = True
except ImportError:
    xgb = None
    HAS_XGBOOST = False

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import Ridge

    HAS_SKLEARN = True
except ImportError:
    RandomForestRegressor = None
    Ridge = None
    HAS_SKLEARN = False

try:
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    HAS_STATSMODELS = True
except ImportError:
    SARIMAX = None
    HAS_STATSMODELS = False

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    pd = None
    HAS_PANDAS = False

from experiments.member_studies.cyber_baselines.models.base import BaseForecaster


def extract_features(record: dict[str, Any]) -> np.ndarray:
    """Flatten 24x7 x_hist and 24x5 c_future into a 288-dim 1D array."""
    x_hist = np.asarray(record["x_hist"], dtype=float).flatten()  # 168
    c_future = np.asarray(record["c_future"], dtype=float).flatten()  # 120
    return np.concatenate([x_hist, c_future])  # 288


class RidgeBaseline(BaseForecaster):
    """Multi-output Ridge Regression baseline."""

    def __init__(
        self,
        alpha: float = 1.0,
        initial_records: list[dict[str, Any]] | None = None,
    ) -> None:
        self.alpha = alpha
        self.model = Ridge(alpha=alpha)
        self.x_train: list[np.ndarray] = []
        self.y_train: list[np.ndarray] = []
        self.is_fitted = False

        if initial_records:
            for rec in initial_records:
                fc = rec.get("forecast", rec)
                self.x_train.append(extract_features(fc))
                self.y_train.append(np.asarray(rec["y_scaled"], dtype=float))
            self._fit()

    @property
    def name(self) -> str:
        return "Ridge"

    @property
    def param_count(self) -> int:
        # 288 input weights * 24 outputs + 24 intercepts = 6,936
        return 288 * 24 + 24

    def _fit(self) -> None:
        if len(self.x_train) > 0:
            X = np.vstack(self.x_train)
            Y = np.vstack(self.y_train)
            self.model.fit(X, Y)
            self.is_fitted = True

    def predict(self, record: dict[str, Any]) -> list[float]:
        if not self.is_fitted:
            # Fallback to mean of history or zeros
            return [0.0] * 24
        x = extract_features(record).reshape(1, -1)
        pred = self.model.predict(x)[0]
        # EV power/energy is non-negative
        pred = np.maximum(0.0, pred)
        return pred.tolist()

    def update(self, record: dict[str, Any], y_scaled: list[float]) -> dict[str, Any]:
        self.x_train.append(extract_features(record))
        self.y_train.append(np.asarray(y_scaled, dtype=float))
        self._fit()
        return {"status": "ok", "samples": len(self.x_train)}


class SARIMABaseline(BaseForecaster):
    """SARIMA baseline on a regular hourly index with origin-relative forecasting.

    Protocol (locked for run tag v3):
    - The observed series lives on a regular hourly DatetimeIndex; calendar gaps and
      incomplete days stay as NaN and are handled by the Kalman filter, never concatenated away.
    - Parameters are re-estimated on the most recent 336 hours every ``refit_interval``
      complete-label updates. Between refits, the fitted state is advanced with every newly
      arrived complete day via ``append(refit=False)``.
    - ``predict`` never mutates state: it forecasts from the end of the filtered state up to the
      requested origin's horizon and returns the final 24 hours (origin-relative horizon).
    - Failed fits/advances and fallback forecasts are counted and exported as diagnostics.
    """

    def __init__(
        self,
        order: tuple[int, int, int] = (1, 0, 1),
        seasonal_order: tuple[int, int, int, int] = (1, 0, 0, 24),
        maxiter: int = 15,
        refit_interval: int = 7,
        initial_records: list[dict[str, Any]] | None = None,
    ) -> None:
        self.order = order
        self.seasonal_order = seasonal_order
        self.maxiter = maxiter
        self.refit_interval = refit_interval

        self.hourly_dict: dict[Any, float] = {}
        self.fitted_res = None
        self.step_count = 0
        self.last_fit_status = "unfitted"
        self.fit_error: str | None = None
        self.fit_attempts = 0
        self.fit_failures = 0
        self.advance_failures = 0
        self.fallback_forecasts = 0
        self.model_forecasts = 0
        self.fallback_reasons: dict[str, int] = {}

        if not (HAS_PANDAS and HAS_STATSMODELS):
            # Optional dependencies missing: every forecast is a counted "unfitted" fallback
            self.last_fit_status = "dependencies_unavailable"
        elif initial_records:
            for rec in initial_records:
                timestamps = self._extract_timestamps(rec)
                y_scaled = rec.get("y_scaled", [])
                if len(y_scaled) == len(timestamps):
                    for t, v in zip(timestamps, y_scaled, strict=True):
                        self.hourly_dict[t] = float(v)
            self._fit()

    @property
    def name(self) -> str:
        return "SARIMA"

    @property
    def param_count(self) -> int:
        return sum(self.order[::2]) + sum(self.seasonal_order[::2]) + 1

    @property
    def diagnostics(self) -> dict[str, Any]:
        """Surface fitting status, failures and fallback usage for auditability."""
        return {
            "last_fit_status": self.last_fit_status,
            "fit_error": self.fit_error,
            "step_count": self.step_count,
            "total_hourly_points": len(self.hourly_dict),
            "fit_attempts": self.fit_attempts,
            "fit_failures": self.fit_failures,
            "advance_failures": self.advance_failures,
            "model_forecasts": self.model_forecasts,
            "fallback_forecasts": self.fallback_forecasts,
            "fallback_reasons": dict(self.fallback_reasons),
        }

    def _extract_timestamps(self, record: dict[str, Any]) -> list[Any]:
        """Extract the 24 hourly horizon timestamps of a forecast record."""
        fc = record.get("forecast", record)
        labels = fc.get("future_labels")
        if HAS_PANDAS and labels and len(labels) == 24:
            return [pd.Timestamp(t) for t in labels]
        if HAS_PANDAS and "origin" in fc:
            base = pd.Timestamp(fc["origin"])
            return [base + pd.Timedelta(hours=h) for h in range(24)]
        raise ValueError("SARIMA record has neither future_labels nor origin timestamps")

    def _state_end(self) -> Any:
        return self.fitted_res.fittedvalues.index[-1]

    def _observed_series(self, start: Any, end: Any) -> Any:
        """Observed values on a regular hourly grid [start, end]; unobserved hours are NaN."""
        idx = pd.date_range(start=start, end=end, freq="h")
        return pd.Series(self.hourly_dict, dtype=float).reindex(idx)

    def _fit(self) -> None:
        """Re-estimate parameters on the most recent 336 hours (14 days) of the hourly grid."""
        if not HAS_STATSMODELS or not HAS_PANDAS or not self.hourly_dict:
            return
        self.fit_attempts += 1
        max_t = max(self.hourly_dict)
        start = max(min(self.hourly_dict), max_t - pd.Timedelta(hours=335))
        active_series = self._observed_series(start, max_t)

        if active_series.notna().sum() < 48:
            self.last_fit_status = "insufficient_data"
            self.fit_failures += 1
            self._advance_state()
            return
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                mod = SARIMAX(
                    active_series,
                    order=self.order,
                    seasonal_order=self.seasonal_order,
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                )
                self.fitted_res = mod.fit(disp=False, maxiter=self.maxiter)
            self.last_fit_status = "ok"
            self.fit_error = None
        except Exception as e:  # noqa: BLE001 - surfaced through diagnostics
            self.last_fit_status = "failed"
            self.fit_error = str(e)
            self.fit_failures += 1
            # Keep previous parameters but bring the filtered state up to the newest data
            self._advance_state()

    def _advance_state(self) -> None:
        """Filter every observed hour after the current state end (gaps as NaN), no refit."""
        if self.fitted_res is None or not self.hourly_dict:
            return
        last_t = self._state_end()
        max_t = max(self.hourly_dict)
        if max_t <= last_t:
            return
        new_s = self._observed_series(last_t + pd.Timedelta(hours=1), max_t)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.fitted_res = self.fitted_res.append(new_s, refit=False)
        except Exception as e:  # noqa: BLE001 - surfaced through diagnostics
            self.advance_failures += 1
            self.fit_error = f"advance_failed: {e}"

    def _fallback(self, record: dict[str, Any], reason: str) -> list[float]:
        self.fallback_forecasts += 1
        self.fallback_reasons[reason] = self.fallback_reasons.get(reason, 0) + 1
        x_hist = record.get("x_hist", [])
        return [row[0] if len(row) >= 7 and row[-1] > 0.5 else 0.0 for row in x_hist]

    def predict(self, record: dict[str, Any]) -> list[float]:
        """Forecast the record's 24-hour horizon relative to the end of the filtered state."""
        if self.fitted_res is None or not HAS_PANDAS:
            return self._fallback(record, "unfitted")
        try:
            target_timestamps = self._extract_timestamps(record)
            last_t = self._state_end()
            steps = int((target_timestamps[-1] - last_t) / pd.Timedelta(hours=1))
            if steps < 24:
                return self._fallback(record, "horizon_overlaps_state")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fc = np.asarray(self.fitted_res.forecast(steps=steps), dtype=float)[-24:]
            if not np.all(np.isfinite(fc)):
                return self._fallback(record, "non_finite_forecast")
            self.model_forecasts += 1
            return np.maximum(0.0, fc).tolist()
        except Exception as e:  # noqa: BLE001 - surfaced through diagnostics
            self.fit_error = f"predict_failed: {e}"
            return self._fallback(record, "predict_exception")

    def update(self, record: dict[str, Any], y_scaled: list[float]) -> dict[str, Any]:
        """Add a newly arrived complete day; refit weekly, otherwise advance the state."""
        if not (HAS_PANDAS and HAS_STATSMODELS):
            self.step_count += 1
            return {"status": self.last_fit_status, "step": self.step_count, "total_points": 0}
        timestamps = self._extract_timestamps(record)
        for t, v in zip(timestamps, y_scaled, strict=True):
            self.hourly_dict[t] = float(v)

        self.step_count += 1
        if self.step_count % self.refit_interval == 0 or self.fitted_res is None:
            self._fit()
        else:
            self._advance_state()

        return {
            "status": self.last_fit_status,
            "step": self.step_count,
            "total_points": len(self.hourly_dict),
        }


class RandomForestBaseline(BaseForecaster):
    """Random Forest regressor with model-appropriate weekly refit."""

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 10,
        refit_interval: int = 7,
        seed: int = 42,
        initial_records: list[dict[str, Any]] | None = None,
    ) -> None:
        self.seed = seed
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.refit_interval = refit_interval
        self.model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=seed,
            n_jobs=-1,
        )
        self.x_train: list[np.ndarray] = []
        self.y_train: list[np.ndarray] = []
        self.is_fitted = False
        self.step_count = 0

        if initial_records:
            for rec in initial_records:
                fc = rec.get("forecast", rec)
                self.x_train.append(extract_features(fc))
                self.y_train.append(np.asarray(rec["y_scaled"], dtype=float))
            self._fit()

    @property
    def name(self) -> str:
        return "Random Forest"

    @property
    def param_count(self) -> int:
        return self.n_estimators * (2 ** (self.max_depth + 1) - 1)

    def _fit(self) -> None:
        if len(self.x_train) > 0:
            X = np.vstack(self.x_train)
            Y = np.vstack(self.y_train)
            self.model.fit(X, Y)
            self.is_fitted = True

    def predict(self, record: dict[str, Any]) -> list[float]:
        if not self.is_fitted:
            return [0.0] * 24
        x = extract_features(record).reshape(1, -1)
        pred = self.model.predict(x)[0]
        pred = np.maximum(0.0, pred)
        return pred.tolist()

    def update(self, record: dict[str, Any], y_scaled: list[float]) -> dict[str, Any]:
        self.x_train.append(extract_features(record))
        self.y_train.append(np.asarray(y_scaled, dtype=float))
        self.step_count += 1
        if self.step_count % self.refit_interval == 0 or not self.is_fitted:
            self._fit()
        return {"status": "ok", "samples": len(self.x_train)}


class XGBoostBaseline(BaseForecaster):
    """Native multi-output XGBoost baseline with weekly refit frequency."""

    def __init__(
        self,
        n_estimators: int = 50,
        max_depth: int = 5,
        learning_rate: float = 0.1,
        refit_interval: int = 7,
        seed: int = 42,
        initial_records: list[dict[str, Any]] | None = None,
    ) -> None:
        self.seed = seed
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.refit_interval = refit_interval

        self.model = xgb.XGBRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=seed,
            n_jobs=-1,
            verbosity=0,
        )
        self.x_train: list[np.ndarray] = []
        self.y_train: list[np.ndarray] = []
        self.is_fitted = False
        self.step_count = 0

        if initial_records:
            for rec in initial_records:
                fc = rec.get("forecast", rec)
                self.x_train.append(extract_features(fc))
                self.y_train.append(np.asarray(rec["y_scaled"], dtype=float))
            self._fit()

    @property
    def name(self) -> str:
        return "XGBoost"

    @property
    def param_count(self) -> int:
        return self.n_estimators * (2 ** (self.max_depth + 1) - 1)

    def _fit(self) -> None:
        if len(self.x_train) > 0:
            X = np.vstack(self.x_train)
            Y = np.vstack(self.y_train)
            self.model.fit(X, Y)
            self.is_fitted = True

    def predict(self, record: dict[str, Any]) -> list[float]:
        if not self.is_fitted:
            return [0.0] * 24
        x = extract_features(record).reshape(1, -1)
        pred = self.model.predict(x)[0]
        pred = np.maximum(0.0, pred)
        return pred.tolist()

    def update(self, record: dict[str, Any], y_scaled: list[float]) -> dict[str, Any]:
        self.x_train.append(extract_features(record))
        self.y_train.append(np.asarray(y_scaled, dtype=float))
        self.step_count += 1
        if self.step_count % self.refit_interval == 0 or not self.is_fitted:
            self._fit()
        return {"status": "ok", "samples": len(self.x_train)}
