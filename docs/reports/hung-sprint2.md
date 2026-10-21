# Sprint 2 của Hùng — đề xuất giao diện và checkpoint #19

Ngày: 21/10/2026. Phạm vi: #39, #19–#21. Mốc đối chiếu: commit `7a57e9e8954eb8fcdc0809b1d7f02f6c32753a0c` trên `dev`. Đây là đề xuất giao diện để rà soát và bằng chứng kiểm thử cục bộ, chưa phải bằng chứng huấn luyện thật hay thống nhất giao diện.

## Kiểm tra đầu vào

- Report 1, trang 3–6, quy định mô hình, hàm mất mát, ứng viên, quyết định, replay và đánh giá. `AGENTS.md`, `README.md`, `docs/WORKFLOW.md`, `docs/SPRINT_PLAN.md`, `data/README.md` và các issue #15/#19/#20/#21/#39 quy định quy trình, gate nghiệm thu.
- Dùng lại `ev_inputs`, thứ tự đặc trưng `ev-input-v1` và manifest `ev-loader-run-v2` đã được chấp nhận. Bộ dự báo nhận `X_hist[B,24,7]` và `C_future[B,24,5]` float32; không nhận nhãn hay trạng thái nhãn tương lai. Training, forecast, label, entity và schedule là các artifact riêng.
- Chính sách `ev-missing-data-v1` giữ origin theo lịch dù không phát dự báo; chỉ chấm/cập nhật khi đủ 24 nhãn hợp lệ đã đến; tách `source_checkpoint_only`; chặn scale chưa xác định. Tính nhân quả online trên dữ liệu thật chưa được chứng nhận.
- Worktree chưa có snapshot DATA-v1. Không tìm thấy Python 3.12 bằng `py -3.12`; chưa huấn luyện hay xác minh checksum dữ liệu thật.

## Giao diện Python đề xuất

Tên và kiểu cụ thể có thể sửa sau khi bên sử dụng rà soát, nhưng không thay đổi hợp đồng dữ liệu đã chấp nhận.

| Thành phần | Đầu vào | Đầu ra / bất biến |
| --- | --- | --- |
| Mô hình `forward` | `x_hist: Tensor[B,24,7]`, `c_future: Tensor[B,24,5]` | Dự báo `Tensor[B,24]` không âm; latent `Tensor[B,64]` lấy từ trạng thái GRU cuối và truy cập tường minh. |
| Mất mát dự báo | Dự báo và `y_scaled` đủ 24 nhãn hợp lệ | MAE trung bình trên 24 giờ và các mẫu đủ điều kiện; không điền nhãn thiếu. |
| Mất mát retention | Latent target, latent source đóng băng trên **cùng X đã chuẩn hóa**, `scale[64]` từ Source và epsilon dương | Trung bình theo mẫu của `(1/64) * sum(((z_target-z_source)/(scale+epsilon))**2)`; source không nhận gradient; scale sai phải báo lỗi. |
| Khởi tạo target | Checkpoint source, identity `(dataset,city,entity,budget,scale_id)` và mẫu khởi tạo được phép | Mỗi target/budget có model và optimizer riêng; `source_checkpoint_only` bỏ qua thích nghi ban đầu. |
| Điểm controller | Mức đang hoạt động và MAE chuẩn hóa của ba ứng viên trên cùng ngày đủ nhãn | Quan sát ghép cặp `MAE(active)-MAE(challenger)`; không chấm ngày thiếu. |
| Quyết định controller | Ba mức, mức hiện tại, quan sát ghép cặp, `Bmin`, `delta`, `alpha`, đoạn bootstrap, số lần lấy mẫu và seed | Giữ mức trừ khi `B>=Bmin` và `LCB>delta`; chọn LCB lớn nhất, mức gần nhất, rồi thứ tự cố định. Chỉ đổi từ block kế tiếp. |
| Sự kiện runner | Origin theo lịch, đầu vào chỉ dành cho dự báo hoặc lý do bỏ qua, nhãn đến riêng | Tách ba model/optimizer giống nhau đầu block; lưu dự báo trước nhãn; chỉ chấm/cập nhật sau khi đủ nhãn; quyết định block trước dự báo chịu ảnh hưởng. |
| Checkpoint/resume | Model/optimizer, RNG, dự báo, điểm, con trỏ sự kiện, block ID, audit | Checkpoint mới ghi nguyên tử tại đúng vị trí replay; resume không phát lại dự báo hay cập nhật. |
| Ràng buộc đầu vào | `ev-checkpoint-input-binding-v1` theo `docs/data/INPUT_ACCEPTANCE.md` | Gắn manifest SHA, run ID, feature schema, identity, budget, scale ID và source checkpoint SHA; xác minh trước khi nạp. |
| Metric/bằng chứng | Dự báo, nhãn đủ điều kiện, energy scale, lịch, bộ đếm | MAE/RMSE kWh gốc; coverage yêu cầu/phát/chấm và lý do thiếu; chi phí ứng viên/audit riêng; run ID, code SHA, config/seed và hash. |

