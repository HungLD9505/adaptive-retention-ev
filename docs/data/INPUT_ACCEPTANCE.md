# Input handoff policy v1

## Decision and scope

On 2026-10-19 the team lead instructed implementation of the missing-data rules discussed in PR #35, so that preprocessing can produce a model-consumable handoff. This records that user decision; independent peer approval, producer integration and PR merges remain required. It does not claim strict-online readiness or research effectiveness.

This extends the pinned PR #30 tensor contract (`c406ae0`) without changing feature order, 24→24 horizon, exact 7/14/28-day budgets, loss, retention or controller. Use config `missing_data_policy: "ev-missing-data-v1"` explicitly. Legacy configs retain v1 behavior for reproducibility. New policy runs use manifest schema `ev-loader-run-v2`.

## Fixed rules

| Condition | Rule |
| --- | --- |
| Missing historical energy | Preserve missingness; numeric placeholder 0 with mask 0. A real valid zero has mask 1. No interpolation. |
| Partially observed history | At least one valid energy value available at the origin permits the 24-hour input. Keep all positions and masks; no percentage threshold or future-based selection. This minimum is an operational policy, not proof of adequate information. |
| All historical energy missing/unavailable | Do not emit a forecast input or initial training example. For replay, retain the requested origin with `skipped_all_missing_history`; count coverage loss. Apply the same gate across compared methods. |
| Incomplete/late labels | Never fill labels. Initial training and later scoring/update require all 24 valid labels available by the relevant cutoff. Forecast scheduling and historical-input gates cannot inspect future label completeness. |
| Defined scale, zero initial target examples | Record `source_checkpoint_only`. The future trainer must start that target from the selected source checkpoint without initial target fine-tuning and report this stratum separately. Later updates require eligible inputs and complete arrived labels under the runner. No model training is performed by this pipeline. |
| Empty valid/available fit prefix | Keep `undefined_scale`, `initialization=blocked_undefined_scale`, and every target origin as `skipped_undefined_scale`. No invented scale, widened history, reassignment or automatic later recovery. |
| p95 = 0 with a nonempty valid prefix | Retain the existing explicit 1 kWh fallback, flag `zero-p95-unit-kwh`, and preserve zeros and sparse positive values without clipping. This is a fixed operational choice, not a claim of optimal normalization. Any revision must use Source/Development and a separate version before Final evaluation. |
| Source with zero initial examples | Keep the source ID and reason in inventory; it contributes zero training examples. It is not reassigned to another role. |

## Fixed experiment boundaries

Keep the existing declared salt `ev-input-review-v1`, role assignments, per-city CHARGED splits, deployment dates and bin-end + 0h availability assumption from the real-data trial. Do not reroll splits or tune using Final outcomes/completeness. The salt name is historical and remains unchanged for comparability. No new physical-location separation is claimed: this is an ID-based benchmark; co-located IDs remain a disclosed dependence limitation. Do not describe held-out IDs as verified unseen physical sites. A physical-site-disjoint sensitivity analysis would require a separate grouping decision before evaluation; it is not silently added here.

UrbanEV uses assumed constant +08 local bin starts; CHARGED uses published naive local labels. Actual reporting latency and publisher causality are not established. UrbanEV remains the primary benchmark; CHARGED supplementary; SZH is reported separately and is not independent external validation. Do not pool datasets/cities for source pretraining. Unknown upstream observation/imputation masks remain unknown.

## Artifacts and consumer obligations

| Artifact | Meaning |
| --- | --- |
| `training.jsonl` | Contained examples, selected by role for source training or matching target adaptation; no all-missing X or incomplete Y. |
| `forecasts.jsonl` | Only historical-input-eligible target inputs; shapes remain X[24,7], C[24,5]; no future-label fields. |
| `labels.jsonl` | Separate delayed-label records for every defined-scale target origin, including skipped-history origins. A label record alone is not permission to score/update: join to a created forecast and check all-label availability. Blocked-scale origins have schedule records, not label records. |
| `schedule.jsonl` | Every requested target origin, including blocked entities. Status is exactly `created`, `skipped_all_missing_history`, or `skipped_undefined_scale`. Contains no future labels or future-completeness decisions. |
| `entities.jsonl` | Every configured ID, fixed role, fit/scaler identity, prefix diagnostics, initialization mode and coverage/skip counts. |
| `manifest.json` | Policy/version, config/hash, source fingerprints, code/runtime/run identity, all artifact hashes, counts and acceptance limitations. |

Coverage invariant: `requested_forecasts = scheduled_forecasts + skipped_all_missing_history + skipped_undefined_scale`. Here the inherited name `scheduled_forecasts` means emitted inputs; `requested_forecasts` is the full daily schedule. Count full-label evaluable forecasts separately by joining **created** origins with arrived labels. Report coverage and missing-label counts with accuracy; do not compare methods on different origins or mix source-only and initially adapted targets without stratification.

A completed policy run may report `technical_success_with_coverage_limits`: explicit blocks/skips are fully accounted, not fixed, imputed or certified scientifically valid. This differs from the old trial's unresolved-policy failure. A run with requested targets but zero usable forecasts remains `incomplete_no_usable_forecasts`; structural/QC failures still fail. A successful target-only subset run does not establish that a usable source checkpoint exists. The #19 consumer must verify a nonempty source pool and independently retain each target's state/scaler.

Technical output readiness does not close #18. Review/merge of prerequisites and this policy implementation, CI, source/target consumer review and the handoff report remain necessary. No merge is authorized by this document.

## Checkpoint input binding contract

The future #19 checkpoint writer must persist an `input_binding` object with schema **`ev-checkpoint-input-binding-v1`**. This is the data interface requirement, not an implemented model/checkpoint serializer.

| Required field | Meaning |
| --- | --- |
| `schema`, `feature_schema` | `ev-checkpoint-input-binding-v1` and the exact input feature schema/order (`ev-input-v1` for this snapshot). |
| `input_manifest_sha256`, `input_run_id` | Identify the source or target input run and all artifact/config/policy identities it binds. Do not identify inputs only by a mutable directory name. |
| `dataset_id`, `city_id`, `stage` | Dataset/city namespace and `source` or `target` training stage; stages cannot be inferred from file position. |
| `entity_id`, `history_days`, `scale_id` | For target state, its string ID, exact 7/14/28-day initial budget and fitted scale fingerprint; null for a shared Source state, whose per-entity scales are bound through its source-run entities artifact. |
| `source_checkpoint_sha256` | For a target, identity of the selected source initialization/reference; null for the original source checkpoint. |

A source checkpoint may be reused across budget runs only when its Source population, permitted history, scales, source training configuration and seed remain compatible. A target checkpoint must bind its own target-run manifest and scale; it cannot become another target's initialization. The #19 model schema must additionally record architecture/configuration, seed, model/optimizer state and code identity; runner timing/state persistence belongs to its own consumer implementation. No weights, dummy checkpoints or speculative framework are added by #18.

## Integration acceptance record

On 2026-10-20 the team lead explicitly requested final integrated verification, merge into dev, main synchronization and cleanup. [The integration report](../reports/data-integration.md) records the executed checks and the one-time lead-directed disposition when independent peer approval has not been supplied. This does not fabricate an Approve review or weaken the normal peer-review rule for future work. The minimum 1/24 available historical-energy gate is accepted with mandatory coverage/missing-rate reporting and identical gates across compared methods; `source_checkpoint_only` outcomes remain a separate stratum. Clock/upstream/location limitations are unchanged.
