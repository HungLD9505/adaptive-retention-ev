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

## Block-7 Development variant (subsequent execution)

A separately pinned block-size-7 proposal was executed on the same representative UrbanEV/SZH Development cohort at code commit `a0edded8228e8a1b64b0aee18c2655d94a1c4144` (documentation-only successor of the integrated code above). The config SHA-256 was `1a3877487eda15c7b0f8c28e7efc677b4a38dc9f1b90d783387be80b34d63fb8`. An actual-input dry-run enumerated 9 Source, 69 target, and 138 replay commands. The CUDA execution then exited 0 with 216/216 stages. This is **one diagnostic variant**, not the complete matched nine-baseline/five-ablation matrix.

An external audit completed 216/216 stages, checked 354 hashes across 69 rows, and found zero missing. Its summary SHA-256 is `78ce835a322382d70f76470bebd51e59265fdf99ccf2375e528498448648377b`; 33 rows had no complete-label MAE and remain null. The first audit attempt correctly stopped without writing a summary because its new script expected the old split cursor 42; the block-7 run used cursor 21. After fixing those three audit-script references, the audit passed without retraining or changing run artifacts.

The complete block-7 run, checkpoints, forecasts, logs, audit and Git bundle are in the [Private block-7 Development archive](https://www.kaggle.com/datasets/hungluongduc/hung-urbanev-block7-dev-a0edded-20261026-v1). The uploaded `hung-matched-block7-development.zip.bin` is 252,607,537 bytes, SHA-256 `6191688c21da85640302d98a866e96bbb8829de07aa6ccdcf06ae77c36a9a8f8`; catalog SHA-256 is `d76feb68805533b9e812936ead8807a69bec2bc982927234e9b097b8ae285814`. The ZIP contains 576 members. Kaggle metadata reported `isPrivate: true`; all three remote files matched their expected size and SHA-256 via streaming readback without saving another ZIP locally. The readback proof SHA-256 is `0610fcfebbcb812dd4bab236a2a7e65bee399b847cf227da08712f0003a43f78`. Remove the `.bin` suffix after an authorized download and verify against the catalog before restoring.

## Finite Parameter Retention lambda selection (subsequent execution)

Before inspecting these outcomes, the Development-only grid fixed four Parameter Retention low levels (`0.1`, `10`, `1000`, `10000`), the corresponding high level at twice each low level, budgets 7/14/28 days, seeds 7/11/19, and the first declared verification entity per budget (`2264`, `1153`, `1165`). The accepted UrbanEV/SZH input handoff and predeclared selection were unchanged. All four grids ran on CUDA at code commit `ffa133686a81a375dd58c1030e4205fda45bc7e0`. Each run exited 0 with 9 Source, 18 Target and 36 replay stages, giving **252/252 completed stages** across the four candidates. The execute-log SHA-256 values for indices 0–3 are respectively `594f0f9ca0885c5946e0602451d3c0be655fd2c3f4607f3674ef2a707a44ed8a`, `3785450d2e0204734652dd02be5b514c641bac5fa085a4cd16c7d21b4d0cf6d5`, `db44887207b9e7f3bcef8093287758911d3471bb9b585ee7acfd2a7ed39c25d0`, and `1512b6c77fc00c4f71b5023707c99f66c5f6176db2ae546fcdbae3e0e83f0f18`.

The selector authenticated 36/36 declared adaptation cells against input, manifest, Source/Target/runner checkpoint and event-log hashes; it recomputed original-unit 24-hour MAE from accepted Development labels, required each causally available complete label to be scored, and checked issued/scored origins pair across lambdas. It averaged the three seeds within each budget, then averaged the three budget means equally, breaking an exact tie toward the smaller lambda. The create-only [selection proof](evidence/hung-parameter-lambda-selection-20261026.json) has SHA-256 `275f440d981f45d8b4ea69795d46859be40ed80dd851c32adc133d2832933e0b`.

| Low lambda | Equal-budget Development MAE (kWh) | Config SHA-256 |
| ---: | ---: | --- |
| 0.1 | 6.841455 | `c2069cfce96a72d05f03cdbc469798ae81814020ffd8fd48702f51502f778cc8` |
| **10** | **6.836163** | `8a71e084e62556940964b718652e3f8c1902325d950790e83d07e1bcc867b58d` |
| 1000 | 6.887297 | `ff38c4f2faa41aaa8c0072730b8b16c571ac1c19a0f278b7c1347bdf9e17a5cf` |
| 10000 | 7.020288 | `626491caed7bbf1868f181982241330eb412791083ca45a5bd9521d6a2988d61` |

The conditional Development choice is **low lambda 10**; it is not an independently approved Final lock or evidence of effectiveness. No test/Final data was used for the choice. The four output roots, checkpoints, forecasts, logs, configs, selector code/test, selection proof and Git bundle are in the [Private Parameter lambda archive](https://www.kaggle.com/datasets/hungluongduc/hung-urbanev-lambda-dev-ffa1336-20261026-v1). Its `parameter-lambda-development.zip.bin` is 256,605,000 bytes, SHA-256 `da715afc3bba78d5ed5c6c9edbbe116267c9de0a3460bb55f4720a99aa30a05b`; catalog SHA-256 is `422c8d17b778f05a1007cab1344e8b80bc493b72c76fc4b0937f3c6e95f60b9c`. The ZIP has 673 unique members and passed CRC readback. Kaggle reported `isPrivate: true`, `ready` version 1; all four remote files matched size and SHA-256 by streamed readback. The tracked [readback proof](evidence/hung-parameter-lambda-kaggle-readback-20261026.json) has SHA-256 `c6a083e79f8ae95cb45eb62f355110874284604beeb9ba72a4fee11c4c5b60c4`. An authorized reviewer can verify the four Dataset files against the proof and catalog, remove `.bin` from the ZIP name after download, then restore into a new directory.

## Scope and remaining acceptance work

The separate six-city CHARGED Development matrices retain their original code/run attribution; [PR #54](https://github.com/HungLD9505/adaptive-retention-ev/pull/54) records their archive proofs. This integrated UrbanEV execution does not complete Qyroven's separate Issue #23 recovery or certify those CHARGED runs as executed on commit `969f3de`.

Issue #39 still requires an actual Colab GPU run and Drive checkpoint/log handoff. Independent peer review, full matched comparisons and ablations, the immutable Final lock, Final execution, and final reporting remain open. Keep Issues #22/#23/#39 and PR #66 under review; do not treat this Development record as 100% task completion.
