# First matched Kaggle shard terminal evidence — 2026-10-27

[Private Kaggle version 362612528](https://www.kaggle.com/code/hungluongduc/hung-matched-shard0001-44b8532-20261027?scriptVersionId=362612528)
completed successfully in **1,810.4 seconds (30m10s)** on GPU T4 x2. Only device 0
was used. All 20 jobs / 40 stages in shard 0001 completed with dispatcher exit 0;
its separate CPU receipt/dependency verifier exited 0. Execution alone took
1,298.753 seconds; the whole provider time includes startup, dry-run, numerical
probe, independent-process verification and packaging.

The archive is 65,931,034 bytes, SHA
`29e3db51106402942959f80762e4c27995ad4ec9f2253fd96cc8a4681d3b2dcd`,
runtime-local member CRC passed. A completed version now preserves its Output.
Independent provider readback of this archive is required before the next batch;
this snapshot does not claim that readback or a local download.

The provider plan SHA was
`80a1666cf2083594c9a2bc0b0a4dc3e30118eda43d07187cd5b6d8b51f90e0bb`
and partition SHA
`e2c6cb6f15a7473c6cdfd7912fefa838d63a770cf352dff93c2cccc3ae86a15c`.
Both derive by path relocation from the same pinned 782-job parent plan and
40-shard partition. Model code remains `44b8532`, exact config/input/Source/Target
bytes and job IDs are preserved. [Evidence JSON](evidence/hung-kaggle-shard0001-20261027.json)
contains the complete terminal receipt and the SHA of the visible log capture.

Including the verified local pilot and shard 0039, **42 new jobs have completed
and passed receipt/dependency verification at their execution locations**.
Six have additionally passed the provider-mounted archive readback documented
in the earlier report. Another 740 remain outside this completed set: 200 in
the ordinary Python local queue and 540 in the conditional Kaggle route.

## Measured feasibility and automation capability

An authenticated SDK quota query at `2026-10-26T20:51:14.219032+00:00` reported
108,000 seconds total, 23,588.570124 seconds used, zero reserved and paid scaling
disabled: approximately 23h27m remained. These are actual account values, not an
assumed 27-hour allowance. The first 20-job whole-runtime extrapolation for the
remaining 540 Kaggle jobs, with a 1.25 margin, is 1,018.35 minutes (16h58m).
This is a provisional estimate across a heterogeneous matrix; later quota,
per-shard runtime and disk limits remain mandatory gates. Per-job subprocess P95,
VRAM, update totals and readback cost will be independently extracted from the
predecessor archive before the next bounded group starts.

The next prepared notebook selects only shards 0002 and 0003 (40 jobs), verifies
the predecessor's exact output SHA/CRC and canonical job set, checks the measured
quota feasibility, and runs its own frozen CPU/CUDA probe before execution.
It has not been submitted by this snapshot. Other proposed groups remain bounded
to at most 120 jobs. No notebook executes the entire matrix.

The [official Kagglehub documentation](https://github.com/Kaggle/kagglehub#authenticate)
states that Kaggle notebooks have built-in authentication. A CPU-only capability
probe used that existing authentication, without creating, copying or printing
credentials. Quota querying and a 314-byte private control-Dataset upload
succeeded, but `GetDatasetStatus` returned **403**. Version 362621233 is retained
as a failed probe, not a successful end-to-end readback. That forbidden status
endpoint is not retried or bypassed. A separate v2 probe tests the documented
authenticated file-download resolver and optional CPU-only kernel dispatch;
any unsupported capability remains unavailable. No local user-profile Kaggle
configuration was read.

Validation to this point: ten focused transport/queue tests passed; the earlier
clean full suite passed 282 tests with one skip; five additional queue tests are
covered by subsequent CI. Full-repository Ruff and diff checks pass, including
the prepared notebooks. This phase does not supply independent scientific
acceptance, the #39 substitution decision, complete paired metrics or a Final
lock. No issue was closed or PR merged.

The subsequent clean full suite passed **287 tests with one skip**, exit 0,
in 209.369 seconds (`.cache/provider-offline-tests-v3*`). The group-02 launcher
now queries the authenticated quota API again inside its actual runtime,
requires complete quota fields and disabled paid scaling, and applies the
remaining-matrix estimate plus a 60-minute reserve to that fresh observation.
The earlier preparation-time quota remains explicitly labelled as a reference.

API probe version 362623009 failed before uploading any v2 control Dataset:
`GetKernelSessionStatus` with an explicit version label returned 404. The official
CLI implementation queries this endpoint without that label; v3 follows that
request form and preserves both earlier failures. No successful API file
readback or automatic GPU relay is asserted by this snapshot.
