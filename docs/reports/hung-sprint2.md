# Sprint 2 của Hùng — đề xuất giao diện và tiến độ cục bộ

Ngày: 21/10/2026. Phạm vi: issue #39 và các phần #19–#21. Mốc đối chiếu ban đầu: commit `7a57e9e8954eb8fcdc0809b1d7f02f6c32753a0c` trên nhánh `dev`. Đây là đề xuất triển khai và bằng chứng kiểm thử cục bộ; chưa chứng minh đã huấn luyện mô hình hay đã thống nhất giao diện với bên sử dụng.

## Kiểm tra đầu vào

- Report 1, trang 3–6, quy định mô hình, hàm mất mát, ứng viên, quyết định, replay và đánh giá. `AGENTS.md`, `README.md`, `docs/WORKFLOW.md`, `docs/SPRINT_PLAN.md`, `data/README.md` cùng các issue #15/#19/#20/#21/#39 quy định quy trình và điều kiện nghiệm thu.
- Dùng lại `ev_inputs` và thứ tự đặc trưng `ev-input-v1` đã được chấp nhận. Bộ dự báo nhận `X_hist[B,24,7]` và `C_future[B,24,5]` kiểu float32; không được nhận nhãn hay trạng thái hợp lệ của nhãn tương lai. `iter_forecasts` xác minh manifest và dấu vân tay artifact. Dữ liệu huấn luyện, nhãn, thực thể và lịch vẫn là các artifact riêng theo `ev-loader-run-v2`.
- Chính sách `ev-missing-data-v1` giữ lại origin trong lịch ngay cả khi không phát dự báo; chỉ chấm điểm/cập nhật khi đủ 24 nhãn hợp lệ đã đến; giữ `source_checkpoint_only` thành nhóm riêng; chặn scale chưa xác định. Tính nhân quả online trên dữ liệu thật chưa được chứng nhận.
- Worktree này chưa có snapshot DATA-v1. Không tìm thấy Python 3.12 bằng `py -3.12`. Chưa huấn luyện trên dữ liệu thật hoặc xác minh checksum của DATA-v1.

## Giao diện Python đề xuất

Các chữ ký sau mô tả ý nghĩa; tên và kiểu cụ thể có thể điều chỉnh sau khi bên sử dụng rà soát, nhưng hợp đồng dữ liệu đã được chấp nhận phải được giữ nguyên.

| Thành phần | Đầu vào | Đầu ra / bất biến |
| --- | --- | --- |
| Mô hình `forward` | `x_hist: Tensor[B,24,7]`, `c_future: Tensor[B,24,5]` | `forecast: Tensor[B,24]` không âm; `latent: Tensor[B,64]` được trả qua phương thức riêng hoặc đầu ra có cấu trúc. Latent là trạng thái GRU cuối. |
| Mất mát dự báo | `forecast`, `y_scaled`; chỉ nhận horizon hợp lệ và đủ nhãn | MAE trung bình trên 24 giờ và các mẫu đủ điều kiện; không điền nhãn thiếu. |
| Mất mát retention | Latent target và source đóng băng trên **cùng X đã chuẩn hóa**, `scale[64]` cố định từ huấn luyện source, epsilon dương | Trung bình theo mẫu của `(1/64) * sum(((z_target-z_source)/(scale+epsilon))**2)`. Source không nhận gradient; scale sai phải báo lỗi. |
| Khởi tạo target | Mô hình/checkpoint source định danh rõ, target `(dataset,city,entity,budget,scale_id)` và mẫu khởi tạo được phép | Mỗi target/budget có mô hình và optimizer độc lập. `source_checkpoint_only` bỏ qua thích nghi ban đầu. |
| Điểm controller | Mức đang hoạt động; MAE chuẩn hóa hằng ngày của cả ba ứng viên trên cùng ngày đủ 24 nhãn đã đến | Quan sát ghép cặp `MAE(active)-MAE(challenger)`; không chấm ngày thiếu nhãn. |
| Quyết định controller | Ba mức theo thứ tự; mức hiện tại; quan sát ghép cặp; `Bmin`, `delta`, `alpha`, độ dài đoạn bootstrap, số lần lấy mẫu và seed | Giữ nguyên trừ khi `B>=Bmin` và một đối thủ có `LCB>delta`; chọn LCB lớn nhất, rồi mức gần nhất, rồi thứ tự cố định. Quyết định chỉ áp dụng từ block kế tiếp. |
| Sự kiện runner | Origin theo lịch; đầu vào chỉ dành cho dự báo hoặc lý do bỏ qua; nhãn đến riêng | Tách ba bản sao trạng thái model/optimizer giống nhau đầu block; phát và lưu dự báo trước khi đọc nhãn; chỉ chấm/cập nhật khi nhãn đã đến đủ; hoàn tất quyết định block trước dự báo chịu ảnh hưởng. |
| Checkpoint/resume | Trạng thái model/optimizer đang hoạt động và ứng viên, toàn bộ RNG, dự báo đã phát, điểm, con trỏ sự kiện, block ID và trạng thái audit | Tạo checkpoint nguyên tử tại đúng vị trí replay; resume không phát lại dự báo hay lặp cập nhật optimizer. |
| Ràng buộc đầu vào | Các trường `ev-checkpoint-input-binding-v1` trong `docs/data/INPUT_ACCEPTANCE.md` | Gắn manifest SHA source/target, run ID, schema đặc trưng, identity, budget, scale ID và source checkpoint SHA; xác minh trước khi nạp. |
| Metric/bằng chứng | Dự báo đã phát, nhãn đủ điều kiện đã ghép, energy scale cố định, lịch, bộ đếm thực thi | MAE/RMSE đơn vị kWh gốc; coverage yêu cầu/phát/chấm và lý do thiếu; thời gian, số bước, bộ nhớ ứng viên và audit tách riêng; run ID, code SHA, config/seed, hash đầu vào/checkpoint. |

