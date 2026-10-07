# Báo cáo phase data — Adaptive Retention cho dự báo nhu cầu sạc EV

**Ngày đồng bộ thiết kế:** 02/10/2026. **Nhóm:** AIP491_G10. **Bản phương pháp chuẩn:** [adaptive_retention_report_1.pdf](adaptive_retention_report_1.pdf).

**Mục đích:** chốt phạm vi dữ liệu và quy trình chuẩn bị dữ liệu để kiểm chứng Adaptive Retention, đồng thời giữ đủ nguồn và bằng chứng cho phần Data, Preprocessing, Experimental Setup và Limitations của báo cáo tổng.

**Trạng thái cập nhật 02/10/2026:** đã tải release UrbanEV/CHARGED, chạy full audit và tạo panel giờ candidate, EDA/visual và readback checks. Xem mục 11 cho số liệu local và đường dẫn thực. Chưa chứng nhận strict causal replay vì time/bin semantics, label availability và upstream observation masks còn cần xác minh. Theo phạm vi đã chọn, split/cohort, imputation, scaling, features và windows chuyển sang development; không huấn luyện trong phase này.

Các mục 1–10 giữ đặc tả và nguồn khảo sát trước thực thi; các trạng thái chưa chạy ở đó là lịch sử thiết kế, được thay thế bởi evidence mục 11. Cập nhật liên phase ngày **04/10/2026** ở mục 12: split/cohort, scaling, features/windows và QC Input đã chạy riêng trong phase đầu vào; model và thực nghiệm chưa chạy.

## 1. Quyết định chọn dữ liệu

| Bộ dữ liệu | Vai trò theo Report 1 | Bản cần lấy | Điều kiện đưa vào thí nghiệm |
|---|---|---|---|
| **UrbanEV** | **Bộ chính dự kiến**, sau audit station release | Raw station-level 5 phút, metadata và mô tả trường. Bản station-level đã xử lý dùng để đối chiếu; bản zone-level không thay thế station | Xác minh schema/đơn vị, truy vết missing và xây được chuỗi giờ bằng quy trình chỉ sử dụng dữ liệu đã xuất hiện |
| **CHARGED** | **Bộ kiểm tra tổng quát hóa có điều kiện sau audit** | Khảo sát Zenodo v3 `Hourly.zip` bản standard; city/phạm vi sử dụng chọn sau audit. Gói 5 phút chỉ khảo sát khi cần truy vết upstream | Xác minh license của bản dữ liệu, timezone, site IDs và provenance. Nếu không phục hồi được mask/raw thì chỉ báo kết quả trên published processed benchmark, giới hạn rõ claim online |
| **ACN-Data** | Dự phòng, **không đưa vào bộ thí nghiệm bắt buộc v1** | Session metadata và time series nếu sau này cần | Phải xác minh khả năng tạo năng lượng giờ từ time series; tổng năng lượng một phiên không đủ xác định năng lượng từng giờ |

**Vai trò dự kiến: UrbanEV chính, CHARGED bổ sung sau audit.** Phạm vi city, số entity và checkpoint của thí nghiệm bổ sung chưa khóa. UrbanEV trả lời câu hỏi station-level; CHARGED hỗ trợ khảo sát site-level. CHARGED gồm site được gom theo vị trí, vì vậy khi viết báo cáo phải dùng đúng tên đơn vị. Lặp lại thí nghiệm trên nhiều thành phố không tự đồng nghĩa đánh giá một thành phố chưa từng xuất hiện trong training.

Việc chọn UrbanEV và CHARGED bám mục 4 của Report 1. Nếu UrbanEV không vượt qua kiểm tra khả dụng/causal preprocessing, không tự đổi sang zone-level hoặc coi CHARGED là raw; ghi rõ điểm không đạt và cập nhật thiết kế trước thí nghiệm chính.

## 2. Nguồn đã xác minh và giới hạn còn lại

### 2.1. UrbanEV

Paper mô tả khoảng thời gian **01/09/2022–28/02/2023**. Volume là năng lượng **ước tính từ duration và công suất định mức**, không phải số đo công tơ. Pipeline công bố có backward filling và thay outlier bằng giá trị lân cận; vì vậy không mặc định dữ liệu đã xử lý đáp ứng đánh giá online causal. [U1]

README chính thức phân biệt bản zone trên GitHub với raw station-level 5 phút và bản station-level đã xử lý phát hành riêng. Repository thông báo cập nhật station release ngày 11/05/2026, liên kết Drive/Baidu; tọa độ station dùng GCJ-02. [U2] LICENSE repository là CC0; vẫn lưu điều khoản/version đi kèm đúng gói tải. [U3]

