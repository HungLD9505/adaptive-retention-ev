# Provisional Development results

Provisional; full coverage and independent review required

This v5 snapshot combines 291 local/historical records from the SHA-pinned v4 collections with independently read-back Kaggle export batches00–02 (240 records). It supersedes v4 only for available Development metrics; batches03–06 (320 planned Kaggle jobs) are absent. The 69 historical Main records are anchors rather than newly executed Development jobs. The underlying daily-error result and collection spec remain in ignored repository `.cache` paths; their hashes are recorded below. The tracked [batch00–02 readback checkpoint](../hung-cpu-export-readback-00-02-20261028.md) records saved Kaggle versions, payload SHA and limits. Do not use this partial matrix to select Final settings.

Recomputed runs: **531**; scorable: **278**; zero scored: **253**.

Exact daily label-hash intersection within station/seed; equal seed means within station, then equal station means within each budget. Disjoint expected job sets; no global ranking or Final selection.

Only already-arrived labels saved with issued Development forecasts are scored. Each checkpoint, manifest and supporting proof is SHA-checked. Historical unmatched runs are excluded. This report does not select configurations or authorize Final.

| Method | Runs | Scorable | Scored/requested days |
|---|---:|---:|---:|
| block28 | 69 | 36 | 2322/6210 |
| drift | 69 | 36 | 2322/6210 |
| fixed_retention | 69 | 36 | 2322/6210 |
| frozen_source | 69 | 36 | 2322/6210 |
| full_finetuning | 45 | 23 | 1383/4050 |
| main | 69 | 36 | 2322/6210 |
| online_best | 1 | 1 | 52/90 |
| parameter_retention | 1 | 1 | 52/90 |
| seasonal_naive | 12 | 7 | 477/1080 |
| source_error | 69 | 36 | 2322/6210 |
| target_only | 1 | 1 | 90/90 |
| uncertainty | 57 | 29 | 1884/5130 |

Each method/reference table uses its own paired day intersection. Different rows can have different cohorts and must not be interpreted as a global performance ranking. Cells with missing labels or unequal input/initialization/labels remain blocked. Full baseline/ablation, seed and budget coverage plus independent review are required.

