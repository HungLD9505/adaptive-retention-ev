# Independent UrbanEV/SZH Baseline Benchmark — Hữu Đức (#96)

**Owner:** Nguyễn Hữu Đức (`@huuduc32`)  
**Status:** Execution ledger complete (172/172 successful result rows); independent per-origin artifact audit and peer review remain pending.  
**Execution date:** 11 November 2026, Vietnam time (session `benchmark-20261111-003045-e3e4e0`).  
**Scope:** UrbanEV Shenzhen **Development** benchmark only. This report supersedes the earlier one-station pilot document in PR #111.

## Executive summary

The current Colab notebook and the independently produced `runs.csv` and `runs_graph.csv` report **160/160 non-spatial + 12/12 graph = 172/172 successful rows** for all 12 model families. These rows cover stations **1405, 2152, 1153 and 1693** over a 90-day Development replay. Stochastic methods were run with seeds **42, 43 and 44**, while deterministic baselines were not artificially repeated.

For the **station-equal, seed-averaged MAE** used below, the lowest transferred-neural MAE is **5.1979 kWh (timexer)**. TCN Transfer, GRU Transfer and LSTM Transfer are close, at **5.3027**, **5.3157**, and **5.3168 kWh**, respectively. This does **not** establish statistical superiority. All 60 station-and-seed-aligned within-backbone Transfer comparisons show a lower reported aggregate MAE than Target-only, but exact common-origin forecast pairing has not yet been independently replay-verified.

