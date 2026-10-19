"""Independent fixtures distinguish duration-only exclusions from joint missingness."""

import csv
import io
import unittest
from datetime import datetime

from tools.audit_urbanev_rules import classify, compare_station
from tools.urbanev_hourly import RAW_FIELDS, HourlyConfig


class RuleComparisonTests(unittest.TestCase):
    def run_rows(self, volume: str = "0.5", duration: str = "0.0833333333", mutate=None) -> dict:
        config = HourlyConfig(datetime(2022, 9, 1), datetime(2022, 9, 1, 1), "UTC", "start")
        rows = [
            [f"2022-09-01 00:{m:02}:00", "1", "0", "0", "0", "0", "0", "1", "0", duration, volume]
            for m in range(0, 60, 5)
        ]
        if mutate:
            mutate(rows)
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(RAW_FIELDS)
        writer.writerows(rows)
        stream.seek(0)
        return compare_station(stream, config, config.slots(), "fixture")

    def test_duration_only_missing_loses_one_hour_under_b(self) -> None:
        def mutate(rows):
            rows[2][9] = ""

        result = self.run_rows(mutate=mutate)
        self.assertEqual(result["hourly"]["rule_a_retained"], 1)
        self.assertEqual(result["hourly"]["rule_b_retained"], 0)
        self.assertEqual(result["hourly"]["rejected_only_by_duration"], 1)
        self.assertEqual(result["sample_pairs"]["volume_valid_duration_invalid"], 1)

    def test_joint_missing_is_not_a_duration_only_loss(self) -> None:
        def mutate(rows):
            rows[2][9] = rows[2][10] = ""

        result = self.run_rows(mutate=mutate)
        self.assertEqual(result["hourly"]["rule_a_retained"], 0)
        self.assertEqual(result["hourly"]["rule_b_retained"], 0)
        self.assertEqual(result["hourly"]["rejected_only_by_duration"], 0)

    def test_zero_disagreement_remains_visible_and_retained_by_both(self) -> None:
        for volume, duration, category in [
            ("0", "0.0833333333", "zero_volume_positive_duration"),
            ("0.5", "0", "positive_volume_zero_duration"),
        ]:
            with self.subTest(category=category):
                result = self.run_rows(volume, duration)
                self.assertEqual(result["sample_pairs"][category], 12)
                self.assertEqual(result["hourly"]["rule_a_retained"], 1)
                self.assertEqual(result["hourly"]["rule_b_retained"], 1)
                self.assertEqual(result["hourly"]["rule_b_retained_with_zero_disagreement"], 1)

    def test_invalid_volume_rejected_by_both(self) -> None:
        for token in ["", "nan", "inf", "-1", "bad"]:
            with self.subTest(token=token):
                result = self.run_rows(volume=token)
                self.assertEqual(result["hourly"]["rule_a_retained"], 0)
                self.assertEqual(result["hourly"]["rule_b_retained"], 0)

    def test_duplicates_apply_same_clock_rule_to_both(self) -> None:
        def mutate(rows):
            rows.append(rows[0].copy())

        result = self.run_rows(mutate=mutate)
        self.assertEqual(result["hourly"]["rule_a_retained"], 0)
        self.assertEqual(result["hourly"]["rule_b_retained"], 0)
        self.assertEqual(result["structurally_invalid_hours"], 1)

    def test_token_categories_distinguish_missing_and_zero(self) -> None:
        self.assertEqual(classify(""), (None, "blank"))
        self.assertEqual(classify("0"), (0.0, "valid"))
        self.assertEqual(classify("NaN"), (None, "nonfinite"))
