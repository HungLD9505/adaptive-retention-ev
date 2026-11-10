# Huu Duc UrbanEV benchmark results

Owner @huuduc32. Related issue #96. Execution date 11 November 2026, Vietnam time.

This report replaces the pilot-only document proposed in PR #111. The full execution produced 172 successful unique model/mode/station/seed rows across 12 model families. Scientific acceptance and peer review remain open.

## Evidence and execution

- Run directory `benchmark-20261111-003045-e3e4e0`.
- [Executed Colab notebook](https://colab.research.google.com/drive/1lJrdyTcX5RAl5SHtmJZ0UF-YLw3WitlY).
- [External run artifacts](https://drive.google.com/drive/folders/19Gb0oQ0f8DC1p4Trl85aD7uDzp0HqFRr).
- [Non-spatial ledger](https://drive.google.com/file/d/1EHQbIoVZfGAcDxavvFJ-nyqUaEv3ZevJ/view) and [spatial ledger](https://drive.google.com/file/d/17d7cFrohLGbtyLKBS_ZDvWvgURBqteeV/view).
- Small ledger snapshots and derived summaries are in [member-duc-benchmark](member-duc-benchmark/).
- Imported repository modules came from `dffd16a0b37df336330ef9b9d23056facd388681`. Additional model/runner code lives in the linked notebook. This documentation commit identifies the handoff separately from training code.
- Colab CPU, Intel Xeon at 2.20 GHz, 2 cores, Python 3.13.18. Resolved dependencies and configuration are preserved in `session.json`.

## Protocol

UrbanEV/SZH Development targets 1405, 2152, 1153 and 1693. Initial history is 14 days, with respectively 4, 12, 13 and 13 complete trainable examples. Source population is 65,888 examples. Each prediction uses 24 historical hours to forecast 24 hourly energy values. Neural transfer uses retention lambda 0.

Stochastic models use seeds 42, 43 and 44. Source training uses 3 epochs, batch 256 and learning rate 0.001, retaining the final checkpoint. Target adaptation uses 3 epochs, batch 4 and learning rate 0.0005, followed by one epoch per eligible arrived example. Ridge refits daily, tree models weekly, and SARIMA weekly over 336 hours. Graph initialization uses 5 epochs and learning rate 0.001.

The notebook implements separate target-only and transfer runs for MLP, GRU, LSTM, TCN and TimeXer. Source checkpoints are reused across targets for the same backbone and seed. Graph models use a geographical 16-node graph with four scored targets and three Development supports per target, and are reported separately.

Input manifest SHA-256 recorded by the run is `66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9`. Prepared ZIP SHA-256 is `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`. The saved notebook reports passing input checks. This handoff validates the exported ledgers and does not independently re-hash the external raw archives or every fitted artifact.

## Coverage

| Target | Scheduled | Issued | Scored |
|---|---:|---:|---:|
| 1405 | 90 | 90 | 89 |
| 2152 | 90 | 59 | 52 |
| 1153 | 90 | 59 | 52 |
| 1693 | 90 | 59 | 52 |

All successful rows match these counts. There are 245 scored station-origins per complete configuration/seed. Missing or unavailable days remain excluded according to the replay contract. Equal coverage counts across implementations do not independently verify the exact per-origin timestamp pairing.

## Aggregate results

Values are kWh. First average seeds within a station, then average the four stations equally. RMSE is averaged from station-level RMSE values. Lower is better.

| Model | Mode | Rows | MAE | RMSE |
|---|---|---:|---:|---:|
| daily_naive | target_only | 4 | 7.0757 | 9.5704 |
| gru | target_only | 12 | 8.9239 | 10.9727 |
| gru | transfer | 12 | 5.3157 | 7.1630 |
| lstm | target_only | 12 | 8.9565 | 11.0017 |
| lstm | transfer | 12 | 5.3168 | 7.1523 |
| mlp | target_only | 12 | 8.6855 | 10.7766 |
| mlp | transfer | 12 | 5.4753 | 7.3131 |
| random_forest | target_only | 12 | 5.8204 | 7.7012 |
| ridge | target_only | 4 | 5.9339 | 7.9213 |
| sarima | target_only | 4 | 6.6771 | 9.2030 |
| seasonal_naive | target_only | 4 | 8.4631 | 11.1458 |
| tcn | target_only | 12 | 7.8415 | 9.8784 |
| tcn | transfer | 12 | 5.3027 | 7.2046 |
| timexer | target_only | 12 | 7.0224 | 9.0077 |
| timexer | transfer | 12 | 5.1979 | 7.1556 |
| xgboost | target_only | 12 | 6.4613 | 8.8010 |

## Spatial comparator

| Model | Rows | MAE | RMSE |
|---|---:|---:|---:|
| GCN-LSTM | 12 | 7.1790 | 9.4164 |

The graph receives additional support-node histories. Its result is a separate spatial comparison.

## Station-level MAE

| Model | Mode | 1405 | 2152 | 1153 | 1693 |
|---|---|---:|---:|---:|---:|
| daily_naive | target_only | 6.9523 | 7.2482 | 11.1941 | 2.9083 |
| gru | target_only | 9.1836 | 10.3474 | 11.2262 | 4.9383 |
| gru | transfer | 6.0363 | 5.9443 | 6.9394 | 2.3427 |
| lstm | target_only | 9.5191 | 10.4865 | 10.9313 | 4.8890 |
| lstm | transfer | 6.0000 | 6.0495 | 6.8589 | 2.3590 |
| mlp | target_only | 9.1603 | 9.8799 | 10.8052 | 4.8965 |
| mlp | transfer | 5.9748 | 6.3159 | 7.2884 | 2.3220 |
| random_forest | target_only | 6.6124 | 6.0929 | 7.7088 | 2.8677 |
| ridge | target_only | 6.4952 | 6.3975 | 8.0155 | 2.8275 |
| sarima | target_only | 7.5352 | 6.2026 | 10.2170 | 2.7535 |
| seasonal_naive | target_only | 8.5471 | 8.1456 | 12.5791 | 4.5807 |
| tcn | target_only | 8.1942 | 8.1778 | 10.5097 | 4.4844 |
| tcn | transfer | 6.1368 | 6.0034 | 6.8217 | 2.2490 |
| timexer | target_only | 6.9865 | 6.8179 | 10.4056 | 3.8795 |
| timexer | transfer | 5.6639 | 5.7273 | 7.1190 | 2.2816 |
| xgboost | target_only | 7.4639 | 7.0682 | 8.2149 | 3.0982 |
| gcn_lstm | spatial | 8.2888 | 7.2108 | 9.7741 | 3.4422 |

## Comparison with Cyber v3

Cyber ledger Git blob identity is `3355870c5ff123255693b871d644b1ef9f388990`. Reference [Cyber v3 report](https://github.com/HungLD9505/adaptive-retention-ev/blob/feat/cyber-urbanev-baseline-benchmark/docs/reports/member-cyber-baselines.md). All 172 row keys and scheduled/issued/scored counts match. Differences below are Duc minus Cyber.

| Model | Mode | Duc MAE | Cyber MAE | Difference | Duc RMSE | Cyber RMSE |
|---|---|---:|---:|---:|---:|---:|
| daily_naive | target_only | 7.0757 | 7.0763 | -0.0006 | 9.5704 | 9.5713 |
| gru | target_only | 8.9239 | 8.9406 | -0.0168 | 10.9727 | 10.9920 |
| gru | transfer | 5.3157 | 5.3150 | 0.0007 | 7.1630 | 7.1238 |
| lstm | target_only | 8.9565 | 8.9360 | 0.0205 | 11.0017 | 10.9821 |
| lstm | transfer | 5.3168 | 5.3356 | -0.0187 | 7.1523 | 7.1980 |
| mlp | target_only | 8.6855 | 8.6711 | 0.0144 | 10.7766 | 10.7580 |
| mlp | transfer | 5.4753 | 5.5196 | -0.0444 | 7.3131 | 7.3081 |
| random_forest | target_only | 5.8204 | 5.8008 | 0.0196 | 7.7012 | 7.6669 |
| ridge | target_only | 5.9339 | 5.9339 | -0.0000 | 7.9213 | 7.9214 |
| sarima | target_only | 6.6771 | 6.5799 | 0.0972 | 9.2030 | 9.0473 |
| seasonal_naive | target_only | 8.4631 | 8.4631 | -0.0000 | 11.1458 | 11.1458 |
| tcn | target_only | 7.8415 | 8.0734 | -0.2318 | 9.8784 | 10.1041 |
| tcn | transfer | 5.3027 | 5.3447 | -0.0420 | 7.2046 | 7.2246 |
| timexer | target_only | 7.0224 | 8.1209 | -1.0986 | 9.0077 | 10.1265 |
| timexer | transfer | 5.1979 | 5.5823 | -0.3844 | 7.1556 | 7.5034 |
| xgboost | target_only | 6.4613 | 6.4847 | -0.0234 | 8.8010 | 8.7584 |
| gcn_lstm | spatial | 7.1790 | 7.1288 | 0.0502 | 9.4164 | 9.3308 |

TimeXer transfer has the lowest nominal MAE here (5.1979), while LSTM transfer has the lowest aggregate RMSE (7.1523). Cyber v3 ranks GRU transfer first on both. GRU transfer MAE is almost identical between runs (5.3157 versus 5.3150).

The notebook uses the pinned official TimeXer implementation at `76011909357972bd55a27adba2e1be994d81b327`, while Cyber documents a custom adapter with different tokenization and output head. The TimeXer comparison therefore includes architecture/adapter differences. Other independent implementation and environment differences also remain.

## Transfer benefit

| Backbone | Target-only MAE | Transfer MAE | Reduction (%) |
|---|---:|---:|---:|
| mlp | 8.6855 | 5.4753 | 36.96 |
| gru | 8.9239 | 5.3157 | 40.43 |
| lstm | 8.9565 | 5.3168 | 40.64 |
| tcn | 7.8415 | 5.3027 | 32.38 |
| timexer | 7.0224 | 5.1979 | 25.98 |

Transfer lowers seed-averaged MAE for every backbone at each of the four stations. Random Forest is the strongest target-only model by aggregate MAE. These findings are conditional on this previously inspected Development cohort. Model rank alone does not establish statistically significant superiority.

## Validation and remaining acceptance work

Ledger checks pass for 172 unique expected combinations, 160 non-spatial and 12 spatial rows, all statuses `ok`, empty error fields, finite nonnegative metrics, and expected coverage. Summary arithmetic is recomputed from full-precision exports. The final notebook cell reports `172/172 successful rows`.

The ledger retains measured Source, adaptation, inference, update/refit, replay and job-wall timers. Shared Source timings must be counted once per checkpoint identity, and nested timers must not be added to job-wall time. Runtime rankings against Cyber have not been normalized for hardware or timer boundaries.

Per-origin metric recomputation, paired uncertainty intervals, comprehensive external artifact/hash verification, parameter-count audit, pre-execution tuning/protocol agreement and independent peer review remain outstanding under #96. The fixed three-epoch Source schedule and absence of a demonstrated tuning search are disclosed. The report summarizes completed execution rather than closing all issue acceptance criteria.

README source listing, release checks, three unittest suites, Ruff lint/format and git diff checks were not executed on the current remote branch in this handoff. Local Git network access failed and the separate worktree could not be created. CI and peer review remain pending. No effectiveness conclusion is inferred from software checks.
