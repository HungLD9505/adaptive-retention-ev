"""Build a deterministic metadata-only confirmation cohort before target execution."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from ev_models.checkpoint import digest
from tools.confirmation_run import validate_recipe

ROOT = Path(__file__).resolve().parents[1]
STUDY = "new-entity-confirmation-20261113-v1"


def select_entities(
    rows: list[dict], excluded: set[str], namespace: str, cap: int = 10
) -> list[dict]:
    """Hash-rank ready Development IDs using prefix metadata, never forecast errors."""
    eligible = []
    for row in rows:
        identity = row["identity"]
        if (
            "-".join(identity[:2]) != namespace
            or row["role"] != "development"
            or row["status"] != "ready"
            or row.get("initial_trainable", 0) < 1
            or identity[2] in excluded
        ):
            continue
        rank = hashlib.sha256(
            json.dumps([STUDY, namespace, identity[2]], separators=(",", ":")).encode()
        ).hexdigest()
        eligible.append(
            {
                "entity_id": identity[2],
                "rank_sha256": rank,
                "role": row["role"],
                "initial_trainable": row["initial_trainable"],
                "status": row["status"],
            }
        )
    return sorted(eligible, key=lambda row: (row["rank_sha256"], row["entity_id"]))[:cap]


def build(history: Path, input_parent: Path, historical_lock: Path, output: Path) -> dict:
    """Bind audited history, namespace checkpoints and an unchanged prospective objective."""
    if output.exists():
        raise FileExistsError("Never overwrite a confirmation lock")
    audit = json.loads((history / "audit.json").read_text())
    if audit["read_failures"] or audit["skipped"]:
        raise ValueError("Resolve skipped/unreadable recorded history before selecting a cohort")
    if digest(history / "exclusions.json") != audit["exclusions_sha256"]:
        raise ValueError("Exposure exclusion registry changed")
    references = json.loads((history / "exclusions.json").read_text())
    ambiguous = {r["entity_id"] for r in references if r["namespace"] == "*"}
    historical = json.loads(historical_lock.read_text())
    groups, unavailable, inventory = [], [], []
    for old in sorted(
        (g for g in historical["groups"] if g["history_days"] == 14), key=lambda g: g["namespace"]
    ):
        namespace = "-".join(old["namespace"])
        folder = input_parent / (namespace + "-14d")
        if digest(folder / "manifest.json") != old["input_manifest_sha256"]:
            raise ValueError("Prepared input identity differs from the fixed recipe's data")
        manifest = json.loads((folder / "manifest.json").read_text())
        if digest(folder / "entities.jsonl") != manifest["files"]["entities.jsonl"]["sha256"]:
            raise ValueError("Entity metadata fingerprint differs")
        rows = [json.loads(line) for line in (folder / "entities.jsonl").read_text().splitlines()]
        excluded = ambiguous | {r["entity_id"] for r in references if r["namespace"] == namespace}
        selected = select_entities(rows, excluded, namespace)
        count = len(select_entities(rows, excluded, namespace, cap=len(rows)))
        inventory.append(
            {"namespace": namespace, "eligible_unmatched_development": count, "selected": selected}
        )
        if not selected:
            unavailable.append(namespace)
            continue
        groups.append(
            {
                "namespace": namespace,
                "selected_ids": [r["entity_id"] for r in selected],
                "selected_metadata": selected,
                "deployment": manifest["config"]["deployment"],
                "input_manifest_sha256": old["input_manifest_sha256"],
                "entities_sha256": digest(folder / "entities.jsonl"),
                "source_population_sha256": old["source_population_sha256"],
                "sources": old["sources"],
            }
        )
    if not groups:
        raise ValueError("No eligible new entity remains under the audited exclusions")
    files = [
        p.relative_to(ROOT).as_posix()
        for folder in ("ev_inputs", "ev_models", "ev_control", "ev_runner")
        for p in sorted((ROOT / folder).glob("*.py"))
    ]
    files += [
        "tools/confirmation_run.py",
        "tools/confirmation_summary.py",
        "tools/confirmation_lock.py",
        "tools/data_use_history.py",
        "tools/issue99_stable_fast.py",
        "tools/issue99_study_support.py",
        "tools/issue99_confidence_readback.py",
    ]
    lock = {
        "schema": "new-entity-confirmation-lock-v1",
        "study_id": STUDY,
        "execution_authorized": True,
        "authorization": "2026-11-13: explicit instruction to audit prior use, lock a cohort and execute adaptive versus Fixed and static confirmation; no merge authorization.",
        "implementation_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "executed_code_sha256": {name: digest(ROOT / name) for name in files},
        "history_audit_sha256": digest(history / "audit.json"),
        "history_exclusions_sha256": digest(history / "exclusions.json"),
        "historical_recipe_lock_sha256": digest(historical_lock),
        "history_scope": "No prior execution/registered target declaration in 107 fetched refs and audited local run metadata; ambiguous IDs excluded globally. Preparation/catalogue metadata alone does not count as model execution. This is a recorded-use boundary, not universal absence of unrecorded/human inspection.",
        "selection": {
            "rule": "Lexicographic SHA256 of compact JSON [study_id, namespace, entity_id], then entity ID",
            "cap_per_namespace": 10,
            "when_fewer": "Use all eligible IDs",
            "future_outcomes_used": False,
            "replacement_after_execution": False,
        },
        "history_days": 14,
        "scheduled_days": 90,
        "seeds": [42, 43, 44],
        "recipe": {
            "initial_weight": 0.4307815378871372,
            "eta": 0.1,
            "share": 0.1,
            "stable_lambda": 1.0,
            "fast_lambda": 0.0,
            "fast_window_days": 7,
            "initial_epochs": 3,
            "online_epochs": 1,
            "learning_rate": 0.001,
            "batch_size": 64,
        },
        "evaluation": {
            "aggregate": "Equal-namespace mean of percentage MAE reduction, after equal seed and equal scored-entity means within each namespace",
            "comparators": ["fixed", "static"],
            "family_alpha": 0.05,
            "alpha_per_comparison": 0.025,
            "primary_block_days": 7,
            "block_days": [3, 7, 14],
            "resamples": 10000,
            "seed": 20261113,
            "primary_success": "No unscored selected target, and both primary lower percentage interval endpoints > 0. Report point estimates regardless; do not discard invalid replicates or switch to a favorable profile.",
            "missingness": "90 scheduled local dates; use only complete labels on matched origins. Keep null targets and no replacement. Any undefined bootstrap replicate makes that entire interval unavailable.",
        },
        "groups": groups,
        "unavailable_namespaces": unavailable,
        "metadata_inventory": inventory,
        "limits": [
            "New entity IDs relative to audited recorded uses; unrecorded remote/human exposure cannot be excluded",
            "Same historical dates, data releases and namespace-specific Source10 models; not new-city or future-period validation",
            "Development role is retained; no frozen Final gate is bypassed",
            "Dataset IDs do not certify physical-site uniqueness or cross-dataset alias freedom",
            "Some namespaces may have only one eligible entity; interval interpretation remains conditional and exploratory at that scale",
            "Expert forecasts are durably stored before labels; mixture forecasts are evaluated by offline causal feedback replay",
            "Percentile/Bonferroni intervals are approximate under selected cohorts, nonstationarity and circular calendar seams",
        ],
    }
    validate_recipe(lock)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        json.dump(lock, stream, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            {
                "groups": [
                    {"namespace": g["namespace"], "selected": len(g["selected_ids"])}
                    for g in groups
                ],
                "total_targets": sum(len(g["selected_ids"]) for g in groups),
                "target_seed_cells": 3 * sum(len(g["selected_ids"]) for g in groups),
                "protocol_sha256": digest(output),
            },
            indent=2,
        )
    )
    return lock


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--input-parent", type=Path, required=True)
    parser.add_argument("--historical-lock", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.history, args.input_parent, args.historical_lock, args.output)


if __name__ == "__main__":
    main()
