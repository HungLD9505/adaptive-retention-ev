# #39 Kaggle Development verification — 2026-10-25

Status: **downloaded output independently checked; Kaggle version status not confirmed**. This is a diagnostic execution of the predeclared verification set on Kaggle, pending persisted-version readback and team acceptance of Kaggle as the execution platform. It does not use Final/test data or establish model effectiveness.

## Identity and executed checks

- Notebook: [Hung 39 Development verification T4](https://www.kaggle.com/code/hungluongduc/hung-39-development-verification-t4). Run ID: `hung-39-kaggle-verification-20261025-v2`. Output path: `/kaggle/working/hung-39-kaggle-verification-20261025-v2/`.
- Code bundle: private [Kaggle dataset](https://www.kaggle.com/datasets/hungluongduc/hung-39-pinned-code-bundle-f523718-20261025) containing `hung-39-f523718.bundle`, SHA-256 `e29f1526ae1e01dacaebe46dd947c6a1d2583749300f0894b2e204c7b5f8002b`. Code commit: `f52371823c1ddbf765eacfe2b89f7bcc0baf4869`. The notebook fix moves `git bundle verify` into the cloned repository; Kaggle verified the bundle and commit before training.
- DATA-v1 UrbanEV ZIP was downloaded in the Kaggle session, then verified at 151,254,390 bytes and SHA-256 `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`. The 7/14/28-day input manifest SHA-256 values are `fd1b5d1767e94a3e5c6f62447d446e1f13859b823c5fe14c51b5055d8e67169c`, `66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9`, and `cdd43152bbda3de9f468938262a8bf00e041a9f264cf29051b71d06e788beadd`.
- `matrix_identity.json` SHA-256: `8a603e4034f2231708cb1d7c930fde92a8f2b7132d4931e4b372a871e2fb260f`. It records selection SHA-256 `273858dfb2bf949c297ecd209a5127a22966cb31703f7b2deefcf17323e13c91`, config SHA-256 `20cb0f0962af6e3f3781ef9bebdf03c162548e06894ae4b59ddc1d58be277ba0`, budgets 7/14/28, seeds 7/11/19, phase `verification`, and device `cuda`.
- Kaggle reported PyTorch `2.8.0+cu126`, CUDA available, and Tesla T4 (15,360 MiB). All **63/63** stage manifests completed: 9 Source, 18 target, 18 replay-42, and 18 replay-90. The notebook recomputed and matched **99/99** checkpoint and journal hashes.
- The downloaded `results.zip` is 79,122,558 bytes with SHA-256 `567161f10c152fad06fd30a87ce5f1a8681a48cf119829df7c313aef2856e7a2`. ZIP CRC passed. Its run folder contains **165 files, 72,613,895 uncompressed bytes** (nine bytes below the earlier draft folder count). The summary itself remains identical at 19,934 bytes and SHA-256 `9dd8ee6f55ae4fd65c16f04ed33e221af16496a71f978ff273904fce31f75487`.
- Independent readback directly from the ZIP found **63 completed run manifests**, exactly 9 Source, 18 target, 18 replay-42 and 18 replay-90. All **99 checkpoint/event-journal SHA-256 references** matched archived bytes; all 18 replay-90 summary rows matched their manifests, and the matrix identity SHA-256 matched the summary. The archive also contains a `hung-sprint2-code/` checkout (178 files). Keep this archive outside Git; the report and fingerprints are the shareable evidence.

## Replay-90 outcomes

The table records live forecast error only for the adaptation entity with arrived complete labels. `Created/scored` counts forecast days out of 90 requested origins. Values are rounded here; the Kaggle manifests contain full precision.

| Budget | Seed | Adaptation entity | Created/scored | Live MAE / RMSE (kWh) | Source-only entity | Created/scored |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 7d | 7 | 2264 | 90/90 | 3.639 / 5.889 | 1050 | 90/0 |
| 7d | 11 | 2264 | 90/90 | 3.580 / 5.847 | 1050 | 90/0 |
| 7d | 19 | 2264 | 90/90 | 3.622 / 5.851 | 1050 | 90/0 |
| 14d | 7 | 1153 | 59/52 | 6.674 / 8.888 | 2644 | 59/0 |
| 14d | 11 | 1153 | 59/52 | 6.669 / 8.966 | 2644 | 59/0 |
| 14d | 19 | 1153 | 59/52 | 6.600 / 8.909 | 2644 | 59/0 |
| 28d | 7 | 1165 | 59/52 | 10.339 / 13.561 | 1188 | 59/0 |
| 28d | 11 | 1165 | 59/52 | 10.538 / 13.751 | 1188 | 59/0 |
| 28d | 19 | 1165 | 59/52 | 10.360 / 13.639 | 1188 | 59/0 |

The nine source-checkpoint-only runs created forecasts but scored **zero** days. Their MAE/RMSE are undefined; no value is imputed. The 14/28-day runs skipped 31 origins for all-missing history and had 7 created days without complete arrived labels. Budgets use different selected entities and coverage, so these rows are not a budget ranking. Metrics differ slightly from the earlier local GPU diagnostic; code commit and hardware differ, and bitwise equivalence was not established.

## Fix, local checks, and remaining gates

- The first Kaggle attempt could not clone a private GitHub repository. The corrected notebook uses the private code bundle. After attaching it, the previously unexecuted `git bundle verify` order was fixed: verifying outside a repository failed locally with `need a repository to verify a bundle`; verifying inside the cloned checkout passed. All notebook code cells compiled.
- Local checks after the notebook edit: `python -m tools.sources list` passed; `python -m unittest discover -s tests -v` passed 174 tests with one Windows skip; `git diff --check` passed. `python -m ruff check .` and `python -m ruff format --check .` could not run in the local Python 3.13 environment because `ruff` is not installed there. The Kaggle draft run itself completed all 63 stages and 99 hash checks.
- Version #1, named `Hung39 T4 verification 63-stage output`, was launched with **Save & Run All (Commit)** to persist output from a fresh Kaggle run. The downloaded ZIP proves its own contents, but does not carry Kaggle version metadata; the version result, final URL, and whether this ZIP came from that committed version remain unverified. Keep the completed draft session until the version is verified.
- This is still the selected verification set, not the representative Development set or full cohort. Team acceptance of Kaggle in place of Colab, cross-implementation comparison with Quyền, independent PR review, and dependency integration remain open for #39. No Final/test set was used for model or threshold selection.
