"""Build bounded private Kaggle Development jobs and a CPU-only relay.

Uses Kaggle's existing notebook identity. No credentials, paid scaling, Final
labels or local work are included. Submission failures are never retried.
"""

from __future__ import annotations

import hashlib
import json
import time
import zipfile
from pathlib import Path

OWNER = "hungluongduc"
PAYLOAD = f"{OWNER}/hung-matched-payload-44b8532-20261027-v1/1"
ALLOCATION_SHA = "12f5bc9ee402a806faedc89574a4e00c427c384335a3868668adf8ce7f93a0f2"
GROUPS = (
    (2, 3),
    tuple(range(8, 14)),
    tuple(range(14, 20)),
    tuple(range(20, 26)),
    (26, 27, 28),
    (33, 34),
    (35, 36),
)
LOCAL = {4, 5, 6, 7, 29, 30, 31, 32, 37, 38, 39}
EXPECTED_JOBSET_SHA = {
    "shard_0001": "e2051de08dfb0f0ee91c3617151f08d5cd2c712bb88344244980e4ec2f350c69",
    "shard_0002": "1cf89024e9c8b9d8488b386a54a0995924fad19a9334f9539d50843d345260f1",
    "shard_0003": "145d75ce5a847f1494d7ec4285e47812c769acb7206bc0da7a20a48e4545f4d8",
    "shard_0004": "a7e50150565ca83055e33a9b246e6f8ae7fea6b376d4e1cde6ae55ec0aa8192a",
    "shard_0005": "0912c4c7c32350f611bce7493b207cba24810e4aaa20d793a7ee8f2769e1990c",
    "shard_0006": "50b870631b6c422dc5b2a29c5e71288a1c07de79428e36cadd989d0a764d1a28",
    "shard_0007": "7b448f6b347ad6feae86b5301d97ad4e14a5d590ef70f24c0e6a877149144ec5",
    "shard_0008": "928996ffad7ba48f210d2b69cc23cdf4c402a8d34c9a79be76a58a1591d7ff9d",
    "shard_0009": "ac51753e9c13f2e6f0677fda3e1e67174fb8a2080a7a859e02465a0c790278f0",
    "shard_0010": "9ec71c246ca5334cc5a622cbff9e7b76e6535e447ce0ae6520a8ee9095dc34a3",
    "shard_0011": "7ff773c49768e8f73a3b7245e6b6a178de0f599adccee87234f2c4dfa2299932",
    "shard_0012": "ae3f9b967f922de325bd35c045eeaafddb3647da47c09d2749887c0351102017",
    "shard_0013": "d19ce730e5d2bd6d02c545359838569e1b712269689a58f9ca0e1a03d30b18b8",
    "shard_0014": "1454cb90a5e8e0406617e4a0a8a1408040ae570ed6ce9cf81479e08878b5b6a8",
    "shard_0015": "e839173725dde0f0e4fb122a9813fac263907e08dd9889d2011073e1e52c30d6",
    "shard_0016": "ad6e9fe1219eec06bcde8a95ef333f50bee40c27ed97459375d208e76a01ed0f",
    "shard_0017": "a494de718f33adde057a68ef1b4e9e0ea31b56461594f9316fdb6e45211fee75",
    "shard_0018": "05c45a5b8bed8e143d16053d892c8abede23633e6c7d96d41288b601f429df20",
    "shard_0019": "15761f42e1b901f0b99f98d90a61f9c9f81ba058535054f612be11867048bfef",
    "shard_0020": "15e41973e7f727fdcbe7f239922ad02dc05c8efe77cc9609245e29f6278be493",
    "shard_0021": "14e4fc0a128f8ed81e52b34d15af9a123503e0d5903f65eb16b5a20c477de5cb",
    "shard_0022": "229dfba032263815967bfa18f3a5baef677747ed0c6f828e89202c12703e78fc",
    "shard_0023": "f9def5fc4236ed9d9a540c937d554795b4da684d6b0705225dc8dff0f7f01c69",
    "shard_0024": "86cb50e120c3081676b0e75a13055659ab17c7092ea8473e311fadad1328ce00",
    "shard_0025": "ffc9c9a46dc12a5f843182e1e092c2e434cab2432d218ae1076b987c3b3e1937",
    "shard_0026": "3cc709041d096465692797a24d8290c6b8d2e14f3e994d50a734c8fe34e64646",
    "shard_0027": "19f14ba77bf687edcf8847933ea5807006096d9a8eb0128560ad20f1cddc5369",
    "shard_0028": "a1328e31335db38f13e20e843025c25e6767ed1e86e11ff39b1da10a994db567",
    "shard_0029": "33c10aa43b9d1c2675b4cc89e087a12e6c8875c5cd0ac5789a39775a760e7dfc",
    "shard_0030": "a908b9eb43e288809722c1c8300370bf0acac961aaaba25d98a169008457395a",
    "shard_0031": "35d10c724dd8ac4ed4bb03f864c35288f9edc453900024e12383a328d0c6a0d9",
    "shard_0032": "b6fc0d6d0924f2c970da1e40783c6f9ef740d5898458c7caffb7c66830659270",
    "shard_0033": "a570c5e215f60b6463e4641f73ce13f7035552162a851d754f524d754031debe",
    "shard_0034": "79b8e55f8a74e34b504a736555e9add02e1422bbd5a872509bdab00ae4a21d8a",
    "shard_0035": "0ecdc975791fe6b62b0d1be6514d5ca243b3892bf8e8fe612be00dd71a93dac0",
    "shard_0036": "c0f24e5038e361798c83d44bd292ef8d099cf575ba00fcab92d55cf178873c2a",
    "shard_0037": "aee8e665e66576f461c3a69de62ede64c0840c1189c8e26b51c158cd3b2303ce",
    "shard_0038": "09b5c62ae11c1563ee12d6d97c9e10902a48da50a89d80129b581721b35606f2",
    "shard_0039": "4177fe39acd6ac291e38b82aea9cc148376f578a58de1bf2d875ed9fa8dddab4",
}


