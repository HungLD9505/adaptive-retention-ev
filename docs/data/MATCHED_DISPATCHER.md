# Explicit matched Development dispatcher

`python -m experiments.hung_sprint2.dispatch_matched` accepts a JSON plan and
prints the allowlisted stage commands by default. It executes only with
`--execute`. It does not choose a cohort, method, lambda, proxy mapping, or
result. The plan must be reviewed and hashed before execution. The dispatcher
does not read Final inputs.

## Plan v1

Create a new Git-ignored JSON file in the current worktree with exactly these
top-level fields:

```json
{
  "schema": "hung-matched-development-dispatch-v1",
  "scope": "development_only",
  "code_commit": "<this worktree's reviewed HEAD SHA>",
  "selection": {"path": "<absolute predeclared selection JSON>", "sha256": "<sha256>"},
  "input_base": "<absolute accepted Development input directory>",
  "budgets": [7, 14, 28],
  "seeds": [7, 11, 19],
  "configs": [{"id": "main", "path": "<absolute reviewed config JSON>", "sha256": "<sha256>"}],
  "cells": [{"id": "szh7seed7entity2264", "budget": 7, "seed": 7,
             "entity_id": "2264", "input_manifest_sha256": "<sha256>"}],
  "jobs": [{"id": "best7seed7entity2264", "cell": "szh7seed7entity2264",
            "config": "main", "method": "online_best_lambda", "device": "cuda",
            "source": {"path": "<absolute Source checkpoint>", "sha256": "<sha256>"},
            "target": {"path": "<absolute compatible target checkpoint>", "sha256": "<sha256>"}}],
  "output_root": "<new Git-ignored absolute directory in this worktree>"
}
```

Every cell must be a unique UrbanEV/SZH Development representative in the
hash-pinned selection. The accepted input manifest and all its artifacts are
rehash-checked. Every job names one declared cell and config. Jobs cannot
duplicate a method/config/cell; deterministic Seasonal Naive is scheduled
only once per entity/budget rather than counted as three independent seeds.

Methods are the existing controller rules (`confidence`,
`online_best_lambda`, `without_confidence`, `fixed_retention`,
`full_finetuning`, `source_error`, `uncertainty`, `drift`) or the existing
single-policy methods (`seasonal_naive`, `target_only`, `frozen_source`). The
controller method must equal the config's explicit `replay.selection_rule`
(default `confidence`). Proxy settings, including a Drift reference, belong
in that hash-pinned config; the dispatcher never derives them from scores.
Source and compatible target checkpoints must be named with exact SHA-256.
Generated plans also include `run_manifest_sha256` for each reused Source or
target checkpoint; the dispatcher rechecks those manifest bytes before every
stage.
For a controller needing fresh target adaptation, set `target` to `null`;
the dispatcher creates a new target stage using that config. Target-only
always creates its own seeded initial stage and has `source: null,
target: null`. Seasonal Naive also uses both nulls and CPU. Frozen Source
uses its Source checkpoint and `target: null`.

The dispatcher validates existing Source/target checkpoint manifests and
input bindings, config and input hashes, seed, initialization, retention kind,
and target lambda. Source-using jobs in one budget/seed share the same Source
checkpoint; Seasonal Naive and Target-only do not use Source. It requires a
complete one-pass Source schedule and the full target adaptation prefix under
the declared batch size and learning rate, including zero optimizer steps for
a `source_checkpoint_only` entity. The existing controller CLI requires
`--steps 1` for that zero-prefix case, but receives no target examples and
records `steps: 0`. It rechecks plan, selection, code identity, and dependency
hashes before every stage. It refuses
an existing output root without explicit resume, tracked output path, changed code commit, dirty
tracked worktree, unsupported method, missing data, or less than 8 GiB free.
It creates a dispatch identity, separate job stage directories, one log per
stage, and split/resumed replay checkpoints. Interrupted or failed outputs
remain for inspection. The default refuses existing roots; explicit
receipt-based continuation is described below. Large run artifacts remain ignored.

