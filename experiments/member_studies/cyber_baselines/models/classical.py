"""Classical statistical and machine learning baselines for Cyber benchmark."""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import xgboost as xgb
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from statsmodels.tsa.statespace.sarimax import SARIMAX

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
    """SARIMA baseline with weekly bounded refit on available hourly sequence."""

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
        self.series: list[float] = []
        self.fitted_res = None
        self.step_count = 0

        if initial_records:
            for rec in initial_records:
                for v in rec.get("y_scaled", []):
                    self.series.append(float(v))
            self._fit()

    @property
    def name(self) -> str:
        return "SARIMA"

    @property
    def param_count(self) -> int:
        return sum(self.order[::2]) + sum(self.seasonal_order[::2]) + 1

    def _fit(self) -> None:
        active_series = self.series[-336:]
        if len(active_series) >= 48:
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
            except Exception:
                self.fitted_res = None

    def predict(self, record: dict[str, Any]) -> list[float]:
        x_hist = record.get("x_hist", [])
        if self.fitted_res is not None:
            try:
                fc = self.fitted_res.forecast(steps=24)
                return np.maximum(0.0, np.asarray(fc, dtype=float)).tolist()
            except Exception:
                pass

        # Fallback to recent 24h from visible history
        fallback = [row[0] if len(row) >= 7 and row[-1] > 0.5 else 0.0 for row in x_hist]
        return fallback

    def update(self, record: dict[str, Any], y_scaled: list[float]) -> dict[str, Any]:
        for v in y_scaled:
            self.series.append(float(v))
        self.step_count += 1
        if self.step_count % self.refit_interval == 0 or self.fitted_res is None:
            self._fit()
        return {"status": "ok", "total_hours": len(self.series)}


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
