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

## Submitted Kaggle version (2026-11-10 16:33 UTC)

The existing notebook accepted **Version 2**, with GPU T4 x2, and displayed
**Queued**. This confirms submission, not successful execution or a measured MAE.
Version name: `persistent-v1 bd552cf technical+calibration`.

- Execution commit: `bd552cf0484fe047ed96416f569cc19529bc4111`.
- Embedded code ZIP SHA-256:
  `71ca9687ca795f68a2723b992627c3444773d906978dd284df45420ccdccd1bc`.
- Local upload file:
  `D:\Đồ Án\.cache\issue99-persistent-lambda\.cache\issue99-persistent-v4.ipynb`
  (251,021 bytes; 72 packaged files).
- Expected new Kaggle root: `/kaggle/working/issue99-persistent-bd552cf0`;
  code, stage and results are separate subdirectories. This path is prepared by
  the notebook and has not yet been verified as an executed output.
- Draft PR: <https://github.com/HungLD9505/adaptive-retention-ev/pull/113>.

The first save attempt used a 1,393,917-byte notebook at commit `18bdfa9`.
Kaggle rejected it: "The kernel source must be less than 1 megabytes in size."
No run was created by that rejected attempt. The successful submission narrows
the embedded package to the relevant modules, issue99 tests and configs, while
preserving committed file hashes. Old local packaging files are retained.

Commands performed locally were Git inspection, commits/push, notebook packaging
and the code-only verifier checks documented in
`issue99-persistent-verifier-notes-20261110.md`. No new model or data replay ran
locally. The packaging attempt at `aab29aa` correctly failed because a formatting
edit differed from its pinned commit; the edit was committed before repackaging.

The initial Version 2 status check was scheduled around 16:54–17:03 UTC
(20–30 minutes after submission).
Two pre-existing queued jobs were visible before submission: Fixed search v1
Version 2 and independent pilot audit Version 1, both approximately 21 hours old.
They were not cancelled or claimed as results of this follow-up.

## Status update (2026-11-10 approximately 17:00 UTC)

The Version 2 submission above was later cancelled after zero seconds. Version 3
was also cancelled after zero seconds. The Kaggle editor had saved JSON notebook
content while set to **Script**, so neither version ran the experiment. These
versions and their job records remain historical; they are not empirical
failures of the controller. The editor was explicitly changed using
**File → Editor Type → Script** before the next save.

