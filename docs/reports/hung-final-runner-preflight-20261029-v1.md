# Hùng Final runner preflight — 29 October 2026

**Status: executable code and synthetic fixtures only. No Hùng Final job has been launched, no Final label has been opened, and no immutable execution lock exists.** This handoff responds to the Hùng-specific lead exception recorded by Qyroven on [#23 comment 6476049006](https://github.com/HungLD9505/adaptive-retention-ev/issues/23#issuecomment-6476049006). That comment permits execution after an outcome-blind exact lock and technical gates; it is not scientific peer acceptance, a merge approval, or permission to tune from Final results. Block7, parity and CHARGED remain explicit limitations.

## Implemented route

`final_lock.py` authenticates a SHA-pinned `hung-final-lock-v1` with the exact code ancestor/clean source tree, Hùng-specific authorization, Report 1 decisions, input package, analysis file, Source checkpoints, sorted jobset and full per-job execution plan. Before any Final role file is read, it checks all pinned bytes/SHA. It then checks each input-run manifest and artifact hashes, exact Final entity identity and locked daily schedule without parsing labels. `final_coverage.py` compares job rows with the declared entity × budget × seed × variant matrix, the nine baseline and five ablation categories, and all seven required dataset/city scopes. Missing cells/categories/cities require a named shortfall and return `coverage_status: incomplete`; a selected jobset cannot be presented as complete E2E coverage by default. Final replay remains fixed at the 90-origin protocol; a different saved schedule fails before label access.

`final_dispatch.py` processes the **exact locked jobset**, one job or all jobs. It requires the lock's free-space reserve of at least **8 GiB**, a fresh or identically bound output root, a nonblocking OS lock, and create-only per-stage output, log and receipt files. A second invocation rehashes complete stages and skips only verified jobs; missing receipts, partial stages, unexpected files or changed bytes fail closed. It supports job-boundary continuation, not automatic recovery of a torn in-stage checkpoint. Its status distinguishes selected-job verification from overall matrix coverage.

The existing causal replay reader, Hùng controller CLI and single-baseline CLI now accept an explicit `final` role while keeping `development` as the default. Final manifests carry distinct schemas, scope, lock SHA and job ID; Final initialization checks its training prefix ends before deployment and uses one exact prefix pass. The single-policy forecast journal validates against the selected role. Source training is reused only through exact locked checkpoint hashes. No Development artifact is relabelled Final.

## Lock schema and execution command

The lock requires `schema=hung-final-lock-v1`, `scope=final_only`, `code_commit`, `authorization`, `report1_contract`, pinned `input`/`analysis`, sorted `source_checkpoints`, pinned `jobset` and `execution_plan`, explicit `coverage`, `resources`, `output_root`, `created_at_utc`, and `final_label_access_after_lock=true`. Each jobset row includes exact identity, budget, seed, method, variant and input/Source hashes. A newly generated Final Target checkpoint is `null` in the lock and receives its real SHA in the immutable stage receipt; the lock is never backfilled from outcomes. The execution plan pins every stage argument and is cross-checked against the jobset.

After a real lock has been reviewed, committed and hashed, the route is:

```powershell
python -m experiments.hung_sprint2.final_dispatch --lock <project-lock.json> --lock-sha256 <SHA256>
python -m experiments.hung_sprint2.final_dispatch --lock <project-lock.json> --lock-sha256 <SHA256> --run
python -m experiments.hung_sprint2.final_dispatch --lock <project-lock.json> --lock-sha256 <SHA256>
```

The first and last commands are readback/verification only. The middle command is **not yet authorized to run with a real input**: the exact Hùng lock/jobset, CHARGED Final input package and capacity/provider preflight are still missing. The local D drive was below the existing 8 GiB reserve at the latest measurement. Do not lower the reserve, omit a city/method/seed silently or count Qyroven's Final as Hùng's.

## Checks and limitations

Synthetic fixtures exercised Final-role isolation, a three-origin Hùng controller replay, a 90-origin Seasonal Naive dispatch, create-only receipt readback, changed-byte rejection and the storage gate. **Five new tests passed**. The affected pre-existing replay/CLI/single-baseline suites plus these tests passed **38/38**. Ruff check/format and `git diff --check` passed. A clean full-repository suite is left to the coordinator after integration because this worktree contains new uncommitted source files during development. These fixtures are integrity checks, not Final research evidence.

The current runner does not support reuse of a pre-existing Final Target checkpoint or automatic in-stage resume; both fail closed rather than altering the lock. A new reviewed lock/plan would be needed if those behaviors become necessary. Scientific choices, exact Final scope and provider resources must be recorded before the first real `--run`.
