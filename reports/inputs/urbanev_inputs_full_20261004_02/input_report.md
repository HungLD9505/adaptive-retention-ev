# Báo cáo đầu vào model — urbanev

Run: `urbanev_inputs_full_20261004_02`. Nghiệm thu benchmark: **True**. Không huấn luyện model.

## Protocol và giới hạn

Nguồn chuẩn Report 1; split theo SHA-256 `20261004|entity_id`, 60/20/20, round source/dev và remainder final, riêng từng city. File split được lưu trước khi đọc energy để fit scale/cohort. Cutoff `2022-12-01`; calendar dùng giờ naive phát hành, timezone/bin thực chưa xác minh.

Đây là benchmark trên dữ liệu phát hành; không claim strict online. `assumed_available_at` là cuối horizon exclusive/00:00 ngày kế tiếp; thời điểm label thật vẫn unknown trong panel gốc. CHARGED có interpolation/IQR/masks chưa biết; Shenzhen chưa xác minh độc lập với UrbanEV.

Target cohort: có một window full48 căn midnight trong warmup7 ngày; tất cả budgets dùng chung cohort. Source cần một window trước cutoff với đủ24 label và input có ít nhất một giờ hợp lệ, không áp gate full48 của target. Windows dùng cho train/score có đủ24 label, input có ít nhất một giờ hợp lệ; input thiếu mã hóa scaled0/mask0, zero thật mask1. Mask chỉ phản ánh file validity, không chứng minh original observation.

Scale-only p95 linear mỗi entity/budget từ lịch sử trước cutoff; fallback source-positive p95 trong cùng dataset, nếu không có positive dùng1kWh. Giữ scale cố định. Fallback chỉ dùng valid positive energy trước cutoff của source entities đủ điều kiện training, không dùng entity không có training window hoặc final energy để fit fallback.

## Kết quả thực

| city | role | entities | eligible | excluded |
| --- | --- | --- | --- | --- |
| SZH | development | 336 | 292 | 44 |
| SZH | final | 337 | 292 | 45 |
| SZH | source | 1009 | 898 | 111 |

| city | role | budget_days | phase | candidate_origins | accepted_windows | missing_labels | all_history_missing | outside_panel |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SZH | development | 7 | stream | 26280 | 21691 | 4589 | 0 | 0 |
| SZH | development | 7 | warmup | 1752 | 1752 | 0 | 0 | 0 |
| SZH | development | 14 | stream | 26280 | 21691 | 4589 | 0 | 0 |
| SZH | development | 14 | warmup | 3796 | 3792 | 4 | 0 | 0 |
| SZH | development | 28 | stream | 26280 | 21691 | 4589 | 0 | 0 |
| SZH | development | 28 | warmup | 7884 | 7709 | 175 | 0 | 0 |
| SZH | final | 7 | stream | 26280 | 22215 | 4065 | 0 | 0 |
| SZH | final | 7 | warmup | 1752 | 1752 | 0 | 0 | 0 |
| SZH | final | 14 | stream | 26280 | 22215 | 4065 | 0 | 0 |
| SZH | final | 14 | warmup | 3796 | 3795 | 1 | 0 | 0 |
| SZH | final | 28 | stream | 26280 | 22215 | 4065 | 0 | 0 |
| SZH | final | 28 | warmup | 7884 | 7738 | 146 | 0 | 0 |
| SZH | source | 0 | source_train | 80820 | 68230 | 12590 | 0 | 0 |

Eligibility/exclusions chi tiết: `cohort_manifest.csv`. Counts/rejections: `window_audit.csv`; rejection reason ưu tiên missing_labels rồi all_history_missing. Thống kê zero/missing và scale chỉ trên allowed prefix; không chọn bằng stream. Mỗi row index có input/horizon bounds, scale, nguồn panel và rowgroup; tensors tạo khi đọc.

## Visual và ý nghĩa

- `01_cohort.png`: phân bố role/cohort, giúp thấy exclusion do lịch sử ban đầu.
- `02_scales.png`: độ chênh thang năng lượng trước cutoff; không dùng để tuning final.
- `03_mask_window.png`: window target theo rule số giờ history hợp lệ ít nhất; zero encoding phải đọc cùng mask.
- `04_prefix_zero.png`: zero-rate trong phạm vi được phép, giữ cả trạm toàn zero.

## Loader và tái chạy

`python -m src.inputs.build --dataset urbanev --run-id NEW_UNIQUE_ID`

`InputLoader(run_dir).load(i)` chỉ trả X/C. Khi lấy Y phải gọi `include_labels=True, as_of=...` và qua assumed availability. Dataset index có role/phase; caller model phase sau phải tách source/train, warmup/update và final/scoring đúng protocol. `Y * scale_kwh` đổi về kWh; loss trên scaled, metrics trên đơn vị gốc.

Warmup/source windows là batch offline tại deployment: scaler dùng toàn prefix được phép và chỉ sẵn sàng tại cutoff, không claim các warmup windows là forecast online lúc origin cũ. Label loader kiểm tra cả availability và scaler-frozen-at. `forecast(entity_id,budget_days,origin)` tạo input cho target stream kể cả origin bị loại khỏi scoring do thiếu labels; không dùng future-label completeness để quyết định có forecast. Index chính là retrospective train/score index.

Manifest lưu SHA256 raw/panel/config/index/code, Git base và source snapshot. Raw/candidate panel/run cũ không sửa. Dữ liệu lớn local trong `data\inputs\urbanev\urbanev_inputs_full_20261004_02`. Readback và samples đầu/giữa/cuối từng city/role/budget/phase tại `readback_checks.json`, `tensor_samples.json`.

## Chưa hoàn thành

Model/loss/retention/controller và experiment chưa triển khai. Physical timezone/DST/bin, causal upstream masks và label arrival chưa xác minh. Strict online chỉ được claim khi các gate trong `data_contract.json` đạt.
