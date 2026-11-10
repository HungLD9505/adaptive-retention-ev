"""Unit and regression tests for Cyber UrbanEV Baseline Benchmark (Issue #95)."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

import numpy as np
import torch

from experiments.member_studies.cyber_baselines.config import BenchmarkConfig
from experiments.member_studies.cyber_baselines.data import TargetReplayData
from experiments.member_studies.cyber_baselines.models.base import BaseForecaster
from experiments.member_studies.cyber_baselines.models.classical import (
    HAS_PANDAS,
    HAS_SKLEARN,
    HAS_STATSMODELS,
    HAS_XGBOOST,
    RandomForestBaseline,
    RidgeBaseline,
    SARIMABaseline,
    XGBoostBaseline,
)
from experiments.member_studies.cyber_baselines.models.graph import BasicGCNLSTM, GCNLSTMNet
from experiments.member_studies.cyber_baselines.models.naive import DailyNaive, SeasonalNaive
from experiments.member_studies.cyber_baselines.models.neural import (
    GRUForecaster,
    LSTMForecaster,
    MLPForecaster,
    TCNForecaster,
    TimeXerForecaster,
)
from experiments.member_studies.cyber_baselines.runner import (
    BenchmarkRunner,
    append_summary_to_csv,
)


class MockStatefulForecaster(BaseForecaster):
    """Forecaster that outputs 0.0 before update and 99.0 after update for testing causal arrival."""

    def __init__(self) -> None:
        self.was_updated = False

    @property
    def name(self) -> str:
        return "MockStateful"

    @property
    def param_count(self) -> int:
        return 1

    def predict(self, record: dict[str, Any]) -> list[float]:
        val = 99.0 if self.was_updated else 0.0
        return [val] * 24

    def update(self, record: dict[str, Any], y_scaled: list[float]) -> dict[str, Any]:
        self.was_updated = True
        return {"status": "ok"}


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

    # -------------------------------------------------------------------------
    # Regression fixtures addressing Reviewer Findings (Issue #95 / PR #104)
    # -------------------------------------------------------------------------

    def test_delayed_label_arrival_guard(self) -> None:
        """Finding 3: Future label availability must NOT trigger premature model update."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            cfg = BenchmarkConfig(
                output_dir=Path(tmp_dir), runs_csv_path=Path(tmp_dir) / "runs.csv"
            )
            runner = BenchmarkRunner(cfg)

            origin1 = "2022-12-01T00:00:00+08:00"
            origin2 = "2022-12-02T00:00:00+08:00"

            # Dec 1 label is delayed until Dec 10
            mock_labels = {
                origin1: {
                    "origin": origin1,
                    "file_valid": [True] * 24,
                    "available_at": ["2022-12-10T00:00:00+08:00"] * 24,
                    "energy_kwh": [10.0] * 24,
                },
                origin2: {
                    "origin": origin2,
                    "file_valid": [True] * 24,
                    "available_at": ["2022-12-03T00:00:00+08:00"] * 24,
                    "energy_kwh": [10.0] * 24,
                },
            }
            mock_forecasts = {
                origin1: {
                    "origin": origin1,
                    "x_hist": [[0.0] * 7] * 24,
                    "c_future": [[0.0] * 5] * 24,
                },
                origin2: {
                    "origin": origin2,
                    "x_hist": [[0.0] * 7] * 24,
                    "c_future": [[0.0] * 5] * 24,
                },
            }
            schedule = [
                {"origin": origin1, "status": "created", "identity": ["urbanev", "SZH", "1405"]},
                {"origin": origin2, "status": "created", "identity": ["urbanev", "SZH", "1405"]},
            ]
            replay_data = TargetReplayData(
                entity_id="1405",
                p95_scale=1.0,
                initial_trainable_count=0,
                initial_records=[],
                schedule=schedule,
                forecasts=mock_forecasts,
                labels=mock_labels,
            )

            model = MockStatefulForecaster()
            summary = runner.run_replay(model, replay_data)

            # Check exported predictions
            preds_file = cfg.output_dir / f"{summary.run_id}_predictions.json"
            self.assertTrue(preds_file.is_file())
            with open(preds_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            daily = data["daily_results"]
            self.assertEqual(len(daily), 2)
            # Origin 1 prediction was issued at origin 1 (value 0.0)
            self.assertEqual(daily[0]["predictions_kwh"][0], 0.0)
            # Origin 2 prediction was issued at origin 2: Dec 1 label was NOT available yet!
            # Therefore, model must NOT have updated yet -> must predict 0.0 (NOT 99.0)!
            self.assertEqual(
                daily[1]["predictions_kwh"][0],
                0.0,
                "Premature learning detected: model updated before label availability clock!",
            )

    def _two_origin_replay(self, label1_available_at: str) -> TargetReplayData:
        origin1 = "2022-12-01T00:00:00+08:00"
        origin2 = "2022-12-02T00:00:00+08:00"
        labels = {
            origin1: {
                "origin": origin1,
                "file_valid": [True] * 24,
                "available_at": [label1_available_at] * 24,
                "energy_kwh": [10.0] * 24,
            },
            origin2: {
                "origin": origin2,
                "file_valid": [True] * 24,
                "available_at": ["2022-12-03T00:00:00+08:00"] * 24,
                "energy_kwh": [10.0] * 24,
            },
        }
        forecasts = {
            o: {"origin": o, "x_hist": [[0.0] * 7] * 24, "c_future": [[0.0] * 5] * 24}
            for o in (origin1, origin2)
        }
        schedule = [
            {"origin": o, "status": "created", "identity": ["urbanev", "SZH", "1405"]}
            for o in (origin1, origin2)
        ]
        return TargetReplayData(
            entity_id="1405",
            p95_scale=1.0,
            initial_trainable_count=0,
            initial_records=[],
            schedule=schedule,
            forecasts=forecasts,
            labels=labels,
        )

    def test_label_arriving_at_next_origin_is_used_before_that_prediction(self) -> None:
        """A label whose last hour arrives exactly at the next origin is causally usable there.

        All real UrbanEV labels arrive at origin + 24h, so updating only after the next
        prediction would silently delay every model by one extra day (v2 defect).
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            cfg = BenchmarkConfig(
                output_dir=Path(tmp_dir), runs_csv_path=Path(tmp_dir) / "runs.csv"
            )
            replay = self._two_origin_replay("2022-12-02T00:00:00+08:00")
            summary = BenchmarkRunner(cfg).run_replay(MockStatefulForecaster(), replay)
            data = json.loads((cfg.output_dir / f"{summary.run_id}_predictions.json").read_text())
            day1, day2 = data["daily_results"]
            # Day 1 forecast was saved before its own label (predict-before-label) ...
            self.assertEqual(day1["predictions_kwh"][0], 0.0)
            # ... and the Day 1 label, arrived at Day 2 00:00, updated the model before Day 2.
            self.assertEqual(day2["predictions_kwh"][0], 99.0)
            self.assertEqual(summary.scored_days, 2)

    def test_label_arriving_one_hour_after_next_origin_is_not_used(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cfg = BenchmarkConfig(
                output_dir=Path(tmp_dir), runs_csv_path=Path(tmp_dir) / "runs.csv"
            )
            replay = self._two_origin_replay("2022-12-02T01:00:00+08:00")
            summary = BenchmarkRunner(cfg).run_replay(MockStatefulForecaster(), replay)
            data = json.loads((cfg.output_dir / f"{summary.run_id}_predictions.json").read_text())
            self.assertEqual(data["daily_results"][1]["predictions_kwh"][0], 0.0)
            # Still scored once the replay clock passes its arrival
            self.assertEqual(summary.scored_days, 2)

    def test_run_ids_carry_run_tag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cfg = BenchmarkConfig(
                run_tag="vtest",
                output_dir=Path(tmp_dir),
                runs_csv_path=Path(tmp_dir) / "runs.csv",
            )
            replay = self._two_origin_replay("2022-12-02T00:00:00+08:00")
            summary = BenchmarkRunner(cfg).run_replay(DailyNaive(), replay)
            self.assertTrue(summary.run_id.startswith("cyber_vtest_daily_naive_"))

    def test_full_benchmark_refuses_to_overwrite_existing_ledger(self) -> None:
        from experiments.member_studies.cyber_baselines.cli import run_full_benchmark

        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "runs.csv"
            csv_path.write_text("existing evidence\n", encoding="utf-8")
            cfg = BenchmarkConfig(output_dir=Path(tmp_dir), runs_csv_path=csv_path)
            with self.assertRaises(FileExistsError):
                run_full_benchmark(cfg)
            self.assertEqual(csv_path.read_text(encoding="utf-8"), "existing evidence\n")

    def test_zero_scored_runs_handling(self) -> None:
        """Finding 4: Runs with zero scored days must return None metrics, not misleading 0.0."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "runs.csv"
            cfg = BenchmarkConfig(output_dir=Path(tmp_dir), runs_csv_path=csv_path)
            runner = BenchmarkRunner(cfg)

            origin1 = "2022-12-01T00:00:00+08:00"
            origin2 = "2022-12-02T00:00:00+08:00"

            # Labels exist but sensors are invalid (sensor dropouts)
            mock_labels = {
                origin1: {
                    "origin": origin1,
                    "file_valid": [False] * 24,
                    "available_at": ["2022-12-02T00:00:00+08:00"] * 24,
                    "energy_kwh": [0.0] * 24,
                },
                origin2: {
                    "origin": origin2,
                    "file_valid": [False] * 24,
                    "available_at": ["2022-12-03T00:00:00+08:00"] * 24,
                    "energy_kwh": [0.0] * 24,
                },
            }
            mock_forecasts = {
                origin1: {
                    "origin": origin1,
                    "x_hist": [[0.0] * 7] * 24,
                    "c_future": [[0.0] * 5] * 24,
                },
                origin2: {
                    "origin": origin2,
                    "x_hist": [[0.0] * 7] * 24,
                    "c_future": [[0.0] * 5] * 24,
                },
            }
            schedule = [
                {"origin": origin1, "status": "created", "identity": ["urbanev", "SZH", "1405"]},
                {"origin": origin2, "status": "created", "identity": ["urbanev", "SZH", "1405"]},
            ]
            replay_data = TargetReplayData(
                entity_id="1405",
                p95_scale=1.0,
                initial_trainable_count=0,
                initial_records=[],
                schedule=schedule,
                forecasts=mock_forecasts,
                labels=mock_labels,
            )

            dn = DailyNaive()
            summary = runner.run_replay(dn, replay_data)
            append_summary_to_csv(summary, csv_path)

            self.assertEqual(summary.scheduled_days, 2)
            self.assertEqual(summary.issued_days, 2)
            self.assertEqual(summary.scored_days, 0)
            self.assertIsNone(summary.mae_kwh, "Zero scored days must have None MAE, not 0.0")
            self.assertIsNone(summary.rmse_kwh, "Zero scored days must have None RMSE, not 0.0")

            # Verify CSV formatting has empty string for metrics
            with open(csv_path, "r", encoding="utf-8") as f:
                content = f.read()
            lines = content.strip().split("\n")
            row = lines[1].split(",")
            # Index 8 (mae_kwh) and 9 (rmse_kwh)
            self.assertEqual(row[8], "", "CSV mae_kwh must be empty string for unscored run")
            self.assertEqual(row[9], "", "CSV rmse_kwh must be empty string for unscored run")

    @unittest.skipUnless(HAS_STATSMODELS, "statsmodels is not installed in environment")
    def test_sarima_state_advance_between_refits(self) -> None:
        """Finding 2: SARIMA state must advance horizon after receiving complete day."""
        import pandas as pd

        # Setup 3 initial days
        initial_records = []
        base_time = pd.Timestamp("2022-11-20 00:00:00")
        for day in range(3):
            day_t = base_time + pd.Timedelta(days=day)
            rec = {
                "origin": day_t.isoformat(),
                "future_labels": [(day_t + pd.Timedelta(hours=h)).isoformat() for h in range(24)],
                "x_hist": [[0.5] * 7] * 24,
                "y_scaled": [float(np.sin(day * 24 + h) + 1.0) for h in range(24)],
            }
            initial_records.append(rec)

        sarima = SARIMABaseline(initial_records=initial_records, maxiter=5, refit_interval=7)

        # Day 4 prediction
        day4_t = base_time + pd.Timedelta(days=3)
        rec4 = {
            "origin": day4_t.isoformat(),
            "future_labels": [(day4_t + pd.Timedelta(hours=h)).isoformat() for h in range(24)],
            "x_hist": [[0.5] * 7] * 24,
        }
        pred4 = sarima.predict(rec4)

        # Update with Day 4 complete observations
        y4 = [1.5] * 24
        sarima.update(rec4, y4)

        # Day 5 prediction
        day5_t = base_time + pd.Timedelta(days=4)
        rec5 = {
            "origin": day5_t.isoformat(),
            "future_labels": [(day5_t + pd.Timedelta(hours=h)).isoformat() for h in range(24)],
            "x_hist": [[0.5] * 7] * 24,
        }
        pred5 = sarima.predict(rec5)

        # Predictions must NOT be identical (horizon and Kalman state must have advanced)
        self.assertFalse(
            np.allclose(pred4, pred5),
            "SARIMA failed to advance forecasting state between weekly refits!",
        )

    def _sarima_fixture(self) -> tuple[Any, Any]:
        import pandas as pd

        base = pd.Timestamp("2022-11-20 00:00:00+08:00")
        initial = []
        for day in range(4):
            day_t = base + pd.Timedelta(days=day)
            initial.append(
                {
                    "origin": day_t.isoformat(),
                    "future_labels": [
                        (day_t + pd.Timedelta(hours=h)).isoformat() for h in range(24)
                    ],
                    "x_hist": [[0.5] * 7] * 24,
                    "y_scaled": [float(np.sin(h / 24 * 2 * np.pi) + 1.2) for h in range(24)],
                }
            )
        return base, initial

    def _day_record(self, base: Any, day: int) -> dict[str, Any]:
        import pandas as pd

        day_t = base + pd.Timedelta(days=day)
        return {
            "origin": day_t.isoformat(),
            "future_labels": [(day_t + pd.Timedelta(hours=h)).isoformat() for h in range(24)],
            "x_hist": [[0.5] * 7] * 24,
        }

    @unittest.skipUnless(HAS_STATSMODELS and HAS_PANDAS, "statsmodels/pandas not installed")
    def test_sarima_predict_does_not_mutate_state_and_uses_origin_horizon(self) -> None:
        base, initial = self._sarima_fixture()
        sarima = SARIMABaseline(initial_records=initial, maxiter=5)
        state_end = sarima.fitted_res.fittedvalues.index[-1]

        # Origin 1 day ahead of the filtered state vs 2 days ahead (missing day in between)
        near = sarima.predict(self._day_record(base, 4))
        far = sarima.predict(self._day_record(base, 5))
        self.assertEqual(sarima.fitted_res.fittedvalues.index[-1], state_end)
        expected_far = np.maximum(0.0, np.asarray(sarima.fitted_res.forecast(steps=48))[-24:])
        np.testing.assert_allclose(far, expected_far)
        expected_near = np.maximum(0.0, np.asarray(sarima.fitted_res.forecast(steps=24)))
        np.testing.assert_allclose(near, expected_near)
        self.assertEqual(sarima.diagnostics["fallback_forecasts"], 0)

    @unittest.skipUnless(HAS_STATSMODELS and HAS_PANDAS, "statsmodels/pandas not installed")
    def test_sarima_update_after_calendar_gap_keeps_hourly_index(self) -> None:
        import pandas as pd

        base, initial = self._sarima_fixture()
        sarima = SARIMABaseline(initial_records=initial, maxiter=5, refit_interval=7)
        # Day 4 label never arrives (incomplete); day 5 arrives -> 24 NaN hours in between
        sarima.update(self._day_record(base, 5), [2.0] * 24)
        diag = sarima.diagnostics
        self.assertEqual(diag["advance_failures"], 0, diag)
        idx = sarima.fitted_res.fittedvalues.index
        self.assertEqual(idx[-1], base + pd.Timedelta(days=5, hours=23))
        self.assertEqual(len(idx), 6 * 24, "calendar gap must stay on the hourly index")
        self.assertTrue(np.isnan(np.asarray(sarima.fitted_res.model.endog)[4 * 24 : 5 * 24]).all())

    @unittest.skipUnless(HAS_STATSMODELS and HAS_PANDAS, "statsmodels/pandas not installed")
    def test_sarima_failed_or_unfitted_forecasts_are_counted(self) -> None:
        sarima = SARIMABaseline()  # no history -> cannot fit
        sarima.predict(self.mock_record)
        self.assertEqual(sarima.diagnostics["fallback_forecasts"], 1)
        self.assertEqual(sarima.diagnostics["fallback_reasons"], {"unfitted": 1})

    def test_runner_exports_model_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cfg = BenchmarkConfig(
                output_dir=Path(tmp_dir), runs_csv_path=Path(tmp_dir) / "runs.csv"
            )
            replay = self._two_origin_replay("2022-12-02T00:00:00+08:00")
            summary = BenchmarkRunner(cfg).run_replay(SARIMABaseline(), replay)
            data = json.loads((cfg.output_dir / f"{summary.run_id}_predictions.json").read_text())
            self.assertIn("model_diagnostics", data)
            self.assertGreaterEqual(data["model_diagnostics"]["fallback_forecasts"], 1)

    def test_graph_node_selection_uses_nearest_development_supports(self) -> None:
        import zipfile

        from experiments.member_studies.cyber_baselines.data import (
            STATION_DISTANCE_CSV,
            load_all_targets_history_lookup,
            select_graph_nodes,
        )

        ids = ["T1", "D1", "D2", "D3", "F1"]
        pos = {"T1": 0.0, "D1": 100.0, "D2": 300.0, "D3": 900.0, "F1": 10.0}
        roles = {"T1": "development", "D1": "development", "D2": "development",
                 "D3": "development", "F1": "final"}  # fmt: skip
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            lines = ["ID," + ",".join(ids)]
            lines += [a + "," + ",".join(str(abs(pos[a] - pos[b])) for b in ids) for a in ids]
            raw_zip = tmp / "raw.zip"
            with zipfile.ZipFile(raw_zip, "w") as z:
                z.writestr(STATION_DISTANCE_CSV, "\n".join(lines) + "\n")
            with open(tmp / "entities.jsonl", "w", encoding="utf-8") as f:
                for s, r in roles.items():
                    f.write(json.dumps({"identity": ["urbanev", "SZH", s], "role": r}) + "\n")

            node_ids, lock = select_graph_nodes(raw_zip, tmp, ("T1",), support_k=2)
            # Closest station F1 is Final-role and must be excluded
            self.assertEqual(node_ids, ["D1", "D2", "T1"])
            self.assertEqual([n["station_id"] for n in lock["neighbors"]["T1"]], ["D1", "D2"])

            origin = "2022-12-01T00:00:00+08:00"
            with open(tmp / "training.jsonl", "w", encoding="utf-8") as f:
                f.write("")
            with open(tmp / "forecasts.jsonl", "w", encoding="utf-8") as f:
                for s, role in (("D1", "development"), ("F1", "final")):
                    rec = {"role": role, "identity": ["urbanev", "SZH", s], "origin": origin,
                           "x_hist": [[1.0] * 7] * 24}  # fmt: skip
                    f.write(json.dumps(rec) + "\n")
            lookup = load_all_targets_history_lookup(tmp, ["D1", "F1"])
            self.assertIn(("D1", origin), lookup)
            self.assertNotIn(("F1", origin), lookup, "Final-role histories must never be read")

    def test_gcn_lstm_reads_support_histories_from_lookup(self) -> None:
        node_ids = ["N1", "T1"]
        origin = "2022-12-01T00:00:00+08:00"
        rec = {"origin": origin, "x_hist": [[1.0] * 7] * 24, "c_future": [[0.1] * 5] * 24}
        low = BasicGCNLSTM(node_ids, np.full((2, 2), 0.5), "T1", seed=1,
                           history_lookup={("N1", origin): [[1.0] * 7] * 24})  # fmt: skip
        high = BasicGCNLSTM(node_ids, np.full((2, 2), 0.5), "T1", seed=1,
                            history_lookup={("N1", origin): [[40.0] * 7] * 24})  # fmt: skip
        self.assertGreater(np.max(np.abs(np.subtract(low.predict(rec), high.predict(rec)))), 1e-4)
        self.assertEqual(low.diagnostics["missing_support_histories"], 0)
        missing = BasicGCNLSTM(node_ids, np.full((2, 2), 0.5), "T1", seed=1)
        missing.predict(rec)
        self.assertEqual(missing.diagnostics["missing_support_histories"], 1)

    def test_gcn_lstm_distinct_node_signals(self) -> None:
        """Finding 1: GCN-LSTM must receive and aggregate distinct multi-node histories."""
        node_ids = ["1153", "1405", "1693", "2152"]
        adj_norm = np.array(
            [
                [0.9, 0.1, 0.0, 0.0],
                [0.1, 0.8, 0.1, 0.0],
                [0.0, 0.1, 0.8, 0.1],
                [0.0, 0.0, 0.1, 0.9],
            ]
        )

        gcn = BasicGCNLSTM(
            node_ids=node_ids,
            adj_norm=adj_norm,
            target_id="1405",
            seed=42,
        )

        # Signal A: All nodes have low signal 1.0
        rec_a = {
            "origin": "2022-12-01T00:00:00+08:00",
            "c_future": [[0.1] * 5] * 24,
            "node_histories": {nid: [[1.0] * 7] * 24 for nid in node_ids},
        }
        pred_a = gcn.predict(rec_a)

        # Signal B: Neighboring station 1153 has high surge signal 50.0, target 1405 stays identical
        rec_b = {
            "origin": "2022-12-01T00:00:00+08:00",
            "c_future": [[0.1] * 5] * 24,
            "node_histories": {
                "1153": [[50.0] * 7] * 24,
                "1405": [[1.0] * 7] * 24,
                "1693": [[1.0] * 7] * 24,
                "2152": [[1.0] * 7] * 24,
            },
        }
        pred_b = gcn.predict(rec_b)

        # Target node prediction must change because of spatial convolution with neighbor 1153
        max_diff = float(np.max(np.abs(np.array(pred_a) - np.array(pred_b))))
        self.assertGreater(
            max_diff,
            1e-3,
            "GCN-LSTM failed to aggregate spatial signals: neighbor change had no effect!",
        )

    def test_binary_hash_contract(self) -> None:
        """Finding 5: Binary mode serialization guarantees exact SHA-256 agreement on disk."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            cfg = BenchmarkConfig(
                output_dir=Path(tmp_dir), runs_csv_path=Path(tmp_dir) / "runs.csv"
            )
            runner = BenchmarkRunner(cfg)

            origin = "2022-12-01T00:00:00+08:00"
            mock_labels = {
                origin: {
                    "origin": origin,
                    "file_valid": [True] * 24,
                    "available_at": ["2022-12-02T00:00:00+08:00"] * 24,
                    "energy_kwh": [10.0] * 24,
                }
            }
            mock_forecasts = {
                origin: {"origin": origin, "x_hist": [[0.5] * 7] * 24, "c_future": [[0.1] * 5] * 24}
            }
            schedule = [
                {"origin": origin, "status": "created", "identity": ["urbanev", "SZH", "1405"]}
            ]
            replay_data = TargetReplayData(
                entity_id="1405",
                p95_scale=1.0,
                initial_trainable_count=0,
                initial_records=[],
                schedule=schedule,
                forecasts=mock_forecasts,
                labels=mock_labels,
            )

            dn = DailyNaive()
            summary = runner.run_replay(dn, replay_data)

            json_path = cfg.output_dir / f"{summary.run_id}_predictions.json"
            with open(json_path, "rb") as f:
                disk_bytes = f.read()
            disk_sha256 = hashlib.sha256(disk_bytes).hexdigest()

            # Hash in summary must match exact disk bytes without CRLF divergence
            self.assertEqual(
                summary.predictions_sha256,
                disk_sha256,
                "Checksum mismatch between runner memory hash and on-disk binary bytes!",
            )


if __name__ == "__main__":
    unittest.main()
