"""Regression checks for station-clustered Development switch accounting."""

from __future__ import annotations

import csv
import unittest

from tools.hung_block7_switch_sensitivity_v1 import SOURCE, summarize


def _rows() -> list[dict[str, str]]:
    with SOURCE.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


class SwitchSensitivityTests(unittest.TestCase):
    def test_real_source_preserves_switch_and_station_denominators(self) -> None:
        result = summarize(_rows())
        main = result["main"]
        self.assertEqual(main["evaluable_switches"], 28)
        self.assertEqual(main["audit_better_switches"], 19)
        self.assertEqual(main["station_count"], 6)
        self.assertEqual(main["by_station"]["1405"]["audit_better_switches"], 10)
        self.assertEqual(main["leave_one_station_out"]["1405"]["evaluable_switches"], 16)
        self.assertEqual(result["historical"]["evaluable_switches"], 55)

    def test_duplicate_decision_rejected(self) -> None:
        rows = _rows()
        rows[1] = dict(rows[0])
        with self.assertRaisesRegex(ValueError, "Duplicate switch"):
            summarize(rows)

    def test_changed_score_rejected(self) -> None:
        rows = _rows()
        rows[0]["live_minus_audit_mae_kwh"] = "123"
        with self.assertRaisesRegex(ValueError, "Inconsistent paired switch score"):
            summarize(rows)

    def test_role_and_run_id_must_agree(self) -> None:
        rows = _rows()
        rows[0]["role"] = "main"
        with self.assertRaisesRegex(ValueError, "Run ID and role disagree"):
            summarize(rows)


if __name__ == "__main__":
    unittest.main()
