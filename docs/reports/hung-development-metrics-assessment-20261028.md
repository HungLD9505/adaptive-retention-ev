# Hung Development metrics assessment — 28 October 2026, 02:10 ICT

**Scope:** read-only assessment of the last authenticated portable metrics snapshot, [Hybrid v4](hung-development-hybrid-20261027-v4/report.md), plus a live status check of the fixed CPU reader/export route. This is a Development checkpoint, not a full-matrix or Final result. The [detailed phase tables](hung-provider-phase-detailed-results-20261028.md) retain every available paired row, #39 result and cost stratum.

## Source binding and actual coverage

The local ignored portable result `.cache/portable-hybrid-results-v4.json` is 3,347,815 bytes and hashes to `bfdff9be47653c25ea5e15049b35e9148f4dfffc750a4249ec5afd0ccf73f39c`, exactly the `result_sha256` in the tracked [Hybrid v4 summary](hung-development-hybrid-20261027-v4/summary.json). It contains 371 distinct physical run records, 166 exact-label-hash paired cell records and 142 blocked pairs. This check reopens the pinned result; it does not restore every model checkpoint or independently verify the other 411 new jobs' per-run manifests.

| History budget | Physical run records | Scorable | Zero scored | Requested origins across records | Scored days across records |
|---|---:|---:|---:|---:|---:|
| 7 days | 97 | 49 | 48 | 8,730 | 3,786 |
| 14 days | 132 | 67 | 65 | 11,880 | 4,076 |
| 28 days | 142 | 80 | 62 | 12,780 | 4,768 |
| **Total** | **371** | **196** | **175** | **33,390** | **12,630** |

The origin/day sums are **descriptive sums across methods**, including repeated station-days, and must not be interpreted as independent observations or overall cohort coverage. A zero-scored run has undefined MAE/RMSE. The [coverage audit](evidence/hung-hybrid371-coverage-20261027.json) shows 418/1,104 required logical family cells matched and 223 scorable logical family views, but family aliases share physical artifacts. These logical totals are not independent runs. Full fine-tuning, fair Block7 and no-Source have zero matched cells in this snapshot; Target-only and Frozen Source have one each. These gaps make a full method ranking invalid.

## Paired comparisons and scientific interpretation

The [25-row paired CSV](hung-development-hybrid-20261027-v4/paired.csv) uses exact common scored-day label hashes within station/seed, then equal seed means within station and equal station weight within budget. Of the 25 **row-specific** observed MAE gains, 20 are positive and five negative. The 19 comparisons against Main split 14 positive/five negative; the six comparisons against Target-only are positive, but each uses only one station and one seed and one is the non-Source Seasonal Naive. By budget, the signs are 7d 9/3, 14d 6/1, and 28d 5/1 positive/negative. Rows share data and have different participating methods/stations, so these counts are a descriptive sign inventory, **not** a vote, significance test, global win rate or model-selection criterion.

Only five Source-using, Target-only-reference rows have a defined negative-transfer fraction/transfer gain. All five have fraction 0 on their **single observed station**; this does not estimate a cohort negative-transfer rate. The other 20 rows have null transfer fields by definition. The supplied NTR column is the worse-than-reference station fraction for its own row; it must not be pooled across rows. RMSE is available per paired row in the CSV, but incomplete method coverage and changing cohorts prevent a global MAE/RMSE conclusion. There is no defensible full-cohort station-level uncertainty interval, bootstrap sensitivity, or threshold selection yet. The 142 blocked pairs lack paired scored days and cannot be filled with zero or unpaired errors.

The [24 observed cost strata](evidence/hung-hybrid371-observed-costs-20261027.json) have 371 duration samples, 359 peak-allocation samples and 357 complete runtime-counter samples. Their mean/P95 cover only the **last replay stage** of unequal cohorts/code/devices. They exclude Source/Target initialization, earlier continuation, provider wall time, upload and remote readback. Accordingly, no complete per-job/per-provider cost or hardware speed ranking is reported.

## Live CPU metrics/export route

At this observation, [reader21](https://www.kaggle.com/code/hungluongduc/hung-cpu-metrics-shard0021-20261027-v1/log) saved version `362847566` displayed `RUNNING` after about 19,701 seconds and 0 B output; no terminal receipt was visible. [Metrics coordinator06](https://www.kaggle.com/code/hungluongduc/hung-cpu-metrics-coordinator-06-20261027-v1/log) saved version `362935445` displayed `RUNNING` after about 1,505 seconds and 0 B output. The earlier [portable export coordinator00](https://www.kaggle.com/code/hungluongduc/hung-portable-coordinator-00-20261027-v1/log), version `362673642`, displayed `CANCELED` after 9,187.5 seconds. Its visible log confirms only `batch_00` completed: 80 jobs, 42 scorable and 38 zero scored; this batch was independently ingested and hashed in the [CPU export pilot report](hung-cpu-export-pilot-20261027.md). It shows no completed batch01–06 receipt.

The repository contains a [prepared resume01 notebook](../../experiments/hung_sprint2/kaggle_export_deferred_resume01_v1.ipynb), but its validation record states `prepared_only=true`, `batches_remaining=6`, `jobs=480` and `requires_all_remaining_readers_complete=true`. No repo output/receipt for batch01–06 was found. The running reader is therefore a real dependency: launching a duplicate or claiming the six exports finished would violate the fixed route. No reader, export batch, GPU job, or output was resubmitted or overwritten for this assessment.

## Acceptance consequence

The 782/782 archived new-job remote readback remains a valid **execution/durability** milestone, separate from metric completeness. Full Development acceptance still needs the 782-row job/manifest/receipt ledger, the remaining CPU reader completions, exact SHA-checked batch01–06 ingestion, full family/seed/budget coverage, paired station-level MAE/RMSE and uncertainty, negative-transfer and controller/audit analysis, plus fairness/parity review. Final must remain locked until those Development gates and independent review are resolved. No Final labels were opened or used here.

**Checks:** Python recomputed grouped counts from the source portable JSON, confirmed the portable SHA-256 equals the tracked summary, and verified the 25 paired-row sign counts. Kaggle statuses were read on the saved-version log pages. This report adds documentation only; no model or evaluation code changed.
