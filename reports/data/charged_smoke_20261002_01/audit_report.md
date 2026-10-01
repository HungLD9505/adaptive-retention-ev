# Data audit — charged

- Full-period EDA is descriptive only; not used for split/model/threshold selection.
- publisher processed, masks unknown
- candidate only: released timezone/bin/availability require verification
- No scaler/imputed label/split/features/windows were created.

```json
{
  "dataset": "charged",
  "run_id": "charged_smoke_20261002_01",
  "entities_succeeded": 3,
  "entities_failed": 0,
  "scope": "smoke",
  "panel_status": "candidate only: released timezone/bin/availability require verification",
  "strict_online_ready": false,
  "upstream_status": "publisher processed, masks unknown",
  "independence_status": "Shenzhen overlap not established; no cross-release native-ID mapping",
  "source_sha256": "1ec9c9513b64f3f492fe73261bf08a5955c268dfb876ef0fe283d05cc5a02fab",
  "code_sha256": "ec47ea74e8036dd7962985f4e0cca50a7a465be51d3ddfae3ef25b24e8f86553",
  "runtime": {
    "pandas": "3.0.1",
    "numpy": "2.5.3",
    "pyarrow": "25.0.1"
  },
  "totals": {
    "input_rows": 13176,
    "exact_duplicates": 0,
    "conflicting_timestamps": 0,
    "malformed_timestamps": 0,
    "negative_values": 0,
    "nonfinite_values": 0,
    "valid_hours": 13176,
    "invalid_hours": 0,
    "zero_hours": 8784
  },
  "reconciliation_pass": true,
  "panels": [
    "data\\processed\\charged\\charged_smoke_20261002_01\\AMS_hourly_candidate.parquet"
  ]
}
```

## Daily coverage — released timestamps

3 entities; coverage is file validity, not original-observation proof.

![Daily coverage — released timestamps](figures/coverage_heatmap.png)

## Zero and missing are separate

Invalid hours: 0; valid zero hours: 8,784.

![Zero and missing are separate](figures/zero_missing.png)

## Estimated hourly energy — descriptive sample

Up to256 evenly spaced valid bins per entity, fixed deterministic rule; not full-distribution quantiles.

![Estimated hourly energy — descriptive sample](figures/energy_distribution.png)

## Daily totals over available valid bins

Coverage changes can drive totals; not a complete metered demand series.

![Daily totals over available valid bins](figures/daily_energy.png)

## Before/after examples

Only validity masking/aggregation; no imputation, scaling or outlier removal.

![Before/after examples](figures/before_after_examples.png)

## Hour × weekday pattern

Released clock only; timezone and DST semantics unverified. Weighted across valid entity-hour bins.

![Hour × weekday pattern](figures/hour_weekday.png)

## Invalid/missing run lengths

0 invalid runs; file missingness only, not hidden upstream imputation.

![Invalid/missing run lengths](figures/gap_lengths.png)
