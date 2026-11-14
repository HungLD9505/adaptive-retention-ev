"""Conservative recorded-target history across Git objects and local run metadata."""

import argparse
import csv
import hashlib
import io
import json
import os
import re
import subprocess
from collections import defaultdict
from pathlib import Path

from tools.confirmation_inventory import digest, normalize_namespace

ID_KEYS = {"entity_id", "target", "target_id", "station_id"}
LIST_KEYS = {
    "targets",
    "target_ids",
    "selected_ids",
    "development_entities",
    "calibration_targets",
    "evaluation_targets",
}
SKIP_KEYS = {
    "cell",
    "arms",
    "model",
    "optimizer",
    "rng",
    "predictions",
    "predictions_kwh",
    "labels",
    "x_hist",
    "c_future",
    "y_scaled",
    "source_sha256",
    "files",
    "source_evidence_sha256",
}
CITIES = {
    "AMSTERDAM": "AMS",
    "JOHANNESBURG": "JHB",
    "LOS ANGELES": "LOA",
    "MELBOURNE": "MEL",
    "SAO PAULO": "SPO",
    "SÃO PAULO": "SPO",
    "SHENZHEN": "SZH",
}
PREPARED_ARTIFACTS = {
    "entities.jsonl",
    "schedule.jsonl",
    "forecasts.jsonl",
    "training.jsonl",
    "labels.jsonl",
}


def namespace_of(value: dict, inherited: str | None, locator: str) -> str | None:
    """Use explicit namespace, input binding or city metadata before path inference."""
    direct = normalize_namespace(value.get("namespace"))
    if direct:
        return direct
    dataset = value.get("dataset_id", value.get("dataset"))
    city = value.get("city_id", value.get("city"))
    if isinstance(city, str):
        city = CITIES.get(city.upper(), city.upper())
    if isinstance(dataset, str):
        dataset = dataset.lower().replace("_", "")
    if dataset in ("urbanev", "charged") and isinstance(city, str):
        direct = normalize_namespace([dataset, city])
        if direct:
            return direct
    if city in {"AMS", "JHB", "LOA", "MEL", "SPO"}:
        return "charged-" + city
    binding = value.get("binding", {})
    nested = binding.get("input") if isinstance(binding, dict) else None
    if isinstance(nested, dict):
        direct = namespace_of(nested, None, locator)
        if direct:
            return direct
    if inherited:
        return inherited
    matches = re.findall(r"(?i)(urbanev|charged)[/\-_ ](AMS|JHB|LOA|MEL|SPO|SZH)", locator)
    if len(set((a.lower(), b.upper()) for a, b in matches)) == 1:
        a, b = matches[0]
        return a.lower() + "-" + b.upper()
    if (
        any(s in locator for s in ("issue99", "member_studies/cyber", "member_studies/duc"))
        and "full-scope" not in locator
    ):
        return "urbanev-SZH"
    return None


def target_ids(value: object, locator: str) -> set[tuple[str, str]]:
    """Extract identity/allowlist declarations, never inspect error magnitudes."""
    found = set()

    def add(entity: object, namespace: str | None) -> None:
        if isinstance(entity, (str, int)) and re.fullmatch(r"[0-9]{1,10}", str(entity)):
            found.add((namespace or "*", str(entity)))

    def walk(node: object, namespace: str | None = None, parent: str = "") -> None:
        if isinstance(node, dict):
            ns = namespace_of(node, namespace, locator)
            role = node.get("role", node.get("stage"))
            if role == "source":
                return
            for key in ID_KEYS:
                if key in node:
                    add(node[key], ns)
            identity = node.get("identity")
            if (
                isinstance(identity, list)
                and len(identity) == 3
                and node.get("role") in ("development", "final", "target")
            ):
                explicit = normalize_namespace(identity[:2])
                if explicit:
                    add(identity[2], explicit)
            for key, child in node.items():
                if key in SKIP_KEYS:
                    continue
                if key in LIST_KEYS and isinstance(child, list):
                    for entity in child:
                        add(entity, ns)
                if key == "graph_supports" and isinstance(child, dict):
                    for entities in child.values():
                        for entity in entities:
                            add(entity, ns)
                if isinstance(child, (dict, list)):
                    walk(child, ns, key)
        elif isinstance(node, list) and (not node or isinstance(node[0], (dict, list))):
            for child in node:
                walk(child, namespace, parent)

    walk(value)
    return found


