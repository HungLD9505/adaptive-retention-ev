# Hung Sprint 2 — Phase 00 interface proposal

Date: 2026-10-21. Scope: Issue #39, stages #19–#21. Prepared against `dev` commit
`7a57e9e8954eb8fcdc0809b1d7f02f6c32753a0c`. This is an implementation
proposal for consumer review, not evidence of model training or interface agreement.

## Preflight

- Report 1 pp. 3–6 supplies the model, loss, candidate, decision, replay and
  evaluation rules. `AGENTS.md`, `README.md`, `docs/WORKFLOW.md`,
  `docs/SPRINT_PLAN.md`, `data/README.md`, and Issues #15/#19/#20/#21/#39
  supply workflow and acceptance gates.
- Reuse `ev_inputs` and the accepted `ev-input-v1` feature order. The predictor
  takes `X_hist[B,24,7]` and `C_future[B,24,5]`, both float32, and must never
  receive labels or future-label validity. `iter_forecasts` verifies the input
  manifest and artifact fingerprint. Training, labels, entities and schedule
  remain separate artifacts under `ev-loader-run-v2`.
- The accepted `ev-missing-data-v1` policy keeps a scheduled origin even when
  no forecast is emitted, requires all 24 arrived valid labels to score/update,
  retains `source_checkpoint_only` as a separate stratum, and blocks undefined
  scales. Local strict-online causality is not certified.
- This checkout has no DATA-v1 input snapshot installed and Python 3.12 was not
  found by `py -3.12`. No real-data training or checksum verification has run.

## Proposed Python interfaces

These signatures describe semantics. Types and exact names may be revised after
consumer review without changing the accepted data contract.

| Component | Proposed input | Proposed output / invariant |
| --- | --- | --- |
| Model `forward` | `x_hist: Tensor[B,24,7]`, `c_future: Tensor[B,24,5]` | `forecast: Tensor[B,24]` nonnegative; `latent: Tensor[B,64]` available through an explicit method or structured output. The latent comes from the last GRU state. |
| Forecast loss | `forecast, y_scaled`, only complete valid horizons | Mean absolute error over 24 hours and eligible batch samples; no partial-label filling. |
| Retention loss | Target latent, frozen source latent on the **same** normalized X, fixed source-training `scale[64]`, positive epsilon | Mean over samples of `(1/64) * sum(((z_target-z_source)/(scale+epsilon))**2)`. Source has no gradient. Invalid scale is an error, not silently repaired. |
| Target initialization | Identified source model/checkpoint, target identity `(dataset,city,entity,budget,scale_id)`, permitted initial examples | Independent model and optimizer per target/budget. `source_checkpoint_only` skips initial adaptation. |
| Controller score | Active level, daily normalized MAE for all three candidates on the same complete, arrived 24-hour label day | Paired `MAE(active)-MAE(challenger)` observations; no score from missing days. |
| Controller decision | Three ordered levels, current level, paired daily observations, `Bmin`, `delta`, `alpha`, bootstrap segment length, resample count and seed | Keep unless `B>=Bmin` and a challenger has `LCB>delta`; choose largest LCB, then nearest level, then fixed order. Decision changes only the next block. |
| Runner event | Scheduled origin, predictor-only input or explicit skip, separately arriving label record | Fork three identical model/optimizer states at block start; forecast and persist before labels; score and update only after all labels arrive; finish previous block decision before the next affected forecast. |
| Checkpoint/resume | Active and candidate model/optimizer states, all RNG states, issued forecasts, scores, event cursor, block ID, audit state | Atomic new checkpoint with exact replay position; resume must not reissue a forecast or repeat an optimizer update. |
| Input binding | `ev-checkpoint-input-binding-v1` fields from `docs/data/INPUT_ACCEPTANCE.md` | Bind source/target manifest SHA, run ID, feature schema, identity, budget, scale ID and source checkpoint SHA; verify before load. |
| Metrics/evidence | Issued predictions, joined eligible labels, fixed energy scale, schedule, runtime counters | Original-kWh MAE/RMSE; requested/emitted/scored coverage and missing reasons; separate candidate/audit time, steps and memory; run ID, code SHA, config/seed, input/checkpoint hashes. |

## Open decisions for Development and interface review

Report 1 does not fix future-calendar MLP width/activation, epsilon value,
latent standard-deviation estimator and degenerate-scale policy, exact
bootstrap resampling/quantile and two-challenger adjustment, positive lambda
levels, initial level, `Bmin`, `delta`, `alpha`, update schedule or seed list.
Choose and record these on Development only; do not use Final for selection.
The first #19 implementation can expose explicit configuration while the
model consumer reviews the interface. Dependent #21 integration waits for
controller/runner payload agreement. Issue comments have not been posted.

## Work allocation and checkpoint

