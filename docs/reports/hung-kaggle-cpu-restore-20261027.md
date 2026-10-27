# Kaggle CPU restore and Development progress — 27 October 2026

Related: #22, #23, #39, #10; implementation PR #70 and provider/reporting PR #72.
This is an evidence handoff, not a replacement for `docs/SPRINT_PLAN.md`.

## Actual execution

At the 08:08 ICT observation, 222 of 782 new Development jobs have completed-shard
evidence: 202 have persistent remote SHA/CRC readback, and 20 local shard0031 jobs
await remote readback. The other 560 are outside completed-shard certification.
Historical Main's 69 runs are separate. Block-7 remains unmatched pending independent
fairness review. No Final execution or independent acceptance is claimed.

Kaggle recovery v2 is still running on T4. Its shard0009 receipt records a private
Dataset version 1, 68,786,447 bytes, SHA
`37f635185da5bf08fd927e0ecacb9efb53f41f2b87f85ad3554f5a92ee53de5e`,
20.658 seconds upload and 113.815 seconds upload plus separate CPU readback.
The local training process and CPU report worker were independently observed live.
Python workers handle these repeated operations without a Codex call per job.

## Completed shard0008 restore

[Kaggle CPU run 362658126](https://www.kaggle.com/code/hungluongduc/hung-shard0008-full-cpu-restore-20261027-v1?scriptVersionId=362658126)
succeeded in 764.3 seconds without a GPU. It restored the original runtime paths,
validated SHA/CRC and exact receipt binding, then ran the official dispatcher with
`--resume --verify-only`, exit 0, in 726.772 seconds. There was no training fallback.
Saved forecasts were recomputed using the pinned scorer: 20 runs, 11 scorable,
9 with zero scored days. Zero scored days do not imply zero prediction error.
The original archive and historical receipt identities were preserved.

The accompanying JSON records code/plan/partition/scorer/input provenance,
verification command, log hash, result hash, artifact hash and original receipt hash.
Model code remains `44b8532959d76fb20691881539f991ca44983727`; the canonical parent
plan remains `2d448d2584f65baf7e09445e013b4283314b08ea2cce855c6850e9fc12ba87ee`.
Runtime path relocation has its own explicitly recorded plan hash.

## Prepared CPU queue

`tools/hung_kaggle_metric_queue.py` and its notebook prepare 27 CPU-only receivers
for the remaining Kaggle route, reusing shard0008's completed trial. They never
submit GPU training. Each child mounts a completed version-1 Notebook output,
restores its original runtime plan, verifies it through the official dispatcher,
and computes saved Development metrics. Fixed routing excludes local shards.
Create-only submission claims prevent duplicate execution; unexpected provider
states stop the queue. Relays are bounded to three hours each and twelve total.
An owned-kernel inventory capability gate runs before status requests for future
resources. Access failures propagate without endpoint fallback or retry.

The queue is prepared, not deployed at this report's observation. Its eight offline
tests pass, including failure gates, ownership inventory gating, routing and handoff
without duplicate submission. Full-suite and live inventory results must be recorded
separately after the source is frozen.

The new local partial snapshot v4 has 191 catalogued runs (69 Main plus 122 new
local jobs), 101 scorable and 90 zero-scored. Kaggle's 20 newly restored runs are a
separate collection and are not silently added to that table. No partial cohort
supports a global method ranking or Final selection.

Independent peer review, complete matched coverage, durable local shard0031
readback, and immutable Final lock remain pending. #39's Kaggle/local alternative
still needs team approval; Colab/Drive acceptance is not asserted. #10 remains a
results handoff, not a completed final thesis evaluation.
