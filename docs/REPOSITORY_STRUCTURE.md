# Cấu trúc repository — 07/10/2026

| Vị trí | Vai trò |
|---|---|
| README.md | Điểm bắt đầu, links và trạng thái tổng hợp |
| adaptive_retention_report_1.pdf | Nguồn chuẩn thiết kế; giữ nguyên |
| docs/RESEARCH_ROADMAP.md | Giải thích nghiên cứu, workflow A–I và phân công |
| plan.md | Trạng thái thực thi, quyết định và nhật ký; không tạo plan trùng |
| BAO_CAO_PHASE_DATA.md, BAO_CAO_DAU_VAO_MODEL.md | Báo cáo bàn giao từng phase |
| HUONG_DAN_LAM_DO_AN_CHUNG.md và hai XLSX | Hướng dẫn/literature/blueprint; giữ làm nguồn tham khảo |
| src/data/ | Acquisition, processing, audit, verify và tests |
| src/inputs/ | Protocol, windows, loader, QC và tests |
| reports/data/, reports/inputs/ | Evidence bất biến từng run, logs, manifests và galleries |
| data/raw/, data/processed/, data/inputs/ | Dữ liệu lớn local, Git ignore |
| .deps/, .cache/ | Dependencies/cache local, Git ignore |
| handoff/ | ZIP snapshot bàn giao local, Git ignore |

## Inventory dọn dẹp

- Dọn thư mục __pycache__ trong src/data và src/inputs: bytecode tái tạo được, không phải code nguồn/evidence.
- ZIP v1/v2 giữ local; thêm handoff/ vào ignore để tránh upload bản tài liệu trùng và lỗi thời.
- Giữ smoke/partial/v1/rebuild, source_snapshot và manifests để truy vết. Không di chuyển reports/data/input vì manifest/CLI/galleries dùng đường dẫn này.
- Active Input xác định bằng reports/inputs/active_runs.json; v1 có superseded_by.json. Data active: urbanev_full_20261002_01, charged_full_20261002_02.
- Không xóa raw/panel/index, PDF/XLSX, reports, logs hoặc checkpoints. Không có file report nào được xác định là thừa đủ bằng chứng để xóa.

Không tạo thư mục model rỗng hoặc ghi đã training khi chưa thực hiện. Module model/controller sẽ thêm trong phase tiếp theo cùng tests/config tương ứng.
