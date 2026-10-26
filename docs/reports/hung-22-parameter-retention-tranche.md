# Hung Issue #22: Parameter Retention and block-size sensitivity readiness

This code tranche stacks on draft PR #59 (`4453944`) and has no real-data
Development or Final execution. It is an implementation and fixture handoff,
not an effectiveness result or an accepted method configuration.

## Parameter Retention definition

`--retention-kind parameter` replaces only the positive-lambda latent loss with
the mean squared displacement of **all transferred GRU, calendar MLP, and
forecast-head weights and biases** from the exact frozen Source checkpoint:

`L = MAE_24 + lambda * (sum_p ||theta_target,p - theta_source,p||_2^2 / sum_p numel(p))`.

The zero-lambda candidate still uses forecast MAE alone. The reference model is
frozen; no Source gradient or target label enters it. This is a declared
parameter-regularization ablation, not the Report 1 main latent loss. Its
numeric lambda scale need not match latent retention's strength and must be
chosen with a finite Development-only budget before comparison or Final lock.

The separate target initialization uses the same chosen loss and initial
lambda, with the same permitted prefix and step budget as the latent run. Its
checkpoint payload and run manifest bind `initial_retention_kind` and lambda.
Replay checks both fields against the requested kind/initial level before
output creation. The bound Source checkpoint SHA remains in the target input
binding and identifies the parameter anchor. Runner snapshots and run manifests
bind the loss kind across resume; an altered kind is rejected. Three candidates
still fork the same active model/optimizer state, use the same daily forecast
and complete-label update schedule, and share paired RNG. Candidate update
timers include the parameter penalty computation; the existing state-memory
record still includes the loaded latent-scale tensor although this ablation
does not use that tensor in its loss.

## Different Block Size

The existing `--block-days` controller input is the declarative sensitivity
parameter. The 7- and 28-day variants change only this value from the main
14-day setting; lambda levels, model, origin/label rules, selection algorithm,
candidate count and update budgets remain unchanged. Offline 7/28 fixtures
cross a decision boundary and verify split/resume parity with uninterrupted
replay, including candidate models, optimizers, issued forecasts and events.
The two versioned proposal files are `development_block7_proposal_v1.json` and
`development_block28_proposal_v1.json`; tests compare them against the 14-day
base config and require no other method-setting difference.
The Development matrix orchestrator now derives its verification split from
`block_days`: 21/42/84 origins for 7/14/28-day blocks at a 90-origin horizon.
It requires two block boundaries and the next origin, and checks target/replay
retention kind plus initial parameter lambda before execution. The existing
14-day config still splits at 42. These are code-path checks only; no 7/28
real-data runs are claimed.

## Remaining evidence

No raw archives, real Development inputs, GPU training, CHARGED cells or Final
labels were opened by this tranche. Parameter lambda calibration, measured
fairness/cost on shared real entities and seeds, full UrbanEV/CHARGED matrix,
independent review, immutable lock, Final execution and the complete report
remain open. The sibling Seasonal Naive branch must be reconciled into one
reviewed integration path before merging either stacked PR.