[Version 4, run 368138679](https://www.kaggle.com/code/hungluongduc/issue99-source10-2798384-paired-comparison-v2?scriptVersionId=368138679)
was saved at approximately 16:59 UTC. The saved source was checked and is actual
Python, not JSON. It showed **Queued** at the last observation; no training,
pilot, Calibration, or Later result has been observed from this version.

- Pinned execution commit:
  `087b7ee085835824fc7bb8effef7a05df126e6e8`.
- Embedded code ZIP SHA-256:
  `dc1e78cf2ba00cf11794b32ed42f140777e904a4a012c6423dc9aa9b497ad0a8`.
- Local upload source:
  `D:\Đồ Án\.cache\issue99-persistent-lambda\.cache\issue99-persistent-v5.py`,
  259,584 bytes, 73 packaged files. This is a packaging artifact, not a run output.
- Session options shown for the pinned original environment: **T4 x2** and
  internet on. The quota display was **01:59 / 30 hours**; it does not by
  itself establish remaining usable GPU time.
- A separate draft session was started at approximately 17:00 UTC to check GPU
  availability and showed **Starting**. This was not the Version 4 run, and no
  GPU availability or empirical result was established from the draft session.

Preserve Versions 1–4 and their outputs/status records. Resume checking Version 4
at approximately 20–30 minute intervals without starting duplicate experiments.
Draft PR #113 already exists; the remaining empirical work is to observe the
Version 4 run, independently verify its saved pilot and Calibration artifacts,
apply the locked gate, and run/report Later only if that gate passes.

## Executed Kaggle result (2026-11-11)

The later pinned package at commit `b2ab78b` completed the six-run pilot and
48-run Calibration matrix. The independent verifier passed. The registered
Calibration promotion gate **failed**, so the notebook did not dispatch the
48 Later runs. The new controller's Calibration result is exploratory
Development evidence, not an independent Final result.

- Runtime root: `/kaggle/working/issue99-persistent-b2ab78ba`.
- Protocol SHA-256:
  `f0443273e12eac8c0f8311e4e7b7ba2abd7bdc2a616a74d688bea442fcd96acb`.
- Embedded package SHA-256:
  `97cf995e84decb5e7725a7e5f5216a1281ae86df49a57e4983dd07e2c6c7faf0`.
- Kaggle runtime: Python 3.13.16, PyTorch 2.11 with CUDA 13.0, T4 GPU.
- Focused tests: 26 passed in 14.36 seconds. Ruff was unavailable in this
  Kaggle runtime, and the embedded package lacked the README files needed by
  `check_release`; full README and Ruff checks had passed separately in CI
  run `42858352451` at `c0ef72c`.
- Pilot: zero accepted candidate blocks; the real Persistent trajectories
  matched Fixed in the pilot. This does not imply an improvement.

| Calibration method | Macro MAE (kWh) |
| --- | ---: |
| λ=0 | 5.443630217787778 |
| Fixed | 5.331705633298364 |
| Immediate controller | 5.318961684341266 |
| Persistent controller | 5.331587155372982 |

Persistent improved over Fixed by only `0.00011847792538244306` kWh macro MAE,
below the locked `0.01` kWh promotion threshold. Its total invocation wall-time
ratio to Fixed was `1.6138442882175836`. Only seed 42 improved on the
four-target seed macro; only target 1153/seed 42 ended at λ `0.898445` instead
of the initial `0.798445`. All other persistent runs kept the initial λ.
Historical Fixed baseline comparison matched all 12 Calibration cells and both
macro values exactly (reported delta zero); this is comparability evidence,
not a replacement for the new saved-run verification.

The execution history must remain distinct: the queued Version 4 at commit
`087b7ee` was cancelled for interactive use. A subsequent `087b7ee` attempt
failed before training because `ev_baselines` was absent from the package; the
`3c6b3c7` attempt failed before training because of a protocol trailing comma.
Both packaging failures were fixed by the executed `b2ab78b` package. Preserve
their job records and outputs; do not count them as negative model results.

Next work is to preserve the Kaggle outputs and hashes in the repository report,
independently document the failed gate and PR review status, and avoid a Later
run under this locked protocol. No new local training is required or reported.

Quick Save of Version 5 with Output failed with `502 UploadKernelSessionOutput`.
The original kernel was still alive at the last observation. This error does
not erase the already observed metrics, but it means **durable saved Output is
not yet verified**. Preserve the live kernel and all historical versions while
investigating another output-preservation route; do not claim the Kaggle Output
artifact has been archived or locally rehashed.

### Version 6 output-preservation attempt

To reduce the live `/kaggle/working` upload, only **reconstructible duplicate
input directories** were relocated in three new experiment roots:
`087b7ee0`, `b2ab78ba`, and `3c6b3c7a`. In each root, `stage/inputs`
(895,451,840 bytes) and `verified-bundle` (177,449,505 bytes) were moved to
`/kaggle/temp/issue99-reconstructible-input-copies-b2ab78ba/<rootname>/<same-relative>`.
The original mounted Kaggle input dataset was unchanged. The relocation map
is saved at
`/kaggle/working/issue99-persistent-b2ab78ba/reconstructible-input-relocations.json`.
The first console command had a newline SyntaxError and made no mutation; a
corrected single-line command completed the moves. `/kaggle/working` output
size fell from about 3.1 GiB to 155.5 MiB as displayed by the Kaggle UI;
the separately reported logical working-file total was 135,540,907 bytes.
These are different measurements, not an exact unit conversion. **No Source checkpoint/weight,
run result, committed tick, code or report directory was moved or deleted**.
For example, the final Persistent 1153/seed 42 state remains at
`/kaggle/working/issue99-persistent-b2ab78ba/results/calibration/persistent-1153-seed42/tick-0028/state.pt`
(1,464,155 bytes), alongside `commit.json` (345 bytes), `forecasts.json`
(6,970 bytes) and `events.jsonl` (3,548 bytes). That `state.pt` SHA-256 was
`5d631f2dcc4c7197d153d9161602d6bad3466465a12fdd6deedccb4259daeed4`.
The independent verifier and report-manifest SHA-256 values were unchanged
after relocation.

`/kaggle/temp` is not durable. Any future replay must reconstruct `stage/inputs`
from the original attached input ZIP and verify its manifest/file hashes before
use; the relocated temporary copy is only an upload-size workaround. The
original `stage/sources` checkpoint files remain in `/kaggle/working`.
Quick Save Version 6, named `b2ab78b verified54 compact output`, was submitted
with **Save output this version** and subsequently completed. Its
[saved viewer](https://www.kaggle.com/code/hungluongduc/issue99-source10-2798384-paired-comparison-v2?scriptVersionId=368145244)
showed the `report/` directory with all eight expected files and their
recorded sizes. The viewer's 10.5-second runtime is the Quick Save conversion
time, **not** the pilot/Calibration experiment duration. This confirms a
saved Kaggle Output view; it is not local byte-level verification.

For a second preservation path, a ZIP was made **inside Kaggle only** at
`/kaggle/working/00-issue99-b2ab78b-verified-artifacts.zip` (53,304,857
bytes, SHA-256
`64148ffce5b104f3d51038aa8d72cef64c0eddf66cf46ae3b47e1f6159c6de0d`).
The ZIP contains 5,709 files and passed ZIP CRC verification in Kaggle. It
contains the whole `issue99-persistent-b2ab78ba` root, including code,
reports, results, Source weights and relocation map. It excludes only the
reconstructible duplicate inputs moved to `/kaggle/temp`; the original input
dataset remains attached separately. The receipt is at
`/kaggle/working/00-issue99-b2ab78b-archive-receipt.json`. These ZIP/receipt
paths were created after the Version 6 save. Version 7 then completed with
the ZIP and receipt in its [saved Output](https://www.kaggle.com/code/hungluongduc/issue99-source10-2798384-paired-comparison-v2/output?scriptVersionId=368146429).
The saved viewer displayed the 294-byte receipt with the exact ZIP size,
SHA-256 and 5,709-file count above, `model_experiments_rerun: false`, and the
ZIP listed at the output root. Version 7's 10.4-second runtime is Quick Save
conversion time, not experiment duration. This establishes a Kaggle saved
archive receipt and visible ZIP, **not** a local download or byte-level check;
neither ZIP nor receipt has been rehashed locally.

After the archive was confirmed, the older Version 4 queued job was explicitly
stopped and showed **Cancelled**. The failed Version 5 save had a queued stop
request sent; a final Cancelled state was not observed. Versions 2 and 3 had
already been cancelled. The separate draft GPU-check session showed
**Session stopped**. Two unrelated older queued notebooks were left untouched.
These statuses do not alter the completed `b2ab78b` results or the failed gate.
