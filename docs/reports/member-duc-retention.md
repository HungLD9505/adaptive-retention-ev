# Duc independent target adaptation and retention study

Date: 2026-10-26 (Asia/Ho_Chi_Minh). Owner: huuduc32; implementation and execution
assisted by Codex. Scope: issue #40, related to #19. Branch:
`feat/19-duc-retention-study`, based on dev `7a57e9e8954eb8fcdc0809b1d7f02f6c32753a0c`.
Training code commit: `98899873ebd317bb5475885fd0d2a6c5c329b5ca`, clean at execution.
Later evidence/report/verifier commits do not change the executed training code.

## Status and deliverables

Implementation, independent calculations/tests, and real CPU Development execution
are complete. Peer review, CI disposition and artifact distribution are separate
acceptance gates. No merge or issue closure is performed by this report.

- Own model/loss, input verifier, training/evaluation CLI, config and offline tests:
  [study directory](../../experiments/member_studies/duc_retention/).
- Reproducible run: `duc-retention-cpu-20261026-v2`, 293.194 seconds total wall time.
- Evidence: [machine-readable results and per-artifact hashes](../../experiments/member_studies/duc_retention/evidence.json).
- 49 checkpoints: one independently trained Source, 36 adapted targets, and 12
  zero-step source_checkpoint_only target snapshots. All are outside Git.
