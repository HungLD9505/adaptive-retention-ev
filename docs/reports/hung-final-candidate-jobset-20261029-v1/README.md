# Hùng UrbanEV Final first-three-ID jobset candidate — 29 October 2026

**Status: candidate only; no executable lock, no Final run.** This packet is derived from the [outcome-blind metadata preflight](../hung-final-metadata-preflight-20261029-v1/README.md) and [measured resource scenarios](../hung-final-resource-preflight-20261029-v2/README.md). It gives the new Hùng Final runner an exact reviewable 360-job identity and stage-argument draft. It does not select a Final cohort for execution or use any Final label, forecast, schedule or score file. [#23 comment 6476049006](https://github.com/HungLD9505/adaptive-retention-ev/issues/23#issuecomment-6476049006) is a Hùng-specific lead pre-execution exception, **not** peer or scientific approval.

## Outcome-blind identity and method coverage

The first **three** of 373 Final-role UrbanEV/SZH IDs under the already published `SHA256("hung-final-urban-candidate-v1|" + entity_id)` order are **2118, 2579 and 2534**. They were chosen by ID hash, not availability, error or metric. The candidate keeps these same IDs for budgets 7/14/28 and seeds 7/11/19. It records the other **370 UrbanEV IDs** as outside this bounded option and all six CHARGED cities as missing Hùng input/Source/jobset scope; it never calls the option full E2E completion.

[candidate_jobset.json](candidate_jobset.json) has exactly **360 sorted unique physical job IDs**: 3 entities × 3 budgets × **40 physical jobs already spanning the three seeds**. Each entity × budget has 13 seeded variants × 3 runs plus one deterministic Seasonal Naive run at seed 7. [candidate_coverage.json](candidate_coverage.json) declares the seed-11/19 Seasonal Naive views as aliases of its seed-7 execution, never as two extra physical runs. The 14 variant labels are Main, Block7, Block28, no-Source initialization, parameter retention, Target-only, Frozen Source, Full Fine-tuning, Fixed Retention, Online Best, Source Error, Uncertainty, Drift and Seasonal Naive. `fixed_lambda` aliases Fixed Retention; with the frozen zero-δ config, `without_confidence` aliases Online Best. The five ablation categories and nine baseline families are represented without double-counting artifact identities. The coverage validator reports `incomplete` because of the explicitly declared UrbanEV/CHARGED scope shortfalls, not because deterministic aliases were counted as missing runs.

Each job binds dataset/city/ID, budget, seed, variant, actual runner method, planned input-run path, exact input-manifest SHA and applicable Source checkpoint SHA. New Final Target initialization has `target_checkpoint_sha256: null` until a create-only stage receipt records the actual bytes; this candidate never backfills the lock. Nine reused Development Source checkpoint candidates and adjacent manifests were separately hashed in the v1 preflight. Their reuse is proposed, not automatically accepted.

## Stage plan and exact blockers

[candidate_execution_plan.json](candidate_execution_plan.json) contains the matching 360 stage records. The target-init step count follows the executed Development rule from the selected entities' **initial-trainable metadata** and the pinned batch size; it does not inspect labels or choose IDs from that count. The 90-origin replay/controller/proxy numbers come from the hash-pinned Development configs listed in [source_config_bindings.json](source_config_bindings.json). For Drift, all 69 Development cell configs had the same thresholds/levels after removing their per-entity reference mean/scale. These numbers were **not copied** from a Development entity to a Final entity.

Two concrete fields remain unresolved for each of the **27 Drift jobs**: `replay.drift_reference_mean` and `replay.drift_reference_scale`, recorded as `null` and enumerated in [missing_stage_args.json](missing_stage_args.json). The executed Development rule derives them from the first causal issued history, so a future lock must pin that deterministic rule and record the post-lock derivation before Drift execution. Filling them with another entity's constants would change the method. The planned `input_run` directories are derived exactly from the input ZIP member prefixes, but **none is materialized**. A post-lock create-only extractor must restore the pinned ZIP bytes at those paths before any runner validation or label access; this candidate does not extract the ZIP. The correctness-based head/bootstrap contract, provider/device capacity, output root, immutable code/analysis lock and CHARGED scope also remain open.

| #15 requirement / boundary | Candidate evidence | Remaining shortfall |
| --- | --- | --- |
| UrbanEV/SZH Final IDs | 3 hash-ranked IDs × all 7/14/28 budgets | 370 eligible Final IDs outside this bounded option; generalization scope is narrow |
| Fixed comparison seeds | 7/11/19 for every seeded variant; Seasonal Naive one physical run with declared aliases | No missing physical seed job inside this 3-ID option |
| Nine baselines + five ablation categories | 14 variant labels, 40 physical jobs per entity × budget | Block7 historical Development equivalence and shared parity still unapproved; candidate does not certify scientific acceptance |
| Six CHARGED cities | No Hùng Final input or Source identity in repository-local package | All six separate city scopes remain undelivered; Qyroven's runs cannot be relabeled |
| Final execution/restore | 360-row schema-shaped jobset and plan; 9 Source candidate hashes | Input directories absent, 27 Drift reference pairs unresolved, runner/contract/lock/provider not finalized; no Final output |

The [resource preflight](../hung-final-resource-preflight-20261029-v2/README.md) extrapolates this 3-ID method matrix to **3.808 observed-p95 Development-stage hours** and **12.165 GB raw-plus-ZIP with a 1.5 multiplier**, excluding Source/provider/CHARGED and without a capacity guarantee. Local D had only 3.827 GB free, below its 8 GiB dispatch reserve; Kaggle quota remains unknown. Do not dispatch this candidate.

## Checks and file identities

Reproduce from repository root with a **new** output directory and the pinned local Development payload:

```powershell
python -m tools.hung_final_candidate_jobset --root . --output-dir docs/reports/hung-final-candidate-reproduction-NEW
```

The generator checks the input ZIP, metadata CSV, portable plan, all used Development config hashes and consensus Drift policy, Source/input bindings, 90-origin entity metadata, and exact 360 sorted IDs. Current `final_lock._valid_job` and `_plan_identity` accepted all 360 schema-shaped rows; `final_coverage._coverage_status` returned `incomplete` for declared scope shortfalls. The full `validate_lock` was intentionally **not** run: there is no lock and the planned input-run directories do not yet exist. Focused tests, Ruff and diff checks are recorded in the commit handoff. No Final/test values, provider call, training, old-output overwrite or usage reset occurred.
