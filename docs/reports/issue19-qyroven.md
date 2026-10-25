# Issue 19 — independent Qyroven model and training handoff

**Status:** implementation and actual Colab Source/Development smoke ready for peer review in [PR #47](https://github.com/HungLD9505/adaptive-retention-ev/pull/47). Issue #19 stays open; no merge or research-effectiveness acceptance is claimed.

## Implementation

Written independently from Report 1 and the accepted #18 interfaces, without importing/copying Hung's implementation. `ev_models/` provides a standard two-layer hidden-64 GRU, future-calendar MLP/ReLU/Softplus head, mean normalized MAE, frozen source reference and exact dimension-normalized latent retention, Source training, isolated target adaptation and versioned input-bound checkpoints. Source latent scales use every permitted Source training example, population std (ddof=0), and remain fixed. No #20 controller or #21 online runner is implemented.

See [training/interface instructions](../data/MODEL_TRAINING.md) and [full machine evidence](issue19-qyroven-evidence.json). Architecture/head width, epsilon, Adam and smoke budgets are explicit Development choices; Report 1 and accepted input/data policies are unchanged.

## Executed scope and provenance

- Runtime code: `81101185dab76bcb593daff08131c32a6c4d7b6b` (clean Git-bundle checkout). The final handoff adds this report and a return type annotation to the internal batching helper; training mathematics/control flow are unchanged. Resume an existing artifact at its recorded runtime revision, because exact resume validates module hashes.
- Colab Tesla T4; Python 3.13.16; PyTorch 2.11.0+cu130; CUDA 13.0; deterministic algorithms enabled. Local/CI reference is Python 3.12 with PyTorch 2.11.0. Exact cross-version/device equivalence is not claimed. Full resolved Colab packages are in the run ZIP.
- Input ZIP `inputs-urbanev-SZH-v1.zip`: SHA-256 `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`, downloaded and verified on Colab. Raw archives were not freshly reverified in this model task and were not changed.
- One full Source pass: **65,888 eligible examples, 1,030 Adam steps**, seed 42, batch 64, lr 0.001. Source elapsed pipeline time 57.395 seconds; training-batch mean normalized MAE 0.183827 (not a held-out accuracy score and not evidence of convergence).
- Two predeclared Development IDs **1001/1008**, separate 7/14/28-day initial prefixes and scalers, lambda 0/0.01, three adaptation epochs, epsilon 0.001, MLP width 64, last planned checkpoints. No favorable seed/checkpoint selection or Final use.
- **12 target runs** plus one Source run and one target resume verification: **14 recorded runs**. Score seven predeclared daily origins Dec 1–7, 2022, with a fixed adapted checkpoint; no online updates. Each target run emitted/scored 7/7 days (24 labels/day); no skipped/unscored days in this small interval. All selected targets had initial examples; actual source_checkpoint_only behavior is covered by fixtures, not a real target in this matrix.

## Actual Development smoke metrics

These are limited smoke measurements, not tuned baselines or statistical evidence that retention is superior. All settings/runs are retained, including worse results. MAE/RMSE are original hourly kWh.

| Target | Initial days | Lambda | Initial samples | MAE (kWh) | RMSE (kWh) | Scored days |
|---|---:|---:|---:|---:|---:|---:|
| 1001 | 7 | 0 | 6 | 4.527888 | 6.259606 | 7 |
| 1001 | 7 | 0.01 | 6 | 4.519618 | 6.261556 | 7 |
| 1008 | 7 | 0 | 6 | 6.925345 | 8.960232 | 7 |
| 1008 | 7 | 0.01 | 6 | 6.791009 | 8.802096 | 7 |
| 1001 | 14 | 0 | 13 | 4.360888 | 6.300590 | 7 |
| 1001 | 14 | 0.01 | 13 | 4.367822 | 6.330400 | 7 |
| 1008 | 14 | 0 | 13 | 6.125851 | 7.779523 | 7 |
| 1008 | 14 | 0.01 | 13 | 6.089308 | 7.733231 | 7 |
| 1001 | 28 | 0 | 27 | 4.266772 | 5.937324 | 7 |
| 1001 | 28 | 0.01 | 27 | 4.260274 | 5.948424 | 7 |
| 1008 | 28 | 0 | 27 | 6.386503 | 8.268012 | 7 |
| 1008 | 28 | 0.01 | 27 | 6.369066 | 8.231890 | 7 |

## Verification

- **139 tests PASS** (119 existing + 20 new) locally on Python 3.12/PyTorch 2.11.0, in Colab (8.454 seconds), and in initial Ubuntu/Windows CI [run 40206639838](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/40206639838). Final PR-head CI is tracked on the PR. Ruff lint/format, diff check, source catalog listing and local dependency check pass. Notebook cells compile; routine checks neither download raw data nor run real training.
- Tests cover shapes/last hidden state, encoder/head gradients, independent hand-calculated retention, source-only latent std, frozen reference, target isolation, lambda-zero equivalence, nonfinite-gradient failure before optimizer step, hash/prefix/role/scaler guards, all three budgets, future-label independence, source-only initialization, checkpoint reload and epoch-boundary resume.
- Actual GPU resume from target 1001/7-day/lambda0 epoch 1 reproduces uninterrupted model **and Adam state, CPU/CUDA/Python RNG states and prediction bytes exactly**. Checkpoint file hashes differ because run metadata/lineage differ; that is not a state discrepancy.
- After Drive persistence, the ZIP and matrix JSON were independently downloaded through the connector and their full SHA-256 verified locally. ZIP CRC passes; **192 per-file hashes** checked; all **14 final checkpoints** loaded with expected hashes using weights-only CPU reads. All target latent scales match the source scale. No local real-data optimizer/training run was executed.

## Artifacts and reconstruction

- [Team Drive folder](https://drive.google.com/drive/folders/1iaPJtwnKBbKFAZkuKnaNWyWJCOMWoZDL): executed notebook, run ZIP and full matrix JSON. Existing team folder access is inherited.
- [Run ZIP, 28,476,229 bytes](https://drive.google.com/file/d/1nTgjpoDwgY78KirC8T5aCcNhmpHDMBWl/view), SHA-256 `280a2c9c302313b174754a0749824a0ad4a4538663462f309cec85ff77797f75`. Includes epoch/final checkpoints and checksums, per-run bindings/configs/code hashes, logs, predictions, metrics, commands, pip freeze and `SHA256SUMS.txt`.
- [Full matrix JSON](https://drive.google.com/file/d/14tA8jtq3xqS8IRbikhEAXq03BE56ceyV/view), SHA-256 `d631791d6b0858a7764cc37444506c1eaee1ba33721664b9466359930f1e6e5d`.
- [Executed Colab notebook](https://colab.research.google.com/drive/1h0AlP8b_0TLx_zV4Zx13U4ANq9ch0X-E). The tracked notebook is a clean reusable template. The executed notebook retains a declined initial Drive-mount attempt and subsequent successful user-authorized mount/copy/flush; those storage attempts did not alter the completed training runs.
- Check out the recorded runtime commit, install recorded dependencies, verify DATA-v1 inputs, and run `python -m tools.issue19_colab_smoke --inputs-root /path/to/issue18-input-handoff-v1-20261019 --output /path/to/NEW-run`. For resume use the identical planned config, recorded runtime module hashes and epoch checkpoint with explicit SHA, into a new output directory. Never overwrite raw/shared artifacts.

## Remaining acceptance and comparison with Hung

Independent peer review and matched comparison with Hung are pending. Align MLP/future-calendar layout, latent std population/ddof, epsilon, optimizer initialization, batch order, seed/device, input/scaler identities, tolerances and checkpoint semantics before attributing discrepancies to an implementation bug. This report does not claim a comparison was already performed.

No controller, chronological online updating/audit, official hyperparameter lock, full baselines/ablations, >=3-seed experiment matrix or Final evaluation has been completed here. CHARGED training was not executed; the data-consumer fixture includes the AMS naive-clock profile only. Source one-epoch readiness does not establish adequate convergence. The existing upstream imputation, clock/availability and ID-versus-physical-site limitations remain; local tests do not establish strict-online data causality.
