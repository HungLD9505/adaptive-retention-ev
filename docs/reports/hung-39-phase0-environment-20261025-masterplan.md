# #39 Phase 0 — environment and provenance

Evidence date: 2026-10-25, Asia/Saigon. Runtime code is pinned at `a34a49e5f04920ef30456fe6c0ea56eb2f1d659a`. This report records the environment used by the local representative execution; it does not certify a clean Python 3.12 installation or team acceptance.

## 1. Objective & Scope

Establish input, code, configuration, device and output identity before the #39 Development workload. The user's masterplan explicitly permits preserving the already running local matrix. Source training uses the permitted Source role; target adaptation/replay uses Development. Final/test remains unused. This is an engineering handoff for #19–#21, separate from research effectiveness.

## 2. Methodology

The preflight reads the release archive and all three input runs, checks recorded identities, validates the predeclared selection against Development entity metadata, and probes actual CUDA availability. A matrix identity binds code-file hashes, config SHA, selection SHA, manifest SHA, phase, budgets, seeds and device. Completed stage reuse requires matching code identity and checkpoint hash; an incomplete stage must be preserved and investigated.

## 3. Implementation

The existing `run_development.py` orchestrates the existing CLI; `cli.py` verifies the release/input manifests; `selection.py` derives selection from permitted metadata. All are under `experiments/hung_sprint2/`. No core implementation was changed for the representative run. The untracked historical selection draft without `-v2` was present and preserved. The run's `matrix_identity.json` records executed file hashes and that worktree status.

## 4. Input

DATA-v1-20261019 UrbanEV/SZH input ZIP: **151,254,390 bytes**, SHA-256 `2b8d1a47edebe066543f8f0aec5897c23945edcef62ba10357b1cb95e5ba27c7`. ZIP verification passed. Fresh `_load_run` reads verified manifests and their referenced artifact hashes for all three budgets.

| Budget | Manifest SHA-256 |
| --- | --- |
| 7d | `fd1b5d1767e94a3e5c6f62447d446e1f13859b823c5fe14c51b5055d8e67169c` |
| 14d | `66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9` |
| 28d | `cdd43152bbda3de9f468938262a8bf00e041a9f264cf29051b71d06e788beadd` |

The accepted tensor interface is `X_hist[B,24,7]`, `C_future[B,24,5]`, `Y[B,24]`. History masks distinguish missing values from real zeros; target labels are never filled. Input clock/arrival assumptions and upstream estimated energy remain subject to the limitations in the input handoff.

## 5. Configuration

- Config v1 SHA-256: `20cb0f0962af6e3f3781ef9bebdf03c162548e06894ae4b59ddc1d58be277ba0`.
- Selection v2 SHA-256: `840ea1984592d920b513cbf5c7a67eb370227111b3f609040d12a2f720b12b56`; 6/8/9 representative entities for 7/14/28d, seeds 7/11/19.
- Python **3.13.7**; PyTorch **2.8.0+cu126**, CUDA runtime **12.6**; NVIDIA GeForce RTX 3050 Ti Laptop GPU, **4 GiB**; `torch.cuda.is_available()` returned true. The README recommends Python 3.12, so this run records an environment deviation.
- Pre-run free disk: **63,845,855,232 bytes**. Each execution uses its own output root; no CPU fallback occurred.

## 6. Output

The new output root is `runs/hung-39-representative-local-20261025T2103/` inside the worktree and ignored by Git. It contains the matrix identity, Source/target/replay manifests and checkpoints, replay journals, and the independently generated `audit_summary.json`. Old run directories, raw/input bytes and `results.zip` were preserved. The representative audit reports 216 completed stages and 354 checkpoint/journal hashes checked; Phase D/E reports hold the detailed results and archive inventory.

## 7. Experimental Results

| Check actually executed | Result |
| --- | --- |
| `python -m tools.sources list` | PASS; catalog listing only |
| CLI `verify-input-zip` against the identified ZIP | PASS |
| Three `_load_run` calls and representative driver dry run | PASS |
| `python -m unittest tests.test_hung_completion -v` with repo-local temp | PASS, 2 tests including CUDA checkpoint fixture |
| `python -m unittest discover -s tests -q` with repo-local temp and UTF-8 | PASS, 174 tests, 1 POSIX-only skip |
| `python -m ruff check .` using pinned Ruff 0.17.0 | FAIL at preflight: existing unused `os` in Kaggle notebook cell 4 |
| `python -m ruff format --check .` | FAIL at preflight: same notebook; 103 other files formatted |
| `python -m pip check` | FAIL: installed `ultralytics==8.3.82` requires NumPy `<=2.1.1`, but global NumPy is `2.4.2` |
| `git diff --check` | PASS at preflight |

The initial default-temp test attempt failed on sandbox temp permissions. With repo-local temp, the default cp1252 environment still failed on Unicode paths. Setting `PYTHONUTF8=1` resolved those environment failures. Ruff was initially absent; pinned Ruff 0.17.0 was installed into ignored `.deps`. No environment failure is represented as a code test pass.

## 8. Correctness & Validation

Input/config/selection identities and CUDA availability met the GPU execution gate. The input ZIP and manifests were freshly checked rather than inferred from historical fingerprints. Full fixtures passed in the recorded local environment. P0 is **not a fully clean dependency/lint gate at the training commit** because of the documented Ruff and global dependency failures; later presentation fixes or isolated-environment checks require their own evidence and must not rewrite this snapshot.

## 9. Discussion & Limitations

Successful fixtures and training show that this execution environment worked for this diagnostic workload; they do not establish compatibility with every clean installation. The NumPy conflict concerns an unrelated globally installed package, but means the shared global environment fails `pip check`. A clean pinned environment remains the preferred reproduction path. GPU quota from Kaggle/Colab is not established by this local probe. There is no Source-pass/config approval, peer approval, merge or issue acceptance in this report.

## 10. Reproduction

From the branch worktree, set `$env:PYTHONUTF8='1'`, and set `TEMP`/`TMP` to a writable `.cache/testtmp` inside the repo. Use the exact commands in [the representative execution report](hung-39-representative-local-20261025.md), including `--phase representative --device cuda --budgets 7 14 28 --seeds 7 11 19 --execute`, with a **new** output root when reproducing. To audit retained outputs, run `python runs/hung-39-representative-local-20261025T2103/audit_representative.py` only if its create-only `audit_summary.json` does not already exist; otherwise inspect the existing summary and use Phase E's readback instructions. The audit script is a run artifact, not an alternate training implementation.
