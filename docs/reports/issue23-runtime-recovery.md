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