## Quyết định còn mở trên Development

Report 1 chưa cố định độ rộng/activation của MLP lịch tương lai, epsilon, cách ước lượng độ lệch chuẩn latent và xử lý scale suy biến, cách bootstrap/quantile và điều chỉnh cho hai đối thủ, ba mức lambda dương, mức ban đầu, `Bmin`, `delta`, `alpha`, lịch cập nhật hoặc danh sách seed. Chỉ chọn và ghi nhận các giá trị này trên Development; không dùng Final để lựa chọn. Phần #19 cho phép cấu hình tường minh trong khi bên sử dụng rà soát giao diện. Tích hợp #21 còn chờ thống nhất payload controller/runner. Chưa đăng bình luận lên các issue.

Bootstrap hiện xem các **quan sát hợp lệ liên tiếp** là liền kề, kể cả khi giữa chúng có một ngày theo lịch không đủ nhãn. Report 1 chưa quy định cách xử lý khoảng trống này; cần rà soát chính sách Development trước replay thật.

## Phân công và ngân sách token

Orchestrator chịu trách nhiệm hợp đồng, gate và bằng chứng. Agent model phụ trách #19 (model, retention, training, test); agent controller phụ trách #20 sau khi xem payload điểm; agent runner phụ trách #21 sau khi API #19/#20 ổn định; QA kiểm thử độc lập giá trị kỳ vọng và tích hợp. Tối đa hai agent sửa các file khác nhau cùng lúc.

Phân bổ mềm trong ngày: 15% kiểm tra đầu vào/giao diện, 50% model và retention, 20% controller, 10% kiểm thử có mục tiêu, 5% checkpoint/bàn giao. Đây là tỷ lệ lập kế hoạch, không phải bộ đếm token hay quyền bỏ qua gate. Runner nhận ngân sách sau khi giao diện model/controller đạt; không mở luồng lập trình thứ ba đồng thời. Khi usage gần hết, lưu checkpoint code/tài liệu an toàn rồi dừng; không sử dụng usage reset.

## Tiến độ cục bộ ngày 21/10/2026

- #19 đã có GRU, hàm mất mát và điểm vào smoke Source/Development có giới hạn, gắn manifest. #20 có controller độc lập với quy tắc bootstrap và phá hòa tường minh. Đây mới là kết quả code và fixture.
- `python -m tools.sources list` đạt. Lần chạy đầu của bộ test thất bại do sandbox không cho dùng thư mục tạm mặc định; lần chạy với TEMP nội bộ nhưng thiếu UTF-8 gặp ba lỗi codec Windows. Với `TEMP`/`TMP` trong worktree và `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`, `python -m unittest discover -s tests -q` đạt **140 test** tại checkpoint đầu, rồi **152 test** sau adapter đầu tiên trên Python 3.13. `python -m compileall -q experiments/hung_sprint2` và `git diff --check` đạt.
- Không có `python -m ruff`. Cài bản ghim `ruff==0.17.0` vào dependency cục bộ bị lỗi phân giải tên PyPI. Máy cũng không có Python 3.12.
- Chưa tải/xác minh DATA-v1; chưa có pretraining Source thật, adaptation Development thật, chạy Colab, replay controller trên dữ liệu thật, đối chiếu hai bản triển khai hay peer review. Các gate tương ứng vẫn mở.