def extract(data: bytes, locator: str) -> set[tuple[str, str]]:
    """Read structured metadata; code/notes contribute only annotated JSON blocks."""
    if any(
        part in locator.lower()
        for part in (
            "entity_metadata",
            "scope_gap",
            "omitted-disposition",
            "metadata-preflight",
            "metadata-capacity",
        )
    ):
        return set()
    if locator.endswith(".jsonl"):
        found = set()
        for index, line in enumerate(data.decode("utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Malformed JSONL at {locator}:{index}") from error
            if not isinstance(row, dict):
                raise ValueError(f"Expected JSONL object at {locator}:{index}")
            # Persisted execution records may identify the target only in a run ID.
            run_id = row.get("run_id")
            if isinstance(run_id, str) and (
                match := re.search(r"_([0-9]+)_(?:det|(?:seed)?(?:42|43|44))$", run_id)
            ):
                found.add((namespace_of(row, None, locator) or "*", match[1]))
            if "identity" in row and "role" not in row and "stage" not in row:
                row = {**row, "role": "target"}
            found |= target_ids(row, locator)
        return found
    text = data.decode("utf-8", errors="replace")
    if locator.endswith(".csv"):
        reader = csv.DictReader(io.StringIO(text))
        columns = reader.fieldnames or []
        if not any(
            any(
                token in column.lower()
                for token in (
                    "mae",
                    "rmse",
                    "metric",
                    "method",
                    "variant",
                    "run_id",
                    "run_path",
                    "model",
                    "loss",
                    "completed",
                )
            )
            for column in columns
        ):
            return set()
        return set().union(*(target_ids(row, locator) for row in reader))
    try:
        return target_ids(json.loads(text), locator)
    except json.JSONDecodeError:
        found = set()
        for block in re.findall(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.S):
            try:
                found |= target_ids(json.loads(block), locator)
            except json.JSONDecodeError:
                continue
        return found


def audit(repository: Path, local_runs: Path, output: Path) -> dict:
    """Record reachable structured history and local attempted-run declarations."""
    output.mkdir(parents=True, exist_ok=False)
    refs = subprocess.check_output(
        ["git", "for-each-ref", "--format=%(refname) %(objectname)"], cwd=repository, text=True
    ).splitlines()
    objects = subprocess.check_output(
        ["git", "rev-list", "--objects", "--all"], cwd=repository, text=True
    ).splitlines()
    candidates = []
    for line in objects:
        fields = line.split(" ", 1)
        if len(fields) != 2:
            continue
        oid, path = fields
        if Path(path).suffix != ".jsonl" and not path.startswith(
            ("docs/", "reports/", "report/", "configs/", "handoff/", "notebooks/", "experiments/")
        ):
            continue
        if (
            Path(path).suffix not in {".json", ".jsonl", ".csv", ".ipynb", ".md"}
            or "/tests/" in path
            or "fixture" in path.lower()
        ):
            continue
        candidates.append((oid, path))
    evidence = defaultdict(set)
    inspected, skipped, failures, prepared_paths = [], [], [], []
    process = subprocess.Popen(
        ["git", "cat-file", "--batch"],
        cwd=repository,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    try:
        for index, (oid, path) in enumerate(candidates):
            process.stdin.write((oid + "\n").encode())
            process.stdin.flush()
            header = process.stdout.readline().decode().strip().split()
            if len(header) != 3 or header[1] != "blob":
                raise ValueError("Unexpected Git object response")
            size = int(header[2])
            data = process.stdout.read(size)
            process.stdout.read(1)
            if size > 20_000_000:
                skipped.append({"oid": oid, "path": path, "reason": "over_20MB"})
                continue
            ids = extract(data, path)
            inspected.append(
                {
                    "kind": "git_blob",
                    "identity": oid,
                    "path": path,
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "target_declarations": len(ids),
                }
            )
            for identity in ids:
                evidence[identity].add("git:" + oid + ":" + path)
            if (index + 1) % 1000 == 0:
                print(f"Git metadata objects inspected: {index + 1}/{len(candidates)}", flush=True)
    finally:
        process.stdin.close()
        process.stdout.close()
        process.wait()
    metadata_names = {
        "run.json",
        "binding.json",
        "registration.json",
        "selection-lock.json",
        "protocol-lock.json",
        "session.json",
        "run-profile.json",
    }
    local_count = 0
    for folder, directories, files in os.walk(local_runs):
        directories[:] = [
            d
            for d in directories
            if not d.startswith(("tick-", ".pending-"))
            and d
            not in {
                ".git",
                "__pycache__",
                "node_modules",
                "source-rebuild",
                "source",
                "site-packages",
            }
        ]
        here = Path(folder)
        ns = namespace_of({}, None, str(here))
        directory_id = re.search(
            r"(?:fast-|stable-|target-)([0-9]+)-(?:seed)?(?:42|43|44)$", here.name
        )
        if directory_id and ns:
            evidence[ns, directory_id[1]].add("local-directory:" + str(here))
        for name in files:
            if name in PREPARED_ARTIFACTS and "/data/inputs/" in (here / name).as_posix():
                # Preparation is not target execution. Never decode these value arrays.
                prepared_paths.append(str(here / name))
                continue
            cell = re.fullmatch(r"cell-([0-9]+)-(?:42|43|44)\.json", name)
            if cell and ns:
                evidence[ns, cell[1]].add("local-cell-path:" + str(here / name))
            if (
                name not in metadata_names
                and not name.endswith(".jsonl")
                and not (
                    name.endswith(".json")
                    and any(s in name for s in ("ledger", "execution-lock", "cohort"))
                )
            ):
                continue
            path = here / name
            if path.stat().st_size > 20_000_000:
                skipped.append({"path": str(path), "reason": "local_over_20MB"})
                continue
            try:
                data = path.read_bytes()
                ids = extract(data, str(path))
            except (OSError, ValueError) as error:
                failures.append({"path": str(path), "error": str(error)})
                continue
            inspected.append(
                {
                    "kind": "local_metadata",
                    "path": str(path),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "target_declarations": len(ids),
                }
            )
            for identity in ids:
                evidence[identity].add("local:" + str(path))
            local_count += 1
        if local_count and local_count % 3000 == 0:
            print(f"Local run metadata inspected: {local_count}", flush=True)
    rows = [
        {"namespace": ns, "entity_id": entity, "references": sorted(paths)}
        for (ns, entity), paths in sorted(evidence.items())
    ]
    (output / "exclusions.json").write_text(json.dumps(rows, indent=2) + "\n")
    (output / "scan-manifest.json").write_text(json.dumps(inspected, indent=2) + "\n")
    result = {
        "schema": "recorded-data-use-history-v1",
        "code_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repository, text=True
        ).strip(),
        "script_sha256": digest(Path(__file__)),
        "git_refs": refs,
        "git_objects_inspected": sum(r["kind"] == "git_blob" for r in inspected),
        "local_metadata_files_inspected": local_count,
        "distinct_namespace_ids": len(rows),
        "ambiguous_namespace_ids": sum(r["namespace"] == "*" for r in rows),
        "skipped": skipped,
        "read_failures": failures,
        "prepared_artifacts_not_opened": prepared_paths,
        "exclusions_sha256": digest(output / "exclusions.json"),
        "scan_manifest_sha256": digest(output / "scan-manifest.json"),
        "scope": "All fetched reachable refs plus local run metadata; conservative execution/allowlist declarations include attempted and planned uses; station catalogues and explicit metadata-only disposition files are not model executions. No new target vector is decoded. Unrecorded remote/human inspection and physical ID aliases remain unverified.",
    }
    (output / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in ("git_refs", "skipped", "read_failures")},
            indent=2,
        )
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--local-runs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit(args.repository, args.local_runs, args.output)


if __name__ == "__main__":
    main()
