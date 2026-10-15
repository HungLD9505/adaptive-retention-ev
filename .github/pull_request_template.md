Issue: #... (PR vào `dev`; cập nhật/đóng issue khi acceptance criteria đạt).

## Vấn đề và kết quả

Mô tả vấn đề, phạm vi và hành vi sau thay đổi.

## Phạm vi phương pháp / dữ liệu

- Có thay đổi phương pháp, protocol hoặc nguồn dữ liệu không? Nếu có, chỉ rõ quyết định cần review.
- Source/input/run IDs và config liên quan:

## Kiểm tra và evidence

- Commands đã chạy và kết quả:
- Report bàn giao / artifacts nhỏ có thể review:
- Phần chưa chạy, assumptions và giới hạn:

## Checklist

- [ ] Tests, lint, format và diff checks phù hợp đã pass.
- [ ] Không commit raw, checkpoints, environment hoặc secrets.
- [ ] Không ghi đè raw/run cũ hoặc dùng future data trái protocol.
- [ ] Report và tài liệu liên quan khớp implementation thực tế.
- [ ] Target là `dev`; vào `main` phải có chỉ đạo riêng cho lần cập nhật này.
- [ ] Có peer khác tác giả duyệt commit mới nhất (Approve review hoặc comment `approved merge` + SHA theo WORKFLOW).
