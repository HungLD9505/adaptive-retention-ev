"""One missing Development shard; completed Save & Run output is the storage barrier."""

from __future__ import annotations

from tools.hung_kaggle_queue import gpu_source, module_prefix
from tools.hung_kaggle_recovery import replace_once

GPU_NAME = "hung-group03-shard13-recovery-20261027-v1"
READBACK_NAME = "hung-g03-s13-readback-20261027-v1"
CONTROLLER_CLAIM = "hung-g03-s13-controller-execute-20261027-v2"
CARRIED = (8, 9, 10, 11, 12)
ARCHIVE_PINS = {
    8: (74362442, "a49fc9c6c56b5e6cdcf54bb1af15d05cb511d017f3be3cb4abfb41f17dc151e8"),
    9: (68786447, "37f635185da5bf08fd927e0ecacb9efb53f41f2b87f85ad3554f5a92ee53de5e"),
    10: (66147049, "c83b3af82e5eedc2c4b68d0bb1d808b10e66fb037708bb5345c38ae3c602b180"),
    11: (317485131, "959dbb76e407ac6c1ff7fce723fdc1510046280b1b473902ede231ff79bcfc6b"),
    12: (452751164, "d0f7f0335745843adbf16b5c05aafd7fb7a4505ba13c92ab649849677d9b92dc"),
}


def recovery_gpu(module: str, setup: str, parity: str) -> str:
    """Reuse original paths/pins; copy verified archives, execute exactly shard13."""
    source = gpu_source(module, setup, parity, 1)
    source = replace_once(
        source,
        "claim('hung-matched-group03-44b8532-20261027-v2'+'-execute', {'group_index': 1})",
        f"claim({GPU_NAME!r}+'-execute', {{'group_index': 1, 'only': 'shard_0013'}})",
    )
    source = replace_once(
        source,
        "readback = verify_predecessor(Path('/kaggle/input'), (2, 3))",
        f"readback = verify_predecessor(Path('/kaggle/input'), {CARRIED!r}, archive_name='artifacts.zip.bin')",
    )
    selected = "selected = ['shard_0008', 'shard_0009', 'shard_0010', 'shard_0011', 'shard_0012', 'shard_0013']\nreceipts = []"
    carry = f"""archive_pins = {ARCHIVE_PINS!r}
for number, record in zip({CARRIED!r}, readback, strict=True):
    expected_bytes, expected_sha = archive_pins[number]
    assert (record['bytes'], record['sha256']) == (expected_bytes, expected_sha)
    name = f'shard_{{number:04d}}'
    matches = [p for p in Path('/kaggle/input').rglob('receipt.json')
               if json.loads(p.read_text()).get('shard_id') == name
               and p.with_name('artifacts.zip.bin').is_file()]
    assert len(matches) == 1
    folder = base / name
    folder.mkdir(exist_ok=False)
    shutil.copyfile(matches[0], folder/'receipt.json')
    shutil.copyfile(matches[0].with_name('artifacts.zip.bin'), folder/'artifacts.zip')
    assert provider.sha256(folder/'artifacts.zip') == expected_sha
selected = ['shard_0013']
receipts = []"""
    source = replace_once(source, selected, carry)
    boundary = source.index(f"claim({GPU_NAME!r}+'-execute'")
    source = source[:boundary] + replace_once(
        source[boundary:],
        "    persist_shard(record, base/shard_id/'artifacts.zip', module_prefix(MODULE_SOURCE),\n                  owner=OWNER, submit=submit, status=status)",
        "    print(json.dumps({'durability_pending': shard_id, 'barrier': 'Completed private Save & Run version + independent CPU output readback'}), flush=True)",
    )
    # No Dataset creation/readback is attempted inside this GPU version. Its
    # immutable Output must exist before the independent CPU child is submitted.
    compile(source, "shard13-recovery-gpu", "exec")
    return source


def launcher(module: str, setup: str, parity: str) -> str:
    """CPU validates terminal predecessors/quota, submits one GPU, then one CPU proof."""
    gpu = recovery_gpu(module, setup, parity)
    proof = (
        module_prefix(module)
        + """
assert not __import__('torch').cuda.is_available(), 'CPU readback only'
records = verify_predecessor(Path('/kaggle/input'), (8,9,10,11,12,13))
proof = {'passed': True, 'records': records,
         'storage': 'Private completed Save & Run All notebook version 1',
         'scope': 'Development durability only; peer acceptance and Final remain pending'}
Path('/kaggle/working/readback.json').open('x').write(json.dumps(proof))
print(json.dumps(proof), flush=True)
"""
    )
    source = module_prefix(module)
    source += f"\nRECOVERY_GPU={gpu!r}\nOUTPUT_PROOF={proof!r}\n"
    source += f"""
assert status('hung-matched-group03-recovery-20261027-v2') == 'ERROR'
assert status('hung-dev-readback-shard0012-20261027-v2') == 'ERROR'
assert status('hung-shard0012-reconcile-cpu-20261027-v2') == 'COMPLETE'
assert status('hung-shard0013-recovery-cpu-20261027-v1') == 'ERROR'
claim({CONTROLLER_CLAIM!r}, {{'only':'shard_0013'}})
from kagglehub.clients import build_kaggle_client
from kagglesdk.kernels.types.kernels_api_service import ApiGetAcceleratorQuotaStatisticsRequest
with build_kaggle_client() as client:
    quota = client.kernels.kernels_api_client.get_accelerator_quota_statistics(
        ApiGetAcceleratorQuotaStatisticsRequest()).gpu_quota
assert quota is not None and not quota.is_pay_to_scale_enabled
assert all(v is not None for v in (quota.total_time_allowed,quota.time_used,quota.time_reserved))
available=(quota.total_time_allowed-quota.time_used-quota.time_reserved).total_seconds()
required=3600+1810.4*1.25
assert available >= required, 'Fresh quota + reserve insufficient'
print(json.dumps({{'available_gpu_seconds':available,'required_gpu_seconds':required}}),flush=True)
datasets=[PAYLOAD]+[f'{{OWNER}}/hung-dev-shard{{n:04d}}-44b8532-20261027-v2/1' for n in {CARRIED!r}]
submit({GPU_NAME!r},RECOVERY_GPU,gpu=True,datasets=datasets)
deadline=time.monotonic()+3*3600
while True:
    state=status({GPU_NAME!r})
    if state=='COMPLETE': break
    assert state in {{'QUEUED','RUNNING'}}, ('Recovery stopped; preserve output',state)
    assert time.monotonic()<deadline,'Bounded controller timeout; do not resubmit GPU'
    time.sleep(60)
submit({READBACK_NAME!r},OUTPUT_PROOF,gpu=False,predecessor={GPU_NAME!r},datasets=[])
print(json.dumps({{'gpu_complete':{GPU_NAME!r},'cpu_readback_submitted':{READBACK_NAME!r},
                  'next_groups':'Not submitted by this bounded recovery'}}),flush=True)
"""
    compile(source, "shard13-recovery-cpu", "exec")
    return source
