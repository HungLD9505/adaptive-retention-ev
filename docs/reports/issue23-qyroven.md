# Issue #23 — evaluation helpers and independent verification (partial)

Executed 2026-10-26. This is a partial technical handoff, not completion of #23.
No Final access, tuning, configuration lock, research-effectiveness claim or merge.

## Implemented and tested

- `ev_evaluation/metrics.py`: complete24-hour original-unit errors; MAE and RMSE;
  exact paired-origin gates; station-first aggregation over at least three declared
  paired seeds; explicit zero Target-only MAE handling and NTR denominator.
- `tools/verify_comparison.py`: stdlib, read-only artifact verification independent
  of the model/runner score implementation. It authenticates input/daily files,
  checks chronology and recomputes every candidate/deployed original-unit score
  against the identified Development target's labels with availability checks.
- [Evaluation contract](../data/EVALUATION_CONTRACT.md): proposed units, pairing,
  honest missing-cell handling, absent uncertainty intervals and capacity warning.

205 independent fixture tests passed locally; Ruff lint/format and diff checks
passed. CI for code head `8b7acf55c8f80d19b0b7783b9f96ddaeeca28a28` passed both
Ubuntu/Windows in run40216623673. Subsequent changes integrate #22 evidence/docs
and this report; latest-head CI is required separately.

The verifier actually executed in Colab with file SHA-256
`23aa9b8b9c0b66774868061ce6b3d848d562ad199e957d52e0fa2d5219817ced`.
It verified42 UrbanEV and252 CHARGED cells:39,690 daily files and all corresponding
candidate/deployed MAE/MSE/aggregate RMSE/counts/commit chains. No model was retrained
or predictions replaced during verification. The exact models/runs/configs are
identified in the [comparison handoff](issue22-qyroven.md); all artifacts and
verification outputs are in its [catalog](issue22-artifacts.json).

A fixed three-method UrbanEV spot-check was downloaded back, checksum/CRC checked,
reverified against local inputs and its final checkpoints loaded safely on CPU.
Separate Colab checks hash-verified and CPU-reloaded all21 Source checkpoints with
namespace/seed/architecture/64-dimensional latent-scale validation. These are
integrity checks, not evidence of scientific superiority or upstream causality.

## Remaining work and approval boundaries

The actual comparison smoke has one target per namespace and main seed42 only.
Source ensemble seeds42/43/44 are not three comparison replications. Official
Development cohorts, comparable finite tuning grids/budgets, Source convergence
choices, proxy calibration, three or more comparison seeds, time/station-dependent
uncertainty and context/switch analyses remain unfinished. The aggregate helper
refuses missing seed cells and supplies no invented population confidence interval.

An exact feasible full experiment matrix and artifact-retention policy are still
required. Dense daily-state storage extrapolates poorly; the measured warning in
the contract does not authorize dropping mandatory budgets/methods/seeds or silently
changing the cohort. After Development decisions, record immutable code/config/
data/cohort/checkpoint identities and obtain independent lock approval before any
Final evaluation. This PR neither grants that approval nor exposes a Final runner.

The branch starts from dev and locally integrates the author's pending #47/#49/#50/
#51 with normal Git merges. Refresh against reviewed/integrated dev before merge;
no GitHub PR merge was performed. All work is independently implemented, without
copying Hung's model/controller/runner code.
