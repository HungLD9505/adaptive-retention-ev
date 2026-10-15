# Bàn giao foundation thay main — 15/10/2026

## Mục tiêu và phạm vi

Tạo working tree sạch để nhóm làm lại processing và phát triển các phase sau theo review. Bản trước ở commit `528680dd73791322ed12f32b2c72a3b58618a428` được giữ bằng remote branch `master`; không rewrite lịch sử hoặc force-push main.

Nhánh đề xuất: `feat/research-foundation`. Đây là implementation để review, chưa đồng nghĩa main đã được thay thế hoặc reviewer đã nghiệm thu. PR #3 về Master Flow thay thế PR #2 sau khi đổi tên nhánh; vẫn được review riêng, chưa merge.

## Những gì mang sang

- Report 1 nguyên bytes, SHA-256 `cafc1db09a7fda4e196808a96cedf1b18098a4e7ff859d272402e049ebd65bbc`.
- URL/release, số bytes, SHA-256 và publisher checksum của ba archive trong acquisition manifest ngày 02/10/2026: UrbanEV chính, supplemental tùy chọn và CHARGED Hourly standard.
- Provenance trỏ chính xác về commit/path của manifest cũ, giữ khác biệt giữa SHA team quan sát và checksum publisher.

Không mang code Data/Input cũ, processed data, window indices, reports hoặc PASS flags cũ sang làm pipeline/evidence mới. Chúng vẫn truy cập được trong backup và Git history. Không có raw directories trong checkout lúc bắt đầu; không có raw file nào bị sửa/xóa trong task này.

## Đã triển khai trên nhánh mới

- `data/sources.json` và hướng dẫn lấy đúng archive, vị trí đặt file và giới hạn dữ liệu.
- `python -m tools.sources list`: liệt kê nguồn đã ghi, không gọi mạng.
- `python -m tools.sources verify`: kiểm tra local size/SHA-256/publisher checksum, không ghi hoặc tải data; failure có exit code khác 0.
- Guards cho catalog, duplicate IDs/paths và resolved paths; unit fixtures không phụ thuộc data thật.
- Python 3.12, venv, Ruff pin chính xác; không mang dependencies xử lý/ML cũ sang.
- CI Ubuntu/Windows: catalog, tests, lint, format và diff checks; actions pin theo commit SHA.
- AGENTS, CODEOWNERS, PR template, ignore rules và quy trình branch → checks/report → review → main.
- Text dùng LF; binary/raw checksum không phụ thuộc chuyển line endings.

## Kiểm tra local

Commands chạy từ repository root bằng Python 3.12; môi trường phát triển tạo ở thư mục tạm ngoài repo.

| Kiểm tra | Kết quả |
|---|---|
| Unit fixtures | 9 tests PASS: selection, missing, valid file, size mismatch, same-size corruption, publisher checksum, path guards và CLI exit codes |
| Archive identities so với manifest lịch sử | 3/3 khớp URL, size, SHA-256, publisher checksum |
| Report 1 so với `origin/main` | Nguyên bytes, hash khớp |
| `tools.sources list` | PASS; không tải data |
| Ruff, dependency check, links và diff | PASS: Ruff lint/format, pip check; local document links và git diff --check |
| CI trên GitHub | Chờ chạy và team review; không coi cấu hình workflow là một run PASS |

Tests dùng bytes tổng hợp, không phải ZIP dataset thật và không là bằng chứng data đã tải được. Checksum PASS trong fixtures chỉ kiểm tra hành vi tool.

## Chưa làm / giới hạn

- Chưa tải, extract hoặc checksum lại các archive thật. Download endpoints giữ theo provenance lịch sử; không khẳng định link đang tải được.
- Chưa có acquisition/processing pipeline mới, data audit mới, inputs, model, loss/controller hoặc experiments.
- Các unknown về upstream processing/masks, time/bin/label arrival và Shenzhen independence vẫn cần audit; chưa claim strict online.
- Branch protection chưa được cấu hình: tài khoản thực thi không có admin; API còn báo giới hạn private-repo rulesets. CI/CODEOWNERS không tự tạo enforcement.
- Chưa xác nhận mọi thành viên hiểu method hoặc đã setup máy. Peer review còn cần thực hiện trước merge.

## Bước bàn giao tiếp theo

Sau khi foundation được review/merge: tạo nhánh acquisition để tải hoặc phục hồi đúng raw, xác nhận size/checksums và ghi manifest mới. Sau đó mới triển khai processing mới với acceptance criteria, fixtures và report riêng. Không sửa expected hashes để nhận một release khác hoặc đánh dấu phase sau hoàn thành từ evidence cũ.
