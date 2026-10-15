# Adaptive Retention — Research Foundation

Foundation for **Adaptive Transfer Learning for Cold-Start EV Charging Demand Forecasting**. Work follows **Issue → working branch → PR → `dev`**. Updating `main` requires a separate instruction; `master` preserves the previous codebase.

**Current status:** the data source catalog and local archive verification tool are implemented. Raw archives have not been downloaded in this foundation task. The new processing pipeline, models, and experimental results are not implemented yet.

## Start here

Read the [Master Research Flow — WHY → HOW → PROVE](docs/MASTER_RESEARCH_FLOW.md) to understand the problem, proposed method, and required evidence.

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

## History and transition

The previous codebase is preserved on [backup branch `master`](https://github.com/HungLD9505/adaptive-retention-ev/tree/master), commit `528680dd73791322ed12f32b2c72a3b58618a428`. Old processing code, processed outputs, and PASS statuses are not carried forward as the new pipeline or its results.

The [Master Research Flow](docs/MASTER_RESEARCH_FLOW.md) distinguishes the new foundation from historical Data/Input evidence and decisions, linked to fixed historical commits. Those records do not count as progress on the new implementation.

If raw archives already exist on another machine, preserve their bytes and verify checksums before use. Do not commit raw or processed data, virtual environments, checkpoints, or run outputs to Git. Maintained repository content, issues, and PR descriptions use English; original source documents and historical evidence remain unchanged.
