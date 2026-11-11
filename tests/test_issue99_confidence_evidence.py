"""Causal selection, gate isolation and random-initialization guards."""

import json
import unittest
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ev_control.confidence import ControllerConfig, DailyScore
from ev_runner.continuous_run import execute
from tools.issue99_confidence_evidence import available_rows, policy_replay, select

DAY = timedelta(days=1)
START = datetime(2022, 12, 1)
CONFIG = ControllerConfig(0.1, 1.0, 0.1, 7, 5, 0, 0.05, 3, 20, 42)


def fixture_rows():
    return [
        DailyScore(
            START + i * DAY,
            START + i * DAY,
            START + (i + 1) * DAY,
            24,
            (2.0, 1.0, 0.5),
            "fixture",
            ("a", "b", "c"),
        )
        for i in range(21)
    ]


class ConfidenceEvidenceTests(unittest.TestCase):
    def test_unavailable_and_future_rows_cannot_change_first_decision(self):
        rows = fixture_rows()
        first = policy_replay(rows, CONFIG, START, START + 21 * DAY, "test", "fixture", True)
        changed = rows[:7] + [
            DailyScore(
                r.origin,
                r.issued_at,
                r.available_at,
                24,
                (0, 100, 1000),
                r.scale_id,
                r.prediction_ids,
            )
            for r in rows[7:]
        ]
        second = policy_replay(changed, CONFIG, START, START + 21 * DAY, "test", "fixture", True)
        self.assertEqual(first["choices"][(START + 7 * DAY).isoformat()], 1.0)
        self.assertEqual(
            first["choices"][(START + 7 * DAY).isoformat()],
            second["choices"][(START + 7 * DAY).isoformat()],
        )
        missing = DailyScore(START, START, None, 0, None, "fixture", ("a", "b", "c"))
        self.assertEqual(available_rows([missing], START, START + 7 * DAY), [])

    def test_gate_checks_same_mean_challenger(self):
        bound = SimpleNamespace(
            comparisons=[
                SimpleNamespace(challenger=1.0, qualifies=False),
                SimpleNamespace(challenger=0.0, qualifies=True),
            ],
            as_dict=lambda: {"fixture": True},
        )
        with patch("tools.issue99_confidence_evidence.decide", return_value=bound):
            chosen, evidence = select(
                fixture_rows(), CONFIG, 0.1, START, START + 7 * DAY, "t", "fixture", True
            )
        self.assertEqual(evidence["recommended"], 1.0)
        self.assertEqual(chosen, 0.1)

    def test_report_errors_use_original_units(self):
        result = policy_replay(
            fixture_rows(), CONFIG, START, START + 7 * DAY, "t", "fixture", False, scale=10
        )
        self.assertEqual(result["mae"], 10)

    def test_fixed_start_uses_calibrated_level_before_first_decision(self):
        result = policy_replay(
            fixture_rows(),
            replace(CONFIG, initial_lambda=1.0),
            START,
            START + 7 * DAY,
            "t",
            "fixture",
            True,
            scale=10,
        )
        self.assertTrue(all(level == 1.0 for level in result["choices"].values()))
        self.assertEqual(result["mae"], 5.0)

    def test_random_initialization_rejects_retention(self):
        config = json.loads(
            Path("docs/reports/issue99-study-20261110/controller-lock.json").read_text()
        )["study_template"]
        config.update(phase="pilot", protocol_sha256=None, objective_origins=[], frozen_lambda=True)
        with self.assertRaisesRegex(ValueError, "Random target"):
            execute(
                None,
                "1405",
                Path("unused"),
                "unused",
                config,
                Path("unused"),
                device="cpu",
                source_initialization=False,
            )


if __name__ == "__main__":
    unittest.main()
