# Development queue start evidence — 2026-10-27

[Private Kaggle CPU coordinator version 362629668](https://www.kaggle.com/code/hungluongduc/hung-development-cpu-coordinator-20261027-v1?scriptVersionId=362629668)
is actually running without an accelerator. Its log shows the initial 107-byte
private execution-claim upload. It waits for existing group 02; the first
automatically submitted GPU group has not yet been observed. The chain is
prepared for 500 subsequent jobs in six bounded groups, and must stop on any
claim, provider, quota, archive or parity failure. A running coordinator is not
proof those jobs completed.

The separate interactive capability probe passed private Dataset readback,
CPU-only child submission, terminal completion and exact completion-file SHA.
The initial batch probe failures remain retained. The successful interactive
probe and its captured-log hash, code/notebook SHA pins, local shard-0037 receipt
and test-log SHA appear in [this evidence JSON](evidence/hung-development-queue-start-20261027.json).

Current completed new workload is **62/782 jobs**, with **26** additionally
verified by remote archive readback. Local shard 0038 is running in the ordinary
Python queue, with 180 jobs remaining there. Kaggle group 02 has 40 running jobs;
another 500 are assigned to the conditional CPU relay. Historical reused and
unmatched runs retain their previous identities and status. No running job is
included in completed totals.

The enlarged clean-commit full suite passed **295 tests, one skip, exit 0**,
in 218.060 test seconds / 225.231 wrapper seconds. Commands were
`python -m unittest discover -s tests -v`, full-repository `ruff check .`,
`ruff format --check .`, and `git diff --check`. All passed. No model code changed
from the already validated dispatcher commit `44b8532`; coordinator commit
`2c5e739` adds the provider orchestration only. Latest observed CI at that head
has Ubuntu passing and Windows still in progress; this snapshot does not infer
the later CI outcome.

Files changed in this follow-up are this report and its evidence JSON. The
preceding phase's queue module, tests and two notebooks are inventoried in
[the queue report](hung-kaggle-queue-20261027.md). No issue was closed or PR merged.
Outstanding work: finish Development jobs, independently read back remaining
archives, aggregate paired station-first metrics and coverage, obtain peer
acceptance and the #39 provider-substitution decision, then obtain an immutable
Final lock before running Final or completing #10 Results/Discussion/Limitations.