EXPECTED_PROVIDER_PINS = {
    "shard_0002": (
        "70dff1c41380aa781062470b6986829e470e320a1cd0522ac49c63956ea6d12d",
        "7d99e722c6e27b7257a709182a0827b63c4a1599cfe14f3472e9e4a914cf8ad1",
    ),
    "shard_0003": (
        "70dff1c41380aa781062470b6986829e470e320a1cd0522ac49c63956ea6d12d",
        "7d99e722c6e27b7257a709182a0827b63c4a1599cfe14f3472e9e4a914cf8ad1",
    ),
    "shard_0008": (
        "34f252fd19e33698a56faf4f3b19e921248ddf419b91fdfc3a69e7bc3f63f1a4",
        "3f022fe12fe9918062959240b8f1dd3be9b25f18fdcae982ba972f867e78c342",
    ),
    "shard_0009": (
        "34f252fd19e33698a56faf4f3b19e921248ddf419b91fdfc3a69e7bc3f63f1a4",
        "3f022fe12fe9918062959240b8f1dd3be9b25f18fdcae982ba972f867e78c342",
    ),
    "shard_0010": (
        "34f252fd19e33698a56faf4f3b19e921248ddf419b91fdfc3a69e7bc3f63f1a4",
        "3f022fe12fe9918062959240b8f1dd3be9b25f18fdcae982ba972f867e78c342",
    ),
    "shard_0011": (
        "34f252fd19e33698a56faf4f3b19e921248ddf419b91fdfc3a69e7bc3f63f1a4",
        "3f022fe12fe9918062959240b8f1dd3be9b25f18fdcae982ba972f867e78c342",
    ),
    "shard_0012": (
        "34f252fd19e33698a56faf4f3b19e921248ddf419b91fdfc3a69e7bc3f63f1a4",
        "3f022fe12fe9918062959240b8f1dd3be9b25f18fdcae982ba972f867e78c342",
    ),
    "shard_0013": (
        "34f252fd19e33698a56faf4f3b19e921248ddf419b91fdfc3a69e7bc3f63f1a4",
        "3f022fe12fe9918062959240b8f1dd3be9b25f18fdcae982ba972f867e78c342",
    ),
    "shard_0014": (
        "754fa4f3a7e79a017b64fb36ca19624c224f84b773cb88c570f74cd406b7ea4d",
        "60b67243dd5911dd0a63061ad7430732db3381bdc0777c14b900316fc46e6781",
    ),
    "shard_0015": (
        "754fa4f3a7e79a017b64fb36ca19624c224f84b773cb88c570f74cd406b7ea4d",
        "60b67243dd5911dd0a63061ad7430732db3381bdc0777c14b900316fc46e6781",
    ),
    "shard_0016": (
        "754fa4f3a7e79a017b64fb36ca19624c224f84b773cb88c570f74cd406b7ea4d",
        "60b67243dd5911dd0a63061ad7430732db3381bdc0777c14b900316fc46e6781",
    ),
    "shard_0017": (
        "754fa4f3a7e79a017b64fb36ca19624c224f84b773cb88c570f74cd406b7ea4d",
        "60b67243dd5911dd0a63061ad7430732db3381bdc0777c14b900316fc46e6781",
    ),
    "shard_0018": (
        "754fa4f3a7e79a017b64fb36ca19624c224f84b773cb88c570f74cd406b7ea4d",
        "60b67243dd5911dd0a63061ad7430732db3381bdc0777c14b900316fc46e6781",
    ),
    "shard_0019": (
        "754fa4f3a7e79a017b64fb36ca19624c224f84b773cb88c570f74cd406b7ea4d",
        "60b67243dd5911dd0a63061ad7430732db3381bdc0777c14b900316fc46e6781",
    ),
    "shard_0020": (
        "4b0c6e5b63d5a7e28165454988650bcbdcc6b61ccea375899840197780574fe5",
        "fddd50e4992855dd5519b8562bce1daee0a2dfc31ab20181a23e11a7b5405666",
    ),
    "shard_0021": (
        "4b0c6e5b63d5a7e28165454988650bcbdcc6b61ccea375899840197780574fe5",
        "fddd50e4992855dd5519b8562bce1daee0a2dfc31ab20181a23e11a7b5405666",
    ),
    "shard_0022": (
        "4b0c6e5b63d5a7e28165454988650bcbdcc6b61ccea375899840197780574fe5",
        "fddd50e4992855dd5519b8562bce1daee0a2dfc31ab20181a23e11a7b5405666",
    ),
    "shard_0023": (
        "4b0c6e5b63d5a7e28165454988650bcbdcc6b61ccea375899840197780574fe5",
        "fddd50e4992855dd5519b8562bce1daee0a2dfc31ab20181a23e11a7b5405666",
    ),
    "shard_0024": (
        "4b0c6e5b63d5a7e28165454988650bcbdcc6b61ccea375899840197780574fe5",
        "fddd50e4992855dd5519b8562bce1daee0a2dfc31ab20181a23e11a7b5405666",
    ),
    "shard_0025": (
        "4b0c6e5b63d5a7e28165454988650bcbdcc6b61ccea375899840197780574fe5",
        "fddd50e4992855dd5519b8562bce1daee0a2dfc31ab20181a23e11a7b5405666",
    ),
    "shard_0026": (
        "2e9faad307c29ca681eedcc0f64da2ab6ec00ef3893a280d1aead08b30d16836",
        "7750cfc08778c747122a2a2e82190a63c5e2f034d68f690748290c599b7c41be",
    ),
    "shard_0027": (
        "2e9faad307c29ca681eedcc0f64da2ab6ec00ef3893a280d1aead08b30d16836",
        "7750cfc08778c747122a2a2e82190a63c5e2f034d68f690748290c599b7c41be",
    ),
    "shard_0028": (
        "2e9faad307c29ca681eedcc0f64da2ab6ec00ef3893a280d1aead08b30d16836",
        "7750cfc08778c747122a2a2e82190a63c5e2f034d68f690748290c599b7c41be",
    ),
    "shard_0033": (
        "a15728a0c6e54de080e0fbfce2b49fbae9cfeedeaa2a76f281f584f369847886",
        "0a02b5c6737445748fcff41d88b2a44cacdfd1f394d80f0a341de47bd983e08b",
    ),
    "shard_0034": (
        "a15728a0c6e54de080e0fbfce2b49fbae9cfeedeaa2a76f281f584f369847886",
        "0a02b5c6737445748fcff41d88b2a44cacdfd1f394d80f0a341de47bd983e08b",
    ),
    "shard_0035": (
        "19129a69120e4f1cfd7dc6eae08d9a5ce4a20373fd9f48f584d8faf04801cb7d",
        "bd9bc74c3c417f04fbb16781f9c3fb33b07b78d193145dfeae953e7ac610a01f",
    ),
    "shard_0036": (
        "19129a69120e4f1cfd7dc6eae08d9a5ce4a20373fd9f48f584d8faf04801cb7d",
        "bd9bc74c3c417f04fbb16781f9c3fb33b07b78d193145dfeae953e7ac610a01f",
    ),
}


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def validate_groups() -> None:
    flat = [n for group in GROUPS for n in group]
    assert len(flat) == len(set(flat)) and not set(flat) & LOCAL
    assert set(flat) | {1} == {1, 2, 3, *range(8, 29), 33, 34, 35, 36}
    assert all(0 < len(group) <= 6 for group in GROUPS)


