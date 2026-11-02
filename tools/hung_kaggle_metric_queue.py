"""Finite CPU-only receivers for the existing immutable Kaggle Development route."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

TRIAL = "hung-shard0008-full-cpu-restore-20261027-v1"
MODEL_CODE = "44b8532959d76fb20691881539f991ca44983727"
PAYLOAD_SHA = "23a6d420523d990d07ff07d814ed642a851925283a102a3ae806f3b666e1d6f4"
HELPER_SHA = "cadcd80d671d3b49a317312f125735362ffba3068247f1714a0ae56c6be83424"


def bundle_sources(queue: str, metric_queue: str, receiver: str, scorer: str) -> str:
    """Compile separate versioned modules, preserving future-import boundaries."""
    sources = {
        "QUEUE_SOURCE": queue,
        "METRIC_SOURCE": metric_queue,
        "RECEIVER_SOURCE": receiver,
        "SCORER_SOURCE": scorer,
    }
    result = "import hashlib\n"
    for name, source in sources.items():
        compile(source, name, "exec")
        result += f"{name}={source!r}\n"
        result += f"assert hashlib.sha256({name}.encode()).hexdigest()=={hashlib.sha256(source.encode()).hexdigest()!r}\n"
    result += "exec(compile(QUEUE_SOURCE,'pinned_queue','exec'),globals())\n"
    result += "exec(compile(METRIC_SOURCE,'pinned_metric_queue','exec'),globals())\n"
    compile(result, "cpu-metric-bundle", "exec")
    return result


def readers(groups: tuple, provider_pins: dict) -> list[dict]:
    """Only allocated Kaggle shards; the already-running shard8 trial is reused."""
    result = [
        {
            "shard_id": "shard_0001",
            "training": "hung-matched-shard0001-44b8532-20261027",
            "base": "hung-matched-shard0001-v1",
            "plan_sha256": "80a1666cf2083594c9a2bc0b0a4dc3e30118eda43d07187cd5b6d8b51f90e0bb",
            "partition_sha256": "e2c6cb6f15a7473c6cdfd7912fefa838d63a770cf352dff93c2cccc3ae86a15c",
        }
    ]
    for index, group in enumerate(groups):
        training = (
            "hung-matched-group03-recovery-20261027-v2"
            if index == 1
            else f"hung-matched-group{index + 2:02d}-44b8532-20261027" + ("-v2" if index else "")
        )
        for number in group:
            if number == 8:
                continue
            shard = f"shard_{number:04d}"
            plan_sha, partition_sha = provider_pins[shard]
            result.append(
                {
                    "shard_id": shard,
                    "training": training,
                    "base": f"hung-matched-group{index + 2:02d}-v1",
                    "plan_sha256": plan_sha,
                    "partition_sha256": partition_sha,
                }
            )
    expected = {1, 2, 3, *range(9, 29), 33, 34, 35, 36}
    assert {int(r["shard_id"][6:]) for r in result} == expected and len(result) == len(expected)
    return result


def reader_name(record: dict) -> str:
    return f"hung-cpu-metrics-{record['shard_id'].replace('_', '')}-20261027-v1"


def owned_kernel_exists(slug_name: str) -> bool:
    """Observe owned resources before asking status of a not-yet-submitted group."""
    from kagglehub.clients import build_kaggle_client
    from kagglesdk.kernels.types.kernels_api_service import ApiListKernelsRequest
    from kagglesdk.kernels.types.kernels_enums import KernelsListViewType

    request = ApiListKernelsRequest()
    request.user, request.page_size = "hungluongduc", 100
    request.group = KernelsListViewType.PUBLIC_AND_USERS_PRIVATE
    seen = set()
    with build_kaggle_client() as client:
        for _ in range(10):
            result = client.kernels.kernels_api_client.list_kernels(request)
            if any(k.ref == f"hungluongduc/{slug_name}" for k in result.kernels):
                return True
            if not result.next_page_token:
                return False
            assert result.next_page_token not in seen, "Owned inventory pagination repeated"
            seen.add(result.next_page_token)
            request.page_token = result.next_page_token
    raise ValueError("Owned inventory bound exceeded; no status/submission inference")


def receiver_source(record: dict, receiver: str, scorer: str) -> str:
    import hashlib

    source = """import hashlib, importlib.util, json, types
from pathlib import Path
import torch
assert not torch.cuda.is_available(), 'CPU receiver only'
"""
    source += f"SPEC={record!r}\nRECEIVER_SOURCE={receiver!r}\nSCORER_SOURCE={scorer!r}\n"
    source += f"MODEL_CODE={MODEL_CODE!r}\nPAYLOAD_SHA={PAYLOAD_SHA!r}\nHELPER_SHA={HELPER_SHA!r}\n"
    source += f"RECEIVER_SHA={hashlib.sha256(receiver.encode()).hexdigest()!r}\n"
    source += f"SCORER_SHA={hashlib.sha256(scorer.encode()).hexdigest()!r}\n"
    source += """
payloads=list(Path('/kaggle/input').rglob('provider-payload.zip.bin'))
assert len(payloads)==1, 'Pinned payload missing/ambiguous'
helper=payloads[0].parent/'hung_provider.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest()==HELPER_SHA
module_spec=importlib.util.spec_from_file_location('hung_provider',helper)
provider=importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(provider)
receipts=[p for p in Path('/kaggle/input').rglob('receipt.json')
          if p.with_name('artifacts.zip').is_file()
          and json.loads(p.read_bytes()).get('shard_id')==SPEC['shard_id']]
