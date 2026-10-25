# Source-duration Development study — pre-execution declaration

Declared 2026-10-26 before executing this grid. This extends Issue #23, not the
research method or the sole sprint schedule. Sprint 2 implementation and real
smoke evidence exist in #47/#49/#50, but peer acceptance/integration and the full
capacity gate are pending; Sprint 2 is not formally accepted.

The earlier Source checkpoints used one epoch. The finite grid now compares
checkpoints after **1, 3 and 10 Source epochs**, with paired seeds **42/43/44**.
For each seed, train one ten-epoch trajectory over the same permitted pre-deployment
Source pool; retain every epoch, optimizer/RNG and Source-derived latent scales.
No Source target selection, architecture, loss or data-contract change is introduced.
This is bounded duration assessment, not proof that ten epochs ensure convergence.

Use the previously identified Development cohort (6/8/9 IDs for budgets7/14/28,
90 scheduled days) including null and source-checkpoint-only strata. Compare
**Full Fine-tuning only** to assess a common transferable initialization without
selecting Source duration for a favorable confidence-controller result. Initial
target training remains three epochs and online updates one epoch, with the same
fixed optimizer and chronological complete-label gates. Nine candidate Source
checkpoints feed **207** target replays; these are not independent station samples.
The profile and cohort hashes are recorded before execution. Previous artifacts
remain immutable and cannot be mixed into the new study as if code/weights matched.

The provisional ranking averages seeds within station, stations within each budget,
then the three budget means equally, in original-unit MAE. All candidates must
have the same forecast/scoring counts per paired unit; null units remain listed.
An entirely unscored budget prevents ranking. Exact ties prefer fewer epochs.
The same small nonrandom/possibly colocated cohort and different budget populations
limit generalization. Source-only versus initial-adaptation membership stays in
per-run records; scores cannot be pooled without explicit stratum disclosure.

The best endpoint at epoch10 raises a grid-boundary warning; it does not trigger an
automatic grid extension. Training loss curves and Development results are both
reported, with no formal convergence guarantee or automatic Final configuration
promotion. This profile assesses Source duration only: learning rate, target/update
budgets, retention/confidence settings, parameter-retention scale and proxy mappings
remain distinct finite Development decisions, not silently tuned here.

`python -m tools.source_epoch_sweep` requires CUDA (Colab/Kaggle), authenticated input
and cohort/profile hashes, fresh outputs and the hardened role/entity reader. No
long local training or Final fitting/tuning/evaluation. Per-run CUDA peaks are reset
after shared prefix/replay preparation; Source/preparation/audit costs stay explicit.
Durable epoch checkpoints support interruption recovery; the matrix-level driver
does not yet offer resume orchestration. Preserve failed outputs rather than overwrite.

Actual counts, measured runtime, code SHA, logs, metrics and Drive links will be
appended only after execution. Independent review, full comparison/ablation
replication, proxy calibration and immutable Final lock remain required.

## Identified execution and reproduction

Training code: `ff42ea944bf05b4b77e2b730edf500b1fee6e851`.
Profile SHA-256: `1be79afd6543bf7140c66e23562277f54115c39e458409b27cc9eb768bcd896f`.
247 fixture tests passed locally and on Colab. Both CI platforms passed for that
code in [run40226991465](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/40226991465).
The Colab T4 run uses `qyroven-i23-source-duration-20261026-v1`; it is still running
at this update, not a completed study or selected official Source checkpoint.

On an authenticated checkout of that code and verified DATA-v1 input installation:

```sh
python -m tools.source_epoch_sweep \
  --inputs-root /content/ev-data/data/inputs/issue18-input-handoff-v1-20261019 \
  --profile configs/issue23/source-epoch-study.json \
  --profile-sha256 1be79afd6543bf7140c66e23562277f54115c39e458409b27cc9eb768bcd896f \
  --selection configs/issue23/readiness-cohort.json \
  --output /content/qyroven-i23-source-duration-reproduction
```

Use a fresh output directory. Run only on CUDA; the routine test suite uses fixtures.
The original notebook also queues immutable per-seed Source backups and full-run
verification/export to Drive. The CLI itself does not upload or grant permissions.
After successful execution, independently verify the generated matrix:

```sh
python -m tools.verify_comparison \
  --matrix /content/qyroven-i23-source-duration-reproduction/matrix.json \
  --inputs-root /content/ev-data/data/inputs/issue18-input-handoff-v1-20261019 \
  --output /content/qyroven-i23-source-duration-reproduction-verification.json
```
