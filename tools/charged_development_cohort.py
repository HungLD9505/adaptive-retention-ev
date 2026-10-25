"""Outcome-blind CHARGED supplementary Development cohort declaration."""

import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

from ev_evaluation.artifacts import authenticate_matrix
from ev_models.checkpoint import digest, write_json
from ev_models.data import InputRun
from ev_runner.run import runtime_code

CITIES = ("AMS", "JHB", "LOA", "MEL", "SPO", "SZH")
RULE = "three_prefix_count_rank_bins_hash_min_plus_one_empty_prefix_v1"


def choose_entities(
    rows: list[dict], namespace: tuple[str, str], manifest_sha: str, budget: int
) -> dict:
    """Select using allowed-prefix counts/identity only; never inspect energy/outcomes."""
    eligible = []
    seen = set()
    for row in rows:
        if row.get("role") != "development" or row.get("status") != "ready":
            continue
        identity = tuple(row["identity"])
        count = row["initial_trainable"]
        if identity[:2] != namespace or len(identity) != 3 or identity in seen:
            raise ValueError("Duplicate/wrong-namespace Development identity")
        if type(count) is not int or count < 0 or not isinstance(identity[2], str):
            raise ValueError("Invalid prefix count/entity identifier")
        seen.add(identity)
        token = json.dumps(
            [RULE, manifest_sha, list(namespace), budget, identity[2]], separators=(",", ":")
        )
        eligible.append(
            {
                "entity_id": identity[2],
                "initial_trainable": count,
                "identity_hash": hashlib.sha256(token.encode()).hexdigest(),
            }
        )
    positive = sorted(
        (r for r in eligible if r["initial_trainable"] > 0),
        key=lambda r: (r["initial_trainable"], r["identity_hash"]),
    )
    empty = [r for r in eligible if r["initial_trainable"] == 0]
    selected = []
    for index, label in enumerate(
        ("lower_prefix_count_rank", "middle_prefix_count_rank", "upper_prefix_count_rank")
    ):
        group = positive[index * len(positive) // 3 : (index + 1) * len(positive) // 3]
        if group:
            selected.append(
                {**min(group, key=lambda r: r["identity_hash"]), "selection_stratum": label}
            )
    if empty:
        selected.append(
            {
                **min(empty, key=lambda r: r["identity_hash"]),
                "selection_stratum": "no_initial_trainable",
            }
        )
    if not selected:
        raise ValueError("No ready Development targets; do not silently drop this city/budget")
    return {
        "manifest_sha256": manifest_sha,
        "ready_development_population": len(eligible),
        "positive_prefix_population": len(positive),
        "empty_prefix_population": len(empty),
        "entities": selected,
    }


def run(args: argparse.Namespace) -> None:
    started = time.perf_counter()
    code = runtime_code()
    if code["dirty"]:
        raise ValueError("Commit the outcome-blind rule before inspecting real metadata")
    reference = authenticate_matrix(args.reference_matrix, args.verification)
    fingerprints = {}
    for row in reference["runs"]:
        b = row["binding"]["input"]
        if b["dataset_id"] != "charged" or b["city_id"] not in CITIES:
            raise ValueError("Only six separate CHARGED namespaces permitted")
        key = b["city_id"], b["history_days"]
        sha = b["input_manifest_sha256"]
        if key in fingerprints and fingerprints[key] != sha:
            raise ValueError("Inconsistent smoke input fingerprints")
        fingerprints[key] = sha
    if set(fingerprints) != {(city, budget) for city in CITIES for budget in (7, 14, 28)}:
        raise ValueError("All six cities and history budgets required")
    cohorts = {}
    for city in CITIES:
        groups, sources, clocks, starts = {}, set(), set(), set()
        for budget in (7, 14, 28):
            data = InputRun(
                args.inputs_root / f"charged-{city}-{budget}d", fingerprints[city, budget]
            )
            if (
                data.namespace != ("charged", city)
                or data.config["history_days"] != budget
                or data.clock != "publisher-local-naive"
            ):
                raise ValueError("Changed CHARGED namespace/budget/publisher clock")
            groups[str(budget)] = choose_entities(
                list(data.entities.values()), data.namespace, data.sha256, budget
            )
            sources.add(data.source_hash)
            clocks.add(data.clock)
            starts.add(data.config["deployment"])
        if len(sources) != 1 or len(clocks) != 1 or len(starts) != 1:
            raise ValueError("Budget Source populations/deployment/clock differ")
        cohorts[city] = {
            "namespace": f"charged-{city}",
            "seeds": [42, 43, 44],
            "days": 90,
            "state_retention": "latest",
            "selection_rule": RULE,
            "budgets": groups,
            "source_population_sha256": next(iter(sources)),
            "clock_mode": next(iter(clocks)),
            "deployment": next(iter(starts)),
            "scope": "Small supplementary Development cohort; no Final or population-effectiveness claim. SZH analyzed separately for possible UrbanEV overlap.",
        }
    args.output.mkdir(parents=True, exist_ok=False)
    for city, cohort in cohorts.items():
        write_json(args.output / f"charged-{city}.json", cohort)
    write_json(
        args.output / "inventory.json",
        {
            "scope": "Pre-execution CHARGED supplementary Development identities only",
            "run_id": args.output.name,
            "code": code,
            "python": platform.python_version(),
            "wall_seconds": time.perf_counter() - started,
            "reference_matrix_sha256": digest(args.reference_matrix),
            "verification_sha256": digest(args.verification),
            "selection_rule": RULE,
            "cities": {
                city: {
                    "cohort_sha256": digest(args.output / f"charged-{city}.json"),
                    "entity_budget_combinations": sum(
                        len(g["entities"]) for g in c["budgets"].values()
                    ),
                }
                for city, c in cohorts.items()
            },
            "limits": "Prefix-count rank bins may tie; identity hashes break ties before outcomes. No full-release zero/activity filter, city pooling, UTC reinterpretation, implementation copying or Final selection.",
        },
    )
    print(json.dumps({"status": "declared", "cities": list(cohorts), "training_performed": False}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs-root", "reference-matrix", "verification", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
