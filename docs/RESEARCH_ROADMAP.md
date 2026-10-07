# Research roadmap — Adaptive Retention for EV Charging Demand Forecasting

**Trạng thái: bản phác thảo để review, 07/10/2026.** Nguồn chuẩn duy nhất cho thiết kế nghiên cứu là [Report 1](../adaptive_retention_report_1.pdf). Tài liệu này diễn giải và tổ chức công việc; không thay thế hoặc chỉnh sửa Report 1. Khi có bất đồng, quay lại Report 1 và đưa quyết định vào PR riêng. Không dùng hướng multi-source/source-selection cũ làm phương pháp chính.

## 1. Bài toán và giả thuyết trong một trang

Dự báo nhu cầu sạc (năng lượng ước tính theo giờ, sau khi schema và unit được xác nhận) cho một trạm target chỉ được cấp 7, 14 hoặc 28 ngày lịch sử lúc bắt đầu. Đây là **mô phỏng cold-start**, không khẳng định các trạm trong release vừa khai trương. Mỗi ngày tại một giờ cố định, dùng 24 giờ quá khứ để dự báo 24 giá trị giờ tiếp theo. Nguồn kiến thức là một model được pretrain trên tập source stations cố định trước mốc triển khai.

Target-only dễ overfit vì ít cửa sổ và tải sạc thưa/biến động; transfer có thể giúp nhưng cũng có thể gây negative transfer. Source error, uncertainty và behavior drift là proxy hữu ích để phân tích, nhưng không trực tiếp trả lời: **giữ biểu diễn source nhiều hơn có thực sự giảm sai số target so với giữ ít hơn không?** Giả thuyết làm việc: so sánh các trajectory học với những mức retention khác nhau trên cùng những ngày đã dự báo, rồi chỉ chuyển mức khi cải thiện quan sát đủ chắc chắn, có thể tốt hơn fixed retention, online best-λ dựa trên mean error và controller theo proxy. Đây là **candidate gap/contribution**, chưa xác nhận novelty hay hiệu quả.

```mermaid
flowchart LR
    P["Cold-start target"] --> T["Pretrain source GRU"]
    T --> R["Transfer encoder + head"]
    R --> C["3 mức retention chạy song song"]
    C --> E["Dự báo trước nhãn; chấm điểm sau"]
    E --> D["LCB của lợi ích retention"]
    D --> N["Giữ / tăng / giảm λ cho block sau"]
    N --> V["Đánh giá final target chưa từng dùng để tuning"]
```

## 2. Model, loss và gradient — cái gì được học?

- **Backbone:** GRU 2 lớp, hidden size 64. Input gồm 24 giờ target history, lịch và missing mask; MLP head nhận latent cuối cùng cộng lịch 24 giờ tương lai đã biết trước; Softplus trả 24 dự báo không âm. GRU không phải novelty.
- **Source pretrain:** forward → forecasting loss → backpropagation → optimizer step trên source encoder và head. Chỉ dùng source data hợp lệ trước mốc triển khai tương ứng. Lưu checkpoint.
- **Target init:** copy encoder và compatible head từ source. Source encoder tham chiếu được freeze/eval/no-gradient. Target encoder và head là phần được cập nhật.
- **Forecast loss:** trung bình 24 sai số tuyệt đối trên thang chuẩn hóa cố định từ dữ liệu được phép; báo metric sau inverse transform về đơn vị gốc.
- **Retention loss:** trung bình trên 64 chiều của bình phương khoảng cách giữa latent target và latent source trên **cùng input**, chia từng chiều cho độ lệch chuẩn latent tính từ source training cộng epsilon. Gradient chỉ đi về target encoder, không đi vào source tham chiếu.
- **Total loss:** forecast loss + λ × retention loss. λ = 0 là full fine-tuning không có ràng buộc retention. λ lớn hơn siết ràng buộc biểu diễn; giảm λ không đồng nghĩa tự tăng learning rate.
- **Candidate levels:** {0, λ_low, λ_high}, hai mức dương và λ khởi đầu được chọn trên development rồi khóa trước final. λ và controller **không học bằng backprop**; chúng chọn giữa các quá trình học đã được cập nhật bằng backprop.

```mermaid
flowchart TD
    S["Source data trước deployment"] --> SF["Source forward → forecast loss"]
    SF --> SB["Backward + optimizer step: source encoder/head"]
    SB --> CK["Source checkpoint"]
    CK --> TI["Copy sang target; freeze source encoder tham chiếu"]
    TI --> TF["Target forward: 24 giờ input → latent → 24 dự báo"]
    TF --> FL["Forecast loss: cần 24 nhãn đã đến"]
    TI --> SR["Source latent cùng input; eval + no-grad"]
    TF --> RL["Retention loss"]
    SR --> RL
    FL --> TOTAL["Total loss = forecast + λ × retention"]
    RL --> TOTAL
    TOTAL --> TB["Backward + optimizer step: target encoder/head"]
```

