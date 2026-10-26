# Adaptive retention for cold-start EV charging demand forecasting

**Status (2026-10-26): evidence-backed draft for Issue #10.** This document separates the proposed method, implemented components, Development observations, and pending Final evidence. It is not a completed effectiveness claim. The method reference is [Report 1](../adaptive_retention_report_1.pdf); the [research flow](MASTER_RESEARCH_FLOW.md), [input acceptance policy](data/INPUT_ACCEPTANCE.md), and [sprint plan](SPRINT_PLAN.md) provide the implementation and acceptance context.

## Abstract

This study examines whether a controller that compares the observed forecast errors of concurrent retention levels can improve adaptation of a source-pretrained model to EV charging sites with limited initial history. The task uses the previous 24 hourly demand values to forecast the next 24 hours once per day, with initial target histories of 7, 14, or 28 days. UrbanEV is the primary published-data benchmark; six CHARGED city releases are supplementary, with Shenzhen reported separately because physical-location independence from UrbanEV has not been established. Development implementations and bounded diagnostic runs exist, but integrated peer acceptance, a locked Final evaluation, and complete CHARGED replication are pending. Consequently, this draft reports no final comparative conclusion.

## 1. Motivation and research questions

A newly deployed forecasting model may have little target-specific history. Source pretraining can provide an initialization, but retaining the source representation too strongly may obstruct adaptation, while relaxing it too early may discard useful structure. The project simulates this limited-history setting through chronological replay; it does not establish that sites in the published datasets had just opened.

The proposed contribution is a confidence-based decision over **observed differences between retention trajectories**, rather than a decision derived solely from source error, predictive uncertainty, or behavioral drift. This remains a candidate contribution. Online hyperparameter selection and adaptive transfer have precedents, so a new name, backbone, or EV domain alone does not establish novelty. [Report 1, §§1–3 and 9](../adaptive_retention_report_1.pdf) defines three questions:

1. How do retention levels affect forecasting error, and when do source-error, uncertainty, or drift proxies fail to reflect their relative benefit?
2. Does the confidence controller improve on fixed retention, mean-error online selection, and proxy controllers under matched budgets?
3. How stable are results across sites, initial-history budgets, and behavior contexts, and what computation and memory do they require?

Answers require matched Final forecasts, uncertainty analysis, and complete cost accounting. Development scores are for configuration selection and diagnostics.

## 2. Related work and contribution boundary

[Report 1, §3](../adaptive_retention_report_1.pdf) identifies online EV forecasting, continual time-series adaptation, online transfer, uncertainty-guided distillation, drift-aware updates, and online hyperparameter tuning as nearby work. Its bibliography lists Li et al., R-Tuning, BOTL, GUARD, PADRE, and Hyperon. A direct numerical comparison requires a faithful implementation or an explicitly labeled adaptation with compatible horizons and metrics; a project-built proxy controller is not a reproduction of those papers. Before the final literature chapter is accepted, verify each substantive comparison against its primary paper and record the exact task and implementation differences.

The scientific test here is narrower than a general claim that transfer learning helps: compare retention trajectories and their selection rules on the same forecast origins and labels. Full fine-tuning, fixed retention, and Simple Online Best-λ are particularly important controls. A negative or null result is a valid outcome and must be reported without selecting favorable seeds or sites afterward.

## 3. Data and permitted information

### 3.1 Sources and meaning of the target

UrbanEV supplies station-level hourly **estimated or derived charging energy**, not independently verified meter readings. CHARGED supplies provider-processed hourly demand for virtual sites formed from chargers. The six standard city namespaces are AMS, JHB, LOA, MEL, SPO, and SZH; they are separate experiments, not one pooled Source population. SZH has documented coordinate overlap with UrbanEV and cannot be presented as independent unseen-location validation. The [data flow](data/DATA_FLOW.md), [UrbanEV reference](data/URBANEV.md), [CHARGED reference](data/CHARGED.md), and [integration handoff](reports/data-integration.md) document the released inputs and limitations.

The DATA-v1-20261019 snapshot contains prepared inputs for each city and each 7/14/28-day budget. Its [release catalog](../data/releases/DATA-v1-20261019.json) supplies package sizes and SHA-256 fingerprints; a consumer must rehash each downloaded archive before using it. The input acceptance policy retains missing historical hours through a zero placeholder plus mask, distinguishes a valid zero from a missing hour, and never fills missing target labels. A forecast is issued only when the history gate permits it; scoring and updates require all 24 labels to have arrived. Requested, issued, and scored counts are different denominators.

