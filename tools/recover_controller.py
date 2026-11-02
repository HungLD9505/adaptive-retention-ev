"""Recover completed Colab controller runs from immutable Drive backup chunks."""

import argparse
import json
import shutil
import stat
import time
import zipfile
from pathlib import Path

import torch

from ev_evaluation.artifacts import authenticate_matrix
from ev_models.checkpoint import digest, write_json
from ev_runner.run import runtime_code
from ev_runner.state import state_digest
from tools.controller_calibration import summarize, validate_profile
from tools.fixed_retention_sweep import selected_sources


def inspect_chunk(path: Path) -> list[dict]:
    """CRC-check and reject unsafe paths, symlinks, extra runs or mismatched reports."""
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("Corrupt backup chunk")
        rows = json.loads(archive.read("completed-runs.json"))
        names = [row["run_id"] for row in rows]
        if (
            not rows
            or len(set(names)) != len(names)
            or any(Path(name).name != name or name in (".", "..") for name in names)
        ):
            raise ValueError("Unique safe completed-run identities required")
        members = set()
        for info in archive.infolist():
            p = Path(info.filename)
            if (
                info.filename in members
                or p.is_absolute()
                or ".." in p.parts
                or stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK
            ):
                raise ValueError("Unsafe or duplicate backup member")
            members.add(info.filename)
            if info.filename != "completed-runs.json" and (
                len(p.parts) < 3 or p.parts[0] != "study" or p.parts[1] not in names
            ):
                raise ValueError("Unexpected backup member outside completed runs")
        for row in rows:
            report = json.loads(archive.read(f"study/{row['run_id']}/run.json"))
            if any(row.get(k) != v for k, v in report.items()):
                raise ValueError("Backup row contradicts saved run report")
    return rows


def run(args: argparse.Namespace) -> None:
    started = time.perf_counter()
    code = runtime_code()
    if code["dirty"]:
        raise ValueError("Clean committed recovery code required")
    registry = json.loads(args.registry.read_text())
    profile = json.loads(args.profile.read_text())
    validate_profile(profile)
    if digest(args.selection) != profile["selection_sha256"]:
        raise ValueError("Changed identified Development cohort")
    cohort = json.loads(args.selection.read_text())
    study = authenticate_matrix(args.source_study, args.source_verification)
    proof = json.loads(args.source_verification.read_text())
    if proof.get("status") != "verified" or proof.get("matrix_sha256") != digest(args.source_study):
        raise ValueError("Authenticated Source study required")
    epoch, sources = selected_sources(study, cohort, profile)
    chunks, rows = [], []
    for item in registry["files"]:
        name = item["name"]
        if Path(name).name != name:
            raise ValueError("Unsafe archive identifier")
        path = args.archive_dir / name
        if path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            raise ValueError("Downloaded backup fingerprint mismatch")
        values = inspect_chunk(path)
        if len(values) != item["completed_runs"]:
            raise ValueError("Backup run count changed")
        chunks.append(path)
        rows.extend(values)
    selection = summarize(rows, cohort)
    original = rows[0]["code"]
    if (
        original["dirty"]
        or original["files"] != code["files"]
        or any(row["code"] != original for row in rows)
    ):
        raise ValueError("Original completed runs must share identified unchanged algorithms")
    args.output.mkdir(parents=True, exist_ok=False)
    state_count = 0
    for path in chunks:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if info.filename == "completed-runs.json":
                    continue
                relative = Path(info.filename).relative_to("study")
                target = args.output / relative
                if target.exists():
                    raise ValueError("Duplicate/overwriting recovered file")
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as src, target.open("xb") as dst:
                    shutil.copyfileobj(src, dst)
    for seed, source in sources.items():
        src = args.source_study.parent / f"source-seed{seed}" / f"epoch-{epoch}.pt"
        if digest(src) != source["sha256"]:
            raise ValueError("Changed original Source weights")
        target = args.output / f"source-seed{seed}" / src.name
        target.parent.mkdir()
        shutil.copy2(src, target)
        sources[seed] = {**source, "original_path": source["path"], "path": str(target.resolve())}
    for row in rows:
        seed = row["binding"]["config"]["initial_training"]["seed"]
        if row["source_checkpoint_sha256"] != sources[seed]["sha256"]:
            raise ValueError("Recovered run Source binding differs")
        ticks = sorted((args.output / row["run_id"]).glob("tick-*"))
        value = torch.load(ticks[-1] / "state.pt", map_location="cpu", weights_only=True)
        if {str(k): state_digest(v) for k, v in value["branches"].items()} != row[
            "final_branch_state_sha256"
        ]:
            raise ValueError("Recovered latest state content differs")
        state_count += 1
    matrix = {
        "scope": "Original completed Colab controller grid reconstructed from verified backup bytes; no retraining or Final",
        "profile_sha256": digest(args.profile),
        "source_study_sha256": digest(args.source_study),
        "source_epochs": epoch,
        "selection_sha256": digest(args.selection),
        "sources": sources,
        "code": original,
        "runs": rows,
        "status": "technical_success",
        "wall_seconds": None,
        "reconstruction": {
            "code": code,
            "registry_sha256": digest(args.registry),
            "archives": len(chunks),
            "latest_states_cpu_rehashed": state_count,
            "wall_seconds": time.perf_counter() - started,
            "original_loop_wall_seconds": None,
            "completed_run_elapsed_seconds_sum": sum(r["elapsed_seconds"] for r in rows),
            "limits": "Original complete matrix/loop timer lost on runtime eviction. Header rebuilt from pinned profile/source/cohort and original saved run reports. Full daily independent verification still required; no local training.",
        },
    }
    write_json(args.output / "matrix.json", matrix)
    write_json(args.output / "selection.json", selection)
    write_json(args.output / "profile.json", profile)
    print(
        json.dumps(
            {
                "status": "recovered",
                "completed_runs": len(rows),
                "latest_states_cpu_rehashed": state_count,
                "training_performed": False,
            }
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "archive-dir",
        "registry",
        "profile",
        "selection",
        "source-study",
        "source-verification",
        "output",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
