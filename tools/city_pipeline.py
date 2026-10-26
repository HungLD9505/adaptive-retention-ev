"""One accepted CHARGED city with mandatory completed-run backup and canonical handoff."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from tools.durable_run_backup import require_drive_mount
from tools.export_development import safe_name


def sha(path: str | Path) -> str:
    """Hash bytes without loading full city artifacts into memory."""
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def save_new(path: Path, value: dict) -> None:
    """Keep every existing run/phase record unchanged."""
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def publish_file(source: Path, destination: Path, *, expected_sha256: str | None = None) -> None:
    """Publish a new, hash-read-back copy; preserve pending bytes on failure."""
    if (
        source.is_symlink()
        or not source.is_file()
        or destination.exists()
        or destination.is_symlink()
    ):
        raise ValueError("Regular source and unused destination required")
    expected_size = source.stat().st_size
    expected_hash = expected_sha256 or sha(source)
    pending = destination.with_name(destination.name + ".pending")
    with source.open("rb") as input_stream, pending.open("xb") as output_stream:
        shutil.copyfileobj(input_stream, output_stream)
        output_stream.flush()
        os.fsync(output_stream.fileno())
    if pending.stat().st_size != expected_size or sha(pending) != expected_hash:
        raise ValueError("Handoff copy changed; preserve pending file")
    if destination.exists() or destination.is_symlink():
        raise ValueError("Concurrent handoff writer; preserve pending file")
    pending.rename(destination)


def training_command(args: argparse.Namespace, root: Path, study: Path) -> list[str | Path]:
    """Require completed-run backup for every Source/target; never alter method configs."""
    command = [
        "tools.charged_matched_development",
        "--inputs-root",
        args.inputs_root,
        "--cohort",
        root / "cohort.json",
        "--cohort-sha256",
        args.cohort_sha256,
        "--primary-analysis",
        root / "primary-analysis.json",
        "--primary-sha256",
        args.primary_sha256,
        "--output",
        study,
        "--backup-root",
        args.backup_root,
        "--drive-mount",
        args.drive_mount,
    ]
    if args.resume_backup:
        command.append("--resume-backup")
    return command


def run_stage(
    name: str, argv: list[str | Path], repo: Path, root: Path, handoff: Path, metadata: dict
) -> None:
    """Persist stage command/start/terminal result, and fail before advancing on error."""
    safe_name(name)
    command = [sys.executable, "-u", "-m", *map(str, argv)]
    start_path = root / (name + "-start.json")
    save_new(start_path, {"name": name, "command": command, "status": "started"})
    publish_file(start_path, handoff / start_path.name)
    begin = time.perf_counter()
    with (root / (name + ".log")).open("x") as log:
        result = subprocess.run(command, cwd=repo, stdout=log, stderr=subprocess.STDOUT)
    stage = {
        "name": name,
        "command": command,
        "exit_code": result.returncode,
        "wall_seconds": time.perf_counter() - begin,
    }
    metadata["stages"].append(stage)
    save_new(root / (name + "-stage.json"), stage)
    for path in (root / (name + ".log"), root / (name + "-stage.json")):
        publish_file(path, handoff / path.name)
    print(json.dumps(stage), flush=True)
    if result.returncode:
        raise RuntimeError("Stage failed; preserve all outputs: " + name)


def handoff_exports(exports: Path, destination: Path) -> None:
    """Account for every canonical part and refuse missing, changed or extra payloads."""
    catalog_path = exports / "catalog.json"
    catalog_bytes = catalog_path.read_bytes()
    catalog = json.loads(catalog_bytes)
    parts = catalog["parts"]
    names = [safe_name(p["name"]) for p in parts]
    if (
        catalog.get("status") != "complete"
        or len(set(names)) != len(names)
        or "catalog.json" in names
    ):
        raise ValueError("Invalid completed export catalog")
    if {p.name for p in exports.iterdir()} != {*names, "catalog.json"}:
        raise ValueError("Missing/extra export payloads")
    for part in parts:
        path = exports / part["name"]
        if path.stat().st_size != part["bytes"] or sha(path) != part["sha256"]:
            raise ValueError("Changed export payload")
    destination.mkdir(exist_ok=False)
    for part in parts:
        publish_file(
            exports / part["name"], destination / part["name"], expected_sha256=part["sha256"]
        )
    publish_file(
        catalog_path,
        destination / "catalog.json",
        expected_sha256=hashlib.sha256(catalog_bytes).hexdigest(),
    )


def run_pipeline(args: argparse.Namespace) -> None:
    """Run the accepted city stages; complete is still pending off-runtime/peer acceptance."""
    started = time.perf_counter()
    if args.repo.resolve() != Path(__file__).resolve().parents[1]:
        raise ValueError("Pipeline module and executed repository must be the same checkout")
    for path, expected in (
        (args.cohort, args.cohort_sha256),
        (args.primary_analysis, args.primary_sha256),
        (args.density_contexts, args.density_sha256),
    ):
        if sha(path) != expected:
            raise ValueError("Changed identified pipeline dependency: " + path.name)
    code = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=args.repo, text=True).strip()
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=args.repo, text=True).strip():
        raise ValueError("Clean committed repository required")
    cohort, primary = (json.loads(p.read_text()) for p in (args.cohort, args.primary_analysis))
    if (
        cohort["namespace"]
        not in {
            "charged-JHB",
            "charged-SPO",
            "charged-MEL",
            "charged-LOA",
            "charged-SZH",
            "charged-AMS",
        }
        or cohort["seeds"] != [42, 43, 44]
        or cohort["days"] != 90
    ):
        raise ValueError("Only the accepted six-city Development replication is permitted")
    if args.source_examples <= 0:
        raise ValueError("Positive source metadata example count required")
    require_drive_mount(args.backup_root, args.drive_mount)
    require_drive_mount(args.handoff_root, args.drive_mount)
    if args.output.resolve().is_relative_to(args.inputs_root.resolve()):
        raise ValueError("Keep outputs outside accepted input data")
    if args.backup_root.resolve().is_relative_to(
        args.handoff_root.resolve()
    ) or args.handoff_root.resolve().is_relative_to(args.backup_root.resolve()):
        raise ValueError("Backup and canonical handoff directories must be separate")
    args.output.mkdir(parents=True, exist_ok=False)
    args.handoff_root.mkdir(parents=True, exist_ok=False)
    root = args.output
    for path, name in (
        (args.cohort, "cohort.json"),
        (args.primary_analysis, "primary-analysis.json"),
        (args.density_contexts, "density-contexts.json"),
        (args.repo / "configs/issue23/analysis-profile.json", "analysis-profile.json"),
        (Path(__file__), "pipeline-source.py"),
    ):
        shutil.copyfile(path, root / name)
    study, daily, states, analysis, exports = (
        root / n
        for n in ("study", "daily-verification.json", "latest-states.json", "analysis", "exports")
    )
    metadata = {
        "scope": "One accepted supplementary city; no Final, city retuning, cleanup or off-runtime acceptance",
        "namespace": cohort["namespace"],
        "code_commit": code,
        "pipeline_sha256": sha(__file__),
        "cohort_sha256": args.cohort_sha256,
        "primary_summary_sha256": args.primary_sha256,
        "density_sha256": args.density_sha256,
        "expected_source_examples": args.source_examples,
        "source_epochs": primary["choices"]["source_epochs"],
        "expected_target_runs": sum(len(g["entities"]) for g in cohort["budgets"].values())
        * len(cohort["seeds"])
        * len(primary["choices"]["unique_method_names"]),
        "command": sys.argv,
        "stages": [],
    }
    metadata["backup_root"] = str(args.backup_root)
    metadata["resume_backup"] = args.resume_backup
    metadata["remote_handoff_scope"] = (
        "Mounted filesystem publication; independent remote download/reverification remains required"
    )
    save_new(root / "pipeline-start.json", metadata)
    for path in root.iterdir():
        if path.is_file():
            publish_file(path, args.handoff_root / path.name)
    metadata["setup_before_training_seconds"] = time.perf_counter() - started

    def stage(name: str, argv: list[str | Path]) -> None:
        run_stage(name, argv, args.repo, root, args.handoff_root, metadata)

    try:
        stage("training", training_command(args, root, study))
        matrix = json.loads((study / "matrix.json").read_text())
        if (
            matrix["status"] != "technical_success"
            or len(matrix["runs"]) != metadata["expected_target_runs"]
            or {s["seed"] for s in matrix["sources"]} != set(cohort["seeds"])
        ):
            raise ValueError("Incomplete city run matrix or Source population")
        for source in matrix["sources"]:
            if source["run"]["training_examples"] != args.source_examples:
                raise ValueError("Actual Source examples contradict prior metadata capacity check")
        stage(
            "daily-verification",
            [
                "tools.verify_comparison",
                "--matrix",
                study / "matrix.json",
                "--inputs-root",
                args.inputs_root,
                "--output",
                daily,
                "--cache-inputs",
            ],
        )
        stage(
            "latest-state-verification",
            [
                "tools.verify_latest_states",
                "--matrix",
                study / "matrix.json",
                "--verification",
                daily,
                "--output",
                states,
            ],
        )
        stage(
            "analysis",
            [
                "tools.analyze_charged_matched",
                "--matrix",
                study / "matrix.json",
                "--verification",
                daily,
                "--cohort",
                root / "cohort.json",
                "--cohort-sha256",
                args.cohort_sha256,
                "--primary-analysis",
                root / "primary-analysis.json",
                "--primary-sha256",
                args.primary_sha256,
                "--analysis-profile",
                root / "analysis-profile.json",
                "--inputs-root",
                args.inputs_root,
                "--density-contexts",
                root / "density-contexts.json",
                "--density-sha256",
                args.density_sha256,
                "--output",
                analysis,
            ],
        )
        command = [
            "tools.export_development",
            "--matrix",
            study / "matrix.json",
            "--verification",
            daily,
            "--latest-states",
            states,
            "--source-root",
            study,
            "--output",
            exports,
        ]
        for name, path in [
            ("city-analysis.json", analysis / "summary.json"),
            ("city-runs.csv", analysis / "runs.csv"),
            ("city-cohort.json", root / "cohort.json"),
            ("primary-analysis.json", root / "primary-analysis.json"),
            ("analysis-profile.json", root / "analysis-profile.json"),
            ("density-contexts.json", root / "density-contexts.json"),
            ("pipeline-source.py", root / "pipeline-source.py"),
            ("pipeline-start.json", root / "pipeline-start.json"),
        ]:
            command += ["--attachment", name + "=" + str(path)]
        stage("export", command)
        handoff_started = time.perf_counter()
        handoff_exports(exports, args.handoff_root / "exports")
        for path in (
            study / "matrix.json",
            daily,
            states,
            analysis / "summary.json",
            analysis / "runs.csv",
        ):
            publish_file(path, args.handoff_root / path.name)
        metadata.update(
            status="technical_success_pending_offruntime_and_peer_acceptance",
            canonical_handoff_seconds=time.perf_counter() - handoff_started,
            wall_seconds=time.perf_counter() - started,
            matrix_sha256=sha(study / "matrix.json"),
            catalog_sha256=sha(exports / "catalog.json"),
        )
        save_new(root / "pipeline-complete.json", metadata)
        publish_file(root / "pipeline-complete.json", args.handoff_root / "pipeline-complete.json")
        print(
            "CITY PIPELINE COMPLETE; TRANSFER/RESTORE/REVIEW STILL REQUIRED",
            json.dumps(metadata),
            flush=True,
        )
    except Exception as error:
        metadata.update(
            status="failed", error=repr(error), wall_seconds=time.perf_counter() - started
        )
        save_new(root / "pipeline-failed.json", metadata)
        publish_file(root / "pipeline-failed.json", args.handoff_root / "pipeline-failed.json")
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "repo",
        "inputs-root",
        "cohort",
        "primary-analysis",
        "density-contexts",
        "output",
        "backup-root",
        "drive-mount",
        "handoff-root",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("cohort-sha256", "primary-sha256", "density-sha256"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--source-examples", type=int, required=True)
    parser.add_argument("--resume-backup", action="store_true")
    run_pipeline(parser.parse_args())


if __name__ == "__main__":
    main()
