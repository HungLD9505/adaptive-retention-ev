# Fixed-model target-adaptation study

This isolated implementation evaluates fixed-model target adaptation. Its settings
and results are separate from the primary online forecasting pipeline.

## Scope and model

Source training and initial target adaptation use the Report 1 two-layer GRU,
hidden dimension 64, with no dropout. The last hidden state is concatenated with
the flattened 24x5 future calendar. Our explicit MLP choice is
Linear(184,64), ReLU, Linear(64,24), Softplus. This head width is an implementation
choice, not an independently established optimum or guaranteed weight compatibility
with another implementation's head. The same architecture is used for our Source and targets.

The forecast loss is mean absolute error over batch and 24 normalized outputs.
Retention is the mean over batch and 64 dimensions of
`((z_target - z_source) / (source_std + epsilon))**2`.
Population standard deviations (correction=0) are measured in evaluation/no-grad
mode over every selected Source training input, once per example, after training.
The frozen Source reference and standard deviations never receive target updates.
Total loss is forecast MAE + lambda * retention. Adam updates the entire target.

Each target/budget/lambda starts independently from the same Source weights with a
fresh Adam optimizer and the same seeded minibatch order. There is no checkpoint
carry between 7/14/28 days and no optimizer sharing between targets or lambda arms.
This is **initial adaptation followed by fixed-model held-out Development evaluation**:
there are no post-deployment updates, controller decisions, or official online
comparison claims. All predictions are persisted before the evaluator opens labels.
Only complete labels available by replay_stop are scored. Future validity never
determines whether to issue a prediction. Missing labels are never filled.

## Declared bounded configuration

`config.json` declares seed 320; 16 Source IDs; four initially trainable Development
IDs; three Source epochs; five target epochs; batch size 32; Adam learning rate .001;
epsilon 1e-6; fixed exploratory lambda values 0/.01/.1; budgets 7/14/28.
Selection is lexicographic from the **7-day prefix inventory**, not replay scores:
first 16 nonempty Source IDs, first four trainable Development IDs, plus the first
source_checkpoint_only ID and first blocked_undefined_scale ID. Keep those same
target IDs at all budgets, report each budget's actual initialization stratum.
This deliberately bounded prefix-defined Source subset is not source selection
for the main experiment and must not be presented as representative of all sites.

Zero-example targets preserve the Source weights with zero initial optimizer steps.
Undefined-scale targets remain blocked and have no invented model/scaler or score.
Coverage and original-unit station MAEs must accompany comparisons. Aggregate
station MAEs with equal station weight within initialization strata, excluding
undefined metrics explicitly. This single-seed study cannot establish benefit,
significance, optimal lambda, physical-site independence, or strict-online validity.

## Run (Python 3.12, CPU)

The recorded execution used a local CPU environment. Install
study dependencies separately; foundation requirements and CI stay unchanged.

```sh
python -m pip install -r experiments/fixed_adaptation/requirements.txt
python -m unittest discover -s experiments/fixed_adaptation -v
python -m experiments.fixed_adaptation.run --inputs data/inputs/issue18-input-handoff-v1-20261019 --output runs/duc-retention-cpu-20261026-v2
```

Use a **new output directory for every run**. For the released UrbanEV input ZIP,
verify size 151254390 bytes and SHA-256
`2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`
before extraction. The reader additionally pins the three extracted manifest hashes
and verifies every artifact's size/hash. It rejects changed inputs, even if a
modified manifest claims new hashes. Source reuse checks all selected entity/scaler
metadata and all example content; only the enclosing input_run_id is excluded from
the cross-budget content comparison. Each checkpoint still binds its exact manifest.

The CLI records config, code commit, dirty state, executed Python source hashes,
Python/PyTorch/platform/device, Source population/statistics, loss traces,
predictions, target coverage/MAE, checkpoints and a per-artifact SHA-256 inventory.
Checkpoints include model/optimizer state, torch RNG, architecture and
ev-checkpoint-input-binding-v1. They are terminal initial-adaptation snapshots,
not resumable online-runner checkpoints. Load only trusted study checkpoints;
the local round-trip validation uses PyTorch's full checkpoint deserializer.
Raw archives were not freshly downloaded or verified by this study.

## Independent calculation

Use one 64-dimensional latent difference with first two values (2,4), all others
zero; first two source std values (1.5,3.5); epsilon=.5. Denominators are (2,4).
Then retention=(1+1)/64=1/32; derivatives with respect to the first two target
latent values are 1/64 and 1/128, with all others zero. The fixture checks these
numbers directly, independent of the model implementation. This artificial epsilon
is for hand calculation only; the real study uses 1e-6. Other tests check matched
lambda-zero model/optimizer trajectories, frozen/no-grad source, isolated target
state, shape/positivity, checkpoint reload/no-overwrite, label availability,
role/prefix/scaler rejection and Source cross-budget identity. Identical CPU GRUs
in train/eval kernels can differ at roundoff; the model fixture uses a 1e-12
retention tolerance rather than claiming bitwise identity across those kernels.

Run the README foundation checks as well. These ML tests are invoked separately
so foundation CI does not acquire Torch or train on real data. See
`docs/reports/member-duc-retention.md` for completed-run evidence and limitations.