## Receipt-based continuation and fixed shards

The default remains create-only. `--resume` accepts an existing root only when
its dispatch identity matches the exact plan SHA, complete partition SHA,
code commit and executed sources. A nonblocking OS file lock serializes the
root across processes and shards; process death releases the lock. Do not
delete a lock file to force execution.

Each successful stage is verified before an atomic, create-only receipt pins
its full output tree, log, command, cell, input, config, Source and target
declarations. A job receipt binds its stage receipts. Resume verifies the
whole selected shard before starting missing stages, then rechecks dependencies
before each stage. Only receipted stages are skipped. A missing receipt with
an existing log/output, changed byte, added artifact, changed plan or corrupt
receipt stops execution and preserves the evidence. Completed stages are never
adopted merely because their files exist. A job receipt can be reconstructed
from all verified stage receipts after interruption between those two writes.

Receipts use fsynced temporary files and atomic hardlink publication. This
requires a local filesystem supporting hardlinks (for example NTFS/ext4).
Unsupported publication fails while creating the dispatch identity, before
training. Use provider-local execution storage; remote upload and independent
hash/CRC readback are a separate required durability gate. These receipts alone
do not prove remote backup or independent review.

`dispatch_measurement.json` records actual subprocess wall time, local hash
readback time and output bytes. Device/VRAM and model costs remain in the
existing stage manifests. Remote transfer cost and provider quota must be
measured separately. Dry-run caches repeated input/source-schedule reads only
within its invocation and rehashes distinct inputs at the end; execution does
not cache dependency validation across stages.

Prepare a complete partition without training:

```powershell
python -m tools.hung_e2e_gate shards --plan $plan --plan-sha256 $sha `
  --jobs-per-shard 20 --output .cache/shards-v1.json
$shardsSha = (Get-FileHash .cache/shards-v1.json -Algorithm SHA256).Hash.ToLowerInvariant()
python -m experiments.hung_sprint2.dispatch_matched --plan $plan --plan-sha256 $sha `
  --shards .cache/shards-v1.json --shards-sha256 $shardsSha --shard-id shard_0000
```

The partition must contain every parent-plan job exactly once; duplicate,
missing and unknown job IDs fail. The entire partition SHA remains fixed
through continuation. A separately reviewed pilot may be its own first shard,
with every remaining job retained in the other shards. No performance-based
pilot selection is permitted.

After explicit execution approval, use the same arguments with `--execute`;
add `--resume` for later shards or continuation. To authenticate a complete
shard without training, use `--resume --verify-only` instead of `--execute`.
Verification requires all stage and job receipts and returns failure for any
missing or changed evidence. It does not launch model processes.

`python -m tools.hung_e2e_gate ledger --help` documents the read-only ledger
worker. It consumes SHA-pinned plan/recipe/coverage, authenticates original
Main/Block-7 manifests/checkpoints/journals and compares exact model,
optimizer, scale and RNG payloads. Its state comparison is a fairness
diagnostic; it never reclassifies historical Block-7 as matched automatically.

## Commands

From the plan's worktree:

```powershell
$env:PYTHONUTF8 = '1'
$env:TEMP = (Resolve-Path .).Path
$env:TMP = $env:TEMP
$plan = '.cache/matched-plan-v1.json'
$sha = (Get-FileHash $plan -Algorithm SHA256).Hash.ToLowerInvariant()
python -m experiments.hung_sprint2.dispatch_matched --plan $plan --plan-sha256 $sha
# Review every printed command, artifact identity, method and output root.
# A separate explicit decision is required before GPU execution:
python -m experiments.hung_sprint2.dispatch_matched --plan $plan --plan-sha256 $sha --execute
```

The dry-run performs no training and writes no outputs. The `--execute`
command is shown for an approved run only; opening this document or running
the dry-run does not authorize execution. This dispatcher's stage logs and
hashes establish technical provenance, not independent scientific review or
an immutable Final lock. Use the independent replay verifier and station-first
paired-origin analysis before reporting method comparisons.
