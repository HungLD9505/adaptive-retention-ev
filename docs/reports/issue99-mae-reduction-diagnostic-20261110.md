# Issue #99: where a larger MAE reduction may come from (10 November 2026)

## Decision

The completed local Calibration probes do **not** establish a reliable global MAE reduction of at least `0.05` kWh from changing only retention shape, a single global lambda, a naive lambda controller, a hard target-specific lambda map, a hard causal expert gate, or freezing the entire encoder. Keep the existing #99 Fixed pair as the supported reference. The largest apparent gains are target-dependent and are concentrated in different mechanisms; they were discovered on already inspected Calibration dates.

The next separate method study should test a **learned, mask-aware recent-load skip gate** in the forecast head, because the current GRU head sees recent energy only through a 64-dimensional encoder state, while the 24 matching hours from the preceding day are directly available in the historical input. A fixed 25% blend helped target 2152 but harmed other targets; a learned gate can condition that shortcut on available history and calendar context. This is a mechanism hypothesis, not a proven improvement. Residual/skip forecasting has precedent in [short-term load forecasting research](https://arxiv.org/abs/1805.11956), but that paper does not establish effectiveness for this UrbanEV cohort.

## Local evidence and limits

All metrics below use the same 19 registered **Calibration** origins per target, not Evaluation or Final. The MSE retention / Fixed `lambda=0.5634538227695682` baseline has 4 targets × 3 seeds macro MAE `5.265561` kWh.

| Diagnostic | Observed result | Why it is not a supported replacement |
| --- | --- | --- |
| Target-specific MSE lambda selected on seeds 42/43: `1405→1`, `2152→0.25`, `1153→4`, `1693→0.25` | Two-seed macro gain `0.092637` kWh; three-seed gain `0.060620` kWh. | Seed 44 macro was worse by `0.003414` kWh; target 2152 three-seed mean worsened by `0.078807` kWh, above the `0.05` harm limit. |
| Only target 1153 uses MSE `lambda=4` | Three-seed macro gain `0.056698` kWh, inferred from saved paired runs. | Target and value were selected after viewing all three seeds on these same dates. This is a hindsight oracle, not a deployable selection rule. |
| Only target 2152 blends 25% matching-hour previous-day energy with the Fixed forecast | Target 2152 MAE `6.382483→6.166969` kWh across three seeds; hypothetical macro gain `0.053878` kWh. All 57 day-level historical vectors had 24 present energy hours. | Target and blend coefficient were selected from these Calibration scores. Applying the same blend globally worsened macro `5.265561→5.569925` kWh. |
| Causal online hard gate for the 25% blend, using at least five prior complete arrived labels and recent seven-label mean gain ≥`0.05` kWh | 228/228 Calibration forecasts scored; macro `5.265561→5.266825` kWh. | The gate worsened aggregate MAE despite using only available past labels for decisions. |
| Causal online gate for the target-1153 `lambda=4` expert, same five-label/seven-label rule | Target 1153 mean `6.856702→6.758794` kWh, but seed 44 worsened by `0.021602` kWh; macro gain if other targets stay Fixed is only `0.024477` kWh. | Requires two trained target branches; falls short of the gain gate and is not a single-branch controller. |
| Frozen Source encoder, train target forecast head only, `lambda=0` | Seeds 42/43 macro `5.271401→5.248836` kWh (gain `0.022565`). | Target 2152 worsened `0.106566`, target 1693 worsened `0.086944` kWh. The method uses a local monkeypatch and no formal resume binding. |

The target-specific lambda map was locked after inspecting seeds 42/43, then run on seed 44. Its seed-44 four-target macro was `5.257296` versus Fixed `5.253882`. The new script `.cache/issue99-target-lambda-seed44-v1.py` has SHA-256 `494f875290f26b74bdf7df308af0be68f007fbfb0860fb573c159edcfb9b9e9d`; output `.cache/issue99-target-lambda-seed44-v1/summary.json` has `18d79ff1272ed0a344d700530b6a87e26e6adbd7776fe8d7733684a339a49ab9`. An independent pass recomputed all 76/76 Calibration scores and MAE/RMSE from tick events.

The head-only probe script `.cache/issue99-head-only-probe-v1.py` has SHA-256 `19bddcc0dd5beb25230b546c2ff7e425ac18ef982d7b72362cf281ba1d8d00f6`; output `.cache/issue99-head-only-probe-v1/summary.json` has `255984d6fbf2a42c3d719d941be4552656caab14a508f7221e21ccb6faefe725`. Eight runs completed with 152/152 unique Calibration scores, independently recomputed from events. The encoder-freeze monkeypatch is not represented in the standard run code fingerprint; no formal resume claim is made. The persistence/blend and causal-gate figures were read-only calculations from saved Fixed or paired forecast events; no separate versioned script or independently audited result bundle was created for them. Treat them as exploratory diagnostics, not locked study output.

## Next separate method proposal

For forecast origin `t`, let `p_h` be the current GRU forecast for horizon hour `h`, `b_h = x_hist[h,0]` the same-hour energy from the previous day, and `m_h = x_hist[h,6]` its observed-energy mask. A candidate output is

```text
alpha_h = sigmoid(g_phi(z, future_calendar_h, history_summary_h))
yhat_h = (1 - m_h * alpha_h) * p_h + (m_h * alpha_h) * b_h
```

Initialize the gate close to zero so the existing GRU prediction is the starting behavior. For a cheap first pilot, keep Source10 GRU weights and latent scale unchanged, fit a separate small gate on Source-only rows with forecast MAE and a penalty against large gate values, then adapt only its small target parameters using the allowed prefix and arrived complete labels. Save the gate checkpoint and its training identity separately. The mask forces `alpha_h=0` for unavailable historical energy, and the same-hour history is known at issuance. Keep nonnegative output through the convex blend. If a later study jointly retrains the GRU/head, it needs new Source checkpoints and latent scales; do not substitute those into historical Source10 runs or compare unmatched initializations as if paired.

First run a bounded 4-target × 3-seed Calibration pilot with a versioned code/config and exact paired no-gate control, logging per-target/horizon MAE, gate weights, missing-hour coverage, runtime and VRAM. Stop if macro gain is below `0.05` kWh, any target mean worsens by more than `0.05` kWh, or cost exceeds the declared budget. Predeclare all choices before a scored search. Because the current Calibration and Evaluation results have already been inspected, any result on them is exploratory; obtain a genuinely uninspected Development cohort or later period before claiming independent improvement. Do not use Final to design or choose the gate.

Commands in this follow-up: Ruff check/format check and `python -m py_compile` for both new ignored scripts; `PYTHONPATH=. python .cache/issue99-target-lambda-seed44-v1.py`; `PYTHONPATH=. python .cache/issue99-head-only-probe-v1.py`; Python aggregation against prior summaries; independent event recomputation; `python -m tools.check_release`; `git diff --check`. PyTorch emitted a non-contiguous GRU-weight performance warning, but no run failed. No tracked model/controller code was changed or Kaggle job submitted. The full README unit suite was not rerun for this report-only change.
