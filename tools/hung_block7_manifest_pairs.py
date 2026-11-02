"""Build a manifest-level Block7/Main review table without accepting equivalence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/reports/evidence/hung-development-coverage-20261027.json"
DEFAULT_COVERAGE = ROOT / ".cache/block7-review-v1/coverage.json"
DEFAULT_MANIFEST_DIR = ROOT / ".cache/block7-review-v1/manifests"
DEFAULT_OUTPUT = ROOT / "docs/reports/hung-block7-manifest-pairs-20261028.csv"


def sha_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checked_manifest(spec: dict, path: pathlib.Path) -> dict:
    if not path.is_file() or sha_file(path) != spec["sha256"]:
        raise ValueError(f"Missing or changed manifest: {path}")
    return json.loads(path.read_text(encoding="utf8"))


def compare(coverage: dict, manifest_dir: pathlib.Path = DEFAULT_MANIFEST_DIR) -> list[dict]:
    external = coverage["external_complete_jobs"]
    main = coverage["reused_jobs"]
    if len(external) != 69 or len(main) != 69:
        raise ValueError("Expected exactly 69 historical and 69 Main runs")
    rows = []
    for historical_id, proof in sorted(external.items()):
        match = re.fullmatch(r"block7_(b(7|14|28)s(7|11|19)e\d+)", historical_id)
        if match is None:
            raise ValueError(f"Unexpected historical ID: {historical_id}")
        cell_id, budget, seed = match.groups()
        main_id = f"main_{cell_id}"
        if main_id not in main:
            raise ValueError(f"Missing Main run: {main_id}")
        old = checked_manifest(proof["run_manifest"], manifest_dir / f"block7_{cell_id}.json")
        current = checked_manifest(main[main_id], manifest_dir / f"main_{cell_id}.json")
        old_binding = {
            k: v for k, v in old["input_binding"].items() if k != "source_checkpoint_sha256"
        }
        main_binding = {
            k: v for k, v in current["input_binding"].items() if k != "source_checkpoint_sha256"
        }
        old_config = json.loads(json.dumps(old["config"]))
        main_config = json.loads(json.dumps(current["config"]))
        old_block = old_config["controller"].pop("block_days")
        main_block = main_config["controller"].pop("block_days")
        checks = {
            "input_except_source_sha_equal": old_binding == main_binding,
            "source_input_equal": old["source_input_binding"] == current["source_input_binding"],
            "config_except_block_days_equal": old_config == main_config,
            "executed_sources_equal": old["code"]["executed_sources"]
            == current["code"]["executed_sources"],
            "coverage_equal": old["coverage"] == current["coverage"],
            "historical_source_recorded": old["source_checkpoint_sha256"]
            == proof["source"]["sha256"],
            "historical_target_recorded": old["target_checkpoint_sha256"]
            == proof["target"]["sha256"],
            "only_block7_vs_main": old_block == 7 and main_block == 14,
        }
        rows.append(
            {
                "cell_id": cell_id,
                "budget_days": int(budget),
                "seed": int(seed),
                "historical_run_id": historical_id,
                "main_run_id": main_id,
                "historical_manifest_sha256": proof["run_manifest"]["sha256"],
                "main_manifest_sha256": main[main_id]["sha256"],
                "historical_source_sha256": old["source_checkpoint_sha256"],
                "main_source_sha256": current["source_checkpoint_sha256"],
                "historical_target_sha256": old["target_checkpoint_sha256"],
                "main_target_sha256": current["target_checkpoint_sha256"],
                **checks,
                "review_status": "PENDING_PEER" if all(checks.values()) else "MANIFEST_MISMATCH",
            }
        )
    if set(main) != {row["main_run_id"] for row in rows}:
        raise ValueError("Unpaired Main run")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", type=pathlib.Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--manifest-dir", type=pathlib.Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    evidence = json.loads(EVIDENCE.read_text(encoding="utf8"))
    expected_sha = evidence["audit"]["provenance"]["inputs"]["coverage"]["sha256"]
    if sha_file(args.coverage) != expected_sha:
        raise SystemExit("Coverage SHA mismatch")
    rows = compare(json.loads(args.coverage.read_text(encoding="utf8")), args.manifest_dir)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    data = stream.getvalue().encode("utf8")
    if args.output.exists():
        if args.output.read_bytes() != data:
            raise SystemExit("Existing review table differs")
    else:
        args.output.write_bytes(data)
    print(
        json.dumps(
            {
                "rows": len(rows),
                "manifest_consistent": sum(row["review_status"] == "PENDING_PEER" for row in rows),
                "manifest_mismatch": sum(
                    row["review_status"] == "MANIFEST_MISMATCH" for row in rows
                ),
                "peer_accepted": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