**Lựa chọn thực hiện:** lấy raw station release để tự chuẩn hóa theo giờ. Không dùng 275 zone trong GitHub như 275 station. Chưa xác minh header, parser, dung lượng, số station giữ lại hoặc mask của gói station trên máy. Các số lượng trong paper không được chép thành số lượng sau audit của nhóm.

### 2.2. CHARGED

Paper mô tả dữ liệu **01/04/2023–30/09/2023**, gồm AMS, JHB, LOA, MEL, SPO và SZH. Site là cụm charger theo vị trí. Volume được xây từ trạng thái/công suất; preprocessing có interpolation, forward/backward fill. Đây là hạn chế của dữ liệu upstream mà pipeline của nhóm không thể tự xóa bằng cách chỉ tránh backward fill ở bước tiếp theo. [C1]

Zenodo đang hiển thị **v3, record 15814263**. Gói `Hourly.zip` có dung lượng công bố **268,7 MB**, checksum **MD5 099a592653ca74fa1f1051e9c23d6456**; đây là metadata nhà phát hành, chưa phải checksum tệp đã tải của nhóm. [C2]

README đi kèm gói xác định `volume.csv` là **kWh**, `duration.csv` là giờ; `sites.csv` có các trường tổng kết như `total_volume`, `total_duration`, `avg_power`. Tài liệu cũng nhắc xử lý zero sequences. [C3] README GitHub lại mô tả volume là số phiên; đây là mâu thuẫn tài liệu cần ghi nhận, ưu tiên README của release và paper khi kiểm tra schema. [C4]

**Lựa chọn thực hiện:** dùng standard version và giữ các khoảng zero hợp lệ. Không mặc định dùng `_remove_zero`, không tự biến chuỗi zero thành missing. Không đưa các thống kê tổng kỳ trong metadata vào predictor. Không dùng khẳng định MIT trong README repository làm bằng chứng đủ cho license của bản dataset Zenodo; mục license của release còn phải xác minh.

### 2.3. ACN-Data dự phòng

Trang chính thức cung cấp API session và endpoint time series riêng, cần đăng ký token. `kWhDelivered` là tổng năng lượng phiên; `chargingCurrent` là dòng điện theo thời gian. [A1] Nếu triển khai sau này, phải có cách chuyển dòng điện sang công suất với điện áp/hệ số phù hợp hoặc nguồn power trace đã xác minh. Không phân bổ đều năng lượng phiên rồi trình bày như năng lượng thực đo theo giờ.

### 2.4. Bảng trạng thái bằng chứng

| Nội dung | Trạng thái hiện tại |
|---|---|
| Vai trò dataset theo Report 1 | Đã đồng bộ vai trò dự kiến; khả dụng còn cần audit |
| Paper/README UrbanEV, CHARGED; danh mục gói CHARGED | Đã đọc nguồn công khai |
| LICENSE UrbanEV repository | Đã kiểm tra |
| Quyền sử dụng đúng gói CHARGED | Chưa xác minh đầy đủ |
| Tải file, checksum local, header/schema thật | Chưa thực hiện |
| Missing masks hoặc raw chưa bị điền thiếu | Chưa xác minh |
| Số trạm/site đạt QC, coverage, split cuối | Chưa có kết quả |
| Preprocessing, tensors, leakage tests | Chưa chạy |

Trong lần khảo sát này, một số trang DOI/Dryad không trả nội dung, web fetch Drive không hiển thị danh mục và kết nối HTTP từ Python bị môi trường chặn. Nguồn đọc được đủ để chốt hướng; chưa đủ để tuyên bố đã kiểm tra dữ liệu trong các archive.

## 3. Task, input và output theo Report 1 §4–5

| Thành phần | Quy định nguồn chuẩn |
|---|---|
| Đối tượng | Station UrbanEV; site CHARGED đúng cấp thực tế. Mô phỏng ít lịch sử, không khẳng định trạm mới mở |
| Target | Năng lượng giờ đo hoặc ước tính theo schema thật; nếu từ rated power phải ghi estimated |
| Input / output | 24 giờ lịch sử → 24 giờ tương lai, output không âm |
| Initial history | 7 / 14 / 28 ngày, mỗi mức là experiment riêng; cả input và label initial nằm trong budget |
| Forecast origin | Một lần/ngày tại giờ cố định; timezone, DST, bin convention và availability chọn sau audit/development |
| Features | Load history, hour/day/weekend, missing indicator; future calendar biết trước. Encoding và tensor width chọn trên development |
| Feedback | Dự báo → lưu → chờ đủ 24 label → score → update; quyết định cuối block chỉ áp dụng block sau |

