# Hùng bounded Final — checkpoint-recomputed forecast results (v1)

**Status: evidence-bound Final analysis, pending independent scientific review.** This result covers only the three locked UrbanEV/SZH entities `2118`, `2534`, `2579`, budgets 7/14/28 days and physical seeds 7/11/19. The deterministic Seasonal Naive variant has one physical seed per entity/budget; it is not three independent replications. The 370 other eligible UrbanEV IDs and six CHARGED city scopes remain outside this Final.

## Provenance and denominator

The GPU [Final saved version `/1`](https://www.kaggle.com/code/hungluongduc/hung-final-e5e8fe1c-360-20261029-v1) produced archive SHA-256 `531bff0d24ddf7eb0a08d4ed9d97976e55140b81025db0d91c28c557684e1114` under lock `e5e8fe1cb5636e508b3edbcedbbd00a72d9d8230041bf383eeba3d1133883e5e`. A separate [CPU metrics saved version `/1`](https://www.kaggle.com/code/hungluongduc/hung-final-360-metrics-20261029-v2) mounted that exact GPU saved output, reverified the complete archive, loaded each terminal replay checkpoint with `weights_only=True`, recomputed 24-hour original-kWh forecast errors, and checked the declared manifest metrics and label/input bindings. Its receipt reports 360 scored jobs, zero null jobs and output SHA-256 `9e09ae4f72b13c03ed029deb338301753ae377c15cbbfa7414433c5538cba73a` (5,998,020 bytes). Pulled provider source text matches [the submitted v2 source](../../../tools/hung_final_remote_metrics_v2.py); metadata says private, CPU, internet disabled, source kernel attached. CPU v1 failed after 90 jobs because it guessed the `frozen_source` checkpoint name; its error log is preserved, and no result from v1 enters these tables.

The [local aggregator](../../../tools/hung_final_aggregate_v1.py) checked the downloaded receipt/output hash, exact 360 locked job IDs, the independent [job→artifact ledger](../hung-final-direct-kaggle-readback-20261029-v1.md), row identities, checkpoint path inventory, coverage, and every per-run MAE/RMSE sum. It found **32,400 requested and issued origins**, **32,280 complete scored days** (774,720 hourly labels), **120 unscored issued origins**, **666 valid physical-seed pairs**, **zero blocked pairs**, and **78 station-first comparison groups**. Every missing/late final horizon remains unscored; it is never a zero error. The full row tables are [runs](runs.csv), [paired](paired.csv), [blocked](blocked.csv), [station-first](station_first.csv) and the machine-readable [summary](summary.json). The 6 MB daily-error source stays in ignored repository cache, outside Git.

## Main versus Target-only

Values below are equal-seed means within each of three stations, then equal-station means. Positive gain is `Target-only − Main` in kWh; Transfer Gain divides that gain by the Target-only MAE. The interval is the locked exact `n^n` station bootstrap with `n=3`, 95% linearly interpolated percentiles. Each budget has 9 matched station/seed cells. All three stations are SZH UrbanEV; forecast horizon is 24 hours.

| History | Main MAE / RMSE (kWh) | Target-only MAE / RMSE (kWh) | Paired MAE gain (kWh; descriptive 95% interval) | Transfer Gain | NTR |
| --- | ---: | ---: | ---: | ---: | ---: |
| 7 d | 8.051 / 11.315 | 13.591 / 17.401 | 5.540 [1.197, 11.227] | 0.408 | 0/3 |
| 14 d | 8.042 / 11.345 | 13.043 / 16.753 | 5.000 [1.113, 10.082] | 0.383 | 0/3 |
| 28 d | 7.916 / 11.201 | 12.401 / 16.011 | 4.486 [0.733, 9.288] | 0.362 | 0/3 |

These are held-out observations for the **bounded** locked cohort, not evidence of all-UrbanEV or cross-city superiority. The bootstrap has only three station units and does not model temporal dependence as independent stations.

## Adverse and inconclusive comparisons

The Main variant does **not** have the lowest observed MAE among all locked methods. For example, `source_error` is lower than Main by 0.112, 0.113 and 0.076 kWh for budgets 7, 14 and 28; `full_finetuning` is lower by 0.049, 0.074 and 0.109 kWh. These small differences are descriptive and should not be used to retune the frozen method. The `no_source` ablation has MAE 13.883, 13.136 and 12.420 kWh; its station-mean MAE is worse than Target-only at 3/3, 3/3 and 2/3 stations. `frozen_source` is worse than Target-only at 1/3 stations for 28 days. Seasonal Naive has only seed 7 physically and is never counted as three independent seed runs. All 78 method/budget/reference estimates and uncertainty bounds remain in `station_first.csv` so unfavorable results are visible.

## Controller, audit and measured cost

A separate [CPU manifest audit saved version `/1`](https://www.kaggle.com/code/hungluongduc/hung-final-360-events-20261029-v1) rechecked the archive and exported the 360 exact stage manifest event/cost records. Its 5,664,639-byte output has SHA-256 `02434d02989fb60bd18e8002cf9878bb29dab0aa436048cb8e235fcf80b54f08`. The local [event auditor](../../../tools/hung_final_event_audit_v1.py) joined these records to the score rows and job ledger, yielding [360 job rows](job_events.csv), [14 variant rows](variant_events.csv) and [summary](event_summary.json). The 297 controller jobs contain 1,863 decisions and 313 recorded switches; 63 single-baseline jobs have no controller decision list, represented as null rather than zero. Main's 27 jobs have 162 decisions, 24 switches, 7,263 measured candidate update steps, 7,290 candidate inference calls and 320 old-policy audit update/inference calls. These are observed actions and costs, not evidence that switching caused an error reduction.

The 360 saved replay-stage durations sum to 4,329.8 s. Across stages, the sum of **available** durations is 8,238.4 s; 54 Target-initialization/Drift-reference duration fields are absent and remain null. The provider Final session ran 17,497.5 s. These figures exclude or incompletely cover Source preparation, archive creation, transport and provider overhead; they are not matched model-cost comparisons. The three proxy methods each record 2,430 proxy inference calls, but the published variant table only aggregates candidate/audit counts; detailed proxy nanosecond fields stay in the pinned ignored CPU event output. WAPE is not yet computed because the score export does not include the scored-label denominator; it remains undefined here, not zero.

## Reproduction

From the repository root, using the small CPU output files downloaded create-only into `.cache`:

```sh
python -m tools.hung_final_aggregate_v1 \
  --scores .cache/hung-final-metrics-20261029-v2/saved-output-v1-complete/final-run-scores.json \
  --receipt .cache/hung-final-metrics-20261029-v2/saved-output-v1-complete/final-metrics-receipt.json \
  --ledger .cache/hung-final-direct-readback-20261029-v1/saved-output-v1-complete/final-job-artifact-ledger.json \
  --output .cache/hung-final-aggregate-20261029-v3
```

Use a new output directory: the command refuses an existing one. The `v2` local output directory supplied these published tables. Focused offline aggregation tests passed 3/3; the clean full repository suite passed 497 with one skip before this new aggregator was added. GitHub CI must be evaluated on the new head independently. Scientific Block7/parity/CHARGED and Colab #39 peer gates remain open; this analysis does not approve them.

The event tables were produced by `python -m tools.hung_final_event_audit_v1` with the downloaded `final-run-events.json`, its receipt, the same score file and the independent job ledger. The create-only local output was `.cache/hung-final-event-audit-20261029-v2`; all published table hashes were checked against its summary.
