# Fixed CPU metric export batches — 27 October 2026

Related: #22, #23, #10 and PR #72. `docs/SPRINT_PLAN.md` remains the schedule.

The existing metric receiver queue verifies Kaggle training outputs automatically,
but exporting each resulting daily-error collection through Codex would repeat UI
and log-transfer work. `tools/hung_kaggle_export_batches.py` prepares seven disjoint
80-job CPU batches over the existing 560-job Kaggle route. It excludes every local
shard. The original 20-job shard8 export is reused by its exact verified SHA.

The allocation is `experiments/hung_sprint2/kaggle_export_batches_v1.json`, SHA
`a97c78a1584db41deab1dc029b64904bdfd4db94c52aca3e7ba3f9ea4d9f3c85`.
Its canonical batch-list SHA is
`5bf1235b00b69ae5693d67488bcdac50cde38f80c20012d3ad397ceb73a62667`.
Every shard's expected job-set SHA was checked against the existing execution
queue's pinned values. Model code, plan, partition, Source/Target identities,
configuration, input data and historical runs are unchanged.

Each producer mounts at most four immutable receiver version1 outputs, checks
the receiver/helper/scorer and runtime-plan/partition pins, and rechecks saved
checkpoint/proof hashes through the already-tested portable exporter. Disjoint
expected job sets and the existing station-first pairing code validate the combined
collection. Small daily-error JSON, summary, manifest and compressed transport
chunks are saved. No checkpoint is trained, no Final labels are opened and no GPU
request is made. GPU assertions also guard the producer environment.

The CPU coordinator observes owned resources before requesting status of future
receiver handles. It submits a batch once only after all four inputs complete;
the first producer must complete successfully before later producers can submit.
Unexpected states or access errors stop the chain. Create-only remote claims and
version1 assertions prohibit duplicate execution or overwriting an existing run.
Relays hand off after three hours, bounded to twelve relays/36 hours. These waits
are performed by Python rather than Codex. Waiting does not imply completion.

Ten offline tests pass: fixed coverage/overlap rejection, private CPU-only request
construction, exact source pins and compilation, immutable allocation, inventory
gating, failed-receiver/failed-pilot stops, handoff without duplicate submission,
and honest CPU-completion receipts. The full suite and live SDK/multi-input pilot
still need separate evidence after freezing the source. At this report's creation,
the notebook and allocation are prepared; no batch execution/readback is claimed.

Batch completion metadata is not scientific acceptance or independent hash
readback. Outputs still need exact SHA-checked ingestion before entering the
central hybrid report. Main anchors must be counted once. Full Development and
paired coverage, Block7 disposition, peer review, #39 alternative approval and
immutable Final lock remain pending. No autonomous merge or issue closure occurs.
