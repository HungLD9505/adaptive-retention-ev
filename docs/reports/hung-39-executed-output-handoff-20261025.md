# Hung #39 executed code and output handoff — 2026-10-25

Status: **Development diagnostics completed; issue #39 not yet accepted**. This report inventories executed work and retained outputs. The recorded configuration is a diagnostic proposal. No Final/test result was used for model, hyperparameter, threshold or calibration selection. Data/input integration is a prerequisite delivered by the wider project; it is not claimed as a new #39 experiment.

## Code and protocol that were exercised

- The implementation under `experiments/hung_sprint2/` contains `model.py` (two-layer GRU and 24-hour forecast), `retention.py` (latent retention loss), `training.py` (Source and target training), `controller.py` (block decisions), `runner.py` (forecast, delayed score/update and resume), `checkpoint.py` and `_create_only.py` (state and create-only writes), `replay_inputs.py`, `evaluation.py`, `cli.py`, `selection.py` and `run_development.py` (predeclared matrix). The Colab and Kaggle notebooks call this implementation; they are not separate models.
- The input contract is 24 historical hours to 24 forecast hours, with masks and delayed labels separate. DATA-v1 UrbanEV SZH input ZIP is 151,254,390 bytes, SHA-256 `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`. The 7/14/28-day manifest hashes are recorded in [the Kaggle report](hung-39-kaggle-verification-20261025.md). The released input has explicit coverage limits.
- `development_config_v1.json` fixes seeds 7/11/19; Source one pass over 65,888 examples per budget/seed (2,059 batch-32 steps); target one pass when initial examples exist; replay 90 scheduled origins in 14-day blocks, with retention levels 0/0.1/0.2. This is **not an approved Final lock**. The v2 Development selection is predeclared from metadata. Verification pairs by budget are adaptation/source-only: 7d `2264/1050`, 14d `1153/2644`, 28d `1165/1188`. Representative entities were selected but not run as a full matrix.
- The exact executed Kaggle driver invocation is recorded in the archived `execution.log` and in [the notebook](../../experiments/hung_sprint2/kaggle_39_verification.ipynb):

  ```text
  /usr/bin/python3 -m experiments.hung_sprint2.run_development --input-base /kaggle/temp/hung-39-input/data/inputs/issue18-input-handoff-v1-20261019 --selection /kaggle/working/hung-sprint2-code/docs/reports/hung-development-selection-20261025-v2.json --config /kaggle/working/hung-sprint2-code/experiments/hung_sprint2/development_config_v1.json --output-root /kaggle/working/hung-39-kaggle-verification-20261025-v2 --phase verification --device cuda --budgets 7 14 28 --seeds 7 11 19 --execute
  ```

  Before that command, notebook cells checked the pinned Git bundle and commit, installed pinned requirements, probed CUDA/T4, downloaded or located the DATA-v1 ZIP, verified its size/SHA-256 and extracted it. The driver called the existing `source-smoke`, `target-smoke` and `replay-development` CLI stages. After execution, the final notebook cell verified all stage/checkpoint/journal hashes and wrote `kaggle_verification_summary.json`.

## Executed runs and retained outputs

| Execution | Scope actually completed | Output and integrity | Interpretation |
| --- | --- | --- | --- |
| 2026-10-23 local CPU diagnostic | One-pass Source and selected 7d entity replay; source-only `1871` created 75 forecasts, scored 38 days, MAE/RMSE 2.6175/3.5376 kWh. | Local ignored outputs and hashes in [diagnostic report](hung-development-diagnostic-20261023.md). A stopped seed-19 attempt is not counted as a successful run. | Narrow diagnostic only. |
| 2026-10-23 Colab Development | 3 seeds × 2 entities at 7d, each Source one pass. Adaptation `1001`: 59 created/52 scored; source-only `1871`: 75/38. | Run `hung-urbanev-7d-dev-multiseed-20261023T161534600069Z` on Drive with checkpoint, journal, manifest, summary and `handoff_complete.json`; notebook verified copied file hashes. [Colab report](hung-colab-development-multiseed-20261023.md). PyTorch was CPU even though the displayed runtime was T4. | Executed Development slice, not a GPU benchmark or cohort result. |
| 2026-10-25 local GPU verification | 7/14/28d × 3 seeds × 2 initialization strata; **63/63 stages**: 9 Source, 18 target, 18 replay-42, 18 replay-90. | `runs/hung-39-local-multibudget-20261025/` (ignored), 163 files/73,069,805 bytes, **99/99** checkpoint/journal hashes matched. RTX 3050 Ti; 19m51s wall time for this local matrix. [Local report](hung-39-local-verification-20261025.md). | Complete predeclared verification matrix locally; no Colab acceptance or full-cohort inference. |
| 2026-10-25 Kaggle T4 verification | Same matrix shape, pinned code commit `f52371823c1ddbf765eacfe2b89f7bcc0baf4869`, run `hung-39-kaggle-verification-20261025-v2`; **63/63 stages** completed. | `/kaggle/working/hung-39-kaggle-verification-20261025-v2/`; downloaded `results.zip` SHA-256 `567161f10c152fad06fd30a87ce5f1a8681a48cf119829df7c313aef2856e7a2`. The run folder has 165 files/72,613,895 bytes: 63 manifests, 9 Source checkpoints, 18 target checkpoints, 36 runner checkpoints, 36 event journals, matrix identity, execution log and summary. ZIP CRC, **99/99** archived hashes, 18 replay-summary rows and matrix identity passed independent local readback. [Kaggle report](hung-39-kaggle-verification-20261025.md). | Executed Development verification on CUDA/Tesla T4. Kaggle committed-version metadata has not been confirmed. |

