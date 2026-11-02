# #39 Phase A — forecasting model, transfer and retention

Evidence date: 2026-10-25. Runtime snapshot: `a34a49e5f04920ef30456fe6c0ea56eb2f1d659a`, local run `hung-39-representative-local-20261025T2103`. This report separates executed diagnostic evidence from the subsequent fixture-tested model-checkpoint RNG addition.

## 1. Objective & Scope

Implement the Report 1 forecasting backbone and source-initialized target adaptation for #19/#39. Verify shapes, gradient flow, frozen reference semantics, latent normalization, checkpoint weight/optimizer reload and real forecast output. Research adequacy of one Source pass and the Development configuration remains for team review; baseline effectiveness and Final evaluation are outside this report.

## 2. Methodology

The two-layer GRU maps historical input to the final 64-dimensional latent vector. A ReLU calendar MLP maps flattened known-future calendar features from 120 to 8 dimensions. Concatenating the latent and calendar vector feeds a 72→24 linear head followed by Softplus. Actual parameter count read from the current model is **41,696**: encoder 38,976, calendar MLP 968, head 1,752.

For a batch of complete 24-hour samples, the implemented scaled loss is

\[
L_{\mathrm{forecast}}=\frac{1}{B\,24}\sum_{b,h}|\hat y_{b,h}-y_{b,h}|,\qquad
L_{\mathrm{retain}}=\frac{1}{B\,64}\sum_{b,k}\left(\frac{z_{T,b,k}-z_{S,b,k}}{s_k+\epsilon}\right)^2,
\quad L_{\mathrm{total}}=L_{\mathrm{forecast}}+\lambda L_{\mathrm{retain}}.
\]

These match the Report 1 equations carried by the masterplan and repository research-flow reference. The reference is a separate cloned Source model in evaluation mode with gradients disabled. Both encoders receive the same target-normalized history. Source latent scales are population standard deviations (`correction=0`) estimated from permitted Source-training histories and held fixed. At **λ=0**, the code skips retention and performs full fine-tuning from Source weights; this is not target-only initialization.

## 3. Implementation

Existing modules under `experiments/hung_sprint2/` provide `ForecastGRU`, `forecast_mae`, `initialize_target`, `source_step`, `target_step`, `source_latent_scale` and model checkpoint save/load. Public model input/output dimensions are validated; nonfinite loss/gradients and invalid scale/epsilon fail before an optimizer step. `initialize_target` copies the model and creates independent Adam state, so one target cannot mutate the Source/reference or another target. No core code was edited for this representative execution.

## 4. Input

Use DATA-v1-20261019 UrbanEV/SZH, the three verified manifests and hashes listed in [Phase 0](hung-39-phase0-environment-20261025-masterplan.md). `X_hist[B,24,7]` includes scaled energy, calendar and the energy-present mask; `C_future[B,24,5]` contains known calendar; `Y[B,24]` contains complete labels only. Source examples precede deployment under the accepted input lineage. Each target's scaler and history budget are bound by manifest, entity, scale ID and Source checkpoint SHA. Undefined-scale entities remain blocked; source-checkpoint-only targets use zero initial adaptation steps.

## 5. Configuration

Config v1 fixes Source at one pass, batch 32, Adam LR 0.001, calendar hidden 8; target initialization at one pass, batch 2, LR 0.001, retention weight 0.1, epsilon `1e-6`. Seeds are 7/11/19. The representative execution used actual CUDA on RTX 3050 Ti with PyTorch 2.8.0+cu126/Python 3.13.7; full hashes and the Python-version deviation are in Phase 0. No epoch/λ/seed selection used Final or diagnostic MAE.

## 6. Output

Source and target stages save bound model weights, Adam state, architecture, fixed latent scales, seed/code/step metadata and manifest/checkpoint hashes. Replay checkpoints retain issued forecasts. Example lineage for **7d / seed 7 / entity 1405**:

- Source checkpoint SHA `06b048acc27334638867c36f175e3eafa28592db5c8981deb5341facc4b2c307`.
- Target checkpoint SHA `65af52f84b642c8541c1b34a17e7a0b3e035bdf14bca506961b35f9df297fba1`.
- Replay-90 checkpoint SHA `87bcc939eb166b6a5411d44b975095bf66dbfd87918b04f1d93735a194aa22fc`.

Paths are under `runs/hung-39-representative-local-20261025T2103/7d/seed-7/`, with target/replay under `entity-1405/`. These are retained ignored artifacts, not files committed to Git.

## 7. Experimental Results

The sample Source stage used **65,888/65,888** available examples, **2,059** steps, 33.407 seconds CLI duration, peak CUDA allocation 85,135,360 bytes. Its manifest retains the scope label `bounded_source_smoke`; using every permitted example for one pass does not approve the pretraining budget. Entity 1405 had four initial trainable examples and completed two target steps, 11.547 seconds CLI duration.