Forecast loss là MAE trên **thang chuẩn hóa cố định của dữ liệu được phép**, không phải MAE kWh trực tiếp. Metrics MAE/RMSE được inverse-transform về đơn vị gốc. Normalizer năng lượng phải tương thích Softplus, fit không dùng final future và khóa trước final; cách fit cụ thể chưa chọn. Không lấy weather tương lai thực đo hoặc giá chưa công bố tại origin làm feature.

Không chốt sẵn 00:00 UTC, encoding sin/cos hay input 24×7/future 24×5. Cần ghi UTC/local semantics và DST rõ sau audit. Biến latent riêng: d=64, s_k là độ lệch chuẩn latent source-training, giữ cố định; source encoder freeze/eval/no-gradient.

## 4. Quy trình processing

`Nguồn phát hành → raw bất biến + manifest → parse và QC → panel giờ + provenance → station/time split → causal features + scaler → window manifest → kiểm tra leakage → tensors cho model`

### Bước 1 — Thu nhận và lưu nguồn

- Lưu URL chính xác, release/version hoặc commit, ngày tải, file size, publisher checksum, local SHA-256, license và README đi kèm.
- Giữ nguyên archive/raw; output xử lý nằm ở một version riêng. Không ghi đè dữ liệu hoặc kết quả đã tồn tại.
- Trước download lớn, kiểm tra dung lượng gói và dung lượng ổ đĩa. Danh sách cần lấy tối thiểu: target series, station/site metadata, timezone và field definitions. Distance/POI chưa cần cho GRU v1.

### Bước 2 — Parse, IDs và timestamps

- Map tên cột thật sang schema chuẩn sau khi đọc header; không suy đoán raw station fields từ file zone.
- Tạo `entity_id = dataset:city:native_id`; lưu riêng `entity_level`, `native_id` và dataset version.
- Parse timezone-aware; lưu timestamp UTC cho join/sort và local time cho calendar. UrbanEV dùng Asia/Shanghai sau khi kiểm chứng timestamp semantics. CHARGED cần xác minh múi giờ từng city và quy tắc DST.
- Duplicate hoàn toàn giống nhau được gộp và ghi số lượng. Duplicate mâu thuẫn được gắn cờ, không tự cộng/average một giá trị kWh vốn đã là tổng giờ.
- Nếu timestamp chỉ là local naive trong vùng có DST và không giải được giờ lặp/mất, đánh dấu dataset-city chưa đủ điều kiện strict online.

### Bước 3 — QC và zero/missing

- Negative energy, NaN/Inf, timestamp lỗi hoặc record không hợp lệ được gắn cờ; không sửa thành zero.
- Zero được giữ khi telemetry hợp lệ xác nhận không sạc. Thiếu record hoặc thiếu coverage không đủ chứng minh zero.
- Không loại station vì có nhiều zero trong final stream. Sparse demand là một context phải đánh giá.
- Không áp dụng IQR toàn bộ target stream hoặc thay peak bằng trung bình hai phía. V1 chỉ kiểm tra tính hợp lệ/schema và giới hạn vật lý khi có metadata đáng tin cậy; các rule thống kê phải được fit trên source/development phù hợp và khóa trước final evaluation.

### Bước 4 — Tạo năng lượng giờ

**UrbanEV raw:** nếu có energy theo interval đúng đơn vị thì cộng interval energy trong giờ. Nếu chỉ có trạng thái và công suất định mức, tái tạo đúng công thức estimate đã xác minh: `E_interval = Σ_p P_rated,p × Δt_hours × active_flag,p`. Khoảng dùng hai trạng thái liên tiếp chỉ available sau khi trạng thái thứ hai xuất hiện. Không nhân công suất thêm lần nữa nếu trường đã là energy.

Một giờ đủ dữ liệu phải có tất cả interval cần thiết theo schema và telemetry inventory đã biết lúc đó. Với lưới 5 phút đều, giờ gồm 12 interval hoàn chỉnh; số snapshot đầu/cuối phụ thuộc định nghĩa interval. Nếu thiếu interval/charger coverage, giữ partial energy ở trường audit và gắn target giờ là missing; không tự nhân tỷ lệ để ước lượng cả giờ.

**CHARGED hourly:** giữ volume giờ của release, xác minh chiều matrix/time/site IDs và bin convention; không sum lại một giờ đã được tổng hợp. Các gói 5 phút không được gọi là raw chỉ vì độ phân giải cao: phải kiểm tra xem đã denoise/impute hay chưa.

### Bước 5 — Missing policy cần chọn trên development

| Trường hợp | Ràng buộc phải giữ |
|---|---|
| Thiếu input | Chỉ dùng thông tin đã available; imputer, độ dài gap và fallback chọn sau audit/development |
| Thiếu ground truth / partial coverage | Không impute label; chưa đủ 24 label thì không score daily paired observation hoặc update |
| Publisher đã impute không có mask | `original_observation_status = unknown`; không suy ra observed từ file không có NaN |
| Zero hợp lệ | Giữ zero, không đổi thành missing hoặc xóa zero sequences |

