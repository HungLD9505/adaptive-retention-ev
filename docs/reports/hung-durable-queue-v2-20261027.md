# Durable per-shard Kaggle queue v2 — 2026-10-27

The real storage integration passed with the completed **65,931,034-byte**
shard-0001 archive; no training was repeated. Its SHA remains
`29e3db51106402942959f80762e4c27995ad4ec9f2253fd96cc8a4681d3b2dcd`.
Upload to the create-only private Dataset took **7.033 seconds**; upload plus
waiting for the independent CPU readback took **45.608 seconds**. The CPU's own
hash/CRC check took **2.169 seconds** and its returned `readback.json` was also
retrieved. The Dataset is
[version 1](https://www.kaggle.com/datasets/hungluongduc/hung-dev-shard0001-44b8532-20261027-v2/versions/1);
the [independent CPU version](https://www.kaggle.com/code/hungluongduc/hung-dev-readback-shard0001-20261027-v2)
is version 1, submitted source SHA
`f3f4ae355b23333f5f758a75b98caf9cb503980b0b96832a2b2cde861540342a`.

The [v2 CPU coordinator, version 362634406](https://www.kaggle.com/code/hungluongduc/hung-development-cpu-coordinator-20261027-v2?scriptVersionId=362634406)
has actually started without an accelerator. The v1 coordinator was cancelled
with authoritative `CANCEL_ACKNOWLEDGED` before any observed group-03 submission;
its earlier evidence is preserved. The separate interactive CPU capability
session was stopped after its successful proof to free resources. The original
GPU group 02 and local GPU worker continue. Subsequent v2 GPU groups require
every shard's independent Dataset readback before another shard can execute.
Future GPU submissions by v2 have not yet been observed in this snapshot.

Kaggle shard **0002 completed 20 jobs**, with execute and separate verification
exits 0, archive CRC passed, 61,939,216 bytes and SHA
`409c523b421397fecc22bc953a13b2642aa49cf1f0f443c9e88f1d11af4ca908`.
It used the expected relocated plan
`70dff1c41380aa781062470b6986829e470e320a1cd0522ac49c63956ea6d12d`
and partition
`7d99e722c6e27b7257a709182a0827b63c4a1599cfe14f3472e9e4a914cf8ad1`.
This raises completed, receipt-verified new jobs at execution sites to
**82/782**. Its archive is still inside the running group-02 runtime and is
not yet counted as remotely read back or independently durable. The remotely
read-back subset remains **26**. Group 02 has 20 jobs remaining, the local queue
180 and the future Kaggle route 500. Running jobs remain outside completion.

[Evidence JSON](evidence/hung-durable-queue-v2-20261027.json) contains the full
terminal shard receipt, actual upload/readback proof, log hashes, pinned runtime
links and validation result. The separate metric snapshot covers 69 reused Main
plus 42 new local runs, not all 82 completed new jobs. Its
[partial results](hung-development-partial-20261027/report.md) recompute 111 runs,
60 scorable and 51 with zero scored horizons; incomplete cohorts do not select
configuration or establish final research conclusions.

The clean-commit enlarged suite passed **305 tests, one skip, exit 0**, in
208.997 test seconds / 214.870 wrapper seconds. Full Ruff check/format and diff
checks pass. The preceding report inventories code, tests, commands, equations,
coverage and remaining gates; this follow-up changes only this report and its
evidence JSON. No model/dispatcher code changed from `44b8532`. No merge, issue
closure or Final evaluation occurred. Independent reviewer access, fairness,
#39 substitution approval, full Development coverage and an immutable Final lock
remain required.
