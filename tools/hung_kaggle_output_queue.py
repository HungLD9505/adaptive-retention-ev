"""Serial approved Development groups gated by independent private Output readback."""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from collections.abc import Callable
from pathlib import Path

ALLOCATION_QUEUE_SHA = "12f5bc9ee402a806faedc89574a4e00c427c384335a3868668adf8ce7f93a0f2"
OUTPUT_GROUPS = {
    1: tuple(range(8, 14)),
    2: tuple(range(14, 20)),
    3: tuple(range(20, 26)),
    4: (26, 27, 28),
    5: (33, 34),
    6: (35, 36),
}
PENDING_STORAGE = """    persist_shard(record, base/shard_id/'artifacts.zip', module_prefix(MODULE_SOURCE),
                  owner=OWNER, submit=submit, status=status)"""


def gpu_name(index: int) -> str:
    assert index in OUTPUT_GROUPS
    if index == 1:
        return "hung-group03-shard13-recovery-20261027-v1"
    return f"hung-matched-group{index + 2:02d}-44b8532-20261027-v2"


def readback_name(index: int) -> str:
    assert index in OUTPUT_GROUPS
    if index == 1:
        return "hung-g03-s13-readback-20261027-v1"
    return f"hung-output-g{index + 2:02d}-readback-20261027-v1"


def atomic_record(path: Path, value: dict) -> None:
    """Publish without replacing an old receipt; interrupted partials remain visible."""
    partial = path.with_name(path.name + ".partial")
    with partial.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.link(partial, path)
    partial.unlink()


def available_quota() -> float:
    """Current free provider seconds, excluding reserved time and any paid scaling."""
    from kagglehub.clients import build_kaggle_client
    from kagglesdk.kernels.types.kernels_api_service import ApiGetAcceleratorQuotaStatisticsRequest

    with build_kaggle_client() as client:
        quota = client.kernels.kernels_api_client.get_accelerator_quota_statistics(
            ApiGetAcceleratorQuotaStatisticsRequest()
        ).gpu_quota
    assert quota is not None and not quota.is_pay_to_scale_enabled
    assert all(
        v is not None for v in (quota.total_time_allowed, quota.time_used, quota.time_reserved)
    )
    return (quota.total_time_allowed - quota.time_used - quota.time_reserved).total_seconds()


def output_gpu_source(module: str, setup: str, parity: str, index: int, *, build: Callable) -> str:
    """Preserve the original execution program except its in-GPU Dataset publication."""
    assert index in range(2, 7), "Already-run groups cannot be dispatched"
    source = build(module, setup, parity, index)
    marker = f"\nclaim({gpu_name(index)!r}+'-execute'"
    assert source.count(marker) == 1, "Execution identity changed; review required"
    boundary = source.index(marker)
    prefix, body = source[:boundary], source[boundary:]
    assert body.count(PENDING_STORAGE) == 1, "Storage template changed; review required"
    body = body.replace(
        PENDING_STORAGE,
        "    print(json.dumps({'durability_pending':shard_id,'storage':'Completed private Output + independent CPU readback required'}),flush=True)",
    )
    source = prefix + body
    compile(source, "output-gpu-group", "exec")
    return source


def output_readback_source(module: str, index: int) -> str:
    assert index in range(2, 7)
    source = (
        module
        + f"""
assert not __import__('torch').cuda.is_available(), 'Independent CPU readback only'
records=verify_predecessor(Path('/kaggle/input'),{OUTPUT_GROUPS[index]!r})
proof={{'passed':True,'records':records,'gpu':False,'allocation_sha256':{ALLOCATION_QUEUE_SHA!r},
        'scope':'Development private completed Output readback; scientific acceptance pending'}}
Path('/kaggle/working/readback.json').open('x').write(json.dumps(proof))
print(json.dumps(proof),flush=True)
"""
    )
    compile(source, "output-cpu-readback", "exec")
    return source


def bundle_sources(queue: str, output_queue: str, inventory: str) -> str:
    """Compile versioned programs separately and bind the unchanged allocation."""
    source = "import hashlib\n"
    for name, program in (
        ("QUEUE_PROGRAM", queue),
        ("OUTPUT_PROGRAM", output_queue),
        ("INVENTORY_PROGRAM", inventory),
    ):
        compile(program, name, "exec")
        source += f"{name}={program!r}\n"
        source += f"assert hashlib.sha256({name}.encode()).hexdigest()=={hashlib.sha256(program.encode()).hexdigest()!r}\n"
        source += f"exec(compile({name},{name!r},'exec'),globals())\n"
    source += "validate_groups()\nassert ALLOCATION_SHA==ALLOCATION_QUEUE_SHA\n"
    source += "assert tuple(GROUPS[1:])==tuple(OUTPUT_GROUPS.values())\n"
    compile(source, "output-queue-bundle", "exec")
    return source


