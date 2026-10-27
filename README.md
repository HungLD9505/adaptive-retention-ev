# Adaptive Retention — Research Foundation

Foundation for **Adaptive Transfer Learning for Cold-Start EV Charging Demand Forecasting**. Work follows **Issue → working branch → PR → `dev`**. Updating `main` requires a separate instruction.

**Current status:** raw acquisition, UrbanEV hourly processing, CHARGED audit/adapter and the model-input pipeline are implemented. The shared data snapshot includes raw, hourly and prepared 7/14/28-day inputs. See the [integrated verification and acceptance record](docs/reports/data-integration.md) for checks, scope and the lead-directed review exception. The independent #19 GRU/source/adaptation implementation and actual Colab Development smoke are available for peer review; see [training instructions](docs/data/MODEL_TRAINING.md) and the [run handoff](docs/reports/issue19-qyroven.md). The independent #20 controller and #21 online runner, including real Development replay/resume evidence, are also available for review; see the [runner handoff](docs/reports/issue21-qyroven.md). The baseline/ablation implementation and seven-namespace Development smoke are available for review; see the [comparison handoff](docs/reports/issue22-qyroven.md). A [three-seed UrbanEV readiness run](docs/reports/issue23-readiness.md) adds sparse/source-only and exact GPU resume evidence. The [complete Development evidence handoff](docs/reports/issue23-development-handoff.md) now covers all 231 declared whole units / 3,234 method cells across UrbanEV and six separate CHARGED cities, with independent artifact checks and full analyses. The [bounded Final preparation](docs/reports/issue23-final-bounded-preparation.md) declares30UrbanEV stations plus10sites per CHARGED city with shared IDs across budgets (270pairs/11,340cells). Lead Development/capacity acceptance and independent Final lock approval remain pending; no Final execution has started. Large data stays on Drive/outside Git.

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

The [confidence-controller contract](docs/data/CONTROLLER_CONTRACT.md) describes the
independent #20 helper, bootstrap profile, availability gates and #21 integration
boundary. Its example configuration is not a Final lock.

The [prequential-runner contract](docs/data/PREQUENTIAL_RUNNER.md) documents #21
candidate state, causal event order, isolated audit and daily resume. Its
[handoff](docs/reports/issue21-qyroven.md) records the actual Development smoke scope.

The [baseline contract](docs/data/BASELINE_CONTRACT.md) defines the nine comparisons,
ablation aliases, proxy estimators and calibration limits. Its
[execution handoff](docs/reports/issue22-qyroven.md) distinguishes real Development
smoke from pending scientific validation and Final configuration approval.

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

Tests use temporary fixtures and require no raw datasets, GPU, credentials, or dataset downloads. The data/input pipelines use the standard library; Ruff is the only development dependency. For #19 model tests, also install `python -m pip install -r requirements-model.txt`. The model requirements pin PyTorch/NumPy; actual training records the complete resolved environment.

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
