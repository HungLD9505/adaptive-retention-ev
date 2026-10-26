# Authenticated selected Development collection and analysis

Issue #23 / PR #52. `tools.analyze_matched` is read-only. It assembles selected
rows from the completed Source-duration, Fixed Retention, Adaptive Controller,
proxy/parameter and missing-comparator matrices. Every matrix must match its
independent verifier fingerprint, complete population, counts, scores and commit
chains. The source/controller dependency hashes and common cohort must agree.
No Final data, best-seed selection or retrospective forecast replacement.

Recompute all five families' selections using the predeclared station/seed-first,
equal-budget scores. Never trust an edited winner pointer. Require every expected
method/station/budget/seed cell, including nulls, and the correct actual config,
common training schedule, input/Source family and unchanged core algorithms.
Without Confidence aliases Online Best only at delta0. The bridge is a separate
diagnostic reference when needed, not a second tuned main Adaptive method.

For each selected run, rehash the actual daily forecasts/events and commit chains,
check the authenticated local run report, follow each saved prediction identity
into its score event and reconstruct original-unit daily MAE/MSE. Compare the
**full actual ordered issued origins and scored-origin sets**, not counts or a
silent intersection. The previous independent verifier has already recomputed
original-unit residuals from arrived complete labels; the collection checks its
fingerprint and exact scores before trusting it. This collector does not itself
re-read label arrays, rehash checkpoint tensor contents or prove publisher causality.
A complete downloaded-state check remains required after export.

## Aggregation and interpretation

- Average paired seeds within station and stations within budget. Keep budgets
  separate; their station IDs differ. Report MAE and mean per-seed/per-station RMSE,
  not a misleading pooled-hour RMSE under the same label.
- Retain unscored entities explicitly. Mixed score availability across seeds,
  absent cells, altered bindings and coverage differences fail closed.
- NTR is station-level after averaging paired-seed MAEs against Target-only.
  Target-only MAE0 has no relative gain/NTR classification: report absolute gap
  and zero-baseline denominator counts, not a substituted denominator.
- Report initial-adaptation versus no-initial-trainable strata separately, with
  method-specific initialization in run rows. Source-checkpoint-only targets are
  not silently pooled as initially adapted targets. Also retain weekday/weekend
  station-first slices.
- Adaptive-minus-comparator uncertainty reuses the declared seven-calendar-day,
  circular paired station/time bootstrap with 2,000 resamples and fixed analysis
  seed. Preserve calendar gaps, average the recorded three seeds within stations,
  and share calendar draws across stations. Intervals are exploratory marginal,
  conditional on this small nonrandom/possibly colocated Development cohort and
  all staged tuning. They are not population, simultaneous or unbiased Final CIs.
- Saved old-policy audits provide descriptive paired new-minus-old gaps, with
  unscored audits remaining null. No harmful-switch threshold or recovery time is
  invented. Cost rows retain candidate/audit steps, elapsed totals and reset GPU
  peaks; reused Source/preparation/export and overlapping fixture/backup costs
  still need explicit total capacity accounting.

The collection records whether selected Fixed Retention lies in the Adaptive
candidate set. If it does not, surface this for ablation/fairness review rather
than silently changing the selected baseline or controller. Proxy signal-versus-
retention relationships, load-density context thresholds and complete fairness/
capacity review still need actual analysis. This command cannot grant Final lock,
independent peer approval, merge or acceptance of all Sprint 3 deliverables.

## Completed primary matched execution — 2026-10-26

The original Kaggle batch completed all **690/690 fresh matched reference and
comparator runs**, after all 1,104 proxy/parameter calibration runs. Downloaded
server logs record exit 0 for matched training (3,061.748 seconds), independent
daily verification (343.701 seconds) and the first collection analysis
(79.518 seconds). These are stage wall times, not standalone per-method costs.
The later context/proxy analysis ran at clean code `5fa321f`. All training stayed
at clean `54131cbb` on one visible Tesla T4; no laptop training or Final outcomes.

