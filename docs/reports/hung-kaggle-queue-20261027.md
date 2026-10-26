# Bounded Kaggle CPU coordination — 2026-10-27

The interactive CPU capability probe passed all three actual operations: private
303-byte Dataset native readback with SHA/CRC, private CPU-only SDK submission,
and readback of the completed child's `completion.json` with SHA
`438e92e59a1da8c3e6d307a9110ddba4b8478a3a45945ddfeb9bff30fe77053d`.
[Child notebook](https://www.kaggle.com/code/hungluongduc/hung-api-dispatch-probe-20261027-v1)
is version 1. This uses existing Kaggle notebook authentication; no credential
was copied, created or read from the local user profile. Native attachment
succeeded in an interactive session; batch sessions require inputs at submission.
The official [Kagglehub implementation](https://github.com/Kaggle/kagglehub/blob/main/src/kagglehub/datasets_helpers.py)
distinguishes Dataset creation from version creation; the new queue calls only
the create endpoint for exclusive claims, with no conflict-to-version fallback.

`tools/hung_kaggle_queue.py` and its generated CPU notebook prepare the remaining
500 Kaggle jobs as groups 03–08: shards 8–13, 14–19, 20–25, 26–28, 33–34 and
35–36. They wait for the already-running 40-job group 02. Every GPU version
mounts version 1 of the exact payload Dataset and its completed predecessor's
Output. Before training it checks predecessor archive SHA/CRC, exact job-set
digest, expected relocated plan/partition SHA and successful execute/verify exit
codes, then repeats the frozen CPU/CUDA parity probe. Each shard checks fresh
quota with a one-hour reserve, eight GiB disk reserve and a six-hour group bound.
Model/dispatcher code remains `44b8532`; only this transport coordinator changes.

The CPU relay makes one submission attempt per unique group. Private create-only
Dataset claims separately guard submission, GPU execution and CPU relay execution.
An existing claim, uncertain API outcome, provider failure, partial archive or
hash mismatch stops the chain for reconciliation. No automatic retry creates
another version. The CPU relay hands its current fixed group index to a new CPU
version after three hours, so it does not depend on one long-lived CPU session.
At the last completed group it submits a separate CPU archive-readback version.
Kaggle, rather than an LLM, polls status once per minute. No notebook executes
the full matrix, no performance metrics determine allocation, and no Final
evaluation is submitted. Submission and execution of this newly prepared chain
are not claimed by this snapshot; subsequent provider evidence must establish
its actual start, terminal results and readback.

Local shard 0037 has now completed 20 jobs / 40 stages with execute and separate
verify exits 0. Its archive is 62,004,895 bytes, CRC passed, SHA
`53cdb816e107c30d546e2256e48842b2b8011be7cf96db97ffbae3ccbc4c2d40`.
The ordinary local worker advanced to shard 0038. Thus **62 new jobs** are
complete and receipt-verified at execution sites, **26** additionally read back
remotely. Group 02 remains running and is not included in that total. Remote
readback of local shards 0037/0039 and all remaining jobs are still outstanding.

Validation commands: `python -m unittest tests.test_hung_kaggle_queue -v`
passed eight offline cases covering fixed disjoint allocation, full readback,
corruption, relabelled jobs, nonzero verification exits, missing predecessors,
compilation of every generated GPU/CPU source, duplicate-claim rejection and
provider-failure stopping. Full Ruff and `git diff --check` pass. The earlier
clean full suite passed 287 tests / one skip; the enlarged suite must be rerun.
Changed files are the queue module, its eight tests, generated CPU coordinator
notebook, native CPU capability notebook, this report and group-02 readback report
with its evidence JSON. Independent peer acceptance, #39 substitution decision,
complete metrics and the Final lock remain open.
