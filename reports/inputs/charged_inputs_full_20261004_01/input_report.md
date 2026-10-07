# Báo cáo đầu vào model — charged

Run: `charged_inputs_full_20261004_01`. Nghiệm thu benchmark: **True**. Không huấn luyện model.

## Protocol và giới hạn

Nguồn chuẩn Report 1; split theo SHA-256 `20261004|entity_id`, 60/20/20, round source/dev và remainder final, riêng từng city. File split được lưu trước khi đọc energy để fit scale/cohort. Cutoff `2023-07-01`; calendar dùng giờ naive phát hành, timezone/bin thực chưa xác minh.

Đây là benchmark trên dữ liệu phát hành; không claim strict online. `assumed_available_at` là cuối horizon exclusive/00:00 ngày kế tiếp; thời điểm label thật vẫn unknown trong panel gốc. CHARGED có interpolation/IQR/masks chưa biết; Shenzhen chưa xác minh độc lập với UrbanEV.

Target cohort: có một window full48 căn midnight trong warmup7 ngày; tất cả budgets dùng chung cohort. Source cần một window full48 trước cutoff. Windows dùng cho train/score có đủ24 label, input có ít nhất một giờ hợp lệ; input thiếu mã hóa scaled0/mask0, zero thật mask1. Mask chỉ phản ánh file validity, không chứng minh original observation.

Scale-only p95 linear mỗi entity/budget từ lịch sử trước cutoff; fallback source-positive p95 trong cùng dataset, nếu không có positive dùng1kWh. Giữ scale cố định. Source-role fallback dùng tất cả source IDs trước cutoff, kể cả source không đủ window; không dùng final energy để fit fallback.

## Kết quả thực

| city | role | entities | eligible | excluded |
| --- | --- | --- | --- | --- |
| AMS | development | 490 | 490 | 0 |
| AMS | final | 490 | 490 | 0 |
| AMS | source | 1469 | 1469 | 0 |
| JHB | development | 9 | 9 | 0 |
| JHB | final | 10 | 10 | 0 |
| JHB | source | 28 | 28 | 0 |
| LOA | development | 46 | 46 | 0 |
| LOA | final | 46 | 46 | 0 |
| LOA | source | 137 | 137 | 0 |
| MEL | development | 13 | 13 | 0 |
| MEL | final | 12 | 12 | 0 |
| MEL | source | 38 | 38 | 0 |
| SPO | development | 9 | 9 | 0 |
| SPO | final | 10 | 10 | 0 |
| SPO | source | 28 | 28 | 0 |
| SZH | development | 289 | 289 | 0 |
| SZH | final | 289 | 289 | 0 |
| SZH | source | 867 | 867 | 0 |

