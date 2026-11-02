# Bounded Final temporal uncertainty sensitivity — 30 October 2026

This **post hoc descriptive sensitivity** uses the authenticated 360-job CPU score source and independently checked Final jobset/receipt/artifact ledger. The [deterministic evidence JSON](evidence/hung-final-temporal-sensitivity-20261030-v1.json) has SHA-256 `00c1765334c5fafc37232c55d246afcd3de1aca0073658e832826d70b28966c0`. The code rechecks the 5,998,020-byte score source SHA-256 `9e09ae4f72b13c03ed029deb338301753ae377c15cbbfa7414433c5538cba73a`, the frozen lock and 360 exact job IDs, and all paired daily label hashes. Its point estimate reproduces the [locked station-first table](hung-final-analysis-20261029-v1/station_first.csv) within `1e-9` kWh.

Daily MAE gain is `(Target-only absolute-error sum − Main absolute-error sum)/24` on the **same** scored origin and physical seed. The calculation first averages seeds 7/11/19 for each station/day, then days within each station, then the three stations equally. Station `2118` has 89 scored days with one missing calendar day in the sequence; `2534` and `2579` have 90 consecutive scored days each. For sensitivity, each of 5,000 deterministic draws samples three stations with replacement and, within each sampled station, resamples circular blocks of **ordered scored days** to the original count. A block for station `2118` may cross the one missing calendar day. Both 7- and 14-scored-day block lengths are reported; neither is selected from the observed result. Percentiles use linear interpolation at 2.5% and 97.5%.

| History | Point MAE gain, kWh | Station-only interval from locked analysis | Station + 7-day block interval | Station + 14-day block interval |
| --- | ---: | ---: | ---: | ---: |
| 7 days | 5.540 | [1.197, 11.227] | [0.995, 13.192] | [0.939, 13.632] |
| 14 days | 5.000 | [1.113, 10.082] | [0.892, 12.151] | [0.838, 11.999] |
| 28 days | 4.486 | [0.733, 9.288] | [0.592, 11.033] | [0.534, 11.032] |

The temporal sensitivity intervals are wider than the station-only intervals at each budget. Their positive lower endpoints remain **descriptive for the three locked SZH stations**. Three stations and overlapping daily forecasts cannot support a general UrbanEV population or cross-city confidence claim. The analysis was performed after observing Final results; it does not retune any model, threshold or selection, and it is not a confirmatory significance test. Main also has adverse observed comparisons against Source-error, Fixed retention and Drift, reported elsewhere in the [draft research report](hung-e2e-research-report-draft-20261030-v22.md).

Reproduce from repository root using the ignored, SHA-pinned small CPU outputs:

```sh
python -m tools.hung_final_temporal_sensitivity_v1
python -m unittest tests.test_hung_final_temporal_sensitivity_v1 -v
```

The tool refuses to overwrite a different existing evidence file. No Kaggle run, checkpoint, method choice or Final lock was changed.
