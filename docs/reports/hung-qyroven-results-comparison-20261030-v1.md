# AIP491_G10 — Evidence-bound comparison of Hùng and Qyroven results (2026-10-30)

**Status:** DRAFT — scientific comparison / review aid, **not** an independently accepted Final Report. This file reports the pinned results available in the two authors' review branches. It does not modify or re-run experiments. **Lower MAE/RMSE is better.**

## 1. Provenance and scope

- **Hùng:** [PR #72](https://github.com/HungLD9505/adaptive-retention-ev/pull/72), review head `ce1af6f0e78981b6f4cc787953fdf69122c02dda`; [bounded Final research report v29](https://github.com/HungLD9505/adaptive-retention-ev/blob/776d2c82ffb376d48295cbee46ab97d44681e778/docs/reports/hung-e2e-research-report-draft-20261030-v29.md) and [Final analysis tables](https://github.com/HungLD9505/adaptive-retention-ev/tree/776d2c82ffb376d48295cbee46ab97d44681e778/docs/reports/hung-final-analysis-20261029-v1). Final lock `e5e8fe1cb5636e508b3edbcedbbd00a72d9d8230041bf383eeba3d1133883e5e`; execution code `929480bfb123aaecab2cb9178f0e9088fb4d6593`.
- **Qyroven (Nguyễn Mạnh Quyền):** [PR #52](https://github.com/HungLD9505/adaptive-retention-ev/pull/52), review head `377723f5d55a91cde6229807300429365c764117`; [complete Development handoff](https://github.com/HungLD9505/adaptive-retention-ev/blob/9e96770718c41b5d873cc88128cef5e959a80eea/docs/reports/issue23-development-handoff.md); [partial Final terminal checkpoint](https://github.com/HungLD9505/adaptive-retention-ev/blob/377723f5d55a91cde6229807300429365c764117/docs/reports/issue23-final-stop-checkpoint-20261028.json).
- These two PRs are **draft, separate implementations and review tracks**. No reviewer acceptance, merged scientific result, or benchmark parity is inferred from their presence on GitHub. The figures below are snapshots, not a universal claim of the latest provider status.

## 2. Execution and validation comparison

| Dimension | Hùng | Qyroven | Interpretation |
| --- | --- | --- | --- |
| Development execution | **782 unique new jobs** (6 pilot + 216 local + 560 Kaggle); analytical matrix **851 runs** includes 69 historical Main anchors | **231 whole units × 14 variants = 3,234 selected method cells**, spanning UrbanEV plus six CHARGED cities | Jobs, whole units, selected cells and analytical rows are **different denominators**, not training-fit counts |
| Development scored coverage | 444/851 runs scored; 407 null; 816 paired cells valid, 748 blocked | 3,234 selected method cells; UrbanEV has 462 null metric cells; six CHARGED city collections report no null metric cells | Different datasets, cohort intersection and label availability; no direct completion-rate ranking |
| Source scope | 9 Source budget/seed strata in matched Hùng plan | 21 identified own-city/primary Source trajectories | Distinct Source identities, training budgets and potential transfer effects |
| Development budgets/seeds | 7/14/28 days; seeds **7, 11, 19** | 7/14/28 days; seeds **42, 43, 44** | Seed sets do not match |
| Final scope | **360/360 physical jobs**, three locked UrbanEV/SZH stations; 32,400 issued and 32,280 scored daily origins, 120 unscored | At last pinned terminal checkpoint **170/810 accepted whole units**, 2,380/11,340 selected method cells; execution safely stopped | Hùng's bounded Final is complete **within its lock**; Qyroven's larger frozen Final was incomplete in the cited checkpoint |
| Hùng Final integrity | Exact Kaggle saved run completed; external independent CPU archive SHA/CRC/member/job-map readback for 360 jobs; **0/360 full archives downloaded for local byte audit** | Last checkpoint reports per-unit native/content acceptance with a local canonical metadata audit | Validation tiers are different; do not call either full scientific acceptance |
| CI / peer review | Local test and audit evidence; PR review gates still open; account billing may prevent latest-head CI jobs | Development handoff ready for peer review; PR still draft; same billing limitation reported | Test success is not scientific peer acceptance |

The Hùng Final covers **three** selected stations, not 370 other Final-role UrbanEV IDs or the six CHARGED cities. The Qyroven Development handoff also warns about nonrandom sampling, mixed runtime environments, sparse labels, migrating/replayed artifacts and possible SZH overlap. These restrictions remain material.

## 3. Descriptive UrbanEV errors — **not a fair head-to-head benchmark**

Hùng numbers are **held-out bounded Final** on three selected stations; Qyroven numbers are **Development** on his UrbanEV cohort. They use different station/seed/evaluation populations. Equal metric units do **not** make absolute MAE values directly comparable.

| History budget | Hùng Final Main MAE (kWh) | Qyroven Dev Adaptive MAE (kWh) | Qyroven Dev Fixed MAE (kWh) |
| --- | ---: | ---: | ---: |
| 7 d | 8.051 | 4.8420 | 4.8081 |
| 14 d | 8.042 | 5.0988 | 5.0570 |
| 28 d | 7.916 | 5.5244 | 5.4998 |

**Prohibited inference:** “Qyroven's model is better because its MAE is smaller.” A valid model-to-model comparison requires the same target stations, input/label hashes, origin windows, budgets, seeds (or controlled randomization), Source conditions, methods, metric aggregation and comparable compute/update conditions.

## 4. Within-implementation comparison: Adaptive/Main versus Fixed

Here a **positive** difference means the adaptive controller's MAE is **worse** (Adaptive/Main MAE minus Fixed MAE). Each column is an **internal** contrast in its own experiment, not a cross-implementation effect size.

| History budget | Hùng Final Main − Fixed MAE (kWh) | Qyroven UrbanEV Dev Adaptive − Fixed MAE (kWh) |
| --- | ---: | ---: |
| 7 d | **+0.090** (8.051 − 7.961) | **+0.0339** (4.8420 − 4.8081) |
| 14 d | **+0.090** (8.042 − 7.952) | **+0.0418** (5.0988 − 5.0570) |
| 28 d | **+0.056** (7.916 − 7.860) | **+0.0246** (5.5244 − 5.4998) |

**Shared observation:** Fixed Retention has lower mean MAE than Adaptive/Main in all three reported UrbanEV budgets for these separate evaluations. The differences are modest; neither set establishes superiority, equivalence, or causation without sufficient independent comparisons.

Qyroven's CHARGED Development has heterogeneous directions. MEL's Adaptive MAE is lower than Fixed at 7/14/28 d, while AMS is higher; the Development report says all exploratory Adaptive-minus-Fixed intervals cross zero. Do **not** turn this into a universal “adaptive fails” conclusion.

## 5. Hùng's held-out bounded Final: transfer helps, adaptive advantage not established

| Budget | Main MAE/RMSE (kWh) | Target-only MAE/RMSE (kWh) | Paired absolute MAE gain (kWh) | Reported Transfer Gain | NTR |
| --- | ---: | ---: | ---: | ---: | ---: |
| 7 d | 8.051 / 11.315 | 13.591 / 17.401 | +5.540 | 40.8% | 0/3 |
| 14 d | 8.042 / 11.345 | 13.043 / 16.753 | +5.000 | 38.3% | 0/3 |
| 28 d | 7.916 / 11.201 | 12.401 / 16.011 | +4.486 | 36.2% | 0/3 |

The positive transfer gains are **bounded three-station observations**, not evidence for the whole UrbanEV population. One station (2579) contributes approximately 83–85% of the gain sum by budget; a station-sign diagnostic for three positive stations is one-sided 0.125 per budget and is not a prespecified confirmatory test. A post hoc 14-day temporal-block bootstrap gives descriptive intervals [0.939,13.632], [0.838,11.999] and [0.534,11.032] kWh, respectively; these do not prove general superiority.

The **Main controller is not the lowest-MAE method in this Final**. The Hùng report gives, respectively for 7/14/28 d:

| Comparator | 7 d MAE | 14 d MAE | 28 d MAE |
| --- | ---: | ---: | ---: |
| Main confidence controller | 8.051 | 8.042 | 7.916 |
| Fixed retention | 7.961 | 7.952 | 7.860 |
| Full fine-tuning | 8.001 | 7.969 | 7.807 |
| Source-error controller | **7.939** | **7.929** | **7.840** |
| Online best-λ / without confidence | 7.982 | 7.949 | 7.884 |
| Target-only | 13.591 | 13.043 | 12.401 |
| No Source initialization | 13.883 | 13.136 | 12.420 |

No-Source initialization has substantially worse MAE than Main; removing the confidence mechanism (online best-λ) or using Fixed can slightly improve MAE. Thus **the evidence presently supports a benefit from Source initialization in this selected case, but not an incremental forecasting-accuracy benefit from the proposed confidence controller**.

## 6. Training effort and reproducibility boundaries

- Hùng's 782 new jobs are **not** 782 unique Source pretrainings; the 851 analytical runs also contain reused historical Main identities. The report records 360 Final physical jobs, 297 controller jobs, 1,863 decisions and 313 switches across controller variants, including 24 Main switches. No claim of independently repeated Source fits is made for aliases or reused artifacts.
- Qyroven reports **21** Source trajectories contributing 140,970 optimizer steps; selected target reports record 507,060 candidate, 30,874 audit and 7,344 initial adaptation optimizer steps, plus 21,881.04 seconds of selected target process spans. These are recorded overlapping process spans and **not** total GPU wall-clock or billable cost.
- Hùng's saved legacy run costs lack some candidate/audit splits; the bounded Final reports 54 null replay-stage durations. **Do not rank training efficiency or model speed** until matched resource accounting is available.
- Hùng's PR marks provider saved-version IDs in compact proof JSONs as **not independently authenticated**, although archive member receipts and other byte/stage gates are documented. Review the precise authentication tier before treating “782 verified” as an unqualified independent provider-provenance claim.

## 7. Research interpretation and review actions

**What is supported:** Both separate results are compatible with Source initialization being useful under some EV cold-start regimes; Hùng's held-out three-station Final has substantial paired gains relative to Target-only. Both UrbanEV comparisons show Fixed Retention competitive with or slightly better than Adaptive/Main.

**What is not supported:** A blanket claim that Adaptive Retention outperforms Fixed/online-best/proxy controllers, is SOTA, mitigates negative transfer broadly, or generalizes to unseen stations/cities. No conclusion that one developer's forecasting code outperforms the other's follows from the absolute MAEs above.

**Open acceptance gates:** Hùng Block7 historical equivalence or replay; Hùng–Qyroven head/bootstrap/runner trained-state parity; CHARGED supplementary physical executor/code/Source/artifact attribution and independence; Colab #39 reviewer readback; whether bounded 3-station Final meets the intended scientific scope; current PR approvals; and CI blocked by account billing. See [Hùng PR #72](https://github.com/HungLD9505/adaptive-retention-ev/pull/72) and [Qyroven PR #52](https://github.com/HungLD9505/adaptive-retention-ev/pull/52).

**Most important next experiment/design decision:** Define a **preapproved matched cohort and common protocol** to test the controller's incremental effect over Fixed Retention and online best-λ, subject to data/compute/Final lock rules. Do not post hoc tune or silently expand an already frozen Final.

### Bottom line

1. **Engineering delivery:** substantial, reproducible bounded technical evidence from both tracks.
2. **Transfer benefit:** encouraging on Hùng's small held-out cohort; broader generalization unverified.
3. **Adaptive controller contribution:** **not demonstrated** by current MAE results; Fixed and some simpler methods have slightly better mean MAE.
4. **Scientific readiness:** draft, pending independent scientific decisions and scope review. No claim of 100% research acceptance.
