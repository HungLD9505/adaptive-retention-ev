# Representative Development matrix plan generator

`python -m experiments.hung_sprint2.generate_matched_plan` writes a new
dispatcher plan and coverage record. It never runs training. The recipe and
every referenced file are SHA-pinned; the λ selection must be complete
Development evidence. A reviewer must approve the configs and explicit
reuse/rerun decisions before running the resulting plan. This tool handles
UrbanEV/SZH representative cells only, not CHARGED or Final.

## Recipe v1

Create a Git-ignored JSON file inside the worktree with these exact keys:

```json
{
  "schema": "hung-matched-plan-generator-v1",
  "scope": "development_only",
  "code_commit": "<clean reviewed HEAD>",
  "selection": {"path": "<accepted representative selection>", "sha256": "<SHA-256>"},
  "input_base": "<accepted Development input directory>",
  "lambda": {
    "selection": {"path": "<36-cell finite Development selection>", "sha256": "<SHA-256>"},
    "preflight": {"path": "<predeclared calibration preflight>", "sha256": "<SHA-256>"},
    "roots": [
      {"index": 0, "path": "<lambda-0 matrix root>", "matrix_sha256": "<SHA-256>",
       "config": {"path": "<lambda-0 config>", "sha256": "<SHA-256>"}}
    ],
    "chosen_lambda_low": 0.1
  },
  "proxy_profile": {"path": "<finite four-recipe Development profile>", "sha256": "<SHA-256>"},
  "proxy_selection": {"path": "<108-run provisional Development selection>", "sha256": "<SHA-256>"},
  "proxy_plan": {"path": "<nine-cell proxy calibration plan>", "sha256": "<SHA-256>"},
  "proxy_runs": {"path": "<108-row proxy runs.jsonl>", "sha256": "<SHA-256>"},
  "configs": {
    "main": {"path": "<config>", "sha256": "<SHA-256>"},
    "online_best": {"path": "<config>", "sha256": "<SHA-256>"},
    "without_confidence": {"path": "<config>", "sha256": "<SHA-256>"},
    "fixed_retention": {"path": "<config>", "sha256": "<SHA-256>"},
    "full_finetuning": {"path": "<config>", "sha256": "<SHA-256>"},
    "source_error": {"path": "<config>", "sha256": "<SHA-256>"},
    "uncertainty": {"path": "<config>", "sha256": "<SHA-256>"},
    "parameter_retention": {"path": "<config>", "sha256": "<SHA-256>"},
    "block7": {"path": "<config>", "sha256": "<SHA-256>"},
    "block28": {"path": "<config>", "sha256": "<SHA-256>"},
    "no_source": {"path": "<config>", "sha256": "<SHA-256>"}
  },
  "drift_configs": [
    {"cell": "b7s7e2264",
     "config": {"path": "<cell-specific drift config>", "sha256": "<SHA-256>"}}
  ],
  "sources": [
    {"budget": 7, "seed": 7,
     "checkpoint": {"path": "<Source checkpoint>", "sha256": "<SHA-256>",
                    "run_manifest_sha256": "<SHA-256>"}}
  ],
  "targets": [
    {"cell": "b7s7e2264", "variant": "main", "mode": "reuse",
     "checkpoint": {"path": "<target checkpoint>", "sha256": "<SHA-256>",
                    "run_manifest_sha256": "<SHA-256>"}},
    {"cell": "b7s7e2264", "variant": "parameter_retention", "mode": "create",
     "checkpoint": null}
  ],
  "existing_runs": [
    {"job_id": "main_b7s7e2264", "action": "reuse",
     "run_manifest": {"path": "<completed replay run_manifest.json>", "sha256": "<SHA-256>"},
     "reason": "Reviewed original run identity"},
    {"job_id": "block7_b7s7e2264", "action": "rerun",
     "run_manifest": null, "reason": "Original code identity differs"}
  ],
  "output_root": "<new Git-ignored run directory inside this worktree>"
}
```

The abbreviated arrays above show the row shapes, not a complete recipe.
Provide all nine Source budget/seed pins; 69 cell-specific Drift config pins;
all 69 cells times five target
variants (`main`, `fixed_retention`, `full_finetuning`,
`parameter_retention`, `no_source`); and an explicit reuse or rerun decision
for every one of the 69 main and 69 block-7 jobs. `create` means the dispatcher
will build a fresh target under the new output root. It never silently uses an
old target. Reuse requires the checkpoint and completed run manifests to match
input, code sources, schedule, seed, λ, and SHA. Incompatible old runs remain
preserved but must be declared `rerun`; they cannot be relabeled.

Each Drift config must pin that cell's first-history reference and may differ
from the main config only in the Drift rule, proxy thresholds/mapping, and
reference. The generator recomputes each of the 23 budget/entity references
from the first accepted Development forecast history, checks the pinned
values for all three seeds, and records the origin IDs in coverage. The other config comparison
keeps input release, seeds, Source training, target
batch/learning schedule, replay origins and update settings matched. Block-7
and block-28 configs may change only block length from the 14-day main config.
The parameter config binds the selected positive λ to target adaptation,
replay initial level and first nonzero candidate. Proxy recipes and drift
reference must already be fixed in their reviewed configs; this generator
does not choose them from outcomes.
Provide all four lambda roots/configs, not only index 0 in the example. The
generator authenticates each of 36 replay manifests/checkpoints, compares
the selected cell MAE with its manifest and declared origin hashes across
lambda candidates, then recomputes station/seed/budget
means, the ranking and the tie-broken λ winner. It also authenticates the
proxy plan and all 108 pinned run rows, then calls the existing proxy selector
to re-verify the replay evidence and compare the entire provisional selection.
That proxy verification replays the Development chronology on CPU and may take
substantial time; it is read-only and writes no training output.
It checks the three proxy thresholds and λ-bin mappings against the
hash-pinned four-recipe profile and its 9-cell/108-run provisional Development
selection. That selection remains conditional evidence, not approval of the
method or a Final lock.

The generator emits 23 deterministic Seasonal jobs and 69 jobs per other
method/variant. Fixed λ aliases the exact Fixed Retention run. If Without
Confidence uses `delta=0` with the otherwise identical Online Best config,
it aliases Online Best, yielding 920 declared jobs. A positive delta yields
69 distinct Without Confidence jobs and 989 declared jobs. The two block
variants and main method are included; verified old main/block-7 runs appear
only in the coverage record and are omitted from the executable plan. The
coverage record states the scheduled count, reuse pins, rerun decisions,
aliases, and resulting plan SHA.

## Create and inspect

```powershell
$env:PYTHONUTF8 = '1'
$recipe = '.cache/matched-recipe-v1.json'
$sha = (Get-FileHash $recipe -Algorithm SHA256).Hash.ToLowerInvariant()
python -m experiments.hung_sprint2.generate_matched_plan `
  --recipe $recipe --recipe-sha256 $sha `
  --output .cache/matched-plan-v1.json `
  --coverage-output .cache/matched-coverage-v1.json
$planSha = (Get-FileHash .cache/matched-plan-v1.json -Algorithm SHA256).Hash.ToLowerInvariant()
python -m experiments.hung_sprint2.dispatch_matched `
  --plan .cache/matched-plan-v1.json --plan-sha256 $planSha
```

The last command is a dry-run. GPU execution still requires an explicit
`--execute`, a separate capacity review, peer approval, and artifact/report
handoff. See [the dispatcher contract](MATCHED_DISPATCHER.md).
