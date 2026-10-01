# Phase data CLI

Chạy từ project root. Dependencies chỉ nằm trong `.deps` của project:

```powershell
python -m pip install --target .deps --no-cache-dir -r requirements-data.txt
python src/data/acquire.py --run-id acquisition_<unique>
python src/data/test_acquire.py
python src/data/test_process.py
python src/data/process.py --dataset urbanev --run-id urbanev_smoke_<unique> --limit 3
python src/data/process.py --dataset urbanev --run-id urbanev_full_<unique>
python src/data/audit_auxiliary.py --run-id urbanev_full_<unique>
python src/data/process.py --dataset charged --run-id charged_smoke_<unique> --limit 3
python src/data/process.py --dataset charged --run-id charged_full_<unique>
python src/data/verify.py --run-id urbanev_full_<unique>
python src/data/verify.py --run-id charged_full_<unique>
python src/data/finalize.py --run-id urbanev_full_<unique>
python src/data/finalize.py --run-id charged_full_<unique>
```

Không dùng lại run_id; raw đã tồn tại được checksum/size kiểm tra và tái sử dụng, không ghi đè. FileLock ngăn hai writers cùng raw path. Partial lỗi được giữ riêng.

Panel tên `*_hourly_candidate.parquet`: tổng hợp theo giờ hiển thị trong released timestamps, timezone/bin/availability còn unknown. `file_value_valid` chỉ là đầy đủ energy intervals số học; không chứng minh observed gốc, upstream causal hoặc snapshot inventory đúng. `strict_online_ready=false` cho tới khi chứng minh time/provenance. Không tự dịch timestamp, fill label, xóa zero, scale, split hay tạo model windows.

UrbanEV volume raw là estimate đã được publisher suy ra; bản raw không chứa trạng thái theo từng pile đủ tái tính độc lập. Auxiliary QC chỉ gắn cờ và báo cáo, không tự sửa target dựa trên metadata toàn kỳ. CHARGED giữ published hourly energy, có upstream processing và không có original masks xác nhận.

Charts nằm trong `reports/data/<run_id>/figures`; mở `eda.html` để xem. EDA toàn kỳ không được dùng chọn final cohort/model/threshold. Scaler, imputation, features, split và windows thuộc development.

`finalize.py` chạy một lần/run sau verify (và auxiliary audit đối với UrbanEV); thêm nhận xét tiếng Việt cùng visual bổ sung. `source_snapshot.py` trong mỗi full run là bản code đúng SHA-256 lúc thực thi để truy vết, không phải entrypoint cần chạy. Bản code hiện tại chỉ thêm audit metadata CHARGED và cache path; phép tổng hợp UrbanEV giữ nguyên, đã đối chiếu đầu ra độc lập.
