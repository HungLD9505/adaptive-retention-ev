# Authenticated hybrid371 coverage and observed costs — 2026-10-27

This is a read-only audit of the existing371-run portable metric snapshot, not a new training result. The pinned daily-error collections were reloaded; exact jobsets, duplicate rejection, label-hash coverage and recalculated metrics/paired results reproduced saved v4 byte-value content. The canonical plan and generator coverage pins were rechecked before the existing coverage auditor counted families. No raw checkpoint restoration is claimed by this pass.

| Family | Required cells | Matched metric cells | Scorable cells | Physical artifacts |
|---|---:|---:|---:|---:|
| main | 69 | 69 | 36 | 69 |
| seasonal_naive | 69 | 36 | 21 | 12 |
| target_only | 69 | 1 | 1 | 1 |
| frozen_source | 69 | 1 | 1 | 1 |
| full_finetuning | 69 | 0 | 0 | 0 |
| fixed_retention | 69 | 22 | 12 | 22 |
| online_best | 69 | 1 | 1 | 1 |
| source_error | 69 | 69 | 36 | 69 |
| uncertainty | 69 | 57 | 29 | 57 |
| drift | 69 | 69 | 36 | 69 |
| without_confidence | 69 | 1 | 1 | 1 |
| fixed_lambda | 69 | 22 | 12 | 22 |
| parameter_retention | 69 | 1 | 1 | 1 |
| block7 | 69 | 0 | 0 | 0 |
| block28 | 69 | 69 | 36 | 69 |
| no_source | 69 | 0 | 0 | 0 |

[Coverage JSON](evidence/hung-hybrid371-coverage-20261027.json) includes each missing/unmatched/zero-scored cell and counts by7/14/28-day budget. Seeds7/11/19 and all69 logical cells are preserved. The nine mandatory baseline families and five ablation categories remain incomplete. Source Error, Drift and Block28 have69 matched metric cells each (36 scorable each); this does not establish effectiveness or complete the remaining families. All69 historical Block7 cells remain unmatched pending independent disposition.

Fixed Lambda reuses Fixed Retention; Without Confidence reuses the exact predeclared delta0 Online Best configuration. Seasonal Naive has12 physical artifacts representing36 deterministic seed views, not36 independent trials. Alias counts must never be summed into the unique371 physical artifacts. Missing labels remain missing.

[Observed cost JSON](evidence/hung-hybrid371-observed-costs-20261027.json) reports24 strata by method, budget, device and original code SHA. Fields include sample counts, mean and nearest-rank P95 of saved final-stage duration, maximum observed peak allocation, complete runtime-counter samples, summed model update/inference steps and synchronized seconds. P95 uses sorted durations[ceil(0.95*n)-1]; it describes the observed partial cohort and is not a whole-matrix capacity guarantee. Null samples remain null. Candidate/audit counters are summed; proxy costs are excluded.

These durations cover the final replay stage only, excluding initialization and earlier continuation stages. They must not be called whole-job or provider wall time. Provider upload/readback, archive bytes and full GPU session time remain in their original shard/capsule receipts. Device/code stratification preserves historical Main969f3de versus new model44b8532; unequal station/seed/label cohorts prohibit unpaired hardware or method speed rankings. Some deterministic/baseline records have no model runtime counters, which is disclosed by sample counts.

The actual execution ledger remains402/782 new jobs remotely verified;380 remain and100 completed GPU jobs are outside this metric snapshot pending reconciliation. Existing Python GPU/CPU queues continue independently. No completed work was repeated. Export remains deferred until CPU readers finish; no new GPU or provider session was launched for this audit.

Inputs: portable result SHA bfdff9be47653c25ea5e15049b35e9148f4dfffc750a4249ec5afd0ccf73f39c; merge spec SHA f1eb33723e9cb9b6038b02cc38a14a7e16b7652e2dd8e232505720d2d6d09446; canonical plan SHA2d448d2584f65baf7e09445e013b4283314b08ea2cce855c6850e9fc12ba87ee. Exact Source/Target/input/config/manifest/code pins remain in [hybrid v4 provenance](hung-hybrid-v4-provenance-20261027.json).

Commands: existing merge_collections with pinned daily-error inputs; equality against saved v4; existing hung_coverage.audit with SHA-checked canonical plan/coverage; deterministic descriptive cost reduction; JSON syntax checks; Ruff and git diff --check. An initial read-only console inspection hit the Windows default output encoding; rerunning with python -X utf8 succeeded without data changes. No Python implementation or model source changed, so the393-test/1skip/exit0 core result is retained and no full suite was repeated. Files added: this report, the coverage JSON and the observed-cost JSON.

Remaining acceptance: complete pending training and CPU export/metric reconciliation; independently review fairness/implementation/data coverage; record #39 provider substitution; lock immutable Final configuration/cohort/code independently before running Final. No Final labels, selection, merge, issue closure or acceptance claim. docs/SPRINT_PLAN.md remains the sole schedule.
