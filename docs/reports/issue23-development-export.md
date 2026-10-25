# Verified Development export without Kaggle output snapshots

Issue #23 / PR #52. The live Kaggle GPU batch is preserved. Output-bearing Quick
Versions have not been verified complete; a code-only version does not preserve
model artifacts. `tools.export_development` provides a separate post-completion
path to download the actual files through Kaggle's Output-file Download action.
That action has already retrieved the 149-record running progress snapshot; the
new complete-matrix exporter has not yet run on the live proxy/matched studies.

| File | Contents |
|---|---|
| `runs-0000.zip`, … | Original completed-run reports, bindings, every retained daily forecast/event/commit/latest state and per-run stdout. Twelve runs per part by default, in original matrix order; null-score runs remain included. |
| `metadata.zip` | Complete matrix, independent daily and latest-state proofs, available profile/selection, CPU-loaded/hash-checked common Source checkpoints, available Source reports/stdout and explicitly named attachments. |
| `code.bundle` | Full reachable committed Git history through the export code, including original executed study commits. No environment, data or checkpoint is committed to Git. |
| `catalog.json` | Exact part sizes/SHA-256, CRC checks, run-ID populations, Source identities, omissions and export code. Written only after the complete export succeeds. |

Each run ZIP stores its own unique `part-records/runs-NNNN.json`; there is no
shared per-part header path to overwrite during a multipart restore.

Before export, require an independently verified complete matrix and a matching,
complete latest-state proof bound to that daily verifier. Rehash daily commit
chains and committed bytes, CPU-rehash latest model/optimizer/RNG contents and
check the actual binding/report. Source weights must match every target's seed,
namespace/population and fixed 64-dimensional latent scale. No training or new
forecast is performed. Existing runs and archives are never overwritten.

Reject unsafe/drive/reserved paths, symlinks, extra uncommitted files, missing
required states/logs and duplicate/colliding identities. Historical full states
intentionally absent under the original `latest` policy remain absent, with the
same omitted-state count as the independent daily proof. The exporter never
manufactures those states. CRC-check every ZIP before publishing the catalog.
A failed export may retain partial parts for diagnosis; without a complete valid
catalog it is not a successful distributable release. Use a fresh output directory.

```sh
python -m tools.export_development \
  --matrix COMPLETED_STUDY/matrix.json \
  --verification DAILY_VERIFICATION.json \
  --latest-states LATEST_STATE_VERIFICATION.json \
  --source-root ORIGINAL_SELECTED_SOURCE_STUDY \
  --output NEW_EXPORT_DIRECTORY \
  --attachment analysis-summary.json=COMPLETED_ANALYSIS/summary.json
```

Keep attachment names unique and explicit. Include the identified Source/Fixed/
controller selection matrices/proofs and analysis outputs when packaging the
primary study; original shared packages remain valid dependencies with their
existing hashes. The archive preserves original report paths as provenance;
extract all parts into a new root, use its `study/` directory for the daily/state
verifiers and `sources/` as the selected Source root. Restore the supplied code
bundle with Git and use the exact executed code/config/data identities.

The default gives 92 run ZIPs for 1,104 calibration cells, plus metadata, code and
catalog. Keeping each package below 100 files also avoids a misleading partial
listing from the Drive folder reader. This is packaging granularity, never a
change in methods/cohorts or a favorable result filter. Download every part,
check its exact catalog identity/CRC, restore and independently reverify before
claiming complete off-runtime preservation or releasing any runtime storage.

The historical recovered controller chunks did not contain separate per-run
stdout files. A test repack may explicitly use `--allow-missing-run-logs`; the
catalog must list every missing original log. Do not use that exception silently
for new proxy/matched/CHARGED runs, where the original logs are available.

Five independent exporter fixture tests cover byte preservation, declared historical
omissions, corrupted/extra/symlinked files, binding changes, proof population,
portable paths and Source checkpoint identity. All 300 local offline tests and
README lint/format/diff/source-list checks passed. Corrected controller round-trip evidence is recorded below;
live-study export/transfer/readback remains to be verified; a tested exporter alone
does not prove that Kaggle outputs have been saved. No Final access or merge.

## Independent restore and first real trial

The first local CPU-only controller trial exported all276 recovered runs into23
run ZIPs plus metadata/code, with CRC checks and three Source models loaded. The
independent restore rejected it: each part reused the root `completed-runs.json`
header, which would overwrite a previous part's record. **That trial is not an
accepted distributable package.** Original archives/runs remain unchanged; the
rejected trial and its restore output are retained separately. No model training
or favorable experiment rerun was performed.

The corrected writer uses unique per-part metadata paths. The separate
`tools.restore_development_export` pins the catalog, checks every part size/hash,
rejects missing/aliased/traversing/symlinked/overlapping payloads, restores to a new
directory without overwrites, and checks restored matrix/proofs/Source identities.
It never runs bundled code or trains/infers. Three transport regression fixtures
cover multi-part restoration, the legacy overlap, changed identities/parts and
unsafe payloads. The full303-test local suite and checks pass.

```sh
python -m tools.restore_development_export \
  --package ALL_DOWNLOADED_PARTS \
  --catalog-sha256 PINNED_CATALOG_SHA256 \
  --output NEW_RESTORED_ROOT
```

Transport success is followed by `tools.verify_comparison` with the accepted
input root and `NEW_RESTORED_ROOT/study/matrix.json`, then
`tools.verify_latest_states` bound to that fresh daily proof. Use new verification
output paths. Corrected real-data round-trip verification is recorded below;
the live Kaggle export/transfer is still pending. Neither CRC alone nor successful
ZIP creation can close that acceptance gate.

