# Independent UrbanEV Baseline Benchmark — Pilot Handoff

**Owner** — Nguyễn Hữu Đức (@huuduc32)  
**Issue** — #96  
**Execution date** — 10 November 2026, Vietnam time (UTC+07:00)  
**Status** — Pilot complete, 17 successful result rows across 12 model families

## 1. Executive Summary & Scope

The pilot covers one UrbanEV Shenzhen Development target, station 2152, with a 14-day initial history budget and a 90-day replay. Stochastic models use seed 42. The pilot yielded 16 successful non-spatial rows and one successful GCN-LSTM row. Five neural backbones ran in both Target-only and Source → full fine-tuning modes.

TimeXer Transfer recorded the lowest pilot MAE and RMSE at 5.9383 kWh and 7.4540 kWh. GRU Transfer ranked third among the five transferred neural backbones by MAE and sixth among the 16 non-spatial configurations. GRU MAE fell from 8.7850 to 6.5227 kWh with Source initialization, a reduction of 25.75%. The complete benchmark has a separate 172-row execution requirement. The result archive reviewed for this handoff contains pilot sessions. [Issue #96][issue96] · [Pilot result archive][archive]

| Scope | Non-spatial rows | Spatial rows | Scored targets | Stochastic seeds |
|---|---:|---:|---|---|
| Observed pilot | 16 | 1 | 2152 | 42 |
| Required full benchmark | 160 | 12 | 1405, 2152, 1153, 1693 | 42, 43, 44 |

## 2. Experimental Invariants & Data Accounting

- **Prepared input** — UrbanEV/SZH, `urbanev-SZH-14d`, from the issue #18 handoff. The task uses the previous 24 hours to forecast the next 24 hourly energy values.
- **Source and target prefixes** — The prepared training file contains 65,888 Source examples. Independently counted initial Development examples are 4 for station 1405, 12 for 2152, 13 for 1153 and 13 for 1693. The pilot scores station 2152.
- **Inputs and targets** — The historical tensor is `[24, 7]`, the known future calendar is `[24, 5]` and the forecast has 24 hourly outputs. The runner converts normalized predictions to kWh using the target scale.
- **Coverage per successful pilot row** — 90 scheduled origins, 59 issued forecasts and 52 scored origins. The other 38 comprise 31 origins without usable history and seven issued forecasts without complete labels. These are station-origin counts per replay. The same calendar repeats across models. [Prepared inputs][data] · [Report 1][report1] · [Non-spatial pilot ledger][non] · [Spatial pilot ledger][spatial]

The runner saves the forecast for an origin, keeps it pending until the replay provider reports label availability, then scores and updates using complete labels. Run MAE averages hourly absolute errors over scored days. Run RMSE takes the square root of the mean of the corresponding squared errors. Every scored day contributes 24 hours. A row without scored forecasts has an undefined metric. [Pilot notebook][notebook]

## 3. Model Architecture & Protocol Definitions

| Model | Pilot implementation |
|---|---|
| Daily Naive | Same hour of the previous day. Falls back to the mean of known history and then zero when history is empty. |
| Seasonal Naive | Repository implementation. Uses weekly lag, then daily lag, then historical mean and a final zero fallback. |
| Ridge Regression | Direct 24-output ridge on 288 flattened features, with alpha 1.0. |
| SARIMA | Seasonal period of 24 hours. Selects a converged initial candidate by AIC from two fixed order pairs. Fits with at most 30 iterations, preserves missing hours as `NaN` and filters through the current forecast origin with the latest fitted parameters. |
| Random Forest | Direct 24-output regression with 100 trees and maximum depth 4. |
| XGBoost | 24 single-output estimators through `MultiOutputRegressor`. Each uses 50 boosting rounds, depth 2, learning rate 0.05 and subsample 0.8. |
| MLP/FCNN | Two width-64 fully connected layers over flattened historical features, followed by a calendar-conditioned forecast head. |
| GRU | Repository `ForecastGRU`, with two recurrent layers of width 64 and a calendar-conditioned forecast head. |
| LSTM | Two width-64 recurrent layers followed by a calendar-conditioned forecast head. |
| TCN | Four causal residual blocks with kernel size 3 and dilations 1, 2, 4 and 8. |
| TimeXer | Official implementation pinned to `76011909357972bd55a27adba2e1be994d81b327`. The adapter moves energy to the final historical channel for MS mode and passes the known future calendar through the auxiliary embedding input. It uses a six-hour patch, model width 32, four heads and one encoder layer. |
| Basic GCN-LSTM | Fixed symmetric nearest-neighbor graph with self-loops, a 32-channel graph projection and a width-64 LSTM. Each graph node receives its own history. |

The pilot pretrains each neural backbone for one Source epoch with batch size 128. Target-only starts from random weights. Transfer loads the matching Source checkpoint and initializes a fresh target optimizer. Both use three initial target epochs with batch size 16 and one online epoch per arrived eligible example. Neural training uses Adam and normalized MAE with retention weight zero. Ridge, SARIMA, Random Forest and XGBoost attempt refits on a seven-day calendar cadence when new eligible labels exist. SARIMA retains the previous parameters when a refit fails to produce a converged finite candidate. [Pilot notebook][notebook] · [TimeXer reference implementation][timexer]

## 4. Comprehensive Pilot Results

### 4.1 Non-Spatial Matrix

Every row below is from station 2152 and has coverage 90 scheduled, 59 issued and 52 scored. A dash in the parameters column denotes a count absent from the ledger.

| Model | Mode | Seed | MAE (kWh) | RMSE (kWh) | Trainable parameters |
|---|---|---:|---:|---:|---:|
| Daily Naive | Target-only | — | 7.2482 | 9.7305 | — |
| Seasonal Naive | Target-only | — | 8.1456 | 10.4666 | — |
| Ridge Regression | Target-only | — | 6.6215 | 8.6842 | — |
| SARIMA | Target-only | — | 5.9782 | 7.5876 | — |
| Random Forest | Target-only | 42 | 6.0771 | 7.4931 | — |
| XGBoost | Target-only | 42 | 6.4160 | 8.0586 | — |
| MLP/FCNN | Target-only | 42 | 8.5567 | 10.9862 | 28,376 |
| MLP/FCNN | Source → full fine-tuning | 42 | 6.9752 | 8.6037 | 28,376 |
| GRU | Target-only | 42 | 8.7850 | 11.2174 | 52,376 |
| GRU | Source → full fine-tuning | 42 | 6.5227 | 8.1727 | 52,376 |
| LSTM | Target-only | 42 | 8.9654 | 11.4182 | 65,368 |
| LSTM | Source → full fine-tuning | 42 | 6.2123 | 7.7583 | 65,368 |
| TCN | Target-only | 42 | 7.8394 | 9.9985 | 52,376 |
| TCN | Source → full fine-tuning | 42 | 6.8743 | 8.7370 | 52,376 |
| TimeXer | Target-only | 42 | 6.9432 | 9.0518 | 17,784 |
| TimeXer | Source → full fine-tuning | 42 | 5.9383 | 7.4540 | 17,784 |

[Non-spatial pilot ledger][non]

### 4.2 Transfer Benefit Within Each Backbone

| Backbone | Target-only MAE (kWh) | Transfer MAE (kWh) | MAE reduction |
|---|---:|---:|---:|
| MLP/FCNN | 8.5567 | 6.9752 | 18.48% |
| GRU | 8.7850 | 6.5227 | 25.75% |
| LSTM | 8.9654 | 6.2123 | 30.71% |
| TCN | 7.8394 | 6.8743 | 12.31% |
| TimeXer | 6.9432 | 5.9383 | 14.47% |

These are differences between the reported pilot aggregates. Each pair has the same station, seed and scored-day count. Matching the exact scored origins from the per-day artifacts is part of the full verification handoff. [Non-spatial pilot ledger][non]

### 4.3 Backbone Choice

Within Transfer, the MAE order was TimeXer, LSTM, GRU, TCN and MLP/FCNN. GRU was 0.5844 kWh behind TimeXer and 0.3104 kWh behind LSTM in this pilot. The strongest Target-only non-spatial MAE was SARIMA at 5.9782 kWh. Random Forest had the strongest Target-only RMSE at 7.4931 kWh. The pilot establishes a single-station, single-seed reference. The full comparison will aggregate seeds within each station, then give stations equal weight and compare matched forecasts on common scored origins. [Non-spatial pilot ledger][non] · [Issue #96][issue96]

## 5. Spatial Comparator — Basic GCN-LSTM

| Run ID | Scored target | Seed | Shared initial graph days | Scheduled / issued / scored | MAE (kWh) | RMSE (kWh) | Trainable parameters |
|---|---|---:|---:|---|---:|---:|---:|
| `gcn_lstm-spatial-graph-42-7f8af8` | 2152 | 42 | 4 | 90 / 59 / 52 | 9.2731 | 11.7108 | 38,744 |

The graph combines the four designated targets with configured Development support stations. The pilot scores and supervises station 2152. The initialization window is the intersection of eligible prefix origins across graph nodes. The successful run folder includes `graph.json` with the graph definition, coordinate provenance and checksum. Full benchmark configuration will record the exact nodes, edge rule and history allowance before execution. [Spatial pilot ledger][spatial] · [Successful spatial run][graph_run]

## 6. Execution Costs & Runtime Boundaries

Reported times are in seconds. A dash denotes an inapplicable Source phase. Job wall time includes work within the job boundary such as data loading and initialization. It overlaps the component columns and varies with cache state. Full-suite wall time was not captured in the reviewed ledgers.

| Model | Mode | Source train | Initial fit or adaptation | Inference | Online update or refit | Job wall |
|---|---|---:|---:|---:|---:|---:|
| Daily Naive | Target-only | — | 0.000 | 0.324 | 0.020 | 2.060 |
| Seasonal Naive | Target-only | — | 0.000 | 0.270 | 0.020 | 1.863 |
| Ridge Regression | Target-only | — | 2.730 | 0.045 | 0.110 | 3.837 |
| SARIMA | Target-only | — | 6.590 | 53.988 | 106.854 | 168.225 |
| Random Forest | Target-only | — | 0.378 | 3.097 | 5.073 | 9.928 |
| XGBoost | Target-only | — | 2.700 | 4.098 | 11.958 | 19.886 |
| MLP/FCNN | Target-only | — | 11.850 | 0.037 | 0.272 | 12.755 |
| MLP/FCNN | Transfer | 3.193 | 0.020 | 0.033 | 0.192 | 74.262 |
| GRU | Target-only | — | 0.083 | 0.165 | 1.010 | 1.868 |
| GRU | Transfer | 31.701 | 0.072 | 0.163 | 1.028 | 33.614 |
| LSTM | Target-only | — | 0.054 | 0.087 | 0.361 | 1.099 |
| LSTM | Transfer | 28.765 | 0.063 | 0.087 | 0.372 | 29.901 |
| TCN | Target-only | — | 0.167 | 0.119 | 0.363 | 1.178 |
| TCN | Transfer | 24.450 | 0.036 | 0.129 | 0.380 | 25.626 |
| TimeXer | Target-only | — | 1.740 | 0.140 | 0.553 | 3.005 |
| TimeXer | Transfer | 12.461 | 0.066 | 0.161 | 0.546 | 13.871 |
| Basic GCN-LSTM | Spatial | — | 0.089 | 0.095 | 0.351 | 27.641 |

The largest recorded process peak RSS was 2,335,984 KiB, approximately 2.23 GiB. This is the process high-water mark since kernel start, including cached data and prior work. CUDA peak allocation was blank in the reviewed ledgers. The session metadata captures the runtime and resolved packages. Exact hardware and package versions should be transcribed from that metadata for the full handoff. Source costs in the full benchmark should be counted once per backbone and seed, and shared spatial job costs once per seed. [Non-spatial pilot ledger][non] · [Spatial pilot ledger][spatial] · [Pilot session metadata][session]

## 7. Adverse Findings, Null Cases & Scientific Limitations

| Run ID | Outcome | Interpretation |
|---|---|---|
| `gcn_lstm-spatial-graph-42-be23e7` | Graph CSV, lineage or support IDs were missing. | Setup stopped before any forecasts. MAE and RMSE remained undefined. |
| `gcn_lstm-spatial-graph-42-77a671` | A graph node configuration value was an integer where an iterable was required. | Setup stopped before any forecasts. MAE and RMSE remained undefined. |
| `gcn_lstm-spatial-graph-42-7f8af8` | Retry succeeded. | Scored 52 origins and retained the earlier failure records separately. |

The 52 scored origins on one Development station provide a pilot estimate. Seed variation and cross-station performance remain to be measured. Timing includes warm-up, cached input and I/O effects. The pilot leaderboard gives descriptive comparisons within this setting. [First graph failure][failed1] · [Second graph failure][failed2] · [Spatial pilot ledger][spatial]

## 8. Artifact Provenance & SHA-256 Checksums

| Artifact or identity | Reference |
|---|---|
| Upstream source-module commit | `dffd16a0b37df336330ef9b9d23056facd388681` |
| Reviewed notebook snapshot SHA-256 | `ab9ba7aea2c24d1459810b6704e3c0be9724ade6c16df0d9b1deeaccc139c622` |
| Prepared ZIP SHA-256 | `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7` |
| 14-day input manifest SHA-256 | `66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9` |
| Successful non-spatial pilot session | [`pilot-20261110-155423-3cec4d`][non_folder] |
| Successful spatial retry session | [`pilot-20261110-164710-e9831b`][spatial_folder] |

The reviewed notebook SHA identifies the downloaded reference snapshot. Any Colab edits need their own exported snapshot or execution commit before the full benchmark. The prepared ZIP and manifest were independently hashed, and all five manifest-listed artifacts were checked against their byte sizes and SHA-256 values.

The pilot run directories retain forecast and label events in `daily.jsonl`, result summaries, fitted estimators or checkpoints and per-run checksum files. Source trajectories retain checkpoint files and source metadata. A consolidated bundle hash and reviewer read access remain to be verified. [Pilot notebook][notebook] · [Pilot result archive][archive]

## 9. Quality Gates & Acceptance Verification

| Check | Status at pilot handoff |
|---|---|
| Prepared ZIP, embedded manifest, input file hashes and Source/target prefix counts | Verified independently against the prepared snapshot. |
| Pilot model coverage | Verified 17 successful rows across all 12 families. Two failed graph attempts remain recorded separately. |
| Independent metric reproduction | Replayed Daily Naive on 2152 using the reviewed notebook and prepared data. Recomputed MAE 7.248197165327 kWh and RMSE 9.730496605799 kWh from the emitted hourly forecasts and labels, with coverage 90/59/52. The replay check confirmed that a saved forecast preceded scoring and that every scored label was available at the recorded scoring time. |
| Remaining pilot prediction and checkpoint readback | Pending. Reported metrics are transcribed from the successful ledgers. |
| Protocol lock and full benchmark | Pending. Lock tuning and checkpoint rules, refit settings, graph configuration and executable code identity, then record the 172 full benchmark rows under separate run IDs. |
| Regression fixtures and repository checks | Pending for the #96 handoff. Include delayed arrivals, undefined metrics for zero-score runs, SARIMA gaps and a graph fixture with distinct histories at two nodes. Record README checks on the versioned branch. |
| Final evidence and peer review | Pending. Recompute metrics from accessible artifacts, summarize by station and seed, include paired common-origin results and publish the reviewed bundle. |

The pilot conclusions and checklist use the reporting structure of Cyber's handoff and the verification priorities from Qyroven's review of PR #104. [Cyber report][cyber] · [Qyroven review][review] · [Issue #96][issue96]

[issue96]: https://github.com/HungLD9505/adaptive-retention-ev/issues/96
[archive]: https://drive.google.com/drive/folders/1rqfGBYcMDevQBmpA-yR17kgy-K23Hg7U
[data]: https://drive.google.com/file/d/17pfYqnnSq0Uao2zDNdb8h7GAYfotu_w4/view
[report1]: https://github.com/HungLD9505/adaptive-retention-ev/blob/dffd16a0b37df336330ef9b9d23056facd388681/adaptive_retention_report_1.pdf
[notebook]: https://chatgpt.com/library?file_id=libfile_a8a88f1d3a8881918c97e7d230cb3561&account_id=personal
[non]: https://drive.google.com/file/d/1qZWHtLS61pJgyTJlykwYVZLG8TTpb2Bw/view
[spatial]: https://drive.google.com/file/d/1GghUP-l5VLyG5chnSnXpabtvIMpmhkdA/view
[non_folder]: https://drive.google.com/drive/folders/1gMj28h_lIF3mSzPvyTbH7CyWXZril9BT
[spatial_folder]: https://drive.google.com/drive/folders/1iWc1VGRg5sX6nLmFg0NsmhieSccqazq0
[graph_run]: https://drive.google.com/drive/folders/14H_yeAkBPHZSi8jgsqa7F9nNPs8A0R6E
[session]: https://drive.google.com/file/d/1pximbSrLK1wNVnZhgpQuFhN6PGH1BDqd/view
[failed1]: https://drive.google.com/file/d/13MoqQQYa9Rq399z9cJ06Yru6L7CDkO75/view
[failed2]: https://drive.google.com/file/d/1cR-eatc1kVUBeP5pgw7nQ6WYA2IzQtyf/view
[timexer]: https://github.com/thuml/TimeXer/blob/76011909357972bd55a27adba2e1be994d81b327/models/TimeXer.py
[cyber]: https://github.com/HungLD9505/adaptive-retention-ev/blob/5f67bd225f0fe340393a6d73bcc03363144d2561/docs/reports/member-cyber-baselines.md
[review]: https://github.com/HungLD9505/adaptive-retention-ev/pull/104#pullrequestreview-5838725837
