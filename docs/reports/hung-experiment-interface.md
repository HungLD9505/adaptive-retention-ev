# Hung Sprint 2 experiment interface proposal

Status: **proposed for consumer and method review**, 2026-10-22. This is the
experiment-readiness interface work attached to #21/#39. Issue #22 has no
assigned owner or reviewer and does not authorize implementation. No baseline,
ablation, Development comparison, or Final evaluation is claimed here.

## Shared comparison contract

Every compatible method must consume the accepted 24-hour history and future
calendar inputs, issue a 24-hour forecast at the same scheduled origin, and
receive labels only when their full 24-hour horizon has arrived. The accepted
input manifest, feature schema, entity identity, history budget (7/14/28
days), frozen scale, requested origins, missing-day reasons, and complete-label
gate remain shared. A method cannot add future labels, change its cohort, or
silently drop an unfavorable scheduled day.

The proposed adapter boundary is:

| Operation | Required behavior and evidence |
| --- | --- |
| Initialize | Bind dataset/city/entity/budget, input manifest SHA, source checkpoint SHA when used, method/config/seed/code identity, and permitted initial prefix. Create independent model and optimizer state for each target/budget/method/seed. |
| Forecast | Accept predictor-visible tensors only. Return nonnegative 24-hour predictions and method state identity before any matching label is read. Store issued predictions durably for scoring and resume. |
| Label arrival | Receive the scheduled status and an availability/validity gate. Score and update only on a complete arrived horizon; never backfill an unavailable or partial horizon. Preserve issued forecasts when a late label arrives. |
| Boundary/decision | If the method has an online decision, use only information available at that boundary. Record candidate scores, decision rule, selected trained state, and any separate audit branch. A fixed or non-adaptive method records that no decision was made. |
| Checkpoint/resume | Persist enough model/optimizer, RNG, issued forecast, origin cursor, and decision state to resume without reissuing forecasts or repeating updates. Bind the checkpoint to the exact inputs/config/code and verify hashes before loading. |
| Output | Record requested/created/scored coverage, original-kWh MAE/RMSE for eligible issued forecasts, seed/config/run ID, code and input hashes, events/decision evidence, elapsed time, peak process RSS where available, and actual inference/update costs. Candidate and audit costs stay separate when present. Unavailable measurements remain null with scope stated. |

The current `experiments/hung_sprint2` runner/CLI is an implementation slice of
this boundary for the adaptive method. This document does not assert that all
baseline adapters already satisfy it. A reviewer must decide which existing
runner interfaces can be reused and which need extension without changing the
accepted input contract.

## Required method families

The nine baselines in `docs/SPRINT_PLAN.md` §2 remain mandatory. The table
states the proposed integration seam, not a completed algorithm or a new
method choice.

| Baseline | Proposed seam / unresolved review point |
| --- | --- |
| Seasonal Naive with fallback | Stateless forecast adapter on the same origin schedule. Specify the fallback using Development only before implementation. |
| Target-only GRU | Same backbone/task and target-prefix budget, with no source initialization. Keep independent seed and optimizer state. |
| Frozen Source | Bound source checkpoint used for prediction without target updates. |
| Full Fine-tuning | Source initialization with retention weight zero, independent target state. |
| Fixed Retention | Source initialization with one Development-locked positive retention weight, without online selection. |
| Simple Online Best-λ | Same three candidate forks, block length, data, update budget, and checkpoints as the adaptive method; replace only confidence selection with mean-error selection. |
| Source-error controller | Use recent frozen-source error on arrived complete labels only. Review the Development-locked proxy, window, and mapping to levels. |
| Uncertainty controller | Review a source-prediction dispersion estimator and Development-only calibration/mapping; no future-label or Final calibration. |
| Drift controller | Compare decision-time load descriptors with an available historical reference. Review the reference, statistic, and Development-only mapping; high drift does not automatically imply lower retention. |

The five required ablations are Without Confidence, Fixed λ, Parameter
Retention, Different Block Size, and Without Source Initialization. The first
two may reuse an identical baseline run only when method, config, seed, input,
and artifact identity are exactly the same; report one run once rather than
counting it as independent evidence. Parameter Retention and Without Source
Initialization need explicit loss/state definitions reviewed before coding.
Different Block Size changes only a Development-locked block schedule unless
the method review records a justified wider change.

## Fairness and lock evidence

- Use identical eligible targets, origin schedule, frozen scale, label
  availability rule, and original-kWh metric aggregation across compatible
  methods. Record exceptions and their coverage effect instead of hiding them.
- Record at least three seeds for the mandatory Final matrix. Select proxy
  estimators, thresholds, fallback, positive λ levels, block sizes, exclusions,
  and calibration only on Development; lock them before Final. Final labels may
  enter only the locked online procedure.
- Count actual work for each method. A single-model baseline does not inherit
  fictitious three-candidate or audit costs; the adaptive method reports all
  three candidates and its isolated audit branch. Wall time and process peak
  RSS are not per-candidate memory attribution.
- A measured representative Development run must support any throughput,
  storage, and execution-window estimate for the complete seed × budget ×
  method matrix. No capacity figure is available yet; do not infer one from
  fixture timings or green CI.

## Decisions required before #22 implementation

1. Assign #22 an owner and a different reviewer; obtain consumer review of
   this interface and the exact adapter boundary.
2. Fix the Seasonal Naive fallback, proxy estimators and level mappings,
   Parameter Retention loss/state, and no-source ablation initialization on
   Development. Record comparable tuning budgets.
3. Decide how the current runner/checkpoint schema represents stateless,
   single-model, three-candidate, and audit methods without erasing actual
   cost differences; add fixtures for chronology, resume, and coverage.
4. Run real Development smoke and measure capacity after Colab access is
   available. Only then lock configuration and schedule Final work.

Source of requirements: `docs/SPRINT_PLAN.md` §2, §5–6, and GitHub issues
[#21](https://github.com/HungLD9505/adaptive-retention-ev/issues/21),
[#22](https://github.com/HungLD9505/adaptive-retention-ev/issues/22), and
[#39](https://github.com/HungLD9505/adaptive-retention-ev/issues/39).
