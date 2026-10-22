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
- Lần cài Ruff đầu thất bại do lỗi phân giải tên PyPI; lần cài sau vào cache nội bộ đạt. Trên nhánh #19 sau khi định dạng, **135 test**, `ruff check .`, `ruff format --check .` và `git diff --check` đều đạt tại máy local. Máy vẫn không có Python 3.12.
- Chưa tải/xác minh DATA-v1; chưa có pretraining Source thật, adaptation Development thật, chạy Colab, replay controller trên dữ liệu thật, đối chiếu hai bản triển khai hay peer review. Các gate tương ứng vẫn mở.
- Lượt CI đầu của PR #42/#43 thất bại trên Windows và Ubuntu vì chưa cài PyTorch, khiến các module test model không import được. PR #42 đề xuất `requirements-model.txt` ghim PyTorch 2.8.0 CPU và bước cài riêng trong CI; thay đổi dependency này vẫn cần review. Workflow mới đã đạt trên Windows và Ubuntu cho PR #42 (commit `b76d62a`, run 56) và PR #43 (commit `8f93d79`, run 57), gồm unit test, Ruff và kiểm tra dependency trên Python 3.12.

## #20 — controller

Phần này dựa trên commit #19 cục bộ `1ba63a1` vì hai module dùng chung giao diện điểm đề xuất; #19 chưa merge vào `dev`. Controller nhận MAE chuẩn hóa ghép cặp theo ngày, bỏ ngày thiếu hoặc nhãn chưa đến, dùng moving-block bootstrap với cùng chỉ số lấy mẫu cho hai đối thủ và hiệu chỉnh Bonferroni `alpha/2`, rồi yêu cầu nghiêm ngặt `LCB > delta`. Phân vị dùng thống kê thứ tự thực nghiệm cố định; seed và block ID giúp tái lập. Chi tiết bootstrap là đề xuất chính sách Development, đang chờ bên sử dụng rà soát.

`python -m unittest tests.test_hung_controller -v` đạt **9 test** với Python 3.13, UTF-8 và TEMP nội bộ. Kết quả này chưa chứng minh thời điểm xử lý runner hay hành vi controller trên dữ liệu thật. Giá trị config trong fixture chỉ phục vụ test, chưa phải tham số nghiên cứu được chọn.

Nhánh #20 đã hợp nhất lịch sử phụ thuộc #19 ở commit `b5b126d`; trên nhánh #20 sau hợp nhất, **144 test đạt**. Draft PR #43 hướng vào `dev` nhưng phụ thuộc review/merge PR #42.

## #21 — runner và adapter đầu vào

Nhánh #21 được xếp chồng trên commit #20 `1bcde3a`, còn chờ review/merge. Runner fixture trên CPU tách ba ứng viên model/optimizer; lưu dự báo trước nhãn; chỉ chấm và cập nhật horizon đủ nhãn; quyết định block trước dự báo tiếp theo; mang trạng thái đã huấn luyện của ứng viên được chọn; giữ một nhánh audit chính sách cũ riêng cho một block. Checkpoint tạo mới chứa model/optimizer, RNG, dự báo chờ nhãn, con trỏ sự kiện, lịch sử điểm và ràng buộc đầu vào. Test bao phủ giữ mức, chuyển mức bắt buộc, thiếu nhãn, thứ tự biên block và resume.

QA tái hiện lỗi epsilon tràn dưới ở float32. Commit #19 `7a93558` đã chặn retention/gradient không hữu hạn, xác thực trước số mẫu Source giới hạn và ghi checkpoint nguyên tử. Sửa lỗi được đưa vào nhánh này ở `68fb36e` và vào #20 ở `ac1726e`. Trước adapter, test runner fixture đạt **6 test** và toàn nhánh đạt **149 test**.

Adapter replay hiện xác minh manifest v2 cùng hash artifact, chọn một target Development, kiểm tra binding và scale, giữ coverage theo lịch, và phát dự báo chỉ dùng predictor trước khi tra nhãn tương ứng. `ready_labels` chỉ cho phép horizon đầy đủ đã sẵn sàng. Fixture test bao phủ nhãn đến trễ, thiếu nhãn, coverage bị chặn, artifact bị sửa, binding và thứ tự phát dự báo. Sau adapter, toàn bộ **152 test đạt**; commit checkpoint hiện tại là `1f1a888`.