def slug(index: int) -> str:
    assert 0 <= index < len(GROUPS)
    return f"hung-matched-group{index + 2:02d}-44b8532-20261027"


def verify_predecessor(root: Path, shards: tuple[int, ...]) -> list[dict]:
    """Hash/CRC readback of a pinned predecessor version, before new training."""
    records = []
    for number in shards:
        name = f"shard_{number:04d}"
        matches = list(root.rglob(f"{name}/receipt.json"))
        assert len(matches) == 1, f"Missing/ambiguous predecessor {name}"
        receipt = json.loads(matches[0].read_text())
        archive = matches[0].with_name("artifacts.zip")
        assert receipt["shard_id"] == name
        assert receipt["exit_code"] == receipt["local_verify_exit_code"] == 0
        assert (receipt["plan_sha256"], receipt["shards_sha256"]) == EXPECTED_PROVIDER_PINS[name]
        jobset = json.dumps(sorted(receipt["job_ids"]), separators=(",", ":")).encode()
        assert hashlib.sha256(jobset).hexdigest() == EXPECTED_JOBSET_SHA[name]
        assert archive.stat().st_size == receipt["artifact_bytes"]
        assert digest(archive) == receipt["artifact_sha256"]
        with zipfile.ZipFile(archive) as contents:
            names = contents.namelist()
            assert len(names) == len(set(names))
            assert all(not n.startswith(("/", "\\")) and ".." not in n.split("/") for n in names)
            assert contents.testzip() is None
            identity = json.loads(contents.read("dispatch_identity.json"))
            assert identity["plan_sha256"] == receipt["plan_sha256"]
            measured = {
                n.split("/")[1]
                for n in names
                if n.startswith("jobs/") and n.endswith("/dispatch_measurement.json")
            }
            assert set(measured) == set(receipt["job_ids"])
            assert len(receipt["job_ids"]) == len(set(receipt["job_ids"])) == 20
        records.append(
            {
                "shard": name,
                "sha256": receipt["artifact_sha256"],
                "bytes": receipt["artifact_bytes"],
                "crc": "passed",
            }
        )
    return records


