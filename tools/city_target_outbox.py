"""Bounded separate-city Development targets from three published Sources; never fit Source/Final."""

import argparse
import contextlib
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch

from ev_models.checkpoint import digest, write_json
from ev_models.run import environment
from ev_runner.replay import Replay
from ev_runner.run import execute, runtime_code
from tools.charged_development_cohort import CITIES
from tools.charged_matched_development import backup_context, validate_cohort
from tools.city_source_outbox import require_outbox, validate_environment
from tools.cloud_outbox import CLOUD_ROOTS, cloud_working_root
from tools.comparison_matrix import CachedInputs
from tools.durable_run_backup import RunBackup, canonical
from tools.export_development import safe_name
from tools.replay_checkpoint_chunk import (
    check_handoff,
    checkpoint_progress,
    initial_sources,
    package_outbox,
    select_chunk,
    shared_source_package,
)


def check_source_kit(root: Path, pin: str, context: dict) -> dict:
    """Check immutable files and operator's external publication receipts, not OAuth."""
    path = root / "source-kit.json"
    if root.is_symlink() or path.is_symlink() or digest(path) != pin:
        raise ValueError("Pinned Source kit required")
    kit = json.loads(path.read_text())
    names = {"context.json"}
    for seed in (42, 43, 44):
        names.update(
            (
                f"source-seed{seed}.zip",
                f"source-seed{seed}.receipt.json",
                f"publication-seed{seed}.json",
            )
        )
    if (
        kit.get("schema") != "ev-published-city-source-kit-v1"
        or kit.get("namespace") != context["namespace"]
        or kit.get("seeds") != [42, 43, 44]
        or set(kit.get("files", {})) != names
        or {p.name for p in root.iterdir()} != {*names, "source-kit.json"}
    ):
        raise ValueError("Exactly three separately published same-city Sources required")
    for name, fingerprint in kit["files"].items():
        safe_name(name)
        item = root / name
        if (
            item.is_symlink()
            or not item.is_file()
            or item.stat().st_size != fingerprint["bytes"]
            or digest(item) != fingerprint["sha256"]
        ):
            raise ValueError("Changed Source kit member")
    if (root / "context.json").read_bytes() != canonical(context):
        raise ValueError("Changed independently rebuilt Source context")
    source_pins = {}
    for seed in (42, 43, 44):
        publication = json.loads((root / f"publication-seed{seed}.json").read_text())
        receipt = json.loads((root / f"source-seed{seed}.receipt.json").read_text())
        artifact = publication.get("artifact", {})
        if (
            publication.get("schema") != "verified-city-source-publication-v1"
            or publication.get("namespace") != "-".join(context["namespace"])
            or publication.get("seed") != seed
            or publication.get("context_sha256") != digest(root / "context.json")
            or publication.get("source_checkpoint_sha256") != receipt["record"]["entry"]["sha256"]
            or not re.fullmatch(r"[0-9a-f]{64}", publication.get("source_checkpoint_sha256", ""))
            or publication.get("independent_content_verified") is not True
            or publication.get("remote_readback_verified") is not True
            or not re.fullmatch(r"[0-9a-f]{64}", publication.get("verification_sha256", ""))
            or not re.fullmatch(r"[0-9a-f]{64}", artifact.get("sha256", ""))
            or type(artifact.get("bytes")) is not int
            or artifact["bytes"] <= 0
            or not re.fullmatch(
                r"https://drive\.google\.com/file/d/[A-Za-z0-9_-]{20,100}/view",
                artifact.get("drive_url", ""),
            )
            or any(
                publication.get(key) != context[key]
                for key in ("cohort_sha256", "primary_sha256", "environment_profile_sha256")
            )
        ):
            raise ValueError("Missing or changed independent Source publication evidence")
        source_pins[seed] = publication["source_checkpoint_sha256"]
    return source_pins


def target_plan(context: dict, kit_sha256: str) -> tuple[str, list[dict]]:
    """Freeze all predeclared city cells in existing budget/entity/seed/method order."""
    if context.get("seeds") != [42, 43, 44] or not context.get("expected_runs"):
        raise ValueError("Complete city seed/config scope required")
    rows = [{"run_id": name, **entry} for name, entry in context["expected_runs"].items()]
    identity = {
        "schema": "ev-city-target-plan-v1",
        "context_sha256": hashlib.sha256(canonical(context)).hexdigest(),
        "source_kit_sha256": kit_sha256,
        "run_ids": [row["run_id"] for row in rows],
    }
    return hashlib.sha256(canonical(identity)).hexdigest(), rows


