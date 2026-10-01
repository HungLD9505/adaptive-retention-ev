# Adaptive Retention — EV Charging Research

Nguồn chuẩn thiết kế: [Report 1](adaptive_retention_report_1.pdf).

## Kết quả phase data

Đã chạy acquisition, audit, EDA và processing local:

| Dataset | Entities | Hourly candidate rows | Visuals |
|---|---:|---:|---:|
| UrbanEV station-raw | 1.682 | 7.306.608 | 11 |
| CHARGED standard, 6 cities | 4.280 | 18.797.760 | 9 |

- [Báo cáo phase data](BAO_CAO_PHASE_DATA.md)
- [Gallery visual](reports/data/index.html): tải repository về rồi mở file HTML bằng browser.
- [UrbanEV audit/EDA](reports/data/urbanev_full_20261002_01/audit_report.md)
- [CHARGED audit/EDA](reports/data/charged_full_20261002_02/audit_report.md)
- [CLI và lệnh tái chạy](src/data/README.md)
- [Hướng dẫn đồ án](HUONG_DAN_LAM_DO_AN_CHUNG.md)

Panel là **candidate**, chưa được chứng nhận dùng cho strict online evaluation. Timezone/bin semantics, label availability, upstream processing và tính độc lập Shenzhen còn cần xác minh. UrbanEV có 21,36% bin giờ missing/invalid. CHARGED không thiếu trong file phát hành không chứng minh mọi giá trị đều observed gốc.

## Tái lập

Chạy từ repository root với Python 3.12:

```powershell
python -m pip install --target .deps -r requirements-data-lock.txt
python -m unittest discover -s src/data -p 'test_*.py'
```

13 tests đã pass; readback hai full runs pass. Các lệnh acquisition, smoke, audit, processing và verify có trong CLI README. Mỗi execution cần run_id mới; raw và kết quả cũ không ghi đè.

Raw archives và hourly panels lớn giữ local, được loại khỏi Git qua `.gitignore`. Repository chia sẻ code, proposal, tài liệu, manifests, audit tables và visual; đường dẫn local trong manifest chỉ phục vụ provenance trên máy thực thi, không mặc định tồn tại trên máy khác. Không redistribute toàn bộ raw trong repository.

Split/cohort, dates, imputation, scaling, features, windows và training chuyển sang development; chưa chạy trong phase này.