def status(slug_name: str) -> str:
    from kagglehub.clients import build_kaggle_client
    from kagglesdk.kernels.types.kernels_api_service import ApiGetKernelSessionStatusRequest

    request = ApiGetKernelSessionStatusRequest()
    request.user_name, request.kernel_slug = OWNER, slug_name
    with build_kaggle_client() as client:
        response = client.kernels.kernels_api_client.get_kernel_session_status(request)
    value = response.status.name
    assert value in {
        "QUEUED",
        "RUNNING",
        "COMPLETE",
        "ERROR",
        "NEW_SCRIPT",
        "CANCEL_REQUESTED",
        "CANCEL_ACKNOWLEDGED",
    }, value
    return value


def submit(name: str, source: str, *, gpu: bool, predecessor: str | None = None) -> dict:
    """One submission attempt. Caller must hold the unique relay chain position."""
    from kagglehub.clients import build_kaggle_client
    from kagglesdk.kernels.types.kernels_api_service import ApiSaveKernelRequest

    claim(name + "-submit", {"source_sha256": hashlib.sha256(source.encode()).hexdigest()})
    request = ApiSaveKernelRequest()
    request.slug, request.new_title = f"{OWNER}/{name}", name
    request.text, request.language, request.kernel_type = source, "python", "script"
    request.is_private, request.enable_gpu, request.enable_internet = True, gpu, True
    request.session_timeout_seconds = 8 * 3600 if gpu else 5 * 3600
    request.dataset_data_sources = [PAYLOAD] if gpu or predecessor else []
    request.kernel_data_sources = [f"{OWNER}/{predecessor}/1"] if predecessor else []
    if gpu:
        request.machine_shape = "NvidiaTeslaT4"
    with build_kaggle_client() as client:
        response = client.kernels.kernels_api_client.save_kernel(request)
    assert not response.error and response.version_number == 1, "Unexpected version; stop"
    assert not response.invalid_dataset_sources and not response.invalid_kernel_sources
    record = {
        "name": name,
        "url": response.url,
        "version": response.version_number,
        "gpu": gpu,
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
    }
    print(json.dumps({"submitted": record}), flush=True)
    return record


