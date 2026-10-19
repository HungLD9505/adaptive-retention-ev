# Issue #18 — input policy implementation and real-data handoff

## Status

The team lead explicitly requested finalization/implementation on 2026-10-19. [Input handoff policy v1](../data/INPUT_ACCEPTANCE.md) now defines operational missing-data handling. All 21 configurations have been rerun into new uniquely identified outputs. The original PR #35 trial, workbook and evidence remain unchanged.

**Technical preprocessing implementation and actual-data handoff are ready for independent review. Formal #18 closure remains pending peer approval, CI, integration/merge of the prerequisite PRs and consumer acceptance.** No model was trained and no PR was merged. Readiness applies to the usable, explicitly accounted input stream, not to every configured station/day or strict-online causality.

## What changed

- Opt-in `ev-missing-data-v1`, v2 run manifests and a schedule artifact account for every requested target origin.
- Partially observed histories keep masks. Fully missing/unavailable histories emit no model input; labels remain separate and the skipped origin is recorded.
- No initial target examples with a defined scaler are marked `source_checkpoint_only`, a separate stratum for the future trainer. No model fallback is actually executed by preprocessing.
- Undefined-scale entities stay in inventory and their target dates stay in the schedule as blocked. No fabricated scale, filled Y, widened budget or role reassignment.
- Existing flagged p95-zero 1 kWh fallback is retained explicitly; no new scaling/split/threshold selection was done after the trial. Unit fallback may leave large normalized sparse spikes and is not established as optimal.
- A completed run with accounted blocks/skips is `technical_success_with_coverage_limits`. This status replaces unresolved-policy failure only for explicit v2 configs. Zero usable target forecasts or structural failures still fail. Legacy configs preserve v1 behavior.

## Actual results

Full inventory remains 1,682 UrbanEV station IDs and 4,280 CHARGED site IDs, 17,886 entity/budget records. These are dataset-scoped IDs, not deduplicated physical sites. All 21 CLI invocations exited 0: 3 UrbanEV runs have explicit coverage limits; 18 CHARGED runs have no skips under the released-file gate.

| Dataset-city-budget | Initial examples, all roles | Requested origins | Emitted inputs | Blocked: no scale | Skipped: empty history | Emitted inputs with complete Y |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| urbanev-SZH-7d | 69,546 | 63,090 | 48,701 | 6,030 | 8,359 | 45,416 |
| urbanev-SZH-14d | 73,807 | 63,090 | 48,792 | 5,760 | 8,538 | 45,490 |
| urbanev-SZH-28d | 82,115 | 63,090 | 49,116 | 4,950 | 9,024 | 45,789 |
| charged-AMS-7d | 140,358 | 87,676 | 87,676 | 0 | 0 | 87,676 |
| charged-AMS-14d | 147,029 | 87,676 | 87,676 | 0 | 0 | 87,676 |
| charged-AMS-28d | 160,371 | 87,676 | 87,676 | 0 | 0 | 87,676 |
| charged-JHB-7d | 2,466 | 1,932 | 1,932 | 0 | 0 | 1,932 |
| charged-JHB-14d | 2,613 | 1,932 | 1,932 | 0 | 0 | 1,932 |
| charged-JHB-28d | 2,907 | 1,932 | 1,932 | 0 | 0 | 1,932 |
| charged-LOA-7d | 12,882 | 8,464 | 8,464 | 0 | 0 | 8,464 |
| charged-LOA-14d | 13,526 | 8,464 | 8,464 | 0 | 0 | 8,464 |
| charged-LOA-28d | 14,814 | 8,464 | 8,464 | 0 | 0 | 8,464 |
| charged-MEL-7d | 3,234 | 2,668 | 2,668 | 0 | 0 | 2,668 |
| charged-MEL-14d | 3,437 | 2,668 | 2,668 | 0 | 0 | 2,668 |
| charged-MEL-28d | 3,843 | 2,668 | 2,668 | 0 | 0 | 2,668 |
| charged-SPO-7d | 2,718 | 1,656 | 1,656 | 0 | 0 | 1,656 |
| charged-SPO-14d | 2,844 | 1,656 | 1,656 | 0 | 0 | 1,656 |
| charged-SPO-28d | 3,096 | 1,656 | 1,656 | 0 | 0 | 1,656 |
| charged-SZH-7d | 83,094 | 51,428 | 51,428 | 0 | 0 | 51,428 |
| charged-SZH-14d | 87,007 | 51,428 | 51,428 | 0 | 0 | 51,428 |
| charged-SZH-28d | 94,833 | 51,428 | 51,428 | 0 | 0 | 51,428 |

