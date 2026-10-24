# #39 Development verification — local GPU, 2026-10-25

Status: **executed local diagnostic; not Colab or team acceptance**. All inputs came from DATA-v1 Development. No Final/test labels were read or used to select a configuration. This is the predeclared verification set, not the representative set or full cohort.

## Run identity and integrity

- Output: ignored `runs/hung-39-local-multibudget-20261025/`, created separately from earlier runs. Code commit `edef07db5d46e3b2797bc7c760786fd34202fb27`; versioned selection `hung-development-selection-20261025-v2.json` and `development_config_v1.json`; device RTX 3050 Ti Laptop GPU with PyTorch `2.8.0+cu126`. Seeds were fixed at 7, 11, 19.
- Matrix started 03:08:36 and the final manifest was written 03:28:27 Asia/Saigon (19 min 51 sec elapsed). The sum of the 63 recorded CLI stage durations was 901.47 sec; this excludes process startup/gaps and is not a Colab timing estimate. The run has 163 files occupying 73,069,805 bytes.
- All **63/63** stage manifests report `completed`: nine Source, 18 target initialization and 36 replay stages (42 and 90 origins). Recomputed SHA-256 values matched **99/99** recorded checkpoint and event-journal hashes. Each replay-90 has `runner_cursor=90`, resumes from its same-entity replay-42 checkpoint, and records six 14-day decisions. No stage was overwritten.
- Each Source seed/budget used all **65,888** available Source examples in one pass, **2,059** batch-32 steps. Individual Source CLI durations were 31.67–40.82 sec; peak CUDA allocation was 81.2 MiB. This establishes execution, not adequacy of one-pass Source training.

## Replay outcomes by predeclared stratum

`Created/scored` counts forecast days. MAE/RMSE are live forecast errors in kWh where labels were available; `—` means undefined because zero forecast days were scored. Values below are rounded for display; run manifests retain full precision. All rows requested 90 origins and made six block decisions.

| Budget | Seed | Adaptation entity: created/scored | Live MAE / RMSE kWh | Switches | Source-only entity: created/scored | Live MAE / RMSE |
| --- | ---: | --- | ---: | ---: | --- | --- |
| 7d | 7 | `2264`: 90/90 | 3.661 / 5.912 | 1 | `1050`: 90/0 | — |
| 7d | 11 | `2264`: 90/90 | 3.573 / 5.846 | 2 | `1050`: 90/0 | — |
| 7d | 19 | `2264`: 90/90 | 3.633 / 5.855 | 2 | `1050`: 90/0 | — |
| 14d | 7 | `1153`: 59/52 | 6.691 / 8.967 | 1 | `2644`: 59/0 | — |
| 14d | 11 | `1153`: 59/52 | 6.598 / 8.891 | 1 | `2644`: 59/0 | — |
| 14d | 19 | `1153`: 59/52 | 6.491 / 8.800 | 1 | `2644`: 59/0 | — |
| 28d | 7 | `1165`: 59/52 | 10.382 / 13.574 | 1 | `1188`: 59/0 | — |
| 28d | 11 | `1165`: 59/52 | 10.524 / 13.730 | 1 | `1188`: 59/0 | — |
| 28d | 19 | `1165`: 59/52 | 10.320 / 13.527 | 1 | `1188`: 59/0 | — |

The source-only entities had no complete arrived label days in this bounded slice. Their forecasts, event logs and decisions are present; no error metric is inferred. Different budgets/entities have different scored-day coverage, so these MAEs are **not** a model or budget ranking. The selected Development configuration remains diagnostic.

## Limits and next gates

- These runs used the local Victus GPU, while the current #39 training acceptance path calls for Colab or an explicit recorded local exception. Colab execution is still unverified. In the first Colab attempt, Source failed on Google Drive FUSE when saving a checkpoint with a hard link; the Colab output iframe also failed to load JavaScript. The failed Colab folders and logs remain on Drive. A create-only fallback fix is committed separately as `9580c9e` and tested on Windows, but has **not** yet been run on Colab.
- Representative Development coverage, independent comparison with Quyền, review of #42→#44/#46, and team acceptance remain outstanding. No claim is made for #21/#22 full-matrix capacity or effectiveness.
