# Đánh giá Development nhiều seed trên Colab — 23/10/2026

**Trạng thái:** `Run all` hoàn tất trên Colab cho 3 seed × 2 entity của UrbanEV Shenzhen, đầu vào 7 ngày. Đây là đánh giá Development có giới hạn; chưa phải nghiệm thu hiệu quả mô hình trên toàn cohort, so sánh baseline bắt buộc hay đánh giá Final.

## Phạm vi và danh tính lượt chạy

- Notebook: [Colab Development nhiều seed](https://colab.research.google.com/drive/1Dz_YID3BU7t_N1Lq5gNI9BBvScLLbTDa), bản nguồn `experiments/hung_sprint2/colab_development_multiseed_20261023.ipynb`.
- Run ID: `hung-urbanev-7d-dev-multiseed-20261023T161534600069Z`.
- Runtime hiển thị `T4 (Python 3)`; code ghim `torch 2.8.0+cpu` và runner chạy trên CPU. Không có phép đo tốc độ GPU.
- Code commit `85e45606789eaff7e2e929eb7a7ee353a4ee49f9`; bundle SHA-256 `08120b8eb6b63db6eb78518d4f333cacc8f402ff2d9824bee400d60016e4a0b2`; manifest đầu vào `urbanev-SZH-7d` SHA-256 `fd1b5d1767e94a3e5c6f62447d446e1f13859b823c5fe14c51b5055d8e67169c`.
- Seed 7, 11, 19. Mỗi seed huấn luyện Source một lượt: 2.059 bước × batch 32 = 65.888/65.888 ví dụ. Target `1001` có 6 ví dụ thích nghi ban đầu và 3 bước; `1871` không có ví dụ ban đầu nên dùng nguyên checkpoint Source, 0 bước target. Mỗi entity replay 90 origin, block 14 ngày. Các tham số controller trong notebook là cấu hình chẩn đoán, chưa được chọn/khóa bằng so sánh Development.

Mô hình ghim là `ForecastGRU`: GRU hai lớp, 64 hidden units cho 24 giờ lịch sử; MLP ReLU rộng 32 cho lịch 24 giờ tương lai; đầu ra Softplus cho 24 dự báo không âm. Source tối ưu MAE trên dữ liệu đã scale. Target tối ưu MAE cộng loss giữ biểu diễn latent với trọng số retention. Replay duy trì ba mức retention `0`, `0,1`, `0,2` và dùng controller ra quyết định tại ranh giới block.

## Kết quả quan sát được

MAE/RMSE theo kWh gốc, chỉ trên các ngày có 24 nhãn hoàn chỉnh đã đến hạn. Không gộp hai entity vì thuộc hai strata và có độ phủ khác nhau.

| Entity | Seed | Dự báo tạo / 90 | Ngày chấm | Giờ chấm | MAE (kWh) | RMSE (kWh) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `1001`, target có 6 mẫu | 7 | 59 | 52 | 1.248 | 4,3940 | 6,4309 |
| `1001`, target có 6 mẫu | 11 | 59 | 52 | 1.248 | 4,2122 | 6,1889 |
| `1001`, target có 6 mẫu | 19 | 59 | 52 | 1.248 | 4,2446 | 6,3808 |
| `1871`, Source checkpoint only | 7 | 75 | 38 | 912 | 2,6776 | 3,5717 |
| `1871`, Source checkpoint only | 11 | 75 | 38 | 912 | 2,6051 | 3,4819 |
| `1871`, Source checkpoint only | 19 | 75 | 38 | 912 | 2,6635 | 3,5795 |

Trung bình MAE theo **seed trong từng entity**: `1001` = **4,2836 kWh** (độ lệch chuẩn mẫu 0,0970); `1871` = **2,6487 kWh** (độ lệch chuẩn mẫu 0,0384). Đây là ba lần khởi tạo cho mỗi một entity, không phải khoảng tin cậy trên station/cohort. Coverage theo seed giống nhau: `1001` có 31 origin bỏ qua vì toàn bộ lịch sử thiếu và 7 dự báo tạo nhưng chưa chấm; `1871` lần lượt 15 và 37. Vì vậy, MAE không thể đại diện cho toàn bộ 90 origin.

**Đánh giá:** pipeline thực thi được trên dữ liệu thật và cho kết quả ổn định giữa ba seed ở hai entity được kiểm tra. Chưa thể nói model tốt hay xấu theo tiêu chí nghiên cứu: chưa có baseline chính thức trên cùng ngày được chấm, chưa đủ station/budget, chưa có 9 baseline và 5 ablation của #22, chưa có review độc lập và chưa đánh giá Final. Kết quả chẩn đoán local trong `hung-development-diagnostic-20261023.md` có cấu hình/phạm vi khác nên không dùng làm kết luận hơn kém.

## Bàn giao và kiểm tra

Notebook hoàn tất các cell code và in `hoan_tat_development 6 luot`, `so_luot_development 6`. Cell cuối gọi `publish_run` theo kiểu chỉ tạo mới, so SHA-256 mọi file nguồn và bản sao, tạo `handoff_complete.json`, rồi gọi `verify_drive_run` để kiểm tra schema, code SHA, tập file và từng SHA-256 trước khi in thư mục Drive:

`/content/drive/MyDrive/hung-sprint2-runs/hung-urbanev-7d-dev-multiseed-20261023T161534600069Z`

Trong thư mục này có `development_summary.json`, manifest/checkpoint của từng Source/target/replay, nhật ký replay và marker bàn giao. Việc xác minh được thực hiện bởi code cell trong Colab; báo cáo này không sao chép checkpoint vào Git. Môi trường Colab có cảnh báo `pip check` về `jedi` và `torchvision` cài sẵn, nhưng các CLI đã hoàn tất với phiên bản `torch 2.8.0+cpu` được kiểm tra.

## Việc còn mở theo #21, #22, #39

1. Chốt giao diện và thực hiện 9 baseline cùng 5 ablation trên cùng protocol Development, cùng origin hợp lệ và ngân sách được ghi rõ; báo coverage, metric, chi phí theo station rồi tổng hợp cohort. #22 cần owner/reviewer.
2. Đánh giá thêm cohort và budget 14/28 ngày; kiểm tra khả năng chạy ma trận đầy đủ, resume, tính toàn vẹn checkpoint và đối chiếu implementation với lead. Các tham số chọn bằng Development, không dùng Final/test để chọn.
3. Sau peer review và khóa code/cấu hình/dữ liệu, chạy Final một lần theo protocol đã khóa. Không merge draft PR #44 khi các gate của #39 chưa hoàn thành.

Tài liệu này ghi lại kết quả quan sát từ notebook Colab và phép tính tổng hợp MAE theo seed; không tuyên bố hoàn thành #21/#39 hay hiệu quả mô hình trên Final.
