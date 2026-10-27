"""One bounded14-method Final unit with immutable per-run mounted backups."""

import argparse
import contextlib
import copy
import json
import shutil
import time
import zipfile
from pathlib import Path

import torch

from ev_models.checkpoint import digest, write_json
from ev_models.run import environment
from ev_models.training import seed_everything
from ev_runner.final_gate import FinalAccess, FinalInputRun, authorize
from ev_runner.replay import Replay
from ev_runner.run import ROOT, execute
from tools.durable_run_backup import require_drive_mount
from tools.export_development import put_file, put_run, safe_name
from tools.verify_comparison import verify_run
from tools.verify_latest_states import verify_state


class CachedFinalInputs(FinalInputRun):
    """Reuse one authenticated target prefix in a single14-method unit."""

    def __init__(self, root: Path, sha256: str, access: FinalAccess) -> None:
        super().__init__(root, sha256, access)
        self._training_cache = {}

    def training(self, role: str, entity_id: str | None = None) -> list[dict]:
        self.check_target(entity_id)
        self.verify("training.jsonl")
        key = role, entity_id
        if key not in self._training_cache:
            self._training_cache[key] = super().training(role, entity_id)
        return self._training_cache[key]


def unit_at(lock: dict, index: int, lane: int) -> dict:
    """Keep the frozen metadata order and disjoint two-lane unit assignment."""
    if type(index) is not int or not 0 <= index < len(lock["unit_order"]):
        raise ValueError("Unit index outside frozen scope")
    if lane not in (0, 1) or index % 2 != lane:
        raise ValueError("Wrong frozen worker lane")
    return lock["unit_order"][index]


def check_receipt(lock_sha: str, index: int, lane: int, path: Path | None, sha: str | None) -> None:
    """No next same-lane unit without root's fresh external-content acceptance."""
    if index < 2:
        if path is not None or sha is not None:
            raise ValueError("First lane unit has no predecessor receipt")
        return
    if path is None or sha is None or digest(path) != sha:
        raise ValueError("Verified predecessor receipt and exact hash required")
    record = json.loads(path.read_text())
    if (
        record.get("schema") != "ev-final-unit-acceptance-v1"
        or record.get("lock_sha256") != lock_sha
        or record.get("unit_index") != index - 2
        or record.get("lane") != lane
        or record.get("independent_content_verified") is not True
        or record.get("native_readback_verified") is not True
        or record.get("accepted_method_cells") != 14
    ):
        raise ValueError("Predecessor publication scope/content/readback differs")


def check_packages(root: Path, lock: dict) -> None:
    """Require the actual preflight dependency inventory before any target values."""
    import subprocess
    import sys

    raw = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True)
    actual = sorted(line.strip() for line in raw.splitlines() if line.strip())
    expected = json.loads((root / lock["runtime_packages_path"]).read_text())["pip_freeze"]
    if actual != expected:
        raise ValueError("Installed packages differ from immutable runtime preflight")


