# Adaptive Retention — Research Foundation

Foundation for **Adaptive Transfer Learning for Cold-Start EV Charging Demand Forecasting**. Work follows **Issue → working branch → PR → `dev`**. Updating `main` requires a separate instruction.

**Current status:** raw acquisition, UrbanEV hourly processing, CHARGED audit/adapter and the model-input pipeline are implemented. The shared data snapshot includes raw, hourly and prepared 7/14/28-day inputs. See the [integrated verification and acceptance record](docs/reports/data-integration.md) for checks, scope and the lead-directed review exception. Models, controllers and research experiments are not implemented yet. Large data stays on Drive/outside Git.

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
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

Run before opening a PR:

```sh
python -m tools.sources list
python -m unittest discover -s tests -v
python -m ruff check .
python -m ruff format --check .
git diff --check
```

Tests use temporary fixtures and require no raw datasets, GPU, credentials, or dataset downloads. The data/input pipelines use the standard library; Ruff is the only development dependency. Data/ML dependencies will be selected and locked in their implementation PRs.

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