## #20 — controller

Phần này dựa trên commit #19 cục bộ `1ba63a1` vì hai module dùng chung giao diện điểm đề xuất; #19 chưa merge vào `dev`. Controller nhận MAE chuẩn hóa ghép cặp theo ngày, bỏ ngày thiếu hoặc nhãn chưa đến, dùng moving-block bootstrap với cùng chỉ số lấy mẫu cho hai đối thủ và hiệu chỉnh Bonferroni `alpha/2`, rồi yêu cầu nghiêm ngặt `LCB > delta`. Phân vị dùng thống kê thứ tự thực nghiệm cố định; seed và block ID giúp tái lập. Chi tiết bootstrap là đề xuất chính sách Development, đang chờ bên sử dụng rà soát.

`python -m unittest tests.test_hung_controller -v` đạt **9 test** với Python 3.13, UTF-8 và TEMP nội bộ. Kết quả này chưa chứng minh thời điểm xử lý runner hay hành vi controller trên dữ liệu thật. Giá trị config trong fixture chỉ phục vụ test, chưa phải tham số nghiên cứu được chọn.

## #21 — runner và adapter đầu vào

Nhánh #21 được xếp chồng trên commit #20 `1bcde3a`, còn chờ review/merge. Runner fixture trên CPU tách ba ứng viên model/optimizer; lưu dự báo trước nhãn; chỉ chấm và cập nhật horizon đủ nhãn; quyết định block trước dự báo tiếp theo; mang trạng thái đã huấn luyện của ứng viên được chọn; giữ một nhánh audit chính sách cũ riêng cho một block. Checkpoint tạo mới chứa model/optimizer, RNG, dự báo chờ nhãn, con trỏ sự kiện, lịch sử điểm và ràng buộc đầu vào. Test bao phủ giữ mức, chuyển mức bắt buộc, thiếu nhãn, thứ tự biên block và resume.

QA tái hiện lỗi epsilon tràn dưới ở float32. Commit #19 `7a93558` đã chặn retention/gradient không hữu hạn, xác thực trước số mẫu Source giới hạn và ghi checkpoint nguyên tử. Sửa lỗi được đưa vào nhánh này ở `68fb36e` và vào #20 ở `ac1726e`. Trước adapter, test runner fixture đạt **6 test** và toàn nhánh đạt **149 test**.

Adapter replay hiện xác minh manifest v2 cùng hash artifact, chọn một target Development, kiểm tra binding và scale, giữ coverage theo lịch, và phát dự báo chỉ dùng predictor trước khi tra nhãn tương ứng. `ready_labels` chỉ cho phép horizon đầy đủ đã sẵn sàng. Fixture test bao phủ nhãn đến trễ, thiếu nhãn, coverage bị chặn, artifact bị sửa, binding và thứ tự phát dự báo. Sau adapter, toàn bộ **152 test đạt**; commit checkpoint hiện tại là `1f1a888`.

Checkpoint tiếp theo bổ sung hàng đợi nhãn theo `available_at`: nhãn đầy đủ đến trễ được chấm theo dự báo đã lưu và cập nhật các ứng viên hiện hành trước dự báo tiếp theo. Quyết định block đã phát không đổi hồi tố. Adapter kiểm tra lịch, con trỏ và forecast đã phát để resume mà không phát lặp. Fixture mới bao phủ nhãn trễ qua biên block, thứ tự đến khác thứ tự origin và resume khi còn nhãn chờ. Toàn nhánh chạy **156 test, OK**; `compileall` và `git diff --check` đạt.

Sau snapshot báo cáo nhóm lúc 20:31, nhánh #19 đã có [draft PR #42](https://github.com/HungLD9505/adaptive-retention-ev/pull/42) với code/test/báo cáo cục bộ; chưa có PR cho #20/#21. Snapshot cũ không phản ánh các commit local hoặc draft PR mới, nhưng cũng không chứng minh các gate đã hoàn tất.

Gate replay Development thật vẫn mở: chưa có kiểm chứng DATA-v1, xử lý CUDA RNG, event log bền vững, thống kê đầy đủ chi phí và smoke thực tại biên block. Nhãn vẫn chưa sẵn sàng tại cutoff cuối replay tiếp tục không được chấm. Không suy diễn từ fixture rằng gate dữ liệu thật, Colab, Ruff hay Python 3.12 đã đạt.
