"""Build a no-submit, hash-checked candidate ledger for 69 Block7 replay jobs."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
PARENT_PLAN_SHA256 = "2d448d2584f65baf7e09445e013b4283314b08ea2cce855c6850e9fc12ba87ee"
PORTABLE_PLAN_SHA256 = "b7c79f501230ea5e1308b4bc02b2707089a8c788e4ee3df229aadec005a05198"
PAIR_CSV_SHA256 = "e260de421d6c53ef3dffe5901f9e3478708b9e578791d3f370588a0a508699de"
LEDGER_SHA256 = "bf1117c1d5fc0a902411cb6d850dca51e77802997c32880295ede20d8ac83004"
INPUT_ZIP_SHA256 = "2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7"
MAIN_CONFIG_SHA256 = "d9622ffa702cd4130cfed46371acca463a98f7fd21b880a83d36c3899559951f"
BLOCK7_CONFIG_SHA256 = "91ef6159391c8fa2b30e82d4cea740667135466bf36b7e797e7bf73e9fccf24f"


def digest(path: Path) -> str:
    """Return the SHA-256 of the saved file bytes."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def pinned_json(path: Path, expected_sha256: str) -> dict:
    """Read exact pinned JSON bytes."""
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError(f"Pinned SHA-256 differs: {path}")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def replay_id(cell_id: str) -> str:
    """Use a new namespace that cannot silently alias historical Block7 IDs."""
    if not cell_id.isidentifier():
        raise ValueError(f"Invalid cell ID: {cell_id}")
    return f"block7_replay_candidate_v1_{cell_id}"


def assert_only_block_days_changes(main: dict, block7: dict) -> None:
    """Reject a contingency config that changes any other field."""
    expected = copy.deepcopy(main)
    if expected["replay"]["block_days"] != 14 or block7["replay"]["block_days"] != 7:
        raise ValueError("Unexpected Main/Block7 block length")
    expected["replay"]["block_days"] = 7
    if expected != block7:
        raise ValueError("Main and Block7 configs differ beyond replay.block_days")


def safe_payload_path(payload: Path, relative: str) -> Path:
    """Resolve a frozen portable-plan member without leaving the payload tree."""
    path = (payload / relative).resolve()
    if not path.is_relative_to(payload.resolve()):
        raise ValueError(f"Checkpoint escapes payload: {relative}")
    return path


def checked_checkpoint(payload: Path, spec: dict) -> tuple[Path, int]:
    """Check checkpoint and its adjacent manifest against the frozen plan."""
    if set(spec) != {"path", "sha256", "run_manifest_sha256"}:
        raise ValueError("Incomplete frozen checkpoint binding")
    path = safe_payload_path(payload, spec["path"])
    if digest(path) != spec["sha256"]:
        raise ValueError(f"Checkpoint SHA-256 differs: {path}")
    if digest(path.parent / "run_manifest.json") != spec["run_manifest_sha256"]:
        raise ValueError(f"Checkpoint manifest SHA-256 differs: {path}")
    return path, path.stat().st_size


