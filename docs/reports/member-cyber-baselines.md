# Cyber UrbanEV Baseline Benchmark Report (Issue #95)

**Author:** Trần Mạnh Hùng (`@hung00cyber`)  
**Target Issue:** GitHub Issue #95 (`HungLD9505/adaptive-retention-ev`)  
**Branch:** `feat/cyber-urbanev-baseline-benchmark`  
**Execution Date:** 10 November 2026 (Asia/Ho_Chi_Minh)  
**Revision:** v2 (Post-Review Resolution of Audit Findings)  
**Status:** Complete Independent Benchmark  

---

## 1. Executive Summary & Scope

This report presents the complete, independent UrbanEV baseline benchmark conducted on the Shenzhen (SZH) cohort under a strict 14-day historical observation budget. The benchmark evaluates 12 distinct forecasting models across 4 Development target stations (`1405`, `2152`, `1153`, `1693`) over the official 90-day Development replay schedule (2022-12-01 to 2023-02-28).

Following peer review feedback on PR #104, this revision incorporates comprehensive resolution of all audit findings:
1. **Real Spatial Node Signals:** `BasicGCNLSTM` ingests genuine, time-aligned 24-hour histories from all 4 stations simultaneously rather than repeating target history across nodes.
2. **SARIMA State Advance & Gap Preservation:** `SARIMABaseline` preserves regular hourly time indexing with Kalman missing-value support across calendar gaps and advances its forecasting state between weekly refits via Kalman filtering (`append(..., refit=False)`).
3. **Strict Causal Arrival Guard:** Label decoding and online learning are strictly gated by the replay clock (`datetime.fromisoformat(a) <= current_as_of`).
4. **Exact Null Metric Accounting:** Evaluated runs with zero scored observations emit explicit `None` / `null` metrics with reason codes rather than misleading `0.0`.
5. **Byte-Level LF Checksum Contract:** All prediction artifacts and ledger rows are written in binary mode with explicit LF (`\n`) newlines, eliminating OS newline discrepancies.
6. **Complete Artifact Enumeration & External Handoff:** Checksum manifest enumerates all 172 prediction files, 15 PyTorch source checkpoints, and `runs.csv` (188 verified entries total), published in an external release bundle with independent readback verification.

The benchmark comprises **172 unique model-mode-target-seed rows**:
- **160 rows** in the primary non-graph matrix:
  - 4 Statistical models $\times$ 4 targets = 16 rows.
  - 2 Classical ML models $\times$ 3 seeds (42, 43, 44) $\times$ 4 targets = 24 rows.
  - 5 Neural backbones $\times$ 2 modes (Target-Only, Transfer) $\times$ 3 seeds $\times$ 4 targets = 120 rows.
- **12 rows** in the spatial comparator matrix (Basic GCN-LSTM $\times$ 3 seeds $\times$ 4 targets), reported separately.

All executions were performed independently by `@hung00cyber` with own versioned code, configuration, checkpoints, prediction outputs, and SHA-256 manifests. Original v1 artifacts are archived in `historical_v1/`.

---

## 2. Experimental Invariants & Data Accounting

### 2.1 Authenticated Input Metadata

The benchmark strictly conforms to the authenticated inputs at `data/inputs/issue18-input-handoff-v1-20261019/urbanev-SZH-14d/`:
- **Source Population:** Exactly **65,888** eligible 24-to-24 Source examples loaded from `training.jsonl` (verified against historical records, with zero arbitrary truncation).
- **Target Stations & 14-Day Initial Budgets:**
  - `1405`: 4 initial trainable prefix examples, $s_{\text{p95}} = 43.8667\text{ kWh}$.
  - `2152`: 12 initial trainable prefix examples, $s_{\text{p95}} = 42.0000\text{ kWh}$.
  - `1153`: 13 initial trainable prefix examples, $s_{\text{p95}} = 56.0000\text{ kWh}$.
  - `1693`: 13 initial trainable prefix examples, $s_{\text{p95}} = 14.0000\text{ kWh}$.

### 2.2 Replay Calendar & Gated Scoring Accounting

