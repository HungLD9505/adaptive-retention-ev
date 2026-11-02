# Bounded Final — Main adverse-comparator station audit (v1)

**Status:** post hoc descriptive audit of the already frozen three-station UrbanEV/SZH Final. No model, method, cohort, threshold, score or lock is changed. Source: [`paired.csv`](hung-final-analysis-20261029-v1/paired.csv), SHA-256 `7ce9d01e61d5d13c4ebc61f9b22f160bf29d5a10818dc43f49f1167d670ceda6`; the equal-station mean is checked against [`station_first.csv`](hung-final-analysis-20261029-v1/station_first.csv), SHA-256 `f01def5b1074cddf2bfda8fba98b9d7f5609dcea9510c3314ffe2645b0535c17`. These tables share the same checkpoint-recomputed score source, so their agreement is arithmetic consistency, not a second raw-checkpoint readback.

The signed difference is `Main MAE − comparator MAE` in original kWh: positive means the named comparator has lower error. For each station and budget, three matched physical-seed differences are averaged first; the displayed mean then weights the three stations equally. Each line has **3 stations × 3 matched physical seeds**, with identical scored-day label identities in the source paired table. Budgets reuse the same three stations and are not independent replications.

| Comparator | Budget | 2118 | 2534 | 2579 | Equal-station mean | Positive stations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Source-error controller | 7 d | 0.093 | 0.025 | 0.216 | 0.112 | 3/3 |
| Source-error controller | 14 d | 0.130 | 0.025 | 0.185 | 0.113 | 3/3 |
| Source-error controller | 28 d | 0.089 | 0.022 | 0.116 | 0.076 | 3/3 |
| Fixed retention | 7 d | 0.067 | 0.024 | 0.179 | 0.090 | 3/3 |
| Fixed retention | 14 d | 0.119 | 0.022 | 0.130 | 0.090 | 3/3 |
| Fixed retention | 28 d | 0.058 | 0.019 | 0.090 | 0.056 | 3/3 |
| Drift controller | 7 d | 0.064 | 0.028 | 0.216 | 0.103 | 3/3 |
| Drift controller | 14 d | 0.110 | 0.025 | 0.185 | 0.107 | 3/3 |
| Drift controller | 28 d | 0.075 | 0.025 | 0.116 | 0.072 | 3/3 |

The source station-first descriptive 95% bootstrap intervals for all nine equal-station differences are above zero, but each uses only three station units. Under an independent, sign-symmetric station null, three positive signs have a post hoc one-sided exact probability of `0.125` for one comparator at one budget. The three comparators and budgets share stations and related training/decision paths; their nine rows cannot be combined as independent tests. No multiplicity-adjusted, prespecified superiority claim follows. The observed mean differences are small relative to Main MAE (~8 kWh), and the table does not identify which controller action caused them. These results strengthen the bounded negative answer to RQ2: Main is not empirically best among the executed comparators on this locked subset.

Reproduce the station means and signs from the pinned CSV without opening Final inputs or changing outputs:

```python
import csv
from collections import defaultdict
from statistics import mean

base = "docs/reports/hung-final-analysis-20261029-v1/"
with open(base + "paired.csv", newline="", encoding="utf-8") as stream:
    pairs = list(csv.DictReader(stream))
with open(base + "station_first.csv", newline="", encoding="utf-8") as stream:
    station_first = list(csv.DictReader(stream))
for variant in ("source_error", "fixed_retention", "drift"):
    for budget in (7, 14, 28):
        gains = defaultdict(list)
        for row in pairs:
            if (
                row["variant"] == variant
                and row["reference"] == "main"
                and int(row["budget_days"]) == budget
            ):
                gains[row["entity_id"]].append(
                    float(row["reference_mae_kwh"]) - float(row["method_mae_kwh"])
                )
        assert set(gains) == {"2118", "2534", "2579"}
        assert all(len(values) == 3 for values in gains.values())
        station_gains = {key: mean(values) for key, values in gains.items()}
        published = next(
            row
            for row in station_first
            if row["variant"] == variant
            and row["reference"] == "main"
            and int(row["budget_days"]) == budget
        )
        assert abs(mean(station_gains.values()) - float(published["mae_gain_kwh"])) < 1e-12
        print(variant, budget, station_gains, sum(value > 0 for value in station_gains.values()))
```

The full [station-first table](hung-final-analysis-20261029-v1/station_first.csv) retains the other executed comparators, including ties, adverse Main-favorable comparisons and Seasonal Naive's one physical seed. No result is used to revise the frozen Development selection or Final protocol.
