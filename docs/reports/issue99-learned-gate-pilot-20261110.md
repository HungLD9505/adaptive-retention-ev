# Issue #99: causal learned skip-gate pilot (10 November 2026)

## Decision

**Do not adopt this gate.** A bounded, one-parameter-per-target online version of the proposed recent-load skip gate increased Calibration macro MAE from `5.2655613743` to `5.2983313810` kWh (`+0.0327700067`), and increased target 2152 MAE by `0.104878` kWh. It failed the proposed no-target-harm limit of `0.05` kWh. This is an exploratory pilot on already inspected Calibration dates, not an independent effectiveness test. It does **not** test a Source-trained contextual per-hour network gate; that larger model remains unimplemented and unproven.

## Method tested

Use each saved Fixed `lambda=0.5634538227695682` Source10 forecast `p_(t,h)`, the matching-hour previous-day energy `b_(t,h)=x_hist[h,0]`, and its availability mask `m_(t,h)=x_hist[h,6]`. Issue

```text
yhat_(t,h) = p_(t,h) + a_t * m_(t,h) * (b_(t,h) - p_(t,h))
```

At forecast origin `t`, collect only earlier issued forecasts whose **complete labels have arrived by t**, using the repository `Replay.labels(prior_origin, as_of=t)` gate. If fewer than five such pairs exist, set `a_t=0`. Otherwise select `a_t` on the fixed grid `{0, 0.005, ..., 0.5}` using the latest seven arrived pairs, minimizing mean normalized 24-hour forecast MAE plus `0.01*a_t²`, with smaller `a_t` as the tie-break. These constants were set before the run as a small engineering pilot; they were not optimized after viewing its scores. Scoring of the current day occurs only after all decisions have been issued. No training or Source checkpoint is changed, and masked hours exactly keep the Fixed forecast.

The run read 4 targets × seeds 42/43/44 × 19 registered Calibration origins. The base and gate received the same forecast inputs, labels, and complete-day coverage.

| Target | Fixed MAE (kWh) | Gate minus Fixed (kWh) | Scored days with gate > 0 |
| --- | ---: | ---: | ---: |
| 1405 | 5.464601 | +0.012475 | 17/57 |
| 2152 | 6.382483 | +0.104878 | 41/57 |
| 1153 | 6.856702 | +0.011787 | 6/57 |
| 1693 | 2.358460 | +0.001941 | 39/57 |
| **Equal-target macro** | **5.265561** | **+0.032770** | **103/228** |

The earlier 25% blend looked useful when applied retrospectively **only** to target 2152, but choosing that target and weight from the same Calibration outcomes was a hindsight oracle. The online gate correctly uses only prior arrived labels yet worsened 2152 in seeds 42/43; its selected coefficients reached `0.5`. This illustrates why retrospective per-target gains did not translate into a deployable causal rule. Do not continue tuning the seven-day window, penalty, maximum gate, or threshold on these same outcomes.

## Artifact identity and checks

- Worktree: `D:\Đồ Án\.cache\issue99-retention-audit`, branch `feat/continuous-retention-99`.
- Script: `.cache/issue99-learned-gate-probe-v1.py`, SHA-256 `7e760262663ee9bdc7d5bc1c0728072689a44663611f5ecc02fbe8f36421137a`.
- New output directory: `.cache/issue99-learned-gate-probe-v1/`; `summary.json` SHA-256 `609029e546c2d2ed85723528f6195466b8a7dc8e27e632a0604b2503be85539b`; `decisions.jsonl` SHA-256 `717712b4a09c47e98d4982a29b3bee7640b1040e3a46be1776ef46fbdde58d55`.
- Saved Fixed forecasts: `.cache/issue99-retention-screen-v2/mse-{target}-seed{42,43}` and `.cache/issue99-retention-seed44-v1/mse-{target}-seed44`. Each forecast file's SHA-256 was checked against its committed tick manifest before use. Input identity is the manifest SHA-256 in `configs/issue99-protocol-locked-v2.json`; the repository `InputRun` and `Replay` loader/gate were used.

An independent read-only audit recomputed **all 264 coefficient decisions** from only prior complete arrived labels and matched `decisions.jsonl` exactly. It also recomputed all 12 base/gate MAE cells, checked 228/228 unique registered Calibration scores, and matched each base cell to the saved Fixed summary. The script only added a gate prediction to in-memory rows; saved Fixed forecasts and historical runs were not changed. No Evaluation or Final score was used.

Commands: Ruff check/format check and `python -m py_compile` on the ignored pilot script; `PYTHONPATH=. python .cache/issue99-learned-gate-probe-v1.py`; independent decision/metric recomputation; `python -m tools.check_release`; `git diff --check`. No model code changed, no Kaggle job was submitted, and the full README unit suite was not rerun for this documentation-only change. No run error occurred. A separate contextual gate would need a versioned implementation and protocol, Source-only training identity, a fresh assessment window, and paired tests before any improvement claim.
