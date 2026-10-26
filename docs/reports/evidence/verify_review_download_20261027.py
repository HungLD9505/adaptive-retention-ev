"""Verify the two-file Kaggle review export without training or changing inputs."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT.parents[1] if ROOT.parent.name == ".cache" else ROOT
DATASET = "https://www.kaggle.com/datasets/hungluongduc/hung-e2e-review-gates-44b8532-20261027-v1"
EXPECTED = {
    "e2e-review-bundle-v1.zip.bin": (
        212497,
        "7e088184c279fed43c3f7cfc2a312e1400e44baa4aceb0fcf5c0bd826d4267eb",
    ),
    "transport-map.json": (
        419,
        "aed7fc2f2e38cf08bac3be345e4cc2f1dfdd70dbced46b46e61db0f86afdf8d8",
    ),
}


def project_path(path: Path) -> Path:
    result = path.resolve()
    if not result.is_relative_to(PROJECT):
        raise ValueError("Artifact path must stay inside the supplied project")
    return result


def verify(path: Path) -> dict:
    """Accept either the downloaded Dataset ZIP or a directory with both files."""
    started = time.perf_counter()
    path = project_path(path)
    if path.is_dir():
        payloads = {}
        for name, (size, _) in EXPECTED.items():
            source = project_path(path / name)
            if source.stat().st_size != size:
                raise ValueError(f"Readback size mismatch: {name}")
            payloads[name] = source.read_bytes()
        transport = "directory"
    else:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or set(names) != set(EXPECTED):
                raise ValueError("Dataset ZIP contains duplicate, missing or unexpected files")
            if any(archive.getinfo(name).file_size != EXPECTED[name][0] for name in names):
                raise ValueError("Dataset ZIP member size mismatch")
            if archive.testzip() is not None:
                raise ValueError("Dataset ZIP CRC failed")
            payloads = {name: archive.read(name) for name in EXPECTED}
        transport = "dataset_zip"
    checks = []
    for name, (size, expected_sha) in EXPECTED.items():
        raw = payloads[name]
        actual_sha = hashlib.sha256(raw).hexdigest()
        if len(raw) != size or actual_sha != expected_sha:
            raise ValueError(f"Readback bytes/SHA mismatch: {name}")
        checks.append({"name": name, "bytes": size, "sha256": actual_sha})
    with zipfile.ZipFile(io.BytesIO(payloads["e2e-review-bundle-v1.zip.bin"])) as bundle:
        members = bundle.namelist()
        if len(members) != 94 or len(members) != len(set(members)):
            raise ValueError("Review bundle member count/uniqueness mismatch")
        if bundle.testzip() is not None:
            raise ValueError("Review bundle CRC failed")
    return {
        "schema": "hung-review-bundle-readback-v1",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_url": DATASET,
        "version": 1,
        "input": str(path),
        "input_transport": transport,
        "files": checks,
        "review_bundle_members": 94,
        "review_bundle_crc": "passed",
        "verification_seconds": time.perf_counter() - started,
        "scope": "Byte/CRC validation only; does not prove remote origin, reviewer access or independent teammate reproduction",
        "training_executed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        value = verify(args.download)
        output = project_path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        parser.exit(1, f"Review readback verification failed: {error}\n")
    print(json.dumps({"status": "verified_bytes_only", "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