The complete downloaded matched matrix and daily proof authenticate **127,650
daily files**, 690 run identities/counts/chains and 330 null-metric cells. Bound
latest-state proofs cover all 1,104 calibration and 690 matched runs on Kaggle.
Local recomputation authenticates all five matrix/proof dependencies, the exact
finite choices,966 selected cells and every station-first MAE/RMSE point estimate.
This does not substitute for independently restoring daily files and checkpoint
contents outside Kaggle; full multipart transfer/restore is still underway.

Conditional Development MAE (kWh), with paired seeds 42/43/44 averaged within each
station, stations weighted equally within each budget:

| Method / unique variant | 7-day | 14-day | 28-day | Equal-budget mean |
|---|---:|---:|---:|---:|
| `adaptive` | 4.842021 | 5.098825 | 5.524448 | 5.155098 |
| `block28` | 4.860595 | 5.114370 | 5.529150 | 5.168038 |
| `block7` | 4.823624 | 5.074131 | 5.501052 | 5.132936 |
| `drift` | 4.889842 | 5.100598 | 5.508642 | 5.166361 |
| `fixed_retention` | 4.808104 | 5.056981 | 5.499802 | 5.121629 |
| `frozen_source` | 5.052220 | 5.250804 | 5.687057 | 5.330027 |
| `full_finetuning` | 4.899140 | 5.144953 | 5.527041 | 5.190378 |
| `online_best` | 4.905242 | 5.090410 | 5.517026 | 5.170893 |
| `parameter_retention` | 4.899126 | 5.144972 | 5.526255 | 5.190118 |
| `seasonal_naive` | 8.845463 | 8.463111 | 9.810850 | 9.039808 |
| `source_error` | 4.846813 | 5.097881 | 5.526969 | 5.157221 |
| `target_only` | 8.775013 | 8.023459 | 8.528936 | 8.442469 |
| `uncertainty` | 4.846813 | 5.120451 | 5.524383 | 5.163882 |
| `without_source_initialization` | 8.971036 | 8.261207 | 8.578580 | 8.603608 |

**Adaptive does not beat selected Fixed Retention on any of these three budget
point estimates.** It improves on Full Fine-tuning in this selected cohort;
that is not evidence of population superiority or a reason to keep searching
until a favorable configuration appears. No new tuning configurations were added.
The nonrandom cohort has only 3/4/5 scored IDs by budget; another 3/4/4 IDs remain
unscored. The complete selected 14-method collection retains 462 null cells out of
966, not zero errors. Budget IDs differ and possible co-location remains.

Fourteen unique methods cover the main method, nine baselines and five ablation
categories through declared aliases: Without Confidence reuses Online Best-lambda
at delta 0, and Fixed lambda reuses Fixed Retention. Selected Fixed lambda 1 lies
inside the Adaptive candidate set 0/0.1/1. Fresh Kaggle Adaptive/FT/Fixed rows
replace earlier Colab comparison rows; the old outcomes remain calibration
provenance only. All common runtime/config/input/Source identities match.

The downloaded context/proxy summary includes exploratory station/calendar
intervals, density/weekday/initialization/30-day slices, descriptive proxy
relationships and component costs. Stronger full-collection audit/switch verification also completed and its downloaded
supplement was authenticated (see the recovery update below). Complete off-runtime
re-execution of daily/state joins and intervals remains pending;
no equivalence, causal, independent Final or related-paper reproduction claim.
Independent review and complete compute/storage acceptance are still required.
JHB subsequently logged a complete pipeline, but its full outputs were not recovered
before the temporary runtime was replaced; the other five cities remain unstarted.

