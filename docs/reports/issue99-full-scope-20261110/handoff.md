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
- `mean7`: reuse the original three-candidate bank. All candidates share the
  original prefix adaptation at lambda=0.1; their online trajectories use
  lambda=0/0.1/1. Select the lowest preceding seven-day mean, initially lambda=0.1.
- `confidence7`: same bank, challenger and seven-day cadence as `mean7`; a paired
  bootstrap confidence gate permits a switch. Minimum five valid days, segment
  length three, 2,000 resamples, alpha 0.05, delta=0, paired seed. This is the
  previous Development ablation, not a newly tuned historical-cohort method.
- `fast_only`: new Source10 GRU adaptation, lambda=0, three initial prefix epochs when complete prefix examples exist,
  Adam 0.001, one online epoch on the last seven calendar days of already arrived
  complete examples, ending at the newly arrived forecast origin. Each online
  window fits one optimizer step.
- `static_mix`: blend `old_fixed` and `fast_only` with stable weight
  0.4307815378871372, previously chosen on four UrbanEV Development stations.
- `fixed_share`: same expert pair, initial weight and losses; the previously
  selected eta=0.1/share=0.1 update. This controls forecast weights, not lambda.

No new calibration or candidate selection uses this historical cohort. The same
14-day Development selection is deliberately carried into all cities and all
history budgets. This tests a fixed recipe's transfer, not per-city optimality.
The original report's source/initial/online training profiles are unchanged.
The historical Fixed arm adapts its prefix at lambda=1; the adaptive bank starts
from the common lambda=0.1 prefix state. Consequently `confidence7` versus
`old_fixed` inherits that original initialization difference. `confidence7` versus
`mean7` isolates the confidence gate on an identical bank. Do not describe the
historical bank as three independently initialized fixed-lambda models.

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

The second dispatch exposed the empty-prefix case at UrbanEV ID2193: the new
training adapter called `train_epoch` on an empty list, which correctly rejected
it. The dispatch was stopped, preserving completed experts and partial outputs.
[execution-lock-v3.json](execution-lock-v3.json) records the corrected policy: zero
initial optimizer steps when no complete prefix examples exist, retain Source
initialization, and train only if complete labels later arrive. This matches the
original runner's source-only initialization behavior. A real synthetic replay
regression starts with no prefix and verifies three later online updates. The
third dispatch reuses only completed compatible experts from the prior roots.

Execution roots outside Git:

- `runs/issue99-full-scope-20261110-v1`: incomplete first dispatch, preserved.
- `runs/issue99-full-scope-20261110-v2`: stopped second dispatch, preserved.
- `runs/issue99-full-scope-20261110-v3`: zero-prefix-corrected full dispatch.

Both live under `/Users/quyenmanh/Developer/TFL-EV`. Model checkpoints and large
cell artifacts remain outside Git. Fresh-run execution only; rolling-memory
resume is unsupported. The corrected dispatcher uses two CPU processes, each with
one Torch thread. No provider GPU session or compute purchase is started.

## Verification and reproduction

```
python -m tools.issue99_full_scope --base ORIGINAL_CHECKOUT \
  --lock docs/reports/issue99-full-scope-20261110/execution-lock-v3.json \
  --output NEW_RUN --jobs 2
python -m tools.issue99_full_scope_readback --base ORIGINAL_CHECKOUT \
  --lock docs/reports/issue99-full-scope-20261110/execution-lock-v3.json \
  --run NEW_RUN --output NEW_READBACK
```

Readback independently reconstructs exponential mixture weights and forecast
MAEs, checks effective online retention choices, authenticates both historical
forecast banks, reconstructs every rolling-window update, verifies retained
model/Adam/RNG state digests and finite tensors, rehashes inputs and rebuilds all
21 station-first aggregates. The confidence gate itself is covered by the existing independent offline
fixtures; readback does not independently rerun every real bootstrap resample.
Counts, final measured results and code checks are appended only after execution
completes.

## Verified results

All **810 units / 21 groups** completed. Independent readback preserved all nine unscored UrbanEV2193 units, verified all retained expert states and rebuilt the original Fixed/Adaptive aggregates.

