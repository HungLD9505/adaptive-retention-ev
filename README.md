# Adaptive Retention — Research Foundation

Foundation for **Adaptive Transfer Learning for Cold-Start EV Charging Demand Forecasting**. Work follows **Issue → working branch → PR → `dev`**. Updating `main` requires a separate instruction.

**Integration snapshot:** this source tree combines the data/input foundation, the primary GRU/controller/runner/baseline/evaluation implementation and isolated member studies for `dev`. The lead-directed integration scope, local checks and remaining scientific limits are recorded below. The shared data snapshot includes raw, hourly and prepared 7/14/28-day inputs. See the [integrated verification and acceptance record](docs/reports/data-integration.md) for checks, scope and the lead-directed review exception. The [integration handoff](docs/reports/dev-integration-final-20261102.md) records the preserved heads, local verification and outstanding review limits. Large data stays on Drive/outside Git.

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

## Implementations in this integration candidate

- **Primary pipeline:** `ev_models/`, `ev_control/`, `ev_runner/`, `ev_baselines/` and
  `ev_evaluation/`; the contracts linked above describe its interfaces. The report's
  primary results belong to its pinned historical execution, not to an untested rerun
  of this integration branch.
- **Duc study:** `experiments/member_studies/duc_retention/` contains an isolated
  fixed-model Development study with separate settings and historical dependencies.
  It is not an online controller benchmark.
- **Cyber study:** `experiments/member_studies/cyber_controller/` is preserved as
  a separate implementation with [corrected input and replay guards](
  experiments/member_studies/cyber_controller/README.md). Historical scores were not
  rerun and are not outputs of the corrected IO version.
- **Hung supporting track:** `experiments/hung_sprint2/` and the `tools/hung_*`
  utilities preserve #72 as a separate implementation. Historical Development and
  bounded three-station Final results remain distinct from primary results.
  See the [integration scope and limitations](docs/reports/dev-integration-final-20261102.md).

## Environment setup

Use **Python 3.12**. Do not copy virtual environments or compiled dependencies between machines.

macOS/Linux:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip install -r requirements-model.txt
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pip install -r requirements-model.txt
```

Run the offline checks below. Historical artifact checks are separate; see
[external artifact verification](tests/artifact/README.md). No GPU or dataset download
is required for these offline commands.

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
