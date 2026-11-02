"""Offline checks for a fresh, exact saved Kaggle GPU attestation."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from experiments.supporting_pipeline.final_archive import require
from tools import hung_final_kaggle_attestation as att
from tools.hung_final_lock_preflight import _attestation

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 29, 1, 28, tzinfo=timezone.utc)


class FakeApi:
    def __init__(self, receipt: dict):
        self.receipt = receipt
        self.versions: list[str] = []

    def kernels_status(self, version: str):
        self.versions.append(version)
        return SimpleNamespace(status=SimpleNamespace(name="COMPLETE"), failure_message="")

    def kernels_output(self, version: str, path: str, **kwargs):
        self.versions.append(version)
        require(kwargs["force"] is False, "Test download must be create-only")
        root = Path(path)
        root.mkdir(parents=True, exist_ok=False)
        (root / att.PROBE_NAME).write_text(json.dumps(self.receipt), encoding="utf-8")
        return [str(root / att.PROBE_NAME)], ""


class KaggleAttestationTests(unittest.TestCase):
    def setUp(self) -> None:
        (ROOT / ".cache").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".cache")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.packet = self.root / "packet"
        self.receipt = {
            "schema": "hung-final-gpu-capacity-probe-v1",
            "scope": "gpu_runtime_capacity_only_no_final_data",
            "observed_at_utc": NOW.isoformat(),
            "working_total_bytes": 22_000_000_000,
            "working_free_bytes": 21_000_000_000,
            "cuda_available": True,
            "gpu_name": "Tesla T4",
            "gpu_total_memory_bytes": 15_636_037_632,
        }
        self.api = FakeApi(self.receipt)

    def _prepare(self):
        receipt_raw = json.dumps(self.receipt).encode()
        with (
            mock.patch.object(att, "PROBE_SHA256", hashlib.sha256(receipt_raw).hexdigest()),
            mock.patch.object(att, "_credential_api", return_value=(self.api, "test-only-token")),
            mock.patch.object(
                att,
                "_provider_quota",
                return_value=(att.EXPECTED_ACCOUNT, 21_000, {"total_seconds": 30_000}),
            ),
            mock.patch.object(att, "_now_utc", return_value=NOW),
        ):
            path, verifier = att.prepare_attestation(
                ROOT, self.root / "credential.json", self.packet, now=NOW
            )
            value = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(verifier(value, self.packet / "provider-response.json"))
            return path, value, verifier

    def test_exact_saved_version_and_lock_compatible_packet(self) -> None:
        path, value, _ = self._prepare()
        self.assertEqual(self.api.versions, [att.PROBE_VERSION] * 3)
        self.assertEqual(value["gpu_seconds_available"], 21_000)
        self.assertEqual(value["provider_storage_free_bytes"], 21_000_000_000)
        self.assertEqual(
            _attestation(ROOT, path, NOW, 14_000, 12_000_000_000),
            value,
        )
        with self.assertRaisesRegex(ValueError, "must be new"):
            self._prepare()

    def test_stale_probe_fails_before_attestation(self) -> None:
        self.receipt["observed_at_utc"] = (NOW - timedelta(minutes=21)).isoformat()
        with self.assertRaisesRegex(ValueError, "stale/future"):
            self._prepare()
        self.assertFalse((self.packet / "attestation.json").exists())

    def test_gpu_capability_is_required(self) -> None:
        for index, change in enumerate(
            (
                {"cuda_available": False},
                {"gpu_name": ""},
                {"gpu_total_memory_bytes": att.MIN_GPU_MEMORY_BYTES - 1},
            )
        ):
            with self.subTest(change=change):
                self.packet = self.root / f"packet-{index}"
                self.receipt.update(change)
                with self.assertRaisesRegex(ValueError, "probe fields differ"):
                    self._prepare()
                self.assertFalse((self.packet / "attestation.json").exists())
                self.receipt.update(
                    cuda_available=True,
                    gpu_name="Tesla T4",
                    gpu_total_memory_bytes=15_636_037_632,
                )

    def test_changed_saved_receipt_is_rejected(self) -> None:
        _, value, verifier = self._prepare()
        receipt = self.packet / "saved-output-v1" / att.PROBE_NAME
        receipt.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Saved probe receipt changed"):
            verifier(value, self.packet / "provider-response.json")

    def test_quota_requires_complete_free_tier_fields(self) -> None:
        quota = SimpleNamespace(
            is_pay_to_scale_enabled=False,
            total_time_allowed=timedelta(hours=30),
            time_used=timedelta(hours=24),
            time_reserved=timedelta(0),
        )
        self.assertEqual(att._quota_fields(quota)[0], 21_600)
        quota.time_reserved = None
        with self.assertRaisesRegex(ValueError, "incomplete/paid"):
            att._quota_fields(quota)
        quota.time_reserved = timedelta(0)
        quota.is_pay_to_scale_enabled = True
        with self.assertRaisesRegex(ValueError, "incomplete/paid"):
            att._quota_fields(quota)

    def test_credential_must_stay_inside_repository(self) -> None:
        outside = self.root / "credential.json"
        outside.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Repository-local"):
            att._credential_api(ROOT, outside, NOW)


if __name__ == "__main__":
    unittest.main()
