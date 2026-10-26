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
an existing output root, tracked output path, changed code commit, dirty
tracked worktree, unsupported method, missing data, or less than 8 GiB free.
It creates a dispatch identity, separate job stage directories, one log per
stage, and split/resumed replay checkpoints. Each successful stage appends a
verified receipt to its log after checking the run manifest, checkpoint,
Development binding and event/forecast journal. Interrupted or failed outputs
remain for inspection.

For an interrupted run, `--execute --resume` accepts its existing output root
only when `dispatch_identity.json` exactly matches the pinned plan, code and
job/stage counts. It rechecks the current plan, selection, code, input and
dependencies before each stage. A completed stage is skipped only when its
directory, manifest, checkpoint, journal and log receipt all verify; a missing
or partial stage runs only if neither stage directory nor log exists. Any
partial or mismatched output stops the dispatcher and stays untouched for
review. Plain `--execute` remains create-only and refuses an existing root.
The resume flag does not bypass the capacity or scientific review gates.
The final command summary reports `new_stage_runs` and `verified_skips` so a
resume can be audited without counting skipped work as a new run.
Large run artifacts remain ignored.

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
# Only for an interrupted, previously approved run after inspecting its root:
python -m experiments.hung_sprint2.dispatch_matched --plan $plan --plan-sha256 $sha --execute --resume
```

The dry-run performs no training and writes no outputs. The `--execute`
command is shown for an approved run only; opening this document or running
the dry-run does not authorize execution. This dispatcher's stage logs and
hashes establish technical provenance, not independent scientific review or
an immutable Final lock. Use the independent replay verifier and station-first
paired-origin analysis before reporting method comparisons.
