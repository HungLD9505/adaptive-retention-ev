# Data audit — urbanev

- Full-period EDA is descriptive only; not used for split/model/threshold selection.
- structured station-raw release, already derived volume; original pile events unavailable
- candidate only: released timezone/bin/availability require verification
- No scaler/imputed label/split/features/windows were created.

```json
{
  "dataset": "urbanev",
  "run_id": "urbanev_full_20261002_01",
  "entities_succeeded": 1682,
  "entities_failed": 0,
  "scope": "full released standard scope",
  "panel_status": "candidate only: released timezone/bin/availability require verification",
  "strict_online_ready": false,
  "upstream_status": "structured station-raw release, already derived volume; original pile events unavailable",
  "independence_status": "Shenzhen overlap not established; no cross-release native-ID mapping",
  "source_sha256": "9d3f0aec34434546d082509efcdeeaea116eaa841701cc5854a9b62a27881a79",
  "code_sha256": "ec47ea74e8036dd7962985f4e0cca50a7a465be51d3ddfae3ef25b24e8f86553",
  "runtime": {
    "pandas": "3.0.1",
    "numpy": "2.5.3",
    "pyarrow": "25.0.1"
  },
  "totals": {
    "input_rows": 87679296,
    "exact_duplicates": 0,
    "conflicting_timestamps": 0,
    "malformed_timestamps": 0,
    "negative_values": 0,
    "nonfinite_values": 0,
    "valid_hours": 5745899,
    "invalid_hours": 1560709,
    "zero_hours": 1901982
  },
  "reconciliation_pass": true,
  "panels": [
    "data\\processed\\urbanev\\urbanev_full_20261002_01\\SZH_hourly_candidate.parquet"
  ]
}
```

## Daily coverage — released timestamps

1682 entities; coverage is file validity, not original-observation proof.

![Daily coverage — released timestamps](figures/coverage_heatmap.png)

## Zero and missing are separate

Invalid hours: 1,560,709; valid zero hours: 1,901,982.

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

29,949 invalid runs; file missingness only, not hidden upstream imputation.

![Invalid/missing run lengths](figures/gap_lengths.png)

## UrbanEV station metadata — GCJ-02

Coordinates from official station_information; no basemap mixing or coordinate conversion.

![UrbanEV station metadata — GCJ-02](figures/station_map.png)

## Nhận xét và bàn giao

- Đã xử lý 1,682 entities; 7,306,608 bin giờ; missing/invalid theo file 21.36%.
- 1,901,982 bin giờ zero hợp lệ số học được giữ nguyên; thiếu label không được điền.
- Energy là estimate từ trạng thái/công suất, không phải số đo công tơ. Original-observation status và label availability chưa xác minh.
- Panel là candidate theo giờ hiển thị; không chứng nhận strict online, timezone/DST/bin semantics hoặc upstream causality.
- EDA toàn kỳ chỉ mô tả. Split/cohort/dates, imputation/scaling, features và windows chuyển development.
- Nghiệm thu: đủ để tiếp tục audit/development trên published-data candidate, chưa đạt gate strict causal experiment.
- Metadata local: 1,682 station IDs, 22,650 pile IDs; 82 rated-power records thiếu/không dương. Không dùng số paper thay số local.
- Auxiliary QC được lưu riêng; static inventory không được mặc định known-at-origin. {'busy_balance_mismatch_rows': 0, 'idle_balance_mismatch_rows': 0, 'negative_fee_rows': 0}

## Daily energy distribution

Tổng ngày trên các giờ có giá trị; chưa phải tổng energy ngày đủ coverage. Không dùng để chọn cohort final.

![Daily energy distribution](figures/daily_distribution.png)

## Weekday vs weekend

Calendar theo timestamp phát hành, timezone chưa xác minh; weighted theo valid entity-hour, không phải so sánh nhân quả.

![Weekday vs weekend](figures/weekday_weekend.png)

## Publisher processed vs structured raw

Đối chiếu trực tiếp volume theo cùng station và timestamp; không dùng bản filled làm ground truth. Counterparts không tồn tại được ghi riêng.

![Publisher processed vs structured raw](figures/publisher_before_after.png)