## Quyết định cần rà soát trên Development

Report 1 chưa cố định độ rộng/activation của MLP lịch tương lai, epsilon, cách tính độ lệch chuẩn latent và xử lý scale suy biến, cách bootstrap/quantile và hiệu chỉnh hai đối thủ, mức lambda dương, mức ban đầu, `Bmin`, `delta`, `alpha`, lịch cập nhật hoặc danh sách seed. Chỉ chọn các giá trị này trên Development; không dùng Final. #21 còn chờ thống nhất payload controller/runner. Chưa đăng đề xuất lên các issue.

## Phân công và ngân sách token

Orchestrator giữ hợp đồng, gate, bằng chứng. Agent model làm #19; controller làm #20 sau khi nhận payload điểm; runner làm #21 sau API #19/#20; QA kiểm thử giá trị kỳ vọng và tích hợp độc lập. Tối đa hai agent sửa các file khác nhau đồng thời.

Phân bổ mềm trong ngày: 15% kiểm tra đầu vào/giao diện, 50% model/retention, 20% controller, 10% kiểm thử, 5% checkpoint/bàn giao. Đây là tỷ lệ lập kế hoạch, không phải số token đã tiêu thụ hay quyền bỏ qua gate. Khi usage gần hết, lưu checkpoint an toàn rồi dừng; không dùng usage reset.

## Bằng chứng cục bộ #19 — 21/10/2026

- Đã viết GRU hai lớp, loss, retention, checkpoint gắn manifest và CLI smoke Source/Development có giới hạn. Commit `f4118fb` thêm chặn loss/gradient Source không hữu hạn trước bước optimizer.
- `python -m unittest discover -s tests -q` đạt **135 test** trên Python 3.13 với TEMP/TMP nội bộ và UTF-8. `git diff --check` đạt. Trước đó, lần thử đầu thất bại vì sandbox từ chối thư mục tạm mặc định; lần thử kế với TEMP nội bộ nhưng thiếu UTF-8 gặp ba lỗi codec Windows.
- Không có Ruff; cài `ruff==0.17.0` thất bại do lỗi phân giải tên PyPI. Python 3.12 không có trên máy.
- [Draft PR #42](https://github.com/HungLD9505/adaptive-retention-ev/pull/42) công bố code để review. Chưa có DATA-v1, huấn luyện Source/Development thật, kết quả Colab, so sánh độc lập hoặc peer approval. Smoke fixture không chứng minh hiệu quả mô hình; các gate này vẫn mở.
- Lượt CI đầu của PR #42 thất bại trên Windows và Ubuntu vì `requirements-dev.txt` chưa cài PyTorch, khiến ba module test #19 không import được. Nhánh đề xuất thêm `requirements-model.txt` ghim PyTorch 2.8.0 CPU và bước cài riêng trong CI; thay đổi dependency này cần review, chưa được coi là CI đạt cho đến khi workflow mới chạy xong.
- Sau khi cài Ruff 0.17.0 vào cache nội bộ và định dạng năm file #19, toàn bộ **135 test đạt**; `ruff check .`, `ruff format --check .` và `git diff --check` đều đạt tại máy local. Kết quả này không thay thế kiểm tra CI Python 3.12.