Không khóa forward-fill 2 giờ hay source median. Không backward-fill từ tương lai. Mỗi paired daily observation phải đủ cùng 24 label cho cả active và hai challengers; ngày thiếu label được log, không tính vào Bmin. Scoring coverage và nhãn thiếu phải được báo. Nếu tính diagnostic từng giờ thiếu một phần, tách khỏi metric/protocol chính và confidence test.

### Bước 6 — Scaling và windows

- Forecast MAE trên thang chuẩn hóa; output inverse về đơn vị gốc để báo metrics. Cách energy scaling chọn trên development sau audit; không khóa P95 hoặc floor 1 kWh.
- Normalizer fit trên phần dữ liệu được phép, giữ cố định trong final; không dùng toàn target stream. Không center output thành âm nếu dùng Softplus. Latent s_k chỉ fit source-training, không fit lại từ development/target.
- Window initial có đủ input và 24 label nằm trong b ngày; source windows không có label vượt ranh giới. Không thêm pre-budget history cho b nhỏ.
- Lưu bounds, availability, scaler/feature IDs và provenance để tái lập.

## 5. Split và time protocol: ràng buộc đã có, quyết định còn mở

**Theo Report 1 §7:** source training trước mốc triển khai; source pool cố định; source/development/final targets tách vai trò. Development chọn backbone, λlow/λhigh, initial λ, normalizer, thresholds, block, proxy và update schedule. Final chỉ dùng initial budget 7/14/28 ngày rồi tích lũy labels đã đến; không retune grid/threshold/calibration bằng final labels.

| Quyết định | Trạng thái / việc cần làm |
|---|---|
| Station split, stratification, seed cụ thể | Chọn sau audit/development; không khóa 70/15/15 hay seed 20261001 |
| Source training/validation dates, deployment origins, final stream length | Chọn từ coverage thực; không khóa 90/84 ngày, 80/20 hay 174 ngày eligibility |
| QC/coverage và eligibility thresholds | Chọn từ audit và pre-deployment information; không khóa 95%, không lọc theo lỗi/coverage final tương lai |
| Timestamp/bin/timezone/DST, label delay, origin cố định | Xác minh release rồi khóa giả định mô phỏng; không coi timestamp đo là thời gian công bố thực |
| Imputation, feature encoding, energy normalizer | Chọn trên development, version trước final |
| Controller | Λ={0, λlow, λhigh}; block khởi đầu 14 ngày, sensitivity trên development; Bmin, δ≥0, α và bootstrap segment chọn trên development |

Mỗi ngày: forecast từ trạng thái hiện tại → lưu predictions trước labels → chờ đủ 24 labels → score → update candidates theo lịch chung. Cuối block dùng daily paired benefit và LCB>δ để chọn checkpoint cho block sau; không sửa predictions đã phát. Scheduling chi tiết khi một label event trùng origin phải được khóa causal trên development.

CHARGED cần audit city/site và Shenzhen overlap với UrbanEV trước claim external independence. Thiết kế source checkpoint cho từng dataset hoặc transfer chéo dataset chưa được khóa bởi Report 1; chọn trước final, không gọi là quyết định đã triển khai. Nhiều deployment origins trên cùng entity có phụ thuộc; aggregation/uncertainty phải tính đến station/time dependence.

## 6. Schema và artifacts cần có sau khi chạy phase data

### 6.1. Panel chuẩn

Mỗi dòng là một `entity_id × hourly interval`. Tối thiểu có:

| Nhóm | Trường cần lưu |
|---|---|
| Identity | `dataset`, `dataset_version`, `city`, `entity_level`, `entity_id`, `native_id` |
| Time | `interval_start_utc`, `interval_end_utc`, `local_time`, `timezone`, `label_available_at` |
| Target | `y_energy_kwh`, `target_semantics` = estimated/reconstructed/measured nếu có bằng chứng |
| Quality | `file_value_valid`, `original_observation_status`, `coverage_fraction`, `invalid_reason`, `publisher_processed` |
| Provenance | `source_file`, `source_row_or_interval_ids`, `transform_version` |

Feature đã impute/scale nằm ở feature table hoặc tensors riêng; target gốc và audit flags vẫn giữ. Không tạo `original_observed_mask` giả từ điều kiện “file không có NaN”.

### 6.2. Bộ đầu ra final của phase

