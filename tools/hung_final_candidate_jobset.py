"""Build a non-executable Hùng Final candidate from pinned metadata and Development configs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from zipfile import ZipFile

from tools.hung_final_metadata_preflight import INPUT_SHA256, PLAN_SHA256

ROOT = Path(__file__).resolve().parents[1]
ENTITY_CSV_SHA256 = "512cd9f036832bb5502deb5bed3cda3df5cd1ef0e98023ba97724e8d531a10b7"
SOURCE_CSV_SHA256 = "05035160f3fef3cf58ebdb9f70deec0475ddd8e0d1f2dd55ee6ec6c87b29302f"
IDS = 3
BUDGETS = (7, 14, 28)
SEEDS = (7, 11, 19)
VARIANTS = (
    "main",
    "target_only",
    "frozen_source",
    "full_finetuning",
    "fixed_retention",
    "online_best_lambda",
    "source_error",
    "uncertainty",
    "drift",
    "parameter_retention",
    "block7",
    "block28",
    "no_source",
    "seasonal_naive",
)
CONFIG_NAMES = {
    "main": "main",
    "target_only": "main",
    "frozen_source": "main",
    "full_finetuning": "full_finetuning",
    "fixed_retention": "fixed_retention",
    "online_best_lambda": "online_best",
    "source_error": "source_error",
    "uncertainty": "uncertainty",
    "drift": "drift_consensus",
    "parameter_retention": "parameter_retention",
    "block7": "block7",
    "block28": "block28",
    "no_source": "no_source",
    "seasonal_naive": "main",
}
METHODS = {
    variant: (
        "confidence"
        if variant in {"main", "block7", "block28", "no_source", "parameter_retention"}
        else variant
    )
    for variant in VARIANTS
}
CONTROLLER = set(VARIANTS) - {"target_only", "frozen_source", "seasonal_naive"}
CATEGORIES = {
    "main": ["main"],
    "target_only": ["baseline:target_only"],
    "frozen_source": ["baseline:frozen_source"],
    "full_finetuning": ["baseline:full_finetuning"],
    "fixed_retention": ["baseline:fixed_retention", "ablation:fixed_lambda"],
    "online_best_lambda": ["baseline:online_best_lambda", "ablation:without_confidence"],
    "source_error": ["baseline:source_error"],
    "uncertainty": ["baseline:uncertainty"],
    "drift": ["baseline:drift"],
    "parameter_retention": ["ablation:parameter_retention"],
    "block7": ["ablation:different_block_size"],
    "block28": ["ablation:different_block_size"],
    "no_source": ["ablation:without_source_initialization"],
    "seasonal_naive": ["baseline:seasonal_naive"],
}


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def pinned_csv(path: Path, digest: str) -> list[dict]:
    if sha(path) != digest:
        raise ValueError(f"Pinned CSV SHA differs: {path}")
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def configs(payload: Path, plan: dict) -> tuple[dict[str, dict], list[dict]]:
    by_id = {row["id"]: row for row in plan["configs"]}
    values = {}
    bindings = []
    for name in sorted(set(CONFIG_NAMES.values()) - {"drift_consensus"}):
        spec = by_id[name]
        path = (payload / spec["path"]).resolve()
        if not path.is_relative_to(payload.resolve()) or sha(path) != spec["sha256"]:
            raise ValueError(f"Development config SHA differs: {name}")
        values[name] = json.loads(path.read_bytes())
        bindings.append({"id": name, "sha256": spec["sha256"], "path": spec["path"]})
    drift_specs = sorted(
        (spec for name, spec in by_id.items() if name.startswith("drift_")),
        key=lambda spec: spec["id"],
    )
    if len(drift_specs) != 69:
        raise ValueError("Expected 69 pinned Development drift configs")
    consensus = None
    for spec in drift_specs:
        path = (payload / spec["path"]).resolve()
        if not path.is_relative_to(payload.resolve()) or sha(path) != spec["sha256"]:
            raise ValueError(f"Development Drift config SHA differs: {spec['id']}")
        value = json.loads(path.read_bytes())
        replay = dict(value["replay"])
        replay.pop("drift_reference_mean")
        replay.pop("drift_reference_scale")
        candidate = {**value, "replay": replay}
        if consensus is None:
            consensus = candidate
        elif candidate != consensus:
            raise ValueError("Development Drift policy differs across cells")
        bindings.append({"id": spec["id"], "sha256": spec["sha256"], "path": spec["path"]})
    values["drift_consensus"] = consensus
    if values["online_best"]["replay"]["delta"] != 0:
        raise ValueError("Without-confidence alias requires zero delta")
    return values, bindings


def metadata(input_zip: Path, ids: list[str]) -> tuple[dict, dict]:
    if sha(input_zip) != INPUT_SHA256:
        raise ValueError("Frozen input ZIP SHA differs")
    rows = {}
    manifests = {}
    with ZipFile(input_zip) as archive:
        for budget in BUDGETS:
            prefix = f"data/inputs/issue18-input-handoff-v1-20261019/urbanev-SZH-{budget}d/"
            manifest_bytes = archive.read(prefix + "manifest.json")
            manifests[budget] = hashlib.sha256(manifest_bytes).hexdigest()
            found = {}
            for line in archive.read(prefix + "entities.jsonl").splitlines():
                item = json.loads(line)
                if item["role"] == "final" and item["identity"][2] in ids:
                    entity = item["identity"][2]
                    if entity in found or item["history_days"] != budget:
                        raise ValueError("Duplicate/mismatched Final entity metadata")
                    found[entity] = item
            if set(found) != set(ids):
                raise ValueError("Candidate ID absent from Final role")
            rows[budget] = found
    return rows, manifests


def target_init(variant: str, config: dict, cell: dict, common: dict) -> dict | None:
    if variant in {"frozen_source", "seasonal_naive"}:
        return None
    target = config["target"]
    if variant == "target_only":
        return {
            **{
                key: common[key]
                for key in ("input_run", "manifest_sha256", "entity_id", "seed", "device")
            },
            "calendar_hidden": config["source"]["calendar_hidden"],
            "learning_rate": target["learning_rate"],
            "batch_size": target["batch_size"],
            "steps": math.ceil(cell["initial_trainable"] / target["batch_size"]),
        }
    return {
        **common,
        "steps": max(1, math.ceil(cell["initial_trainable"] / target["batch_size"])),
        "batch_size": target["batch_size"],
        "learning_rate": target["learning_rate"],
        "retention_weight": target["retention_weight"],
        "retention_kind": target.get("retention_kind", "latent"),
        "initialization_kind": target.get("initialization_kind", "source"),
        "epsilon": target["epsilon"],
    }


def replay_args(variant: str, config: dict, common: dict) -> dict:
    base = {
        "input_run": common["input_run"],
        "manifest_sha256": common["manifest_sha256"],
        "entity_id": common["entity_id"],
        "seed": common["seed"],
        "device": common["device"],
        "max_origins": 90,
        "resume_checkpoint": None,
    }
    if variant not in CONTROLLER:
        base.update(
            method=METHODS[variant],
            block_days=config["replay"]["block_days"],
            initial_checkpoint=None,
            source_input_run=common.get("source_input_run") if variant == "frozen_source" else None,
            source_manifest_sha256=common.get("source_manifest_sha256")
            if variant == "frozen_source"
            else None,
            source_checkpoint=common.get("source_checkpoint")
            if variant == "frozen_source"
            else None,
        )
        return base
    replay = {
        key: value
        for key, value in config["replay"].items()
        if key != "missing_day_bootstrap_policy"
    }
    base.update(replay)
    base.update(
        source_input_run=common["source_input_run"],
        source_manifest_sha256=common["source_manifest_sha256"],
        source_checkpoint=common["source_checkpoint"],
        target_checkpoint=None,
        epsilon=config["target"]["epsilon"],
        retention_kind=config["target"].get("retention_kind", "latent"),
        initialization_kind=config["target"].get("initialization_kind", "source"),
        selection_rule=METHODS[variant],
    )
    for key in (
        "proxy_low",
        "proxy_high",
        "proxy_level_low",
        "proxy_level_mid",
        "proxy_level_high",
        "drift_reference_mean",
        "drift_reference_scale",
    ):
        base.setdefault(key, None)
    return base


def build(root: Path) -> tuple[dict, dict, dict, list[dict], dict]:
    report = root / "docs/reports/hung-final-metadata-preflight-20261029-v1"
    ranked = pinned_csv(report / "urban_final_entity_metadata.csv", ENTITY_CSV_SHA256)
    ids = [row["entity_id"] for row in ranked[:IDS]]
    if len(ids) != IDS or len(set(ids)) != IDS:
        raise ValueError("Candidate IDs are not unique")
    sources = pinned_csv(report / "development_source_candidates.csv", SOURCE_CSV_SHA256)
    source_by_cell = {(int(row["budget_days"]), int(row["seed"])): row for row in sources}
    payload = root / ".cache/kaggle-payload-v2/payload"
    plan_path = payload / "portable-plan.json"
    if sha(plan_path) != PLAN_SHA256:
        raise ValueError("Development portable plan SHA differs")
    plan = json.loads(plan_path.read_bytes())
    config_values, bindings = configs(payload, plan)
    entity_metadata, input_hashes = metadata(payload / "inputs.zip", ids)
    jobs = []
    planned = []
    missing = []
    for entity in ids:
        for budget in BUDGETS:
            cell = entity_metadata[budget][entity]
            if cell["scheduled_forecasts"] != 90:
                raise ValueError("Candidate has a non-90-origin metadata schedule")
            input_run = f"data/inputs/issue18-input-handoff-v1-20261019/urbanev-SZH-{budget}d"
            for seed in SEEDS:
                source = source_by_cell[budget, seed]
                if source["input_manifest_sha256"] != input_hashes[budget]:
                    raise ValueError("Development Source/input manifest differs")
                for variant in VARIANTS:
                    if variant == "seasonal_naive" and seed != 7:
                        continue
                    method = METHODS[variant]
                    config = config_values[CONFIG_NAMES[variant]]
                    source_required = variant not in {"target_only", "seasonal_naive"}
                    job_id = f"hung_final_candidate_v1_{variant}_b{budget}s{seed}e{entity}"
                    common = {
                        "input_run": input_run,
                        "manifest_sha256": input_hashes[budget],
                        "entity_id": entity,
                        "seed": seed,
                        "device": "cpu" if variant == "seasonal_naive" else "cuda",
                    }
                    if source_required:
                        common.update(
                            source_input_run=input_run,
                            source_manifest_sha256=input_hashes[budget],
                            source_checkpoint=source["source_checkpoint_path"],
                        )
                    jobs.append(
                        {
                            "job_id": job_id,
                            "variant": variant,
                            "entity_id": entity,
                            "dataset_id": "urbanev",
                            "city_id": "SZH",
                            "budget_days": budget,
                            "seed": seed,
                            "method": method,
                            "input_run": input_run,
                            "input_manifest_sha256": input_hashes[budget],
                            "source_checkpoint_sha256": source["source_checkpoint_sha256"]
                            if source_required
                            else None,
                            "target_checkpoint_sha256": None,
                        }
                    )
                    replay = replay_args(variant, config, common)
                    planned.append(
                        {
                            "job_id": job_id,
                            "variant": variant,
                            "method": method,
                            "target_init": target_init(variant, config, cell, common),
                            "replay": replay,
                        }
                    )
                    if variant == "drift":
                        missing.append(
                            {
                                "job_id": job_id,
                                "fields": [
                                    "replay.drift_reference_mean",
                                    "replay.drift_reference_scale",
                                ],
                                "reason": "Requires lock-pinned causal first-history derivation after Final input access",
                            }
                        )
    jobs.sort(key=lambda row: row["job_id"])
    planned.sort(key=lambda row: row["job_id"])
    if len(jobs) != 360 or [row["job_id"] for row in jobs] != [row["job_id"] for row in planned]:
        raise ValueError("Candidate must have exact 360 sorted job identities")
    coverage = {
        "selected_entities": sorted(
            [{"dataset_id": "urbanev", "city_id": "SZH", "entity_id": entity} for entity in ids],
            key=lambda row: (row["dataset_id"], row["city_id"], row["entity_id"]),
        ),
        "budgets": list(BUDGETS),
        "seeds": list(SEEDS),
        "variants": sorted(VARIANTS),
        "variant_categories": {variant: CATEGORIES[variant] for variant in sorted(VARIANTS)},
        "variant_seed_policy": {
            variant: (
                {"deterministic_representative_seed": 7, "alias_seeds": [11, 19]}
                if variant == "seasonal_naive"
                else "all_seeds"
            )
            for variant in sorted(VARIANTS)
        },
        "replay_origins": 90,
        "expected_jobs": 360,
        "missing_cells": [],
        "declared_shortfalls": [
            "370 of 373 Final-role UrbanEV/SZH IDs outside this bounded first-three-ID candidate",
            "Six CHARGED city input/Source/jobset identities are unavailable in the repo-local package",
        ],
    }
    return (
        {"schema": "hung-final-jobset-v1", "jobs": jobs},
        {"schema": "hung-final-execution-plan-v1", "jobs": planned},
        coverage,
        missing,
        {
            "config_bindings": bindings,
            "input_zip_sha256": INPUT_SHA256,
            "portable_plan_sha256": PLAN_SHA256,
            "selected_entity_ids_hash_ranked": ids,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output_dir.resolve()
    if not output.is_relative_to(root) or output.exists():
        raise ValueError("Output must be a new directory inside repository")
    jobset, plan, coverage, missing, bindings = build(root)
    output.mkdir(parents=True, exist_ok=False)
    for name, value in (
        ("candidate_jobset.json", jobset),
        ("candidate_execution_plan.json", plan),
        ("candidate_coverage.json", coverage),
        ("missing_stage_args.json", missing),
        ("source_config_bindings.json", bindings),
    ):
        (output / name).write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
    print(json.dumps({"candidate_jobs": len(jobset["jobs"]), "missing_drift_jobs": len(missing)}))


if __name__ == "__main__":
    main()