| city | role | budget_days | phase | candidate_origins | accepted_windows | missing_labels | all_history_missing | outside_panel |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AMS | development | 7 | stream | 45080 | 45080 | 0 | 0 | 0 |
| AMS | development | 7 | warmup | 2940 | 2940 | 0 | 0 | 0 |
| AMS | development | 14 | stream | 45080 | 45080 | 0 | 0 | 0 |
| AMS | development | 14 | warmup | 6370 | 6370 | 0 | 0 | 0 |
| AMS | development | 28 | stream | 45080 | 45080 | 0 | 0 | 0 |
| AMS | development | 28 | warmup | 13230 | 13230 | 0 | 0 | 0 |
| AMS | final | 7 | stream | 45080 | 45080 | 0 | 0 | 0 |
| AMS | final | 7 | warmup | 2940 | 2940 | 0 | 0 | 0 |
| AMS | final | 14 | stream | 45080 | 45080 | 0 | 0 | 0 |
| AMS | final | 14 | warmup | 6370 | 6370 | 0 | 0 | 0 |
| AMS | final | 28 | stream | 45080 | 45080 | 0 | 0 | 0 |
| AMS | final | 28 | warmup | 13230 | 13230 | 0 | 0 | 0 |
| AMS | source | 0 | source_train | 132210 | 132210 | 0 | 0 | 0 |
| JHB | development | 7 | stream | 828 | 828 | 0 | 0 | 0 |
| JHB | development | 7 | warmup | 54 | 54 | 0 | 0 | 0 |
| JHB | development | 14 | stream | 828 | 828 | 0 | 0 | 0 |
| JHB | development | 14 | warmup | 117 | 117 | 0 | 0 | 0 |
| JHB | development | 28 | stream | 828 | 828 | 0 | 0 | 0 |
| JHB | development | 28 | warmup | 243 | 243 | 0 | 0 | 0 |
| JHB | final | 7 | stream | 920 | 920 | 0 | 0 | 0 |
| JHB | final | 7 | warmup | 60 | 60 | 0 | 0 | 0 |
| JHB | final | 14 | stream | 920 | 920 | 0 | 0 | 0 |
| JHB | final | 14 | warmup | 130 | 130 | 0 | 0 | 0 |
| JHB | final | 28 | stream | 920 | 920 | 0 | 0 | 0 |
| JHB | final | 28 | warmup | 270 | 270 | 0 | 0 | 0 |
| JHB | source | 0 | source_train | 2520 | 2520 | 0 | 0 | 0 |
| LOA | development | 7 | stream | 4232 | 4232 | 0 | 0 | 0 |
| LOA | development | 7 | warmup | 276 | 276 | 0 | 0 | 0 |
| LOA | development | 14 | stream | 4232 | 4232 | 0 | 0 | 0 |
| LOA | development | 14 | warmup | 598 | 598 | 0 | 0 | 0 |
| LOA | development | 28 | stream | 4232 | 4232 | 0 | 0 | 0 |
| LOA | development | 28 | warmup | 1242 | 1242 | 0 | 0 | 0 |
| LOA | final | 7 | stream | 4232 | 4232 | 0 | 0 | 0 |
| LOA | final | 7 | warmup | 276 | 276 | 0 | 0 | 0 |
| LOA | final | 14 | stream | 4232 | 4232 | 0 | 0 | 0 |
| LOA | final | 14 | warmup | 598 | 598 | 0 | 0 | 0 |
| LOA | final | 28 | stream | 4232 | 4232 | 0 | 0 | 0 |
| LOA | final | 28 | warmup | 1242 | 1242 | 0 | 0 | 0 |
| LOA | source | 0 | source_train | 12330 | 12330 | 0 | 0 | 0 |
| MEL | development | 7 | stream | 1196 | 1196 | 0 | 0 | 0 |
| MEL | development | 7 | warmup | 78 | 78 | 0 | 0 | 0 |
| MEL | development | 14 | stream | 1196 | 1196 | 0 | 0 | 0 |
| MEL | development | 14 | warmup | 169 | 169 | 0 | 0 | 0 |
| MEL | development | 28 | stream | 1196 | 1196 | 0 | 0 | 0 |
| MEL | development | 28 | warmup | 351 | 351 | 0 | 0 | 0 |
| MEL | final | 7 | stream | 1104 | 1104 | 0 | 0 | 0 |
| MEL | final | 7 | warmup | 72 | 72 | 0 | 0 | 0 |
| MEL | final | 14 | stream | 1104 | 1104 | 0 | 0 | 0 |
| MEL | final | 14 | warmup | 156 | 156 | 0 | 0 | 0 |
| MEL | final | 28 | stream | 1104 | 1104 | 0 | 0 | 0 |
| MEL | final | 28 | warmup | 324 | 324 | 0 | 0 | 0 |
| MEL | source | 0 | source_train | 3420 | 3420 | 0 | 0 | 0 |
| SPO | development | 7 | stream | 828 | 828 | 0 | 0 | 0 |
| SPO | development | 7 | warmup | 54 | 54 | 0 | 0 | 0 |
| SPO | development | 14 | stream | 828 | 828 | 0 | 0 | 0 |
| SPO | development | 14 | warmup | 117 | 117 | 0 | 0 | 0 |
| SPO | development | 28 | stream | 828 | 828 | 0 | 0 | 0 |
| SPO | development | 28 | warmup | 243 | 243 | 0 | 0 | 0 |
| SPO | final | 7 | stream | 920 | 920 | 0 | 0 | 0 |
| SPO | final | 7 | warmup | 60 | 60 | 0 | 0 | 0 |
| SPO | final | 14 | stream | 920 | 920 | 0 | 0 | 0 |
| SPO | final | 14 | warmup | 130 | 130 | 0 | 0 | 0 |
| SPO | final | 28 | stream | 920 | 920 | 0 | 0 | 0 |
| SPO | final | 28 | warmup | 270 | 270 | 0 | 0 | 0 |
| SPO | source | 0 | source_train | 2520 | 2520 | 0 | 0 | 0 |
| SZH | development | 7 | stream | 26588 | 26588 | 0 | 0 | 0 |
| SZH | development | 7 | warmup | 1734 | 1734 | 0 | 0 | 0 |
| SZH | development | 14 | stream | 26588 | 26588 | 0 | 0 | 0 |
| SZH | development | 14 | warmup | 3757 | 3757 | 0 | 0 | 0 |
| SZH | development | 28 | stream | 26588 | 26588 | 0 | 0 | 0 |
| SZH | development | 28 | warmup | 7803 | 7803 | 0 | 0 | 0 |
| SZH | final | 7 | stream | 26588 | 26588 | 0 | 0 | 0 |
| SZH | final | 7 | warmup | 1734 | 1734 | 0 | 0 | 0 |
| SZH | final | 14 | stream | 26588 | 26588 | 0 | 0 | 0 |
| SZH | final | 14 | warmup | 3757 | 3757 | 0 | 0 | 0 |
| SZH | final | 28 | stream | 26588 | 26588 | 0 | 0 | 0 |
| SZH | final | 28 | warmup | 7803 | 7803 | 0 | 0 | 0 |
| SZH | source | 0 | source_train | 78030 | 78030 | 0 | 0 | 0 |

