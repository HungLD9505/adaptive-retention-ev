# #39 Phase C — prequential runner and inference

Evidence date: 2026-10-25. Runtime code snapshot `a34a49e5f04920ef30456fe6c0ea56eb2f1d659a`; local representative run `hung-39-representative-local-20261025T2103`. Fixtures and real split replay are executed; independent implementation acceptance remains open.

## 1. Objective & Scope

Verify #21/#39 forecast chronology, equal candidate trajectories, trained-state carry, isolated audit and checkpoint/resume. Every scheduled origin remains in the denominator. Only forecasts issued before labels and later supplied with all 24 valid arrived labels can be scored or updated. This report covers pipeline correctness and measured costs; research effectiveness remains outside the diagnostic evidence.

## 2. Methodology

At a block start, clone the active trained model and Adam state into three independent candidates. For each scheduled origin, persist all candidate forecasts (or the declared missing-history skip), then process its label event. Complete delayed labels are delivered in availability/origin order before the next affected forecast. Compute paired normalized MAEs from stored predictions and update candidates only on complete labels. Each candidate receives the same data/order and paired CPU/CUDA RNG state.

At a completed block, compute the controller decision from arrived evidence, carry the selected **trained** model/optimizer forward, and fork new candidates. A keep continues the trained current candidate. A switch also starts an isolated old-policy audit trajectory for the next block; its forecasts/updates/costs never feed controller selection. A bounded replay ending exactly at a block boundary leaves that decision pending until a resumed origin can deliver newly eligible late labels.

## 3. Implementation

`runner.py` owns origins, label arrivals, candidate/audit state and chronological events. `replay_inputs.py` validates the accepted schedule, forecast/label identities, scale, late queue and cursor. `checkpoint.py` publishes runner snapshots without replacing old files; `evaluation.py` computes complete-day errors in original kWh. `cli.py` records manifests, event-journal hashes and measured costs. No replacement runner or retrospective prediction layer was added.

## 4. Input

The DATA-v1 schedule, predictor-only forecasts and delayed label records are matched by `(dataset, city, entity, origin)` and input/scale identity. Input tensors arrive on CPU (`[1,24,7]`, `[1,24,5]`) and are transferred to the selected compute device. All-missing histories stay scheduled skips. A label record's serialized presence is not treated as availability; replay respects `available_at` and the all-24-label rule. Phase 0 lists manifest hashes and upstream clock/energy limitations.

## 5. Configuration

Each selected budget/entity/seed runs replay 42, saves its state, then resumes into a new replay-90 stage. The fixed controller config is detailed in Phase B. Epsilon is `1e-6`; device is CUDA on RTX 3050 Ti, PyTorch 2.8.0+cu126/Python 3.13.7. The same Source checkpoint is shared only within the matching budget/seed, and target and replay input bindings must match its lineage.

## 6. Output

Runner schema `hung-sprint2-runner-v1` stores model config; input binding; frozen reference and latent scale; active/candidate/audit model and Adam state; current level/block/cursor; pending and late labels; days; issued forecasts; decisions; events; update/cost counters; CPU RNG and CUDA RNG for the selected device. Checkpoints retain issued forecasts as CPU tensors; model trajectories execute on the selected device. Load rejects incompatible device type rather than silently moving a CUDA resume to CPU. Model-stage checkpoint RNG is a separate gap in the frozen runtime snapshot; Phase A records the subsequent optional RNG metadata/restore addition and its CPU fixture limits.

Each replay has `events.jsonl`, `runner_checkpoint.pt` and `run_manifest.json`. Resumed stage journals contain the newly appended event range, while checkpoints retain full history; verify start/end indices and both stage hashes rather than treating replay-90 journal alone as the entire run.

## 7. Experimental Results

Sample **7d / seed 7 / entity 1405** ended at cursor 90 with 90 forecasts, 89 scored days and six block decisions. Its replay-90 manifest reports 12.335 seconds CLI duration, peak CUDA allocation **22,323,200 bytes**. The first forecast example and live MAE/RMSE are in Phase A. The journal records events 196–412 (217 newly written events; end index 413) with SHA-256 `8ef81c942b073920c64849b24f73da2a7b47c22ce2bcd825fb64751484d8705c`.

| Trajectory | Inference calls / time | Update steps / time |
| --- | ---: | ---: |
| Candidate λ=0 | 90 / 0.190113 s | 89 / 0.779474 s |
| Candidate λ=0.1 | 90 / 0.072356 s | 89 / 0.705508 s |
| Candidate λ=0.2 | 90 / 0.068662 s | 89 / 0.684840 s |
| Old-policy audit | 42 / 0.032170 s | 42 / 0.308323 s |

These cumulative counters measure synchronized `model.forward`/`target_step` calls, excluding input verification, checkpoint I/O and process startup. End-state logical tensors occupy 500,400 bytes for active and for each candidate, 166,784 for reference and 256 for scale; audit is null at this final state. Logical tensor bytes are not peak device/process memory; Windows process peak RSS was unavailable. Phase D/E contain the full matrix and artifact audit (216 stages, 354 checkpoint/journal hashes).

## 8. Correctness & Validation

The combined 43-test command in Phase A passed, including runner, resume and replay-input fixtures. These exercise forecast-before-label, incomplete-label no score/update, missing origins, forced switch and isolated audit, trained state carry, repeated identities, late-label update exactly once, runtime counters, checkpoint after forecast/update, audit resume after switch, legacy cost metadata and bounded-boundary replay equivalence.

The session separately passed two #39 completion tests including CUDA issued-forecast/RNG restoration. A historical real CUDA diagnostic in `runs/hung-39-cuda-resume-fixed-20261025/` matched uninterrupted replay: 307 events, 59 forecasts, six decisions, forecast tensors and candidate weights (see the existing completion report). The new representative run executes split 42→90 replay for all cells and verifies lineage/cursors/hashes; it does **not** add 69 new uninterrupted comparator runs or claim that the historical comparator used the new runtime commit.

## 9. Discussion & Limitations

Fixture agreement checks implementation behavior, not full scientific validity of input arrival assumptions or controller inference. The runner's real bounded replay demonstrates stored predictions and chronological updates on accepted Development artifacts; it cannot establish original meter arrival times or unseen-location independence. Sample timing is local and workload-specific. Reproduction across CPU/CUDA is not promised bit-for-bit, and cross-device runner resume is rejected at this snapshot. Config approval, independent Qyroven comparison and peer review remain open.

## 10. Reproduction

Use the fixed input/config/selection and exact driver command in [the representative report](hung-39-representative-local-20261025.md), with a new output root for a new execution. Retained replay-90 must name the SHA of its own matching replay-42 checkpoint. Before recovery, verify both checkpoint and journal hashes, input binding, code hashes, device and dependencies; preserve partial output and start a new stage directory if the existing one is incomplete. For offline validation, run the combined CPU fixture command from Phase A, or the corresponding runner/resume/replay-input modules. Use Phase E's archive/readback instructions for durable handoff; do not restart training merely to display a result table.
