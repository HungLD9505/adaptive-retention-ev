# Issue23 joint execution evidence and research report readiness

As of 30 October 2026. Related issues: [#23](https://github.com/HungLD9505/adaptive-retention-ev/issues/23) and [#10](https://github.com/HungLD9505/adaptive-retention-ev/issues/10). **Draft evidence synthesis for peer review.**

Qyroven has completed the frozen 810-unit, 11,340-cell Final with seven separate namespace analyses and output/bootstrap audits. Hùng has completed a separate, bounded 360-job UrbanEV Final and supplied extensive Development, lineage and sensitivity evidence. Both tracks support reporting useful transfer in selected settings. Neither establishes a general accuracy advantage of the proposed confidence controller over fixed retention or online best-lambda. A full manuscript can be written now if it preserves that finding and the unresolved review boundaries.

This synthesis does not approve either implementation, close an issue, merge code, expand a Final cohort or change a frozen method. Its verification is analysis-output hash and arithmetic reconciliation, distinct from remote checkpoint verification and independent scientific review.

## 1. Current sources and the stale comparison correction

- Hùng review head: `1b730c7f83d6d8dd57198219c2593004d0318f4e` in [PR #72](https://github.com/HungLD9505/adaptive-retention-ev/pull/72). The current report is [draft v47](https://github.com/HungLD9505/adaptive-retention-ev/blob/1b730c7f83d6d8dd57198219c2593004d0318f4e/docs/reports/hung-e2e-research-report-draft-20261030-v47.md); the current acceptance register is [v70](https://github.com/HungLD9505/adaptive-retention-ev/blob/1b730c7f83d6d8dd57198219c2593004d0318f4e/docs/reports/hung-e2e-gate-register-20261030-v70.md).
- Qyroven production science: `61c32328d9829a69037dca629f727b4863015122`, lock `9c65169cced1506a450fdd7b8a57a69d5a720cac7acaa0dcd1c8ccfd1723ce42`. Final canonical ledger v813 has SHA256 `1be8a84c6ce0097492ee9dd6e2a2f8e0eae3e745dc5f7b94a47e603aa6b85a02`, exactly indices 0–809. The [completed primary handoff](issue23-final-complete-handoff-20261029.md) is included byte-for-byte.
- [Hùng's latest cross-track comparison](https://github.com/HungLD9505/adaptive-retention-ev/blob/1b730c7f83d6d8dd57198219c2593004d0318f4e/docs/reports/hung-qyroven-results-comparison-20261030-v1.md) accurately labels its sources as snapshots but uses Qyroven's old 170/810 terminal checkpoint and Development errors. It must not be cited as the current primary Final status. The current primary Final figures below supersede that snapshot for reporting.
- The new [integrated status report](https://github.com/HungLD9505/adaptive-retention-ev/blob/1b730c7f83d6d8dd57198219c2593004d0318f4e/docs/reports/aip491-g10-integrated-status-20261030-v1.md) is the sole change after 207255b. It also uses the old primary 170/810 checkpoint. Its fresh-clone test failure is material and is retained below; no Final table changed in this push.
- The [machine-readable synthesis](issue23-joint-evidence-synthesis-20261030-v1.json) contains all 14 primary methods, MAE/RMSE/NTR, comparator intervals, Hùng's reaggregated 14-method MAE/RMSE/WAPE, and source hashes. Large archives and model states remain outside Git.

The copied primary handoff retains its original links into ignored `runs/` evidence. Those links require the original operational evidence workspace or its archive and are not public GitHub artifacts. The committed synthesis JSON records their identities and the current numeric tables; it does not replace the underlying model/checkpoint archive.

## 2. What each track has delivered

| Dimension | Qyroven primary track | Hùng independent track |
| --- | --- | --- |
| Development | 231 declared whole units / 3,234 selected method cells across UrbanEV and six CHARGED cities | Author ledger: 782 unique new jobs; 851 analysis rows include 69 historical Main anchors; 407 null runs and 748 blocked pairs retained |
| Frozen Final | 810 whole units × 14 variants = 11,340 cells | 360 physical jobs; deterministic Seasonal Naive has one physical seed, not three independent replications |
| Final targets | 30 UrbanEV IDs plus 10 IDs in each of six CHARGED cities; 90 selected entities | UrbanEV/SZH 2118, 2534, 2579 only; excluded cohort/city scope is explicit |
| Histories and seeds | 7/14/28 days; seeds 42/43/44 | 7/14/28 days; physical seeds 7/11/19 |
| Output coverage | All declared Final cells accepted; 126 UrbanEV metric cells remain null at entity 2193 | 360 metric rows; 32,400 issued origins, 32,280 scored and 120 unscored; no null job |
| Analysis | Seven original namespace analyses plus separate output and derived bootstrap audits; 294 comparisons, 42 null intervals retained | Checkpoint-recomputed MAE/RMSE/WAPE, station/temporal sensitivity, switching and recorded stage costs |
| Execution state | Final completed, provider sessions released | Saved Kaggle Final /1 complete according to pinned provider readback reports |
| Review status | Execution/analysis handoff complete; peer approval and PR integration remain separate | Draft, CHANGES_REQUESTED at snapshot; explicit Block7/parity/lineage/Colab dispositions remain open |

A whole unit, method cell, physical job and analytical row are different units of accounting. Do not add 360 jobs to 810 whole units or turn their sum into a count of independent experiments. The three Hùng Final IDs are disjoint from the 30 primary UrbanEV Final IDs, but both tracks use UrbanEV/SZH; disjoint IDs do not prove geographical or statistical independence. Different heads, seeds, Source states, cohorts and calibration prevent direct ranking of their absolute MAE values.

## 3. Primary Final accuracy by namespace and history

All values are original-kWh MAE; lower is better. Seeds are averaged within station, then stations equally within each namespace. UrbanEV has 29 scored stations out of 30; each CHARGED namespace has 10. Cities are not pooled. Best refers to the lowest full-precision point estimate among the 14 executed methods, not a significance claim.

| Namespace | Days | Adaptive | Fixed | Online best | Full fine-tuning | Target-only | Seasonal | Best of 14 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| urbanev-SZH | 7 | 8.1014 | 8.0400 | 8.1152 | 8.2399 | 13.4341 | 12.1373 | fixed_retention |
| urbanev-SZH | 14 | 8.0517 | 7.9758 | 7.9668 | 8.1469 | 13.4132 | 12.1373 | online_best |
| urbanev-SZH | 28 | 8.0015 | 7.9159 | 7.9924 | 8.0670 | 13.3079 | 12.1373 | source_error |
| charged-AMS | 7 | 6.1559 | 6.1483 | 6.1520 | 6.1807 | 2.5621 | 0.8534 | seasonal_naive |
| charged-AMS | 14 | 6.1520 | 6.1482 | 6.1550 | 6.1794 | 2.6456 | 0.8534 | seasonal_naive |
| charged-AMS | 28 | 6.1529 | 6.1482 | 6.1535 | 6.1841 | 2.5537 | 0.8534 | seasonal_naive |
| charged-JHB | 7 | 1.3685 | 1.3206 | 1.3156 | 1.5829 | 2.8098 | 2.8870 | frozen_source |
| charged-JHB | 14 | 1.3604 | 1.3227 | 1.3535 | 1.5386 | 2.7865 | 2.8870 | frozen_source |
| charged-JHB | 28 | 1.3560 | 1.2919 | 1.2957 | 1.5366 | 2.6510 | 2.8870 | frozen_source |
| charged-LOA | 7 | 1.3273 | 1.3220 | 1.3275 | 1.3274 | 1.9062 | 1.5877 | drift |
| charged-LOA | 14 | 1.3431 | 1.3334 | 1.3388 | 1.3389 | 2.0956 | 1.5877 | source_error |
| charged-LOA | 28 | 1.3271 | 1.3265 | 1.3302 | 1.3350 | 2.0070 | 1.5877 | source_error |
| charged-MEL | 7 | 52.1542 | 52.8482 | 52.1250 | 52.2675 | 57.5527 | 67.7944 | block28 |
| charged-MEL | 14 | 53.0840 | 54.3655 | 53.3602 | 53.3272 | 77.9222 | 67.7944 | block7 |
| charged-MEL | 28 | 53.0832 | 54.2423 | 53.3592 | 53.8249 | 72.4460 | 67.7944 | block28 |
| charged-SPO | 7 | 1.9702 | 2.0217 | 1.9510 | 2.0221 | 2.4466 | 2.6805 | online_best |
| charged-SPO | 14 | 1.9414 | 1.9893 | 1.9316 | 1.9854 | 2.4683 | 2.6805 | online_best |
| charged-SPO | 28 | 1.9679 | 2.0256 | 1.9748 | 2.0116 | 2.5302 | 2.6805 | adaptive |
| charged-SZH | 7 | 90.6306 | 91.8211 | 93.2670 | 88.8440 | 101.9142 | 85.6015 | seasonal_naive |
| charged-SZH | 14 | 89.3300 | 90.8436 | 91.3722 | 88.5427 | 101.5134 | 85.6015 | seasonal_naive |
| charged-SZH | 28 | 89.3310 | 90.8853 | 91.7419 | 88.1054 | 101.6067 | 85.6015 | seasonal_naive |

The frozen primary bootstrap uses station-first aggregation, the shared 90-day calendar, seven-day blocks, 2,000 resamples, seed 20261026 and alpha 0.05. It is exploratory and conditional on the selected cohort and fixed paired seeds, without simultaneous-comparison correction. Counts below summarize directions across repeated budget cells, not independent statistical replications.

| Comparator for Adaptive | Lower point MAE / 21 | Higher point MAE / 21 | Defined intervals below zero | Defined intervals above zero | Intervals spanning zero | Null intervals |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| fixed_retention | 9 | 12 | 0 | 0 | 18 | 3 |
| online_best | 11 | 10 | 0 | 0 | 18 | 3 |
| full_finetuning | 17 | 4 | 6 | 0 | 12 | 3 |
| target_only | 18 | 3 | 15 | 3 | 0 | 3 |
| seasonal_naive | 15 | 6 | 9 | 3 | 6 | 3 |
| without_source_initialization | 18 | 3 | 15 | 3 | 0 | 3 |

For both Fixed and online best, all 18 defined Adaptive-minus-comparator intervals contain zero; the three UrbanEV intervals are null. This is insufficient evidence of an incremental controller advantage, and it is also not an equivalence test. Adaptive is the lowest point-MAE method in only one of the 21 namespace/budget panels: SPO, 28 days.

Adaptive improves point MAE over Target-only at 18/21 panels, but is worse in all three AMS panels. At AMS its MAE is about 6.15 kWh versus Target-only about 2.55–2.65 and Seasonal about 0.85; negative transfer affects 5/10 scored AMS stations at every history. AMS is an explicit adverse result, not an excluded outlier. MEL and SPO also retain station-level negative transfer despite favorable namespace averages. At CHARGED/SZH, Adaptive improves over Fixed and Target-only in point estimates, while Seasonal remains lower-MAE. These differences prevent a universal transfer or adaptive-benefit claim.

UrbanEV entity 2193 retains 126 null cells. Forty undefined bootstrap replicates out of 2,000 occur in each of its 42 comparisons; the original rule leaves all 42 intervals null. No undefined replicate is dropped or filled.

## 4. Hùng bounded Final accuracy and the contribution of confidence

The following values are recomputed from the tracked 360-row checkpoint-derived score table using equal physical-seed means per station and equal station means. They are internal comparisons within Hùng's three-station lock, not head-to-head errors against Qyroven.

| Variant | MAE 7 d | MAE 14 d | MAE 28 d |
| --- | ---: | ---: | ---: |
| main | 8.0505 | 8.0424 | 7.9156 |
| fixed_retention | 7.9607 | 7.9523 | 7.8599 |
| online_best_lambda | 7.9824 | 7.9494 | 7.8844 |
| full_finetuning | 8.0015 | 7.9687 | 7.8066 |
| target_only | 13.5907 | 13.0427 | 12.4014 |
| seasonal_naive | 11.1454 | 11.1454 | 11.1454 |
| frozen_source | 8.2994 | 8.2708 | 8.3225 |
| block7 | 7.9959 | 7.9982 | 7.8667 |
| block28 | 7.9491 | 7.9360 | 7.8585 |
| source_error | 7.9389 | 7.9292 | 7.8396 |
| uncertainty | 7.9633 | 7.9604 | 7.8692 |
| drift | 7.9480 | 7.9358 | 7.8435 |
| parameter_retention | 8.0015 | 7.9698 | 7.8249 |
| no_source | 13.8834 | 13.1364 | 12.4202 |

| Days | Main RMSE | Target-only RMSE | Main WAPE | Target-only WAPE | Source-error WAPE |
| --- | ---: | ---: | ---: | ---: | ---: |
| 7 | 11.3153 | 17.4006 | 51.56% | 86.06% | 50.50% |
| 14 | 11.3449 | 16.7526 | 52.29% | 84.33% | 50.99% |
| 28 | 11.2006 | 16.0114 | 51.43% | 78.65% | 50.46% |

Main improves over Target-only by 5.540/5.000/4.486 kWh at 7/14/28 days, with station-level NTR 0/3. Source-error, Fixed and Drift have lower point MAE than Main at each of the three stations and each budget. Online best and full fine-tuning also have lower namespace mean MAE at all three budgets. The reported gains therefore do not isolate a benefit of confidence-based selection.

The primary Hùng Transfer Gain is a ratio of station-first means: 40.76%/38.34%/36.17%. The mean of station-specific percentages is a different estimand: 38.92%/36.91%/33.05%. Station 2579 contributes approximately 83–85% of the absolute gain sum. These quantities must be named explicitly rather than interchanged.

The locked station-only bootstrap has three units. A post hoc 5,000-draw station plus 14-scored-day-block sensitivity reports Main-versus-Target-only gain intervals [0.939,13.632], [0.838,11.999], [0.534,11.032] kWh. These remain descriptive: one missing day at station 2118 is crossed by some ordered-scored-day blocks, repeated budgets are dependent and no population-wide confidence claim follows. All 120 unscored job-origins correspond to the same calendar day at station 2118 across methods/seeds/budgets; no method receives an easier scored-day set within a matched cell.

## 5. Switching evidence and measured cost

A switch count is not an accuracy improvement. The primary analysis retains the following Adaptive decision inventory across all three budgets and seeds, including unscored targets:

| Namespace | Switches | Decision opportunities | Insufficient-evidence boundaries |
| --- | ---: | ---: | ---: |
| urbanev-SZH | 232 | 1620 | 315 |
| charged-AMS | 101 | 540 | 0 |
| charged-JHB | 89 | 540 | 0 |
| charged-LOA | 92 | 540 | 0 |
| charged-MEL | 75 | 540 | 0 |
| charged-SPO | 94 | 540 | 0 |
| charged-SZH | 86 | 540 | 0 |

Hùng's Final event inventory records 1,863 decisions and 313 switches across 297 controller jobs; Main has 24 switches out of 162 decisions. These counts do not provide paired old-policy forecast errors. Separately, its Development Main old-policy audit has 32 switches, 28 paired-evaluable: the old policy has lower next-block observed MAE in 19/28, with four unevaluable switches. That retrospective comparison is not proof the decision was wrong when made and cannot be relabeled as a Final result. It is adverse evidence against asserting that switching reliably improves the next block.

Hùng reports 4,329.8 seconds of saved replay stages and 8,238.4 seconds across available stage-duration fields; 54 duration fields remain missing (27 Drift references and 27 Target-only initializations). Primary per-run component/update/audit accounting also omits or overlaps setup, source reuse, publication and lost original D compute. Neither track supports a complete matched end-to-end cost ratio, billable cost or speedup claim. More work, switches or tests are not evidence of a better forecasting method.

## 6. What the newer Hùng audits resolve and what remains open

| Item | New evidence actually supplied | Current synthesis disposition |
| --- | --- | --- |
| Block7 historical contrast | 78 initial Source/Target payloads; pre-resume imports; terminal journals/checkpoints; full ordered event and label trace; 11 executed source pins and runtime identities. Intended block size is 7 versus 14 days. | The old missing-journal request is superseded by the supplied full-trace evidence. Different commits or checkpoint file hashes alone are not a reason for 69 replays. Non-author byte/trace review still needs an explicit comparison-fairness decision; this synthesis does not claim one. |
| Trained forecast head | One real Development checkpoint can be embedded into the wider Qyroven head: initial max difference 1.1921e-7 normalized units; after one fresh Adam step 0.05561. | Treat executed heads as distinct trained implementations. Initial function matching does not establish optimizer/update or resume parity. No Final may be relabeled to the other head. |
| Bootstrap/controller | Hùng code reproduces 414/414 saved Development decisions. At 168 eligible boundaries, fixed Hùng draws plus Qyroven quantile change 3 decisions; full Qyroven RNG/quantile changes 8. | Decision-rule sensitivity is real at these saved scores. It is not a Qyroven policy replay or an accuracy effect. A common contract is required before any claimed matched implementation replication. |
| CHARGED lineage | Same LOA textual run ID has different matrix/trajectory/errors across PR #67 and the physically bound primary PR #52 archive. | Keep PR #67 supplementary until its own run/archive/code/config/Source/executor mapping is authenticated. The primary accepted CHARGED analyses are not automatically invalidated by a separate ambiguous proof. |
| Colab #39 | Reviewer-access folder and a 163-file peer verifier have been prepared. | Reviewer-owned readback and a scoped disposition are still not recorded in the current gate register. A shared link alone is not acceptance. |
| Wider Hùng cohort | Input schedules/prefixes and created forecast rows audited for all 373 Final-role IDs; 370 remain outside the 3-ID lock. | This is input readiness/accounting, not target-model execution or held-out score coverage. It does not authorize an extension or imply that all omitted IDs are trainable. |
| Tests and CI | Author populated-workspace validation reports 604 tests, one skip at 786390d; exact-head CI at 30ed8e7 was billing-blocked before either OS test job started. The new integrated-status report records a fresh clone at 207255b: 604 tests, **2 failures, 18 errors, 1 skip**; missing ignored Block7 manifests appear in the trace. Ruff was unavailable in that Python 3.13 environment. | Fresh-clone portability is unresolved. The complete failure set has not been isolated; neither all failures nor metric invalidity can be inferred from the missing-file example. Separate unavailable dependencies/runtime from genuine failing assertions and make routine tests independent of private artifacts. Earlier local success is not a clean-clone pass, CI PASS or peer approval. |

Sources: [full Block7 trace](https://github.com/HungLD9505/adaptive-retention-ev/blob/1b730c7f83d6d8dd57198219c2593004d0318f4e/docs/reports/hung-block7-full-trace-audit-20261030-v2.md), [head diagnostic](https://github.com/HungLD9505/adaptive-retention-ev/blob/1b730c7f83d6d8dd57198219c2593004d0318f4e/docs/reports/hung-q-head-embedding-audit-20261030-v1.md), [controller diagnostic](https://github.com/HungLD9505/adaptive-retention-ev/blob/1b730c7f83d6d8dd57198219c2593004d0318f4e/docs/reports/hung-q-controller-decision-sensitivity-20261030-v1.md), [validation](https://github.com/HungLD9505/adaptive-retention-ev/blob/1b730c7f83d6d8dd57198219c2593004d0318f4e/docs/reports/hung-e2e-validation-20261030-v16.md), [acceptance register](https://github.com/HungLD9505/adaptive-retention-ev/blob/1b730c7f83d6d8dd57198219c2593004d0318f4e/docs/reports/hung-e2e-gate-register-20261030-v70.md).

## 7. Research claims the combined evidence can support

| Research question or proposed claim | Evidence-based answer | Wording for the report |
| --- | --- | --- |
| Can Source-informed adaptation help limited-history EV forecasting? | Favorable within-track results in many selected settings; primary AMS is strongly adverse; Hùng's result is confined to three stations. | Source-informed adaptation can improve forecasting under some limited-history conditions, with material heterogeneity and negative transfer. |
| Does the confidence controller add forecasting accuracy beyond Fixed or online best? | Primary Fixed: 9 lower versus 12 higher point-MAE panels; online best: 11 versus 10; all defined comparator intervals span zero. Hùng Main is above both comparators on all three budget means. | An incremental accuracy benefit of confidence-based switching is not established in these frozen experiments. |
| Does not finding a difference prove equivalence? | No equivalence margin/design is supplied; intervals spanning zero do not prove equality. | Results are inconclusive about small effects, rather than equivalent. |
| Does confidence prevent harmful switches or negative transfer? | Next-block Development audit often favors keeping the old policy; primary AMS retains 50% NTR. Selection LCB concerns past paired blocks under assumptions, not a guaranteed future block. | The controller supplies an explicit evidence-based decision rule; a future-error safety guarantee is not established. |
| Is the approach novel, SOTA, generally robust or efficient? | No complete external reproduction, novelty review, generalization design or matched end-to-end cost evidence is established by these outputs. | Present the method and bounded empirical evaluation; do not assert these properties as demonstrated. |
| Can two implementations be pooled as one experiment? | Different heads, optimization/controller details, seeds, Source states and targets. | Report two distinct implementation tracks and their internal contrasts; no pooled effect or direct developer ranking. |

**Supported contribution framing:** an explicit paired-comparison retention-selection mechanism, a causal prequential evaluation and reproducible multi-baseline evidence showing when transfer helps and where adaptive selection adds little or fails. The empirical contribution is the measured boundary of usefulness, not an unobserved accuracy victory. Engineering correctness and reproducibility support trust in the evaluation, not method superiority.

A useful central manuscript statement is: "Across the frozen selected cohorts, transfer-based adaptation often improved on training from scratch, but confidence-guided retention did not establish a consistent advantage over fixed retention or simple online selection. Adverse domains and retrospective switching outcomes reveal limits of using past paired improvement to anticipate future retention benefit." This is a synthesis of the executed internal comparisons, not a new confirmatory hypothesis.

## 8. Reporting and repository handoff requirements

The manuscript can be drafted now. Its Results must separate Development from Final, primary seven-namespace results from Hùng's three-station implementation, point estimates from exploratory uncertainty, and mathematical selection rules from empirical future-block behavior. Include full 14-method MAE/RMSE panels, Hùng WAPE with its station-first definition, NTR denominators, missing data, initialization/online/context analyses and the recorded cost limitations. Keep AMS and all null/negative outcomes visible.

Before calling the combined work independently accepted or submission-ready, the remaining concrete review work is:

1. Review the supplied Block7 bytes/trace and record an exact-head fairness disposition; request a replay only for an identified unmet condition and explicit run IDs.
2. Decide on correctness grounds whether both executed head/controller variants are admissible distinct implementations. If one canonical implementation is required for future work, specify it before any new Development calibration and new Final lock. Do not select it using favorable Final MAE.
3. Complete or explicitly scope out PR #67 physical lineage and Colab #39 peer readback. Distinguish a bounded Hùng deliverable from the originally assigned wider E2E acceptance scope.
4. Publish the current primary 810/810 handoff and correct stale README/PR/comparison prose while retaining original historical checkpoint files. Preserve and externally back up the final local analysis artifacts; the primary handoff does not establish a newly created external backup of every file.
5. Review the manuscript's method-to-Report-1 mapping, equations, bibliographic identity and novelty argument; related-work citations are not reproduced numerical baselines. Audit table transcription and define each estimand and interval.
6. Isolate and repair the recorded fresh-clone test failures before integration: supply independent fixtures or explicit optional-artifact skips with focused coverage, rather than depending on private ignored manifests. Use the documented environment, reconcile integration dependencies, test the chosen integrated code and obtain current non-author approval. CI billing exceptions permit stated execution scope; they are not successful CI or merge approval. Merge to dev only under the repository workflow; main promotion and issue closure remain separate.

No additional training is needed merely to prepare an honest manuscript from the current evidence. If a verified correctness defect invalidates a result, identify exactly the affected scope and version a repair/rerun. If the research goal remains a positive controller-superiority claim, it is currently unmet: any method change or new empirical test must be a new, preregistered/approved Development-and-evaluation iteration with an evaluation set whose independence is defensible after the present Final has been inspected. Do not keep tuning against these Final outcomes.

## 9. Verification performed for this synthesis

- Verified 54 local primary artifact entries against the completed handoff manifest, plus its report/manifest hashes and exact canonical indices 0–809. Recomputed 294 primary macro MAE and 294 macro RMSE values from station summaries; maximum arithmetic difference 0 kWh.
- Verified four Hùng analysis table hashes and three WAPE table hashes at the pinned Git head. Reaggregated all 360 tracked score rows into 42 variant/budget groups, matched published point estimates, checked 666 paired rows and 78 comparison rows. These use the existing checkpoint-derived score source and do not constitute an additional provider checkpoint readback.
- Source hashes and full-precision numeric tables are retained in the machine-readable synthesis. No raw archives, labels, model states, accepted receipts, code, locks or scientific fixtures were modified. No GPU job or long training ran.
- README training/software suites and remote CI were not rerun for this documentation-only synthesis. Link/hash/count/arithmetic checks and git diff whitespace checks are its applicable validation; author test reports remain attributed to their exact source heads, including the newly disclosed failed fresh-clone run.
- No formal peer approval, GitHub review/comment, merge, issue closure, new automation, spending or message to Hùng was performed by this synthesis.
