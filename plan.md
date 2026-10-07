# Plan đồ án — Adaptive Retention cho EV Charging

Cập nhật: **07/10/2026**. Nguồn chuẩn: [Report 1](adaptive_retention_report_1.pdf).

## Quy ước cập nhật

- Mỗi lần yêu cầu lập/chỉnh plan của đồ án, cập nhật trực tiếp **file này**, không tạo các bản plan nháp trùng nhau.
- Giữ kế hoạch hiện hành, trạng thái, quyết định chưa chốt và nhật ký thay đổi. Khi đổi quyết định, ghi lý do; không xóa evidence/kết quả cũ.
- Chỉ đánh dấu hoàn thành khi có artifact và check thực tế. Phân biệt đã chạy, đã chuẩn bị code, chưa làm và chưa xác minh.
- Thiết kế phải bám Report 1; phương pháp/thực nghiệm là đóng góp ứng viên. Evaluation, leakage control và cost reporting là yêu cầu phương pháp.

## 1. Trạng thái bàn giao

| Phase/hạng mục | Trạng thái | Evidence |
|---|---|---|
| Proposal | Đã chốt theo chỉ thị người dùng | Report 1 |
| Acquisition, audit, EDA và canonical processing | Đã chạy đến candidate hourly panel | [Báo cáo data](BAO_CAO_PHASE_DATA.md), [gallery 20 visual](reports/data/index.html) |
| Kiểm tra data | 13 tests và readback hai full run pass | [Execution summary](reports/data/execution_summary.json) |
| QC Input | Full/readback/rebuild hai bộ pass theo artifacts; 273 mẫu tensor readback và 126 mẫu future perturbation | QC supplements của active input runs; 11 fixtures đầu vào pass |
| Strict causal data gate | Chưa đạt | Timezone/bin/arrival, upstream processing và Shenzhen independence chưa xác minh đủ |
| Đầu vào model | Đã nghiệm thu published-data benchmark cho cả hai bộ | [Bàn giao đầu vào](BAO_CAO_DAU_VAO_MODEL.md), [gallery10 visual](reports/inputs/index.html), full/readback/rebuild pass. Xem mục7 |
| Model/controller và thực nghiệm | Chưa thực hiện | Không huấn luyện trong phase đầu vào |

UrbanEV: 1.682 trạm, 7.306.608 bin giờ, 21,36% missing/invalid. CHARGED: 4.280 sites, 18.797.760 bin giờ; không thiếu trong file phát hành không chứng minh observed gốc. Energy là estimate với giới hạn đã ghi trong audit. Raw/panel lớn giữ local.

## 2. Kế hoạch development

Thực hiện theo thứ tự; chưa đặt thời hạn mới khi chưa xác định khối lượng và blockers. Ưu tiên UrbanEV, CHARGED có kết luận riêng.

| Bước | Việc cần làm | Đầu ra/điều kiện bàn giao | Trạng thái |
|---|---|---|---|
| DEV1 — Data contract | Contract verified/assumed/unknown cho target/unit, time, upstream và label arrival; strict gate giữ mở | Contract và evidence mỗi run | Hoàn thành contract benchmark hai bộ; unknown được giữ rõ |
| DEV2 — Protocol | Split hash 60/20/20 theo entity/city, cutoffs và cohort7 ngày; budgets7/14/28 | Split/cohort manifests, counts/exclusions; final IDs khóa | Đã chạy cả hai bộ; IDs/dates/target eligibility khóa |
| DEV3 — Đầu vào model | Scale-only p95 trên prefix, missing mask, calendar, index24→24 và lazy loader | Fixtures/readback/visuals/reproducibility | 11 fixtures +13 regression pass;273 samples readback; full rebuild/QC hai bộ pass |
| DEV4 — Model và loss | Trích chính xác kiến trúc và công thức Report 1; source model, target adaptation và latent retention. | Math/tensor specification, forward/update, tests gradient/freeze/reduction | Chưa làm |
| DEV5 — Controller/evaluation | Implement challengers, confidence rule, switching/checkpoint, baselines, audit branch và cost logging. | Prequential runner cùng config/seed/logging; tests clone/update/switch/checkpoint | Chưa làm |
| DEV6 — Smoke end-to-end | Chạy stream development nhỏ qua predict → labels available → update → block decision. | Logs và artifacts tái lập, không dùng smoke làm kết quả nghiên cứu chính | Chưa làm |
| EXP — Thực nghiệm | Sau nghiệm thu development: chạy baselines/ablations tối thiểu ba seed, đối chiếu transfer và chi phí; viết kết quả. | Metrics, uncertainty, audit, cost và báo cáo cho report tổng | Chưa làm |

## 3. Đặc tả đầu vào và toán cần chốt

### Inputs, labels và scaling

