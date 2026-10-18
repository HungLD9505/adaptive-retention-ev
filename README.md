# Adaptive Retention — Research Foundation

Foundation for **Adaptive Transfer Learning for Cold-Start EV Charging Demand Forecasting**. Work follows **Issue → working branch → PR → `dev`**. Updating `main` requires a separate instruction.

**Current status:** the data source catalog and local archive verification tool are implemented. The two required raw archives have been acquired and verified locally; see the [acquisition report](docs/reports/data-acquisition.md). Raw files are not stored in Git. The processing pipeline, models, and experiments are not implemented yet.

## Start here

Read the [Master Research Flow — WHY → HOW → PROVE](docs/MASTER_RESEARCH_FLOW.md) to understand the problem, proposed method, and required evidence.

For file-by-file dataset explanations, read the [UrbanEV reference](docs/data/URBANEV.md) and [CHARGED / AMS reference](docs/data/CHARGED.md).

The proposed [model input contract](docs/data/INPUT_CONTRACT.md) defines the #18 feature schema and input/label boundary for review; no model input pipeline or official artifacts are implemented by that document.

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

Tests use temporary fixtures and require no raw datasets, GPU, credentials, or dataset downloads. The foundation uses the standard library; Ruff is the only development dependency. Data/ML dependencies will be selected and locked in their implementation PRs.

## Structure

```text
data/sources.json        Raw archive URLs, releases, sizes, and checksums
data/README.md           Acquisition instructions and source limitations
tools/sources.py         List sources / verify local files without writing or downloading
tests/                   Unit tests independent of real datasets
docs/WORKFLOW.md          Issue → branch → checks/review → dev; main needs separate authorization
docs/FOUNDATION_REPORT.md Foundation scope and evidence
.github/                 CI, CODEOWNERS, issue and PR templates
```
