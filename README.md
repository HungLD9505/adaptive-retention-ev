# Adaptive Retention — Research Foundation

Nền tảng mới cho khóa luận **Adaptive Transfer Learning for Cold-Start EV Charging Demand Forecasting**. Nhóm phát triển trên nhánh riêng; `main` chỉ nhận thay đổi đã có checks, báo cáo và review.

**Trạng thái của bản này:** đã lập catalog nguồn dữ liệu và công cụ kiểm tra file sau tải. Chưa tải raw, chưa xây pipeline xử lý mới, chưa có model hoặc kết quả thực nghiệm trên nền tảng mới.

## Bắt đầu

Đọc [Master Research Flow — WHY → HOW → PROVE](docs/MASTER_RESEARCH_FLOW.md) để hiểu bài toán, phương pháp và bằng chứng cần có.

1. Đọc [quy trình làm việc](docs/WORKFLOW.md) và [quy tắc cho coding agents](AGENTS.md).
2. Đọc [nguồn dữ liệu và cách tải/kiểm tra](data/README.md).
3. Xem [báo cáo bàn giao foundation](docs/FOUNDATION_REPORT.md).
4. Khi làm method, đối chiếu [Report 1](adaptive_retention_report_1.pdf), nguồn chuẩn thiết kế được giữ nguyên.

## Thiết lập môi trường

Dùng **Python 3.12**, không sao chép virtualenv hoặc compiled dependencies giữa các máy.

macOS/Linux:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

Kiểm tra trước khi mở PR:

```sh
python -m tools.sources list
python -m unittest discover -s tests -v
python -m ruff check .
python -m ruff format --check .
git diff --check
```

Tests dùng fixtures tạm; không yêu cầu raw data, GPU, credential hoặc tải dataset. Foundation chỉ dùng standard library; Ruff là dependency phát triển duy nhất. Data/ML dependencies sẽ được chọn và khóa trong PR triển khai tương ứng.

## Cấu trúc

```text
data/sources.json       Catalog URL, release, size và checksum của raw archives
data/README.md          Cách lấy dữ liệu và giới hạn nguồn
tools/sources.py        Liệt kê nguồn / kiểm tra file local, không ghi hoặc tải data
tests/                  Unit tests không phụ thuộc dataset thật
docs/WORKFLOW.md         Branch → implementation → checks → report → review → main
docs/FOUNDATION_REPORT.md Phạm vi và evidence của lần dựng foundation
.github/                CI, CODEOWNERS và PR template
```

## Lịch sử và chuyển đổi

Bản trước được giữ tại [backup `master`](https://github.com/HungLD9505/adaptive-retention-ev/tree/master), commit `528680dd73791322ed12f32b2c72a3b58618a428`. Code processing, processed outputs và trạng thái PASS cũ không được mang sang làm pipeline hoặc kết quả của foundation mới.

[Master Research Flow](docs/MASTER_RESEARCH_FLOW.md) đã đối chiếu trạng thái với foundation mới. Evidence và các quyết định Data/Input từ codebase trước được dẫn về commit lịch sử, không tính là tiến độ implementation mới.

Raw archives nếu đã có ở máy khác phải giữ nguyên và kiểm tra checksum trước khi dùng. Raw, processed data, virtualenv, checkpoints và run outputs không được commit vào Git.
