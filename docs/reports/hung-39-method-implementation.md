# #39 — Phương pháp và triển khai mô hình

**Cập nhật:** 26/10/2026 (ICT). **Phạm vi:** phần triển khai của Hùng cho #19, #20, #21 và lượt Development #39. Đây là điểm đọc chuẩn về phương pháp; [Report 1](../../adaptive_retention_report_1.pdf) là thiết kế gốc và các [báo cáo Phase A/B/C](#nguồn-và-giới-hạn) giữ nguyên bằng chứng theo thời điểm. Bảng số liệu chạy thuộc [báo cáo thực nghiệm](hung-39-experiments-results.md), còn trạng thái nghiệm thu thuộc [báo cáo đánh giá](hung-39-assessment-handoff.md).

## Bài toán và ranh giới dữ liệu

Dự báo một lần mỗi ngày cho 24 giờ tiếp theo của một UrbanEV station có ít lịch sử target. Mục tiêu là năng lượng sạc theo giờ tính bằng kWh theo pipeline dữ liệu đã audit; không tự gọi đó là công tơ đo trực tiếp. Source chỉ dùng phần pre-deployment được phép, còn target adaptation và replay dùng Development. Nhãn của Final/test không tham gia chọn model, seed, ngưỡng hay cấu hình. Phân vai và hạn chế về timestamp, missingness, scaler nằm trong [hợp đồng input](../data/INPUT_ACCEPTANCE.md) và [báo cáo input](input-handoff.md).

| Tensor | Shape | Vai trò |
| --- | --- | --- |
| `X_hist` | `[B,24,7]` | 24 giờ lịch sử, gồm giá trị đã scale, biến thời gian và mask hiện diện; số 0 thật khác dữ liệu thiếu. |
| `C_future` | `[B,24,5]` | Lịch tương lai đã biết tại origin. |
| `Y` | `[B,24]` | Nhãn hoàn chỉnh để huấn luyện/chấm khi đã đến hạn. |
| `forecast` | `[B,24]` | 24 giá trị không âm; metric báo cáo chuyển về kWh gốc. |

Input không có lịch sử khả dụng vẫn giữ trong schedule nhưng không tạo forecast. Ngày thiếu bất cứ nhãn nào trong 24 giờ không được chấm hoặc cập nhật. Các budget lịch sử target 7/14/28 ngày là các thí nghiệm tách biệt, không được dùng nhãn tương lai để mở rộng budget.

## Kiến trúc GRU và kiểm tra tham số

[`ForecastGRU`](../../experiments/hung_sprint2/model.py) mã hóa `X_hist` bằng GRU hai lớp, hidden size 64, lấy latent cuối `z`. Lịch tương lai được làm phẳng từ `24×5=120` và đưa qua Linear `120→8` + ReLU. Ghép `64+8=72`, Linear `72→24` và Softplus tạo forecast không âm. Đếm trực tiếp `sum(p.numel() for p in ForecastGRU(ModelConfig(calendar_hidden=8)).parameters())` trong môi trường Python 3.12/PyTorch của repo ngày 26/10 cho **41.696 tham số**: encoder 38.976, calendar MLP 968, head 1.752. Đây là số lượng cấu trúc, không phải số mẫu huấn luyện hay kích thước checkpoint.

## Source pretraining và target adaptation

[`training.py`](../../experiments/hung_sprint2/training.py) huấn luyện Source một pass trên 65.888 ví dụ được phép, batch 32, 2.059 bước cho mỗi Source stage, Adam learning rate `0,001`. Có 871 Source station ID đóng góp input; cùng Source examples có thể được dùng lại giữa budget, không được cộng chúng thành dữ liệu độc lập. Target khởi tạo từ checkpoint Source, có Adam state riêng; reference Source được clone, đóng băng và ở evaluation mode. Target có dữ liệu ban đầu học một pass, batch 2, learning rate `0,001`. Target có scaler nhưng không có mẫu thích nghi ban đầu thuộc stratum `source_checkpoint_only`, ghi 0 target step chứ không tạo nhãn giả.

Với `H=24`, latent dimension `d=64` và batch gồm nhãn hoàn chỉnh:

\[
L_{\mathrm{forecast}}=\frac{1}{BH}\sum_{b=1}^{B}\sum_{h=1}^{H}|\hat y_{b,h}-y_{b,h}|,\quad
L_{\mathrm{retain}}=\frac{1}{Bd}\sum_{b=1}^{B}\sum_{k=1}^{d}\left(\frac{z_{T,b,k}-z_{S,b,k}}{s_k+\epsilon}\right)^2,
\quad L_{\mathrm{total}}=L_{\mathrm{forecast}}+\lambda L_{\mathrm{retain}}.
\]

`s_k` là độ lệch chuẩn quần thể (`correction=0`) từ Source training histories hợp lệ, cố định sau khi tính; `epsilon=10⁻⁶`. Cùng `X_hist` đã chuẩn hóa theo target đi qua encoder Target và Source frozen; gradient chỉ cập nhật Target. Trong replay, `λ=0` là **full fine-tuning từ Source weights**, không phải target-only. Cấu hình Target ban đầu dùng retention weight `0,1`; đây là thiết lập chẩn đoán cần review, không được chọn lại sau khi nhìn MAE.