| Budget | Method | Reference | Stations | Min seeds | MAE | RMSE | Reference MAE | MAE gain | Worse than reference | Negative transfer vs Target-only |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 7 | block28 | main | 3 | 3 | 5.207440 | 7.544727 | 5.206837 | -0.000604 | 0.667 | n/a |
| 7 | block28 | target_only | 1 | 1 | 3.616167 | 5.892761 | 5.029901 | 1.413734 | 0.000 | 0.000 |
| 7 | drift | main | 3 | 3 | 5.139197 | 7.438881 | 5.206837 | 0.067639 | 0.333 | n/a |
| 7 | drift | target_only | 1 | 1 | 3.571745 | 5.838736 | 5.029901 | 1.458156 | 0.000 | 0.000 |
| 7 | fixed_retention | main | 3 | 3 | 5.201225 | 7.526943 | 5.206837 | 0.005612 | 0.333 | n/a |
| 7 | fixed_retention | target_only | 1 | 1 | 3.579039 | 5.840999 | 5.029901 | 1.450862 | 0.000 | 0.000 |
| 7 | frozen_source | main | 3 | 3 | 5.283687 | 7.901793 | 5.206837 | -0.076850 | 1.000 | n/a |
| 7 | frozen_source | target_only | 1 | 1 | 3.712148 | 6.198997 | 5.029901 | 1.317753 | 0.000 | 0.000 |
| 7 | main | target_only | 1 | 1 | 3.661227 | 5.911514 | 5.029901 | 1.368674 | 0.000 | 0.000 |
| 7 | seasonal_naive | main | 3 | 1 | 7.313067 | 10.226014 | 5.244938 | -2.068129 | 1.000 | n/a |
| 7 | seasonal_naive | target_only | 1 | 1 | 4.627778 | 7.102126 | 5.029901 | 0.402123 | 0.000 | n/a |
| 7 | source_error | main | 3 | 3 | 5.187037 | 7.504378 | 5.206837 | 0.019799 | 0.333 | n/a |
| 7 | source_error | target_only | 1 | 1 | 3.576274 | 5.838772 | 5.029901 | 1.453627 | 0.000 | 0.000 |
| 7 | target_only | main | 1 | 1 | 5.029901 | 6.262198 | 3.661227 | -1.368674 | 1.000 | n/a |
| 7 | uncertainty | main | 3 | 3 | 5.092915 | 7.338746 | 5.206837 | 0.113921 | 0.000 | n/a |
| 7 | uncertainty | target_only | 1 | 1 | 3.542390 | 5.700570 | 5.029901 | 1.487511 | 0.000 | 0.000 |
| 14 | block28 | main | 4 | 3 | 5.235566 | 7.169242 | 5.232235 | -0.003331 | 0.750 | n/a |
| 14 | drift | main | 4 | 3 | 5.147371 | 7.059111 | 5.232235 | 0.084864 | 0.250 | n/a |
| 14 | fixed_retention | main | 4 | 3 | 5.190855 | 7.120801 | 5.232235 | 0.041380 | 0.250 | n/a |
| 14 | frozen_source | main | 4 | 3 | 5.491232 | 7.618020 | 5.232235 | -0.258997 | 0.750 | n/a |
| 14 | full_finetuning | main | 4 | 3 | 5.191221 | 7.093668 | 5.232235 | 0.041013 | 0.750 | n/a |
| 14 | online_best | main | 1 | 1 | 6.548480 | 8.831341 | 6.690553 | 0.142074 | 0.000 | n/a |
| 14 | source_error | main | 4 | 3 | 5.188813 | 7.120097 | 5.232235 | 0.043422 | 0.250 | n/a |
| 14 | uncertainty | main | 4 | 1 | 5.212997 | 7.119405 | 5.264968 | 0.051972 | 0.250 | n/a |
| 28 | block28 | main | 5 | 3 | 5.579476 | 7.597162 | 5.598521 | 0.019045 | 0.200 | n/a |
| 28 | drift | main | 5 | 3 | 5.564866 | 7.581545 | 5.598521 | 0.033656 | 0.200 | n/a |
| 28 | fixed_retention | main | 5 | 3 | 5.558037 | 7.555955 | 5.598521 | 0.040484 | 0.000 | n/a |
| 28 | frozen_source | main | 5 | 3 | 5.979928 | 8.200498 | 5.598521 | -0.381406 | 0.800 | n/a |
| 28 | full_finetuning | main | 5 | 2 | 5.574486 | 7.616467 | 5.583937 | 0.009451 | 0.600 | n/a |
| 28 | parameter_retention | main | 1 | 1 | 10.303079 | 13.562555 | 10.381852 | 0.078773 | 0.000 | n/a |
| 28 | seasonal_naive | main | 4 | 1 | 6.606611 | 8.948342 | 4.432446 | -2.174165 | 1.000 | n/a |
| 28 | source_error | main | 5 | 3 | 5.565872 | 7.580693 | 5.598521 | 0.032650 | 0.000 | n/a |
| 28 | uncertainty | main | 5 | 3 | 5.578790 | 7.590110 | 5.598521 | 0.019731 | 0.200 | n/a |

Blocked pair reasons: `{"no_paired_scored_days": 220}`.

Full result SHA: `fd1dfaf1279e5754628900fbb52d5e1041c328b77e89732aa67947b469e99a89`.
Catalog SHA: `6b997a74d83b50119918476d9c3d1d5eb6470eb49016684e5c816e136106f377`.

Runtime fields in the full JSON identify the device, final-stage duration and cumulative runner/proxy costs. Final-stage duration excludes earlier continuation/init stages; these values must not be presented as whole-job provider time. No independent acceptance, #39 completion or Final-lock claim is made.