Eligibility/exclusions chi tiết: `cohort_manifest.csv`. Counts/rejections: `window_audit.csv`; rejection reason ưu tiên missing_labels rồi all_history_missing. Thống kê zero/missing và scale chỉ trên allowed prefix; không chọn bằng stream. Mỗi row index có input/horizon bounds, scale, nguồn panel và rowgroup; tensors tạo khi đọc.

## Visual và ý nghĩa

- `01_cohort.png`: phân bố role/cohort, giúp thấy exclusion do lịch sử ban đầu.
- `02_scales.png`: độ chênh thang năng lượng trước cutoff; không dùng để tuning final.
- `03_mask_window.png`: window target theo rule số giờ history hợp lệ ít nhất; zero encoding phải đọc cùng mask.
- `04_prefix_zero.png`: zero-rate trong phạm vi được phép, giữ cả trạm toàn zero.

## Loader và tái chạy

`python -m src.inputs.build --dataset charged --run-id NEW_UNIQUE_ID`

`InputLoader(run_dir).load(i)` chỉ trả X/C. Khi lấy Y phải gọi `include_labels=True, as_of=...` và qua assumed availability. Dataset index có role/phase; caller model phase sau phải tách source/train, warmup/update và final/scoring đúng protocol. `Y * scale_kwh` đổi về kWh; loss trên scaled, metrics trên đơn vị gốc.

Warmup/source windows là batch offline tại deployment: scaler dùng toàn prefix được phép và chỉ sẵn sàng tại cutoff, không claim các warmup windows là forecast online lúc origin cũ. Label loader kiểm tra cả availability và scaler-frozen-at. `forecast(entity_id,budget_days,origin)` tạo input cho target stream kể cả origin bị loại khỏi scoring do thiếu labels; không dùng future-label completeness để quyết định có forecast. Index chính là retrospective train/score index.

Manifest lưu SHA256 raw/panel/config/index/code, Git base và source snapshot. Raw/candidate panel/run cũ không sửa. Dữ liệu lớn local trong `data\inputs\charged\charged_inputs_full_20261004_01`. Readback và samples đầu/giữa/cuối từng city/role/budget/phase tại `readback_checks.json`, `tensor_samples.json`.

## Chưa hoàn thành

Model/loss/retention/controller và experiment chưa triển khai. Physical timezone/DST/bin, causal upstream masks và label arrival chưa xác minh. Strict online chỉ được claim khi các gate trong `data_contract.json` đạt.
