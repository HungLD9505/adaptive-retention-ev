"""Independent operational fixtures; no training, cloud, data or quota consumption."""

import json
import tempfile
import unittest
from pathlib import Path

from tools.final_receipt_policy import (
    ReceiptPolicy,
    claim_undispatched,
    dispatch_budget,
    verified_receipt,
    wait_expired,
)


class ReceiptPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = ReceiptPolicy()
        self.quota = {
            "balance": 60,
            "aggregatePerHour": 2.14,
            "observedEpoch": 1000,
            "activeSessions": 2,
            "reserve": 30,
        }

    def test_measured207second_delay_fits_bounded600second_wait(self):
        self.assertFalse(wait_expired(100, 307.61, self.policy))
        self.assertFalse(wait_expired(100, 699.99, self.policy))
        self.assertTrue(wait_expired(100, 700, self.policy))
        self.assertEqual(self.policy.completed_inflight, 1)

    def test_invalid_or_unbounded_policy_rejected(self):
        for values in (
            {"receipt_seconds": 0},
            {"receipt_seconds": 901},
            {"completed_inflight": 2},
            {"reserve": 29},
            {"unit_seconds": 1199},
            {"release_seconds": 1},
            {"completed_inflight": True},
            {"receipt_seconds": 600.0},
            {"release_seconds": float("inf")},
        ):
            with self.subTest(values=values), self.assertRaises(ValueError):
                ReceiptPolicy(**values)

    def test_worst_case_budget_includes_wait_age_unit_and_release(self):
        result = dispatch_budget(self.quota, 1600, self.policy)
        self.assertAlmostEqual(result["estimated_balance_now"], 60 - 2.14 / 6)
        self.assertAlmostEqual(result["required_balance"], 30 + 2.14 * 2100 / 3600)
        self.assertEqual(result["actual_observed_epoch"], 1000)
        for change in (
            {"balance": 31},
            {"aggregatePerHour": 0},
            {"aggregatePerHour": float("nan")},
            {"balance": True},
            {"observedEpoch": 1601},
            {"observedEpoch": 699},
            {"activeSessions": 3},
            {"reserve": 29},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                dispatch_budget({**self.quota, **change}, 1600, self.policy)

    def test_actual_root_proofs_required_before_next_same_lane_unit(self):
        valid = {
            "schema": "ev-final-unit-acceptance-v1",
            "lock_sha256": "fixture-lock",
            "unit_index": 166,
            "lane": 0,
            "accepted_method_cells": 14,
            "native_readback_verified": True,
            "independent_content_verified": True,
        }
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "receipt.json"
            p.write_text(json.dumps(valid))
            self.assertEqual(len(verified_receipt(p, "fixture-lock", 166, 0)), 64)
            for key, value in (
                ("unit_index", 164),
                ("lane", 1),
                ("accepted_method_cells", 13),
                ("native_readback_verified", False),
                ("independent_content_verified", False),
                ("native_readback_verified", 1),
            ):
                p.write_text(json.dumps({**valid, key: value}))
                with self.subTest(key=key), self.assertRaises(ValueError):
                    verified_receipt(p, "fixture-lock", 166, 0)
            p.write_text(json.dumps(valid)[:-1] + ',"unit_index":166}')
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                verified_receipt(p, "fixture-lock", 166, 0)
            p.write_text("truncated{")
            with self.assertRaises(ValueError):
                verified_receipt(p, "fixture-lock", 166, 0)

    def test_duplicate_or_uncertain_restart_never_dispatches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            intent, output = root / "intent.json", root / "unit"
            claim_undispatched(intent, (output,), {"index": 168})
            self.assertEqual(json.loads(intent.read_text()), {"index": 168})
            with self.assertRaises(FileExistsError):
                claim_undispatched(intent, (output,), {"index": 168})
            output.mkdir()
            with self.assertRaises(FileExistsError):
                claim_undispatched(root / "other-intent", (output,), {"index": 168})
            self.assertFalse((root / "other-intent").exists())

    def test_clock_reversal_rejected(self):
        with self.assertRaises(ValueError):
            wait_expired(100, 99, self.policy)