## 3. Online lifecycle đúng thứ tự nhân quả

Đầu mỗi block (14 ngày là cấu hình khởi đầu, chưa khóa), fork checkpoint **và optimizer state** của active thành ba candidate cùng normalization, data, batch order, update schedule và step count; ghép cặp RNG/dropout/sampling trong mỗi seed. Một candidate active được xác định **trước** block; hai nhánh còn lại chạy shadow để so sánh công bằng.

```mermaid
flowchart TD
    A["Fork 3 candidate từ cùng state"] --> F["Forecast 24 giờ: cả 3 forward/no-grad, lưu dự báo trước nhãn"]
    F --> Y["Đợi đủ 24 nhãn, đúng thời điểm khả dụng"]
    Y --> S["Score MAE của dự báo đã lưu; không sửa forecast quá khứ"]
    S --> U["Mỗi candidate: forward → total loss → backward → optimizer step"]
    U --> B{"Cuối block?"}
    B -- "Chưa" --> F
    B -- "Rồi" --> N{"Đủ B_min ngày hợp lệ?"}
    N -- "Không" --> H["Giữ active đã học"]
    N -- "Có" --> C["So MAE ghép cặp theo ngày; bootstrap LCB một phía"]
    C -- "Không challenger nào có LCB > δ" --> H
    C -- "Có challenger đạt" --> W["Chọn LCB lớn nhất; tie-break đã khóa"]
    H --> K["Mang model + optimizer state sang block sau"]
    W --> K
    K --> A
```

Với challenger j và active a, mỗi **ngày dự báo đủ 24 nhãn** cho một chênh lệch d_b = MAE_b(a) − MAE_b(j); d_b > 0 là j tốt hơn. Chỉ switch khi B ≥ B_min và LCB của mean chênh lệch > δ. Các ngưỡng, alpha, độ dài block bootstrap theo ngày và multiple-comparison rule (tối đa hai challenger) chọn trên development. Nếu không đủ bằng chứng, giữ active. Checkpoint thắng chỉ ảnh hưởng tương lai. LCB không chứng minh causal effect hay an toàn lâu dài qua các block lặp.

Điểm dễ rò rỉ: dùng target labels của 24 giờ chưa kết thúc; backward-fill từ tương lai; fit scaler trên final/test; tạo input từ future target; chọn cohort hoặc threshold bằng final performance; score shadow forecasts sau khi biết nhãn mà không lưu trước; để calendar/weather/price chứa giá trị chưa available tại forecast origin. Cần test future-perturbation và assert source gradient không tồn tại, target gradient hữu hạn, forecast phase no-grad.

## 4. Trạng thái thật ở repo (không nhầm với kế hoạch)

| Hạng mục | Đã có bằng chứng trong repo | Chưa được coi là xong |
|---|---|---|
| Thiết kế | Report 1 và hướng dẫn chung | Novelty/effectiveness chưa được thực nghiệm xác nhận |
| UrbanEV | Acquisition + audit/EDA trên 1.682 station IDs; candidate hourly panel; 21,36% bin missing/invalid theo release | Timezone/bin/label availability và upstream causality chưa đủ để gọi strict online-ready |
| CHARGED | Audit/EDA 4.280 **sites** ở 6 city; 0 missing trong file phát hành | Không suy ra 0 upstream imputation; Shenzhen independence chưa xác minh; chưa chốt external validation |
| Code | src/data, tests và audit reports; 13 data tests được README báo pass | Chưa có source/dev/final split, windows, scaler, model training, controller hay kết quả forecasting |

Các con số là **inventory/candidate panel**, không phải số cohort đủ điều kiện thí nghiệm. Energy trong hai release là **ước tính/derived**, không gọi là measured meter energy. [Phase data](../BAO_CAO_PHASE_DATA.md) ghi chi tiết nguồn, QC và giới hạn.

## 5. Lộ trình A–Z với gate kiểm tra

