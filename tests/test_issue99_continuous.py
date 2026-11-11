"""Causal A/V eligibility and resume-state fixtures for continuous retention."""

import unittest
from datetime import datetime, timedelta, timezone

from ev_control.continuous import ArrivedWindow, WindowRule


class WindowTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2022, 12, 1, tzinfo=timezone.utc)
        self.rule = WindowRule(
            older_count=2, newer_count=1, upper_bound=2.0, meta_step_size=0.01, epsilon=0.001
        )

    def add(self, window, day, *, arrived=True):
        origin = self.start + timedelta(days=day)
        available = origin + timedelta(days=1)
        window.add(
            origin=origin,
            available_at=available,
            as_of=available if arrived else origin,
            record={"y_scaled": [0.1] * 24},
        )

    def test_arrival_order_untrained_validation_and_restore(self):
        window = ArrivedWindow()
        self.add(window, 0)
        self.add(window, 1)
        self.assertIsNone(window.select(self.start + timedelta(days=2), self.rule))
        window.mark_trained(self.start)
        window.mark_trained(self.start + timedelta(days=1))
        self.add(window, 2)
        selected = window.select(self.start + timedelta(days=3), self.rule)
        self.assertEqual(
            [r["origin"] for r in selected[0]],
            [(self.start + timedelta(days=i)).isoformat() for i in (0, 1)],
        )
        self.assertEqual(selected[1][0]["origin"], (self.start + timedelta(days=2)).isoformat())
        resumed = ArrivedWindow.restore(window.snapshot())
        self.assertEqual(resumed.snapshot(), window.snapshot())
        resumed.mark_trained(self.start + timedelta(days=2))
        self.assertIsNone(resumed.select(self.start + timedelta(days=3), self.rule))

    def test_future_label_is_rejected(self):
        with self.assertRaises(ValueError):
            self.add(ArrivedWindow(), 0, arrived=False)


if __name__ == "__main__":
    unittest.main()
