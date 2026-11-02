# Hồ sơ bằng chứng để viết báo cáo cuối — task #39

Ngày tổng hợp: 25/10/2026. Trạng thái: **chưa nghiệm thu #39**. Tài liệu này là chỉ mục bằng chứng và nhật ký phương pháp, không thay thế manifest, checkpoint, event journal hoặc báo cáo gốc. Các số bên dưới chỉ phản ánh lượt đã chạy; cấu hình vẫn là đề xuất chẩn đoán trên Development. Không dùng Final/test để chọn tham số.

## 1. Phạm vi và nguồn chuẩn

- Task cá nhân #39: model, retention, controller, runner, bằng chứng Development và đối chiếu độc lập. #22 (9 baseline, 5 ablation) là phạm vi khác; PR #45 không phải điều kiện để tuyên bố đã hoàn tất chúng.
- Đọc Report 1, `docs/FOUNDATION_REPORT.md`, `docs/data/INPUT_CONTRACT.md`, `docs/data/INPUT_ACCEPTANCE.md`, `docs/data/DATA_DOWNLOADS.md`, `docs/WORKFLOW.md`, `docs/SPRINT_PLAN.md` và báo cáo #39 trước khi sửa code. Hợp đồng input dùng `X_hist[B,24,7]`, `C_future[B,24,5]`, mask/nhãn đến riêng, schema `ev-input-v1`, `ev-loader-run-v2`, `ev-missing-data-v1`.
- Code theo lớp: `model.py` (GRU/forecast), `retention.py` (loss), `training.py` (Source/target), `controller.py` (quyết định), `runner.py` (event order/candidate), `checkpoint.py` (state/RNG), `replay_inputs.py` (input), `evaluation.py` (metric), `cli.py` (stage), `run_development.py` (ma trận), `_create_only.py` (ghi artifact không ghi đè). Config chính: `experiments/hung_sprint2/development_config_v1.json`.
- Nhánh bàn giao `codex/39-completion`, draft PR [#46](https://github.com/HungLD9505/adaptive-retention-ev/pull/46). Các dependency draft là [#42](https://github.com/HungLD9505/adaptive-retention-ev/pull/42) → [#43](https://github.com/HungLD9505/adaptive-retention-ev/pull/43) → [#44](https://github.com/HungLD9505/adaptive-retention-ev/pull/44). Chưa coi CI xanh là review/merge/nghiệm thu.

## 2. Phase đầu vào DATA-v1

- ZIP UrbanEV SZH `inputs-urbanev-SZH-v1.zip`, release `DATA-v1-20261019`: **151,254,390 byte**, SHA-256 `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`; kiểm tra ZIP CRC đạt. Bản tải và giải nén local ở thư mục ignored trong repository; không ghi đè bản cũ.
- Manifest SHA-256: 7d `fd1b5d1767e94a3e5c6f62447d446e1f13859b823c5fe14c51b5055d8e67169c`; 14d `66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9`; 28d `cdd43152bbda3de9f468938262a8bf00e041a9f264cf29051b71d06e788beadd`. Manifest, năm artifact mỗi budget, identity và SHA đều đạt. Kết quả `technical_success_with_coverage_limits` không chứng minh cohort đủ coverage.
- Source có **65,888** bản ghi. Development chỉ dùng metadata để lập danh sách entity trước khi xem metric. Danh sách cuối: `docs/reports/hung-development-selection-20261025-v2.json`; bản không có `-v2` là bản nháp giữ lại, không dùng. Theo budget 7/14/28, số entity adaptation/source-only là **281/13**, **282/14**, **283/18**. Quy tắc thứ tự SHA-256 cố định, stratum theo số mẫu ban đầu; nhóm rỗng giữ rỗng. Ma trận local verification chọn adaptation/source-only lần lượt `2264/1050`, `1153/2644`, `1165/1188`. Representative list đã công bố trong JSON nhưng **chưa chạy mở rộng**.

## 3. Phase triển khai và phương pháp

- Model `ForecastGRU`: GRU 2 lớp, hidden 64 trên 24 giờ lịch sử; MLP ReLU hidden 32 trên lịch tương lai; Softplus cho 24 dự báo không âm. Source tối ưu MAE trên nhãn đã scale. Latent scale là độ lệch chuẩn population trên Source training hợp lệ. Target khởi tạo từ Source, tối ưu MAE + `0.1 ×` retention loss chuẩn hóa latent; source reference đóng băng. `source_checkpoint_only` có 0 bước thích nghi ban đầu.
- Config v1, **diagnostic, chưa được nhóm chấp nhận**: seed 7/11/19; Source 1 pass, batch 32, LR 0.001, calendar hidden 8; target 1 pass, batch 2, LR 0.001, epsilon `1e-6`; replay tối đa 90 origin, block 14 ngày, lambda `0/0.1/0.2`, mức đầu 0, ít nhất 5 ngày đủ nhãn, delta 0, alpha 0.05, bootstrap segment 2 ngày/100 resample, Bonferroni cho hai challenger. Các quan sát hợp lệ liên tiếp được coi là liền kề dù có khoảng ngày thiếu; cần team duyệt.
- Runner phát forecast **trước** khi đọc nhãn; chỉ score/update khi 24 nhãn hợp lệ đã đến. Ba candidate tách model/optimizer từ đầu block; quyết định giữ/chuyển chỉ áp dụng block sau. Replay lưu `events.jsonl` theo thứ tự, flush/fsync, checkpoint cursor, trạng thái model/optimizer và RNG CPU/CUDA. Resume từ checkpoint hoàn tất sang stage/thư mục mới, kiểm tra hash journal/checkpoint và không lặp update. Metric MAE/RMSE ở kWh gốc; ngày không có nhãn đủ điều kiện để metric null.
- Driver `python -m experiments.hung_sprint2.run_development` kiểm tra ZIP/input, code/config/selection SHA, identity, tạo output mới theo phase/budget/seed/entity, tái sử dụng stage hoàn tất cùng identity, replay 42 rồi 90 origin. Có `--device cpu|cuda`; ghi device thực, thời gian, process peak RSS hoặc CUDA allocation, kích thước tensor trạng thái theo nhánh. Float32 và batch đã ghim; thiếu VRAM phải dừng/log và tạo run mới, không đổi batch giữa run.
- Lỗi resume CUDA ban đầu: stage dừng đúng biên block đã quyết định trước khi nhãn trễ tới. Artifact lỗi ở `runs/hung-39-cuda-resume-20261025/` được giữ lại. Sau sửa, `runs/hung-39-cuda-resume-fixed-20261025/` cho replay 42→90 khớp run liên tục: **307 event, 59 forecast, 6 quyết định, mọi forecast tensor và candidate weights**. Checkpoint 42 có 2 quyết định; quyết định kế tiếp đợi nhãn đủ điều kiện.
- Lỗi checkpoint trên Drive FUSE: `os.link` bị từ chối. `_create_only.py` dùng fallback tạo file độc quyền, bảo toàn create-only; không ghi đè checkpoint cũ. Fix ở commit `f52371823c1ddbf765eacfe2b89f7bcc0baf4869`; unit fixture POSIX đạt, **chưa xác nhận save checkpoint thật trên Drive bằng lượt matrix mới**.

## 4. Phase thực nghiệm đã chạy

### 4.1 Chẩn đoán 23/10 (không cộng vào ma trận nghiệm thu)

- CPU local seed 7, 7d: Source 512 bước/16,384 mẫu và một lượt 2,059 bước/65,888 mẫu; lượt một pass mất **67.264 s**. Entity source-only `1871` replay 90 origin: 75 forecast, 38 ngày chấm, MAE **2.6175**, RMSE **3.5376 kWh**; 15 origin thiếu lịch sử. Báo cáo chi tiết `docs/reports/hung-development-diagnostic-20261023.md`. Seed 11 Source local hoàn tất, seed 19 bị dừng; không suy ra kết quả đa seed từ đây.
- Colab 7d Development, run `hung-urbanev-7d-dev-multiseed-20261023T161534600069Z`: 3 seed × 2 entity, Source 1 pass mỗi seed. Runtime hiển thị T4 nhưng code ghim `torch 2.8.0+cpu`, **tính toán bằng CPU**. Adaptation `1001`: 59 forecast, 52 ngày chấm, MAE 4.3940/4.2122/4.2446 kWh theo seed 7/11/19. Source-only `1871`: 75 forecast, 38 ngày chấm, MAE 2.6776/2.6051/2.6635. Checkpoint, journal, manifest và `handoff_complete.json` được cell notebook so hash với Drive. Chi tiết và RMSE ở `docs/reports/hung-colab-development-multiseed-20261023.md`. Đây là Development giới hạn, chưa phải GPU benchmark hay cohort estimate.

### 4.2 Local GPU 25/10, matrix verification đầy đủ

- Thiết bị **NVIDIA GeForce RTX 3050 Ti Laptop GPU**, PyTorch `2.8.0+cu126`; run `runs/hung-39-local-multibudget-20261025/`, code commit `edef07db5d46e3b2797bc7c760786fd34202fb27`. `matrix_identity.json` ghim config SHA `20cb0f0962af6e3f3781ef9bebdf03c162548e06894ae4b59ddc1d58be277ba0`, selection SHA `840ea1984592d920b513cbf5c7a67eb370227111b3f609040d12a2f720b12b56` và source file SHA. Dùng 7/14/28d × 7/11/19 × 1 adaptation + 1 source-only.
- **63/63 stage completed**: 9 Source, 18 target, 36 replay (42 và 90). **99/99** checkpoint/journal SHA khớp phép tính lại. Mỗi replay-90 có cursor 90, resume từ replay-42 và 6 quyết định block. 163 file, **73,069,805 byte**. Wall time từ 03:08:36 tới 03:28:27 giờ Việt Nam = **19 phút 51 giây**; tổng stage CLI 901.47 s (không tính khoảng chờ/process startup). Source mỗi seed/budget dùng đủ 65,888 mẫu, 2,059 bước; 31.67–40.82 s, peak CUDA allocation 81.2 MiB. Đây là số đo local, không ngoại suy thành thời gian Colab/toàn cohort.

| Budget | Seed | Adaptation: forecast tạo/chấm; MAE/RMSE kWh | Source-only: forecast tạo/chấm; MAE/RMSE |
| --- | ---: | --- | --- |
| 7d | 7 | `2264`: 90/90; 3.661/5.912 | `1050`: 90/0; undefined |
| 7d | 11 | `2264`: 90/90; 3.573/5.846 | `1050`: 90/0; undefined |
| 7d | 19 | `2264`: 90/90; 3.633/5.855 | `1050`: 90/0; undefined |
| 14d | 7 | `1153`: 59/52; 6.691/8.967 | `2644`: 59/0; undefined |
| 14d | 11 | `1153`: 59/52; 6.598/8.891 | `2644`: 59/0; undefined |
| 14d | 19 | `1153`: 59/52; 6.491/8.800 | `2644`: 59/0; undefined |
| 28d | 7 | `1165`: 59/52; 10.382/13.574 | `1188`: 59/0; undefined |
| 28d | 11 | `1165`: 59/52; 10.524/13.730 | `1188`: 59/0; undefined |
| 28d | 19 | `1165`: 59/52; 10.320/13.527 | `1188`: 59/0; undefined |

Source-only không có ngày nhãn hoàn chỉnh đã đến trong slice này, nên không tính MAE/RMSE. Coverage khác nhau theo budget/entity; không xếp hạng budget từ bảng. Số đầy đủ và switches trong `docs/reports/hung-39-local-verification-20261025.md` cùng từng `run_manifest.json`.
- Benchmark bước update trên một input Development thật, model/reference/scale khởi tạo tổng hợp, 3 warm-up + 10 phép đo: median CPU **11.25075 ms**, CUDA **7.6183 ms**; peak CUDA 18,856,448 byte. File `docs/reports/hung-device-benchmark-20261025.json`. Chỉ là timing bước, không đo throughput ma trận.

## 5. Phase Colab mới và lỗi đã xử lý

- Bundle pinned `handoff/hung-39-f523718.bundle`, SHA-256 `e29f1526ae1e01dacaebe46dd947c6a1d2583749300f0894b2e204c7b5f8002b`; notebook `handoff/hung-39-colab-configured-f523718-20261025.ipynb`, cũng đã tải lên Drive. Notebook ghim commit `f52371823c1ddbf765eacfe2b89f7bcc0baf4869`, run mới `hung-39-verification-20261025T024400Z`, CUDA, verification, ba budget/seed. Notebook chỉ gọi code đã ghim, kiểm tra bundle/input SHA, rồi chạy driver; không sửa kết quả cũ.
- Lượt Colab mới đã mount Drive nhưng dừng **trước training** ở probe: `torch 2.8.0+cu126`, `torch.cuda.is_available() == False`. UI hiển thị backend CPU dù runtime type đặt T4. Sau khi ngắt runtime CPU và kết nối lại T4, Colab hiện thông báo **“Cannot connect to GPU backend — You cannot currently connect to a GPU due to usage limits in Colab.”** Vì vậy không đổi `DEVICE` âm thầm sang CPU, không có manifest matrix Colab mới, không có checkpoint Source mới được xác nhận trên Drive.
- Lỗi iframe “Could not load the JavaScript files needed to display output” là lỗi hiển thị Colab từng gặp; traceback Python sau đó đọc được. Lỗi `CalledProcessError` ở notebook trước là wrapper; nguyên nhân riêng đã tìm thấy ở hardlink Drive FUSE và được sửa trong code. Không gộp hai lỗi này với giới hạn cấp GPU hiện tại.

## 6. Kiểm thử, tính toàn vẹn và trạng thái review

- Sau fix `f523718`, Windows local: `python -m unittest discover -s tests -q` **174 test pass**, 1 test POSIX-only skipped; `ruff check --no-cache .`, `ruff format --check .`, `git diff --check` đạt. Foundation CI Windows/Ubuntu của PR #46 đã đạt tại `f523718`; tài liệu mới sau đó ở `f1393f1`. Cần đối chiếu lại CI tại head cuối trước review/merge. Không có test nào thay thế lượt training Colab thật.
- Các folder run ignored, bundle và notebook ở `handoff/` được giữ lại; không xóa/ghi đè artifact cũ. Bản selection không `-v2` là untracked historical draft. Không tự merge PR, không đóng #39.
- Gate còn mở: Colab GPU được cấp và matrix verification hoàn tất với hash Drive; representative set sau khi team xác nhận phạm vi; so sánh prediction/latent/loss/gradient, controller, block/resume với Quyền trên cùng fixture và dung sai cố định; peer review #42→#43→#44/#46, tích hợp theo quy trình nhóm. Cần xác nhận Source một pass và config Development. Chỉ đóng #39 khi Quyền chấp nhận bàn giao và thay đổi cần thiết đã tích hợp.

## 7. Lệnh tái lập/đối chiếu quan trọng

Từ root repository, dùng Python và dependencies đã ghim. **Không** dùng lại cùng output root khi thay đổi config hoặc phase.

```text
python -m experiments.hung_sprint2.cli verify-input-zip --archive <archive-in-repo> --package inputs-urbanev-SZH-v1.zip
python -m experiments.hung_sprint2.run_development --input-base <DATA-v1-input-base> --selection docs/reports/hung-development-selection-20261025-v2.json --config experiments/hung_sprint2/development_config_v1.json --output-root <new-run-root-in-repo-or-Drive> --phase verification --device cuda --budgets 7 14 28 --seeds 7 11 19 --execute
python -m unittest discover -s tests -q
ruff check --no-cache .
ruff format --check .
git diff --check
```

Đường dẫn `<...>` là placeholder, không phải lệnh đã chạy nguyên văn. Lệnh thực tế Colab dùng input `/content/hung-39-input/data/inputs/issue18-input-handoff-v1-20261019`, selection/config dưới `/content/hung-sprint2-code`, output Drive `/content/drive/MyDrive/hung-sprint2-runs/<new-run-id>`. Trước khi dùng số trong báo cáo cuối, đọc manifest stage và kiểm tra lại SHA theo `matrix_identity.json`; không lấy một bảng làm nguồn duy nhất.
