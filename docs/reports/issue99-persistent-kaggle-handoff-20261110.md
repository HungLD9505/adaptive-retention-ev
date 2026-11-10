# Issue 99 persistent lambda follow-up: execution handoff

## Status and scope

Implementation preparation is in progress. No new persistent-controller experiment
has completed at the time of this initial handoff. Tests have been written, not
executed locally. All new tests, data verification and model execution must run on
Kaggle following the owner's latest instruction. Do not infer effectiveness from
code or earlier per-day counterfactual experiments.

- Worktree: `D:\Đồ Án\.cache\issue99-persistent-lambda`.
- Branch: `feat/99-persistent-lambda`, based on `dev` with dependency PR #102,
  commit `302fb6b00a190c788ba3ffd81268ace52a151e8a`.
- Repository: `https://github.com/HungLD9505/adaptive-retention-ev`.
- Existing Kaggle notebook to update by adding a new version:
  `https://www.kaggle.com/code/hungluongduc/issue99-source10-2798384-paired-comparison-v2`.
- Existing Version 1, run `367824175`, completed in 777.4 seconds on T4 x2.
  This is historical PR #100/v2 evidence, not a run of the new controller.
  Its code and protocol differ from PR #102 and must not silently become a baseline.
- On inspection, the editor was a saved draft with the session off. No new
  persistent execution had been submitted.

## Locked experiment

The formula and acceptance criteria are machine-readable in
`configs/issue99-persistent-protocol-v1.json`. Preserve MAE plus Source-scaled
latent MSE. Clone the candidate once per block, train it alongside the real branch,
and adopt only its scalar lambda. Real model, Adam and RNG remain unchanged at
the decision. Five complete arrived-label pairs require mean candidate-minus-real
MAE below -0.01 kWh, at least four wins and no harm above 0.05 kWh. Expire after
nine issued days. Missing-label eligibility cannot depend on observed errors.

Pilot: Fixed and persistent on 1405/42, 2152/43, 1693/42, 22 ticks each (six runs).
Calibration: four methods by four targets by three seeds (48 runs). Only a passing
registered Calibration gate permits 48 later runs. All inspected Development
windows remain exploratory. No Final replay or 7/28-day extension is authorized
by the promotion gate itself.

## Reused Kaggle inputs

Mounted dataset:
`/kaggle/input/datasets/hungluongduc/issue99-source10-2798384-scored-inputs-v1`.
It contains the input ZIP, three Source10 ZIPs, manifest and old code ZIP.
Use newly packaged code, never the attached old `issue99-code.zip.bin` as the
implementation of persistent_v1. Extract into a new working directory; preserve
historical notebook versions and their outputs.

| Binding | SHA-256 |
| --- | --- |
| Input manifest | `66c82dd38bd6e2c50af06bd1363605b033878289283997fe11f314bf8c2418d9` |
| Source population | `c77778935190a7acd3cc00c35d7940a5c9bd59fa3dc0dca14b86505ead87b760` |
| Seed 42 epoch-10.pt | `a3d3485d8d9a3e96c0483ab61e659e3a31b0f9bd62cc51ae6b77c0d204920d8b` |
| Seed 43 epoch-10.pt | `2ad6ed33fb7e692eae5f8db6be075ce43564851f70390d19edb4314052a17f5f` |
| Seed 44 epoch-10.pt | `6f475e54768322c5b51f5837d6ce7e863cb9ef6d33aec05b4a1c2468cd0285a5` |

These are expected historical bindings, not a claim of fresh Kaggle verification.
The new notebook must verify archives, checkpoint metadata, latent scale and
actual input bytes before execution. Record Python, Torch, CUDA and GPU versions;
README requests Python 3.12, and any Kaggle deviation must remain explicit.

## Evidence and reporting requirements

Save commit and package hashes, exact Kaggle version/run URL, run directories,
commands, runtime, logs, failures/nulls, forecast and label provenance, independent
metric verification, accepted/rejected/expired blocks, real lambda paths, runtime,
VRAM and artifact sizes. Recompute metrics from forecast vectors and arrived labels;
averaging stored score events alone is not independent verification. Record whether
output bytes were verified locally or only read/verified within Kaggle.

The historical wide-paired negative screen is preserved in
`docs/reports/issue99-wide-paired-screen-20261110.md`. It describes a different,
earlier controller and cannot establish the result of this persistent variant.

## Remaining work

Finish static review and small commit-bound notebook packaging; run tests and
README checks on Kaggle; verify baseline reproduction and technical pilot; execute
Calibration; apply its gate; independently audit and report outputs; push this
branch and open a dependent PR into `dev`. Do not merge or close #99 automatically.