def build_candidate(
    payload: Path, pairs_path: Path, ledger_path: Path
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Validate all 69 pair, input, and checkpoint bytes and return candidate rows."""
    parent = pinned_json(payload / "parent-plan.json", PARENT_PLAN_SHA256)
    portable = pinned_json(payload / "portable-plan.json", PORTABLE_PLAN_SHA256)
    if parent.get("code_commit") != "44b8532959d76fb20691881539f991ca44983727":
        raise ValueError("Frozen Development code commit differs")
    if parent.get("scope") != "development_only" or portable.get("scope") != "development_only":
        raise ValueError("Unexpected plan scope")
    if len(parent.get("jobs", [])) != 782 or len(portable.get("jobs", [])) != 782:
        raise ValueError("Frozen new-job count differs")
    main = pinned_json(payload / ".cache/provider/configs/main.json", MAIN_CONFIG_SHA256)
    block7 = pinned_json(payload / ".cache/provider/configs/block7.json", BLOCK7_CONFIG_SHA256)
    assert_only_block_days_changes(main, block7)
    if digest(pairs_path) != PAIR_CSV_SHA256 or digest(ledger_path) != LEDGER_SHA256:
        raise ValueError("Pair table or ledger SHA-256 differs")
    with pairs_path.open(newline="", encoding="utf-8") as stream:
        pairs = list(csv.DictReader(stream))
    with ledger_path.open(newline="", encoding="utf-8") as stream:
        ledger_ids = {row["job_id"] for row in csv.DictReader(stream)}
    if len(pairs) != 69 or len(ledger_ids) != 782:
        raise ValueError("Expected 69 pairs and 782 unique new-job IDs")
    cells = {cell["id"]: cell for cell in portable["cells"]}
    anchors = {
        job["cell"]: job for job in portable["jobs"] if job["id"] == f"block28_{job['cell']}"
    }
    if len(cells) != 69 or len(anchors) != 69:
        raise ValueError("Missing matched Main-state Block28 anchor")
    input_zip = payload / "inputs.zip"
    if digest(input_zip) != INPUT_ZIP_SHA256:
        raise ValueError("Frozen input ZIP SHA-256 differs")
    with ZipFile(input_zip) as archive:
        for budget in (7, 14, 28):
            name = (
                f"data/inputs/issue18-input-handoff-v1-20261019/urbanev-SZH-{budget}d/manifest.json"
            )
            raw = archive.read(name)
            actual = hashlib.sha256(raw).hexdigest()
            if {
                cell["input_manifest_sha256"] for cell in cells.values() if cell["budget"] == budget
            } != {actual}:
                raise ValueError(f"Input manifest differs for budget {budget}")
    rows: list[dict[str, object]] = []
    seen = set()
    historical_ids: set[str] = set()
    main_ids: set[str] = set()
    for pair in sorted(pairs, key=lambda row: row["cell_id"]):
        cell_id = pair["cell_id"]
        if cell_id in seen or cell_id not in cells:
            raise ValueError(f"Duplicate/unknown pair cell: {cell_id}")
        seen.add(cell_id)
        if pair["historical_run_id"] in historical_ids or pair["main_run_id"] in main_ids:
            raise ValueError(f"Duplicate historical/Main ID: {cell_id}")
        historical_ids.add(pair["historical_run_id"])
        main_ids.add(pair["main_run_id"])
        cell = cells[cell_id]
        anchor = anchors[cell_id]
        source, target = anchor["source"], anchor["target"]
        if source is None or target is None or anchor["method"] != "confidence":
            raise ValueError(f"Block28 anchor lacks matched state: {cell_id}")
        if (
            source["sha256"] != pair["main_source_sha256"]
            or target["sha256"] != pair["main_target_sha256"]
            or pair["main_run_id"] != f"main_{cell_id}"
            or pair["historical_run_id"] != f"block7_{cell_id}"
            or int(pair["budget_days"]) != cell["budget"]
            or int(pair["seed"]) != cell["seed"]
        ):
            raise ValueError(f"Pair/anchor identity differs: {cell_id}")
        _, source_bytes = checked_checkpoint(payload, source)
        _, target_bytes = checked_checkpoint(payload, target)
        job_id = replay_id(cell_id)
        if job_id in ledger_ids or job_id in historical_ids or job_id in main_ids:
            raise ValueError(f"Replay ID collides with old job: {job_id}")
        rows.append(
            {
                "candidate_job_id": job_id,
                "cell_id": cell_id,
                "budget_days": cell["budget"],
                "seed": cell["seed"],
                "entity_id": cell["entity_id"],
                "historical_block7_run_id": pair["historical_run_id"],
                "historical_block7_manifest_sha256": pair["historical_manifest_sha256"],
                "main_run_id": pair["main_run_id"],
                "main_manifest_sha256": pair["main_manifest_sha256"],
                "input_manifest_sha256": cell["input_manifest_sha256"],
                "source_checkpoint_sha256": source["sha256"],
                "source_manifest_sha256": source["run_manifest_sha256"],
                "source_checkpoint_bytes": source_bytes,
                "target_checkpoint_sha256": target["sha256"],
                "target_manifest_sha256": target["run_manifest_sha256"],
                "target_checkpoint_bytes": target_bytes,
                "block7_config_sha256": BLOCK7_CONFIG_SHA256,
                "planned_stage_names": "replay-21|replay-90",
                "status": "CONTINGENT_NOT_AUTHORIZED",
            }
        )
    budgets = Counter(row["budget_days"] for row in rows)
    if budgets != {7: 18, 14: 24, 28: 27} or len({row["candidate_job_id"] for row in rows}) != 69:
        raise ValueError("Candidate jobset differs from the 18/24/27 allocation")
    summary = {
        "scope": "Development Block7 contingency only; no submission or authorization",
        "candidate_jobs": 69,
        "budget_counts": dict(sorted(budgets.items())),
        "source_checkpoint_hashes": len({row["source_checkpoint_sha256"] for row in rows}),
        "target_checkpoint_hashes": len({row["target_checkpoint_sha256"] for row in rows}),
        "frozen_parent_plan_sha256": PARENT_PLAN_SHA256,
        "frozen_portable_plan_sha256": PORTABLE_PLAN_SHA256,
        "pair_table_sha256": PAIR_CSV_SHA256,
        "v5_ledger_sha256": LEDGER_SHA256,
        "input_zip_sha256": INPUT_ZIP_SHA256,
        "block7_config_sha256": BLOCK7_CONFIG_SHA256,
        "frozen_development_code_commit": parent["code_commit"],
        "stages_per_job": ["replay-21", "replay-90"],
    }
    return rows, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--pairs", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    payload, pairs, ledger, output = (
        path.resolve() for path in (args.payload, args.pairs, args.ledger, args.output_dir)
    )
    if not all(path.is_relative_to(ROOT) for path in (payload, pairs, ledger, output)):
        parser.error("All paths must remain inside this repository")
    if output.exists():
        parser.error("Create-only output directory already exists")
    rows, summary = build_candidate(payload, pairs, ledger)
    output.mkdir(parents=True)
    table = output / "candidate_jobs.csv"
    with table.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    summary["candidate_csv_sha256"] = digest(table)
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
