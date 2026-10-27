# Issue 23 — completed-run backup and recovery

The [Colab template](../../notebooks/issue23_durable_city.ipynb) defaults to a
Source-only storage probe using original JHB checkpoints and an exact hash-pinned
d5f6157 code bundle (including the canonical-JSON backup fix). It does not train in probe mode. Explicit new, resume and
read-only rescue modes use accepted city inputs and unchanged primary selection;
training modes require CUDA. Keep the same authorized account.

The interactive-runtime incidents exposed a storage gap: complete notebook metrics
are not complete forecasts/events/checkpoint delivery. This change adds optional
mounted-Drive publication to the separate-city execution CLI. It does not modify
model, controller, runner, loss, candidate, cohort, seed or evaluation code.
Existing running9057364 jobs are not patched or restarted by this change.

## Publication and recovery contract

`--backup-root` and `--drive-mount` must be supplied together. An ordinary local
directory is refused as a claimed Drive mount. Use a unique backup directory and
a new local output directory; keep every previous run/archive unchanged.

Each completed Source publishes its selected epoch checkpoint, checksum sidecar,
training record, completion record and stdout. Each completed target publishes its
issued forecasts, events, daily commit chain, latest model/optimizer/RNG state,
report and stdout. Existing independent Development-only daily/state verifiers
must pass before publication. A null-metric run remains a completed artifact.
CPU Source verification preserves Torch RNG; it performs no fitting or inference.

One ZIP is copied per completed run. Size, SHA-256 and ZIP CRC are read back from
mounted storage before its receipt is committed. A failed copy stops execution
before starting another target. Pending/orphan/corrupt files are preserved and
refused on automatic resume; they require inspection, never silent replacement.
This is mounted-filesystem verification, not proof of Google server-side sync.
Independent cloud/anonymous download checks remain a handoff requirement.

`--resume-backup` restores verified completed Sources/targets into a NEW output
directory and skips them. Context binds the accepted manifests/scalers, Source
population/config, complete expected execution, primary selection, core file
fingerprints and runtime environment. A changed context or non-prefix selection
is refused. Completed Sources keep their original weights/identity; no favorable
seed/checkpoint/config reselection is introduced. A still-active or inaccessible
job must be inspected before dispatching a replacement.

The granularity is a completed Source/target, not an arbitrary in-flight epoch or
mid-day optimizer operation. An interrupted unfinished run is not automatically
certified/recovered. Existing daily runner resume remains a separate verified
interface. Intermediate Source epoch checkpoints are not all copied by this
completed-run archive. GPU equality with backup enabled and DriveFS failure modes
remain unverified until an actual cloud run is possible.

Backup verification/I/O and resume verification have separate timers. Per-run and
Source compute timers remain intact. After resume, `wall_seconds` describes the
current invocation only; lost pre-interruption wall/backup overhead is not
reconstructed or claimed as complete experiment cost.

## Colab usage

Use the existing authorized account, mount Drive, and select an identified clean
checkout containing this change. Do not rotate accounts to evade usage limits.
If no GPU is available, storage probes and read-only rescue may use CPU; real
training still requires CUDA. Kaggle Files-only persistence is not a Drive mount.

```python
from google.colab import drive

drive.mount("/content/drive")
```

Add these arguments to the unchanged identified city training command:

```text
--backup-root /content/drive/MyDrive/<team-folder>/<unique-city-backup>
--drive-mount /content/drive
```

To continue a verified backup, keep the same backup directory/context and use
`--resume-backup` with a new `--output`. Do not reuse a partial local output.

To rescue an existing completed prefix without training:

```sh
python -m tools.backup_completed_city \
  --snapshot <existing-study>/progress.json \
  --inputs-root <accepted-inputs> \
  --cohort <identified-city-cohort.json> --cohort-sha256 <recorded-sha256> \
  --primary-analysis <identified-primary-analysis.json> --primary-sha256 <recorded-sha256> \
  --backup-root /content/drive/MyDrive/<team-folder>/<unique-rescue-directory> \
  --drive-mount /content/drive
```

The rescue command captures one immutable prefix snapshot. It preserves the live
study and does not establish process liveness or whole-matrix acceptance. Its
receipts are compatible with later training resume under the same context.

## Verification scope

Six independent storage fixture tests cover byte-identical Source/null-target
restore after removing the temporary study, intentional historical-state
omissions, RNG preservation, overwrite refusal, changed context, failed copy,
pending/orphan archives, non-Development targets, changed configs/daily bytes,
unexpected files and traversal payloads. No raw dataset download, GPU or model
fitting is required. The final implementation suite passed327 tests in5.975 seconds;
Ruff lint/format, source listing and diff checks passed. Source listing is not a fresh raw audit.

Actual read-only CPU verification then archived three original UrbanEV Source
checkpoints and the first original declared retained proxy run, removed only the
disposable staging COPY and restored all295 file hashes identically. Daily and
latest-state proofs match the previously verified original; no training, inference
or Final labels were used. The first trial on legacy JHB stopped because its
standalone target stdout was not retained; no empty log was fabricated. JHB's
verified committed forecasts/events/states and aggregate logs remain unchanged.
See [exact evidence, code/proof downloads and scopes](issue23-durable-recovery-evidence.json).

Implementation4f174bd passed GitHub Actions40350149501; documentation/template
commitde587d8 passed40354758097. The maintained notebook template has been
syntax/lint checked, not executed as a whole.