The full ledger can be inspected in [non-spatial CSV](https://drive.google.com/file/d/1EHQbIoVZfGAcDxavvFJ-nyqUaEv3ZevJ/view), [graph CSV](https://drive.google.com/file/d/17d7cFrohLGbtyLKBS_ZDvWvgURBqteeV/view), and the [session root](https://drive.google.com/drive/folders/19Gb0oQ0f8DC1p4Trl85aD7uDzp0HqFRr). **Drive currently reports these research artifacts as not shared**; external reviewer access must be granted separately. Copies of the two small ledgers and the notebook snapshot are committed under `experiments/member_studies/duc_baselines/` in this PR.

## Dataset, provenance and execution contract

- Dataset: prepared `urbanev-SZH-14d` release from the issue #18 input handoff. History `[B,24,7]`, known-future calendar `[B,24,5]`, hourly energy forecast `[B,24]`, next-24-hours horizon.
- Source: **65,888** eligible initial training examples, as asserted by the notebook against its prepared input metadata.
- Development targets: **1405, 2152, 1153, 1693**, all on the fixed 14-day initial-history budget. Their initial trainable example counts from the notebook/session are **4, 12, 13, 13**.
- Seeds: **42, 43, 44** for RF, XGBoost, MLP, GRU, LSTM, TCN, TimeXer, GCN-LSTM. One result per target for each deterministic method.
- Training and updates: neural source training **3 epochs** (batch 256, LR 0.001); initial target adaptation **3 epochs** (batch 4, LR 0.0005); online update **1 epoch** after eligible labels arrive; retention `lambda=0`. Ridge refits daily; SARIMA and tree models use 7-day refit cadence; SARIMA uses a 336-hour window.
- Spatial comparator: fixed geographic adjacency on 16 graph nodes (4 scored targets and 12 support stations); GCN-LSTM trains 5 initial epochs. It receives spatial inputs unavailable to non-graph models and is reported separately.
- Run environment from `session.json`: **CPU**, Intel Xeon 2.20 GHz, 2 cores, Python **3.13.18**, PyTorch **2.14.1+cpu**, scikit-learn **1.6.1**, statsmodels **0.14.5**, XGBoost **3.0.5**. TimeXer official-code commit `76011909357972bd55a27adba2e1be994d81b327`.
- Upstream code identity recorded in the execution session: `dffd16a0b37df336330ef9b9d23056facd388681` (base of the independent code used in Colab). Implementation lineage is Đức's pilot, not a copy of Cyber's result rows. The notebook explicitly follows some Cyber v3 scheduling choices but retains separately implemented model/adapter logic. Direct equality of metrics or architectures is **not** assumed.

### Replay availability (per model configuration on each station)

| Target station | Scheduled days | Issued forecasts | Scored days |
|---|---:|---:|---:|
| 1405 | 90 | 90 | 89 |
| 2152 | 90 | 59 | 52 |
| 1153 | 90 | 59 | 52 |
| 1693 | 90 | 59 | 52 |

Within each station the ledger has identical scheduled/issued/scored counts across models. Across all 172 result rows, there are **15,480 scheduled**, **11,481 issued**, and **10,535 scored row-days**. These sums repeat the same target calendar for many model configurations; they are *not* unique calendar days. Daily/per-origin forecasts have not yet been exhaustively rehashed or independently rescored here.

## Main non-spatial results

**Aggregation contract:** first mean a metric over the available seeds within each station and model/mode; then give **each of the four target stations equal weight**. The table's RMSE is a mean of per-run RMSE values, **not** a pooled RMSE over concatenated hourly errors. Lower MAE/RMSE is better. Absolute units are kWh.

| Model | Mode | Rows | Mean MAE (kWh) | Mean RMSE (kWh) |
|---|---|---:|---:|---:|
| timexer | transfer | 12 | 5.1979 | 7.1556 |
| tcn | transfer | 12 | 5.3027 | 7.2046 |
| gru | transfer | 12 | 5.3157 | 7.1630 |
| lstm | transfer | 12 | 5.3168 | 7.1523 |
| mlp | transfer | 12 | 5.4753 | 7.3131 |
| random_forest | target_only | 12 | 5.8204 | 7.7012 |
| ridge | target_only | 4 | 5.9339 | 7.9213 |
| xgboost | target_only | 12 | 6.4613 | 8.8010 |
| sarima | target_only | 4 | 6.6771 | 9.2030 |
| timexer | target_only | 12 | 7.0224 | 9.0077 |
| daily_naive | target_only | 4 | 7.0757 | 9.5704 |
| tcn | target_only | 12 | 7.8415 | 9.8784 |
| seasonal_naive | target_only | 4 | 8.4631 | 11.1458 |
| mlp | target_only | 12 | 8.6855 | 10.7766 |
| gru | target_only | 12 | 8.9239 | 10.9727 |
| lstm | target_only | 12 | 8.9565 | 11.0017 |

These are the results of **this** benchmark run, not Cyber's PR #104; do not interchange the numeric tables. See [model-level CSV](../../experiments/member_studies/duc_baselines/summary_by_model.csv) and [station-level CSV](../../experiments/member_studies/duc_baselines/summary_by_station.csv).

## Transfer vs Target-only (within backbone)

| Backbone | Target-only MAE (kWh) | Transfer MAE (kWh) | MAE reduction | Station-seed groups improved |
|---|---:|---:|---:|---:|
| mlp | 8.6855 | 5.4753 | 36.96% | 12/12 |
| gru | 8.9239 | 5.3157 | 40.43% | 12/12 |
| lstm | 8.9565 | 5.3168 | 40.64% | 12/12 |
| tcn | 7.8415 | 5.3027 | 32.38% | 12/12 |
| timexer | 7.0224 | 5.1979 | 25.98% | 12/12 |

A positive percentage here is computed as `(Target-only MAE − Transfer MAE) / Target-only MAE × 100` using the **station-equal averages** above. The individual `transfer_pairs.csv` provides **60 station-and-seed-aligned aggregate comparisons**. Equal issued/scored counts alone do not prove identical underlying scored origin IDs; strict per-origin paired error differences, uncertainty estimates and confidence intervals remain pending. The observed improvements are exploratory Development evidence, not a Final test or a negative-transfer guarantee in new stations.

## Spatial comparator (separate)

| Model | Mode | Rows | Mean MAE (kWh) | Mean RMSE (kWh) |
|---|---|---:|---:|---:|
| gcn_lstm | spatial | 12 | 7.1790 | 9.4164 |

The graph benchmark has **12/12** successful target/seed rows. It uses a fixed geographical adjacency and spatial support histories, which differs from the non-spatial information setting. Its MAE is not evidence that a graph architecture is strictly inferior in a matched-feature comparison. The graph source differs from the independent pilot and the node/initial-history choices must be read from the saved `session.json`, notebook and per-run `graph.json`.

## Validation, limitations and open acceptance gates

**Checked now:** the native Colab notebook has executed cells through the final 172/172 assertion; the two newly read Drive ledgers contain exactly **160** and **12** rows, all with `status=ok` and nonempty numeric MAE/RMSE; model/mode/station/seed group counts and station coverage were rechecked for this report. The reported summary tables were **recomputed from these ledgers**, without importing Cyber's numbers.

**Not yet checked:** full independent per-origin reconstruction of every metric, strict forecast-before-label and matched-origin identity audit, fresh hashes/readback of every trained checkpoint and daily event file, all `sha256.json` contents, exact archived executable environment/commit alignment, local execution of repository README tests, and independent peer review. A `status=ok` row documents a completed job but is not by itself full scientific acceptance.

**Selection and generalization limitations:** this four-target cohort was already inspected and chosen using known Development coverage. The notebook records Cyber v3 as a scheduling reference, but independent implementation choices, model details, graph setup and runtime can still differ. Do not claim a strict same-protocol numerical replication of Cyber PR #104, a population-wide GRU winner, a clean held-out model-selection result or any improvement of the frozen primary Final method.

**Artifact access:** source Drive run root is currently owner-only, so reviewer readback requires permission changes by the owner. Git contains the lightweight result ledgers, session metadata and notebook snapshot; the numerous checkpoint/event artifacts remain on Drive.

**Input identities recorded in session (not freshly rehashed by this report):**
- Prepared input ZIP SHA-256: `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`.
- Input manifest SHA-256: `66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9`.
- Source identity: `c77778935190a7acd3cc00c35d7940a1c9bd59fa3dc0dca14b86505ead87b3760`.
- Downloaded updated Colab notebook SHA-256 (local readback): `3532676068745a7a4c9695b14ac01c635c7ad57147604539ffc4ff935ba5b32e`.

## References and reproducibility

- [Issue #96 — Đức's complete independent benchmark](https://github.com/HungLD9505/adaptive-retention-ev/issues/96) (benchmark acceptance contract)
- [Colab execution notebook](https://colab.research.google.com/drive/1lJrdyTcX5RAl5SHtmJZ0UF-YLw3WitlY) and [session config](https://drive.google.com/file/d/1rjq0Via0pZ084MFblDlKHvkkH-85xKND/view)
- [Independent execution artifacts (Drive)](https://drive.google.com/drive/folders/19Gb0oQ0f8DC1p4Trl85aD7uDzp0HqFRr)
- [Cyber's independent benchmark PR #104](https://github.com/HungLD9505/adaptive-retention-ev/pull/104) (context only; **not** a source for the tables)
- [Former pilot-only PR #111](https://github.com/HungLD9505/adaptive-retention-ev/pull/111) (superseded; not full results)

This change is a new benchmark report and lightweight results handoff. It does **not** merge the PR, close #96, alter data/retention/controller/Final experiments, or certify acceptance gates that are not completed.
