"""Validate pinned configuration, lambda and checkpoint provenance for matched plans."""

from __future__ import annotations

import json
import math
from pathlib import Path

from experiments.hung_sprint2 import dispatch_matched as dispatch
from experiments.hung_sprint2.controller import ControllerConfig
from experiments.hung_sprint2.proxy_selection import ProxyConfig

CONFIG_NAMES = (
    "main",
    "online_best",
    "without_confidence",
    "fixed_retention",
    "full_finetuning",
    "source_error",
    "uncertainty",
    "parameter_retention",
    "block7",
    "block28",
    "no_source",
)
TARGET_NAMES = ("main", "fixed_retention", "full_finetuning", "parameter_retention", "no_source")
BASELINE_METHODS = (
    ("online_best", "online_best_lambda"),
    ("fixed_retention", "fixed_retention"),
    ("full_finetuning", "full_finetuning"),
    ("source_error", "source_error"),
    ("uncertainty", "uncertainty"),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def pinned_json(spec: dict) -> dict:
    require(isinstance(spec, dict) and set(spec) == {"path", "sha256"}, "Pinned JSON required")
    path = dispatch.project_path(spec["path"])
    return dispatch.read_verified_json(path, spec["sha256"])


def pinned_file(spec: dict) -> dict:
    require(isinstance(spec, dict) and set(spec) == {"path", "sha256"}, "Pinned file required")
    path = dispatch.project_path(spec["path"])
    dispatch.verify_file(path, spec["sha256"])
    return {"path": str(path), "sha256": spec["sha256"]}


def pinned_checkpoint(spec: dict) -> dict:
    require(
        isinstance(spec, dict) and set(spec) == {"path", "sha256", "run_manifest_sha256"},
        "Checkpoint and run-manifest pins required",
    )
    checkpoint = pinned_file({"path": spec["path"], "sha256": spec["sha256"]})
    dispatch.verify_file(
        Path(checkpoint["path"]).parent / "run_manifest.json", spec["run_manifest_sha256"]
    )
    return {**checkpoint, "run_manifest_sha256": spec["run_manifest_sha256"]}


def cell_id(budget: int, seed: int, entity_id: str) -> str:
    require(entity_id.isalnum(), "Entity ID must be alphanumeric")
    return f"b{budget}s{seed}e{entity_id}"


def comparable_configs(configs: dict[str, dict]) -> None:
    main = configs["main"]
    main_target = {
        k: v
        for k, v in main["target"].items()
        if k not in {"retention_weight", "retention_kind", "initialization_kind"}
    }
    ignored_replay = {
        "selection_rule",
        "delta",
        "initial_level",
        "level_one",
        "level_two",
        "block_days",
        "retention_kind",
        "initialization_kind",
        "proxy_low",
        "proxy_high",
        "proxy_level_low",
        "proxy_level_mid",
        "proxy_level_high",
        "drift_reference_mean",
        "drift_reference_scale",
    }
    main_replay = {k: v for k, v in main["replay"].items() if k not in ignored_replay}
    for name, config in configs.items():
        require(config.get("schema") == "hung-sprint2-development-config-v1", f"Bad config {name}")
        require(
            config.get("input_release") == main["input_release"], f"Input release differs: {name}"
        )
        require(config.get("seeds") == main["seeds"], f"Seed grid differs: {name}")
        require(config.get("source") == main["source"], f"Source schedule differs: {name}")
        target = {
            k: v
            for k, v in config["target"].items()
            if k not in {"retention_weight", "retention_kind", "initialization_kind"}
        }
        replay = {k: v for k, v in config["replay"].items() if k not in ignored_replay}
        require(
            target == main_target and replay == main_replay, f"Matched schedule differs: {name}"
        )
        expected_rule = {
            "main": "confidence",
            "parameter_retention": "confidence",
            "block7": "confidence",
            "block28": "confidence",
            "no_source": "confidence",
            "online_best": "online_best_lambda",
        }.get(name, name)
        require(
            config["replay"].get("selection_rule", "confidence") == expected_rule,
            f"Selection rule differs: {name}",
        )
    for name, block in (("block7", 7), ("block28", 28)):
        left = {
            **configs[name],
            "status": main.get("status"),
            "replay": {**configs[name]["replay"], "block_days": main["replay"]["block_days"]},
        }
        require(
            left == main and configs[name]["replay"]["block_days"] == block,
            f"Block variant changes more than block_days: {name}",
        )
    require(main["replay"]["block_days"] == 14, "Main block must be 14 days")
    no_source = configs["no_source"]
    no_source_target = {**no_source["target"]}
    no_source_replay = {**no_source["replay"]}
    for section, original in (
        (no_source_target, main["target"]),
        (no_source_replay, main["replay"]),
    ):
        if "initialization_kind" in original:
            section["initialization_kind"] = original["initialization_kind"]
        else:
            section.pop("initialization_kind", None)
    require(
        no_source["target"].get("initialization_kind")
        == no_source["replay"].get("initialization_kind")
        == "random_target"
        and {
            **no_source,
            "status": main.get("status"),
            "target": no_source_target,
            "replay": no_source_replay,
        }
        == main,
        "No-source config must change only initialization kind",
    )
    parameter = configs["parameter_retention"]
    parameter_target = {
        **parameter["target"],
        "retention_weight": main["target"]["retention_weight"],
    }
    parameter_replay = {
        **parameter["replay"],
        **{key: main["replay"][key] for key in ("initial_level", "level_one", "level_two")},
    }
    for section, original in (
        (parameter_target, main["target"]),
        (parameter_replay, main["replay"]),
    ):
        if "retention_kind" in original:
            section["retention_kind"] = original["retention_kind"]
        else:
            section.pop("retention_kind", None)
    require(
        {
            **parameter,
            "status": main.get("status"),
            "target": parameter_target,
            "replay": parameter_replay,
        }
        == main,
        "Parameter config changes more than retention kind/lambda",
    )
    without = configs["without_confidence"]
    online = configs["online_best"]
    comparable = {
        **without,
        "status": online.get("status"),
        "replay": {
            **without["replay"],
            "selection_rule": "online_best_lambda",
            "delta": online["replay"].get("delta", 0),
        },
    }
    require(comparable == online, "Without Confidence differs from Online Best beyond rule/delta")
    require(online["replay"].get("delta", 0) == 0, "Online Best requires delta=0")
    require(without["replay"]["delta"] >= 0, "Without Confidence delta must be nonnegative")
    for name in ("source_error", "uncertainty"):
        replay = configs[name]["replay"]
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
            drift_reference_mean=replay.get("drift_reference_mean"),
            drift_reference_scale=replay.get("drift_reference_scale"),
        ).validate(controller, name)