For each target station over the 90-day Development schedule:
- **Scheduled Days:** 90 calendar days per station ($4 \times 90 = 360\text{ total scheduled days}$).
- **Issued Forecasts:**
  - Station `1405`: 90 issued days (0 skipped).
  - Stations `2152`, `1153`, `1693`: 59 issued days each (31 days skipped due to `skipped_all_missing_history`).
  - Total issued forecasts = $90 + 3 \times 59 = 267\text{ issued days}$.
- **Scored Days (Forecast Issued AND Arrived Label Complete):**
  - Station `1405`: 89 scored days (1 incomplete label day on 2023-01-22).
  - Stations `2152`, `1153`, `1693`: 52 scored days each (7 incomplete label days).
  - Total scored days = $89 + 3 \times 52 = 245\text{ scored days}$.
- **Unscored Accounting:** Exactly $360 - 245 = 115\text{ unscored days}$ (93 missing history + 22 incomplete labels). Every unscored origin is preserved as a verified null; no imputation or label leaking occurred.

---

## 3. Model Architecture & Protocol Definitions

### 3.1 Feature Space & Information Boundaries
- **Historical Window ($X_{\text{hist}}$):** $\mathbb{R}^{24 \times 7}$ containing hourly normalized energy, temporal encodings ($\sin/\cos$ for hour-of-day and day-of-week), and validity mask.
- **Future Known Calendar ($C_{\text{future}}$):** $\mathbb{R}^{24 \times 5}$ containing $\sin/\cos$ calendar features for the 24 forecast hours.
- **Output ($Y$):** $\mathbb{R}^{24}$ non-negative hourly energy values. Evaluation is strictly in original units ($\text{kWh}$) after unscaling by $s_{\text{p95}}$.

### 3.2 Model Specifications

1. **Daily Naive:** Causal baseline predicting same-hour energy from previous day ($y_{t, h} = X_{\text{hist}}[h, 0]$). If masked/missing, falls back to available history mean, then zero.
2. **Seasonal Naive:** Causal weekly naive predicting same-hour energy from 7 days prior ($168\text{h}$ lag). Fallback order: weekly lag $\to$ daily lag ($24\text{h}$) $\to$ available history mean $\to$ zero.
3. **Ridge Regression:** Multi-output linear regression with L2 regularization ($\alpha = 1.0$) on flattened $288$-dimensional features ($168\text{ historical} + 120\text{ calendar}$). Fitted on target initial prefix, with weekly expanding-window refit. Outputs clipped at zero.
4. **SARIMA:** Univariate $\text{SARIMAX}(1, 0, 1)(1, 0, 0)_{24}$ fit on available hourly sequence (up to 336 hours history) with bounded optimization (`maxiter=15`). Fitted initially and refit weekly; between weekly refits, state is advanced daily via Kalman filter (`append(..., refit=False)`), preserving hourly DatetimeIndex across calendar gaps.
5. **Random Forest:** Multi-output regressor with 100 trees, maximum depth 10, seeded across {42, 43, 44}. Ingests 288 flattened features with weekly expanding-window refit.
6. **XGBoost:** Gradient boosted tree ensemble with 50 estimators, depth 5, learning rate 0.1, native multi-output regression. Seeded across {42, 43, 44} with weekly expanding-window refit.
7. **MLP / FCNN:** 2-layer perceptron: $\text{Linear}(288 \to 128) \to \text{ReLU} \to \text{Linear}(128 \to 64) \to \text{ReLU} \to \text{Linear}(64 + 120 \to 64) \to \text{ReLU} \to \text{Linear}(64 \to 24) \to \text{Softplus}$.
8. **GRU (Canonical Backbone):** 2-layer GRU ($\text{hidden}=64$) encoding $X_{\text{hist}} \to h_{24} \in \mathbb{R}^{64}$, concatenated with flattened $C_{\text{future}}$ into MLP head ($64 \to 24$) with Softplus.
9. **LSTM:** 2-layer LSTM ($\text{hidden}=64$) encoding $X_{\text{hist}} \to h_{24} \in \mathbb{R}^{64}$, concatenated with flattened $C_{\text{future}}$ into MLP head with Softplus.
10. **TCN (Temporal Convolutional Network):** 3 residual blocks with causal dilated 1D convolutions (kernel size 3, dilations 1, 2, 4; receptive field = 29 hours $> 24\text{h}$). Final time step latent vector $\in \mathbb{R}^{64}$ fed to calendar-conditioned MLP head.
11. **TimeXer Architecture Adaptation:** Implements endogenous-exogenous cross-attention adapted for compact 24-step horizon. Endogenous series ($24 \times 7$) is projected to embedding dimension $D=64$ via linear series patching. Exogenous calendar features ($24 \times 5$) are embedded into $D=64$ calendar tokens. Endogenous self-attention block is followed by endogenous-query / exogenous-key cross-attention and FFN, pooled and projected to 24 hourly outputs with Softplus.
12. **Basic GCN-LSTM (Spatial Comparator):** Spatial graph convolutional network ($A_{\text{norm}} X_t W$) coupled with node-level LSTM across time steps. Spatial adjacency $A$ is computed from `station_distance.csv` in `UrbanEVDataset.zip` using Gaussian kernel thresholding:
    $$\tilde{A}_{ij} = \exp\left(-\frac{d_{ij}^2}{\sigma^2}\right), \quad A_{\text{norm}} = D^{-1/2} (A + I) D^{-1/2}$$
    At each origin, the model receives a true $[1, 24, N, 7]$ multi-node tensor populated with each station's actual time-aligned historical records, zero-masked when stations have missing history.

