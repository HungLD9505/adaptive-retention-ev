# Hướng dẫn chung — Adaptive Retention

**Đồng bộ 02/10/2026 — AIP491_G10.** Nguồn thiết kế duy nhất: [adaptive_retention_report_1.pdf](adaptive_retention_report_1.pdf), mục 1–10. Hai PDF nguyên bản giữ nguyên; PDF final cũ là bản lịch sử.

## 1. Hướng nghiên cứu, RQ và đóng góp — Report 1 §1–2,9

Mô phỏng station ít lịch sử, không khẳng định trạm thật mới mở. Prediction error/uncertainty/drift không đồng nhất với retention benefit. Lập luận theo prior work → giới hạn có bằng chứng → gap → cải tiến ứng viên → kiểm chứng.

- RQ1: retention giảm forecast error khi nào; điều kiện proxy không phản ánh retention benefit?
- RQ2: benefit quan sát và confidence có tốt hơn fixed retention, online mean-error selection và proxies?
- RQ3: ổn định theo station/history/context và chi phí runtime/memory/update?

Đóng góp **ứng viên**: phương pháp và phân tích thực nghiệm điều kiện retention hữu ích. Prequential evaluation, leakage control và cost reporting là yêu cầu phương pháp; chỉ là đóng góp riêng nếu tạo benchmark/resource mới tái sử dụng được. GRU/TCN, metrics/datasets không tự là novelty. Superiority không tự chứng minh tính mới; chưa có kết quả xác nhận hiệu quả.

## 2. Literature và data — §3–4,10

Ưu tiên [1] Li, [2] R-Tuning, [3] BOTL, [4] GUARD, [5] PADRE, [6] Hyperon; map [7] UrbanEV, [8] CHARGED. Giữ record lịch sử làm background với mức xác minh. Phân tích gap của nhóm không trình bày như hạn chế tác giả. Chưa audit full text/code không gọi là reproduction.

UrbanEV station-level là bộ chính dự kiến; GitHub zone không thay station release. CHARGED tổng quát hóa sau audit; site có thể là cụm charger, kiểm tra Shenzhen overlap trước claim external independence. ACN chỉ background/dự phòng ngoài core.

Task 24 giờ lịch sử → 24 giờ tương lai; một forecast/ngày tại giờ cố định; budgets 7/14/28 ngày riêng. Target đo hoặc ước tính theo schema, rated-power estimate ghi đúng. History/hour/day/weekend/missing và future calendar biết trước; weather/price cần available tại origin.

Không missing=zero, backward fill tương lai hay xóa zero sequences hợp lệ. Split/dates/QC/timezone/origin/DST/availability/imputer/energy normalizer/encoding chọn sau audit/development, không dùng default cũ làm protocol đã khóa. Xem [BAO_CAO_PHASE_DATA.md](BAO_CAO_PHASE_DATA.md) cho nguồn và evidence.

## 3. Model và loss — §5

Một source pool cố định pretrain trước deployment; chuyển GRU encoder **và compatible head** sang target. Source reference frozen, không source selection trong core. GRU 2 lớp hidden64; latent cuối cùng và 24 future calendar qua MLP/Softplus ra24 giá trị không âm. TCN chỉ extension; comparators cùng backbone.

L_forecast = mean24 |y_norm − yhat_norm| trên **thang chuẩn hóa cố định của dữ liệu được phép**. MAE/RMSE inverse về đơn vị gốc. Chỉ score daily paired observation/update khi đủ **24 label** đã available.

L_retain = (1/d) Σ_k ((z_target,k − z_source,k)/(s_k+ε))²; **d=64**, s_k = latent std **source training**, giữ cố định. Source encoder freeze/eval/no-gradient.
L_total = L_forecast + λ L_retain; λ=0 là fine-tuning. Giảm λ chỉ giảm constraint, không bảo đảm tăng learning rate/tốc độ học.

## 4. Controller — §6

1. Λ={0, λlow, λhigh}, 0<λlow<λhigh. Hai mức dương/initial active chọn development rồi khóa. Block khởi đầu **14 ngày**, sensitivity development.
2. Clone cùng model/optimizer state, normalizer, data, batch order, update schedule và step count. Couple/khóa RNG dropout/sampling trong mỗi seed và tái lập RNG khi fork/restore.
3. Active chọn trước block; mỗi candidate giữ λ cả block. Forecast → lưu cả3 predictions trước labels → chờ đủ24 labels → score → update cùng lịch; không chọn prediction quá khứ.
4. d_b(j,a)=ell_b(a)−ell_b(j); b là **một daily forecast đủ24labels**, không 24 observation độc lập. Mean trên B ngày hợp lệ đo trajectory benefit vừa quan sát, không toàn bộ source value hoặc guarantee future winner.
5. Chỉ switch khi đủ **Bmin** và **LCB_j,a > δ**, δ≥0 trong normalized loss. One-sided block bootstrap **theo ngày**; Bmin/α/segment length/δ chọn development. Report cho phép α/2 mỗi comparison cho tối đa2challengers; chọn/khóa policy trước final.
6. Cả2pass: maxLCB; tie λ gần current nhất rồi fixed order. Không pass/thiếu evidence: hold. Repeated blocks/nonstationarity không cho safety guarantee dài hạn.
7. Commit **model+optimizer checkpoint** candidate chọn; hold tiếp tục active checkpoint đã học. Fork candidates từ checkpoint đó với RNG policy đồng bộ; chỉ đổi block sau.

