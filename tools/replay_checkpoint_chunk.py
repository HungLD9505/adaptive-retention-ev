"""Bounded Kaggle Development replay; local outbox is NOT a published Drive backup."""

import argparse
import contextlib
import copy
import hashlib
import json
import re
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import torch

from ev_models.checkpoint import digest, write_json
from ev_models.run import environment
from ev_runner.replay import Replay
from ev_runner.run import execute, runtime_code
from tools.comparison_matrix import CachedInputs
from tools.durable_run_backup import RunBackup
from tools.export_development import safe_name
from tools.replay_missing_primary import planned_rows, recovery_context, stage_original_sources


def select_chunk(rows: list[dict], start: int, count: int) -> list[dict]:
    """Keep original order and bound unacknowledged work to twelve complete runs."""
    if (
        type(start) is not int
        or type(count) is not int
        or not 0 <= start < len(rows)
        or not 1 <= count <= 12
    ):
        raise ValueError("Valid original offset and one to twelve runs required")
    return rows[start : start + count]


def check_handoff(
    rows: list[dict], start: int, plan_sha: str, family: str, path: Path | None, pin: str | None
) -> None:
    """Validate the external operator's hash-pinned publication receipt, not OAuth.

    The operator must actually download, verify, upload and read back the previous
    chunk before creating this receipt. This local gate cannot certify a claimed
    remote check by itself; independent readback evidence must accompany it.
    """
    if start == 0:
        if path is not None or pin is not None:
            raise ValueError("First chunk has no previous same-family publication")
        return
    raw = path.read_bytes() if path is not None else b""
    if path is None or pin is None or hashlib.sha256(raw).hexdigest() != pin:
        raise ValueError("Verified previous-publication receipt and exact hash required")
    receipt = json.loads(raw)
    first = receipt.get("start")
    artifact = receipt.get("artifact", {})
    if (
        receipt.get("schema") != "verified-kaggle-outbox-publication-v1"
        or receipt.get("plan_sha256") != plan_sha
        or receipt.get("family") != family
        or receipt.get("end") != start
        or type(first) is not int
        or not 0 <= first < start <= first + 12
        or receipt.get("run_ids") != [r["run_id"] for r in rows[first:start]]
        or receipt.get("independent_content_verified") is not True
        or receipt.get("remote_readback_verified") is not True
        or not re.fullmatch(r"[0-9a-f]{64}", artifact.get("sha256", ""))
        or type(artifact.get("bytes")) is not int
        or artifact["bytes"] <= 0
        or not re.fullmatch(
            r"https://drive\.google\.com/file/d/[A-Za-z0-9_-]{20,100}/view",
            artifact.get("drive_url", ""),
        )
    ):
        raise ValueError("Changed plan/range/IDs or missing independent publication evidence")


def package_outbox(exports: Path, record: dict, destination: Path) -> dict:
    """Wrap only checksum-verified canonical parts for one normal browser download."""
    catalog_path = exports / "catalog.json"
    catalog = json.loads(catalog_path.read_text())
    parts = catalog["parts"]
    names = [safe_name(p["name"]) for p in parts]
    run_ids = [name for p in parts if p.get("kind") == "target_runs" for name in p["run_ids"]]
    kinds = [p.get("kind") for p in parts]
    if (
        catalog.get("schema") != "ev-development-export-v1"
        or catalog.get("status") != "complete"
        or catalog.get("target_runs") != len(record["run_ids"])
        or run_ids != record["run_ids"]
        or len(set(run_ids)) != len(run_ids)
        or kinds.count("code") != 1
        or kinds.count("metadata_and_sources") != 1
        or any(k not in ("target_runs", "code", "metadata_and_sources") for k in kinds)
        or record.get("catalog_sha256") != digest(catalog_path)
        or len(set(n.casefold() for n in names)) != len(names)
        or any(Path(n).name != n or n in (".", "..", "catalog.json") for n in names)
    ):
        raise ValueError("Complete unaliased bounded export required")
    for part in parts:
        p = exports / part["name"]
        if p.is_symlink() or p.stat().st_size != part["bytes"] or digest(p) != part["sha256"]:
            raise ValueError("Changed canonical outbox part")
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("handoff-record.json", json.dumps(record, indent=2, allow_nan=False))
        archive.write(catalog_path, "package/catalog.json")
        for name in names:
            archive.write(exports / name, "package/" + name)
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise ValueError("Corrupt outbox wrapper; preserve it before retry")
        for part in parts:
            h = hashlib.sha256()
            with archive.open("package/" + part["name"]) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    h.update(block)
            if h.hexdigest() != part["sha256"]:
                raise ValueError("Canonical part changed while packaging; preserve wrapper")
    return {
        "name": destination.name,
        "bytes": destination.stat().st_size,
        "sha256": digest(destination),
    }


