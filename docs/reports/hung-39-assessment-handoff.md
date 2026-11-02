# #39 — Đánh giá tiến độ, đối chiếu nghiệm thu và bàn giao reviewer

**Cập nhật:** 26/10/2026 (ICT). **Đọc file này trước.** Phạm vi là implementation và evidence của Hùng cho [Issue #39](https://github.com/HungLD9505/adaptive-retention-ev/issues/39) và #19–#21; đây **không** phải chấp thuận phương pháp hay nghiệm thu GitHub. Bốn báo cáo chuẩn: **(1)** [phương pháp/triển khai](hung-39-method-implementation.md), **(2)** [thực nghiệm/kết quả](hung-39-experiments-results.md), **(3)** [tái lập/handoff](hung-39-reproducibility-handoff.md), **(4)** file đánh giá này. Evidence JSON, 19 báo cáo #39 cũ, run manifests, checkpoints, configs và notebook được giữ nguyên.

## Kết luận ở phạm vi đúng

**PASS kỹ thuật cá nhân:** GRU/Source/Target/retention, controller, prequential runner, lượt local representative 216/216 stages/69 cells và audit integrity có output thật. Lượt chạy 25/10 từ **21:00:54 đến 22:08:29 ICT**; archive hoàn tất **23:18:45**. Python 3.12 clean-kernel notebook readback và Kaggle cloud artifact readback được bổ sung ngày 26/10. Chi tiết số liệu/MAE/coverage nằm ở [bảng kết quả duy nhất](hung-39-experiments-results.md); identity, SHA, lệnh và PASS/FAIL/SKIP ở [báo cáo tái lập](hung-39-reproducibility-handoff.md).

**OPEN nghiệm thu:** #39 và #19–#21 vẫn mở; [PR #46](https://github.com/HungLD9505/adaptive-retention-ev/pull/46) là draft, hướng `dev`, chưa merge/chưa có review tại lần kiểm 26/10. Cross-implementation comparison với Quyền, Source/config approval, độc lập review, xử lý khác biệt, Colab GPU/Drive criterion gốc và việc tích hợp vào shared implementation chưa có bằng chứng hoàn tất. Phần kỹ thuật đã chạy không đồng nghĩa method có lợi hoặc Issue được đóng. Khi reviewer yêu cầu sửa, cần ghi version/code identity mới; không đổi output run cũ.

## Đối chiếu acceptance criteria của #19–#21

`PASS` dưới đây chỉ đánh giá **bằng chứng implementation của Hùng**; trạng thái issue chính thức vẫn cần peer review/integration. Chi tiết nguyên văn nằm ở [#19](https://github.com/HungLD9505/adaptive-retention-ev/issues/19), [#20](https://github.com/HungLD9505/adaptive-retention-ev/issues/20), [#21](https://github.com/HungLD9505/adaptive-retention-ev/issues/21).

| Điều kiện | Bằng chứng gốc / kết quả | Đánh giá |
| --- | --- | --- |
| #19: GRU hai lớp hidden 64, calendar MLP, Softplus 24 output, tensor 24→24 | [Method](hung-39-method-implementation.md), [`model.py`](../../experiments/hung_sprint2/model.py), [Phase A](hung-39-phase-a-model-transfer-20261025-masterplan.md); 41.696 tham số được đếm trực tiếp với config thực thi. | **PASS implementation** |
| #19: Source pre-deployment, transfer độc lập từng target, loss MAE + retention với Source frozen/scale cố định, `λ=0` đúng nghĩa | 871 Source IDs, 65.888 mẫu/pass, 2.059 bước/Source stage; Phase A kiểm shape/gradient/freeze/scale/checkpoint, Source/Target run thật trong [Phase D](hung-39-representative-local-20261025.md). | **PASS thực thi**; mức đủ của một Source pass **OPEN phương pháp** |
| #20: ba mức λ, paired error đã đến, bootstrap LCB, `Bmin`, strict `LCB>δ`, tie-break, deterministic fixtures | [Phase B](hung-39-phase-b-controller-20261025-masterplan.md), [`controller.py`](../../experiments/hung_sprint2/controller.py), 414 decisions trong output (32 switch/382 keep). | **PASS logic**; lợi ích và inference qua nhiều block **OPEN** |
| #21: ba candidate cùng state/data/randomness; forecast trước label; missing/late/boundary; trained-state carry và audit độc lập | [Phase C](hung-39-phase-c-runner-20261025-masterplan.md) có fixtures; 69 replay 42→90 thật; audit/checkpoint/journal hash và tensor readback trong [Phase D](hung-39-representative-local-20261025.md). | **PASS local technical** |
| #21: cost, checkpoint/RNG recovery, Development smoke và capacity | CUDA runner state restore được kiểm; per-candidate/audit counters lưu trong manifests; local wall 67,57 phút. Source/Target model checkpoint lịch sử không có RNG snapshot, bổ sung opt-in sau run. | **PASS trong phạm vi đã ghi**; runtime phương pháp khác chưa đo |
| #19–#21: peer approval, tích hợp shared code trên `dev` | PR #42–#46 vẫn draft, chưa merge hoặc có review ở lần kiểm. | **OPEN chính thức** |

## Đối chiếu các nhóm yêu cầu của #39

[Issue #39](https://github.com/HungLD9505/adaptive-retention-ev/issues/39) yêu cầu Hùng làm end-to-end **và** đối chiếu độc lập với co-lead, Colab handoff và PR review. Masterplan cá nhân sau đó cho phép dùng local/Kaggle và hoãn Colab khi quota chưa khả dụng; điều này **không tự sửa acceptance criteria GitHub**.

| Nhóm yêu cầu #39 | Trạng thái dựa trên evidence | Cần ai quyết định / việc còn thiếu |
| --- | --- | --- |
| A: Model/Source/Target/Retention và 7/14/28 ngày thật | **PASS** phần triển khai và thực thi local. | Quyền/team duyệt Source một pass, initial config và sai khác so với implementation độc lập. |
| B: Controller, arriving labels, tests và giới hạn thống kê | **PASS** logic/fixtures và decision output. | Review độ phù hợp `Bmin`, block bootstrap, missing-day policy, lặp kiểm định. |
| C: Runner, state, audit, cost và resume | **PASS** local fixtures + representative 42→90 + bounded CUDA recovery. | So sánh với runner của Quyền, chốt một shared implementation. |
| Thin Colab notebook và Drive handoff | **PARTIAL**: Colab Development CPU 23/10 có Drive copy + hash; Colab T4 UI/probe mới không thực thi do session/reCAPTCHA. Local CUDA và Kaggle T4 là run khác. | Team quyết định tiêu chí thay thế hoặc chờ Colab GPU tensor/Drive verification; không ghi `PASS` từ UI T4. |
| Data/config/code/run/checkpoint lineage, artifact tồn tại ngoài session | **PASS có điều kiện truy cập**: local archive, private Kaggle raw/mounted readback, 354 hashes, notebook Python 3.12; [reproducibility](hung-39-reproducibility-handoff.md). | Cấp quyền private Kaggle dataset cho reviewer; user miễn lượt tải lại archive local, **không** coi là kiểm đã chạy. |
| So sánh hai implementation, giải quyết khác biệt, reviewed fixes | **OPEN**; không dùng điểm Development đẹp hơn để chọn implementation. | Quyền + Hùng + reviewer độc lập: cùng input/hash/entity/budget/seed/tolerance, so tensor/loss/gradient/decision/state rồi quyết định. |
| PR/CI, peer approval, tích hợp vào `dev`, nghiệm thu #39 | **OPEN**; #46 draft hướng `dev`, chưa có peer approval/merge. | Reviewer GitHub xem bốn báo cáo và artifacts; team tích hợp theo thứ tự dependency rồi quyết định issue. Codex không tự merge/đóng. |

## Đánh giá chất lượng mô hình: biết gì và chưa biết gì

- **Accuracy có giới hạn mẫu số:** 4.146 forecasts đã phát trên 6.210 origins yêu cầu, nhưng chỉ 2.322 ngày được chấm; 36/69 cells có MAE/RMSE, 33 null vì nhãn 24 giờ không đầy đủ. Ví dụ MAE/RMSE từng entity/seed và định nghĩa micro-average theo giờ ở [báo cáo thực nghiệm](hung-39-experiments-results.md). Không có cohort-wide score được phê duyệt.
- **Transferability:** chưa đo paired transfer gain hoặc Negative Transfer Rate so với target-only/frozen Source trên cùng origin, scale, budget và đơn vị station.
- **Retention:** chưa tách lợi ích của adaptive loss so với `λ=0` và fixed λ bằng ablation công bằng. `λ=0` ở đây vẫn khởi tạo từ Source.
- **Adaptivity:** 32 switches/382 keeps cho biết code hoạt động, **không** chứng minh controller thắng Online Best-λ hoặc proxy controllers. Audit cũ là phép đo riêng, không là baseline hoàn chỉnh.
- **Stability:** ba seeds dùng lại entity; 3 lần seed **không** là ba station độc lập hoặc confidence interval theo cohort.
- **Cost:** phải tính Source, Target, ba candidate, audit, update, checkpoint và I/O; 67,57 phút local chỉ đo **một** matrix current method. Không nhân thẳng để cam kết thời gian chín baseline/năm ablation.
- **Baseline tham chiếu có provenance:** [PR #45](https://github.com/HungLD9505/adaptive-retention-ev/pull/45) ghi Seasonal Naive **đề xuất** MAE 4,8798 và 4,0443 kWh cho Colab Development entity 1001/1871, ghép với adaptive 4,2836/2,6487 kWh trên 52/38 scored days. Các số có nguồn, nhưng PR draft chưa duyệt protocol, không chứng minh riêng transfer/retention/controller hay hiệu quả toàn cohort.

## Quyết định của nhóm và phân công kế tiếp

1. **Quyền và reviewer độc lập:** review #46 cùng các PR phụ thuộc #42–#44; đối chiếu implementation #19–#21 và thống nhất module cuối. Reviewer cần xét tính đúng của Source một pass, retention scale, controller policy, label availability và coverage. PR của Quyền do Hùng review; đồng tác giả cần reviewer thứ ba.
2. **Nhóm / #22:** [PR #51](https://github.com/HungLD9505/adaptive-retention-ev/pull/51) chứa công việc baseline/ablation đang review; chín baseline, năm ablation và paired-origin/station-first comparisons cần thực thi và duyệt. Hùng là reviewer, không tự nhận kết quả của Quyền thành output #39.
3. **Nhóm / #23:** [PR #52](https://github.com/HungLD9505/adaptive-retention-ev/pull/52) là contract đánh giá đang review. Chỉ khóa config, cohort, code và statistical plan bằng Development sau khi phương pháp và so sánh được chấp thuận; rồi mới chạy Final. Không dùng Final/test để sửa threshold/model.
4. **Người sở hữu artifact:** cấp quyền private Kaggle dataset cho reviewer hoặc chọn kênh lưu trữ được nhóm chấp nhận. Không xóa archive/run cũ; việc tải ngược ZIP đã được Hùng miễn ngày 26/10 nên giữ nhãn **SKIP theo yêu cầu**, không ghi PASS.

## Ánh xạ báo cáo lịch sử → bốn điểm đọc chuẩn

**Chính sách bảo toàn:** 19 Markdown cũ ghi trạng thái ở **thời điểm tạo** và nhiều inbound GitHub/README/report links trỏ tới chúng. Giữ nguyên toàn bộ và Git history; không xóa/đổi tên chỉ để đạt số bốn. Bốn file canonical là **bốn điểm đọc mới**, không phải toàn bộ `docs/reports/` của nhóm. Liên kết cũ vẫn hợp lệ; mỗi hàng dưới đây chỉ nguồn chính cho thông tin hiện tại.

| Báo cáo lịch sử giữ nguyên | Điểm đọc chuẩn / ghi chú |
| --- | --- |
| [Phase 0 environment](hung-39-phase0-environment-20261025-masterplan.md) | [Phương pháp](hung-39-method-implementation.md), [tái lập](hung-39-reproducibility-handoff.md) cho input/runtime. |
| [Phase A model](hung-39-phase-a-model-transfer-20261025-masterplan.md) | [Phương pháp](hung-39-method-implementation.md). |
| [Phase B controller](hung-39-phase-b-controller-20261025-masterplan.md) | [Phương pháp](hung-39-method-implementation.md). |
| [Phase C runner](hung-39-phase-c-runner-20261025-masterplan.md) | [Phương pháp](hung-39-method-implementation.md). |
| [Representative local / Phase D](hung-39-representative-local-20261025.md) | [Thực nghiệm](hung-39-experiments-results.md), nguồn 216-stage. |
| [Local verification](hung-39-local-verification-20261025.md) | [Thực nghiệm](hung-39-experiments-results.md), lượt 63-stage riêng. |
| [Kaggle transition](hung-39-kaggle-transition-20261025.md) | [Thực nghiệm](hung-39-experiments-results.md), nguyên nhân đổi backend. |
| [Kaggle verification](hung-39-kaggle-verification-20261025.md) | [Thực nghiệm](hung-39-experiments-results.md); mệnh đề “Version 1 chưa xác nhận” là snapshot sớm, được [platform UI](hung-39-platform-readiness-20261025T2325.md) bổ sung, nhưng ZIP chưa độc lập gắn với V1. |
| [Phase E handoff](hung-39-phase-e-handoff-20261025-masterplan.md) | [Tái lập](hung-39-reproducibility-handoff.md); “Python 3.12 còn thiếu” được kiểm ngày 26/10, không sửa Phase E gốc. |
| [Notebook validation](hung-39-notebook-validation-20261025-masterplan.md) | [Tái lập](hung-39-reproducibility-handoff.md), Python 3.13 snapshot. |
| [Post-freeze validation](hung-39-postfreeze-validation-20261026.md) | [Tái lập](hung-39-reproducibility-handoff.md), Python 3.12 CI. |
| [Python 3.12 notebook readback](hung-39-python312-notebook-readback-20261026.md) | [Tái lập](hung-39-reproducibility-handoff.md), clean kernels ngày 26/10. |
| [Platform readiness](hung-39-platform-readiness-20261025T2325.md) | [Tái lập](hung-39-reproducibility-handoff.md), Kaggle/Colab UI và upload. |
| [Cloud mounted readback](hung-39-cloud-mounted-readback-20261026.md) | [Tái lập](hung-39-reproducibility-handoff.md), Version 4 tree SHA. |
| [Raw archive upload](hung-39-raw-archive-upload-20261026.md) | [Tái lập](hung-39-reproducibility-handoff.md), quá trình upload private dataset. |
| [Raw archive readback](hung-39-raw-archive-readback-20261026.md) | [Tái lập](hung-39-reproducibility-handoff.md), Version 5 raw SHA/CRC. |
| [Completion snapshot](hung-39-completion-20261025.md) | [Đánh giá hiện tại](hung-39-assessment-handoff.md); “in progress” phản ánh thời điểm cũ. |
| [Executed-output handoff](hung-39-executed-output-handoff-20261025.md) | [Đánh giá hiện tại](hung-39-assessment-handoff.md), inventory các lượt chạy khác nhau. |
| [Final-report evidence](hung-39-final-report-evidence-20261025.md) | [Đánh giá hiện tại](hung-39-assessment-handoff.md), ranh giới claim cho báo cáo đồ án sau này. |

Các nguồn ngoài 19 file #39 như [Colab multiseed](hung-colab-development-multiseed-20261023.md), [input handoff](input-handoff.md), [evidence JSON](hung-39-representative-local-20261025-evidence.json), [`hung-sprint2.md`](hung-sprint2.md), [Report 1](../../adaptive_retention_report_1.pdf), configs, notebooks và mọi checkpoint/run artifact cũng được giữ nguyên. Không tạo sprint plan thứ hai. Nếu reviewer thấy số khác nhau giữa snapshot cũ và file mới, phải so **run ID, code SHA, ngày chạy và phạm vi** trước khi gọi đó là mâu thuẫn.
