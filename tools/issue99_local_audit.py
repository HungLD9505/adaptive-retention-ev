"""Read-only, streaming local gate for the issue #99 input and Source10 archives."""

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZipFile

import torch

from ev_models.checkpoint import load_checkpoint

TARGETS = ("1405", "2152", "1153", "1693")
EXPECTED_PREFIX = (4, 12, 13, 13)
SOURCE_SHA = {
    42: (
        "ed9ae3be074332a987b2964fa46b441c4bf696e94219dc218d1cb8b2561d7924",
        "a3d3485d8d9a3e96c0483ab61e659e3a31b0f9bd62cc51ae6b77c0d204920d8b",
    ),
    43: (
        "ab1711327555c7f30c383e8e85fdd47358b3e7cc1b85b34f625f381b67b3ef50",
        "2ad6ed33fb7e692eae5f8db6be075ce43564851f70390d19edb4314052a17f5f",
    ),
    44: (
        "f07904e93e27b0d9d79a27f6b9cd64d33310d1d100f070aecd0d841f25561656",
        "6f475e54768322c5b51f5837d6ce7e863cb9ef6d33aec05b4a1c2468cd0285a5",
    ),
}
INPUT_SHA = "2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7"
ROOT = "data/inputs/issue18-input-handoff-v1-20261019/"


def sha_stream(stream):
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def source_rows(archive, budget):
    with archive.open(ROOT + f"urbanev-SZH-{budget}d/training.jsonl") as stream:
        for line in stream:
            if not line.startswith(b'{"role": "source",'):
                continue
            row = json.loads(line)
            row["forecast"].pop("input_run_id", None)
            yield row


def audit_input(path):
    result = {"zip_sha256": sha_stream(path.open("rb")), "budgets": {}}
    if result["zip_sha256"] != INPUT_SHA:
        raise ValueError("Input ZIP hash differs from release catalog")
    with ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("Input ZIP CRC failure")
        manifests = {}
        for budget in (7, 14):
            prefix = ROOT + f"urbanev-SZH-{budget}d/"
            raw = archive.read(prefix + "manifest.json")
            manifest = json.loads(raw)
            manifests[budget] = manifest
            hashes = {}
            for name, expected in manifest["files"].items():
                info = archive.getinfo(prefix + name)
                with archive.open(info) as stream:
                    actual = sha_stream(stream)
                if info.file_size != expected["size_bytes"] or actual != expected["sha256"]:
                    raise ValueError(f"Input mismatch: {budget}d/{name}")
                hashes[name] = actual
            result["budgets"][str(budget)] = {
                "manifest_sha256": hashlib.sha256(raw).hexdigest(),
                "run_id": manifest["run_id"],
                "status": manifest["status"],
                "file_sha256": hashes,
            }
        left, right = source_rows(archive, 7), source_rows(archive, 14)
        count = 0
        canonical = hashlib.sha256()
        for a, b in zip(left, right, strict=True):
            if a != b:
                raise ValueError(f"Source training row differs at index {count}")
            canonical.update(json.dumps(a, sort_keys=True, separators=(",", ":")).encode() + b"\n")
            count += 1
        result["source_rows_equal_excluding_input_run_id"] = count
        result["source_rows_canonical_sha256"] = canonical.hexdigest()
        if count != 65888:
            raise ValueError("Unexpected Source row count")
        prefix = ROOT + "urbanev-SZH-14d/"
        source_identities = {}
        target_counts = Counter()
        for budget in (7, 14):
            m = manifests[budget]
            with archive.open(ROOT + f"urbanev-SZH-{budget}d/entities.jsonl") as stream:
                entities = [json.loads(line) for line in stream]
            p = {
                "namespace": (m["config"]["dataset_id"], m["config"]["city_id"]),
                "source_start": m["config"]["source_start"],
                "deployment": m["config"]["deployment"],
                "salt": m["config"]["split_salt"],
                "clock": m["source"]["clock_mode"],
                "availability_delay_hours": m["config"]["availability_delay_hours"],
                "hourly_sha256": m["source"]["hourly_sha256"],
                "policy": m["missing_data_policy"],
                "entities": [
                    r
                    for r in sorted(entities, key=lambda r: tuple(r["identity"]))
                    if r["role"] == "source"
                ],
            }
            source_identities[budget] = hashlib.sha256(
                json.dumps(p, sort_keys=True).encode()
            ).hexdigest()
        if source_identities[7] != source_identities[14]:
            raise ValueError("Source population identities differ")
        result["source_population_sha256"] = source_identities[14]
        with archive.open(prefix + "training.jsonl") as stream:
            for line in stream:
                row = json.loads(line)
                if row["role"] == "development" and row["forecast"]["identity"][2] in TARGETS:
                    target_counts[row["forecast"]["identity"][2]] += 1
        schedules = {target: [] for target in TARGETS}
        with archive.open(prefix + "schedule.jsonl") as stream:
            for line in stream:
                row = json.loads(line)
                if row["identity"][2] in schedules:
                    schedules[row["identity"][2]].append(row)
        target_result = {}
        for target, expected in zip(TARGETS, EXPECTED_PREFIX, strict=True):
            rows = schedules[target]
            if target_counts[target] != expected or len(rows) != 90:
                raise ValueError(f"Target prefix/schedule differs: {target}")
            origins = [datetime.fromisoformat(row["origin"]) for row in rows]
            if any(b - a != timedelta(days=1) for a, b in zip(origins, origins[1:])):
                raise ValueError(f"Schedule is not daily: {target}")
            target_result[target] = {
                "prefix": target_counts[target],
                "scheduled": len(rows),
                "created": sum(row["status"] == "created" for row in rows),
                "statuses": dict(Counter(row["status"] for row in rows)),
            }
        result["targets"] = target_result
        label_status = {target: Counter() for target in TARGETS}
        with archive.open(prefix + "labels.jsonl") as stream:
            for line in stream:
                row = json.loads(line)
                target = row["identity"][2]
                if target not in label_status:
                    continue
                valid = all(row["file_valid"]) and all(t is not None for t in row["available_at"])
                label_status[target]["complete" if valid else "incomplete"] += 1
                if valid and max(
                    datetime.fromisoformat(t) for t in row["available_at"]
                ) < datetime.fromisoformat(row["origin"]) + timedelta(days=1):
                    raise ValueError(f"Label availability precedes completed horizon: {target}")
        result["labels"] = {target: dict(counts) for target, counts in label_status.items()}
        result["source_manifest_population_identity_equal"] = (
            manifests[7]["source"] == manifests[14]["source"]
        )
    return result


