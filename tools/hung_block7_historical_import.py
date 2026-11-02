"""Inventory and verify staged historical Block7 checkpoint files without training."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAIRS = ROOT / "docs/reports/hung-block7-manifest-pairs-20261028.csv"
PAIRS_SHA256 = "e260de421d6c53ef3dffe5901f9e3478708b9e578791d3f370588a0a508699de"
STAGE = ROOT / ".cache/block7-historical-import-v1"
REQUEST = ROOT / "docs/reports/hung-block7-historical-checkpoint-request-20261029-v1.csv"
FIELDS = ("role", "sha256", "staged_path", "budget_days", "seed", "historical_run_ids")


def sha_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_pairs() -> list[dict[str, str]]:
    if sha_file(PAIRS) != PAIRS_SHA256:
        raise ValueError("Pinned Block7 pair CSV SHA-256 mismatch")
    with PAIRS.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 69 or len({row["historical_run_id"] for row in rows}) != 69:
        raise ValueError("Expected exactly 69 distinct historical Block7 runs")
    return rows


def request_rows(pairs: list[dict[str, str]], *, strict: bool = True) -> list[dict[str, str]]:
    requests: dict[tuple[str, str], dict[str, str]] = {}
    for pair in pairs:
        run_id = pair["historical_run_id"]
        if not re.fullmatch(r"block7_b(7|14|28)s(7|11|19)e\d+", run_id):
            raise ValueError(f"Unexpected historical run ID: {run_id}")
        for role in ("source", "target"):
            digest = pair[f"historical_{role}_sha256"]
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError(f"Invalid {role} SHA-256 for {run_id}")
            key = (role, digest)
            request = requests.setdefault(
                key,
                {
                    "role": role,
                    "sha256": digest,
                    "staged_path": f".cache/block7-historical-import-v1/{digest}.pt",
                    "budget_days": pair["budget_days"],
                    "seed": pair["seed"],
                    "historical_run_ids": [],
                },
            )
            if role == "source" and (
                request["budget_days"] != pair["budget_days"] or request["seed"] != pair["seed"]
            ):
                raise ValueError("Source checkpoint reused across incompatible budget/seed")
            request["historical_run_ids"].append(run_id)
    result = []
    for request in requests.values():
        result.append(
            {
                **request,
                "historical_run_ids": ";".join(sorted(request["historical_run_ids"])),
            }
        )
    result.sort(
        key=lambda item: (item["role"], int(item["budget_days"]), int(item["seed"]), item["sha256"])
    )
    if strict and (
        len(pairs) != 69
        or sum(row["role"] == "source" for row in result) != 9
        or sum(row["role"] == "target" for row in result) != 69
    ):
        raise ValueError("Expected 9 unique Source and 69 unique Target checkpoint files")
    return result


def render_request(rows: list[dict[str, str]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def verify_stage(rows: list[dict[str, str]], stage: Path) -> dict:
    expected = {f"{row['sha256']}.pt" for row in rows}
    present = {path.name for path in stage.iterdir()} if stage.is_dir() else set()
    counts = {"VERIFIED": 0, "MISSING": 0, "MISMATCH": 0}
    for row in rows:
        path = stage / f"{row['sha256']}.pt"
        if not path.exists():
            status = "MISSING"
        elif path.is_symlink() or not path.is_file() or sha_file(path) != row["sha256"]:
            status = "MISMATCH"
        else:
            status = "VERIFIED"
        counts[status] += 1
    extra = sorted(present - expected)
    return {
        "schema": "hung-block7-historical-checkpoint-stage-v1",
        "scope": "file_bytes_only; no payload equivalence or scientific acceptance",
        "expected_files": len(rows),
        "counts": counts,
        "unexpected_entries": extra,
        "complete": counts["VERIFIED"] == len(rows) and not extra,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-request", action="store_true")
    args = parser.parse_args()
    if not STAGE.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Staging directory resolves outside the repository")
    rows = request_rows(load_pairs())
    payload = render_request(rows)
    if args.write_request:
        if REQUEST.exists():
            if REQUEST.read_bytes() != payload:
                raise ValueError("Existing request differs; historical evidence is create-only")
        else:
            REQUEST.write_bytes(payload)
    result = verify_stage(rows, STAGE)
    result["pair_csv_sha256"] = PAIRS_SHA256
    result["request_sha256"] = hashlib.sha256(payload).hexdigest()
    print(json.dumps(result, sort_keys=True))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