[Exact metrics, provenance and acceptance boundaries](issue23-matched-evidence.json)
· [metadata/proofs/analysis/logs ZIP](https://drive.google.com/file/d/1VTTbc30qxMbKA4oAdKcASiJMnqijkH5a/view).
The ZIP passed anonymous byte/hash/CRC and all member fingerprints. It is not a
full checkpoint/forecast backup. Complete exports were generated on Kaggle
(94 calibration parts, 60 matched parts). The runtime-loss update below supersedes
the previous assumption that their source copies were still available. No Final lock/evaluation, autonomous merge or issue closure.

Historical implementation status:269 fixture tests initially passed before the
full matrices completed. The current321-test implementation and subsequent
actual evidence do not imply independent peer approval. Earlier source/fixture
snapshots retain their original scopes; see the linked evidence record and
[analysis definitions](issue23-analysis-extensions.md).


## Runtime-loss and recovered evidence update — 2026-10-26

A fresh draft session was observed with only the 600,416-byte virtual notebook
source under `/kaggle/working`; an executed read-only cell raised
`FileNotFoundError` for the former JHB `pipeline-complete.json`. The old Output
sidebar retained cached file names and is not evidence that those files survived.
A test download of missing proxy part0038 timed out. No output-preserving saved
version is verified: version3 is explicitly code-only and versions1/2 still show
Starting. The exact cause/time of the original session replacement is unknown.
This is a storage/handoff failure, not a new numerical research finding.

The original notebook output records JHB's three same-city Source completions,
378 target completions and pipeline exit0, with training/daily/state/analysis/
export stage exits0 (2,467.321/21.434/16.284/54.499/95.747 seconds). It records
matrix SHA-256 `64e6b865eacb3c7f5fc14e7b110198f0f11571430f7d77812b7b07619fd2d488`
and export catalog `72e4508f01fc76b3b3774368553d20cd9ebb6f2aa3f353627a38672803eaf40e`.
Those log identities cannot replace the missing files. **No JHB metrics, complete
checkpoint handoff or off-runtime acceptance is claimed.** Do not call JHB
unexecuted, but do not count it as reproducibly delivered either.

Primary metadata/analysis/proofs and the three previously archived Source models,
Fixed and controller archives remain available outside this runtime. Local proxy
export parts0000–0037, `code.bundle` and `metadata.zip` match catalog size/SHA-256:
40/94 parts,718,194,764 bytes. This is a partial backup; the remaining54 parts and
the full60-part matched export are not recovered. The complete downloaded primary
summary still supports the table above at its stated metadata-verification scope;
it does not prove that every underlying checkpoint/forecast remains recoverable.

The stronger completed analysis supplement is durably shared:
[full switch/audit supplement](https://drive.google.com/file/d/1mQcEv5Lke8SxZqwIu-v63Rh0uJao_2-M/view),
504,599 bytes, SHA-256
`0e83c76254fee25928b51cdb6896bba27ef8094cfbb535d7daa00a14882d35b2`.
Anonymous bytes/hash/ZIP CRC and all15 member fingerprints matched. Its summary
SHA-256 is `ecc8b1854128f84ab13070be4ab38d6179d7f15c331f8cf2caf72604576157b6`;
all previous14-method point estimates and finite selections are unchanged.
The downloaded stronger proofs cover2,070 runs,382,950 daily files,12,696 decision
events,741 finalized audit summaries and8,452 recomputed old-policy audit scores.
These are recorded remote checks, not a new complete local daily/state restore.
A local draft counter summary used the wrong key and reported0 audit scores; the
corrected summary uses `audit_forecast_scores_verified`. Original archive and
verifier bytes were preserved; no expected hash was changed.

Recovery must use the unchanged finite configuration, seeds and input identities,
with a distinct run identity and explicit comparison to retained metadata.
Do not rerun until a favorable score appears. Before another city is delivered,
verify its complete off-runtime archive or output-preserving saved version; a
printed exit0 and code-only notebook are insufficient. No new training was
started during this incident inspection. Independent review, all six delivered
city scopes, complete primary restoration, compute acceptance and Final lock
remain open. No Final, autonomous merge or issue closure.


### Same-configuration JHB recovery started

After the filesystem loss was confirmed, a new run was explicitly launched at
`/kaggle/working/qyroven-jhb-storage-recovery-20261026-v2`, child PID407.
Bootstrap fixtures, Ruff lint and format passed before launch. It checks out
original city code `9057364e6a8e663b9ba9c204621d109c02bed3e0`, reuses the exact
accepted JHB input/cohort, primary-summary and density fingerprints and retains
seeds42/43/44, all7/14/28-day budgets,10 Source epochs and the same378 target cells.
This is disclosed recovery from missing storage, not a new configuration search
or selection of a favorable rerun. No recovered numerical result is claimed yet.

The [self-contained recovery dependency archive](https://drive.google.com/file/d/13E4lTy6jqCrH6IEQlCDKbcj1Ea-lvKDz/view)
is8,176,124 bytes, SHA-256
`7f21d35ba89113aed187a644a7b583e70cf83f15f3a87052bc794144ad2076dd`.
Anonymous archive size/hash/CRC and all member hashes passed; it contains complete
code history, unchanged pipeline source, primary summary and density metadata,
not trained weights or replacement evidence. The new launcher prepares both a
small metadata archive and a single complete export ZIP immediately after the
pipeline succeeds. Creating those files on temporary storage is still not durable
acceptance; download/readback and independent full checks remain required.


The three new JHB Sources have now been preserved independently of Kaggle:
[Source checkpoints and training records](https://drive.google.com/file/d/1ebTZQ3lsNdtaR6TLbaxsowYDVxAaJ6ed/view),
18,263,480 bytes, SHA-256
`3ca64e13696ae7aa03ed5686cf2c99e83495eead1580cda4fa27dcdb1c914767`.
Local download and anonymous Drive readback matched bytes/hash/ZIP CRC/all78
manifest members. All three epoch10 checkpoints loaded on CPU using the
weights-only loader; architecture, JHB Source binding, seeds42/43/44,10 completed
epochs and finite64-dimensional latent scales passed. This is verification, not
local training. Each Source used2,340 allowed examples; target comparisons remain
in progress. These are the explicitly identified recovery Sources, not an
undisclosed replacement for the missing original JHB checkpoints.


### Independent verification of physically preserved proxy runs

All40 available export parts were rechecked against the original complete catalog
(size/SHA-256/ZIP CRC) and restored into a new explicitly partial directory. This
recovers456 complete original proxy/parameter runs, not all1,104. Their saved
reports match the unchanged original matrix. The existing daily/input verifier
recomputed all84,360 daily-file hashes, availability-bound original-unit scores,
commit chains and2,696 audit forecast errors; each per-run proof exactly matches
the stronger original remote proof. The existing weights-only CPU state verifier
also matched all456 latest serialized model/optimizer/RNG branch contents.
No model was trained, no Final label decoded, and no source expected hash changed.

This preserves192 null-metric runs rather than filling or dropping them. The
runs are an ordered archive prefix, not a newly selected performance cohort.
[Exact scope and partial proof](issue23-preserved-partial-evidence.json) links the
77,175-byte proof/source/log/catalog ZIP; anonymous bytes/hash/CRC/all4-member
readback passed. Missing54 proxy parts and the60-part matched export remain
explicitly unrecovered; partial verification cannot grant full-matrix acceptance.


All40 preserved proxy parts (718,194,764 bytes) are now in the shared partial
export folder and have passed anonymous remote size/SHA-256 checks; every ZIP
also passed CRC. Exact returned file IDs and fingerprints are in the linked
partial-evidence JSON. This covers the same456 original runs, not the648 missing
ones. The folder has an explicit `README-PARTIAL.txt` and partial index; the
original complete catalog and expected run population were not weakened.

The JHB recovery's first182 completed target runs were captured from one immutable
progress snapshot and backed up locally. The289,105,442-byte ZIP was too large
for the browser download to return a file within its observation timeout. Fourteen
20MiB-or-smaller transport chunks were downloaded and independently hashed, then
concatenated; the exact original ZIP SHA-256
`b7c8de2733f0e7720b28698e83e8a20d0b7e0c400d416a71b6707d216b9867f9`,
CRC and all50,778 manifest member hashes matched. Existing read-only verifiers
then recomputed33,670 daily files,3,261 old-policy audit forecast errors and all182
latest model/optimizer/RNG branch states against the accepted JHB Development
inputs and archived Source identities. This is a completed-prefix check, not a
full378-cell result. The first local draft inspection used the wrong nesting
for a Source seed and raised `KeyError`; its failure log was retained. Corrected
v2 verification passed without changing any data, expected hash or model.

Uploading that289MB archive through the connector failed with a300-second blob
transfer timeout and returned no Drive file ID. Direct Drive UI upload was then
started; it is not counted complete until confirmed and read back. A Quick Save
with **Save output for this version** was also requested; version4 remains Queued,
so it is not accepted as a durable backup. No new training was dispatched by the
save operation. SPO inputs have been staged and their archive/all three manifest
hashes verified, but SPO training has not started.

## Prepared exact missing-artifact replay

The later recovery inventory authenticates the original complete proxy and
matched matrices and all three retained epoch10 Source checkpoints. It partitions
the proxy population into456 already verified originals to preserve and648
physically missing runs to replay. All690 matched raw runs also require recovery.
Selection uses physical absence and original matrix order, never error or seed.
The missing subsets retain336 proxy and330 matched null-metric cells.

The [prepared recovery kit](issue23-primary-recovery-plan-evidence.json) contains
the original matrices, exact partition, original Source bytes and a standalone
CUDA driver calling the unchanged runner. Anonymous Drive size/hash/CRC/all9-member
readback passed. Read-only actual-plan validation and independent miniature
fail-closed cases passed; the driver is not yet GPU-executed or accepted as a
completed recovery. It checks Development roles/scalers before execution, records
new lineage, verifies each new daily/state artifact and reports differences from
the original results. It performs no new calibration or favorable selection.
Core model/controller/runner/baseline files are byte-identical between original
training54131cbb and recovery9057364. GPU numerical equality and full physical
recovery remain to be tested; no original expected hashes are replaced.


### Missing-proxy recovery: complete metadata, physical handoff still pending

The unchanged missing-only plan completed all 648 proxy runs on Colab with
phase exit0. The independently downloaded 17,982,875-byte matrix has SHA-256
`d6a9f48fae009b5f5046b101e8499f2b660b451eca31ee6222fb842099c178b2`.
All 648 exact original missing IDs are present, with unchanged inputs/configs/three
Source checkpoint identities. MAE/RMSE, scheduled/issued/scored days, forecast
identity, candidate/audit steps and final branch-state hashes have zero reported
differences from the original matrix. The 456 original preserved proxy runs remain
untouched. This is metadata/digest agreement, not yet independent verification
of every raw prediction/event/checkpoint byte.

At 01:22 ICT October 27, the actual primary handle was live with 224/690 matched
runs completed; the 114-cell same-runtime selected-proxy bridge and subsequent
LOA/SZH/AMS city queue were live waits on their verified process dependencies.
An immutable progress/log/package snapshot was saved and hash-checked on the
mounted Drive, with a separate local observation receipt. This is a dated
observation, not a promise of future job liveness.

A separate [CPU-only canonical handoff](https://drive.google.com/drive/folders/1K1ai721dHeOqNBo8h9fkzsBLTmouh8_M)
was dispatched as PID 31955. It independently verifies all 648 daily and final-state
records before exporting immutable parts, verifying mounted copies and publishing
the catalog last. It neither retrains nor restarts the GPU process. CPU/I-O overlap
with matched execution is recorded; affected wall times are not isolated latency
measurements. Canonical completion, anonymous download, complete local restoration
and peer acceptance remain pending. See the [exact evidence](issue23-primary-recovery-plan-evidence.json).


### Complete 648-run recovery: independent physical verification passed

The [canonical export](https://drive.google.com/drive/folders/1ykS8yHGKs-IiUgupbclkW2CWk6ahd-Hj)
completed with 56 parts totaling 912,026,869 bytes. Catalog SHA-256:
`c3818e006b014b4e2d47a0e1392eb5e73723ca00d2df2e385a8f946fcaf0bc59`.
All parts were downloaded outside the runtime, checked for size/hash/ZIP CRC and
safe nonoverlapping payload paths, then restored into a new local directory.
42 parts used anonymous Drive downloads; 14 used the connected Drive stream after
anonymous link retrieval failed. Sharing, accounts and expected hashes were not
changed. The failed downloader log and each successful part were preserved.

Independent read-only CPU verification of every restored daily forecast/label/event
chain and latest model/optimizer/RNG branch passed for all 648 runs. Full daily/input
and latest-state proof objects exactly equal the Colab proofs. The three selected
Source checkpoint bytes also match the catalog and original Source hashes.
No bundled code was executed and no local training was performed. The verifier
code was confirmed unchanged from export commit `1ac2ae0`; local verification
ran at `6b16a3e`. Historical states intentionally absent in the original latest-state
policy remain absent; they were not reconstructed or presented as recovered.

The [independent evidence archive](https://drive.google.com/file/d/1k0gH58SMseJ_04MT7uQdFumgO6yi2hEh/view)
contains transport/content proofs, commands and actual stage logs, scripts and the
immutable catalog: 102,070 bytes, SHA-256
`f1c41b25d1bac003ac97b30e6267dbc906845e6f564ada846f493abea4f3b53f`.
Daily proof SHA-256 is
`aaf25424fa9409b5e401786c80ea51435a160e417c5e52d5b1e7ddb12eb7d7e7`;
latest-state proof SHA-256 is
`f6e4724544b96c2a01d9bdf0244f93f89eec5b546c6a5f60ff6bba4c99760408`.

This completes the missing 648-run proxy physical-artifact recovery, not all
primary comparisons, same-environment bridge, six-city Development acceptance,
independent peer reproduction or Final. The 690 matched recovery and 114-cell
bridge remain separate gates. The CPU verifier/export overlapped matched runs
242–283 for 372.586 seconds; affected wall times are explicitly not isolated
method-latency measurements. No calibration choice or outcome was changed.


### Provider runtime interruption after the verified proxy handoff

Colab then explicitly reported runtime disconnection due to inactivity or maximum
duration, and the same-account reconnect reported GPU usage limits. The exact
original disconnection cause is not supplied. There is no current GPU-job liveness
claim. The queues in that runtime also need redispatch after restoration; cached
PID/output text is not a live process. No account was rotated or compute purchased.

The complete matched backup folder inventory has 909 files: 451 target ZIP/receipt
filename pairs, three selected Source ZIP/receipt pairs and context. If every target
pair passes restoration, 239 of the planned 690 matched runs remain. The filename
inventory alone is not content verification; CPU restoration is the next check.
The completed 648-run proxy handoff already passed complete off-runtime checks
and remains safe on Drive and local storage. Its uploaded independent evidence
also passed anonymous size/hash/ZIP CRC/all 15 payload checks on readback.

The 451 matched filename pairs exactly form the first 451 IDs in the authenticated
original 690-run plan; there are no ID gaps, reordered selection or extra targets.
The first remaining ID is `urbanev-SZH-2152-28d-target_only-seed42`. A same-account
CPU runtime connected with Python3.13.16/Torch2.11.0+cpu and no old runtime files.
Its Drive mount failed after two minutes (`ValueError: mount failed`), so this
step did not restore or execute matched targets. GPU access and the Drive mount
remain concrete recovery blockers; the 451 archive contents are not yet claimed
verified from the directory listing.


### Matched interruption boundary: all 451 completed targets restored and verified

The connected Drive stream retrieved the complete 909-file backup inventory
(434,277,286 bytes) independently of the failed Colab mount. No permissions or
accounts changed. The first local preflight stopped on an incorrect historical
Source-report path before extraction; the failed script/log were retained and the
correct original report path was used for the successful read-only second run.

All 454 archive/receipt pairs passed byte hashes, ZIP CRC, envelopes, context and
safe-path checks. The three original Source checkpoints/reports/latent scales
were CPU-reloaded and matched their original hashes. All 451 target daily/input
and latest-state proofs exactly reproduced their receipts: 83,435 files hashed,
26,489 issued days, 14,332 scored days, 1,796 audit forecast scores and 451 latest
model/optimizer/RNG states. These are repeated per-run counts, not unique target
days or independent statistical samples. Every checked original MAE/RMSE,
scheduled/issued/scored count, forecast identity, candidate/audit step count and
final branch-state hash matched; zero difference records.

The restored IDs form the exact first 451 of the original 690-run plan. Therefore
239 matched runs remain, starting with `urbanev-SZH-2152-28d-target_only-seed42`.
Exact backup continuation requires the recorded CUDA13.0/Torch2.11.0+cu130,
Python3.13.16, TeslaT4/Linux environment, unchanged code/input/config/Source context
and a real durable mount. A new provider/environment must not be silently
appended to that context or mixed within paired comparisons.

[Independent full prefix evidence](https://drive.google.com/file/d/1IGjxp_BxzBfZcofTjNCDjRKAnV0fBXk9/view):
2,443,091 bytes, SHA-256
`ac38ca60a2857cf2199be4e934c2a64e88648a1dd5523633add90e7a462d01b9`.
The uploaded proof passed anonymous readback for size/hash/ZIP CRC and all464
manifest payloads. Context SHA-256:
`25839a9cfddcb6805e6ea8c52021d39042869917a91ce8eb4be0d3517e40a46f`.
This is completed-prefix recovery, not 690-run completion or GPU continuation.
No training, Final access or outcome-based reselection occurred locally.


### Separate Kaggle runtime: preserve complete paired units, replay incomplete units

A new independent Kaggle notebook successfully executed an environment-only probe
on Tesla T4 (Python3.13.15, Torch2.11.0+cu128, CUDA12.8), with16 GPU hours remaining
shown by the provider. The inaccessible SPO/MEL notebook was not restarted. Its
latest saved version4 is a historical quick-version snapshot, not a new durable
SPO/MEL raw export. Colab's exact-context GPU continuation remains unavailable.

The new runtime cannot be silently appended to the Colab backup context. The
existing analysis requires all methods within each station/budget/seed unit to
share target execution environment. An outcome-blind artifact/identity inventory
finds16 of69 units complete with all14 methods in the Colab environment. Those224
selected cells are preserved. The remaining53 units must each execute all14
methods together:212 frozen selected-proxy plus530 matched cells,742 replays.
This includes291 already restored matched cells that require same-unit runtime
replication; it does not redefine them as lost artifacts. The239 physically missing
matched IDs remain distinguished in the interruption ledger. Existing outputs
are never overwritten, and repeat runs are not independent statistical samples.

The [prepared plan/Source kit](https://drive.google.com/file/d/1d7BozzYvIFC06lTfGHJVaBKdvXZgy7fj/view)
is3,085,286 bytes, SHA-256
`1aa4f8fca25701073862f39c55f2f06a372488f5c68907b1e8ae1ac4fb9c2d2f`;
plan SHA-256 `984226d37a815f331e754fb64eb511052cd2bf46d8527ca3ea055bdfd2062fc8`.
Both families passed authenticated metadata/Source validation. Selection uses only
identity, method, execution environment and verified artifact availability, never
errors/outcomes. Original69 units, three seeds, configs, selected recipes and
Source checkpoints are unchanged. NumPy2.3.3 and the exact new execution profile
are pinned before fitting; the initial notebook probe had NumPy2.1.3.

The maintained bounded Kaggle outbox explicitly stops after at most12 target
runs and requires external independent transport/content/Drive-readback acceptance
before its next offset. It does not fake a Drive mount. The first actual cloud
transport acceptance must use one run before expanding to larger chunks. This
prepared742-run matrix is not executed or accepted yet. See the
[outbox contract](issue23-durable-recovery.md) and exact evidence JSON.


### First new-runtime run published; bounded continuation dispatched

Kaggle bootstrap code103bf2c passed346 actual cloud fixtures (23.176s), Ruff and
code/kit/input hashes. One actual Source-error run completed:
`urbanev-SZH-1405-7d-source_error-seed42-recipe1`. Daily/state verification passed,
but canonical export rejected its three Source descriptors for one initial seed.
No further run was dispatched after that failure. The original Source/target
archive/receipt set was retrieved using the notebook's ordinary Download control.

All four backup pairs were independently restored locally. The checked metrics,
forecast identities, step counts and final branch-state hash exactly matched the
original frozen reference, with zero difference records. The export-only fix
e831501 preserves actual initial-seed descriptors and attaches all three original
Source dependencies; it leaves the original target report, weights and predictions
unchanged. CPU-only rescue/export succeeded without refitting.

The [canonical first-run handoff](https://drive.google.com/file/d/1dhIos4YMXDRAAX2TQINthFaH1kBcriEx/view)
is12,108,887 bytes, SHA-256
`15a6addbf533d336ce1769cefed3fa166a4e6831c5509876f896ba09f00a63be`.
Actual Drive readback, canonical restoration, complete daily/input/state equality
and CPU reload of all three shared Source dependencies passed. The hash-pinned
[publication receipt](https://drive.google.com/file/d/1sfLpwKvAc4Dock3Jsr35OzsWKmwg_owe/view)
SHA-256 is `5f3462380fb190bf1463693420f55c7d3dbf251d88d850dda9a383af4a0257d3`.
[Independent proof/scripts](https://drive.google.com/file/d/1AG5Itn7u9h5jlYJ170WglJfW215KZQGU/view)
and the unchanged original backup wrapper are linked in the exact evidence JSON.

Only after those actual checks was the next range [1,13) dispatched as PID453
in the same Kaggle notebook, using a separate corrected checkout and that receipt.
It must pass fixtures and stop after at most12 runs for external publication.
Process dispatch is not12-run completion; the742-run matrix, remaining cities,
analysis, review and Final gates remain open. The source/export fix passed347
local fixtures (6.043s); new cloud fix acceptance is reported when actually seen.

### Two-run prefix preserved after progress metadata failure

The next chunk passed347 real Kaggle fixtures (22.146s), Ruff lint and format.
Two targets completed and committed their immutable archive/receipt pairs:
`urbanev-SZH-1405-7d-uncertainty-seed42-recipe1` and
`urbanev-SZH-1405-7d-drift-seed42-recipe3`. The process then exited1 because
the second progress update used exclusive creation for an existing progress.json.
This is an orchestration metadata failure; neither completed target is rerun.

The fix replaces only the progress pointer atomically after writing a new pending
file; immutable completed archives are untouched. The regression checks repeated
updates and preservation of prior progress/archives on an interrupted pending
write.348 local tests passed (6.926s), Ruff lint/format and diff checks passed.
No model, controller, runner or baseline algorithm changed.

The [two-run raw backup](https://drive.google.com/file/d/1GyrrXLF663N4Ldwf4_2Mg9PoO7Th77Qr/view)
was downloaded outside Kaggle and verified for ZIP CRC and all11 manifest payload
hashes before upload. It is5,541,810 bytes, SHA-256
`44898cec34489f92d1b0a6572974fd37f37a693a69e8f10287caa549914b74b3`.
Full independent target-content restoration and actual Drive readback remain
pending at this handoff. No next offset is authorized by this raw upload alone.
A first verifier preflight stopped because the local tooling fix was uncommitted;
it did not fit or alter any target.

Full two-run backup restoration then passed, including the immutable target
reports/weights, daily/input checks and latest branch states. Both runs exactly
matched all checked original reference fields. The first wrapper attempt rejected
the backup restoration's alphabetical order; a separate export restored frozen
plan order without fitting or changing target bytes. Failed attempt logs remain
preserved outside Git.

The [canonical two-run handoff](https://drive.google.com/file/d/1sk6sQtiPLV-SeV0DUDYIPSjGhlf61LyH/view)
is14,015,051 bytes, SHA-256
`17aedfbacb317c5b27de43e31c8ef12f2a4af07c0dad5785fc608ef5e244d101`.
Actual Drive redownload, canonical restore, full daily/state proof equality and
CPU reload of all three original Source dependencies passed. Prefix [1,3) is
accepted; [3,13) was never executed. The next eligible original offset is3.
There are now3 actual new-runtime targets fully published, not742.