### 3.3 Training & Adaptation Protocol
- **Source Pretraining:** 3 epochs on all 65,888 Source examples with PyTorch DataLoader (`batch_size=256`, Adam optimizer, `lr=1e-3`, L1 loss). Checkpoints saved per backbone/seed (15 total source trajectories).
- **Target-Only Mode:** Initialized with random seeded weights, adapted for 3 epochs on target initial prefix (`batch_size=4`, `lr=5e-4`), followed by 1 epoch online adaptation per newly arrived complete day.
- **Transfer Mode ($\lambda=0$):** Initialized from matching Source backbone/seed checkpoint, fine-tuned for 3 epochs on target initial prefix, followed by 1 epoch online update per arrived complete day.

---

## 4. Comprehensive Benchmark Results

### 4.1 Overall Performance Summary (Non-Graph Matrix: 160 Rows)

| Model | Mode | Scored Rows | Mean MAE (kWh) | Mean RMSE (kWh) | Param Count | Wall Time / Run (s) |
|---|---|---:|---:|---:|---:|---:|
| **Daily Naive** | Target-Only | 4 | 7.0763 | 9.5713 | 0 | 0.0031 |
| **Seasonal Naive** | Target-Only | 4 | 8.4631 | 11.1458 | 0 | 0.0371 |
| **Ridge** | Target-Only | 4 | 6.0589 | 8.0729 | 6,936 | 0.0583 |
| **SARIMA** | Target-Only | 4 | 12.8808 | 15.8189 | 4 | 4.0597 |
| **Random Forest** | Target-Only | 12 | 5.8672 | 7.7341 | 204,700 | 1.7649 |
| **XGBoost** | Target-Only | 12 | 6.6335 | 8.9998 | 3,150 | 3.5602 |
| **MLP** | Target-Only | 12 | 8.8028 | 10.8960 | 43,288 | 0.1134 |
| **MLP** | Transfer ($\lambda=0$) | 12 | 5.5328 | 7.3137 | 43,288 | 1.1504 |
| **GRU** | Target-Only | 12 | 9.0687 | 11.1210 | 52,376 | 0.8135 |
| **GRU** | Transfer ($\lambda=0$) | 12 | **5.3381** | **7.1417** | 52,376 | 8.0693 |
| **LSTM** | Target-Only | 12 | 9.0686 | 11.1129 | 65,368 | 0.2726 |
| **LSTM** | Transfer ($\lambda=0$) | 12 | 5.3604 | 7.2253 | 65,368 | 4.6554 |
| **TCN** | Target-Only | 12 | 8.2280 | 10.2710 | 77,080 | 0.5214 |
| **TCN** | Transfer ($\lambda=0$) | 12 | 5.3668 | 7.2414 | 77,080 | 5.5456 |
| **TimeXer** | Target-Only | 12 | 8.2352 | 10.2497 | 66,072 | 0.3408 |
| **TimeXer** | Transfer ($\lambda=0$) | 12 | 5.6164 | 7.5321 | 66,072 | 5.4813 |

