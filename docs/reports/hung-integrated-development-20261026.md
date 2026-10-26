# Hung integrated Development execution and artifact handoff — 2026-10-26

Refs #22, #23, #39. This is an execution record for the integrated code at commit `969f3deca111e998b197fedd869e891c753a4417` in draft PR #66. It is **Development diagnostic evidence**, not Final evaluation, peer acceptance, or a claim of research effectiveness.

## Actual UrbanEV/SZH execution

The representative Development matrix used the frozen input handoff `issue18-input-handoff-v1-20261019`, the predeclared selection `hung-development-selection-20261025-v2.json`, budgets 7/14/28 days, seeds 7/11/19, and CUDA. `python -m experiments.hung_sprint2.run_development ... --phase representative --device cuda --budgets 7 14 28 --seeds 7 11 19 --execute` exited 0. It completed 9 Source, 69 target, and 138 replay stages (216/216 total). An independent create-only audit checked 354 artifact hashes across 69 rows with zero missing. The audit summary SHA-256 is `1a43169511809122a827cefd2865f171cccac8b955d4774c490279686fd125b8`; the matrix identity SHA-256 inside it is `b7245353deb45159e966d28deeb1417dcbe08cc55ea594dcae571a64d056a727`. The run included incomplete-label rows; a missing MAE is not converted to a numeric result.

The complete run, checkpoints, forecasts, logs, audit, and Git bundle are in the [Private UrbanEV Development archive](https://www.kaggle.com/datasets/hungluongduc/hung-urbanev-dev-969f3de-20261026-v1). The uploaded `integrated-development.zip.bin` is 256,959,184 bytes, SHA-256 `fea734a652265fa3b0ebef1078db6b013b2f1ccea6a2704984634ff0104449c3`; its catalog SHA-256 is `aa58dacaf6b28fb04a92b172a382aa3a88d279d00d3f4c95ca0b0da99965c565`. The ZIP contains 576 members. Kaggle metadata reported `isPrivate: true`; all three remote files were downloaded and matched their local SHA-256 and sizes. The local readback proof SHA-256 is `8ddd5f1ec23d835a3e63995302f6c49651edfcd1a0968fa87955228ea1430a0b`.

## Finite proxy calibration on Development

Before examining performance, the calibration preflight selected the first declared verification entity for each budget and seeds 7/11/19: nine cells in all. The pinned plan SHA-256 is `ba8952beb1ffb7527c6bf6fa11fc4be5c42553051fd02494354220e635672aa5`. `python -m tools.hung_proxy_calibration run --plan ... --plan-sha256 ... --output ...` exited 0 with 108/108 declared recipe runs. `python -m tools.hung_proxy_calibration select --plan ... --plan-sha256 ... --runs ... --output ...` exited 0 after authenticating all runs. The selection file SHA-256 is `7b7277716552978bfe59aaa32ad03a3204ae3f997b056db6edf2bafe3ad814b5`; it records 9 cells, 108 runs, and zero null run cells.

| Proxy | Provisional recipe | Equal-budget Development MAE (kWh) |
| --- | ---: | ---: |
| `drift` | 1 | 6.817828 |
| `source_error` | 1 | 6.837713 |
| `uncertainty` | 3 | 6.830755 |

These are conditional choices from one verification entity per budget, aggregated across the declared seeds. They do not establish generalization, an approved method choice, or a Final result. No test/Final data was used to choose the recipes.

The complete calibration plan, 108 run manifests, event logs, runner checkpoints, selection, and Git bundle are in the [Private proxy calibration archive](https://www.kaggle.com/datasets/hungluongduc/hung-urbanev-proxy-cal-969f3de-20261026-v1). The uploaded `proxy-calibration.zip.bin` is 233,079,369 bytes, SHA-256 `7b99f109ed8bf5b2930b323f79d24bea519223df8198cf59ee0963cccbff6b3c`; its catalog SHA-256 is `92cc7c4874b1b93193e145a4fcaed2ac7e23136eed42e0ddc7313ccfa63e1c1f`. The ZIP contains 334 members. Kaggle metadata reported `isPrivate: true`; all three remote files were downloaded and matched SHA-256 and size. The local readback proof SHA-256 is `762e003a325162db7544bcce2369634fdb8b188090c530abb95aa33bb001831a`.

For either archive, an authorized reviewer should download the three Dataset files, verify the transport map and catalog SHA-256, remove the `.bin` suffix from the ZIP, then restore the ZIP. The original large run artifacts remain outside Git.

## Scope and remaining acceptance work

The separate six-city CHARGED Development matrices retain their original code/run attribution; [PR #54](https://github.com/HungLD9505/adaptive-retention-ev/pull/54) records their archive proofs. This integrated UrbanEV execution does not complete Qyroven's separate Issue #23 recovery or certify those CHARGED runs as executed on commit `969f3de`.

Issue #39 still requires an actual Colab GPU run and Drive checkpoint/log handoff. Independent peer review, full matched comparisons and ablations, the immutable Final lock, Final execution, and final reporting remain open. Keep Issues #22/#23/#39 and PR #66 under review; do not treat this Development record as 100% task completion.