The benchmark assumes the published bin clock and label availability at the exclusive horizon end. Actual arrival latency, upstream interpolation/imputation provenance, and physical-site disjointness remain unverified. Results must be called a **chronological benchmark on published data**, not a certified strict-online or causal evaluation.

### 3.2 Roles and replay

Source entities support predeployment pretraining; Development target entities select model and controller configuration; unseen Final target entities evaluate the frozen design. The reviewed input handoff uses ID-based splits and separate CHARGED city assignments. Source and Development may be inspected for tuning; Final target performance must not select a model, seed, threshold, exclusion, or reporting subgroup. Within the locked Final online stream, arrived labels may update the already specified algorithm.

Each eligible target receives exactly 7, 14, or 28 days of initial history. Once deployed in replay, its available history grows. At each daily origin the method first stores a forecast, then scores and updates only after a complete valid 24-hour label vector becomes available. Forecast scheduling cannot consult future label completeness. See [Report 1, §§4 and 7](../adaptive_retention_report_1.pdf) and the [input policy](data/INPUT_ACCEPTANCE.md).

## 4. Proposed model and adaptive-retention method

The initial backbone is a two-layer GRU with hidden size 64. A head combines its final latent representation with the known calendar for the next 24 hours and uses Softplus to produce 24 nonnegative predictions. Historical input includes demand, known calendar, and missingness. Weather or price would require proof of availability at the forecast origin and are outside the current input contract. The GRU is a supporting backbone, not the proposed novelty.

Source pretraining uses only the permitted predeployment Source population. The target model copies compatible encoder and head parameters. A separate Source reference encoder remains frozen, in evaluation mode, and without gradients. For each complete-label example, forecast loss is the mean absolute error over 24 normalized hourly targets. Retention loss averages the squared difference of target and Source latent components **after** division by the corresponding fixed Source-training latent standard deviation plus ε. With latent dimension 64, the total objective is forecast loss plus λ times retention loss. λ = 0 is Source-initialized full fine-tuning; it is not target-only training. [Report 1, §5](../adaptive_retention_report_1.pdf) contains the governing equations.

At the beginning of each block, three candidate learning processes with λ in `{0, λ_low, λ_high}` fork the same active model and optimizer state. They use matched normalization, data, update schedules, step budgets, and paired random streams. The active candidate is chosen before the block; all three predictions are stored before their labels. On each complete-label day, paired normalized MAE improvement is active error minus challenger error. A positive value favors the challenger. After at least `B_min` valid days, a one-sided day-block-bootstrap lower confidence bound must exceed δ to switch. Among qualifying challengers, the largest bound wins, followed by the predefined distance and fixed-order tie rules. Otherwise the **trained active state** continues. Any decision affects only future forecasts. [Report 1, §6](../adaptive_retention_report_1.pdf) defines the rule and its repeated-testing limits.

An isolated audit branch may continue the old policy after a switch for retrospective harmful-switch analysis. Its predictions cannot influence the live controller, and its cost is reported separately. Recovery time is meaningful only for an event with a defined onset and a threshold chosen on Development; absent that, report error trajectories rather than an invented recovery number.

## 5. Evaluation design and acceptance gates

