# Hùng Final local archive preflight — 29 October 2026

**Status: implementation and synthetic fixture verified; no real Final run or archive.**

`experiments/hung_sprint2/final_archive.py` creates one ZIP after the lock-bound Final output tree contains exactly the declared jobs and required stages. It rejects missing/extra jobs or stages, partial receipts, changed stage bytes, incorrect completed manifests, and lock identity mismatches. Publication is create-only: a temporary archive is checked independently, then linked to a new destination without replacing prior output. The ZIP contains a job → stage → artifact index with byte length, SHA-256 and CRC32 for every file. `readback_archive` reopens the ZIP without reading the original stage tree, checks the outer archive SHA, exact member set, ZIP CRC, file SHA/CRC/bytes, log/receipt binding, and complete jobset.

The fixture exercises three jobs (controller with Target initialization, Drift with its separately receipted `drift_reference` stage, and single-stage Seasonal Naive), nested artifacts, missing receipt, missing Drift reference, extra job, mutated stage artifact, create-only protection, wrong expected jobset, changed outer archive, and a changed inner member with a newly computed outer SHA. Five focused tests passed. This is a technical local durability preflight only. Fixture bytes are not research results or evidence of Final evaluation.

## Remaining execution and durability gaps

- No Hùng Final lock/jobset has been accepted or executed. The first-three-ID candidate remains non-executable and records 27 unresolved Drift reference pairs, 370 UrbanEV IDs outside its bounded option, and absent CHARGED scope.
- No real Final stage output exists to archive. The module does not submit jobs or read Final labels.
- A local ZIP and local independent readback do **not** establish remote durability. A separate create-only upload and independent remote download/mount with exact archive byte/SHA/CRC readback, provider version/URL and receipt are still required before claiming Final artifact acceptance.
- Provider quota and output storage reserve remain unconfirmed; local D free space was below the 8 GiB dispatch reserve at the preceding preflight.

## Checks

From repository root:

```powershell
python -m unittest tests.test_hung_final_archive -q
.cache/local-tools/bin/ruff.exe check experiments/hung_sprint2/final_archive.py tests/test_hung_final_archive.py
.cache/local-tools/bin/ruff.exe format --check experiments/hung_sprint2/final_archive.py tests/test_hung_final_archive.py
python -m py_compile experiments/hung_sprint2/final_archive.py tests/test_hung_final_archive.py
git diff --check
```

All listed checks passed on the synthetic fixture. No remote provider operation or real Final execution was run.
