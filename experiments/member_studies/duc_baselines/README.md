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
| `transfer_pairs.csv` | 60 aligned-by-station-and-seed aggregate Target-only vs Transfer comparisons; reviewer verified exact common scored origins |

**Report:** [docs/reports/member-duc-baselines.md](../../../docs/reports/member-duc-baselines.md). **Task:** [Issue #96](https://github.com/HungLD9505/adaptive-retention-ev/issues/96).

Run provenance: [Drive session](https://drive.google.com/drive/folders/19Gb0oQ0f8DC1p4Trl85aD7uDzp0HqFRr) · [Colab source](https://colab.research.google.com/drive/1lJrdyTcX5RAl5SHtmJZ0UF-YLw3WitlY). Reviewer access and authenticated artifact readback are confirmed. To rerun, use the notebook and verified UrbanEV issue18 data, original source repository modules and package requirements captured in the notebook/session; cloning this directory alone does not obtain the full training inputs or checkpoints.

**CI/lint policy:** `urbanev_szh_benchmark_issue96.ipynb` is the byte-identical **186,940-byte executed snapshot** with SHA-256 `3532676068745a7a4c9695b14ac01c635c7ad57147604539ffc4ff935ba5b32e`. It is explicitly excluded from Ruff by `pyproject.toml`, following the existing policy for immutable executed notebooks. This **does not mean that historical notebook code passes Ruff**. If the notebook is modified for future maintenance, save a **different versioned maintained source/notebook**, lint it normally, and never replace or imply re-execution of this archived evidence. The `ci.yml` workflow is unchanged.

**Protocol:** See the [post-execution #95/#96 protocol reconciliation](../../../docs/reports/member-duc-baselines.md#issue-95--96-benchmark-protocol-reconciliation-post-execution). The team lead accepted the fixed-recipe exploratory Development scope on 11 November 2026, waiving prospective joint protocol and architecture-specific tuning requirements for this handoff. Final merge review is pending.

Verification status: reviewer artifact/hash validation, daily/run metric reconstruction, causal event chronology and common-origin pairing passed. See the [audit receipt](https://github.com/HungLD9505/adaptive-retention-ev/pull/114#issuecomment-6783698688). Full training reproduction, upstream raw-data audit and bootstrap superiority analysis were not performed. Final peer approval and latest-revision CI remain pending. Do not treat these results as Final or as proof of a universally best backbone.
