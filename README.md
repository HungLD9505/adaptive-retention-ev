# Adaptive Retention — EV Charging Research

Nguồn chuẩn thiết kế: [Report 1](adaptive_retention_report_1.pdf).

## Đọc theo thứ tự

1. [Roadmap nghiên cứu và phân công](docs/RESEARCH_ROADMAP.md).
2. [Plan hiện hành](plan.md).
3. [Báo cáo Data](BAO_CAO_PHASE_DATA.md) và [Input/QC](BAO_CAO_DAU_VAO_MODEL.md).
4. [Cấu trúc repository và inventory dọn dẹp](docs/REPOSITORY_STRUCTURE.md).

## Trạng thái tổng hợp — 04/10/2026

| Phase | Kết quả đã có | Giới hạn / bước còn lại |
|---|---|---|
| Data và QC data | Acquisition, audit, EDA, panel candidate hai bộ; artifacts ghi 13 tests và readback PASS; 20 visual | Strict causal gate chưa đạt |
| Input | Split/cohort, scale/mask/calendar, windows 24→24; UrbanEV 226.486 và CHARGED 782.616 records | Chỉ published-data benchmark |
| QC Input | Artifacts ghi 11 fixtures PASS, 273 mẫu readback, 126 mẫu future perturbation; full rebuild hai bộ khớp; 10 visual | Không chứng minh causality của upstream hoặc arrival thật |
| Model/controller/thực nghiệm | Chưa thực hiện | Tiếp theo: model/loss trên development, rồi controller/baselines và experiments |

Kết quả chi tiết và trạng thái lịch sử được phân biệt tại [báo cáo data, mục 12](BAO_CAO_PHASE_DATA.md#12-cập-nhật-liên-phase--04102026) và [bàn giao đầu vào](BAO_CAO_DAU_VAO_MODEL.md). Lần cập nhật này đối chiếu artifacts có sẵn; không chạy lại full processing/rebuild hay training.

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
- [Research roadmap, workflows và gate triển khai](docs/RESEARCH_ROADMAP.md)

Panel là **candidate**, chưa được chứng nhận dùng cho strict online evaluation. Timezone/bin semantics, label availability, upstream processing và tính độc lập Shenzhen còn cần xác minh. UrbanEV có 21,36% bin giờ missing/invalid. CHARGED không thiếu trong file phát hành không chứng minh mọi giá trị đều observed gốc.

## Tái lập

Chạy từ repository root với Python 3.12:

```powershell
python -m pip install --target .deps -r requirements-data-lock.txt
python -m unittest discover -s src/data -p 'test_*.py'
```

13 tests đã pass; readback hai full runs pass. Các lệnh acquisition, smoke, audit, processing và verify có trong CLI README. Mỗi execution cần run_id mới; raw và kết quả cũ không ghi đè.

Raw archives và hourly panels lớn giữ local, được loại khỏi Git qua `.gitignore`. Repository chia sẻ code, proposal, tài liệu, manifests, audit tables và visual; đường dẫn local trong manifest chỉ phục vụ provenance trên máy thực thi, không mặc định tồn tại trên máy khác. Không redistribute toàn bộ raw trong repository.

Phase data ban đầu không bao gồm split/scaling/windows. Phase đầu vào model tiếp theo đã triển khai riêng trong `src/inputs`; trạng thái thực thi hiện hành tại [plan.md](plan.md).

## Đầu vào model

- [CLI, loader và tensor contract](src/inputs/README.md)
- [UrbanEV input report](reports/inputs/urbanev_inputs_full_20261004_02/input_report.md)
- [UrbanEV QC và tái lập](reports/inputs/urbanev_inputs_full_20261004_02/qc_supplement.md)
- [CHARGED input report](reports/inputs/charged_inputs_full_20261004_02/input_report.md)
- [Bàn giao và lệnh/check đã chạy](BAO_CAO_DAU_VAO_MODEL.md)
- [Gallery10 visual của đầu vào](reports/inputs/index.html)
- [CHARGED QC và tái lập](reports/inputs/charged_inputs_full_20261004_02/qc_supplement.md)

Source/development/final theo entity hash60/20/20; target cohort chung7 ngày, budgets7/14/28, windows24→24. Mask và scale từ prefix được phép, không fill target labels. Raw/panel/index lớn giữ local; code, audit và visual chia sẻ được qua repository. Không huấn luyện model trong phase này. CHARGED là benchmark trong release; Shenzhen chưa xác minh độc lập.