| Namespace | History | Old Fixed | Old Adaptive | Confidence7 | Static blend | Fixed-share | Fixed-share reduction vs Fixed |
|---|---:|---:|---:|---:|---:|---:|---:|
| urbanev-SZH | 7 | 8.039986 | 8.101369 | 8.073095 | 8.150995 | 8.111110 | -0.885% |
| urbanev-SZH | 14 | 7.975751 | 8.051655 | 8.025337 | 8.036057 | 8.001586 | -0.324% |
| urbanev-SZH | 28 | 7.915859 | 8.001464 | 7.965144 | 7.987887 | 7.951246 | -0.447% |
| charged-AMS | 7 | 6.148281 | 6.155903 | 6.155706 | 6.129360 | 6.130952 | +0.282% |
| charged-AMS | 14 | 6.148170 | 6.151978 | 6.150738 | 6.130498 | 6.132130 | +0.261% |
| charged-AMS | 28 | 6.148167 | 6.152893 | 6.150437 | 6.133101 | 6.134250 | +0.226% |
| charged-JHB | 7 | 1.320553 | 1.368513 | 1.372357 | 1.223038 | 1.217904 | +7.773% |
| charged-JHB | 14 | 1.322741 | 1.360420 | 1.353257 | 1.234085 | 1.226923 | +7.244% |
| charged-JHB | 28 | 1.291883 | 1.356048 | 1.348250 | 1.192612 | 1.192437 | +7.698% |
| charged-LOA | 7 | 1.322025 | 1.327253 | 1.335537 | 1.280666 | 1.280346 | +3.153% |
| charged-LOA | 14 | 1.333404 | 1.343140 | 1.347212 | 1.289520 | 1.288887 | +3.339% |
| charged-LOA | 28 | 1.326499 | 1.327091 | 1.329226 | 1.276539 | 1.275918 | +3.813% |
| charged-MEL | 7 | 52.848216 | 52.154153 | 52.112722 | 51.638396 | 51.644275 | +2.278% |
| charged-MEL | 14 | 54.365506 | 53.083993 | 52.921551 | 52.222188 | 52.264934 | +3.864% |
| charged-MEL | 28 | 54.242339 | 53.083191 | 53.142133 | 52.144367 | 52.193404 | +3.777% |
| charged-SPO | 7 | 2.021739 | 1.970220 | 1.949402 | 1.928417 | 1.923425 | +4.863% |
| charged-SPO | 14 | 1.989324 | 1.941425 | 1.934185 | 1.888683 | 1.886924 | +5.147% |
| charged-SPO | 28 | 2.025607 | 1.967929 | 1.952137 | 1.913308 | 1.912575 | +5.580% |
| charged-SZH | 7 | 91.821113 | 90.630583 | 90.817577 | 85.702645 | 85.916603 | +6.430% |
| charged-SZH | 14 | 90.843572 | 89.329988 | 90.164839 | 85.030083 | 85.190723 | +6.223% |
| charged-SZH | 28 | 90.885344 | 89.331033 | 90.383608 | 84.667508 | 84.864786 | +6.624% |

MAE is in kWh; positive reduction means lower error. Namespaces have different scales and are not pooled. Counts below describe group means, not independent replications or significance.

| Method | Groups with lower MAE than original Fixed |
|---|---:|
| old_adaptive | 9/21 |
| fast_only | 16/21 |
| static_mix | 18/21 |
| fixed_share | 18/21 |
| mean7 | 10/21 |
| confidence7 | 9/21 |

Fixed-share improves on static blending in **12/21 groups** (UrbanEV, JHB, LOA and SPO at all three histories), but loses in **9/21** (AMS, MEL, CHARGED/SZH). It improves on the old Adaptive in **20/21**, losing at UrbanEV 7d. Static blending itself also beats Fixed in **18/21**, so the expanded win count is not uniquely attributable to the adaptive update. The fast expert alone beats Fixed in 16/21.

The new family has a stronger descriptive result than the old controller across this historical scope. This does **not** establish a superior continuous-lambda controller: the improved variant is a two-GRU forecast ensemble. The same-bank confidence update alone remains at 9/21 wins, and UrbanEV remains unfavorable at all three budgets. No posthoc parameter replacement was made. An untouched confirmation cohort and method-level scientific review remain necessary before a generalization/novelty claim.

Readback checked **201,879 daily mixture vectors**, **67,293 rolling updates**, and **810 finite final model/Adam/RNG states**. Full precision: [group-results.csv](group-results.csv), [cells.csv](cells.csv), [verification.json](verification.json). Runtime/input identity: [run-registration.json](run-registration.json), [execution-evidence.json](execution-evidence.json).

The corrected dispatch reused **273** completed compatible experts and produced **537** remaining trajectories. There are **9** source-only initializations with zero initial target steps. Its 387.94-second wall time excludes prior incomplete dispatches, their reusable training, Source pretraining and independent readback; it is not total compute cost. Any partially written expert at termination was excluded from accepted reuse.

## Code validation

On implementation commit `4159233`, the root offline suite passed **966 tests**, with two CUDA-only skips. Fixed-adaptation and confidence-controller suites passed **9** and **12** tests. All five targeted follow-up tests pass, including zero-prefix initialization, identity authentication, null/equal-station weighting and independently causal mixture arithmetic. Ruff lint and formatting pass across 586 Python files; release verification passes 17 reports and 92 historical source pins. Source catalog listing and diff checks pass. No separate type checker is configured. The separate external-artifact suite was not run; real follow-up artifacts were checked by the readback above. Local success does not imply CI/peer approval.
