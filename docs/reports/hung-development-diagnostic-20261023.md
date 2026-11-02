# Chẩn đoán Development Sprint 2 — 23/10/2026

**Trạng thái:** chẩn đoán local trên UrbanEV SZH, ngân sách Source một lượt và
một seed; **ngoài quy trình nghiệm thu #39**, vì #39 yêu cầu huấn luyện và thí
nghiệm dữ liệu thật trên Colab, local chỉ dành cho code và test nhỏ. Các run này
không thay thế bằng chứng Colab, chưa phải đánh giá Final hay kết luận model tốt
trên toàn bộ cohort.
Báo cáo này bổ sung, không thay thế lượt Colab smoke đã ghi trong
`hung-colab-development-smoke-20261023.md`.

## Danh tính và phạm vi

- Input: `urbanev-SZH-7d`, manifest SHA-256
  `fd1b5d1767e94a3e5c6f62447d446e1f13859b823c5fe14c51b5055d8e67169c`.
- Code: commit `f83cdaaa57477fcd3f9319ec75b27dfbf6b20fc7` trên nhánh
  `feat/21-hung-runner`; seed 7, CPU local. Không dùng Final/test để chọn cấu hình.
- Source đại diện: 512 bước, batch 32, dùng 16.384/65.888 ví dụ; checkpoint
  `.cache/source-representative-20261023T113559Z`.
- Source một lượt: 2.059 bước, batch 32, dùng 65.888/65.888 ví dụ trong
  67,264 giây; checkpoint
  `.cache/source-one-pass-20261023T113900Z/source_checkpoint.pt`, SHA-256
  `73b2c4bb78ab1f81f216c344e8637a41ed45d284320fad36b1a96b538aca2540`.
  CLI vẫn gắn scope `bounded_source_smoke`; một lượt không chứng minh Source đã
  hội tụ hoặc được chọn bằng Development.

## Nhóm không có mẫu thích nghi ban đầu

ID `1025`: `target-smoke` ghi `source_checkpoint_only`, 0 mẫu target và 0 bước.
Replay 15 origin tạo 15 dự báo, 0 ngày có nhãn hoàn chỉnh; MAE/RMSE đều `null`.
Không được diễn giải 0 ngày chấm là model dự báo tốt hay xấu.

Trong 13 ID Development 7 ngày thuộc nhóm này, chỉ ID `1871` có nhãn hoàn chỉnh
trong lịch 90 ngày (38 ngày). Đây là lựa chọn để kiểm tra đường chạy có thể chấm
điểm, **không phải** chọn entity theo điểm model. Với cùng checkpoint Source,
`target-smoke` của `1871` ghi 0 mẫu/0 bước và checkpoint SHA-256
`cd18d4aff149c9affc6ec0832c49ef10b8204b7e213cc7b073cc15ea5d45f2e6`.
Replay 90 origin: 75 dự báo được tạo, 15 ngày bỏ qua vì toàn bộ lịch sử thiếu,
38 ngày được chấm (912 giờ), 37 dự báo đã tạo chưa chấm. MAE live =
**2,6175 kWh**, RMSE = **3,5376 kWh**. Hai lần switch ở các block cuối
(`0 → 0,1 → 0,2`), nhưng các block trước thiếu ngày hợp lệ; không coi quyết
định này là lợi ích thống kê đã được xác nhận. Checkpoint runner SHA-256
`718cb478d514eee6c292c6523b66aa2b722bdcfc74f82f8ae8dae613d6762015`;
journal SHA-256
`bf0c571d3940889aaf59b5b729f7f1ce39550e12e985c156498a75f23f303dea`.
Hai hash đã đối chiếu với file hiện có.

## Mốc chẩn đoán cùng ngày được chấm

Quy tắc **tham chiếu tạm thời**, chưa phải Seasonal Naive bắt buộc: lấy giá trị
cùng giờ của 24 giờ lịch sử ngay trước origin nếu mask cho biết đã có; khi giờ
đó thiếu, dùng giá trị có sẵn gần nhất trong 24 giờ lịch sử; nếu cả 24 giờ đều
thiếu, dự báo 0. Chỉ dùng `x_hist` có sẵn tại origin. Quy tắc được ấn định trước
khi tính các số bên dưới; chưa được team duyệt làm fallback chính thức.

