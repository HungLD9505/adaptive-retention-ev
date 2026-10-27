"""Export a fully verified Development matrix as small, self-contained ZIP parts."""

import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import torch

from ev_evaluation.artifacts import authenticate_matrix
from ev_models.checkpoint import digest, load_checkpoint, write_json
from ev_runner.run import runtime_code
from ev_runner.state import state_digest
from tools.analyze_core_comparisons import saved_errors
from tools.verify_latest_states import verify_state


def safe_name(name: str) -> str:
    """Use portable, single-component archive names, never traversal or drive paths."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name) or name.endswith("."):
        raise ValueError("Unsafe archive name")
    if name.split(".")[0].upper() in {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }:
        raise ValueError("Reserved archive name")
    return name


def put_file(archive: zipfile.ZipFile, name: str, path: Path, expected: str | None = None) -> None:
    """Read regular-file bytes once, authenticate them if committed, then archive them."""
    parts = PurePosixPath(name).parts
    if "/".join(parts) != name or not parts:
        raise ValueError("Canonical relative archive path required")
    for part in parts:
        safe_name(part)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Regular file required: {path.name}")
    raw = path.read_bytes()
    if expected is not None and hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"Changed committed bytes: {path.name}")
    archive.writestr(name, raw)


def put_run(
    archive: zipfile.ZipFile, parent: Path, row: dict, state_proof: dict, expected_omitted: int
) -> int:
    """Recheck full daily chains/state contents; preserve intentional historical omissions."""
    name = safe_name(row["run_id"])
    root = parent / name
    if root.is_symlink() or any(p.is_symlink() for p in root.rglob("*")):
        raise ValueError("Symlinked run content is not exportable")
    report = json.loads((root / "run.json").read_text())
    if any(row.get(k) != v for k, v in report.items()):
        raise ValueError("Changed completed run report")
    if json.loads((root / "binding.json").read_text()) != row["binding"]:
        raise ValueError("Changed run binding")
    saved_errors(root, row)
    actual = verify_state(root, row)
    if actual != state_proof:
        raise ValueError("Latest-state verification no longer matches actual contents")
    prefix = f"study/{name}/"
    allowed = {root / "binding.json", root / "run.json"}
    if "final_authorization" in row["binding"]:
        initial = root / "initial-adaptation.json"
        logs = json.loads(initial.read_text())
        if (
            logs != row["initial_logs"]
            or state_digest(logs) != row["binding"]["initial_adaptation_identity"]
        ):
            raise ValueError("Final initialization record differs from committed binding")
        allowed.add(initial)
        put_file(archive, prefix + initial.name, initial)
    omitted = 0
    for index, tick in enumerate(sorted(root.glob("tick-*"))):
        commit = json.loads((tick / "commit.json").read_text())
        if set(commit["files"]) != {"forecasts.json", "events.jsonl", "state.pt"}:
            raise ValueError("Unexpected committed file population")
        allowed.add(tick / "commit.json")
        for filename, checksum in commit["files"].items():
            path = tick / filename
            if not path.exists():
                if (
                    filename != "state.pt"
                    or index == row["ticks"] - 1
                    or row["binding"]["config"].get("state_retention", "all") != "latest"
                ):
                    raise ValueError("Missing required committed file")
                omitted += 1
                continue
            allowed.add(path)
            put_file(archive, prefix + path.relative_to(root).as_posix(), path, checksum)
        put_file(archive, prefix + tick.name + "/commit.json", tick / "commit.json")
    if omitted != expected_omitted:
        raise ValueError("Historical-state omissions differ from independent daily proof")
    if {p for p in root.rglob("*") if p.is_file()} != allowed:
        raise ValueError("Unexpected/uncommitted file in completed run")
    for filename in ("binding.json", "run.json"):
        put_file(archive, prefix + filename, root / filename)
    return len(allowed)


def checked_part(path: Path, kind: str, run_ids: list[str]) -> dict:
    """CRC-check every completed ZIP and register its exact downloaded-byte identity."""
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None or len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError("Corrupt/duplicate archive entries")
        count = len(archive.namelist())
    return {
        "name": path.name,
        "kind": kind,
        "bytes": path.stat().st_size,
        "sha256": digest(path),
        "files": count,
        "run_ids": run_ids,
        "zip_crc": "PASS",
    }


def latest_proofs(matrix_path: Path, verification: Path, matrix: dict, path: Path) -> dict:
    proof = json.loads(path.read_text())
    rows = proof["runs"]
    by_id = {r["run_id"]: r for r in rows}
    if (
        proof.get("status") != "verified"
        or proof.get("matrix_sha256") != digest(matrix_path)
        or proof.get("daily_verification_sha256") != digest(verification)
        or len(by_id) != len(rows)
        or len(by_id) != proof["latest_states"]
        or set(by_id) != {r["run_id"] for r in matrix["runs"]}
    ):
        raise ValueError("Complete bound latest-state verification required")
    return by_id


def put_sources(archive: zipfile.ZipFile, root: Path, matrix: dict) -> list[dict]:
    """CPU-load/hash-check the selected common Source models; never fit or infer."""
    entries = matrix["sources"]
    entries = (
        [{"seed": int(k), **v} for k, v in entries.items()]
        if isinstance(entries, dict)
        else entries
    )
    expected = {
        r["binding"]["config"]["initial_training"]["seed"]: r["source_checkpoint_sha256"]
        for r in matrix["runs"]
    }
    if any(
        r["source_checkpoint_sha256"]
        != expected[r["binding"]["config"]["initial_training"]["seed"]]
        or r["binding"]["input"]["source_checkpoint_sha256"] != r["source_checkpoint_sha256"]
        for r in matrix["runs"]
    ):
        raise ValueError("Source differs across target/method/budget bindings for the same seed")
    if len(entries) != len(expected) or {s["seed"] for s in entries} != set(expected):
        raise ValueError("Exactly one common Source checkpoint per declared seed required")
    result = []
    for item in entries:
        seed = item["seed"]
        path = root / f"source-seed{seed}" / f"epoch-{matrix['source_epochs']}.pt"
        if item["sha256"] != expected[seed]:
            raise ValueError("Selected Source fingerprint differs from target bindings")
        _, _, value = load_checkpoint(path, sha256=expected[seed], device="cpu")
        meta, latent = value["metadata"], value["latent_scale"]
        if (
            meta["input_binding"]["stage"] != "source"
            or value["completed_epochs"] != matrix["source_epochs"]
            or meta["training_config"]["seed"] != seed
            or latent is None
            or latent.shape != (64,)
            or not torch.isfinite(latent).all()
            or (latent < 0).any()
            or any(
                r["binding"]["source_population_sha256"] != meta["source_population_sha256"]
                for r in matrix["runs"]
            )
            or any(
                any(
                    r["binding"]["input"][k] != meta["input_binding"][k]
                    for k in ("dataset_id", "city_id")
                )
                for r in matrix["runs"]
            )
        ):
            raise ValueError("Source identity/latent scale/population mismatch")
        prefix = f"sources/source-seed{seed}/"
        put_file(archive, prefix + path.name, path, expected[seed])
        for name in ("run.json",):
            if (path.parent / name).exists():
                put_file(archive, prefix + name, path.parent / name)
        source_log = root / f"source-seed{seed}.log"
        if source_log.exists():
            put_file(archive, prefix + "stdout.log", source_log)
        result.append(
            {
                "seed": seed,
                "sha256": expected[seed],
                "bytes": path.stat().st_size,
                "source_population_sha256": meta["source_population_sha256"],
                "cpu_load": "PASS",
                "source_stdout_exported": source_log.exists(),
            }
        )
    return result


def run(args: argparse.Namespace) -> None:
    code = runtime_code()
    if code["dirty"] or not 1 <= args.runs_per_part <= 128:
        raise ValueError("Clean committed code and a valid part size required")
    matrix = authenticate_matrix(args.matrix, args.verification)
    if not matrix["runs"]:
        raise ValueError("Cannot export an empty completed study")
    states = latest_proofs(args.matrix, args.verification, matrix, args.latest_states)
    daily = {r["run_id"]: r for r in json.loads(args.verification.read_text())["runs"]}
    ids = {safe_name(r["run_id"]) for r in matrix["runs"]}
    folded_ids = {name.casefold() for name in ids}
    if len(folded_ids) != len(ids):
        raise ValueError("Case-aliased run identities are not portable")
    if folded_ids & {
        "matrix.json",
        "verification.json",
        "latest-states.json",
        "profile.json",
        "selection.json",
    } or folded_ids & {name + ".log" for name in folded_ids}:
        raise ValueError("Run paths collide with exported metadata/logs")
    args.output.mkdir(parents=True, exist_ok=False)
    parts, missing_logs = [], []
    for offset in range(0, len(matrix["runs"]), args.runs_per_part):
        rows = matrix["runs"][offset : offset + args.runs_per_part]
        part = args.output / f"runs-{offset // args.runs_per_part:04d}.zip"
        with zipfile.ZipFile(
            part, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=1
        ) as archive:
            for row in rows:
                put_run(
                    archive,
                    args.matrix.parent,
                    row,
                    states[row["run_id"]],
                    daily[row["run_id"]]["historical_states_intentionally_omitted"],
                )
                log = args.matrix.parent / (safe_name(row["run_id"]) + ".log")
                if log.exists():
                    put_file(archive, "study/" + log.name, log)
                elif not args.allow_missing_run_logs:
                    raise ValueError("Required per-run stdout log missing")
                else:
                    missing_logs.append(row["run_id"])
            archive.writestr(f"part-records/{part.stem}.json", json.dumps(rows, allow_nan=False))
        parts.append(checked_part(part, "target_runs", [r["run_id"] for r in rows]))
    bundle = args.output / "code.bundle"
    subprocess.run(
        [
            "git",
            "-C",
            str(Path(__file__).resolve().parents[1]),
            "bundle",
            "create",
            str(bundle.resolve()),
            "HEAD",
        ],
        check=True,
        capture_output=True,
    )
    parts.append(
        {
            "name": bundle.name,
            "kind": "code",
            "bytes": bundle.stat().st_size,
            "sha256": digest(bundle),
            "commit": code["commit"],
        }
    )
    metadata = args.output / "metadata.zip"
    with zipfile.ZipFile(
        metadata, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=1
    ) as archive:
        for name, path in (
            ("matrix.json", args.matrix),
            ("verification.json", args.verification),
            ("latest-states.json", args.latest_states),
        ):
            put_file(archive, "study/" + name, path)
        for name in ("profile.json", "selection.json"):
            if (args.matrix.parent / name).exists():
                put_file(archive, "study/" + name, args.matrix.parent / name)
        names = set()
        for item in args.attachment:
            name, path = item.split("=", 1)
            safe_name(name)
            if name in names:
                raise ValueError("Duplicate attachment name")
            names.add(name)
            put_file(archive, "attachments/" + name, Path(path))
        sources = put_sources(archive, args.source_root, matrix)
    parts.append(checked_part(metadata, "metadata_and_sources", []))
    write_json(
        args.output / "catalog.json",
        {
            "schema": "ev-development-export-v1",
            "status": "complete",
            "scope": "Byte-preserving export of verified Development runs, selected Source models and code; no training or Final lock",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "export_code": code,
            "matrix_sha256": digest(args.matrix),
            "verification_sha256": digest(args.verification),
            "latest_states_sha256": digest(args.latest_states),
            "target_runs": len(matrix["runs"]),
            "runs_per_part": args.runs_per_part,
            "sources": sources,
            "parts": parts,
            "missing_original_run_stdout_logs": missing_logs,
            "historical_state_policy": "Preserve original latest/all policy; absent historical states remain absent and are not reconstructed",
        },
    )
    print(json.dumps({"status": "exported", "runs": len(matrix["runs"]), "parts": len(parts)}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("matrix", "verification", "latest-states", "source-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--runs-per-part", type=int, default=12)
    parser.add_argument("--attachment", action="append", default=[], metavar="NAME=PATH")
    parser.add_argument("--allow-missing-run-logs", action="store_true")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
