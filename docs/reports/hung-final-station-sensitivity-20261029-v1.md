# Bounded Final — station sensitivity audit (v1)

**Status:** post hoc descriptive sensitivity analysis of the already frozen 360-job Final. It does not change the lock, cohort, method, thresholds or selection. Source: [`paired.csv`](hung-final-analysis-20261029-v1/paired.csv), SHA-256 `7ce9d01e61d5d13c4ebc61f9b22f160bf29d5a10818dc43f49f1167d670ceda6`. The published [`station_first.csv`](hung-final-analysis-20261029-v1/station_first.csv), SHA-256 `f01def5b1074cddf2bfda8fba98b9d7f5609dcea9510c3314ffe2645b0535c17`, independently agrees with the three equal-station means below. Both tables ultimately derive from the same checkpoint-recomputed Final score export; this check is an arithmetic sensitivity analysis, not an independent raw-checkpoint readback.

For each budget and station, the audit takes the mean of the three matched physical-seed values `Target-only MAE − Main MAE` from `paired.csv`. It then weights the three stations equally. Every row has three physical seeds; seeds and days are not counted as new stations.

| Budget | 2118 gain | 2534 gain | 2579 gain | Three-station mean | Mean omitting 2579 | 2579 share of sum |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7 d | 1.057 | 1.701 | 13.862 | 5.540 | 1.379 | 83.4% |
| 14 d | 0.981 | 1.588 | 12.432 | 5.000 | 1.285 | 82.9% |
| 28 d | 0.523 | 1.490 | 11.444 | 4.486 | 1.006 | 85.0% |

All nine station-budget gains are positive. Omitting 2118 yields 7.782, 7.010 and 6.467 kWh; omitting 2534 yields 7.460, 6.707 and 5.984 kWh at 7/14/28 days. Thus the direction survives any one-station deletion within this three-station cohort, while the magnitude depends strongly on 2579.

As a **post hoc diagnostic**, under a null in which the three station-level gain signs are independent and symmetric, observing three positive signs has exact one-sided probability `1/2^3 = 0.125` at each budget (two-sided `0.25`). The same three stations appear at every budget, so the nine signs are not nine independent trials and the three budget probabilities cannot be combined as if independent. The diagnostic is not a prespecified confirmatory test, a causal claim, or evidence that the null is true. The positive exact station-bootstrap percentile interval in the main report is likewise descriptive with only three station units; neither result establishes a population-wide transfer effect or RQ2 superiority.

Reproduction from repository root, using the pinned CSV only:

```python
import csv
from collections import defaultdict
from statistics import mean

by_station = defaultdict(list)
with open(
    "docs/reports/hung-final-analysis-20261029-v1/paired.csv", newline="", encoding="utf-8"
) as f:
    for row in csv.DictReader(f):
        if row["variant"] == "main" and row["reference"] == "target_only":
            key = (int(row["budget_days"]), row["entity_id"])
            by_station[key].append(float(row["reference_mae_kwh"]) - float(row["method_mae_kwh"]))
for budget in (7, 14, 28):
    gains = {station: mean(values) for (b, station), values in by_station.items() if b == budget}
    assert set(gains) == {"2118", "2534", "2579"}
    assert all(len(by_station[(budget, station)]) == 3 for station in gains)
    print(
        budget,
        gains,
        mean(gains.values()),
        mean(g for station, g in gains.items() if station != "2579"),
    )
```
