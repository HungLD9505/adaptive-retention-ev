# 21-day research execution plan

> Historical schedule and acceptance requirements. Current report-release scope and
> explicit unfulfilled criteria are recorded in [RELEASE_SCOPE.md](../RELEASE_SCOPE.md)
> and the [2 November readiness handoff](reports/main-readiness-20261102.md).
> The original schedule below is preserved; elapsed dates do not establish completion.

**Project:** Adaptive Retention EV — `HungLD9505/adaptive-retention-ev`  
**Execution window:** October 16–November 5, 2026 (21 calendar days)  
**Final delivery gate:** November 6, 2026, Asia/Ho_Chi_Minh (UTC+7)  
**Status:** Proposed for team review; becomes the official execution schedule after recorded approval. No sprint is accepted merely because its date has passed. No exact delivery hour has been specified; the lead must confirm it in the delivery issue.  
**Plan review:** [#15](https://github.com/HungLD9505/adaptive-retention-ev/issues/15)

## 1. Authority, scope, and starting evidence

[Report 1](../adaptive_retention_report_1.pdf) is the method reference. This plan schedules its implementation; it does not change the research method or experimental protocol. Read it with the [Master Research Flow](MASTER_RESEARCH_FLOW.md), [AGENTS.md](../AGENTS.md), [workflow](WORKFLOW.md), [data guide](../data/README.md), [UrbanEV reference](data/URBANEV.md), and [CHARGED reference](data/CHARGED.md).

Starting snapshot: `dev` at `0479da382df0cb198cddd07e42d435bccec484ae`, inspected October 17. October 16 remains day 1 of the requested schedule, not a retroactive claim of completion.

- The required UrbanEV and CHARGED archives were acquired and verified locally; [acquisition evidence](reports/data-acquisition.md) does not mean every developer has local copies.
- Dataset references and scoped verification exist. UrbanEV station energy is derived; CHARGED Hourly was already processed/imputed/aggregated by its provider. The [AMS evidence](reports/charged-ams-verification.json) does not certify other cities or causal suitability.
- UrbanEV hourly processing, project model inputs, models, controller, runner and experiments remain unimplemented at this snapshot.
- GitHub branch protection is not established; follow the documented PR/review rules manually. Passing CI is not peer approval or research evidence.

This is the **single sprint schedule**. GitHub Issues hold owners, task status, blockers, decisions, and acceptance evidence. Do not duplicate daily progress here or create a second task plan. Phase handoffs belong in `docs/reports/`, linked to code/config/run identities. The Master Flow remains the conceptual/method map, not a duplicate calendar.

## 2. Mandatory method and evidence requirements

These requirements survive schedule pressure. Any threatened omission must be raised explicitly in its issue and the final shortfall register; it cannot be silently removed or described as completed.

| Report 1 reference | Mandatory delivery scope |
|---|---|
| §4, §7: task and permitted data | Primary UrbanEV station-level hourly estimated energy; latest 24 hours → 24 hourly outputs once daily at a fixed origin. Separate 7/14/28-day initial target-history experiments, followed by chronological accumulation. History and labels for initial training must both fit the permitted prefix. Source training uses a fixed source set and only pre-deployment data. Source/development/final target entities stay separate. |
| §4, §7: inputs and causality | History, known calendar and missing mask; future calendar is permitted. No missing-Y filling, missing-as-zero assumption, backward filling from future, or target leakage. Store predictions before labels, score then update only after the complete valid 24-label vector arrives. Keep scheduled origins even when later labels prove incomplete. Weather/prices require demonstrated availability, not retrospective knowledge. |
| §5: backbone and loss | Initial two-layer GRU, hidden size 64; compatible encoder/head transfer; MLP with future calendar and Softplus 24-output head. Forecast loss is mean MAE over 24 normalized targets. Latent loss is mean squared difference divided dimensionwise by source-training latent standard deviations plus epsilon, with d=64. Total loss is forecast loss + λ × latent loss. Reference source encoder is frozen, in evaluation mode, without gradients. No main-experiment source selection. |
| §6: candidates and state | Three levels `{0, λlow, λhigh}`, `0 < λlow < λhigh`; initial block size 14 days, sensitivity assessed on development. Each block forks the same active model/optimizer state into three candidates, with shared data, normalization, batch order, schedule, step budgets and paired random streams. Select active before the block; store all candidate predictions before labels. Carry the selected trained checkpoint and optimizer forward; keeping active does not restore the block-start checkpoint. |
| §6: confidence decisions | Pair daily MAEs: improvement = active minus challenger. B counts days with all 24 valid labels, not hours. Require Bmin and a one-sided day-block-bootstrap LCB > δ, with δ ≥ 0 on the normalized loss scale; otherwise retain active. Select the largest qualifying LCB, then nearest current λ, then fixed order. Choose/lock positive λ values, initial level, Bmin, α, bootstrap segment/resampling settings, and two-challenger treatment on development. Report repeated-testing/nonstationarity limits; no safety guarantee. Decisions change future forecasts only. |
| §8.1: nine required baselines | Seasonal Naive with fallback; Target-only GRU; Frozen Source; Full Fine-tuning (λ=0); Fixed Retention; Simple Online Best-λ; Source-error controller; Uncertainty controller; Drift controller. Online Best-λ shares the candidate/block/checkpoint/update budget and differs in mean-error selection rather than confidence. Source-error uses recent frozen-source MAE on arrived labels; uncertainty uses a development-checked source-prediction dispersion estimator; drift compares currently available load descriptors with an available historical reference. Proxies use the same valid decision-time inputs, a documented mapping and comparable development-tuning budgets; high drift does not automatically require lower retention. |
| §8.3: five required ablations | Without Confidence; Fixed λ; Parameter Retention; Different Block Size; Without Source Initialization. Review implementation choices without replacing the core latent-retention main method. Reuse identical baseline/ablation runs without counting them as independent evidence. |
| §7–8: fairness and lock | Same forecasting task, cohorts, origins and label rules across compatible comparisons; at least three recorded seeds. Choose thresholds, budgets, exclusion rules, context groups and estimators on development. Lock before final evaluation; final labels may feed only the locked online algorithm, not design revision. |
| §8.2–8.3: metrics, analysis and cost | Original-unit MAE primary and RMSE supplementary; station-first aggregation, gain/NTR versus Target-only, predefined evaluation unit and zero-denominator handling, uncertainty accounting for station/time dependence. Analyze proxies versus retention differences, weekday/weekend and sparse/dense groups with development-derived thresholds, switches, insufficient evidence and post-switch error. Implement the isolated old-policy audit branch for harmful-switch analysis; never feed it to the controller. Report total runtime, memory, inference and update steps for all three candidates, with audit costs separately. |
| §1–3, §9: claims and report | Address RQ1–RQ3 using traceable evidence, including negative/null results. Check literature and related-method reproduction feasibility; custom proxies are not paper reproductions. No proof of novelty from renaming, backbone changes or good scores. Recovery time requires a known intervention/event and a development-locked definition; otherwise report error curves without an invented recovery metric. |

### Conditional requirements and optional extensions

- **CHARGED audit/QC is required in Sprint 1.** Its use for generalization is conditional on documented suitability, as in Report 1 §4. Execute an approved benchmark on accepted cities/sites if the gate passes. If none is usable or runs cannot finish, explicitly report missing cross-dataset evidence and obtain lead review; do not label it independent external validation or remove it silently. Shenzhen/UrbanEV overlap must be assessed before independence claims.
- **Strict online claims are conditional on upstream/time/label evidence.** If upstream imputation/arrival causality cannot be established, label results a chronological benchmark on published data, disclose limits, and never claim local leakage tests undo upstream processing. Missing-Y protection in our own pipeline remains mandatory.
- **Optional, only after mandatory work:** TCN/other backbones; synthetic stress tests with known interventions; weather/price/POI/Supplemental features; extra λ levels or continuous λ; context-specific controllers; source selection; additional infrastructure. Method-changing extensions need separate review. Related-paper implementations beyond compatible mandatory comparisons require feasibility review; comparisons to incompatible horizons/quantiles are not interchangeable with this task.
- UrbanEV Supplemental remains unused for model inputs. Optional work may be deferred to protect the schedule; required baselines, ablations, budgets, seeds or causal safeguards may not be silently downgraded.

## 3. Ownership and GitHub tracking

The lead assigns one owner and a different reviewer per implementation issue before work begins. The following workstreams are proposed responsibilities, not unconfirmed assignments to individuals. Contracts are reviewed by their consumers before parallel implementation; four developers should not edit a shared working branch.

| Workstream | Responsibility / handoff |
|---|---|
| Data and integration | UrbanEV processing; accepted input artifacts and lineage; coordinate QC decisions with input/model consumers. |
| Model and loss | Source/target GRU, loss/gradient semantics and compatible checkpoints. |
| Controller and runner | Confidence decisions, chronological event ordering, candidate and audit state, resumability. Split these tasks between available owners after contracts agree. |
| Baselines, evaluation and report | Fair comparison adapters, metrics/run matrix, development/final lock, analysis and report. Data QC can run in parallel early; report outline work can progress without fabricated results. |

Issue creation is backlog preparation, not evidence of implementation or authorization to merge.

| Sprint | Task / evidence owner to be assigned in issue | Dependencies |
|---|---|---|
| 1 | [#16 UrbanEV hourly processing, QC and acquisition handoff](https://github.com/HungLD9505/adaptive-retention-ev/issues/16) | Existing acquisition #8; source references #11/#13 |
| 1 | [#17 CHARGED release audit and suitability](https://github.com/HungLD9505/adaptive-retention-ev/issues/17) | Acquisition #8 and current CHARGED/AMS findings |
| 1 | [#18 Inputs and shared contracts](https://github.com/HungLD9505/adaptive-retention-ev/issues/18) | #16; CHARGED branch depends on #17 disposition |
| 2 | [#19 GRU, adaptation and latent retention](https://github.com/HungLD9505/adaptive-retention-ev/issues/19) | #18 accepted inputs/contracts |
| 2 | [#20 Confidence controller](https://github.com/HungLD9505/adaptive-retention-ev/issues/20) | #18 score/state interfaces; independent fixtures can precede model integration |
| 2 | [#21 Runner and end-to-end smoke](https://github.com/HungLD9505/adaptive-retention-ev/issues/21) | #19 + #20, using #18 contracts |
| 3 | [#22 Baselines and ablations](https://github.com/HungLD9505/adaptive-retention-ev/issues/22) | #21; specify adapters/test expectations in Sprint 2 to avoid integration surprises |
| 3 | [#23 Development tuning and locked final evaluation](https://github.com/HungLD9505/adaptive-retention-ev/issues/23) | #22, accepted dataset/input versions and #17 disposition |
| 1–3 / delivery | [#10 Existing thesis/report issue](https://github.com/HungLD9505/adaptive-retention-ev/issues/10) | Outline/literature now; final Results/Discussion depend on #23 evidence |

Critical path: verified UrbanEV source → hourly QC → inputs/contracts → GRU + controller → integrated runner → complete baseline/ablation readiness → development selection → lock → final execution → analysis/report → delivery. CHARGED QC and report drafting run in parallel. A blocked CHARGED decision must not prevent independent UrbanEV implementation, but it remains visible as a cross-dataset risk.

## 4. Sprint 1 — October 16–22: Data and input foundation

**Goal:** reproducible, reviewed data and model-input contracts before model integration.

| Deliverable | Dependencies | Acceptance criteria |
|---|---|---|
| Acquisition handoff / #16 | Existing local archive identities and acquisition manifest | Verify on the machine used for processing; preserve archive bytes and ignored storage; distinguish completed local acquisition from fresh reproduction. Record source fingerprints. Do not spend the sprint rebuilding download tooling. |
| UrbanEV hourly processing and QC / #16 | Confirm station-raw file/target/time semantics | Document reviewed aggregation and hour-completeness rules; preserve genuine zeros and missing masks; do not fill Y. Validate schema/IDs/units, time grid/duplicates/boundaries and excluded samples. New outputs and reproducible commands, not overwritten prior evidence. |
| CHARGED audit/QC / #17 | Standard Hourly release and scoped AMS findings | Inspect every proposed city/cohort, published imputation/zero handling, time/bin assumptions and energy suitability. Disposition static/hourly discrepancies, plug-duration limits, missing masks and Shenzhen overlap. Provide accepted/limited/blocked decisions, including conditions under which a published-data benchmark is supportable. No need to enable optional price/weather merely because files exist. |
| Model inputs and shared contracts / #18 | Accepted UrbanEV QC; CHARGED input scope follows #17 | Agree entity splits, training/deployment cutoffs, exact budgets, calendar/mask fields, causal normalization and complete-label gates. Test prefix-only sample construction, disjointness, hour boundaries, missingness and inverse scaling. Record real eligible sample counts per budget, accepted artifacts and data/forecast/checkpoint interface schemas. |

The Master Flow's implementation references—hash-based 60/20/20 splits, per-city CHARGED splits, `X_hist[24,7]`, `C_future[24,5]`, `Y[24]`, permitted-prefix p95 scaling, deployment dates UrbanEV 2022-12-01 and CHARGED 2023-07-01—must be explicitly reviewed in #18. They are reference choices requiring verification, not newly fixed Report 1 constants. Any change must be recorded at its proper protocol/method review level rather than silently introduced by this schedule.

**Definition of Done / October 22 gate:** #16/#18 have accepted real-data handoffs and consumer-reviewed contracts; #17 has a reviewed dataset disposition and actionable blockers. Relevant independent fixtures and README checks pass; implementation PRs are peer-approved and merged by an authorized team member into dev. Each accepted run records config, input/source identity, code revision, environment/runtime, run ID and acceptance scope. Another developer reproduces the accepted input sample from documented inputs. Acquisition or CSV explanations alone do not satisfy this gate. A limited/blocked CHARGED result must be carried explicitly into Sprint 3 and delivery status.

## 5. Sprint 2 — October 23–29: Method and end-to-end execution

**Goal:** exercise the actual method chronologically before spending the final week on experiments.

| Deliverable | Dependencies | Acceptance criteria |
|---|---|---|
| Source GRU, target adaptation and retention / #19 | Sprint 1 inputs/contracts | Implement the §5 backbone/loss exactly; fixed source checkpoint before deployment, compatible transfer, frozen evaluation-mode reference and fixed source latent scales. Verify shapes, nonnegative outputs, gradients, λ=0 behavior, source freeze and checkpoint reload. Real development smoke produces stored forecasts; fixture success is not research effectiveness. |
| Confidence controller / #20 | Score/config interfaces; model-independent tests | Implement all §6 candidate/LCB/Bmin/δ/tie-break semantics. Configuration choices remain development decisions. Test insufficient evidence, exact threshold/equality, multiple challengers, zero level and deterministic bootstrap behavior. No final-target-informed decisions. |
| Runner, audit and smoke / #21 | #19 + #20 and accepted inputs | Same model/optimizer initial state and paired randomness; forecast-store-score-update order, all-24-label gate, missing-day logs, boundary ordering and selected trained-state carry. Test resume without changing issued forecasts; isolated old-policy audit branch cannot influence decisions. Real development run exercises a block boundary and decision path; fixtures force switch/keep/missing paths if real smoke does not trigger them. |
| Experiment readiness / #21, #22 interface preparation | Integrated runner | Record runtime/memory/update/inference accounting including all candidates and audit. Measure representative real-data throughput and extrapolate the required seed/budget/method matrix. Confirm compute/storage availability and experiment owners. Agree baseline/ablation adapters and metrics schemas without starting final evaluation. |

**Definition of Done / October 29 gate:** reviewed model/controller/runner code is integrated on dev with offline tests and real end-to-end evidence; a second developer can resume/reproduce the smoke using identified artifacts. Forecast chronology and checkpoint semantics pass; all three candidates and audit costs are visible. The complete mandatory experiment matrix has a measured capacity estimate and a feasible execution window. If hardware, method completeness or throughput is insufficient, the lead receives a specific gap and recovery decision before Sprint 3; a single demo model is not a substitute.

## 6. Sprint 3 — October 30–November 5: Comparisons, lock and report

**Goal:** complete fair comparisons and evidence-supported conclusions, not only an adaptive-method result.

| Deliverable | Dependencies | Acceptance criteria |
|---|---|---|
| Required baselines and ablations / #22 | Accepted runner and method interfaces | Implement/test all nine baselines and five ablations listed in §2, reusing identical configurations. Verify every method on real development data; fix proxy estimator/calibration and equal tuning budgets. Define Parameter Retention and Without Source Initialization variants for review without changing the main method. Record related-paper feasibility and honest adaptation/reproduction labels. |
| Development tuning and configuration lock / #23 | All comparison methods ready; accepted data | Select finite training/tuning budgets, λ values, confidence/bootstrap settings, update schedules, proxy mappings, block sensitivity values, ≥3 seeds, evaluation units, context thresholds and exclusions using development only. Record exact run matrix, immutable config/hash, data/cohort and code identities plus independent lock approval before final-target evaluation. |
| Locked final evaluation / #23 | Approved lock, runtime capacity and accepted artifacts | Evaluate all 7/14/28-day budgets and ≥3 seeds for the mandatory comparison/ablation matrix on eligible final targets. Use accepted CHARGED scope if its audit gate passes; otherwise report the unmet generalization objective. Final labels only enter the locked online algorithm. Preserve forecasts, metrics, checkpoint lineage, failed/excluded runs and complete candidate/audit costs. |
| Analysis and final report / #23 → #10 | Actual run outputs, not expected outcomes | Original-unit MAE/RMSE, gain/NTR including zero-denominator cases, station-first uncertainty, proxy/retention relationships, context/seed stability, switches and isolated audit analysis. Answer RQ1–RQ3 with distributions/practical magnitude and limitations. No arbitrary recovery time, novelty or superiority claim. Provide commands/config/run links and explain missing or negative results. |

### Sprint 3 dependency checkpoints

These are gates, not a duplicate daily progress log. Status and changes stay in the linked issues.

| Target checkpoint | Required decision/evidence |
|---|---|
| October 30–31 | Complete baseline/ablation development smoke and bounded tuning. If any mandatory method is absent, do not lock a reduced matrix and call it complete. |
| November 1 | Independent configuration/data/cohort/code lock approval; final run matrix fits measured capacity. Final target performance must not have been used to select it. |
| November 2–3 | Target completion window for final runs and integrity checks, leaving time for analysis and one correctness-driven rerun if capacity permits. |
| November 4–5 | Evidence reconciliation, uncertainty/cost/context analysis and report review. No post-hoc final-score tuning. |

If a correctness fix changes locked data, code or protocol, invalidate affected results, record why, obtain a new lock and rerun the affected matrix. Preserve original evidence; do not select the better of pre/post-fix final scores. If rerun time is insufficient, disclose the shortfall rather than present invalid results.

**Definition of Done / November 5 gate:** mandatory run matrix and analysis are reviewed and traceable; #10 report matches actual implementation/results; reproduction commands and artifact access are checked by a second developer. Required comparisons, ablations, budgets, seeds and costs are accounted for. Unresolved data claims are bounded explicitly. Missing mandatory evidence means this gate is not fully met, even if documentation is polished. No positive result is required for honest delivery; a valid negative result is acceptable.

## 7. November 6 — Final delivery gate

The lead records the delivery decision in #15, with #10/#23 evidence links and any remaining issues. Do not create another schedule or duplicate the report.

- **Method coverage:** each mandatory row in §2 maps to reviewed code and an accepted run/analysis, or a named unmet requirement with impact.
- **Reproducibility:** source identities, approved protocol/config lock, code revision, ≥3 seeds, cohort/sample counts, runtime/environment, commands, forecasts/metrics/checkpoints and storage access are recoverable. Raw data and large artifacts remain outside Git.
- **Research evidence:** all required budgets/comparisons/ablations and accepted-dataset scope are accounted for; complete candidate and separate audit costs are reported; no final-data tuning, invented measurements or unqualified external/strict-online claims.
- **Report:** RQ1–RQ3, methodology, evidence, literature/novelty limits, failed/null results and data/compute limitations match the delivered artifacts. Report 1 and original evidence remain unchanged.
- **Engineering:** relevant CI passes, PRs have independent peer review and authorized merges, dev is reproducible, finished branches/issues are cleaned up only when criteria are met; preserve main/dev/master and unmerged work.

**Decision:** record Accepted, Accepted with explicit limitations, or Not ready. Accepted with limitations is not permission to hide missing core requirements. Any unmet mandatory requirement remains explicitly identified as incomplete; the lead's scope/delivery disposition is recorded, not retroactively described as method-complete. November 6 is a delivery gate, not permission to tune on final results or extend the 21 execution days silently.

## 8. Risks and escalation rules

| Risk / trigger | Required action and impact |
|---|---|
| Sprint 1 gate misses October 22 | Record exact missing QC/input evidence, owner and recovery date in its issue immediately. Model fixtures may continue, but no acceptance or final experiments on unapproved data. Do not take time from required evaluation without reporting the resulting deadline risk. |
| CHARGED imputation/masks, static/hourly discrepancies or source overlap remain unresolved | #17 records city-specific allowed benchmark claims or blocked use. No silent repairs, source substitution, independent-external claim or automatic deletion of CHARGED from objectives. |
| UrbanEV target/time semantics or actual label arrival cannot be verified | #16/#18 record assumptions and claim boundaries. Use no invented labels; escalate suitability. Local chronological replay cannot establish real-time label availability. |
| Hardware/owners unavailable or projected matrix exceeds remaining time at October 29 / November 1 gate | Lead assigns resources/reorders independent tasks or reviews bounded development work. Defer optional extensions first. Required baselines, five ablations, budgets and ≥3 seeds remain requirements; report any threatened omission explicitly. |
| Late baseline/controller bug or invalid final run | Stop affected claims; preserve logs; review fix, relock and rerun. If impossible by deadline, report not-ready/limited delivery with exact missing evidence. |
| No improvement over Online Best-λ/fixed/fine-tuning, unstable results or high overhead | Report null/negative results and narrow claims. Do not retune final targets or substitute a favorable subset. |
| Review/integration bottleneck across four developers | Use contract reviews, separate branches, small linked PRs and consumer review. Resolve shared-interface changes before merging consumers; no direct pushes to main and no agent self-approval. |

Escalations live in task issues and are summarized by the lead at gates. No artificial completion percentages or daily duplicate tracking. Any proposed change to Report 1 is a separate method decision/PR and must identify the requirement at risk; deadline pressure alone does not amend the method.

## 9. Review, approval, and one-time promotion

1. Submit this documentation-only plan in a branch from dev, linking #15; require CI and independent review. Task issues track work; this plan does not launch implementation or alter existing artifacts.
2. Record team-lead plan approval against the exact PR head commit. **Approval of the plan is not authorization to merge or promote it.** Do not merge into dev or main autonomously.
3. Once approved, report the PR/head and ask the team lead for explicit authorization for the dev merge and the **one-time promotion of the approved plan to main**, specifying the exact scope. Do not infer authorization from earlier data-documentation merges.
4. Only after authorization, use the existing PR/review workflow. A main-targeted promotion PR must expose its actual diff; if dev contains unrelated work, do not bundle it under plan-promotion approval. No force-push/direct push to main. Later main updates each require separate authorization.
5. After an authorized merge, verify preservation, close only completed issues and delete only the finished working branch. Keep #15 open until its approval/promotion acceptance criteria are resolved; preserve implementation issues until their own evidence is accepted.
