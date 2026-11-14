# Issue #99: small Calibration screen of retention penalties (10 November 2026)

## Decision

**Keep the current Source-scaled latent MSE retention** for #99. Among four prespecified penalties at the previously selected Fixed `lambda = 0.5634538227695682`, it had the lowest mean MAE across four targets and seeds 42/43. The closest candidate, pseudo-Huber with `delta=2`, remained worse after a separate seed-44 check. The observed differences are small, the Calibration window was already explored in earlier #99 work, and each new penalty would need its own lambda calibration. This is an exploratory local ranking, not proof that MSE is globally optimal or an independent test result. No new formula is promoted to Kaggle or the scored protocol.

## Experimental design

All runs used authenticated UrbanEV 14-day input, Source10 checkpoint for the matching seed, a fresh target clone and Adam state, the same initial adaptation, forecast MAE, chronological 22-tick replay, and the 19 registered **Calibration** score origins per target. The controller was frozen at the same Fixed lambda in every arm. Only `ev_models.training.retention_loss` was replaced in memory for candidate arms; the target predictor, labels, scale, and update schedule were unchanged. The script did not read Evaluation or Final scores.

Let `u = (z_target - stopgrad(z_source)) / (stopgrad(source_scale) + epsilon)` and `q_i = mean_k(u_ik²)` for day `i`. The screened penalties were:

| Arm | Retention penalty |
| --- | --- |
| `mse` | `mean(u²)`; repository/Report 1 formula |
| `mixed` | `0.5 mean(u²) + 0.5 mean[2(sqrt(1+u²)-1)]` |
| `window_log` | `mean_i log(1+q_i)` |
| `pseudo_huber_2` | `mean[8(sqrt(1+u²/4)-1)]` |

The candidate penalties match MSE's quadratic behavior near zero while reducing the influence of large latent differences. These shapes and constants were selected for a bounded diagnostic, not calibrated for best performance. A prior two-target probe of pure pseudo-Huber `delta=1` also failed to improve the mean; see `issue99-formula-probe-20261110.md`.

## Results

The first screen completed 4 targets × 2 seeds × 4 penalties = **32 runs**, with 608/608 unique Calibration scores. An independent read-only pass recomputed MAE/RMSE from saved score events and matched all summary cells to tolerance `1e-12`; the eight MSE cells also matched the prior Fixed probe exactly.

| Arm | Equal-cell mean MAE, seeds 42/43 (kWh) | Difference from MSE (kWh) | Paired cells improved |
| --- | ---: | ---: | ---: |
| **MSE** | **5.271401** | **0** | reference |
| Pseudo-Huber `delta=2` | 5.274009 | +0.002608 | 4/8 |
| Window log | 5.276187 | +0.004786 | 3/8 |
| Mixed | 5.282248 | +0.010847 | 2/8 |

After MSE ranked first, only MSE and the nearest candidate were run on seed 44: 4 targets × 2 penalties = **8 more runs**, with 152/152 unique Calibration scores. The resulting 12-cell MAE was **5.265561** kWh for MSE and **5.267017** kWh for pseudo-Huber `delta=2`, a candidate-minus-MSE difference of **+0.001455** kWh. The three-seed target mean differences were `+0.002656` (1405), `+0.001252` (2152), `+0.005268` (1153), and `-0.003354` (1693). No candidate showed a practically meaningful macro gain; the prior proposed local promotion threshold was at least `0.05` kWh without target harm above `0.05` kWh.

The first MSE run incurred GPU warm-up, so sequential wall-time sums are not a fair speed ranking. PyTorch emitted a non-contiguous GRU-weight performance warning; all 40 runs completed. Seed 44 checks seed variability for the nearest candidate, but it reuses the same dates and is not a new temporal holdout. The old Fixed lambda was selected for MSE; a fair scored comparison of new losses would require recalibrating lambda on Calibration and evaluating on a truly uninspected Development window. Existing #99 Evaluation results have already been viewed, so they cannot serve that role for method selection.

## Artifacts, identity, and checks

- Worktree: `D:\Đồ Án\.cache\issue99-retention-audit`, branch `feat/continuous-retention-99`.
- Screen script: `.cache/issue99-retention-screen-v2.py`, SHA-256 `95f6cca978749d89cf9f5e5f7334df8552cb64994c2f5b1e22456688499e684b`; output `.cache/issue99-retention-screen-v2/summary.json`, SHA-256 `c3b4fe48b850a9049a944e12734b8491f480560f252e47295b8582c83aad3202`.
- Seed-44 script: `.cache/issue99-retention-seed44-v1.py`, SHA-256 `3a36e8620d21a097b2d5c65dde12a1c48b6cf02572c5d85330ad162fd0f87822`; output `.cache/issue99-retention-seed44-v1/summary.json`, SHA-256 `7202ef7aa653f8b29d439266f451a90e9735bc8ba167a282489f9e3a591b09ea`.
- Each output directory has separate per-arm/target/seed run directories with tick events and run metadata. These are ignored local artifacts; no historical output was overwritten. Source and input hashes are bound through `configs/issue99-protocol-locked-v2.json` and checked by the repository loader at each run.
- The in-memory loss monkeypatch is **not** represented in the standard runner code fingerprint or run ID. Interpret these diagnostics together with the exact script hash; a formal study would need a tracked `loss_variant` setting, versioned protocol, and corresponding resume/hash tests.

Commands run: `python -m py_compile` on both scripts; Ruff check and format check before execution; `PYTHONPATH=. python .cache/issue99-retention-screen-v2.py`; `PYTHONPATH=. python .cache/issue99-retention-seed44-v1.py`; independent recomputation from tick `events.jsonl`; Python aggregation of both summaries; `python -m tools.check_release` (passed: 17 report files, 92 historical source pins); and `git diff --check` (passed after staging). No code module or scored protocol changed; the full README unit suite was not rerun for this documentation-only addition.
