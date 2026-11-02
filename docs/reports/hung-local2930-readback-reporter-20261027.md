# Local2930 remote readback and CPU reporting worker — 2026-10-27

## Actual artifact evidence

Local shards 0029 and 0030 now have persistent private storage and a separate
CPU readback. [Dataset version 1](https://www.kaggle.com/datasets/hungluongduc/hung-local2930-review-capsule-20261027-v1/versions/1)
contains the unchanged archive bytes, receipt and pinned verifier. The capsule
is **213,029,158 bytes**, SHA
`4b01079aabad7ec74528fe56b199c0002e431efd69d2d94fd8a171e6fa2fe3c0`.
It includes the 40 newly durable local jobs and 69 unchanged historical Main
anchors. The anchors are duplicated for self-contained verification and counted
once across capsules; no training or historical run-ID rewrite occurred.

[Separate CPU version 362651054](https://www.kaggle.com/code/hungluongduc/hung-local2930-cpu-readback-20261027-v1?scriptVersionId=362651054)
actually mounted version 1, checked outer/member SHA/CRC, canonical job/stage
receipts, inputs/config/Source/Target bindings and saved checkpoints, then
recomputed **109 runs**: **55 scorable, 54 with zero scored horizons**. It passed
in **15.518 verification seconds / 29.1 whole-provider seconds**, Python 3.13.15,
Torch 2.11.0+cpu. GPU training/update counts for this verifier are zero. Peak RSS
and exact upload latency were not instrumented and are not invented. Private
storage UI showed 6.18 GB used of 214.75 GB before this upload; this is not GPU
quota evidence. The helper SHA remains
`78c4bd421ec0971023dca141ed8e81b22dbc97fe5c5855cd2511bfb30d1761be`.

At the completed-shard observation, **182/782 new jobs** are complete and all
**182 have remote readback**. The 69 historical Main runs remain separate.
Another **600 new jobs** remain outside completed-shard certification. Running
or partially written jobs are excluded. Kaggle GPU recovery version 362649842
and the original local CUDA worker continue their fixed disjoint allocations;
no new complete-job claim is inferred from their running metadata.

## Provisional metric handoff

[Partial results v3](hung-development-partial-20261027-v3/report.md) expands the
local/historical collection to **171 runs: 89 scorable and 82 zero-scored**.
This is 69 historical Main plus 102 new local jobs; the 80 completed Kaggle jobs
are outside this metric table. The CPU collection/aggregation took 61.707
seconds. Result SHA is
`d962a18a677ebcbc4d8a992e38ac9b5a907012317ce0f0d9d0f63042458ee2ab`;
catalog SHA is
`a27aad9974739cdf052207252e938a2d3148ffe72ee23d462b7213beabbf6f49`.

Only already-arrived saved labels are scored in original kWh units. Complete
24-hour errors are paired within station/seed, seeds are averaged within each
station, and stations receive equal weight within each history budget. Pairing
checks input, applicable initialization and label identities. Transfer gain and
negative transfer apply against Target-only; other references use generic
paired differences. Missing labels remain missing; cohorts differ between rows
and cannot establish a global ranking or model selection. Method equations and
cost distinctions remain in the [metrics/storage report](hung-development-metrics-storage-gate-20261027.md).
The [handoff comment on #10](https://github.com/HungLD9505/adaptive-retention-ev/issues/10#issuecomment-6430360268)
links the new evidence to the existing thesis draft and owner without replacing
that work or completing Final-dependent sections.

## CPU worker and validation

`tools/hung_result_worker.py` is an ordinary Python reporter, independent of
Codex monitoring and of the unchanged live training worker. Its immutable config
pins the collection, allocation, plan/partition and reporter/scorer sources.
It checks exact assigned local job sets, execute/verify exits, artifact SHA/CRC,
then uses the existing per-job/stage verifier and scorer. Every snapshot has a
create-only catalog, results, report and receipt. Partial/corrupt output, changed
inputs/source, failed verification or duplicate ambiguous snapshots stop the
reporter and preserve evidence. It has an OS lock, 120-second CPU receipt checks
and a 24-hour deadline. It neither starts training nor publishes to GitHub/cloud,
and makes no remote-readback or independent-review inference.

After tests passed, the reporter started as OS process **8124**, separately
confirmed live alongside training coordinator **35940**. It has already produced
and read back `through-shard_0030`: 171 runs / 89 scorable / 82 zero-scored.
All per-run metrics, coverage, costs and paired results equal the manual v3
observation. The only JSON value difference is the catalog provenance SHA;
independent snapshot files have their own collection/catalog identity. No
byte-identical archive/result claim is made. The snapshot receipt SHA is
`51832043fe62b6e242fcef9e941dce0f14a7fe4951de571e7b2cc7305a8a75b5`.

The clean-commit full suite passed **325 tests, one skip, exit 0**, 218.061 test
seconds / 224.389 wrapper seconds at `ae7d5ca`, with UTF-8 enabled. Both Ubuntu
and Windows CI passed at that commit. Full Ruff lint/format (121 files) and
`git diff --check` passed. Seven reporter tests cover exact receipts, missing or
failed terminals, wrong jobs/plan/partition, corrupt archives and partial or
corrupt snapshot readback. The actual 171-run reporter execution and separate
109-run Kaggle readback also passed.

[Machine-readable evidence](evidence/hung-local2930-readback-reporter-20261027.json)
contains receipt/spec/source pins, code/plan/config/input provenance, raw log
hashes, process/config identity, test terminal, CI links and acceptance scope.
Changed files: the new reporter and its test module, the local2930 readback
notebook, three partial-v3 report files, this report and its evidence JSON.
Commands: existing capsule build/verify(score=True), collection build,
aggregate_results, publish_report, focused/full offline tests, full Ruff,
diff check, and `python -u -m tools.hung_result_worker --config ... --watch`.
No existing data, checkpoint or report was overwritten.

Non-author approval, reviewer Kaggle access, #39 substitution acceptance,
remaining family/ablation/budget/seed coverage, paired cost/transfer analysis,
Block-7 fairness, an immutable Final lock and verified Final artifacts remain
outstanding. No PR merge, issue closure, main promotion or Final evaluation
occurred. `docs/SPRINT_PLAN.md` remains the sole schedule.