| ID / phạm vi | Model MAE | Tham chiếu MAE | Model RMSE | Tham chiếu RMSE | Giờ dùng fallback |
| --- | ---: | ---: | ---: | ---: | ---: |
| `1001`, Colab smoke, 14 ngày/336 giờ | 7,3131 | 6,5104 | 8,6230 | 9,0588 | 0 |
| `1871`, Source một lượt, 38 ngày/912 giờ | 2,6175 | 4,0443 | 3,5376 | 5,2380 | 23 |

ID `1001` dùng Source chỉ 2 bước/4 mẫu ở Colab; ID `1871` dùng Source một
lượt. Hai hàng khác entity, ngân sách và khoảng chấm nên **không so trực tiếp**.
Theo MAE ở ID `1001`, model smoke kém hơn tham chiếu này; ở ID `1871`, model tốt
hơn. Cả hai chỉ là chẩn đoán cục bộ, không đủ kết luận hiệu quả chung hoặc lợi
ích của adaptive retention. Mốc dự báo bằng 0 cũng được kiểm tra nhưng không
dùng làm baseline chính: MAE tương ứng 10,4792 và 4,7617 kWh.

## Bước tiếp theo và giới hạn

1. #22 cần owner, reviewer khác người triển khai, và duyệt giao diện so sánh.
   Hoàn thiện đủ chín baseline, năm ablation theo `docs/SPRINT_PLAN.md` §2;
   quy tắc fallback/proxy và ngân sách tuning phải chốt trên Development.
2. Chạy cùng cohort, origin, ngân sách Source/target và ít nhất ba seed trên
   Development; tổng hợp theo station trước, báo coverage, sai số và chi phí.
   Đo khả năng chạy toàn bộ ma trận, không ngoại suy từ smoke một entity.
3. Khóa cấu hình, code, dữ liệu và luật loại trừ trước khi đánh giá Final. Không
   dùng Final để chọn model, hyperparameter, threshold hoặc calibration.

Không có file code nào được sửa trong lượt này. Các output mới nằm trong
`.cache/entity-1871-one-pass-source-20261023/` và không đưa vào Git. Lệnh đã
chạy: `target-smoke`, `replay-development --max-origins 90` cho ID `1871`, các
script Python chỉ đọc manifest/input để tính mốc chẩn đoán và đối chiếu SHA-256.
Lượt kiểm tra hash đầu tiên lỗi do script kiểm tra dùng nhầm tên khóa/file trong
manifest; đã sửa script kiểm tra và đối chiếu thành công, không sửa artifact.
Source seed 11 local cũng đã kết thúc trong `.cache/source-one-pass-seed11-20261023/`;
seed 19 local bị dừng sau khi đối chiếu #39, không có manifest thành công và
không được tính vào so sánh nhiều seed. Cần chạy lại ma trận phù hợp trên Colab.

Notebook `experiments/hung_sprint2/colab_development_multiseed_20261023.ipynb`
đã chuẩn bị cho ba seed trên Colab (hai strata riêng, 90 origin mỗi target),
nhưng **chưa thực thi**. Cổng phê duyệt trình duyệt từ chối thao tác tải notebook
lên `colab.research.google.com`; không thử phương thức thay thế. Vì chưa có run
Colab nhiều seed, chưa cập nhật PR/GitHub bằng các số chẩn đoán local này.

## Bổ sung sau lượt chẩn đoán

Người dùng đã tải notebook lên Colab theo đường dẫn mới; `Run all` sau đó hoàn tất
6 lượt Development trên ba seed. Kết quả và giới hạn được ghi riêng trong
`hung-colab-development-multiseed-20261023.md`. Các câu ở đoạn trên phản ánh
trạng thái **tại thời điểm chẩn đoán**, không còn là trạng thái hiện tại.
