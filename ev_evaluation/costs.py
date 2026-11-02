"""Common descriptive cost accounting for primary and separate-city collections."""


def comparison_costs(cells: dict, source_runs: list[dict]) -> dict:
    """Retain actual candidate/audit/estimator costs and charge reused Source once."""
    costs = {}
    for name in sorted({key[-1] for key in cells}):
        reports = [value["report"] for key, value in cells.items() if key[-1] == name]
        costs[name] = {
            "run_count": len(reports),
            "elapsed_seconds_sum": sum(r["elapsed_seconds"] for r in reports),
            "candidate_steps": sum(r["candidate_steps"] for r in reports),
            "audit_steps": sum(r["audit_steps"] for r in reports),
            "initial_adaptation_steps": sum(
                step["steps"] for r in reports for step in r["initial_logs"]
            ),
            "candidate_models_per_run": sorted({len(r["candidate_levels"]) for r in reports}),
            "uncertainty_source_members_per_run": sorted(
                {len(r["binding"]["uncertainty_members"]) for r in reports}
            ),
            "component_seconds_sum": {
                key: sum(r["cost"][key] for r in reports)
                for key in (
                    "inference_seconds",
                    "update_seconds",
                    "audit_inference_seconds",
                    "audit_update_seconds",
                    "controller_seconds",
                    "proxy_seconds",
                )
            },
            "gpu_peak_allocated_bytes_max": max(r["gpu_peak_allocated_bytes"] for r in reports),
            "gpu_peak_reserved_bytes_max": max(r["gpu_peak_reserved_bytes"] for r in reports),
            "scope": "Per-run reset peaks; setup fixture overlap/background backup I/O may affect early timing. Include reused Source training and initialization/input/export costs separately.",
        }
    return {
        "costs": costs,
        "source_cost_reused_once": {
            "source_training_elapsed_seconds": sum(r["elapsed_seconds"] for r in source_runs),
            "source_training_optimizer_steps": sum(
                step["steps"] for r in source_runs for step in r["logs"]
            ),
            "source_environments": [r["environment"] for r in source_runs],
            "limits": "Recorded Source training cost, not complete setup/latent-scale/export/transfer/verification cost. Source and target environments may differ. Do not charge reused Source models once per target or omit them entirely.",
        },
    }
