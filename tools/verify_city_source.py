"""Independently restore one CHARGED Source outbox; no fitting or remote-access claim."""

import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path

from ev_models.checkpoint import digest, write_json
from ev_runner.run import runtime_code
from tools.charged_matched_development import backup_context, primary_recipe, validate_cohort
from tools.city_source_outbox import validate_environment
from tools.comparison_matrix import CachedInputs
from tools.durable_run_backup import RunBackup, canonical


def restore_source(
    archive_path: Path, checksum: str, output: Path, expected_context: dict, data: dict
) -> dict:
    """Verify exact wrapper/receipt/CPU checkpoint against independently rebuilt inputs."""
    if archive_path.is_symlink() or digest(archive_path) != checksum:
        raise ValueError("Changed pinned Source transport")
    if output.exists() or output.is_symlink():
        raise ValueError("New verification directory required; never overwrite")
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        if (
            archive.testzip() is not None
            or len({m.filename.casefold() for m in members}) != len(members)
            or any(
                m.is_dir() or stat.S_IFMT(m.external_attr >> 16) == stat.S_IFLNK for m in members
            )
        ):
            raise ValueError("Corrupt, aliased or nonregular Source wrapper")
        record = json.loads(archive.read("source-handoff-record.json"))
        seed = record.get("seed")
        if type(seed) is not int or seed not in expected_context["seeds"]:
            raise ValueError("Declared same-city Source seed required")
        names = {"context.json", f"source-seed{seed}.zip", f"source-seed{seed}.receipt.json"}
        manifest = json.loads(archive.read("manifest.json"))
        if set(manifest) != names or set(archive.namelist()) != {
            "manifest.json",
            "source-handoff-record.json",
            *("backup/" + name for name in names),
        }:
            raise ValueError("Exactly one Source pair and its context required")
        payloads = {}
        for name in names:
            value = archive.read("backup/" + name)
            if (
                len(value) != manifest[name]["bytes"]
                or hashlib.sha256(value).hexdigest() != manifest[name]["sha256"]
            ):
                raise ValueError("Changed Source wrapper member")
            payloads[name] = value
    if payloads["context.json"] != canonical(expected_context):
        raise ValueError("Changed independently bound city/input/config/code/environment context")
    if (
        record.get("schema") != "ev-one-city-source-outbox-v1"
        or record.get("status") != "awaiting_external_publication"
        or record.get("namespace") != "-".join(expected_context["namespace"])
        or record.get("context_sha256") != hashlib.sha256(payloads["context.json"]).hexdigest()
        or record.get("environment") != expected_context["environment"]
        or record.get("code", {}).get("dirty") is not False
        or record["code"]["files"] != expected_context["core_files"]
        or any(
            record.get(key) != expected_context[key]
            for key in (
                "source_epochs",
                "cohort_sha256",
                "primary_sha256",
                "environment_profile_sha256",
                "source_population_sha256",
                "source_manifest_sha256",
            )
        )
    ):
        raise ValueError("Source handoff claims differ from accepted dependencies")
    output.mkdir(parents=True, exist_ok=False)
    backup, study = output / "backup", output / "study"
    backup.mkdir()
    study.mkdir()
    for name, value in payloads.items():
        with (backup / name).open("xb") as stream:
            stream.write(value)
    reader = RunBackup(study, backup, expected_context, data, resume=True)
    sources, rows = reader.restore()
    if len(sources) != 1 or rows or sources[0]["seed"] != seed:
        raise ValueError("Unexpected Source/target population")
    entry = sources[0]
    examples = sum(
        r["initial_trainable"] for r in data[7].entities.values() if r["role"] == "source"
    )
    if (
        examples <= 0
        or entry["sha256"] != record.get("source_checkpoint_sha256")
        or entry["run"].get("training_examples") != examples
        or record.get("expected_source_examples") != examples
        or entry["run"].get("code")
        != {
            **record["code"],
            "files": {
                k: v for k, v in record["code"]["files"].items() if k.startswith("ev_models/")
            },
        }
        or entry["run"].get("environment") != expected_context["environment"]
    ):
        raise ValueError("Source count/checkpoint/producer report differs")
    proof = {
        "schema": "ev-verified-city-source-content-v1",
        "status": "independent_source_content_verified",
        "namespace": record["namespace"],
        "seed": seed,
        "archive_sha256": checksum,
        "archive_bytes": archive_path.stat().st_size,
        "context_sha256": reader.context_sha,
        "source_checkpoint_sha256": entry["sha256"],
        "source_examples": examples,
        "producer_code": record["code"],
        "environment": expected_context["environment"],
        "scope": "Exact local transport and independent CPU Source reload/latent/input/recipe checks. No training, target/Final access, remote availability or full-city acceptance claim.",
    }
    write_json(output / "source-verification.json", proof)
    return proof


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "archive",
        "inputs-root",
        "cohort",
        "primary-analysis",
        "environment-profile",
        "output",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("archive-sha256", "cohort-sha256", "primary-sha256", "environment-sha256"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    for path, checksum in (
        (args.cohort, args.cohort_sha256),
        (args.primary_analysis, args.primary_sha256),
        (args.environment_profile, args.environment_sha256),
    ):
        if digest(path) != checksum:
            raise ValueError("Changed verification dependency")
    cohort, primary, profile = (
        json.loads(p.read_text())
        for p in (args.cohort, args.primary_analysis, args.environment_profile)
    )
    validate_environment(profile["environment"], profile, profile["numpy"])
    primary_recipe(primary, 42, "not-used-by-source")
    if not primary.get("collection_lineage") or not primary.get("matrix_identities"):
        raise ValueError("Authenticated primary selection lineage required")
    # Validate namespace before constructing paths; validate_cohort also checks all budgets.
    from tools.charged_development_cohort import CITIES

    if cohort.get("namespace") not in {f"charged-{city}" for city in CITIES}:
        raise ValueError("Declared separate CHARGED city required")
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
        runtime_code(),
        profile["environment"],
        cohort_sha256=args.cohort_sha256,
        primary_sha256=args.primary_sha256,
    )
    context.update(
        schema="ev-kaggle-city-source-outbox-v1",
        backend="local_pending_external_publication",
        environment_profile_sha256=args.environment_sha256,
        numpy_version=profile["numpy"],
    )
    print(json.dumps(restore_source(args.archive, args.archive_sha256, args.output, context, data)))


if __name__ == "__main__":
    main()