def claim(name: str, record: dict) -> None:
    """Create-only private Dataset claim; 409 never becomes a new version."""
    from kagglehub.clients import build_kaggle_client
    from kagglehub.gcs_upload import upload_files_and_directories
    from kagglesdk.blobs.types.blob_api_service import ApiBlobType
    from kagglesdk.datasets.types.dataset_api_service import ApiCreateDatasetRequest

    folder = Path("/kaggle/working/claims") / name
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "claim.json").open("x").write(
        json.dumps({**record, "allocation_sha256": ALLOCATION_SHA})
    )
    upload = upload_files_and_directories(
        str(folder), item_type=ApiBlobType.DATASET, ignore_patterns=[]
    ).to_proto()
    request = ApiCreateDatasetRequest()
    request.owner_slug, request.slug, request.title = OWNER, name, name
    request.files, request.directories, request.is_private = upload.files, upload.directories, True
    with build_kaggle_client() as client:
        result = client.datasets.dataset_api_client.create_dataset(request)
    assert not result.error, "Claim failed; no submission/training retry"


def module_prefix(module_source: str) -> str:
    compile(module_source, "hung_kaggle_queue.py", "exec")
    return module_source + "\nMODULE_SOURCE = " + repr(module_source) + "\n"


def gpu_source(module_source: str, setup: str, parity: str, index: int) -> str:
    assert 1 <= index < len(GROUPS)
    selected = [f"shard_{n:04d}" for n in GROUPS[index]]
    base_name = f"hung-matched-group{index + 2:02d}-v1"
    setup = setup.replace("hung-matched-group02-v1", base_name)
    setup = setup.replace('["shard_0002", "shard_0003"]', repr(selected))
    source = module_prefix(module_source)
    source += f"\nclaim({slug(index)!r}+'-execute', {{'group_index': {index}}})\n" + setup
    source += "\nreadback_started = time.perf_counter()\n"
    source += f"readback = verify_predecessor(Path('/kaggle/input'), {GROUPS[index - 1]!r})\n"
    source += "provider.save(base / 'predecessor-readback.json', {'records': readback, 'seconds': time.perf_counter()-readback_started})\n"
    source += "print(json.dumps({'predecessor_readback': readback}), flush=True)\n"
    source += "\n" + parity + "\nassert passed\n"
    source += f"selected = {selected!r}\nreceipts = []\ngroup_start = time.perf_counter()\n"
    source += """
for shard_id in selected:
    from kagglehub.clients import build_kaggle_client
    from kagglesdk.kernels.types.kernels_api_service import ApiGetAcceleratorQuotaStatisticsRequest
    with build_kaggle_client() as client:
        quota = client.kernels.kernels_api_client.get_accelerator_quota_statistics(
            ApiGetAcceleratorQuotaStatisticsRequest()).gpu_quota
    assert quota is not None and not quota.is_pay_to_scale_enabled
    assert all(v is not None for v in (quota.total_time_allowed, quota.time_used, quota.time_reserved))
    available = (quota.total_time_allowed-quota.time_used-quota.time_reserved).total_seconds()
    assert available >= 3600 + 20 * 1810.4 / 20 * 1.25, 'Fresh quota + reserve failed'
    assert shutil.disk_usage(base).free >= 8*1024**3, 'Disk reserve failed'
    assert time.perf_counter()-group_start < 6*3600, 'Bounded session limit'
    record = provider.execute_shard(repo, shard_id, base / shard_id)
    receipts.append(record)
    print(json.dumps(record), flush=True)
provider.save(base / 'group-complete.json', {'shards': selected, 'receipts': receipts,
    'allocation_queue_sha256': ALLOCATION_SHA, 'scope': 'Development only; peer acceptance pending'})
print(json.dumps({'group_complete': True, 'shards': selected}), flush=True)
"""
    compile(source, base_name, "exec")
    return source


