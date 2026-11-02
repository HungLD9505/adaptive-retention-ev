# #39 — Dữ liệu, thực nghiệm và kết quả Development

**Cập nhật:** 26/10/2026 (ICT). **Loại bằng chứng:** lượt representative **local CUDA** trên UrbanEV/SZH Development; Kaggle T4 và Colab là các lượt chẩn đoán riêng. Không dùng Final/test, không tuyên bố ưu thế nghiên cứu. [Báo cáo đánh giá](hung-39-assessment-handoff.md) là điểm đọc đầu tiên cho reviewer; file này giữ bảng số liệu chính, tránh chép lại ở ba báo cáo canonical còn lại.

## Thiết lập và nguồn dữ liệu

Input là DATA-v1-20261019 UrbanEV/SZH, archive 151.254.390 byte, SHA-256 `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`. Ba input manifest 7/14/28 ngày lần lượt có SHA-256 `fd1b5d1767e94a3e5c6f62447d446e1f13859b823c5fe14c51b5055d8e67169c`, `66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9`, `cdd43152bbda3de9f468938262a8bf00e041a9f264cf29051b71d06e788beadd`. [Phase 0](hung-39-phase0-environment-20261025-masterplan.md) ghi lệnh kiểm ZIP và manifest. Dữ liệu Source có 871 station ID đóng góp 65.888 ví dụ cho **mỗi pass**; lặp Source giữa budget không tạo station mới. Mục tiêu kWh/giờ được xử lý theo [input handoff](input-handoff.md), với mask lịch sử, scale theo identity và nhãn đến muộn.

Selection v2 cố định trước kết quả: 6/8/9 entity cho 7/14/28 ngày, ba seed 7/11/19. Mỗi budget-seed có một Source stage; mỗi entity có target stage, replay-42 và replay-90. Tổng `9 Source + 69 target + 138 replay = 216 stages`, ứng với **69 entity-budget-seed cells**. Source một pass, batch 32, learning rate 0,001; Target một pass, batch 2, learning rate 0,001, initial retention 0,1; replay thử λ `{0; 0,1; 0,2}`, block 14 ngày, tối đa 90 origins. Cấu hình là chẩn đoán, chưa qua phê duyệt phương pháp. Ma trận chạy commit `a34a49e5f04920ef30456fe6c0ea56eb2f1d659a` với Python 3.13.7, PyTorch 2.8.0+cu126, CUDA 12.6 trên RTX 3050 Ti Laptop GPU 4 GiB. Các phiên bản Python 3.12 notebook/CI chỉ kiểm tra code **sau** run, không thay đổi output lịch sử.

## Mốc thời gian và output thực tế

| Mốc (ICT) | Thao tác / output | Nguồn kiểm |
| --- | --- | --- |
| **25/10 21:00:54.855** | Tạo `matrix_identity.json`, bắt đầu wall span representative. | [`statistics.wall_start_vietnam`](hung-39-representative-local-20261025-evidence.json) |
| **25/10 22:08:29.106** | Stage cuối hoàn tất: **216/216**; wall span **4.054,25 giây = 67,57 phút**. | [`statistics.last_stage_completed_vietnam`](hung-39-representative-local-20261025-evidence.json) |
| **25/10 23:18:45** | Archive hoàn tất: **249.622.687 byte**, 573 file; SHA-256 và CRC/member SHA PASS. | [`archive.completed_at_utc`](hung-39-representative-local-20261025-evidence.json), đổi UTC→ICT |
| **25/10 23:24:40** | Tạo private Kaggle dataset của archive đã giải nén; đây là lưu trữ, không phải lượt train mới. | [Báo cáo platform](hung-39-platform-readiness-20261025T2325.md) |
| **26/10, saved Version 4 và 5** | Kaggle CPU đọc lại 573 mounted files và raw ZIP; tree/SHA/CRC PASS, mỗi saved run khoảng 9–10 giây. | [Mounted-file](hung-39-cloud-mounted-readback-20261026.md), [raw archive](hung-39-raw-archive-readback-20261026.md) |