Checkpoint `d8fb07d` bổ sung hàng đợi nhãn theo `available_at`: nhãn đầy đủ đến trễ được chấm theo dự báo đã lưu và cập nhật các ứng viên hiện hành trước dự báo tiếp theo. Quyết định block đã phát không đổi hồi tố. Adapter kiểm tra lịch, con trỏ và forecast đã phát để resume mà không phát lặp. Fixture mới bao phủ nhãn trễ qua biên block, thứ tự đến khác thứ tự origin và resume khi còn nhãn chờ. Sau đó sửa lỗi Source #19 từ commit `f4118fb` được áp dụng rõ ràng lên nhánh này thành `3b88093`. Sau khi đồng bộ dependency/CI và định dạng Ruff, toàn nhánh chạy **157 test, OK**; `compileall`, `ruff check --no-cache .`, `ruff format --check .` và `git diff --check` đều đạt cục bộ.

Sau snapshot báo cáo nhóm lúc 20:31, các nhánh đã có [draft PR #42](https://github.com/HungLD9505/adaptive-retention-ev/pull/42) cho #19, [draft PR #43](https://github.com/HungLD9505/adaptive-retention-ev/pull/43) cho #20 và [draft PR #44](https://github.com/HungLD9505/adaptive-retention-ev/pull/44) cho #21. PR #43/#44 đang xếp chồng phụ thuộc dù đều hướng vào `dev`; thứ tự review/merge phải là #42 → #43 → #44 và không được merge độc lập. Snapshot cũ không phản ánh các commit hoặc draft PR mới, nhưng cũng không chứng minh các gate đã hoàn tất. CI cho commit Runner `59e856e` (run 58) cũng đạt trên Windows và Ubuntu, gồm unit test, Ruff và kiểm tra dependency trên Python 3.12.

Gate replay Development thật vẫn mở: chưa có kiểm chứng DATA-v1, xử lý CUDA RNG, event log bền vững, thống kê đầy đủ chi phí và smoke thực tại biên block. Nhãn vẫn chưa sẵn sàng tại cutoff cuối replay tiếp tục không được chấm. CI đã xác nhận test và Ruff trên Python 3.12 ở ba nhánh; không suy diễn từ fixture rằng gate dữ liệu thật hay Colab đã đạt.

## Cập nhật Phase 04 — 22/10/2026

- `evaluation.py` tính tổng sai số tuyệt đối/bình phương theo kWh gốc cho từng horizon 24 giờ đủ nhãn, tổng hợp MAE/RMSE theo số giờ và kiểm tra coverage theo lịch yêu cầu. Evaluation replay dùng đúng dự báo đã phát và nhãn đã đến, giữ ba ứng viên, live và audit riêng; không chấm horizon thiếu. Unit test có giá trị kỳ vọng tính tay và fixture adapter. Chưa có metric thực nghiệm từ DATA-v1.
- Runner đo số lần và nanosecond thực tế của `model.forward` và `target_step` cho từng ứng viên/audit trên CPU; các bộ đếm được lưu qua checkpoint. Phạm vi đo không gồm I/O, tiền xử lý, bộ nhớ hay toàn bộ wall time; checkpoint cũ không có số đo được đánh dấu `complete=False`. Sự kiện hiện được lưu trong checkpoint, chưa có journal từng sự kiện trên đĩa.
- Sau thay đổi này, `python -m unittest discover -s tests -q` đạt **164/164 test** trên Python 3.13 với TEMP nội bộ và UTF-8. `python -m compileall -q experiments/hung_sprint2`, `python -m tools.sources list`, Ruff check/format và `git diff --check` đạt cục bộ. Đây là kết quả offline fixture, không phải Source/Development training thật.
- Gate còn mở: DATA-v1 snapshot và checksum, real Development replay tại biên block, chọn và khóa config trên Development, CUDA RNG nếu chạy GPU, journal bền vững, bộ nhớ/cost đầy đủ, Colab output, so sánh implementation độc lập và peer review. Không dùng Final để chọn tham số.

## Đối chiếu tiến độ cuối ngày 21/10 — cập nhật 22/10/2026

- [Daily progress tracker](https://github.com/HungLD9505/ev-capstone-control/blob/main/reports/DAILY_PROGRESS.md) đã có snapshot mới lúc **00:59:16 ngày 22/10 (UTC+7)**, thay cho mục 21/10 còn ở mốc 02:11. Tracker nhận #19, #20, #21 và #39 là `IN_REVIEW` theo **phân loại bằng chứng GitHub**, không phải đã được người duyệt chấp thuận hay đã đạt nghiệm thu. #15 vẫn `IN_PROGRESS`; #41 vẫn `NOT_STARTED` theo tracker. Không có nhiệm vụ nào được tracker xác nhận hoàn thành.
- Ba PR [#42](https://github.com/HungLD9505/adaptive-retention-ev/pull/42) (`b76d62a`), [#43](https://github.com/HungLD9505/adaptive-retention-ev/pull/43) (`8f93d79`) và [#44](https://github.com/HungLD9505/adaptive-retention-ev/pull/44) (`0b335a1`) đều **mở ở trạng thái draft**, hướng vào `dev`, chưa merge. Workflow Foundation checks tại đúng các head SHA trên đều thành công ở Windows và Ubuntu; riêng #44 là [run 60](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/39644139858). Các nhánh cục bộ sạch và đã đồng bộ lên origin.
- Mốc #39 là **23/10**, còn một ngày theo snapshot 22/10; #19–#21 có hạn **29/10**. Bằng chứng hiện có là code, fixture, kiểm thử offline và CI. Chưa có DATA-v1, huấn luyện Source/Development thật, replay thực tại biên block, kết quả mô hình, đối chiếu với Quyền hay peer review. Vì thế không đánh dấu #39 hoặc #19–#21 hoàn thành.
- Việc cần xử lý tiếp: thống nhất giao diện/chính sách Development với Quyền và nhóm; cung cấp, xác minh hash DATA-v1 trước Phase 05 trên Colab; ghi checkpoint/log/runtime của chạy thật; sau đó đối chiếu hai implementation và review theo thứ tự phụ thuộc #42 → #43 → #44. Kế hoạch sprint vẫn ở trạng thái *Proposed for team review* trên tracker.

## Chuẩn bị kiểm tra dữ liệu trước Colab — chưa chạy trên DATA-v1

Để bắt đầu UrbanEV, gói đầu vào cần tải là `inputs-urbanev-SZH-v1.zip`, kích thước **151254390 byte**, SHA-256 `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7` theo release catalog `DATA-v1-20261019`. Sau khi tải vào vị trí mới, có thể chạy:

```powershell
$archive = 'C:\duong-dan-moi\inputs-urbanev-SZH-v1.zip'
python -m experiments.hung_sprint2.cli verify-input-zip --archive $archive --package inputs-urbanev-SZH-v1.zip
```

Lệnh chỉ đọc và đối chiếu tên gói, kích thước, SHA-256, CRC với catalog cố định; không giải nén, xác minh manifest bên trong hay huấn luyện. Đã kiểm thử lệnh bằng ZIP fixture nhỏ, **chưa** tải/chạy trên gói DATA-v1. Chỉ khi ZIP thật đạt mới giải nén vào checkout sạch theo `docs/data/DATA_DOWNLOADS.md`, xác minh manifest của từng run 7/14/28 ngày và chọn/khóa config trên Development. Chưa có lệnh huấn luyện đầy đủ/Colab được thực thi hoặc xác nhận.

## Rà soát báo cáo cuối ngày 21/10 — đối chiếu lúc 08:24 ngày 22/10/2026

- Báo cáo 20:31 ngày 21/10 chỉ có snapshot tới 12:19 và chưa thấy lượt đồng bộ 20:10. Tracker hiện đã có snapshot mới lúc **00:59:16 ngày 22/10 (UTC+7)**. Phân loại #19, #20, #21 và #39 chuyển sang `IN_REVIEW` do ba draft PR liên kết, **không phải** đã được duyệt hoặc nghiệm thu; tracker chưa xác minh hạng mục nào hoàn thành. #15 vẫn `IN_PROGRESS`, #41 `NOT_STARTED` theo snapshot.
- Draft [PR #42](https://github.com/HungLD9505/adaptive-retention-ev/pull/42) tại `b76d62a`, [PR #43](https://github.com/HungLD9505/adaptive-retention-ev/pull/43) tại `8f93d79` và [PR #44](https://github.com/HungLD9505/adaptive-retention-ev/pull/44) đều chưa merge. GitHub Foundation checks đã `success` cho #42/#43 (run 56/57) và head #44 **trước khi thêm replay CLI** là `534f8a0` (run 62). Commit replay CLI/báo cáo `083daff` đã đẩy lên #44; cần xem CI tại head mới trước khi xác nhận. #43/#44 chứa lịch sử phụ thuộc #42/#43 nên vẫn cần review theo thứ tự #42 → #43 → #44. Kết quả CI chỉ xác nhận bộ kiểm tra hiện có, không xác nhận nghiên cứu thực nghiệm.
- Đã chuẩn bị lệnh `replay-development` giới hạn số origin và resume từ checkpoint vào **output mới**; kiểm tra SHA manifest/artifact, binding và chuỗi checkpoint Source/target/runner. Manifest đầu ra ghi cấu hình/seed/hash code, coverage, MAE/RMSE kWh cho forecast đã chấm, bộ đếm runtime hiện có, sự kiện/quyết định và checkpoint runner. Đây là code mới cùng fixture, **chưa** chạy trên DATA-v1 hay Colab. Bộ đếm runtime chỉ bao phủ CPU `model.forward` và `target_step`; chưa đo toàn bộ wall time, I/O, bộ nhớ hoặc chi phí đầy đủ. Event evidence trong manifest chưa phải journal bền vững theo từng sự kiện.
- Trên Python 3.13 cục bộ, với TEMP/TMP trong worktree và UTF-8, `python -m unittest discover -s tests -q` đạt **167/167 test**. `ruff check --no-cache .`, `ruff format --check .`, `python -m compileall -q experiments\hung_sprint2` và `git diff --check` đạt. Chưa xác minh Python 3.12 cho thay đổi CLI mới qua CI tại thời điểm đối chiếu này.
- Mốc bàn giao cá nhân [#39](https://github.com/HungLD9505/adaptive-retention-ev/issues/39) là **23/10**; #19–#21 là **29/10** theo kế hoạch vẫn *Proposed for team review*. Việc chưa hoàn thành: nhận và xác minh gói DATA-v1, chạy Source/Development thật, replay qua biên block với bằng chứng checkpoint/log và cost đầy đủ, cấu hình được khóa trên Development, đối chiếu độc lập với Quyền và peer review. Không dùng Final để chọn tham số, không coi smoke/fixture là hiệu quả mô hình.

## DATA-v1 UrbanEV đã xác minh — 08:34 ngày 22/10/2026

- Đã tải **gói thật** `inputs-urbanev-SZH-v1.zip` từ link công khai trong `docs/data/DATA_DOWNLOADS.md` vào `.cache/data-downloads/` của worktree, không ghi đè dữ liệu cũ. Kích thước **151254390 byte**, SHA-256 **`2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`** khớp release catalog; `verify-input-zip` đạt kiểm tra CRC. ZIP có 18 artifact, tổng kích thước giải nén 2715188524 byte; đường dẫn đã được kiểm tra không thoát khỏi thư mục đích.
- Đã giải nén vào thư mục mới `.cache/data-v1-20261022/` trong worktree. `_load_run` xác minh manifest `ev-loader-run-v2`, `ev-missing-data-v1` và SHA-256 của **toàn bộ artifact** ở ba run: 7d `fd1b5d1767e94a3e5c6f62447d446e1f13859b823c5fe14c51b5055d8e67169c`, 14d `66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9`, 28d `cdd43152bbda3de9f468938262a8bf00e041a9f264cf29051b71d06e788beadd`. Cả ba báo `technical_success_with_coverage_limits`, **không** có nghĩa đủ coverage hay đã đạt hiệu quả mô hình.
- Các gói ZIP và dữ liệu giải nén nằm trong `.cache` bị Git bỏ qua; `git status` vẫn sạch trước khi sửa báo cáo này. Chưa chạy huấn luyện Source, thích nghi Development hay replay trên dữ liệu thật. Theo #39, những lượt huấn luyện/thực nghiệm này chạy trên Colab; bước kế tiếp là chuyển dữ liệu đã xác minh và code pinned lên Colab, rồi ghi run ID, config, seed, checkpoint, chi phí và log thật. Không dùng Final để chọn tham số.
- Đã chuẩn bị `experiments/hung_sprint2/colab_handoff.ipynb` để gọi CLI ở commit code `e609f0b`, xác minh ZIP trước giải nén, chạy **smoke giới hạn** Source/Development 7 ngày và replay 15 origin qua biên block 14 ngày cho Development ID `1001`, rồi sao chép output/checkpoint sang thư mục Drive mới và so hash từng file. Có ô resume vào output mới tới origin 29. Notebook cũng hướng dẫn lượt riêng cho ID `1025` thuộc `source_checkpoint_only` (0 mẫu thích nghi đầu, 15 origin đầu được tạo) để giữ stratum tách biệt. Các số bước và mức lambda trong notebook chỉ là ví dụ smoke, chưa được chọn/khóa cho nghiên cứu. **Notebook chưa chạy trên Colab**; người chạy phải cung cấp đường dẫn ZIP và Drive output thật.
- Notebook nay chỉ ghi `handoff_complete.json` sau khi so SHA-256 mọi file trong bản sao Drive; ô resume từ chối run thiếu marker hoặc có file bị sửa/thiếu và kiểm tra code SHA. Helper đã qua fixture copy, sửa file và thư mục dở dang trong `.cache/test-temp`. Kiểm tra này xác minh bản sao qua mount tại thời điểm chạy, **chưa** chứng minh đồng bộ byte từ Drive server hoặc khả năng resume trên Colab thật.

## Journal sự kiện replay — chuẩn bị bổ sung ngày 22/10

- `replay-development` nay tạo `events.jsonl` trong output mới trước khi phát origin. Mỗi sự kiện được ghi theo chỉ số của runner, `flush` và `fsync` trước sự kiện kế tiếp; manifest hoàn tất ghi SHA-256 và đoạn chỉ số journal. Lượt resume chỉ ghi các sự kiện mới, gắn SHA của checkpoint trước trong header. Fixture xác nhận thứ tự journal với `runner.events`, resume không lặp, và lỗi giả lập sau forecast giữ journal một phần **không** tạo manifest/checkpoint hoàn tất.
- Journal một phần dùng để chẩn đoán lỗi; nó **không** phải checkpoint có thể resume. Replay chỉ resume từ checkpoint đã hoàn tất ở output trước, tạo output mới. Chưa có lượt replay DATA-v1/Colab, chưa xác nhận độ bền trên Drive server và vẫn thiếu đo bộ nhớ/chi phí toàn trình.
- Trước khi resume, CLI còn đối chiếu SHA-256 và khoảng chỉ số `events.jsonl` của run trước với manifest/checkpoint. Fixture sửa journal cũ xác nhận resume bị từ chối trước khi tạo output mới. Điều này bảo vệ chuỗi bằng chứng của checkpoint đã hoàn tất; chưa kiểm chứng trên Drive thật.

## Giới hạn bộ nhớ cho Source smoke — 22/10/2026

- Input UrbanEV 7d đã xác minh có `training.jsonl` **453615715 byte**, gồm **65888** bản ghi Source theo phép đếm streaming. `source-smoke` nay vẫn đọc hết để kiểm tra role/identity/schema và báo số mẫu sẵn có, nhưng chỉ giữ tối đa `steps × batch_size` mẫu đầu cho lượt smoke. Fixture 5 mẫu Source với giới hạn 2 xác nhận manifest ghi `source_examples_available=5`, `source_examples_used=2` và 1 bước. Đây là giảm lượng bản ghi giữ trong RAM theo cấu trúc code; **chưa đo peak RSS** hay chạy Source DATA-v1 trên Colab.
