# Hung #22: Development proxy baseline implementation

This tranche adds three selectable policies to the existing three-candidate
Development runner. It is code and fixture evidence, not a Development
selection result. No Final data or result was used.

| Rule | Decision-time observation | Block statistic |
| --- | --- | --- |
| `source_error` | Frozen Source forecast stored before the daily label; MAE enters only after all 24 labels arrive | Mean of complete-day Source MAEs in the just-finished block |
| `uncertainty` | Population standard deviation of the frozen Source's 24 forecast values | Mean of issued-day dispersions in the block |
| `drift` | Mean of currently available scaled historical load (`X_hist` channel 0 where channel 6 mask is 1), compared with a fixed Development reference | Mean absolute reference distance divided by its positive scale |

The uncertainty measure is a deterministic **within-horizon dispersion
heuristic**, not calibrated predictive uncertainty. Its usefulness and the
historical drift reference must be checked on Development before either can
support an effectiveness claim. All rules require at least the controller's
`min_complete_days` observed proxy values. That count denotes proxy coverage
for the label-free rules, not complete labels. Deferred Source-error labels
arriving after a block decision never revise that decision.

The CLI requires `--proxy-low`, `--proxy-high`, and an explicit permutation of
the three configured candidate levels through `--proxy-level-low`,
`--proxy-level-mid`, `--proxy-level-high`. `drift` additionally requires
`--drift-reference-mean` and `--drift-reference-scale`. These values must be
chosen with the same Development-only tuning budget as the other methods and
locked before Final. The mapping may select *higher* retention for higher
drift; no direction is hard-coded. The runner still forecasts and updates all
three candidate states on the same origins and complete labels. Its separate
`proxy_costs` record counts one extra frozen-Source inference per created
origin, including source-error days that never receive complete labels.

Replay manifests bind the rule and all proxy settings; checkpoints persist
them, the issued forecasts/proxy values, and inference counts for resume.
Existing nonproxy checkpoints use the zero-cost default. The recorded
`perf_counter_ns` timing covers Source forward calls only and is not an
end-to-end wall-clock or peak-memory measurement.

Remaining acceptance work: select thresholds/mapping and drift reference on
real Development entities under a comparable declared search budget; verify
the uncertainty heuristic is useful; run the declared seeds/history budgets;
obtain independent review; lock configs before any Final evaluation.
