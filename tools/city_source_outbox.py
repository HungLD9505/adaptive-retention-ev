"""One frozen CHARGED Source seed in a local Kaggle outbox; never target/Final fitting."""

import argparse
import contextlib
import json
import os
import time
import zipfile
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import numpy as np
import torch

from ev_models.checkpoint import digest, write_json
from ev_models.run import environment
from ev_models.run import execute as train_source
from ev_runner.run import runtime_code
from tools.charged_development_cohort import CITIES
from tools.charged_matched_development import backup_context, primary_recipe, validate_cohort
from tools.comparison_matrix import CachedInputs
from tools.durable_run_backup import RunBackup


def require_outbox(output: Path, inputs_root: Path, working: Path) -> None:
    """Permit a new cloud output only; never confuse it with mounted storage."""
    target, data, cloud = output.resolve(), inputs_root.resolve(), working.resolve()
    if (
        not working.is_dir()
        or target == cloud
        or not target.is_relative_to(cloud)
        or target.is_relative_to(data)
        or data.is_relative_to(target)
        or output.exists()
        or output.is_symlink()
    ):
        raise ValueError("New separate Kaggle local outbox required; no overwrite or fake mount")


def validate_environment(actual: dict, profile: dict, numpy_version: str) -> None:
    """Reject environment drift before Source fitting; no cross-runtime assumption."""
    if (
        profile.get("schema") != "ev-city-cloud-environment-v1"
        or profile.get("environment") != actual
        or profile.get("numpy") != numpy_version
        or actual.get("device") != "cuda"
        or actual.get("deterministic_algorithms") is not True
    ):
        raise ValueError("Pinned deterministic cloud CUDA/NumPy profile required")


def package_source(backup: Path, record: dict, destination: Path) -> dict:
    """Transport one verified Source pair and its context; remote proof is still external."""
    seed = record.get("seed")
    if type(seed) is not int or seed not in (42, 43, 44):
        raise ValueError("One declared Source seed required")
    names = {"context.json", f"source-seed{seed}.zip", f"source-seed{seed}.receipt.json"}
    if {p.name for p in backup.iterdir()} != names:
        raise ValueError("Only the complete one-Source pair/context may be exported")
    if any((backup / name).is_symlink() or not (backup / name).is_file() for name in names):
        raise ValueError("Regular Source payload required")
    context = json.loads((backup / "context.json").read_text())
    if (
        record.get("schema") != "ev-one-city-source-outbox-v1"
        or record.get("status") != "awaiting_external_publication"
        or context.get("schema") != "ev-kaggle-city-source-outbox-v1"
        or record.get("namespace") not in {f"charged-{city}" for city in CITIES}
        or context.get("namespace") != record["namespace"].split("-")
        or record.get("context_sha256") != digest(backup / "context.json")
    ):
        raise ValueError("Bound one-city local Source context required")
    receipt = json.loads((backup / f"source-seed{seed}.receipt.json").read_text())
    archive = backup / f"source-seed{seed}.zip"
    if (
        receipt.get("context_sha256") != digest(backup / "context.json")
        or receipt.get("name") != f"source-seed{seed}"
        or receipt.get("record", {}).get("kind") != "source"
        or receipt["record"]["entry"]["seed"] != seed
        or archive.stat().st_size != receipt.get("bytes")
        or digest(archive) != receipt.get("sha256")
        or receipt["record"]["entry"]["sha256"] != record.get("source_checkpoint_sha256")
    ):
        raise ValueError("Source receipt/context/checkpoint fingerprint differs")
    with zipfile.ZipFile(archive) as original:
        envelope = json.loads(original.read("backup-record.json"))
        if (
            original.testzip() is not None
            or envelope.get("schema") != "ev-completed-backup-v1"
            or any(receipt.get(k) != value for k, value in envelope.items())
        ):
            raise ValueError("Corrupt Source archive or mismatched committed record")
    manifest = {}
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_STORED) as output:
        for name in sorted(names):
            path = backup / name
            if path.is_symlink() or not path.is_file():
                raise ValueError("Regular Source payload required")
            manifest[name] = {"bytes": path.stat().st_size, "sha256": digest(path)}
            output.write(path, "backup/" + name)
        output.writestr("manifest.json", json.dumps(manifest, indent=2))
        output.writestr("source-handoff-record.json", json.dumps(record, indent=2))
    with zipfile.ZipFile(destination) as output:
        if output.testzip() is not None:
            raise ValueError("Corrupt Source wrapper; preserve failed bytes")
    return {
        "name": destination.name,
        "bytes": destination.stat().st_size,
        "sha256": digest(destination),
    }


