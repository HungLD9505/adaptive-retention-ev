# Private Output-gated Development dispatcher — 2026-10-27

## Problem and prepared behavior

Recovery13 is already running (GPU362690241; controller362690145) and will independently CPU-read its completed private Output before certification. It does not dispatch groups14+. The old group03 relay failed during asynchronous Dataset publication, and CPU metric/export workers need later approved groups to become available without Codex polling individual jobs.

`tools/hung_kaggle_output_queue.py` adds a CPU state machine for the **existing five disjoint groups**:14–19,20–25,26–28,33–34,35–36 (380 jobs). No new forecasting method, tuning choice, dataset, seed, history budget, Source/Target identity or model44 code is introduced. Original group names/base paths and runtime plan/partition/jobset hashes are preserved so existing CPU metrics/readers/export manifests consume them unchanged. The canonical plan SHA is2d448d2584f65baf7e09445e013b4283314b08ea2cce855c6850e9fc12ba87ee; approved allocation12f5bc9ee402a806faedc89574a4e00c427c384335a3868668adf8ce7f93a0f2.

This is a phase handoff, not another schedule. `docs/SPRINT_PLAN.md` remains authoritative.

## Three-stage barrier

1. **Predecessor**: observe the exact first GPU version and an independently completed CPU readback. A missing proof is waited for through owned inventory; it is never treated as success or queried as an existing status. GPU failure or CPU failure stops the chain. The first prerequisite is the existing recovery13 plus its already-arranged `hung-g03-s13-readback-20261027-v1`; this dispatcher never submits13 or repeats8–12.
2. **GPU**: reread current free provider quota (allowed minus used minus reserved), disallow paid scaling and require `3600 + shard_count × 1810.4 × 1.25` seconds. The1810.4s per20-job shard estimate comes from the earlier bounded capacity evidence; it is a capacity guard, not a guaranteed completion forecast. Each original GPU execution program retains its own per-shard fresh quota,8GiB disk reserve, six-hour execution bound and28-check parity guard. Only the per-shard Dataset-publication call is replaced by a pending-durability notice. Complete private **Save & Run All Output version1** is required; draft saving/upload acknowledgement cannot satisfy the gate.
3. **Readback**: a separate CPU VM mounts exact completed Output version1. The pinned program checks archive bytes/SHA/ZIP CRC, runtime plan/partition and exact jobsets/exit receipts. No GPU/training/Final is enabled. A group is marked REMOTE_READBACK_VERIFIED only after that CPU program completes, then the next fixed group can start. Full scientific acceptance and metric coverage remain separate.

Private versioned Notebook Output is the persistent archive for this route. Keep every completed version/private artifact accessible; longer-term distribution and reviewer access still require the existing handoff. Independent CPU metrics subsequently performs full verify-only restoration and scoring. No inference about completion is made from GitHub metadata.

## Safe handoff and exact version

Create-only claims cover controller execution and every child submission. Claims cannot exceed50 URL-safe characters; provider errors and invalid sources preserve the returned identity. The controller's small receipts are atomic/no-overwrite hard-link publications: partial files remain when publication is interrupted, and an existing receipt is never replaced. At three hours the CPU controller submits a new CPU continuation with the exact group and predecessor/GPU/readback phase. Acknowledged GPU/readback children are not resubmitted. Twelve finite CPU relays bound the chain; timeout/failure stops without automatic retraining or identity replacement.

`hung_kaggle_queue.status` now explicitly requests **version_label=v1**, rather than latest. This spelling is verified in the official installed-as-data Kaggle CLI2.2.5 source (`_kernel_version_label` formats numeric1 asv1; bare1 gives404) and SDK0.1.38 request schema. Wheel files were downloaded from the standard package registry into project.cache for inspection only, not installed for credentials/runtime use. The same permitted kernel status endpoint is used; denied Dataset status/download endpoints are untouched.

## Immutable package

- Launcher:`experiments/hung_sprint2/kaggle_output_dispatch_cpu_v1.ipynb`; embedded SHA **f4a41b7689f6899979c9c1f76edae5bbea7c4080d7fb72d61f51f3ef6cb8f690**.
- Manifest:`experiments/hung_sprint2/kaggle_output_dispatch_manifest_v1.json`; canonical LF SHA **167eedc010cd9a216fa14eac96c35b80f1664f965b6e4de424e64f53492c7ac8**. It records every GPU/CPU program SHA and original runtime plan/partition/jobset hash, exact names/version and capacity guards. No Final execution.
- The initial CPU state is group index2,ordinal0,predecessor phase. It may wait for13's independent readback but cannot launch GPU14 before that passes.

These programs are **prepared, not yet submitted at this report's creation**. Actual native Save & Run version/terminal evidence must be recorded separately. The existing GPU13, metric continuation and export controller are not replaced.

## Validation and limits

28 focused offline tests passed: exact original group routes,380 unique jobs/no local overlap, both packaged program hashes and per-shard identity pins, all five GPU→CPU barriers, failed/missing predecessor, bad quota/NaN, error/partial receipts, acknowledged children across handoff, ordinal bound and exactv1 status request. An initial package-hash test failed because Windows default decoding misread UTF-8 source after notebook formatting; explicit UTF-8 decoding restored byte identity **without changing the expected hashes**. Original failed log is retained. No raw data, provider or training calls occur in these tests.

Repository-wide Ruff/diff checks pass. A full offline suite will run after freezing the implementation commit. Human independent review, Block7 disposition, #39 substitution approval, complete Development coverage and immutable Final lock remain unmet. No issue/PR is merged or closed.

Files: tools/hung_kaggle_output_queue.py; one status-version line in tools/hung_kaggle_queue.py; tests/test_hung_kaggle_output_queue.py and tests/test_hung_kaggle_queue.py; the two package files above; this report. Commands: focused `python -m unittest tests.test_hung_kaggle_output_queue tests.test_hung_kaggle_queue`, Ruff lint/format, `git diff --check`, deterministic package construction/AST verification and official wheel-source inspection.
