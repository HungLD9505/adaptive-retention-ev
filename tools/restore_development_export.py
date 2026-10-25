"""Restore checksum-pinned Development export parts; never train or run bundled code."""

import argparse
import json
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath

from ev_models.checkpoint import digest
from tools.export_development import safe_name


def restore(package: Path, output: Path, catalog_sha256: str) -> dict:
    """Fail closed on missing, changed, aliased or overlapping parts and payload paths."""
    catalog_path = package / "catalog.json"
    if digest(catalog_path) != catalog_sha256:
        raise ValueError("Changed pinned export catalog")
    catalog = json.loads(catalog_path.read_text())
    if catalog["schema"] != "ev-development-export-v1" or catalog["status"] != "complete":
        raise ValueError("Complete identified export required")
    names = [safe_name(p["name"]) for p in catalog["parts"]]
    if len(set(n.casefold() for n in names)) != len(names):
        raise ValueError("Duplicate/aliased part names")
    archived_ids = []
    for part in catalog["parts"]:
        path = package / part["name"]
        if (
            path.is_symlink()
            or path.stat().st_size != part["bytes"]
            or digest(path) != part["sha256"]
        ):
            raise ValueError("Missing or changed export part")
        if part["kind"] == "target_runs":
            archived_ids.extend(part["run_ids"])
        elif part["kind"] not in {"code", "metadata_and_sources"}:
            raise ValueError("Unknown export part type")
    kinds = [p["kind"] for p in catalog["parts"]]
    if kinds.count("code") != 1 or kinds.count("metadata_and_sources") != 1:
        raise ValueError("Exactly one code bundle and metadata/Source archive required")
    if (
        len(set(safe_name(n).casefold() for n in archived_ids)) != len(archived_ids)
        or len(archived_ids) != catalog["target_runs"]
    ):
        raise ValueError("Changed/duplicate target-run population")
    output.mkdir(parents=True, exist_ok=False)
    occupied, directories = set(), {}
    for part in catalog["parts"]:
        path = package / part["name"]
        if part["kind"] == "code":
            if part["name"] != "code.bundle" or "code.bundle" in occupied:
                raise ValueError("Unexpected/duplicate code bundle")
            with path.open("rb") as src, (output / "code.bundle").open("xb") as dst:
                shutil.copyfileobj(src, dst)
            occupied.add("code.bundle")
            continue
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None or len(archive.infolist()) != part["files"]:
                raise ValueError("Corrupt or changed ZIP member population")
            for info in archive.infolist():
                relative = PurePosixPath(info.filename)
                if (
                    not relative.parts
                    or "/".join(relative.parts) != info.filename
                    or info.is_dir()
                    or stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK
                ):
                    raise ValueError("Unsafe/noncanonical ZIP payload")
                for component in relative.parts:
                    safe_name(component)
                key = info.filename.casefold()
                ancestors = ["/".join(relative.parts[:n]) for n in range(1, len(relative.parts))]
                # O(path depth), rather than scanning every previously restored file.
                if (
                    key in occupied
                    or key in directories
                    or any(a.casefold() in occupied for a in ancestors)
                ):
                    raise ValueError("Overlapping/aliased archive payload; never overwrite")
                for ancestor in ancestors:
                    folded = ancestor.casefold()
                    if folded in directories and directories[folded] != ancestor:
                        raise ValueError("Aliased directory case is not portable")
                    directories[folded] = ancestor
                target = output.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as src, target.open("xb") as dst:
                    shutil.copyfileobj(src, dst)
                occupied.add(key)
    matrix_path = output / "study/matrix.json"
    if digest(matrix_path) != catalog["matrix_sha256"]:
        raise ValueError("Restored matrix differs from pinned catalog")
    for name, field in (
        ("verification.json", "verification_sha256"),
        ("latest-states.json", "latest_states_sha256"),
    ):
        if digest(output / "study" / name) != catalog[field]:
            raise ValueError("Restored proof differs from catalog")
    matrix = json.loads(matrix_path.read_text())
    matrix_ids = [r["run_id"] for r in matrix["runs"]]
    if len(set(matrix_ids)) != len(matrix_ids) or set(matrix_ids) != set(archived_ids):
        raise ValueError("Restored matrix/parts run populations differ")
    for source in catalog["sources"]:
        path = (
            output
            / "sources"
            / f"source-seed{source['seed']}"
            / f"epoch-{matrix['source_epochs']}.pt"
        )
        if path.stat().st_size != source["bytes"] or digest(path) != source["sha256"]:
            raise ValueError("Restored Source checkpoint differs")
    return {
        "status": "transport_verified",
        "runs": len(matrix_ids),
        "files": len(occupied),
        "catalog_sha256": catalog_sha256,
        "next": "Independently re-run daily/input and latest-state verifiers; this transport check is not model effectiveness or Final acceptance",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--catalog-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(restore(args.package, args.output, args.catalog_sha256)))


if __name__ == "__main__":
    main()
