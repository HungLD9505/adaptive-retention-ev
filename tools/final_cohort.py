"""Declare the bounded, same-ID Final cohort using authenticated metadata only."""

import argparse
import hashlib
import json
from pathlib import Path

from ev_models.checkpoint import digest, write_json
from ev_models.data import InputRun

RULE = "issue23-bounded-final-same-ids-v1"
BUDGETS = (7, 14, 28)
NAMESPACES = (("urbanev", "SZH"),) + tuple(
    ("charged", city) for city in ("AMS", "JHB", "LOA", "MEL", "SPO", "SZH")
)


def select_shared_ids(
    groups: dict[int, list[dict]], namespace: tuple[str, str], count: int
) -> dict:
    """Reserve one empty-prefix case if available; hash-sample the positive remainder.

    Eligibility requires ready Final metadata in all three budgets. No future
    activity, forecast/label values, coverage or errors enter this selection.
    """
    if set(groups) != set(BUDGETS) or type(count) is not int or count < 1:
        raise ValueError("All three budgets and a positive integer count required")
    populations = {}
    for budget, rows in groups.items():
        ready = {}
        seen = set()
        for row in rows:
            identity = tuple(row["identity"])
            if len(identity) != 3 or identity[:2] != namespace or identity in seen:
                raise ValueError("Duplicate/wrong-namespace identity")
            seen.add(identity)
            if row["role"] != "final" or row["status"] != "ready":
                continue
            if type(row["initial_trainable"]) is not int or row["initial_trainable"] < 0:
                raise ValueError("Invalid prefix count")
            ready[identity[2]] = row["initial_trainable"]
        populations[budget] = ready
    shared = set.intersection(*(set(p) for p in populations.values()))
    empty = {entity for entity in shared if any(p[entity] == 0 for p in populations.values())}
    positive = shared - empty

    def rank(entity: str) -> tuple[str, str]:
        token = json.dumps([RULE, list(namespace), entity], separators=(",", ":"))
        return hashlib.sha256(token.encode()).hexdigest(), entity

    empty_quota = int(bool(empty))
    if len(shared) < count or len(positive) < count - empty_quota:
        raise ValueError("Insufficient shared eligible identities for declared stratum quotas")
    selected = (
        sorted(empty, key=rank)[:empty_quota] + sorted(positive, key=rank)[: count - empty_quota]
    )
    return {
        "shared_ready_population": len(shared),
        "shared_positive_all_budgets_population": len(positive),
        "shared_empty_any_budget_population": len(empty),
        "selected_ids": sorted(selected),
        "entities": [
            {
                "entity_id": entity,
                "identity_hash": rank(entity)[0],
                "stratum": "empty_in_at_least_one_budget"
                if entity in empty
                else "positive_all_budgets",
                "initial_trainable": {str(b): populations[b][entity] for b in BUDGETS},
            }
            for entity in sorted(selected)
        ],
    }


def prepare(inputs_root: Path, historical: Path, output: Path) -> dict:
    """Authenticate old manifest pins; write a new cohort without decoding Final values."""
    old = json.loads(historical.read_text())
    if old["entity_budget_pairs"] != 3510 or old["seeds"] != [42, 43, 44]:
        raise ValueError("Unexpected historical all-ready inventory")
    reference = {(tuple(g["namespace"]), g["history_days"]): g for g in old["groups"]}
    groups = []
    for namespace in NAMESPACES:
        data = {
            budget: InputRun(
                inputs_root / f"{'-'.join(namespace)}-{budget}d",
                reference[namespace, budget]["input_manifest_sha256"],
            )
            for budget in BUDGETS
        }
        if len({d.source_hash for d in data.values()}) != 1:
            raise ValueError("Budget Source populations differ")
        for budget, d in data.items():
            ref = reference[namespace, budget]
            if (
                d.namespace != namespace
                or d.config["history_days"] != budget
                or digest(d.root / "entities.jsonl") != ref["entities_sha256"]
                or d.source_hash != ref["source_population_sha256"]
            ):
                raise ValueError("Changed metadata/input identity")
        selection = select_shared_ids(
            {b: list(d.entities.values()) for b, d in data.items()},
            namespace,
            30 if namespace[0] == "urbanev" else 10,
        )
        groups.append(
            {
                "namespace": list(namespace),
                **selection,
                "budgets": {
                    str(b): {
                        "input_manifest_sha256": d.sha256,
                        "entities_sha256": digest(d.root / "entities.jsonl"),
                        "source_population_sha256": d.source_hash,
                        "clock_mode": d.clock,
                        "deployment": d.config["deployment"],
                    }
                    for b, d in data.items()
                },
            }
        )
    result = {
        "schema": "ev-final-bounded-cohort-v1",
        "scope": "Lead-approved bounded membership; immutable execution lock not approved",
        "selection_rule": RULE,
        "historical_all_ready_sha256": digest(historical),
        "seeds": [42, 43, 44],
        "history_budgets": list(BUDGETS),
        "replay_days": 90,
        "required_unique_variants": old["required_unique_variants"],
        "distinct_namespace_entity_ids": 90,
        "entity_budget_pairs": 270,
        "method_seed_cells": 11340,
        "execution_authorized": False,
        "groups": groups,
    }
    if sum(len(g["selected_ids"]) for g in groups) != 90:
        raise ValueError("Incomplete bounded scope")
    if output.exists():
        raise ValueError("Create a new cohort; do not overwrite historical declarations")
    write_json(output, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs-root", "historical", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    prepare(args.inputs_root, args.historical, args.output)


if __name__ == "__main__":
    main()
