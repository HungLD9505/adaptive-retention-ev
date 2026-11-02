"""Finite CPU export batches for the existing Kaggle metric receivers.

Seven disjoint 80-job exports wait on immutable receiver version1 outputs. No GPU,
training, Final data or resubmission on failure. Existing training queues are untouched.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Callable

PLAN_SHA = "2d448d2584f65baf7e09445e013b4283314b08ea2cce855c6850e9fc12ba87ee"
PARTITION_SHA = "7dd340b84a51abca9dcb2e83490d088c07178ffbdbb9d81d68225d665a279c7f"
REUSED_EXPORT = "b7b28cb8c70c75a5268ae94b9026a0ec67d53a5d36f0aa6a51b4e24fefc0035e"
RECEIVER_SHA = "5cfd98dd7c4a64f672a12fce2d5a65454f069d5a2c6a099d3a3d7c7d9fb48571"


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def fixed_batches(readers: list[dict], partition: dict) -> list[dict]:
    """Use the fixed Kaggle route only; reuse the already exported shard8 bytes."""
    assert partition["plan_sha256"] == PLAN_SHA
    shards = {s["id"]: s["job_ids"] for s in partition["shards"]}
    records = {
        r["shard_id"]: {
            **r,
            "reader": f"hung-cpu-metrics-{r['shard_id'].replace('_', '')}-20261027-v1",
            "job_ids": shards[r["shard_id"]],
        }
        for r in readers
    }
    assert len(records) == len(readers) == 27
    records["shard_0008"] = {
        "shard_id": "shard_0008",
        "reader": "hung-portable-shard0008-cpu-export-20261027-v2",
        "reuse_export_sha256": REUSED_EXPORT,
        "job_ids": shards["shard_0008"],
    }
    groups = [(1, 2, 3, 8), *[tuple(range(n, n + 4)) for n in (9, 13, 17, 21, 25, 33)]]
    expected = {f"shard_{i:04d}" for group in groups for i in group}
    assert set(records) == expected, "Foreign or missing Kaggle route"
    seen, result = set(), []
    for i, group in enumerate(groups):
        rows = [records[f"shard_{n:04d}"] for n in group]
        assert all(len(r["job_ids"]) == len(set(r["job_ids"])) == 20 for r in rows)
        jobs = [j for r in rows for j in r["job_ids"]]
        assert len(jobs) == len(set(jobs)) == 80 and not seen.intersection(jobs)
        seen.update(jobs)
        result.append({"id": f"batch_{i:02d}", "records": rows, "job_ids": jobs})
    assert len(seen) == 560
    return result


def batch_name(batch: dict) -> str:
    return f"hung-portable-{batch['id'].replace('_', '')}-20261027-v1"


def cpu_request(name: str, source: str, inputs: list[str], factory: Callable) -> object:
    """Construct a private CPU-only, fixed-version request; no implicit inputs."""
    assert len(inputs) <= 4 and len(inputs) == len(set(inputs))
    request = factory()
    request.slug, request.new_title = f"hungluongduc/{name}", name
    request.text, request.language, request.kernel_type = source, "python", "script"
    request.is_private, request.enable_gpu, request.enable_internet = True, False, bool(not inputs)
    request.session_timeout_seconds = 5 * 3600
    request.dataset_data_sources = []
    request.kernel_data_sources = [f"hungluongduc/{name}/1" for name in inputs]
    return request


def submit_cpu(name: str, source: str, inputs: list[str], *, claim_fn: Callable) -> dict:
    """Submit once using the same native SDK contract as the proven CPU queue."""
    from kagglehub.clients import build_kaggle_client
    from kagglesdk.kernels.types.kernels_api_service import ApiSaveKernelRequest

    source_sha = hashlib.sha256(source.encode()).hexdigest()
    claim_fn(name + "-submit", {"source_sha256": source_sha, "cpu_inputs": inputs})
    request = cpu_request(name, source, inputs, ApiSaveKernelRequest)
    with build_kaggle_client() as client:
        response = client.kernels.kernels_api_client.save_kernel(request)
    assert not response.error and response.version_number == 1, (
        "Submit failed; no retry/version overwrite"
    )
    assert not response.invalid_dataset_sources and not response.invalid_kernel_sources
    receipt = {
        "name": name,
        "url": response.url,
        "version": 1,
        "gpu": False,
        "source_sha256": source_sha,
        "inputs": inputs,
    }
    print(json.dumps({"submitted_cpu_export": receipt}), flush=True)
    return receipt


def producer_source(batch: dict, portable_source: str, scorer_source: str) -> str:
    """Reverify receiver evidence, preserve daily errors and emit small hash-bound transport."""
    source = "import base64, hashlib, json, sys, time, zlib\nfrom pathlib import Path\n"
    source += f"BATCH={batch!r}\nBATCH_SHA={digest(batch)!r}\n"
    source += f"RECEIVER_SHA={RECEIVER_SHA!r}\n"
    source += f"PORTABLE_SOURCE={portable_source!r}\nSCORER_SOURCE={scorer_source!r}\n"
    source += f"assert hashlib.sha256(PORTABLE_SOURCE.encode()).hexdigest()=={hashlib.sha256(portable_source.encode()).hexdigest()!r}\n"
    source += """
