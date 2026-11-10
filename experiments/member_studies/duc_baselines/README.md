# Hữu Đức independent UrbanEV benchmark (Issue #96)

This directory is the **11 November 2026** lightweight benchmark handoff; the independent execution was performed in Google Colab and the complete artifacts remain on Google Drive.

| Path | Contents |
|---|---|
| `urbanev_szh_benchmark_issue96.ipynb` | Downloaded Colab notebook snapshot with executed cells and end-of-run 172/172 assertion |
| `session.json` | Execution config, input identity, environment, station/seed settings |
| `runs.csv` | 160 raw non-spatial model/mode/station/seed result rows |
| `runs_graph.csv` | 12 separate spatial result rows |
| `summary_by_model.csv` | Seed-then-station-equal MAE/RMSE summary |
| `summary_by_station.csv` | Per station/model/mode seed-average summary |
| `transfer_pairs.csv` | 60 aligned-by-station-and-seed aggregate Target-only vs Transfer comparisons; not verified per-origin pairing |

**Report:** [docs/reports/member-duc-baselines.md](../../../docs/reports/member-duc-baselines.md). **Task:** [Issue #96](https://github.com/HungLD9505/adaptive-retention-ev/issues/96).

Run provenance: [Drive session](https://drive.google.com/drive/folders/19Gb0oQ0f8DC1p4Trl85aD7uDzp0HqFRr) · [Colab source](https://colab.research.google.com/drive/1lJrdyTcX5RAl5SHtmJZ0UF-YLw3WitlY). The session folder is currently not shared outside its owner account. To rerun, use the notebook and verified UrbanEV issue18 data, original source repository modules and package requirements captured in the notebook/session; cloning this directory alone does not obtain the full training inputs or checkpoints.

Verification status: ledger completeness and summary derivation checked; exhaustive daily/event/checkpoint hash validation and reviewer acceptance **pending**. Do not treat these results as Final or as proof of a universally best backbone.