def verify_lambda(spec: dict, config: dict, selection_sha256: str) -> float:
    require(
        isinstance(spec, dict) and set(spec) == {"selection", "chosen_lambda_low"},
        "Chosen lambda pin required",
    )
    selected = pinned_json(spec["selection"])
    value = spec["chosen_lambda_low"]
    require(
        selected.get("schema") == "hung-parameter-lambda-development-selection-v1"
        and selected.get("scope")
        == "UrbanEV SZH Development target_initial_adaptation only; no Final lock"
        and set(selected)
        == {
            "schema",
            "scope",
            "rule",
            "preflight_sha256",
            "selection_sha256",
            "chosen_index",
            "chosen_lambda_low",
            "ranking",
            "cells",
        }
        and all(
            isinstance(selected[key], str) and len(selected[key]) == 64
            for key in ("preflight_sha256", "selection_sha256")
        )
        and type(selected["chosen_index"]) is int
        and 0 <= selected["chosen_index"] < 4
        and len(selected["ranking"]) == 4
        and selected["selection_sha256"] == selection_sha256
        and type(value) in {int, float}
        and math.isfinite(value)
        and value > 0
        and selected.get("chosen_lambda_low") == value
        and len(selected.get("cells", [])) == 36,
        "Finite Development lambda selection differs or is incomplete",
    )
    target, replay = config["target"], config["replay"]
    require(
        target.get("retention_kind") == replay.get("retention_kind") == "parameter"
        and target["retention_weight"] == replay["initial_level"] == replay["level_one"] == value
        and replay["level_two"] > value,
        "Parameter config does not bind chosen lambda",
    )
    return value


