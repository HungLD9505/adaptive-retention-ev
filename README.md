<h1 align="center">Adaptive Transfer Learning for Cold-Start<br>Electric Vehicle Charging Demand Forecasting</h1>

<p align="center">GRU transfer forecasting with limited target history, explicit source retention and online expert weighting.</p>

<p align="center">
  <a href="report/confirmation-review-20261113/adaptive-transfer-learning-ev.pdf"><strong>Read the paper</strong></a> ·
  <a href="report/confirmation-review-20261113/README.md">LaTeX source</a> ·
  <a href="docs/reports/README.md">Results &amp; evidence</a> ·
  <a href="data/README.md">Data setup</a> ·
  <a href="#reproduce">Reproduce</a>
</p>

## Research question

When does knowledge from established charging locations remain useful for a
low-history target, and when should its influence decrease? We study source
initialization, latent retention, retention selection and adaptive fusion as
separate contributions to forecasting performance.

The reviewed manuscript contains **23 pages, native equations, eight vector
figures, twelve tables and sixteen scientific references**. Earlier reports and
executed evidence remain available through the [report index](report/README.md).

| Setting | Protocol |
|---|---|
| Forecast | Previous 24 hourly observations → next 24 hourly energy values |
| Data | UrbanEV/SZH and six CHARGED city namespaces |
| Initial target history | 7, 14 or 28 days, simulated on existing dataset identifiers |
| Evaluation | 90 scheduled daily origins; scoring and updates require complete arrived labels |
| Core model | Source-initialized GRU with a frozen source reference for latent retention |

## Findings

| Evidence scope | Observed result | Interpretation |
|---|---|---|
| [Calibrated transfer, 12 Development IDs](docs/reports/issue99-history-review-20261110/handoff.md) | Source fine-tuning reduces MAE by **29.8–33.4%** versus calibrated target-only training across the three history budgets. | Supports transfer under the measured protocol. GRU is a competitive backbone; a universal model winner is unestablished. |
| [Historical retention selection](report/Adaptive_Retention_Report.pdf) | Confidence-guided retention beats Fixed in **9/21** namespace–history groups. | Retention-selection gains are conditional. |
| [Historical two-expert fusion](docs/reports/issue99-full-scope-20261110/handoff.md) | Adaptive and matched static fusion each beat single Fixed in **18/21** groups. Adaptive beats static in **12/21** and loses in nine. | Complementary forecasts explain much of the gain; the additional weighting benefit is mixed. |
| [Locked 46-ID evaluation, 14-day history](docs/reports/issue119-confirmation-20261113/README.md) | Adaptive mean percentage reductions across seven namespaces: **0.6653% vs Fixed**, **0.3610% vs static**. Both primary intervals include zero. | The prespecified dual-comparator confirmation criterion **was not met**. Numerical-scale wins remain qualified. |
| [Bounded weighting replay, 12 exposed Development IDs](docs/reports/issue123-bounded-weighting-20261113/README.md) | Best new candidate AdaHedge: 3.284880 kWh MAE; single Fixed: **3.267000**. | The progression gate **failed**; the study stops without new-cohort training or model promotion. |

The 21 historical groups reuse identifiers, seeds and history windows; they are
descriptive aggregates. The 46 IDs are new relative to the audited recorded uses,
with unresolved unrecorded exposure and physical-site aliases. Shared historical
dates, unequal compute and external large artifacts limit generalization and
independent reproduction. See the [evidence limits](RELEASE_SCOPE.md) and
[reviewed manuscript](report/confirmation-review-20261113/adaptive-transfer-learning-ev.pdf).

## Method and implementation

Retention selection changes the training coefficient **λ**. Two-expert fusion
keeps the stable/fast coefficients fixed and changes their forecast weights
**w**. The paper reports both mechanisms and their matched controls separately.

![Implementation overview: inputs, model training, causal replay, saved artifacts and verification](docs/diagrams/system.svg)

[Data pipeline](docs/data/DATA_FLOW.md) ·
[Retention/controller contract](docs/data/CONTROLLER_CONTRACT.md) ·
[Causal replay](docs/data/PREQUENTIAL_RUNNER.md) ·
[Detailed diagrams](docs/diagrams/README.md)

## Reproduce

Use **Python 3.12** and a complete Git checkout with retained history and tags.
The offline checks use fixtures and require no raw-data download, GPU or
credentials.

```sh
python3.12 -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt -r requirements-model.txt
python -m tools.sources list
python -m tools.check_release
python -m unittest discover -s tests -v
python -m unittest discover -s experiments/fixed_adaptation -v
python -m unittest discover -s experiments/confidence_controller -v
python -m ruff check .
python -m ruff format --check .
git diff --check
```

Some provenance checks require a clean tracked checkout. Optional execution
conditions produce explicit skips. The [external-artifact checks](tests/artifact/README.md)
require original run files and are invoked separately. Passing fixtures verifies
software behavior; it does not reproduce training or establish forecasting
superiority.

For real data, use the [download and checksum guide](data/README.md) and
[identified shared snapshot](docs/data/DATA_DOWNLOADS.md). Keep datasets,
checkpoints, environments and large runs outside Git. Reproduce each study from
its own code, input, configuration and artifact identities; the original primary
execution is retained at `evidence/primary-final-20261027-v2`.

## Repository guide

| Path | Contents |
|---|---|
| `ev_inputs/` | Entity roles, features, scaling and 24→24 input windows |
| `ev_models/` | GRU, forecast/retention losses, training and checkpoints |
| `ev_control/` | Retention selection and expert-weighting rules |
| `ev_runner/` | Delayed-label replay, updates, saved state and resume |
| `ev_baselines/`, `ev_evaluation/` | Forecasting controls, metrics, paired comparisons and verification |
| `experiments/`, `tools/`, `configs/`, `notebooks/` | Study entry points, CLIs, execution locks and notebooks |
| `report/` | Current and historical manuscripts, editable source, figures and result tables |
| `docs/`, `data/`, `tests/` | Contracts/evidence, source and distribution catalogues, regression/artifact checks |

[Documentation](docs/README.md) ·
[Experiment entry points](experiments/README.md) ·
[Report 1 method reference](adaptive_retention_report_1.pdf) ·
[Contribution workflow](docs/WORKFLOW.md) ·
[Working rules](AGENTS.md)
