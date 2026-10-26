# Hung #23: finite Development proxy calibration tranche

**Status:** code and fixtures prepared. No full real-data calibration, method
ranking, Final evaluation, or immutable configuration lock is claimed.

Report 1 §7–8 requires Development-only design selection, at least three seeds,
comparable proxy tuning budgets, station-first metrics, and a separate Final
lock. Issue #23 adds exact input/cohort/code/checkpoint identities, null cells,
7/14/28-day budgets and complete cost accounting. This tranche implements those
selection gates for Hung's #59 proxy runner. It does not use Qyroven's run rows
or scores as Hung evidence. The four-recipe structure follows Qyroven's
**pre-execution** finite-grid declaration; Hung's uncertainty estimator is
within-horizon Source dispersion, not Qyroven's Source ensemble, so its numeric
thresholds still need empirical Development checks.

## Declared finite grid

`configs/hung-proxy-calibration-v1.json` fixes seeds 7/11/19; 7/14/28-day
budgets; 90 scheduled origins; common three candidates 0/0.1/0.2 and the
recorded diagnostic block/update settings. Each proxy receives exactly four
recipes: threshold pair A or B crossed with ascending or descending λ-bin
mapping. These are bounded candidate settings, **not calibrated values**. The
same candidate forecast/update schedule and `min_complete_days` rule apply to
all recipes. Source-error, uncertainty and drift each incur one additional
frozen-Source inference per created origin; the calibration verifier requires
equal counts and reports the proxy cost separately. Inference timing does not
include all Python, I/O or upstream training costs, so equal recipe count is
not an equal-compute claim.

The drift reference is fixed per target/budget from the **first created
Development forecast's already available 24-hour X history**: mean and
population standard deviation of load values with presence mask 1, with a
predeclared 0.1 normalized-unit scale floor. The reference origin, mean and
scale are pinned in the plan. A missing first available history blocks the
cell rather than substituting a later label or zero. This is a proposed causal
reference, not a validated drift detector.

## Reproducible sequence

1. Provide a JSON cell list (`hung-proxy-cells-v1`) containing one explicitly
   identified Development entity per budget/seed, with its input/source-run
   manifest SHA-256 and Source/target checkpoint paths. Use **separate plans**
   for each dataset, city and initialization stratum. All 7/14/28 budgets and
   all three seeds must be present for every included entity/budget.
2. On a clean commit, put the cell list in the worktree's Git-ignored
   `.cache/` directory (or track it if it contains no sensitive paths), then
   create a plan with
   `python -m tools.hung_proxy_calibration plan --profile configs/hung-proxy-calibration-v1.json --cells .cache/CELLS.json --output .cache/NEW_PLAN.json`.
   The plan pins profile/cell/code/driver hashes, checkpoint bytes, Development
   role, first-history drift references and cohort identities.
3. Record the plan SHA-256 and execute
   `python -m tools.hung_proxy_calibration run --plan .cache/NEW_PLAN.json --plan-sha256 SHA --output .cache/NEW_RUN_DIR`.
   The directory must be new and Git-ignored inside this worktree. Each completed replay
   appends a fsynced `runs.jsonl` row. A failure leaves all completed and
   partial artifacts untouched; there is no automatic favorable rerun or
   matrix-level resume in this tranche.
4. Only after every declared cell completes, run
   `python -m tools.hung_proxy_calibration select --plan .cache/NEW_PLAN.json --plan-sha256 SHA --runs .cache/NEW_RUN_DIR/runs.jsonl --output .cache/NEW_SELECTION.json`.
   The selector verifies every manifest/checkpoint SHA and bound configuration,
   then re-executes each full Development chronology from its pinned Source and
   target checkpoints plus manifest-hashed input. It requires the issued
   forecasts, arrived labels, candidate/optimizer/RNG states, decisions, event
   sequence, integer inference/update counts and authenticated event journal
   to match before recomputing original-unit
   MAE/RMSE. This verification roughly doubles replay computation; an
   unrepeatable CUDA result blocks selection rather than being silently used.
   Nanosecond timings and process peak RSS remain measured self-reports; they
   cannot be expected to repeat exactly and are not independent timing proofs.
   Selection requires identical scored origins, coverage, candidate update budgets and
   proxy inference counts across recipes, then averages seeds within station,
   stations within budget and the three budget means equally. Exact ties use
   recipe index. All-null groups stay null; a missing recipe or partially null
   seed group blocks selection. Each recipe reports summed inference/update
   counts and timed calls for all three candidates, the audit and the extra
   Source proxy, plus total process duration and available peak-RSS coverage.
   This is conditional Development selection, not
   a held-out effect estimate or Final lock.

## Evidence and remaining work

Fixture tests exercise finite-grid validation, Development/Final isolation,
masked first-history drift reference, null handling, tie order, pairing
rejection, ignored-output preflight, authentic selection on CPU and CUDA, and
forged checkpoint/manifest pairs with altered forecasts, arrived labels, RNG
or cost counts plus a rewritten journal/hash. The CUDA fixture runs only when
CUDA is available. Local
Source/target checkpoints exist for earlier diagnostic runs, but their target
checkpoint payloads predate the `initial_retention_weight` binding. Calibration
execution and selection reject those legacy targets even if a manifest claims
λ=0.1; use newly trained, verified target checkpoints. No complete reviewed
matrix for this calibration profile was established in this tranche, so no real
Development selection was run. A complete
cohort, all run outputs, independent review, measured feasibility, mandatory
baselines/ablations and the approved immutable lock remain required before
Final. Published Qyroven Development scores cannot fill Hung cells.
