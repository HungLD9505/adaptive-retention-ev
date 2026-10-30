# Adaptive Retention — Research Foundation

Foundation for **Adaptive Transfer Learning for Cold-Start EV Charging Demand Forecasting**. Work follows **Issue → working branch → PR → `dev`**. Updating `main` requires a separate instruction.

**Integrated code status:** raw acquisition, UrbanEV hourly processing, CHARGED audit/adapter and the model-input pipeline are implemented. The shared data snapshot includes raw, hourly and prepared 7/14/28-day inputs. See the [integrated verification and acceptance record](docs/reports/data-integration.md) for checks, scope and the lead-directed review exception. Model/controller implementations and experiments exist on separate review branches; this documentation does not integrate or approve their code. Large data stays on Drive/outside Git.

**Research evidence as of 30 October 2026:** Qyroven's frozen Final has completed all 810 whole units / 11,340 method cells across seven namespaces, including analysis and output/bootstrap audits. Hùng has a separate bounded 360-job Final on three UrbanEV stations. The [joint evidence synthesis](docs/reports/issue23-joint-evidence-synthesis-20261030.md), [full-precision result tables and source hashes](docs/reports/issue23-joint-evidence-synthesis-20261030-v1.json), and [primary Final handoff](docs/reports/issue23-final-complete-handoff-20261029.md) distinguish the completed evidence from pending scientific review, integration, CI and scope decisions. The two implementations and cohorts must not be pooled or ranked by their absolute MAE. A consistent accuracy benefit of confidence-based selection over Fixed Retention or online best-lambda has not been established.

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