def run(args: argparse.Namespace) -> None:
    """Train exactly one city Source, then stop before any target execution."""
    started = time.perf_counter()
    if args.seed not in (42, 43, 44) or not torch.cuda.is_available():
        raise ValueError("A declared Source seed and cloud CUDA are required")
    for path, pin in (
        (args.cohort, args.cohort_sha256),
        (args.primary_analysis, args.primary_sha256),
        (args.environment_profile, args.environment_sha256),
    ):
        if digest(path) != pin:
            raise ValueError("Changed frozen Source dependency: " + path.name)
    require_outbox(args.output, args.inputs_root, Path("/kaggle/working"))
    code = runtime_code()
    if code["dirty"]:
        raise ValueError("Clean committed code required")
    torch.use_deterministic_algorithms(True)
    actual = environment("cuda")
    profile = json.loads(args.environment_profile.read_text())
    validate_environment(actual, profile, np.__version__)
    cohort, primary = (json.loads(p.read_text()) for p in (args.cohort, args.primary_analysis))
    if cohort.get("namespace") not in {f"charged-{city}" for city in CITIES}:
        raise ValueError("Only a declared separate CHARGED city is permitted")
    if not primary.get("collection_lineage") or not primary.get("matrix_identities"):
        raise ValueError("Authenticated primary selection lineage required; no city tuning")
    epoch, _, source_config = primary_recipe(primary, args.seed, "not-used-by-source")
    data = {
        b: CachedInputs(
            args.inputs_root / f"{cohort['namespace']}-{b}d",
            cohort["budgets"][str(b)]["manifest_sha256"],
        )
        for b in (7, 14, 28)
    }
    validate_cohort(data, cohort)
    expected_examples = sum(
        r["initial_trainable"] for r in data[7].entities.values() if r["role"] == "source"
    )
    if expected_examples <= 0:
        raise ValueError("No prefix-trainable same-city Source data")
    args.output.mkdir(parents=True, exist_ok=False)
    study = args.output / "study"
    study.mkdir()
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
        schema="ev-kaggle-city-source-outbox-v1", backend="local_pending_external_publication"
    )
    context.update(environment_profile_sha256=args.environment_sha256, numpy_version=np.__version__)
    backup = RunBackup(study, args.output / "local-completed", context, data)
    config = {
        "training": {**source_config, "seed": args.seed, "epochs": epoch},
        "lambda": 0,
        "development_entities": ["not-used-by-source"],
        "evaluation_origins": 90,
    }
    start_record = {
        "schema": "ev-one-city-source-outbox-v1",
        "namespace": cohort["namespace"],
        "seed": args.seed,
        "source_epochs": epoch,
        "cohort_sha256": args.cohort_sha256,
        "primary_sha256": args.primary_sha256,
        "environment_profile_sha256": args.environment_sha256,
        "source_population_sha256": data[7].source_hash,
        "source_manifest_sha256": data[7].sha256,
        "expected_source_examples": expected_examples,
        "code": code,
        "environment": actual,
        "training": config["training"],
        "scope": "One own-city Source only; local outbox is not Drive. No target/Final fitting or automatic next seed. Independent download/restore/Drive-readback acceptance required.",
    }
    write_json(args.output / "source-start.json", start_record)
    if runtime_code() != code:
        raise ValueError("Output setup or concurrent edits changed clean code; stop before fitting")
    with (study / f"source-seed{args.seed}.log").open("x") as log, contextlib.redirect_stdout(log):
        report = train_source(
            "source", data[7], config, study / f"source-seed{args.seed}", device="cuda"
        )
    if (
        report.get("status") != "technical_success"
        or report["training_examples"] != expected_examples
    ):
        raise ValueError("Actual Source count/status differs; preserve outputs")
    checkpoint = study / f"source-seed{args.seed}" / f"epoch-{epoch}.pt"
    entry = {
        "seed": args.seed,
        "run": report,
        "path": str(checkpoint),
        "sha256": digest(checkpoint),
    }
    write_json(study / f"source-seed{args.seed}-complete.json", entry)
    backup.source(entry)
    record = {
        **start_record,
        "status": "awaiting_external_publication",
        "source_checkpoint_sha256": entry["sha256"],
        "context_sha256": backup.context_sha,
        "source_before_transport_wrapper_seconds": time.perf_counter() - started,
    }
    artifact = package_source(backup.root, record, args.output / "source-handoff.zip")
    handoff = {
        **record,
        "artifact": artifact,
        "source_outbox_seconds": time.perf_counter() - started,
    }
    write_json(args.output / "handoff.json", handoff)
    print("CITY_SOURCE_LOCAL_READY_STOPPED", json.dumps(handoff), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs-root", "cohort", "primary-analysis", "environment-profile", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("cohort-sha256", "primary-sha256", "environment-sha256"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--seed", type=int, choices=(42, 43, 44), required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
