# Actual CPU export pilot and hybrid v2 — 27 October 2026

Related: #22, #23, #10, #39; PR #72. `docs/SPRINT_PLAN.md` remains the schedule.

## Actual execution and readback

The [CPU export coordinator362673642](https://www.kaggle.com/code/hungluongduc/hung-portable-coordinator-00-20261027-v1?scriptVersionId=362673642)
is running the fixed seven-batch route. Its first, nonperformance-selected batch
uses receiver outputs for shards1/2/3 and the exact previously exported shard8
bytes. Static version1 inputs and the native multi-input SDK request worked.
No GPU, training fallback or Final data was used.

[Batch00 version362673711](https://www.kaggle.com/code/hungluongduc/hung-portable-batch00-20261027-v1?scriptVersionId=362673711)
succeeded in46.6s total; export verification/reconciliation took24.271s. Its output
is80 runs,42 scorable/38 zero-scored; the portable JSON is1,001,665 bytes,106 chunks,
SHA `48e9f3d28cc1c48890a72b97513e7d29de3e74e96878932802f81a0945d2811e`.
One batch does not establish P95 or whole-matrix runtime. The UI reports2.7MB total
output, including member exports, code and results. No GPU quota estimate is made.

The actual `python -m tools.hung_ingest_export` command checked the observed log's
SHA, canonical manifest SHA, exact allocation/batch/job set, decompression bounds,
all106 chunks and payload SHA, then recomputed coverage/paired results and wrote
the terminal readback receipt atomically. Existing-output and partial/corrupt
evidence protections remain active. This is technical readback, not independent
scientific approval. The coordinator may now wait/submit later fixed batches
without Codex monitoring individual jobs; later outputs still need readback.

During deployment, old browser handles lost debugger attachment. The running
server version was subsequently inspected through a fresh read-only tab in the
same Chrome connection. The existing run was used; no second submission occurred.
Earlier handoffs described execution as unverified during that interruption.

## Updated workload and metrics

302 of782 new jobs now have completed-shard certification:282 have remote readback,
and20 local shard4 jobs await remote readback. Another480 are outside certification.
This adopts actual receipts, not GitHub metadata or checkpoint existence.

GPU shard11 now has a private persistent317,485,131-byte archive and separate CPU
readback, SHA `959dbb76e407ac6c1ff7fce723fdc1510046280b1b473902ede231ff79bcfc6b`.
Upload took11.484s; upload plus readback51.728s. The GPU handle was directly observed
running while this receipt was collected. Local training/report workers were also
observed live. Local4's archive and report snapshot were independently SHA/CRC checked.

[Hybrid v2](hung-development-hybrid-20261027-v2/report.md) combines fresh local data
and the new80-job batch, replacing the earlier shard8-only collection rather than
adding it twice:

| Unique collection | Runs | Scorable | Zero scored |
|---|---:|---:|---:|
| Main69 + new local162 + new Kaggle80 |311|165|146|

There are134 paired cells and113 blocked pairs. Another60 completed new jobs are
outside this particular metric collection. These are partial cohorts, not a global
method ranking. Missing labels stay missing; zero scored days do not mean zero error.
Daily label-hash intersections and station-first seed aggregation are unchanged.
Transfer gain/negative transfer remain restricted to Source-using comparisons
against Target-only. Historical Main anchors are counted once; Block7 stays unmatched.

The companion JSON records code/manifest/allocation/log/export/result hashes,
runtime, receipt URLs and review status. `hung-hybrid-v2-provenance-20261027.json`
records model/input/selection/config/cell and all311 run/Source/Target/checkpoint
bindings. Raw archives, checkpoints and full daily-error exports remain outside Git.

## Validation and gates

Full offline suite:373 tests, one skip, exit0 on clean code head
`d434ffccbd708527819761150f88cd19883fb03b`; suite209.979s. Ruff check/format and
diff checks pass. The preceding373-test attempt had two calibration provenance
errors because Git reported a manifest dirty despite identical worktree/index/blob
bytes after LF normalization. An index metadata refresh restored clean status;
both targeted CPU/CUDA fixtures passed, then the complete suite passed unchanged.
Failed logs and the original creation bytes were preserved; no expected hash,
fixture or guard was relaxed. The new manifest uses canonical Git-matching LF SHA
`05e0d8158f71fc07d58c49c30a165aadce0b333b2f7df0f09b069d0b2f510ed5`.

PR70/71/72 still had no independent review submissions at the gate check. #39's
Kaggle/local substitution remains unapproved. Remaining experiments/metrics, full
baseline/ablation/budget/seed coverage, Block7 disposition, independent review and
immutable Final lock remain incomplete. No Final run, merge, issue closure or main
promotion is authorized by this handoff.
