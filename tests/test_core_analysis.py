"""Saved prediction identity and scale checks without raw data or model fitting."""

import json
import tempfile
import unittest
from pathlib import Path

from ev_models.checkpoint import digest
from tools.analyze_core_comparisons import audit_gap_kwh, saved_errors


class SavedErrorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.origin = "2022-12-01T00:00:00+08:00"
        self.forecast = {
            "origin": self.origin,
            "active": 0.01,
            "record": {"energy_scale": 10, "x_hist": [[0, 1]] * 24},
        }
        self.previous = "0" * 64
        self.write_tick(0, self.forecast, [])
        self.checksum = digest(self.root / "tick-0000/forecasts.json")
        self.event = {
            "event": "score",
            "origin": self.origin,
            "prediction_sha256": self.checksum,
            "issued_active": 0.01,
            "mae_scaled": [2],
            "mse_scaled": [5],
        }
        self.write_tick(1, {}, [self.event])
        self.report = {
            "candidate_levels": [0.01],
            "issued_days": 1,
            "scored_days": 1,
            "commit_chain": self.previous,
        }

    def tearDown(self):
        self.temp.cleanup()

    def write_tick(self, index, forecast, events):
        tick = self.root / f"tick-{index:04d}"
        tick.mkdir()
        (tick / "forecasts.json").write_text(json.dumps(forecast))
        (tick / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
        meta = {
            "index": index,
            "previous": self.previous,
            "files": {name: digest(tick / name) for name in ("forecasts.json", "events.jsonl")},
        }
        (tick / "commit.json").write_text(json.dumps(meta))
        self.previous = digest(tick / "commit.json")

    def test_scaled_daily_errors_and_real_zero_history_coverage(self):
        errors, coverage = saved_errors(self.root, self.report)
        self.assertEqual(errors[0].mae, 20)
        self.assertEqual(errors[0].mse, 500)
        self.assertEqual(coverage["valid_history_hours_min"], 24)

    def test_changed_forecast_rejected_before_score_aggregation(self):
        (self.root / "tick-0000/forecasts.json").write_text("{}")
        with self.assertRaises(ValueError):
            saved_errors(self.root, self.report)

    def test_wrong_score_population_rejected(self):
        self.report["scored_days"] = 0
        with self.assertRaises(ValueError):
            saved_errors(self.root, self.report)


class AuditGapTests(unittest.TestCase):
    def test_unscored_audit_retains_null(self):
        self.assertIsNone(audit_gap_kwh({"paired_days": 0, "mean_new_minus_old": None}, 10))
        self.assertIsNone(audit_gap_kwh({"paired_days": 0, "mean_new_minus_old": None}, None))

    def test_scored_real_zero_and_signed_gap_are_converted(self):
        self.assertEqual(audit_gap_kwh({"paired_days": 2, "mean_new_minus_old": 0}, 10), 0)
        self.assertEqual(audit_gap_kwh({"paired_days": 2, "mean_new_minus_old": -0.1}, 10), -1)

    def test_inconsistent_audit_missing_mean_is_rejected(self):
        for count, value in ((0, 1), (2, None), (-1, 0)):
            with self.assertRaises(ValueError):
                audit_gap_kwh({"paired_days": count, "mean_new_minus_old": value}, 10)


class AnalysisPipelineTests(unittest.TestCase):
    def test_five_method_fixture_uses_original_units_and_all_paired_seeds(self):
        from argparse import Namespace

        from ev_models.checkpoint import write_json
        from ev_runner.run import runtime_code
        from tools.analyze_core_comparisons import METHODS, analyze

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference, comparators = root / "reference", root / "comparators"
            reference.mkdir()
            comparators.mkdir()
            start = "2022-12-01T00:00:00+08:00"
            cohort = {"seeds": [42, 43, 44], "budgets": {}}
            for budget in (7, 14, 28):
                folder = root / "inputs" / f"urbanev-SZH-{budget}d"
                folder.mkdir(parents=True)
                write_json(folder / "manifest.json", {"config": {"deployment": start}})
                cohort["budgets"][str(budget)] = {
                    "manifest_sha256": digest(folder / "manifest.json"),
                    "entities": [{"entity_id": "a", "initial_trainable": 1}],
                }
            write_json(root / "cohort.json", cohort)
            code = {"files": runtime_code()["files"], "dirty": False}
            matrices = [
                {
                    "status": "technical_success",
                    "seeds": [42, 43, 44],
                    "selection_sha256": digest(root / "cohort.json"),
                    "runs": [],
                }
                for _ in range(2)
            ]
            checks = [[], []]
            for budget in (7, 14, 28):
                for seed in (42, 43, 44):
                    for method in METHODS:
                        group = 0 if method in ("adaptive", "target_only") else 1
                        folder = (
                            reference if group == 0 else comparators
                        ) / f"{budget}-{seed}-{method}"
                        folder.mkdir()
                        previous = "0" * 64
                        normalized = METHODS.index(method) + 1
                        forecast = {
                            "origin": start,
                            "active": 0.01,
                            "record": {"energy_scale": 10, "x_hist": [[0, 1]] * 24},
                        }
                        for day in (0, 1):
                            tick = folder / f"tick-{day:04d}"
                            tick.mkdir()
                            (tick / "forecasts.json").write_text(
                                json.dumps(forecast if day == 0 else {})
                            )
                            events = (
                                []
                                if day == 0
                                else [
                                    {
                                        "event": "score",
                                        "origin": start,
                                        "issued_active": 0.01,
                                        "prediction_sha256": digest(
                                            folder / "tick-0000/forecasts.json"
                                        ),
                                        "mae_scaled": [normalized],
                                        "mse_scaled": [normalized**2],
                                    }
                                ]
                            )
                            (tick / "events.jsonl").write_text(
                                "".join(json.dumps(e) + "\n" for e in events)
                            )
                            meta = {
                                "index": day,
                                "previous": previous,
                                "files": {
                                    n: digest(tick / n) for n in ("forecasts.json", "events.jsonl")
                                },
                            }
                            write_json(tick / "commit.json", meta)
                            previous = digest(tick / "commit.json")
                        config = {
                            "replay_days": 90,
                            "state_retention": "latest",
                            "development_entities": ["a"],
                            "initial_training": {"seed": seed},
                            "online_training": {"seed": seed},
                            "controller": {"seed": seed},
                            "method": {"name": method},
                        }
                        report = {
                            "run_id": folder.name,
                            "binding": {
                                "input": {
                                    "dataset_id": "urbanev",
                                    "city_id": "SZH",
                                    "history_days": budget,
                                    "entity_id": "a",
                                    "input_manifest_sha256": cohort["budgets"][str(budget)][
                                        "manifest_sha256"
                                    ],
                                },
                                "config": config,
                            },
                            "code": code,
                            "method": {"name": method},
                            "candidate_levels": [0.01],
                            "source_checkpoint_sha256": "source",
                            "initialization": "fixture",
                            "issued_days": 1,
                            "scored_days": 1,
                            "active_mae_kwh": normalized * 10,
                            "active_rmse_kwh": normalized * 10,
                            "commit_chain": previous,
                            "audits": [{"paired_days": 0, "mean_new_minus_old": None}],
                            "decisions": [],
                            "elapsed_seconds": 1,
                            "initial_logs": [],
                            "candidate_steps": 0,
                            "audit_steps": 0,
                            "gpu_peak_allocated_bytes": 0,
                            "cost": {"update_seconds": 0},
                        }
                        write_json(folder / "run.json", report)
                        matrices[group]["runs"].append(report)
                        checks[group].append({"run_id": folder.name, "commit_chain": previous})
            write_json(reference / "matrix.json", matrices[0])
            matrices[1]["reference_matrix_sha256"] = digest(reference / "matrix.json")
            write_json(comparators / "matrix.json", matrices[1])
            for group, folder in enumerate((reference, comparators)):
                write_json(
                    folder / "verified.json",
                    {
                        "status": "verified",
                        "matrix_sha256": digest(folder / "matrix.json"),
                        "runs": checks[group],
                    },
                )
            write_json(
                root / "profile.json",
                {
                    "seeds": [42, 43, 44],
                    "contexts": ["weekday", "weekend"],
                    "bootstrap": {"segment_days": 7, "resamples": 10, "alpha": 0.05, "seed": 5},
                },
            )
            args = Namespace(
                selection=root / "cohort.json",
                profile=root / "profile.json",
                reference=reference / "matrix.json",
                matrix=comparators / "matrix.json",
                reference_verification=reference / "verified.json",
                verification=comparators / "verified.json",
                inputs_root=root / "inputs",
                output=root / "summary",
            )
            import contextlib
            import io

            with contextlib.redirect_stdout(io.StringIO()):
                analyze(args)
            output = json.loads((args.output / "summary.json").read_text())
            self.assertEqual(
                output["station_first"]["7/initial_adaptation/adaptive"]["macro_mae_kwh"], 10
            )
            self.assertEqual(
                output["station_first"]["28/initial_adaptation/online_best"]["macro_mae_kwh"], 50
            )
            self.assertEqual(
                output["adaptive_minus_comparator_intervals"]["14/initial_adaptation/target_only"][
                    "gap_kwh"
                ],
                -10,
            )
            self.assertEqual(len((args.output / "runs.csv").read_text().splitlines()), 46)
            self.assertTrue(
                all(a["new_minus_old_mae_kwh"] is None for a in output["isolated_audits"])
            )


if __name__ == "__main__":
    unittest.main()
