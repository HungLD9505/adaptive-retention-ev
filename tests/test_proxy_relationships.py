"""Proxy relationships preserve pairing, availability and undefined correlations."""

import copy
import unittest
from datetime import datetime, timedelta

from ev_evaluation.metrics import DailyError
from ev_evaluation.proxy_relationships import (
    analyze_proxy_cells,
    correlation,
    proxy_blocks,
    summarize_relationships,
)


class ProxyRelationshipTests(unittest.TestCase):
    def fixture(self, name: str) -> tuple[dict, dict, dict]:
        start = datetime(2026, 1, 1)
        origins = [(start + timedelta(days=d)).isoformat() for d in range(3)]
        end = (start + timedelta(days=3)).isoformat()
        trace = {
            "forecasts": {o: {"signal": d + 1} for d, o in enumerate(origins)},
            "scores": [
                {
                    "origin": o,
                    "as_of": (start + timedelta(days=d + 1)).isoformat(),
                    "mae_scaled": [3 + d, 2, 4],
                }
                for d, o in enumerate(origins)
            ],
        }
        frozen = {o: 2 * (d + 1) for d, o in enumerate(origins)}
        signals = [
            {
                "origin": o,
                "value": d + 1,
                "available_at": trace["scores"][d]["as_of"] if name == "source_error" else o,
            }
            for d, o in enumerate(origins)
        ]
        report = {
            "method": {"name": name},
            "candidate_levels": [0, 0.1, 1],
            "policy_state": {"signals": signals},
            "decisions": [
                {
                    "block_start": start.isoformat(),
                    "effective_from": end,
                    "used_origins": origins,
                    "valid_days": 3,
                    "reason": "fixture",
                    "config": {
                        "min_valid_days": 2,
                        "method_statistics": {
                            "mean_available_signal": 2,
                            "signal_days": 3,
                        },
                    },
                }
            ],
        }
        return report, trace, frozen

    def test_available_signals_and_candidate_differences_use_identical_days(self):
        for name in ("source_error", "uncertainty", "drift"):
            report, trace, frozen = self.fixture(name)
            result = proxy_blocks(report, trace, frozen, 2)[0]
            self.assertEqual(result["paired_days"], 3)
            self.assertEqual(result["policy_signal_mean"], 2)
            self.assertEqual(result["zero_minus_low_mae_kwh"], 4)
            self.assertEqual(result["zero_minus_high_mae_kwh"], 0)

    def test_future_scores_wrong_signal_and_wrong_frozen_source_fail(self):
        for mode in ("future", "signal", "source", "population", "missing_mean"):
            report, trace, frozen = self.fixture("source_error")
            origin = trace["scores"][0]["origin"]
            if mode == "future":
                trace["scores"][0]["as_of"] = "2026-02-01T00:00:00"
                report["policy_state"]["signals"][0]["available_at"] = "2026-02-01T00:00:00"
            elif mode == "signal":
                report["policy_state"]["signals"][0]["value"] += 1
            elif mode == "source":
                frozen[origin] += 1
            elif mode == "missing_mean":
                report["decisions"][0]["config"]["method_statistics"] = {}
            else:
                report["decisions"][0]["used_origins"].append(origin)
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                proxy_blocks(report, trace, frozen, 2)

    def test_empty_unscored_blocks_and_constant_correlations_stay_undefined(self):
        report, _, _ = self.fixture("drift")
        report["policy_state"]["signals"] = []
        d = report["decisions"][0]
        d.update(used_origins=[], valid_days=0)
        d["config"]["method_statistics"] = {}
        row = proxy_blocks(report, {"forecasts": {}, "scores": []}, {}, None)[0]
        self.assertIsNone(row["policy_signal_mean"])
        self.assertIsNone(row["zero_minus_low_mae_kwh"])
        self.assertIsNone(correlation([(1, 2), (1, 3)]))
        self.assertIsNone(correlation([(1, 2)]))

    def test_all_three_seeds_required_before_equal_station_averaging(self):
        units = []
        for entity in ("defined", "undefined"):
            for seed in (42, 43, 44):
                units.append(
                    {
                        "budget": 7,
                        "method": "drift",
                        "entity_id": entity,
                        "seed": seed,
                        "blocks": [
                            {
                                "policy_signal_mean": d,
                                "zero_minus_low_mae_kwh": d,
                                "zero_minus_high_mae_kwh": -d,
                            }
                            for d in range(3)
                        ]
                        if entity == "defined"
                        else [],
                    }
                )
        result = summarize_relationships(units, [42, 43, 44])["7/drift"]
        self.assertEqual(result["zero_minus_low_mae_kwh"]["mean_station_r"], 1)
        self.assertEqual(result["zero_minus_low_mae_kwh"]["undefined_stations"], 1)
        self.assertEqual(result["zero_minus_high_mae_kwh"]["mean_station_r"], -1)
        incomplete = copy.deepcopy(units[:-1])
        with self.assertRaises(ValueError):
            summarize_relationships(incomplete, [42, 43, 44])

    def test_collection_join_uses_same_station_seed_frozen_errors(self):
        cells = {}
        for seed in (42, 43, 44):
            report, trace, frozen = self.fixture("source_error")
            cells[7, "a", seed, "source_error"] = {
                "report": report,
                "coverage": {"proxy_trace": trace, "scale": 2},
            }
            cells[7, "a", seed, "frozen_source"] = {
                "errors": [
                    DailyError(datetime.fromisoformat(o), x, x * x) for o, x in frozen.items()
                ]
            }
        result = analyze_proxy_cells(cells, [42, 43, 44])
        self.assertEqual(len(result["units"]), 3)
        self.assertEqual(result["units"][0]["blocks"][0]["zero_minus_low_mae_kwh"], 4)
        self.assertIsNone(
            result["station_first"]["7/source_error"]["stations"]["a"]["zero_minus_low_mae_kwh"]
        )
        cells[7, "a", 43, "frozen_source"]["errors"][0] = DailyError(
            datetime(2026, 1, 1), 100, 10000
        )
        with self.assertRaises(ValueError):
            analyze_proxy_cells(cells, [42, 43, 44])
