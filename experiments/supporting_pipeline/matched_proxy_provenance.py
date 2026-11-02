"""Bind cell-specific Drift references and finite proxy calibration recipes."""

from __future__ import annotations

import json
from pathlib import Path

from experiments.supporting_pipeline import dispatch_matched as dispatch
from experiments.supporting_pipeline.controller import ControllerConfig
from experiments.supporting_pipeline.matched_plan_provenance import (
    pinned_file,
    pinned_json,
    require,
)
from experiments.supporting_pipeline.proxy_selection import ProxyConfig
from tools.hung_proxy_calibration import recipe as proxy_recipe
from tools.hung_proxy_calibration import select as proxy_select
from tools.hung_proxy_calibration import validate_profile


def verify_drift_config(config: dict, main: dict) -> None:
    """Require a cell-specific causal reference and otherwise matched settings."""
    require(
        config.get("schema") == "hung-sprint2-development-config-v1"
        and config.get("input_release") == main["input_release"]
        and config.get("seeds") == main["seeds"]
        and config.get("source") == main["source"]
        and config.get("target") == main["target"],
        "Drift config changes shared input/Source/target settings",
    )
    replay = config["replay"]
    allowed = {
        "selection_rule",
        "proxy_low",
        "proxy_high",
        "proxy_level_low",
        "proxy_level_mid",
        "proxy_level_high",
        "drift_reference_mean",
        "drift_reference_scale",
    }
    require(
        replay.get("selection_rule") == "drift"
        and {key: value for key, value in replay.items() if key not in allowed}
        == {key: value for key, value in main["replay"].items() if key not in allowed},
        "Drift config changes matched replay settings",
    )
    controller = ControllerConfig(
        levels=(0.0, replay["level_one"], replay["level_two"]),
        initial_level=replay["initial_level"],
        block_days=replay["block_days"],
        min_complete_days=replay["min_complete_days"],
        delta=replay["delta"],
        alpha=replay["alpha"],
        bootstrap_segment_days=replay["bootstrap_segment_days"],
        bootstrap_resamples=replay["bootstrap_resamples"],
        seed=7,
        challenger_rule=replay["challenger_rule"],
    )
    ProxyConfig(
        low=replay["proxy_low"],
        high=replay["proxy_high"],
        levels_by_bin=(
            replay["proxy_level_low"],
            replay["proxy_level_mid"],
            replay["proxy_level_high"],
        ),
        drift_reference_mean=replay["drift_reference_mean"],
        drift_reference_scale=replay["drift_reference_scale"],
    ).validate(controller, "drift")


def verify_proxy_selection(
    profile_spec: dict,
    selection_spec: dict,
    plan_spec: dict,
    runs_spec: dict,
    configs: dict,
) -> dict:
    """Bind all proxy threshold/mapping values to the provisional Development recipes."""
    profile = pinned_json(profile_spec)
    validate_profile(profile)
    selected = pinned_json(selection_spec)
    plan = pinned_json(plan_spec)
    runs_path = Path(pinned_file(runs_spec)["path"])
    require(
        plan.get("profile_sha256") == profile_spec["sha256"]
        and plan.get("profile") == profile
        and isinstance(plan.get("cells"), list)
        and len(plan["cells"]) == 9,
        "Proxy plan/profile evidence differs",
    )
    records = [json.loads(line) for line in runs_path.read_text(encoding="utf-8").splitlines()]
    expected = {
        (i, method, recipe)
        for i in range(9)
        for method in ("source_error", "uncertainty", "drift")
        for recipe in range(4)
    }
    observed = set()
    for record in records:
        require(
            isinstance(record, dict)
            and set(record) == {"cell_index", "method", "recipe", "run_path", "manifest_sha256"},
            "Proxy run evidence row fields differ",
        )
        key = (record["cell_index"], record["method"], record["recipe"])
        require(key in expected and key not in observed, "Missing/duplicate proxy run evidence")
        observed.add(key)
        run_path = dispatch.project_path(record["run_path"])
        dispatch.verify_file(run_path / "run_manifest.json", record["manifest_sha256"])
    require(observed == expected, "Proxy run evidence grid incomplete")
    require(
        selected.get("schema") == "hung-proxy-development-selection-v1"
        and selected.get("scope") == "conditional_development_selection_only; no Final lock"
        and selected.get("cells") == 9
        and selected.get("matrix_runs") == 108
        and selected.get("null_run_cells") == 0
        and selected.get("seeds") == [7, 11, 19]
        and set(selected.get("selection", {})) == {"source_error", "uncertainty", "drift"}
        and isinstance(selected.get("plan_sha256"), str)
        and len(selected["plan_sha256"]) == 64
        and isinstance(selected.get("runs_sha256"), str)
        and len(selected["runs_sha256"]) == 64
        and selected["plan_sha256"] == plan_spec["sha256"]
        and selected["runs_sha256"] == runs_spec["sha256"],
        "Proxy selection is incomplete or not provisional Development evidence",
    )
    verified = proxy_select(plan, records)
    require(
        {key: value for key, value in selected.items() if key not in {"plan_sha256", "runs_sha256"}}
        == verified,
        "Proxy selection differs from authenticated plan/run evidence",
    )
    choices = {}
    for name in ("source_error", "uncertainty", "drift"):
        index = selected["selection"][name]["provisional_recipe"]
        require(type(index) is int and 0 <= index < 4, "Proxy recipe index invalid")
        choices[name] = index
        expected = proxy_recipe(
            profile,
            name,
            index,
            {"drift_reference_mean": 0.0, "drift_reference_scale": 1.0},
        )
        values = expected["levels_by_bin"]
        if name != "drift":
            replay = configs[name]["replay"]
            require(
                replay["proxy_low"] == expected["low"]
                and replay["proxy_high"] == expected["high"]
                and [
                    replay["proxy_level_low"],
                    replay["proxy_level_mid"],
                    replay["proxy_level_high"],
                ]
                == values,
                f"Proxy config does not match selected recipe: {name}",
            )
    require(
        all(
            value
            == (
                configs["main"]["target"]["epsilon"]
                if key == "epsilon"
                else configs["main"]["replay"][key]
            )
            for key, value in profile["controller"].items()
        )
        and profile["max_origins"] == configs["main"]["replay"]["max_origins"],
        "Proxy profile and matched main schedule differ",
    )
    return {"selection": selected, "choices": choices, "profile": profile}
