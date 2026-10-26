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
