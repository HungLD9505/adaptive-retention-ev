"""Regression checks for pinned Development controller-decision sensitivity."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from tools import hung_q_controller_decision_sensitivity_v1 as sensitivity


class ControllerDecisionSensitivityTests(unittest.TestCase):
    def test_pinned_evidence_change_is_rejected(self) -> None:
        original = sensitivity._sha

        def changed(path):
            if path == sensitivity.PAIRS:
                return "0" * 64
            return original(path)

        with patch.object(sensitivity, "_sha", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "Pinned Development"):
                sensitivity.audit()


if __name__ == "__main__":
    unittest.main()