The local and Kaggle matrices used different code commits and GPUs; their individual floating-point metrics are not asserted to be bitwise equal. The Kaggle private Input is a pinned code bundle, not the training dataset. Its SHA-256 is `e29f1526ae1e01dacaebe46dd947c6a1d2583749300f0894b2e204c7b5f8002b`. The DATA-v1 ZIP was separately downloaded and checked in the notebook. `results.zip` also contains a 178-file checkout of private code; retain the ZIP outside Git and share only the small report/fingerprints here.

### Kaggle replay-90 results

For the adaptation entities, live MAE/RMSE (kWh) by seed 7/11/19 were:

| Budget/entity | Created/scored per seed | MAE by seed | RMSE by seed |
| --- | ---: | --- | --- |
| 7d / `2264` | 90/90 | 3.639 / 3.580 / 3.622 | 5.889 / 5.847 / 5.851 |
| 14d / `1153` | 59/52 | 6.674 / 6.669 / 6.600 | 8.888 / 8.966 / 8.909 |
| 28d / `1165` | 59/52 | 10.339 / 10.538 / 10.360 | 13.561 / 13.751 / 13.639 |

The source-only entities `1050`, `2644` and `1188` created 90, 59 and 59 forecasts per seed, respectively, but scored **zero** days in these slices; MAE/RMSE are undefined. The 14/28d runs skipped 31 all-missing-history origins and had seven created forecasts without complete arrived labels. Different budgets use different entities and coverage; do not rank budgets or claim adaptive-retention benefit from these rows. Full-precision values remain in the archived manifests and summary.

## Fixes, checks and unresolved gates

- A replay resume defect at a block boundary was reproduced locally and fixed. The fresh 42→90 replay matched the uninterrupted run across 307 events, 59 forecasts, six decisions, forecast tensors and candidate weights. The failed diagnostic folder was preserved. A separate create-only checkpoint fallback addressed the observed Drive FUSE hard-link error; its POSIX fixture passed, while an actual new Colab Drive save has not been confirmed.
- Kaggle initially could not clone the private GitHub repository. The notebook now uses a private pinned Git bundle. A subsequent `git bundle verify` ordering error was fixed by verifying inside the cloned checkout. The Kaggle T4 run above then completed.
- After the notebook edit, `python -m tools.sources list` passed, `python -m unittest discover -s tests -v` passed 174 tests with one Windows skip, and `git diff --check` passed. Ruff check/format could not run in that local Python 3.13 environment because `ruff` was absent; earlier pinned-environment checks and CI are recorded in [the prior evidence index](hung-39-final-report-evidence-20261025.md). Documentation-only changes in this handoff do not substitute for a fresh code test run.
- Outstanding: confirm Kaggle Save Version #1 and its output URL; obtain team acceptance of Kaggle as a #39 execution platform; agree on the Development configuration and Source one-pass adequacy; run the predeclared representative set; compare with Quyền on common inputs; complete baseline/ablation work in its own scope; obtain independent PR review, CI at final heads and authorized integration. Do not close #39 or claim Final/test effectiveness from this handoff.

The current branch is `codex/39-completion`, with draft [PR #46](https://github.com/HungLD9505/adaptive-retention-ev/pull/46) toward `dev`. The dependent drafts are #42, #43 and #44. This report adds evidence to the branch; it is not a merge or acceptance decision.
