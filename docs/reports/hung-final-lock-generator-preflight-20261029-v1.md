# Hùng Final lock generator preflight — 29 October 2026

**Status: generator and synthetic checks prepared; no real executable Final lock created.** `tools/hung_final_lock_preflight.py` converts the frozen 360-job UrbanEV first-three-ID candidate, its execution plan, analysis specification, nine Source candidates and UrbanEV input ZIP into a create-only `hung-final-lock-v1` packet under ignored repository `.cache`. It does not read Final role rows, labels, forecasts, schedules or outcomes. It pins the Hùng-specific #23 comment 6476049006 as a lead pre-execution exception, not peer approval, and keeps the 370-ID UrbanEV and six-city CHARGED shortfalls explicit.

The generator refuses absent, stale (>20 minutes), future or insufficient Kaggle quota/storage evidence. The provider attestation must show free-tier GPU time at least the locked estimate plus one hour, and provider storage at least the locked output estimate **plus 8 GiB**. A separately supplied trusted authenticated-evidence verifier callback must approve the evidence; a JSON `authentication_method` claim alone cannot pass. The code does not contain a production verifier callback yet, because Kaggle authentication/quota inspection was not available in this milestone. Offline consistency and freshness checks cannot cryptographically prove that a supplied response came from Kaggle; an operator/reviewer must verify its saved authenticated API provenance. Synthetic tests use an explicitly fake callback and leave no permanent lock.

The locked estimate cannot undercut the hash-pinned Development scenario (360 jobs; 3.808 observed-p95 stage hours and 12,165,321,218 bytes after the 1.5 storage multiplier). Local builder storage is checked only for the small copied lock packet; the **Kaggle runtime** must recheck the full 8 GiB reserve plus estimated output bytes before dispatch. The generated input, Source, jobset, plan and analysis references, and output root are canonical **repo-relative paths**, so a hash-identical checkout on another host can resolve them. Only ignored `.cache` overlay paths are used, matching the separate Kaggle source-bundle builder. The generator checks a clean executed code commit, all candidate/code/config pins, nine checkpoint and adjacent Source manifest hashes, input manifest set, no missing selected-matrix cells, named #15 shortfalls and all 27 Drift plan constants left null under the pinned post-lock derivation rule. It invokes `validate_lock(..., verify_input_runs=False)` on its newly created packet, so this preflight does not open Final role artifacts.

Synthetic checks reject stale/insufficient provider evidence, provider storage between estimate and estimate-plus-reserve, absent trusted verifier, understated resource estimate, insufficient local staging, changed candidate/code, missing shortfall and changed Drift plan. A passing fake fixture creates the lock once, confirms its schema and pins, then relocates all referenced files to a second checkout root and validates the same lock there without opening Final inputs. A second creation is rejected. The current real workspace still lacks an authenticated Kaggle attestation and a production verifier callback; no real lock was generated, no Kaggle API called and no Final job submitted.

Checks:

```powershell
python -m unittest tests.test_hung_final_lock_preflight -q
.cache/local-tools/bin/ruff.exe check tools/hung_final_lock_preflight.py tests/test_hung_final_lock_preflight.py
.cache/local-tools/bin/ruff.exe format --check tools/hung_final_lock_preflight.py tests/test_hung_final_lock_preflight.py
python -m py_compile tools/hung_final_lock_preflight.py tests/test_hung_final_lock_preflight.py
git diff --check
```
