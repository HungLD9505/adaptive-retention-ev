"""Ingest one bounded CPU batch from observed log text, with exact SHA/job binding."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import zlib
from pathlib import Path

from experiments.supporting_pipeline.dispatch_state import atomic_create
from tools.hung_kaggle_export_batches import digest
from tools.hung_portable_results import PLAN_SHA, merge_collections
from tools.hung_results import file_sha, verified_file

MAX_BYTES = 32 * 1024 * 1024


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def decode_log(text: str) -> tuple[dict, bytes]:
    """DOM table or native AX text: repeated identical rows are allowed, conflicts are not."""
    summary, chunks = None, {}
    decoder = json.JSONDecoder()
    for line in text.splitlines():
        start = line.find('{"portable_')
        if start < 0:
            continue
        record, _ = decoder.raw_decode(line[start:])
        if "portable_export" in record:
            require(
                summary is None or summary == record["portable_export"], "Conflicting summaries"
            )
            summary = record["portable_export"]
        elif "portable_chunk" in record:
            index, data = record["portable_chunk"], record["data"]
            require(type(index) is int and 0 <= index < 10000, "Invalid chunk index")
            require(isinstance(data, str) and len(data) <= 3000, "Invalid chunk size")
            require(index not in chunks or chunks[index] == data, "Conflicting duplicate chunk")
            chunks[index] = data
    require(isinstance(summary, dict), "Missing export summary")
    count, size = summary["chunks"], summary["bytes"]
    require(type(count) is int and 0 < count <= 10000, "Invalid declared chunk count")
    require(type(size) is int and 0 < size <= MAX_BYTES, "Unbounded export size")
    require(set(chunks) == set(range(count)), "Missing/extra transport chunks")
    try:
        compressed = base64.b64decode("".join(chunks[i] for i in range(count)), validate=True)
        stream = zlib.decompressobj()
        body = stream.decompress(compressed, size + 1)
    except (binascii.Error, zlib.error) as error:
        raise ValueError("Corrupt export transport") from error
    require(
        stream.eof and not stream.unconsumed_tail and not stream.unused_data,
        "Invalid compressed stream",
    )
    require(len(body) == size, "Export byte count differs")
    require(hashlib.sha256(body).hexdigest() == summary["sha256"], "Export SHA differs")
    return summary, body


def ingest(log_pin: dict, manifest_pin: dict, batch_id: str, output: Path, root: Path) -> dict:
    """Create an immutable readback receipt only after exact allocation and record validation."""
    require(output.resolve().is_relative_to(root.resolve()), "Output outside project")
    require(not output.exists(), "Output exists; preserve completed/partial evidence")
    log = verified_file(log_pin, root)
    manifest = json.loads(verified_file(manifest_pin, root).read_bytes())
    require(
        manifest["schema"] == "hung-kaggle-export-batches-v1"
        and manifest["scope"] == "development_only",
        "Foreign allocation",
    )
    require(manifest["canonical_plan_sha256"] == PLAN_SHA, "Canonical plan differs")
    require(
        digest(manifest["batches"]) == manifest["allocation_sha256"], "Allocation digest differs"
    )
    candidates = [b for b in manifest["batches"] if b["id"] == batch_id]
    require(len(candidates) == 1, "Missing/duplicate batch")
    batch = candidates[0]
    summary, body = decode_log(log.read_text(encoding="utf-8"))
    require(
        summary["scope"] == "development_only"
        and summary["executed"] is False
        and summary["gpu"] is False,
        "Not a CPU-only Development export",
    )
    require(
        summary["batch"] == batch_id and summary["batch_sha256"] == digest(batch),
        "Batch binding differs",
    )
    require(summary["counts"]["runs"] == len(batch["job_ids"]) == 80, "Batch count differs")
    value = json.loads(body)
    require(value["provenance"]["batch_sha256"] == digest(batch), "Payload batch binding differs")
    output.mkdir(parents=True, exist_ok=False)
    path = output / "portable-batch.json"
    with path.open("xb") as stream:
        stream.write(body)
    spec = {
        "scope": "development_only",
        "collections": [
            {
                "export": {"path": str(path.resolve()), "sha256": summary["sha256"]},
                "job_ids": batch["job_ids"],
            }
        ],
    }
    atomic_create(output / "collection.json", spec)
    result = merge_collections({**spec, "spec_sha256": file_sha(output / "collection.json")}, root)
    require(result["counts"] == summary["counts"], "Reconciled coverage differs")
    atomic_create(output / "results.json", result)
    receipt = {
        "schema": "hung-portable-batch-readback-v1",
        "scope": "development_only",
        "passed": True,
        "batch": batch_id,
        "batch_sha256": digest(batch),
        "allocation_sha256": manifest["allocation_sha256"],
        "log": log_pin,
        "manifest": manifest_pin,
        "export_sha256": summary["sha256"],
        "counts": result["counts"],
        "files": [
            {"path": str(p.resolve()), "sha256": file_sha(p)}
            for p in sorted(output.iterdir())
            if p.is_file()
        ],
        "acceptance": "Exact technical transport/readback; independent scientific approval pending",
    }
    atomic_create(output / "receipt.json", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--log-sha256", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    result = ingest(
        {"path": str(args.log), "sha256": args.log_sha256},
        {"path": str(args.manifest), "sha256": args.manifest_sha256},
        args.batch,
        args.output,
        args.root,
    )
    print(
        json.dumps(
            {"batch": result["batch"], "passed": result["passed"], "counts": result["counts"]}
        )
    )


if __name__ == "__main__":
    main()
