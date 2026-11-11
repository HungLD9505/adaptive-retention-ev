# Issue 19 — independent GRU training and target adaptation

Implementation owner: Qyroven. This code was written from Report 1 and the accepted #18
interfaces, without importing/copying Hung's implementation. #20 controller and #21
online runner are deliberately outside this implementation.

## Model and loss

`ForecastGRU.encode(X_hist[B,24,7]) -> z[B,64]` uses a standard unidirectional
`torch.nn.GRU(7,64,num_layers=2,batch_first=True)`. Hidden state starts fresh for every
window. The final state of the second layer is concatenated with the flattened
known future calendar `[B,24*5]`. The MLP outputs `[B,24]` through Softplus.
The current MLP width 64, ReLU, dropout 0, Adam and smoke training budgets are explicit
implementation/Development choices; only the Report 1 requirements are method constants.

Forecast loss is mean MAE over complete normalized 24-label samples. Retention is:

$$L_r=\frac1{64}\sum_{k=1}^{64}\left(\frac{z_{T,k}(X)-z_{S,k}(X)}{s_k+\epsilon}\right)^2.$$

The reference encoder is frozen, in evaluation mode, and detached. Its input is the
same normalized historical tensor as the target. `s_k` is the **population standard
deviation (ddof=0)** of the final source encoder on every permitted source training
example. Moments are accumulated in float64, scales stored in float32 and fixed.
No target/future samples estimate these scales. Constant dimensions are handled by
the declared epsilon; the code does not replace latent scales with arbitrary units.
Total adaptation loss is forecast MAE + lambda times retention. Lambda zero skips the
retention branch and matches ordinary source-initialized fine-tuning.

## Training and reproducibility

Install Python 3.12, `requirements-dev.txt` and `requirements-model.txt`. Colab's actual
Python/PyTorch/CUDA/device and pip freeze must be retained if its runtime differs.
CPU CI installs the pinned PyTorch CPU wheel. Local tests use tiny independent fixtures;
actual Source/Development training is run on Colab, rather than on a local workstation.

Use [the notebook](../../notebooks/issue19_development.ipynb). It accepts a Git bundle
of this branch, so private repository access does not require tokens in notebook code.
Check the bundle SHA and executed commit, then verify the accepted input package.
All weights/configs/metrics/logs go to a new run directory. The final cell supports
an explicitly authorized Drive mount and copies to a new Drive directory. Alternatively
download the run ZIP and upload it to the team Drive without granting a new mount.

The fixed Development smoke matrix is:

- One full Source pass, seed 42, Adam lr 0.001, batch 64, MLP width 64.
- Targets 1001 and 1008, chosen by ID/Development role before outcomes; no filtering
  by favorable errors or future label completeness.
- Three independent budgets (7/14/28); three adaptation epochs; lambda 0 and 0.01.
- Epsilon 0.001. Last planned checkpoint, never best score/seed selection.
- First seven scheduled Development days scored with the adapted fixed checkpoint.
  No online updates, confidence decisions or Final evaluation.
- One GPU target resume from epoch 1, compared against uninterrupted predictions.

The configuration is a bounded readiness check, not the official tuned configuration,
not all nine baselines/five ablations/three seeds, and not evidence of method superiority.
CHARGED is supported as a separate profile by the consumer, but this matrix exercises
UrbanEV only; do not claim six-city experimental coverage.

## CLI and interfaces

```sh
python -m ev_models.run source --inputs /path/to/urbanev-SZH-7d \
  --manifest-sha256 EXPECTED_SHA --config configs/issue19/development-smoke.json \
  --output /path/to/new-source-run --device cuda

python -m ev_models.run target --inputs /path/to/urbanev-SZH-7d \
  --manifest-sha256 EXPECTED_SHA --config /path/to/target-config.json \
  --source /path/to/source/final.pt --source-sha256 EXPECTED_CHECKPOINT_SHA \
  --entity-id 1001 --output /path/to/new-target-run --device cuda
```

A target config is a copy of the smoke config with explicit `lambda` and adaptation
`training.epochs`; the matrix driver materializes all exact configs. Entry point:

```sh
python -m tools.issue19_colab_smoke --inputs-root /path/to/issue18-input-handoff-v1-20261019 \
  --output /path/to/new-matrix-run
```

Every CLI checks manifest and consumed artifact fingerprints, declared hash split,
profile, daily window/calendar/mask, prefix containment, label completeness and
normalization. Only Source and explicitly identified Development targets can train.
The accepted input producer supplies original label availability evidence; consuming
contained examples does not establish upstream causality. Forecasts are written and
hashed before label artifacts open for scoring; all-24 availability gate is reused.
Coverage and initialization stratum accompany metrics. Final samples in shared files
are not used for model fitting, scoring or configuration selection.

## Checkpoints and resume

Each source checkpoint binds the input manifest, all source entity/scaler metadata,
permitted source bounds/profile and source-population identity. Reuse across budgets
requires compatible Source identities/scales/history/config/seed. Each target gets its
own model and fresh adaptation optimizer, bound to its entity, budget, scale and source
checkpoint hash. Source optimizer transfer is not initial target adaptation; carrying
an optimizer across online blocks belongs to #21.

Checkpoint schema `ev-model-checkpoint-v1` stores architecture, model/Adam state,
source-derived latent scales, seed/config/code/input binding, Python/Torch CPU/CUDA RNG
states and completed epochs. Read uses `weights_only=True` and an explicit expected
SHA. Writes never overwrite. Resume is supported at **epoch boundaries**, with the
same planned config, executed module hashes and recorded environment, into a new output
directory. Supply `--resume /path/epoch-N.pt --resume-sha256 SHA`. Batch order is derived
from the recorded seed and epoch. No exact cross-device/library replay is promised.

Targets with zero initial examples but defined scales retain Source weights and are
reported as `source_checkpoint_only`; undefined scales remain blocked. No labels are
filled and neither targets nor budgets share mutable adaptation state.

## Comparison with Hung

Compare the same fixture weights/input tensors and model/head dimensions before
comparing metrics. Record MLP shape/activation, epsilon, latent std ddof/population,
optimizer initialization/state, batch order, seed/device and checkpoint binding.
Then compare forecast/latent/loss/gradient and reload/resume behavior under agreed
numerical tolerances. Equivalent architecture/loss alone does not imply identical
weights after differently configured training. Do not read score differences as a
method win or select the favorable implementation post hoc.
