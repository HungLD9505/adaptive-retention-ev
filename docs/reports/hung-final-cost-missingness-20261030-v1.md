# Hùng bounded Final stage-duration missingness audit — 30 October 2026

The saved remote event receipt (`.cache/hung-final-events-20261029-v1/saved-output-v1-complete/final-events-receipt.json`) binds the downloaded 5,664,639-byte `final-run-events.json` in the same ignored repository directory to SHA-256 `02434d02989fb60bd18e8002cf9878bb29dab0aa436048cb8e235fcf80b54f08`, the 360-job Final lock and the producer archive. The tracked [job table](hung-final-analysis-20261029-v1/job_events.csv) has SHA-256 `ff1648153823140e3a0ebe4ef237f80f7d82184fe6b1e799ace819d2b867036f`; the [variant table](hung-final-analysis-20261029-v1/variant_events.csv) has SHA-256 `19ae7995cd0fbf28006dcbc1143d64eeb0e2f90906a3d215678bb3cb6270ef05`.

The 360 jobs contain **711 stage records**: 360 replay, 324 target initialization and 27 drift reference. Exactly **54 stage durations are null**, one in each of 54 jobs. All 54 nulls are concentrated in two executed variants:

| Variant | Jobs affected | Missing stage | Other saved event fields for that stage |
| --- | ---: | --- | --- |
| Drift | 27/27 | `drift_reference` | Coverage, event evidence, proxy cost and runtime cost are also null. |
| Target-only | 27/27 | `target_init` | Coverage, event evidence, proxy cost and runtime cost are also null. |

The other **306 jobs have complete saved stage-duration inventories**. All present durations are nonnegative. Their sum across all 360 jobs is **8,238.380264 s**; the event auditor's `all_stage_duration_seconds_sum=7,128.104986 s` includes only jobs with no missing stage duration and must not be read as the full-cohort total. The replay-stage sum is **4,329.812594 s** across all 360 jobs. The 8,238.380264 s figure is a lower bound on the sum of saved stage durations if the missing durations are nonnegative; it is **not** provider wall time, end-to-end cost, or a matched cost ratio. No duration was imputed.

Reproduce by checking the receipt SHA, then grouping `jobs[].stages` in the pinned JSON by `job_id` variant and stage name where `duration_seconds is null`. Cross-check the counts against `job_events.csv`, `variant_events.csv` and the [event summary](hung-final-analysis-20261029-v1/event_summary.json). The original GPU output archive was not downloaded locally. Recovery of the two missing stage classes would require their original executor logs/receipts with immutable identity; the current saved event JSON has null for those fields and cannot supply them. The Kaggle CLI's current credential returns `Permission 'kernels.get' was denied` for the producer saved version, so no fresh provider log was obtained in this audit. No training, GPU, Final lock or metric was changed.
