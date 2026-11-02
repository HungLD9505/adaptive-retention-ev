"""Focused offline checks for saved Development context and proxy audit helpers."""

import unittest

import torch

from tools.hung_development_context_proxy import (
    selected_forecast,
    stage_hashes,
    target_context,
)


class ContextProxyTests(unittest.TestCase):
    def test_target_context_uses_local_target_hour(self) -> None:
        self.assertEqual(target_context("2022-12-02T00:00:00+08:00", 23), ("weekday", 23))
        self.assertEqual(target_context("2022-12-03T00:00:00+08:00", 0), ("weekend", 0))

    def test_selected_forecast_uses_issued_active_level(self) -> None:
        item = {
            "active_level": 0.1,
            "forecasts": [torch.zeros(1, 24), torch.ones(1, 24)],
        }
        self.assertTrue(torch.equal(selected_forecast(item, [0.0, 0.1]), torch.ones(24)))
        with self.assertRaises(ValueError):
            selected_forecast(item, [0.0, 0.2])

    def test_stage_hashes(self) -> None:
        self.assertEqual(
            stage_hashes("replay-42:abc;replay-90:def"), {"replay-42": "abc", "replay-90": "def"}
        )


if __name__ == "__main__":
    unittest.main()
