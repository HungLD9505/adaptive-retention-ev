# Development Block7/Main switch-effect audit — 30 October 2026

**Scope.** This retrospective audit uses 138 saved 90-day Development runner checkpoints: 69 historical Block7 and 69 Main. It addresses the old-policy branch comparison specified in [Report 1 §8.2](../../../adaptive_retention_report_1.pdf), separately from the existing switch-count audit. It does **not** evaluate the bounded 360-job Final's old-policy outcomes, establish that a switch was unjustified when chosen, approve historical Block7 fairness, or resolve Hùng–Quyền parity.

The [terminal checkpoint import](../hung-block7-terminal-checkpoint-import-20261030-v1.json), SHA-256 `009fce2052b69bae7dde12d80b1d9e7cec28459d6f5531ce17ad76c489f535f5`, binds all 138 `.pt` files to the saved manifests. The [full trace audit](https://github.com/HungLD9505/adaptive-retention-ev/blob/8cdab1bc096a9c116c7b7f911d548a7621dd81ac/docs/reports/hung-block7-full-trace-audit-20261030-v2.md) separately binds the pre-resume and terminal journals and recomputes candidate scores. This audit rechecks every terminal checkpoint's bytes/SHA before `torch.load(weights_only=True)` and recalculates both the selected live and old-policy audit MAE from the saved 24-hour forecast, complete label and energy scale on every paired day. Each saved score must agree within **10⁻⁵ kWh**, an arithmetic diagnostic rather than a statistical equivalence margin.

For each recorded switch at the end of block `q`, the comparison uses only complete-label origins issued in block `q+1` for which the old-policy audit forecast was saved. The paired daily quantity is `live MAE − old-policy audit MAE` in original kWh; positive means the old policy had lower *observed next-block* error. The locked controller threshold is `δ=0` for these checkpoints, so a positive mean is marked `audit_better_beyond_delta`. A switch without any paired scored next-block day is **unevaluable**, not counted as favorable or adverse. This is a retrospective branch comparison; it does not reveal what was knowable at decision time and does not correct for repeated or dependent switches.

| Executed role | Switches | Paired-evaluable switches | Old-policy audit lower MAE | Paired scored next-block days | Unevaluable switches |
| --- | ---: | ---: | ---: | ---: | ---: |
| Historical Block7 | 55 | 55 | 26/55 | 378 | 0 |
| Main | 32 | 28 | **19/28** | 352 | **4** |

Main's observed audit-lower counts by history budget are 8/11 evaluable at 7 days, 6/9 at 14 days and 5/8 at 28 days. Across Main's 28 evaluable switches, the signed mean next-block difference ranges from −0.2103 to +1.4414 kWh. These are **switch-level descriptive counts**, not independent station trials or a confidence interval. The 32 Main switches agree exactly, per run, with the earlier [851-run manifest switch audit](../hung-development-switch-audit-20261028-v4/report.md). The 55 historical Block7 switches are separate historical method evidence and were not added as new 782-job Development executions.

The [87-row switch table](switches.csv) has SHA-256 `0b863d2fce6d6f95b701ffd24a40999061d3158c405a482fe077b3dca9f0527b`; the [summary](summary.json) has SHA-256 `73021d8ee768aab1ad4f354b1ebc6b9ee861271f8bb84a1f79ef033ab4f5bc03`. Four Main rows are labeled `NO_PAIRED_SCORED_DAY`; all other switches have at least one paired scored day. No missing branch score was imputed.

Reproduce with the 138 ignored, SHA-pinned checkpoints already staged inside the repository:

```sh
python -X utf8 -m tools.hung_block7_switch_effect_audit_v1 --output-dir .cache/hung-block7-switch-effect-recheck-NEW
python -X utf8 -m unittest tests.test_hung_block7_switch_effect_audit_v1 -v
```

The tool refuses an existing output directory. An independent create-only rerun to `.cache/hung-block7-switch-effect-recheck-20261030-v1` regenerated both published files **byte for byte**; focused offline regressions passed 3/3. The result is evidence that a substantial fraction of observed Main switches did not improve next-block MAE relative to the saved old-policy audit branch on this Development subset. It is a negative finding to retain in the research report. Full Final switch-effect claims would require the corresponding authenticated per-origin audit forecast/label data from the frozen Final archive; the currently published small Final event table provides counts and costs, not those paired errors.
