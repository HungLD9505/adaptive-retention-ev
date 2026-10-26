"""Bounded recovery of group03 after an acknowledged-by-readback HTTP499."""

from __future__ import annotations

from tools.hung_kaggle_queue import gpu_source, module_prefix

RECOVERY_SLUG = "hung-matched-group03-recovery-20261027-v1"
SHARD8_DATASET = "hungluongduc/hung-dev-shard0008-44b8532-20261027-v2/1"
SHARD8_SHA = "a49fc9c6c56b5e6cdcf54bb1af15d05cb511d017f3be3cb4abfb41f17dc151e8"


def recovery_module(module_source: str) -> str:
    """Keep all original groups/pins; redirect only the failed group identity."""
    return (
        module_source
        + f"""
original_slug = slug
def slug(index):
    return {RECOVERY_SLUG!r} if index == 1 else original_slug(index)
"""
    )


def replace_once(source: str, old: str, new: str) -> str:
    assert source.count(old) == 1, "Recovery source changed; review required"
    return source.replace(old, new)


def recovered_gpu_source(module_source: str, setup: str, parity: str) -> str:
    """Carry the exact completed shard8 archive; execute only disjoint shards9–13."""
    source = gpu_source(module_source, setup, parity, 1)
    source = replace_once(
        source,
        "readback = verify_predecessor(Path('/kaggle/input'), (2, 3))",
        "readback = verify_predecessor(Path('/kaggle/input'), (8,), archive_name='artifacts.zip.bin')",
    )
    marker = "selected = ['shard_0008', 'shard_0009', 'shard_0010', 'shard_0011', 'shard_0012', 'shard_0013']\nreceipts = []"
    carry = f"""assert readback[0]['sha256'] == {SHARD8_SHA!r}
assert readback[0]['bytes'] == 74362442
original = [p for p in Path('/kaggle/input').rglob('receipt.json')
            if json.loads(p.read_text()).get('shard_id') == 'shard_0008']
assert len(original) == 1
carried = base / 'shard_0008'
carried.mkdir(exist_ok=False)
shutil.copyfile(original[0], carried / 'receipt.json')
shutil.copyfile(original[0].with_name('artifacts.zip.bin'), carried / 'artifacts.zip')
assert provider.sha256(carried/'artifacts.zip') == {SHARD8_SHA!r}
selected = ['shard_0009', 'shard_0010', 'shard_0011', 'shard_0012', 'shard_0013']
assert 'shard_0008' not in selected
receipts = []"""
    source = replace_once(source, marker, carry)
    compile(source, "group03-recovery-gpu", "exec")
    return source


def launcher_source(module_source: str, setup: str, parity: str) -> str:
    """CPU relay validates the terminal failure and shard8 before GPU submission."""
    module = recovery_module(module_source)
    gpu = recovered_gpu_source(module, setup, parity)
    source = module_prefix(module)
    source += f"\nSETUP = {setup!r}\nPARITY = {parity!r}\nRECOVERY_GPU = {gpu!r}\n"
    source += f"""
assert status('hung-matched-group03-44b8532-20261027-v2') == 'ERROR'
assert status('hung-development-cpu-coordinator-20261027-v2') == 'ERROR'
assert status('hung-shard0008-reconcile-cpu-20261027-v1') == 'COMPLETE'
records = verify_predecessor(Path('/kaggle/input'), (8,), archive_name='artifacts.zip.bin')
assert records[0]['sha256'] == {SHARD8_SHA!r} and records[0]['bytes'] == 74362442
Path('/kaggle/working/reconciled-shard0008.json').open('x').write(json.dumps(records))
submit({RECOVERY_SLUG!r}, RECOVERY_GPU, gpu=True, datasets=[PAYLOAD, {SHARD8_DATASET!r}])
relay(MODULE_SOURCE, SETUP, PARITY, 1, 2, submit_current=False)
"""
    compile(source, "group03-recovery-cpu", "exec")
    return source
