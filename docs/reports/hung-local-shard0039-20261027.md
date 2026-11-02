# Local shard 0039 terminal evidence — 2026-10-27

The 16-job uncertainty shard completed all 32 stages with exit code 0 in
1,659.889 seconds (27m40s). The separate CPU `--resume --verify-only` invocation
also exited 0. Its ZIP is 48,346,859 bytes, CRC passed, SHA
`76b3f2196c514c04a44587a6e4502dc864b4f3d08614e1a4cea8e857eaef2be8`.
The original outputs/logs/receipts remain on local persistent SSD. This archive
has not yet been uploaded and read back from remote storage.

[Evidence JSON](evidence/hung-local-shard0039-20261027.json) records the immutable
plan/partition/code identities, all 16 job IDs and the terminal log hashes.
Together with the six-job pilot, **22 of 782 new jobs have completed and passed
local receipt/dependency verification**. Six have also passed provider-mounted
archive readback; 760 jobs remain outside that completed set. Historical Main,
Block-7, proxy/calibration and six-city runs retain their original attribution
and are not included in these new-job counts.

The ordinary Python local worker authenticated the shard-0039 terminal barrier
and started its next fixed shard, 0037. Its remaining queue contains 200 jobs,
with no LLM monitoring or performance-based selection. This is execution
progress, not certification that those 200 jobs are complete. The Kaggle route
contains 560 jobs including the live first 20-job shard; further release still
requires measured first-shard capacity and durable readback.

No forecasting code, data contract, Source/Target split or historical output was
changed. Independent review/fairness acceptance, the #39 provider-substitution
decision, complete paired metrics and the immutable Final lock remain pending.