Initial training counts are unchanged from the trial; Source examples repeat across budgets. Do not pretrain on all roles or pool cities/datasets. Complete Y here describes released values under the declared availability convention, not genuine observation masks or model scores. Missing-label and history gates overlap; accuracy denominators must use the emitted-input/available-label join, not subtract unrelated aggregate totals.

UrbanEV has 24 / 26 / 30 defined-scale targets with zero initial adaptation samples for 7 / 14 / 28 days. They are explicitly distinguished from 67 / 64 / 55 target IDs blocked by undefined scale. There are additionally 67 undefined-scale Source IDs in every budget. No Source/Development/Final role was changed. Source pretraining retains 871 contributing IDs and 65,888 samples.

## One-station examples (7 days)

| Station | Valid prefix hours | Initial examples | Requested dates | Emitted inputs | History skips | Scale-blocked dates | Complete Y among emitted inputs | Initialization |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1001 | 168 | 6 | 90 | 59 | 31 | 0 | 52 | target_initial_adaptation |
| 1004 | 119 | 0 | 90 | 88 | 2 | 0 | 0 | source_checkpoint_only |
| 1005 | 0 | 0 | 90 | 0 | 0 | 90 | 0 | blocked_undefined_scale |

1001 can initialize from six examples and later emits only inputs with some available history. 1004 has a scale but no complete initial Y window; the future trainer must identify it as no-initial-adaptation. 1005 cannot initialize from its permitted prefix and stays blocked. These illustrate prefix/input handling; they do not select policy using Final labels.

## Verification

- 76 offline tests PASS, including nine new policy regressions for partial/empty histories, arrival-based masks, label-independent gates, true zeros, source-only initialization, blocked IDs, no usable forecasts and legacy behavior. Ruff lint/format, source listing and diff checks PASS.
- Every new artifact hash and byte size verified independently. Every entity preserves its old role, scaler and initial trainable count. Every new forecast record exactly matches the corresponding original forecast after removing only the run ID; the only removed inputs have all 24 energy masks equal to zero.
- The predictor reader was additionally exercised on all 21 actual v2 runs: manifest/artifact verification, first-record shapes and predictor-only fields PASS. All executed runtime file hashes still match the worktree used for these checks.
- All separate label records are unchanged. Every requested origin is unique and accounted. Every serialized initial training record was checked for nonempty history, 24 labels and matching entity role. Actual 24-hour complete-label counts are joined only to created origins.
- The old trial independently reconciled the producers' 26,104,368 hourly rows. New loader runs freshly revalidated producer manifests/hourly hashes, schema, full grids and QC. Raw archives were neither changed nor freshly verified.
- Code identity and executed file hashes are captured per run. The new runtime was committed before launching the suite; later test/report edits do not change the executed runtime hashes. Outputs were not overwritten.

## Reproduce and consume

Compact [evidence JSON](input-handoff-evidence.json) contains every exact config, source identity, output hash, runtime and audit result. On a new machine acquire the same verified producer outputs; set `producer_manifest` to their local location while preserving `producer_manifest_sha256`. Write any `audit.runs[].config` to a JSON file and run:

```sh
python -m tools.model_inputs --config CONFIG.json --output data/inputs/NEW_UNIQUE_RUN_ID
```

The CLI resolves a relative producer path against CONFIG.json. Outputs are local/ignored under `data/inputs/issue18-input-handoff-v1-20261019/<dataset>-<city>-<budget>d/`. Run configs/logs/audit drivers are under `runs/issue18-input-handoff-v1-20261019/`. Each output manifest identifies all five artifacts and the exact acceptance boundary. `iter_forecasts` accepts verified v2 success/coverage-limited runs and reads only predictor-visible records; it never opens labels. This is an input stream, not forecasts made by a trained model.

The #19 consumer must select Source records only for pretraining, preserve per-target independent states, join each target's initialization mode/scaler by identity, apply the common input gate to all compared methods, and score/update only created forecasts after all labels arrive. Report source-only targets separately and retain blocked/skipped counts beside metrics. No checkpoint or runner behavior is certified here.

## Remaining acceptance gates

Request independent review from all three peers. Merge/integrate #25–#35 prerequisites and this implementation through the normal workflow, reconcile any reviewed changes and rerun if runtime/producer/policy changes. #16/#17/#18 cannot be called formally closed merely because this branch works. Main remains unchanged.

Known scientific limits remain explicit: entity-ID rather than verified physical-site separation; assumed UrbanEV offset/bin labels and availability; CHARGED publisher preprocessing/unknown original observation masks and naive local clocks; SZH potential overlap. Keep UrbanEV primary, CHARGED supplementary with SZH separate, no cross-dataset pooling. No gap/novelty/effectiveness claim or strict-online certification is made. Method extensions or tuning use a separately reviewed version on Development, not future Final outcomes.