The actual Colab CPU trial `qyroven-storage-drive-20261026-v2` then passed327 tests
in23.715 seconds, Ruff lint/format, mounted-Drive publication and restoration of
three original JHB Sources, and CPU RNG preservation. A separate anonymous
remote download verified the proof package and all three checkpoint archives by
size, SHA-256, ZIP CRC and original checkpoint bytes. The
[Drive evidence folder](https://drive.google.com/drive/folders/1c9hIubhDQrHbKuMoUvtMsGVOthQugsJY)
contains the executed script, config/context, receipts, logs and runtime versions.
The first cloud attempt stopped before publication because the shared team folder
was not directly exposed in My Drive; its outputs were preserved. Adding a My
Drive shortcut to the existing approved folder resolved the path without moving
or changing permissions on the shared data. The successful trial used a new ID.

This verifies actual Source-only storage and independent download, not target-run
GPU continuation or immunity to future provider/storage failures. No new fitting,
inference, Final lock/evaluation, peer approval or merge is claimed. Colab GPU
allocation remains usage-limited. Kaggle still displays `Session is starting`;
current MEL liveness and complete SPO raw export remain unverified, so the old
job has not been restarted. Next execution must first inspect/rescue that existing
state and retain the accepted protocol and original Source identities.

## Exact primary missing-artifact replay

`python -m tools.replay_missing_primary` authenticates the existing recovery plan
and original matrix, keeps the physical-absence partition and original Source
weights, and requires CUDA plus mounted Drive publication. Supply `--plan`,
`--plan-sha256`, `--family proxy|matched`, `--inputs-root`, `--source-root`, a NEW
`--output`, `--backup-root` and `--drive-mount`. The Source root must include the
original selected checkpoint, sidecar, report and stdout for every seed. Newly
created outer completion descriptors are explicitly labeled, not presented as
historical files. No missing logs or labels are synthesized.

Every newly completed target passes independent daily/state checks and publishes
its archive/receipt before the next cell executes. `--resume-backup` restores only
a contiguous completed prefix of the originally declared missing cells into a new
output under the same context; changed environment/config/input identities fail
closed. New numeric differences from original metadata are retained, never used
for reselection. Restored rows retain their independent backup-verification
scope; comparison differences/daily proof arrays cover newly executed rows only.
Invocation wall/backup costs are explicit, not reconstructed original total cost.

Five offline fixture tests cover authenticated subsets, changed source/plan/matrix
identities, reordered/overlapping/duplicate cells, changed protocol, and invalid
resume prefixes. Read-only actual preflight validated648 proxy and690 matched
cells and archived all three original Sources for each family without training.
The full332-test suite, Ruff lint/format and diff checks passed before dispatch;
actual GPU execution is reported separately and is not implied by those tests.

### First GPU dispatch and JSON representation fix

The T4 dispatch on2026-10-26 passed332 cloud tests, lint/format and all pinned
code/kit/input downloads. The first missing proxy cell completed92 ticks with59
issued and52 scored days, then publication correctly stopped at the report check.
Actual CPU readback of its final state established that decision `used_origins`
were tuples in memory and lists in JSON: direct equality failed while JSON values
were identical. No training or method defect was inferred from this serialization
mismatch. Reports are now compared and passed to archive verification in canonical
JSON form; changed values still fail. The regression test and full333-test suite,
Ruff lint/format and diff checks pass. The failed dispatch's original outputs,
Sources, logs and receipts remain preserved; rescue/continuation must be reported
as a separate execution using the fixed code, never a silent overwrite.

## Complete city pipeline with mandatory backup

`python -m tools.city_pipeline` promotes the previously executed independent city
orchestration into maintained code. It preserves the five accepted stages:
training, independent daily verification, latest-state verification, analysis,
and canonical export. New required `--backup-root`, `--drive-mount` and
`--handoff-root` arguments enforce identified mounted storage and separate unique
output/backup/handoff directories. Existing accepted cohort, primary-summary,
density hashes and expected Source-example count arguments are still mandatory.
The module and `--repo` must refer to the same clean checkout.

Every completed Source/target is verified and archived before continuing. Stage
start/command, stdout and exit/timing records are also published. Failure stops
before the next stage and preserves pending bytes; no automatic cleanup/restart
or missing-log fabrication. After export, all catalogued parts, selected Sources,
code bundle, proofs and analysis are copied/read back by size/SHA, with the catalog
published last. Missing, extra, changed or duplicate payloads fail. Independent
remote download and full off-runtime/peer acceptance still follow separately.

`--resume-backup` restores only verified completed prefixes into NEW outputs and
handoff directories under the same exact context. Method/seed/data/Source policy
is unchanged; no new per-city tuning, Final execution, or claim about inaccessible
old SPO/MEL outputs is introduced. Source/target backup timers, stage timers,
canonical-handoff time and pipeline wall time are recorded separately. Provider
wait, package installation and download overhead belong to the outer dispatch,
not an invented total in the inner pipeline.

Seven additional offline fixtures cover backup argument propagation, explicit
resume, byte-preserving copy/overwrite refusal, corrupted pending copy, durable
stage failure, changed-source copy identity, wrong-checkout refusal and canonical-export population/hash checks. Full cloud execution
of this maintained pipeline is recorded only when actually observed.

The maintained city pipeline atd5f6157 passed340 local tests in5.753 seconds,
Ruff/source-list/diff checks and CI40369603121. Its actual Colab bootstrap passed
340 tests in30.830 seconds and Ruff checks, then the city queue was observed
waiting on the live selected-proxy-bridge PID13716. The queue holds LOA→SZH→AMS;
MEL had already been launched earlier, but its old job and full SPO raw outputs
remain inaccessible and are not overwritten/replaced. No new city training was
claimed at that observation. Each new city receives its own input, three Sources,
cohort, backups and canonical handoff. See the
[exact code, queue and verification evidence](issue23-durable-recovery-evidence.json).

The maintained notebook pin was refreshed tod5f6157 and its exact shared bundle
size/SHA. All cells remain unexecuted; per-cell syntax and combined Pyflakes/error
checks passed. This avoids directing new training to the historical4f174bd report-
representation bug. Historical storage-probe evidence retains its original code ID.

## Bounded Kaggle outbox: explicit external publication barrier

Colab's GPU runtime ended and its CPU Drive mount failed. A separate Kaggle probe
actually obtained a Tesla T4, but CUDA/Python/kernel differ from the Colab runs.
The original SPO/MEL notebook was not restarted. Existing mounted-Drive commands
and their real-mount requirement remain unchanged.

`python -m tools.replay_checkpoint_chunk` is an additional bounded transport
workflow for the authenticated UrbanEV Development plan. It is **not** a fake
Drive mount or automatic remote-backup implementation. It requires cloud CUDA,
a clean unchanged core, a new output below `/kaggle/working`, exact plan-pinned
execution environment/NumPy and original input/config/Source identities. It calls
the existing runner without modifying model/controller/retention algorithms.

A call executes at most twelve original-order target runs. Each Source/target is
locally archived with the existing daily/state/CRC/receipt checks. Independent
verification and canonical export follow. `handoff.zip` wraps the verified export
parts, selected Source checkpoints, code and the bounded range record. The command
then exits with `awaiting_external_publication`; it never starts another chunk.
That status certifies local content, not remote durability or full-family success.

Before the next nonzero offset, the external operator must:

1. Download the actual wrapper through the notebook's normal file controls.
2. Check wrapper/part hashes, CRC and paths, restore it, and independently reproduce
   the complete daily/input/latest-state proofs using the accepted local inputs.
3. Upload the unchanged wrapper to the approved Drive folder and read it back to
   verify the same size/hash/CRC/content.
4. Write a separate hash-pinned `verified-kaggle-outbox-publication-v1` receipt with
   plan/family/start/end/run IDs, actual Drive URL/size/hash and both completed-check
   flags. Pass its path/hash to the next call.

The receipt gate rejects missing/changed scope, gaps, mismatched IDs and unverified
publication declarations. It validates an external operator assertion; it does
not independently authenticate OAuth or make a self-authored JSON into remote
proof. Actual download/verification/readback evidence must accompany each receipt.
The first cloud call is one run to test this complete handoff before larger chunks.

If the operator is offline, no next chunk starts. An unacknowledged local chunk
can still be lost to provider eviction, requiring at most twelve target replays;
previous remotely verified chunks and original Sources are preserved. This is a
bounded failure window, not a guarantee of unattended publication. Storage,
verification, transfer, operator wait and GPU-idle costs must be reported separately
from model work. No local real-data training, Final access or favorable reselection
is enabled. Six independent offline tests cover ranges, receipt barriers and
wrapper corruption/path/population/overwrite and copy-time-change rejection.
Actual cloud acceptance is reported only after execution and independent readback.

### Single-seed export boundary discovered by the real one-run trial

The Kaggle bootstrap at103bf2c passed346 cloud fixtures (23.176s), Ruff and exact
code/kit/input hashes. Its real first run
`urbanev-SZH-1405-7d-source_error-seed42-recipe1` completed local backup and both
independent daily/latest-state verifiers. Export then correctly rejected three
Source descriptors for a bounded matrix containing only initial seed42. The
failed export and trained run are retained; this was not a fitting failure and
no next chunk was dispatched.

The bounded driver now projects canonical Source descriptors to the actual
initial seeds in that chunk, while attaching a separate hash-bound package of
**all three original Source checkpoints/reports/logs**. This preserves uncertainty
ensemble dependencies even when an individual chunk does not initialize all
three seeds. The established canonical export's exact-Source validation is not
weakened. A regression test covers one-seed projection, all-three dependency byte
preservation and rejection of changed Source bytes. Full347 local fixtures PASS
(6.043s); actual corrected cloud/canonical handoff acceptance remains separate.
Source/target weights, predictions, configs, expected hashes and core algorithms
are unchanged. Recovery must copy and re-export the completed first run, not
silently retrain it or rewrite its original report.

### Separate-city Source outbox (implementation; cloud acceptance pending)

`python -m tools.city_source_outbox` prepares exactly one own-city Source seed
(42,43 or44), then stops before any target. It reuses the existing authenticated
city cohort, frozen primary recipe, Source trainer and `RunBackup` verification;
it does not copy UrbanEV/Hung weights, tune per city or change model/loss/runner
algorithms. A new output below `/kaggle/working`, clean code, positive metadata
Source count, hash-pinned cohort/primary/environment profile and deterministic
CUDA/NumPy identity are required. Output setup is rechecked for code dirtiness
before fitting. Inputs/raw data and existing runs cannot be overwritten.

The environment profile is captured and pinned before fitting:
`{"schema":"ev-city-cloud-environment-v1","environment":<actual environment>,"numpy":<actual version>}`.
Do not regenerate it silently to accept a changed runtime. The CLI arguments are
`--inputs-root`, `--cohort`, `--cohort-sha256`, `--primary-analysis`,
`--primary-sha256`, `--environment-profile`, `--environment-sha256`, `--seed` and
`--output`. Paths and hashes must refer to the actual accepted cloud files.

A completed Source is weights/metadata/latent checked and committed as one ZIP
and receipt, plus context. `source-handoff.zip` includes only this complete pair,
its context, a member manifest and an explicit local-only handoff record. No
automatic next seed, target or Final execution occurs. The external operator must
actually download, safely restore/CPU-check the original namespace/population,
seed/config/code/checkpoint/64-dimensional latent, upload and freshly read back
Drive before accepting it. All three accepted same-city Sources are required for
the later target/uncertainty stage. This Source-only CLI is not yet a bounded city
target runner or a complete city handoff. Do not refit already usable Sources or
blindly replace unresolved old SPO/MEL artifacts.

Generic `RunBackup` receipt wording now says filesystem readback, accurately
covering both an actual mounted caller and an explicit local outbox. Mounted
callers still must pass `require_drive_mount`; no guard was removed. Remote
acceptance still needs actual independent download/content evidence.

Local356 fixtures passed (6.014s), including8 new independent Source wrapper,
mutation/context/path/environment and no-CUDA guards; Ruff lint/format and diff
checks passed. Routine checks require no raw data/network/GPU. A metadata-only
preflight authenticated all existing city cohorts, the primary summary and all
budgets, without fitting: AMS134,640 Source examples; JHB2,340; LOA12,330;
MEL3,060; SPO2,610; SZH79,740. Each existing city plan declares378 target cells;
these counts do not assert execution. New Source GPU fitting and portable Source
publication remain unverified. No Final access, merge or issue acceptance.


## Recovery checkpoint — 2026-10-27, published prefix 135

The frozen runtime-fair UrbanEV recovery plan now has **135/742** target replays
externally published and independently restored. This is recovery-plan progress,
not the percentage of the thesis or the complete experiment matrix. Historical
648 proxy outputs and the451 matched prefix remain separately preserved; these
collections overlap and must not be added as unique experiments.

The latest12-run chunk, offsets123–134, completed on cloud GPU. Its35,631,751-byte
[canonical archive](https://drive.google.com/file/d/1Mmx8eFQNP_v-_fGEZ5k3Li-wJqdkSbl9/view)
has SHA-256 `5eef50ca177b8ab3c5db3fd4af0db66a5e28e4e9ae6f103e4f14aa2dea62eb29`.
A fresh Drive download passed safe restoration, complete daily/input/state checks
and all three original Source checkpoint reloads. The
[publication receipt](https://drive.google.com/file/d/1DoWUf-wfIK80JUSYx-gTQsZQs0bEVA_m/view)
and [independent proof](https://drive.google.com/file/d/175III5KRbw9UOVfErLhFdgF1BzVFO_oV/view)
are uploaded separately. Exact run IDs and hashes are recorded in
`issue23-primary-recovery-plan-evidence.json`.

Only after this publication was verified was the next bounded chunk135–146
submitted. Its completion and backup are not yet claimed. Each chunk stops after
at most12 runs pending external publication. A lost runtime can still lose its
unpublished chunk; already published chunks can be restored without retraining.
The notebook/runtime alone is not durable storage.

The exact committed code at `cab601d` passed356 tests in5.986 seconds locally.
The new separate-city Source outbox remains implementation-tested only; no new
city Source GPU training is claimed. CHARGED six-city completion, the remaining
runtime-fair comparisons, independent Final-lock approval and Final evaluation
are outstanding. No merge, protocol change or Final execution occurred.

### Independent city Source readback

`python -m tools.verify_city_source --help` documents the CPU-only verifier for
the single-seed Source wrapper. Supply the downloaded archive and its observed
SHA-256, the three accepted city input manifests, and the same pinned cohort,
primary-selection and environment-profile files used by the producer. It rebuilds
the expected context from those dependencies rather than trusting the wrapper.
It rejects extra/aliased paths, changed manifest or producer claims, reloads the
actual checkpoint and latent scale using `RunBackup`, checks the Source example
count and writes `source-verification.json` into a new output directory.

This is content verification, not remote storage verification. The operator must
upload the exact archive, download it again from Drive, run this verifier on the
fresh bytes, and publish the separate proof before accepting the Source. No
target may silently use an unaccepted city Source or an UrbanEV checkpoint.
The verifier does not fit a model or inspect Final values. Four additional
synthetic tests cover genuine CPU reload, changed dependencies/producer/count,
unsafe or extra members and overwrite rejection; the full360-test suite passed
in6.020 seconds. Real city GPU execution and remote proof remain pending.

### Actual LOA Source42 acceptance and verifier correction

The clean cloud checkout `b4376dc88d62c55ae23af56f3c0f595c2bfe463f`
passed360 CPU tests plus Ruff lint/format, then trained only the predeclared
LOA Source seed42 for10 epochs on12,330 same-city Source examples. The accepted
input ZIP SHA-256 is `eca98b9b1be158e91379d98599c3b89a6fef3106c30f7cf05961369d8d44a13e`;
the [launch kit](https://drive.google.com/file/d/1M6R4YEvfCRcbkqlI-eOfNioKal9R8km3/view)
pins code, primary recipe, cohort and CUDA/NumPy profile. Source/outbox work took
35.623069401 seconds, including local verification/packaging; this is not the
whole provider allocation or exact billed GPU cost.

The first independent verifier attempt stopped after CPU restoration because it
compared Source-only `ev_models/` fingerprints with the runner's four-package
fingerprint. Source and outer producer commit, clean flag and all actual model
hashes agreed. The verifier now compares the Source-scoped projection while
retaining exact full-core checks on the outer handoff/context. The regression
fixture includes a nonempty runner fingerprint to expose this distinction.
The failed proof/logs are preserved under
`runs/issue23-loa-source42-publication-20261027-v1`; only verification was repeated,
with a fresh Drive download and new output directory. No checkpoint was changed
or Source refitted. The360-test corrected suite passed in6.294 seconds locally.

The [Source wrapper](https://drive.google.com/file/d/1b4uLKPW5tYsFc8EruxgpE4LPgwVORqHm/view)
is868,439 bytes/SHA-256
`18549a2aed3e7d4277206aebbb16f0da5382d920976a91e82d213c8139eb3af8`;
its actual epoch10 checkpoint is
`ca703dc98859cefc8ac9145a97970c0b0c2f083eb07fcc39d56fd417d3d1b419`.
The [actual Drive-roundtrip receipt](https://drive.google.com/file/d/1t4nqCC1yuxY4Yvj1O1OOQH6EN8xyg6Td/view)
and [independent CPU proof](https://drive.google.com/file/d/1lI5vZjgNoxJY8uH6WXpd_6ViNGIL6H5q/view)
preserve exact recipe/input/Source/latent identities and original training log.
LOA target adaptation/evaluation and seeds43/44 were not completed by this receipt.
This is Source acceptance only, not a city result or method-effectiveness claim.

### Bounded city target consumer — implementation only

`tools.city_target_outbox` consumes three independently published same-city Source
pairs, restoring/rechecking their actual checkpoints before any target fitting.
`source-kit.json` pins context, Source archives/receipts and the three external
publication receipts. Those receipts are operator assertions backed by actual
download proofs; the local CLI does not authenticate Google Drive or manufacture
remote acceptance. The CLI rebuilds city inputs/cohort/primary recipe/environment,
rejects cross-city/changed identities and keeps new outputs separate from inputs
and the Source kit. It never imports or invokes Source training.

The complete predeclared budget/entity/seed/method order and Source-kit identity
are hashed before execution. All14 unique variants, budgets7/14/28 and seeds42/43/44
remain; the existing full city cohort is unchanged. A call executes at most12
targets, checks daily/input/latest states, exports canonical parts plus all three
Source dependencies and stops for external publication. Every subsequent call
requires the exact previous same-city/plan/range publication. There is no
automatic next chunk, Final role or full-city acceptance. `--help` documents
the hash-pinned dependencies and offset/count arguments.

Six new fixtures cover complete method/budget/seed order, Source-kit changes,
unaccepted publication, changed weights/namespace, cross-city continuation and
the cloud-CUDA gate. The full366-test local suite passed in6.412 seconds;
Ruff lint/format passed. This does not yet prove target GPU execution, complete
city integration or remote target publication. Those require actual cloud runs
and independent readback. Core `ev_models`, `ev_control`, `ev_runner` and
`ev_baselines` remain byte-identical to `1ac2ae0`.

## Execution checkpoint — 2026-10-27, primary prefix195 and LOA1

This checkpoint supersedes earlier progress counts without changing the frozen
population or recipe. **195/742** new-runtime UrbanEV replays are durably
published and independently restored. The latest
[183–194 archive](https://drive.google.com/file/d/1ekdRidg9ET8rTiI66GL3COh6KAcoGqgu/view),
[receipt](https://drive.google.com/file/d/1IuuCJwzeurEt1hxH2diwev8Msg-08F3q/view)
and [independent proof](https://drive.google.com/file/d/1NRXffIdMtJ3FP6Un9KFjeUQZ1xhpkrq_/view)
record complete daily/input/latest-state and original Source checks. Primary
offsets195–206 were dispatched; completion/publication are not claimed here.
This count is neither thesis completion nor unique experiments across overlapping
historical collections.

All three predeclared LOA Sources completed10 epochs on12,330 same-city Source
examples in seed order42/43/44. Each actual wrapper was uploaded, freshly
downloaded and independently restored/CPU-loaded. Seed42 evidence is above.

| Seed | Epoch10 checkpoint SHA-256 | External proof |
|---|---|---|
|43|`31ee68e5ed021f4318b9fc1a239c30a914c8d2c8f3b40fabe2462cca43538086`|[wrapper](https://drive.google.com/file/d/1BBL1vezCemLPOlp7YgJ8cwivb6q4zCgs/view), [receipt](https://drive.google.com/file/d/1bPZTExQ3BB0PPRS-aLeZIZhTwJCaAwXC/view), [proof](https://drive.google.com/file/d/16pr4yaAxp450CQaRl68C66lgOjHq4lO9/view)|
|44|`1549235c7bbb948005bdd970cb4a04d8527639f5f5d22bffa44ff3143dd47b8e`|[wrapper](https://drive.google.com/file/d/1Ilg5TueVkuaOKu9OM5I4Sf1xJNZcj60m/view), [receipt](https://drive.google.com/file/d/1NNVhg-BBizUiEZ_l1_qvHCcyzQvnIVhj/view), [proof](https://drive.google.com/file/d/1ofahGsNGBajMDxmgN05Inky8EjHi2D-1/view)|

The [target launch kit](https://drive.google.com/file/d/1EMz-p_MhuZ8vDzWgXGLuhCqS1NIml7we/view)
pins all three accepted Sources and the unchanged378-cell LOA order before
target execution. The clean target checkout
`aa9f91cdc828e0d48c693a26b306208ec41de640` passed366 cloud CPU tests plus
Ruff lint/format; setup took32.140028441 seconds. No GPU model fits overlapped.
Preparation/transport/verification overhead remains separate from model timers;
these timers are not provider billing estimates.

Exactly the first frozen cell, `charged-LOA-201-7d-adaptive-seed42`, completed
90 issued and90 scored Development days,270 candidate updates and6 audit updates.
MAE is1.267744379 kWh; RMSE is1.611225697 kWh. This is **one cell**, not a
baseline comparison, a favorable selection or a complete city result. All377
other cells remain required. No Source was refitted or configuration reselected
after observing this value.

The [target archive](https://drive.google.com/file/d/1NVFIpDSSJLOfTvZsb6u45amf5WnEEduu/view)
is12,584,285 bytes, SHA-256
`cc24309d24cd473838b0ce3073d8aec328b6a104f563a6c0771bf5f2887073b5`.
Its [receipt](https://drive.google.com/file/d/1JA2oyl5K_ThHKBcoPtdOoo2IW6e6kR-q/view)
and [independent proof](https://drive.google.com/file/d/1D3PwdC8mRSTl4ESMDp201qen48Ox3TuA/view)
follow an actual fresh Drive download, safe full restoration, frozen city/input/
config/code/Source checks, complete daily/input/latest-state equality and CPU
reload of all three Source dependencies. No bundled code or training ran locally.
The companion recovery-evidence JSON records exact receipt/proof hashes.

SPO/MEL recovery, remaining cities/primary cells, complete paired analysis/cost,
independent Final lock and Final evaluation remain outstanding. No merge, issue
closure, Final access or claim of Adaptive superiority occurred.

### Windows CI archive-path correction

[Actions40411194731](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/40411194731)
at `98bd459` passed Ubuntu and failed Windows job121882009748. All366 fixtures
ran; the sole error was `test_one_seed_descriptor_keeps_three_source_dependency_package`:
`shared_source_package` converted a relative native Windows path with `str`,
producing backslashes that the portable ZIP path guard correctly rejected.
The fix uses `Path.as_posix()` for ZIP member names, keeping the guard strict.
The fixture now requires the exact twelve portable Source member names.
The complete local366-test suite passed in6.133 seconds; Ruff lint/format passed.
Windows confirmation requires the new CI run, not inference from macOS.

This changes archive naming on Windows only. Existing Linux cloud member names
already use forward slashes and have independently passed transport/content
verification. Frozen running checkouts and accepted artifacts were not modified,
and no models were refitted. Core method files remain unchanged.

## Durable checkpoint — primary224/742, LOA13/378

All212 selected-proxy recovery runs are independently published. The
[last proxy archive](https://drive.google.com/file/d/1Z8vaMCHHedl9IUj02MHC0xqlpFeE6Y5T/view),
[receipt](https://drive.google.com/file/d/1wjx1LMZMb4cmT2kFzkspS0sWuLiG4Qrv/view)
and [proof](https://drive.google.com/file/d/1wS3dtGeaYyO2la8g8VUHoKgp3Ev2vrIX/view)
complete this family. A read-only comparison of all212 with the original frozen
references found zero differences in nine checked fields: MAE/RMSE, scheduled/
issued/scored counts, prediction identity, candidate/audit update steps and final
branch-state hashes. Maximum checked metric delta is0. The
[comparison script/results](https://drive.google.com/file/d/1asM5j-EBqFQBA5UsS9rshVyaE6lFtUJx/view)
ZIP is8,776 bytes/SHA-256
`1759f0b3e30986bc8d9762effa708c38d7c463b11358b7d128e6fe1709a25177`;
fresh Drive download/CRC/all member hashes passed. This is reproduction evidence,
not algorithm effectiveness, equal runtime cost or permission to omit the530
matched replays required by the frozen runtime-fair plan.

The first12/530 matched replays also completed and were independently restored
after actual Drive download: [archive](https://drive.google.com/file/d/13aGOScQAS-7ehP3TBypfCICvtAePxYRU/view),
[receipt](https://drive.google.com/file/d/1l1QIewlT7arzrpLkFOPKEu4UQMNYJawT/view),
[complete proof](https://drive.google.com/file/d/1T2UyJsOkIohua7Z14g9llXqevedus7cN/view).
The first matched-family call had no previous matched receipt; its operator
required the complete proxy212 publication, without falsely passing that as a
same-family predecessor. Next matched offsets12–23 were dispatched; live PID2791
was polled with nine local completions, not accepted as a published chunk.
The CPU operator supports this explicit empty-predecessor boundary; three valid
and four invalid boundary fixtures passed without network or fitting.

LOA now has13/378 frozen target cells independently restored, with all three
published Source dependencies retained. The additional12-run
[archive](https://drive.google.com/file/d/1073tqC5GYB_kEtXRnsv01gZKUPgO-u2A/view),
[receipt](https://drive.google.com/file/d/1Z2h9-JQyITtTVKA3SjYJ7cdAPTRtAmm9/view)
and [proof](https://drive.google.com/file/d/1px-GuRhl3CLWRTKl3X26ntKaEGDAwF1w/view)
passed complete frozen bindings, daily/input/latest-state equality and three
Source CPU reloads. This remains an incomplete city/multi-seed comparison;
365 cells are outstanding. No results were used to change ordering or recipes.

[CI40411978648](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/40411978648)
at code `e7e167278c21ade9c0eb63a300563e09f8eebe8d` now passed both
Ubuntu24.04 and Windows jobs after the portable Source-archive path correction.
The failed prior CI remains linked above. No artifacts, fixtures or scientific
thresholds were altered to hide it. Remaining matched/city runs, full analysis,
independent Final approval and Final evaluation are still mandatory.

### Latest accepted prefix: primary236/742, LOA13/378

Matched offsets12–23 are now independently published, bringing the new-runtime
recovery prefix to **236/742** (212/212 proxy and24/530 matched). Their
[archive](https://drive.google.com/file/d/1FUGDvQol2n8XQPyiILmssQ1rP0hJ5_0P/view),
[receipt](https://drive.google.com/file/d/1qfDb5aVEghzSj7RUzuyDsJHpahxNq5V4/view)
and [proof](https://drive.google.com/file/d/1MEDYsNAF_f6ey52il_ar2XbmONPKJ3tI/view)
passed actual Drive readback and full Source/daily/input/latest-state equality.
Next matched offsets24–35 were dispatched only after this publication. Actual
PID2850 was polled live; its completion and publication are not claimed. LOA's
verified13-cell prefix and all three Source checkpoints remain preserved.
Neither count indicates a completed experiment matrix, thesis or Final gate.

### Latest durability checkpoint: primary260/742; original SPO Sources recovered

Matched offsets24–47 have now passed actual Drive redownload, exact archive
fingerprints and independent daily/input/latest-state comparison with Source
CPU reload. The accepted recovery prefix is **260/742**: proxy212/212 and
matched48/530. These are recovery executions, not a count of unique scientific
experiments or a percentage of thesis completion.

The latest12-run [archive](https://drive.google.com/file/d/18ebdrI7l6BuT1iqe2IWLHHgbq06w5PnT/view),
[publication receipt](https://drive.google.com/file/d/1mdmVTP5OiEPEN5QAry0QSZJzoJnMi_gr/view)
and [independent proof](https://drive.google.com/file/d/15RdE7LHZ3pspkuVwbt-sVJZEaW19xbLC/view)
are outside the Kaggle runtime. Its archive SHA-256 is
`7da739340542d7d0f51cc44c5efbcab78cfb9d26cc87ea892c420f3071870715`.
Offsets48–59 were dispatched only after that receipt was uploaded, and were
polled live. Their completion and remote publication are not yet claimed.
LOA remains13/378 independently published targets with all three Sources.

All three original SPO Source weights, run reports and stdout were compared
byte-for-byte against the authenticated historical metadata ZIP. Their complete
core-code fingerprints and runtime profile match the current fixed methods.
They were repacked without fitting; the original producer remains
`9057364e6a8e663b9ba9c204621d109c02bed3e0`. New wrappers have been uploaded and all three passed independent CPU verification
after fresh Drive download, including the exact2,610 Source examples per seed.
Publication receipts and verification proofs are also on Drive; their identities
and hashes are recorded in the accompanying evidence JSON.
This does not recover or accept the missing original378 SPO target raw payloads.

Each bounded job stops after at most12 runs pending external publication.
A runtime failure can still lose an unpublished chunk; verified published
chunks can be restored without refitting. Run IDs, source/input/config/code
bindings, checksums, daily records, latest states and verification logs are
retained. Full Sprint3 analysis and independently approved Final remain pending.

### Primary284/742 and first SPO reconstruction independently published

Matched offsets48–71 passed fresh Drive redownload and complete independent
Source/daily/input/latest-state checks. The new-runtime recovery prefix is
**284/742**, comprising212 proxy and72 matched replays. The latest
[archive](https://drive.google.com/file/d/1PzzxtRlZVdA9VaAK6R5-5pWPaJcDl6X1/view),
[receipt](https://drive.google.com/file/d/18VlfPs99iwSz9SF6zEfFTFnY2638RMAQ/view)
and [proof](https://drive.google.com/file/d/1yjKPgLX2p-JHfGfkaTdv3jmI8mRC1aMH/view)
are preserved outside the runtime. Next matched offsets72–83 were dispatched
and polled live; they are not yet counted as externally published.

SPO now has a complete378-cell frozen reconstruction plan using the three
original authenticated own-city Source checkpoints. The
[launch kit](https://drive.google.com/file/d/1mEQqKrQn2vPWfPRsZJHtHJyvkBXI0X5d/view)
passed exact input/Source checks and366 clean cloud CPU tests, lint and format.
No Source was refitted. The old runtime was rechecked and still showed
Session is starting and failed draft save; its original target raw export
remains undelivered. Reconstruction preserves the entire predeclared cohort,
all14 variants, three budgets and three seeds, independent of outcomes.

The first reconstructed target, `charged-SPO-17-7d-adaptive-seed42`, completed
all90 Development days and passed fresh Drive download, full independent
daily/input/state equality and all three Source CPU reloads:
[archive](https://drive.google.com/file/d/1QfQRvOqz6FcKb58RRoMX3qYzhqQIlhw6/view),
[receipt](https://drive.google.com/file/d/1rRJQqALcnE864IO25DSfoj0dkFsvr9kR/view),
[proof](https://drive.google.com/file/d/1Htl4gtWnIuSCaDcMOvcwWaab4Md4EoEa/view).
Its nine predeclared original/reconstruction metric/count/prediction/update/
latest-state fields match exactly. MAE is0.615875263 kWh and RMSE0.940861169 kWh.
This is1/378 reconstructed cells, not a baseline comparison, restored original
raw bytes, full-city acceptance or scientific effectiveness claim.
LOA remains13/378. No Final, peer approval or merge is claimed.

The first SPO original/reconstruction [comparison proof](https://drive.google.com/file/d/17GKk6VRQLd8x1Go_qXYnZLLNbPxvetDm/view)
passed fresh Drive size/SHA/CRC/all-member checks. Next SPO offsets1–12 were
dispatched as PID3439 only after the prior publication receipt and primary
GPU job had completed. This is a live dispatch, not accepted completion.

### Primary308/742; SPO13/378; all remaining-city inputs independently checked

Matched offsets72–95 are externally published and independently restored,
bringing the recovery prefix to **308/742** (212 proxy and96 matched).
Latest [archive](https://drive.google.com/file/d/1-PISKuy39c7KceE4aQhxuBgZybTdJfvZ/view),
[receipt](https://drive.google.com/file/d/15ckg5jgGsd8Kvyy8mhSr8cnlsn8HjHmj/view),
[proof](https://drive.google.com/file/d/1sapm3DjagHGea67IFSEdAf6IgK1S-Pbo/view).
No historical/recovery counts are added as unique scientific experiments.

SPO offsets1–12 also passed actual Drive readback, full independent daily/
input/latest-state checks and all three Source CPU reloads:
[archive](https://drive.google.com/file/d/1vLcx7Jfa5PNkLDkuATdQhc0zhtxZSaZF/view),
[receipt](https://drive.google.com/file/d/1eakPttA2zYXK0taxkwf9vt7XtxTVTdH8/view),
[proof](https://drive.google.com/file/d/1geTqFpwSMm1p6Xelc-RrLJQM-8u0zOBZ/view).
All12 match the nine declared original metadata fields; combined with the
first target this is13/378 reconstructed cells. The Source-repack, assembly,
cloud-launch, publication and comparison [operators/proof](https://drive.google.com/file/d/19oa4CF2E-CBvarG4YGq3y_VHle9ctq0X/view)
passed actual fresh Drive bytes/SHA/CRC/all-member verification.

MEL, AMS and SZH accepted input archives were freshly downloaded on cloud,
checked against release fingerprints, and validated against fixed cohorts.
The [cloud preflight proof](https://drive.google.com/file/d/1RLDbIZtio7ACfmRaX51yZX-3quluL8g3/view)
passed fresh Drive readback and [independent local metadata checks](https://drive.google.com/file/d/1X4EWt7HIbMtjBcRXzemOhchdYLzEKxsF/view)
for all three cities. Source training-example counts are3,060,134,640 and79,740
respectively. This is preparation only; no Final values decoded or fitting
in that preflight. The clean existing b437 Source checkout's360-fixture gate
was reused, not rerun and counted as three new suites. Original MEL Source/
target payloads remain unverified; they are not counted or overwritten.

First AMS own-city Source seed42 was dispatched as PID3623 using the unchanged
10-epoch primary recipe, original fixed seed/profile and accepted AMS Source
entities only. Its handle was polled live and epoch1–4 checkpoint files were
observed. Completion, final model publication and AMS target results are not
yet claimed. A completed intermediate epoch is being exported solely as
resume insurance, never as checkpoint selection or a completed Source.
No GPU fits overlapped. Source43/44 still require separate verified handoffs.

LOA offsets13–24 have now passed fresh Drive redownload and independent
full Source/daily/input/latest-state checks, bringing its prefix to25/378:
[archive](https://drive.google.com/file/d/1IczH1PPzEDpCEspHEc8sB2uGP3Vtzeqm/view),
[receipt](https://drive.google.com/file/d/1b-0gsYNbKzjwzLY3MtyHZf6AILvzLlGI/view),
[proof](https://drive.google.com/file/d/1VpTled81SFSO5xYPhWOiIOmO-Va6wZJ6/view).
AMS Source42 was subsequently polled live with epoch1–8 checkpoint files
observed; it remains incomplete until the10-epoch final handoff is verified.
All city and primary full-matrix, statistical analysis, independent lock
approval and Final gates remain outstanding.

### AMS Source42 final handoff accepted; next primary chunk live

AMS Source42 completed its fixed10 epochs and134,640 Source examples. Its
[final archive](https://drive.google.com/file/d/1_Kvx5MS4HZy1W4VCKxvejU-YRy2Gzah5/view),
[receipt](https://drive.google.com/file/d/1fZuIJO1uCLBHNfzQmABW3OJptGrIGBOM/view)
and [independent proof](https://drive.google.com/file/d/1GpGsHGx0xDjWb8drcNOl2521CvHIHfGI/view)
passed fresh Drive download, exact bytes/hash, full independent CPU Source
checkpoint, original input/population/config/code/seed and64-dimensional latent
scale/count checks. Final checkpoint SHA-256:
`a368c3ebabeb9cb91180ff01ee41b271dbbdf888b610083834bbc75a5b2eda2d`.
The Source outbox operation took381.5812 seconds including validation/training/
local packaging; this is not provider billing or isolated GPU fitting time.
Seeds43/44 and every AMS target remain required; Source42 is1/3 Sources only.

A fixed [epoch5 recovery archive](https://drive.google.com/file/d/1e14G14MmzW1z17STgsl7ON90rMMLHXK4/view)
and [CPU verification proof](https://drive.google.com/file/d/10AHN-VeXF0KmgSEcgIm7CGe-ND3Q63aK/view)
were also preserved mid-run. Actual Drive readback/checkpoint/optimizer/RNG
verification passed. This insurance checkpoint was selected by fixed epoch
index, never loss, and was not used as the final Source. No interrupted cloud
GPU resume was executed or claimed; exact continuation still requires the
original compatible runtime/CUDA topology and fixed recipe.

Matched offsets96–107 were dispatched and polled live after Source42 stopped.
Only308/742 primary replays, SPO13/378 and LOA25/378 are externally accepted
at this snapshot. No Final, study completion, peer approval or merge is claimed.

### Accepted primary320/742; AMS Source43 in progress

Matched offsets96–107 passed actual fresh Drive download, exact frozen
bindings, complete independent daily/input/latest-state equality and all three
Source CPU reloads. Latest [archive](https://drive.google.com/file/d/1ES7XX3IRSxWxVfWsm3lyxFlu5kRMKoW_/view),
[receipt](https://drive.google.com/file/d/1FTdXDwcH5ClWdsOwanYVTniqAH-Zpjy7/view),
[proof](https://drive.google.com/file/d/1tGsrk6KZ8u7n7k94rvtzEaTcihvtPFxy/view).
The prefix is320/742:212 proxy plus108 matched. Next matched108–119 is not
dispatched while AMS Source43 uses the GPU.

AMS Source43 was dispatched as PID3715 only after Source42's actual published
receipt was downloaded and SHA/content checked. Its live process, epoch1
checkpoint and134,640-example training log were observed. The fixed10-epoch
run is not complete or externally published; seed44 and every AMS target
remain required. Source42 is safely preserved as documented above.

The [all13 SPO original/reconstruction comparison proof](https://drive.google.com/file/d/13oq2z2HhGt50PjC-ms3_yL0K1820F3F1/view)
also passed fresh Drive bytes/SHA/CRC/all-member checks. All13 published
reconstructed cells match nine declared original fields. This does not waive
the remaining365 SPO cells or prove effectiveness. LOA remains25/378.
No Final, peer approval, merge or full Sprint3 completion is claimed.


### Durable primary344; all AMS Sources, MEL replication and SZH progress

Actual published and independently verified primary recovery is344/742:
212 proxy and132 matched. New matched ranges108–119 and120–131 passed fresh
Drive bytes/SHA, independent daily/input/latest-state equality and Source reload.
The latest [archive](https://drive.google.com/file/d/1MqGffTYWabUwQ-gfjRCE62dwE4WNaYdU/view),
[receipt](https://drive.google.com/file/d/1a9nLQ6IVf4AnihbC0FPBvZwyrCTrgMWl/view)
and [proof](https://drive.google.com/file/d/1UpSs6LI2-c2eeD5LsbYvReVuuVCT3Nwj/view)
are external to the runtime. Exact identities for both ranges are recorded in
the evidence JSON beside this report. These are recovery cells, not percentage
completion or unique full-study results.

AMS Sources42/43/44 completed their fixed10 epochs on134,640 examples each.
All three archives passed fresh Drive download and independent CPU checkpoint,
input/population/config/seed and64-dimensional latent-scale verification.
AMS first target1200/7d/adaptive/seed42 passed90 scheduled/scored days and the
same external publication gate: MAE12.79950616845391 kWh and
RMSE12.802859758457855 kWh. This single cell establishes neither superiority
nor full-city completion. [Archive](https://drive.google.com/file/d/1Xu6sQl4XJmHZKIAp72r4tXBp9L_8-gIo/view),
[receipt](https://drive.google.com/file/d/1Az5pgLKMBXlhHEeEWkDeKY888GBff62h/view),
[proof](https://drive.google.com/file/d/1yz-rWkbQUKv1tnXC3PfDPt8XVBbb-alt/view).
The next bounded range1–12 was dispatched as PID3995 only after all GPU child
processes were terminal success and the actual prior receipt was available.
It is not counted as published until independent external verification passes.

The original MEL session remains inaccessible for portable checkpoint recovery.
A [predeclared complete replication](https://drive.google.com/file/d/1QZHk7kOVcU61pfi4EmOLLgakf-m804aX/view)
retains the same city inputs, cohort, fixed seeds,10 epochs and378-cell matrix,
with new output paths. Original cached59 targets are not mixed or adopted.
MEL Sources42 and43 now passed fresh Drive and independent CPU verification;
seed44 and all new targets remain outstanding. Latest
[Source43 archive](https://drive.google.com/file/d/1F6-5gLRNVs0IX4Z2yTBe9BGG9kk30tPk/view),
[receipt](https://drive.google.com/file/d/1bdHXG_QRuku_c-B4QzsEVeALQHHCvwP7/view),
[proof](https://drive.google.com/file/d/1IepGwkzdFJXmWhWiOOTAoF9IImNtCkbh/view).
This is new execution, not recovery of original MEL bytes.

SZH Source42 completed10 epochs on79,740 own-city Source examples and passed
fresh Drive and independent CPU verification. [Archive](https://drive.google.com/file/d/1GN_i74J_TP4oAufxO3u9GJMAn27r6XdZ/view),
[receipt](https://drive.google.com/file/d/1o51qHhADQ8l9mQpOUGw1pov1bKClrxz2/view),
[proof](https://drive.google.com/file/d/1YWurNknyab0t5FnPK6j0M_uhHHqvtBrd/view).
Seeds43/44 and its target matrix remain outstanding. No UrbanEV Source
weights or cross-city pooling were used. SZH retains its separate temporal/
possible-overlap interpretation.

**Research finding requiring review:** on the first predeclared AMS1200
Development forecast input, Sources42 and44 produce near-zero predictions
(mean1.00e-9 and6.86e-10 kWh) with near-zero Softplus derivatives, while
Source43 predicts mean12.9387 kWh. Final normalized Source train MAE is
0.20237,0.02092,0.20237 respectively. The
[diagnostic script/results/Source bindings](https://drive.google.com/file/d/1yFj43gCsmsHa8pvTqfjhjevioAIoyv1l/view)
are preserved. This was CPU inference on one input, without opening Y/Final
records or fitting. Saturation is observed; its cause and population-wide
impact are not proven. Keep all three seeds. No favorable checkpoint selection,
reinitialization, loss/architecture change or claim of method effectiveness.

The last actual storage scan found14.916 GiB generated working content and
4.141 GiB filesystem free. No cleanup was performed. Preserve raw/input
archives, Sources, code, logs and all unpublished or failed partial work.
JHB remains378/378, LOA25/378 and SPO13/378 accepted. Full Development,
statistical comparisons, independent Final lock approval and Final remain
outstanding. No peer approval, merge or Sprint3 completion is claimed.

### All remaining city Sources verified; AMS25 paired diagnostic

AMS now has25/378 accepted target cells. Both new ranges passed fresh Drive
bytes/SHA, exact frozen bindings, complete independent daily/input/latest-state
proof equality and all three Source CPU reloads. Latest
[archive](https://drive.google.com/file/d/1aqyG5zgbrKhmK5vmUKuzKsvmEVAP3GTR/view),
[receipt](https://drive.google.com/file/d/1yxKvmUrC-Pbevi1vs4aL8tgXQkL_zPlQ/view),
[proof](https://drive.google.com/file/d/1DdnPozyh0oyLCVVwD3e7LcOAlsKdDNT0/view).
A separate [read-only diagnostic](https://drive.google.com/file/d/1Dz8LGDyvuoG6P3am2jRw491yUPUz6hhj/view)
rehashes all25 daily forecast/event commit chains and verifies the exact same
90 scored origins. The diagnostic archive also passed fresh Drive bytes/SHA,
CRC and both-member equality. It contains its rerunnable script and exact
publication bindings; no fitting or Final records were used.

The following are **partial Development observations for the first predeclared
AMS entity1200,7-day budget**, not city/population estimates. Seed42 has all14
variants, seed43 currently11; seed44 and the rest of the matrix remain required.
Do not average this unequal prefix across seeds or select the favorable seed.

| Method | Seed42 MAE, kWh | Seed43 MAE, kWh |
| --- | ---: | ---: |
| Adaptive | 12.799506 | 0.336414 |
| Fixed Retention | 12.799506 | 0.274458 |
| Full Fine-tuning | 12.799506 | 0.358287 |
| Target-only | 0.844062 | 0.794008 |
| Seasonal Naive | 0.089383 | 0.089383 |
| Frozen Source | 12.799506 | 0.213617 |
| Online Best | 12.799506 | 0.288696 |

This prefix exposes seed sensitivity and a poor Source-initialized seed42 case.
Adaptive also trails Fixed Retention and Seasonal Naive for seed43 here. The
observed Source42/44 Softplus saturation may help explain poor transfer, but
causality and the population-wide effect are not established. Complete the
predeclared comparisons, retain all seeds and report negative results. This
finding does not authorize silently changing architecture/loss/initialization,
selecting checkpoints, dropping seeds or opening Final.

MEL Source44 passed independent CPU verification after a fresh Drive download,
completing its three fixed10-epoch,3,060-example Source models. Latest
[archive](https://drive.google.com/file/d/1LJy2CrzDLVLCVkKW-vQVTJfqNVpWTZr1/view),
[receipt](https://drive.google.com/file/d/18LP3615GZ_kIZuM6dOfgtWuKAFf_FliP/view),
[proof](https://drive.google.com/file/d/1gNK6EaOZ-GDAbz1wgfjv29huJLvh4jBj/view).
All three were restored into a pinned [new target replication kit](https://drive.google.com/file/d/1qhzYHXuRZuUsq5mBEHBrKS3jFMhyq6NH/view).
Its first target15/7d/adaptive/seed42 passed90 issued/scored days and external
verification: MAE27.663882754392425 kWh, RMSE45.01648552700619 kWh.
[Archive](https://drive.google.com/file/d/1uy03jl_QbOJd-9cT3Kj-mChiG3R2VO8R/view),
[receipt](https://drive.google.com/file/d/1zIz2raIF0xzRofq4j-g0H4jTpzABwHXk/view),
[proof](https://drive.google.com/file/d/1tFiZ_8hKBJbnXvDoJPfXRgC7Dkz_4j3v/view).
This is1/378 new replication targets; original cached59 are not mixed/adopted.
Without paired baselines, this one value is not an effectiveness conclusion.

SZH Sources43/44 both completed10 epochs on79,740 own-city Source examples
and passed fresh Drive download, exact Source/input/population/config/seed
binding and independent CPU/latent-scale checks. Latest Source44
[archive](https://drive.google.com/file/d/1fX1rBJF3BD5m85Qgi9IssbBEJHBgkf4Q/view),
[receipt](https://drive.google.com/file/d/1LTejvqtAgDHrRVDFeY-vdAqP27g-o3JA/view),
[proof](https://drive.google.com/file/d/1EZjuEJkCTfUgXI2jsh5OVj4Realab8Fw/view).
The [three-Source SZH target kit](https://drive.google.com/file/d/1UetucVF4vQhrv5Luh3OeU_9ateDGS2ry/view)
was independently CPU restored locally and in cloud preparation. Both MEL and
SZH reuse the clean pinned aa9 target checkout and its existing366-fixture/
lint/format gate; these are not new366-test suites. All six CHARGED cities now
have their own three accepted Source checkpoints (including the independently
restored original SPO Sources), not pooled city/UrbanEV weights. Target matrices
remain incomplete outside JHB; SZH remains a separate temporal/possible-overlap
supplementary analysis and CHARGED upstream preprocessing limitations remain.

Primary matched offsets132–143 also passed external verification. Accepted
new-runtime recovery is356/742:212 proxy plus144 matched. Latest
[archive](https://drive.google.com/file/d/1Ed0kRN1bgmGd7Wm9gp-RlbgXltG6wQXI/view),
[receipt](https://drive.google.com/file/d/1_X_o5knuufv56PD8yniPxm-syfFMCS4C/view),
[proof](https://drive.google.com/file/d/1gHp-lfAy8KZXbMZoIiFZXthcTlT-9LOz/view).
Next144–155 was dispatched only after terminal success, the actual preceding
published receipt and the no-live-GPU-child guard. It is not counted as accepted
until independent external verification passes. No Final, merge, peer approval,
full experimental matrix or Sprint3-completion claim.

SZH first target4/7d/adaptive/seed42 subsequently passed independent external
verification on90 issued/scored days: MAE18.16418929969041 kWh and
RMSE23.541384442375847 kWh. [Archive](https://drive.google.com/file/d/1yhAfkSyaEOsoA7EVSBIWA6D1v-3VQq0w/view),
[receipt](https://drive.google.com/file/d/176MKOjs9brj4NM2J-G4DAYYmuM1oVjFu/view),
[proof](https://drive.google.com/file/d/1BJh0sOfZq7gogeOekSey-jR_2s7Ft1k_/view).
This is1/378 cells, not a paired baseline or independent geographical-validation
claim. All six CHARGED namespaces now have at least one actually executed,
externally verified Development target. Their matrices remain separate.

Matched144–155 passed actual fresh Drive and independent full-content checks,
raising the accepted recovery prefix to368/742:212 proxy plus156 matched.
[Archive](https://drive.google.com/file/d/1liFGw_VRkZ36UF_E6N2rbxyd-kdkmk5u/view),
[receipt](https://drive.google.com/file/d/14Y3YKNYmQsCMXFxdf3bZtt382LlFmKuM/view),
[proof](https://drive.google.com/file/d/1_NzISbQ-uJOPoRdYj7tyGE26LIQ75pNH/view).
The next bounded matched156–167 is dispatched after actual prior publication
and terminal-success guards. MEL replication1–12 also reached terminal success;
its external publication gate is pending at this observation. No unverified
batch is included in the accepted counters. Core research modules are unchanged;
these updates only record new run/provenance/negative-result evidence.

MEL replication1–12 passed fresh Drive and complete independent Source/daily/
input/latest-state checks, bringing its new verified prefix to13/378.
[Archive](https://drive.google.com/file/d/1U-8xQkh_1QUfHMyeWGpIw03VggdHK4KX/view),
[receipt](https://drive.google.com/file/d/159x5vjm00OORpkJ-JFilYiBmqE3d1m8B/view),
[proof](https://drive.google.com/file/d/1k6HJxHBQ98e98bAi0guQI02CfSpmZfZR/view).
Current accepted city target prefixes are JHB378, LOA25, SPO13, AMS25,
MEL13 (new replication) and SZH1, each against its separate378-cell plan.
These are neither pooled data nor full-study effectiveness results. Continue
from each actual published receipt; preserve all incomplete/failed work.

Matched156–167 passed fresh Drive and complete independent Source/daily/input/
latest-state equality, raising accepted new-runtime recovery to380/742:
212 proxy plus168 matched. [Archive](https://drive.google.com/file/d/1pf7C7sEKb5dO2ET4VHEXhvFi4M4KQalS/view),
[receipt](https://drive.google.com/file/d/1YX0YPMD0Ny89675eFr8yVi8K5WegJ7gs/view),
[proof](https://drive.google.com/file/d/1CqJBoGXulBbPlA5n40hZA09uOBK-VDmv/view).
Next primary168–179 has not been dispatched. AMS25–36 is now running as
PID4492, actually polled live after all other GPU children stopped; the previous
actual AMS13–24 publication receipt was downloaded and pinned by the launcher.
Its accepted city counter remains25 until the external gate passes. Never
restart it solely because browser observation times out. No Final/merge/full-
completion claim. Only maintained handoff/evidence files changed in Git;
research model/controller/runner/baseline bytes remain identical to1ac2ae0.

## October27 — durable428 prefix, complete first AMS seed group and storage guard

The latest externally accepted new-runtime prefix is **428/742**, comprising
all212 selected-proxy cells and216/530 matched cells. This is recovery progress,
not the fraction of the thesis completed. All four additional12-cell primary
batches (168–180,180–192,192–204,204–216) passed fresh Drive download, exact
frozen configuration/input/code/Source binding, full independent daily/input/
latest-state equality and all3 Source CPU reloads. Exact receipt hashes and
Drive IDs are recorded in the [evidence catalog](issue23-primary-recovery-plan-evidence.json).
Latest primary [archive](https://drive.google.com/file/d/1zdTBjUz8cgjvm5GU9XAI1lqAAjalpUWK/view),
[receipt](https://drive.google.com/file/d/1dCFJ-4z8m9g_ySnHwcs-aWEigd4C96xS/view),
[proof](https://drive.google.com/file/d/15XbjmBd2IZVM-Nkj9FgjlIt3DWJHz3mf/view).
Next matched216–228 was dispatched as PID5091 only after actual prior publication,
terminal success, no live GPU child and the working-storage guard. It has no
automatic successor and is not included in accepted counts.

Current separately verified CHARGED target prefixes are JHB378, AMS49, LOA37,
SPO37, MEL25 (new complete replication) and SZH1, each against its own378-cell
plan. All18 own-city Source checkpoints remain preserved; no pooling or new
Source fitting was used for these target batches. SPO's additional24 reconstructed
targets match all9 declared original fields exactly, extending the original
metadata comparison to37 targets; this does not recover the original raw bytes.
Latest SPO [archive](https://drive.google.com/file/d/1swpwnFzmHeOneosRfGz6AbcaZyRN_HoQ/view),
[receipt](https://drive.google.com/file/d/1K_JM0Z-GQX9EXJLoFbpGQo3-AcwmbW6T/view),
[proof](https://drive.google.com/file/d/1j5ScEyVfZwHhM8RjGW3-VcNe-RHKk61v/view).
All accepted handoffs exist locally and on Drive. Unpublished/failed work remains
preserved and is never counted as externally accepted.

### Complete first AMS group: adverse result retained

The first predeclared AMS1200/7d group now has all14 variants ×3 fixed seeds,
42 authenticated daily chains and identical90 scored forecast origins. The full
analysis includes CSV, JSON, PNG/SVG, scripts, environment and input/Source identities.
[Analysis bundle](https://drive.google.com/file/d/1VPRlng7dPVGzEYMR8XKDfLqpi5fbISUD/view),
238,205 bytes, SHA-256
`b52c5896e921b8f848f06484c0d64626c09c240019d286d2ebdbcd194506acfa`;
fresh Drive readback passed bytes/hash/CRC/all14 manifest members. Extract the
bundle under this repository's `runs/issue23-ams-first-three-seed-analysis-20261027-v1/`
for its documented relative paths. Plotting used a separate Matplotlib environment;
the training environment and research implementation were unchanged.

| Method | Seed42 MAE,kWh | Seed43 | Seed44 |
|---|---:|---:|---:|
| Adaptive |12.799506|0.336414|12.799506|
| Fixed Retention |12.799506|0.274458|12.799506|
| Target-only |0.844062|0.794008|0.685789|
| Seasonal Naive |0.089383|0.089383|0.089383|

![AMS1200,7-day history: three fixed seeds and six displayed comparisons; logarithmic MAE axis](figures/ams-first-three-seeds-20261027.svg)

Across all90×24 issued Adaptive predictions, seed42 ranges from
2.2545e-10 to3.1230e-8 kWh; seed44 from3.1881e-10 to6.7671e-9 kWh.
Seed43 ranges from10.3928 to13.9017 kWh. Thus near-zero predictions persist
through this complete replay under the frozen update budget, rather than only
appearing on the earlier single diagnostic input. Adaptive loses to Seasonal
Naive for all three seeds on this one station. Differences below2e-10 between
Adaptive and Fixed for42/44 are not interpreted as meaningful wins.

This is **one station/budget**, not population efficacy or a significance test.
Source/model/controller RNG vary together across seeds; this is not a controlled
causal Source-quality ablation. The cause and wider impact remain unresolved.
All seeds, checkpoints and negative results are retained. No method, head,
initialization, loss, epoch count or checkpoint selection was changed. The first
analysis script rejected expected seed-specific Source fingerprint differences;
the corrected verifier requires every other input field identical and each
Source exactly pinned. The failed script/log are retained; no experiment or
metric was changed to make the analysis pass.

### Storage durability and resumption boundary

A read-only filesystem check found `/kaggle/working` and `/tmp` on different
devices. A reversible move relocated34 **already externally verified** primary
scratch directories,114,408 files, into the runtime's own `/tmp` cache. Every
file hash was checked before relinquishing its old location and again through
the retained original-path aliases. Raw/input files, Source banks, code, root
export ZIPs and unpublished/failed chunks were untouched. No payload was discarded.
Working free space increased from2.509 to5.907 GiB; a later live observation was
5.343 GiB after subsequent writes. This is measured storage, not a runtime estimate.

[Move proof](https://drive.google.com/file/d/1gr-b7R16DSb3T3lCWMA4q6c6Mp7gw-tR/view)
(5,887,185 bytes, SHA-256
`ef4e5d9376184da00f4cfc2739baf1f196aaf9954b40c6705234c3af3223d82c`)
and [independent Drive readback](https://drive.google.com/file/d/16esaQkwHCxeshzui_MC6rjcBpQH6eSFe/view)
preserve the allowlist,34 file manifests, move journal, alias verification and
result. Local verification proves the archive/manifest consistency; the cloud
worker performed the actual file reads. New dispatches reject live GPU/cache-move
children and less than1 GiB working headroom. Existing city launchers were pinned,
compiled and [published](https://drive.google.com/file/d/11MhREnfcPZNrs4XgqsCW4xMHgdEUZIJD/view)
without changing their research configurations.

Both working and tmp runtime storage are **volatile**. Durability comes from the
canonical exports on Drive plus verified local copies. Those exports retain all
committed forecasts/events and the latest accepted model/optimizer/RNG state;
they do not promise every historical intermediate model state. If the runtime
vanishes, restore the accepted publication chain and continue the first unfinished
bounded batch. At worst an unpublished batch may need replay; completed published
batches and Source models do not need retraining. No claim of zero possible loss
inside a live/unpublished batch is made.

Sprint3, full paired analyses and Final acceptance remain incomplete. Final has
not been opened or executed. No autonomous approval, merge or issue closure.

Matched216–227 subsequently completed and passed fresh Drive download and all
independent Source/daily/input/latest-state checks, raising the accepted prefix
to **440/742 =212 proxy+228 matched**. Latest
[archive](https://drive.google.com/file/d/1DoFThQH4vB8HCflKzBE0LzyHRcpLFPMG/view),
[receipt](https://drive.google.com/file/d/19Ca1a0UoK6xabvOQZ5mqYpvCp0qgLWWt/view),
[proof](https://drive.google.com/file/d/1rSJ3_6kC9ABoOX2xX3GBK43BAzm_6oRx/view).
The SPO additional24-target [original-metadata comparison proof](https://drive.google.com/file/d/13JrrWLHBRm7e_CRT2IF5A1KhuSBbITSL/view)
also passed actual fresh Drive bytes/hash/CRC/all4 manifest members. Primary228–240
has not been dispatched. SZH1–13 was dispatched as PID5148 only after all GPU
children stopped, using its existing exact published receipt and fixed own-city
Source bank. SZH accepted count remains1 until the external gate passes.
The last working-storage observation was5.224 GiB. No new research code changed;
JSON syntax, diff whitespace and core-module byte identity checks passed.

## October27 continuation — primary476 and separately verified city increments

The next three12-cell primary batches passed independent external acceptance,
raising the frozen runtime-fair recovery prefix from440 to **476/742**:
212 selected-proxy and264/530 matched. All accepted batches have actual local
and Drive copies, exact frozen inputs/config/Source/code/environment bindings,
complete independently recomputed daily/input/latest-state equality and all3
Source CPU reloads. The newest [primary archive](https://drive.google.com/file/d/1bQKR1IcqdmESf9XYy6OpOFJcDC_v93MJ/view),
[receipt](https://drive.google.com/file/d/1F-LPYW3nZ4uoZ7KCjio6ci8cJX2TFDyp/view)
and [proof](https://drive.google.com/file/d/1DhN6wy-BYhGzVKRKguu334nzi-TNMi6G/view)
are catalogued with bytes/hash in the evidence JSON. This counts plan cells,
not unique experiments across overlapping old/new collections or thesis percent.

Separately, SZH1–12, AMS49–60 and LOA37–48 passed the same independent city
publication gates. Current accepted target prefixes are:

| Namespace | Accepted / planned | Latest increment receipt |
|---|---:|---|
| JHB |378/378|Previously complete and independently restored|
| AMS |61/378|[49–61](https://drive.google.com/file/d/1_SeSU8mOAun88DAdLKBDQuw-BZ2iZemw/view)|
| LOA |49/378|[37–49](https://drive.google.com/file/d/1eldoarngG12nPmEaVgBXv4zffW-8lkpt/view)|
| SPO |37/378|Previously published37, original metadata comparison retained|
| MEL |25/378|New complete replication; original cached59 not adopted|
| SZH |13/378|[1–13](https://drive.google.com/file/d/10pZPo9TAtPoyvvty0n8MDy5tcE5sAISZ/view)|

All18 own-city Source checkpoints are retained; these increments did not refit
Sources or mix cities. The original matched-completed Drive folder was inspected
read-only and is reachable with published Source/receipt/archive entries. Its
virtualized first visible rows are not a complete folder inventory. An empty
scoped connector search is not proof missing original bytes are irrecoverable;
239 original matched payloads remain undelivered, not proven destroyed. The
new frozen replays remain distinct replacement evidence requiring review.

The lead's reply to the Final-cohort question asked for clarification; it did
not select the66-pair candidate or authorize Final. The readiness report now
explains pair versus physical station,42 method/seed cells per pair and the
2,772 versus147,420-cell alternatives. No Final values were decoded or executed,
and no configuration or scientific method was changed. Full Development,
compute/capacity review, Final-capable interfaces and independent immutable-lock
approval remain outstanding. No new efficacy claim follows from these prefixes.

Latest continuation boundary: primary264–276 has not been dispatched. MEL25–37
was dispatched after all GPU children stopped and its existing exact prior
publication/Source/launcher identities were verified; it is excluded from the
accepted25 until external verification passes. The last observed working free
space was4.459 GiB, with the1 GiB launch guard retained. No raw/input/Source/code
or unpublished output cleanup occurred. The bounded read-only probe now reports
exact current PID/log and uniquely identified output, avoiding stale older cell
output as evidence of a live job.

MEL25–36 subsequently passed independent fresh Drive bytes/hash, complete frozen
city/Source/input/config/code bindings, daily/input/latest-state proof equality
and all3 Source CPU reloads. Its new-replication accepted prefix is now37/378;
[archive](https://drive.google.com/file/d/1gygOiKXmSKb4wavx4FpH03QANpfVo6-1/view),
[receipt](https://drive.google.com/file/d/1kbfAWc3Fw5JI8u-PDOagMJj4MQehLn16/view),
[proof](https://drive.google.com/file/d/1XCBbE4bMX-yt-RkKzU-qY48YQH9sbHcr/view).
No original cached59 adoption or original-byte recovery is claimed.
Next primary264–276 was dispatched as PID5561 from the actual published preceding
receipt; that exact handle was polled live (`None`) with4.316 GiB working free.
Accepted primary count remains476 until the external gate passes. All other
GPU children were terminal before dispatch. The current turn completed actual
artifact acceptance, not merely a status restatement or wait. Goal remains active;
Final scope and independent lock approval are unresolved, not implicitly accepted.
Only maintained evidence/clarification changed in Git; no research code changed.

## Fresh resource check after the lead's quota question

The current Kaggle session exposes GPU T4 x2 with literal UI quota text
`13:09 /30 hrs`; this snapshot does not independently interpret the counter
as used versus remaining. Primary264–276 PID5561 was freshly polled terminal0,
with no usage-limit error. Its outbox is locally downloaded and hash-checked;
it is not yet added to the accepted476 until independent Drive/content gates pass.
The old notebook's earlier connection problem is not treated as proof that this
working session/account has exhausted quota. Future GPU availability is not guaranteed.

The authorized Colab notebook showed a disconnected-runtime dialog. Reconnect
was attempted without running any notebook cells; the fresh allocation result
was `Cannot connect to GPU backend` and `You cannot currently connect to a GPU
due to usage limits in Colab.` This confirms a current GPU usage-limit block
for that notebook/account, not all of the user's accounts or a precise reset time.
No purchase, account switch, quota evasion, Run All or local real-data fit occurred.
Screenshots and a timestamped structured observation remain in the ignored local
resource-status run. Development/Final acceptance remains unchanged.

The primary264–275 publication passed actual fresh Drive and complete independent
Source/daily/input/latest-state checks. Its receipt/proof were uploaded, bringing
the accepted new-runtime prefix to **488/742 =212 proxy+276 matched**.
[Receipt](https://drive.google.com/file/d/1T0AqiZudHAMK2Dhqh4E_rGDewDLM1aYQ/view),
[proof](https://drive.google.com/file/d/1AjQ9v9xHcgTHIJJ1xoL9ZIOSdQG729lD/view).
No new fitting was dispatched during the lead's paid-compute clarification.
Current three-tab inventory contains Colab and two Drive tabs; the original
Kaggle tab17 is absent. Tab closure is not proof the allocated runtime has stopped
or exhausted quota. Primary276–288 remains undispatched. A bounded live job is
never restarted merely because its tab/observation disappeared.

A read-only capacity review now preserves an authenticated9-group/378-cell JHB
timing sample and conditional Final scope scenarios in the Final-readiness
report. Its fresh Drive bytes/hash/member check passed. The review changes no
methods, inputs, seeds or selected cohort, makes no Colab billing/parallelism/
completion-time guarantee and is not Final approval. No new training, Final
value access, paid purchase or account switch occurred. Previous turn classification:
progress from fresh resource evidence and rescued outputs; current turn adds
actual publication acceptance and a reproducible resource-sizing artifact.

## Colab scratch-path preparation and whole-unit parallel review

A concrete portability gap was found in the existing Source, city-target and
primary replay CLIs: their scratch output root was fixed to `/kaggle/working`.
They now accept `--cloud-root /content` explicitly, retaining `/kaggle/working`
as the default. The choice permits only those two roots, is recorded in new
handoff metadata, and does not approve or rewrite a GPU/environment profile.
Output admission rejects existing/data-overlapping paths, nested mounts and
Colab's reserved `/content/drive` destination. Scratch is not a published Drive
backup. Legacy transport schema names are retained for compatibility; actual
runtime/profile and the recorded cloud root establish provenance.

No model, loss, controller, runner, baseline, Source weights, dataset, budget,
seed, clock or selection rule changed. The previous Kaggle producers remain
pinned at their own recorded revisions; this patch was not deployed into a
running experiment or used to create a Colab training result. An old Kaggle
profile remains invalid on a different Colab environment. GPU allocation,
clean dependency/profile recording, input/Source restoration and independent
CPU preflight are still required before using a new environment-bound manifest.

Verification: **373 local tests passed** in5.809s, including7 new root-admission,
all-three-CLI parsing, mount/data preservation and CPU-fitting rejection tests.
Ruff lint passed; all194 Python files passed format check; `tools.sources list`
and `git diff --check` passed. Core `ev_models/ev_control/ev_runner/ev_baselines`
remain byte-identical to1ac2ae0. No cloud GPU, fresh raw acquisition, new runtime
resume or research effectiveness is claimed from these fixture checks.

A separate metadata-only [whole-unit partition review](https://drive.google.com/file/d/12BhdklYVx18h7F5GP4wpuAkxOtlQOg9X/view)
records exact original config/input/Source identities and accepted prefixes.
Archive155,693 bytes, SHA-256
`ce61d4246498a47cec2962df1728b6436723aa2835cec3455cdb6675a8cc2753`;
actual fresh Drive bytes/hash/CRC/all7 manifest members passed. Variant names
come from the frozen primary recipe; no error/activity/outcome rank was used.

The current-environment queue remains1,947 missing cells. If all remaining
incomplete units move to a new Colab profile, the safe scope is150 complete
units ×14 variants =**2,100 cells**, including153 declared repeats of partial
units. A unit is dataset/city/entity/budget/seed. Retain complete accepted old
units; never stitch partial old/new methods into a completed same-runtime
comparison. JHB is complete and does not enter this queue. Original metadata,
artifacts and current Kaggle continuation plans remain unchanged.

| Namespace | Current missing cells | Whole-unit cells if migrated | Declared repeats |
|---|---:|---:|---:|
| UrbanEV SZH |254|364|110|
| CHARGED AMS |317|322|5|
| CHARGED LOA |329|336|7|
| CHARGED SPO |341|350|9|
| CHARGED MEL |341|350|9|
| CHARGED SZH |365|378|13|

Hypothetical two-worker lanes contain1,050 cells each; three-worker lanes700.
These are identity-sorted deterministic whole-unit assignments, not allocated
GPUs, a guarantee of equal runtime, an active new experiment plan or Final
approval. Every worker needs a separate new attempt/output root, actual profile
and immutable bindings, no shared live optimizer/RNG, and external publication
after at most12 runs. A14-method unit may span chunks on its assigned worker.
Different hardware/profiles must not be silently pooled into comparable cost
numbers. This is resource feasibility evidence under #23, not a competing sprint
schedule or a silent replacement of the accepted742-cell recovery plan.

## October 27 — authorized E2E checklist, current peer comparison and Colab resume gate

The lead authorized continuation after the earlier stop. The single task-level
[E2E checklist and stop/recovery rules](https://github.com/HungLD9505/adaptive-retention-ev/issues/23#issuecomment-6433415375)
are now on Issue #23; a new active execution goal preserves those gates. This does
not approve Final scope, method changes, automatic merge or main promotion.

Read-only local inventory found 67 publication-verification records, including
overlapping/historical collections. This is not 67 independent experiment batches.
Fresh local SHA/ZIP-CRC rechecks of the already downloaded primary276–288,
primary288–300 and SPO37–49 wrappers passed; see the
[bounded byte audit](issue23-resume-gate-local-artifact-audit.json).
Externally published primary prefix remains500/742 (212 proxy+288 matched);
the next12 have local independent verification and raw Drive bytes but their proof
publication still needs completing. Do not silently promote them to full handoff.
SPO's accepted reconstructed prefix is49/378, not its older37 snapshot.
AMS61–73 cloud completion is not counted without external publication acceptance.

The [current Hung component recheck](implementation-comparison-readiness.md#october-27-current-head-recheck)
pins PR #72 at30fe7d and retains head/bootstrap/profile differences. Encoders agree
under shared encoder weights and latent loss/gradients match exactly on bounded
CPU fixtures. Full model/controller/runner parity and a fair metric leaderboard
are not established. No Hung weights or implementation were adopted.

The new [Colab notebook](https://colab.research.google.com/drive/12pPMj0ghylZjbYZgr-yqUUW_HV7xrM6w)
obtained Tesla T4, Python3.13.16, PyTorch2.11.0+cu130; fresh child processes use
NumPy2.3.3. Three bounded processes ran a five-day synthetic CUDA fixture:
uninterrupted, partial through day2, then resumed from a SHA-verified archive
copied back from mounted Drive. All three exited0. Total measured orchestration
was28.636s, excluding runtime allocation/setup. Complete model/Adam/RNG/cursor/
controller state (excluding measured cost durations), prediction hashes,
decisions and counters match exactly. Two block decisions kept the active policy;
this fixture does not cover a switching audit, missing/delayed labels, epoch-boundary
Source resume or real-data migration. Existing evidence for those paths retains
its original environment and scope.

[Exact cloud result](issue23-colab-resume-gate.json) and
[independent Drive API readback](issue23-colab-resume-readback.json) authenticate
the1,340,486-byte checkpoint archive SHA
`4848e73f1e4d97b68bd6b20db1be8fee429e4a41d067a9f7d065ea7238c6ed80`.
The external CPU integrity check verified three committed ticks, their hash chain
and three candidate states. Direct CUDA-tagged Store restore on CPU failed;
explicit map_location=cpu was used only for independent integrity loading, never
as a cross-device resume claim. The first local integrity command also lacked
Torch in system Python; the pinned model environment was used for the actual
check. Raw failed attempts are preserved locally. Exact report bytes were fetched
through Drive rather than relying on JavaScript-rounded large RNG integers.

[Drive folder](https://drive.google.com/drive/folders/1k-5ytClnEU0VB5Ds9bqGI1xFqW16R9Tm)
contains the checkpoint, probe source, summaries and logs. Connector metadata
reports shared=true; a second-user access test was not performed. The executed
core code is1ac2ae0, byte-identical in ev_models/ev_control/ev_runner/ev_baselines
to the current6d3feec review head. No actual VM deletion/network outage, real-data
benchmark, Final execution or completion of E2E is claimed by this fixture.

Colab reported99.97 available units and approximately1.15 units/hour for this T4
at observation, with two active sessions. That is a provider UI estimate, not a
guaranteed job price or a claim that both sessions use GPUs. The lead explicitly
requires compute conservation. Initial real-data migration/resume preflight is
capped at2 further units and30 minutes, with bounded child timeouts and no bulk
queue before measured capacity review. Provisionally reserve30 units for later
Final/analysis; this is a reserve, not evidence that Final fits. Do not consume it
or silently remove mandatory methods/seeds/budgets; report a scope/capacity blocker
if projected work does not fit. Disconnect idle owned GPU resources after required
artifacts are preserved; do not terminate another session or discard unique state.
No fake clicks, keep-alives, automatic quota-evasion account switching, duplicate
Run All launches after reconnect, or unlimited retries are authorized.

Only synthetic fixture updates ran this phase; real Development queue continuation,
whole-unit profile migration, epoch/day real-data restore and immutable Final
approval gates remain next. The previous373-test/CI result is historical; this
prose/evidence update does not claim a fresh full-suite run.

### Real-data restore gate and first bounded Colab comparison partition

The same Colab T4 then ran an explicitly declared operational Development gate:
UrbanEV1001,7-day budget,seed42,14 replay days, the existing Source10 checkpoint
SHA `a3d3485d8d9a3e96c0483ab61e659e3a31b0f9bd62cc51ae6b77c0d204920d8b`
and unchanged calibrated learning/retention settings. Only the probe horizon is
14 days rather than the scientific90-day matrix; this probe is not counted as a
matrix cell or tuning result. Whole/partial/resumed execute in separate processes;
the partial stops after five committed ticks, is copied to/from mounted Drive,
then resumes. Prediction identity, final candidate model/Adam/RNG states and
decisions agree exactly. Whole issued/scored14 days; orchestration35.128s and
whole runner4.608s exclude input download/runtime setup. No VM deletion was used.

[Exact real-data gate](issue23-colab-real-resume-gate.json) and
[external verification](issue23-colab-real-resume-readback.json) retain original
JSON integers. Fresh authenticated Drive download outside Colab verified the
1,599,548-byte partial ZIP SHA
`e25f773369db5016b9b2fa92bae5818f2ebbe135397379ec86b345ff4af0d660`
and ZIP CRC. Independent local verification reproduced all four scored days of
the five-tick partial from accepted input bytes and CPU-verified its latest
model/optimizer/RNG state against the committed run report. This integrity load
does not claim cross-device continuation. [Drive evidence](https://drive.google.com/drive/folders/1NJABKJIO8ewAxEdAhewXRYlo5O4zPaor).

Before dispatch, the [next unit and allowance](https://github.com/HungLD9505/adaptive-retention-ev/issues/23#issuecomment-6433753277)
were declared: UrbanEV1165/28d/seed42,90 days, all14 frozen variants in one actual
Colab environment, first12 then external verification before the last2. Ordering
minimizes already-accepted cells needing repetition, then budget/entity/seed;
it does not rank by outcomes or remove any incomplete unit. This unit repeats4
earlier partial-method cells solely for runtime fairness.44/69 primary units
are already complete at accepted proxy212/matched288 prefixes;25 remain incomplete.
The enclosing14-method unit is not accepted until all14 new same-profile variants
are verified. Old partial outputs remain historical evidence, not combined with
the new unit or silently removed.

Operator kit55,700 bytes, SHA
`5e0193d79c588f988adad3cc4404598c46c67b2ba1d293c98d1bf2a79a5950e4`;
derived frozen-reference batch plan SHA
`9f7b26b32a088208c4a111bbaaaaa0a688b628548ab9253538dbc3e0bf5461fe`.
The existing1ac2ae0 `tools.replay_missing_primary` runs unchanged behind a finite
operator wrapper. Derived reference scores are kept only for discrepancy
reporting, not adopted as new outcomes or described as original-byte recovery.
All three original Source bytes/reports/logs are retained and preflight checked;
no Source fitting or Hùng implementation is used. The new context records actual
Colab profile/core/input/config identities, not the old Kaggle profile.

The wrapper allows at most120 seconds without a completed run and1,200 seconds
overall, terminates the child on timeout, preserves its outputs and does not
retry. The batch allowance is1 unit with30 units reserved; the T4 UI rate is an
estimate and does not prove the entire remaining E2E fits. Actual PID8454 was
observed live with two independently checked/mounted-backed-up targets at the
first status sample. This is an execution observation, not12-run completion or
external handoff acceptance. Per-run Drive backups and logs are followed by
external verification before the remaining2 or another unit.

The first12 subsequently completed with child exit0 in96.200s. Cloud daily/input,
latest-state and canonical export stages all passed. Five canonical parts total
25,977,181 bytes, catalog SHA
`a8dbd68f38f71e14012480bd0d82906d50cb21b814e678e42145376c85ffac66`.
Fresh off-Colab Drive downloads verified every part's size/SHA/ZIP-CRC; safe restore
checked3,373 files, independent daily/input verification checked12 runs/2,220 hashes,
and independent CPU state verification checked all12 latest states. All3 original
Source dependencies were independently CPU-loaded against their original SHA/epoch/
seed identities. No downloaded Git bundle was executed. The Drive connector did
not return a usable raw code.bundle URI; ordinary direct Drive downloads with
unchanged expected hashes completed the transport without changing permissions.

[Partition receipt](issue23-colab-unit1165-first12-receipt.json),
[raw parts and independent proofs](https://drive.google.com/drive/folders/1YN4rJ6dKG6Oh01gF-a_3wvTs7B8XWe84).
Original operator receipt SHA
`a9dd550e95d50aaefc111299d6954a702ad4504bda5df592634efd7109583717`
and5,294-byte proof ZIP SHA
`c9c46765642e92655870838c0444a3965f1b9def79531f307f6e21c142bbdae1`
were copied to the shared Drive before the last2 were dispatched. The tracked
receipt additionally includes the observed transport IDs/folder and is therefore
a different derived evidence file, not claimed to have the operator receipt hash.

Only after that external verification did the same-profile final2 start: Uncertainty
recipe1 and Without Source Initialization, same1165/28d/seed42/90-day identity.
New plan SHA `b9ea8a2fa8138240678a056d08a3160a9f241198ce1c0f7edcb34b5a1c8f80f5`;
kit SHA `0dd91978ff9b3af187c2dea44d4d004dcc7e6f8e20516db80c1d765cb15ee56b`.
Its wrapper requires the exact prior receipt and allows at most300 seconds total,
120 seconds without run progress and0.25 units, retaining the30-unit reserve.
Actual dispatch PID11151 was observed; no terminal/whole14 acceptance is inferred
from that dispatch. The14-method unit still requires complete last2 external proof
before entering any canonical comparison collection.

The last2 then completed with exit0 in30.017s. Cloud daily/state/export stages
passed; three canonical parts total13,904,671 bytes, catalog SHA
`844fb9ddfc120c5ddceafb4cbdcf1786193d39dae25e631b2699eaec95229617`.
Fresh off-Colab downloads passed all part sizes/SHA/ZIP-CRC and safe restore of571
files. Independent daily/input verification reproduced2 runs/370 hashes and
independent CPU verification authenticated both latest states.

[Complete unit acceptance](issue23-colab-unit1165-acceptance.json) now proves all14
unique frozen variants, exact original configs/input bindings, the same actual
environment/code and identical52 scored origins across all methods. Each method
scheduled90 days and issued59 forecasts; missing-history/label gates explain the
smaller evaluated population and remain in the preserved schedules. Initial
adaptation is present; this is not a source-checkpoint-only unit. This one unit
is not a population estimate or proof of Adaptive superiority.

The two batches took126.217s combined child wall time and98.929s summed runner
time, excluding runtime/setup/download/export/independent verification/idle costs.
The externally verified full-unit receipt SHA
`071d8f8b4d5c6c337bfc2b210b273426bf8a400d5b5907be770acfe5567b22ef`
was saved to shared Drive and freshly downloaded with that exact hash:
[receipt](https://drive.google.com/file/d/1lSF4KEhBWWig7kUvweqNuY268gXrSDrC/view?usp=drivesdk),
[last2 raw parts](https://drive.google.com/drive/folders/1_KaL6F-TvlxTLynCBU3eG0QOcXPjY8iL).
Matched analysis must use the complete new14-method unit instead of its4 old
partial-method cells, while retaining all historical bytes. Do not count the4
repeats as additional independent observations or change the old contiguous
Kaggle publication prefix. Under that whole-unit ledger,45/69 primary selected
comparison units are complete,24 remain incomplete; this is not thesis completion.

The provider UI then reported99.21 available units, approximately1.07/hour and
one active session. Compared with the initial100 balance, this includes setup,
verification and idle resource allocation; it is not a direct experiment-only
bill. Previous1.15/hour and99.97 readings retain their observation times. No
renewal, top-up, second paid account or additional spend was initiated. The
30-unit reserve remains intact. Both owned fit handles were terminal0 before
preserving the remaining operational-gate outputs and preparing GPU release.
The full E2E goal remains active; Final scope/independent lock are still unapproved.

A refreshed outcome-blind remaining-work ledger authenticates the two primary
reference matrices, five still-incomplete city target contexts and this new
whole-unit receipt. It preserves the already complete JHB27 units without rerunning
them. Across the selected Development scope there are231 comparison units:
84 complete and147 incomplete. Migrating all remaining whole units requires2,058
method replays, comprising1,913 new missing cells and145 explicitly repeated old
partial-method cells. These are operational counts, not an experiment completion
percentage or pooled metric. No outcome ranked the queue; the next identity is
UrbanEV1165/28d/seed43. The full local metadata ledger SHA is
`260d5740327b4c2bba4b9da79eda172a807938738bb99e7614f61cc8d74b6b17`.
It is an inventory, not an automatically activated multi-unit queue.

At the later resource check Colab showed99.12 units and one active session.
Both fit handles remained terminal. Every unique operational-gate output archive
was freshly downloaded from Drive and passed bytes/SHA/CRC: synthetic full attempt
25,552,254 bytes/SHA
`e6eca59d0b9d69163192fce5e8c2c0c2d200934e6dca9016a4a06081a77079a4`,
real-data whole/partial/resumed outputs4,881,662 bytes/SHA
`dbdfe2d88c8a7e973bd16205bab4c65236e6f227c09bc7098a0e6fb813317456`.
The Colab release action explicitly warns that VM files/variables are lost;
browser action-time confirmation for that deletion is pending. No Yes/reset
was clicked, no runtime release is yet claimed and no new GPU batch was opened
while that dialog is pending. Independent Final-scope selection is also pending
with the lead; elapsed time is not approval. Latest7254a62 CI passed Ubuntu and
Windows ([run40452459625](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/40452459625)).


### Next whole unit: UrbanEV1165 /28d /seed43

The existing Colab T4 session was retained by cancelling the deletion dialog;
no destructive confirmation or new runtime was used. The provider showed98.94
units before dispatch and98.85 at the subsequent observation (approximately1.07/hour).
No cost-per-experiment inference is made from these allocation readings.

The next outcome-blind ledger identity was1165/28d/seed43. Its first12 methods
completed at PID18527, exit0, in96.198s with unchanged core/config/input/Source
identities. Plan SHA
`1f27f8f1a26f11feb8ede8a963c323df1cc33300490ca62a0f26d588fc8e2d39`;
operator ZIP SHA
`7c5fb66a9ce5f4d127a057999341554087d881470146f7c745ee82b57433faf4`.
All5 exported parts (26,107,308 bytes) were freshly downloaded from shared
[Drive](https://drive.google.com/drive/folders/1HrBAh0rddlkNlTBOzRScR0gKNCXjCHXT),
authenticated against catalog SHA
`a2a75c59968c2b25f8d371cd8315f4e22856b64d9c2bf96703d4ea65221a901e`,
ZIP-CRC checked and restored (3,373 files). Independent daily/input verification
checked12 runs/2,220 hashes; latest-state verification checked12 states. All3
original Source checkpoints were separately CPU-loaded against their fixed
hashes, seed and epoch identities; no Source was refitted.

The resulting external partition receipt SHA is
`1fe8ebd1b48c685092e993fd972d06b3cba6ad498484d63b8837fd6ddf98d814`.
Only after those checks were its proof and receipt copied back to Drive and
the last2-method partition dispatched. Those2 are not yet accepted merely
because dispatch was requested. The prior84/231 complete-unit count is retained
until all14 methods pass joint external acceptance. Four old partial cells
must be replaced as a whole unit rather than counted as extra observations.

`python -m tools.prepare_primary_unit` now prepares first12/last2 metadata
partitions from an exact externally pinned remaining ledger and runtime reference
(`--ledger`, `--ledger-sha256`, `--template`, `--template-sha256`, `--output`).
It never trains or dispatches. It selects only the first pending primary identity,
requires all14 unique methods, original config/input/core hashes and all3 original
Source identities, rejects already-complete units and preserves historical rows
as references. A CHARGED context is explicitly rejected by this primary helper;
city migration must retain separate provenance. The execution-time role checks,
profile validation, mounted backup, time limits and external publication gate
remain necessary. Preparing both partitions does not authorize last2 dispatch.
This replaces repeated manual metadata selection without changing algorithms.

The last2 then completed at PID19991, exit0, in32.019s. Its3 canonical parts
(13,937,128 bytes) were freshly downloaded from
[Drive](https://drive.google.com/drive/folders/1IWibxu335sJiTnjyKYGVr2SzRf2UhWw_),
checked against catalog SHA
`9d26ba62c5c24a259562aa0e717926dec73355190b21ba4e8cb6f6f938506c7c`,
and safely restored (571 files). Independent daily/input verification checked2
runs/370 hashes and latest-state verification checked both states.
[Joint acceptance](issue23-colab-unit1165-seed43-acceptance.json) verifies all14
methods, identical52 scored origins,90 scheduled/59 issued days, exact frozen
configs/input bindings and the same actual Colab code/environment. Its SHA is
`ce446202be583011afcc672c398b82eab4f1b290d01dae670e62507805b1f0c0`;
the [shared receipt](https://drive.google.com/file/d/1KwYhzYWp8-UhaQzvdmXSyP1SxzGj5Ehl/view)
was saved and freshly downloaded with that exact hash. The two partitions total
128.218s child wall, excluding setup/export/readback/idle. Both handles are
terminal0. No new GPU batch was automatically launched.

The refreshed immutable local ledger (`remaining-whole-unit-ledger-v2.json`, SHA
`e34a138fc7ed14b3e1142b22d3209363e57e19c4aac613e0c65fdd24c6685ce0`)
now has85/231 complete units,146 incomplete. Whole-unit migration would require
2,044 cells:1,903 missing and141 declared repeats. Primary is46/69 complete;
the next identity is1165/28d/seed44. Existing JHB and completed city units remain
unchanged. Counts are not thesis completion or method-effectiveness estimates.
For this seed43 unit alone Adaptive MAE10.078115kWh exceeds Fixed9.981572;
no favourable seed/config selection or superiority claim is made.

Verification for the metadata preparation helper:376 offline tests PASS
(including3 new independent preparation tests), Ruff lint PASS, Ruff format
PASS (196 Python files), sources catalog listing PASS and git diff --check PASS.
A real-metadata dry preparation reproduced the frozen1165/28d/seed43 configs
without reading labels or fitting. The first mutation-test attempt failed because
the fixture used the production create-only writer to overwrite itself; the test
now explicitly mutates only its temporary fixture, preserving production guards.
The latest prior045f78d CI passed Ubuntu/Windows
([run40452998747](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/40452998747));
new helper commit CI is not inferred from that prior result. Final scope and
independent lock approval remain pending; no merge/main promotion occurred.

### Complete1165 /28d /seed44 and three-seed case study

The next metadata-only preparation authenticated the immutable remaining ledger
SHA `e34a138fc7ed14b3e1142b22d3209363e57e19c4aac613e0c65fdd24c6685ce0`
and the accepted runtime reference. It selected1165/28d/seed44 without inspecting
new outcomes. First12 plan SHA
`8d70581eeae30103252a6d597e9f6d944b4502f791cf4f76a613de0649f394d8`,
kit SHA `842c84fa253afd6ecde319011297e1b4b2bd987039e071f71bd55478fba0b188`.
The existing mounted T4 session showed98.67 units before dispatch; no new runtime,
paid top-up, account rotation, keep-alive activity or Source fitting was used.

First12 PID21555 exited0 in100.223s. Cloud daily/state/export passed. All5
canonical parts (26,009,753 bytes), catalog SHA
`257e125ade3e5b5b7cb25fee3511deb9b026707b1e2345c76045d6fa6d75d329`,
were freshly downloaded and independently restored/daily/input/state checked,
including all3 original Source checkpoints. External receipt SHA
`060e040efec68b77389b322b49e9d2bc73b0d60c7cd40cbc0e643dd009ee77d0`
was copied back with its proof before last2 dispatch. The new read-only local
`verify_colab_partition.py` script reuses the existing canonical restore/daily/
latest-state verifiers and automates bytes/SHA/CRC, exact reference bindings,
Source reload and proof packaging. It does not run models or dispatch jobs.
The script and its environment/proofs are retained with the analysis bundle.

Last2 PID22553 exited0 in31.023s. Its3 parts (13,915,157 bytes), catalog SHA
`0c76e7f6a95ec8015ac38afb7deb1ea4b4f6d2a523b11c4bb278ba4f5a62f204`,
also passed actual fresh external transport/CRC, safe restore and independent
daily/input/latest-state checks. Together the14 runs authenticate2,590 daily
file hashes and14 latest states. All14 preserve90 scheduled days,59 issued
forecasts and identical52 scored origins. Exact configs/input bindings and the
actual Colab code/environment match across methods. Sum child wall is131.246s,
excluding setup/transfer/verification/idle and therefore not a billing estimate.
[Joint acceptance](issue23-colab-unit1165-seed44-acceptance.json) SHA
`bb6cd79b14b6e7a8db1c725bacc24ada2c13135346e17a5334e6fb7d5f6fdc4d`
was saved to [Drive](https://drive.google.com/file/d/1Oz3jlBagvUVWFjZAL2O9bTZVX2tiOpEK/view)
and freshly downloaded with that hash. Both handles are terminal0; no next unit
was automatically launched.

[First12 raw artifacts](https://drive.google.com/drive/folders/1Z_tsIgLDSlaARS7cBynJT2sfQ0bpjl0V),
[last2 raw artifacts](https://drive.google.com/drive/folders/126MrFyu1Ro9bAvxDstg1g32W-Ru6T2AD).
The refreshed immutable ledger SHA
`9c9d74c84c7256d520034732680ab770017ef2cb42e3c1345f51f1951264c4dd`
now records86/231 complete whole Development units,145 incomplete; primary47/69.
Remaining migration is2,030 cells:1,893 new missing plus137 declared repeats.
The next outcome-blind identity isUrbanEV1188/28d/seed42. JHB and other already
complete units are preserved. No count is a thesis-completion percentage.

The [complete1165/28d three-seed case study](issue23-urbanev1165-28d.md) now contains
all42 method/seed replays, actual same52 scored origins, a14-method numeric table,
CSV/JSON, PNG/SVG, pinned sources/code/profile/partition proofs and reproducible
script/environment. Adaptive mean seed MAE10.265471kWh exceeds Fixed10.155355
by0.110116kWh on this one case. This is not a population/significance claim;
all fixed seeds and unfavourable/null findings are retained. Analysis does not
fit models or decode Final records. The small bundle is225,727 bytes, SHA
`e1723509d6ed4177280c1453384bbfad06f6107775cc7f0d522fa4d888197c43`;
[fresh Drive readback](https://drive.google.com/file/d/10sK5-zoe5gaAqicb7uWYZ3A_plUDsJDO/view)
passed bytes/hash/ZIP-CRC and every manifest member. The separate plotting
virtual environment leaves the research/training environments untouched.

Commit8b0bb61 CI passed Ubuntu/Windows
([run40454417284](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/40454417284)).
This evidence/figure addition changes no research code or protocol; no artificial
unit suite was rerun. The failed legacy-proxy analysis attempt, repaired script
and layout draft are preserved; final CSV bytes match the pre-layout version.
Full Development and independently approved Final remain incomplete. No merge,
main promotion, approval impersonation or issue closure occurred.

After the complete1165/28d three-seed artifact was externally read back, the
provider showed98.49 available units at approximately1.07/hour. The next
outcome-blind unit1188/28d/seed42 was prepared from ledger-v3, with first12 plan
SHA `dd996e3201d7f611504ad1e8cc461206351bce1699678a2bfbb600f7c69b55d5`
and27,670-byte kit SHA
`2d97af7da51158d43cd6354b169c091e19272e1ae37cb02b7daea101c7497d3d`.
PID24550 was dispatched on the same T4 session with20-minute/1-unit allowance,
120-second no-completed-run deadman and30-unit reserve. This is dispatch evidence
only; it does not increase the86 complete-unit count. Completed per-run payloads
are backed up to mounted Drive; first12 external readback must pass before last2.
No Final or further automatic GPU queue was activated.

### 1188 /28d /seed42 complete; full Final scope metadata prepared

After re-opening the saved notebook, Colab reconnected to the same existing VM;
no Run All, restart or duplicate Source/target launch was used. The first12
PID24550 was already terminal0 with mounted per-run backups. All5 canonical
parts (17,572,156 bytes), catalog SHA
`38a79fb8ce1851bde6900682c97e459fa9b7381600b6a08250478a07235a4fba`,
were freshly downloaded, SHA/CRC checked, safely restored and independently
verified for daily/input/latest states and all3 original Source checkpoints.
External receipt SHA
`7503e6beee0da2e991936398885205affc802b372467d087ac66a8522b4336dc`
was copied back before last2 dispatch.

Last2 plan SHA `ca42c2cfae2b30255e546b347e2a6ebdad193cb4d5f2e4a1e960fdb63dd63c73`,
22,407-byte kit SHA
`271ed1b50e8255baea8be5b78020d925dd67974b250b830458a580ca54fab9ab`.
PID26998 exited0 in21.011s. Its3 parts (11,749,961 bytes), catalog SHA
`6c2480e591560efce33c637dbf033b812f80a1b39d8560150d2c8a9b17b6f3ef`,
passed fresh external transport/restore/daily/input/latest-state and Source checks.
[Joint acceptance](issue23-colab-unit1188-seed42-acceptance.json) verifies all14
frozen methods on the same actual code/environment and exact original bindings.
It records90 scheduled days,59 issued forecasts,0 scored days and0 initial
examples for every method. MAE/RMSE remain null, not zero. Source-checkpoint-only,
frozen, random-target and seasonal-history initialization policies are explicit.
This unit is complete execution/coverage evidence, **not a scorable effectiveness
result**. Its81.116s combined child wall excludes setup, verification and idle.

The [shared acceptance](https://drive.google.com/file/d/1pjBG3TwNsvn_nYIk4C2afdvTxzO9naSd/view),
SHA `98223f56dc13f3dcfc7b8b247bab95c19850c31b60e030cf3e2b644e35ec7a9a`,
was freshly downloaded with the exact hash. [First12 parts](https://drive.google.com/drive/folders/1-MkUBfrvPY0WFtHAlLRe4lAp5FbFu-uO)
and [last2 parts](https://drive.google.com/drive/folders/1HC2Quhh43b8O5y7CgZBw6RltBQSqhPbc)
retain every forecast/event chain and latest state. Both process handles are
terminal0. The immutable ledger-v4 SHA
`ea4c17c362a440a5a0dfdfd9faddd018a7e6e1a2ed00df1e7c36ff1b36a70f5a`
now counts87/231 complete units,144 incomplete (primary48/69). Remaining migration
is2,016 cells:1,883 new missing and133 declared repeats. The next identity is
1188/28d/seed43. Null-score units remain explicit in all scientific denominators.

The lead's subsequent direct reply selected **all3,510 ready Final entity-budget
pairs =147,420 target cells**, accepting additional compute/time. It supersedes
the earlier pending-scope/66-pair proposal; independent immutable execution lock
approval is still absent. No new date or paid top-up is implied. The actual
[all-ready cohort](../../configs/issue23/final-all-ready-cohort.json), SHA
`88e9203c552cc4b4404f54c4be08e4fd5ab8a845cae8b0bc62805e18f6586734`,
revalidated all21 current accepted manifests/entity files and exact IDs against
the pinned prior inventory, while hashing training records only as opaque bytes.
It preserves35 no-initial-trainable pairs. No Final value records were decoded.
Independent structural checks passed group uniqueness, all seven namespaces,
three budgets/seeds,14 methods, all counts and same-city Source population across
budgets. This prepares membership; it does not supply a Final-capable reader.

The full static-coordinate audit flags7 pairs /4 distinct Final IDs with exact
coordinates shared with prefix-trainable Source IDs. All3,510 pairs remain kept;
coordinate equality is a physical-independence risk rather than proof of shared
traces/leakage. Exact IDs, metadata fingerprints, scripts/logs and limitations
are in the [scope evidence](issue23-final-scope-evidence.json) and
[metadata-only bundle](https://drive.google.com/file/d/1pNc_J41uKVFoSxBeWWWr1Am-i1IBQHSK/view)
(35,734 bytes, SHA
`783bcf8aec0845297aef868f0701aa1116bdd01d17b4cca7bacf857250da34e2`).
Fresh external Drive readback passed bytes/hash/ZIP-CRC/all9 manifest members.
Issue23 now leads with this updated scope decision, preserving its history.
No research code/protocol was changed; no artificial unit suite rerun was needed.
No Final execution, merge, main promotion, runtime deletion or issue closure.

### 1188 /28d /seed43 and complete-unit publication preparation

Seed43 first12 PID30383 exited0 in57.096s. Five parts total17,577,021 bytes,
catalog SHA `e125c5676b41a79cd84ab57af1c44a1680f628f54d0d6fb6f0fc4167e77df19f`.
Fresh external download/SHA/CRC, safe restore, daily/input/latest-state and all3
original Source CPU checks passed before last2 dispatch. Last2 plan SHA
`b86873297e4c197cc7a9d696587b81375021eaf5a95ffe99a85e8d71448d9725`,
22,434-byte kit SHA
`2fd6b27d4e22c969dc420a2de77dbae581dc618d063318015ab19811fbff3a99`;
PID36210 exited0 in22.013s. Its3 parts total11,755,056 bytes, catalog SHA
`a2138dddecf894e92a5ec8d3dda886deb8cbdf7adc92bf7dfe03eed33df59ab5`,
also passed full external transport and independent daily/input/state/Source
verification. [Complete unit](issue23-colab-unit1188-seed43-acceptance.json) retains
all14 variants,90 scheduled /59 issued /0 scored days and0 initial examples;
all metrics stay null. Source-checkpoint-only/random/seasonal/frozen policies are
recorded, not presented as successful supervised adaptation or zero forecast error.

The [native-connector uploaded receipt](https://drive.google.com/file/d/1fiHAGiZaqcS62HgaQC_XHxj9t1A7dsgI/view)
was freshly downloaded with SHA
`ad80693dc93117da374f17a98b633631bc47c1cef530b4a3228b266fe8c79d6a`.
[First12 artifacts](https://drive.google.com/drive/folders/1y3R9Yuz68ybnxk8SbgtkpnN6tajqQ8Pr)
and [last2 artifacts](https://drive.google.com/drive/folders/1BTjL2hKWrQyH-qDZof3uSI9VPzkwd2jY)
remain preserved. Combined child wall79.109s excludes setup/export/readback/idle.
Both handles are terminal0. Ledger-v5 SHA
`cfca85897353b1fc5b415617636a1b84ef5c5a3ef572f9d6a1bb80fce08af1f5`
now records88/231 complete execution units,143 incomplete; primary49/69.
Remaining migration2,002 cells comprises1,873 new missing plus129 declared repeats.
Unscorable units do not become scored station observations.

A native Drive upload path was tested with an actual pending independent proof
ZIP, rather than dummy data: [file](https://drive.google.com/file/d/197WRIzFn2Bsw_8BQ3H-_H8dnAhzem4UP/view),
3,226 bytes/SHA
`a91bb55d1088d551c79b872ea83d7ea611f5089baa18f6b4b2b6cc7be93acc17`.
Fresh external bytes/hash/CRC passed; the same mounted Colab directory observed
the uploaded file and its expected SHA. No credential transfer, new account,
permission expansion, fake activity or raw-data changes were required.

To reduce repeated Source staging/export/idle overhead, the preparation helper
now optionally emits one publication of the first1..4 **complete** pending units
(`--whole-unit-count 1..4`,14..56 cells). Default12/2 output and its CLI key remain
compatible. Every unit must contain all14 exact original configurations; prefixes
cannot skip a missing/changed/complete unit, duplicate identity or cross into
CHARGED/Final. All3 original Source hashes and clean byte-identical core identities
remain mandatory. The original reference template binds historical Source/core
identities; actual runtime is separately probed and recorded by the executor.

This explicitly updates the earlier operational<=12 convention for declared
complete-unit publications, not the scientific protocol. Daily transactions,
per-completed-run mounted backups, no-future-label/target-isolation gates and
external verification before the next batch remain. First56-cell dispatch is
bounded by20min/1unit,120s without a completed run and30-unit reserve, with no
automatic retry/next batch. Canonical export remains4 runs/part with an8MB size
check. The prior81.116–131.246s14-method child timings are sizing observations,
not guarantees or experiment-only bills.

379 offline tests PASS; Ruff lint/format PASS (197 Python files). New tests cover
mixed-seed complete prefix/config preservation,14/56 counts, invalid bounds,
changed later units and legacy behaviour. A real56-reference dry plan passed the
unchanged replay validator, all original Source hashes and56 actual Development
role/scaler bindings without decoding windows/labels or fitting. No new scientific
unit is credited merely from those fixtures/dry checks. The first prepared batch
is1188/28d/seed44 and1251/28d/seeds42/43/44, following ledger order. Plan SHA
`f622e4fa18a75d3358fbaf956db0d865350a7cd350039377d453ba30ec91b30f`;
100,657-byte kit SHA
`f16fa4681e9b5168108ea558f866c608cbd183b4d1fd81db6127e012ff48e3d5`.
The kit was [uploaded natively](https://drive.google.com/file/d/1RNS5gU990WY1gDqSxaD4Cxcdm_dT2G6L/view)
and freshly downloaded/hash/CRC checked. These are preparation facts, not56-run
completion. Final membership remains the lead-selected full3,510 pairs, with
independent immutable execution approval still pending.

### First complete four-unit publication independently accepted

The predeclared56-cell job PID43036 exited0 in242.863 seconds, including19.593s
of mounted completed-run backup time. All56 runs retain exact original configs,
input/scaler/Source bindings and the unchanged18 core file fingerprints under
actual clean cloud1ac2ae0, Python3.13/Torch2.11.0+cu130/NumPy2.3.3/T4. This is
new cross-environment execution, not recovery of original missing bytes.

CPU daily/input and latest-state checks passed before canonical export. All16
parts (47,520,786 bytes, each below8MB) were freshly downloaded from
[Drive](https://drive.google.com/drive/folders/1tSOZ9M7rcgFXIQSA4v5khJ4px12a6qs_).
Catalog SHA `3f3425c81ab87029e4007367b3eb31e71761ae3ed0aa2f551c2b869404614ef4`;
external bytes/SHA/ZIP-CRC, safe restore, independent daily/input/state verification
and CPU integrity loads of all3 original epoch10 Sources passed. The per-unit
check additionally enforces all14 variants, unique run IDs, exact reference
configs, same environment and identical scored origins **within each unit**.
It does not incorrectly require different stations to share scoring coverage.

[Acceptance](issue23-colab-whole01-acceptance.json), SHA
`2c2ee464657f2c0d462d25115fc473d76d336bce5e49299a0d437df9d53e24ba`,
covers1188/28d/seed44 and1251/28d/seeds42/43/44. Each has90 scheduled,59 issued
and0 scored days. Their MAE/RMSE stay null; completion is operational, not
supervised-adaptation or scientific-effectiveness evidence. Null units stay in
coverage denominators, with original initialization statuses preserved.

[Receipt](https://drive.google.com/file/d/12So0yupwET0XILWM66cwARhm1kwcNqVN/view)
and [independent proofs](https://drive.google.com/file/d/1JrbP861DtawPvDYZW4b9vbMxd-exLvwk/view)
were uploaded natively and freshly downloaded again with matching hashes/CRC.
The proof ZIP SHA is
`38e7b1715277f9133b09d64fdf9e0ef5f2635522017b94dadd5d484d4d11d2a9`.
Ledger-v6 SHA `36f984d1643e0017273b12616a412a1747848146a4879a4f51d83d943b7a1b74`
now credits92/231 whole Development units,139 incomplete; primary53/69 complete.
Historical partial cells are replaced canonically, never double counted.

The next strict prefix is1408/28d/seeds42/43/44 and2005/28d/seed42, with the
same56-cell/20min/1unit allowance,120s no-completed-run deadman and30-unit reserve.
Plan SHA `d3fb1e2ae16c3eee1c539143e0fd986807ac4ce9b8f5fc7265c00d02cc150198`;
158,073-byte kit SHA
`362f16e01a8ed35ff8aedc7b6a19658c18c0d7963dbe2bf779fc50422615dcb5`.
Dispatch requires the prior externally verified acceptance on mounted Drive and
probes the actual environment again. A dispatched batch is not accepted evidence.

All379 previously recorded tests are unchanged; head364b2d3 additionally passed
[Ubuntu/Windows CI40462236054](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/40462236054).
This handoff adds actual evidence, not a new method. No Final execution, self merge,
main promotion, runtime deletion or issue closure. Latest observed provider UI:
97.07 units at approximately1.07/hour with one active T4 session; this is not a
promise that the full147,420-cell Final scope fits available compute.

### Second complete four-unit publication accepted; third dispatched

PID46115 exited0 after56 cells in316.205s. The next16-part canonical publication,
60,315,398bytes, catalog SHA
`eff5b13b26a1a8951626566c8196f4314b47d89fe8b95214d1655b94eedc579d`,
passed fresh external Drive bytes/SHA/ZIP-CRC, safe restore, independent daily/input,
latest-state and all3 original Source CPU integrity checks. The56 rows match exact
reference configs/input bindings, and all14 methods share the scored origins within
each of the four declared units. No new research code, Source refit or seed choice.

[Acceptance](issue23-colab-whole02-acceptance.json) covers1408/28d/seeds42/43/44
(90 scheduled/59 issued/0 scored each, null metrics retained) and2005/28d/seed42
(90 scheduled/90 issued/90 scored). The latter has18 available trainable prefix
windows; this does not imply that Frozen Source or Seasonal Naive fits them.
For that **single station/budget/seed**, Adaptive MAE4.883356kWh, Fixed4.778724,
Full Fine-tuning4.840771, Target-only7.653882, Seasonal Naive8.843982. Adaptive
is worse than Fixed here. This is not a three-seed aggregate or population result.
The two remaining fixed seeds are next in unchanged ledger order.

[Canonical parts](https://drive.google.com/drive/folders/1zOEpKf52eQF0r-sG7v-Hgg52Ok5j8Js2),
[corrected acceptance receipt](https://drive.google.com/file/d/1yGdLfVMfP2Ncfej6xTYQYbs6gysPWktP/view),
[independent proofs](https://drive.google.com/file/d/1hr0C8uBBjH0Z2-FmRfAW0odZ21wkNJu4/view).
The corrected receipt SHA is
`51ea318e6b6ba0152e9369ae56f424cd32639f0877a861e20d939f2f6f5502cd`;
proof ZIP SHA `1a7d89deb8528d67b235a9c7413d91e1135d3436e4996727d2ebfddf314cc1ec`.
The first receipt copied the preceding publication's folder hyperlink; this metadata
error was corrected in a new version retaining the old receipt/hash and unchanged
catalog, exact bindings, verification proofs and metrics. No rerun or expected-hash
change was used. Current ledger-v8 preserves the correction and credits96/231 whole
Development units (primary57/69),135 incomplete. Its predecessor-v7 has identical
counts and selected prefix; the difference is only the added correction receipt pin.

The third56-cell strict prefix2005/28d/seeds43/44 and2152/28d/seeds42/43 was
prepared against ledger-v7 and dispatched as unique PID70969 after prior external
acceptance. Same-handle inspection confirmed it live with7 completed rows at the
observation, not complete/accepted. Plan SHA
`38293c8f3d528adbb4e72f4b12a04163ea277255421c100efb86239d087f8c30`;
262,006-byte kit SHA
`9b8dd0a02aae5fbc3d2ada78f0dbe6bdeae1c9c01795b8c6512b3baa71643d33`.
The same20min/1unit/120s deadman/30-unit-reserve limits apply, no automatic next
batch/retry, no Final. Latest provider observation95.37units at approximately1.07/hour
with one active T4 session. Provider balance includes allocated idle time; target
child elapsed times are not a complete experiment bill. Evidence-only380f4c6 passed
[Ubuntu/Windows CI40463594179](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/40463594179).

### Third complete four-unit publication accepted after bounded packaging repair

The new chat reattached to the surviving Colab VM and inspected the exact
`COLAB_WHOLE03_PROCESS` handle: PID70969, terminal returncode0,484.262362172s.
No training was relaunched. CPU daily/input and latest-state verification passed.
The first four-runs-per-part export stopped at the8MB transport guard: two parts
were8,180,597 and8,226,592bytes. Those outputs remain preserved. One CPU-only
packaging repair produced a new `exports-v2` using two runs per part; no model,
configuration, Source, seed or forecast changed.

All30 parts,92,934,355bytes, each below8MB, were freshly downloaded from
[the actual batch03 export folder](https://drive.google.com/drive/folders/1_5NiZ-Ofc29DT7oMGpPdMmVP5eBV0Yv1).
Catalog SHA `ce892f8278d245f8004e2d4b9bf3146d722e0dada39b26b24f2789664ba15280`.
Bytes/SHA/ZIP-CRC, safe restore, independent daily/input/latest-state checks and
CPU integrity loads of all3 original epoch10 Sources passed. Exact original
configs/input/core bindings, actual common environment and identical scored
origins within each14-method unit also passed.

[Acceptance](issue23-colab-whole03-acceptance.json) covers2005/28d/seeds43/44
(90 issued/90 scored each) and2152/28d/seeds42/43 (59 issued/52 scored each),
all90 scheduled days. [Receipt](https://drive.google.com/file/d/1sumwuM3Uuv3KemDHps4feodWw914310x/view)
SHA `517e57a0511b5d40734512c3c0da99b6069a4d80f0c028ff636249ad109f2d31`
and [independent proofs](https://drive.google.com/file/d/1siS_bySa7qIVx0Gpo7M3wGxZEpHbf893/view)
SHA `aece76f44fe79a77a1f946828ceeac2d5d2054d91babd972016cc92a607ff166`
were uploaded natively and freshly read back byte-for-byte; proof ZIP CRC passed.
Ledger-v9 SHA `2f605dfe12d705289556c0d0d4b2b159a7326f85fbd60bcb0d2ea62cd4af8c0a`
credits100/231 whole Development units,131 incomplete, primary61/69 complete.
Overlapping historical partial cells are replaced canonically, never added twice.

The now complete2005/28d group has42 authenticated runs across all14 variants
and fixed seeds42/43/44, identical90 scored origins and one actual environment.
Mean seed MAE: Adaptive4.860253, Fixed4.811535, Full Fine-tuning4.788682,
Online Best4.816429, Target-only7.636828, Seasonal Naive8.843982kWh.
Adaptive is worse than Fixed/Full Fine-tuning/Online Best here. This is one
Development entity-budget, not a population estimate or significance test;
Source/model/controller RNG vary together. No favorable seed selection.

Correction to the preceding prose: batch02's1408 units each issued58 days,
not59, as the unchanged machine-readable acceptance correctly records. Their
zero scored days and null metrics are unchanged. The receipt metadata correction
and original bytes remain preserved.

Latest observed provider UI:95.02 compute units, approximately1.07/hour, one
active T4 session. This includes allocation idle time and is not a full Final
capacity guarantee. Head55c3047 passed Ubuntu/Windows
[CI40473675244](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/40473675244).
No new tests are claimed for this evidence-only update, no Final, self merge,
main promotion or issue closure. The selected Final scope remains all3,510 ready
entity-budget pairs/147,420cells, awaiting independent immutable lock approval.

The [2005 three-seed case](issue23-urbanev2005-28d.md) now links the complete
per-seed14-method CSV/JSON, inspected PNG/SVG, scripts and member manifest.
Fresh authenticated Drive readback passed bytes/hash/CRC/all6 members.
The next strict prefix2152/28d/seed44 and2472/28d/seeds42/43/44 was dispatched
as PID77006 after batch03 receipt/proof readback. Plan SHA
`61db35e20e8bd88c161f17fedab066ac15b47176569f694dce141ade569ff095`,
213,712-byte kit SHA
`0ca8a7451ef4e24786974eb20af1b3d7381b65a62b486c0b69a30d84629e437b`.
Authenticated native kit/script readback matched exact bytes/hash/CRC after a
direct anonymous response failed byte equality and was rejected. Same56-cell,
20min/1unit/120s deadman/30-unit reserve; no automatic next batch. Dispatch is
not accepted completion, and does not increase the100/231 accepted count.

### Namespace-aware Development migration preparation

The remaining CHARGED work needs original city Source reuse under the actual
Colab target environment. `tools.prepare_city_units` now prepares1..4 strict
pending ledger units in one city. It authenticates pinned original context/target
plan and the existing three-source publication kit without rebuilding or relabeling
its producer environment. All14 exact original configs, ready Development roles,
input/scaler/Source population and seed/checkpoint identities are required. It
copies only explicitly named original Source members; it performs no fitting and
records references as `predeclared_development_reference`, never as historical
successful outcomes.

The existing replay operator admits this separately named city-plan schema while
legacy primary plans remain UrbanEV-only. It validates the complete-unit
declaration, same-city namespace, every method, fixed seed/budget/protocol and
Source hashes, then uses unchanged execute/Replay/CachedInputs/RunBackup logic.
Actual target runtime goes into the new backup context; original Source report
metadata/environment stays unchanged and is checked by RunBackup. New city
execution is not described as recovering old outcome bytes. Final is still
rejected by the existing Development readers and role checks.

Verification:384 offline tests passed, including5 new city recipe/namespace/
Source/method/role/declaration cases; Ruff lint and format200 Python files passed,
source catalog listing and diff checks passed. No datasets were downloaded or
training performed by these tests. Raw archives were not freshly rechecked in
this turn; source-list output is a catalog read, not fresh archive verification.
The18 research-core file fingerprints are unchanged. Actual city Colab execution
and full-source/target external acceptance remain pending; fixtures do not supply
research effectiveness or the Final lock.

### Fourth publication externally accepted; final primary prefix dispatched

PID77006 completed56/56 cells, returncode0,470.500297536s. The two-runs-per-part
export produced30 parts/89,282,421bytes, all below8MB. Fresh external Drive
bytes/SHA/CRC, safe restore, independent daily/input/latest-state checks, three
original Source CPU loads, exact reference configs and per-unit14-method scored
origin equality passed. All four units have90 scheduled,59 issued and52 scored
days. [Acceptance](issue23-colab-whole04-acceptance.json) SHA
`88171762650ea5e53fc39a1e9ff406dd4aed8473f81200e6c027fcce184b7b83`.
[Canonical exports](https://drive.google.com/drive/folders/1pbqD9DOQHTMSFDF7OpMrjz3oW3nF6JVD),
[receipt](https://drive.google.com/file/d/1JG1GMTnPTmQP8itDvajUgcXr3ku73rJD/view),
[proof](https://drive.google.com/file/d/1HYqAbP4SRkZvrNDrw-Biv_Vl3qggL3di/view).
Catalog SHA `754d97074fcff0f5c9411c45ea8bbb2e5cf4e113b53c7073b8a2aafbf48051fb`;
proof SHA `46f3196b76aeff7255cc45ab7d0d73b44695dd4a83274d7275694589ae72610e`.
Native receipt/proof readbacks matched every byte, with proof ZIP CRC PASS.
Ledger-v10 SHA `88c372cc105c7b22f7bbaa9535382f35675d3c33d2baa42c9d6d384d835f77af`
now credits104/231 whole units,127 incomplete; primary65/69 complete.

The final four pending primary units2633/28d/seeds42/43/44 and1153/14d/seed43
were prepared in ledger order and dispatched as PID80699 after acceptance
readback. Plan SHA `58380e139f4dd4eee5c33f11c8f2e7896c37093bbe444c0132eae81e3c3d7f6c`;
224,858-byte kit SHA
`dabfd1c3435a5af614dd6258e58897397ba8839ed6d4f4cd9e578ec550ac1354`.
Native kit/script readback passed. Same56-cell/20min/1unit/120s deadman/30-unit
reserve, no automatic next batch. Latest provider observation94.75units at
approximately1.07/hour, one active T4 session. This dispatch is not yet accepted.

Read-only admission additionally passed for all123 pending CHARGED units:
AMS23, LOA24, SPO24, MEL25, SZH27, all14 original configs and own-city Sources.
This is metadata readiness, not their execution or scientific acceptance. An
unchanged accepted AMS input archive was copied into the mounted workspace;
Colab verified253,455,529bytes/SHA/CRC/safe extraction and all3 exact input
manifest hashes without training or decoding Final value records.

Self-review tightened replay admission to compare each target's declared Source
checkpoint with its planned seed before fitting; the existing backup/execute
checks remain.384 offline tests passed again, including the cross-city Source
mutation regression, and Ruff lint/format200 files/diff checks passed. No research
core changed. [CI40477006930](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/40477006930)
at4f6ecf8 passed Ubuntu/Windows; the subsequent Source admission guard's new CI
is not yet claimed. No Final, autonomous merge, main promotion or issue closure.

### UrbanEV whole Development coverage complete; AMS migration started

Batch05 PID80699 completed56/56 cells, returncode0,502.457423664s. All30
canonical parts/89,360,785bytes, catalog SHA
`5bd522c9c000e63def0dcaed2f19e668dd081dde8e525cd9e13a1695890b6d82`,
passed fresh external bytes/SHA/CRC, safe restore, independent daily/input/state,
all3 original Source CPU integrity loads and all14-method per-unit scored-origin
checks. The four units each have90 scheduled,59 issued and52 scored days.
[Acceptance](issue23-colab-whole05-acceptance.json), SHA
`acf03d5d6b443bd27c7ea9adc6f79372b559ce205758a93f3d380021885733ab`;
[canonical exports](https://drive.google.com/drive/folders/1nLNtjnmoM3Vx5m0kJ6cvD8aWgkhiJH7y),
[receipt](https://drive.google.com/file/d/1KeMOE6A2JDBGeD99kTbVDV6uB99XwDeC/view),
[proof](https://drive.google.com/file/d/12sk_p_S-0RZLH0TdNkBa6-RKTuiKP-zR/view).
Proof SHA `b8819e87b29c4f28d8a155014012f84e9dcbc65b1e97d2deda298689fc2dc776`.
Native receipt/proof readbacks matched all bytes/hash and proof ZIP CRC.
Ledger-v11 SHA `fe065cad6e6b2ca4295373a3c9f9462a80198ce220f127ae0b861237cd93bb96`
credits108/231 whole Development units,123 pending: UrbanEV69/69 complete,
JHB27/27 complete, other CHARGED cities12 complete/123 pending. This is complete
primary artifact coverage, not complete analysis or an effectiveness finding.

The continuation chat's Development-only goal was actually created and its
`active` state re-read. It stops at a complete Development handoff for human lead
acceptance. No Final execution belongs to this goal. Full Final membership remains
3,510 ready pairs/147,420cells under a separate later gate.

Cloud city code is cleanb85c151, with unchanged18 research-core fingerprints.
Its384 CPU fixture tests passed in26.143s. The preflight stopped because Ruff was
absent; the failed log was preserved. One dependency repair installed the exact
`ruff==0.17.0` pin, then lint/format200 files/source-list checks passed. An initial
attempt to load the repair script hit mounted-Drive visibility lag before any
repair code ran; the same small reviewed repair was then pasted directly. No
scientific model or Source was fit by these checks. Source producer environments
remain unchanged; the actual target profile is Python3.13.16/Torch2.11.0+cu130/
NumPy2.3.3/T4. [CI40478046900](https://github.com/HungLD9505/adaptive-retention-ev/actions/runs/40478046900)
atb85c151 also passed Ubuntu/Windows.

Batch06 is the strict first four pending AMS units:1359/7d/seed44 and1515/7d/
seeds42/43/44. The exact own-city Source kit and original producer context passed
metadata preparation and replay admission. Plan SHA
`114e95e5d49e0c1672af45836d057069fa1ea7d9ccd2859c2d6136993fd37f42`;
1,661,007-byte kit SHA
`dd63961810ff1b4bc9aafd7cb81fd0595cc5f60a844e58c0ca86b61d216c5892`.
Native kit/script readback passed. PID87008 was dispatched with56-cell/20min/
1unit/120s deadman/30-unit reserve; no automatic next batch. Dispatch start UTC
is recorded separately for compute+publication+external verification/analysis
elapsed accounting; earlier input/bootstrap setup remains separate. No completion
or representative-city E2E estimate is claimed before its external acceptance.
Latest observed provider UI94.39units, approximately1.07/hour, one active session.
No paid purchase, Final, self merge, main promotion or issue closure.

### AMS A06 accepted and disjoint multiworker dispatch

A06's four complete AMS7-day units (1359seed44 and1515seeds42/43/44) passed fresh external raw transport, CRC, independent daily/latest-state, all three original Source, exact configuration/input and within-unit coverage checks. Each method has90 identical scored origins per unit. Acceptance SHA `a0819acf3905f7363f203ae09277d38a80f67a2c9794aea8afed12036fde238f` is in [the acceptance record](issue23-colab-whole06-acceptance.json). Independent proof SHA `c41bf56bd29debf7df56f47334089770e53453c2a4d9d35fb4c72a0ed21c4258`; both uploaded artifacts passed fresh native exact-byte readback and ZIP CRC. [Published acceptance](https://drive.google.com/file/d/1CX3RvNfXLMQ-ZkbR9zu203-Tjha-nNAQ/view), [proof](https://drive.google.com/file/d/1wgB8ebBVou_I94IpOb4ooUkgqLqD2U4q/view), [canonical export](https://drive.google.com/drive/folders/1cCny1JDU8uHUD_WXTstiU7B9TXRgJi2N). Catalog SHA `1abc8f9640f9855473871196061b573ea17879b2ec60ac3e3f66c374493881e0`; child wall578.541seconds is not full end-to-end time.

The new ledger v12 SHA `8244646c4227417830ae5d7c9b9b3c3ea2d72c0288040fce882af900d4e1b3ef` has112/231 accepted and119pending. UrbanEV remains69/69 complete; CHARGED cities remain separate. [Multiworker controls](issue23-multiworker-controls.md) document actual guards, manual billing/release gaps, failed staging, publication repair and disjoint B07/C08/A09 reservations. No claim is made that a Goal alone prevents idle provider charges.

The [complete UrbanEV primary Development analysis](issue23-urbanev-development-primary.md) covers966cells. Observed Adaptive MAE exceeds Fixed retention by0.0339/0.0418/0.0246kWh at7/14/28days; corresponding exploratory paired intervals crosszero.462null cells remain explicit. This does not establish superiority or population effectiveness. Final values/execution remain untouched.

B07's single AMS14-day/entity110/seed42 unit also passed external raw verification and common90-origin coverage. Acceptance SHA `407f8df06befa093585f9275049f3a700c896333e5a77b5d5344cf100e400fe3` is in [the B07 acceptance record](issue23-colab-whole07-acceptance.json); proof SHA `86e338a863462e606617e902957a397ec4b9bc6f9d4fda24074fc366ce805c94`. [Published acceptance](https://drive.google.com/file/d/1eBK6AfOkvF6UoVd0oJLdFV_BsmpKyQjG/view) and [proof](https://drive.google.com/file/d/1it9SyYSMWesDGUZCSn785sEED9nNqq3N/view) passed fresh native exact-byte/CRC readback. Ledger13 SHA `76b87d5b24fb52c15db6dc5e9171945b46d5d511ec9c6953fbd611204838a21e` records113/231 accepted,118pending. This is a dated progress checkpoint; later ledgers supersede counts.

A defensible global remaining-time estimate is not yet available: the new scorable timing sample covers only five AMS units. AMS-rate arithmetic for118pending units gives3.91–4.74 single-worker fit-hours or2.14 ideal parallel fit-hours, excluding setup/publication/verification/analysis. Observed dispatch-through-local-acceptance spans imply substantially longer conditional scenarios (12.95–20.64 single-workflow hours or7.96 ideal parallel hours), plus untimed city analysis/review. These are scenarios rather than cross-city bounds. Local acceptance filesystem times are observations, not authoritative remote acceptance timestamps; workloads, null coverage, archive sizes and hardware/thread policies differ. New inline publication is being measured separately; no matched A100/T4 performance claim is supported. Scratch estimate v2 SHA `55a2cef0134a54397300623164c3558323cee89f5191909a2d9dda7a6118d133` preserves formulas and provenance.

### Inline publications and parallel external verification

A09 and B10 each completed four disjoint AMS units and passed fresh external transport, CRC, restore, daily, latest-state, original Source and common-origin coverage checks. Every method in each of the eight units has90 identical scored origins. A09 used the existing T4 runtime:540.427seconds fit and581.186seconds dispatch through mounted publication. B10 used the actual A100 runtime:424.247seconds fit and454.659seconds through publication. Different units and operational thread policies prevent a matched hardware-speed claim. Inline publication reduced the observed non-fit publication span; full external acceptance and analysis remain additional work.

[A09 acceptance](issue23-colab-whole09-acceptance.json), SHA `a326753e64c36eb71be46e4ef741136e90b7d98d42428c7923547cbad8396b22`, [published receipt](https://drive.google.com/file/d/147VdkoKQma0axRjF3cQR5yibT9QBhUxa/view) and [proof](https://drive.google.com/file/d/1gbSG8IUcVxWtWVI3NBWmNElX-FktXrNf/view), proof SHA `d3298f2fcf239fd72b2cf0b765c63f4648093de2ef227d213f2cb1c60074687c`.

[B10 acceptance](issue23-colab-whole10-acceptance.json), SHA `bb623f306c2baa2f6d7c2d50857dbd16d20e31c78eb129bfb82f8619e2693f85`, [published receipt](https://drive.google.com/file/d/1r8G5j9E20l5OGxxWeRNF2EQeXTQpAaSt/view) and [proof](https://drive.google.com/file/d/1MueQfaYtenBVSoTNUWZ4HhofjineSbVR/view), proof SHA `14bebcda956cc8c350f27fedf3308c3d5e314bcc9f01a15728316e6c7a844d6f`. Worker C performed the independent B10 raw verification on CPU; root separately checked coverage and alone advanced the ledger. All four uploaded artifacts passed fresh native exact-byte readback and ZIP CRC.

C08 never fitted on its failed-mount VM. Its exact original plan/declaration/reference were reassigned exclusively to healthy A as A08R, which completed14cells in142.468seconds fit and163.546seconds through publication. External verification and90-common-origin coverage passed. [A08R acceptance](issue23-colab-whole08R-acceptance.json), SHA `abcc55af01414e9289562d614e3410994bf791b4147b9f1f5fbeacf3b9596ca7`, records that one unit without duplicate credit. Ledger16 SHA `0804f02bfb0b8886263ee952845b98ea9f76cf71869c6bfdb66f705943d8ea7c` has122/231 accepted and109pending. Disjoint reservations can finish out of order; acceptance removes only the exact declared remaining identities and preserves every other pending unit, instead of discarding an uncompleted prefix.

At the10:24UTC provider observation,90.69compute units remained and the two allocated sessions consumed approximately6.37units/hour in aggregate. This is an observation, not a live billing guard. Original LOA processed inputs were copied into new staging and authenticated by exact archive/manifest/artifact hashes and CRC in4.130seconds on B's idle CPU; no Final values were decoded. Queued LOA batches use original LOA Sources and independent namespace checks. The later pending AMS unit remains in its original queue position; no city-completion assumption changes the frozen order.

A08R's [published acceptance](https://drive.google.com/file/d/16DqOjiyvYuhgoq_0zUIwor64qJKs_9j6/view) and [proof](https://drive.google.com/file/d/1DWGgiaQidsAHXfAXcsQzk6I_DPhnTz36/view) passed fresh native exact-byte readback and ZIP CRC; proof SHA `33eabff7d7b09b354066b26901a7a1be92dcb146f258aa3e1406026b2ea2faa9`. A11 and B12 were then dispatched independently on their healthy existing runtimes, with root acceptance gates and unique output/backup roots. No C GPU retry or duplicate C08 fit occurred.

### Development checkpoint: 142 accepted units

Ledger21 SHA `7a11198ba6970d2934ef2be3375e359fb3b09abd5e5737134df063dcf8457480` records142/231 accepted and89pending. A11/B12 complete eight more AMS units; B14/A15/B16 complete twelve LOA units. Every method in each unit has90 identical scored origins. Independent A and B verifiers used fresh raw bytes and checked transport/CRC, daily inputs, latest states, own-city original Sources, exact configs and within-unit coverage. Root alone recorded acceptance.

| Publication | Acceptance SHA | Evidence |
|---|---|---|
| 11 | `9b5c36517522497e981c1f71e6a005e978d8df6978788cb1ddf832d5b21c19c4` | [Receipt](https://drive.google.com/file/d/1Kb5qjAWcYunzeLjvM5lKnNFGAaLanxuu/view), [proof](https://drive.google.com/file/d/1TjyIoqYYP5xfJoJO_mK5Xg5axVBQxgue/view), proof SHA `0f45660c114325fac7b161a68c65fa98d025d3c5e78bdaeeab7087fba37362fc` |
| 12 | `67654168dedbb6e4eb69454baf1d7727675d73a0cf8b72d3ec20b91cb137971d` | [Receipt](https://drive.google.com/file/d/1TgHpH5HY_HIJrVkB4FCgW_nKVBMshnZa/view), [proof](https://drive.google.com/file/d/1KHq5t7-pgmX4CVgUjpHi8ExcCEDsn4ug/view), proof SHA `98b84e3930441fc855bbf0d0f4271a9f1b94c931dc4dca5a388727224cebb4af` |
| 14 | `13fea1476274efa643a91d159d283fb72c56aade7758e55d0d711d55df8a6265` | [Receipt](https://drive.google.com/file/d/1H5olUvPpRroyCNHyWLKuVo4rVpAk7x7B/view), [proof](https://drive.google.com/file/d/1_99igbWN-jA7LFD7-m-OuT6aW7zmyOXw/view), proof SHA `125001691b5f79e921d6449d29e4b243c44202ae1c841187f5742cfff6ff26b2` |
| 15 | `c29b02285c0f42af943c6e950b04dce0d7f4acd40aaaa5a2c915d8de3a994534` | [Receipt](https://drive.google.com/file/d/1vaoa5hPjqWZO5VhoSJ48my5s7epJBA3r/view), [proof](https://drive.google.com/file/d/1iGe2qbFwVIIZzhk1m38aWoPw0J7w6Kn5/view), proof SHA `a3b6ee3a03862be18d97a220c373dbab0f8ad7113f0daeb1e9df70ee1e2fcbbf` |
| 16 | `7a868bf9aab57247eb13a82177960a24da82f257fb1d2fc93e4f68e755b2959d` | [Receipt](https://drive.google.com/file/d/1ARwDO_JV8fLwo_KXcLXT7dhYEU_7hKhI/view), [proof](https://drive.google.com/file/d/14qZy4q_jnBjtzMpLYR1MnmIzq-JXGCEM/view), proof SHA `12bf8a2f2aa252a7775960515700fe3b5d0042946022e28999d99c0f4903d0ce` |

All uploaded receipts/proofs above passed fresh native exact-byte readback and ZIP CRC. A11/B12 fit/publication spans were540.422/580.444 and419.098/448.450seconds; B14/A15/B16 were400.893/429.761,522.108/561.316 and405.960/435.268seconds. These are operational observations across different units and runtime/thread policies, not isolated hardware comparisons.

A17 and B18 then received disjoint LOA work after predecessor external acceptance. The last observed provider balance was87.51units at10:55:21UTC, aggregate approximately6.37units/hour for two sessions, with30units reserved. All remaining finite queue assets are prepared and independently checked offline, including city boundaries and five late partial-unit replacements; runtime success is not inferred from those checks. Unit/reserve billing controls remain coordinator policy, and blocking dispatch staging precedes the isolated operator watchdog.

The [JHB Development report](issue23-jhb-development.md) independently reviews27complete units/378cells and all three original Source CPU loads, retaining adverse results and exploratory interval limits. The maintained UrbanEV and JHB reports do not establish effectiveness, novelty, peer approval or a Final lock. Final values/execution remain untouched.

### Development checkpoint: 150 accepted units

Ledger23 SHA `85f2187a1f8fde0d1c0de17b1b65e276aec5980ceaf5e42f7d76ea552c57784f` records150/231 accepted and81pending. A17 and B18 each added four complete LOA units; all14 methods per unit share90 scored origins. A17 fit/publication took522.058/561.499seconds; B18 took408.998/438.034seconds. Independent transport/input/daily/latest-state/originalSource/config/coverage proofs passed before root acceptance.

[A17 acceptance](issue23-colab-whole17-acceptance.json), SHA `55b51331c8684ea8180fc9741f7a23978897376f3f39a74dae9f65874096b4db`, [published receipt](https://drive.google.com/file/d/1t9XtE8jJAQdg6m-wk5gbA_8zTQ1WB-YH/view) and [proof](https://drive.google.com/file/d/1p1HE84ALMUWqazQO91IBHr8auWtN4qCw/view), proof SHA `208b98fe0877c2bf63d9e2dc6e44ddaa50166f96681bc2daea4052794f4c341f`.

[B18 acceptance](issue23-colab-whole18-acceptance.json), SHA `0dfac613424cbda803e4f019ac52e1adda33e96c040feedcd47c0c8208f2e849`, [published receipt](https://drive.google.com/file/d/14eVyMhpxep23TKBFTO-iHQra4wAjTnbk/view) and [proof](https://drive.google.com/file/d/1F91v1NwEaFOKlTO1IsSY8QF1-7zkRsiG/view), proof SHA `2a4b6cf840b541495170817df2e8a15812f0273b454ce0526a969ede03bf124c`. The native readback record pins the exact proof bytes; all four uploaded artifacts passed exact-byte/SHA/CRC verification. These are dated counts, not claims that the full matrix is complete. A19 retains its three-unit/42-cell boundary; B20 moves to MEL with original MEL Sources and separately authenticated inputs. No Final execution or method change.

### Development checkpoint: 157 accepted units

Ledger25 SHA `dc0172419598607570a001a16f86530f624acfd4dfd86e4845fde9016ed830f2` records157/231 accepted and74pending. A19 contains exactly three LOA units/42cells; B20 contains four MEL units/56cells with original MEL Sources. Every method per unit has90 common scored origins. Independent transport/CRC, inputs/daily, latest-state, original Source and coverage checks passed.

[19 acceptance](issue23-colab-whole19-acceptance.json), SHA `d8aab794d294752ee7b247acc60ccf29e4fa9e540b6fc740d47853bbf462bd44`, [published receipt](https://drive.google.com/file/d/1yewW0lGxQp90COB34aSMWrK7EzE2lCWk/view) and [proof](https://drive.google.com/file/d/1_4h7pWIIXyqjf2dM0IrPTzhgJhRkacSD/view), proof SHA `0e40d9342083fad740f2e5a00b96176d22e3b17dfb0efb3f9c80ed5d8a525f65`.

[20 acceptance](issue23-colab-whole20-acceptance.json), SHA `9ccfa99d3a6f511a9f39a0e90ad00f88fda3303e847359eb61746e60741c5697`, [published receipt](https://drive.google.com/file/d/1vae4npjLhKs0jBqhn9gGsa80741CaK3U/view) and [proof](https://drive.google.com/file/d/1DaZsSvwWyLd5FUZSiS3U9-aBKUfxHnwv/view), proof SHA `ac613454fd5a90ac0b0fecce0a16c4e6d68d95b66e2b039c6d622693741c26b8`.

All four uploaded artifacts passed fresh native exact-byte/SHA/CRC readback. A19 fit/publication took381.922/414.231seconds; B20 took405.887/434.456seconds. B20 external verification initially received an incorrectly shaped file-list argument; the CPU caller preserved the error and corrected metadata format before fresh verification. No fit was repeated. A21 and B22 then received disjoint MEL work after predecessor acceptance and separate A/B input staging. No Final execution or method change occurred.

### Development checkpoint: 169 accepted units

Ledger28 SHA `1ae3cebc51715f4134883cffa14fb06f0e94c4934f8341768aa60f9772a1f740` records169/231 accepted and62pending. Publications21,22 and24 each add four complete MEL units/56cells. All14 methods per unit share90 scored origins; fresh independent raw transport/CRC, input/daily, latest-state, own-city Source and coverage checks passed before root acceptance. A23 remains uncredited while running; no incomplete city analysis is presented as complete.

| Publication | Acceptance | Native publication |
|---|---|---|
| A21 | [Record](issue23-colab-whole21-acceptance.json), SHA `5eae011c6b5196909e582d309dcef18d44a09cfae5807f1e8e01fe529d84bc2d` | [Receipt](https://drive.google.com/file/d/1VEY5UuaJcfnJu9fLNJM1SpNJ6qm9aQhV/view), [proof](https://drive.google.com/file/d/13Iqq2OWXw-OXxPy_0dGvA-rv0dihPugu/view) |
| B22 corrected v2 | [Record](issue23-colab-whole22-acceptance-v2.json), SHA `ce5589fb8fd6ba84e5a76b0986371554d46164b04b04e34fb88badd652f2e426` | [Receipt](https://drive.google.com/file/d/1EMsXXiRKE9G4q0CfClt2GnJNJGa6m6nU/view), [proof](https://drive.google.com/file/d/1krLKm0fT9UqtsUUnTyKED5QwV5BjMT19/view) |
| B24 | [Record](issue23-colab-whole24-acceptance.json), SHA `0f2903b030f9440725f5e8a26c2e27ba25e829175b9850f1ae8206e11d3114a7` | [Receipt](https://drive.google.com/file/d/1DltX77P0ZizbL7C5f6CL-d7pKDtW3Ywq/view), [proof](https://drive.google.com/file/d/1nAo3ChpCsPXpKqGBR6r7hncqFoBT3uF1/view) |

All six uploaded artifacts passed fresh native exact-byte/SHA verification and proof ZIP CRC. A21 fit/publication took510.894/548.937seconds, B22 took409.142/437.969seconds, and B24 took400.001/428.706seconds. These are different workloads and runtime/thread policies, not matched hardware comparisons or provider billing measurements.

Root initially entered incorrect B22 fit time406.094595125seconds manually. The authenticated exit records409.1415830470005seconds. The [original v1](issue23-colab-whole22-acceptance.json) and original ledger26 are preserved as superseded metadata evidence; v2 corrects only timing and traces the original. Counts, metrics, proof identities and accepted units are unchanged. Ledger26-corrected, then27 and28, carry the correction lineage. Later acceptors read timing programmatically from the authenticated current-batch exit and check its catalog identity.

B26 proceeds to the frozen SPO reservation after CPU-only input authentication. The provider observation at11:38UTC showed82.72units, approximately6.37units/hour across two sessions, above the30unit reserve. This does not constitute a provider-enforced budget guard. Late partial-unit replacements remain required before city completion. Final remains unstarted and no method change was made.

### Development checkpoint: 177 accepted units

Ledger30 SHA `163545cb56b71ca0f182c6b8d6bff27cc5c46aab5739797a369efd0ff0abbd87` records177/231 accepted and54pending. A23 adds four MEL units and B26 adds four SPO units. All14 methods in each unit share90 scored origins. Independent fresh raw transport/CRC, input/daily, latest-state, original Source and coverage checks passed; root alone advanced the ledger.

[A23 acceptance](issue23-colab-whole23-acceptance.json), SHA `c0652c3f716ef467637fc0a0f76498996f3ae144191eebc1212b70d9675c09d3`, [published receipt](https://drive.google.com/file/d/1Qs_rERxM0zV6qFRTnv-GJqoD5KV5Jz-2/view) and [proof](https://drive.google.com/file/d/1yeBI3em44DftwL6WWBlOJMlkvYX5jf56/view), proof SHA `6138ccf216413fb5b7687c50da33f090029ef46d13a8218e7fdaed75561be325`.

[B26 acceptance](issue23-colab-whole26-acceptance.json), SHA `e10cffb00924e4a8b7a6e646b3323bd6bc0ef741e30ccd6dfed9c056a59014fb`, [published receipt](https://drive.google.com/file/d/1pgp0SJKo3VCclWFUF-3dI9Imbw579_rH/view) and [proof](https://drive.google.com/file/d/1ku948Wn0SmSyr8YTkxFs0W20l22Og7WS/view), proof SHA `392513b25929023e8d92729dd0d81d87d03b338e171a268848b97a4cd7a14905`.

All four uploads passed fresh native exact-byte/SHA/CRC readback. A23 fit/publication took515.715/554.723seconds, with58.528seconds external verification; B26 took409.148/437.910seconds, with97.449seconds external verification. These are operational observations across different units, hardware and thread policies.

Review found robustness gaps in the reusable root acceptance helper: fixed counts/ledger paths, output writes before ledger validation, and incomplete explicit proof-chain checks. Independent verifier evidence supplied additional checks for earlier batches; no invalid accepted unit was identified. A new232-line scratch helper hash `49722d75459ebd9de52474dd6fc46cee93e9670135a0d27554d433b3e314eaa0` now validates hash-pinned registry/plan/declaration, catalog and raw parts, mandatory proof status/ZIP membership, actual profile/code/environment/caps, all original Sources, unique common origins, metrics and exact current-ledger bindings before rendering outputs. Output creation is exclusive and unrelated Final metadata is preserved. Real B24 temporary-output reproduction and B26 dry validation passed; wrong proof, stale ledger, missing Source proof, changed input binding and existing-output cases were rejected without actual acceptance writes. Root then accepted B26 with the pinned helper. This is operational verification, not peer approval or research effectiveness evidence.

Timing scenario v3 uses five A and eight B authenticated four-unit AMS/LOA/MEL batches; the shorter three-unit A19 remains separate. At ledger29's58pending units/19reservations, a conditional warm parallel-cycle scenario is1.96/2.08/2.55hours using observed minimum/median/maximum spans, including observed acceptance/dispatch gaps. Active A25/B26 are counted in full. The earlier preliminary1.6hour minimum incorrectly pooled A19 and is superseded. These are sample-rate scenarios, not total-Development bounds: SPO/SZH behavior, staging, complete canonical city verification/analysis, reporting and review remained unmeasured in that snapshot. JSON SHA `8049e46a48171065321a17a37578f15f3076e979a699e1ead390e6b4c252477e` preserves exact inputs/formulas. B26 supplies the first later SPO sample; it does not retroactively change v3.

A25 and B28 continue disjoint frozen work. The11:50UTC provider observation showed81.68units at approximately6.37units/hour across two sessions, with30units reserved. CI at9e3516d passed Ubuntu and Windows. No fresh local raw-archive check, Final execution, method change, merge or issue closure is claimed.

The [operational review bundle](https://drive.google.com/file/d/1IhTHJ0R9HlXwqBtP0AB5WMWkbli1KDhN/view),72,862bytes, SHA `e7293e1284fcfb21f5d0af04d60f6a402eedad478ec311443b2349e06e1514c4`, preserves the acceptance helper, positive/negative test sources and report, registry-derived v2 dispatch snippets, root B26 review/arguments and timing-v3 formulas. Fresh native exact-byte/SHA/ZIP-CRC and all28 manifest-file checks passed. Reconstructed3/2/1-unit artifact fixtures and duplicate-origin rejection passed; those are helper tests, not real execution acceptance. V2 snippets correct monitor aliases and bound CPU staging at120seconds; older v1 is preserved locally. The receipt does not embed the verifier source hash, so the helper records the caller-pinned reviewed verifier identity without claiming cryptographic execution attestation.

### Development checkpoint: 185 accepted units

Ledger32 SHA `cd0603a79a67fa6149118c223382474b640d5f24b384c3b91c6810d05f4e21e3` records185/231 accepted and46pending. A25 adds four MEL units (ledger31 reached181accepted); B28 adds four SPO units. Every14-method unit has90 common scored origins and passed independent fresh raw/input/daily/latest-state/own-city Source/runtime/coverage verification plus root's pinned acceptance CLI checks.

[A25 acceptance](issue23-colab-whole25-acceptance.json), SHA `e4bc531730c9b5535f8a97cbc0400ebd14bce0bb2d14192c07fb6c34c91819b2`, [published receipt](https://drive.google.com/file/d/1j1JXyMAO9wEHZ2TsTCSRCXzo86nlU-D1/view) and [proof](https://drive.google.com/file/d/1a5OXZGREHGld4AgNrSsw7p4YtHDE8Wcu/view), proof SHA `8c75fd799317d2819409b846c8fdf72eb5674b924217c3f22ac72109f3e53f3d`.

[B28 acceptance](issue23-colab-whole28-acceptance.json), SHA `00571e3576a166709f2350b2caef531990ee91e8212f3a2f476ef3c13b56be8a`, [published receipt](https://drive.google.com/file/d/14CeG6bIx_schfVnorbsk7G1ek5F_i-kb/view) and [proof](https://drive.google.com/file/d/1a9_sex-LfNLipR8LL1h5NCHR2GTbuTzP/view), proof SHA `12bd9142ea0bd1feafefa2391eb42979a4552dc7dddef2c1f9184cefaad97941`.

All four uploads passed fresh native exact-byte/SHA/ZIP-CRC readback. Root performed A25 publication/readback; a separate publication-only agent performed B28 after explicit root acceptance, without raw re-verification or ledger/Git/fitting writes. Its readback receipt SHA is `879a293442d2dbef02905a890767f3ee3c51fc9b0f86f7087e24b2e541141f65`. A25 fit/publication/verification took529.160/568.436/60.470seconds; B28 took405.018/434.129/76.520seconds. These are operational observations, not isolated billing or hardware-speed comparisons.

Actual accepted counts are UrbanEV69/69, JHB27/27, AMS26/27, LOA26/27, MEL26/27, SPO11/27 and SZH0/27. Five late partial-unit replacements remain in the frozen queue. A27 and B30 continue SPO; no running work is credited. At11:59UTC,80.61compute units remained, approximately6.37units/hour across two sessions; reserve30 remains coordinator policy. CI at3aae42f passed Ubuntu and Windows. Whole-city analysis remains gated on27/27 accepted units; no Final, method change, merge or issue closure occurred.

### Development checkpoint: 193 accepted units

Ledger34 SHA `7168cfccee4f168ef7aab2a24373b9107d634c0474ec0ed578635ff5d1a1761f` records193/231 accepted and38pending. A27 and B30 each add four SPO units/56cells. All14 methods in every unit share90 observed scored origins. Fresh independent raw transport/CRC, daily/input, latest-state, all three own-SPO Source CPU, profile/binding and coverage checks passed before root's pinned CLI acceptance.

[A27 acceptance](issue23-colab-whole27-acceptance.json), SHA `a3d8565543ae5059766b02e1d3ed20c17751009d970ec5b070cfc3336c4ce696`, [native receipt](https://drive.google.com/file/d/1Y53SGwD889Cj8fWCNgIhDyeM2oFWLXvt/view) and [proof](https://drive.google.com/file/d/1iwAiyzJf1rbpJydRvymtR2pFMeiy-zwK/view), proof SHA `e6ef6078bc34e652c8f279f7bb8f082935d9a7ee1b1cde6b5c97872c4a1a1fb3`.

[B30 acceptance](issue23-colab-whole30-acceptance.json), SHA `dd954e4bb514270df31b5513709db4835a2982195a68d02608dc8b48b2d736b2`, [native receipt](https://drive.google.com/file/d/10s27xh498IWtVZp3cRTiwwbggViQc4rX/view) and [proof](https://drive.google.com/file/d/16aGUcmrwI_mKPwD3BVGD9CD71UrvIijj/view), proof SHA `22e054be3ac28361704eea73f376e5484a4387075fa17523dc441f5bd2a6cefa`.

The publication-only agent uploaded the four exact root-accepted artifacts and passed fresh native exact-byte/SHA/ZIP-CRC readback. Readback receipt SHAs are `6a9457db37277bd06d8e10e1fad4fca657afcd23b379fe43f3a9fba3a64bf6c4` and `45051ccfbffbff9bd5d3775155daf564c8fae26ead34bd6701e8223b1a6bc891`. No duplicated publication, fitting, raw re-verification or agent ledger/Git write occurred. A27 fit/publication/verification took526.286/564.908/54.375seconds; B30 took399.917/428.286/72.993seconds. These are workload observations, not controlled speed or billing comparisons.

SPO now has19/27 accepted units. A29 continues SPO on the existing T4; B32 starts the frozen SZH reservation on the existing A100 after a separate hash-pinned CPU-only SZH input stage. Its actual process is36622. SZH has no accepted unit at this checkpoint and remains a separate temporal/possible-UrbanEV-overlap supplement, not independent geographical validation. At12:06UTC,79.55compute units were observed at approximately6.37units/hour/two sessions; reserve30 remains coordinator policy. CI at16d8f4d passed Ubuntu and Windows. Final remains unstarted; no method change, merge or issue closure occurred.