The orchestrator owns contracts, gates and evidence. Model agent owns #19
model/retention/training and tests; controller agent owns #20 and tests after
reviewing the score payload; runner agent owns #21 only after #19/#20 APIs;
QA owns independent expected-value and integration tests. At most two agents
should edit disjoint files concurrently in this workspace. No training runs
or PR merges are part of Phase 00.

Today's soft token allocation is 15% preflight/interface, 50% model and
retention, 20% controller, 10% targeted verification, and 5% checkpoint and
handoff. These are planning shares, not token counters or permission to relax
acceptance gates. The runner receives a later allocation after model and
controller interfaces pass; avoid opening a third concurrent coding stream.
Stop at a safe code/document checkpoint if account usage becomes tight; never
consume a usage reset.

## Local execution checkpoint — 2026-10-21

- #19 now has the GRU, loss and bounded manifest-bound Source/Development
  smoke entry points. #20 has an independent controller with explicit
  bootstrap and tie rules. These are code and fixture results only.
- `python -m tools.sources list` passed. With `TEMP`/`TMP` set inside this
  worktree and `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`,
  `python -m unittest discover -s tests -q` ran **140 tests, OK** under
  Python 3.13. `python -m compileall -q experiments/hung_sprint2` and
  `git diff --check` passed. The first baseline suite attempt failed because
  the sandbox denied its default temporary directory; a second attempt with
  local TEMP but without UTF-8 had three Windows codec failures. The final
  configured run passed.
- `python -m ruff` was unavailable. Installing the pinned `ruff==0.17.0`
  into ignored local dependencies failed because PyPI name resolution was
  blocked. Python 3.12 was not found by `py -3.12`.
- No DATA-v1 files have been downloaded/verified in this worktree. No real
  Source pretraining, Development adaptation, Colab run, controller replay,
  cross-implementation comparison or peer review has run. The phase gates
  requiring those activities remain open.

## #20 controller slice

This slice is based on #19 offline commit `1ba63a1` because the two modules
share the proposed score interface; #19 is not merged into `dev` yet. The
controller takes daily paired normalized MAEs, excludes incomplete or
unarrived days, applies a moving contiguous-day block bootstrap with shared
resample indices across challengers and Bonferroni `alpha/2`, then requires a
strict `LCB > delta`. The percentile uses a fixed empirical order statistic;
the seed and block ID make decisions reproducible. These bootstrap details
are an explicit Development policy proposal pending consumer review.

`python -m unittest tests.test_hung_controller -v` ran **9 tests, OK** under
the local Python 3.13 UTF-8/TEMP setup. It does not establish runner timing or
real-data controller behavior. The config parameters have no selected
research values yet; fixture values are tests only.

Bootstrap currently treats successive **valid observations** as adjacent even
when a scheduled day between them had no complete label. Report 1 does not
specify this gap handling. Review this Development policy before actual replay.

## #21 runner fixture slice

This branch is stacked on #20 commit `1bcde3a` pending review/merge. The CPU
fixture runner forks three model/optimizer candidates, stores forecasts before
arrived labels, scores and updates only complete horizons, completes block
decisions before later forecasts, carries the trained selected/active state,
and keeps a separate one-block old-policy audit branch. It can save/load a
create-only checkpoint containing model/optimizer, RNG, pending forecasts,
event cursor, score history and input binding. Unit tests exercise keep,
forced switch, missing labels, boundary ordering and resume.

This is not the real Development replay gate: no accepted DATA-v1 schedule/
labels adapter, actual timestamp availability validation, CUDA RNG handling,
durable event log, full cost accounting or real block-boundary smoke exists.
The runner fixture tests ran **6 tests, OK**. QA reproduced a float32 epsilon
underflow; #19 commit `7a93558` now rejects nonfinite retention/gradients,
prevalidates bounded Source sample count, and publishes checkpoints atomically.
The fix was applied to this stacked branch as `68fb36e` (and to #20 as
`ac1726e`). The final branch-wide local check ran **149 tests, OK** under
Python 3.13 with repo-local TEMP and UTF-8, plus `compileall` and
`git diff --check`. The checkout is clean. This is offline fixture evidence,
not a claim that any real-data, Colab, Ruff or Python 3.12 gate passed.

## #21 accepted-input adapter checkpoint

The replay adapter verifies the v2 input manifest and artifact hashes, selects
one Development target, checks its binding and scale, preserves scheduled
coverage, and issues predictor-only forecasts before consulting matching
labels. It uses `ready_labels` to admit only complete, available horizons;
fixture tests cover label delay, missing labels, blocked coverage, tampered
artifacts, binding, and forecast-first order.

After this adapter was added, `python -m unittest discover -s tests -q` ran
**152 tests, OK** on Python 3.13 with repo-local TEMP and UTF-8. `python -m
compileall -q experiments/hung_sprint2` and `git diff --check` passed. The
adapter cannot resume from a nonzero cursor, and labels arriving after the
next origin are currently skipped rather than queued for later updates.
There is no installed DATA-v1 snapshot or real Development replay evidence;
the #21 integration and Phase 04 gates remain open.
