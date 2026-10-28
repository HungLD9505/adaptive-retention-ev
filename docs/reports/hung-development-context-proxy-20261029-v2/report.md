# Hùng Development context and proxy audit — 29 October 2026

**Scope: saved Development outputs only.** This CPU audit reads the immutable forecasts and labels retained in runner checkpoints. It does not retrain, call a provider, select a method or Final configuration, or use Final/test data. The [782-job ledger](../hung-development-782-job-ledger-20261028-v5.csv) is pinned at SHA-256 `bf1117c1d5fc0a902411cb6d850dca51e77802997c32880295ede20d8ac83004`; the frozen input ZIP is pinned at `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`.

## Verified support

| Saved source | Jobs/runs | Scorable | Zero-scored | Issued origins | Scored origins | Scored hours | Proof class |
|---|---:|---:|---:|---:|---:|---:|---|
| 40 new-job archives | 782 | 408 | 374 | 46,988 | 26,316 | 631,584 | Ledger job receipt, stage receipt, manifest, checkpoint and archive SHA/CRC |
| Historical Main review capsule | 69 | 36 | 33 | 4,146 | 2,322 | 55,728 | Capsule ledger and manifest/checkpoint SHA/CRC; no individual job receipts |
| **Combined Development coverage** | **851** | **444** | **407** | **51,134** | **28,638** | **687,312** | Mixed proof classes above |

For each new job, the tool checked the archive byte length and SHA, read receipt, stage receipt, manifest and checkpoint members through ZIP CRC, matched the ledger hashes, and matched checkpoint/input bindings to the pinned frozen input manifest and exact scheduled origin. It independently recomputed live MAE/RMSE from saved 24-hour forecasts and labels; each scorable job matched its saved manifest within `1e-4` kWh. Zero-scored runs remain null. The 69 historical Main checkpoints were checked against the independently read-back [review capsule](../hung-review-capsule-readback-20261027.md), capsule ledger manifest SHA, checkpoint SHA, input binding, origin set and saved live MAE/RMSE. Their [per-job binding table](../hung-development-main-context-20261029-v1/main_job_bindings.csv) explicitly labels the weaker receipt class.

## Context-sliced error

[New-job context error](context_error.csv) has 1,440 method × budget × weekday/weekend × local target-hour cells. [Historical Main context error](../hung-development-main-context-20261029-v1/main_context_error.csv) has 144 cells. Each row gives its own **scored-hour denominator**, MAE and RMSE in original kWh. The date category and hour refer to each target timestamp, not to a training or selection period. A scored 24-hour origin contributes one hour to each local target-hour cell. Unscored origins contribute nothing; neither missing labels nor their errors are imputed. These descriptive cells repeat stations and seeds and are not independent samples or a method ranking. The frozen Development window does not justify a season-generalization claim.

## Proxy signal and retention decision

[Proxy decision records](proxy_decisions.csv) preserve exact job, archive, receipt, manifest, checkpoint and input-manifest SHA bindings for **1,242 block decisions** (414 each for Source Error, Uncertainty and Drift). The signal is observed at a decision block; `selected_level` is the resulting retention level. Signal values are defined on different scales by proxy method and must not be pooled.

| Proxy method | Decisions | Numeric signal | Missing signal | Selected level 0.0 / 0.1 / 0.2 | Switch decisions |
|---|---:|---:|---:|---:|---:|
| Source Error | 414 | 168 | 246 | 207 / 192 / 15 | 54 |
| Uncertainty | 414 | 279 | 135 | 414 / 0 / 0 | 0 |
| Drift | 414 | 279 | 135 | 138 / 153 / 123 | 114 |

The missing values are explicit decision records, primarily `insufficient_days`; they are not zero proxy values. In this saved Development cohort, Uncertainty has no variation in selected retention, so an association between its signal and selected level cannot be estimated. Source Error and Drift have variation, but these observed associations are policy decisions under their configured thresholds, not evidence that a proxy caused lower forecast error. The table does not condition method or threshold selection on these Development results.

## Reproduce and checks

Run from the repository root with Python/Torch installed and **new** output directories:

```powershell
python -m tools.hung_development_context_proxy --root . --ledger-sha256 bf1117c1d5fc0a902411cb6d850dca51e77802997c32880295ede20d8ac83004 --input-sha256 2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7 --output-dir docs/reports/context-proxy-reproduction-NEW
python -m tools.hung_development_main_context --root . --input-sha256 2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7 --output-dir docs/reports/main-context-reproduction-NEW
python -m unittest tests.test_hung_development_context_proxy -v
```

The commands are create-only and refuse a changed pinned source. Output SHA-256 values: `context_error.csv` `016aeda5ce9ebd55b06b57a749a55d6efa4e116b944ddf986ee1677b1f5dddbf`; `proxy_decisions.csv` `d69e66be048ed967784544b7e6a7d327fb21aa280c5f2968574e98d9ef4253fe`; new-job `summary.json` `924206d989a32adf647077d67084b51d57d5d2fa27a006bd282fccc2b80e45fd`; historical `main_context_error.csv` `836f401108745dc28d57ff4a4999bffa9d51dde8b91aa02a78df2b113f11ea6b`; `main_job_bindings.csv` `bb7a9f2c5865b8aab807e4323a7fa2276793d90d89808ebadca925d498ce928b`; historical `summary.json` `3340e54e6d2bdc75b1c5d0515ec95b5c6a6b701a09cd16a0bd94e2f99ca52e4e`.

Both full CPU scans completed with exact scored-count and saved live-metric parity. Three focused offline tests, Ruff check/format, `py_compile` and `git diff --check` passed. Independent scientific review, Block7/parity decisions and Final lock remain separate gates.
