# Colab eviction and completed controller backup recovery

Issue #23 / PR #52. Colab displayed a runtime-disconnected/max-duration message
and then explicitly denied a new GPU connection because of usage limits. The
old kernel/serial workers are no longer usable. Do not describe proxy/matched/
analysis stages queued in that kernel as still running or completed.

The last live process probe observed controller PID93434 at 260/276 runs. Drive
subsequently contained all 23 completed-run chunks. All 394,373,490 bytes were
downloaded, provider sizes and ZIP CRCs checked; their embedded completed-run
lists contain **276 unique runs**, no duplicates. This establishes completed
individual run evidence, not yet full scientific acceptance or global verification.
The original complete matrix/selection/export and loop timer were not preserved.

`tools.recover_controller` authenticates the downloaded chunk registry, validates
safe paths/report identities, reconstructs every original run without training,
recomputes the fixed finite-grid selection and binds the already verified original
Source/cohort/profile. It CPU-loads and content-rehashes all latest branch states.
A new matrix explicitly records reconstruction provenance and leaves original
loop wall time null; per-run elapsed counters remain available. It must then pass
the independent daily artifact/label-arrival/original-unit verifier before any
new training consumes the selected recipe. Preserve original archives and outputs.

The recovery is CPU-only read/verification, not laptop model training. It does not
invent the original batch exit code, total loop timing or an unobserved downstream
execution. The grid/code/profile and all forecast bytes remain unchanged; no
favorable seed/checkpoint rerun or missing-cell omission.

## Authorized fallback

