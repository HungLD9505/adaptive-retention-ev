"""Declarative block-size verification boundaries keep the 14-day default."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from experiments.hung_sprint2.run_development import verification_split_limit


class BlockAblationTests(unittest.TestCase):
    def test_variant_configs_change_only_block_days_and_proposal_status(self) -> None:
        root = Path(__file__).resolve().parents[1] / "experiments" / "hung_sprint2"
        base = json.loads((root / "development_config_v1.json").read_text(encoding="utf-8"))
        for block_days in (7, 28):
            with self.subTest(block_days=block_days):
                variant = json.loads(
                    (root / f"development_block{block_days}_proposal_v1.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(variant["replay"].pop("block_days"), block_days)
                self.assertIn("proposal", variant.pop("status"))
                base_without_variant = json.loads(json.dumps(base))
                base_without_variant["replay"].pop("block_days")
                base_without_variant.pop("status")
                self.assertEqual(variant, base_without_variant)

    def test_split_scales_with_declared_block_size(self) -> None:
        self.assertEqual(verification_split_limit(7, 90), 21)
        self.assertEqual(verification_split_limit(14, 90), 42)
        self.assertEqual(verification_split_limit(28, 90), 84)
        self.assertEqual(verification_split_limit(28, 60), 59)
        self.assertEqual(verification_split_limit(28, 57), 56)

    def test_rejects_insufficient_or_invalid_horizon(self) -> None:
        for block_days, horizon in ((7, 14), (14, 28), (28, 56), (28, 0), (0, 90)):
            with self.subTest(block_days=block_days, horizon=horizon):
                with self.assertRaisesRegex(ValueError, "two block boundaries"):
                    verification_split_limit(block_days, horizon)
