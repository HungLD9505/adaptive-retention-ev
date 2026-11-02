"""The resume boundary and audit branch must not hide core interior changes."""

import unittest

from tools.hung_block7_shared_event_order_v1 import classify_pair


class SharedEventOrderTests(unittest.TestCase):
    def test_classifies_boundary_and_audit_only_differences(self):
        historical = {
            "2023-01-01": ["forecast", "score", "update"],
            "2023-01-02": ["forecast", "score", "update"],
        }
        main = {
            "2023-01-01": ["score", "update"],
            "2023-01-02": ["forecast", "score", "update", "audit-update"],
        }
        result = classify_pair(historical, main)
        self.assertEqual(result["core_boundary_differences"], 1)
        self.assertEqual(result["audit_only_differences"], 1)
        self.assertEqual(result["core_nonboundary_differences"], 0)

    def test_detects_interior_core_order_change(self):
        historical = {"2023-01-01": ["forecast"], "2023-01-02": ["score", "update"]}
        main = {"2023-01-01": ["forecast"], "2023-01-02": ["update", "score"]}
        result = classify_pair(historical, main)
        self.assertEqual(result["core_nonboundary_differences"], 1)
