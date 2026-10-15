# Quy tắc làm việc

- Đọc `README.md`, `docs/WORKFLOW.md` và `data/README.md` trước khi làm task.
- Report 1 là nguồn chuẩn phương pháp. Không âm thầm đổi task 24→24, budgets, loss, retention hoặc controller; ghi đề xuất thay đổi riêng để review.
- Không coi research gap, novelty hoặc hiệu quả là đã chứng minh. Không dùng kết quả/fixtures của code cũ như kết quả của implementation mới.
- Mọi implementation trên nhánh riêng và qua PR. Dùng prefix theo mục đích: `feat/`, `fix/`, `docs/`, `chore/`; nhánh lưu lịch sử dùng `archive/`. Quy tắc áp dụng cho cả thành viên và coding agent. Không push trực tiếp hoặc force-push `main`.
- `main` chỉ nhận phần có tests/checks phù hợp, báo cáo bàn giao và ít nhất một reviewer khác tác giả. Không tự merge khi chưa có review theo quy trình nhóm.
- `data/sources.json` giữ nguồn tải và fingerprints lịch sử. Nêu rõ chưa kiểm tra file thật nếu raw chưa có; checksum lịch sử không phải bằng chứng vừa tải lại.
- Không ghi đè, chỉnh sửa hoặc xóa raw archives. Không fill target labels, coi missing là zero hoặc dùng future labels trước availability.
- Dataset, environment, checkpoints và runs lớn giữ ngoài Git. Không commit secrets hoặc credentials.
- Foundation chưa có processing/model. Chỉ tạo module khi có implementation cần thiết; tránh framework hoặc abstraction chưa có use case.
- Với pipeline mới: ghi config, source/input identity, code version, runtime, run ID và acceptance scope; tạo output mới, không ghi đè run cũ.
- Tests phải dùng fixtures độc lập khi có thể. Tests/CI thông thường không tải raw hoặc chạy training dài.
- Chạy các commands kiểm tra trong README, báo rõ pass/fail/chưa chạy và giới hạn. Không sửa expected hashes hoặc fixtures để che một thay đổi chưa giải thích.
- Đưa report của phase/PR vào `docs/reports/` khi có bàn giao thực tế; không tạo nhiều bản plan mâu thuẫn.