Tổng thời gian CLI cộng từng stage là **2.944,40 giây**, khác wall span vì có overhead ngoài stage. Source stages dùng 65.888 mẫu/2.059 bước, dài 31,17–60,42 giây. Peak **PyTorch CUDA allocation** lớn nhất được ghi là 85.135.360 byte (**81,19 MiB**), không gồm mọi cấp phát GPU/process. Output local giữ dưới `runs/hung-39-representative-local-20261025T2103/` (ignored Git): manifests, Source/Target/runner checkpoints, `events.jsonl`, forecasts, audit và archive. [Evidence JSON](hung-39-representative-local-20261025-evidence.json) lưu 69 hàng full precision, per-file SHA, timings, update/cost counters và run identity; không dùng bảng làm tròn dưới đây thay thế artifact.

## Coverage và quyết định controller

`requested` là origin theo schedule; `issued` là origin có input lịch sử khả dụng và forecast được tạo; `scored` là forecast có đủ 24 nhãn hợp lệ đã đến. Theo [`evaluation.py`](../../experiments/hung_sprint2/evaluation.py), một cell với tập ngày được chấm `S` có:

\[
\mathrm{MAE}_{kWh}=\frac{\sum_{t\in S}\sum_{h=1}^{24}|\hat y_{t,h}-y_{t,h}|}{24|S|},\qquad
\mathrm{RMSE}_{kWh}=\sqrt{\frac{\sum_{t\in S}\sum_{h=1}^{24}(\hat y_{t,h}-y_{t,h})^2}{24|S|}}.
\]

Sai số được đưa về kWh bằng scale đã ghi trong manifest trước khi tổng hợp theo **giờ**; không lấy trung bình daily RMSE. Khi `|S|=0`, MAE/RMSE là `null`, không phải 0.

| Budget | Entity × seed | Stages | Requested | Issued | Scored | Cells có metric / tổng | Switch / keep | Stage CLI (giây) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 7 ngày | 6 × 3 | 57/57 | 1.620 | 1.341 | 693 | 9/18 | 12 / 96 | 662,59 |
| 14 ngày | 8 × 3 | 75/75 | 2.160 | 1.293 | 735 | 12/24 | 11 / 133 | 1.145,78 |
| 28 ngày | 9 × 3 | 84/84 | 2.430 | 1.512 | 894 | 15/27 | 9 / 153 | 1.136,03 |
| **Tổng** | **69 cells** | **216/216** | **6.210** | **4.146** | **2.322** | **36/69** | **32 / 382** | **2.944,40** |

Issued/requested = **66,8%**; scored/requested = **37,4%**, scored/issued = **56,0%**. Các tỷ lệ này là coverage của selection đại diện, **không** phải độ chính xác. 33 cells null gồm 27 Source-checkpoint-only với 0 ngày đủ 24 nhãn và sáu cells của entity `1987` ở 14/28 ngày × ba seed. Dữ liệu có label records không đồng nghĩa nhãn hoàn chỉnh/đã đến; [Phase D](hung-39-representative-local-20261025.md) liệt kê missing hours. Mỗi replay-90 đạt cursor 90 và sáu block decisions. Có 32 switch, 382 keep trong 414 decisions; tần suất switch tự nó không chứng minh controller có lợi.

## MAE/RMSE đã đo, không xếp hạng budget

Bảng sau là ví dụ **theo cùng entity và trung bình ba seed**; mẫu số ngày được chấm giống nhau giữa ba seed trong mỗi hàng. Các entity được nêu để truy dấu các lượt verification/handoff, không chọn làm kết luận vì MAE thuận lợi. Full precision và mọi entity nằm ở `rows` của [evidence JSON](hung-39-representative-local-20261025-evidence.json).

| Budget · entity | Scored / 90 mỗi seed | MAE trung bình seed (kWh) | RMSE trung bình seed (kWh) |
| --- | ---: | ---: | ---: |
| 7 ngày · `2264` | 90 | 3,6223 | 5,8709 |
| 7 ngày · `1405` | 89 | 5,9017 | 8,1786 |
| 14 ngày · `1153` | 52 | 6,5932 | 8,8860 |
| 28 ngày · `1165` | 52 | 10,4087 | 13,6103 |

