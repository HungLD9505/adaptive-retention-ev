# Issue #99 history extension and teacher review manuscript

Completed the requested baseline check, stronger target-only calibration, 7/14/28-day replay and a nine-page English teacher-review manuscript. The manuscript is at report/teacher-review-20261110 in PDF, DOCX and Markdown source form, with figures, equations and references.

## Baseline acceptance audit

Cyber PR #104 remains at 5f67bd225f0fe340393a6d73bcc03363144d2561 with CHANGES_REQUESTED. Its 172 unique ledger rows and their aggregates were independently recomputed. Direct code inspection confirms repeated target histories at all graph nodes, non-advancing SARIMA fitted state between refits, a non-null-only label availability gate, and zero metrics for empty score sets. External prediction/checkpoint authenticity remains unresolved. A prior audit reproduced Daily Naive for target 1405; that limited positive finding does not authenticate the entire benchmark.

Duc issue #96 is open with no comments at the final check. The only PR found under huuduc32 is the earlier independent retention study #69, which does not satisfy the baseline issue. Unpushed work is unknown. The manuscript leaves architecture superiority unresolved and does not treat provisional rankings as accepted evidence. baseline-audit.json retains the exact inspected head, ledger means and review reference.

## Training duration correction

All three budgets use the existing authenticated Source10 checkpoints and the same Source population. Independent prepared-row header counts are 65,888 Source examples at every budget. Source training was not rerun.

Both initialization modes receive the same five initial epoch candidates, 3/10/30/100/300, scored only on the first 28 scheduled origins of the original four calibration targets. A declared 900-epoch extension is unused because no 300-epoch candidate wins. Random target-only selects 30/100/100 epochs at 7/14/28 days. Source fine-tuning selects 3/3/10. Random validation error worsens at 300 in all budgets. This is a finite validation-selected schedule with fixed learning rate 0.001, not a global convergence proof.

The selected Source duration is then shared by all three λ=0/0.1/1 experts. Calibration selects λ=1/1/0 across budgets. Both selectors start from that selected expert and see exactly the same independent bank. The same-challenger bootstrap gate is retained. Mean and confidence policies differ only in gating and their resulting active-level histories.

There are 120 epoch-calibration invocations, 36 bank-calibration invocations and 144 evaluation training invocations per budget, totalling 900 GRU invocations across three budgets. The 540 five-method evaluation rows are derived from the underlying four trained models per station/seed (three experts and one random model). They must not be counted as 540 independent training jobs.

## Results

| Method MAE in kWh | 7 days | 14 days | 28 days |
| --- | ---: | ---: | ---: |
| Target-only | 5.052071 | 4.834071 | 4.769687 |
| Source fine-tune | 3.367095 | 3.304605 | 3.348210 |
| Calibration-selected Fixed | 3.318623 | 3.267000 | 3.348210 |
| Past mean selection | 3.323416 | 3.290432 | 3.325200 |
| Confidence-gated selection | 3.323394 | 3.275479 | 3.313967 |
| Daily naive | 5.090612 | 5.090612 | 5.090612 |
| Weekly naive | 6.077298 | 6.077298 | 6.077298 |

Source fine-tuning improves on the validation-selected target-only model by approximately 33.4/31.6/29.8%. At fourteen days the stronger target-only result revises the previous 39.5% estimate downward to 31.6%. Confidence versus mean improves negligibly at seven days and by approximately 0.45/0.34% at fourteen/twenty-eight days.

Confidence beats calibration-selected Fixed by 1.02% at twenty-eight days. The selected Fixed there is λ=0; retrospectively constant λ=1 scores 3.292501 and beats the gate at 3.313967. This diagnostic is explicitly retrospective. The favorable result therefore does not establish general adaptive superiority.

All three histories have identical per-station/seed scored-origin masks. Coverage is 888 station-days per seed, or 2,664 seed-days per history. Missingness and incomplete labels remain excluded identically. Full-precision MAE/RMSE, station means, intervals, chosen epochs, Fixed coefficients and retrospective constant scores are in verified-summary.json and cells.csv.

## Verification and execution

Independent post-run readback checks all 31,968 neural evaluation forecast scores, their saved vector hashes, available complete labels, original-unit MAE/MSE, selected expert lineage and every method/history mask. The normal causal runner saves predictions before scoring and updates. Inputs were rehashed after each phase. Publisher raw archives were not freshly checked.

The two deterministic baselines add 72 station-budget-method rows. Their complete predictor pass is saved before retrospective scoring. Daily missing predictor hours use the mean of observed daily hours. Weekly unavailable hours use the daily forecast. Target labels are never filled. A regression fixture checks that masked values are not silently interpreted as observed zero demand.

Three budget-specific CPU processes ran concurrently, each with one Torch thread. The full budget pipelines completed in approximately 244/257/267 seconds. Invocation wall times include file reading, replay, training and score readback in a concurrent environment. Historical Source pretraining cost is outside these timers.

The implementation only extends the continuous runner with an explicit approved_history_days argument. Its existing default remains fourteen days, and the Development role guard remains in force. New tests check the history opt-in and baseline fallback. The original Report 1 task, primary frozen report, inputs, Source checkpoints and Final artifacts are preserved.

External root:
 /Users/quyenmanh/Developer/TFL-EV/runs/issue99-history-review-20261110-v1

Reproduce each budget with python -m tools.issue99_history_study, specifying --input-parent, --sources, --inventory, --history-days and a new --output. Run tools.issue99_simple_baselines for the deterministic controls and tools.issue99_history_report for independent aggregate readback. The Source directory contains source-seed42/epoch-10.pt through source-seed44/epoch-10.pt.

The DOCX/PDF were built with the resolved bundled document runtime. Nine pages were rendered and inspected after the final layout update. Tables remain together, the inherited title border was removed, equations and numeric values were checked, and the final PDF text and Word styling were structurally checked. Final document byte identities are in the report artifact manifest. Authoring helpers and initial rendering attempts remain in the external run root.
