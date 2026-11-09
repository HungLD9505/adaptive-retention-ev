# Issue #99 paired Development comparison, protocol v2

The [saved Kaggle comparison](https://www.kaggle.com/code/hungluongduc/issue99-source10-2798384-paired-comparison-v2) Version 1 (run `367824175`) reported `60` `job_completed` events, `matrix_verified`, no failed jobs, and `version_finished`. The saved verification JSON showed SHA-256 `c3038079cd65f575851dfd53be139017c6ad95aad087d7a3817dcd34a3d6bfed`, matching the logged hash. This is a log-bound Kaggle readback; the output bytes have not been downloaded for local, independent hash verification.

## Bound execution

- Scorer code commit: `27983845b5d446e3915b0b4353570466f1da23ef`; [protocol v2](../../configs/issue99-protocol-locked-v2.json) SHA-256 `f104d8809e04d0cde7d8982efd8146788f32c3c9a1c561ee9309891e6b040eb0`; [comparison lock](../../configs/issue99-comparison-lock-v2.json) SHA-256 `209102126ca696c5da2e959b053cc413d0e8d59fda3f92b30168a7a483577269`.
- The uploaded comparison runner from commit `2c9a348` had SHA-256 `350cca0dd5e1721497c13723f23fcfad913bf108da503c81a8b0f2aa2b9130a8`. The current tracked runner has SHA-256 `732d6b6944645cb5d955ffb236089566915afdd75f61660251b7081d80d665e7` after Ruff formatting commit `3744d32`; its AST SHA-256 remained `21a6e38c0bfbf0576215276b71e647f8ffd3cf63df6953877a1664dd939ec79a`. The saved run used the uploaded bytes, not the later formatted file.
- Kaggle reported 777.4 seconds for the version; the dispatch log recorded 728.63933 seconds. Its cumulative budget debit was 2528.63933 seconds, including a conservative 1800-second charge for prior work, so that debit is not a measured wall time. Final output size was 3,910,165,244 bytes.

## Reported MAE (kWh)

These values come from the saved comparison verification preview. The macro is the equal-station mean after averaging the three paired Source10 seeds within each station. Columns retain the registered method identities.

| Target | λ=0 | Fixed λ=0.5634538227695682 | Old discrete | Continuous Adam | Frozen λ=0.1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1153 | 6.427889 | 6.265896 | 6.312769 | 6.484508 | 6.486730 |
| 1405 | 5.805606 | 5.454826 | 5.545440 | 5.710284 | 5.710324 |
| 1693 | 2.064763 | 2.126269 | 2.091307 | 2.147728 | 2.075754 |
| 2152 | 6.011299 | 5.918735 | 5.939886 | 5.940918 | 5.939886 |
| **Macro** | **5.077389167412713** | **4.941431498059513** | **4.972350274324078** | **5.0708594517889924** | **5.05317344024457** |

Fixed has the lowest reported macro MAE in this comparison. The continuous controller's reported macro MAE exceeds Fixed by about 0.1294 kWh and the old discrete controller by about 0.0985 kWh. At target 1693, λ=0 has the lowest reported target mean. These are descriptive comparisons only: this Development cohort and historical aggregate outcomes had prior exposure, so the later chronological window is exploratory, not an untouched test. No Final replay was run for issue #99, and protocol v2 results must not be pooled with the failed protocol v1 search.

## Coverage readback

The saved verification JSON's 60 coverage entries were opened in the Kaggle UI. Every method and seed had `evaluation_scored_days = 28` for its target. The following issued/scored counts cover the **full 90-day replay**, including days outside the 28-day Evaluation objective.

| Target | Full-replay issued days | Full-replay scored days | Evaluation scored days |
| --- | ---: | ---: | ---: |
| 1405 | 90 | 89 | 28 |
| 2152 | 59 | 52 | 28 |
| 1153 | 59 | 52 | 28 |
| 1693 | 59 | 52 | 28 |

These counts were read in Kaggle, not recomputed from locally held forecasts and labels. The complete output remains there. Browser automatic approval denied downloading it, and the owner cannot transfer it manually at present. Local possession, independent file-hash and metric checks, further diagnostics analysis, and PR review/merge remain outstanding. The PR is not merged and issue #99 is not complete.
