"""Predeclare Development entities from accepted metadata, without scores."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from experiments.hung_sprint2.cli import _load_run, _records

SEEDS = (7, 11, 19)
SELECTION_SCHEMA = "hung-sprint2-development-selection-v1"


def _rank(manifest_sha256: str, identity: list[str]) -> str:
    value = json.dumps([manifest_sha256, identity], separators=(",", ":"))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def select_development(runs: list[tuple[Path, str]]) -> dict:
    """Select a fixed metadata-only verification and representative set."""
    if len(runs) != 3:
        raise ValueError("Exactly the 7/14/28-day input runs are required")
    budgets: dict[int, dict] = {}
    for path, manifest_sha256 in runs:
        manifest = _load_run(path, manifest_sha256)
        budget = manifest["config"]["history_days"]
        if budget in budgets:
            raise ValueError("Duplicate input budget")
        identity_prefix = [manifest["config"]["dataset_id"], manifest["config"]["city_id"]]
        eligible = []
        for row in _records(path / "entities.jsonl"):
            if row.get("role") != "development":
                continue
            if row.get("identity", [])[:2] != identity_prefix:
                raise ValueError("Entity profile differs from verified input manifest")
            if row.get("initialization") not in {
                "target_initial_adaptation",
                "source_checkpoint_only",
            }:
                continue
            count = row.get("initial_trainable")
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError("Development entity lacks valid initial_trainable count")
            if (row["initialization"] == "source_checkpoint_only") != (count == 0):
                raise ValueError("Initialization/count mismatch")
            eligible.append(
                {
                    "entity_id": row["identity"][2],
                    "initialization": row["initialization"],
                    "initial_trainable": count,
                    "rank": _rank(manifest_sha256, row["identity"]),
                }
            )
        if len({row["entity_id"] for row in eligible}) != len(eligible):
            raise ValueError("Duplicate Development entity")
        adaptation = sorted(
            (row for row in eligible if row["initialization"] == "target_initial_adaptation"),
            key=lambda row: (row["initial_trainable"], row["entity_id"]),
        )
        checkpoint_only = sorted(
            (row for row in eligible if row["initialization"] == "source_checkpoint_only"),
            key=lambda row: row["rank"],
        )
        groups = [[] for _ in range(3)]
        unique_counts = sorted({row["initial_trainable"] for row in adaptation})
        count_group = {
            count: min(2, 3 * index // len(unique_counts))
            for index, count in enumerate(unique_counts)
        }
        for row in adaptation:
            groups[count_group[row["initial_trainable"]]].append(row)
        selected_adaptation = []
        for group in groups:
            selected_adaptation.extend(sorted(group, key=lambda row: row["rank"])[:2])
        selected = selected_adaptation + checkpoint_only[:3]
        verification = []
        if selected_adaptation:
            verification.append(min(selected_adaptation, key=lambda row: row["rank"])["entity_id"])
        if checkpoint_only:
            verification.append(checkpoint_only[0]["entity_id"])
        budgets[budget] = {
            "input_run_id": manifest["run_id"],
            "input_profile": identity_prefix,
            "manifest_sha256": manifest_sha256,
            "eligible_counts": {
                "adaptation": len(adaptation),
                "source_checkpoint_only": len(checkpoint_only),
            },
            "adaptation_group_sizes": [len(group) for group in groups],
            "verification_entity_ids": verification,
            "representative_entities": selected,
        }
    if set(budgets) != {7, 14, 28}:
        raise ValueError("Input budgets must be 7, 14 and 28 days")
    return {
        "schema": SELECTION_SCHEMA,
        "status": "predeclared; no training or scoring performed",
        "selection_rule": "initial_trainable unique-count tertiles, then SHA-256(manifest SHA, identity); empty groups stay empty",
        "seeds": list(SEEDS),
        "minimum_origins_for_two_14_day_boundaries": 42,
        "budgets": {str(key): budgets[key] for key in sorted(budgets)},
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    for budget in (7, 14, 28):
        parser.add_argument(f"--run-{budget}", type=Path, required=True)
        parser.add_argument(f"--sha-{budget}", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    runs = [
        (getattr(args, f"run_{budget}"), getattr(args, f"sha_{budget}")) for budget in (7, 14, 28)
    ]
    result = select_development(runs)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
