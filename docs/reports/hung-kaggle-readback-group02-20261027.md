# Kaggle predecessor readback and group 02 — 2026-10-27

The independent group-02 runtime read the completed shard-0001 archive from
Kaggle's mounted version output. Its 65,931,034 bytes matched SHA
`29e3db51106402942959f80762e4c27995ad4ec9f2253fd96cc8a4681d3b2dcd`;
member CRC, exact 20-job set and plan identity passed. Hash/CRC readback took
1.527 seconds. This raises the archive-readback subset to **26 of 42 completed
new jobs** at this snapshot; local shard 0039 still awaits remote readback.

[Group 02 version 362625674](https://www.kaggle.com/code/hungluongduc/hung-matched-group02-44b8532-20261027?scriptVersionId=362625674)
then passed 28 CPU/CUDA parity checks and began its fixed shards 0002/0003,
40 jobs disjoint from the local route. It is running, not counted complete.
Its authenticated quota observation at `2026-10-26T21:16:58.401867+00:00`
reported **1,405.892 GPU minutes available**, with zero reserved seconds and
paid scaling disabled. The 1,018.35-minute extrapolation plus 60-minute reserve
passed. Future runtimes must refresh that observation.

The predecessor measurements show subprocess P95 of 25.974 seconds per job,
39,502,336 bytes peak CUDA allocation and 44,040,192 bytes peak CUDA reservation.
The archive contains 76,577,575 uncompressed bytes and 2,133 cumulative replay
update steps. P95 excludes orchestration, verification and archive overhead;
update totals include candidate/audit/proxy work and exclude reused Source/Target
training. The whole first provider runtime remains 1,810.4 seconds. These are
capacity measurements, not model-selection metrics.

[Machine-readable evidence](evidence/hung-kaggle-readback-group02-20261027.json)
binds the observed values to the captured log SHA. A separate CPU API probe
version 362627452 failed in 13.5 seconds: Kaggle's native resolver does not allow
new Dataset attachments in non-interactive sessions. Earlier HTTP/status 403
failures remain preserved; no forbidden endpoint is bypassed. An interactive
CPU capability check is separate from these GPU jobs and is not evidence of a
working automatic relay until its terminal result passes.

Validation: the clean full offline suite passed 287 tests with one skip and exit
0; Ruff and diff checks pass. Changed files for this phase are this report, its
evidence JSON and the versioned CPU native-resource probe notebook. Independent
scientific review, #39 substitution acceptance, complete Development coverage,
paired aggregation and the immutable Final lock remain outstanding. No merge,
issue closure or Final evaluation occurred.