- Đã khóa `X_hist[24,7]`, `C_future[24,5]`, `Y[24]` float32; energy scaled, file-valid mask và calendar phát hành. Chi tiết ở `src/inputs/README.md` và config từng run.
- Phân biệt cutoff quan sát, thời điểm forecast và thời điểm labels available. Chỉ dùng thông tin available tại origin.
- Không fill target labels; missingX mã hóa scaled0/mask0, zero hợp lệ mask1. Training/scoring index cần full24Y; không dùng index này làm lịch forecast duy nhất.
- Scale-only p95 linear theo entity/budget từ prefix được phép, frozen tại cutoff. P95=0 dùng positive-source-training p95 cùng dataset; source không có positive dùng1kWh. Inverse=scaled×scale; mọi method cùng entity/budget dùng chung scale.
- Forecast loss trên thang chuẩn hóa; metrics MAE/RMSE đổi về đơn vị gốc. Chỉ cập nhật khi đủ 24 labels theo Report 1.
- Không dùng EDA toàn kỳ để chọn final cohort, threshold hoặc preprocessing.

### Model/loss theo Report 1

- Latent dimension `d=64`; source encoder freeze/eval.
- Latent scale tính từ source training và giữ cố định.
- Ghi nguyên công thức forecast loss, retention loss, reduction theo batch/horizon/latent và tổng objective; đối chiếu PDF trước implement, không tự thay bằng công thức khác.
- Phân biệt tensors từ source/target encoder và tham số nào trainable; kiểm tra source không có gradient/update ngoài thiết kế.

### Controller, baselines và evaluation

- Candidates `Λ={0, λlow, λhigh}`; block khởi đầu 14 ngày.
- Clone model, optimizer và RNG theo Report 1; đủ `Bmin` và `LCB > δ` mới switch.
- Chốt đúng xử lý hai challengers, trường hợp tie/không đủ evidence và checkpoint chuyển sang block sau.
- Online best-λ dùng cùng candidates, block và checkpoint policy; triển khai đầy đủ baselines/ablations của Report 1.
- Audit branch cho switch bất lợi; chỉ báo recovery khi có mốc xác định. Tối thiểu ba seed, báo đầy đủ chi phí.
- Prequential: predict trước khi labels được phép dùng để update; score trên cùng phạm vi hợp lệ giữa methods. Không claim checks local loại được leakage upstream.

## 4. Các quyết định còn mở

Chọn bằng dữ liệu/phạm vi development hợp lệ, ghi evidence và freeze config trước final experiment:

| Nhóm | Quyết định |
|---|---|
| Data semantics | Timezone/bin/availability, khả năng dùng strict online, limitations benchmark, Shenzhen overlap |
| Protocol | Đã chọn thiết kế 60/20/20, hash seed20261004, UrbanEV01/12/2022 và CHARGED01/07/2023, origins00:00, cohort7 ngày; chưa chứng minh tối ưu |
| Preprocessing | Đã chọn scale-only p95, fallback source-positive, missing0/mask0; valid zero mask1; không fill labels |
| Model/controller | Kiến trúc/hyperparameters chưa chốt trong Report 1, λlow/λhigh, δ, Bmin và confidence details |
| Experiment | Seed list, chi phí/budget thực thi, reporting/aggregation metrics |

Không đưa lại defaults 70/15/15, 90/84 ngày, QC95%, UTC, imputation/scaling cũ khi chưa được chọn bằng development. Nội dung nào PDF đã chốt thì tuân theo PDF, không coi là hyperparameter tự do.

## 5. Bước tiếp theo và kiểm tra

1. Phase sau: đối chiếu math/kiến trúc model/loss/retention với Report1; xây source model và adaptation trên development.
2. Sau model mới triển khai controller/baselines/prequential runner; chưa chạy final experiment để chọn cấu hình.
3. Giữ active input runs đã nghiệm thu; khi đổi code/config tạo run mới và kiểm tra tương ứng, không đổi final seed/IDs sau xem kết quả.
4. Mỗi mốc lưu config, code version, seed, logs, metrics/checks và báo cáo bàn giao. Raw, checkpoints và kết quả cũ không ghi đè.

Không tự usage reset/reset credit; gần giới hạn lưu checkpoint an toàn rồi dừng.

## 6. Nhật ký cập nhật

| Ngày | Thay đổi | Trạng thái thực thi |
|---|---|---|
| 02/10/2026 | Tạo plan.md từ kế hoạch development đã trao đổi; ghi data handoff, việc đầu vào/toán và quyết định còn mở. Chọn file này làm nơi cập nhật plan tiếp theo. | Mới lưu kế hoạch; chưa chạy development/model |
| 04/10/2026 | Người dùng chốt protocol đầu vào: split theo entity, cutoffs, budgets, mask/scale/calendar và giả định availability benchmark. | Implement và nghiệm thu đang chạy; không model training |
| 04/10/2026 | Hoàn thành input phasev2; sửa source gate/fallback theo plan, không thay final split/cohort; full/readback/rebuild/QC và10visual cho hai bộ. | 11 input fixtures +13 data regression pass; UrbanEV226.486 và CHARGED782.616 window records; chưa model training |
| 04/10/2026 | Đồng bộ kết quả Data, QC data, Input và QC Input giữa README/báo cáo data/plan; làm rõ trạng thái chưa chạy ở mốc data cũ. | Đối chiếu artifacts hiện có; không chạy lại full data/rebuild; strict online và model/controller/experiments còn mở |
| 04/10/2026 | Thử kiểm tra lại input fixtures bằng `python -m unittest src.inputs.test_inputs -v`. | Exit 1 trước khi chạy fixtures: Python 3.13 không tương thích NumPy cp312 trong `.deps`; cần runtime Python 3.12. PASS đã lưu không được coi là rerun hiện tại |