## Corrected controller round trip verified

| Check | Actual evidence |
|---|---|
| Producer / independent restorer code | `143aa74adb91e0425ae41316eee5d6d69ae39a74` / `b34c97989bf51b224042991ccfa1752b088ffadc` |
| Package | 23 target ZIPs + metadata ZIP + code bundle; 405,799,711 part bytes |
| Restore | 276 runs, 77,042 files; no overwrites |
| Post-restore daily/input verification | 276 runs, 51,060 committed files hashed |
| Daily proof | Byte-identical to the original independently verified controller proof |
| Post-restore latest-state check | All 276 model/optimizer/RNG states pass |
| Source checkpoint reload | All three restored Source10 models CPU-loaded/hash-checked; all three original Source stdout files included |
| Historical target stdout | 276 original per-run stdout files absent from quota-recovery chunks; explicit exception recorded, not invented |
| Tests / CI | 304 local offline tests and README checks; Ubuntu/Windows CI40240334688 passed for `b34c979` |

[Machine-readable round-trip evidence](issue23-export-roundtrip.json) records exact
code/catalog/proof identities. The rejected v1 trial remains separate. A small
summary-harness field lookup failed after valid verifiers finished; the summary
was corrected to sum per-run file counts, without retraining or replacing any
verification result. This is an actual byte-preservation and reconstruction test,
not additional experimental runs or a new scientific effectiveness result.

The [incremental export/restore code bundle](https://drive.google.com/file/d/1mkrh2nmHfAAS9SaFVmil6uvROEj2xRe_/view)
extends the queued analysis commit `5fa321f` to `b34c979`. It was downloaded without
account/browser authentication and matched SHA-256
`69702ab03733525260ebade91dd77b25a8fdd7503d9039a2ff80f9ceb2a7455f`.
A new Kaggle cell is queued after successful context/proxy analysis. Only then
will it update the checkout, run its tests/checks and export the completed proxy
and matched families with their Source/Fixed/controller dependency matrices,
proofs, context output, analysis and logs. The original live training checkout is
unchanged. Those future exports have not run or reached Drive yet; full download,
restore and independent verification remain required before releasing storage
or starting storage-heavy subsequent city batches.

## Actual live-Kaggle binary checkpoint download

While the original GPU batch continued, the supported Output-file Download action
retrieved the first completed run's `run.json`, tick0091 `commit.json` and
`state.pt`: `urbanev-SZH-1405-7d-source_error-seed42-recipe0`. Selection follows
the predeclared batch order, not observed accuracy. The report matches its entry
in the previously saved529-report snapshot. The latest commit hash matches the
report chain, and the1,971,709-byte checkpoint matches the commit's state hash.

CPU weights-only loading and model/Adam reconstruction passed for all three
branches, lambda0/0.1/1. Model, optimizer, RNG and step content hashes match the
report exactly; the original Source10 seed42 checkpoint identity also matches.
Each branch retains one CUDA RNG state, but no CUDA RNG restoration or GPU resume
was attempted on the laptop. No local training or prediction substitution.

[Full integrity record](issue23-kaggle-first-checkpoint.json) ·
[checkpoint/report/commit/proof ZIP](https://drive.google.com/file/d/1hNqnUcR6myCWEQ9Zaqu1Q3Lapz6IYNrF/view).
The1,604,068-byte package was anonymously downloaded again: archive bytes/hash,
CRC and all four member fingerprints match, and all three downloaded branch
content hashes pass CPU checks again. Large checkpoint bytes stay outside Git.

This preserves **one latest state**, not the complete study or a self-contained
runner Store. Earlier tick directories, all daily forecasts/events and stdout
were not transferred by this test; do not fabricate empty ticks or claim exact
resume from this partial package. Complete multipart exports, off-runtime score/
arrival verification, full state checks and independent teammate reproduction
remain pending. The live Kaggle checkout was not modified or interrupted.

## Opt-in input snapshots for repeated read-only verification

The default verifier path remains streaming and unchanged. For a large completed
matrix, `tools.verify_comparison --cache-inputs` authenticates immutable byte
snapshots of each input root's manifest, entity metadata and label file, using
their existing expected SHA-256 identities. It decodes labels only for explicitly
requested Development targets and reuses those target records across methods/
recipes/seeds. Source/Final label value arrays are never broadly decoded. Captured
byte strings cannot be changed by later writes to a source path; file identity,
size and nanosecond timestamp guards additionally reject ordinary input changes
during capture, between runs and before proof acceptance.

Every daily forecast/event/state-file hash, original-unit candidate/deployed/audit
error, arrival gate, decision identity and intentional historical-state omission
check remains in the common verifier. The new proof records authenticated input
file identities and raw snapshot bytes separately from the unchanged daily-file
counts. This trades RAM for repeated input I/O; it is not an end-to-end speed or
memory claim. UrbanEV's three label files alone total about348MB; a pooled matrix
can retain more roots. Use per-namespace verification when memory is constrained.

321 local offline tests and lint/format/diff checks pass. New fixtures require
exact proof parity with the streaming path, one input-byte read across repeated
runs, rejection of changed input files/manifest requests and changes during daily
checks, and rejection of Final targets without decoding unrelated Final arrays.
A complete real-controller parity/timing run remains pending at this code commit.
No running Kaggle checkout or command was changed; this option is for subsequent
explicit verification calls after its real-data checks pass.
