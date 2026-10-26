# Issue #39 Colab verification handoff: pinned local preflight

**Status (2026-10-26): prepared and checked locally; not uploaded to Drive or run on Colab.** This is a Development verification run, not Final evaluation or independent method acceptance. The original Colab GPU/Drive criterion remains open until a live CUDA tensor calculation, run output, and Drive readback are observed.

## Pinned inputs

| Item | Identity |
| --- | --- |
| Execution code | Draft [PR #46](https://github.com/HungLD9505/adaptive-retention-ev/pull/46) head `e85a53cd02deaa3a3440df8c6922eb679773801b` |
| Complete-history Git bundle | Ignored `runs/hung-39-e85a53c-colab-20261026.bundle`, 7,164,812 bytes, SHA-256 `426eed262475ac417429ff6d0f6ea73ce56720645af472455c0c9c90c9a84c41` |
| Development selection | `docs/reports/hung-development-selection-20261025-v2.json` at that code commit, SHA-256 `273858dfb2bf949c297ecd209a5127a22966cb31703f7b2deefcf17323e13c91` |
| Development config | `experiments/hung_sprint2/development_config_v1.json` at that code commit, SHA-256 `20cb0f0962af6e3f3781ef9bebdf03c162548e06894ae4b59ddc1d58be277ba0` |
| Thin notebook | `experiments/hung_sprint2/colab_39_verification.ipynb`, SHA-256 `fd177edf6de3e96c7940509ccc6069546f5c3beabe738d36b0f0fcec5cd79921` |
| Declared run ID | `hung-39-colab-e85a53c-verification-20261026-v1`; CUDA, verification phase, budgets 7/14/28 and seeds 7/11/19 |

The notebook requires the bundle at `/content/drive/MyDrive/hung-sprint2-runs/hung-39-e85a53c-colab-20261026.bundle`. That path is a **planned destination**, not evidence of a completed upload. It checks the bundle hash, detached code commit, selection/config hashes, pinned PyTorch wheel, live tensor calculation on the declared device, and the DATA-v1 input package before training. The driver writes to the unique Drive run folder and refuses a different matrix identity at an existing folder.

## Checks actually run locally

1. `git bundle create ... codex/39-completion` and `git bundle verify`: complete history, expected branch tip, PASS.
2. Clone the bundle into a fresh ignored folder, detach at the exact commit, check source files and compute the four hashes above: PASS.
3. `python -m tools.verify_colab_39_pins --notebook experiments/hung_sprint2/colab_39_verification.ipynb --bundle runs/hung-39-e85a53c-colab-20261026.bundle --checkout runs/hung-39-e85a53c-bundle-preflight-20261026`: two code cells compile, both unexecuted, bundle/code/selection/config pins match, live tensor probe is present: PASS. The bundle and cloned checkout are ignored local preflight artifacts; the validator is tracked.
4. Python 3.12 README checks after the edit: `python -m tools.sources list` PASS; full unittest suite **174 tests, two skipped, no failures** with UTF-8 and project-local temp; Ruff lint/format over the checkout and `git diff --check` PASS. The full-test log is ignored at `.cache/test-preflight-full-20261026.log`.

These checks do not prove Drive access, Colab GPU availability, successful dependency installation there, Development execution, or durable output. A saved Colab run must record the live tensor/device result, exact code/input/config identities, stage logs and manifest/checkpoint hashes, then verify Drive files after the runtime ends. Do not substitute Kaggle T4 or local CUDA results for that Colab evidence. No usage reset, old artifact deletion, Final access, merge, or issue closure was performed.
