# Full historical-cohort controller follow-up — 10 November 2026

## Scope and authorization

The owner explicitly requested: “thế chạy thử cả như đợt trc đi xem có thắng dc k”.
This authorizes a separate experiment on the historical report's full cohort:
seven namespaces, 90 distinct entity IDs, three initial-history budgets (7/14/28
days), seeds 42/43/44, and 90 scheduled replay days: **810 units / 21 aggregates**.
Historical Final outcomes were already exposed. This is not an untouched test set,
a replacement for frozen Final, or a claim of independent peer approval. No merge
is authorized. This follow-up relates to #99 and depends on #110.

The ordinary Development input boundary and original frozen Final authorization
code remain unchanged. A separate tracked owner-request lock binds the historical
cohort, input/source hashes, algorithm sources, old collection/summary fingerprints
and frozen new-method parameters. A scope-specific input reader uses this explicit
follow-up lock; it cannot silently open other targets or train new Sources.

## Methods fixed before replay

- `old_fixed`: authenticated reuse of the report's Fixed lambda=1 GRU forecasts.
- `old_adaptive`: authenticated reuse of the report's original 14-day confidence
  controller, including its actual issued candidate choices.
- `mean7`: same original three constant-retention expert trajectories (0/0.1/1),
  selecting the lowest preceding seven-day mean, initially lambda=0.1.
- `confidence7`: same bank, challenger and seven-day cadence as `mean7`; a paired
  bootstrap confidence gate permits a switch. Minimum five valid days, segment
  length three, 2,000 resamples, alpha 0.05, delta=0, paired seed. This is the
  previous Development ablation, not a newly tuned historical-cohort method.
- `fast_only`: new Source10 GRU adaptation, lambda=0, three initial prefix epochs,
  Adam 0.001, one online epoch on the last seven calendar days of already arrived
  complete examples. Each online window fits one optimizer step.
- `static_mix`: blend `old_fixed` and `fast_only` with stable weight
  0.4307815378871372, previously chosen on four UrbanEV Development stations.
- `fixed_share`: same expert pair, initial weight and losses; the previously
  selected eta=0.1/share=0.1 update. This controls forecast weights, not lambda.

No new calibration or candidate selection uses this historical cohort. The same
14-day Development selection is deliberately carried into all cities and all
history budgets. This tests a fixed recipe's transfer, not per-city optimality.
The original report's source/initial/online training profiles are unchanged.

The forecast-fusion equation and two-expert share-to-other update follow the
[preceding method handoff](../issue99-stable-fast-20261110/handoff.md), with attribution
to [Herbster and Warmuth (1998)](https://mwarmuth.bitbucket.io/pubs/J39.pdf).
New fast experts run on local CPU (one Torch thread per worker); historical
experts retain their original GPU provenance. Runtime/numeric differences are
explicit, and tiny differences must not be called substantive improvement.

## Data, chronology and aggregation

Use the original 21 prepared input manifests and 21 Source checkpoints. No raw
archive is overwritten or freshly downloaded; current publisher archive checks
are not claimed. Input files are authenticated before use and rehashed after
each dataset/history group. Only selected target prefixes and forecast inputs
are decoded; target labels enter scoring/training only after complete arrival.
Missing labels are never filled. Preserve UrbanEV ID2193 as unscored/null across
its nine budget/seed units. Do not drop the entity from the selected cohort.

Old prediction files are checked against score-event hashes, and their errors
are recomputed from labels available at the recorded score time. New fast runs
save forecasts before their future labels enter training. Mixture weights use
only losses available at the current origin. The rolling window contains only
the initial permitted prefix and already arrived complete days.

Every method shares an identical score mask within each unit. Average seeds
within each station, then average scored stations within each namespace/history
group, matching the old report's station-first MAE. Null stations stay null.
Old Fixed and Adaptive group aggregates must reproduce the historical summary
within numerical tolerance. Never pool cities to declare a global accuracy gain.
A count of lower group means is descriptive, not a significance test.

## Execution records

First lock: [execution-lock.json](execution-lock.json), code `a6f23be`.
The first dispatch stopped on a real adapter error: it passed the prediction-file
hash three times where the confidence validator requires distinct candidate
prediction IDs. No failing run was treated as a completed study. Model training
itself did not depend on those IDs. The adapter now preserves the actual candidate
IDs from each authenticated historical forecast. Regression coverage checks
identity preservation and rejects changed forecast bytes/unavailable labels.

Second lock: [execution-lock-v2.json](execution-lock-v2.json). It preserves the
original lock and authorizes reuse only of completed fast runs whose source,
input, actual training configuration and prior lock match. Reused predictions
are reauthenticated. Remaining experts are newly trained; old output directories
are not overwritten. Reuse paths and report hashes are recorded per cell.

Execution roots outside Git:

- `runs/issue99-full-scope-20261110-v1`: incomplete first dispatch, preserved.
- `runs/issue99-full-scope-20261110-v2`: corrected complete-scope dispatch.

Both live under `/Users/quyenmanh/Developer/TFL-EV`. Model checkpoints and large
cell artifacts remain outside Git. Fresh-run execution only; rolling-memory
resume is unsupported. The second dispatcher uses two CPU processes, each with
one Torch thread. No provider GPU session or compute purchase is started.

## Verification and reproduction

```
python -m tools.issue99_full_scope --base ORIGINAL_CHECKOUT \
  --lock docs/reports/issue99-full-scope-20261110/execution-lock-v2.json \
  --output NEW_RUN --jobs 2
python -m tools.issue99_full_scope_readback --base ORIGINAL_CHECKOUT \
  --lock docs/reports/issue99-full-scope-20261110/execution-lock-v2.json \
  --run NEW_RUN --output NEW_READBACK
```

Readback independently reconstructs exponential mixture weights and forecast
MAEs, checks effective online retention choices, authenticates both historical
forecast banks, reconstructs every rolling-window update, verifies retained
model/Adam/RNG state digests and finite tensors, rehashes inputs and rebuilds all
21 station-first aggregates. Counts, final measured results and code checks are
appended only after execution completes.