---

### 4.2 Isolating Transfer Benefit: Within-Backbone Comparison

A core mandate of Issue #95 is isolating the transfer benefit strictly **within** each neural architecture, eliminating architecture/initialization confounders.

| Backbone | Target-Only MAE (kWh) | Transfer MAE (kWh) | Absolute $\Delta$ (kWh) | **Error Reduction (%)** | Target-Only RMSE (kWh) | Transfer RMSE (kWh) | RMSE Reduction (%) |
|---|---:|---:|---:|---:|---:|---:|---:|
| **GRU** | 9.0687 | 5.3381 | -3.7306 | **-41.14%** | 11.1210 | 7.1417 | -35.78% |
| **LSTM** | 9.0686 | 5.3604 | -3.7082 | **-40.89%** | 11.1129 | 7.2253 | -34.98% |
| **MLP** | 8.8028 | 5.5328 | -3.2700 | **-37.15%** | 10.8960 | 7.3137 | -32.88% |
| **TCN** | 8.2280 | 5.3668 | -2.8612 | **-34.77%** | 10.2710 | 7.2414 | -29.49% |
| **TimeXer** | 8.2352 | 5.6164 | -2.6188 | **-31.79%** | 10.2497 | 7.5321 | -26.51% |

**Key Takeaways:**
- Every neural architecture demonstrates a substantial **31.79% to 41.14% error reduction** when initialized with Source pretraining compared to target-only learning.
- In the low-data Target-Only regime (4 to 13 initial days), deep neural networks suffer severely from data scarcity, achieving MAEs of 8.23 - 9.07 kWh.
- Pretraining on 65,888 Source samples provides robust inductive temporal priors that transfer effectively across charging stations, bringing error down to ~5.34 - 5.62 kWh.

---

### 4.3 Matched Neural Backbone Comparison (Under Transfer)

Comparing backbones when all architectures are initialized from Source pretraining:
1. **GRU (5.3381 kWh MAE, 7.1417 kWh RMSE):** Achieves the lowest error among all evaluated models.
2. **LSTM (5.3604 kWh MAE, 7.2253 kWh RMSE):** Performs nearly identically to GRU (+0.0223 kWh MAE difference, statistically indistinguishable), requiring 25% more parameters (65,368 vs 52,376).
3. **TCN (5.3668 kWh MAE, 7.2414 kWh RMSE):** Delivers competitive accuracy (+0.0287 kWh MAE difference from GRU) via dilated causal convolutions, proving recurrent gating is not strictly required if causal temporal receptive field is preserved.
4. **MLP (5.5328 kWh MAE, 7.3137 kWh RMSE):** Trails GRU by +0.1947 kWh, demonstrating sequence-aware temporal structures slightly outperform unstructured feedforward architectures even after pretraining.
5. **TimeXer (5.6164 kWh MAE, 7.5321 kWh RMSE):** Performs reliably (+0.2783 kWh MAE difference from GRU), but cross-attention over short 24-step horizons does not outperform compact recurrent/convolutional encoders.

---

### 4.4 Classical ML vs Neural Networks & Paired Significance Analysis

Across the 245 common scored origins, we perform formal paired t-tests evaluating pairwise differences against the leading GRU Transfer baseline:

| Model Pair | Mean MAE Diff (kWh) | Paired t-stat | p-value | Significant at $\alpha=0.05$ |
| :--- | :--- | :--- | :--- | :--- |
| **GRU Transfer vs LSTM (Transfer)** | +0.0149 | 0.285 | $7.756 \times 10^{-1}$ | **No (Indistinguishable)** |
| **GRU Transfer vs TCN (Transfer)** | +0.0406 | 0.635 | $5.257 \times 10^{-1}$ | **No (Indistinguishable)** |
| **GRU Transfer vs MLP (Transfer)** | +0.1680 | 1.802 | $7.281 \times 10^{-2}$ | **No (Indistinguishable at $\alpha=0.05$)** |
| **GRU Transfer vs TimeXer (Transfer)** | +0.3220 | 4.240 | $3.169 \times 10^{-5}$ | **Yes (p < 0.05)** |
| **GRU Transfer vs Random Forest (Target-Only)** | +0.5345 | 3.063 | $2.436 \times 10^{-3}$ | **Yes (p < 0.05)** |
| **GRU Transfer vs Daily Naive (Target-Only)** | +1.6124 | 7.084 | $1.490 \times 10^{-11}$ | **Yes (p < 0.05)** |
| **GRU Transfer vs Basic GCN-LSTM (Target-Only)**| +1.8973 | 8.894 | $1.350 \times 10^{-16}$ | **Yes (p < 0.05)** |
| **GRU Transfer vs SARIMA (Target-Only)** | +7.3033 | 14.315 | $3.749 \times 10^{-34}$ | **Yes (p < 0.05)** |

**Scientific Interpretation & Qualification:**
- **Statistical Indistinguishability:** GRU, LSTM, and TCN under transfer form an equivalence cluster ($p > 0.50$). While GRU records the nominal minimum, claims of GRU superiority over LSTM or TCN are not statistically supported.
- **Development Regime Findings:** Within the 4 evaluated Development target stations, transfer pretraining is necessary for deep neural networks to outperform classical ML baselines (Random Forest). In small-sample target-only settings, Random Forest (5.8672 kWh) decisively outperforms all target-only neural models (8.2280 - 9.0687 kWh). These findings constitute conditional empirical evidence within the 4 Development stations rather than an unconstrained universal law.

---

### 4.5 Station-by-Station Breakdown (MAE in kWh)

| Model | Mode | Station 1153 ($s=56.0$) | Station 1405 ($s=43.9$) | Station 1693 ($s=14.0$) | Station 2152 ($s=42.0$) | Overall Mean |
|---|---|---:|---:|---:|---:|---:|
| **Daily Naive** | Target-Only | 11.1941 | 6.9545 | 2.9083 | 7.2482 | 7.0763 |
| **Seasonal Naive** | Target-Only | 12.5791 | 8.5471 | 4.5807 | 8.1456 | 8.4631 |
| **Ridge** | Target-Only | 8.1567 | 6.5483 | 3.0181 | 6.5124 | 6.0589 |
| **SARIMA** | Target-Only | 23.2826 | 12.0070 | 4.3756 | 11.8579 | 12.8808 |
| **Random Forest** | Target-Only | 7.8646 | 6.6145 | 2.8932 | 6.0963 | 5.8672 |
| **XGBoost** | Target-Only | 8.7023 | 7.4645 | 3.1673 | 7.1997 | 6.6335 |
| **MLP** | Target-Only | 10.9375 | 9.3357 | 4.9472 | 9.9907 | 8.8028 |
| **MLP** | Transfer | 7.4175 | 6.0670 | 2.4419 | 6.2048 | 5.5328 |
| **GRU** | Target-Only | 11.3466 | 9.3589 | 4.9745 | 10.5948 | 9.0687 |
| **GRU** | Transfer | 6.9222 | 6.0491 | **2.4241** | 5.9571 | **5.3381** |
| **LSTM** | Target-Only | 10.9835 | 9.7056 | 4.9353 | 10.6500 | 9.0686 |
| **LSTM** | Transfer | **6.8347** | **6.0229** | 2.4794 | 6.1045 | 5.3604 |
| **TCN** | Target-Only | 10.5324 | 8.9427 | 4.7834 | 8.6535 | 8.2280 |
| **TCN** | Transfer | 6.9154 | 6.1570 | 2.5446 | **5.8501** | 5.3668 |
| **TimeXer** | Target-Only | 10.5280 | 8.6043 | 4.7473 | 9.0614 | 8.2352 |
| **TimeXer** | Transfer | 7.2265 | 6.6166 | 2.4787 | 6.1440 | 5.6164 |

