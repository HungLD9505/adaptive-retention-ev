# Hùng Final runtime preflight — 28 October 2026

**Status: preflight audit only.** This document does not lock a Final configuration, authorize Final access, or report a Final execution. It updates the runtime and capacity facts beside the earlier [lock review candidate](hung-final-lock-review-candidate-20261028.md); it does not replace that candidate or the reviewer gate.

## Evidence snapshot

The [Development gate register v15](hung-e2e-gate-register-20261028-v15.md) records 782/782 technically verified job proofs and 560/560 Kaggle CPU metric exports. Those are Development technical milestones. Its scientific acceptance and Hùng Final gates remain open, including Block7 comparability, implementation parity, and CHARGED scope. The earlier lock candidate still describes 222/782 as its historical snapshot; use v15 for the current technical proof count.

The Hùng CLI in `experiments/hung_sprint2/cli.py` exposes `source-smoke`, `target-smoke`, `verify-input-zip`, and `replay-development`; its replay result explicitly declares `fixture/Development evidence only; no Final evaluation` (lines 813, 859–862, 940). `experiments/hung_sprint2/run_development.py` invokes only those Development operations. `experiments/hung_sprint2/dispatch_matched.py` requires a plan with `scope == "development_only"` (line 168) and states that it never reads Final inputs. No Hùng Final runner, Final dispatch plan or immutable Final lock was identified in the inspected `experiments/hung_sprint2` and `tools` trees. The Development safeguards must not be relabeled or bypassed to start Final.

## Exact identities and decisions still needed

| Gate | Required record before Final access |
| --- | --- |
| Scientific decision | Independent disposition for the 69 historical Block7 runs versus replay, Hùng/Qyroven head and bootstrap/controller event parity, and whether any CHARGED cities belong to Hùng's Final matrix. Decisions must use correctness and Development evidence, not Final metrics. |
| Method and artifacts | Exact commit and runner trace contract; immutable config bytes and SHA-256, model/hyperparameters/thresholds, Source and Target checkpoint manifests and hashes, and environment identity. Development reference hashes in the earlier candidate are not automatically Final selections. |
| Outcome-blind evaluation | Hùng-specific entity IDs and eligibility rules; dataset/input/scaler manifests and hashes; seed list, replay origins/windows, label arrival rules, variants and budgets; overlap and exclusion rules. Qyroven's Final cohort and runs do not fill these fields. |
| Analysis | Frozen MAE/RMSE and paired comparison denominators, uncertainty grouping, NTR, switch/audit and compute-cost definitions, plus explicit handling of missing or zero-scored cells. |
| Execution | Final-capable code and a create-only, one-run dispatch/jobset; explicit output identity, checkpoint/resume behavior, receipt schema and independent archive-byte/SHA/CRC readback. Validate on fixtures before opening Final. |
| Approval | A Hùng-specific, non-author decision citing the exact immutable lock identity under [#15](https://github.com/HungLD9505/adaptive-retention-ev/issues/15). The one-time exception in [#23](https://github.com/HungLD9505/adaptive-retention-ev/issues/23) applies to Qyroven's bounded Final only. A new code/config/cohort/analysis version needs a new lock and review. |

## Local capacity snapshot

On this host, `nvidia-smi` reported an NVIDIA GeForce RTX 3050 Ti Laptop GPU with **4096 MiB total** and **3962 MiB free** (driver 592.82). `Get-PSDrive D` reported **4,002,996,224 free bytes** (about 3.73 GiB). The existing Development dispatch requires at least **8 GiB free at its output location** (`dispatch_matched.py`, lines 39 and 101). This is a point-in-time local measurement, not a Final runtime or provider quota estimate. D cannot pass that existing storage reserve at this snapshot; capacity must be measured again after an exact Hùng Final plan and provider/output location are fixed.

## Next executable sequence

1. Complete the Development scientific analysis and obtain recorded independent decisions for Block7, implementation parity and CHARGED.
2. Freeze the exact Hùng Final identities above in a versioned, hash-addressed, create-only lock. Obtain a non-author review of that specific lock before accessing Final labels or metrics.
3. Implement a distinct Final-capable runner and create-only dispatch from the approved contract; verify its lock checks, output preservation, resume path and independent SHA/CRC readback with non-Final fixtures.
4. Measure the selected CPU/GPU provider, runtime and storage budget. Run the single locked Hùng Final allocation, preserve checkpoints, and read back every saved artifact before writing the E2E report.

**Audit commands:** `rg -n "development_only|MIN_FREE_BYTES|Final inputs|bounded_development_replay|replay-development|source-smoke|target-smoke" experiments/hung_sprint2/cli.py experiments/hung_sprint2/dispatch_matched.py experiments/hung_sprint2/run_development.py`; `rg --files experiments/hung_sprint2 tools | rg -i 'final|lock'`; `nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version --format=csv,noheader`; `Get-PSDrive D`. Source and reports were read only; no Final/test data was opened.
