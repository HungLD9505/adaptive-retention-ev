# Hung Sprint 2 #39 completion audit — 2026-10-25

Status: **in progress**. This audit distinguishes earlier Colab evidence from work executed on 2026-10-25. It does not accept #39, #19–#21 or the proposed Development settings.

## Acceptance matrix

| #39 area | Evidence available | Remaining gate | Independent confirmation |
| --- | --- | --- | --- |
| A: GRU, source transfer and retention | Draft #42; model/loss/checkpoint fixtures; three-seed 7-day UrbanEV Colab run in draft #44, with one full pass over 65,888 Source examples per seed | Review whether one pass and the proposed hyperparameters meet the agreed Development protocol; expand to 14/28-day budgets and representative entities; verify source checkpoint lineage for each run | Qyroven, then peer review of final PR head |
| B: confidence controller | Draft #43; deterministic fixture tests | Agree the Development-only lambda, confidence and missing-day bootstrap settings; compare decisions against the independent implementation on common inputs | Qyroven |
| C: runner, audit and resume | Draft #44; prior 7-day, two-entity/three-seed Development replay; checkpoint and event fixtures | Run selected 7/14/28-day cases through at least two block boundaries; verify CPU/CUDA resume, audit costs, coverage and full run handoff on actual inputs | Qyroven and PR reviewer |
| Capacity and Colab handoff | Existing CPU Colab measurements and create-only Drive evidence in #44; preliminary estimate in `hung-development-capacity-20261023.md` | Measure all three budgets and both initialization strata, including storage/failure rate; the old two-entity CPU extrapolation is not a full-matrix forecast | #21/#22 consumer review |
| Integration | #42, #43, #44 remain staged on separate dependent branches | Reconcile into one shared implementation, CI at final heads, independent approval and authorized merges in dependency order | Qyroven; third reviewer for joint code |

## New work actually performed on 2026-10-25

- Confirmed remote `dev` at `7a57e9e` and remote Stage A/B/C at `b76d62a`, `8f93d79`, `a70015c`. No reviews were returned for #42–#44 when checked. Work started from Stage C in a separate `codex/39-completion` branch; prior draft branches and untracked worktree files were not edited.
- Downloaded the UrbanEV input ZIP into this repository's ignored `data/inputs/downloads/` folder. Release catalog size **151,254,390 bytes**, SHA-256 **`2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`** and ZIP CRC passed. Extracted to new ignored input directories. All five artifact hashes and manifest identity passed for 7, 14 and 28 days. Manifest SHA-256: `fd1b5d1767e94a3e5c6f62447d446e1f13859b823c5fe14c51b5055d8e67169c`, `66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9`, `cdd43152bbda3de9f468938262a8bf00e041a9f264cf29051b71d06e788beadd`.
- Added CPU/CUDA device selection, device and peak CUDA allocation metadata, synchronized CUDA timing, paired CUDA RNG snapshots, and CPU-compatible runner checkpoint loading. This is code and small fixture evidence; no DATA-v1 model training was run in this pass.
- Predeclared verification and representative entities using Development `entities.jsonl` only, recorded in `hung-development-selection-20261025-v2.json`. SHA-256 order uses manifest digest and identity; no model score influences selection. Counts are 281/13 (adaptation/source-only) for 7 days, 282/14 for 14 days, and 283/18 for 28 days. The 7- and 14-day adaptation entities all have the same initial example count (6 and 13); 28-day entities have 26 or 27. Empty count groups stay empty rather than inventing sparse/dense strata. The first local selection artifact without this tie correction is retained as an untracked historical draft and must not be used.
- Added `development_config_v1.json` with the diagnostic values from the prior executed notebook and three fixed seeds. It is a proposal for team review, not a Final lock. Representative multi-seed Colab runs across all three budgets, comparison with Qyroven, and approval have **not** happened in this pass.
- Added `run_development.py` and an unexecuted thin Colab notebook. The driver verifies all three manifest/artifact sets and the predeclared selection before execution, records code/config/selection hashes in a create-only matrix identity, reuses only completed same-code stages, and checkpoints replay at 42 origins before resuming to 90. A pinned CUDA PyTorch requirement is separate from the CPU CI requirement. The notebook downloads the public DATA-v1 archive and still needs a pinned code bundle path/hash, commit SHA, unique run ID and execution in Colab.