## 5. Protocol và baselines — §7–8

Development chọn tham số còn mở, proxy estimator/threshold và preprocessing bằng stream causal. Final chỉ online score/update theo thuật toán khóa, không retune grid/model/threshold/calibration. Initial input **và labels** nằm trong budget; nhiều origins cùng station có phụ thuộc.

Baselines: Seasonal Naive (fallback thiếu history), random Target-only, Frozen Source, FT λ=0, fixed λ development, **Simple Online Best-λ** cùng candidates/block/cloning/checkpoint policy, chọn mean error nhỏ nhất không confidence; source-error/uncertainty/drift policies cùng tuning/structure/time/input budget.

Source-error=recentMAE frozen source trên arrived labels; uncertainty=spread estimator chọn/kiểm chứng development; drift=current descriptor so historical anchor đã quan sát. Không hardcode drift tăng→λ giảm. BOTL/R-Tuning/GUARD/PADRE/Hyperon cần feasibility/faithful implementation trước direct comparison; proxy tự viết không phải reproduction, adaptation của nhóm ghi rõ. Li quarter-hour/quantile cần harmonize task/metrics.

## 6. Evaluation và chi phí — §8–9

MAE primary, RMSE bổ sung theo station/history/online time. Gain/negative transfer so Target-only; NTR dùng đơn vị aggregation chọn trước final; TO error0 báo absolute delta. So FT/fixed/đặc biệt Online Best-λ; phân tích proxy-benefit, switches, deployed post-error, insufficient evidence.

Audit switch bất lợi: block sau giữ branch policy cũ và so policy mới bằng threshold khóa. **Audit không feedback controller**, cost riêng; hindsight không tự chứng minh decision sai. Recovery chỉ khi có mốc change xác định hoặc stress test; ngày tới rolling error dưới development threshold duy trì số ngày khóa. Không mốc: báo error curve.

**≥3 seeds**; station-first aggregation và uncertainty xét station/time dependence. Cost gồm pretraining/adaptation, runtime, peak memory, inference, candidates, update steps **bao gồm challengers**; audit overhead riêng. Ablate bỏconfidence/fixed/parameter-space/blocksize/no-source-init. Context chỉ stratification weekday/weekend,sparse/dense (threshold development), không module mới.

## 7. Phase và trạng thái

| Phase | Gate/đầu ra |
|---|---|
| Thiết kế | Report1 và4 tài liệu đồng bộ; chưa chứng minh novelty/effectiveness |
| Data | Đã download/audit/EDA và candidate panel giờ; strict causal gate chưa đạt. Split, imputation, scaling, features/windows chuyển development |
| Development | Model/baselines/controller, seed/config/logging; khóa các quyết định còn mở |
| Final | Locked protocol, ≥3seeds, metrics/ablations/cost đầy đủ |
| Report tổng | Data evidence, phương pháp, kết quả thật, limitations |

Đợt này chỉ đồng bộ tài liệu; không tải dữ liệu, preprocessing hay huấn luyện. Chưa có kết quả xác nhận phase data/model.

## 8. Quy tắc làm việc

- Chỉ sửa trong repo; đọc cấu trúc/tài liệu/config trước sửa code. Không tạo file nháp không cần thiết.
- Không xóa/ghi đè raw/checkpoint/report/kết quả cũ khi chưa yêu cầu rõ. Giữ hai PDF nguyên bản.
- Không bịa dữ liệu/metric/citation/tiến độ/feedback; tách prepared, executed, verified.
- Không dùng test/final chọn model/hyperparameter/threshold/calibration; seed/config/logging/error handling.
- Sau sửa chạy checks phù hợp; báo file sửa, lệnh/check, lỗi và việc chưa hoàn thành.
- Không tự usage reset/reset credit/consume_usage_reset; không hỏi/gợi ý reset. Gần giới hạn checkpoint an toàn rồi dừng.

## 9. Đối chiếu Report 1 mục1–10

| Mục nguồn | Nơi đồng bộ |
|---|---|
| 1: động lực/phạm vi | Guide§1; Blueprint tổngquan; Literature Synthesis |
| 2: RQ | Guide§1; Blueprint tổngquan; Synthesis |
| 3: related methods | Guide§2; Literature6methods |
| 4: task/data | Guide§2; Blueprint dataset/processing; Data§1–5 |
| 5: model/loss | Guide§3; Blueprint math; Data§3–4 |
| 6: controller | Guide§4; Blueprint math; Synthesis |
| 7: protocol | Guide§5; Blueprint processing/evaluation; Data§5–7 |
| 8: baseline/evaluation | Guide§5–6; Blueprint evaluation; Synthesis |
| 9: contribution boundary | Guide§1/6; Blueprint tổngquan; Synthesis |
| 10:8refs | Blueprint References; Literature mapping[1]–[8]; Data nguồn dataset |

## 10. Cập nhật thực thi data — 02/10/2026

UrbanEV1.682 stations và CHARGED4.280 sites đã được xử lý trên release thực, có candidate Parquet và20PNG tổng cộng. Xem [báo cáo phase data mục11](BAO_CAO_PHASE_DATA.md) và [visual gallery](reports/data/index.html). Readback/numerical checks đạt; chưa xác minh đầy đủ timezone/bin/label availability, upstream masks hoặc Shenzhen independence. Không huấn luyện, không tự chốt split/scaling/imputation bằng EDA final.
