# Hùng Final partial checkpoint preflight — 29 October 2026

**Status: synthetic fixture only; no real Final job or provider session.** The existing Final dispatcher can resume verified local stages, but its output tree has no portable partial archive for a Kaggle session handoff. `experiments/hung_sprint2/final_partial_archive.py` adds that bounded checkpoint route without changing dispatcher or runner files.

The create-only checkpoint package contains `checkpoint.json` and `completed-stages.zip`. It binds the immutable **full** lock SHA, full jobset SHA/count, full execution-plan SHA, and a sorted proper subset of completed job IDs. The ZIP uses the local archive verifier's exact stage tree, job → artifact map, per-file bytes/SHA/CRC, completed manifests, logs and stage receipts. Drift jobs require their separate `drift_reference` stage. Unknown IDs, incomplete initialization/replay/Drift stages, extra jobs/stages, mismatched receipts and changed archive bytes fail closed. Its status is always `PARTIAL_CHECKPOINT_ONLY_NOT_FINAL_RESULT` or `PARTIAL_CHECKPOINT_VERIFIED_NOT_FINAL_RESULT`; it never reports coverage or Final evaluation completion.

Restore independently reopens the checkpoint ZIP against the full lock and selected subset, then creates files only at the **absent** output root named in that lock. Existing output is preserved and rejected. After extraction it re-inventories every restored byte before the standard dispatcher may verify stages and resume missing jobs. An interrupted restore leaves visible partial files for inspection; it does not overwrite or silently merge into an old run. This is local handoff preparation, not remote durability: a separate private upload and independent provider mount/download readback still need to be executed and recorded.

Synthetic tests cover two of three jobs, the Drift reference stage, exact restore, rejection of existing destination, unknown/full IDs, partial/extra stage trees, changed full lock pins, changed ZIP bytes, extra package member, and a forged complete status. No Final values, GPU, provider API or OAuth were accessed.

Checks from repository root:

```powershell
python -m unittest tests.test_hung_final_partial_archive -q
.cache/local-tools/bin/ruff.exe check experiments/hung_sprint2/final_partial_archive.py tests/test_hung_final_partial_archive.py tests/test_hung_final_archive.py
.cache/local-tools/bin/ruff.exe format --check experiments/hung_sprint2/final_partial_archive.py tests/test_hung_final_partial_archive.py tests/test_hung_final_archive.py
python -m py_compile experiments/hung_sprint2/final_partial_archive.py tests/test_hung_final_partial_archive.py
git diff --check
```
