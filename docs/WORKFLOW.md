# Cách nhóm phát triển qua dev

- `main`: phiên bản nhóm đã chốt. Không push/merge vào đây nếu chưa có chỉ đạo riêng cho lần cập nhật đó.
- `dev`: tích hợp công việc hằng ngày qua PR, CI và peer review.
- `master`: backup codebase trước reset, giữ nguyên.
- `feat/*`, `fix/*`, `docs/*`, `chore/*`: nhánh cho từng issue, tạo từ `dev`; xóa sau merge.

## Một vòng làm việc

```mermaid
flowchart TB
    A["Issue: owner, phạm vi, acceptance criteria"] --> B["Tạo nhánh từ dev"]
    B --> C["Implement và tạo tests"]
    C --> D["Chạy checks và ghi report"]
    D --> E["PR vào dev, CI và peer review"]
    E -- "Cần sửa" --> C
    E -- "Đủ evidence và được duyệt" --> F["Merge dev"]
    F --> G["Cập nhật issue và xóa nhánh đã merge"]
```

1. Mỗi task có một GitHub Issue với owner, mục tiêu, phạm vi, acceptance criteria và dependencies; PR liên kết issue. Nếu đụng protocol/method, chỉ rõ trước khi code.
2. Mỗi developer dùng nhánh riêng. Dùng `feat/<topic>`, `fix/<topic>`, `docs/<topic>` hoặc `chore/<topic>` theo nội dung thay đổi, áp dụng cho cả thành viên và coding agent. Nhánh lưu lịch sử dùng `archive/<topic>`. Không dùng chung một nhánh để sửa đồng thời.
3. Tests phù hợp, lint, format và diff checks phải pass. Đừng chỉ kiểm tra happy path: failure phải trả failure thật. CI thông thường không cần raw, mạng tải dữ liệu hoặc GPU.
4. Ghi vấn đề, thay đổi, commands/kết quả và giới hạn trong PR. Pipeline/experiment có bàn giao thực tế thì thêm report trong `docs/reports/`; không tạo report riêng cho thay đổi nhỏ.
5. Ít nhất một peer khác tác giả duyệt commit mới nhất, ưu tiên GitHub **Approve review**. Khi review thủ công, chấp nhận comment rõ `approved merge` kèm commit SHA từ peer đã đọc thay đổi; comment này không phải approval kỹ thuật của branch protection. Có commit mới thì cần peer xác nhận lại.
6. Thành viên merge vào `dev` khi checks pass, evidence khớp và peer đã duyệt. Agent không tự merge. Cập nhật/đóng issue sau khi acceptance criteria đạt; PR vào `dev` có thể không tự đóng issue. Không tự động đưa `dev` lên `main`.

## Trạng thái GitHub enforcement

Tại thời điểm dựng foundation, GitHub API báo `main.protected=false`; tài khoản làm task có push nhưng không có admin. Rulesets API trả 403 với thông báo giới hạn tính năng trên private repository. Actions-permissions API trả 404, vì vậy không xác nhận được settings qua endpoint đó.

Repo có workflow CI trên Ubuntu/Windows và CODEOWNERS nhưng **không đồng nghĩa branch protection đã bật**. Owner cần kiểm tra gói/settings hiện có: hạn chế cập nhật `main`; với `dev` yêu cầu PR, một approval, hai checks `checks (ubuntu-24.04)` / `checks (windows-latest)` và chặn force-push nếu tính năng được hỗ trợ. Nếu chưa hỗ trợ enforcement, nhóm phải giữ quy ước review/merge thủ công và ghi rõ giới hạn; không mô tả nó như bảo vệ kỹ thuật đã có.

## Coding rules

Quy tắc code ngắn gọn ở [AGENTS.md](../AGENTS.md#code-tối-thiểu-cần-giữ), áp dụng cho cả người và agent. Review tập trung vào tính đúng, dễ đọc và khả năng tái chạy.

## Làm song song với bốn người

Chốt interface, tensor contract và forecast/checkpoint schema trước khi chia implementation. Sau đó có thể chia: model/loss/training; runner/controller; baselines/configs; metrics/reporting. Chưa gán tên cá nhân khi team chưa thống nhất.

- Dùng một prequential runner chung khi protocol tương thích; không mỗi baseline một vòng thời gian khác nhau.
- Shared contracts/protocol cần người sử dụng interface review. Không sửa source constants để đổi input run hoặc experiment.
- Mỗi run ID duy nhất, mỗi người ghi vào output riêng. Không cùng ghi active pointer hoặc cùng directory.
- Một người tổng hợp tiến độ của phase; các thành viên bàn giao bằng PR và run/report IDs. Chỉ có một plan hiện hành khi nhóm chốt kế hoạch triển khai, không tự tạo nhiều bản plan riêng.

## Data và artifacts

Raw giữ nguyên, Git ignore. Processing mới phải tạo output mới có source identities, config, code version, runtime, run ID và trạng thái acceptance rõ. Verification đọc dữ liệu; report/QA mới không ghi đè evidence cũ. Thiếu required input hoặc QC không đạt phải dừng với failure rõ ràng. Nguồn tài liệu phụ tùy chọn có thể warning nếu không ảnh hưởng input bắt buộc.

Checkpoints/runs lớn giữ local hoặc nơi lưu trữ chung được team chốt. Git giữ code, config và reports/artifacts nhỏ đủ review. Chưa cần service orchestration hay experiment server.

## Các phase sắp tới — chưa triển khai

| Thứ tự | Phạm vi | Điều kiện bàn giao |
|---|---|---|
| 1 | Lấy lại raw theo catalog | Size/checksum và manifest acquisition mới; giữ nguyên raw |
| 2 | Data audit và processing mới | Schema/units/time assumptions, missing/zero, fixtures và report có run identity |
| 3 | Protocol và model inputs | Split/cohort/scaling/windows được chốt, prefix/leakage checks và report |
| 4 | Model/loss và baselines | Bám Report 1, shape/gradient/freeze checks, development evidence |
| 5 | Runner và controller | Lưu forecast trước nhãn, availability/update/switch/checkpoint tests |
| 6 | Lock/final experiments | Config khóa trước final, đối chứng công bằng, metrics và costs có evidence |

Đây là thứ tự bàn giao, không phải checklist đã hoàn thành. Core method vẫn theo Report 1; các thông số cần chọn trên development không được tune bằng final results.