| Artifact dự kiến | Nội dung / dùng ở report tổng |
|---|---|
| `source_manifest.json` | Dataset/version/license/URL/download date/checksum; mục Data Sources |
| `data_audit.csv` | Entity/time coverage, duplicate/invalid/missing/zero; bảng chất lượng dữ liệu |
| `canonical_hourly.parquet` | Panel giờ + quality/provenance; đầu vào pipeline |
| `split_manifest.json` | IDs source/dev/final, seed, t0, budgets, stream bounds; Experimental Setup |
| `feature_manifest.json` | Schema, availability, imputation/scaler và versions; Preprocessing |
| `window_manifest.parquet` | Window bounds, quality/masks và provenance; kiểm tra reproducibility |
| `qc_summary.json` | Kết quả checks và failures; phụ lục kiểm chứng |
| `online_protocol_config.json` | Các quyết định development đã khóa: candidates/block/Bmin/δ/α/bootstrap, seeds ≥3, RNG/checkpoint policy |
| Prediction/update log schema | Origin/availability, normalized loss, original-unit metrics, full-24-label flag, λ/candidate/block, model/optimizer/RNG checkpoint IDs; phase này mới thiết kế schema |

Đây là các đầu ra cần tạo khi thực thi phase data, **chưa tồn tại trong repo tại thời điểm báo cáo**. Dữ liệu raw và artifacts final là deliverable tái lập cần thiết của phase, không phải các bản nháp để xóa sau kiểm tra. Dùng version directory mới khi chạy; không tạo bản test trung gian hoặc ghi đè run cũ.

## 7. Kiểm tra nghiệm thu trước phase model

| Kiểm tra | Điều kiện đạt |
|---|---|
| Release/source | Local checksum đối chiếu publisher nếu có; license/schema/timezone được ghi rõ |
| Schema và IDs | Một key entity-hour duy nhất; ID cấp station/site đúng; không dùng zone thay station |
| Energy reconciliation | Tổng energy giờ khớp tổng interval hợp lệ trong cùng phạm vi với tolerance số học đã ghi |
| Missing và provenance | Missing khác zero; label không impute; original-observation unknown không bị đổi thành observed |
| Station separation | Source/dev/final IDs không giao nhau; source windows không chứa target data |
| Time boundary | Không có adaptation/source window label vượt split; input/feature chỉ biết tại origin |
| Future perturbation | Thay đổi dữ liệu sau một origin không làm đổi feature/scaler/window quyết định tại origin đó |
| Feedback | Chỉ score/update đủ 24 labels đã available; active/challengers chung masks, batch order và update schedule |
| Loss/scales | Forecast loss normalized; metrics original units; d=64, latent scale source-training cố định; source freeze/eval |
| Reproducibility | Cùng source checksum/config/seed tạo cùng split và windows |
| Upstream causality | Raw hoặc mask đủ tái tạo causal processing; nếu không đạt thì ghi giới hạn benchmark đã xử lý |

**Go cho thí nghiệm chính UrbanEV:** raw station-level khả dụng, target đo/ước tính được định nghĩa và QC/leakage checks đạt, có đủ entity cho ba roles và đủ stream. **CHARGED:** chỉ coi là hỗ trợ strict causal claim khi provenance upstream đạt; nếu không, vẫn dùng làm supplementary published-data benchmark với giới hạn đã nêu, không báo rằng toàn bộ chuỗi dữ liệu không leakage.

Nếu số target hợp lệ quá ít, không tuyên bố ổn định qua nhiều trạm; báo số lượng thật và đánh giá lại protocol trên development trước final run. Chưa gán một số lượng station/site sau lọc trong báo cáo này.

## 8. Kế hoạch thực hiện và evidence cho report tổng

| Thứ tự | Việc cần làm | Đầu ra xác nhận |
|---|---|---|
| D1 | Lấy UrbanEV raw station release; CHARGED manifest/Hourly/README; xác minh license | Source manifest và schema audit |
| D2 | Kiểm tra station IDs/timezone/missing và lịch sử xử lý upstream | Data audit, go/no-go từng dataset-city |
| D3 | Triển khai parser/QC/hourly aggregation và causal missing policy | Canonical panel, reconciliation logs |
| D4 | Tạo station/time split và windows đúng budgets | Split/feature/window manifests |
| D5 | Chạy các checks ở mục 7 và đọc lại artifacts đã lưu | QC summary và báo cáo số lượng thật |
| D6 | Cập nhật báo cáo này bằng kết quả audit có nguồn/log | Phần Data và Preprocessing sẵn để đưa vào report tổng |

Khi viết report tổng, cần các bảng: (1) dataset/version/period/unit/entity level; (2) số entity trước/sau QC và lý do; (3) missing/zero/coverage theo city; (4) source/dev/final counts và time bounds; (5) feature availability và transformation. Biểu đồ cần sau khi có dữ liệu: coverage heatmap, phân phối zero/missing và vài chuỗi target đại diện; chọn mẫu bằng rule đã ghi, không chọn vì proposed model chạy tốt.

