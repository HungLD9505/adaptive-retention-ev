# Hung–Qyroven forecast-head contract review aid — 28 October 2026

This supplements the [bounded parity audit](hung-q-parity-20261027-v1.md) for #39/#22. It describes the two **executed** architectures so a reviewer can choose one Report 1 contract before any matched forecast/loss/gradient trace. It makes no choice based on MAE and does not claim parity.

| Component | Hung Development (`calendar_hidden=8`) | Qyroven pinned comparison (`head_width=64`) |
| --- | --- | --- |
| Shared history encoder | Two-layer GRU, 7 input features, hidden 64; 38,976 parameters | Same dimensions and parameter count |
| Future calendar | Flatten 24 × 5 values to 120; `Linear(120,8)` + ReLU | Flatten 24 × 5 values to 120, concatenate with 64-dimensional latent |
| Forecast head | Concatenate 64-dimensional latent with 8-dimensional calendar embedding; `Linear(72,24)` + Softplus | `Linear(184,64)` + ReLU + `Linear(64,24)` + Softplus |
| Non-encoder parameters | 2,720 | 13,400 |
| Total parameters | **41,696** | **52,376** |

The inspected state tensors confirm Hung calendar weight `(8,120)` and forecast weight `(24,72)`; Qyroven head weights are `(64,184)` and `(24,64)`. Both output 24 nonnegative hourly forecasts, but their parameter layouts cannot share a complete checkpoint or yield a same-weight forecast parity test without an explicitly reviewed mapping or one agreed architecture. Encoder/retention equality from the earlier audit is narrower. The bootstrap decision discrepancy and missing common runner trace also remain open.

The counts and shapes were recomputed by importing Hung's current `experiments.hung_sprint2.model.ForecastGRU` with `ModelConfig(calendar_hidden=8)` and the byte-pinned Qyroven model copy in ignored `.cache/parity-q-20261027-v1`, then listing non-encoder `state_dict` tensor shapes and summing parameters. No checkpoint was modified, no training ran and no Final/test outcome was read. A reviewer should choose the head and bootstrap conventions from Report 1 and Development protocol, then request one common input/weights/seed/schedule trace with declared tolerance. Historical results retain their original identities.
