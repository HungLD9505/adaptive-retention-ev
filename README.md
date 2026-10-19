# Adaptive Retention — Research Foundation

Foundation for **Adaptive Transfer Learning for Cold-Start EV Charging Demand Forecasting**. Work follows **Issue → working branch → PR → `dev`**. Updating `main` requires a separate instruction.

**Current status:** the data source catalog and local archive verification tool are implemented. The two required raw archives have been acquired and verified locally; see the [acquisition report](docs/reports/data-acquisition.md). Raw files are not stored in Git. Data-processing and model-input implementations are under review; model training and experiments are not implemented yet.

## Start here

Read the [Master Research Flow — WHY → HOW → PROVE](docs/MASTER_RESEARCH_FLOW.md) to understand the problem, proposed method, and required evidence.

Start with [From the two datasets to model inputs](docs/data/DATA_FLOW.md) for the complete raw → hourly → training/prediction-input flow and a guide to the actual local folders.

For file-by-file dataset explanations, read the [UrbanEV reference](docs/data/URBANEV.md) and [CHARGED / AMS reference](docs/data/CHARGED.md).

The #18 [development loader](docs/reports/input-loader.md) integrates hourly manifest/CSV IO with pinned feature, split/scaler and window helpers. It is validated on independent fixtures; real producer runs, official cohorts/artifacts and model handoff remain pending review.

The [real-data loader trial](docs/reports/input-loader-real.md) covers all UrbanEV/CHARGED entity IDs and budgets 7/14/28. It records actual counts and incomplete UrbanEV prefixes for review; official input/cohort acceptance and model handoff remain pending.

The [input handoff policy](docs/data/INPUT_ACCEPTANCE.md) records the user-selected missing-data rules and v2 coverage accounting. Historical real-data trial counts remain unchanged; see the [policy handoff report](docs/reports/input-handoff.md) for rerun evidence. Independent peer acceptance is still required.

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
