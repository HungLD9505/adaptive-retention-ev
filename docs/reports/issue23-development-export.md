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

Five independent fixture tests cover byte preservation, declared historical
omissions, corrupted/extra/symlinked files, binding changes, proof population,
portable paths and Source checkpoint identity. All 300 local offline tests and
README lint/format/diff/source-list checks passed. Real controller repack and
live-study export/transfer/readback remain to be verified; a tested exporter alone
does not prove that Kaggle outputs have been saved. No Final access or merge.