- Distribution folder: [team Drive](https://drive.google.com/drive/folders/1jVSqUeZe0D_LSfTi5O9AeMVb3ZP_maVB).
  Initial upload failed with HTTP403 `storageQuotaExceeded`; the folder's existence
  is not evidence that files were uploaded. Distribution status will be updated
  after a verified successful retry. The user offered to free space.

## Method and provenance

The model is a two-layer GRU with input size 7, latent size 64 and dropout 0. The
last hidden state is concatenated with all 24x5 future-calendar features. The head
is Linear(184,64), ReLU, Linear(64,24), Softplus. Head width 64 is our documented
implementation choice where Report 1 leaves the hidden MLP width unspecified.
Source and target share this architecture. Another member's checkpoint is neither
required nor used; architectural compatibility is not a claim that our state dict
loads into an independently chosen head.

Forecast loss is mean MAE across batch and 24 normalized outputs. Retention is
the batch mean of `(1/64) sum_k ((z_T,k-z_S,k)/(s_k+epsilon))^2` on identical X.
The source reference is frozen, eval/no-grad. Source population std is computed
once after Source training using all 1,237 selected Source training inputs, with
correction=0, float64 reduction followed by float32 storage, epsilon=1e-6.
Observed std range is 0.10775354–0.38599303; no target data enters this statistic.
Loss is forecast MAE + lambda * retention; no parameter-distance substitute.

The Source checkpoint hash is
`a3c04df856622ed72fa1bf6229f87a43c8d06a8216b900bb15cbd094b584bf4d`.
All target checkpoints bind this hash and their exact target manifest, entity,
7/14/28-day budget and scale fingerprint using ev-checkpoint-input-binding-v1.
They include model/Adam state, torch RNG, config, architecture and code provenance.
These are terminal initial-adaptation checkpoints, not a resumable online runner.

Execution was on Windows 11 build 26200, Python 3.12.14, Torch 2.5.1+cpu,
NumPy 1.26.4, two CPU threads, deterministic Torch algorithms. The user explicitly
authorized local CPU instead of Colab in this session. Actual installed packages
are included in the artifact bundle environment text. No GPU/Colab execution is
claimed. Training used seed 320, Adam lr=.001, batch size 32, Source 3 epochs and
target 5 epochs; exploratory fixed lambdas are 0/.01/.1. No lambda was selected or
locked for the official experiment from this run.

## Data boundaries and cohort

The prepared UrbanEV ZIP was freshly downloaded, checked at 151,254,390 bytes and
SHA-256 `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`, then
extracted without overwriting existing inputs. The CLI pins the three manifest
hashes and validates all five JSONL files per budget. Raw publisher archives were
not freshly verified. No central input/producer, split/scaler policy, other
member's directory, shared dependency file or Final artifact was changed.

Selection was declared before completed results: lexicographically first 16
nonempty Source entities and four initially trainable Development entities in the
7-day prefix inventory, plus one source_checkpoint_only and one undefined-scale
Development entity. This bounded feasibility cohort is not a representative sample
or the fixed full Source population of the main experiment. No replay-score or
future-label-completeness selection was used. Same target IDs persist at all budgets.

Source IDs: 1002, 1011, 1013, 1017, 1018, 1019, 1021, 1029, 1033, 1037, 1040,
1042, 1043, 1047, 1049, 1051. Their 1,237 examples fit the Source prefix starting
2022-09-01 and ending before deployment 2022-12-01 (+08). Source training took
117 Adam steps, approximately 2.472 seconds including statistics/checkpoint work.

Development IDs: 1001, 1008, 1022, 1027 (initial adaptation), 1025 (source-only),
1053 (undefined scale at 7/14 days, source-only at 28 days). For the four adapted
IDs, 7/14/28-day prefixes provide 6/13/27 examples respectively. Each lambda arm
gets five steps at each budget (one batch per epoch), totaling 180 target steps.
Each starts from fresh Source weights and fresh Adam state, with paired ordering.
All Source entity metadata and training content match across budget containers;
only input_run_id differs. This field is excluded solely from the reuse comparison,
never from checkpoint provenance. Source scales/std stay frozen.

## Evaluation and results

This is **initial adaptation followed by fixed-model held-out Development
evaluation**, not the team's online/controller experiment. Predictions for the
90 daily origins Dec 1–Feb 28 are written before labels are read. The model remains
unchanged throughout evaluation. Only complete labels available by the March 1
replay cutoff can score. There are no post-deployment updates, future-label tuning,
adaptive lambda choices, baseline-matrix claims, or Final evaluation.

Station-first mean MAE in kWh for the four initially adapted targets (equal station
weight; same scored days across lambda arms):

| Initial history | lambda=0 | lambda=.01 | lambda=.1 | Scored station-days |
| --- | ---: | ---: | ---: | ---: |
| 7 days | 7.762981 | 7.543264 | 7.131107 | 283 |
| 14 days | 7.209713 | 7.189829 | 7.032354 | 283 |
| 28 days | 7.089927 | 7.095903 | 7.024912 | 283 |

At 28 days lambda=.01 is slightly worse than zero on this aggregate. At 7 days,
station 1001 has MAE 5.730955 with lambda=0 versus 5.782909 with lambda=.1,
despite the lower aggregate of .1. Neither aggregate nor a favorable station is
evidence of universal retention benefit. No uncertainty/significance estimate or
hyperparameter superiority is claimed from this single seed and small cohort.

Coverage, identical across lambda arms and budgets for the four adapted targets:

| ID | Requested | Issued | Full-label scored | Issued but unscored | Missing-X skips |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1001 | 90 | 59 | 52 | 7 | 31 |
| 1008 | 90 | 59 | 51 | 8 | 31 |
| 1022 | 90 | 90 | 90 | 0 | 0 |
| 1027 | 90 | 90 | 90 | 0 | 0 |

**Source-only and blocked strata are not mixed into that aggregate.** ID1025 has
zero initial examples/steps for every budget; all its target weights exactly equal
Source. It issues 43/90 forecasts but has zero complete scored days. Its MAE is
undefined (JSON null), not zero; 47 histories are skipped. ID1053 is blocked for
all 90 origins at 7 and 14 days, with no model/scaler fabricated. At 28 days it has
a defined scale but zero initial examples: 77 issued, 75 scored, 2 unscored and
13 missing-X skips. MAE is 36.864303 for all lambdas, as expected for identical
unadapted weights. Its wider-prefix initialization is a separate budget outcome,
not automatic online recovery of a blocked target.

## Independent calculation and verification

The hand calculation sets a 64-vector difference to (2,4,0,...), source std first
two coordinates (1.5,3.5), epsilon=.5. Retention=(1+1)/64=1/32; derivatives of
target coordinates are 1/64 and 1/128; remaining derivatives are zero. The test
asserts these numbers directly, not an expected value computed by the loss code.
The larger fixture epsilon is not the training epsilon.

Nine dependency-specific offline tests pass: hand calculation/gradient; source
freeze and eval/no-grad; identical-encoder numerical zero; lambda-zero matched
three-step model and Adam trajectories; isolated targets; positive output/shape;
checkpoint exact reload/no-overwrite; complete/late/missing label behavior;
role/prefix/scaler rejection; cross-budget Source signature and pinned manifest
rejection (some assertions share one test). CPU train/eval kernels produced a
retention around 1e-16 for identical weights, so that assertion uses 1e-12 tolerance.

All 119 foundation tests pass; source catalog listing, Ruff lint/format and
`git diff --check` pass. ML tests are separate; foundation CI does not install Torch
or download datasets. The result verifier independently checked 152 artifact
hashes/sizes, 49 checkpoints, source-stat immutability, input bindings, every logged
objective component, equal step/coverage budgets and exact unchanged Source weights
for all zero-example targets. All checks passed. Tests establish implementation
behavior, not effectiveness or scientific acceptance.

Commands (from repository root, Python 3.12 environment):

```sh
python -m tools.sources list
python -m unittest discover -s tests -v
python -m unittest discover -s experiments/member_studies/duc_retention -v
python -m ruff check .
python -m ruff format --check .
git diff --check
python -m experiments.member_studies.duc_retention.run --inputs data/inputs/issue18-input-handoff-v1-20261019 --output runs/duc-retention-cpu-20261026-v2
python -m experiments.member_studies.duc_retention.verify_results runs/duc-retention-cpu-20261026-v2 --output experiments/member_studies/duc_retention/evidence.json
```

Choose fresh output/evidence paths when reproducing. Checkpoint hashes can depend
on serialized provenance; reproducibility comparisons should also inspect tensors,
losses and predictions. The first diagnostic run `...-v1` stopped after 7 days
because a too-strict Source comparison included the different enclosing run IDs.
It remains preserved outside Git and is not used in the reported results. The
fix retains every sample/scaler field and has an independent regression test.

## Artifact handoff and remaining acceptance

Local bundle: `runs/duc-retention-cpu-20261026-v2.zip`, 23,035,669 bytes,
SHA-256 `357431c94b033f6844162d727864e72ac779f60d89f6ea70e6ebcea3933e1fe4`.
It contains the complete successful run plus actual environment versions. Individual
checkpoint/log/prediction hashes are in evidence.json and bundled artifacts.json.
Do not commit the ZIP, datasets, environments or checkpoint weights.

Pending: successful Drive distribution and verified file link; independent review
by hung00cyber and Qyroven; CI on the submitted PR; team's acceptance decision.
No self-approval, autonomous merge, parent-issue closure or Final authorization.
The full Sprint 3 >=3-seed method/budget matrix, online runner/controller and
cross-dataset claims remain outside this member-study evidence. Published UrbanEV
energy, upstream missingness/imputation and assumed arrival clocks retain the
data handoff's limitations; this is not evidence of strict real-world online readiness.
