# Bounded Development allocation — 2026-10-27

The [immutable allocation evidence](evidence/hung-development-allocation-20261027-v1.json)
maps every job in the already pinned 782-job partition exactly once:

| Route | Jobs | State at allocation |
|---|---:|---|
| Completed local pilot | 6 | Execution and local verification passed; private provider readback passed |
| Local CUDA | 216 | Shard 0039 (16 jobs) executing; 200 jobs queued behind its terminal verification |
| Kaggle T4 | 560 | Shard 0001 (20 jobs) executing; remaining 540 require first-shard capacity/readback/quota release |

The queue SHA is `12f5bc9ee402a806faedc89574a4e00c427c384335a3868668adf8ce7f93a0f2`.
Code/config/input/Source/Target and parent plan/partition pins remain unchanged.
Routes use fixed whole shards and measured artifact footprint, never MAE/RMSE.
Larger frozen-Source/target-only outputs stay on Kaggle. Proposed Kaggle sessions
contain at most 120 jobs and retain per-shard archives/receipts; no notebook runs
the entire matrix. Later sessions must verify their predecessors' durable outputs
and current quota before release. This report does not certify their feasibility
or execution while the first T4 shard remains live.

Local free space observed was 13,207,162,880 bytes. The conservative estimate for
the 200 queued lightweight jobs is 3,476,262,600 incremental bytes: 200 times the
largest measured lightweight pilot output (5,793,771 bytes), twice for expanded
files plus ZIP, times a 1.5 margin. This extrapolation is not a measured result.
The existing 8 GiB dispatcher reserve remains mandatory before every stage; the
worker also checks it before each shard. Unexpected growth stops execution and
preserves all outputs. No historical artifact, temporary restore, or raw input was
deleted to obtain this capacity.

`tools/hung_local_worker.py` validates the pinned queue, full disjoint partition,
global routes, worker source hash and successful pilot storage/parity evidence.
It waits for actual shard-0039 exit/verification codes and SHA/CRC archive receipt,
then executes the ten explicit remaining local shards with `--resume`, verifies
each completed shard through a separate dispatcher invocation, creates a ZIP and
publishes a create-only receipt. A partial/corrupt output, changed queue, failed
barrier or low disk stops the worker. There is no LLM call or per-job agent.
Local SSD persistence is recorded separately from remote archive readback, which
is still required for these subsequent shards.

The user's current instruction authorizes Kaggle/local Development execution.
The queue does not supply independent scientific acceptance, a #39 substitution
decision, merge approval or a Final lock. Those gates remain pending.

Validation: ten focused offline provider/queue tests passed, including duplicate
or foreign assignment, changed plan, dry-run without execution, missing terminal
barrier and stop/preserve behavior. Full-repo Ruff check/format and diff checks
passed. The preceding clean full suite passed 282 tests with one skip; the five
new queue tests increase the subsequent CI suite to 287. Queue dry-run exited 0
and listed precisely the ten assigned shards. The ordinary Python worker was
started with a real process record and waits on the current shard's terminal
receipt. It has not yet certified the 200 queued jobs as complete.
