"""Create-only private shard storage and a separate CPU readback barrier."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path


def upload_private(name: str, folder: Path, owner: str) -> None:
    from kagglehub.clients import build_kaggle_client
    from kagglehub.gcs_upload import upload_files_and_directories
    from kagglesdk.blobs.types.blob_api_service import ApiBlobType
    from kagglesdk.datasets.types.dataset_api_service import ApiCreateDatasetRequest

    uploaded = upload_files_and_directories(
        str(folder), item_type=ApiBlobType.DATASET, ignore_patterns=[]
    ).to_proto()
    request = ApiCreateDatasetRequest()
    request.owner_slug, request.slug, request.title = owner, name, name
    request.files, request.directories = uploaded.files, uploaded.directories
    request.is_private = True
    with build_kaggle_client() as client:
        result = client.datasets.dataset_api_client.create_dataset(request)
    assert not result.error, "Private Dataset creation failed; no version/retry fallback"


def persist_shard(
    record: dict, archive: Path, source_prefix: str, *, owner: str, submit, status
) -> dict:
    """Return only after another CPU VM reads exact uploaded bytes, SHA and CRC."""
    assert record["exit_code"] == record["local_verify_exit_code"] == 0
    with archive.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == record["artifact_sha256"]
    assert archive.stat().st_size == record["artifact_bytes"]
    shard = record["shard_id"]
    assert shard.startswith("shard_") and shard[6:].isdigit()
    dataset = f"hung-dev-{shard.replace('_', '')}-44b8532-20261027-v2"
    name = f"hung-dev-readback-{shard.replace('_', '')}-20261027-v2"
    folder = archive.parent / "publish"
    folder.mkdir(exist_ok=False)
    # Preserve the ZIP as one binary object; no extra disk-sized copy is needed.
    os.link(archive, folder / "artifacts.zip.bin")
    with (folder / "receipt.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
    started = time.perf_counter()
    upload_outcome = "acknowledged"
    try:
        upload_private(dataset, folder, owner)
    except Exception as error:
        # HTTP499 can arrive after CreateDataset committed. Never retry creation
        # or training: only an exact, separately mounted CPU readback can adopt it.
        if getattr(getattr(error, "response", None), "status_code", None) != 499:
            raise
        upload_outcome = "HTTP499; reconciled only by exact CPU readback"
        print(json.dumps({"uncertain_dataset_create": dataset, "http_status": 499}), flush=True)
    upload_seconds = time.perf_counter() - started
    source = source_prefix + "\nexpected = " + repr(record) + "\n"
    source += """
receipts = [p for p in Path('/kaggle/input').rglob('receipt.json')
            if json.loads(p.read_text()) == expected]
assert len(receipts) == 1, 'Exact pinned receipt missing/ambiguous'
readback_start = time.perf_counter()
records = verify_predecessor(receipts[0].parent, (int(expected['shard_id'][6:]),),
                             archive_name='artifacts.zip.bin')
proof = {'passed': True, 'records': records, 'seconds': time.perf_counter()-readback_start,
         'scope': 'Independent CPU readback of private Dataset; no training/Final'}
Path('/kaggle/working/readback.json').open('x').write(json.dumps(proof))
print(json.dumps(proof),flush=True)
"""
    compile(source, "cpu-shard-readback", "exec")
    submitted = submit(name, source, gpu=False, datasets=[f"{owner}/{dataset}/1"])
    deadline = time.monotonic() + 1800
    while True:
        state = status(name)
        if state == "COMPLETE":
            break
        assert state in {"QUEUED", "RUNNING"}, f"Readback failed: {state}"
        assert time.monotonic() < deadline, "Readback timeout; preserve Dataset and stop"
        time.sleep(15)
    proof = {
        "shard_id": shard,
        "status": "VERIFIED",
        "dataset": f"{owner}/{dataset}/versions/1",
        "artifact_sha256": record["artifact_sha256"],
        "artifact_bytes": record["artifact_bytes"],
        "upload_seconds": upload_seconds,
        "upload_outcome": upload_outcome,
        "upload_and_readback_wall_seconds": time.perf_counter() - started,
        "cpu_readback": submitted,
        "peer_acceptance": "pending",
    }
    with (archive.parent / "durability.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(proof, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"durable_shard": proof}), flush=True)
    return proof