## 7. Phase đầu vào model — quyết định và checklist đang triển khai

Đã hoàn thành DEV1–DEV5 **của phase đầu vào** cho benchmark; không đổi ý nghĩa các bước model/controller DEV4–DEV6 chưa triển khai ở bảng roadmap mục2.

| Bước trong phase đầu vào | Nội dung | Artifact |
|---|---|---|
| DEV1 | Contract với verified/assumed/unknown; CHARGED đánh giá trong release, Shenzhen chưa độc lập | `data_contract.json` |
| DEV2 | SHA256 `20261004\|entity_id`; source/dev/final60/20/20, round source/dev, final remainder; CHARGED chia riêng city | `split_manifest.csv`, `cohort_manifest.csv` |
| DEV3 | Scale-only p95 prefix, missing scaled0/mask0; zero thật mask1; không fill Y | `scalers.csv`, `allowed_prefix_counts.csv` |
| DEV4 | Midnight24→24; warmup cả X/Y trong7/14/28 ngày; source cả X/Y trước cutoff; stream đến cuối ngày đủ24h | Local `window_index.parquet`, lazy `InputLoader` |
| DEV5 | Fixtures, smoke/full, readback, QC plots, báo cáo, rerun tái lập | Reports và checks mỗi run |

UrbanEV cutoff01/12/2022; CHARGED cutoff01/07/2023 theo clock phát hành chưa gán UTC. Target đủ điều kiện nếu có ít nhất một full48h căn midnight trong warmup7 ngày; dùng cùng cohort cho cả3budgets. Source có ít nhất một window trước cutoff với24 valid labels và ít nhất một valid input hour. UrbanEV final tối thiểu100; nếu thiếu dừng, không đổi seed.

Fallback p95 positive chỉ từ source entities đủ điều kiện training, trong prefix trước cutoff của cùng dataset; không dùng final/stream hoặc source không có training window để fit fallback. Warmup/source windows dùng offline tại deployment; scale frozen tại cutoff. Availability giả định đúng exclusive horizon end/00:00 ngày kế tiếp; actual arrival vẫn unknown.

Index chính dùng train/score và loại incomplete Y. Lịch forecast stream không được loại origin bằng future-label completeness; `forecast()` tạo X/C riêng. Strict online vẫn chưa đủ điều kiện; chỉ published-data benchmark.

Active runs: `urbanev_inputs_full_20261004_02` và `charged_inputs_full_20261004_02`; xem [active manifest](reports/inputs/active_runs.json). Cả hai đã full/readback/QC/tái lập; artifacts benchmark sẵn sàng để xây model.

| Dataset | Source đủ/total | Development đủ/total | Final đủ/total | Window records theo budget |
|---|---:|---:|---:|---:|
| UrbanEV | 898/1.009 | 292/336 | 292/337 | 226.486 |
| CHARGED | 2.567/2.567 | 856/856 | 857/857 | 782.616 |

Readback39+234 mẫu; future perturbation18+108 stream samples pass. Split/scalers/index values/audit counts khớp toàn bộ giữa primary và rebuild, tensor samples bit-exact; scaler được tính lại cho mọi entity-budget. PDF không đổi so vớiHEAD; raw/panel hashes khớp giữa hai lần dựng.

Runv1/partial được giữ để truy vết, không dùng bàn giao (`superseded_by.json`): source gate full48 quá chặt và fallback quá rộng đã được sửa theo plan. Chi tiết lệnh, lỗi đã sửa và giới hạn ở [báo cáo bàn giao](BAO_CAO_DAU_VAO_MODEL.md). Strict online, model/controller và full experiment vẫn chưa hoàn thành.

## 8. Đồng bộ roadmap và repository — 07/10/2026

Đã đối chiếu roadmap PR #1 với Report 1 và evidence Input; bổ sung loss, missing-label branch, controller scale, audit/evaluation và phân công 4 người. [Roadmap](docs/RESEARCH_ROADMAP.md) diễn giải phương pháp; file plan này giữ trạng thái thực thi. Input active không đổi; chưa model training. [Cấu trúc repo](docs/REPOSITORY_STRUCTURE.md) ghi các file giữ/dọn.
