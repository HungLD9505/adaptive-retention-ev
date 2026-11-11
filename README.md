# Adaptive Retention

**Low-history EV charging demand forecasting with GRU transfer learning.**

When should a target model retain knowledge from its source, and when should it
adapt? This research repository implements and evaluates fixed and adaptive
source-retention strategies under causal 24→24 forecasting.

[**Report**](report/Adaptive_Retention_Report.pdf) ·
[**Supplement**](report/Adaptive_Retention_Supplement.pdf) ·
[**System diagrams**](docs/diagrams/README.md) ·
[**Documentation**](docs/README.md) ·
[**Data**](data/README.md)

| Forecast task | Initial target history | Evaluation | Backbone |
|---|---|---|---|
| Past 24 hours → next 24 hours | 7 / 14 / 28 days | 90-day prequential replay | GRU |

## System overview

![Primary research system](docs/diagrams/system.svg)

The diagram shows how prepared inputs, model training, replay, verification and
reporting connect. Detailed views:

- [Data pipeline: UrbanEV/CHARGED preparation and separated labels](docs/data/DATA_FLOW.md).
- [Adaptive mechanism: forecast, observe, update and select](docs/data/CONTROLLER_CONTRACT.md).


## Results and interpretation

The primary frozen execution covers **810 units / 11,340 method cells**, seven
namespaces and three seeds. Null outcomes remain explicit.

| Comparison | Aggregates with lower Adaptive mean MAE |
|---|---:|
| Adaptive vs Target-only | 18 / 21 |
| Adaptive vs Fixed retention | 9 / 21 |

The 21 cells are dataset-group/history aggregates, not independent replications or
significance counts. The source-based Adaptive pipeline has lower error than Target-only in many
evaluated settings; its retention-selection mechanism does not consistently beat
Fixed. Read the [report](report/Adaptive_Retention_Report.pdf),
[paired evidence and limitations](docs/reports/issue23-joint-evidence-synthesis-20261030.md)
and [full-precision tables](report/full-results.csv).

Evaluation scope, coverage and comparisons are documented in the report and
supplement. Results from experiments with different settings are reported separately.

## Reproduce and inspect

Use **Python 3.12** in a new environment. A full Git checkout with retained
history/tags is required for provenance checks. No raw-data download, GPU or
credentials are needed for the offline checks.

```sh
python3.12 -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
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

Tests use fixtures; CUDA checks skip when unavailable. Some provenance tests need a
clean tracked checkout. The [18 external-artifact tests](tests/artifact/README.md)
require original trained artifacts and are invoked separately. Offline test success
does not reproduce training or prove research effectiveness.

For actual data, follow the [download and checksum instructions](data/README.md)
and [shared snapshot guide](docs/data/DATA_DOWNLOADS.md). Data, checkpoints,
environments and large runs are excluded from Git. Preserve their bytes and
verify identities locally; historical checksums alone do not prove a fresh download.

## Repository map

| Directory | Contents |
|---|---|
| `ev_inputs/` | Dataset-role assignment, feature encoding, scaling, time windows and input loading |
| `ev_models/` | GRU architecture, forecast and retention losses, training and model checkpoints |
| `ev_control/` | Paired-error bootstrap calculations and retention-selection rules |
| `ev_runner/` | Forecast scheduling, label-availability checks, online updates, state persistence and resume |
| `ev_baselines/` | Forecasting baselines and ablation policies |
| `ev_evaluation/` | Error metrics, paired comparisons, uncertainty, cost accounting and artifact verification |
| `experiments/` | Experiment-specific training, adaptation, replay and evaluation modules |
| `tools/` | Command-line programs for data processing, experiment execution and verification |
| `configs/` | Data-processing settings, experiment parameters and execution locks |
| `data/` | Source catalog, download references and dataset release manifests; dataset files are excluded from Git |
| `notebooks/` | Notebooks for inspecting inputs and invoking model, replay and evaluation workflows |
| `tests/` | Offline fixtures, regression checks and separately invoked artifact checks |
| `report/` | Report and supplement PDFs, LaTeX source, figures and numerical result tables |
| `docs/` | Data definitions, algorithm contracts, diagrams, usage instructions and evidence references |

For experiment entry points, see [experiments/README.md](experiments/README.md).
For input/output contracts, see the [documentation index](docs/README.md).

## Reproducing the reported results

The reported primary results belong to source tag
`evidence/primary-final-20261027-v2`. Use the identified source, data, configuration
and artifact hashes when reproducing a recorded experiment. The current verifier
checkout is not a replacement for that original execution environment.

[Report 1](adaptive_retention_report_1.pdf) defines the method. The
[evidence index](docs/reports/README.md) links results to their validation records;
[RELEASE_SCOPE.md](RELEASE_SCOPE.md) states coverage and unresolved limitations,
including incomplete full compute accounting and unverified diagnostic results.
Offline fixtures establish software behavior, not forecasting superiority.

See the [contribution workflow](docs/WORKFLOW.md) and [working rules](AGENTS.md)
for repository changes.

## Research team

- [HungLD9505](https://github.com/HungLD9505)
- [Qyroven](https://github.com/Qyroven)
- [hung00cyber](https://github.com/hung00cyber)
- [huuduc32](https://github.com/huuduc32)
