"""Select a Fixed lambda using only the completed, hash-bound calibration ledger."""

import argparse
import json
import math
from pathlib import Path

from ev_models.checkpoint import digest
from ev_search.fixed import FixedSearchConfig, expanded_upper, propose_lambda, sensitivity_design
from ev_search.ledger import FixedLedger, canonical


def select_fixed(ledger_root: Path, protocol_path: Path, search_config_path: Path) -> dict:
    protocol = json.loads(protocol_path.read_text())
    metadata = json.loads((ledger_root / "config.json").read_text())
    search_sha = digest(search_config_path)
    if protocol.get("status") != "locked_owner_approved" or not protocol.get("owner_authorization"):
        raise ValueError("Fixed selection needs locked authorized calibration protocol")
    binding = metadata["binding"]
    required = {
        "schema": "issue99-fixed-calibration-binding-v1",
        "protocol_sha256": digest(protocol_path),
        "fixed_search_config_sha256": search_sha,
        "calibration_study_template_sha256": protocol["calibration_study_template_sha256"],
        "code_commit": protocol["code_commit"],
        "input_manifest_sha256": protocol["input_manifest_sha256"],
        "source_population_sha256": protocol["source_population_sha256"],
        "sources": protocol["source_checkpoint_sha256"],
    }
    if search_sha != protocol["fixed_search_config_sha256"] or any(
        binding.get(key) != value for key, value in required.items()
    ):
        raise ValueError("Fixed calibration ledger/config/protocol hash binding differs")
    config = FixedSearchConfig(**json.loads(search_config_path.read_text()))
    ledger = FixedLedger(ledger_root, config, binding=binding, resume=True)
    completed = ledger.completed()
    if len(completed) < 1 + config.bo_trials:
        raise ValueError("Fixed calibration search budget incomplete")
    if (completed[0]["role"], completed[0]["lambda"]) != ("zero_baseline", 0.0):
        raise ValueError("Fixed calibration trial sequence differs from registered design")
    bo = completed[1 : 1 + config.bo_trials]
    expansions = [event for event in ledger.events if event["event"] == "domain_expansion"]
    upper = config.positive_upper
    expected_expansions = []
    previous_trials = []
    for event in bo:
        expected_weight, expected_role = propose_lambda(config, upper, previous_trials)
        if event["role"] != expected_role or not math.isclose(
            event["lambda"], expected_weight, rel_tol=1e-12, abs_tol=1e-12
        ):
            raise ValueError("Fixed BO trial sequence differs from registered design")
        previous_trials.append((event["lambda"], event["outcome"]["objective_mae_kwh"]))
        if event["status"] == "complete":
            finite_bo = [(weight, score) for weight, score in previous_trials if score is not None]
            expanded = expanded_upper(config, upper, len(expected_expansions), finite_bo)
            if expanded > upper:
                expected_expansions.append(
                    {"after_trial": event["trial"], "previous_upper": upper, "upper": expanded}
                )
                upper = expanded
    if [
        {key: event[key] for key in ("after_trial", "previous_upper", "upper")}
        for event in expansions
    ] != expected_expansions:
        raise ValueError("Fixed domain expansion sequence differs from registered design")
    attempted = [event["lambda"] for event in completed[: 1 + config.bo_trials]]
    expected_sensitivity = [
        weight
        for weight in sensitivity_design(config, upper)
        if all(not math.isclose(weight, old, rel_tol=1e-10, abs_tol=0) for old in attempted)
    ]
    tail = completed[1 + config.bo_trials :]
    if len(tail) < len(expected_sensitivity):
        raise ValueError("Fixed sensitivity budget incomplete")
    if len(tail) > len(expected_sensitivity) or any(
        event["role"] != "sensitivity"
        or not math.isclose(event["lambda"], weight, rel_tol=1e-12, abs_tol=1e-12)
        for event, weight in zip(tail, expected_sensitivity, strict=True)
    ):
        raise ValueError("Fixed sensitivity trial sequence differs from registered design")
    for event in completed:
        score = event["outcome"]["objective_mae_kwh"]
        if event["status"] not in {"complete", "null", "failed"} or (
            event["status"] == "complete"
        ) != (score is not None):
            raise ValueError("Fixed trial status/objective differs")
    tolerance = protocol["practical_equivalence_tolerance_kwh"]
    if (
        isinstance(tolerance, bool)
        or not isinstance(tolerance, (int, float))
        or not math.isfinite(tolerance)
        or tolerance < 0
    ):
        raise ValueError("Invalid registered practical-equivalence tolerance")
    finite = [
        (event["lambda"], event["outcome"]["objective_mae_kwh"], event["trial"])
        for event in completed
        if event["status"] == "complete"
    ]
    if not finite:
        raise ValueError("No finite calibration objective; cannot select Fixed lambda")
    best = min(score for _, score, _ in finite)
    selected = min((weight, trial) for weight, score, trial in finite if score <= best + tolerance)
    return {
        "schema": "issue99-fixed-selection-v1",
        "scope": "calibration_only_exploratory",
        "protocol_sha256": digest(protocol_path),
        "ledger_events_sha256": digest(ledger_root / "events.jsonl"),
        "ledger_chain_sha256": ledger.chain,
        "fixed_search_config_sha256": search_sha,
        "selected_fixed_lambda": selected[0],
        "selected_trial": selected[1],
        "best_calibration_mae_kwh": best,
        "practical_equivalence_tolerance_kwh": tolerance,
        "trials": [
            {
                "trial": event["trial"],
                "lambda": event["lambda"],
                "role": event["role"],
                "status": event["status"],
                "objective_mae_kwh": event["outcome"]["objective_mae_kwh"],
            }
            for event in completed
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--search-config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selection = select_fixed(args.ledger, args.protocol, args.search_config)
    with args.output.open("xb") as stream:
        stream.write(canonical(selection))


if __name__ == "__main__":
    main()
