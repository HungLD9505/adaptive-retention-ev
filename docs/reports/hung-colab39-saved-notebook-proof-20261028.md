# #39 Colab owned-copy saved-output proof — 28 October 2026

**Scope:** read-only inspection of the saved [owned Colab notebook](https://colab.research.google.com/drive/1XqqAX-sAdxYEhtcUARgiIuDfffxN8pPb) in Chrome on 28 October. This report transcribes visible saved cell outputs. It is not a fresh training run, a downloaded Drive artifact, or an independent byte readback performed by this report. The notebook remains the source for the live output; its Drive folder is `MyDrive/hung-sprint2-runs/hung-39-verification-20261025T024400Z`.

## Run identity and observed environment

The notebook's configured run ID is `hung-39-verification-20261025T024400Z`, phase `verification`, device `cuda`, budgets 7/14/28 days, seeds 7/11/19 and code commit `f52371823c1ddbf765eacfe2b89f7bcc0baf4869`. It checks the Git bundle against SHA-256 `e29f1526ae1e01dacaebe46dd947c6a1d2583749300f0894b2e204c7b5f8002b`. The executed setup output states `torch probe 2.8.0+cu126 True device cuda`. A separate initial tensor probe displayed CUDA availability, a Tesla T4 and a CUDA tensor result. The Drive mount cell displayed `Mounted at /content/drive`.

The saved matrix identity output states schema `hung-sprint2-development-matrix-v1`, phase `verification`, device `cuda`, selection SHA-256 `273858dfb2bf949c297ecd209a5127a22966cb31703f7b2deefcf17323e13c91` and config SHA-256 `20cb0f0962af6e3f3781ef9bebdf03c162548e06894ae4b59ddc1d58be277ba0`. The run cell printed the matching Drive folder after the 151 MB input archive download and execution command returned.

## Saved audit output

| Check displayed by notebook | Saved output |
| --- | ---: |
| Source/Target/replay stage manifests | 9 / 18 / 36 |
| Completed stage/checkpoint SHA checks | 63 / 63 |
| Run files / total bytes | 163 / 72,529,254 |
| Empty files | 0 |
| Run manifests / checkpoints | 63 / 63 |
| Audit issues | 0 |
| Manifest statuses | 63 `completed` |
| Replay manifests with nonempty `metrics_kwh` | 36 / 36 |

The audit cell computes SHA-256 from each checkpoint file in the mounted Drive folder and compares it with its stage manifest, checks `status=completed` and the run ID, and requires nonzero checkpoint bytes. The inventory cell counts files and replay metrics. The saved output shown above is evidence that those checks ran in the Colab notebook; this report did not independently download and rehash all 72,529,254 bytes.

## Acceptance limits and next handoff

`metrics_kwh` being nonempty does not provide a reviewable aggregate MAE/RMSE table. This owned copy's numeric per-cell results and daily-error provenance are not yet exported into Git. Do not substitute the separate [23 October CPU-only Colab diagnostic](hung-colab-development-multiseed-20261023.md), [local representative](hung-39-experiments-results.md), or [Kaggle #39 verification](hung-39-kaggle-verification-20261025.md) scores for this run. A reviewer should receive an immutable manifest/metric export with file hashes or independently read the pinned Drive run before granting #39 technical acceptance. The Colab verification identity does not count toward the 782 new matched Development jobs.

**Commands/checks for this report:** Chrome Colab page inspection, saved output comparison against configured run ID/code/device, and local Markdown link validation. No notebook cell was rerun; no Drive files or Final/test labels were modified or opened. Peer disposition remains open.
