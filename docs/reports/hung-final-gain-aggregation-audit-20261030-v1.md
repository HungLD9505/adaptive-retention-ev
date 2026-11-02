# Bounded Final transfer-gain aggregation audit

This audit uses the locked three-station SZH UrbanEV Final and does not change the frozen evaluation protocol or select a method. It checks the [666-row paired table](hung-final-analysis-20261029-v1/paired.csv), SHA-256 `7ce9d01e61d5d13c4ebc61f9b22f160bf29d5a10818dc43f49f1167d670ceda6`, against the [published station-first table](hung-final-analysis-20261029-v1/station_first.csv), SHA-256 `f01def5b1074cddf2bfda8fba98b9d7f5609dcea9510c3314ffe2645b0535c17`. The [machine output](hung-final-gain-aggregation-audit-20261030-v1.json) preserves all station means. The audit requires the nine exact Main/Target-only station/seed pairs at each 7/14/28-day budget, checks the paired-day and Source-use fields, and rederives the published MAE, gain, transfer ratio and negative-transfer denominator.

The reported **Transfer Gain** is the ratio of station-first mean MAE gain to station-first mean Target-only MAE: `mean_s(Target-only_s − Main_s) / mean_s(Target-only_s)`. It is a ratio of means. An equal-station mean of the *station-specific ratios*, `mean_s[(Target-only_s − Main_s)/Target-only_s]`, asks a different descriptive question and gives each station equal weight in percentage terms. Both first average the three physical seeds within a station; neither pools hours across stations.

| History budget | Published ratio of station-first means | Equal-station mean of station ratios | Station 2118 | Station 2534 | Station 2579 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 7 days | 0.407647 | 0.389195 | 0.232939 | 0.513582 | 0.421065 |
| 14 days | 0.383383 | 0.369147 | 0.214550 | 0.496419 | 0.396473 |
| 28 days | 0.361716 | 0.330496 | 0.130685 | 0.480612 | 0.380190 |

All nine station-specific ratios are positive, and the Main-vs-Target-only NTR is 0/3 per budget under the locked station unit. The difference between the two aggregate ratios reflects heterogeneous Target-only MAE denominators, especially station 2579; it is not additional training evidence. Three stations and repeated budgets do not support a population-wide percentage-gain claim. The original published Transfer Gain remains unchanged; the second estimand is a post hoc sensitivity description.

Reproduce from the repository root with a new output path:

```sh
python -m tools.hung_final_gain_aggregation_audit_v1 \
  --paired docs/reports/hung-final-analysis-20261029-v1/paired.csv \
  --station-first docs/reports/hung-final-analysis-20261029-v1/station_first.csv \
  --output NEW_CREATE_ONLY_PATH.json
```

The CLI refuses an existing output. Its two synthetic regression tests cover ratio-of-means versus mean-of-ratios and rejection of a published-ratio mismatch. It does not reauthenticate provider bytes or establish independent scientific acceptance; those are recorded in the Final readback and gate register.
