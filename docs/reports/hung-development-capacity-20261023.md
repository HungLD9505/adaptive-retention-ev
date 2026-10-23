# Quy mô ma trận và thời gian đo trên Colab — 23/10/2026

**Trạng thái:** bằng chứng lập kế hoạch cho #21/#39. Chưa phải ước lượng năng lực được duyệt cho toàn bộ #22/#23, vì chỉ đo hai entity ở budget 7 ngày trên runner CPU.

## Đầu vào đã đối chiếu

Đếm `entities.jsonl` trong ba input UrbanEV SZH đã được bàn giao; mỗi file và manifest được hash lại tại repo. Entity đủ điều kiện ở đây là Development với `target_initial_adaptation` hoặc `source_checkpoint_only`; chưa loại thêm theo kết quả model hay nhãn Final.

| Budget | Manifest SHA-256 | Target có mẫu ban đầu | Source checkpoint only | Tổng đủ điều kiện |
| --- | --- | ---: | ---: | ---: |
| 7 ngày | `fd1b5d1767e94a3e5c6f62447d446e1f13859b823c5fe14c51b5055d8e67169c` | 281 | 13 | 294 |
| 14 ngày | `66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9` | 282 | 14 | 296 |
| 28 ngày | `cdd43152bbda3de9f468938262a8bf00e041a9f264cf29051b71d06e788beadd` | 283 | 18 | 301 |

Tổng là **891 cặp entity × budget**, tức **2.673 lượt target cho một phương pháp với ba seed** nếu giữ toàn bộ các entity đủ điều kiện. Đây là số ô danh nghĩa để lập kế hoạch, không phải số lượt đã chạy; coverage chấm điểm có thể thấp hơn nhiều. Những target không có nhãn hoàn chỉnh vẫn phải được báo coverage, không được âm thầm bỏ vì MAE `null`.

## Thời gian thực đo

Đọc trực tiếp `development_summary.json` trong [Drive run ba seed](https://drive.google.com/drive/u/0/folders/1cNfTOxWk1SPD77W0P4bszED4cYkDuYW7), RUN_ID `hung-urbanev-7d-dev-multiseed-20261023T161534600069Z`. Marker `handoff_complete.json` ghi SHA-256 của summary là `ee04f744dadc2ca543b01a773c897b8777380668c7521d97c3b2737dd7df8510`. Code `85e45606789eaff7e2e929eb7a7ee353a4ee49f9`, input manifest 7 ngày như trên. Source dùng đủ 65.888 ví dụ/seed; target `1001` có 3 bước, `1871` có 0 bước; mỗi replay yêu cầu 90 origin. Runtime Colab chọn T4 nhưng implementation ghim `torch 2.8.0+cpu`, nên các số sau là thời gian **CPU CLI**, không phải throughput GPU.

| Seed | Source (giây, dùng chung cho hai ID) | Target `1001` | Replay `1001` | Target `1871` | Replay `1871` |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 7 | 69,075 | 13,364 | 19,102 | 13,210 | 17,525 |
| 11 | 63,615 | 13,069 | 19,115 | 13,212 | 17,647 |
| 19 | 63,782 | 13,357 | 18,725 | 13,331 | 17,817 |

Trung bình quan sát: Source **65,491 giây/seed**, target **13,257 giây/entity**, replay **18,322 giây/entity**. Thời gian target + replay trung bình là **31,579 giây/entity** ở đúng hai ID/budget này. Các CLI duration không bao gồm đầy đủ việc khởi động Colab, cài gói, tải input và sao chép Drive. Chúng cũng chưa đo storage tiêu thụ của toàn ma trận.

Nếu *chỉ để hình dung quy mô* nhân 31,579 giây với 2.673 ô của **một** phương pháp, kết quả là khoảng **23,45 giờ CPU CLI chạy tuần tự**. Đây **không phải dự báo thời gian**: hai ID không đại diện cho 891 cặp entity × budget, 14/28 ngày có số mẫu ban đầu khác, các baseline có chi phí khác nhau, và không tính cài đặt/Drive/CI/chạy lỗi. Không nhân tuyến tính số này thành cam kết cho 9 baseline và 5 ablation; các run trùng định nghĩa phải tái sử dụng, còn adaptive và proxy có chi phí nhiều candidate/audit.

## Quyết định năng lực còn thiếu

Trước khi khóa ma trận hoặc lên lịch Final, cần đo một mẫu Development đại diện **theo strata và cả ba budget** cho từng nhóm chi phí (stateless, một GRU, ba candidate/proxy), ghi thời gian end-to-end, peak RSS, kích thước artifact và tỉ lệ lỗi. Sau đó lập danh sách run duy nhất của 9 baseline + 5 ablation, nhân theo entity/budget/seed thật, xét song song khả dụng và dung lượng Drive. #22 hiện chưa có owner/reviewer; lead cần xác nhận nguồn lực và cửa sổ chạy nếu ma trận không khả thi. Không giảm âm thầm cohort, seed, budget hay phương pháp bắt buộc, và không dùng Final để chọn cấu hình.

Lệnh kiểm tra đã dùng: `Get-FileHash` SHA-256 cho manifest/entities của ba budget; nhóm `role, initialization` trên `entities.jsonl`; đọc `development_summary.json` từ Drive run đã hoàn tất. Không có huấn luyện hoặc chấm điểm mới trong bước lập kế hoạch này.
