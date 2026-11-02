"""Reject broken prefix provenance and preserve real numeric differences."""

import unittest

import torch

from tools.hung_block7_full_event_order_v1 import compare_days
from tools.hung_block7_prefix_import_v1 import digest, validate_prior
from tools.hung_block7_prefix_numeric_audit_v1 import compare_issued


class PrefixAuditTests(unittest.TestCase):
    def test_rejects_wrong_resume_checkpoint(self):
        checkpoint = b"checkpoint"
        journal = b'{"kind": "header"}\n'
        saved = {
            "resumed_from": {"run_id": "replay-21", "checkpoint_sha256": "0" * 64},
            "input_binding": {"entity_id": "1025"},
        }
        prior = {
            "run_id": "replay-21",
            "status": "completed",
            "runner_cursor": 21,
            "input_binding": saved["input_binding"],
            "final_runner_checkpoint_sha256": digest(checkpoint),
        }
        with self.assertRaisesRegex(ValueError, "checkpoint/manifest mismatch"):
            validate_prior("block7_example", saved, prior, journal, checkpoint)

    def test_numeric_audit_does_not_erase_forecast_difference(self):
        historical = [
            {
                "day_id": "2023-01-01",
                "index": 0,
                "active_level": 0.0,
                "y_scaled": torch.tensor([1.0]),
                "forecasts": [torch.tensor([2.0])],
            }
        ]
        main = [{**historical[0], "forecasts": [torch.tensor([2.5])]}]
        result, by_index = compare_issued(historical, main)
        self.assertEqual(result["forecast_different_origins"], 1)
        self.assertEqual(result.get("label_value_differences_when_both_present", 0), 0)
        self.assertEqual(by_index[0]["forecast_different"], 1)

    def test_full_event_audit_keeps_separate_audit_branch(self):
        historical = {"day": ["forecast", "score", "update"]}
        main = {"day": ["forecast", "score", "update", "audit-update"]}
        result = compare_days(historical, main)
        self.assertEqual(result["audit_only_differences"], 1)
        self.assertEqual(result["core_tag_differences"], 0)
