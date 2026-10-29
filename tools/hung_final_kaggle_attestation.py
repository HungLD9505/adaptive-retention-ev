"""Authenticate one saved Kaggle GPU capacity probe and fresh free-tier quota.

The returned verifier is valid only in the process that performed the provider
readback. No credential or bearer token is written to the attestation packet.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from experiments.hung_sprint2.final_archive import require
from tools.hung_final_lock_preflight import _pin

PROBE_VERSION = "hungluongduc/hung-final-gpu-capacity-probe-20261029-2a6a92a7/1"
PROBE_NAME = "hung-final-gpu-capacity-probe.json"
PROBE_SHA256 = "88c5da9721237509fa3e48f28d418310fdcbe11a6a13b0e8f68070f5532bde98"
EXPECTED_ACCOUNT = "hungluongduc"
MAX_AGE = timedelta(minutes=20)
MIN_GPU_MEMORY_BYTES = 4 * 1024**3


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: str) -> datetime:
    observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(observed.tzinfo is not None, "Capacity timestamp lacks UTC offset")
    return observed.astimezone(timezone.utc)


def _fresh(observed: datetime, now: datetime) -> None:
    require(
        now - MAX_AGE <= observed <= now + timedelta(minutes=2),
        "Saved Kaggle capacity probe is stale/future",
    )


def _credential_api(root: Path, credential_path: Path, now: datetime):
    """Use only the explicitly selected credential inside the repository."""
    safe_root = (root / ".cache" / "kaggle-auth").resolve()
    credential = credential_path.resolve()
    require(
        credential.is_relative_to(safe_root)
        and credential.is_file()
        and not credential_path.is_symlink(),
        "Repository-local Kaggle credential is absent/unsafe",
    )
    raw = json.loads(credential.read_text(encoding="utf-8"))
    require(
        isinstance(raw, dict)
        and raw.get("username") == EXPECTED_ACCOUNT
        and isinstance(raw.get("access_token"), str)
        and bool(raw["access_token"]),
        "Kaggle account/access token differs",
    )
    expiration = _timestamp(raw["access_token_expiration"])
    require(expiration >= now + timedelta(minutes=5), "Kaggle access token is expired/near expiry")

    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.config_values[api.CONFIG_NAME_TOKEN] = raw["access_token"]
    api.config_values[api.CONFIG_NAME_USER] = EXPECTED_ACCOUNT
    return api, raw["access_token"]


def _quota_fields(quota) -> tuple[float, dict]:
    require(quota is not None, "Kaggle GPU quota response is absent")
    total, used, reserved = (
        quota.total_time_allowed,
        quota.time_used,
        quota.time_reserved,
    )
    require(
        quota.is_pay_to_scale_enabled is False
        and all(value is not None for value in (total, used, reserved)),
        "Free-tier Kaggle GPU quota is incomplete/paid",
    )
    seconds = (total - used - reserved).total_seconds()
    require(seconds >= 0, "Kaggle available GPU quota is negative")
    fields = {
        "total_seconds": total.total_seconds(),
        "used_seconds": used.total_seconds(),
        "reserved_seconds": reserved.total_seconds(),
    }
    return seconds, fields


def _provider_quota(api, token: str) -> tuple[str, float, dict]:
    from kagglesdk.kernels.types.kernels_api_service import (
        ApiGetAcceleratorQuotaStatisticsRequest,
    )
    from kagglesdk.security.types.oauth_service import IntrospectTokenRequest

    with api.build_kaggle_client() as client:
        request = IntrospectTokenRequest()
        request.token = token
        identity = client.security.oauth_client.introspect_token(request)
        require(
            identity.active is True and identity.username == EXPECTED_ACCOUNT,
            "Authenticated Kaggle account differs",
        )
        quota = client.kernels.kernels_api_client.get_accelerator_quota_statistics(
            ApiGetAcceleratorQuotaStatisticsRequest()
        ).gpu_quota
    seconds, fields = _quota_fields(quota)
    return EXPECTED_ACCOUNT, seconds, fields


def _saved_probe(api, folder: Path, now: datetime) -> tuple[dict, dict]:
    status = api.kernels_status(PROBE_VERSION)
    state = getattr(status.status, "name", str(status.status)).upper()
    require(
        state == "COMPLETE" and not status.failure_message, "Saved Kaggle probe is not complete"
    )
    downloaded = folder / "saved-output-v1"
    require(not downloaded.exists(), "Kaggle probe output destination already exists")
    api.kernels_output(
        PROBE_VERSION,
        str(downloaded),
        file_pattern=r"^hung-final-gpu-capacity-probe\.json$",
        force=False,
        quiet=True,
    )
    receipt_path = downloaded / PROBE_NAME
    pin = _pin(receipt_path)
    require(pin["sha256"] == PROBE_SHA256, "Saved Kaggle probe receipt SHA differs")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(
        receipt.get("schema") == "hung-final-gpu-capacity-probe-v1"
        and receipt.get("scope") == "gpu_runtime_capacity_only_no_final_data"
        and receipt.get("cuda_available") is True
        and receipt.get("gpu_name") == "Tesla T4"
        and type(receipt.get("gpu_total_memory_bytes")) is int
        and receipt["gpu_total_memory_bytes"] >= MIN_GPU_MEMORY_BYTES
        and type(receipt.get("working_free_bytes")) is int
        and receipt["working_free_bytes"] > 0
        and type(receipt.get("working_total_bytes")) is int
        and receipt["working_total_bytes"] >= receipt["working_free_bytes"],
        "Saved Kaggle probe fields differ",
    )
    _fresh(_timestamp(receipt["observed_at_utc"]), now)
    return receipt, pin


def prepare_attestation(
    root: Path, credential_path: Path, packet: Path, *, now: datetime | None = None
) -> tuple[Path, Callable[[dict, Path], bool]]:
    """Write create-only evidence, then return a live authenticated verifier.

    Call ``prepare_lock`` with the returned path and callback in the same
    process. A later process must repeat the authenticated readback.
    """
    root = root.resolve()
    packet = packet.resolve()
    require(
        packet.is_relative_to((root / ".cache").resolve()) and not packet.exists(),
        "Kaggle attestation packet must be new under repository .cache",
    )
    observed = now or _now_utc()
    require(observed.tzinfo is not None, "UTC-aware attestation time is required")
    observed = observed.astimezone(timezone.utc)
    api, token = _credential_api(root, credential_path, observed)
    account, seconds, quota_fields = _provider_quota(api, token)
    packet.mkdir(parents=True, exist_ok=False)
    receipt, receipt_pin = _saved_probe(api, packet, observed)
    evidence_path = packet / "provider-response.json"
    evidence = {
        "schema": "hung-final-authenticated-kaggle-capacity-v1",
        "provider": "kaggle",
        "account": account,
        "observed_at_utc": observed.isoformat(),
        "gpu_seconds_available": seconds,
        "provider_storage_free_bytes": receipt["working_free_bytes"],
        "is_pay_to_scale_enabled": False,
        "quota": quota_fields,
        "saved_probe_version": PROBE_VERSION,
        "saved_probe_receipt": receipt_pin,
        "saved_probe_observed_at_utc": receipt["observed_at_utc"],
    }
    with evidence_path.open("x", encoding="utf-8") as stream:
        json.dump(evidence, stream, sort_keys=True)
    attested = {
        "schema": "hung-final-provider-attestation-v1",
        "provider": "kaggle",
        "account": account,
        "observed_at_utc": evidence["observed_at_utc"],
        "authentication_method": "authenticated_kaggle_api",
        "evidence": _pin(evidence_path),
        "gpu_seconds_available": seconds,
        "provider_storage_free_bytes": receipt["working_free_bytes"],
        "is_pay_to_scale_enabled": False,
    }
    attestation_path = packet / "attestation.json"
    with attestation_path.open("x", encoding="utf-8") as stream:
        json.dump(attested, stream, sort_keys=True)

    def verify(current: dict, source: Path) -> bool:
        require(current == attested and source.resolve() == evidence_path, "Attestation changed")
        require(_pin(evidence_path) == attested["evidence"], "Attestation evidence changed")
        require(_pin(Path(receipt_pin["path"])) == receipt_pin, "Saved probe receipt changed")
        _fresh(_timestamp(receipt["observed_at_utc"]), _now_utc())
        account_now, seconds_now, _ = _provider_quota(api, token)
        require(
            account_now == account and seconds_now >= seconds,
            "Authenticated Kaggle GPU quota fell after attestation",
        )
        status_now = api.kernels_status(PROBE_VERSION)
        require(
            getattr(status_now.status, "name", str(status_now.status)).upper() == "COMPLETE"
            and not status_now.failure_message,
            "Pinned saved Kaggle probe is no longer complete",
        )
        return True

    return attestation_path, verify
