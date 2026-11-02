# Issue23: where adaptive retention helps, and what the existing evidence supports

31 October 2026. Follow-up to [the joint synthesis](issue23-joint-evidence-synthesis-20261030.md), for [Issue #23](https://github.com/HungLD9505/adaptive-retention-ev/issues/23). **Post hoc descriptive analysis for manuscript drafting; no new training, tuning, cohort selection or confirmatory test.**

The research question remains the one in Report 1: when should a target model preserve Source knowledge, and when should it relax that constraint? It does not require a positive controller-superiority result. The strongest current empirical answer is that Source initialization, ongoing retention and confidence-guided selection have different effects. Transfer is often useful; adaptive selection has localized point-estimate gains but no established consistent advantage over Fixed or online best-lambda.

## 1. Method reference and scope

The supplied `/Users/quyenmanh/Downloads/adaptive_retention_report_1.pdf` has SHA256 `cafc1db09a7fda4e196808a96cedf1b18098a4e7ff859d272402e049ebd65bbc`. Its RQ1 concerns retention effects and the adequacy of proxy signals; RQ2 concerns confidence-guided selection versus Fixed, online selection and proxy controllers; RQ3 concerns stability across stations/history/context and cost. Sections 6.2 and 9 explicitly distinguish past-block candidate improvement from future benefit and require narrowing the claim when confidence does not help. Pages 4, 6 and 7 were also rendered for visual inspection.

This analysis reads the seven completed primary Final summaries, run tables and derived daily errors pinned by the completed handoff. It does not integrate the scientific implementation or repeat checkpoint/forecast/raw-data validation. The primary scope remains 810 whole units / 11,340 method cells, 90 selected entities, 7/14/28 initial-history days, paired seeds 42/43/44, and a 90-day online replay. Target data continue to accumulate after deployment; 7/14/28 days are initial history, not a cap on all subsequent learning. UrbanEV has 29 scored stations and one retained unscored station, 2193; CHARGED has ten selected sites per namespace.

Hùng's bounded three-station Final remains a separate implementation/cohort, as documented in the prior synthesis. It is supporting internal evidence, not pooled observations or a numerical replication of the primary implementation. This report makes no newer GitHub-head claim.

## 2. Estimands and safeguards

- Average paired seeds within station, then average stations equally within each namespace and budget. Do not pool cities or treat seeds, days or repeated budgets as independent station samples.
- The main contrast is `Adaptive MAE - comparator MAE` in original kWh. Relative contrast is 100 times that difference divided by the comparator's namespace mean MAE. Negative values favor Adaptive. A median of station-specific percentages is a different estimand and is retained separately.
- Report station direction counts alongside macro effects. Exact-sign counts include arbitrarily small differences and are descriptive, not tests or practical-benefit thresholds.
- Leave-one-station-out (LOO) diagnostics recompute the contrast for every possible single omission. They measure concentration; they do not authorize dropping any station or replacing the full-cohort result. A preserved sign is not significance or population robustness.
- Seed diagnostics retain all three fixed seeds. No favorable-seed selection is performed, and shared Source/training/controller randomness prevents attributing a seed difference exclusively to Source quality.
- Keep the original exploratory bootstrap intervals unchanged: station/time pairing, common calendar, seven-day blocks, 2,000 resamples, no simultaneous-comparison correction. All 18 finite Adaptive-Fixed intervals and all 18 finite Adaptive-online-best intervals include zero. The three UrbanEV intervals remain null; no undefined replicate is removed.
- The phase and context definitions already existed in the frozen analyzer. New concentration, seed-direction and switch-sign summaries are post hoc descriptions. None supplies a validated rule for choosing a method on a new station.

Full numerical results, comparator intervals, station contrasts, seed effects, all budgets/phases/contexts, proxy summaries and source hashes are in [the companion JSON](issue23-retention-posthoc-20261031-v1.json).

## 3. Where does Adaptive improve on Fixed?

Each three-value sequence is in 7/14/28-day order. Percentages are changes in MAE; negative is favorable.

| Namespace | Adaptive vs Fixed (%) | Stations with lower MAE | Adaptive vs online best (%) | Interpretation |
| --- | --- | --- | --- | --- |
| UrbanEV/SZH | +0.76 / +0.95 / +1.08 | 10/29 / 11/29 / 13/29 | -0.17 / +1.07 / +0.11 | Useful transfer, but the Adaptive macro estimate is worse than Fixed at every history. |
| AMS | +0.12 / +0.06 / +0.08 | 4/10 / 6/10 / 5/10 | +0.06 / -0.05 / -0.01 | Tiny controller differences coexist with a much larger transfer failure. |
| JHB | +3.63 / +2.85 / +4.97 | 4/10 / 4/10 / 3/10 | +4.03 / +0.51 / +4.66 | Adaptive is worse than both controls; Frozen Source has the lowest point MAE among all 14 methods. |
| LOA | +0.40 / +0.73 / +0.04 | 4/10 / 4/10 / 7/10 | -0.02 / +0.32 / -0.24 | Small, mixed differences; no stable Adaptive advantage. |
| MEL | -1.31 / -2.36 / -2.14 | 6/10 / 6/10 / 6/10 | +0.06 / -0.52 / -0.52 | Favorable macro contrast against Fixed, but concentrated and partly seed/phase sensitive. |
| SPO | -2.55 / -2.41 / -2.85 | 4/10 / 2/10 / 3/10 | +0.98 / +0.51 / -0.35 | Macro improvement is not a majority-station improvement; online best is better at 7/14 days. |
| CHARGED/SZH | -1.30 / -1.67 / -1.71 | 6/10 / 8/10 / 3/10 | -2.83 / -2.24 / -2.63 | Most persistent macro point-estimate signal against both selectors; seed sensitivity and stronger alternatives remain. |

Adaptive has lower macro point MAE than Fixed in nine panels and higher in twelve; these are repeated budget panels, not 21 independent trials. Adaptive has the lowest point MAE among all 14 methods only at SPO/28 days. That one result is a descriptive rank, not a selected operating policy or significance claim.

### Concentration changes the interpretation of the favorable domains

- **MEL:** site 34 contributes about 103%, 102% and 89% of the signed net Adaptive-Fixed reduction. Contributions can exceed 100% because other sites offset the gain. Omitting site 34 reverses the aggregate sign at 7/14 days: the remaining-site mean gaps are +0.0224 and +0.0344 kWh. At 28 days, all single-omission means still favor Adaptive; the weakest is -0.1424 kWh. Seed 42 favors Fixed at 14/28 days, although the three-seed average favors Adaptive.
- **SPO:** site 28 contributes about 188%, 173% and 133% of the signed net reduction. Omitting that site gives +0.0501 / +0.0389 / +0.0213 kWh, favoring Fixed at all histories. Median station gaps also favor Fixed at all histories (+0.00052 / +0.00207 / +0.00090 kWh). Conversely, every seed's namespace average favors Adaptive against Fixed. Seed consistency therefore does not imply broad station consistency.
- **CHARGED/SZH:** site 88 accounts for about 67-69% of the signed net reduction, but every single-station omission preserves a favorable aggregate direction at every history. The weakest LOO gaps are -0.4316 / -0.5214 / -0.5658 kWh. However, seed 42 favors Fixed at all histories, the median station gap favors Fixed at 28 days, Full Fine-tuning has lower MAE at all histories, and Seasonal Naive has the lowest MAE among all methods. This is a conditional selector contrast, not evidence of the best forecasting approach or independent geographical validation from UrbanEV.

**Correction to the earlier visual interpretation:** MEL/SPO are favorable aggregate cases, not evidence that Adaptive broadly helps their stations. Their concentration must accompany any favorable headline.

## 4. When is Source useful, and what does retention add?

Report 1 separates Source initialization from the ongoing representation constraint. Setting lambda to zero removes that constraint; it does not erase Source initialization or rewind the learned trajectory. Adaptive-Target-only differences therefore cannot isolate the value of the confidence test, or even the representation penalty alone.

| Observed pattern | Existing result | Defensible interpretation |
| --- | --- | --- |
| Source can help even without target adaptation | JHB Frozen Source MAE is 0.9623 / 0.9645 / 0.8670, below Adaptive 1.3685 / 1.3604 / 1.3560 and all other methods. | Target updates are not automatically beneficial; the evaluated adaptation procedures can degrade a useful Source model. This is not a proof that a particular lambda is universally optimal. |
| Source initialization plus target learning can help | UrbanEV Adaptive improves on Target-only by roughly 40%, yet Fixed is lower at every history. LOA also has substantial transfer gains with little selector separation. | Much of the observed benefit is shared with simpler Source-informed baselines; do not attribute it to Adaptive selection. |
| Relaxing ongoing retention can be competitive or better | CHARGED/SZH Full Fine-tuning MAE is 88.8440 / 88.5427 / 88.1054 versus Adaptive 90.6306 / 89.3300 / 89.3310. | Within this locked recipe, Source initialization followed by unconstrained adaptation is a stronger point-MAE alternative than Adaptive. |
| Source-informed learning can fail badly | AMS Adaptive is 132.5-140.9% worse than Target-only; station-level negative transfer is 5/10 at every history. Full Fine-tuning and Frozen Source are also poor in the aggregate; Seasonal Naive is much better. | Reducing the current representation penalty alone is not demonstrated to repair Source-related failure. Source suitability/initialization/optimization are plausible contributors, not isolated causal diagnoses. |

The AMS 7-day seed means make the instability concrete. Adaptive MAE is 8.9838 / 0.5001 / 8.9838 kWh for seeds 42/43/44; Fixed is 8.9838 / 0.4772 / 8.9838; Target-only is 2.6729 / 2.6409 / 2.3724. The favorable seed is retained alongside both adverse seeds. These current Final scores corroborate strong seed sensitivity; this analysis did not inspect all raw prediction values and does not newly diagnose a zero-output collapse.

Adaptive is below Full Fine-tuning in 17/21 primary macro panels; six finite frozen intervals favor Adaptive, twelve cross zero and three are null. This supports examining retention-based learning, but does not isolate confidence: Fixed, proxy rules, different block sizes and the retained training trajectory also matter. Representation retention is not established as universally superior to parameter retention. Likewise, block7/block28 outperform Adaptive in the MEL point rankings, so the chosen block timescale is a material alternative explanation.

## 5. When during the replay does the advantage appear?

The complete companion table includes all histories. At 14-day initial history, the Adaptive-Fixed relative differences are:

| Namespace | Days 1-30 | Days 31-60 | Days 61-90 |
| --- | ---: | ---: | ---: |
| UrbanEV/SZH | +1.10% | +0.73% | +0.87% |
| AMS | +0.12% | +0.05% | approximately 0% |
| JHB | -0.31% | +14.70% | -3.80% |
| LOA | +0.59% | +1.48% | +0.18% |
| MEL | -7.76% | +0.67% | +0.37% |
| SPO | -4.12% | -3.14% | +0.48% |
| CHARGED/SZH | -0.60% | -3.98% | -1.28% |

MEL's favorable full-stream mean is largely an early-replay phenomenon; it is not sustained improvement throughout online adaptation. SPO/28 days is more temporally consistent against Fixed (-3.79%, -4.15%, -0.47%), but the station-concentration finding still applies. JHB's sign changes show why a single terminal average cannot identify a reliable future switching rule. These are comparisons to Fixed, not event-aligned causal effects of individual switches. No arbitrary drift date or recovery time is introduced.

Context effects also resist a universal rule. At 14 days, MEL favors Adaptive in dense prefixes (-2.58%, six sites) but not sparse prefixes (+0.99%, four sites); SPO favors Adaptive in sparse prefixes (-3.05%, four sites) but not dense prefixes (+3.15%, six sites). These use the existing Development-frozen density thresholds. They describe different selected sites and do not isolate density causally. Do not derive a new context controller or favorable subgroup cutoff from these Final outcomes.

## 6. What does the confidence mechanism actually demonstrate?

### Fewer switches, without an accuracy or efficiency guarantee

All namespace totals include all three histories and all three seeds, including declared unscored entities for the decision inventory.

| Namespace | Adaptive switches | Online best switches | Adaptive retention increases / decreases |
| --- | ---: | ---: | --- |
| UrbanEV/SZH | 232 | 780 | 138 / 94 |
| AMS | 101 | 180 | 22 / 79 |
| JHB | 89 | 250 | 43 / 46 |
| LOA | 92 | 341 | 50 / 42 |
| MEL | 75 | 317 | 45 / 30 |
| SPO | 94 | 313 | 39 / 55 |
| CHARGED/SZH | 86 | 335 | 52 / 34 |

Adaptive switches less than online best in every namespace and every budget. This is evidence of a more conservative decision policy in these saved trajectories. It does not show that the retained decisions are more accurate, that fewer switches are intrinsically desirable, or that total compute is lower. Both increases and decreases occur, consistent with bidirectional retention selection rather than a monotone decay schedule. UrbanEV has 315 insufficient-evidence boundaries; their retention behavior is part of the recorded algorithm, not a safety outcome.

### Existing Final old-policy audits give a mixed outcome

The frozen analyzer exports original-kWh new-minus-old next-block audit means. This is a local retrospective comparison against continuing the old policy from that switch checkpoint, not a complete Fixed trajectory and not a test of the decision using only then-available information. Only exported, finite paired audits enter these sign counts; no missing audit is filled. Exact signs include numerical-scale differences and must not be called the locked rate of practically harmful switches. A locked harm threshold is not supplied by the frozen analysis profile.

| Namespace | Finite paired audit records | New-policy lower MAE | Old-policy lower MAE | Explicit null audit records |
| --- | ---: | ---: | ---: | ---: |
| UrbanEV/SZH | 197 | 124 | 73 | 24 |
| AMS | 100 | 97 | 3 | 0 |
| JHB | 77 | 59 | 18 | 0 |
| LOA | 77 | 39 | 38 | 0 |
| MEL | 61 | 29 | 32 | 0 |
| SPO | 78 | 47 | 31 | 0 |
| CHARGED/SZH | 77 | 27 | 50 | 0 |

Audit records are clustered within runs/sites/seeds and are not independent trials. Their finite counts are not the complete switch inventory. In AMS, median signed audit gaps are about -3e-11 to -6e-11 kWh by budget, so the large count of favorable signs is especially unsuitable as a practical-success headline. MEL/14 days has a median +0.1007 kWh, and CHARGED/SZH has positive median audit gaps at each history despite its favorable Adaptive-Fixed macro contrast. A local switch comparison and a full-path method comparison answer different questions.

The Final audit here is distinct from Hùng's previously reported Development old-policy audit (19/28 paired switches favoring the old policy); do not relabel that Development result as Final. These combined observations do not support a future-block safety guarantee.

### Proxy signals do not directly measure retention benefit

The saved proxy analysis correlates each available signal with same-block zero-minus-low/high candidate MAE on that proxy controller's own path. It is not next-block predictive validation, a shared-path comparison of proxy accuracy, or a confidence-controller causal test. Null/constant cases require all three seeds defined and remain null.

For 14-day history, the mean station correlations with **zero-minus-high** retention benefit are:

| Namespace | Source error | Uncertainty | Drift | Defined stations per signal / selected |
| --- | ---: | ---: | ---: | --- |
| UrbanEV/SZH | +0.030 | -0.022 | -0.068 | 27/30 |
| AMS | -0.144 | +0.519 | +0.068 | 6/10 |
| JHB | -0.021 | +0.382 | -0.161 | 5/10 |
| LOA | -0.269 | -0.217 | -0.161 | 9/10 |
| MEL | -0.048 | -0.016 | -0.074 | 9/10 |
| SPO | -0.102 | +0.138 | +0.050 | 6/10 |
| CHARGED/SZH | -0.322 | +0.069 | -0.036 | 6/10 |

Signs vary, magnitudes are often modest, and the short series/undefined coverage constrain interpretation. This supports the conceptual distinction made to the supervisor: high error, uncertainty or drift is not the same quantity as the relative benefit of retaining Source. It does not establish that direct confidence-guided comparison solves the prediction problem better.

## 7. What can be said about cost without new training?

Recorded main candidate-update steps are exactly three times Fixed in every namespace: 24,300 versus 8,100 per CHARGED namespace, and 56,079 versus 18,693 for UrbanEV, across all budgets/seeds. Adaptive and online best have equal main candidate-step counts; Adaptive has fewer recorded old-policy audit steps because it switches less. The audit branch is evaluation overhead, not part of the deployed controller's information. Source training and initial adaptation are separate costs.

These counters demonstrate real extra work relative to Fixed and isolate one equal-budget aspect of the online-best comparison. They are not FLOPs, complete training-time ratios, billable GPU ratios or end-to-end efficiency. Setup/export overlap, Source reuse, missing predecessor costs and lost unexported compute remain limitations. An efficiency advantage cannot be inferred from fewer switches.

## 8. Report-ready conclusions aligned with the supervisor discussion

**RQ1: answered descriptively, with useful boundaries.** Source-informed adaptation helps many selected limited-history settings, but neither Source usefulness nor the benefit of target adaptation is universal. JHB illustrates a strong Frozen Source; CHARGED/SZH favors relaxing the ongoing penalty relative to Adaptive; AMS shows a severe Source-informed failure that lambda selection does not repair. Proxy signals and retention benefit must be distinguished. No universal operational rule for a new unseen station has been validated.

**RQ2: positive superiority hypothesis not established.** Adaptive has localized average improvements against Fixed at MEL/SPO/CHARGED-SZH. MEL/SPO gains are concentrated; CHARGED-SZH's macro direction survives single-site omission but is seed sensitive and not best among all baselines. All finite Fixed/online-best intervals cross zero. Confidence reduces switching in the saved trajectories, but added accuracy and future-error safety are unproven. This is not an equivalence result.

**RQ3: meaningful heterogeneity is demonstrated; full efficiency remains unresolved.** Station, seed, phase and prefix context can change the apparent advantage. Three candidates incur additional updates relative to Fixed. Existing timing data do not support a complete end-to-end cost claim.

Suggested Results/Discussion wording:

> Across the frozen selected cohorts, Source-informed adaptation often improved forecasting relative to target-only training. The value of ongoing retention and target adaptation varied substantially by domain, station, initialization seed and online phase. Confidence-guided retention selection produced fewer switches than simple online selection and favorable aggregate accuracy contrasts in selected domains, but did not establish a consistent accuracy advantage over fixed retention or online best-lambda. Concentration diagnostics and retrospective old-policy audits further limit claims of broad station-level benefit or future-error protection.

Suggested contribution framing: **a GRU-based candidate retention controller and an empirical analysis of the conditions and limits of Source retention under limited target history**. A method can be implemented and evaluated without a positive superiority result. The evidence supports reporting the measured limits, not presenting engineering verification, a new domain/backbone or post hoc subgroup wins as proof of novelty. Novelty and external-baseline claims need their own literature/reproducibility review.

An appropriate message to the supervisor is: "We implemented the planned GRU and retention comparisons. Transfer helps in many selected cases, but confidence-guided adaptation does not consistently beat Fixed or simple online selection. We are reporting where retention helps, where it harms, and why conservative switching does not guarantee better future forecasts." This report does not send that message.

No new training is needed to write this bounded empirical report. If the project requires a demonstrated universal Adaptive accuracy win, the present evidence cannot supply it. That would require a separately designed and independently evaluated future study, not continued tuning or selective reporting on this inspected Final set.

## 9. Verification, reproducibility and remaining limits

Fresh SHA256 checks matched all seven summaries, seven run tables, seven derived metadata files and seven daily CSVs to the completed handoff/metadata pins. The original summaries/CSV bytes were not changed. All **942,102 scored daily rows** were read; per-cell means/counts reconciled against the run tables for all 11,214 scored method cells, with 126 explicit null UrbanEV cells retained. Station-first contrasts were independently recomputed from the summary station means. Maximum per-cell arithmetic difference is recorded per namespace in the companion JSON and is below 1e-9 kWh.

The read-only calculation script and full intermediate output are at `runs/issue23-posthoc-retention-20261031-v1/analyze_existing.py` and `posthoc-results.json` in the synthesis worktree. The compact tracked JSON records the script SHA256 and all 28 source identities, including absolute operational paths; those paths are not portable public data locations. The underlying primary handoff archive is still required to reproduce the analysis. No claim of a new external archive or independent raw checkpoint readback is made.

This follow-up used CPU-only arithmetic and PDF extraction/rendering. No model fit, GPU allocation, Source modification, lock/config change, bootstrap rerun, new hypothesis test, missing-label filling, worker message, merge or issue closure occurred. Scientific/software peer review and integration remain separate from the arithmetic checks. Full README model/software tests and CI were not run for this analysis/documentation-only change; no passing-CI claim is made.
