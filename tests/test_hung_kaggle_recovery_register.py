"""Fail-closed checks for the exact Kaggle archive recovery checklist."""

import hashlib
import json
import unittest
from unittest import mock

from tools.hung_kaggle_recovery_register import build_rows


def fixture() -> tuple[dict, dict, dict]:
    shards = []
    routes = {}
    expected = {}
    for index in range(28):
        sid = f"shard_{index + 1:04d}"
        ids = [f"job_{index:02d}_{job:02d}" for job in range(20)]
        shards.append({"id": sid, "job_ids": ids})
        routes[sid] = "kaggle"
        expected[sid] = hashlib.sha256(
            json.dumps(ids, separators=(",", ":")).encode("utf8")
        ).hexdigest()
    return {"shards": shards}, {"routes": routes}, expected


class RecoveryRegisterTests(unittest.TestCase):
    def test_exact_disjoint_jobsets_leave_archive_fields_empty(self) -> None:
        shards, allocation, expected = fixture()
        with mock.patch.dict("tools.hung_kaggle_recovery_register.EXPECTED_JOBSET_SHA", expected):
            rows = build_rows(shards, allocation)
        self.assertEqual(len(rows), 28)
        self.assertEqual(sum(row["planned_jobs"] for row in rows), 560)
        self.assertTrue(all(row["archive_sha256"] == "" for row in rows))
        self.assertTrue(
            all(row["per_job_status"] == "AWAITING_EXACT_ARCHIVE_BYTES" for row in rows)
        )

    def test_wrong_jobset_hash_is_rejected(self) -> None:
        shards, allocation, expected = fixture()
        shards["shards"][0]["job_ids"][0] = "changed"
        with mock.patch.dict("tools.hung_kaggle_recovery_register.EXPECTED_JOBSET_SHA", expected):
            with self.assertRaisesRegex(ValueError, "jobset mismatch"):
                build_rows(shards, allocation)

    def test_duplicate_job_id_is_rejected_even_with_matching_shard_hash(self) -> None:
        shards, allocation, expected = fixture()
        shards["shards"][1]["job_ids"][0] = shards["shards"][0]["job_ids"][0]
        ids = shards["shards"][1]["job_ids"]
        expected["shard_0002"] = hashlib.sha256(
            json.dumps(ids, separators=(",", ":")).encode("utf8")
        ).hexdigest()
        with mock.patch.dict("tools.hung_kaggle_recovery_register.EXPECTED_JOBSET_SHA", expected):
            with self.assertRaisesRegex(ValueError, "disjoint Kaggle shards"):
                build_rows(shards, allocation)


if __name__ == "__main__":
    unittest.main()
