"""Independently verify a downloaded issue #99 Kaggle pilot run."""

import argparse
import hashlib
import json
import math
from datetime import datetime, timedelta
from pathlib import Path

import torch


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def state_digest(value: object) -> str:
    """Independent implementation of the runner's tensor/value digest."""
    digest = hashlib.sha256()

    def visit(item: object) -> None:
        if isinstance(item, torch.Tensor):
            tensor = item.detach().cpu().contiguous()
            digest.update(canonical([str(tensor.dtype), list(tensor.shape)]))
            digest.update(tensor.numpy().tobytes())
        elif isinstance(item, dict):
            for key in sorted(item, key=lambda key: (type(key).__name__, str(key))):
                visit(key)
                visit(item[key])
        elif isinstance(item, (list, tuple)):
            digest.update(canonical([type(item).__name__, len(item)]))
            for part in item:
                visit(part)
        else:
            digest.update(canonical(item))

    visit(value)
    return digest.hexdigest()


def finite_nonnegative(value: object, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (float, int))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(f"Nonfinite or negative {name}")
    return float(value)


def verify_pilot(
    run_path: Path,
    runtime_path: Path,
    bundle_manifest_path: Path,
    *,
    expected_manifest_sha256: str,
    expected_code_commit: str,
    expected_ticks: int = 20,
) -> dict:
    """Check SHA bindings, every committed tick and pilot-only scope without edits."""
    if (
        expected_ticks < 1
        or len(expected_manifest_sha256) != 64
        or any(character not in "0123456789abcdef" for character in expected_manifest_sha256)
        or len(expected_code_commit) != 40
        or any(character not in "0123456789abcdef" for character in expected_code_commit)
    ):
        raise ValueError("Invalid expected pilot identity")
    if sha256(bundle_manifest_path) != expected_manifest_sha256:
        raise ValueError("Kaggle bundle manifest differs from pinned SHA-256")
    bundle = json.loads(bundle_manifest_path.read_text(encoding="utf-8"))
    if (
        bundle.get("schema") != "issue99-kaggle-bundle-v1"
        or bundle.get("code_commit") != expected_code_commit
    ):
        raise ValueError("Bundle schema/code commit mismatch")
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    if (
        runtime.get("schema") != "issue99-kaggle-runtime-v1"
        or runtime.get("code_commit") != expected_code_commit
        or "T4" not in str(runtime.get("gpu"))
        or not runtime.get("packages", {}).get("torch")
    ):
        raise ValueError("Missing T4 runtime/package evidence")
    binding_path = run_path / "binding.json"
    report_path = run_path / "run.json"
    initial_path = run_path / "initial-adaptation.json"
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    config = binding.get("config", {})
    env = binding.get("environment", {})
    if (
        binding.get("schema") != "issue99-run-binding-v1"
        or report.get("schema") != "issue99-run-v1"
        or report.get("binding") != binding
        or report.get("run_id") != run_path.name
        or report.get("phase") != "pilot"
        or config.get("phase") != "pilot"
        or config.get("objective_origins") != []
        or env.get("device") != "cuda"
        or "T4" not in str(env.get("device_name"))
        or binding.get("code", {}).get("commit") != expected_code_commit
        or binding.get("input", {}).get("input_manifest_sha256") != bundle["input_manifest_sha256"]
    ):
        raise ValueError("Pilot report/config/input/code/runtime binding mismatch")
    if not str(env.get("torch", "")).startswith(str(runtime["packages"]["torch"])):
        raise ValueError("Runtime and run Torch versions differ")
    for name, expected in bundle["code_files_sha256"].items():
        recorded = binding["code"]["files"].get(name)
        if recorded is not None and recorded != expected:
            raise ValueError(f"Run code file differs from bundled code: {name}")
    seed = config["initial_training"]["seed"]
    if (
        binding["input"].get("source_checkpoint_sha256")
        != bundle["source_checkpoint_sha256"][str(seed)]
    ):
        raise ValueError("Run Source10 differs from bundled checkpoint")
    initial_logs = json.loads(initial_path.read_text(encoding="utf-8"))
    if initial_logs != report.get("initial_logs") or state_digest(initial_logs) != binding.get(
        "initial_adaptation_sha256"
    ):
        raise ValueError("Initial adaptation record differs")
    if list(run_path.glob(".pending-*")):
        raise ValueError("Uncommitted pilot tick remains")
    ticks = sorted(run_path.glob("tick-*"))
    if len(ticks) != expected_ticks or [tick.name for tick in ticks] != [
        f"tick-{index:04d}" for index in range(expected_ticks)
    ]:
        raise ValueError("Pilot tick count or sequence differs")
    previous = "0" * 64
    issued = {}
    scored = {}
    skipped = {}
    actual_updates = 0
    decisions = 0
    state_commitments = {}
    retention = config.get("state_retention", "all")
    if retention not in ("all", "latest"):
        raise ValueError("Invalid state retention policy")
    files = {
        "binding.json": sha256(binding_path),
        "run.json": sha256(report_path),
        "initial-adaptation.json": sha256(initial_path),
        "runtime.json": sha256(runtime_path),
        "bundle-manifest.json": sha256(bundle_manifest_path),
    }
    for index, tick in enumerate(ticks):
        commit_path = tick / "commit.json"
        commit = json.loads(commit_path.read_text(encoding="utf-8"))
        if (
            commit.get("index") != index
            or commit.get("previous") != previous
            or set(commit.get("files", {})) != {"state.pt", "events.jsonl", "forecasts.json"}
        ):
            raise ValueError(f"Broken pilot commit chain at tick {index}")
        for name, expected in commit["files"].items():
            artifact = tick / name
            if name == "state.pt":
                state_commitments[tick.name] = expected
            if (
                not artifact.exists()
                and name == "state.pt"
                and retention == "latest"
                and index < len(ticks) - 1
            ):
                continue
            if sha256(artifact) != expected:
                raise ValueError(f"Changed retained pilot artifact: {tick.name}/{name}")
            files[f"{tick.name}/{name}"] = expected
        files[f"{tick.name}/commit.json"] = sha256(commit_path)
        previous = files[f"{tick.name}/commit.json"]
        forecast = json.loads((tick / "forecasts.json").read_text(encoding="utf-8"))
        events = [
            json.loads(line)
            for line in (tick / "events.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        saved = [event for event in events if event["event"] == "forecast_saved"]
        for event in events:
            if event["event"] == "score":
                origin = event["origin"]
                if (
                    origin not in issued
                    or origin in scored
                    or origin in skipped
                    or event["prediction_sha256"] != issued[origin]
                ):
                    raise ValueError(f"Score lacks prior saved prediction: {origin}")
                for metric in ("mae_kwh", "mse_kwh2"):
                    finite_nonnegative(event[metric], metric)
                scored[origin] = event
            elif event["event"] == "skip_incomplete_labels":
                origin = event["origin"]
                as_of = event["as_of"]
                if (
                    origin not in issued
                    or origin in scored
                    or origin in skipped
                    or (forecast and as_of != forecast["origin"])
                    or datetime.fromisoformat(as_of)
                    < datetime.fromisoformat(origin) + timedelta(days=1)
                ):
                    raise ValueError(
                        f"Incomplete-label skip lacks arrived forecast lineage: {origin}"
                    )
                skipped[origin] = event
            elif event["event"] == "actual_update":
                actual_updates += 1
            elif event["event"] == "meta_decision":
                decisions += 1
        if forecast:
            origin = forecast["origin"]
            if (
                origin in issued
                or len(saved) != 1
                or saved[0]["origin"] != origin
                or saved[0]["prediction_sha256"] != commit["files"]["forecasts.json"]
            ):
                raise ValueError(f"Forecast/event lineage differs at tick {index}")
            issued[origin] = commit["files"]["forecasts.json"]
        elif saved:
            raise ValueError(f"Forecast event without saved forecast at tick {index}")
    if previous != report.get("commit_chain"):
        raise ValueError("Final pilot commit-chain identity differs")
    final = torch.load(ticks[-1] / "state.pt", map_location="cpu", weights_only=True)
    if state_digest(final["branch"]) != report.get("final_state_sha256"):
        raise ValueError("Final model/Adam/RNG state digest differs")
    if (
        report.get("scheduled_days") != 90
        or report.get("issued_days") != len(issued)
        or report.get("scored_days") != len(scored)
        or report.get("objective_requested_days") != 0
        or report.get("objective_scored_days") != 0
        or report.get("objective_minimum_scored_days") is not None
        or report.get("objective_coverage_pass") is not False
        or report.get("mae_kwh") is not None
        or report.get("rmse_kwh") is not None
        or report.get("controller_decisions") != decisions
        or final["actual_steps"] != report.get("actual_steps")
        or final["virtual_steps"] != report.get("virtual_steps")
        or report.get("objective_missing_origins") != []
        or len({row["origin"] for row in final["pending"]}) != len(final["pending"])
        or {row["origin"] for row in final["pending"]} != set(issued) - set(scored) - set(skipped)
    ):
        raise ValueError("Pilot count/coverage/null-objective report differs")
    if (
        report.get("pending_days") != len(final["pending"])
        or report["actual_steps"] < actual_updates
    ):
        raise ValueError("Pilot update/pending counters differ")
    if report.get("cost_seconds") != final.get("cost"):
        raise ValueError("Pilot cost differs from committed state")
    cost = report.get("cost_seconds")
    if not isinstance(cost, dict) or not cost:
        raise ValueError("Missing pilot cost record")
    for name, value in cost.items():
        finite_nonnegative(value, name)
    for name in (
        "invocation_wall_seconds",
        "source_load_wall_seconds_this_invocation",
        "replay_load_wall_seconds_this_invocation",
        "prefix_load_wall_seconds_this_invocation",
        "initial_wall_seconds_this_invocation",
    ):
        finite_nonnegative(report[name], name)
    for name in ("gpu_peak_allocated_bytes", "gpu_peak_reserved_bytes"):
        finite_nonnegative(report[name], name)
    return {
        "schema": "issue99-pilot-independent-verification-v1",
        "status": "PASS",
        "scope": "Downloaded 20-tick pilot artifact verification; no forecasting-effectiveness claim",
        "run_id": report["run_id"],
        "code_commit": expected_code_commit,
        "bundle_manifest_sha256": expected_manifest_sha256,
        "ticks": expected_ticks,
        "issued_days": len(issued),
        "scored_days": len(scored),
        "skipped_incomplete_days": len(skipped),
        "skipped_origins": sorted(skipped),
        "actual_update_events": actual_updates,
        "controller_decisions": decisions,
        "gpu": runtime["gpu"],
        "cost_seconds": report["cost_seconds"],
        "state_commitments_sha256": state_commitments,
        "files_sha256": files,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--bundle-manifest", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--expected-code-commit", required=True)
    parser.add_argument("--expected-ticks", type=int, default=20)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify_pilot(
        args.run,
        args.runtime,
        args.bundle_manifest,
        expected_manifest_sha256=args.expected_manifest_sha256,
        expected_code_commit=args.expected_code_commit,
        expected_ticks=args.expected_ticks,
    )
    if args.output is not None:
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
