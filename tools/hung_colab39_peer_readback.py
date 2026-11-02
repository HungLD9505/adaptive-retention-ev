"""Read and hash Colab #39 Drive artifacts against the pinned 163-file map."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
FILE_MAP = ROOT / "docs/reports/hung-colab39-163-file-map-20261028.csv"
FILE_MAP_SHA256 = "b3e59701a2f52d22b69d7f5b1b04b9903dbec19ffbc41b2367b83bb63b372ca9"
EXPECTED_FILES = 163
EXPECTED_BYTES = 72_529_254


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_map(path: Path, expected_sha256: str) -> list[dict[str, str]]:
    if sha256_file(path) != expected_sha256:
        raise ValueError("File-map SHA-256 differs from the pinned report")
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["path", "bytes", "sha256"]:
            raise ValueError("Unexpected file-map columns")
        rows = list(reader)
    if len(rows) != EXPECTED_FILES or len({row["path"] for row in rows}) != EXPECTED_FILES:
        raise ValueError("File map must contain exactly 163 unique paths")
    if sum(int(row["bytes"]) for row in rows) != EXPECTED_BYTES:
        raise ValueError("File-map byte total differs from the pinned report")
    for row in rows:
        relative = PurePosixPath(row["path"])
        if relative.is_absolute() or ".." in relative.parts or "\\" in row["path"]:
            raise ValueError(f"Unsafe file-map path: {row['path']}")
        if len(row["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in row["sha256"]):
            raise ValueError(f"Invalid SHA-256 in file map: {row['path']}")
    return rows


def verify(folder: Path, rows: list[dict[str, str]]) -> dict[str, object]:
    folder = folder.resolve(strict=True)
    if not folder.is_dir():
        raise ValueError(f"Not a folder: {folder}")
    expected = {row["path"] for row in rows}
    actual = {path.relative_to(folder).as_posix() for path in folder.rglob("*") if path.is_file()}
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    failures: list[str] = []
    bytes_read = 0
    verified = 0
    for row in rows:
        relative = row["path"]
        path = folder.joinpath(*PurePosixPath(relative).parts)
        if relative in missing:
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(folder):
            failures.append(f"unsafe path: {relative}")
            continue
        size = path.stat().st_size
        if size != int(row["bytes"]):
            failures.append(f"size mismatch: {relative}")
            continue
        if sha256_file(path) != row["sha256"]:
            failures.append(f"SHA-256 mismatch: {relative}")
            continue
        bytes_read += size
        verified += 1
    return {
        "status": "VERIFIED" if not (missing or unexpected or failures) else "FAILED",
        "folder": str(folder),
        "expected_files": len(rows),
        "verified_files": verified,
        "verified_bytes": bytes_read,
        "missing": missing,
        "unexpected": unexpected,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--folder",
        required=True,
        type=Path,
        help="Mounted reviewer copy of the exact Drive run folder",
    )
    parser.add_argument("--file-map", default=FILE_MAP, type=Path)
    args = parser.parse_args()
    rows = read_map(args.file_map, FILE_MAP_SHA256)
    result = verify(args.folder, rows)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "VERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