import torch
assert not torch.cuda.is_available(), 'CPU export only'
assert hashlib.sha256(json.dumps(BATCH,sort_keys=True,separators=(',',':')).encode()).hexdigest()==BATCH_SHA
assert hashlib.sha256(SCORER_SOURCE.encode()).hexdigest()=='68fccbed056734d9b4842f7bda088880d7812d12417d64878d1aa018fc010456'
code=Path('/kaggle/working/portable-batch-code-v1')
(code/'tools').mkdir(parents=True,exist_ok=False)
for name,content in [('__init__.py',''),('hung_results.py',SCORER_SOURCE),('hung_portable_results.py',PORTABLE_SOURCE)]:
    with (code/'tools'/name).open('x',encoding='utf-8',newline='\\n') as stream: stream.write(content)
sys.path.insert(0,str(code))
from tools import hung_portable_results as portable
started=time.perf_counter()
exports=[]; collections=[]; all_records=[]
proof_files=list(Path('/kaggle/input').rglob('receiver-proof.json'))
for record in BATCH['records']:
    if 'reuse_export_sha256' in record:
        paths=list(Path('/kaggle/input').rglob('portable-shard0008-v1.json'))
        assert len(paths)==1, 'Existing shard8 export missing/ambiguous'
        assert hashlib.sha256(paths[0].read_bytes()).hexdigest()==record['reuse_export_sha256']
        value=json.loads(paths[0].read_bytes())
    else:
        candidates=[p for p in proof_files if json.loads(p.read_bytes()).get('shard_id')==record['shard_id']]
        assert len(candidates)==1, 'Exact CPU receiver missing/ambiguous'
        proof_path=candidates[0]; proof=json.loads(proof_path.read_bytes())
        assert proof_path.parent.name==record['base']
        assert proof['plan_sha256']==record['plan_sha256'] and proof['partition_sha256']==record['partition_sha256']
        assert proof['receiver_sha256']==RECEIVER_SHA
        assert proof['transport_helper_sha256']=='cadcd80d671d3b49a317312f125735362ffba3068247f1714a0ae56c6be83424'
        assert proof['derivation']['parent_shards_sha256']=='7dd340b84a51abca9dcb2e83490d088c07178ffbdbb9d81d68225d665a279c7f'
        value=portable.export_receiver(proof_path.parent,hashlib.sha256(proof_path.read_bytes()).hexdigest())
    assert len(value['records'])==20 and {r['job_id'] for r in value['records']}==set(record['job_ids'])
    path=Path('/kaggle/working')/('portable-'+record['shard_id']+'.json')
    with path.open('x',encoding='utf-8',newline='\\n') as stream: json.dump(value,stream,sort_keys=True,allow_nan=False)
    pin={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    collections.append({'export':pin,'job_ids':record['job_ids']})
    exports.append(pin); all_records.extend(value['records'])
spec={'scope':'development_only','collections':collections}
spec_path=Path('/kaggle/working/merge-spec.json')
with spec_path.open('x',encoding='utf-8') as stream: json.dump(spec,stream,sort_keys=True,allow_nan=False)
result=portable.merge_collections({**spec,'spec_sha256':hashlib.sha256(spec_path.read_bytes()).hexdigest()},Path('/kaggle/working'))
assert result['counts']['runs']==80 and {r['job_id'] for r in all_records}==set(BATCH['job_ids'])
with Path('/kaggle/working/partial-results.json').open('x',encoding='utf-8') as stream: json.dump(result,stream,sort_keys=True,allow_nan=False)
value={'schema':'hung-portable-daily-errors-v1','scope':'development_only','canonical_plan_sha256':portable.PLAN_SHA,
       'scorer_sha256':portable.SCORER_SHA,'provenance':{'batch_sha256':BATCH_SHA,'exports':exports},
       'acceptance':'Technical export; independent review pending','records':all_records}
body=(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\\n').encode()
with Path('/kaggle/working/portable-batch.json').open('xb') as stream: stream.write(body)
encoded=base64.b64encode(zlib.compress(body)).decode('ascii')
chunks=[encoded[i:i+3000] for i in range(0,len(encoded),3000)]
summary={'scope':'development_only','batch':BATCH['id'],'batch_sha256':BATCH_SHA,'executed':False,'gpu':False,
         'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'chunks':len(chunks),
         'elapsed_seconds':time.perf_counter()-started,'counts':result['counts']}
with Path('/kaggle/working/export-summary.json').open('x',encoding='utf-8') as stream: json.dump(summary,stream,sort_keys=True)
print(json.dumps({'portable_export':summary}),flush=True)
for i,data in enumerate(chunks): print(json.dumps({'portable_chunk':i,'data':data}),flush=True)
"""
    compile(source, "portable-batch-producer", "exec")
    return source


def source_bundle(queue: str, metric_queue: str, exports: str, portable: str, scorer: str) -> str:
    """Freeze separately compiled modules; never modify an existing live notebook."""
    result = "import hashlib\n"
    for name, source in {
        "QUEUE_SOURCE": queue,
        "METRIC_SOURCE": metric_queue,
        "EXPORT_SOURCE": exports,
        "PORTABLE_SOURCE": portable,
        "SCORER_SOURCE": scorer,
    }.items():
        compile(source, name, "exec")
        result += f"{name}={source!r}\nassert hashlib.sha256({name}.encode()).hexdigest()=={hashlib.sha256(source.encode()).hexdigest()!r}\n"
    for name in ("QUEUE_SOURCE", "METRIC_SOURCE", "EXPORT_SOURCE"):
        result += f"exec(compile({name},{name!r},'exec'),globals())\n"
    return result


def controller_source(
    bundle: str, batches: list[dict], expected_sha: str, index: int, ordinal: int, submitted: bool
) -> str:
    source = bundle + f"\nEXPORT_BUNDLE={bundle!r}\nEXPORT_BATCHES={batches!r}\n"
    source += "def submit_export(name,source,inputs):\n    return submit_cpu(name,source,inputs,claim_fn=claim)\n"
    source += f"run_exports(EXPORT_BUNDLE,EXPORT_BATCHES,{expected_sha!r},{index},{ordinal},{submitted!r},submit=submit_export,status=status,claim_fn=claim,exists=owned_kernel_exists,portable=PORTABLE_SOURCE,scorer=SCORER_SOURCE)\n"
    compile(source, "cpu-export-coordinator", "exec")
    return source


def run_exports(
    bundle: str,
    batches: list[dict],
    expected_sha: str,
    index: int,
    ordinal: int,
    submitted: bool,
    *,
    submit: Callable,
    status: Callable,
    claim_fn: Callable,
    exists: Callable,
    portable: str,
    scorer: str,
) -> None:
    """Wait on owned handles; a failed pilot/reader blocks all subsequent exports."""
    assert digest(batches) == expected_sha, "Export allocation changed"
    assert 0 <= index < len(batches) and 0 <= ordinal < 12
    claim_fn(
        f"hung-portable-relay-{ordinal:02d}-execute-20261027-v1",
        {"batch_index": index, "manifest_sha256": expected_sha},
    )
    root = Path(f"/kaggle/working/portable-relay-{ordinal:02d}")
    root.mkdir(exist_ok=False)
    started = time.monotonic()
    known = set()
    while True:
        batch = batches[index]
        if not submitted:
            ready = True
            for row in batch["records"]:
                name = row["reader"]
                if name not in known and exists(name):
                    known.add(name)
                state = status(name) if name in known else "NOT_OBSERVED"
                assert state in {"NOT_OBSERVED", "QUEUED", "RUNNING", "COMPLETE"}, (
                    f"Receiver failed: {state}"
                )
                ready = ready and state == "COMPLETE"
            if ready:
                submit(
                    batch_name(batch),
                    producer_source(batch, portable, scorer),
                    [r["reader"] for r in batch["records"]],
                )
                submitted = True
        if submitted:
            state = status(batch_name(batch))
            assert state in {"QUEUED", "RUNNING", "COMPLETE"}, (
                f"CPU batch failed; later exports blocked: {state}"
            )
            if state == "COMPLETE":
                receipt = {
                    "batch": batch["id"],
                    "name": batch_name(batch),
                    "version": 1,
                    "state": state,
                    "jobs": len(batch["job_ids"]),
                    "manifest_sha256": expected_sha,
                    "meaning": "CPU computation complete; independent hash readback/peer review pending",
                }
                with (root / (batch["id"] + ".json")).open("x", encoding="utf-8") as stream:
                    json.dump(receipt, stream)
                print(json.dumps({"completed_cpu_export": receipt}), flush=True)
                index += 1
                submitted = False
                if index == len(batches):
                    with (root / "complete.json").open("x", encoding="utf-8") as stream:
                        json.dump(
                            {"batches": len(batches), "manifest_sha256": expected_sha}, stream
                        )
                    return
        if time.monotonic() - started >= 3 * 3600:
            assert ordinal + 1 < 12, "Finite CPU export relay limit"
            next_name = f"hung-portable-coordinator-{ordinal + 1:02d}-20261027-v1"
            submit(
                next_name,
                controller_source(bundle, batches, expected_sha, index, ordinal + 1, submitted),
                [],
            )
            with (root / "handoff.json").open("x", encoding="utf-8") as stream:
                json.dump({"next": next_name, "batch_index": index, "submitted": submitted}, stream)
            return
        time.sleep(120)
