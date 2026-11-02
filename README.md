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

The overview maps primary code responsibilities. For the two detailed views:

- [Data pipeline: UrbanEV/CHARGED preparation and separated labels](docs/data/DATA_FLOW.md).
- [Adaptive mechanism: forecast, observe, update and select](docs/data/CONTROLLER_CONTRACT.md).

Member implementations retain their own settings and evidence boundaries.

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

Hùng's separate bounded 360-job Final and the Đức/Cyber studies use different
settings. Their scores are not pooled with the primary evaluation or ranked by
absolute MAE.

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
python -m unittest discover -s experiments/member_studies/duc_retention -v
python -m unittest discover -s experiments/member_studies/cyber_controller -v
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

| Location | Responsibility |
|---|---|
| `ev_inputs/` | Roles, scaling, windows and authenticated loading |
| `ev_models/` | GRU, retention loss and training |
| `ev_control/` | Evidence-based retention selection |
| `ev_runner/` | Causal replay, label gates, updates and checkpoints |
| `ev_baselines/`, `ev_evaluation/` | Comparisons, metrics and verification |
| `tools/`, `configs/` | Data/experiment utilities and versioned configurations |
| `experiments/hung_sprint2/` | Separate supporting implementation |
| `experiments/member_studies/` | Isolated Đức and Cyber studies |
| `report/` | Report PDFs, LaTeX sources, vector figures and result tables |
| `docs/` | Diagrams, contracts, curated evidence and archive navigation |
| `tests/` | Offline fixtures and separate artifact verification |

## Scope and provenance

[RELEASE_SCOPE.md](RELEASE_SCOPE.md) states the exact inclusion scope and unresolved
criteria. Full end-to-end compute accounting, expanded supporting reproduction,
a verified Đức bundle distribution link and corrected-code Cyber real-data results
remain incomplete. Fixtures for Cyber's [corrected IO guards](
experiments/member_studies/cyber_controller/README.md) do not turn historical scores
into corrected-code results. No further real-data training is planned for this release.

The primary results belong to frozen source tag
`evidence/primary-final-20261027-v2`, not a new run of the current verifier code.
[Report 1](adaptive_retention_report_1.pdf) remains the method reference.
The [evidence index](docs/reports/README.md) distinguishes retained results and
validation dependencies from [historical reports](docs/ARCHIVE_INDEX.md).

## Team and contributions

The source history preserves contributions from [Qyroven](https://github.com/Qyroven),
[HungLD9505](https://github.com/HungLD9505), [huuduc32](https://github.com/huuduc32)
and [hung00cyber](https://github.com/hung00cyber). Integration preserves their
original commits; implementation contribution is distinct from scientific
validation of each result.

Follow [AGENTS.md](AGENTS.md) and the [workflow](docs/WORKFLOW.md) for changes.
Work integrates through `dev`; updating `main` requires a separate instruction.
`master` is retained as a backup.
