"""Read-only Development forecast scoring from SHA-pinned, verified artifacts.

Recompute original-unit errors from stored issued forecasts and already arrived
labels. Never load Final inputs or choose configurations. All tables are partial
until the separate coverage, fairness and independent-review gates pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from collections import defaultdict
from pathlib import Path

import torch


def file_sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verified_file(pin: dict, root: Path) -> Path:
    path = Path(pin["path"]).resolve()
    if not path.is_relative_to(root.resolve()) or file_sha(path) != pin["sha256"]:
        raise ValueError("Artifact outside project or SHA mismatch")
    return path


def pin(path: Path, root: Path) -> dict:
    path = path.resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Artifact outside project")
    return {"path": str(path), "sha256": file_sha(path)}


def method_family(job: dict) -> str:
    suffix = "_" + job["cell"]
    if not job["id"].endswith(suffix) or len(job["id"]) <= len(suffix):
        raise ValueError("Job family/cell naming differs")
    return job["id"][: -len(suffix)]


def build_catalog(spec: dict, root: Path) -> dict:
    """Bind complete dispatcher receipts and VERIFIED_REUSE rows to read-only metrics."""
    plan = json.loads(verified_file(spec["plan"], root).read_bytes())
    partition = json.loads(verified_file(spec["partition"], root).read_bytes())
    if plan["scope"] != "development_only" or partition["plan_sha256"] != spec["plan"]["sha256"]:
        raise ValueError("Plan/partition binding differs")
    cells = {c["id"]: c for c in plan["cells"]}
    jobs = {j["id"]: j for j in plan["jobs"]}
    configs = {c["id"]: c for c in plan["configs"]}
    output = Path(spec.get("readback_output_root", plan["output_root"])).resolve()
    rows = []

    def entry(job_id, method, cell, manifest_pin, checkpoint_pin, source, target, proofs, status):
        return {
            "job_id": job_id,
            "method": method,
            "budget": cell["budget"],
            "seed": cell["seed"],
            "entity_id": cell["entity_id"],
            "input_manifest_sha256": cell["input_manifest_sha256"],
            "source_sha256": source["sha256"] if source else None,
            "target_sha256": target["sha256"] if target else None,
            "manifest": manifest_pin,
            "checkpoint": checkpoint_pin,
            "proofs": proofs,
            "status": status,
        }

    if spec.get("reuse_ledger"):
        ledger = json.loads(verified_file(spec["reuse_ledger"], root).read_bytes())
        for row in ledger["jobs"]:
            if row["status"] != "VERIFIED_REUSE":
                continue
            if not row["job_id"].startswith("main_"):
                raise ValueError("Unsupported reuse mapping")
            cell = cells[row["job_id"][len("main_") :]]
            manifest_path = verified_file(row["run_manifest"], root)
            manifest = json.loads(manifest_path.read_bytes())
            checkpoint = {
                "path": str(manifest_path.with_name("runner_checkpoint.pt")),
                "sha256": manifest["final_runner_checkpoint_sha256"],
            }
            proofs = [spec["reuse_ledger"], spec["plan"], row["source"], row["target"]]
            journal = manifest["event_journal"]
            proofs.append(
                {"path": str(manifest_path.with_name(journal["file"])), "sha256": journal["sha256"]}
            )
            rows.append(
                entry(
                    row["job_id"],
                    "main",
                    cell,
                    row["run_manifest"],
                    checkpoint,
                    row["source"],
                    row["target"],
                    proofs,
                    "VERIFIED_REUSE",
                )
            )
    for completed in spec["completed_shards"]:
        exit_record = json.loads(verified_file(completed["verify_exit"], root).read_bytes())
        if exit_record["exit_code"] != 0:
            raise ValueError("Shard verifier did not succeed")
        shard = next(s for s in partition["shards"] if s["id"] == completed["id"])
        for job_id in shard["job_ids"]:
            job, cell = jobs[job_id], cells[jobs[job_id]["cell"]]
            receipt_path = output / "receipts" / job_id / "job.json"
            receipt = json.loads(receipt_path.read_bytes())
            if (receipt["job_id"], receipt["plan_sha256"], receipt["shards_sha256"]) != (
                job_id,
                spec["plan"]["sha256"],
                spec["partition"]["sha256"],
            ):
                raise ValueError("Job receipt identity differs")
            config_pin = {k: configs[job["config"]][k] for k in ("path", "sha256")}
            config = json.loads(verified_file(config_pin, root).read_bytes())
            final_stage = f"replay-{config['replay']['max_origins']}"
            proofs = [
                spec["plan"],
                spec["partition"],
                completed["verify_exit"],
                pin(receipt_path, root),
                config_pin,
            ]
            for stage, sha in receipt["stages"].items():
                stage_pin = {"path": str(receipt_path.with_name(stage + ".json")), "sha256": sha}
                stage_record = json.loads(verified_file(stage_pin, root).read_bytes())
                binding = stage_record["binding"]
                if (
                    binding["job"],
                    binding["plan_sha256"],
                    binding["shards_sha256"],
                    binding["config_sha256"],
                    binding["input_manifest_sha256"],
                ) != (
                    job,
                    spec["plan"]["sha256"],
                    spec["partition"]["sha256"],
                    config_pin["sha256"],
                    cell["input_manifest_sha256"],
                ):
                    raise ValueError("Stage provenance differs")
                proofs.append(stage_pin)
                for name, record in stage_record["files"].items():
                    artifact = {
                        "path": str(output / "jobs" / job_id / stage / name),
                        "sha256": record["sha256"],
                    }
                    verified_file(artifact, root)
                    proofs.append(artifact)
            if final_stage not in receipt["stages"]:
                raise ValueError("Final replay stage incomplete")
            manifest_path = output / "jobs" / job_id / final_stage / "run_manifest.json"
            manifest = json.loads(manifest_path.read_bytes())
            checkpoint_name = (
                "runner.pt"
                if manifest["schema"] == "hung-single-baseline-replay-v1"
                else "runner_checkpoint.pt"
            )
            # The final checkpoint hash is already bound by the stage inventory.
            checkpoint = {
                "path": str(manifest_path.with_name(checkpoint_name)),
                "sha256": manifest["final_runner_checkpoint_sha256"],
            }
            for role in ("source", "target"):
                if job[role]:
                    proofs.append(job[role])
            rows.append(
                entry(
                    job_id,
                    method_family(job),
                    cell,
                    pin(manifest_path, root),
                    checkpoint,
                    job["source"],
                    job["target"],
                    proofs,
                    "DISPATCH_VERIFIED",
                )
            )
    return {
        "scope": "development_only",
        "schema": "hung-results-catalog-v1",
        "spec": spec,
        "runs": rows,
    }


def metrics(days: list[dict]) -> dict | None:
    if not days:
        return None
    hours = 24 * len(days)
    return {
        "hours": hours,
        "mae_kwh": sum(d["absolute"] for d in days) / hours,
        "rmse_kwh": math.sqrt(sum(d["squared"] for d in days) / hours),
    }


def score_saved(state: dict, manifest: dict) -> dict:
    """Score live predictions only; do not use candidate or audit performance."""
    if state["schema"] not in {"hung-sprint2-runner-v1", "hung-single-baseline-runner-v1"}:
        raise ValueError("Unsupported checkpoint schema")
    if manifest.get("status") != "completed":
        raise ValueError("Run not terminal")
    scale = state["energy_scale"]
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("Invalid original-unit scale")
    days = {}
    issued_ids = set()
    for issued in state["issued"]:
        day_id = issued["day_id"]
        if day_id in issued_ids:
            raise ValueError("Duplicate issued day")
        issued_ids.add(day_id)
        labels = issued.get("y_scaled")
        if labels is None:
            if issued.get("normalized_mae") is not None:
                raise ValueError("Missing labels carry a score")
            continue
        if issued.get("normalized_mae") is None:
            raise ValueError("Arrived labels were not scored")
        if state["schema"] == "hung-single-baseline-runner-v1":
            prediction = issued["prediction"]
        else:
            levels = state["controller"]["levels"]
            prediction = issued["forecasts"][levels.index(issued["active_level"])]
        prediction, labels = prediction.reshape(-1).double(), labels.reshape(-1).double()
        if prediction.shape != (24,) or labels.shape != (24,):
            raise ValueError("Incomplete 24-hour horizon")
        if not bool(torch.isfinite(prediction).all() and torch.isfinite(labels).all()):
            raise ValueError("Nonfinite forecast/label")
        if bool((prediction < 0).any() or (labels < 0).any()):
            raise ValueError("Negative forecast/label")
        error = (prediction - labels) * scale
        days[day_id] = {
            "absolute": float(error.abs().sum()),
            "squared": float(error.square().sum()),
            "label_sha256": hashlib.sha256(
                struct.pack("<24d", *(labels * scale).tolist())
            ).hexdigest(),
        }
    coverage = manifest["coverage"]
    if len(issued_ids) != coverage["created"] or len(days) != coverage["scored"]:
        raise ValueError("Checkpoint coverage differs")
    calculated = metrics(list(days.values()))
    declared = manifest["metrics_kwh"]
    if isinstance(declared, dict) and "live" in declared:
        declared = declared["live"]
    if (calculated is None) != (declared is None):
        raise ValueError("Declared metric availability differs")
    if calculated is not None:
        for key, value in calculated.items():
            if not math.isclose(value, declared[key], rel_tol=1e-9, abs_tol=1e-9):
                raise ValueError(f"Recomputed {key} differs")
    return {"coverage": coverage, "metrics": calculated, "days": days}


def verify_artifacts(catalog: dict, root: Path) -> list[dict]:
    if catalog.get("scope") != "development_only":
        raise ValueError("Development-only catalog required")
    records, identities = [], set()
    for entry in catalog["runs"]:
        if entry["status"] not in {"VERIFIED_REUSE", "DISPATCH_VERIFIED"}:
            raise ValueError("Unmatched or unverified run cannot enter metric comparison")
        identity = (entry["method"], entry["budget"], entry["seed"], entry["entity_id"])
        if identity in identities:
            raise ValueError("Duplicate logical run")
        identities.add(identity)
        for proof in entry["proofs"]:
            verified_file(proof, root)
        manifest = json.loads(verified_file(entry["manifest"], root).read_bytes())
        checkpoint = verified_file(entry["checkpoint"], root)
        if manifest["final_runner_checkpoint_sha256"] != entry["checkpoint"]["sha256"]:
            raise ValueError("Manifest/checkpoint binding differs")
        binding = manifest["input_binding"]
        if binding["input_manifest_sha256"] != entry["input_manifest_sha256"]:
            raise ValueError("Input binding differs")
        if binding["entity_id"] != entry["entity_id"] or binding["history_days"] != entry["budget"]:
            raise ValueError("Station/budget binding differs")
        seed = manifest["config"].get("seed")
        baseline_receipt_seed = (
            seed is None
            and entry["status"] == "DISPATCH_VERIFIED"
            and entry["method"] in {"seasonal_naive", "frozen_source", "target_only"}
        )
        if (seed != entry["seed"] and not baseline_receipt_seed) or not entry["proofs"]:
            raise ValueError("Seed or verification proof missing")
        for role in ("source", "target"):
            expected = entry.get(role + "_sha256")
            if expected is not None and manifest.get(role + "_checkpoint_sha256") != expected:
                raise ValueError("Source/Target binding differs")
        state = torch.load(checkpoint, map_location="cpu", weights_only=True)
        if state["binding"] != binding:
            raise ValueError("Checkpoint input binding differs")
        scored = score_saved(state, manifest)
        records.append(
            {
                **entry,
                **scored,
                "code_commit": manifest["code"]["commit"],
                "device": manifest.get("device"),
                "final_stage_duration_seconds": manifest.get("duration_seconds"),
                "cumulative_runtime_costs": manifest.get("runtime_costs", manifest.get("cost")),
                "cumulative_proxy_costs": manifest.get("proxy_costs"),
            }
        )
    return records


def paired_results(records: list[dict]) -> tuple[list[dict], list[dict]]:
    cells = defaultdict(dict)
    for record in records:
        cells[(record["budget"], record["seed"], record["entity_id"])][record["method"]] = record
    pairs, blocked = [], []
    for (budget, seed, station), methods in sorted(cells.items()):
        for reference in ("main", "target_only"):
            if reference not in methods:
                continue
            baseline = methods[reference]
            for method, candidate in sorted(methods.items()):
                if method == reference:
                    continue
                reason = None
                if candidate["input_manifest_sha256"] != baseline["input_manifest_sha256"]:
                    reason = "input_mismatch"
                for role in ("source_sha256", "target_sha256"):
                    left, right = candidate.get(role), baseline.get(role)
                    if left is not None and right is not None and left != right:
                        reason = "initialization_mismatch"
                common = sorted(candidate["days"].keys() & baseline["days"].keys())
                if any(
                    candidate["days"][d]["label_sha256"] != baseline["days"][d]["label_sha256"]
                    for d in common
                ):
                    reason = "label_mismatch"
                if not common:
                    reason = reason or "no_paired_scored_days"
                identity = {
                    "budget": budget,
                    "seed": seed,
                    "entity_id": station,
                    "method": method,
                    "reference": reference,
                }
                if reason:
                    blocked.append({**identity, "reason": reason})
                    continue
                left = metrics([candidate["days"][d] for d in common])
                right = metrics([baseline["days"][d] for d in common])
                pairs.append(
                    {
                        **identity,
                        "paired_days": len(common),
                        "method_metrics": left,
                        "reference_metrics": right,
                        "uses_source": candidate.get("source_sha256") is not None,
                        "paired_day_ids_sha256": hashlib.sha256(
                            json.dumps(common).encode()
                        ).hexdigest(),
                    }
                )
    return pairs, blocked


def station_first(pairs: list[dict]) -> list[dict]:
    stations = defaultdict(list)
    for pair in pairs:
        key = (pair["budget"], pair["method"], pair["reference"], pair["entity_id"])
        stations[key].append(pair)
    groups = defaultdict(list)
    for (budget, method, reference, station), rows in sorted(stations.items()):
        means = {
            side: {
                metric: sum(r[side][metric] for r in rows) / len(rows)
                for metric in ("mae_kwh", "rmse_kwh")
            }
            for side in ("method_metrics", "reference_metrics")
        }
        groups[(budget, method, reference)].append(
            {
                "entity_id": station,
                "seeds": len(rows),
                "uses_source": all(r["uses_source"] for r in rows),
                **means,
            }
        )
    result = []
    for (budget, method, reference), rows in sorted(groups.items()):
        averages = {
            side: {
                metric: sum(r[side][metric] for r in rows) / len(rows)
                for metric in ("mae_kwh", "rmse_kwh")
            }
            for side in ("method_metrics", "reference_metrics")
        }
        gain = averages["reference_metrics"]["mae_kwh"] - averages["method_metrics"]["mae_kwh"]
        denominator = averages["reference_metrics"]["mae_kwh"]
        worse = sum(
            r["method_metrics"]["mae_kwh"] > r["reference_metrics"]["mae_kwh"] for r in rows
        ) / len(rows)
        is_transfer = reference == "target_only" and all(r["uses_source"] for r in rows)
        result.append(
            {
                "budget": budget,
                "method": method,
                "reference": reference,
                "stations": len(rows),
                "minimum_seeds_per_station": min(r["seeds"] for r in rows),
                **averages,
                "absolute_mae_gain_kwh": gain,
                "relative_mae_gain": gain / denominator if denominator > 0 else None,
                "worse_than_reference_station_fraction": worse,
                "negative_transfer_station_fraction": worse if is_transfer else None,
                "transfer_gain": gain / denominator if is_transfer and denominator > 0 else None,
            }
        )
    return result


def aggregate_results(catalog: dict, root: Path) -> dict:
    records = verify_artifacts(catalog, root)
    pairs, blocked = paired_results(records)
    return {
        "schema": "hung-development-partial-results-v2",
        "scope": "development_only",
        "acceptance": "Provisional; full coverage and independent review required",
        "runs": [{k: v for k, v in r.items() if k != "days"} for r in records],
        "counts": {
            "runs": len(records),
            "scorable_runs": sum(bool(r["days"]) for r in records),
            "zero_scored_runs": sum(not r["days"] for r in records),
        },
        "paired_cells": pairs,
        "blocked_pairs": blocked,
        "station_first": station_first(pairs),
        "aggregation": "Complete hourly errors within paired station/seed; mean seeds within station, then equal station mean within each budget. Budgets remain separate. Transfer gain and negative transfer apply only to Source-using methods versus Target-only. Other comparisons report generic MAE differences/worse-than-reference fractions. Zero reference MAE gives undefined relative gain; absolute differences remain available.",
    }


def main() -> None:
    from experiments.supporting_pipeline.dispatch_state import atomic_create

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--catalog-sha256", required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--build-catalog", action="store_true", help="Input is a pinned collection specification"
    )
    args = parser.parse_args()
    path = verified_file(
        {"path": str(args.catalog), "sha256": args.catalog_sha256}, args.project_root
    )
    value = json.loads(path.read_bytes())
    result = (
        build_catalog(value, args.project_root)
        if args.build_catalog
        else aggregate_results(value, args.project_root)
    )
    result["catalog_sha256"] = args.catalog_sha256
    if not args.output.resolve().is_relative_to(args.project_root.resolve()):
        raise ValueError("Output outside project")
    atomic_create(args.output, result)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sha256": file_sha(args.output),
                **result.get("counts", {}),
            }
        )
    )


if __name__ == "__main__":
    main()