### Bounded local GPU diagnostic completed after the initial audit

Using the predeclared **14-day verification** IDs and seed **7**, `run_development.py --phase verification --budgets 14 --seeds 7 --device cuda --execute` completed in the new ignored folder `runs/hung-39-local-gpu-20261025/`. The run used PyTorch `2.8.0+cu126` on the RTX 3050 Ti Laptop GPU. Source consumed all **65,888** examples in one pass (2,059 steps, 32.215 seconds). Target `1153` used all **13** initial examples (7 steps); target `2644` was correctly source-checkpoint-only (zero target steps). Both replays processed **90 scheduled origins** and completed **six** 14-day block decisions, so two boundaries were crossed.

| 14-day entity | Initialization | Created / scored / requested | Live MAE (kWh) | Replay CLI time | Peak CUDA allocation |
| --- | --- | --- | ---: | ---: | ---: |
| `1153` | target adaptation | 59 / 52 / 90 | 6.6906 | 11.754 s | 22,353,920 bytes |
| `2644` | source checkpoint only | 59 / 0 / 90 | undefined | 9.998 s | 10,753,024 bytes |

The second entity had **zero complete arrived label days**; no MAE is inferred. These are local diagnostics with a proposed configuration, one seed and two selected entities. They are not Colab acceptance evidence or a quality comparison. CLI durations include input checks but not archive download, Colab setup or Drive copy. Peak CUDA allocation is process-wide, while the existing `state_tensor_memory` records logical state tensors separately. A small timing probe using one real Development input and synthetic model/reference/latent scale measured median update steps of **11.251 ms CPU** and **7.618 ms CUDA** over ten measured repetitions after three warm-ups; it is recorded in `hung-device-benchmark-20261025.json` and is not a throughput forecast for the complete matrix.

The first 42→90 CUDA resume diagnostic exposed an event-order defect: a bounded replay ending exactly at a block boundary decided before labels that would arrive at the next origin. Its ignored output folder `runs/hung-39-cuda-resume-20261025/` is preserved as failed diagnostic evidence. The adapter now leaves that boundary decision pending until resume. A fresh run in `runs/hung-39-cuda-resume-fixed-20261025/` matched the uninterrupted 14-day replay exactly: **307 events, 59 issued forecasts, six decisions, all forecast tensors and candidate model weights**. The 42-origin checkpoint held two completed decisions; the next decision occurred after eligible late labels arrived. A new offline fixture tests this boundary behavior.

## Run and review sequence

1. Use the v2 selection file and versioned config to create unique Source, target and replay runs for seeds 7/11/19. Start with the verification IDs for each budget and require at least 42 scheduled origins to cross two 14-day boundaries. Keep the source-only stratum separate. Do not silently replace a failed run or shrink a target set after seeing metrics.
2. Check CPU and CUDA on an identical fixture and a bounded Development slice, then use the faster feasible device for a fixed config/run identity. The existing PyTorch environment on the Victus is `2.8.0+cu126` with RTX 3050 Ti Laptop 4 GiB. The project policy currently puts real training on Colab; any local GPU result requires an explicit recorded exception before it counts as acceptance evidence.
3. Extend to the predeclared representative set after the team accepts its coverage. Store forecasts, event journal, checkpoints, run manifests, code SHA, input hashes, seed, environment, timings, peak memory and artifact hashes in create-only run folders. The legacy 7-day Colab runs remain distinct.
4. Compare with Qyroven in order: predictions/latents/loss/gradients; controller decisions; boundary, audit and resume state. Fix mismatches with reproducible fixtures, then request independent review. Review/merge staged dependencies #42 → #43 → #44; never merge stacked duplicates independently.

Final/test remains unused for parameter selection. No claim of model effectiveness or full cohort coverage follows from the current smoke evidence.