def relay_source(
    module_source: str, setup: str, parity: str, index: int, ordinal: int, *, submit_current: bool
) -> str:
    assert 0 <= index < len(GROUPS) and ordinal < 12
    return (
        module_prefix(module_source)
        + "\nSETUP = "
        + repr(setup)
        + "\nPARITY = "
        + repr(parity)
        + f"\nrelay(MODULE_SOURCE, SETUP, PARITY, {index}, {ordinal}, "
        + f"submit_current={submit_current!r})\n"
    )


def relay(
    module_source: str, setup: str, parity: str, index: int, ordinal: int, *, submit_current: bool
) -> None:
    """CPU SDK relay: serial fixed GPU groups; 3h CPU relay bounds, no LLM polling."""
    validate_groups()
    claim(f"hung-development-relay-{ordinal:02d}-execute-20261027-v1", {"group_index": index})
    evidence = Path(f"/kaggle/working/relay-{ordinal:02d}")
    evidence.mkdir(exist_ok=False)
    started = time.monotonic()
    if submit_current:
        assert index > 0
        submit(
            slug(index),
            gpu_source(module_source, setup, parity, index),
            gpu=True,
            predecessor=slug(index - 1),
        )
    while True:
        state = status(slug(index))
        assert state not in {"ERROR", "CANCEL_REQUESTED", "CANCEL_ACKNOWLEDGED", "NEW_SCRIPT"}, (
            state
        )
        if state == "COMPLETE":
            (evidence / f"group-{index:02d}-terminal.json").open("x").write(
                json.dumps({"status": state, "version": 1, "name": slug(index)})
            )
            if index == len(GROUPS) - 1:
                # A separate CPU version mounts the last completed Output and checks bytes.
                proof = (
                    module_prefix(module_source)
                    + f"\nrecords=verify_predecessor(Path('/kaggle/input'), {GROUPS[index]!r})\n"
                    + "Path('/kaggle/working/final-development-readback.json').write_text(json.dumps({'records':records,'scope':'Development technical readback only; no Final evaluation'}))\n"
                    + "print(json.dumps({'passed':True,'records':records}),flush=True)\n"
                )
                submit(
                    "hung-development-last-readback-20261027-v1",
                    proof,
                    gpu=False,
                    predecessor=slug(index),
                )
                return
            index += 1
            submit(
                slug(index),
                gpu_source(module_source, setup, parity, index),
                gpu=True,
                predecessor=slug(index - 1),
            )
        if time.monotonic() - started >= 3 * 3600:
            assert ordinal + 1 < 12, "CPU relay count bound"
            name = f"hung-development-cpu-relay-{ordinal + 1:02d}-20261027-v1"
            submit(
                name,
                relay_source(
                    module_source, setup, parity, index, ordinal + 1, submit_current=False
                ),
                gpu=False,
            )
            (evidence / "handoff.json").open("x").write(json.dumps({"next": name, "index": index}))
            return
        time.sleep(60)