def run(args: argparse.Namespace) -> None:
    plan, original, rows = planned_rows(args.plan, args.plan_sha256, args.family)
    chunk = select_chunk(rows, args.start, args.count)
    check_handoff(
        rows,
        args.start,
        args.plan_sha256,
        args.family,
        args.previous_handoff,
        args.previous_handoff_sha256,
    )
    if not torch.cuda.is_available():
        raise ValueError("Cloud CUDA required; no local real-data fitting")
    code = runtime_code()
    target_environment = {**environment("cuda"), "deterministic_algorithms": True}
    working = Path("/kaggle/working").resolve(strict=True)
    if (
        code["dirty"]
        or code["files"] != original["code"]["files"]
        or not args.output.resolve().is_relative_to(working)
        or args.output.resolve() == working
        or args.output.resolve().is_relative_to(args.inputs_root.resolve())
        or plan.get("target_execution_environment") != target_environment
        or plan.get("required_numpy_version") != np.__version__
    ):
        raise ValueError("Cloud CUDA, unchanged clean core code and a new Kaggle outbox required")
    inputs = {}
    for row in chunk:
        b = row["binding"]["input"]
        budget = b["history_days"]
        if budget not in inputs:
            inputs[budget] = CachedInputs(
                args.inputs_root / f"urbanev-SZH-{budget}d", b["input_manifest_sha256"]
            )
        data = inputs[budget]
        if (
            data.entities.get((*data.namespace, b["entity_id"]), {}).get("role") != "development"
            or data.binding("target", b["entity_id"], b["source_checkpoint_sha256"]) != b
        ):
            raise ValueError("Original Development role/input/scaler binding required")
    args.output.mkdir(parents=True, exist_ok=False)
    study = args.output / "study"
    study.mkdir()
    context = recovery_context(
        plan,
        original,
        chunk,
        target_environment,
        json.loads((args.plan.parent / "source-seed42/run.json").read_text()),
    )
    context.update(
        recovery_plan_sha256=args.plan_sha256,
        recovery_family=args.family,
        backend="kaggle_local_outbox_pending_external_publication",
        start=args.start,
        end=args.start + len(chunk),
    )
    backup = RunBackup(study, args.output / "local-completed", context, inputs)
    started = time.perf_counter()
    stage_original_sources(args.plan.parent, study, original, backup)
    sources = {s: (Path(v["path"]), v["sha256"]) for s, v in backup.sources.items()}
    executed, last_key, replay = [], None, None
    for reference in chunk:
        b, cfg = reference["binding"]["input"], reference["binding"]["config"]
        budget, entity, seed = b["history_days"], b["entity_id"], cfg["initial_training"]["seed"]
        if (budget, entity) != last_key:
            replay = Replay(inputs[budget], entity, cfg["replay_days"])
            replay.prepare_label_index()
            last_key = budget, entity
        torch.cuda.reset_peak_memory_stats()
        with (
            (study / (reference["run_id"] + ".log")).open("x") as log,
            contextlib.redirect_stdout(log),
        ):
            row = execute(
                inputs[budget],
                entity,
                *sources[seed],
                cfg,
                study / reference["run_id"],
                device="cuda",
                prepared_replay=replay,
                ensemble_sources=tuple(sources[s] for s in (42, 43, 44))
                if cfg["method"]["name"] == "uncertainty"
                else (),
            )
        for field in ("recipe", "comparison_variant"):
            if field in reference:
                row[field] = reference[field]
        if row["binding"]["input"] != b or row["binding"]["config"] != cfg:
            raise ValueError("Executed config differs from frozen reference")
        backup.target(row)
        executed.append(row)
        write_json(study / "progress.json", {"runs": executed, "status": "local_outbox_only"})
        print("CHUNK_LOCAL_COMPLETED", len(executed), len(chunk), row["run_id"], flush=True)
    matrix = {k: copy.deepcopy(v) for k, v in original.items() if k not in ("runs", "status")}
    matrix.update(
        status="technical_success",
        runs=executed,
        code=code,
        scope="Completed bounded Development chunk, not a full family or remote publication",
        sources={str(k): v for k, v in backup.sources.items()},
        outbox_context=context,
        family_total=len(rows),
    )
    write_json(study / "matrix.json", matrix)
    for name, command in (
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
            ],
        ),
    ):
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
            raise RuntimeError("Preserve local outputs and inspect failed stage: " + name)
    record = {
        "schema": "kaggle-checkpoint-outbox-v1",
        "status": "awaiting_external_publication",
        "plan_sha256": args.plan_sha256,
        "family": args.family,
        "start": args.start,
        "end": args.start + len(chunk),
        "run_ids": [r["run_id"] for r in chunk],
        "family_total": len(rows),
        "code": code,
        "environment": target_environment,
        "catalog_sha256": digest(args.output / "exports/catalog.json"),
        "previous_publication_sha256": args.previous_handoff_sha256,
        "scope": "Local verified outbox only. External transport/content/Drive-readback proof required before next chunk. No autonomous continuation, Final, or full-study claim.",
    }
    artifact = package_outbox(args.output / "exports", record, args.output / "handoff.zip")
    write_json(
        args.output / "handoff.json",
        {**record, "artifact": artifact, "wall_seconds": time.perf_counter() - started},
    )
    print(
        "CHECKPOINT_OUTBOX_READY_STOPPED",
        json.dumps({k: v for k, v in {**record, "artifact": artifact}.items() if k != "code"}),
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "inputs-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--family", choices=("proxy", "matched"), required=True)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--previous-handoff", type=Path)
    parser.add_argument("--previous-handoff-sha256")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