def run(args: argparse.Namespace) -> None:
    access = authorize(args.lock, ROOT)
    entry = unit_at(access.lock, args.unit_index, args.lane)
    check_receipt(
        access.sha256, args.unit_index, args.lane, args.previous_receipt, args.previous_sha256
    )
    seed_everything(entry["seed"])
    if not torch.cuda.is_available() or environment("cuda") != access.lock["runtime_profile"]:
        raise ValueError("Actual CUDA profile differs from execution lock")
    check_packages(ROOT, access.lock)
    require_drive_mount(args.backup_root, args.drive_mount)
    if shutil.disk_usage(args.output.parent).free < 2 * 1024**3:
        raise ValueError("At least2GiB scratch required before bounded unit")
    ns, budget, entity, seed = (
        tuple(entry["namespace"]),
        entry["history_days"],
        entry["entity_id"],
        entry["seed"],
    )
    group = next(
        g
        for g in access.lock["groups"]
        if tuple(g["namespace"]) == ns and g["history_days"] == budget
    )
    # Authentication of metadata, code and authorization precedes this value reader.
    data = CachedFinalInputs(
        args.inputs_root / f"{'-'.join(ns)}-{budget}d", group["input_manifest_sha256"], access
    )
    data.check_target(entity)
    replay = Replay(data, entity, 90)
    replay.prepare_label_index()
    args.output.mkdir(parents=True, exist_ok=False)
    args.backup_root.mkdir(parents=True, exist_ok=False)
    context = {
        "lock_sha256": access.sha256,
        "authorization": access.provenance(),
        "unit_index": args.unit_index,
        "lane": args.lane,
        "unit": entry,
        "environment": environment("cuda"),
        "scope": "Real bounded Final; independent peer review waived by explicit lead exception",
    }
    write_json(args.output / "context.json", context)
    shutil.copyfile(args.output / "context.json", args.backup_root / "context.json")
    started = time.perf_counter()
    rows, proofs, parts = [], [], []
    for variant in access.lock["required_unique_variants"]:
        if time.perf_counter() - started > 20 * 60:
            raise TimeoutError("Bounded unit exceeded20minutes; preserve completed backups")
        name = safe_name(f"final-{'-'.join(ns)}-{entity}-{budget}d-{variant}-seed{seed}")
        cfg = copy.deepcopy(access.lock["method_configs"][str(seed)][variant])
        cfg["development_entities"] = [entity]
        source = group["sources"][str(seed)]
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        with (
            (args.output / f"{name}.log").open("x") as log,
            contextlib.redirect_stdout(log),
            contextlib.redirect_stderr(log),
        ):
            row = execute(
                data,
                entity,
                ROOT / source["path"],
                source["sha256"],
                cfg,
                args.output / name,
                device="cuda",
                prepared_replay=replay,
                ensemble_sources=tuple(
                    (ROOT / s["path"], s["sha256"]) for s in group["sources"].values()
                )
                if variant == "uncertainty"
                else (),
            )
        row["comparison_variant"] = variant
        daily = verify_run(args.output / name, data.root, final_access=access, final_inputs=data)
        state = verify_state(args.output / name, row)
        proof = {"variant": variant, "daily": daily, "latest_state": state}
        path = args.output / f"{name}.zip"
        with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED) as z:
            put_run(z, args.output, row, state, daily["historical_states_intentionally_omitted"])
            put_file(z, f"logs/{name}.log", args.output / f"{name}.log")
        with zipfile.ZipFile(path) as z:
            if z.testzip() is not None:
                raise ValueError("Completed Final run ZIP failed CRC")
        backup = args.backup_root / path.name
        shutil.copyfile(path, backup)
        if digest(backup) != digest(path):
            raise ValueError("Mounted Final run copy differs")
        part = {
            "name": path.name,
            "bytes": path.stat().st_size,
            "sha256": digest(path),
            "run_id": name,
        }
        write_json(
            args.backup_root / f"{name}.receipt.json",
            {**part, "proof": proof, "context_sha256": digest(args.output / "context.json")},
        )
        rows.append(row)
        proofs.append(proof)
        parts.append(part)
        write_json(
            args.output / f"progress-{len(rows):02d}.json",
            {
                "completed_method_cells": len(rows),
                "parts": parts,
                "scope": "Mounted completed backups; root native readback still pending",
            },
        )
        print("FINAL_RUN_COMPLETED", args.unit_index, len(rows), 14, name, flush=True)
    if len(rows) != 14 or {r["comparison_variant"] for r in rows} != set(
        access.lock["required_unique_variants"]
    ):
        raise ValueError("Incomplete Final whole unit")
    origin_sets = []
    for row in rows:
        path = args.output / row["run_id"]
        issued = []
        scored = []
        for tick in sorted(path.glob("tick-*")):
            f = json.loads((tick / "forecasts.json").read_text())
            if f:
                issued.append(f["origin"])
            scored.extend(
                e["origin"]
                for e in map(json.loads, (tick / "events.jsonl").read_text().splitlines())
                if e["event"] == "score"
            )
        origin_sets.append((issued, scored))
    if any(value != origin_sets[0] for value in origin_sets):
        raise ValueError("Within-unit issued/scored origins differ")
    write_json(
        args.output / "unit-matrix.json",
        {
            "status": "technical_success",
            "context": context,
            "runs": rows,
            "proofs": proofs,
            "parts": parts,
            "wall_seconds": time.perf_counter() - started,
        },
    )
    shutil.copyfile(args.output / "unit-matrix.json", args.backup_root / "unit-matrix.json")
    archive = args.backup_root.parent / f"final-unit-{args.unit_index:04d}-publication.zip"
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_STORED) as z:
        for path in sorted(args.backup_root.iterdir()):
            if path.is_file():
                put_file(z, path.name, path)
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError("Final unit publication failed CRC")
    print(
        "FINAL_UNIT_PUBLICATION_READY",
        json.dumps(
            {
                "unit_index": args.unit_index,
                "lane": args.lane,
                "cells": 14,
                "archive": str(archive),
                "bytes": archive.stat().st_size,
                "sha256": digest(archive),
                "wall_seconds": time.perf_counter() - started,
            }
        ),
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("lock", "inputs-root", "output", "backup-root", "drive-mount", "previous-receipt"):
        parser.add_argument("--" + name, type=Path, required=name != "previous-receipt")
    for name in ("unit-index", "lane"):
        parser.add_argument("--" + name, type=int, required=True)
    parser.add_argument("--previous-sha256")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
