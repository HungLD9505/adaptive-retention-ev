"""Fit descriptive sparse/dense thresholds from authenticated Development metadata."""

import argparse
import json
from pathlib import Path

from ev_evaluation.contexts import fit_density_context
from ev_models.checkpoint import digest, write_json
from ev_runner.run import runtime_code


def fit(root: Path) -> dict:
    code = runtime_code()
    if code["dirty"]:
        raise ValueError("Clean committed context-definition code required")
    groups, seen = [], set()
    for path in sorted(root.glob("*/manifest.json")):
        manifest = json.loads(path.read_text())
        if manifest["schema"] != "ev-loader-run-v2" or manifest["status"] not in {
            "technical_success",
            "technical_success_with_coverage_limits",
        }:
            raise ValueError("Accepted model-input manifest required")
        config = manifest["config"]
        key = config["dataset_id"], config["city_id"], config["history_days"]
        if key in seen:
            raise ValueError("Duplicate namespace/budget input")
        seen.add(key)
        entities = path.parent / "entities.jsonl"
        fingerprint = manifest["files"][entities.name]
        if (
            entities.stat().st_size != fingerprint["size_bytes"]
            or digest(entities) != fingerprint["sha256"]
        ):
            raise ValueError("Changed prefix metadata fingerprint")
        result = fit_density_context(
            [json.loads(line) for line in entities.read_text().splitlines()],
            (config["dataset_id"], config["city_id"]),
            config["history_days"],
            config["deployment"],
        )
        result.update(manifest_sha256=digest(path), entities_sha256=digest(entities))
        groups.append(result)
    if not groups:
        raise ValueError("No accepted namespace/budget manifests")
    return {
        "scope": "Descriptive Development-only grouping proposal; not a Final lock, controller input, cohort exclusion or behavior truth",
        "policy": "prefix-positive-valid-hour-fraction-development-median-v1",
        "rule": "One eligible Development entity vote per namespace/budget; sparse strictly below median, dense includes ties; zero valid hours undefined",
        "limitations": "Missing hours excluded from denominator and reported separately; publisher-imputed values may count as valid; groups describe positive-energy frequency, not physical occupancy or energy magnitude. Budget/namespace thresholds differ. No forecast outcomes used.",
        "code": code,
        "groups": groups,
    }


def authenticate_contexts(path: Path, checksum: str, root: Path) -> dict:
    """Recompute groups from current authenticated metadata, accepting namespace subsets."""
    if digest(path) != checksum:
        raise ValueError("Changed identified density-context output")
    recorded, current = json.loads(path.read_text()), fit(root)
    if recorded["policy"] != current["policy"] or recorded["rule"] != current["rule"]:
        raise ValueError("Changed density definition")
    stored = {}
    for group in recorded["groups"]:
        key = (*group["namespace"], group["history_days"])
        if key in stored:
            raise ValueError("Duplicate calibrated density group")
        stored[key] = group
    result = {}
    for group in current["groups"]:
        key = (*group["namespace"], group["history_days"])
        if stored.get(key) != group:
            raise ValueError("Density groups differ from authenticated allowed-prefix metadata")
        result[key] = group
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Use a new context output")
    result = fit(args.inputs_root)
    write_json(args.output, result)
    print(
        json.dumps(
            {"status": "fitted_from_development_prefix_metadata", "groups": len(result["groups"])}
        )
    )


if __name__ == "__main__":
    main()
