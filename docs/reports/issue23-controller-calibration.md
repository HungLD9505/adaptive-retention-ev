# Bounded Adaptive Controller Development calibration

Issue #23, independent Qyroven implementation, PR #52. Pre-execution declaration:
this is a finite joint recipe search on the existing identified UrbanEV Development
cohort, not a new plan, a convergence claim or a Final configuration lock.

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

256 fixture tests passed locally, with Ruff lint/format and diff checks. Real-data
controller calibration has not yet run at this declaration commit. It requires
Colab/Kaggle CUDA; no laptop real-data training. This four-configuration controller
budget does not silently grant additional searches to proxy comparators: proxy
mapping and parameter-retention grids need their own explicit comparable finite
budgets and actual Development evidence. Full matched baseline/ablation runs,
CHARGED validation, cost feasibility and independent Final lock remain pending.