The existing signed-in Kaggle account allocated GPU T4 x2 and reported 30 GPU hours
remaining. A new **private** notebook was created:
[Qyroven Sprint 3 Development Recovery](https://www.kaggle.com/code/qert12345/qyroven-sprint-3-development-recovery-20261026/edit).
Its first probe uses `CUDA_VISIBLE_DEVICES=0`; the serial driver uses one visible
T4, with the second allocated GPU accounted for separately rather than claiming
full allocation efficiency. No account rotation, paid upgrade or public publishing.

Actual environment: Python3.13.15, PyTorch2.11.0+cu128, CUDA build12.8,
Linux6.18.55+, Tesla T4, driver580.178.04. Colab used Python3.13.16,
PyTorch2.11.0+cu130 and Linux6.6.122+. These are different execution environments;
bootstrap stream identity and floating-point behavior can differ. Do not pool
old Colab Adaptive/FT/Fixed outcomes with new Kaggle methods as if environmentally
matched. The resumed comparison family requires new matched reference replays
under the same Kaggle environment, with fixed previously selected settings and
original identified Source weights, and explicit cross-runtime lineage. This is
replication, never retrospective replacement of original forecasts.

Kaggle downloaded and SHA-256 verified the accepted UrbanEV input ZIP (151,254,390
bytes, `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`).
That authenticates full artifact bytes; the hardened consumer still restricts model
training/evaluation to Source and declared Development identities. No Final tuning
or evaluation and no long local training. Source/checkpoint/code restoration,
complete recovery verification and downstream GPU execution remain in progress.

279 local fixture tests passed before actual recovery execution; new recovery
logic rejects unsafe/duplicate ZIP members, unlisted runs, contradictory reports
and missing/extra finite-grid cells. Routine CI downloads no datasets or trains
models on real data. No merge or issue closure.

## Actual recovery completed

Recovery code `10ada9b` restored all **276 original completed runs** from the
23 chunks and CPU-loaded/content-rehashed all 276 latest candidate-state snapshots.
The independent verifier then recomputed arrived complete-label residuals and
all candidate/deployed metrics, physically hashing **51,060 daily files**.
No local model training and no completed GPU replay reruns.

[Download bytes/hashes and original Drive IDs](issue23-controller-recovery-downloads.json),
[independent verifier](issue23-controller-verification.json),
[full finite-grid station/seed accounting](issue23-controller-selection.json).
The restored matrix is explicitly reconstructed; the original batch-loop wall
time remains unknown. Saved per-run elapsed counters sum to1,639.874496 seconds,
not a substitute for startup/backup/export/total elapsed time.

| Controller recipe | 7d MAE | 14d MAE | 28d MAE | Equal-budget Development score |
|---|---:|---:|---:|---:|
| 0 | 4.889339 | 5.162208 | 5.534161 | 5.195236 |
| 1 | 4.842021 | 5.098825 | 5.524448 | 5.155098 |
| 2 | 4.889056 | 5.139251 | 5.541796 | 5.190034 |
| 3 | 4.867115 | 5.135678 | 5.526969 | 5.176587 |

Original-unit kWh, same selected Development cohort, station-first paired seeds;
132 null run scores retained. Provisional recipe1 uses levels0/0.1/1, initial0.1,
Bmin7, delta0, segment3, alpha0.05 and2,000 bootstrap resamples. This is conditional
Development selection, not controller superiority: the earlier matched Source10
Fixed Retention score5.121629 is lower. No favorable rerun or silent grid extension.

After the old runtime was evicted, the complete backup folder was moved into the
shared Issue23 parent. Drive metadata confirms all23 files shared there; exact
individual team-account access remains untested. Kaggle can retrieve the folder's
file list and has begun its own byte restoration. No Drive OAuth scope was granted
to Kaggle, no notebook was made public and no account rotation occurred.

## Environment-matched replication gate

The collection now rejects missing or mixed target execution environments.
The matched driver can explicitly replay Adaptive, Full Fine-tuning and the
previously selected Fixed baseline in the new environment, in addition to all
missing baseline/ablation rows. It authenticates and recomputes the Fixed choice
from its complete independent calibration verifier. Original settings remain fixed;
this is runtime replication, not a new favorable tuning search.

For the actually selected Bmin7/delta0 recipe, the new matched batch has690 runs
(10 unique methods times69 units), including207 fresh core references. Proxy/
parameter selection contributes the remaining four methods. The collector uses
only new-environment proxy and matched target rows, retains all original calibration
proof/selection lineage and never silently falls back to old Colab forecasts.
Its mixed-environment regression fixture and complete-replication fixture passed;
281 local tests, Ruff lint/format and diff checks pass. New GPU execution of these
post-migration drivers is not claimed yet.

## Kaggle validation and state-content check

At commit `54131cbb8ce47f9d064b80f03956e8e62ec48346`, Kaggle passed all
281 offline fixture tests (27.855 seconds), Ruff lint/format and diff checks. The
child environment reports Python 3.13.15, NumPy 2.3.3 and PyTorch 2.11.0+cu128.
Pip reported conflicts in unused preinstalled packages (including Numba's NumPy
constraint); this is recorded rather than describing the global Kaggle image as
a clean, fully resolved environment. Training uses fresh child Python processes.

The accepted input ZIP has an enclosing `data/inputs/issue18-input-handoff-v1-20261019`
path. An initial recovery argument assumed the ZIP root and failed its manifest
assertion before recovery/training. Corrected the argument only; archive bytes and
manifests remain unchanged. All 23 original backup ZIP fingerprints passed again
on Kaggle; completed states were reconstructed and CPU rehashed. Full independent
daily verification is required again before the queued GPU batch starts.

`tools.verify_latest_states` provides a reusable post-download CPU check after
complete daily verification. It binds the saved report to its authenticated matrix,
tick count, latest commit identity, state-file byte hash and recursive model,
optimizer and RNG content digests. It does not train, reconstruct absent historical
states, or claim Source checkpoint tensor verification. Independently rerunning it
on the downloaded controller artifacts passed for all 276 latest states.

The corrected Kaggle recovery then passed independent verification for all 276
runs and 51,060 daily artifacts. The gated GPU batch subsequently started and
actual completed proxy/parameter runs appeared in `progress.json`. This is live
partial execution, not completion of 1,104 calibration runs, 690 matched reference
runs or subsequent analysis. The serial batch stops on a failed child stage;
matched comparison and analysis require their preceding independent proof.
Kaggle's Quick Save was selected with **Always save output** and a private version
snapshot requested, avoiding a duplicate Save & Run All GPU batch. The UI action
alone is not proof that every future checkpoint has reached persistent storage;
check/export completed outputs and preserve interrupted partial runs if needed.

A new read-only [Development density-context handoff](issue23-density-contexts.md)
records all 21 metadata-derived thresholds. Forecast-error grouping remains
pending the complete matched collection; these proposed thresholds do not grant
Final-lock approval or change training/cohort eligibility.

The reconstructed controller matrix, selection, daily verifier, latest-state
verifier and original backup registry are now [in a shared evidence folder](https://drive.google.com/drive/folders/13q28JpTRMCTu9TGaNgWsebujQ-pwdoUy).
All five were downloaded again and are byte-identical to the original local
outputs; the context output was independently read back in the same six-file
check. Exact identities and access limitations are in the [artifact registry](issue23-recovery-context-artifacts.json).

## Kaggle snapshot persistence warning

The editor later displayed `An error occurred while committing kernel` with an
HTML response where JSON was expected. A separate read-only notebook view showed
Quick Versions1/2 as **Starting...**, not verified complete outputs. Do not equate
creation of a version record with durable checkpoint/forecast preservation.
A diagnostic code-only Quick Version3 subsequently completed (10.9 seconds,
Output0 files). It preserves notebook code/log presentation, not training files.
The Quick Save output preference is now **Never save output** from that diagnostic
attempt; explicitly choose output saving when a completed export is ready.

The original GPU subprocess was not restarted or interrupted; its completed-run
counter continued increasing. The Output sidebar showed roughly5GiB of19.5GiB
in use at an early partial observation. Full matrix/city storage feasibility and
completed-output export remain open requirements, rather than assuming snapshots
solve them. Preserve the live kernel and original working directories.

The supported Output-file Download action retrieved an atomic progress snapshot:
149 completed-run report records, status `running`, clean pinned training code
`54131cbb8ce47f9d064b80f03956e8e62ec48346`. This file was saved locally and
[uploaded to shared Drive](https://drive.google.com/file/d/1wDML-hF-skxQ2ipHff8fA53zHKdXwCWC/view).
[Size, hash, scope and measured partial counters](issue23-kaggle-partial-progress.json)
are recorded. This is not a complete study, independent score verification or a
backup of the149 target checkpoints/forecasts. Do not select configurations from
this incomplete ordered subset or infer a complete-study runtime from it.