def audit_sources(directory, workdir):
    result = {}
    for seed, (zip_sha, checkpoint_sha) in SOURCE_SHA.items():
        path = directory / f"qyroven-issue23-source-duration-20261026-v1-seed{seed}.zip"
        if sha_stream(path.open("rb")) != zip_sha:
            raise ValueError(f"Source ZIP hash mismatch: {seed}")
        with ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise ValueError(f"Source ZIP CRC failure: {seed}")
            info = archive.getinfo("epoch-10.pt")
            with archive.open(info) as stream:
                data = stream.read()
            if hashlib.sha256(data).hexdigest() != checkpoint_sha:
                raise ValueError(f"Source checkpoint hash mismatch: {seed}")
            if archive.read("epoch-10.pt.sha256").decode().strip() != checkpoint_sha:
                raise ValueError(f"Source checkpoint sidecar mismatch: {seed}")
            checkpoint = workdir / f"seed{seed}-epoch10.pt"
            if checkpoint.exists():
                if sha_stream(checkpoint.open("rb")) != checkpoint_sha:
                    raise ValueError(f"Existing extracted checkpoint differs: {seed}")
            else:
                with checkpoint.open("xb") as stream:
                    stream.write(data)
            model, optimizer, value = load_checkpoint(checkpoint, sha256=checkpoint_sha)
            meta = value["metadata"]
            config = json.loads(archive.read("config.json"))
            run = json.loads(archive.read("run.json"))
            if config != meta["experiment_config"] or any(
                run[k] != meta[k]
                for k in ("input_binding", "source_population_sha256", "training_config", "code")
            ):
                raise ValueError(f"Source config/run/checkpoint metadata differ: {seed}")
            if run["status"] != "technical_success" or run["training_examples"] != 65888:
                raise ValueError(f"Source run completion/count mismatch: {seed}")
            if meta["code"]["dirty"]:
                raise ValueError(f"Source code was dirty: {seed}")
            for name, expected in meta["code"]["files"].items():
                historical = subprocess.check_output(
                    ["git", "show", f"{meta['code']['commit']}:{name}"]
                )
                if hashlib.sha256(historical).hexdigest() != expected:
                    raise ValueError(f"Historical source code mismatch: {seed}/{name}")
            if value["completed_epochs"] != 10 or meta["training_config"]["seed"] != seed:
                raise ValueError(f"Checkpoint seed/epoch mismatch: {seed}")
            latent = value["latent_scale"]
            if (
                latent is None
                or latent.shape != (64,)
                or not torch.isfinite(latent).all()
                or (latent < 0).any()
            ):
                raise ValueError(f"Invalid latent scale: {seed}")
            if not optimizer.state or any(
                not torch.isfinite(t).all()
                for state in optimizer.state.values()
                for t in state.values()
                if isinstance(t, torch.Tensor)
            ):
                raise ValueError(f"Invalid optimizer state: {seed}")
            if any(not torch.isfinite(t).all() for t in model.state_dict().values()):
                raise ValueError(f"Invalid model weights: {seed}")
            result[str(seed)] = {
                "zip_sha256": zip_sha,
                "checkpoint_sha256": checkpoint_sha,
                "input_binding": meta["input_binding"],
                "source_population_sha256": meta["source_population_sha256"],
                "training_config": meta["training_config"],
                "code": meta["code"],
                "latent_scale_min": latent.min().item(),
                "latent_scale_max": latent.max().item(),
                "optimizer_parameters": len(optimizer.state),
            }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-zip", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    args = parser.parse_args()
    args.workdir.mkdir(parents=True, exist_ok=True)
    report = {"schema": "issue99-local-audit-v1", "status": "BLOCKER"}
    try:
        report["inputs"] = audit_input(args.input_zip)
        report["source"] = audit_sources(args.source_dir, args.workdir)
        expected = report["source"]["42"]["source_population_sha256"]
        if expected != report["inputs"]["source_population_sha256"] or any(
            row["source_population_sha256"] != expected for row in report["source"].values()
        ):
            raise ValueError("Source population differs among seeds")
        report["status"] = "PASS"
    except Exception as error:
        report["blocker"] = repr(error)
        raise
    finally:
        print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
