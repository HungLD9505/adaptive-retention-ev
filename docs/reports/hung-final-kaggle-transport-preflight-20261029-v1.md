# Hùng Final Kaggle transport preflight — 29 October 2026

**Status: code and fake-provider fixture only. No Kaggle call, saved version, real Final archive or remote readback exists.**

`experiments/hung_sprint2/final_transport.py` prepares a new, create-only private Dataset payload from a previously verified local Final archive. It binds the exact Final lock, jobset, execution plan, archive and standalone `final_archive.py` verifier by byte length/SHA-256 in `final-transport-manifest.json`. The archive itself has already passed local whole-ZIP and per-job byte/SHA/CRC readback before packet creation. The generated `cpu_readback.py` is an immutable CPU-only saved-version source: it requires one mounted Dataset with the exact manifest hash, rehashes every mounted file, checks the lock's jobset/plan pins, and invokes `readback_archive` on the mounted ZIP. It emits `hung-final-remote-readback-v1` with dataset v1, intended readback kernel v1, lock/archive identities and exact job count. `cpu_kernel_spec` declares private CPU, no internet, and the exact Dataset `/1` source.

`upload_once` writes a create-only attempt record **before** calling the injected provider. An acknowledged create remains `CREATE_ACKNOWLEDGED_READBACK_PENDING`; HTTP499 remains `UNCERTAIN_HTTP499`. Both states reject a second upload attempt. The production adapter is `kaggle_create_private`, which calls the existing generic `tools.hung_kaggle_storage.upload_private` (`kagglehub.gcs_upload`, `ApiCreateDatasetRequest`, private Dataset create). No Development shard slug or receipt is reused. `verify_remote_receipt` checks a downloaded receipt against the local packet but cannot independently authenticate its claimed Kaggle version; that requires the saved notebook URL, version number, source list and actual output byte readback.

Fake-provider tests cover lock/archive/jobset/plan/code pinning, CPU saved-version source and dataset v1 request, one acknowledged upload, HTTP499 unknown outcome without retry, unchanged packet protection, and strict remote receipt fields. No OAuth or provider API was called. Normal Python in this workspace lacks `kagglehub` and `kagglesdk`; the repository-local Kaggle CLI environment has `kagglesdk` but lacks `kagglehub`. The repo-local `.cache/kaggle-auth/token` was absent during this read-only preflight. Account authentication, current quota, actual upload, CPU notebook submission, source-version inspection and separate mounted readback remain pending. Do not infer availability from earlier Development jobs.

Checks from repository root:

```powershell
python -m unittest tests.test_hung_final_archive tests.test_hung_final_transport -q
.cache/local-tools/bin/ruff.exe check experiments/hung_sprint2/final_archive.py experiments/hung_sprint2/final_transport.py tests/test_hung_final_archive.py tests/test_hung_final_transport.py
.cache/local-tools/bin/ruff.exe format --check experiments/hung_sprint2/final_archive.py experiments/hung_sprint2/final_transport.py tests/test_hung_final_archive.py tests/test_hung_final_transport.py
python -m py_compile experiments/hung_sprint2/final_archive.py experiments/hung_sprint2/final_transport.py tests/test_hung_final_archive.py tests/test_hung_final_transport.py
git diff --check
```
