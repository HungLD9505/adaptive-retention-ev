"""List historical source identities and verify local archives without modifying them."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data/sources.json"
DATASETS = ("urbanev", "charged")


@dataclass(frozen=True)
class Archive:
    source_id: str
    dataset: str
    download_url: str
    relative_path: str
    size_bytes: int
    sha256: str
    required: bool
    publisher_checksum: str | None = None


def load_catalog(path: Path = CATALOG) -> list[Archive]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload["schema_version"] != 1:
        raise ValueError("Unsupported catalog schema")
    archives = [Archive(**entry) for entry in payload["archives"]]
    if not archives or len({a.source_id for a in archives}) != len(archives):
        raise ValueError("Catalog must contain unique source IDs")
    paths: set[str] = set()
    for archive in archives:
        relative = PurePosixPath(archive.relative_path)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or "\\" in archive.relative_path
            or relative.parts[:2] != ("data", "raw")
            or len(relative.parts) < 3
        ):
            raise ValueError(f"Unsafe archive path: {archive.source_id}")
        if archive.relative_path in paths:
            raise ValueError("Archive paths must be unique")
        paths.add(archive.relative_path)
        if archive.dataset not in DATASETS or not re.fullmatch(r"[a-z0-9-]+", archive.source_id):
            raise ValueError("Invalid dataset or source ID")
        url = urlparse(archive.download_url)
        if url.scheme != "https" or not url.netloc or url.username or url.password:
            raise ValueError("Source URLs must be HTTPS without embedded credentials")
        if type(archive.size_bytes) is not int or archive.size_bytes <= 0:
            raise ValueError("Archive size must be a positive integer")
        if type(archive.required) is not bool or not re.fullmatch(r"[0-9a-f]{64}", archive.sha256):
            raise ValueError("Invalid required flag or SHA-256")
        if archive.publisher_checksum is not None and not re.fullmatch(
            r"(?:md5:[0-9a-f]{32}|sha256:[0-9a-f]{64})", archive.publisher_checksum
        ):
            raise ValueError("Invalid publisher checksum")
    return archives


def select_archives(
    archives: list[Archive], dataset: str | None, include_optional: bool
) -> list[Archive]:
    return [
        a
        for a in archives
        if (dataset is None or a.dataset == dataset) and (a.required or include_optional)
    ]


def verify_archive(archive: Archive, root: Path) -> tuple[bool, str]:
    root = root.resolve()
    path = (root / archive.relative_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Archive resolves outside data root: {archive.source_id}")
    if not path.is_file():
        return False, "MISSING"
    if path.stat().st_size != archive.size_bytes:
        return False, "SIZE MISMATCH"
    digests = {"sha256": hashlib.sha256()}
    expected = [("sha256", archive.sha256)]
    if archive.publisher_checksum:
        algorithm, value = archive.publisher_checksum.split(":", 1)
        expected.append((algorithm, value))
        if algorithm not in digests:
            digests[algorithm] = hashlib.new(algorithm, usedforsecurity=False)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            for digest in digests.values():
                digest.update(block)
    if any(digests[name].hexdigest() != value for name, value in expected):
        return False, "CHECKSUM MISMATCH"
    return True, "PASS"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    listing = subcommands.add_parser("list", help="Show recorded URLs; does not contact providers")
    listing.add_argument("--dataset", choices=DATASETS)
    verifying = subcommands.add_parser("verify", help="Read local files and verify size/checksums")
    verifying.add_argument("--dataset", choices=DATASETS)
    verifying.add_argument("--include-optional", action="store_true")
    verifying.add_argument("--root", type=Path, default=ROOT, help="Root containing data/raw/")
    args = parser.parse_args(argv)
    try:
        archives = load_catalog()
        if args.command == "list":
            for archive in archives:
                if args.dataset is None or archive.dataset == args.dataset:
                    scope = "required" if archive.required else "optional"
                    print(f"{archive.source_id} | {scope} | {archive.size_bytes} bytes")
                    print(f"  {archive.download_url}\n  -> {archive.relative_path}")
            return 0
        selected = select_archives(archives, args.dataset, args.include_optional)
        results = []
        for archive in selected:
            passed, message = verify_archive(archive, args.root)
            print(f"{archive.source_id}: {message}")
            results.append(passed)
        return 0 if results and all(results) else 1
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(f"Source check error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
