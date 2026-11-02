# Hùng bounded Final metrics — local CPU reproduction checkpoint

**Status, 30 October 2026:** This create-only check reran the existing aggregators on the saved, repository-local small Kaggle CPU outputs. It did not change the frozen Final lock, metrics protocol or published tables. The check is a local transformation reproduction, not an independent local readback of the 2.4 GB GPU archive or scientific peer approval.

## Pinned inputs

| Input in ignored repository `.cache` | Bytes | SHA-256 |
| --- | ---: | --- |
| `hung-final-metrics-20261029-v2/saved-output-v1-complete/final-run-scores.json` | 5,998,020 | `9e09ae4f72b13c03ed029deb338301753ae377c15cbbfa7414433c5538cba73a` |
| `hung-final-metrics-20261029-v2/saved-output-v1-complete/final-metrics-receipt.json` | 535 | `657264b1330d48b77f65ea032e3a69f351c6ba8f657a3ae432a3e1060b23bc65` |
| `hung-final-direct-readback-20261029-v1/saved-output-v1-complete/final-job-artifact-ledger.json` | 725,277 | `0dca10975d5431ac199909ccb5bf69298040d6e4a21d3424bd15986a26cfa0a8` |
| `hung-final-wape-20261029-v1/saved-output-v1-complete/final-wape-rows.json` | 64,798 | `5d9eafd520b3d9aedf88d6ccf0a032dce97ac30958059ebaf6067d40cb641dda` |
| `hung-final-wape-20261029-v1/saved-output-v1-complete/final-wape-receipt.json` | 464 | `1336f7af6162c525b625d7a32dfd64696844f3f74bb3af0069d1775f342fa337` |

The [independent remote archive readback](hung-final-direct-kaggle-readback-20261029-v1.md) binds the GPU archive and 360-job ledger to saved Final `/1` and lock SHA-256 `e5e8fe1cb5636e508b3edbcedbbd00a72d9d8230041bf383eeba3d1133883e5e`. The separate [score](hung-final-analysis-20261029-v1/README.md) and [WAPE](hung-final-wape-20261029-v1/README.md) CPU receipts document their own mounted-archive checks and saved output identities.

## Commands and result

From the repository root, both output directories below were new and create-only:

```sh
python -m tools.hung_final_aggregate_v1 --scores .cache/hung-final-metrics-20261029-v2/saved-output-v1-complete/final-run-scores.json --receipt .cache/hung-final-metrics-20261029-v2/saved-output-v1-complete/final-metrics-receipt.json --ledger .cache/hung-final-direct-readback-20261029-v1/saved-output-v1-complete/final-job-artifact-ledger.json --output .cache/hung-final-aggregate-recheck-20261030-v1
python -m tools.hung_final_wape_audit_v1 --scores .cache/hung-final-metrics-20261029-v2/saved-output-v1-complete/final-run-scores.json --wape .cache/hung-final-wape-20261029-v1/saved-output-v1-complete/final-wape-rows.json --receipt .cache/hung-final-wape-20261029-v1/saved-output-v1-complete/final-wape-receipt.json --ledger .cache/hung-final-direct-readback-20261029-v1/saved-output-v1-complete/final-job-artifact-ledger.json --output .cache/hung-final-wape-recheck-20261030-v1
```

The first command passed: 360 exact jobs, 360 scored job rows, zero null jobs, 32,400 issued origins, 32,280 scored complete days, 666 paired physical-seed cells, zero blocked cells and 78 station-first groups. The WAPE audit passed with 360 jobs and 42 station/variant/budget groups. A separate byte comparison found **8/8 generated files identical** to the published files: `runs.csv`, `paired.csv`, `blocked.csv`, `station_first.csv`, `summary.json` in [Final analysis v1](hung-final-analysis-20261029-v1/README.md), plus `wape_runs.csv`, `wape_stations.csv`, `wape_summary.json` in the [WAPE audit](hung-final-wape-20261029-v1/README.md). This is stricter than matching rounded table cells alone.

The historical Final analysis v1 README says WAPE was not yet computed and cites an earlier 497-test checkpoint. Those sentences describe its publication time and are superseded by the later [WAPE audit](hung-final-wape-20261029-v1/README.md) and [clean-tree validation v3](hung-e2e-validation-20261030-v3.md). The current [research draft](hung-e2e-research-report-draft-20261030-v31.md) reports the later WAPE results. No result from the failed first CPU metrics version was used here.

Remaining limits: this local reproduction authenticates the small saved CPU outputs through their receipts and reproduces their aggregation. It does not download or independently inspect the full GPU archive bytes at the local machine, repair the 120 unscored origins, impute missing stage durations, extend the three-station Final cohort, or decide the open scientific review gates.
