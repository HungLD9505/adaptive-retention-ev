"""Prepare outcome-blind Hùng Final entity metadata without reading Final values."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

INPUT_SHA256 = "2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7"
PLAN_SHA256 = "b7c79f501230ea5e1308b4bc02b2707089a8c788e4ee3df229aadec005a05198"
SALT = "hung-final-urban-candidate-v1"
BUDGETS = (7, 14, 28)
SEEDS = (7, 11, 19)


def digest(path: Path) -> str:
    """Hash a file without copying or changing it."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def rank_entity(entity_id: str) -> str:
    """Order Final-role IDs without consulting coverage, labels or outcomes."""
    return hashlib.sha256(f"{SALT}|{entity_id}".encode()).hexdigest()


def final_ids(archive: ZipFile, budget: int) -> tuple[set[str], str]:
    """Read only entity-role metadata and the manifest for one budget."""
    prefix = f"data/inputs/issue18-input-handoff-v1-20261019/urbanev-SZH-{budget}d/"
    manifest_bytes = archive.read(prefix + "manifest.json")
    manifest = json.loads(manifest_bytes)
    if (
        manifest["config"]["history_days"] != budget
        or manifest["config"]["dataset_id"] != "urbanev"
        or manifest["config"]["city_id"] != "SZH"
    ):
        raise ValueError(f"Input manifest identity differs at {budget} days")
    ids: set[str] = set()
    for line in archive.read(prefix + "entities.jsonl").splitlines():
        record = json.loads(line)
        if record["role"] != "final":
            continue
        if record["history_days"] != budget or record["identity"][:2] != ["urbanev", "SZH"]:
            raise ValueError(f"Final entity identity differs at {budget} days")
        entity_id = record["identity"][2]
        if entity_id in ids:
            raise ValueError(f"Duplicate Final entity: {entity_id}")
        ids.add(entity_id)
    if len(ids) != manifest["counts"]["final"]:
        raise ValueError(f"Final entity count differs at {budget} days")
    return ids, hashlib.sha256(manifest_bytes).hexdigest()


def source_catalog(payload: Path, input_hashes: dict[int, str]) -> list[dict]:
    """Authenticate the nine reusable Development Source file identities."""
    plan_path = payload / "portable-plan.json"
    if digest(plan_path) != PLAN_SHA256:
        raise ValueError("Development portable plan SHA differs")
    plan = json.loads(plan_path.read_bytes())
    cells = {cell["id"]: cell for cell in plan["cells"]}
    sources: dict[tuple[int, int], dict] = {}
    for job in plan["jobs"]:
        spec = job.get("source")
        if spec is None:
            continue
        cell = cells[job["cell"]]
        budget, seed = cell["budget"], cell["seed"]
        if cell["input_manifest_sha256"] != input_hashes[budget]:
            raise ValueError("Source cell uses a different input manifest")
        key = (budget, seed)
        if key in sources and sources[key] != spec:
            raise ValueError(f"Conflicting Source specification: {key}")
        sources[key] = spec
    if set(sources) != {(budget, seed) for budget in BUDGETS for seed in SEEDS}:
        raise ValueError("Expected nine budget/seed Source specifications")
    rows = []
    for (budget, seed), spec in sorted(sources.items()):
        path = (payload / spec["path"]).resolve()
        if not path.is_relative_to(payload.resolve()):
            raise ValueError("Source path escapes payload")
        if digest(path) != spec["sha256"]:
            raise ValueError(f"Source checkpoint SHA differs: {budget}/{seed}")
        manifest = path.parent / "run_manifest.json"
        if digest(manifest) != spec["run_manifest_sha256"]:
            raise ValueError(f"Source manifest SHA differs: {budget}/{seed}")
        rows.append(
            {
                "budget_days": budget,
                "seed": seed,
                "source_checkpoint_path": path.relative_to(payload.parent.parent.parent).as_posix(),
                "source_checkpoint_bytes": path.stat().st_size,
                "source_checkpoint_sha256": spec["sha256"],
                "source_manifest_sha256": spec["run_manifest_sha256"],
                "input_manifest_sha256": input_hashes[budget],
                "status": "DEVELOPMENT_SOURCE_CANDIDATE_ONLY",
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output_dir.resolve()
    if not output.is_relative_to(root) or output.exists():
        raise ValueError("Output must be a new directory inside repository")
    payload = root / ".cache/kaggle-payload-v2/payload"
    input_zip = payload / "inputs.zip"
    if digest(input_zip) != INPUT_SHA256:
        raise ValueError("Frozen input ZIP SHA differs")
    with ZipFile(input_zip) as archive:
        by_budget = {budget: final_ids(archive, budget) for budget in BUDGETS}
    cohorts = [value[0] for value in by_budget.values()]
    if any(ids != cohorts[0] for ids in cohorts[1:]):
        raise ValueError("Final entity IDs differ across budgets")
    input_hashes = {budget: value[1] for budget, value in by_budget.items()}
    selected = sorted(cohorts[0], key=lambda entity_id: (rank_entity(entity_id), entity_id))
    entity_rows = [
        {
            "entity_id": entity_id,
            "rank_sha256": rank_entity(entity_id),
            "candidate_urban30": rank < 30,
        }
        for rank, entity_id in enumerate(selected)
    ]
    source_rows = source_catalog(payload, input_hashes)
    output.mkdir(parents=True, exist_ok=False)
    write_csv(output / "urban_final_entity_metadata.csv", entity_rows)
    write_csv(output / "development_source_candidates.csv", source_rows)
    summary = {
        "schema": "hung-final-metadata-preflight-v1",
        "status": "CANDIDATE_ONLY_NOT_EXECUTABLE_LOCK",
        "input_zip_sha256": INPUT_SHA256,
        "portable_development_plan_sha256": PLAN_SHA256,
        "input_manifest_sha256_by_budget": input_hashes,
        "final_urbanev_szh_ids_each_budget": len(selected),
        "same_ids_all_budgets": True,
        "candidate_urban30_ids": 30,
        "candidate_rule": f"SHA256({SALT}|entity_id), ascending, first 30",
        "development_source_candidates": len(source_rows),
        "final_values_read": False,
        "charged_final_input_available_in_this_package": False,
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