---

### 4.6 Stochastic Seed Variability (Seeds 42, 43, 44)

| Model | Mode | Seed 42 MAE | Seed 43 MAE | Seed 44 MAE | Mean MAE | Seed Std Dev |
|---|---|---:|---:|---:|---:|---:|
| **Random Forest** | Target-Only | 5.8842 | 5.8466 | 5.8707 | 5.8672 | $\pm 0.0190$ |
| **XGBoost** | Target-Only | 6.6335 | 6.6335 | 6.6335 | 6.6335 | $\pm 0.0000$ |
| **MLP** | Target-Only | 8.7698 | 8.6912 | 8.9473 | 8.8028 | $\pm 0.1312$ |
| **MLP** | Transfer | 5.6227 | 5.3929 | 5.5828 | 5.5328 | $\pm 0.1228$ |
| **GRU** | Target-Only | 9.1891 | 8.5663 | 9.4507 | 9.0687 | $\pm 0.4544$ |
| **GRU** | Transfer | 5.3390 | 5.4071 | 5.2683 | 5.3381 | $\pm 0.0694$ |
| **LSTM** | Target-Only | 9.1291 | 9.2378 | 8.8388 | 9.0686 | $\pm 0.2063$ |
| **LSTM** | Transfer | 5.4046 | 5.2940 | 5.3826 | 5.3604 | $\pm 0.0586$ |
| **TCN** | Target-Only | 8.2164 | 8.3239 | 8.1437 | 8.2280 | $\pm 0.0906$ |
| **TCN** | Transfer | 5.4276 | 5.3931 | 5.2796 | 5.3668 | $\pm 0.0774$ |
| **TimeXer** | Target-Only | 8.2557 | 8.0093 | 8.4407 | 8.2352 | $\pm 0.2164$ |
| **TimeXer** | Transfer | 5.8519 | 5.5205 | 5.4770 | 5.6164 | $\pm 0.2051$ |

**Seed Consistency Analysis:**
- Across transfer neural models, standard deviation spans $\sigma \in [0.0586, 0.2051]\text{ kWh}$.
- Recurrent (LSTM $\sigma=0.0586$, GRU $\sigma=0.0694$) and convolutional (TCN $\sigma=0.0774$) models exhibit high stability across seeds.
- TimeXer shows higher sensitivity across initialization seeds ($\sigma = 0.2051\text{ kWh}$), reflecting the optimization dynamics of multi-head cross-attention over short temporal patches.

---

## 5. Spatial Comparator Benchmark: Basic GCN-LSTM (12 Rows)

Graph results are reported in this isolated section as the model ingests spatial cross-station distance dependencies from `station_distance.csv`.

### 5.1 Spatial Setup
- **Nodes:** Development target stations {1405, 2152, 1153, 1693} with geographical distances from `UrbanEVDataset.zip`.
- **Adjacency Matrix:** Normalized Laplacian $A_{\text{norm}} = D^{-1/2} (A + I) D^{-1/2}$ with Gaussian kernel thresholding.
- **Multi-Node Historical Inputs:** At each replay origin, each node receives the genuine time-aligned 24-hour history from its corresponding station, with zero-masking for missing history origins.
- **Model:** GCN spatial layer ($32\text{ dims}$) + node-level LSTM ($64\text{ dims}$) + calendar head ($64 \to 24$) with Softplus ($38,744\text{ parameters}$).

### 5.2 Spatial Results Table