### Đoạn có thể dùng ngay ở phần thiết kế dữ liệu

> Nghiên cứu dự kiến dùng UrbanEV station-level làm bộ chính và CHARGED site-level kiểm tra tổng quát hóa sau audit. Đối tượng dự báo là năng lượng sạc theo giờ, đo hoặc ước tính theo schema đã xác minh, với cửa sổ đầu vào 24 giờ, horizon 24 giờ và các mức lịch sử target 7/14/28 ngày. Dữ liệu được tổ chức thành source stations, development targets và final targets; các quyết định xử lý và tham số thuật toán được khóa trước đánh giá final. Bản phát hành đã xử lý được kiểm tra riêng về provenance vì các bước imputation upstream có thể sử dụng thông tin chưa có ở forecast origin.

Đoạn này mô tả **thiết kế**. Sau khi thực thi, chỉ chuyển sang thì quá khứ và điền số trạm/checksum/ngày split khi đã có manifests và logs; không dùng số paper để thay số audit của nhóm.

## 9. Kết luận và trạng thái bàn giao

**Đã đồng bộ:** vai trò dự kiến UrbanEV/CHARGED, task 24→24, budgets 7/14/28, normalized loss và causal online protocol của Report 1. **Cần chọn sau audit/development:** split/dates, QC, timezone/origin/availability, imputation/energy scaling và tham số controller còn mở. **Chưa chạy:** download, schema audit, panel/manifests/tensors và leakage checks. Report 1 là nguồn chuẩn duy nhất cho thiết kế; chưa có dữ liệu hay kết quả xác nhận hiệu quả đóng góp ứng viên.

## 10. Nguồn tham khảo và vị trí bằng chứng