def verify_reuse(spec: dict, job: dict, cell: dict, config: dict, code: dict) -> None:
    require(set(spec) == {"job_id", "run_manifest"}, "Reuse entry fields mismatch")
    require(
        job["id"].startswith(("main_", "block7_")), "Only existing main/block7 runs may be skipped"
    )
    require(job["target"] is not None, "Reused job requires pinned target checkpoint")
    pin = pinned_file(spec["run_manifest"])
    path = Path(pin["path"])
    record = dispatch.read_verified_json(path, pin["sha256"])
    replay = record.get("config", {})
    binding = record.get("input_binding", {})
    settings = config["replay"]
    controller = {
        "levels": [0.0, settings["level_one"], settings["level_two"]],
        "initial_level": settings["initial_level"],
        "block_days": settings["block_days"],
        "min_complete_days": settings["min_complete_days"],
        "delta": settings["delta"],
        "alpha": settings["alpha"],
        "bootstrap_segment_days": settings["bootstrap_segment_days"],
        "bootstrap_resamples": settings["bootstrap_resamples"],
        "seed": cell["seed"],
        "challenger_rule": settings["challenger_rule"],
    }
    require(
        record.get("schema") == "hung-sprint2-development-replay-v1"
        and record.get("status") == "completed"
        and record.get("run_id") == path.parent.name
        and record.get("code", {}).get("executed_sources") == code["executed_sources"]
        and record.get("runner_cursor") == config["replay"]["max_origins"]
        and replay.get("selection_rule") == "confidence"
        and replay.get("controller") == controller
        and replay.get("retention_kind") == settings.get("retention_kind", "latent")
        and replay.get("initialization_kind") == settings.get("initialization_kind", "source")
        and replay.get("epsilon") == config["target"]["epsilon"]
        and replay.get("seed") == cell["seed"]
        and replay.get("max_origins") == config["replay"]["max_origins"]
        and binding.get("input_manifest_sha256") == cell["input_manifest_sha256"]
        and binding.get("entity_id") == cell["entity_id"]
        and record.get("source_checkpoint_sha256") == job["source"]["sha256"]
        and record.get("target_checkpoint_sha256") == job["target"]["sha256"],
        f"Reused run provenance differs: {job['id']}",
    )
    dispatch.verify_stage_output(path.parent, path.parent.name, job["method"], code)
    journal = record.get("event_journal", {})
    dispatch.verify_file(path.parent / journal.get("file", ""), journal.get("sha256"))


def verify_checkpoint_grid(
    cells: list[dict],
    sources: dict,
    targets: dict,
    configs: dict,
    selection: dict,
    input_base: Path,
    code: dict,
) -> None:
    """Authenticate declared Source and reused target checkpoints before writing a plan."""
    for budget in (7, 14, 28):
        input_run = input_base / f"urbanev-SZH-{budget}d"
        manifest_sha = selection["budgets"][str(budget)]["manifest_sha256"]
        manifest = dispatch._load_run(input_run, manifest_sha)
        entity_rows = [
            json.loads(line)
            for line in (input_run / "entities.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        entities = {
            row["identity"][2]: row
            for row in entity_rows
            if row.get("role") == "development"
            and row.get("identity", [])[:2] == ["urbanev", "SZH"]
        }
        for seed in (7, 11, 19):
            source = sources[(budget, seed)]
            source_binding = dispatch._binding(manifest, manifest_sha, stage="source")
            source_record = dispatch.checked_checkpoint(
                Path(source["path"]),
                source["sha256"],
                source_binding,
                code,
                source["run_manifest_sha256"],
            )
            require(source_record.get("seed") == seed, "Source seed differs")
            dispatch.verify_source_schedule(
                source_record, configs["main"]["source"], input_run, manifest
            )
            for cell in (c for c in cells if c["budget"] == budget and c["seed"] == seed):
                entity = entities.get(cell["entity_id"])
                require(
                    entity is not None
                    and entity.get("initialization")
                    in {"target_initial_adaptation", "source_checkpoint_only"},
                    "Selected Development entity missing or blocked",
                )
                for variant in TARGET_NAMES:
                    target = targets[(cell["id"], variant)]
                    if target is None:
                        continue
                    binding = dispatch._binding(
                        manifest,
                        manifest_sha,
                        stage="target",
                        entity_id=cell["entity_id"],
                        scale_id=entity["scale"]["fit_sha256"],
                        source_checkpoint_sha256=source["sha256"],
                    )
                    record = dispatch.checked_checkpoint(
                        Path(target["path"]),
                        target["sha256"],
                        binding,
                        code,
                        target["run_manifest_sha256"],
                    )
                    settings = configs[variant]["target"]
                    dispatch.verify_target_schedule(record, settings, entity["initial_trainable"])
                    require(
                        record.get("seed") == seed
                        and record.get("retention_weight") == settings["retention_weight"]
                        and record.get("retention_kind", "latent")
                        == settings.get("retention_kind", "latent")
                        and record.get("initialization_kind", "source")
                        == settings.get("initialization_kind", "source"),
                        "Reused target method/config differs",
                    )