| Target Station | Seed | Scheduled Days | Issued Days | Scored Days | MAE (kWh) | RMSE (kWh) | Wall Time (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| **1153** | 42 | 90 | 59 | 52 | 9.7952 | 12.2046 | 0.36s |
| **1153** | 43 | 90 | 59 | 52 | 9.9053 | 12.4392 | 0.35s |
| **1153** | 44 | 90 | 59 | 52 | 9.6771 | 12.2214 | 0.44s |
| **1405** | 42 | 90 | 90 | 89 | 8.1624 | 10.4859 | 0.62s |
| **1405** | 43 | 90 | 90 | 89 | 8.0652 | 10.4056 | 0.61s |
| **1405** | 44 | 90 | 90 | 89 | 7.8913 | 10.1132 | 0.61s |
| **1693** | 42 | 90 | 59 | 52 | 3.5188 | 5.3186 | 0.35s |
| **1693** | 43 | 90 | 59 | 52 | 3.4932 | 5.2921 | 0.39s |
| **1693** | 44 | 90 | 59 | 52 | 3.5533 | 5.4081 | 0.35s |
| **2152** | 42 | 90 | 59 | 52 | 7.8070 | 10.1021 | 0.39s |
| **2152** | 43 | 90 | 59 | 52 | 7.4847 | 9.7358 | 0.42s |
| **2152** | 44 | 90 | 59 | 52 | 7.2732 | 9.5634 | 0.35s |

### 5.3 Spatial Comparator Summary

| Target Station | Mean MAE (kWh) | Std Dev MAE | Mean RMSE (kWh) | Param Count | Avg Replay Time (s) |
|---|---:|---:|---:|---:|---:|
| **1153** | 9.7925 | $\pm 0.1142$ | 12.2884 | 38,744 | 0.38s |
| **1405** | 8.0396 | $\pm 0.1373$ | 10.3349 | 38,744 | 0.61s |
| **1693** | 3.5218 | $\pm 0.0301$ | 5.3396 | 38,744 | 0.36s |
| **2152** | 7.5216 | $\pm 0.2688$ | 9.8004 | 38,744 | 0.39s |
| **Overall** | **7.2189** | $\pm 0.1122$ | **9.4408** | **38,744** | **0.44s** |

**Spatial Findings:**
1. **Target-Only Spatial Gain:** When supplied with genuine multi-node historical signals, Basic GCN-LSTM achieves an overall MAE of **7.2189 kWh**, significantly outperforming Target-Only single-station neural networks (GRU: **9.0687 kWh**, LSTM: **9.0686 kWh**, MLP: **8.8028 kWh**, TCN: **8.2280 kWh**). Spatial message passing regularizes local station predictions in the low-data target-only regime.
2. **Transfer Pretraining Remains Superior:** GCN-LSTM without pretraining trails Source-pretrained transfer models (**GRU Transfer 5.3381 kWh**). Cross-station spatial convolution over 4 stations does not replace the statistical advantage of pretraining on 65,888 diverse charging instances.

---

## 6. Execution Costs & Runtime Boundaries

All experiments were executed on an Intel CPU under Windows (Python 3.12, PyTorch 2.14 CPU):

| Model Category | Pretraining Wall Time | Adaptation Time / Station | 90-Day Inference Time | Daily Update Time | Total Replay Wall Time |
|---|---:|---:|---:|---:|---:|
| **Daily Naive** | 0.00s | 0.00s | 0.0008s | 0.0002s | **0.003s** |
| **Seasonal Naive** | 0.00s | 0.00s | 0.0316s | 0.0023s | **0.037s** |
| **Ridge** | 0.00s | 0.00s | 0.0084s | 0.0466s | **0.058s** |
| **SARIMA** | 0.00s | 0.00s | 2.5000s | 1.5500s | **4.060s** |
| **Random Forest** | 0.00s | 0.00s | 1.1000s | 0.6500s | **1.765s** |
| **XGBoost** | 0.00s | 0.00s | 0.0650s | 3.4900s | **3.560s** |
| **MLP (Target-Only)** | 0.00s | 0.0183s | 0.0214s | 0.0737s | **0.113s** |
| **MLP (Transfer)** | 4.17s (1.04s amortized) | 0.0201s | 0.0223s | 0.0680s | **1.150s** |
| **GRU (Target-Only)** | 0.00s | 0.1579s | 0.1772s | 0.4784s | **0.814s** |
| **GRU (Transfer)** | 29.04s (7.26s amortized) | 0.1536s | 0.1860s | 0.4700s | **8.069s** |
| **LSTM (Target-Only)**| 0.00s | 0.0417s | 0.0593s | 0.1716s | **0.273s** |
| **LSTM (Transfer)** | 17.44s (4.36s amortized) | 0.0432s | 0.0598s | 0.1924s | **4.655s** |
| **TCN (Target-Only)** | 0.00s | 0.0635s | 0.1184s | 0.3395s | **0.521s** |
| **TCN (Transfer)** | 20.15s (5.04s amortized) | 0.0618s | 0.1192s | 0.3246s | **5.546s** |
| **TimeXer (Target-Only)**| 0.00s | 0.0620s | 0.0798s | 0.1990s | **0.341s** |
| **TimeXer (Transfer)**| 20.59s (5.15s amortized) | 0.0597s | 0.0890s | 0.1826s | **5.481s** |
| **Basic GCN-LSTM** | 0.00s | 0.00s | 0.1144s | 0.3221s | **0.437s** |

- Full 172-row execution suite completes in **3.33 minutes** with pre-saved source checkpoints (~5 minutes if pretraining from scratch).

---

## 7. Adverse Findings, Null Cases & Scientific Limitations

1. **Empirical Verification of Arrival Guard Invariance:** An exhaustive scan across all target stations verified that **zero complete labels arrive after the next scheduled origin** (`delayed_past_next == 0` for stations 1405, 2152, 1153, 1693). Gating label arrival by the replay clock enforces mathematical causality without altering historical evaluation scores.
2. **Exploratory Development Limitation:** These 4 Development target stations were selected based on historical data availability. Results constitute conditional Development evidence rather than population-wide proof across unobserved stations.
3. **Missing History Nulls:** Target stations 2152, 1153, and 1693 possess 31 days with missing history (`skipped_all_missing_history`). Forecasts were cleanly not issued, and no labels were decoded or imputed for these origins.
4. **Incomplete Ground Truth Days:** Exactly 22 target days experienced sensor dropouts (`file_valid` incomplete). These days were withheld from scoring across all models, ensuring exact common-origin parity.
5. **Target-Only Deep Learning Failure:** Without pretraining, deep neural networks fail to compete with classical Random Forest (5.8672 kWh) and Ridge (6.0589 kWh) under scarce initial data budgets.

---

## 8. Artifact Provenance, SHA-256 Checksums & Readback Evidence

- **Primary Metrics Ledger:** `experiments/member_studies/cyber_baselines/runs.csv` (172 rows, LF newline format).
- **Artifact Manifest:** `experiments/member_studies/cyber_baselines/artifacts/manifest.json` (**188 verified entries**: 172 predictions, 15 PyTorch source checkpoints, 1 runs.csv).
- **Preserved Historical Evidence:** Archived in `experiments/member_studies/cyber_baselines/historical_v1/` (`runs_v1.csv` and `manifest_v1.json`).
- **Independent Verification Tool:** Run `python -m experiments.member_studies.cyber_baselines.verify_results --paired` to verify all 188 checksums, recompute metrics from raw prediction bytes, and generate paired statistical tests.
- **External Immutable Release Bundle:** Full bundle containing all predictions, checkpoints, configs, and readback code published at GitHub Release `v0.9.5-cyber-benchmark-v2`:  
  `https://github.com/HungLD9505/adaptive-retention-ev/releases/tag/v0.9.5-cyber-benchmark-v2`

---

## 9. Quality Gates & Acceptance Verification

- **Linting:** `python -m ruff check experiments/member_studies/cyber_baselines tests/test_cyber_baselines.py` $\to$ **All checks passed!**
- **Formatting:** `python -m ruff format --check .` $\to$ **100% compliant**.
- **Unit & Regression Testing:** `python -m unittest tests.test_cyber_baselines` $\to$ **13 tests passed in 2.31s (OK)**.
- **Manifest Audit:** All 188 files verified with binary SHA-256 match and strict LF newlines.
- **Ownership Notice:** Conducted independently by `@hung00cyber`. Companion Issue #96 owned by `@huuduc32`.
