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

## Latest execution checkpoint — 2026-10-27, primary prefix195 and LOA1

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
