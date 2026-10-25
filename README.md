# Adaptive Retention — Research Foundation

Foundation for **Adaptive Transfer Learning for Cold-Start EV Charging Demand Forecasting**. Work follows **Issue → working branch → PR → `dev`**. Updating `main` requires a separate instruction.

**Trạng thái trên nhánh bàn giao #39:** pipeline dữ liệu đã có [bằng chứng tích hợp](docs/reports/data-integration.md). GRU, transfer, controller và runner đã được triển khai; lượt Development đại diện trên GPU local hoàn thành 216/216 stages. Đây là bằng chứng thực thi kỹ thuật đang chờ review trong [PR #46](https://github.com/HungLD9505/adaptive-retention-ev/pull/46), chưa phải nghiệm thu phương pháp hoặc kết quả Final. Dữ liệu lớn và checkpoints nằm ngoài Git.

## Báo cáo Sprint 2 của Hùng

Đọc [bảng đánh giá và bàn giao #39](docs/reports/hung-39-assessment-handoff.md) trước. Bốn báo cáo chuẩn gồm [phương pháp và triển khai](docs/reports/hung-39-method-implementation.md), [thí nghiệm và kết quả](docs/reports/hung-39-experiments-results.md), [tái lập và artifacts](docs/reports/hung-39-reproducibility-handoff.md), cùng bảng đánh giá trên. Các báo cáo theo phase cũ và evidence JSON vẫn được giữ để truy vết các mốc lịch sử.

## Start here

Read the [Master Research Flow — WHY → HOW → PROVE](docs/MASTER_RESEARCH_FLOW.md) to understand the problem, proposed method, and required evidence.

Download the shared [DATA-v1-20261019 snapshot](docs/data/DATA_DOWNLOADS.md) for the exact raw/hourly/input files, Google Drive links and SHA-256 verification.

Start with [From the two datasets to model inputs](docs/data/DATA_FLOW.md) for the complete raw → hourly → training/prediction-input flow and a guide to the actual local folders.

For file-by-file dataset explanations, read the [UrbanEV reference](docs/data/URBANEV.md) and [CHARGED / AMS reference](docs/data/CHARGED.md).

The [input policy](docs/data/INPUT_ACCEPTANCE.md) defines masks, coverage gates, per-target initialization and checkpoint input binding. The [input handoff](docs/reports/input-handoff.md) records actual counts; the [integration report](docs/reports/data-integration.md) records final combined verification. Earlier fixture/trial reports retain their original snapshot status and do not supersede that acceptance record.

1. Read the [team workflow](docs/WORKFLOW.md) and [working rules](AGENTS.md).
2. Read the [data sources and download/verification instructions](data/README.md).
3. Review the [foundation handoff report](docs/FOUNDATION_REPORT.md).
4. Use [Report 1](adaptive_retention_report_1.pdf) as the unchanged method reference.

## Environment setup

Use **Python 3.12**. Do not copy virtual environments or compiled dependencies between machines.

macOS/Linux:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip install --index-url https://download.pytorch.org/whl/cpu -r requirements-model.txt
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pip install --index-url https://download.pytorch.org/whl/cpu -r requirements-model.txt
```

Run before opening a PR:

```sh
python -m tools.sources list
python -m unittest discover -s tests -v
python -m ruff check .
python -m ruff format --check .
git diff --check
```

Tests use temporary fixtures and require no raw datasets, GPU, credentials, or dataset downloads. The data/input pipelines use the standard library. Hung's draft Sprint 2 model fixtures require the pinned CPU PyTorch dependency in `requirements-model.txt`; this dependency and the CI install step are proposed for review in PR #42 before integration.

## Structure

```text
data/sources.json        Original raw-source URLs and fingerprints
data/releases/          Shared Drive snapshot links, sizes and SHA-256
tools/                 Raw verification and hourly/input CLIs
ev_inputs/             Feature, split/scaler, window and loader helpers
tests/                 Independent offline fixtures
docs/data/             Dataset references, flow, contracts and downloads
docs/reports/          Actual run evidence and integration acceptance
docs/WORKFLOW.md       Issue → branch → PR → dev; main needs explicit instruction
.github/               CI, CODEOWNERS and issue/PR templates
```