| Giai đoạn | Việc cần làm | Gate để đi tiếp |
|---|---|---|
| A. Chốt protocol dữ liệu | Xác minh timestamp/bin, timezone/DST, thời điểm label available, nguồn gốc zero/missing/upstream fill, station/site IDs và Shenzhen overlap | Tài liệu evidence + những giới hạn không thể xác minh; quyết định strict causal hay published-data benchmark |
| B. Chốt target/cohort | Xác nhận exact energy column, unit và cách derived; kiểm tra chuỗi 24→24, budget 7/14/28 và phần future còn lại | Cohort/split specification; không dùng final performance để chọn |
| C. Split chống leakage | Source stations, development targets, final unseen targets; mốc thời gian source trước deployment | IDs/mốc thời gian cố định, seed/config lưu; final không dùng tune |
| D. Causal preprocessing | Impute input có mask nhưng không fill target label; scaler chỉ fit trên phần cho phép; calendar known-at-origin; tạo windows bounded trong initial budget | Tests cho gaps, zero≠missing, timezone, future perturbation, no test scaler fit |
| E. Baselines đơn giản | Seasonal Naive, Target-only GRU, Frozen Source, Full Fine-tuning λ=0 | Cùng task, cùng splits/origins, lưu dự báo trước nhãn; metric đơn vị gốc |
| F. Retention | Frozen source reference, latent-scale source-train; Fixed Retention cùng backbone | Gradient/freeze smoke tests, λ=0 khớp fine-tuning, tiny-batch overfit test |
| G. Controller & comparators | 3 candidate trajectories; confidence-LCB controller; Simple Online Best-λ; source-error/uncertainty/drift controllers | Cùng candidate/block/checkpoint/update budget; replay test không future leak |
| H. Lock & final | Chọn hyperparameters, B_min, δ, alpha, block size, proxy rules trên development; đóng băng config rồi chạy final ≥3 seeds | Final targets không tác động bất kỳ quyết định thiết kế nào |
| I. Phân tích & báo cáo | MAE chính, RMSE; gain/negative transfer, station/history/context, switch aftermath, ablation, runtime/memory/candidate cost | Claim chỉ theo evidence; đối chiếu mạnh với online best-λ và literature |

Không tự chuyển sang bước E nếu gate A–D chưa đạt. Nếu provenance khiến strict causal replay không xác minh được, phải báo giới hạn và xin chốt lại phạm vi claim trước khi huấn luyện, không gọi candidate panel là dữ liệu online quan sát thật.

## 6. Evaluation và tiêu chí kết luận

Baselines bắt buộc: Seasonal Naive (fallback khi ít lịch sử); Target-only GRU (không transfer); Frozen Source (không thích nghi); Full Fine-tuning λ=0; Fixed Retention chọn trên development; Simple Online Best-λ dùng **cùng ba candidate và chi phí** nhưng chọn mean MAE không confidence; Source-error, Uncertainty, Drift controllers dùng proxy và ngân sách tuning tương ứng. Related methods (Li et al., R-Tuning, BOTL, GUARD, PADRE, Hyperon) chỉ so trực tiếp nếu tái lập/adaptation hợp lệ và task/metric tương thích; không gọi controller tự viết là reproduction.

Báo MAE/RMSE theo station, budget và thời gian online; gain và negative-transfer rate so Target-only; sai số sau switch, lần thiếu bằng chứng, stability qua ≥3 seeds; runtime, peak memory, inference, ba candidate và số update steps. Ablation bỏ confidence, fixed λ, retention trên tham số, đổi block size và bỏ source init. Weekday/weekend và sparse/dense chỉ là **phân tích context**, chưa phải context-specific controller.

Hỗ trợ contribution nếu controller cải thiện có ý nghĩa thực tiễn và ổn định so với full fine-tuning, fixed retention và **đặc biệt Simple Online Best-λ**, với overhead chấp nhận được. Nếu confidence không thêm lợi ích hoặc quá tốn, thu hẹp claim. Nếu nguồn kiến thức không giúp hoặc dữ liệu không đủ tin cậy, báo negative result/giới hạn, không sửa final setup sau khi xem kết quả. Thành công thực nghiệm cũng **không tự chứng minh novelty**.

## 7. Cách phối hợp nhóm và bước kế tiếp

Mỗi phase nên có issue/PR nhỏ: ghi owner, input, output, gate, lệnh tái lập và evidence. Người triển khai không tự xác nhận gate của chính mình; PR của phase quan trọng cần bạn cùng nhóm review. Review PR này trước để thống nhất logic. Sau đó ưu tiên A–D (nhất là timestamp/label availability và split), rồi mới giao các nhánh baseline/model/controller. Chưa phân công tên người cho từng phase khi nhóm chưa thống nhất.

**Ngoài phạm vi phương pháp chính:** multi-source transferability estimator, source similarity ranking, multi-factor source-target vector, transfer-gain estimator như output, top-k source selection, source weighting và prediction ensemble. Chúng có thể là background/future work nhưng không được lẫn vào core experiment.
