# Hung provider phase: complete available result tables (28 October 2026)
**Evidence boundary.** This is a detailed rendering of saved Development and #39 evidence, not a new run, Final evaluation or scientific acceptance. See the [phase status report](hung-provider-phase-results-20261028.md), [method implementation](hung-39-method-implementation.md), [allocation](evidence/hung-development-allocation-20261027-v1.json), and [Hybrid v4 provenance](hung-hybrid-v4-provenance-20261027.json). A dash means undefined/missing, never zero error.
## Execution, method and result identities
The forecast target is the next 24 hourly station-energy kWh values. Hung uses a 2-layer GRU with hidden width 64 and 41,696 parameters, Source pretraining (65,888 eligible examples, 2,059 Adam steps per Source stage), one-pass Target initialization, and chronological prequential replay. Candidate retention weights are 0/0.1/0.2; the recorded controller evaluates candidates at 14-day blocks using complete arrived labels, at least five paired days and 100 day-block bootstrap resamples. Full protocol and data limits are in the linked method report. These are executed diagnostic settings, not optimized claims. Final/test labels were not used for model, threshold or calibration selection.
The frozen new-job allocation is pilot 6 + local CUDA 216 + Kaggle 560 = **782**, all execution-complete with independent remote archive SHA/CRC readback. Historical Main 69 and historical Block7 69 are separate. Archive verification does not imply that all 782 per-run metrics or manifests have been consolidated. The latest authenticated portable metric snapshot is **Hybrid v4: 371 unique physical runs (Main 69 + local 222 + Kaggle 80), 196 scorable, 175 zero-scored**. Its cumulative predecessors have fewer runs and must not be summed. Batch00 exported 80 jobs; remaining exports and the 782-row job-to-artifact ledger have not been verified in Git.
## #39 local representative run: all 69 cells
The [source evidence JSON](hung-39-representative-local-20261025-evidence.json) (SHA-256 `ad10cc8ab94b3c2e3c2b35b359489263b77e238f404ceac7bb739956c302362b`) records 216/216 stages, 6,210 requested origins, 4,146 issued forecasts, 2,322 complete-label scored days, 36 numeric and 33 null cells, 32 switches and 382 keeps. It passed 354/354 checkpoint/journal SHA checks and metric recomputation to maximum difference 3.55e-15 kWh. [Full precision and counters for all 69 cells](hung-39-representative-local-20261025-all-69-cells.csv) are derived directly from that JSON. The table below retains each original cell; local MAE/RMSE are per cell, and different entities/budgets are not directly ranked.
| Budget | Entity | Seed | Init | Issued | Scored | MAE kWh | RMSE kWh | Switch | Keep |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 7 | 1405 | 7 | target_initial_adaptation | 90 | 89 | 5.9140 | 8.1486 | 3 | 3 |
| 7 | 2264 | 7 | target_initial_adaptation | 90 | 90 | 3.6612 | 5.9115 | 1 | 5 |
| 7 | 2452 | 7 | target_initial_adaptation | 59 | 52 | 6.1596 | 8.6121 | 1 | 5 |
| 7 | 1050 | 7 | source_checkpoint_only | 90 | 0 | — | — | 0 | 6 |
| 7 | 1200 | 7 | source_checkpoint_only | 59 | 0 | — | — | 0 | 6 |
| 7 | 2447 | 7 | source_checkpoint_only | 59 | 0 | — | — | 0 | 6 |
| 7 | 1405 | 11 | target_initial_adaptation | 90 | 89 | 5.9535 | 8.2591 | 2 | 4 |
| 7 | 2264 | 11 | target_initial_adaptation | 90 | 90 | 3.5728 | 5.8459 | 2 | 4 |
| 7 | 2452 | 11 | target_initial_adaptation | 59 | 52 | 6.0384 | 8.4713 | 0 | 6 |
| 7 | 1050 | 11 | source_checkpoint_only | 90 | 0 | — | — | 0 | 6 |
| 7 | 1200 | 11 | source_checkpoint_only | 59 | 0 | — | — | 0 | 6 |
| 7 | 2447 | 11 | source_checkpoint_only | 59 | 0 | — | — | 0 | 6 |
| 7 | 1405 | 19 | target_initial_adaptation | 90 | 89 | 5.8376 | 8.1280 | 1 | 5 |
| 7 | 2264 | 19 | target_initial_adaptation | 90 | 90 | 3.6329 | 5.8552 | 2 | 4 |
| 7 | 2452 | 19 | target_initial_adaptation | 59 | 52 | 6.0915 | 8.5960 | 0 | 6 |
| 7 | 1050 | 19 | source_checkpoint_only | 90 | 0 | — | — | 0 | 6 |
| 7 | 1200 | 19 | source_checkpoint_only | 59 | 0 | — | — | 0 | 6 |
| 7 | 2447 | 19 | source_checkpoint_only | 59 | 0 | — | — | 0 | 6 |
| 14 | 1405 | 7 | target_initial_adaptation | 90 | 89 | 5.9140 | 8.1486 | 3 | 3 |
| 14 | 1987 | 7 | target_initial_adaptation | 3 | 0 | — | — | 0 | 6 |
| 14 | 2152 | 7 | target_initial_adaptation | 59 | 52 | 6.3068 | 7.9963 | 0 | 6 |
| 14 | 1153 | 7 | target_initial_adaptation | 59 | 52 | 6.6906 | 8.9674 | 1 | 5 |
| 14 | 1693 | 7 | target_initial_adaptation | 59 | 52 | 2.2810 | 3.8252 | 1 | 5 |
| 14 | 2644 | 7 | source_checkpoint_only | 59 | 0 | — | — | 0 | 6 |
| 14 | 2613 | 7 | source_checkpoint_only | 59 | 0 | — | — | 0 | 6 |
| 14 | 1025 | 7 | source_checkpoint_only | 43 | 0 | — | — | 0 | 6 |
| 14 | 1405 | 11 | target_initial_adaptation | 90 | 89 | 5.9535 | 8.2591 | 2 | 4 |
| 14 | 1987 | 11 | target_initial_adaptation | 3 | 0 | — | — | 0 | 6 |
| 14 | 2152 | 11 | target_initial_adaptation | 59 | 52 | 6.1825 | 7.8770 | 0 | 6 |
| 14 | 1153 | 11 | target_initial_adaptation | 59 | 52 | 6.5977 | 8.8909 | 1 | 5 |
| 14 | 1693 | 11 | target_initial_adaptation | 59 | 52 | 2.2700 | 3.7417 | 1 | 5 |
| 14 | 2644 | 11 | source_checkpoint_only | 59 | 0 | — | — | 0 | 6 |
| 14 | 2613 | 11 | source_checkpoint_only | 59 | 0 | — | — | 0 | 6 |
| 14 | 1025 | 11 | source_checkpoint_only | 43 | 0 | — | — | 0 | 6 |
| 14 | 1405 | 19 | target_initial_adaptation | 90 | 89 | 5.8376 | 8.1280 | 1 | 5 |
| 14 | 1987 | 19 | target_initial_adaptation | 3 | 0 | — | — | 0 | 6 |
| 14 | 2152 | 19 | target_initial_adaptation | 59 | 52 | 6.0419 | 7.6516 | 0 | 6 |
| 14 | 1153 | 19 | target_initial_adaptation | 59 | 52 | 6.4912 | 8.7998 | 1 | 5 |
| 14 | 1693 | 19 | target_initial_adaptation | 59 | 52 | 2.2201 | 3.6915 | 0 | 6 |
| 14 | 2644 | 19 | source_checkpoint_only | 59 | 0 | — | — | 0 | 6 |
| 14 | 2613 | 19 | source_checkpoint_only | 59 | 0 | — | — | 0 | 6 |
| 14 | 1025 | 19 | source_checkpoint_only | 43 | 0 | — | — | 0 | 6 |
| 28 | 1987 | 7 | target_initial_adaptation | 3 | 0 | — | — | 0 | 6 |
| 28 | 2152 | 7 | target_initial_adaptation | 59 | 52 | 6.0891 | 7.6942 | 0 | 6 |
| 28 | 2005 | 7 | target_initial_adaptation | 90 | 90 | 4.9290 | 6.5857 | 1 | 5 |
| 28 | 2472 | 7 | target_initial_adaptation | 59 | 52 | 4.5640 | 6.5244 | 0 | 6 |
| 28 | 1165 | 7 | target_initial_adaptation | 59 | 52 | 10.3819 | 13.5741 | 1 | 5 |
| 28 | 2633 | 7 | target_initial_adaptation | 59 | 52 | 2.1477 | 3.7283 | 1 | 5 |
| 28 | 1188 | 7 | source_checkpoint_only | 59 | 0 | — | — | 0 | 6 |
| 28 | 1408 | 7 | source_checkpoint_only | 58 | 0 | — | — | 0 | 6 |
| 28 | 1251 | 7 | source_checkpoint_only | 58 | 0 | — | — | 0 | 6 |
| 28 | 1987 | 11 | target_initial_adaptation | 3 | 0 | — | — | 0 | 6 |
| 28 | 2152 | 11 | target_initial_adaptation | 59 | 52 | 6.1394 | 7.8413 | 0 | 6 |
| 28 | 2005 | 11 | target_initial_adaptation | 90 | 90 | 4.8313 | 6.5431 | 1 | 5 |
| 28 | 2472 | 11 | target_initial_adaptation | 59 | 52 | 4.5537 | 6.5741 | 1 | 5 |
| 28 | 1165 | 11 | target_initial_adaptation | 59 | 52 | 10.5237 | 13.7302 | 1 | 5 |
| 28 | 2633 | 11 | target_initial_adaptation | 59 | 52 | 2.1088 | 3.6235 | 0 | 6 |
| 28 | 1188 | 11 | source_checkpoint_only | 59 | 0 | — | — | 0 | 6 |
| 28 | 1408 | 11 | source_checkpoint_only | 58 | 0 | — | — | 0 | 6 |
| 28 | 1251 | 11 | source_checkpoint_only | 58 | 0 | — | — | 0 | 6 |
| 28 | 1987 | 19 | target_initial_adaptation | 3 | 0 | — | — | 0 | 6 |
| 28 | 2152 | 19 | target_initial_adaptation | 59 | 52 | 5.9278 | 7.5015 | 0 | 6 |
| 28 | 2005 | 19 | target_initial_adaptation | 90 | 90 | 4.8646 | 6.5332 | 1 | 5 |
| 28 | 2472 | 19 | target_initial_adaptation | 59 | 52 | 4.4566 | 6.5140 | 1 | 5 |
| 28 | 1165 | 19 | target_initial_adaptation | 59 | 52 | 10.3204 | 13.5265 | 1 | 5 |
| 28 | 2633 | 19 | target_initial_adaptation | 59 | 52 | 2.1398 | 3.6579 | 0 | 6 |
| 28 | 1188 | 19 | source_checkpoint_only | 59 | 0 | — | — | 0 | 6 |
| 28 | 1408 | 19 | source_checkpoint_only | 58 | 0 | — | — | 0 | 6 |
| 28 | 1251 | 19 | source_checkpoint_only | 58 | 0 | — | — | 0 | 6 |
## #39 Kaggle T4 verification: all scored adaptation rows
This [separate Kaggle verification](hung-39-kaggle-verification-20261025.md) completed 63/63 stages, 99/99 hash checks and 18 cells. Its 79,122,558-byte ZIP passed SHA-256 `567161f10c152fad06fd30a87ce5f1a8681a48cf119829df7c313aef2856e7a2` and CRC. The source-only entity in each row issued forecasts but scored zero complete-label days, so its MAE/RMSE is undefined. The downloaded ZIP is not independently bound to saved version 1.
| Budget | Seed | Adapt entity | Issued/scored | MAE kWh | RMSE kWh | Source-only entity | Issued/scored |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 7d | 7 | 2264 | 90/90 | 3.639 | 5.889 | 1050 | 90/0 |
| 7d | 11 | 2264 | 90/90 | 3.580 | 5.847 | 1050 | 90/0 |
| 7d | 19 | 2264 | 90/90 | 3.622 | 5.851 | 1050 | 90/0 |
| 14d | 7 | 1153 | 59/52 | 6.674 | 8.888 | 2644 | 59/0 |
| 14d | 11 | 1153 | 59/52 | 6.669 | 8.966 | 2644 | 59/0 |
| 14d | 19 | 1153 | 59/52 | 6.600 | 8.909 | 2644 | 59/0 |
| 28d | 7 | 1165 | 59/52 | 10.339 | 13.561 | 1188 | 59/0 |
| 28d | 11 | 1165 | 59/52 | 10.538 | 13.751 | 1188 | 59/0 |
| 28d | 19 | 1165 | 59/52 | 10.360 | 13.639 | 1188 | 59/0 |
## Colab result identities
The [23 October Colab Development diagnostic](hung-colab-development-multiseed-20261023.md) ran Torch `2.8.0+cpu` despite a T4 runtime label. Its six measured rows follow. Means are within entity across three seeds only: entity 1001 MAE 4.2836 kWh (52 scored days per seed); entity 1871 MAE 2.6487 kWh (38 days per seed). They are not a GPU benchmark or same-run comparison with #39.
| Entity | Seed | Issued | Scored days | MAE kWh | RMSE kWh |
| --- | --- | --- | --- | --- | --- |
| 1001 | 7 | 59 | 52 | 4.3940 | 6.4309 |
| 1001 | 11 | 59 | 52 | 4.2122 | 6.1889 |
| 1001 | 19 | 59 | 52 | 4.2446 | 6.3808 |
| 1871 | 7 | 75 | 38 | 2.6776 | 3.5717 |
| 1871 | 11 | 75 | 38 | 2.6051 | 3.4819 |
| 1871 | 19 | 75 | 38 | 2.6635 | 3.5795 |
The later [#39 Colab owned copy](https://colab.research.google.com/drive/1XqqAX-sAdxYEhtcUARgiIuDfffxN8pPb), run `hung-39-verification-20261025T024400Z`, code `f52371823c1ddbf765eacfe2b89f7bcc0baf4869`, had actual CUDA and a read-only Drive audit showing 63/63 completed manifests, 63/63 checkpoint SHA checks, 163 nonempty files and 36/36 replay manifests with nonempty kWh metrics. No numeric aggregate from this new copy is tracked in Git, so the older CPU values above cannot be assigned to it. Its full Drive evidence still needs tracked export.
## Hybrid v4 logical coverage by family and budget
This table renders the [authenticated coverage JSON](evidence/hung-hybrid371-coverage-20261027.json). Budget cells show matched/scorable; each family requires 69 logical cells. Aliases reuse physical artifacts, so physical column values must not be summed. Missingness by exact cell and seed is in the JSON.
| Family | Matched | Scorable | Physical | 7d matched/scorable | 14d matched/scorable | 28d matched/scorable |
| --- | --- | --- | --- | --- | --- | --- |
| main | 69 | 36 | 69 | 18/9 | 24/12 | 27/15 |
| seasonal_naive | 36 | 21 | 12 | 18/9 | 0/0 | 18/12 |
| target_only | 1 | 1 | 1 | 1/1 | 0/0 | 0/0 |
| frozen_source | 1 | 1 | 1 | 0/0 | 1/1 | 0/0 |
| full_finetuning | 0 | 0 | 0 | 0/0 | 0/0 | 0/0 |
| fixed_retention | 22 | 12 | 22 | 0/0 | 22/12 | 0/0 |
| online_best | 1 | 1 | 1 | 0/0 | 1/1 | 0/0 |
| source_error | 69 | 36 | 69 | 18/9 | 24/12 | 27/15 |
| uncertainty | 57 | 29 | 57 | 18/9 | 12/5 | 27/15 |
| drift | 69 | 36 | 69 | 18/9 | 24/12 | 27/15 |
| without_confidence | 1 | 1 | 1 | 0/0 | 1/1 | 0/0 |
| fixed_lambda | 22 | 12 | 22 | 0/0 | 22/12 | 0/0 |
| parameter_retention | 1 | 1 | 1 | 0/0 | 0/0 | 1/1 |
| block7 | 0 | 0 | 0 | 0/0 | 0/0 | 0/0 |
| block28 | 69 | 36 | 69 | 18/9 | 24/12 | 27/15 |
| no_source | 0 | 0 | 0 | 0/0 | 0/0 | 0/0 |
The required full-finetuning, no-source and fair Block7 matched cells are absent in this snapshot; 69 historical Block7 runs remain unmatched pending reviewer disposition. Full method/cohort coverage and adverse/null analysis are open.
## Hybrid v4: all 25 paired comparison rows
This table transcribes the [full precision paired CSV](hung-development-hybrid-20261027-v4/paired.csv) (SHA-256 `98ed55f6a295e4a1be6a8b2b5e8523357044431f94aaf206b0737b410048739a`). Each row compares the method and reference on exact common scored-day label hashes, with seed means within station and equal station weight. `Gain` is reference MAE minus method MAE; positive means lower method MAE for that *row-specific observed cohort*. `NTR` is worse-than-reference station fraction; `negative transfer` and `transfer gain` are defined only for target-only-reference rows where source transfer applies. Null fields remain null. There are 166 paired cells and 142 candidate pairs lacking paired scored days; no global ranking follows from these rows.
| Budget | Method | Reference | Stations | Min seeds | Method MAE | Ref MAE | MAE gain | Relative gain | NTR | Negative transfer | Transfer gain |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 7d | block28 | main | 3 | 3 | 5.207440 | 5.206837 | -0.000604 | -0.000116 | 0.667 | — | — |
| 7d | block28 | target_only | 1 | 1 | 3.616167 | 5.029901 | 1.413734 | 0.281066 | 0.000 | 0.000 | 0.281066 |
| 7d | drift | main | 3 | 3 | 5.139197 | 5.206837 | 0.067639 | 0.012990 | 0.333 | — | — |
| 7d | drift | target_only | 1 | 1 | 3.571745 | 5.029901 | 1.458156 | 0.289898 | 0.000 | 0.000 | 0.289898 |
| 7d | main | target_only | 1 | 1 | 3.661227 | 5.029901 | 1.368674 | 0.272107 | 0.000 | 0.000 | 0.272107 |
| 7d | seasonal_naive | main | 3 | 1 | 7.313067 | 5.244938 | -2.068129 | -0.394309 | 1.000 | — | — |
| 7d | seasonal_naive | target_only | 1 | 1 | 4.627778 | 5.029901 | 0.402123 | 0.079947 | 0.000 | — | — |
| 7d | source_error | main | 3 | 3 | 5.187037 | 5.206837 | 0.019799 | 0.003803 | 0.333 | — | — |
| 7d | source_error | target_only | 1 | 1 | 3.576274 | 5.029901 | 1.453627 | 0.288997 | 0.000 | 0.000 | 0.288997 |
| 7d | target_only | main | 1 | 1 | 5.029901 | 3.661227 | -1.368674 | -0.373829 | 1.000 | — | — |
| 7d | uncertainty | main | 3 | 3 | 5.092915 | 5.206837 | 0.113921 | 0.021879 | 0.000 | — | — |
| 7d | uncertainty | target_only | 1 | 1 | 3.542390 | 5.029901 | 1.487511 | 0.295734 | 0.000 | 0.000 | 0.295734 |
| 14d | block28 | main | 4 | 3 | 5.235566 | 5.232235 | -0.003331 | -0.000637 | 0.750 | — | — |
| 14d | drift | main | 4 | 3 | 5.147371 | 5.232235 | 0.084864 | 0.016219 | 0.250 | — | — |
| 14d | fixed_retention | main | 4 | 3 | 5.190855 | 5.232235 | 0.041380 | 0.007909 | 0.250 | — | — |
| 14d | frozen_source | main | 1 | 1 | 6.540867 | 6.690553 | 0.149687 | 0.022373 | 0.000 | — | — |
| 14d | online_best | main | 1 | 1 | 6.548480 | 6.690553 | 0.142074 | 0.021235 | 0.000 | — | — |
| 14d | source_error | main | 4 | 3 | 5.188813 | 5.232235 | 0.043422 | 0.008299 | 0.250 | — | — |
| 14d | uncertainty | main | 4 | 1 | 5.212997 | 5.264968 | 0.051972 | 0.009871 | 0.250 | — | — |
| 28d | block28 | main | 5 | 3 | 5.579476 | 5.598521 | 0.019045 | 0.003402 | 0.200 | — | — |
| 28d | drift | main | 5 | 3 | 5.564866 | 5.598521 | 0.033656 | 0.006012 | 0.200 | — | — |
| 28d | parameter_retention | main | 1 | 1 | 10.303079 | 10.381852 | 0.078773 | 0.007588 | 0.000 | — | — |
| 28d | seasonal_naive | main | 4 | 1 | 6.606611 | 4.432446 | -2.174165 | -0.490511 | 1.000 | — | — |
| 28d | source_error | main | 5 | 3 | 5.565872 | 5.598521 | 0.032650 | 0.005832 | 0.000 | — | — |
| 28d | uncertainty | main | 5 | 3 | 5.578790 | 5.598521 | 0.019731 | 0.003524 | 0.200 | — | — |
RMSE values for both sides and exact full-precision gains are retained in the linked CSV. A station/seed/budget from one row must not be treated as the same cohort as another row.
## Observed cost: all 24 Hybrid v4 strata
This table renders the [observed cost JSON](evidence/hung-hybrid371-observed-costs-20261027.json). Mean/P95 are saved **final replay stage** seconds only; they exclude Source/Target initialization, earlier continuation, provider wall time, upload and readback. `Peak MiB` is observed maximum allocation, with nulls preserved; inference/update counters and counter completeness are in the JSON. Devices and code revisions are stratified, so the rows do not support paired hardware speed or whole-matrix cost rankings.
| Method | Budget | Device | Runs | Mean s | P95 s | Peak MiB | Counter samples |
| --- | --- | --- | --- | --- | --- | --- | --- |
| block28 | 14d | Tesla T4 | 24 | 9.00 | 9.42 | 37.0 | 24/24 |
| block28 | 28d | Tesla T4 | 27 | 9.64 | 10.05 | 37.0 | 27/27 |
| block28 | 7d | NVIDIA GeForce RTX 3050 Ti Laptop GPU | 9 | 11.64 | 12.25 | 21.3 | 9/9 |
| block28 | 7d | Tesla T4 | 9 | 9.04 | 9.82 | 37.0 | 9/9 |
| drift | 14d | NVIDIA GeForce RTX 3050 Ti Laptop GPU | 24 | 11.50 | 15.12 | 21.3 | 24/24 |
| drift | 28d | NVIDIA GeForce RTX 3050 Ti Laptop GPU | 27 | 8.71 | 11.28 | 21.3 | 27/27 |
| drift | 7d | NVIDIA GeForce RTX 3050 Ti Laptop GPU | 18 | 9.61 | 13.47 | 21.1 | 18/18 |
| fixed_retention | 14d | NVIDIA GeForce RTX 3050 Ti Laptop GPU | 2 | 9.91 | 10.03 | 20.6 | 2/2 |
| fixed_retention | 14d | Tesla T4 | 20 | 9.96 | 11.22 | 37.0 | 20/20 |
| frozen_source | 14d | NVIDIA GeForce RTX 3050 Ti Laptop GPU | 1 | 14.25 | 14.25 | 9.4 | 0/1 |
| main | 14d | NVIDIA GeForce RTX 3050 Ti Laptop GPU | 24 | 6.41 | 7.54 | 21.3 | 24/24 |
| main | 28d | NVIDIA GeForce RTX 3050 Ti Laptop GPU | 27 | 6.52 | 7.60 | 21.3 | 27/27 |
| main | 7d | NVIDIA GeForce RTX 3050 Ti Laptop GPU | 18 | 6.63 | 7.67 | 21.3 | 18/18 |
| online_best | 14d | NVIDIA GeForce RTX 3050 Ti Laptop GPU | 1 | 7.87 | 7.87 | 20.6 | 1/1 |
| parameter_retention | 28d | NVIDIA GeForce RTX 3050 Ti Laptop GPU | 1 | 7.87 | 7.87 | 20.6 | 1/1 |
| seasonal_naive | 28d | None | 6 | 16.58 | 17.90 | — | 0/6 |
| seasonal_naive | 7d | None | 6 | 14.62 | 17.22 | — | 0/6 |
| source_error | 14d | NVIDIA GeForce RTX 3050 Ti Laptop GPU | 24 | 12.04 | 14.36 | 21.3 | 24/24 |
| source_error | 28d | NVIDIA GeForce RTX 3050 Ti Laptop GPU | 27 | 12.30 | 14.76 | 20.8 | 27/27 |
| source_error | 7d | NVIDIA GeForce RTX 3050 Ti Laptop GPU | 18 | 12.42 | 14.30 | 21.3 | 18/18 |
| target_only | 7d | NVIDIA GeForce RTX 3050 Ti Laptop GPU | 1 | 13.47 | 13.47 | 18.4 | 0/1 |
| uncertainty | 14d | NVIDIA GeForce RTX 3050 Ti Laptop GPU | 12 | 11.54 | 13.90 | 20.6 | 12/12 |
| uncertainty | 28d | NVIDIA GeForce RTX 3050 Ti Laptop GPU | 27 | 11.99 | 14.51 | 20.6 | 27/27 |
| uncertainty | 7d | NVIDIA GeForce RTX 3050 Ti Laptop GPU | 18 | 12.23 | 14.98 | 20.6 | 18/18 |
## Provider receipts, current extraction and gates
Kaggle matched comparison group08 GPU saved version `362902889` finished final 40 jobs; independent CPU readback version `362921585` verified archive bytes/SHA/CRC: shard0035 949,818,304 bytes / `44b2d40372948ffc98c7a19398d1e707df095bb2bb16a56d11b04db1`; shard0036 386,014,187 bytes / `15684a44f3dc4d1e37014f71cfcd262f13e821456afb2089872928d12afa0574`. Relay05 version `362911396` reported `REMOTE_READBACK_VERIFIED`. Earlier 742 distinct readbacks plus these 40 establish 782/782 new-job **archive** readback, subject to the missing consolidated per-job manifest ledger.
Latest live check at approximately 02:05 ICT on 28 October: [CPU metrics reader21](https://www.kaggle.com/code/hungluongduc/hung-cpu-metrics-shard0021-20261027-v1/log) saved version `362847566` was still RUNNING with 0 B visible output; [coordinator05](https://www.kaggle.com/code/hungluongduc/hung-cpu-metrics-coordinator-05-20261027-v1/log) version `362888557` completed and submitted [coordinator06](https://www.kaggle.com/code/hungluongduc/hung-cpu-metrics-coordinator-06-20261027-v1/log) version `362935445`, which was RUNNING. These observations do not certify new metric/export batches. No job was resubmitted or output overwritten for this report.
Technical gates remain: construct exact 782-row job → provider/version/archive/receipt/manifest table; verify all per-run bytes and hashes; finish remaining CPU metrics and six 80-job export batches; recompute full matched MAE/RMSE, uncertainty, NTR, switch/audit and costs; obtain Block7 fairness and Hung–Qyroven head/controller/runner-trace decisions; peer-review #39 and PR #72. GitHub Ubuntu/Windows jobs did not start on the prior PR head because of an account billing/spending-limit gate, so CI is unverified. Only after these gates and a frozen Development-based code/config/cohort/seed/threshold lock can the one-shot Final run and #10 E2E Results/Discussion/Conclusion proceed.
