"""Outcome-blind prepared-entity inventory with bounded prior-exposure evidence."""

import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


def digest(path: Path) -> str:
    """Fingerprint existing bytes without modifying data."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_namespace(value: object) -> str | None:
    """Accept only explicit dataset/city identities, preserving identifier strings."""
    if isinstance(value, list) and len(value) == 2:
        value = "-".join(value)
    if isinstance(value, str):
        value = value.replace("UrbanEV/", "urbanev-").replace("CHARGED/", "charged-")
        if re.fullmatch(r"(?:urbanev|charged)-[A-Z]{3}", value):
            return value
    return None


def prior_references(root: Path, csv_paths: list[Path] | None = None) -> tuple[dict, dict]:
    """Read scored target ledgers plus named executed-cohort and support registries.

    Deliberately does not equate every metadata inventory ID with prior outcomes.
    This bounded local scan cannot prove an entity has never been inspected.
    """
    references = defaultdict(set)
    sources = {}
    paths = csv_paths if csv_paths is not None else sorted((root / "docs/reports").rglob("*.csv"))
    if csv_paths is None:
        paths += sorted((root / "experiments/member_studies").rglob("runs*.csv"))
    for path in paths:
        with path.open() as stream:
            reader = csv.DictReader(stream)
            fields = reader.fieldnames or []
            if not any("mae" in field.lower() for field in fields):
                continue
            used = False
            for row in reader:
                entity = next(
                    (row[k] for k in ("target", "station_id", "entity_id") if row.get(k)), None
                )
                if entity is None:
                    continue
                namespace = normalize_namespace(row.get("namespace"))
                if namespace is None and "issue99" in str(path):
                    namespace = "urbanev-SZH"
                if namespace is None and "member_studies" in str(path):
                    namespace = "urbanev-SZH"
                if namespace:
                    references[namespace, entity].add(str(path.relative_to(root)))
                    used = True
            if used:
                sources[str(path.relative_to(root))] = digest(path)
    lock_path = root / "configs/issue23/final-execution-lock-candidate-v2.json"
    if lock_path.is_file():
        lock = json.loads(lock_path.read_text())
        sources[str(lock_path.relative_to(root))] = digest(lock_path)
        for group in lock["groups"]:
            namespace = normalize_namespace(group["namespace"])
            if namespace is None:
                raise ValueError("Explicit namespace required for historical cohort")
            for entity in group["selected_ids"]:
                references[namespace, entity].add(str(lock_path.relative_to(root)))
    registration = root / "docs/reports/issue99-history-review-20261110/14d-registration.json"
    if registration.is_file():
        data = json.loads(registration.read_text())
        sources[str(registration.relative_to(root))] = digest(registration)
        for key in ("calibration_targets", "evaluation_targets"):
            for entity in data[key]:
                references["urbanev-SZH", entity].add(str(registration.relative_to(root)))
    support_path = root / "experiments/member_studies/duc_baselines/session.json"
    if support_path.is_file():
        data = json.loads(support_path.read_text())
        sources[str(support_path.relative_to(root))] = digest(support_path)
        for entities in data.get("graph_supports", {}).values():
            for entity in entities:
                references["urbanev-SZH", entity].add(
                    str(support_path.relative_to(root)) + "#graph_supports"
                )
    return references, sources


def inventory(
    input_parent: Path, root: Path, output: Path, *, prior_manifest: Path | None = None
) -> dict:
    """Use entity metadata only; never open labels, training or forecast vectors."""
    csv_paths = None
    if prior_manifest is not None:
        pinned = json.loads(prior_manifest.read_text())["prior_evidence_sha256"]
        for name, sha in pinned.items():
            if digest(root / name) != sha:
                raise ValueError("Prior evidence fingerprint mismatch")
        csv_paths = [root / name for name in pinned if name.endswith(".csv")]
    references, sources = prior_references(root, csv_paths)
    rows, fingerprints = [], []
    for folder in sorted(input_parent.glob("*-14d")):
        manifest_path, entities_path = folder / "manifest.json", folder / "entities.jsonl"
        manifest = json.loads(manifest_path.read_text())
        expected = manifest["files"]["entities.jsonl"]["sha256"]
        actual = digest(entities_path)
        if actual != expected:
            raise ValueError("Prepared entity metadata fingerprint mismatch")
        namespace = normalize_namespace(folder.name.removesuffix("-14d"))
        if namespace is None or manifest["config"]["history_days"] != 14:
            raise ValueError("Explicit namespace and 14-day preparation required")
        fingerprints.append(
            {
                "namespace": namespace,
                "manifest_sha256": digest(manifest_path),
                "entities_sha256": actual,
                "entities_path": str(entities_path),
            }
        )
        seen = set()
        with entities_path.open() as stream:
            for line in stream:
                entity = json.loads(line)
                dataset, city, target = entity["identity"]
                if f"{dataset}-{city}" != namespace or target in seen:
                    raise ValueError("Duplicate entity or namespace mismatch")
                seen.add(target)
                reasons = sorted(references.get((namespace, target), set()))
                role = entity["role"]
                if role == "source":
                    status = "excluded_source"
                elif reasons:
                    status = "excluded_prior_target_or_support"
                elif entity["status"] != "ready" or entity.get("initial_trainable", 0) < 1:
                    status = "excluded_not_ready_or_no_prefix_examples"
                else:
                    status = "exposure_unresolved"
                rows.append(
                    {
                        "namespace": namespace,
                        "entity_id": target,
                        "role": role,
                        "preparation_status": entity["status"],
                        "initial_trainable": entity.get("initial_trainable", 0),
                        "status": status,
                        "prior_reference_files": ";".join(reasons),
                        "certified_untouched": False,
                    }
                )
    if not fingerprints:
        raise ValueError("No prepared 14-day namespaces found")
    output.mkdir(parents=True, exist_ok=False)
    with (output / "entity-exposure.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "schema": "confirmation-eligibility-inventory-v1",
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "script_sha256": digest(Path(__file__)),
        "prior_registry_sha256": digest(prior_manifest) if prior_manifest else None,
        "scope": "Outcome-blind metadata inventory; bounded local prior-reference scan, not complete exposure certification",
        "namespaces": {
            ns: dict(Counter(r["status"] for r in rows if r["namespace"] == ns))
            for ns in sorted({r["namespace"] for r in rows})
        },
        "total_entities": len(rows),
        "certified_untouched": 0,
        "metadata_eligible_exposure_unresolved": sum(
            r["status"] == "exposure_unresolved" for r in rows
        ),
        "confirmation_started": False,
        "acceptance_status": "Inventory complete; confirmatory cohort not certified",
        "files_read": "Prepared manifests/entities and identified repository evidence only; no raw archive, label vector, forecast vector or checkpoint read",
        "limits": "IDs may denote colocated sites; untracked/local/remote studies and earlier human inspection are not exhaustively observable. Absence from scanned ledgers is not absence of exposure. No entity selection, new outcome or protocol promotion occurs.",
        "prepared_metadata": fingerprints,
        "prior_evidence_sha256": sources,
    }
    (output / "inventory.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--input-parent", type=Path, required=True)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--prior-manifest", type=Path, help="Pin a previous inventory evidence registry"
    )
    args = parser.parse_args()
    result = inventory(
        args.input_parent, args.repository, args.output, prior_manifest=args.prior_manifest
    )
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in ("prepared_metadata", "prior_evidence_sha256")
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