def run(args: argparse.Namespace) -> None:
    started = time.perf_counter()
    if not torch.cuda.is_available():
        raise ValueError("Real city target execution requires cloud CUDA")
    for path, checksum in (
        (args.cohort, args.cohort_sha256),
        (args.primary_analysis, args.primary_sha256),
        (args.environment_profile, args.environment_sha256),
    ):
        if digest(path) != checksum:
            raise ValueError("Changed declared city dependency")
    working = cloud_working_root(getattr(args, "cloud_root", CLOUD_ROOTS[0]))
    require_outbox(args.output, args.inputs_root, working)
    if args.output.resolve().is_relative_to(
        args.sources_root.resolve()
    ) or args.sources_root.resolve().is_relative_to(args.output.resolve()):
        raise ValueError("Keep new target outputs separate from immutable Source kit")
    code = runtime_code()
    if code["dirty"]:
        raise ValueError("Clean committed code required")
    torch.use_deterministic_algorithms(True)
    actual = environment("cuda")
    profile = json.loads(args.environment_profile.read_text())
    validate_environment(actual, profile, np.__version__)
    cohort, primary = (json.loads(p.read_text()) for p in (args.cohort, args.primary_analysis))
    if (
        cohort.get("namespace") not in {f"charged-{city}" for city in CITIES}
        or not primary.get("collection_lineage")
        or not primary.get("matrix_identities")
    ):
        raise ValueError("Authenticated separate-city cohort and primary recipe required")
    data = {
        b: CachedInputs(
            args.inputs_root / f"{cohort['namespace']}-{b}d",
            cohort["budgets"][str(b)]["manifest_sha256"],
        )
        for b in (7, 14, 28)
    }
    validate_cohort(data, cohort)
    context = backup_context(
        cohort,
        primary,
        data,
        code,
        actual,
        cohort_sha256=args.cohort_sha256,
        primary_sha256=args.primary_sha256,
    )
    context.update(
        schema="ev-kaggle-city-source-outbox-v1",
        backend="local_pending_external_publication",
        environment_profile_sha256=args.environment_sha256,
        numpy_version=np.__version__,
    )
    source_pins = check_source_kit(args.sources_root, args.sources_sha256, context)
    plan_sha, all_rows = target_plan(context, args.sources_sha256)
    chunk = select_chunk(all_rows, args.start, args.count)
    check_handoff(
        all_rows,
        args.start,
        plan_sha,
        cohort["namespace"],
        args.previous_handoff,
        args.previous_handoff_sha256,
    )
    args.output.mkdir(parents=True, exist_ok=False)
    study = args.output / "study"
    study.mkdir()
    # Restore three accepted original Source pairs. No Source training is imported here.
    reader = RunBackup(study, args.sources_root, context, data, resume=True)
    sources, restored_targets = reader.restore()
    if restored_targets or {entry["seed"] for entry in sources} != {42, 43, 44}:
        raise ValueError("Exactly three Source dependencies; no target reuse or selection")
    backup = RunBackup(study, args.output / "local-completed", context, data)
    for entry in sources:
        if entry["sha256"] != source_pins[entry["seed"]]:
            raise ValueError("Restored city Source differs from published weights")
        backup.source(entry)
    if runtime_code() != code:
        raise ValueError("Concurrent edits or output setup changed clean code; stop before fitting")
    source_paths = {
        seed: (Path(entry["path"]), entry["sha256"]) for seed, entry in backup.sources.items()
    }
    executed, previous, replay = [], None, None
    for reference in chunk:
        budget, entity, cfg = reference["history_days"], reference["entity_id"], reference["config"]
        seed = cfg["initial_training"]["seed"]
        if (budget, entity) != previous:
            replay = Replay(data[budget], entity, cfg["replay_days"])
            replay.prepare_label_index()
            previous = budget, entity
        torch.cuda.reset_peak_memory_stats()
        with (
            (study / (reference["run_id"] + ".log")).open("x") as log,
            contextlib.redirect_stdout(log),
        ):
            row = execute(
                data[budget],
                entity,
                *source_paths[seed],
                cfg,
                study / reference["run_id"],
                device="cuda",
                prepared_replay=replay,
                ensemble_sources=tuple(source_paths[s] for s in (42, 43, 44))
                if reference["comparison_variant"] == "uncertainty"
                else (),
            )
        row["comparison_variant"] = reference["comparison_variant"]
        if row["run_id"] != reference["run_id"]:
            raise ValueError("Executed target identity differs from declared order")
        backup.target(row)
        executed.append(row)
        checkpoint_progress(study, executed)
        print("CITY_TARGET_LOCAL_COMPLETED", len(executed), len(chunk), row["run_id"], flush=True)
    all_sources = {str(k): v for k, v in backup.sources.items()}
    shared = shared_source_package(
        study, all_sources, context["source_epochs"], args.output / "shared-city-sources.zip"
    )
    matrix = {
        "scope": "Bounded separate-city supplementary Development; not complete city/remote/Final acceptance",
        "namespace": cohort["namespace"],
        "cohort_sha256": args.cohort_sha256,
        "primary_analysis_sha256": args.primary_sha256,
        "source_epochs": context["source_epochs"],
        "code": code,
        "runs": executed,
        "sources": initial_sources(executed, all_sources),
        "shared_city_sources": shared,
        "status": "technical_success",
        "family_total": len(all_rows),
        "plan_sha256": plan_sha,
        "source_kit_sha256": args.sources_sha256,
    }
    write_json(study / "matrix.json", matrix)
    commands = [
        (
            "daily",
            [
                "tools.verify_comparison",
                "--matrix",
                study / "matrix.json",
                "--inputs-root",
                args.inputs_root,
                "--output",
                study / "verification.json",
                "--cache-inputs",
            ],
        ),
        (
            "states",
            [
                "tools.verify_latest_states",
                "--matrix",
                study / "matrix.json",
                "--verification",
                study / "verification.json",
                "--output",
                study / "latest-states.json",
            ],
        ),
        (
            "export",
            [
                "tools.export_development",
                "--matrix",
                study / "matrix.json",
                "--verification",
                study / "verification.json",
                "--latest-states",
                study / "latest-states.json",
                "--source-root",
                study,
                "--output",
                args.output / "exports",
                "--attachment",
                "shared-city-sources.zip=" + str(args.output / shared["name"]),
                "--attachment",
                "source-kit.json=" + str(args.sources_root / "source-kit.json"),
            ],
        ),
    ]
    for name in ("context.json", *(f"publication-seed{seed}.json" for seed in (42, 43, 44))):
        commands[-1][1].extend(["--attachment", name + "=" + str(args.sources_root / name)])
    for name, command in commands:
        before = time.perf_counter()
        with (args.output / (name + ".log")).open("x") as log:
            result = subprocess.run(
                [sys.executable, "-m", *map(str, command)],
                cwd=Path(__file__).resolve().parents[1],
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        write_json(
            args.output / (name + "-stage.json"),
            {"exit_code": result.returncode, "seconds": time.perf_counter() - before},
        )
        if result.returncode:
            raise RuntimeError("Preserve completed city outputs; inspect failed stage " + name)
    record = {
        "schema": "kaggle-checkpoint-outbox-v1",
        "status": "awaiting_external_publication",
        "plan_sha256": plan_sha,
        "family": cohort["namespace"],
        "start": args.start,
        "end": args.start + len(chunk),
        "run_ids": [r["run_id"] for r in executed],
        "family_total": len(all_rows),
        "code": code,
        "environment": actual,
        "cloud_root": str(working),
        "catalog_sha256": digest(args.output / "exports/catalog.json"),
        "previous_publication_sha256": args.previous_handoff_sha256,
        "scope": "Bounded city targets from three independently published own-city Sources. Local outbox only; complete external transport/Source/daily/state verification required before next. No Source fit, Final or city-completion claim.",
    }
    artifact = package_outbox(args.output / "exports", record, args.output / "handoff.zip")
    write_json(
        args.output / "handoff.json",
        {**record, "artifact": artifact, "wall_seconds": time.perf_counter() - started},
    )
    print(
        "CITY_TARGET_HANDOFF_READY_STOPPED",
        json.dumps({k: v for k, v in {**record, "artifact": artifact}.items() if k != "code"}),
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cloud-root", choices=CLOUD_ROOTS, default=CLOUD_ROOTS[0])
    for name in (
        "inputs-root",
        "cohort",
        "primary-analysis",
        "environment-profile",
        "sources-root",
        "output",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("cohort-sha256", "primary-sha256", "environment-sha256", "sources-sha256"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--previous-handoff", type=Path)
    parser.add_argument("--previous-handoff-sha256")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
