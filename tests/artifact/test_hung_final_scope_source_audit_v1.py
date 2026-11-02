"""Regression checks for frozen-input Source readiness accounting."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from tools import hung_final_scope_source_audit_v1 as audit_module


class FinalScopeSourceAuditTests(unittest.TestCase):
    def test_real_pinned_inventory(self) -> None:
        result = audit_module.audit()
        self.assertEqual(result["source_checkpoints_verified"], 9)
        self.assertEqual(result["minimal_input_ready_by_budget"], {"7": 326, "14": 326, "28": 330})
        self.assertEqual(result["minimal_input_ready_all_budgets"], 326)
        self.assertEqual(result["omitted_ids"], 370)
        self.assertEqual(result["locked_jobset_source_bindings_verified"], 360)

    def test_changed_source_fingerprint_rejected(self) -> None:
        original_rows = audit_module._rows

        def changed_rows(path, expected_sha):
            rows = original_rows(path, expected_sha)
            if path == audit_module.SOURCE_CSV:
                rows[0]["source_checkpoint_sha256"] = "0" * 64
            return rows

        with patch.object(audit_module, "_rows", side_effect=changed_rows):
            with self.assertRaisesRegex(ValueError, "Source bytes/SHA changed"):
                audit_module.audit()

    def test_changed_jobset_rejected(self) -> None:
        original_sha = audit_module._sha

        def changed_sha(path):
            return "0" * 64 if path == audit_module.JOBSET else original_sha(path)

        with patch.object(audit_module, "_sha", side_effect=changed_sha):
            with self.assertRaisesRegex(ValueError, "jobset fingerprint changed"):
                audit_module.audit()


if __name__ == "__main__":
    unittest.main()