The first stored candidate forecast for origin `2022-12-01T00:00:00+08:00` has shape `[1,24]`. Its first six values after multiplying by the recorded energy scale 43.8666666667 are **27.691660, 28.050190, 28.012033, 28.163961, 27.565445, 28.056156 kWh**. These are actual checkpoint values, not illustrative predictions. The corresponding live replay produced 90 forecasts, scored 89 complete days, MAE **5.913999**, RMSE **8.148551 kWh**. Those are diagnostic outcomes, without a baseline claim. Full per-cell results belong to Phase D.

## 8. Correctness & Validation

The executed command below passed **43 tests** covering model/retention/training/controller/runner/resume/replay input fixtures. Phase A cases include forecast/latent shapes, nonnegative output, horizon/batch MAE, independent target state, λ-zero equivalence, encoder/head gradients, frozen reference, exact retention math, population Source scale, invalid/nonfinite safeguards, bound checkpoint reload and tamper/source-only handling.

```powershell
python -m unittest tests.test_hung_model tests.test_hung_retention tests.test_hung_training tests.test_hung_controller tests.test_hung_runner tests.test_hung_resume tests.test_hung_replay_inputs -q
```

This ran with repo-local `TEMP`/`TMP` and `PYTHONUTF8=1`; test time was 8.451 seconds. The session's full suite separately passed 174 tests with one skip. The Phase D audit verified checkpoint hashes and lineage across 216 stages.

## 9. Discussion & Limitations

At the pinned training commit, **model checkpoints do not store or restore CPU/CUDA RNG state**. `save_checkpoint` stores weights/Adam/scale/seed/code/step, and `load_checkpoint` restores those but constructs a model and does not restore RNG. A seed value alone is not an RNG snapshot. The frozen representative Source/target artifacts therefore do not support exact RNG resume. Runner checkpoints have a separate RNG implementation and tests, covered in Phase C.

The post-run follow-up adds optional `rng_state` metadata to newly saved model checkpoints, containing CPU state, all available CUDA states, model/device metadata, CUDA runtime and PyTorch version. `load_checkpoint(..., restore_rng=True)` explicitly restores this state after model construction and rejects old checkpoints without RNG, mismatched model device type/index, unavailable CUDA, or mismatched CUDA device/runtime metadata. The default `restore_rng=False` preserves transfer-loading behavior and loads legacy checkpoints. This was added **after** the representative run; it did not generate or modify frozen outputs. At validation, the updated `training.py` SHA-256 was `3a6b9844d203463a43f98252dda9714c569a1801eac9efed9203387f250ff4b5` (the final handoff commit identifies the code snapshot).

Three new CPU-only fixtures verify next-random-number restoration together with model/Adam/scale equality, default/legacy compatibility, and clear failures for missing/incompatible CUDA RNG metadata using mocks. `python -m unittest tests.test_hung_training tests.test_hung_model tests.test_hung_retention -q` passed **20 tests** in 5.507 seconds after this addition; scoped Ruff lint/format and `git diff --check` passed.

A subsequent actual CUDA recovery diagnostic loaded the existing 7d/seed-7 Source model/Adam/scale, saved a **new derived checkpoint without training**, and reloaded it with `restore_rng=True`. The next 11 CPU and CUDA random draws, all model weights, Adam state and latent scales matched exactly on `cuda:0`. Evidence: `runs/hung-39-model-rng-readback-20261025T2330/readback.json`; derived checkpoint SHA-256 `56263c590e5789de8e2cc85fc67871b1fc1eab637954b87a346e8531e3a067f0`. This verifies the new recovery capability, not a resumed Source training trajectory or a replacement for the frozen matrix.

No training loss curves were persisted in these stage manifests; no convergence claim follows from successful optimization. There was no fresh independent comparison to Qyroven, no approved Source-pass/config decision and no full-cohort/Final effectiveness evaluation. Source-checkpoint-only forecasts are useful execution evidence even when their incomplete 24-hour labels make error metrics null.

## 10. Reproduction

Use the fixed code/config/input/selection identity in Phase 0 and the exact driver command in [the representative report](hung-39-representative-local-20261025.md) with a new output root. Read the Source manifest before transferring its checkpoint; validate the exact target input binding on reload. For frozen `a34a49e` model checkpoints, reproduce Source/target stages from their fixed seeds rather than claiming interrupted-stage RNG resume. Newly saved checkpoints support explicit `restore_rng=True` only after same-environment/device validation; transfer loading remains the default. Existing completed stages can be hash-verified and reused by the driver under the original identity. Replay resume instructions and state scope are in Phase C/E.
