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
    """SARIMA baseline with calendar gap preservation, Kalman state advance, and weekly refit."""

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

        if initial_records:
            for rec in initial_records:
                timestamps = self._extract_timestamps(rec)
                y_scaled = rec.get("y_scaled", [])
                if len(y_scaled) == len(timestamps):
                    for t, v in zip(timestamps, y_scaled, strict=False):
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
        """Surface fitting status and error diagnostics for auditability."""
        return {
            "last_fit_status": self.last_fit_status,
            "fit_error": self.fit_error,
            "step_count": self.step_count,
            "total_hourly_points": len(self.hourly_dict),
        }

    def _extract_timestamps(self, record: dict[str, Any]) -> list[Any]:
        """Extract continuous hourly timestamps from record, with synthetic fallback."""
        fc = record.get("forecast", record)
        labels = fc.get("future_labels")
        if HAS_PANDAS and labels and len(labels) == 24:
            return [pd.to_datetime(t) for t in labels]
        if HAS_PANDAS and "origin" in fc:
            base = pd.to_datetime(fc["origin"])
            return [base + pd.Timedelta(hours=h) for h in range(24)]
        if HAS_PANDAS:
            base = pd.Timestamp("2022-11-01 00:00:00") + pd.Timedelta(hours=len(self.hourly_dict))
            return [base + pd.Timedelta(hours=h) for h in range(24)]
        return list(range(len(self.hourly_dict), len(self.hourly_dict) + 24))

    def _fit(self) -> None:
        """Full parameter optimization on active recent history (up to 336 hours = 14 days)."""
        if not HAS_STATSMODELS or not HAS_PANDAS or not self.hourly_dict:
            return

        min_t = min(self.hourly_dict.keys())
        max_t = max(self.hourly_dict.keys())
        full_idx = pd.date_range(start=min_t, end=max_t, freq="h")
        s = pd.Series(self.hourly_dict).reindex(full_idx)
        active_series = s.iloc[-336:]

        # Must have at least 48 valid non-null observations
        if active_series.dropna().shape[0] >= 48:
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
            except Exception as e:
                self.last_fit_status = "failed"
                self.fit_error = str(e)
                # Note: preserve previous fitted_res if present to prevent silent degradation

    def predict(self, record: dict[str, Any]) -> list[float]:
        """Predict 24 hours, advancing across any missing calendar gaps if needed."""
        x_hist = record.get("x_hist", [])
        if self.fitted_res is not None and HAS_PANDAS:
            try:
                target_timestamps = self._extract_timestamps(record)
                if (
                    hasattr(self.fitted_res, "fittedvalues")
                    and isinstance(self.fitted_res.fittedvalues.index, pd.DatetimeIndex)
                    and len(target_timestamps) == 24
                ):
                    last_t = self.fitted_res.fittedvalues.index[-1]
                    target_start = target_timestamps[0]
                    # Fill calendar gap with NaNs in Kalman filter
                    if target_start > last_t + pd.Timedelta(hours=1):
                        gap_idx = pd.date_range(
                            start=last_t + pd.Timedelta(hours=1),
                            end=target_start - pd.Timedelta(hours=1),
                            freq="h",
                        )
                        if len(gap_idx) > 0:
                            gap_s = pd.Series(np.nan, index=gap_idx)
                            with warnings.catch_warnings():
                                warnings.simplefilter("ignore")
                                self.fitted_res = self.fitted_res.append(gap_s, refit=False)

                fc = self.fitted_res.forecast(steps=24)
                return np.maximum(0.0, np.asarray(fc, dtype=float)).tolist()
            except Exception as e:
                self.fit_error = f"predict_failed: {e}"

        # Fallback to recent 24h from visible history
        fallback = [row[0] if len(row) >= 7 and row[-1] > 0.5 else 0.0 for row in x_hist]
        return fallback

    def update(self, record: dict[str, Any], y_scaled: list[float]) -> dict[str, Any]:
        """Incorporate newly arrived complete day. Refit weekly; advance Kalman state daily."""
        timestamps = self._extract_timestamps(record)
        for t, v in zip(timestamps, y_scaled, strict=False):
            self.hourly_dict[t] = float(v)

        self.step_count += 1
        # Weekly refit or initial fit if unfitted
        if self.step_count % self.refit_interval == 0 or self.fitted_res is None:
            self._fit()
        else:
            # Daily state advance between refits without re-estimating parameters
            if self.fitted_res is not None and HAS_PANDAS:
                try:
                    last_t = self.fitted_res.fittedvalues.index[-1]
                    new_start = timestamps[0]
                    if new_start > last_t + pd.Timedelta(hours=1):
                        gap_idx = pd.date_range(
                            start=last_t + pd.Timedelta(hours=1),
                            end=new_start - pd.Timedelta(hours=1),
                            freq="h",
                        )
                        gap_s = pd.Series(np.nan, index=gap_idx)
                        new_s = pd.concat([gap_s, pd.Series(y_scaled, index=timestamps)])
                    else:
                        new_s = pd.Series(y_scaled, index=timestamps)

                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        self.fitted_res = self.fitted_res.append(new_s, refit=False)
                except Exception as e:
                    self.fit_error = f"daily_advance_failed: {e}"

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
