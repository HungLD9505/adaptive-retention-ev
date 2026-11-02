"""Trace the common unscored Final origin to the frozen input-label bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

INPUT_SHA = "2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7"
PREFIX = "data/inputs/issue18-input-handoff-v1-20261019"
IDENTITY = ["urbanev", "SZH", "2118"]
ORIGIN = "2022-12-09T00:00:00+08:00"
BUDGETS = (7, 14, 28)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(input_zip: Path, *, expected_sha: str = INPUT_SHA) -> dict:
    """Check the exact label record and invalid bins in all three budget members."""
    if _sha256(input_zip) != expected_sha:
        raise ValueError("Frozen Final input ZIP SHA-256 mismatch")
    results = []
    with ZipFile(input_zip) as archive:
        for budget in BUDGETS:
            name = f"{PREFIX}/urbanev-SZH-{budget}d/labels.jsonl"
            digest = hashlib.sha256()
            matches = []
            with archive.open(name) as stream:
                for line in stream:
                    digest.update(line)
                    if b'"2118"' not in line or ORIGIN.encode() not in line:
                        continue
                    record = json.loads(line)
                    if record.get("identity") == IDENTITY and record.get("origin") == ORIGIN:
                        matches.append((record, hashlib.sha256(line).hexdigest()))
            if len(matches) != 1:
                raise ValueError(f"Budget {budget}: expected one matching Final label record")
            record, record_sha = matches[0]
            timestamps = record["timestamps"]
            energy = record["energy_kwh"]
            valid = record["file_valid"]
            if (
                record.get("clock_mode") != "offset-aware-local"
                or len(timestamps) != 24
                or len(energy) != 24
                or len(valid) != 24
                or any(type(flag) is not bool for flag in valid)
                or any((value is None) == flag for value, flag in zip(energy, valid, strict=True))
            ):
                raise ValueError(f"Budget {budget}: invalid 24-hour label record")
            invalid = [
                {"index": index, "timestamp": timestamps[index]}
                for index, flag in enumerate(valid)
                if not flag
            ]
            results.append(
                {
                    "budget_days": budget,
                    "member": name,
                    "member_sha256": digest.hexdigest(),
                    "record_sha256": record_sha,
                    "valid_bins": sum(valid),
                    "invalid_bins": invalid,
                }
            )
    if len({row["record_sha256"] for row in results}) != 1:
        raise ValueError("Final label records differ across history budgets")
    if len({json.dumps(row["invalid_bins"], sort_keys=True) for row in results}) != 1:
        raise ValueError("Invalid label bins differ across history budgets")
    return {
        "schema": "hung-final-null-label-input-audit-v1",
        "input_zip_sha256": expected_sha,
        "identity": IDENTITY,
        "origin": ORIGIN,
        "budget_records": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-zip", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"refusing to overwrite {args.output}")
    result = audit(args.input_zip)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps({"budgets": len(result["budget_records"])}))


if __name__ == "__main__":
    main()