Budget dùng **entity khác nhau** và coverage khác nhau, nên không suy ra 7 ngày tốt hơn 28 ngày. Ba seed của cùng entity là ba lần khởi tạo, không phải ba station độc lập hay khoảng tin cậy cohort. Không có score chung cho 33 cells null. Trong [Phase A](hung-39-phase-a-model-transfer-20261025-masterplan.md), dự báo thực của origin đầu cho 7d/seed-7/entity-1405 có shape `[1,24]`, sáu giá trị đầu **27,691660; 28,050190; 28,012033; 28,163961; 27,565445; 28,056156 kWh** sau inverse scaling; đây là ví dụ output thật, không phải target hay mẫu minh họa.

## Đọc lại kết quả, chi phí và các lượt phụ trợ

Audit đã kiểm **354/354** checkpoint/journal SHA, 138 replay states, **20.394 forecast tensors** và **18.313 events**; tính lại metric của cả 69 cells, giữ 33 null, chênh lớn nhất **3,55×10⁻¹⁵ kWh** so với giá trị lưu. Có checkpoint CUDA thực phục hồi model, Adam, cursor 90, CPU/CUDA RNG. Một ví dụ 7d/seed-7/entity-1405 có 90 inference và 89 update cho **mỗi** λ candidate, thêm 42 inference/update audit cũ; [Phase C](hung-39-phase-c-runner-20261025-masterplan.md) ghi thời gian inference/update riêng. Do đó chi phí phải gồm ba candidate, audit, Source/Target, checkpoint/I/O và xử lý input, không chỉ một forward pass GRU. Ngoại suy 14 phương pháp × 67,57 phút chỉ là phép tính cùng chi phí giả định, **không** là benchmark #22.

- **Kaggle T4 verification, 25/10:** run ID `hung-39-kaggle-verification-20261025-v2`, code commit `f523718`, **63/63 stages**, 99/99 hashes, chỉ 18 entity-budget-seed cells; [quan sát saved Version 1](hung-39-platform-readiness-20261025T2325.md) hiển thị T4 x2, runtime 24m16s và successful log 1.455,9 giây. [`results.zip`](hung-39-kaggle-verification-20261025.md) tải về đạt SHA/CRC, nhưng ZIP không mang metadata chứng minh nó thuộc đúng Version 1. URL notebook không khóa version thì có thể hiện bản mới hơn. Đây là run identity khác đại diện local.
- **Colab Development, 23/10:** 7d × hai entity × ba seed; adaptive MAE trung bình seed `1001 = 4,2836` kWh (52 ngày scored), `1871 = 2,6487` kWh (38 ngày). UI từng hiển thị T4, nhưng code dùng `torch 2.8.0+cpu`, vì vậy đây là **CPU diagnostic**, không là benchmark GPU. Xem [báo cáo Colab](hung-colab-development-multiseed-20261023.md).
- **Seasonal Naive được đề xuất ở [PR #45](https://github.com/HungLD9505/adaptive-retention-ev/pull/45):** báo cáo trên nhánh PR ghi MAE `4,8798`/`4,0443` kWh ghép với hai entity Colab trên; đây có provenance ở [báo cáo so sánh PR #45](https://github.com/HungLD9505/adaptive-retention-ev/blob/feat/22-hung-baselines-stacked/docs/reports/hung-development-seasonal-comparison-20261024.md). Nó **chưa** là baseline protocol được nhóm duyệt, chưa thay thế chín baseline/năm ablation; không dùng hai phần trăm cải thiện làm kết luận về riêng retention/controller.

## Nhận xét khoa học

Các số trên xác minh **code đã chạy** và metric được tái tính đúng trên những origin hợp lệ. Chúng chưa trả lời transfer gain so với target-only, lợi ích retention so với `λ=0`/fixed λ, lợi ích adaptivity so với Online Best-λ/proxy controller, hay bất định theo station. Không dùng test/Final để chọn model hoặc ngưỡng. Source chỉ học một pass nên mức đủ học cần được nhóm phê duyệt bằng bằng chứng Development; không tự tăng epoch trong run đã freeze. Những câu hỏi này thuộc #22/#23 sau review, không làm thay đổi 216 stages đã lưu.
