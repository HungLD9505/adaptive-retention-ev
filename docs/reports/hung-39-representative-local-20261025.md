# Phase D — Representative Development, local CUDA, 2026-10-25

## 1. Objective & Scope

**216/216 stages and 69/69 entity × budget × seed cells completed and passed audit.** This expands #39/#19/#20/#21 Development evidence using diagnostic config v1. Config suitability, Source sufficiency, independent comparison and research effectiveness remain subject to review. Final/test was unused.

## 2. Methodology

Each budget/seed trains one Source pass, initializes selected targets, replays 42 scheduled origins, then resumes to 90. Selection v2 fixes 6/8/9 entities for 7/14/28 days and seeds 7/11/19. Forecasts precede labels; scoring/update requires all 24 valid labels. Entity, lambda, seed, batch and CUDA device remained fixed after outcomes were observed.

## 3. Implementation

Executed commit: `a34a49e5f04920ef30456fe6c0ea56eb2f1d659a`, branch `codex/39-completion`. The existing core modules and `run_development.py` executed the matrix. Exact source hashes/worktree status are embedded in the [evidence JSON](hung-39-representative-local-20261025-evidence.json). Later notebook/RNG handoff changes were not used in this run.

Python 3.13.7, PyTorch 2.8.0+cu126, CUDA 12.6, RTX 3050 Ti Laptop GPU (4 GiB). Before execution: 63,845,855,232 free disk bytes. README specifies Python 3.12; the actual version is disclosed. Historical selection draft, existing runs and `results.zip` were preserved.

## 4. Input

DATA-v1 UrbanEV SZH ZIP: 151,254,390 bytes; SHA-256 `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`. Fresh ZIP integrity and all input-manifest/artifact checks passed. Shapes: `X_hist[B,24,7]`, `C_future[B,24,5]`, output `[B,24]`. Source uses the permitted pre-deployment Source set; target/replay use Development.

| Budget | Manifest SHA-256 |
| --- | --- |
| 7d | `fd1b5d1767e94a3e5c6f62447d446e1f13859b823c5fe14c51b5055d8e67169c` |
| 14d | `66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9` |
| 28d | `cdd43152bbda3de9f468938262a8bf00e041a9f264cf29051b71d06e788beadd` |

## 5. Configuration

Config SHA-256 `20cb0f0962af6e3f3781ef9bebdf03c162548e06894ae4b59ddc1d58be277ba0`; selection v2 SHA-256 `840ea1984592d920b513cbf5c7a67eb370227111b3f609040d12a2f720b12b56`.

Source: one pass, batch 32, LR 0.001; every Source stage used 65,888 examples/2,059 steps. Target: one pass, batch 2, LR 0.001, retention weight 0.1, epsilon 1e-6; source-only has zero adaptation steps. Replay: levels 0/0.1/0.2, initial 0, block 14, Bmin 5, delta 0, alpha 0.05, two-challenger Bonferroni, segment 2 days, 100 resamples. These remain diagnostic choices.

## 6. Output

Run root: `runs/hung-39-representative-local-20261025T2103/`: 9 Source, 69 target and 138 replay stages with manifests/checkpoints/journals and stored forecast tensors. The evidence JSON provides all 69 result rows, costs, updates, memory, identity and per-file SHA inventory.

Archive: `runs/hung-39-representative-local-20261025T2103.zip`, 249,622,687 bytes, 573 files, SHA-256 `7d74ec06f9102d1a7357da380bc252570cab2a817a9fcce48030f89c3311f2fa`. ZIP CRC and SHA readback of every member passed. Large artifacts remain outside Git.

## 7. Experimental Results

| Budget | Entities × seeds | Stages | Requested / issued / scored days | Null cells | Switch / keep | Stage CLI seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 7d | 6 × 3 | 57/57 | 1,620 / 1,341 / 693 | 9 | 12 / 96 | 662.59 |
| 14d | 8 × 3 | 75/75 | 2,160 / 1,293 / 735 | 12 | 11 / 133 | 1,145.78 |
| 28d | 9 × 3 | 84/84 | 2,430 / 1,512 / 894 | 12 | 9 / 153 | 1,136.03 |