assert len(receipts)==1, 'Canonical completed shard missing/ambiguous'
repo,plan=provider.materialize(payloads[0],PAYLOAD_SHA,Path('/kaggle/working')/SPEC['base'])
assert provider.sha256(plan)==SPEC['plan_sha256']
assert provider.sha256(repo/'.cache/provider/shards.json')==SPEC['partition_sha256']
assert hashlib.sha256(RECEIVER_SOURCE.encode()).hexdigest()==RECEIVER_SHA
assert hashlib.sha256(SCORER_SOURCE.encode()).hexdigest()==SCORER_SHA
receiver=types.ModuleType('pinned_cloud_receiver')
exec(compile(RECEIVER_SOURCE,'pinned_cloud_receiver','exec'),receiver.__dict__)
scorer={'__name__':'pinned_saved_forecast_scorer'}
exec(compile(SCORER_SOURCE,'pinned_saved_forecast_scorer','exec'),scorer)
summary=receiver.receive(provider,scorer,receipts[0].with_name('artifacts.zip'),receipts[0],repo,
                         expected_code=MODEL_CODE,evidence=repo.parent/'cpu-readback',
                         scorer_sha256=SCORER_SHA)
assert summary['passed'] and summary['executed'] is False and summary['jobs']==20
summary.update({'receiver_sha256':RECEIVER_SHA,'transport_helper_sha256':HELPER_SHA,
                'derivation':json.loads((repo.parent/'derivation.json').read_bytes()),
                'device':'cpu','torch':torch.__version__})
assert summary['derivation']['parent_plan_sha256']=='2d448d2584f65baf7e09445e013b4283314b08ea2cce855c6850e9fc12ba87ee'
provider.save(repo.parent/'receiver-proof.json',summary)
print(json.dumps({'receiver_proof':summary}),flush=True)
"""
    compile(source, "cpu-shard-receiver", "exec")
    return source


def relay_source(
    bundle: str, records: list[dict], index: int, ordinal: int, submitted: bool
) -> str:
    source = bundle + f"\nMETRIC_BUNDLE={bundle!r}\nMETRIC_READERS={records!r}\n"
    source += (
        "assert owned_kernel_exists(METRIC_READERS[0]['training']), 'Owned inventory capability gate failed'\n"
        "print(json.dumps({'owned_inventory_capability':'passed','gpu':False}),flush=True)\n"
    )
    source += (
        f"run_queue(METRIC_BUNDLE,METRIC_READERS,{index},{ordinal},{submitted!r},"
        "submit=submit,status=status,claim=claim,exists=owned_kernel_exists,receiver=RECEIVER_SOURCE,scorer=SCORER_SOURCE)\n"
    )
    compile(source, "cpu-receiver-relay", "exec")
    return source


def run_queue(
    bundle: str,
    records: list[dict],
    index: int,
    ordinal: int,
    submitted: bool,
    *,
    submit,
    status,
    claim,
    exists,
    receiver: str,
    scorer: str,
) -> None:
    """Only provider status handles drive handoffs; no GPU or submission retry."""
    assert 0 <= index < len(records) and ordinal < 12
    assert len({r["shard_id"] for r in records}) == len(records)
    claim(f"hung-cpu-metrics-relay-{ordinal:02d}-execute-20261027-v1", {"reader_index": index})
    root = Path(f"/kaggle/working/cpu-metrics-relay-{ordinal:02d}")
    root.mkdir(exist_ok=False)
    started = time.monotonic()
    known_training = set()
    while True:
        trial = status(TRIAL)
        assert trial in {"QUEUED", "RUNNING", "COMPLETE"}, f"CPU trial failed: {trial}"
        record = records[index]
        if trial == "COMPLETE":
            if not submitted:
                name = record["training"]
                if name not in known_training and exists(name):
                    known_training.add(name)
                training = status(name) if name in known_training else "NOT_OBSERVED"
                assert training in {"NOT_OBSERVED", "QUEUED", "RUNNING", "COMPLETE"}, (
                    f"Provider failed: {training}"
                )
                if training == "COMPLETE":
                    submit(
                        reader_name(record),
                        receiver_source(record, receiver, scorer),
                        gpu=False,
                        predecessor=record["training"],
                    )
                    submitted = True
            if submitted:
                state = status(reader_name(record))
                assert state in {"QUEUED", "RUNNING", "COMPLETE"}, f"CPU receiver failed: {state}"
                if state == "COMPLETE":
                    proof = {
                        "shard_id": record["shard_id"],
                        "cpu_reader": reader_name(record),
                        "version": 1,
                        "status": state,
                        "scope": "Development technical readback only",
                    }
                    with (root / (record["shard_id"] + ".json")).open(
                        "x", encoding="utf-8"
                    ) as stream:
                        json.dump(proof, stream)
                    print(json.dumps({"completed_cpu_receiver": proof}), flush=True)
                    index += 1
                    submitted = False
                    if index == len(records):
                        with (root / "complete.json").open("x", encoding="utf-8") as stream:
                            json.dump({"receivers": len(records)}, stream)
                        return
        if time.monotonic() - started >= 3 * 3600:
            assert ordinal + 1 < 12, "CPU receiver relay limit"
            name = f"hung-cpu-metrics-coordinator-{ordinal + 1:02d}-20261027-v1"
            submit(
                name,
                relay_source(bundle, records, index, ordinal + 1, submitted),
                gpu=False,
                datasets=[],
            )
            with (root / "handoff.json").open("x", encoding="utf-8") as stream:
                json.dump(
                    {"next": name, "reader_index": index, "current_reader_submitted": submitted},
                    stream,
                )
            return
        time.sleep(60)
