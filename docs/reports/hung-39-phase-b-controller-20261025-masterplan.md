# #39 Phase B — confidence controller

Evidence date: 2026-10-25. Executed code snapshot `a34a49e5f04920ef30456fe6c0ea56eb2f1d659a`; diagnostic config v1. Controller fixtures and actual Development decisions are available; independent implementation review remains open.

## 1. Objective & Scope

Verify #20/#39 keep/switch selection among three retention levels using paired errors from forecasts issued before their labels. The controller chooses the next block's trained candidate. This report establishes algorithm behavior and observed execution, not a statistical guarantee of long-term beneficial switches or superiority to a baseline.

## 2. Methodology

For complete arrived day `t` and challenger `j`, use scaled paired improvement

\[
\Delta_{t,j}=\operatorname{MAE}_{active,t}-\operatorname{MAE}_{j,t}.
\]

Positive values favor the challenger. A moving day-block bootstrap samples contiguous segments with replacement until it has `B` valid observations, trims to `B`, and averages the sampled improvements. Both challengers use identical sampled indices. At least `Bmin` valid days are required. The deterministic RNG seed is derived from SHA-256 of `seed:block_id`; each challenger uses alpha/2 under the declared Bonferroni rule. The empirical lower bound is sorted order statistic `max(0, ceil(alpha_each × R) − 1)` without interpolation. For config v1 (`R=100`, alpha_each 0.025), this is index 2.

A challenger qualifies only if **LCB > delta**. Choose greatest LCB, then the retention level nearest the current one, then fixed configured order. Equality keeps the active policy. Missing/incomplete/unavailable days have no paired error. In this diagnostic policy, successive complete observations are treated as adjacent even if missing scheduled days lie between them.

## 3. Implementation

`controller.py` provides validated `ControllerConfig`, `DailyScore`, `Decision`, and `decide_block`. `DailyScore` rejects MAEs without complete arrived labels; `decide_block` validates day identity/count and active level. It does not access datasets or model weights. `runner.py` supplies stored forecasts and chronological label arrivals and applies the returned decision only after the block. Decision payload records current/selected levels, valid/skipped days, all LCBs, alpha per challenger and reason.

## 4. Input

Controller inputs are per-day normalized MAEs of the three candidate forecasts on the same complete 24-hour labels. They are not pooled across entities or budgets. Under the real run, these come from the verified DATA-v1 UrbanEV/SZH Development replay bound to each entity's manifest and scale. The controller cannot fill labels or infer a missing day's score. Phase 0 records input hashes; Phase C documents chronology.

## 5. Configuration

Config v1 levels `{0,0.1,0.2}`, initial level 0, scheduled block 14 days, `Bmin=5`, delta 0, alpha 0.05, Bonferroni two challengers, bootstrap 100 resamples and segment length 2. Seeds 7/11/19 remain fixed. These are diagnostic Development choices awaiting team approval. Unit fixtures deliberately use other small configurations (including levels `{0,0.1,0.3}` and `Bmin=3`) to exercise expected values; their settings must not be mistaken for the real-run config.

## 6. Output

Each replay manifest contains `event_evidence.decisions`, and runner checkpoints contain the same decision history with model/optimizer state. Journals contain chronological `decision:block_id:selected_level` events. A decision's reason is `insufficient_days`, `no_qualifying_challenger`, or `switch`. The selected model is the already trained candidate; no past forecast is replaced by the newly selected policy.

## 7. Experimental Results

Actual examples from `runs/hung-39-representative-local-20261025T2103/7d/seed-7/entity-1405/replay-90/run_manifest.json`:

| Block decision | Current → selected λ | Valid / skipped | Challenger LCBs in level order | Reason |
| --- | --- | --- | --- | --- |
| 0 | 0 → 0.1 | 13 / 1 | null, 0.0000891565, 0.0000753930 | switch |
| 1 | 0.1 → 0.2 | 14 / 0 | −0.0043838434, null, 0.0004919262 | switch |

Both decisions record alpha per challenger 0.025. The source-only selected entities have no complete 24-hour label day in this 90-origin slice; their insufficient-days outcomes must not be presented as evidence that any λ is better. Phase D contains the complete switch/keep inventory for all 69 cells.

## 8. Correctness & Validation

The combined 43-test command recorded in [Phase A](hung-39-phase-a-model-transfer-20261025-masterplan.md) passed, including all controller tests: insufficient/missing days; exact-threshold equality; two qualifying challengers/greatest LCB; nearest-level and fixed-order tie breaks; λ-zero active keep; repeatable paired resampling; invalid configs/scores; duplicate days/unknown levels. These are independent expected-value fixtures, not labels derived from this diagnostic run. The full session suite passed 174 tests with one skip.

The causal requirement also depends on runner tests, because a standalone `DailyScore` validates flags but cannot prove when an external caller issued forecasts. Phase C supplies forecast-before-label, late-label and boundary tests and real replay evidence.

## 9. Discussion & Limitations

Bootstrap confidence is conditional on this finite, dependent, possibly nonstationary slice. Bonferroni addresses the two challengers within a decision; this implementation does not establish family-wise guarantees over repeated blocks, entities or adaptive data trajectories. Treating successive complete observations as adjacent is a declared missing-day policy awaiting review. Only 100 resamples are used; no inferential adequacy claim is made. There is no independent comparison with Qyroven or approved config lock in this report.

## 10. Reproduction

Run `python -m unittest tests.test_hung_controller -v` for the controller-only fixtures, or use the combined command already executed in Phase A. To reproduce actual decision histories, run the exact representative driver/config in [the execution report](hung-39-representative-local-20261025.md) with a new output root and the same fixed seeds/input identities. Inspect LCBs and reasons in each retained manifest and verify its checkpoint/journal hashes with the Phase E inventory. Do not use observed MAEs to replace entities or retune levels.
