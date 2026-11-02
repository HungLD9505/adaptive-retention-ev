"""Calendar-aware switching, missing labels, fixed policies and seed accounting."""

import copy
import unittest
from datetime import datetime, timedelta

from ev_evaluation.metrics import DailyError
from ev_evaluation.switching import analyze_switch_cells, switch_trajectory


class SwitchingTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2023, 7, 1)
        self.origins = tuple((self.start + timedelta(days=d)).isoformat() for d in range(90))
        self.errors = [
            DailyError(self.start + timedelta(days=d), 2, 4)
            for d in range(90)
            if d not in {*range(14, 28), 43}
        ]
        self.report = {
            "scheduled_days": 90,
            "ticks": 92,
            "issued_days": 90,
            "scored_days": len(self.errors),
            "candidate_levels": [0, 0.1, 1],
            "binding": {"config": {"controller": {"block_days": 14, "initial_lambda": 0.1}}},
            "decisions": [],
        }
        current = 0.1
        for index, selected in enumerate((1, 1, 0, 0, 0.1, 0.1)):
            begin = self.start + timedelta(days=index * 14)
            at = begin + timedelta(days=14)
            used = [e.origin.isoformat() for e in self.errors if begin <= e.origin < at]
            self.report["decisions"].append(
                {
                    "block_start": begin.isoformat(),
                    "effective_from": at.isoformat(),
                    "active_lambda": current,
                    "selected_lambda": selected,
                    "valid_days": len(used),
                    "pending_days": 0,
                    "incomplete_days": 14 - len(used),
                    "absent_days": 0,
                    "used_origins": used,
                    "valid_day_gaps": int(index == 3),
                    "reason": "insufficient_valid_days"
                    if not used
                    else "switch"
                    if selected != current
                    else "no_qualifying_challenger",
                }
            )
            current = selected

    def analyze(self, report=None, errors=None):
        return switch_trajectory(
            self.report if report is None else report,
            self.errors if errors is None else errors,
            self.origins,
            start=self.start,
        )

    def test_actual_switches_missing_post_labels_and_final_partial_block(self):
        result = self.analyze()
        self.assertEqual(result["switches"], 3)
        self.assertEqual(result["decision_opportunities"], 6)
        self.assertEqual(result["switches_per_opportunity"], 0.5)
        self.assertEqual(result["insufficient_evidence_boundaries"], 1)
        first = result["decisions"][0]
        self.assertEqual(
            (first["post_scheduled_days"], first["post_issued_days"], first["post_scored_days"]),
            (14, 14, 0),
        )
        self.assertIsNone(first["post_mae_kwh"])
        self.assertEqual(result["decisions"][2]["post_scored_days"], 13)
        self.assertEqual(result["decisions"][-1]["post_scheduled_days"], 6)
        self.assertEqual(result["decisions"][-1]["post_mae_kwh"], 2)

    def test_drain_only_switch_is_retained_but_not_counted_as_deployed(self):
        report = copy.deepcopy(self.report)
        report["binding"]["config"]["controller"]["block_days"] = 7
        report["decisions"] = []
        for index in range(13):
            begin = self.start + timedelta(days=index * 7)
            at = begin + timedelta(days=7)
            used = [e.origin.isoformat() for e in self.errors if begin <= e.origin < at]
            absent = int(index == 12)
            report["decisions"].append(
                {
                    "block_start": begin.isoformat(),
                    "effective_from": at.isoformat(),
                    "active_lambda": 0.1,
                    "selected_lambda": 1 if index == 12 else 0.1,
                    "valid_days": len(used),
                    "pending_days": 0,
                    "incomplete_days": 7 - len(used) - absent,
                    "absent_days": absent,
                    "used_origins": used,
                    "valid_day_gaps": 0,
                    "reason": "fixture",
                }
            )
        result = self.analyze(report)
        self.assertEqual(result["drain_only_boundaries"], 1)
        self.assertEqual(result["drain_only_switches"], 1)
        self.assertEqual(result["decision_opportunities"], 12)
        self.assertEqual(result["switches"], 0)
        self.assertEqual(result["decisions"][-1]["post_scheduled_days"], 0)
        self.assertIsNone(result["decisions"][-1]["post_mae_kwh"])

    def test_fixed_policy_rate_undefined_and_unscored_sites_retained(self):
        report = copy.deepcopy(self.report)
        report.update(candidate_levels=[0.1], scored_days=0)
        for d in report["decisions"]:
            d.update(
                active_lambda=0.1,
                selected_lambda=0.1,
                valid_days=0,
                incomplete_days=14,
                used_origins=[],
                reason="fixed_policy",
            )
        result = self.analyze(report, [])
        self.assertIsNone(result["switches_per_opportunity"])
        self.assertEqual(result["decision_opportunities"], 0)
        cells = {
            (7, "unscored", s, "frozen_source"): {
                "report": report,
                "errors": [],
                "issued": self.origins,
            }
            for s in (42, 43, 44)
        }
        aggregate = analyze_switch_cells(cells, [42, 43, 44], start=self.start)
        self.assertEqual(aggregate["7/frozen_source"]["station_count"], 1)
        self.assertIsNone(aggregate["7/frozen_source"]["mean_station_switches_per_opportunity"])
        cells.pop((7, "unscored", 44, "frozen_source"))
        with self.assertRaises(ValueError):
            analyze_switch_cells(cells, [42, 43, 44], start=self.start)

    def test_changed_continuity_population_or_calendar_fails(self):
        for field, value in (
            ("active_lambda", 0),
            ("selected_lambda", 99),
            ("valid_days", 1),
            ("effective_from", self.start.isoformat()),
        ):
            bad = copy.deepcopy(self.report)
            bad["decisions"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.analyze(bad)
        bad = copy.deepcopy(self.report)
        bad["decisions"].pop()
        with self.assertRaises(ValueError):
            self.analyze(bad)


if __name__ == "__main__":
    unittest.main()
