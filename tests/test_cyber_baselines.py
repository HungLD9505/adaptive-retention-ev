"""Unit tests for Cyber UrbanEV Baseline Benchmark (Issue #95)."""

from __future__ import annotations

import unittest

import torch

from experiments.member_studies.cyber_baselines.models.classical import (
    HAS_SKLEARN,
    HAS_STATSMODELS,
    HAS_XGBOOST,
    RandomForestBaseline,
    RidgeBaseline,
    SARIMABaseline,
    XGBoostBaseline,
)
from experiments.member_studies.cyber_baselines.models.graph import GCNLSTMNet
from experiments.member_studies.cyber_baselines.models.naive import DailyNaive, SeasonalNaive
from experiments.member_studies.cyber_baselines.models.neural import (
    GRUForecaster,
    LSTMForecaster,
    MLPForecaster,
    TCNForecaster,
    TimeXerForecaster,
)


class TestCyberBaselines(unittest.TestCase):
    """Test suite for benchmark models, shapes, and metrics."""

    def setUp(self) -> None:
        self.B = 4
        self.x_hist = torch.rand(self.B, 24, 7)
        self.c_future = torch.rand(self.B, 24, 5)

        # Mock sample record for single prediction
        self.mock_record = {
            "origin": "2022-12-01T00:00:00+08:00",
            "history_labels": [f"2022-11-30T{h:02d}:00:00+08:00" for h in range(24)],
            "future_labels": [f"2022-12-01T{h:02d}:00:00+08:00" for h in range(24)],
            "x_hist": [[0.5, 0.1, 0.2, 0.3, 0.4, 0.5, 1.0]] * 24,
            "c_future": [[0.1, 0.2, 0.3, 0.4, 0.5]] * 24,
        }
        self.mock_y = [0.4] * 24

    def test_daily_naive(self) -> None:
        dn = DailyNaive()
        preds = dn.predict(self.mock_record)
        self.assertEqual(len(preds), 24)
        self.assertAlmostEqual(preds[0], 0.5)

    def test_seasonal_naive_fallback(self) -> None:
        sn = SeasonalNaive()
        preds = sn.predict(self.mock_record)
        self.assertEqual(len(preds), 24)
        # Without weekly history, should fallback to daily/history mean
        self.assertTrue(all(p >= 0.0 for p in preds))

    @unittest.skipUnless(HAS_SKLEARN, "scikit-learn is not installed in environment")
    def test_ridge_baseline(self) -> None:
        rec_with_y = {**self.mock_record, "y_scaled": self.mock_y}
        ridge = RidgeBaseline(alpha=1.0, initial_records=[rec_with_y] * 3)
        preds = ridge.predict(self.mock_record)
        self.assertEqual(len(preds), 24)
        self.assertTrue(all(p >= 0.0 for p in preds))

    @unittest.skipUnless(HAS_STATSMODELS, "statsmodels is not installed in environment")
    def test_sarima_baseline(self) -> None:
        rec_with_y = {**self.mock_record, "y_scaled": self.mock_y}
        sarima = SARIMABaseline(initial_records=[rec_with_y] * 3, maxiter=5)
        preds = sarima.predict(self.mock_record)
        self.assertEqual(len(preds), 24)
        self.assertTrue(all(p >= 0.0 for p in preds))

    @unittest.skipUnless(HAS_SKLEARN, "scikit-learn is not installed in environment")
    def test_random_forest_baseline(self) -> None:
        rec_with_y = {**self.mock_record, "y_scaled": self.mock_y}
        rf = RandomForestBaseline(
            n_estimators=10, max_depth=4, seed=42, initial_records=[rec_with_y] * 3
        )
        preds = rf.predict(self.mock_record)
        self.assertEqual(len(preds), 24)
        self.assertTrue(all(p >= 0.0 for p in preds))

    @unittest.skipUnless(HAS_XGBOOST, "xgboost is not installed in environment")
    def test_xgboost_baseline(self) -> None:
        rec_with_y = {**self.mock_record, "y_scaled": self.mock_y}
        xgb_m = XGBoostBaseline(
            n_estimators=10, max_depth=3, seed=42, initial_records=[rec_with_y] * 3
        )
        preds = xgb_m.predict(self.mock_record)
        self.assertEqual(len(preds), 24)
        self.assertTrue(all(p >= 0.0 for p in preds))

    def test_neural_models_shapes(self) -> None:
        models = [
            ("MLP", MLPForecaster()),
            ("GRU", GRUForecaster()),
            ("LSTM", LSTMForecaster()),
            ("TCN", TCNForecaster()),
            ("TimeXer", TimeXerForecaster()),
        ]

        for name, net in models:
            net.eval()
            with torch.no_grad():
                out = net(self.x_hist, self.c_future)
                self.assertEqual(out.shape, (self.B, 24), f"{name} output shape mismatch")
                # Softplus guarantees non-negativity
                self.assertTrue((out >= 0).all(), f"{name} contains negative outputs")

                latent = net.encode(self.x_hist)
                self.assertEqual(latent.shape[0], self.B, f"{name} latent batch mismatch")

    def test_gcn_lstm_shapes(self) -> None:
        N = 4
        adj = torch.eye(N)
        net = GCNLSTMNet(num_nodes=N, adj_norm=adj)
        x_seq = torch.rand(self.B, 24, N, 7)
        c_future = torch.rand(self.B, 24, 5)

        out = net(x_seq, c_future, node_idx=0)
        self.assertEqual(out.shape, (self.B, 24))
        self.assertTrue((out >= 0).all())


if __name__ == "__main__":
    unittest.main()
