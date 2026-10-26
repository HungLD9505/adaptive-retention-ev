# Hung Issue #22: first selection-adapter tranche

This branch extends Hung's own three-candidate Sprint 2 runner from PR #46 and
its documentation dependency PR #53. It has no dependency on Qyroven's model,
runner, checkpoints, or executed results. This is code and offline fixture
evidence only; no new Development or Final run has been executed.

## Implemented methods

`replay-development --selection-rule confidence` retains the existing adaptive
bootstrap rule. `online_best_lambda` selects the candidate with the lowest mean
normalized MAE over complete, arrived, paired days in the current block. The
choice applies to the next block only. `without_confidence` uses mean
active-minus-challenger improvement with the existing strict `delta` gate. Both
retain `min_complete_days`, the same three candidate forecasts, online updates,
checkpoint state, label schedule, missing-day accounting, audit branch, and
per-candidate costs. Ties keep the active level; equal challenger improvements
prefer the nearer level and then configured level order. Neither method reports
observed means as bootstrap lower bounds. Insufficient evidence records null
selection statistics and keeps the active level.

When `delta=0`, `without_confidence` and `online_best_lambda` have identical
decision rules and should share one identified run in the experiment matrix.
With positive delta they are distinct runs. This branch has no real-data run
to reuse yet. The CLI and checkpoint bind the selected rule; changing it during
resume is rejected. Historical confidence checkpoints default to their original
rule, but old runs retain their original code identity and are not relabeled.

These two methods intentionally run all three candidates, so their measured
candidate inference/update counts match Adaptive. This is the required fair
comparison budget for Online Best. The times can differ due to the selection
calculation. Do not treat this three-candidate implementation as the one-model
Fixed Retention baseline or claim the cost of a single candidate.

## Required matrix still missing from Hung's own implementation

Seasonal Naive exists separately in PR #45 and is not changed here. Still to
implement and execute: Target-only GRU, Frozen Source, one-candidate Full
Fine-tuning, one-candidate Fixed Retention, Source-error, Uncertainty and Drift
controllers; Parameter Retention and Without Source Initialization. The runner
already accepts configurable block lengths, but the 7/28-day variants still
need declared configurations and execution. The Fixed-lambda ablation can
alias an exactly matching Fixed Retention run after its implementation. The
current branch adds the Online Best
baseline and the Without Confidence ablation only at code/fixture scope.

No required matrix cell is silently treated as zero or successful. Missing,
unscored and undefined-scale outcomes remain null under the existing evaluator.
Development calibration of levels, delta, cohort, source duration and proxy
mappings, separate-city CHARGED execution, three comparison seeds, measured
full-matrix capacity, independent peer review, immutable Final lock, Final
evaluation and a complete research report remain open.

## Offline checks

The new fixtures cover observed-mean selection, tie/keep, strict delta,
insufficient valid days with null statistics, equal three-candidate step/count
accounting, checkpoint restore and CLI policy binding. A two-block synthetic
fixture for each new policy forces a switch, verifies the next-block issued
forecast and separate old-policy audit, then compares uninterrupted execution
with a checkpoint saved after issuance and resumed before label arrival. It
compares forecasts, decisions, events, update counts, active model/optimizer
state and audit scores. The synthetic branch separation is an explicit fixture
for state-flow coverage, not training-effectiveness or fair-start evidence.
No dataset download, real training run, or Final access is performed by the fixtures.
