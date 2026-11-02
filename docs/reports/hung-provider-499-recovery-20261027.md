# Dataset-create uncertainty and bounded recovery â€” 2026-10-27

## Actual evidence

Group03 version 362635685 stopped on HTTP499 from CreateDataset after uploading
shard 0008. Owner UI subsequently showed the private Dataset at version 1 with
both original files. No Dataset creation or training retry was performed.
The original receipt records 20 jobs, execute/verify exit 0, 2,087.102 execution
seconds and a 74,362,442-byte archive, SHA
`a49fc9c6c56b5e6cdcf54bb1af15d05cb511d017f3be3cb4abfb41f17dc151e8`.

[Separate CPU version 362647578](https://www.kaggle.com/code/hungluongduc/hung-shard0008-reconcile-cpu-20261027-v1?scriptVersionId=362647578)
actually mounted [Dataset version 1](https://www.kaggle.com/datasets/hungluongduc/hung-dev-shard0008-44b8532-20261027-v2/versions/1),
verified receipt exits, exact plan/partition and job-set pins, archive size/SHA,
all ZIP CRCs, dispatch identity and exact 20 measurement identities. It passed
in 15.1 whole-provider seconds; no training or Final evaluation occurred.
This reconciles the uncertain write. HTTP499 itself is never completion proof.

The first recovery attempt, GPU version 362648315, stopped before materializing
or training because its generated claim still named the old execution. The
create-only lock refused it. CPU relay version 362648279 then observed ERROR and
stopped. Both failures and all claims remain preserved. A regression test now
examines the emitted claim argument, including the builder/runtime namespace
boundary that caused this bug.

## Changes and recovery boundary

The storage adapter handles HTTP499 only by submitting a separate CPU reader
against the expected immutable Dataset version and exact original receipt.
It never repeats CreateDataset or training, never falls back to a new Dataset
version, and never adopts a 403 or another failed write. A failed readback stops
the chain without a VERIFIED receipt. Tests cover successful reconciliation,
readback failure, other upload errors, corrupt archives and duplicate avoidance.

The prepared recovery source preserves model code `44b8532`, original group03
absolute paths and derived plan/partition pins. It carries the verified shard
0008 receipt/archive unchanged into the new Output, and executes only fixed
shards 0009â€“0013. The CPU launcher requires both original failed processes and
the first recovery to be terminal ERROR, and the separate readback COMPLETE;
it verifies shard 0008 again and checks current free GPU quota before submission.
Later groups still require per-shard SHA/CRC readback, disk/quota reserves and
bounded runtime. Their allocation is unchanged. The verifier selects canonical
receipt/archive pairs; upload mirrors with a different archive name cannot
make a valid shard ambiguous. Two canonical copies still fail closed.

No full-matrix execution, historical relabelling, model-method change or Final
selection is introduced. Recovery does not imply non-author scientific review.

## Workload snapshot

Local shards 0029 and 0030 each completed 20 jobs, separate verifier exit 0 and
archive SHA/CRC passed again during this handoff. Their archives are 42,296,117
bytes / SHA `77036b62c6174bbaceb38f27ca5119fa325d63daf508e2711ad15f3e41c43aee`
and 62,014,181 bytes / SHA
`479def89f1ca1cab3b0f74ad7a24319dfafdbe8219b7bffaf051a6b217bc6c9d`.
Their execution walls were 1,798.515 and 2,932.994 seconds respectively. Both
still need remote readback. The original local Python worker remains live;
partial running shards are excluded from completed counts.

The snapshot is **182/782 new jobs complete at shard boundaries**, including
**142 remote-readback jobs** and **40 awaiting remote readback**. Another **600**
are outside completed-shard certification: 120 local and 480 Kaggle. The 69
historical Main runs are separate VERIFIED_REUSE evidence. Block-7 remains
EXTERNAL_COMPLETE_UNMATCHED. No new MAE/RMSE ranking is claimed by this phase.
Previously published partial metric tables retain their stated subset scope.

## Validation and unresolved gates

Full offline suite: **318 tests, one skip, exit 0**, 207.765 test seconds /
214.176 wrapper seconds at clean commit `2a91a64`, with Python UTF-8 enabled.
Full Ruff lint/format (118 files) and diff checks passed. Earlier v8/v9 failures
are retained: provenance fixtures require an unchanged clean checkout, and
project-local temporary paths require UTF-8 on this Windows environment. No
validation guard was weakened to make those failures pass. Ubuntu CI passed at
`2a91a64`; Windows was still running when observed.

The first recovery CPU launcher observed 77,760.624 available GPU seconds and
required 14,915 seconds before submitting its bounded group. This is historical
quota evidence, not a current balance or assurance that all remaining jobs fit.
The next launcher rechecks quota. D: had 12,392,382,464 free bytes at the local
snapshot, above the 8 GiB worker reserve. Failed attempts are retained in the
cost evidence. Upload acknowledgement time is unavailable for the HTTP499
write; no value is invented. Peak memory was not newly instrumented here.

Files changed: `tools/hung_kaggle_storage.py`, `tools/hung_kaggle_recovery.py`,
`tools/hung_kaggle_queue.py`, their three test modules, the shard0008 CPU
reconciliation notebook, recovery CPU notebooks v1/v2, this report and its JSON.
Commands: focused unit tests; full offline suite; full Ruff lint/format;
`git diff --check`; private CPU Save & Run All; create-only SDK GPU submissions.
All original data, outputs and reports remain preserved. Large artifacts stay
in private persistent storage; GitHub stores code and small evidence only.

[Recovery CPU version 362649780](https://www.kaggle.com/code/hungluongduc/hung-development-recovery-cpu-20261027-v2?scriptVersionId=362649780)
was submitted only after the full offline suite passed. It observed **77,750.532
available GPU seconds**, required 14,915 seconds and received a version-1
submission acknowledgement. [GPU recovery version 362649842](https://www.kaggle.com/code/hungluongduc/hung-matched-group03-recovery-20261027-v2?scriptVersionId=362649842)
actually started on Tesla T4, Torch 2.11.0+cu128, model code `44b8532`. Its new
execution claim, exact shard0008 SHA/CRC readback and all 28 CPU/CUDA parity
checks passed (7.673 parity seconds). It had
17,988,767,744 free disk bytes and 15,636,037,632 device-memory bytes. New job
completion is not yet certified by this snapshot.
[Machine-readable evidence](evidence/hung-provider-499-recovery-20261027.json)
records original artifacts, terminal results, hashes and remaining gates.

Reviewers still need authorized Kaggle usernames/access. #39 remains open until
a non-author accepts the provider-substitution request. Full family/ablation,
budget/seed coverage, station-first paired metrics/negative transfer, remaining
readbacks, independent Block-7 fairness decision, peer approval and an immutable
Final lock remain outstanding. #10 Results/Discussion/Limitations stay partial
until those gates pass. No merge, issue closure or main promotion occurred.
`docs/SPRINT_PLAN.md` remains the only schedule.
