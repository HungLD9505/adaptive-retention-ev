# Cyber UrbanEV Baseline Benchmark Report (Issue #95)

**Author:** Trần Mạnh Hùng (`@hung00cyber`)
**Issue / PR:** #95 / #104 (`HungLD9505/adaptive-retention-ev`), branch `feat/cyber-urbanev-baseline-benchmark`
**Revision:** v3 evidence (second response to the PR #104 review of commit `5f67bd2`, `@Qyroven`), plus an 11 November 2026 documentation revision: custom-TimeXer labelling, #95/#96 protocol reconciliation and a proposed scope disposition (§12–§13). No result, artifact or executed-code byte changed in that revision.
**Execution:** 10 November 2026 (Asia/Ho_Chi_Minh), run tag `v3`, local CPU (details in §8)
**Status:** Revised evidence submitted for peer review. **Not self-declared Done**; #95 stays open until the lead's scope decision (§13), final peer approval, merge into `dev` and verification on `dev`.

> **Naming note.** The model recorded as `timexer` / `TimeXer` in the ledger, run IDs and artifacts is a **custom TimeXer-style cross-attention adapter** (§3.4), not the reference TimeXer. In this report it is labelled **"TimeXer-style adapter (custom)"**. Ledger values and run IDs are kept unchanged to preserve the historical identity of the executed rows.

This is an additional, exploratory **Development** study on four historically scoreable UrbanEV/SZH targets. It is not Final evidence, not a fresh held-out selection and not population-wide proof.

---

## 1. What changed in v3 and why

The first review response (v2, commit `553275a`) addressed the review findings only partly and introduced a new defect. v3 fixes the code, reruns **all 172 rows** under new run IDs (`cyber_v3_*`) and a new output root (`artifacts_v3/`, `runs_v3.csv`), and preserves v1 and v2 unchanged (§9).

| Review finding | v2 state (`553275a`) | v3 fix | Evidence |
|---|---|---|---|
| Label-arrival guard | Clock gate added, but labels were applied **after** the next prediction. Every real label arrives exactly at origin + 24 h, so every learner was delayed by one extra day. All 136 learner rows changed versus v1. | `runner.py` scores and updates every label that has fully arrived (`all 24 available_at <= as_of`) **before** predicting the current origin. The forecast for an origin is still saved before its own label exists. | Tests `test_label_arriving_at_next_origin_is_used_before_that_prediction`, `test_label_arriving_one_hour_after_next_origin_is_not_used`, `test_delayed_label_arrival_guard`; v1/v2/v3 comparison in §6 |
| Zero-score metrics | Fixed (null MAE/RMSE plus reason) | Kept; `verify_results` also rejects metrics on unscored origins | `test_zero_scored_runs_handling` |
| SARIMA state/horizon/gaps | `predict()` mutated the state with NaN gaps; the next `update()` then hit an overlapping index and failed silently, freezing the state until the weekly refit (v2 SARIMA MAE 12.88) | Regular hourly index. `predict()` is read-only and forecasts from the end of the filtered state to the origin's horizon (last 24 of `steps`). Daily `append(refit=False)` with NaN gaps. Weekly refit on the last 336 h. Fit/advance failures and fallback forecasts are counted and exported. | Three SARIMA regression tests. v3 diagnostics: 37 fits, **0** fit failures, **0** advance failures, **0** fallback forecasts across the 4 rows |
| Graph inputs | Distinct histories, but the graph contained **only the four targets**, which #95 rules out ("four targets are scored nodes, not an instruction to build a four-node graph"). Missing lookups silently became zeros. | Locked node rule (§3.3): 4 targets + 3 nearest Development-role supports each (16 nodes). Final/Source stations excluded. Supports contribute only their origin-time `x_hist`. Missing support histories are counted. | `graph_lock.json`, `test_graph_node_selection_uses_nearest_development_supports`, `test_gcn_lstm_reads_support_histories_from_lookup` |
| Byte-level hashing | Fixed (binary LF writes) | Kept. Manifest keys are repo-relative paths. The verifier fails on any CRLF text artifact. | `test_binary_hash_contract`; §9 verification |
| Artifact handoff | Release `v0.9.5-cyber-benchmark-v2` holds v2 outputs only. No fitted target estimators; manifest built from flawed v2 runs. | All 172 end-of-replay fitted target states saved (`fitted/`). Environment, code SHA-256s, input hashes, execution log, graph lock, pilot record and readback tables are in one manifest (367 entries). v3 bundle published as release `v0.9.5-cyber-benchmark-v3` (§9). | `artifacts_v3/manifest.json` |
| Overwriting evidence | `--all` deleted `runs.csv` before running | `--all` refuses to run if the run tag already has a ledger or forecasts | `test_full_benchmark_refuses_to_overwrite_existing_ledger` |
| Statistical claims | Pooled t-tests over 245 station-origins (ignoring serial and station dependence). Differences disagreed with the summary table. SD range excluded TimeXer. "Necessary / if and only if" wording. | Station-first paired common-origin differences with a 7-day moving-block bootstrap within each station. Claims restated as conditional Development evidence (§4–5). | `readback/paired_differences.csv` |

---

## 2. Inputs and accounting

- **Input root:** `data/inputs/issue18-input-handoff-v1-20261019/urbanev-SZH-14d/`.
- **Input files:** SHA-256 recomputed on 10 Nov 2026. All five data files match the hashes recorded in the input's own `manifest.json`:

| File | SHA-256 |
|---|---|
| `training.jsonl` | `eadb4bb38d0e3dce1eded428ba4d806346cefc4e09840fa65814670edfd0999c` |
| `forecasts.jsonl` | `d67ba54632b850bf183bc6f0df345f0de060a3907a11e27ef01c9b75edfcb6e8` |
| `labels.jsonl` | `64707cfe755767e0e0b76bab8bb6066bab5a60acef8b30133c573c8cf659015f` |
| `schedule.jsonl` | `eaa88e7e861eb5d70d42b1c0e114de5fff1a3b621a78d635613e278151de143e` |
| `entities.jsonl` | `e7c9dd4cb0b6f95cdfb1a0939fcadbc69edd1af6e9fb0fa30c861c4d7a38953e` |
| `manifest.json` | `66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9` |

  **Correction:** the hash `0efdfaa7…` posted in the earlier #95 update does not match these bytes, and its origin cannot be traced. The value above replaces it.

  **Not verified:** the distribution ZIP (catalog `DATA-v1-20261019.json`, SHA-256 `2b8d1a47…`) was not re-downloaded or re-hashed for v3. Only the extracted files present locally were checked.
- **Source population:** 65,888 Source examples (`role == "source"` in `training.jsonl`), no truncation.
- **Targets and initial budgets:** 14-day prefix; trainable counts 1405 = 4, 2152 = 12, 1153 = 13, 1693 = 13; p95 scales 43.867 / 42.0 / 56.0 / 14.0 kWh.
- **Calendar:** 90 scheduled origins per target (360 in total).
  - Issued: 267 (1405: 90; 2152/1153/1693: 59 each, with 31 `skipped_all_missing_history`).
  - Scored: 245 (1405: 89; others: 52 each).
  - Unscored: 115 nulls (93 missing history + 22 incomplete labels).
  - Every row has identical coverage, so all models are compared on the same origins.
- **Label timing:** in all 57,330 label records, the last `available_at` is exactly origin + 24 h.

---

## 3. Protocol and model definitions (as executed in v3)

### 3.1 Information boundaries
- Predictors see `x_hist` [24×7] (energy, hour/day encodings, validity) and `c_future` [24×5] (known calendar) only.
- Labels are decoded only when they have fully arrived; scoring uses original kWh.
- Tree and linear models use the same 288 flattened values.

### 3.2 Model configurations (`config.py`, run tag v3)

| Model | Configuration |
|---|---|
| Daily Naive | Same hour of the previous day from `x_hist`; masked → history mean → 0 |
| Seasonal Naive | 168 h lag → 24 h lag → history mean → 0 (fallback counts exported) |
| Ridge | α = 1.0, multi-output, refit after every arrived complete day (expanding window), clipped at 0 |
| SARIMA | SARIMAX(1,0,1)(1,0,0)₂₄, `maxiter = 15`, weekly refit on the last 336 h; see §1 |
| Random Forest | 100 trees, depth 10, weekly expanding refit, seeds 42/43/44 |
| XGBoost | 50 trees, depth 5, learning rate 0.1, weekly expanding refit, seeds 42/43/44. **XGBoost is deterministic for this configuration (no row/column subsampling): the three seeds give identical forecasts.** |
| Neural (MLP/GRU/LSTM/TCN/TimeXer-style adapter (custom)) | Normalized-MAE objective, λ = 0.<br>Source: Adam, lr 1e-3, batch 256, **3 epochs**, last-epoch checkpoint.<br>Target: 3 adaptation epochs (lr 5e-4, batch 4), then 1 update epoch per arrived complete day.<br>Target-only starts from random seeded weights; transfer starts from the matching backbone/seed Source checkpoint with a fresh optimizer. |

**Configuration history, disclosed:**
1. **v1 config differed from the v1 report.** The v1 rows were executed with XGBoost `n_estimators = 100` and SARIMA `maxiter = 25` (commits `eac4ecc`/`5f67bd2`), while the v1 report stated 50 and 15. Commit `553275a` changed the code to 50/15. v2 and v3 executed with 50/15. This was a post-hoc change to match the report text, not a tuning outcome.
2. **Deviations from the #95 starting recipe:**
   - Source training uses 3 epochs with only the final checkpoint, not "up to 10 epochs with checkpoints at 1/3/10".
   - No hyperparameter tuning was run for any model. All settings were fixed by the author before the v1 execution.
   - No pre-execution protocol-lock record exists, and none has been reconstructed retrospectively.
   - Selection and evaluation both use these known Development targets.

### 3.3 Basic GCN-LSTM node/edge lock (`artifacts_v3/graph_lock.json`)
- **Nodes (16):** the 4 scored targets plus, for each target, the 3 nearest **Development-role** stations in `station_distance.csv` (raw UrbanEV ZIP). Final-role and Source-role stations are excluded.

| Target | Support nodes (distance) |
|---|---|
| 1405 | 1398 (659 m), 1439 (799 m), 1417 (869 m) |
| 2152 | 2153 (0 m, co-located), 2120 (639 m), 2173 (877 m) |
| 1153 | 1140 (342 m), 1169 (426 m), 1165 (482 m) |
| 1693 | 1723 (758 m), 1836 (2,431 m), 1810 (2,523 m) |

- **Edges:** Gaussian kernel `exp(-(d/σ)²)`, with σ = SD of positive pairwise distances among the 16 nodes, plus self-loops, symmetric-normalized.
- **Node inputs:**
  - The target node uses its own `x_hist`.
  - Each support node uses its own `x_hist` at the same origin, which is available at that origin by construction.
  - Support labels are never decoded or trained on.
  - A missing support history is all-zero, including the validity channel. This applied to **5,490 of 32,490 support lookups (16.9 %)**, mainly the supports' own `skipped_all_missing_history` days.
- **Training:** one model per target/seed, trained only on that target's prefix and arrived labels; no Source graph, no transfer.
- **Network:** GCN (7→32) per hour → LSTM (64) on the target node → calendar head; 38,744 parameters.

### 3.4 TimeXer-style adapter (custom) vs the reference TimeXer
**Label used from here on: "TimeXer-style adapter (custom)"** (ledger/run-ID name: `timexer`). These 24 rows evaluate a custom cross-attention adapter. They do **not** complete the named reference TimeXer baseline of #95 unless the lead explicitly accepts the substitution (§13, decision D2).

The adapter keeps TimeXer's core idea (endogenous tokens querying exogenous tokens through cross-attention) but differs from the [official implementation](https://github.com/thuml/TimeXer) in the following ways:
1. **Tokens:** one token per hour (24 endogenous tokens from a linear 7→64 projection), not patch tokens. The v2 report's "linear series patching" description was wrong.
2. **No global token:** there is no learnable global endogenous token.
3. **Exogenous tokens:** the 5 calendar features are embedded per future hour (24 tokens), not as variate-level series tokens.
4. **Positional embedding and pooling:** a single positional embedding is shared by both token sets, and the output is a mean-pooled endogenous representation concatenated with the flattened calendar into an MLP head (Softplus).
5. **Size and comparison:** one block, 4 heads, D = 64. Results are for this adapter, not a reproduction of published TimeXer.

For contrast, #96 (`@huuduc32`) ran the official implementation pinned at `76011909357972bd55a27adba2e1be994d81b327` (patch length 6, width 32, 4 heads, one encoder). The two `TimeXer` results are therefore materially different models (§12).

---

## 4. Results — non-graph matrix (160 rows)

All MAE/RMSE values are in kWh, **station-first**: the mean over seeds within a station, then the unweighted mean over the 4 stations. Each row is scored on 245 common origins. Source: `readback/station_first_summary.csv`.

| Model | Mode | Rows | MAE | RMSE | Params |
|---|---|---:|---:|---:|---:|
| Daily Naive | Target-only | 4 | 7.0763 | 9.5713 | 0 |
| Seasonal Naive | Target-only | 4 | 8.4631 | 11.1458 | 0 |
| Ridge | Target-only | 4 | 5.9339 | 7.9214 | 6,936 |
| SARIMA | Target-only | 4 | 6.5799 | 9.0473 | 4 |
| Random Forest | Target-only | 12 | 5.8008 | 7.6669 | 204,700 (node bound) |
| XGBoost | Target-only | 12 | 6.4847 | 8.7584 | 3,150 (node bound) |
| MLP | Target-only | 12 | 8.6711 | 10.7580 | 43,288 |
| MLP | Transfer | 12 | 5.5196 | 7.3081 | 43,288 |
| GRU | Target-only | 12 | 8.9406 | 10.9920 | 52,376 |
| GRU | Transfer | 12 | 5.3150 | 7.1238 | 52,376 |
| LSTM | Target-only | 12 | 8.9360 | 10.9821 | 65,368 |
| LSTM | Transfer | 12 | 5.3356 | 7.1980 | 65,368 |
| TCN | Target-only | 12 | 8.0734 | 10.1041 | 77,080 |
| TCN | Transfer | 12 | 5.3447 | 7.2246 | 77,080 |
| TimeXer-style adapter (custom) | Target-only | 12 | 8.1209 | 10.1265 | 66,072 |
| TimeXer-style adapter (custom) | Transfer | 12 | 5.5823 | 7.5034 | 66,072 |

### 4.1 Station breakdown (MAE, kWh)

| Model | Mode | 1153 | 1405 | 1693 | 2152 |
|---|---|---:|---:|---:|---:|
| Daily Naive | Target-only | 11.1941 | 6.9545 | 2.9083 | 7.2482 |
| Seasonal Naive | Target-only | 12.5791 | 8.5471 | 4.5807 | 8.1456 |
| Ridge | Target-only | 8.0154 | 6.4952 | 2.8275 | 6.3975 |
| SARIMA | Target-only | 9.5332 | 7.5622 | 2.7450 | 6.4791 |
| Random Forest | Target-only | 7.7293 | 6.5237 | 2.8634 | 6.0867 |
| XGBoost | Target-only | 8.4153 | 7.2621 | 3.1350 | 7.1265 |
| MLP | Target-only | 10.8564 | 9.1603 | 4.8879 | 9.7797 |
| MLP | Transfer | 7.4025 | 6.0169 | 2.4219 | 6.2373 |
| GRU | Target-only | 11.2578 | 9.1836 | 4.9203 | 10.4007 |
| GRU | Transfer | 6.9232 | 6.0020 | 2.3914 | 5.9435 |
| LSTM | Target-only | 10.8937 | 9.5191 | 4.8728 | 10.4583 |
| LSTM | Transfer | 6.8540 | 5.9732 | 2.4183 | 6.0968 |
| TCN | Target-only | 10.4311 | 8.7457 | 4.6928 | 8.4239 |
| TCN | Transfer | 6.9476 | 6.0806 | 2.4889 | 5.8617 |
| TimeXer-style adapter (custom) | Target-only | 10.4671 | 8.4389 | 4.7008 | 8.8770 |
| TimeXer-style adapter (custom) | Transfer | 7.2402 | 6.5018 | 2.4465 | 6.1407 |

### 4.2 Paired common-origin analysis

For each pair, the per-origin difference in seed-averaged daily MAE (comparator minus reference) is computed on origins scored by both. It is averaged within each station, then across the 4 stations.

The 95 % interval is a 7-day moving-block bootstrap within each station (10,000 replicates, rng seed 20261110). Stations are held fixed: with four Development targets, between-station uncertainty is **not** estimable and is not included. Intervals therefore describe the uncertainty over origins for **these four stations only**. An interval containing 0 shows only that this study cannot separate the two models; it is not evidence of equivalence.

**Transfer benefit within each backbone** (target-only minus transfer; positive = transfer better):

| Backbone | Δ MAE | 95 % CI | Stations favouring transfer |
|---|---:|---|---:|
| MLP | +3.151 | [+2.315, +3.854] | 4/4 |
| GRU | +3.626 | [+2.731, +4.369] | 4/4 |
| LSTM | +3.600 | [+2.706, +4.389] | 4/4 |
| TCN | +2.729 | [+2.000, +3.309] | 4/4 |
| TimeXer-style adapter (custom) | +2.539 | [+1.702, +3.135] | 4/4 |

**Matched backbones and other baselines vs GRU transfer** (comparator minus GRU transfer; positive = GRU transfer lower MAE):

| Comparator | Δ MAE | 95 % CI | Stations favouring GRU transfer |
|---|---:|---|---:|
| LSTM transfer | +0.021 | [−0.076, +0.107] | 2/4 |
| TCN transfer | +0.030 | [−0.128, +0.135] | 3/4 |
| MLP transfer | +0.205 | [+0.009, +0.382] | 4/4 |
| TimeXer-style adapter (custom) transfer | +0.267 | [+0.098, +0.452] | 4/4 |
| Random Forest target-only | +0.486 | [+0.086, +0.834] | 4/4 |
| Ridge target-only | +0.619 | [+0.124, +0.886] | 4/4 |
| XGBoost target-only | +1.170 | [+0.716, +1.519] | 4/4 |
| SARIMA target-only | +1.265 | [+0.812, +1.738] | 4/4 |
| Daily Naive target-only | +1.761 | [+1.386, +2.249] | 4/4 |
| Basic GCN-LSTM target-only (spatial, §5) | +1.814 | [+1.287, +2.280] | 4/4 |
| Seasonal Naive target-only | +3.148 | [+2.592, +3.669] | 4/4 |

### 4.3 Interpretation (conditional Development evidence)
- **Transfer benefit:** on these four targets, Source initialization lowered MAE for every backbone, at every station, by 2.5–3.6 kWh (about 31–41 %).
- **Backbone choice under transfer:**
  - GRU has the lowest nominal MAE, but this study cannot separate it from LSTM or TCN (intervals include 0; LSTM is lower than GRU at 2 of 4 stations).
  - MLP and TimeXer-style adapter (custom) transfer are higher than GRU at all four stations. The MLP interval's lower bound (+0.009) is close to 0.
  - **No GRU superiority claim is made.**
- **Classical vs neural:** among target-only models, Random Forest (5.80) and Ridge (5.93) are lowest, and every target-only neural model is higher (8.07–8.94).
  - The GRU-transfer vs Random-Forest gap mixes architecture, Source data and training regime, so it says nothing about architecture alone (#95).
  - This study does not establish that transfer is *necessary* for neural models to beat classical baselines in general. That claim from v2 is withdrawn.

### 4.4 Seed variability (`readback/seed_variability.csv`)

Sample SD (n = 3) of the seed-level station-first MAE, in kWh:

| Model | Target-only SD | Transfer SD |
|---|---:|---:|
| MLP | 0.128 | 0.096 |
| GRU | 0.447 | 0.061 |
| LSTM | 0.201 | 0.057 |
| TCN | 0.092 | 0.067 |
| TimeXer-style adapter (custom) | 0.218 | 0.205 |
| Random Forest | 0.007 | — |
| XGBoost | 0.000 (deterministic) | — |
| Basic GCN-LSTM | 0.116 | — |

The transfer-mode SD range is **0.057–0.205 kWh**, which includes the TimeXer-style adapter (custom) (0.205). With n = 3, these SDs are imprecise.

---

## 5. Spatial comparator — Basic GCN-LSTM (12 rows, reported separately)

| Station | Seed 42 | Seed 43 | Seed 44 | Mean MAE |
|---|---:|---:|---:|---:|
| 1153 | 9.7551 | 9.8535 | 9.6599 | 9.7562 |
| 1405 | 8.0528 | 7.9101 | 7.7266 | 7.8965 |
| 1693 | 3.4484 | 3.4642 | 3.5336 | 3.4820 |
| 2152 | 7.5781 | 7.5031 | 7.0608 | 7.3806 |
| **Station-first** | 7.2086 | 7.1827 | 6.9952 | **7.1288** (RMSE 9.3308) |

- The graph model uses extra spatial information (support-node histories) that the non-graph models do not receive, so it is not part of the backbone comparison.
- Its MAE (7.13) is lower than the target-only recurrent/MLP networks (8.67–8.94) in this study, but higher than Ridge, Random Forest, SARIMA and Daily Naive. It is 1.81 kWh above GRU transfer (CI [+1.29, +2.28]).
- No paired test of graph vs target-only neural models was run. This report makes no causal claim that spatial message passing improves forecasts, and the v2 "significantly outperforming" wording is withdrawn.
- Results depend on the locked K = 3 rule and the zero-masking of 16.9 % of support histories.

---

## 6. Arrival-guard demonstration: did the historical scores change?

Comparison of all 172 rows by model/mode/station/seed, ignoring the run-tag prefix (`historical_v1/runs_v1.csv`, `historical_v2/runs_v2.csv`, `runs_v3.csv`):

| Model group | Rows | v3 = v1 (exact, 6 d.p.) | v3 = v2 | Max \|v2 − v3\| MAE |
|---|---:|---:|---:|---:|
| Daily / Seasonal Naive (no learning) | 8 | 8 | 8 | 0 |
| Ridge, Random Forest, all 10 neural mode groups | 136 | **136** | 0 | 0.240 |
| XGBoost (config 100 → 50 trees after v1) | 12 | 0 | 0 | 0.287 |
| SARIMA (code fixed) | 4 | 0 | 0 | 13.749 |
| Basic GCN-LSTM (graph fixed) | 12 | 0 | 0 | 0.229 |

What the comparison shows:
- **v3 equals v1:** for every learner whose model code did not change, the corrected guard reproduces the v1 scores exactly. On the real inputs, v1's update timing therefore did not use any label before its arrival time.
- **v2 differed:** v2's ordering lagged every update by one day, which changed all 136 learner rows. **v2 scores are superseded and must not be cited.**
- **Synthetic fixture:** the reviewer's delayed-label case (a label arriving after the next origin) is now covered by tests.

---

## 7. Execution cost (v3, measured)

Mean seconds per row from `runs_v3.csv`:
- Inference and update are summed over the 90-day replay.
- "Source" is the recorded Source wall time for the backbone/seed, amortized over 4 targets.
- `total` is replay wall time plus amortized Source time plus adaptation time.
- Timers do not overlap.

| Model / mode | Source (amortized) | Adapt | Inference | Update/refit | Total |
|---|---:|---:|---:|---:|---:|
| Daily Naive | — | — | 0.0009 | 0.0002 | 0.003 |
| Seasonal Naive | — | — | 0.0321 | 0.0023 | 0.037 |
| Ridge | — | — | 0.0088 | 0.0482 | 0.060 |
| SARIMA | — | — | 0.1656 | 2.3587 | 2.528 |
| Random Forest | — | — | 1.1238 | 0.6876 | 1.817 |
| XGBoost | — | — | 0.0587 | 3.6204 | 3.685 |
| MLP target-only / transfer | — / 1.043 | 0.013 / 0.013 | 0.015 / 0.014 | 0.074 / 0.072 | 0.107 / 1.147 |
| GRU target-only / transfer | — / 7.261 | 0.095 / 0.098 | 0.102 / 0.102 | 0.602 / 0.594 | 0.807 / 8.061 |
| LSTM target-only / transfer | — / 4.360 | 0.032 / 0.033 | 0.044 / 0.042 | 0.165 / 0.156 | 0.248 / 4.596 |
| TCN target-only / transfer | — / 5.038 | 0.045 / 0.045 | 0.083 / 0.084 | 0.212 / 0.217 | 0.346 / 5.391 |
| TimeXer-style adapter (custom) target-only / transfer | — / 5.148 | 0.045 / 0.041 | 0.062 / 0.063 | 0.245 / 0.248 | 0.359 / 5.507 |
| Basic GCN-LSTM | — | in construction | 0.1109 | 0.3000 | 0.418 |

- **Source trajectories:** 15 trajectories, recorded wall seconds per checkpoint (3 seeds each):
  - MLP: 4.0–4.5
  - GRU: 27.4–30.0
  - LSTM: 17.2–17.7
  - TCN: 19.6–20.9
  - TimeXer-style adapter (custom): 19.6–22.0

  The checkpoints were trained during the v1 execution and **reused unchanged** by v2 and v3. Their SHA-256s are logged in `execution_log.jsonl`, and the training code is unchanged since v1.
- **End-to-end:** the 172-row v3 replay took 181.4 s with Source reused. Process peak working set was 776 MiB.
- **Memory (pilot, per model):** `pilot/pilot_record.json` records, for each of the 17 pilot model/mode configurations on 1405 / seed 42:
  - the tracemalloc peak (Python/NumPy heap only: 0.8–88.5 MiB; SARIMA highest);
  - the process working set (334–567 MiB).

  The PyTorch CPU allocator is not tracked by tracemalloc, and the working set is a process-level figure, so per-model neural memory is **not** isolated.
- **Pilot status:** all 17 pilot configurations completed with no failures. The pilot was run after the code fixes and before the v3 full run. It verifies execution and gates only and was not used for model selection.

---

## 8. Environment and code identity

`artifacts_v3/environment.json` records:
- **Machine:** Windows 11 (10.0.26300), Intel64 Family 6 Model 154, 12 torch threads.
- **Software:** Python 3.12.10, numpy 2.5.4, pandas 3.1.1, torch 2.14.1+cpu, scikit-learn 1.9.1, xgboost 3.4.1, statsmodels 0.15.0.
- **Input:** the input `manifest.json` SHA-256.
- **Code identity:** the SHA-256 of every executed study source file. The run was executed from uncommitted changes on top of `553275a`, so the code hashes, not the base commit, identify the executed code. Commit `126f041` contains byte-identical `.py` files, and `verify_results` users can recompute those hashes.

A later CI fix (commit `3d6847b`) changed `models/classical.py` and the Cyber tests only. Without pandas or statsmodels, `SARIMABaseline` now records `dependencies_unavailable` and falls back, instead of raising. The path taken in the v3 execution (both libraries installed) is unchanged, so the v3 results are unaffected. Because `models/classical.py` is one of the hashed executed files, its current hash differs from the `environment.json` value recorded for the v3 execution. The executed bytes are those at `126f041`/`0a0df67`, which the reviewer matched.
- **Platform caveat:** this is a local CPU run, not the external compute environment #95 asks for. The full replay is short (3 minutes), but the run should be read with that caveat.

---

## 9. Artifacts, preservation and readback

**v3 (current), in `experiments/member_studies/cyber_baselines/`:**

Tracked in Git:
- `runs_v3.csv` (172 rows)
- `artifacts_v3/manifest.json` (367 SHA-256 entries)
- `artifacts_v3/environment.json`
- `artifacts_v3/execution_log.jsonl`
- `artifacts_v3/graph_lock.json`
- `artifacts_v3/pilot/pilot_record.json` and `pilot_runs.csv`
- `artifacts_v3/readback/{station_first_summary,seed_variability,paired_differences}.csv`

Outside Git (bundle only):
- 172 per-origin forecast files (`*_predictions.json`, with labels, availability-based scoring and model diagnostics)
- 172 fitted target states (`fitted/`: neural/GCN `state_dict`s, pickled RF/XGBoost/Ridge estimators, SARIMA parameters and diagnostics, naive stubs)
- `readback/daily_errors.csv`
- the 15 Source checkpoints

**External bundle (published):** `cyber_baselines_bundle_v3.zip`, with members at their repo-relative paths, attached to the **new** release [`v0.9.5-cyber-benchmark-v3`](https://github.com/HungLD9505/adaptive-retention-ev/releases/tag/v0.9.5-cyber-benchmark-v3). It does not replace the v2 release.
- Bundle SHA-256: `5edbea2fe6a4e12d4f4236da9913032ec2848ba9fa885cbb38d4d4cea6f7a2b0` (re-downloaded and checked by the producer).
- Reviewer check (`@Qyroven`, [review on `0a0df67`](https://github.com/HungLD9505/adaptive-retention-ev/pull/104#pullrequestreview-5845899849)): the SHA-256 matches and the ZIP CRC passes.

**Preserved prior evidence (unchanged bytes):**
- `historical_v1/runs_v1.csv`, `historical_v1/manifest_v1.json`
- `historical_v2/runs_v2.csv` (SHA-256 `9e429c2c…7099`), `historical_v2/manifest_v2.json` (`27b835c1…6e36`), moved with `git mv`
- release `v0.9.5-cyber-benchmark-v2` (v2 forecasts; superseded, see §6)

**Independent readback** (from a checkout plus the extracted bundle):

```
python -m experiments.member_studies.cyber_baselines.verify_results --readback
```

Result on 10 Nov 2026:
- all 367 manifest entries match on-disk bytes, with LF-only text;
- every daily and run-level MAE/RMSE and every coverage count for the 172 ledger rows was recomputed from the stored forecasts and labels and matches the ledger (≤ 5e-6 kWh);
- the readback tables were regenerated.

The readback above uses the producer's own code.

**Reviewer-side readback (independent implementation, `@Qyroven`, on `0a0df67`):** [review](https://github.com/HungLD9505/adaptive-retention-ev/pull/104#pullrequestreview-5845899849) and [#95 summary](https://github.com/HungLD9505/adaptive-retention-ev/issues/95#issuecomment-6773581895). The reviewer reports:
- all 367 manifest entries match bytes and sizes, and the bundle manifest and `runs_v3.csv` are byte-identical to the Git head;
- exactly 172 unique rows, 172 forecast exports and 172 fitted target states;
- every scored day's and every run's MAE/RMSE recomputed from hourly predictions with zero mismatches;
- every scored ground-truth vector equals the local prepared `labels.jsonl`, and there is exactly one common scoring-origin set per target;
- all 13 executed-code hashes in `environment.json` match the head.

The reviewer did not reproduce training, replicate the bootstrap CIs or recheck the raw archive.

---

## 10. Quality gates (run 10 Nov 2026, repo `.venv`, Python 3.12.10)

| README check | Result |
|---|---|
| `python -m tools.sources list` | exit 0 |
| `python -m tools.check_release` | exit 0 |
| `python -m unittest discover -s tests` | **FAILED:** 915 run, 1 failure, 2 errors, 4 skipped |
| `python -m unittest discover -s experiments/fixed_adaptation` | 9 passed |
| `python -m unittest discover -s experiments/confidence_controller` | 12 passed |
| `python -m ruff check .` | passed |
| `python -m ruff format --check .` | passed (530 files) |

The full-suite failures are in tests this PR does not touch:
- `test_hung_proxy_calibration` (calibration identity mismatch)
- `test_hung_final_candidate_jobset` (plan/job drift)
- `test_release_check` symlink test (`WinError 1314`: Windows symlink privilege)

The branch differs from `dev` only in Cyber files and `.gitignore`. These failures are reported, not attributed to this PR, and not fixed here. The checkout is a OneDrive-synced Windows working copy, not a clean CI checkout.

Cyber tests: `python -m unittest tests.test_cyber_baselines` → **24 passed**, including 11 new regression tests in v3. In the CI dependency set (no pandas, statsmodels, scikit-learn or xgboost), 16 pass and 8 are skipped. These tests are fixtures, not evidence of model effectiveness.

**Clean CI:** the reviewer found clean CI red on Ubuntu and Windows on `0a0df67` (run 42857873379) because of a Cyber test (`test_runner_exports_model_diagnostics` without pandas). This was a defect of this PR. It was fixed in `3d6847b`, and [Foundation checks run 42859382487](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/42859382487) passed on **both** `ubuntu-24.04` and `windows-latest` for that head. The local full-suite failures listed above are a separate matter: they come from the local OneDrive Windows working copy and do not occur in clean CI.

---

## 11. Limitations and open items
1. **Not a held-out result:** four historically selected Development targets, so the study is exploratory and conditional. No Final or population claim is made.
2. **No tuning and no locks:** there was no tuning budget, no pre-execution lock record, and only 3 Source epochs with the last checkpoint, so the backbones may be under-trained to different degrees.
3. **Stations:** stations are fixed in all intervals, and n = 3 seeds.
4. **Graph:** results depend on the K = 3 support rule, and 16.9 % of support histories were zero-masked.
5. **Compute and memory:** local CPU execution, and memory is not isolated per neural model.
6. **TimeXer:** the 24 `timexer` rows are a custom TimeXer-style adapter, not the reference TimeXer (§3.4).
7. **Pending:**
   - the lead's scope decisions D1–D3 (§13);
   - final independent peer approval on the revised head, with CI green;
   - merge into `dev` and verification there.

   #95 remains open.

---

## 12. Protocol reconciliation with #96 (actually executed, recorded post-execution)

This section records the protocols **as actually executed** by #95 (this report, run tag `v3`) and #96 ([`@huuduc32`'s report](https://github.com/HungLD9505/adaptive-retention-ev/blob/ecbc4595a9616f7a7fa42679e595947d3832f6d5/docs/reports/member-duc-baselines.md), PR #114). The #96 column is taken from that report and has not been re-executed here.
- It was written **after** both studies ran.
- It is **not** a pre-execution lock, not a common tuning plan, and not evidence of identical code.
- No prospective mutual sign-off on exact implementation, tuning or checkpoint selection exists for either study, and none is reconstructed here.

| Dimension | #95 Cyber (v3) | #96 Đức | Consequence |
|---|---|---|---|
| Input / task | Manifest `66c82dd3…`; 65,888 Source examples; targets 1405/2152/1153/1693, 14-day prefix, trainable 4/12/13/13; 24 h → next 24 h kWh | Same manifest, Source count, targets and prefix counts | Broad input/task comparability |
| Schedule / coverage / schema | 90-day schedule; 160 + 12 rows; seeds 42/43/44; 1405 = 90/90/89, others 90/59/52; station-first MAE/RMSE | Same counts and schema | Same aggregate schema. Cross-author per-origin equivalence is not verified. |
| Neural recipe | Source 3 epochs, last checkpoint, batch 256, lr 1e-3; target adaptation 3 epochs, batch 4, lr 5e-4; 1 update epoch per arrived day; λ = 0 | Same nominal recipe | Shared **fixed** recipe. No architecture-specific tuning in either. The #95 1/3/10-checkpoint recipe was not executed by either study. |
| MLP | 168 → 128 → 64 encoder + calendar head; 43,288 params | 168 → 128 → 64 encoder; head and parameter count may differ | Not verified as architecture-matched |
| GRU / LSTM | 2 layers, width 64, calendar head | 2 layers, width 64 | Nominally similar; wrappers not cross-audited |
| TCN | 3 residual blocks, 64 channels, kernel 3, dilations 1/2/4; 77,080 params | 4 causal residual blocks, 64 channels | **Different architectures** |
| TimeXer | **Custom TimeXer-style adapter**: hour tokens, no patching, no global token, width 64 (§3.4) | Official TimeXer pinned at `7601190…`: patch 6, width 32, 4 heads, 1 encoder | **Materially different models.** No head-to-head or replication claim. |
| Ridge / RF / XGBoost | α = 1.0 daily refit; RF 100 trees, depth 10, weekly; XGBoost 50 trees, depth 5, lr 0.1, weekly | Same nominal hyperparameters | Library versions differ (below) |
| SARIMA | SARIMAX(1,0,1)(1,0,0)₂₄, maxiter 15, weekly refit on 336 h; read-only forecast, daily `append(refit=False)`, failure counters | Same nominal order/maxiter/window/cadence; replay state filtered up to the origin with fitted parameters | Replay-state implementations differ. Do not infer identical SARIMA execution. |
| Graph | 16 nodes (4 targets + 3 nearest Development-role supports each); Gaussian kernel; 5 initial epochs; supports give origin-time `x_hist` only; 16.9 % zero-masked | 16 nodes with 3 Development-role supports per target, fixed geographic adjacency, 5 initial epochs | Edge/missing-support handling not cross-audited |
| Environment | Local Windows CPU; Python 3.12.10, scikit-learn 1.9.1, statsmodels 0.15.0, xgboost 3.4.1, torch 2.14.1+cpu | Colab CPU; Python 3.13.18, scikit-learn 1.6.1, statsmodels 0.14.5, xgboost 3.0.5, torch 2.14.1+cpu | Neither used the external compute environment #95/#96 describe as the target |
| Reviewer verification | Artifact/metric/common-origin readback passed (§9) | Artifact/per-origin audit passed (PR #114) | Each study verified on its own terms only |

**Use of the two studies:** they are two independent, fixed-recipe exploratory Development studies with the documented differences above. Their numbers must not be ranked against each other or presented as paired replications.

---

## 13. Requirement status and proposed scope disposition (lead decisions needed)

The #96 scope decision (11 November 2026) does **not** automatically apply to #95. The following is the owner's **proposal**; nothing here is accepted until the lead decides it explicitly.

| #95 requirement | Status for #95 | Proposal |
|---|---|---|
| 172-row matrix, seeds, nulls, common origins | Met; reviewer readback passed | — |
| Data/input hashes, Source identity, prefixes, schedule | Met for extracted files; distribution ZIP not re-hashed (§2) | — |
| Artifacts, hash manifest, external bundle | Met; release v3 verified by the reviewer | — |
| Clean CI and README checks | CI green on `3d6847b` (Ubuntu + Windows) | — |
| Common protocol/schema **agreed before execution**; locked configs/checkpoint selection; comparable tuning budget | **Not met.** No pre-execution lock, no tuning, 3 Source epochs with last checkpoint. Only the post-execution reconciliation in §12 exists. | **D1:** accept #95 as a fixed-recipe exploratory Development study with these deviations disclosed, consistent with #96. Any harmonised or tuned comparison must be a new, separately and prospectively registered study with fresh run IDs. |
| TimeXer baseline (reference) | **Not met as named.** The 24 rows use a custom TimeXer-style adapter. | **D2:** accept the custom adapter as a **labelled substitution** ("TimeXer-style adapter (custom)") for this handoff. It makes no reference-TimeXer claim, and existing rows keep their run IDs and artifacts. The reference TimeXer is deferred to the prospective follow-up under D1. |
| External compute environment | **Not met.** Local Windows CPU (the 172-row replay took 3 minutes). | **D3:** accept local CPU as a disclosed exception for this handoff. Any prospective follow-up runs on the agreed external environment. |

If the lead rejects D1, D2 or D3, the owner will draft a prospective specification with `@huuduc32` before any new execution. That specification will cover:
- exact model definitions and adapters (especially the reference TimeXer);
- Source checkpoint selection;
- the tuning budget;
- data, calendar and label boundaries;
- graph supports and edges;
- the score/origin schema;
- artifact verification.

New runs would then use versioned run IDs and output roots. No historical lock will be manufactured, and no existing output will be rewritten.
