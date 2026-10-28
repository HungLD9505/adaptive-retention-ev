# Hung CPU metrics/export resume01 — 28 October 2026, 14:45 ICT

This checkpoint records a new, create-once Kaggle CPU export submission. It does not count submission or a running notebook as completed metrics. The earlier batch00 pilot remains the only 80-job export independently ingested at this snapshot.

## Fixed inputs and scope

- Source notebook: `experiments/hung_sprint2/kaggle_export_deferred_resume01_v1.ipynb`, local file SHA-256 `2625ed1dedf8bffaef1ed499248bf9fe69d62c459e14f53bcdc8411a9b67b5a6`. Its embedded source SHA-256 assertion is `000812306fb6bd5dc41d1ff125b5d2c9ef9522a5c07b33ed5c81465d1d8c68b7`.
- Allocation: `experiments/hung_sprint2/kaggle_export_batches_v1.json`, local file SHA-256 `05e0d8158f71fc07d58c49c30a165aadce0b333b2f7df0f09b069d0b2f510ed5`. A fresh local parse found seven 80-job batches, 560 distinct job IDs in total, and no overlap between batch00 and batches01–06 (480 remaining jobs).
- The resume01 notebook starts at `batch_01` and requires remaining metric readers to be terminal `COMPLETE`; it uses create-only claims and version-one assertions. The Kaggle import dialog selected **Save & Run All (Commit)** and **Run without an accelerator**. No training job or GPU was requested.

## Remote observations

| Saved item | Version | Observed evidence |
| --- | ---: | --- |
| [CPU reader21](https://www.kaggle.com/code/hungluongduc/hung-cpu-metrics-shard0021-20261027-v1/log) | `362847566` | `Successfully ran`; shard0021 receipt says 20 jobs (11 scorable, 9 zero), official `--resume --verify-only` exit 0, `executed:false`, artifact SHA-256 `19eb373ce6943afe5c835037ab2b933bcdbee6bc0d244d0395ad8ffd4fbcf419`, 68,578,761 bytes, results SHA-256 `db0ad5f5bf358a9ec110a162441c39c9fb6a0d357b438e15d8b4b26f1cdd1463`. |
| [CPU coordinator06](https://www.kaggle.com/code/hungluongduc/hung-cpu-metrics-coordinator-06-20261027-v1/log) | `362935445` | `Successfully ran`; log reports shard21 and shard22 `COMPLETE`, then submits shard23 and coordinator07. |
| [CPU coordinator07](https://www.kaggle.com/code/hungluongduc/hung-cpu-metrics-coordinator-07-20261027-v1/log) | `362969524` | `Successfully ran`; log reports shards23–26 `COMPLETE`, then submits shard27 and coordinator08. |
| [CPU coordinator08](https://www.kaggle.com/code/hungluongduc/hung-cpu-metrics-coordinator-08-20261027-v1/log) | `363000909` | `Successfully ran`; log reports shards27, 28, 33, 34 `COMPLETE`, then submits shard35 and coordinator09. |
| [CPU coordinator09](https://www.kaggle.com/code/hungluongduc/hung-cpu-metrics-coordinator-09-20261027-v1/log) | `363032397` | `Successfully ran`; log reports shard35 and final shard36 `COMPLETE`. No later coordinator is claimed. |
| [Export resume01](https://www.kaggle.com/code/hungluongduc/kaggle-export-deferred-resume01-v1/log) | `363089734` | Imported once as a private CPU saved run. It progressed from `Queued` to `Running`; at about 86 seconds, output 0 B and log shows create-only relay01 claim plus batch01 submit claim. Log then reports `submitted_cpu_export` for `hung-portable-batch01-20261027-v1`, version 1, `gpu:false`, source SHA-256 `049b957a81d3a39349ae670a50b7491f509f8390975838ea6cd7da77719f3b6a`, inputs readers shard0009–0012. |
| [Export batch01](https://www.kaggle.com/code/hungluongduc/hung-portable-batch01-20261027-v1/log) | `363090077` | Private saved version accepted and **Running** at about 19 seconds, accelerator `None`, output 0 B. No terminal receipt or exported bytes yet. |

The coordinator sequence is a remote execution receipt for the metric-reader queue. The exact 480-job export content and full scientific tables require the batch01–06 terminal receipts, independent SHA-checked ingestion, and recomputation in the repository. No batch01–06 metrics, paired gains, uncertainty, or Final outcome are asserted here.

## Next finite gate

Read the saved batch01 log after it reaches terminal state, capture its receipt and transport chunks, then run `tools/hung_ingest_export.py` with the pinned allocation and an unused output directory. The export coordinator should continue the fixed batch02–06 sequence only if its create-only and terminal guards pass. Preserve failed or partial output for audit and do not resubmit batch00 or overwrite an existing batch.
