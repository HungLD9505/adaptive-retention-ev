"""Independent hourly fixtures: missing targets never become zero energy."""

import csv
import io
import unittest
from datetime import datetime, timedelta

from tools.urbanev_hourly import HOURLY_FIELDS, RAW_FIELDS, HourlyConfig, aggregate_station


class HourlyTests(unittest.TestCase):
    def config(self, label: str = "start", hours: int = 1) -> HourlyConfig:
        return HourlyConfig(
            datetime(2022, 9, 1), datetime(2022, 9, 1) + timedelta(hours=hours), "UTC", label
        )

    def rows(self, config: HourlyConfig) -> list[list[str]]:
        start = config.start + timedelta(minutes=5 if config.interval_label == "end" else 0)
        return [
            [
                (start + timedelta(minutes=5 * i)).isoformat(sep=" "),
                "1",
                "0",
                "0.5",
                "1",
                "0",
                "0",
                "1",
                "0",
                "0.08333333333333333",
                str(i),
            ]
            for i in range(config.hours * 12)
        ]

    def aggregate(self, rows: list[list[str]], config: HourlyConfig | None = None) -> tuple:
        config = config or self.config()
        source, target = io.StringIO(), io.StringIO()
        writer = csv.writer(source)
        writer.writerow(RAW_FIELDS)
        writer.writerows(rows)
        source.seek(0)
        out = csv.writer(target)
        out.writerow(HOURLY_FIELDS)
        qc = aggregate_station(source, out, "1001", config, config.slots(), (1, 0), 1200.0)
        target.seek(0)
        return list(csv.DictReader(target)), qc

    def test_sum_has_no_extra_power_or_time_multiplier(self) -> None:
        rows, qc = self.aggregate(self.rows(self.config()))
        self.assertEqual(float(rows[0]["energy_kwh"]), 66.0)  # 0+1+...+11
        self.assertEqual(rows[0]["timestamp"], "2022-09-01T00:00:00+00:00")
        self.assertEqual(rows[0]["file_valid_mask"], "1")
        self.assertEqual(qc["diagnostics"]["valid_hours"], 1)

    def test_each_hour_uses_its_own_twelve_samples(self) -> None:
        config = self.config(hours=2)
        rows, _ = self.aggregate(self.rows(config), config)
        self.assertEqual([float(r["energy_kwh"]) for r in rows], [66.0, 210.0])

    def test_zero_energy_is_valid_even_when_busy(self) -> None:
        source = self.rows(self.config())
        for row in source:
            row[-1] = row[-2] = "0"
        rows, _ = self.aggregate(source)
        self.assertEqual(rows[0]["energy_kwh"], "0")
        self.assertEqual(rows[0]["file_valid_mask"], "1")

    def test_missing_grid_and_entire_hour_are_not_filled(self) -> None:
        config = self.config(hours=2)
        source = self.rows(config)[:11]
        rows, qc = self.aggregate(source, config)
        self.assertEqual([r["energy_kwh"] for r in rows], ["", ""])
        self.assertEqual([r["valid_sample_count"] for r in rows], ["11", "0"])
        self.assertEqual(qc["diagnostics"]["missing_grid_samples"], 13)

    def test_blank_negative_nonfinite_and_malformed_targets_invalidate_hour(self) -> None:
        for column in [-1, -2]:
            for value in ["", "-1", "nan", "inf", "bad"]:
                with self.subTest(column=column, value=value):
                    source = self.rows(self.config())
                    source[4][column] = value
                    rows, _ = self.aggregate(source)
                    self.assertEqual(rows[0]["file_valid_mask"], "0")
                    self.assertEqual(rows[0]["energy_kwh"], "")

    def test_duplicate_is_not_summed_or_silently_selected(self) -> None:
        source = self.rows(self.config())
        source.append(source[3].copy())
        rows, qc = self.aggregate(source)
        self.assertEqual(rows[0]["energy_kwh"], "")
        self.assertIn("duplicate_timestamp", rows[0]["qc_flags"])
        self.assertFalse(qc["structural_qc_pass"])

    def test_offgrid_is_flagged_not_rounded(self) -> None:
        source = self.rows(self.config())
        source[2][0] = "2022-09-01 00:11:00"
        rows, qc = self.aggregate(source)
        self.assertIn("off_grid_timestamp", rows[0]["qc_flags"])
        self.assertFalse(qc["structural_qc_pass"])

    def test_ordering_violation_is_visible(self) -> None:
        source = self.rows(self.config())
        source[1], source[2] = source[2], source[1]
        _, qc = self.aggregate(source)
        self.assertFalse(qc["structural_qc_pass"])
        self.assertEqual(qc["diagnostics"]["out_of_order_rows"], 1)

    def test_end_labeled_intervals_shift_to_the_correct_hour(self) -> None:
        config = self.config("end")
        source = self.rows(config)
        # 00:00 is the end of a bin outside this requested window.
        source.insert(0, ["2022-09-01 00:00:00"] + source[0][1:])
        rows, qc = self.aggregate(source, config)
        self.assertEqual(float(rows[0]["energy_kwh"]), 66.0)
        self.assertEqual(qc["diagnostics"]["rows_outside_window"], 1)
        self.assertEqual(rows[0]["timestamp"], "2022-09-01T00:00:00+00:00")

    def test_midnight_boundary_preserves_date(self) -> None:
        config = HourlyConfig(datetime(2022, 9, 1, 23), datetime(2022, 9, 2, 1), "UTC", "start")
        rows, _ = self.aggregate(self.rows(config), config)
        self.assertEqual(rows[1]["timestamp"], "2022-09-02T00:00:00+00:00")

    def test_ancillary_anomalies_are_not_hidden_target_filters(self) -> None:
        source = self.rows(self.config())
        source[0][1] = "999"
        source[0][3] = "-2"
        rows, qc = self.aggregate(source)
        self.assertEqual(rows[0]["file_valid_mask"], "1")
        self.assertEqual(qc["diagnostics"]["occupancy_count_inconsistency"], 1)
        self.assertEqual(qc["diagnostics"]["negative_s_price"], 1)

    def test_bad_header_row_shape_and_timestamp_fail(self) -> None:
        for row in [["nonsense"] * 11, self.rows(self.config())[0][:-1]]:
            with self.assertRaises(ValueError):
                self.aggregate([row])
        with self.assertRaises(ValueError):
            aggregate_station(
                io.StringIO("time,volume\n"),
                csv.writer(io.StringIO()),
                "1",
                self.config(),
                self.config().slots(),
                (1, 0),
                7.0,
            )

    def test_config_rejects_ambiguous_or_invalid_window(self) -> None:
        with self.assertRaises(ValueError):
            HourlyConfig(datetime(2022, 9, 1, 0, 5), datetime(2022, 9, 2), "UTC", "start")
        with self.assertRaises(ValueError):
            self.config("unknown")
