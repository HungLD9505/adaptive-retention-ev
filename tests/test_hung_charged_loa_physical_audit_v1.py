"""Guard the single-ID CHARGED physical-lineage comparison."""

from __future__ import annotations

import unittest
from copy import deepcopy

from tools.hung_charged_loa_physical_audit_v1 import (
    ARCHIVE_SHA,
    PROOF_ZIP_SHA,
    RUN_ID,
    compare_records,
)


class ChargedLoaPhysicalAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        source = {
            "manifest_sha256": "cb09d9d5c751b3bc1fcbad79ef548800c33e1506e6863f2600f88b167ac5e384",
            "files": {
                name: {"bytes": 1, "sha256": name}
                for name in ("manifest.json", "entities.jsonl", "labels.jsonl")
            },
        }
        self.pr67 = {
            "matrix_sha256": "matrix67",
            "input_authentication": {"sources": [deepcopy(source)]},
            "runs": [
                {
                    "run_id": RUN_ID,
                    "mae_kwh": 1.1,
                    "rmse_kwh": 1.6,
                    "commit_chain": "chain67",
                    "issued": 90,
                    "scored": 90,
                }
            ],
        }
        self.pr52 = {
            "loa_first_target_publication": {
                "run_id": RUN_ID,
                "independent_proof_sha256": PROOF_ZIP_SHA,
                "publication_receipt_sha256": "receipt-hash",
                "active_mae_kwh": 1.2,
                "active_rmse_kwh": 1.5,
            }
        }
        self.proof = {
            "receipt_sha256": "receipt-hash",
            "verification_sha256": "verification-hash",
            "receipt": {
                "run_ids": [RUN_ID],
                "artifact": {"sha256": ARCHIVE_SHA, "bytes": 123},
                "target_code": "code52",
                "verification_sha256": "verification-hash",
            },
            "verification": {
                "wrapper_sha256": ARCHIVE_SHA,
                "status": "actual_Drive_roundtrip_complete_content_verified",
            },
            "daily": {
                "matrix_sha256": "matrix52",
                "input_authentication": {"sources": [deepcopy(source)]},
                "runs": [
                    {
                        "run_id": RUN_ID,
                        "mae_kwh": 1.2,
                        "rmse_kwh": 1.5,
                        "commit_chain": "chain52",
                        "issued": 90,
                        "scored": 90,
                    }
                ],
            },
        }
        self.archive = {
            "bytes": 123,
            "catalog": {"matrix_sha256": "matrix52"},
            "binding": {
                "input": {
                    "input_manifest_sha256": source["manifest_sha256"],
                    "source_checkpoint_sha256": "source52",
                }
            },
            "run": {
                "run_id": RUN_ID,
                "code": {"commit": "code52"},
                "active_mae_kwh": 1.2,
                "active_rmse_kwh": 1.5,
                "commit_chain": "chain52",
            },
        }

    def test_same_id_and_input_with_distinct_trajectory_is_not_equated(self) -> None:
        result = compare_records(self.pr67, self.pr52, self.proof, self.archive)
        self.assertEqual(
            result["classification"], "SAME_ID_AND_INPUT_DIFFERENT_RECORDED_TRAJECTORY"
        )
        self.assertFalse(result["pr67"]["physical_archive_bound"])
        self.assertTrue(result["pr52"]["physical_archive_bound"])
        self.assertAlmostEqual(result["mae_difference_pr52_minus_pr67_kwh"], 0.1)

    def test_mismatched_input_file_is_rejected(self) -> None:
        self.pr67["input_authentication"]["sources"][0]["files"]["labels.jsonl"]["sha256"] = (
            "different"
        )
        with self.assertRaisesRegex(ValueError, "Input file identity mismatch"):
            compare_records(self.pr67, self.pr52, self.proof, self.archive)


if __name__ == "__main__":
    unittest.main()
