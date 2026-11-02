# Local CPU archive-metrics validation — 28 October 2026

The new `tools/hung_local_archive_metrics.py` recomputes Development daily errors from an immutable training ZIP on the local CPU. It reads the ZIP without extracting or rerunning training. It checks the fixed payload and allocation SHA, original archive byte count/SHA/CRC, exact shard job set, each stage receipt and member SHA, manifest/checkpoint SHA, input/seed/config/initialization bindings, and the pinned scorer source before calling `score_saved`. A new output path is required; existing files cannot be overwritten.

The pinned allocation file SHA-256 is `05e0d8158f71fc07d58c49c30a165aadce0b333b2f7df0f09b069d0b2f510ed5`, the payload SHA-256 is `23a6d420523d990d07ff07d814ed642a851925283a102a3ae806f3b666e1d6f4`, and the scorer SHA-256 is `68fccbed056734d9b4842f7bda088880d7812d12417d64878d1aa018fc010456`. The local tool SHA-256 at this checkpoint is `3d07f14e37fda969d5a221c7534121239229a9da4c802c7b9f9a83e1f6fcb3c2`.

## Actual golden comparison

The local route scored raw training archives for shards0001–0003: **60/60 exact jobs**, with 31 scorable and 29 zero-scored. For each job, 17 scientific fields matched the independently ingested [Kaggle batch00 export](hung-cpu-export-readback-00-02-20261028.md) exactly: job/method/budget/seed/station/input/Source/Target identity, status, coverage, metrics, daily original-unit errors and label hashes, code, device, duration, runtime and proxy costs. The final manifest and checkpoint SHA values matched for all 60 jobs. Local output SHA-256 values are:

| Shard | Local 20-job output SHA-256 |
| --- | --- |
| 0001 | `4e931b99fafb3bd6f8f3424f4f523df3c0011be8eb7b8c87571c5bbbf0d965ca` |
| 0002 | `140968e395a16b56a8902e31a3336ded1ccee15d0ed7aef927a4c3eab023bcd8` |
| 0003 | `e1d7db3919dd0cf298bd3acf13c5f504973fe1b4b746b2163ac930c42657bf7c` |

These outputs live in ignored `.cache/local-archive-metrics-shard000{1,2,3}-v1.json`. They validate the local scoring route; they are **not** added a second time to Development metrics. Batch00–03 remain the independently ingested **320/560 Kaggle export jobs**. The remaining 240 jobs in batches04–06 still lack the raw training ZIPs or terminal export transport at this checkpoint.

## Blocker and next gate

The proof recovery worker reported Kaggle CLI HTTP 429 on `ListKernelSessionOutput` while fetching group03 and group05. The local `.cache/kaggle-proof-group03-raw-20261028` folder currently contains only `derivation.json`, with no raw `artifacts.zip` or receipt. No 429 workaround, duplicate submission, training run or output overwrite was attempted. Once the missing version-pinned archives arrive and pass their original proof audit, run the local scorer create-once for shards0021–0028 and 0033–0036, verify the exact 240-job batch04–06 job set, then merge with the existing 320 Kaggle exports and 291 local/historical records. Full metrics, paired evaluation, scientific acceptance and Final lock remain pending.

Validation: three local scorer commands exited 0; a 60-row field-by-field golden comparison found zero differences; Ruff check and format check, Python compile, and `git diff --check` passed. No full training or GPU test was run.