- **[R0]** [Report 1](adaptive_retention_report_1.pdf), §§4–8. SHA-256 tại lúc đối chiếu: `cafc1db09a7fda4e196808a96cedf1b18098a4e7ff859d272402e049ebd65bbc`.
- **[U1]** Li et al. (2025), [UrbanEV — Scientific Data](https://www.nature.com/articles/s41597-025-04874-4?error=cookies_not_supported), Methods → EV charging data; Data Records. DOI: 10.1038/s41597-025-04874-4.
- **[U2]** [UrbanEV official repository](https://github.com/IntelligentSystemsLab/UrbanEV), Updates; Data Access; Files. [Station data Drive được tác giả liên kết](https://drive.google.com/drive/folders/1VUgdb8uNgmtvO93BHBK_OrSxjndrF-48?usp=sharing). [Dryad DOI](https://doi.org/10.5061/dryad.np5hqc04z) đã đối chiếu qua paper; landing/file listing chưa đọc được trong lần này.
- **[U3]** [UrbanEV LICENSE](https://github.com/IntelligentSystemsLab/UrbanEV/blob/main/LICENSE), CC0 1.0.
- **[C1]** Guo et al. (2025), [CHARGED — Scientific Data](https://www.nature.com/articles/s41597-025-05584-7), Data Cleansing; Temporal Alignment; Spatial Formalization. DOI: 10.1038/s41597-025-05584-7.
- **[C2]** [CHARGED Zenodo v3 record 15814263](https://zenodo.org/records/15814263), Files; [Hourly archive preview](https://zenodo.org/records/15814263/preview/Hourly.zip?include_deleted=0). DOI phiên bản: 10.5281/zenodo.15814263; concept DOI: 10.5281/zenodo.15638530.
- **[C3]** [CHARGED release README](https://zenodo.org/records/15814263/files/README.md?download=1), Core Charging Data; Infrastructure Information; Data Quality Notes.
- **[C4]** [CHARGED official GitHub](https://github.com/IntelligentSystemsLab/CHARGED), Project Structure; Data Schema; License. Ghi nhận mâu thuẫn mô tả volume; không dùng README này một mình để suy ra đơn vị target.
- **[A1]** [ACN-Data official portal](https://ev.caltech.edu/dataset), Authentication; Sessions API; Fields; Time Series.

Ngày đối chiếu các nguồn công khai: **01/10/2026**. Không có citation hoặc metric thực nghiệm của nhóm được tự tạo trong báo cáo này.

## 11. Kết quả thực thi local — 02/10/2026

### 11.1. Release, phạm vi và số liệu thực

| Dataset | Full run | Entity | Bin giờ | Valid số học | Missing/invalid | Zero hợp lệ |
|---|---|---:|---:|---:|---:|---:|
| UrbanEV station-raw | urbanev_full_20261002_01 | 1.682 | 7.306.608 | 5.745.899 | 1.560.709 | 1.901.982 |
| CHARGED standard, sáu city | charged_full_20261002_02 | 4.280 | 18.797.760 | 18.797.760 | 0 trong file phát hành | 6.936.073 |

UrbanEV archive Drive: 647.305.188 bytes, SHA-256 `9d3f0aec34434546d082509efcdeeaea116eaa841701cc5854a9b62a27881a79`; có station-raw, station-processed và zone. Pipeline chỉ dùng station-raw để tạo target candidate. Supplement được giữ riêng, không đưa weather/POI vào predictor.

CHARGED Hourly.zip: 268.720.500 bytes, MD5 local khớp publisher `099a592653ca74fa1f1051e9c23d6456`, SHA-256 `1ec9c9513b64f3f492fe73261bf08a5955c268dfb876ef0fe283d05cc5a02fab`. License record CC BY4.0 đã đọc và lưu. Không sử dụng các thư mục remove_zero. Sáu city: AMS 2.449, JHB47, LOA229, MEL63, SPO47, SZH1.445 sites.

UrbanEV metadata có 1.682 station IDs, 22.650 pile IDs, 82 rated-power records thiếu/không dương; đây là counts local, không thay bằng số paper. Busy/idle balance và negative fee checks trên các dòng đủ fields không ghi nhận lỗi. Static inventory có thời điểm khả dụng chưa xác nhận; không dùng nó làm feature tại origin.

### 11.2. Quy tắc đã chạy và giới hạn

- UrbanEV: tổng volume theo released timestamp trong bin giờ; chỉ giữ target khi đủ12 interval hợp lệ. Partial sum lưu riêng, label thiếu vẫn missing; không impute, scale, clip peaks hoặc xóa zero.
- CHARGED: giữ giá trị energy giờ phát hành; không aggregate lại. MEL/SPO dùng metadata column `site`, khác các city dùng `site_id`; alias đã ghi nhận. Một số headers info.csv malformed, không dùng làm predictor.
- Energy là estimate, không phải meter reading. UrbanEV raw đã được structured/derived upstream; chưa có pile-level event trace để tái tính độc lập. CHARGED không có missing trong file không chứng minh không có upstream interpolation/fill.
- Timezone/DST/bin event semantics và label availability chưa đủ bằng chứng; giữ naive released timestamps, timezone/availability unknown. Panel có tên `*_hourly_candidate.parquet`, `strict_online_ready=false`. Không tự đổi timestamp sang UTC hoặc gán cuối giờ là arrival thật.
- Missingness toàn kỳ và EDA không được dùng chọn final cohorts/thresholds. Shenzhen overlap giữa hai release chưa xác minh, không claim independent external evaluation.

**Kết luận nghiệm thu:** acquisition, numerical audit, descriptive EDA và candidate hourly processing đã chạy; đủ bàn giao dữ liệu có giới hạn cho development. Gate strict causal experiment vẫn chưa đạt, phải xác minh semantics/provenance hoặc giới hạn claim thành published-data benchmark.

### 11.3. Visual và evidence bàn giao

- [Trang tổng quan visual](reports/data/index.html).
- [UrbanEV EDA HTML](reports/data/urbanev_full_20261002_01/eda.html), 11 PNG gồm coverage, zero/missing, gaps, hourly/daily distributions, weekday/weekend, chuỗi trước–sau, publisher raw/processed comparison và bản đồ GCJ-02.
- [CHARGED EDA HTML](reports/data/charged_full_20261002_02/eda.html), 9 PNG; không vẽ bản đồ khi coordinate system chưa xác minh.
- [Manifest nguồn](reports/data/acquisition_20261002_03/source_manifest.json), gồm CRC/size/checksum và inventory archive; mirror Dryad README trả401, Drive chính thức đã tải được.
- [UrbanEV audit](reports/data/urbanev_full_20261002_01/entity_audit.csv), [auxiliary QC](reports/data/urbanev_full_20261002_01/auxiliary_audit.csv), [CHARGED audit](reports/data/charged_full_20261002_02/entity_audit.csv).
- [UrbanEV readback](reports/data/urbanev_full_20261002_01/readback_checks.json), [CHARGED readback](reports/data/charged_full_20261002_02/readback_checks.json).

### 11.4. Code, lệnh/check và lỗi

Code/CLI: `src/data/acquire.py`, `process.py`, `audit_auxiliary.py`, `verify.py`, `finalize.py`, hai test modules và README. Dependencies local `.deps`, versions ở requirements-data-lock.txt. Raw không ghi đè; run_id mới cho mỗi execution. Full run có source_snapshot đúng hash code lúc chạy.

Các lệnh đã chạy bằng bundled Python:

```text
src/data/acquire.py --run-id acquisition_20261002_03
src/data/process.py --dataset urbanev --run-id urbanev_full_20261002_01
src/data/audit_auxiliary.py --run-id urbanev_full_20261002_01
src/data/process.py --dataset charged --run-id charged_full_20261002_02
src/data/verify.py --run-id <hai full run trên>
src/data/finalize.py --run-id <hai full run trên>
src/data/test_process.py
src/data/test_acquire.py
```

8 processing tests và5 acquisition tests đạt. Full run không có entity failures. Readback kiểm tra keys/time order, counts, zero/missing invariants và energy reconciliation đạt; UrbanEV thêm kiểm độc lập CSV + math.fsum và future perturbation của transform. Tests dùng fixtures, không phải thực nghiệm model. Không chứng nhận leakage upstream hoặc arrival thật.

Lỗi đã sửa: boolean-index alignment trong smoke; schema site/site_id; partial download CHARGED sai kích thước do concurrent writers (đã thêm file lock, giữ rejected partial và tải/checksum thành công). Các failed/smoke runs giữ để truy vết. Lỗi còn mở: mirror Dryad README401, time/provenance/independence audit chưa hoàn tất.

**Tại mốc bàn giao data 02/10/2026, chưa thực hiện:** source/dev/final split, dates/cohort/QC admission, input imputation, scaler, features/windows24→24 và training. Trạng thái đầu vào mới ngày 04/10/2026 được cập nhật tại mục 12; không thay đổi evidence của run data cũ.

Kiểm tra bàn giao cuối: `python -m unittest discover -s src/data -p 'test_*.py'` chạy 13 tests, exit code 0. Gallery chuyển UrbanEV/CHARGED đúng counts; coverage heatmap UrbanEV và weekday/weekend CHARGED đã xem trực tiếp. Preview lưu tại `reports/data/gallery_preview.png`. Exception checksum và warning trong test là fixtures kiểm tra failure path, không phải lỗi full run.

## 12. Cập nhật liên phase — 04/10/2026

Đã đối chiếu execution summaries, active input manifest và QC/readback artifacts trong repository. Phase data hoàn tất acquisition, audit, EDA và panel giờ candidate; phase đầu vào hoàn tất cho **published-data benchmark**, chưa chứng nhận strict online.

| Hạng mục | UrbanEV | CHARGED |
|---|---:|---:|
| Entity ở panel data | 1.682 | 4.280 |
| Bin giờ candidate | 7.306.608 | 18.797.760 |
| Source đủ điều kiện / tổng | 898 / 1.009 | 2.567 / 2.567 |
| Development đủ điều kiện / tổng | 292 / 336 | 856 / 856 |
| Final đủ điều kiện / tổng | 292 / 337 | 857 / 857 |
| Window records đầu vào | 226.486 | 782.616 |
| Mẫu tensor readback | 39 | 234 |
| Mẫu stream future perturbation | 18 | 108 |

Window records gồm source/warmup/stream theo entity × budget × origin; budgets 7/14/28 là các thí nghiệm riêng. Không diễn giải tổng records thành số dự báo độc lập.

- **Data QC:** artifacts ghi 13 tests pass và readback hai full runs PASS; không có entity failures.
- **Input/QC Input:** artifacts ghi 11 fixtures pass; split/cohort/scalers/index/audit khớp toàn bộ giữa primary và rebuild; tensor samples bit-exact, mọi scaler tính lại từ prefix được phép. Có 10 visual đầu vào, bên cạnh 20 visual data.
- **Protocol đã chạy:** split entity hash 60/20/20; cohort target chung từ prefix 7 ngày; windows 24→24; scale-only p95 và fallback source hợp lệ; missing input = scaled0/mask0, zero hợp lệ mask1; không fill Y. Không dùng final stream để fit scaler hoặc chọn cohort.
- **Chưa hoàn thành:** xác minh timezone/DST/bin, actual label arrival, upstream observation masks và Shenzhen independence; model/loss/latent retention, controller/baselines và thực nghiệm nhiều seed chưa thực hiện. Mirror Dryad README trả HTTP401 ở run acquisition cũ; nguồn Drive chính thức đã tải thành công.

Evidence đầu vào: [bàn giao](BAO_CAO_DAU_VAO_MODEL.md), [active runs](reports/inputs/active_runs.json), [execution summary](reports/inputs/execution_summary.json), [UrbanEV QC](reports/inputs/urbanev_inputs_full_20261004_02/qc_supplement.md), [CHARGED QC](reports/inputs/charged_inputs_full_20261004_02/qc_supplement.md). Bước tiếp theo là model/loss trên development theo [plan.md](plan.md), chưa phải final experiment.