def launcher_source(
    bundle: str,
    module: str,
    setup: str,
    parity: str,
    index: int = 2,
    ordinal: int = 0,
    phase: str = "predecessor",
) -> str:
    assert index in range(2, 7) and 0 <= ordinal < 12
    assert phase in {"predecessor", "gpu", "readback"}
    source = (
        bundle
        + f"\nBUNDLE={bundle!r}\nQUEUE_MODULE={module!r}\nSETUP={setup!r}\nPARITY={parity!r}\n"
    )
    source += f"run_output_queue(BUNDLE,QUEUE_MODULE,SETUP,PARITY,{index},{ordinal},{phase!r},"
    source += "submit=submit,status=status,claim_fn=claim,exists=owned_kernel_exists,quota=available_quota,build_gpu=gpu_source)\n"
    compile(source, "output-queue-controller", "exec")
    return source


def run_output_queue(
    bundle: str,
    module: str,
    setup: str,
    parity: str,
    index: int,
    ordinal: int,
    phase: str,
    *,
    submit: Callable,
    status: Callable,
    claim_fn: Callable,
    exists: Callable,
    quota: Callable,
    build_gpu: Callable,
) -> None:
    """One fixed group at a time; resume acknowledged submissions across CPU handoff."""
    assert index in range(2, 7) and 0 <= ordinal < 12
    assert phase in {"predecessor", "gpu", "readback"}
    claim_fn(
        f"hung-output-relay-{ordinal:02d}-execute-20261027-v1",
        {"index": index, "phase": phase, "allocation_sha256": ALLOCATION_QUEUE_SHA},
    )
    root = Path(f"/kaggle/working/output-relay-{ordinal:02d}")
    root.mkdir(exist_ok=False)
    started = time.monotonic()
    known = set()
    while True:
        if phase == "predecessor":
            parent = gpu_name(index - 1)
            parent_state = status(parent)
            assert parent_state in {"QUEUED", "RUNNING", "COMPLETE"}, (parent, parent_state)
            reader = readback_name(index - 1)
            if parent_state == "COMPLETE":
                if reader not in known and exists(reader):
                    known.add(reader)
                state = status(reader) if reader in known else "NOT_OBSERVED"
                assert state in {"NOT_OBSERVED", "QUEUED", "RUNNING", "COMPLETE"}, (reader, state)
                if state == "COMPLETE":
                    available = quota()
                    required = 3600 + len(OUTPUT_GROUPS[index]) * 1810.4 * 1.25
                    assert math.isfinite(available) and available >= required, (
                        "Current quota + reserve insufficient"
                    )
                    print(
                        json.dumps(
                            {
                                "gpu_capacity_gate": {
                                    "index": index,
                                    "available_seconds": available,
                                    "required_seconds": required,
                                }
                            }
                        ),
                        flush=True,
                    )
                    program = output_gpu_source(module, setup, parity, index, build=build_gpu)
                    acknowledgement = submit(gpu_name(index), program, gpu=True, predecessor=parent)
                    atomic_record(root / f"gpu-{index:02d}-submission.json", acknowledgement)
                    phase = "gpu"
        if phase == "gpu":
            state = status(gpu_name(index))
            assert state in {"QUEUED", "RUNNING", "COMPLETE"}, (gpu_name(index), state)
            if state == "COMPLETE":
                acknowledgement = submit(
                    readback_name(index),
                    output_readback_source(module, index),
                    gpu=False,
                    predecessor=gpu_name(index),
                    datasets=[],
                )
                atomic_record(root / f"readback-{index:02d}-submission.json", acknowledgement)
                phase = "readback"
        if phase == "readback":
            state = status(readback_name(index))
            assert state in {"QUEUED", "RUNNING", "COMPLETE"}, (readback_name(index), state)
            if state == "COMPLETE":
                receipt = {
                    "index": index,
                    "shards": OUTPUT_GROUPS[index],
                    "version": 1,
                    "gpu": gpu_name(index),
                    "readback": readback_name(index),
                    "allocation_sha256": ALLOCATION_QUEUE_SHA,
                    "status": "REMOTE_READBACK_VERIFIED",
                    "meaning": "Exact CPU program completed; independent scientific review pending",
                }
                atomic_record(root / f"group-{index:02d}-verified.json", receipt)
                print(json.dumps({"completed_output_group": receipt}), flush=True)
                index += 1
                if index == 7:
                    atomic_record(
                        root / "complete.json",
                        {
                            "terminal_group": 6,
                            "scope": "Development only; earlier relay receipts remain separate; no Final",
                        },
                    )
                    return
                phase = "predecessor"
        if time.monotonic() - started >= 3 * 3600:
            assert ordinal + 1 < 12, "Finite CPU controller bound; stop without resubmitting"
            name = f"hung-output-relay-{ordinal + 1:02d}-20261027-v1"
            program = launcher_source(bundle, module, setup, parity, index, ordinal + 1, phase)
            acknowledgement = submit(name, program, gpu=False, datasets=[])
            atomic_record(
                root / "handoff.json", {"index": index, "phase": phase, "next": acknowledgement}
            )
            return
        time.sleep(60)