## Confidence Controller

[`controller.py`](../../experiments/hung_sprint2/controller.py) nhận sai số trên **cùng ngày và cùng 24 nhãn hoàn chỉnh đã đến** cho active và hai challenger. Với challenger `j`, cải thiện ghép cặp của ngày `t` là

\[
\Delta_{t,j}=\operatorname{MAE}_{active,t}-\operatorname{MAE}_{j,t}.
\]

Bootstrap lấy block ngày liên tiếp dài 2, dùng cùng sampled indices cho hai challenger và 100 lần resample. Cần ít nhất năm ngày hợp lệ trong block 14 ngày. Mỗi challenger dùng `α/2=0,025` từ `α=0,05`; cận dưới thực nghiệm là order statistic index 2 (zero-based) khi có 100 resamples. Chỉ xét switch nếu `LCB > δ=0`; chọn LCB lớn nhất, sau đó mức `λ` gần active nhất, sau đó thứ tự cấu hình. Bằng ngưỡng hoặc thiếu bằng chứng thì giữ active. Ba mức thực thi là `{0; 0,1; 0,2}`. Bonferroni ở **một quyết định** không chứng minh kiểm soát sai lầm qua nhiều block/entity; 100 resamples chưa được phê duyệt là đủ cho suy luận nghiên cứu.

## Runner và thứ tự nhân quả

[`runner.py`](../../experiments/hung_sprint2/runner.py), [`replay_inputs.py`](../../experiments/hung_sprint2/replay_inputs.py), [`checkpoint.py`](../../experiments/hung_sprint2/checkpoint.py) và [`evaluation.py`](../../experiments/hung_sprint2/evaluation.py) triển khai vòng prequential. Pseudocode tương ứng với [Phase C](hung-39-phase-c-runner-20261025-masterplan.md):

```text
đầu block: clone active model + Adam thành 3 candidate độc lập
cho từng origin theo schedule:
    ghi forecast của 3 candidate, hoặc ghi skip vì lịch sử trống
    nhận các label khi available_at cho phép; chỉ chấm/cập nhật khi đủ 24 nhãn
cuối block: tính LCB từ paired errors đã đến; giữ/switch sang candidate đã học
nếu switch: chạy old-policy audit độc lập ở block kế tiếp
ghi event journal, manifest, checkpoint gồm cursor, pending labels, model/Adam và RNG
```

Replay chạy đến origin 42 rồi resume đến origin 90 ở output stage riêng. Mỗi candidate dùng cùng thứ tự dữ liệu và RNG được ghép cặp; audit không tham gia chọn controller. Forecast đã phát không bị sửa khi policy đổi. Runner checkpoint chứa CPU/CUDA RNG và từ chối resume khác loại thiết bị. Checkpoint **model-stage lịch sử** của ma trận chưa có RNG snapshot; tính năng `restore_rng=True` bổ sung **sau** lượt run chỉ áp dụng cho checkpoint mới, không làm thay đổi run đã freeze.

## Cấu hình, entrypoint và nguồn

[`development_config_v1.json`](../../experiments/hung_sprint2/development_config_v1.json) và [`hung-development-selection-20261025-v2.json`](hung-development-selection-20261025-v2.json) cố định seeds 7/11/19, budget 7/14/28 ngày và danh sách entity 6/8/9. Entrypoint là [`run_development.py`](../../experiments/hung_sprint2/run_development.py), gọi các CLI/core modules; bốn [notebook mỏng](../../experiments/hung_sprint2/notebooks/) chỉ trình bày và đọc artifact, không phải implementation thứ hai. Lượt đại diện thực thi mã commit `a34a49e5f04920ef30456fe6c0ea56eb2f1d659a` ngày 25/10/2026; lệnh và thời điểm nằm trong [báo cáo thực nghiệm](hung-39-experiments-results.md). Bản handoff/PR sau đó có thay đổi checkpoint RNG; không tráo code mới vào run identity lịch sử.

### Nguồn và giới hạn

- [Phase 0](hung-39-phase0-environment-20261025-masterplan.md), [Phase A](hung-39-phase-a-model-transfer-20261025-masterplan.md), [Phase B](hung-39-phase-b-controller-20261025-masterplan.md), [Phase C](hung-39-phase-c-runner-20261025-masterplan.md): giải thích chi tiết và kiểm thử theo từng mốc.
- [Report 1](../../adaptive_retention_report_1.pdf) quy định bài toán 24→24, loss, ba candidate, thứ tự nhãn và các so sánh cần có. GRU là backbone, không phải novelty đã chứng minh.
- Source một pass, ngưỡng controller, missing-day bootstrap policy và mức λ hiện là cấu hình Development chẩn đoán. Sự đúng đắn của code không chứng minh transfer, retention hay adaptivity có lợi; các phép so sánh thuộc #22/#23 và cần review độc lập.
