# #39 — Tái lập, kiểm chứng artifact và bàn giao

**Cập nhật:** 26/10/2026 (ICT). Báo cáo này tổng hợp identity, môi trường, lệnh, mốc thời gian, output và mức kiểm chứng cho người tiếp nhận. Đọc [đánh giá nghiệm thu](hung-39-assessment-handoff.md) để biết phần đã hoàn thành và gate còn mở; đọc [thực nghiệm](hung-39-experiments-results.md) cho bảng kết quả. Các báo cáo gốc không bị sửa hoặc xóa.

## Danh tính các lượt chạy — không trộn số liệu

| Lượt | Nguồn mã / môi trường | Kết quả và ý nghĩa |
| --- | --- | --- |
| Representative local | Commit **`a34a49e5f04920ef30456fe6c0ea56eb2f1d659a`**, Python 3.13.7, PyTorch 2.8.0+cu126, CUDA 12.6, RTX 3050 Ti; run ID `hung-39-representative-local-20261025T2103`. | **216/216 stages**, 69 cells, real CUDA tensor/model; đây là kết quả Development chính. |
| Kaggle T4 verification | Commit `f52371823c1ddbf765eacfe2b89f7bcc0baf4869`, run ID `hung-39-kaggle-verification-20261025-v2`, config/selection identity riêng. | **63/63 stages**, 99 hashes; saved Version 1 UI hiển thị T4 x2/24m16s, không đồng nhất với run local. |
| Colab Development 23/10 | Commit `85e45606789eaff7e2e929eb7a7ee353a4ee49f9`, run ID `hung-urbanev-7d-dev-multiseed-20261023T161534600069Z`, PyTorch **CPU** dù UI hiển thị T4. | Hai entity 7d × ba seed; không phải GPU benchmark hoặc full representative. |
| Handoff code sau run | [PR #46](https://github.com/HungLD9505/adaptive-retention-ev/pull/46) tại head `e85a53cd02deaa3a3440df8c6922eb679773801b` trước nhánh gộp báo cáo này. | Thêm model checkpoint RNG opt-in và notebook; các thay đổi **không** tạo ra forecast lịch sử. |

Identity chính của local representative nằm trong `runs/hung-39-representative-local-20261025T2103/matrix_identity.json` và [evidence JSON](hung-39-representative-local-20261025-evidence.json). Config v1 SHA-256 `20cb0f0962af6e3f3781ef9bebdf03c162548e06894ae4b59ddc1d58be277ba0`; selection v2 **bytes CRLF đã chạy** SHA-256 `840ea1984592d920b513cbf5c7a67eb370227111b3f609040d12a2f720b12b56`. Git blob của cùng nội dung LF có SHA-256 `273858dfb2bf949c297ecd209a5127a22966cb31703f7b2deefcf17323e13c91`. Phải tái tạo đúng CRLF rồi so hash trước khi **resume lịch sử**; lấy file LF ở clean checkout trực tiếp sẽ đổi identity. [Freeze manifest](hung-39-freeze-20261025.json) ghi cả hai dạng. Code handoff mới có source hashes khác, nên một execution mới phải dùng output root/run identity mới.

## Input, output và nơi truy xuất

| Thành phần | Identity / nơi giữ | Kiểm chứng |
| --- | --- | --- |
| DATA-v1 UrbanEV/SZH input ZIP | `data/inputs/downloads/inputs-urbanev-SZH-v1.zip`, **151.254.390 byte**, SHA-256 `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`; ba input manifest SHA nằm trong [Phase 0](hung-39-phase0-environment-20261025-masterplan.md). | ZIP và từng manifest/artifact input được kiểm trước GPU run; Source/Development tách vai trò. |
| Representative run | `runs/hung-39-representative-local-20261025T2103/` (ignored Git), manifests/checkpoints/journals, forecasts, `audit_summary.json`. | [Evidence JSON](hung-39-representative-local-20261025-evidence.json): **216/216 stages**, **354/354 hashes**, 138 replay states, 20.394 forecast tensors, 18.313 events. |
| Archive local | `runs/hung-39-representative-local-20261025T2103.zip`: **249.622.687 byte**, 573 files, 287.115.600 byte chưa nén; SHA-256 `7d74ec06f9102d1a7357da380bc252570cab2a817a9fcce48030f89c3311f2fa`. | CRC PASS, member SHA PASS; archive hoàn tất **25/10 23:18:45 ICT**. |
| Lưu trữ cloud | [Private dataset đã giải nén](https://www.kaggle.com/datasets/hungluongduc/hung-39-representative-local-20261025t2103) và [private dataset raw archive bytes](https://www.kaggle.com/datasets/hungluongduc/hung-39-representative-archive-bytes-20261026). | Saved [Version 4](https://www.kaggle.com/code/hungluongduc/hung-39-development-verification-t4?scriptVersionId=362216281) so 573 mounted files/tree SHA; saved [Version 5](https://www.kaggle.com/code/hungluongduc/hung-39-development-verification-t4?scriptVersionId=362225233) đọc raw 249.622.687 byte, cùng SHA và CRC 573 members PASS. Dataset private: reviewer cần được cấp quyền truy cập. |
| Code/config/notebook | [`development_config_v1.json`](../../experiments/hung_sprint2/development_config_v1.json), [selection v2](hung-development-selection-20261025-v2.json), bốn notebook trong [`notebooks/`](../../experiments/hung_sprint2/notebooks/), [PR #46](https://github.com/HungLD9505/adaptive-retention-ev/pull/46). | Freeze report và Python 3.12 validation ghi hash source/notebook; notebook import core Python, không là implementation độc lập. |

Giới hạn: Kaggle dataset-level download từng báo `awaiting compression`. Bản cloud đã được đọc lại bằng notebook và đối chiếu SHA/CRC, nhưng **không có lượt tải dataset ZIP về local** để kiểm roundtrip độc lập. Ngày 26/10/2026, Hùng nói **không cần kiểm tải ngược**; đây là bỏ yêu cầu kiểm thêm, không được diễn giải thành phép kiểm đã chạy. Dữ liệu và artifact lớn không đưa vào Git; file private phải có quyền truy cập khi reviewer tái lập.

## Nhật ký mốc chạy và kiểm chứng

| Thời điểm ICT | Hành động / quan sát | Trạng thái |
| --- | --- | --- |
| **23/10** | Colab Run all hoàn tất 7d × 2 entity × 3 seed; Drive handoff có `handoff_complete.json` được cell so hash. PyTorch dùng CPU. | PASS trong phạm vi Colab CPU diagnostic; không chứng minh T4 tensor. |
| **25/10 21:00:54–22:08:29** | Local representative tạo identity, chạy 9 Source + 69 target + 138 replay; stage CLI cộng 2.944,40 giây, wall 4.054,25 giây. | PASS 216/216; [Phase D](hung-39-representative-local-20261025.md). |
| **25/10 23:18:45** | Archive local hoàn tất, kiểm SHA/CRC/member hashes. | PASS; [evidence JSON](hung-39-representative-local-20261025-evidence.json). |
| **25/10 23:24:40** | Tạo private Kaggle dataset đầu tiên với archive/sidecar; Kaggle giải nén thành 573 members + sidecar. | PASS upload UI; chưa là download. |
| **26/10 00:51:04** | [Validation artifact Python 3.12](hung-39-python312-notebook-readback-20261026.md) hoàn tất: bốn notebook chạy riêng từ kernel sạch. | PASS 4/4 notebook; 177 tests, hai skip. |
| **26/10, giờ chạy cụ thể không ghi trong báo cáo** | CPU Kaggle saved Version 4 và 5 đọc lại mounted files/raw archive; code train của Version 1 không chạy lại ở các version CPU. | PASS path/size/hash/CRC theo [mounted-file report](hung-39-cloud-mounted-readback-20261026.md) và [raw archive report](hung-39-raw-archive-readback-20261026.md). |

Mốc saved Version 4/5 được dẫn bằng version ID và output đã lưu, không gán giờ bắt đầu cụ thể khi evidence không ghi. Kaggle T4 saved Version 1 cho biết runtime 24m16s/log 1.455,9 giây, nhưng ZIP `results.zip` tải trước đó không mang metadata để ràng buộc độc lập với Version 1. Trạng thái URL/version đã được UI đọc lại sau báo cáo Kaggle sớm; [báo cáo platform](hung-39-platform-readiness-20261025T2325.md) giải thích phạm vi.

## Hướng dẫn đọc lại hoặc tái lập có kiểm soát

1. Lấy code đúng commit `a34a49e` để **đọc hoặc tái lập lượt lịch sử**, DATA-v1, ba input manifests và các artifacts tương ứng. Kiểm byte size/SHA trước khi dùng, đặc biệt selection v2 CRLF. Không dùng code handoff mới thay cho commit trong `matrix_identity.json`.
2. Đọc [69 hàng evidence JSON](hung-39-representative-local-20261025-evidence.json), `audit_summary.json`, manifests và hashes; đối chiếu mỗi stage với artifact. Không chạy lại script tạo `audit_summary.json` vào file đã tồn tại: script đó theo chính sách create-only. Nếu cần kiểm lại, dùng output mới và giữ nguyên bản gốc.
3. Muốn **tái chạy** ma trận, dùng `PYTHONUTF8=1`, repo-local `TEMP`/`TMP`, cùng input/config/selection/device/phụ thuộc và **output root mới**. Lệnh lịch sử (chỉ ghi để tái lập, **không được chạy lại cho việc dọn báo cáo**):

```powershell
python -m experiments.hung_sprint2.run_development --input-base data/inputs/issue18-input-handoff-v1-20261019 --selection docs/reports/hung-development-selection-20261025-v2.json --config experiments/hung_sprint2/development_config_v1.json --output-root runs/hung-39-representative-NEW-RUN --phase representative --device cuda --budgets 7 14 28 --seeds 7 11 19 --execute
```

4. Chỉ reuse stage hoàn tất nếu `matrix_identity`, input binding và checkpoint hash khớp; preserve stage dở để điều tra. Replay-90 phải trỏ đúng replay-42 checkpoint, cursor và event-journal range. Model Source/Target checkpoint cũ **không** có RNG snapshot nên không hứa hẹn interrupted-stage exact resume; runner checkpoints có CPU/CUDA RNG và bounded CUDA recovery đã kiểm. Code mới hỗ trợ explicit model `restore_rng=True` cho checkpoint mới, không tự động biến checkpoint cũ thành resumable.
5. Notebook mặc định chỉ đọc artifact; `HUNG_EXECUTE_NEW_RUN=NO`. Khi cấp dataset Kaggle private cho reviewer, kiểm quyền và hash tương ứng, rồi để reviewer chạy/đọc độc lập. Không dùng Final/test để điều chỉnh cấu hình.

## Bảng xác minh và lỗi lịch sử

| Kiểm tra / môi trường | Kết quả đã chạy | Giới hạn cần nhớ |
| --- | --- | --- |
| Local representative stage/hash/metric/state | **PASS** 216/216, 354/354, 69 metric rows được tính lại; 33 null giữ null, sai khác lớn nhất 3,55×10⁻¹⁵ kWh. | Không đánh giá hiệu quả so baseline. |
| Local archive SHA/CRC/member readback | **PASS** 573 members. | Không phải cloud download. |
| Kaggle T4 verification | **PASS** 63/63, 99/99 hashes; downloaded `results.zip` SHA/CRC PASS. | Run 63 stage riêng; ZIP chưa được ràng buộc độc lập với saved V1. |
| Kaggle cloud raw/mounted readback | **PASS** Version 4/5 tree/raw SHA và CRC. | Chỉ CPU integrity; dataset private, local re-download được user miễn. |
| Python 3.12.10 CPU clean environment | **PASS** `pip check`, 177 tests, hai **SKIP** trên Windows, Ruff tracked files, 4 notebook × 4 code cells, 0 error. | Notebook đọc artifact, không train lại; [log](hung-39-python312-notebook-readback-20261026.md). |
| Global Python 3.13 preflight lúc train | **FAIL** `pip check` vì xung đột ultralytics/NumPy không liên quan; Ruff fail do import/format ở Kaggle notebook chưa chạy. | Lỗi môi trường/toàn cục và format đã được xử lý bằng môi trường sạch và sửa notebook **sau** run; không viết lại snapshot preflight. |
| Colab GPU tensor + Drive handoff mới | **OPEN**: T4 UI từng kết nối, probe bị lỗi session/reCAPTCHA và không thực thi. | Colab CPU 23/10 đã có Drive hash handoff nhưng không chứng minh GPU hiện tại. |
| So sánh độc lập, Source/config approval, #39 acceptance | **OPEN**. | Quyền/team review; không tự merge/đóng Issue. |

Nguồn bổ sung: [Phase E lịch sử](hung-39-phase-e-handoff-20261025-masterplan.md), [post-freeze CI](hung-39-postfreeze-validation-20261026.md), [notebook validation](hung-39-notebook-validation-20261025-masterplan.md), [platform readiness](hung-39-platform-readiness-20261025T2325.md) và [freeze JSON](hung-39-freeze-20261025.json). Báo cáo Phase E ngày 25/10 từng nói Python 3.12 còn thiếu; kiểm tra ngày 26/10 đã đóng **riêng** khoảng trống đó, không sửa kết quả training.

## Kiểm tra nhánh tổng hợp tài liệu ngày 26/10

Trong worktree mới từ head `e85a53c` của #46, `python -m tools.sources list` PASS; `python -m unittest discover -s tests -q` bằng Python 3.12.10 chạy **177 tests, hai skip**, còn lại đạt. `python -m ruff check .`, `python -m ruff format --check .` (tắt cache để tránh cảnh báo quyền ghi cache) và `git diff --check` PASS. Kiểm tra liên kết tương đối của README và bốn báo cáo chuẩn: **0 đường dẫn hỏng**. Đọc lại evidence JSON cho 216 stages, 69 rows, 354 hashes, 4.146 forecasts, 2.322 ngày scored và 33 rows null; không chạy lại training hoặc notebook.

Hash byte của bốn notebook ở clean worktree **khác** hash trong `runs/hung-39-notebook-clean-py312-20261026/validation.json` vì lần kiểm Python 3.12 trước đọc file CRLF, còn Git checkout mới giữ LF. Cả bốn JSON notebook có nội dung giống bản cũ; đổi mỗi LF thành CRLF tái tạo **đúng cả bốn SHA-256 đã ghi**. Đây là khác biệt xuống dòng của file nguồn, không phải bằng chứng một lượt notebook mới đã chạy. Không sửa notebook hoặc artifact validation để ép hash khớp.