Every replay-90 reached cursor 90 and six decisions. Filesystem timestamps from identity creation to last stage: 21:00:54.855–22:08:29.106 Vietnam time, 4,054.25 s. Total stage CLI time: 2,944.40 s. Source times: 31.17–60.42 s. Maximum recorded CUDA allocated memory: 85,135,360 bytes (81.19 MiB), excluding non-PyTorch GPU allocations.

Per-cell MAE/RMSE kWh, initialization, coverage, switch/keep, Source/target steps, candidate/audit updates, stage duration and logical state memory are in evidence JSON `rows`. Shared Source time must not be summed once per entity. This selection does not support a pooled cohort score or budget ranking.

## 8. Correctness & Validation

| Executed command/check | Result |
| --- | --- |
| `python -m tools.sources list` | PASS |
| `python -m experiments.hung_sprint2.cli verify-input-zip --archive data/inputs/downloads/inputs-urbanev-SZH-v1.zip --package inputs-urbanev-SZH-v1.zip` | PASS |
| `python -m unittest tests.test_hung_completion -v`, repo-local TEMP/TMP | PASS, 2 tests |
| `python -m unittest discover -s tests -q`, repo-local TEMP/TMP and PYTHONUTF8=1 | PASS, 174 tests, 1 skip |
| Ruff check/format at execution head | FAIL: existing unused import/format in unexecuted Kaggle notebook; repaired later for handoff |
| `git diff --check` | PASS |
| Global `python -m pip check` | FAIL: pre-existing ultralytics 8.3.82 versus numpy 2.4.2 requirement conflict |

Default Windows temp/cp1252 caused initial permission/Unicode failures; repo-local TEMP/TMP and UTF-8 resolved the tests. Pinned Ruff 0.17.0 was installed into ignored `.deps`.

Post-run audit verified **354/354 checkpoint/journal hashes**, stage identity, input lineage and replay 42→90 lineage, with no missing stage. State readback checked 138 replay checkpoints, 20,394 forecast tensors and 18,313 journal events. All 69 live metrics were recomputed from stored predictions/labels: 33 null rows remained null; maximum absolute MAE/RMSE difference 3.55e-15 kWh (tolerance 1e-4).

A real 14d/seed-7/entity-1153 checkpoint restored active model on `cuda:0`, optimizer state, cursor 90 and matching CPU/CUDA RNG. No training was repeated in readback.

## 9. Discussion & Limitations

Each selected source-only entity has 90 label records but zero complete 24-hour valid label days. Missing hours: 7d `1050:708, 1200:1062, 2447:1270`; 14d `1025:1540, 2613:1057, 2644:1061`; 28d `1188:1061, 1251:1168, 1408:1179`. All 27 source-only cells therefore retain null metrics.

The other six null cells are adaptation entity `1987`, 14d/28d × three seeds: 3 forecasts issued, zero scored days, 2,156 missing hours in 90 label records. Initial pre-deployment examples do not imply later replay coverage. Missing labels were not filled. Upstream reasons for missing observations and coverage outside this slice remain unverified.

Execution success does not establish improvement over baselines. Config/Source-pass approval, independent comparison, peer review, #22 baselines/ablations and #23 Final remain open.

## 10. Reproduction & Freeze

With `PYTHONUTF8=1` and TEMP/TMP set to `.cache/testtmp`, the exact matrix command was:

```powershell
python -m experiments.hung_sprint2.run_development --input-base data/inputs/issue18-input-handoff-v1-20261019 --selection docs/reports/hung-development-selection-20261025-v2.json --config experiments/hung_sprint2/development_config_v1.json --output-root runs/hung-39-representative-local-20261025T2103 --phase representative --device cuda --budgets 7 14 28 --seeds 7 11 19 --execute
```

Audit executed: `python runs/hung-39-representative-local-20261025T2103/audit_representative.py` → 216 stages, 354 hashes, 69 rows, 0 missing. Its summary is create-only; do not rerun into the existing summary file. State/metric readback and archive checks are embedded in the evidence JSON.

Historical reproduction/resume requires commit `a34a49e` and matching CUDA dependencies; a new backend/code/config needs a new output root. This matrix is complete and frozen. See Phase E for artifact retrieval, notebook validation and remaining platform/review gates.