The mandatory baselines are Seasonal Naive with fallback, Target-only GRU, Frozen Source, Full Fine-tuning, Fixed Retention, Simple Online Best-λ, and Source-error, Uncertainty, and Drift controllers. The five ablation categories are Without Confidence, Fixed λ, Parameter Retention, Different Block Size, and Without Source Initialization. Identical method/ablation runs may be reused but must not be counted as independent evidence. All compatible methods need the same cohort, origins, input scale, label gate, and matched evaluation unit. Online Best-λ must share the three-candidate update/checkpoint budget and change only its selection rule. [Report 1, §8](../adaptive_retention_report_1.pdf) and [Issue #22](https://github.com/HungLD9505/adaptive-retention-ev/issues/22) define this comparison scope.

Development chooses the finite configuration, proxy mapping, candidate levels, bootstrap settings, block-size sensitivity, inclusion rules, and at least three seeds. Before Final, an independent reviewer must approve immutable data/cohort/code/config identities and a feasible run matrix. The Final experiment then runs that exact specification without result-driven revision. A correctness change that affects locked results requires a recorded new lock and affected reruns; preserve the old evidence. [Issue #23](https://github.com/HungLD9505/adaptive-retention-ev/issues/23) tracks this gate.

The primary metric is original-unit MAE, with RMSE supplementary. Aggregate by site first; report coverage, distributions, and uncertainty that respects site/time dependence. Compare transfer gain and negative transfer rate with Target-only using a prespecified evaluation unit. Where Target-only MAE is zero, report an absolute difference instead of dividing by zero. Stratify by initial-history budget, site, time, and Development-defined sparse/dense context. Report switch paths, insufficient-evidence decisions, next-block audit outcomes, runtime, peak memory, inference and update steps for all three candidates, and audit overhead separately.

## 6. Evidence available on 2026-10-26

The accepted [data/input integration](reports/data-integration.md) documents technical processing and input readiness, including all six CHARGED city profiles. It does **not** establish model effectiveness or strict-online causality.

Hung's independent [Sprint 2 implementation handoff](https://github.com/HungLD9505/adaptive-retention-ev/pull/46) reports a real UrbanEV/SZH Development representative run on 25 October: 216/216 stages, 69 entity-budget-seed cells, 4,146 issued forecasts from 6,210 requested origins, and 2,322 scored days. Only 36/69 cells have MAE/RMSE; the other 33 remain null. The [assessment](https://github.com/HungLD9505/adaptive-retention-ev/blob/docs/39-report-consolidation/docs/reports/hung-39-assessment-handoff.md) distinguishes individual technical PASS from open cross-implementation review, integration, and Colab/Drive criteria. These are diagnostic observations, not a cohort-wide benefit estimate.

The independently authored [baseline PR #51](https://github.com/HungLD9505/adaptive-retention-ev/pull/51) and [Development evaluation PR #52](https://github.com/HungLD9505/adaptive-retention-ev/pull/52) contain additional real runs and artifact checks. Their reviews, full off-runtime restore, complete CHARGED replication, compute acceptance, and Final lock remain pending. In the reported matched UrbanEV Development collection, the selected Adaptive controller did not beat selected Fixed Retention on the conditional equal-budget MAE point estimates. This is a tuning observation on a small scored cohort, not a Final effect or population claim. Do not combine outcomes from different implementation/configuration families as if they were independent replications.

## 7. Final results, discussion, and conclusion — pending evidence

This section will be completed only from the independently approved #23 handoff. Required tables must identify each dataset/city, budget, method, seed, requested/issued/scored coverage, valid sites, MAE/RMSE, paired effects, uncertainty, and null or failed cells. Keep UrbanEV primary; show AMS/JHB/LOA/MEL/SPO supplementary results and SZH separately. Link the exact immutable lock, code SHA, input manifests, run IDs, forecast/event/checkpoint proofs, and cost artifacts used in each table.

Answer RQ1–RQ3 even if Adaptive Retention has no advantage. Discuss transfer, retention, controller selection, robustness, and compute cost separately. State limitations from upstream processing, clock/arrival assumptions, ID-based splits, physical overlap, small scored cohorts, and any incomplete experiment cells. No conclusion about superiority, novelty, independent external validation, or deployment safety is justified by the current Development evidence.

## Reproduction and evidence register

| Evidence | Current use | Acceptance still needed |
| --- | --- | --- |
| [Report 1](../adaptive_retention_report_1.pdf) | Method and research questions | No change to the source document |
| [DATA-v1 release](../data/releases/DATA-v1-20261019.json) and [input handoff](reports/data-integration.md) | Data/input identities and benchmark limits | Recipient-side package hash checks for each run environment |
| [Hung #39 PR](https://github.com/HungLD9505/adaptive-retention-ev/pull/46) and [report consolidation](https://github.com/HungLD9505/adaptive-retention-ev/pull/53) | Independent UrbanEV Development implementation and diagnostic evidence | Peer comparison, integration, reproduction, unresolved Colab criterion |
| [Baseline #51](https://github.com/HungLD9505/adaptive-retention-ev/pull/51) | Implementation and bounded Development checks | Peer acceptance and complete matched matrix |
| [Evaluation #52](https://github.com/HungLD9505/adaptive-retention-ev/pull/52) | Development calibration and partial analysis | Full artifact restore, six-city CHARGED, independent Final lock and Final runs |

The execution log for this report must distinguish commands actually rerun from historical commands quoted in linked evidence. Large inputs, checkpoints, and forecasts remain outside Git; preserve old run directories and reports. The final report PR must link its exact validation commands, results, reviewer decision, and accepted experiment artifacts.
