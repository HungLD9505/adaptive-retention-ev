# Bounded Adaptive Controller Development calibration

Issue #23, independent Qyroven implementation, PR #52. Pre-execution declaration:
this is a finite joint recipe search on the existing identified UrbanEV Development
cohort, not a new plan, a convergence claim or a Final configuration lock.

**Current execution status:** all 276 original controller runs were recovered and
independently verified after Colab eviction. See the [recovery/results record](issue23-runtime-recovery.md)
for all four scores, original-artifact identities and the missing original loop
timer. Recipe1 is provisional; it does not beat selected Fixed Retention on this
cohort. The Colab queue/progress descriptions below are historical snapshots;
those workers are gone. Downstream proxy calibration now runs on Kaggle.

Reuse the verified Source-duration study and recompute its provisional choice
(currently 10 epochs). Authenticate all Source checkpoints, profile, cohort and
unchanged core algorithm hashes before starting. No Hùng implementation or weights
are used. Three paired seeds (42/43/44), 90 scheduled days, 7/14/28-day budgets and
all 23 predeclared entity-budget combinations give 276 runs. Retain null-score
cells, sparse-history and Source-checkpoint-only strata without outcome filtering.

| Recipe | Low / high lambda | Initial lambda | Bmin | Delta (normalized MAE) | Bootstrap segment |
|---|---|---|---:|---:|---:|
| 0 | 0.01 / 0.1 | 0.01 | 7 | 0 | 3 valid days |
| 1 | 0.1 / 1 | 0.1 | 7 | 0 | 3 valid days |
| 2 | 0.01 / 0.1 | 0.01 | 10 | 0.005 | 5 valid days |
| 3 | 0.1 / 1 | 0.1 | 10 | 0.005 | 5 valid days |

Each recipe includes lambda zero. The method, 14-day block, alpha 0.05, 2,000
bootstrap replicates, two-challenger correction, causal event order, candidate
fork/update budgets, architecture and training schedule remain unchanged. Initial
lambda is always the low positive level. These four joint recipes cover two
retention ranges and two evidence profiles; they cannot identify individual
hyperparameter effects. Alpha, resample count and initial-level alternatives are
not exhaustively searched. Neither the preceding Source-duration choice nor this
finite search establishes convergence, optimality or calibrated confidence coverage.
Grid endpoints and finite-search limitations must be reported with actual results.

Selection is equal seed average within station, station average within budget and
then equal average over all three budgets, in original-unit MAE. Exact ties prefer
recipe index 0, 1, 2, 3 in declared order. Require all candidate/seed/station cells,
paired issued/scored coverage, correct actual config-to-recipe bindings and complete
null accounting. No best-seed selection, retrospective forecast substitution or
Final input is permitted. Both non-scoring and scoring entities remain in reports.

`tools.controller_calibration` accepts identified profile/study SHA-256 values,
independent Source-study verification and a fresh CUDA output directory. It records
run/config/code/Source/input identities, full daily forecast/event commit chains,
latest model/optimizer/RNG state, logs, update and audit costs and reset per-run GPU
peaks. Source pretraining cost is reused and must be included once in total capacity
accounting. Startup/input validation and artifact verification/packaging/upload are
separate from the recorded replay-loop timer. Preserve failures and old outputs.
The batch does not yet orchestrate automatic partial-matrix resume; individual
runner checkpoints remain available for identified manual recovery.

Before acceptance, independently verify the complete output matrix, daily hashes,
original-unit scores, label availability and paired forecast/score origin sets;
download and check complete archived bytes and latest state contents. Actual run
results and artifact links will be appended only after verified execution.

## Execution status

At declaration, 256 fixture tests passed locally and on Colab, with Ruff lint/format
and diff checks. Actual T4 execution then started under commit
`0fa960b4e34059b87dc40ba67cce8a105d16da2e`. An observed progress snapshot has
26/276 completed replays; process still running, no completion/result claimed.
No laptop real-data training. Subsequent proxy additions bring the fixture suite
to 260 passing tests locally and on Colab. This four-configuration controller
budget does not silently grant additional searches to proxy comparators: proxy
mapping and parameter-retention grids need their own explicit comparable finite
budgets and actual Development evidence. Full matched baseline/ablation runs,
CHARGED validation, cost feasibility and independent Final lock remain pending.

## Active serial execution and persistence

The authorized Colab notebook is
[Qyroven Development execution](https://colab.research.google.com/drive/1h0AlP8b_0TLx_zV4Zx13U4ANq9ch0X-E).
The batch root is `/content/qyroven-i23-controller-calibration-20261026-v1`;
code lives in `/content/ev-issue23-controller-calibration`. Code bundle increment
SHA-256: `b112dd6841ba352e6b4c9872eff8a5c0e8e04071f0e4a0311a8e85d9686a3102`.
It depends on the already identified Fixed-study code history; the notebook clones
that checkout without changing it, fetches the increment and checks out the exact
controller code SHA. Core model/controller/runner hashes remain unchanged.

A notebook worker backs up each group of 12 completed runs to a new Drive ZIP,
read-checks bytes/hashes and records a snapshot manifest. The first two chunks
(total 24 runs) were observed copied/hash-checked. This is a checkpoint-loss
mitigation, not a guarantee against runtime termination or proof of cloud server
flush. The active backup folder remains in the owner's MyDrive while its mounted
path is being used; move it into the shared team folder only after execution and
flush, then verify team distribution. Do not claim peer access to active backups.

After successful controller subprocess completion, the serial worker independently
verifies all daily chains, forecasts, scores and declared label availability;
archives the run/config/source/code/log identities; and only then starts proxy/
parameter calibration. Failures stop the queue and persist the exact error and
traceback. It never starts simultaneous long GPU training, retries favorable
seeds or changes accounts. Remote fixture tests briefly overlap early controller
execution, and background backups add I/O cost; early timings are not isolated
benchmark measurements. Full independent downloaded-state verification remains
required after final export. No Final runner, merge or issue closure is authorized.
