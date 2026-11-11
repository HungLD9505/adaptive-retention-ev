# Wider paired proposal screen

Exploratory Calibration only, following the paired pilot. No effectiveness guarantee. Existing model/loss/runner code was unchanged. One combined hypothesis was announced before outcomes: larger proposal magnitude with a stricter five-label acceptance gate. This does not isolate individual parameter effects.

Settings: eta 2112.950034305722, max lambda step 0.5, anchor trust radius 0.75, five complete pairs, at least four wins, median difference below -0.01 kWh, timeout nine issued days. Anchor remains 0.7984450067079901. Configs are `.cache/wide-paired-42.json` and `.cache/wide-paired-43.json` under `D:/Đồ Án/.cache/issue99-paired-pilot`.

Three real GPU runs completed using `python -m ev_runner.continuous_run` with the same verified Source10/input hashes and `--stop-after-ticks 22` as the preceding pilot. Outputs: `.cache/wide-paired-1405-42-v1`, `.cache/wide-paired-2152-43-v1`, `.cache/wide-paired-1693-42-v1`. Previous Fixed outputs were read without modification. Origin sets were checked equal for each pair; score events were averaged independently into `.cache/wide-paired-summary-v1.json`.

| Case | Scored days | Fixed MAE kWh | Candidate MAE kWh | Difference |
|---|---:|---:|---:|---:|
| 1405/42 | 20 | 5.3174939648 | 5.3174939648 | 0 |
| 2152/43 | 21 | 6.5391298204 | 6.5391298204 | 0 |
| 1693/42 | 21 | 2.5651248006 | 2.5651248006 | 0 |

Each run rejected three completed blocks and accepted none. The equality with Fixed is therefore a null result, not evidence that adaptive lambda improved forecasting. All three commands returned exit code zero; only the previously observed GRU performance warning appeared. No source-code changes or additional unit-test claim are made.

Read-only diagnosis of the previous pilot found 12/20 proposals saturated at the 0.05 step cap. However, accepted 1405 block 2 had daily differences approximately [-0.0423,-0.1024,+0.1300] kWh: the median gate can ignore a large harmful day even though the study objective is mean MAE. A stricter gate alone can instead leave the algorithm effectively Fixed, as here.

Decision: no full matrix promotion. A subsequent distinct hypothesis should align the acceptance statistic with mean MAE and evaluate persistent candidate trajectories, explicitly defining whether full model/Adam state is adopted. It needs a bounded Calibration pilot, then all four targets and three seeds before any later assessment. These repeatedly inspected slices cannot establish independent effectiveness. Do not keep tuning until a favorable tiny result appears.
